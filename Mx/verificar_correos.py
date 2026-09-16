"""Prevalidación conservadora de correos. No envía mensajes ni consulta SMTP."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import tempfile

import dns.exception
import dns.resolver
from email_validator import EmailNotValidError, validate_email


class DNSChecker:
    def __init__(self, timeout=4.0, retries=1, resolver=None):
        self.resolver = resolver if resolver is not None else dns.resolver.Resolver()
        self.timeout = timeout
        self.retries = retries

    def query(self, name, kind):
        for attempt in range(self.retries + 1):
            try:
                records = list(self.resolver.resolve(
                    name, kind, lifetime=self.timeout, search=False
                ))
                return ("OK", records) if records else ("SIN_REGISTRO", [])
            except dns.resolver.NXDOMAIN:
                return "NXDOMAIN", []
            except dns.resolver.NoAnswer:
                return "SIN_REGISTRO", []
            except (dns.exception.DNSException, OSError):
                if attempt == self.retries:
                    return "ERROR_TEMPORAL", []
        raise AssertionError("Bucle de reintentos inesperado")

    def addresses(self, name):
        statuses = []
        for kind in ("A", "AAAA"):
            status, _ = self.query(name, kind)
            if status == "OK":
                return "OK"
            statuses.append(status)
        return "ERROR_TEMPORAL" if "ERROR_TEMPORAL" in statuses else "SIN_DIRECCION"

    def check(self, domain):
        status, records = self.query(domain, "MX")
        if status == "NXDOMAIN":
            return dns_result("INVALIDO", "DOMINIO_INEXISTENTE", "DNS indica que el dominio no existe.")
        if status == "ERROR_TEMPORAL":
            return dns_result("REVISAR", "DNS_TEMPORAL", "No se pudo resolver MX. Reintentar después; no descartar.")
        if status == "SIN_REGISTRO":
            addresses = self.addresses(domain)
            if addresses == "OK":
                return dns_result("REVISAR", "MX_IMPLICITO", "Sin MX, pero con A/AAAA: posible recepción por MX implícito; no confirmada.")
            if addresses == "ERROR_TEMPORAL":
                return dns_result("REVISAR", "DNS_TEMPORAL", "Sin MX; no fue posible completar la consulta A/AAAA.")
            return dns_result("INVALIDO", "SIN_RUTA_DNS", "Sin MX ni dirección A/AAAA utilizable en esta consulta.")

        mx = sorted((int(r.preference), str(r.exchange).lower()) for r in records)
        labels = [f"{priority} {host}" for priority, host in mx]
        null_records = [(priority, host) for priority, host in mx if host == "."]
        if null_records:
            if mx == [(0, ".")]:
                return dns_result("INVALIDO", "NULL_MX", "El dominio declara explícitamente que no recibe correo.", labels)
            return dns_result("REVISAR", "MX_INCONSISTENTE", "Null MX mal formado o combinado con otros MX; revisar configuración.", labels)

        temporary = False
        for _, host in mx:
            host_status = self.addresses(host)
            if host_status == "OK":
                return dns_result("APTO_DNS", "MX_RESUELVE", "Al menos un MX tiene A/AAAA. No confirma servidor SMTP, buzón ni entrega.", labels)
            temporary |= host_status == "ERROR_TEMPORAL"
        if temporary:
            return dns_result("REVISAR", "DNS_TEMPORAL", "Hay MX, pero no se pudo completar su resolución a IP.", labels)
        return dns_result("INVALIDO", "MX_SIN_IP", "Los MX publicados no tienen A/AAAA utilizable en esta consulta.", labels)


def dns_result(state, code, reason, mx=None):
    return {"estado": state, "codigo": code, "motivo": reason, "mx": mx or []}


def prepare_lines(lines, stop_event=None, on_progress=None):
    rows = []
    seen = {}
    for number, original in enumerate(lines, 1):
        if number % 128 == 1 and stop_event is not None and stop_event.is_set():
            raise ValueError('Importación cancelada. Se conserva la lista anterior.')
        if number % 1000 == 0 and on_progress:
            on_progress(number)
        original = original.rstrip("\r\n")
        value = original.strip()
        if not value:
            continue
        row = {
            "linea": number, "original": original, "normalizado": "", "dominio": "",
            "duplicado_de_linea": None, "requiere_smtputf8": False,
            "buzon": "NO_COMPROBADO", "catch_all": "NO_COMPROBADO",
            "estado": "", "codigo": "", "motivo": "", "mx": [],
        }
        try:
            parsed = validate_email(value, check_deliverability=False,
                                    allow_quoted_local=True, allow_domain_literal=True)
        except EmailNotValidError as exc:
            row.update(dns_result("INVALIDO", "FORMATO_NO_ADMITIDO", str(exc)))
        else:
            row["normalizado"] = parsed.normalized
            row["requiere_smtputf8"] = parsed.smtputf8
            if parsed.domain.startswith("["):
                row.update(dns_result("REVISAR", "DOMINIO_LITERAL", "Dirección con IP literal: fuera del filtro DNS de dominios."))
                key = parsed.normalized
            else:
                row["dominio"] = parsed.ascii_domain
                # No convertir la parte local a minúsculas ni quitar puntos o +etiquetas.
                key = parsed.local_part + "@" + parsed.ascii_domain
            row["duplicado_de_linea"] = seen.get(key)
            seen.setdefault(key, number)
        rows.append(row)
    return rows


def verify(rows, checker, workers=8):
    domains = sorted({r["dominio"] for r in rows if r["dominio"] and not r["estado"]})
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(checker.check, domain): domain for domain in domains}
        for count, future in enumerate(as_completed(futures), 1):
            results[futures[future]] = future.result()
            if count % 25 == 0 or count == len(domains):
                print(f"Dominios revisados: {count}/{len(domains)}", flush=True)
    for row in rows:
        if not row["estado"]:
            row.update(results[row["dominio"]])
        if row["requiere_smtputf8"]:
            row["motivo"] += " La parte local internacionalizada requiere soporte SMTPUTF8."
    return rows


def render_html(report):
    escape = lambda value: html.escape(str(value), quote=True)
    body = []
    for row in report["resultados"]:
        duplicate = row["duplicado_de_linea"]
        cells = [row["linea"], row["original"], row["normalizado"], row["estado"],
                 row["codigo"], f"Línea {duplicate}" if duplicate else "—",
                 "; ".join(row["mx"]), row["motivo"]]
        body.append('<tr>' + ''.join(f'<td>{escape(cell)}</td>' for cell in cells) + '</tr>')
    summary = " · ".join(f"{key}: {value}" for key, value in report["resumen"].items())
    return f'''<!doctype html>
<html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Revisión de correos</title>
<style>body{{font:15px system-ui;margin:28px;color:#202b38}}h1{{margin-bottom:8px}}
.aviso{{padding:16px;background:#fff4d6;border-radius:8px}}table{{border-collapse:collapse;width:100%;margin-top:24px}}
td,th{{padding:10px;border:1px solid #d9e0e6;text-align:left;vertical-align:top;overflow-wrap:anywhere}}
th{{background:#edf3fa}}tbody tr:nth-child(even){{background:#f8fafc}}.tabla{{overflow:auto}}</style>
<h1>Revisión de correos</h1><p>Informe generado (UTC): {escape(report['fecha_utc'])}</p>
<p>Consulta DNS finalizada (UTC): {escape(report['fecha_dns_utc'])}</p>
<p>{escape(summary)}</p><p>Duplicados adicionales: {report['duplicados']}</p>
<p class="aviso">APTO_DNS solo significa infraestructura DNS encontrada, no buzón existente ni entrega garantizada.
REVISAR no debe descartarse automáticamente. INVALIDO refleja esta comprobación, no una eliminación.
Este informe solo describe la revisión previa, no acredita envíos ni comprueba catch-all.
Los duplicados mantienen su resultado y apuntan a su primera línea.</p>
<div class="tabla"><table><thead><tr><th>Línea</th><th>Original</th><th>Normalizado</th><th>Estado</th>
<th>Código</th><th>Duplicado de</th><th>MX (prioridad y servidor)</th><th>Motivo</th></tr></thead>
<tbody>{''.join(body)}</tbody></table></div></html>'''


def save_report(rows, output_root, dns_checked_at=None):
    output_root.mkdir(parents=True, exist_ok=True)
    # Cada ejecución crea su propia carpeta: nunca sobrescribir el original ni un informe.
    folder = Path(tempfile.mkdtemp(prefix=datetime.now().strftime("revision_%Y%m%d_%H%M%S_"), dir=output_root))
    report = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "fecha_dns_utc": dns_checked_at or datetime.now(timezone.utc).isoformat(),
        "alcance": "Sintaxis y DNS; buzones y catch-all no comprobados. Sin SMTP ni envíos.",
        "total": len(rows), "resumen": dict(Counter(r["estado"] for r in rows)),
        "duplicados": sum(r["duplicado_de_linea"] is not None for r in rows),
        "resultados": rows,
    }
    (folder / "informe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "informe.html").write_text(render_html(report), encoding="utf-8")
    return folder, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path, help="TXT UTF-8, una dirección por línea y sin encabezado")
    parser.add_argument("--salida", type=Path, default=Path("resultados"), help="Carpeta para informes nuevos")
    parser.add_argument("--workers", type=int, default=8, help="Consultas de dominios simultáneas (1-32)")
    parser.add_argument("--timeout", type=float, default=4, help="Segundos por intento DNS (0.1-30)")
    parser.add_argument("--reintentos", type=int, default=1, help="Reintentos de cada consulta fallida (0-3)")
    args = parser.parse_args()
    if not 1 <= args.workers <= 32 or not 0.1 <= args.timeout <= 30 or not 0 <= args.reintentos <= 3:
        parser.error("Usa workers 1-32, timeout 0.1-30 y reintentos 0-3.")
    if args.archivo.suffix.lower() != ".txt":
        parser.error("Se espera un .txt UTF-8 con una dirección por línea, no un archivo Excel/CSV.")
    try:
        rows = prepare_lines(args.archivo.read_text(encoding="utf-8-sig").splitlines())
        if not rows:
            parser.error("El archivo está vacío o solo contiene líneas en blanco.")
        print(f"Direcciones: {len(rows)}. Solo sintaxis y DNS; no se enviarán correos.", flush=True)
        verify(rows, DNSChecker(args.timeout, args.reintentos), args.workers)
        folder, report = save_report(rows, args.salida)
    except (OSError, UnicodeError, dns.exception.DNSException) as exc:
        parser.exit(1, f"No se pudo completar: {exc}\n")
    print("Resultado:", report["resumen"])
    print("Duplicados adicionales:", report["duplicados"])
    print("Abre en tu navegador:", (folder / "informe.html").resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
