"""
mxcorreo_server.py — Backend JSON-RPC por stdin/stdout para la interfaz Electron.
Envuelve campana.py y verificar_correos.py con comunicación en tiempo real.
"""
from __future__ import annotations

import json
import sys
import os
import re
import threading
import traceback
from pathlib import Path

# Asegurar que el directorio del script esté en el path
_here = Path(__file__).parent
BASE_DIR = _here
sys.path.insert(0, str(_here))
from datetime import datetime


_send_lock = threading.Lock()
_cancel_event = threading.Event()


def _send(obj: dict):
    """Emite un objeto JSON al renderer (stdout) de forma thread-safe."""
    line = json.dumps(obj, ensure_ascii=False)
    with _send_lock:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


def _send_event(event: str, data=None):
    _send({"type": "event", "event": event, "data": data})


def _send_progress(msg: str, value: int = -1):
    _send({"type": "progress", "message": msg, "value": value})


def _send_result(req_id, result):
    _send({"type": "result", "id": req_id, "ok": True, "data": result})


def _send_error(req_id, error: str):
    _send({"type": "result", "id": req_id, "ok": False, "error": error})


# ──────────────────────────────────────────────
# Handlers de comandos
# ──────────────────────────────────────────────

def cmd_ping(params, req_id):
    _send_result(req_id, {"pong": True, "version": "2.0.0"})


EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')


def extract_emails_from_cell(val) -> list[str]:
    """Extrae direcciones de correo o candidatos con '@' de una celda individual."""
    if val is None:
        return []
    s = str(val).strip()
    if "@" not in s:
        return []
    if s.lower().startswith("mailto:"):
        s = s[7:].strip()
    found = EMAIL_REGEX.findall(s)
    if found:
        cleaned = [em.strip(".,;:()[]{}<>\"' ") for em in found if em.strip(".,;:()[]{}<>\"' ")]
        if cleaned:
            return cleaned
    tokens = re.split(r'[\s,;|\n\r]+', s)
    candidates = []
    for tok in tokens:
        tok = tok.strip(".,;:()[]{}<>\"' ")
        if "@" in tok:
            candidates.append(tok)
    return candidates if candidates else [s.strip(".,;:()[]{}<>\"' ")]


def extraer_correos_de_archivo(path: Path, columna_deseada: str = "") -> list[str]:
    """Extrae correos desde cualquier archivo Excel (.xlsx, .xls), CSV, TSV, TXT o .mxlista."""
    suffix = path.suffix.lower()
    col_clean = columna_deseada.strip().lower() if columna_deseada else ""
    candidatos: list[str] = []

    # 1. Excel (.xlsx, .xls, .xlsm)
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        try:
            from python_calamine import CalamineWorkbook
            wb = CalamineWorkbook.from_path(path)
            for sheet_name in wb.sheet_names:
                sheet = wb.get_sheet_by_name(sheet_name)
                if sheet.end is None:
                    continue
                rows = sheet.to_python(skip_empty_area=False)
                if not rows:
                    continue
                target_col_idx = None
                if col_clean and col_clean not in {"auto", "todos", "todas"}:
                    first_row = [str(c).strip().lower() for c in rows[0]]
                    for idx, h in enumerate(first_row):
                        if h == col_clean:
                            target_col_idx = idx
                            break
                if target_col_idx is not None:
                    for row in rows[1:]:
                        if target_col_idx < len(row):
                            candidatos.extend(extract_emails_from_cell(row[target_col_idx]))
                else:
                    for row in rows:
                        for cell in row:
                            candidatos.extend(extract_emails_from_cell(cell))
            return candidatos
        except Exception:
            pass  # Fallback a lectura de texto si calamine fallara

    # 2. .mxlista (JSON)
    if suffix == ".mxlista":
        from importar_contactos import load_import
        items = load_import(path)
        return [i["normalizado"] for i in items if i.get("normalizado")]

    # 3. CSV o texto delimitado
    if suffix in {".csv", ".tsv"}:
        import csv
        content = None
        for enc in ("utf-8-sig", "latin-1", "cp1252"):
            try:
                content = path.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        if content is None:
            content = path.read_text(encoding="utf-8-sig", errors="ignore")

        lines = content.splitlines()
        if not lines:
            return []

        sample = content[:8192]
        try:
            delim = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except Exception:
            delim = ","

        reader = csv.reader(lines, delimiter=delim)
        rows = list(reader)
        if not rows:
            return []

        target_col_idx = None
        if col_clean and col_clean not in {"auto", "todos", "todas"}:
            first_row = [str(c).strip().lower() for c in rows[0]]
            for idx, h in enumerate(first_row):
                if h == col_clean:
                    target_col_idx = idx
                    break

        if target_col_idx is not None:
            for row in rows[1:]:
                if target_col_idx < len(row):
                    candidatos.extend(extract_emails_from_cell(row[target_col_idx]))
        else:
            for row in rows:
                for cell in row:
                    candidatos.extend(extract_emails_from_cell(cell))
        return candidatos

    # 4. TXT o fallback general de texto
    content = None
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            content = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if content is None:
        content = path.read_text(encoding="utf-8-sig", errors="ignore")

    for line in content.splitlines():
        candidatos.extend(extract_emails_from_cell(line))
    return candidatos


def cmd_verificar(params, req_id):
    """Verifica y depura una lista de correos escaneando celdas. Retorna estadísticas y lista depurada."""
    try:
        from verificar_correos import prepare_lines, DNSChecker
        from concurrent.futures import ThreadPoolExecutor, as_completed

        lista_path = Path(params["lista"])
        column = params.get("columna", "")

        _send_progress("Buscando celdas con correos en el archivo…", 5)
        correos = extraer_correos_de_archivo(lista_path, column)

        if not correos:
            _send_progress("Completado (sin correos encontrados)", 100)
            _send_result(req_id, {
                "total_entrada": 0,
                "validos": 0,
                "invalidos": 0,
                "duplicados": 0,
                "sin_mx": 0,
                "purgados": 0,
                "lista_validos": [],
                "lista_invalidos": [],
            })
            return

        _send_progress(f"Analizando {len(correos)} correos detectados…", 15)
        preparados = prepare_lines(correos)

        # En prepare_lines, los correos válidos tienen estado == "" (no son INVALIDO) y normalizado válido
        sintacticos_validos = [r for r in preparados if r.get("estado") != "INVALIDO" and bool(r.get("normalizado"))]
        invalidos_sintaxis = [r for r in preparados if r.get("estado") == "INVALIDO"]

        # Duplicados
        duplicados = [r for r in sintacticos_validos if r.get("duplicado_de_linea") is not None]
        unicos_validos = [r for r in sintacticos_validos if r.get("duplicado_de_linea") is None]

        lista_invalidos_salida = [
            {"correo": r.get("original", ""), "razon": r.get("motivo") or "Formato inválido"}
            for r in invalidos_sintaxis
        ]

        # Verificación DNS concurrente
        dominios_sin_mx = set()
        dns_fallos_motivo = {}
        if params.get("verificar_dns", True):
            _send_progress("Verificando dominios DNS (MX)…", 35)
            checker = DNSChecker()
            dominios = sorted(list(set(r["dominio"] for r in unicos_validos if r.get("dominio"))))
            total_doms = len(dominios)

            completed_count = 0
            with ThreadPoolExecutor(max_workers=16) as executor:
                future_to_dom = {executor.submit(checker.check, dom): dom for dom in dominios}
                for f in as_completed(future_to_dom):
                    dom = future_to_dom[f]
                    completed_count += 1
                    if completed_count % 10 == 0 or completed_count == total_doms:
                        pct = 35 + int((completed_count / max(total_doms, 1)) * 55)
                        _send_progress(f"DNS: {completed_count}/{total_doms} dominios revisados…", pct)
                    try:
                        res = f.result()
                        if res.get("estado") == "INVALIDO":
                            dominios_sin_mx.add(dom)
                            dns_fallos_motivo[dom] = res.get("motivo") or res.get("codigo") or "Dominio no existe o sin registros MX"
                    except Exception:
                        dominios_sin_mx.add(dom)
                        dns_fallos_motivo[dom] = "Error consultando registros DNS"

        # Correos con dominio sin MX
        sin_mx_unicos = [r for r in unicos_validos if r.get("dominio") in dominios_sin_mx]
        for r in sin_mx_unicos:
            lista_invalidos_salida.append({
                "correo": r.get("normalizado", ""),
                "razon": dns_fallos_motivo.get(r.get("dominio"), "Dominio sin registros de correo (MX)")
            })

        # Válidos finales
        validos_final = [r for r in unicos_validos if r.get("dominio") not in dominios_sin_mx]
        purgados_total = len(invalidos_sintaxis) + len(duplicados) + len(sin_mx_unicos)

        _send_progress("Completado", 100)
        _send_result(req_id, {
            "total_entrada": len(preparados),
            "validos": len(validos_final),
            "invalidos": len(invalidos_sintaxis),
            "duplicados": len(duplicados),
            "sin_mx": len(sin_mx_unicos),
            "purgados": purgados_total,
            "lista_validos": [r["normalizado"] for r in validos_final],
            "lista_invalidos": lista_invalidos_salida,
        })
    except Exception as e:
        _send_error(req_id, traceback.format_exc())


def cmd_simular(params, req_id):
    """Simula el envío de una campaña. Solo valida, no envía nada real."""
    try:
        import campana as c
        from pathlib import Path

        cfg_path = Path(params["config"])
        lista_path = Path(params["lista"])
        base = cfg_path.parent

        _send_progress("Cargando configuración…", 10)
        cfg = c.load_config(cfg_path)

        _send_progress("Cargando contenido del mensaje…", 25)
        content, fingerprint = c.load_content(cfg, base)

        _send_progress("Cargando lista de contactos…", 40)
        rows = c.load_contacts(lista_path)
        validos = [r for r in rows if r.get("estado") != "INVALIDO" and bool(r.get("normalizado")) and not r.get("duplicado_de_linea")]

        _send_progress("Simulación completada", 100)
        _send_result(req_id, {
            "modo": "simulacion",
            "fingerprint": fingerprint,
            "contactos_validos": len(validos),
            "asunto": cfg["mensaje"]["asunto"],
            "remitente": cfg["remitente"]["correo"],
            "nombre_remitente": cfg["remitente"]["nombre"],
            "adjuntos": len(cfg["mensaje"].get("adjuntos", [])),
            "preview_texto": content["texto"][:300] + ("…" if len(content["texto"]) > 300 else ""),
        })
    except Exception as e:
        _send_error(req_id, traceback.format_exc())


def cmd_enviar(params, req_id):
    """Envío real de campaña. Requiere que autorizacion.envio_aprobado=true en el JSON."""
    try:
        import campana as c
        from pathlib import Path

        cfg_path = Path(params["config"])
        lista_path = Path(params["lista"])
        base = cfg_path.parent

        _send_progress("Cargando configuración y lista…", 5)
        cfg = c.load_config(cfg_path)

        if not cfg["autorizacion"]["envio_aprobado"]:
            _send_error(req_id, "El campo 'envio_aprobado' en la configuración debe ser true para enviar.")
            return

        content, fingerprint = c.load_content(cfg, base)
        rows = c.load_contacts(lista_path)
        validos = [r for r in rows if r.get("estado") != "INVALIDO" and bool(r.get("normalizado")) and not r.get("duplicado_de_linea")]

        # Obtener contraseña SMTP desde variable de entorno
        smtp_cfg = cfg["smtp"]
        secret = os.environ.get(smtp_cfg["secreto_env"], "")

        enviados = 0
        errores = 0
        total = min(len(validos), cfg["limites"]["max_por_ejecucion"])

        _send_progress(f"Conectando SMTP ({smtp_cfg['host']})…", 10)

        import smtplib, ssl
        import time

        ctx = ssl.create_default_context()
        if smtp_cfg["seguridad"] == "ssl":
            conn = smtplib.SMTP_SSL(smtp_cfg["host"], smtp_cfg["puerto"], context=ctx)
        else:
            conn = smtplib.SMTP(smtp_cfg["host"], smtp_cfg["puerto"])
            conn.starttls(context=ctx)

        if smtp_cfg["autenticacion"] == "password":
            conn.login(smtp_cfg["usuario"], secret)

        _send_progress("Conexión establecida, iniciando envíos…", 15)

        for i, row in enumerate(validos[:total]):
            pct = 15 + int((i / max(total, 1)) * 80)
            _send_progress(f"Enviando {i+1}/{total}: {row['normalizado']}", pct)
            try:
                msg = c.build_message(cfg, content, row, cfg["campana_id"])
                conn.send_message(msg)
                enviados += 1
                _send_event("correo_enviado", {"correo": row["normalizado"], "numero": i + 1})
            except Exception as ex:
                errores += 1
                _send_event("correo_error", {"correo": row["normalizado"], "error": str(ex)})
                if errores >= cfg["limites"]["max_errores_consecutivos"]:
                    _send_error(req_id, f"Demasiados errores consecutivos ({errores}). Envío detenido.")
                    conn.quit()
                    return

            intervalo = cfg["limites"]["intervalo_segundos"]
            if intervalo > 0 and i < total - 1:
                time.sleep(intervalo)

        conn.quit()
        _send_progress("Envío completado", 100)
        _send_result(req_id, {
            "enviados": enviados,
            "errores": errores,
            "total_intentados": total,
        })
    except Exception as e:
        _send_error(req_id, traceback.format_exc())


def cmd_cargar_config(params, req_id):
    """Lee y valida un archivo campana.json sin ejecutar nada."""
    try:
        import campana as c
        cfg = c.load_config(Path(params["config"]))
        _send_result(req_id, {
            "campana_id": cfg["campana_id"],
            "remitente": cfg["remitente"]["correo"],
            "nombre_remitente": cfg["remitente"]["nombre"],
            "asunto": cfg["mensaje"]["asunto"],
            "smtp_host": cfg["smtp"]["host"],
            "smtp_seguridad": cfg["smtp"]["seguridad"],
            "max_envios": cfg["limites"]["max_por_ejecucion"],
            "autorizacion": cfg["autorizacion"],
        })
    except Exception as e:
        _send_error(req_id, str(e))


def cmd_exportar_purgados(params, req_id):
    """Exporta la lista de correos válidos a un CSV limpio."""
    try:
        import csv
        correos = params["lista_validos"]
        destino = Path(params["destino"])
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["correo"])
            for correo in correos:
                w.writerow([correo])
        _send_result(req_id, {"exportado": str(destino), "total": len(correos)})
    except Exception as e:
        _send_error(req_id, str(e))


def cmd_probar_smtp(params, req_id):
    """Prueba la conexión y autenticación con el servidor SMTP."""
    try:
        import smtplib, ssl
        host = params["host"].strip()
        puerto = int(params.get("puerto", 465))
        seguridad = params.get("seguridad", "ssl").lower()
        usuario = params.get("usuario", "").strip()
        password = params.get("password", "")

        _send_progress(f"Conectando a {host}:{puerto}…", 30)
        ctx = ssl.create_default_context()
        if seguridad == "ssl":
            conn = smtplib.SMTP_SSL(host, puerto, context=ctx, timeout=12)
        else:
            conn = smtplib.SMTP(host, puerto, timeout=12)
            conn.ehlo()
            conn.starttls(context=ctx)
            conn.ehlo()

        if usuario and password:
            _send_progress("Autenticando credenciales…", 60)
            conn.login(usuario, password)

        conn.quit()
        _send_progress("Conexión SMTP verificada", 100)
        _send_result(req_id, {"ok": True, "mensaje": f"Conexión exitosa con {host}:{puerto}."})
    except Exception as e:
        _send_error(req_id, f"Error conectando al servidor SMTP: {e}")


def cmd_enviar_prueba(params, req_id):
    """Envía un único correo de prueba."""
    try:
        import smtplib, ssl, mimetypes
        from email.message import EmailMessage
        from email.headerregistry import Address
        from email.utils import format_datetime
        from datetime import datetime, timezone
        from string import Template

        smtp_cfg = params["smtp"]
        msg_cfg = params["mensaje"]
        destinatario = params["correo_prueba"].strip()

        if not destinatario or "@" not in destinatario:
            _send_error(req_id, "Correo de prueba inválido.")
            return

        host = smtp_cfg["host"].strip()
        puerto = int(smtp_cfg.get("puerto", 465))
        seguridad = smtp_cfg.get("seguridad", "ssl").lower()
        usuario = smtp_cfg.get("usuario", "").strip()
        password = smtp_cfg.get("password", "")
        remitente_correo = smtp_cfg.get("remitente_correo", usuario).strip()
        remitente_nombre = smtp_cfg.get("remitente_nombre", "").strip() or "Actuariosa"
        responder_a = smtp_cfg.get("responder_a", "").strip()

        _send_progress("Conectando para enviar prueba…", 20)
        ctx = ssl.create_default_context()
        if seguridad == "ssl":
            conn = smtplib.SMTP_SSL(host, puerto, context=ctx, timeout=15)
        else:
            conn = smtplib.SMTP(host, puerto, timeout=15)
            conn.ehlo()
            conn.starttls(context=ctx)
            conn.ehlo()

        if usuario and password:
            conn.login(usuario, password)

        variables = {"nombre": "Prueba", "empresa": "Empresa Ejemplo", "correo": destinatario}
        asunto = Template(msg_cfg.get("asunto", "Correo de prueba")).safe_substitute(variables)
        texto = Template(msg_cfg.get("texto", "")).safe_substitute(variables)
        html_body = msg_cfg.get("html", "")
        if html_body:
            html_body = Template(html_body).safe_substitute(variables)

        msg = EmailMessage()
        msg["From"] = Address(display_name=remitente_nombre, addr_spec=remitente_correo)
        msg["To"] = Address(addr_spec=destinatario)
        if responder_a:
            msg["Reply-To"] = Address(addr_spec=responder_a)
        msg["Subject"] = f"[PRUEBA] {asunto}"
        msg["Date"] = format_datetime(datetime.now(timezone.utc))
        msg.set_content(texto)
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        # Adjuntos
        for adj_path in msg_cfg.get("adjuntos", []):
            p = Path(adj_path)
            if p.exists():
                mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
                maintype, subtype = mime.split("/", 1)
                msg.add_attachment(p.read_bytes(), maintype=maintype, subtype=subtype, filename=p.name)

        _send_progress(f"Enviando correo de prueba a {destinatario}…", 60)
        conn.send_message(msg)
        conn.quit()
        _send_progress("Correo de prueba entregado", 100)
        _send_result(req_id, {"ok": True, "mensaje": f"Correo de prueba enviado con éxito a {destinatario}"})
    except Exception as e:
        _send_error(req_id, f"Error enviando correo de prueba: {e}")


def cmd_enviar_directo(params, req_id):
    """Envío masivo directo a empresas con control de intervalo y progreso."""
    global _cancel_event
    _cancel_event.clear()

    try:
        import smtplib, ssl, mimetypes, time
        from email.message import EmailMessage
        from email.headerregistry import Address
        from email.utils import format_datetime
        from datetime import datetime, timezone
        from string import Template

        smtp_cfg = params["smtp"]
        msg_cfg = params["mensaje"]
        destinatarios_raw = params.get("destinatarios", [])
        limites = params.get("limites", {})
        intervalo = max(0.5, float(limites.get("intervalo_segundos", 3)))
        max_envios = int(limites.get("max_envios", 0))

        destinatarios = []
        for d in destinatarios_raw:
            if isinstance(d, str):
                d_clean = d.strip()
                if "@" in d_clean:
                    destinatarios.append({"correo": d_clean, "nombre": "", "empresa": ""})
            elif isinstance(d, dict) and d.get("correo"):
                destinatarios.append({
                    "correo": d["correo"].strip(),
                    "nombre": d.get("nombre", "").strip(),
                    "empresa": d.get("empresa", "").strip(),
                })

        if not destinatarios:
            _send_error(req_id, "No se proporcionaron destinatarios válidos.")
            return

        if max_envios > 0:
            destinatarios = destinatarios[:max_envios]

        total = len(destinatarios)
        host = smtp_cfg["host"].strip()
        puerto = int(smtp_cfg.get("puerto", 465))
        seguridad = smtp_cfg.get("seguridad", "ssl").lower()
        usuario = smtp_cfg.get("usuario", "").strip()
        password = smtp_cfg.get("password", "")
        remitente_correo = smtp_cfg.get("remitente_correo", usuario).strip()
        remitente_nombre = smtp_cfg.get("remitente_nombre", "").strip() or "Actuariosa"
        responder_a = smtp_cfg.get("responder_a", "").strip()

        _send_progress(f"Conectando a {host}:{puerto}…", 5)

        ctx = ssl.create_default_context()
        if seguridad == "ssl":
            conn = smtplib.SMTP_SSL(host, puerto, context=ctx, timeout=20)
        else:
            conn = smtplib.SMTP(host, puerto, timeout=20)
            conn.ehlo()
            conn.starttls(context=ctx)
            conn.ehlo()

        if usuario and password:
            conn.login(usuario, password)

        _send_progress(f"Conectado. Iniciando envío a {total} empresas…", 10)

        # Pre-cargar adjuntos en memoria
        adjuntos_memoria = []
        for adj_path in msg_cfg.get("adjuntos", []):
            p = Path(adj_path)
            if p.exists():
                mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
                maintype, subtype = mime.split("/", 1)
                adjuntos_memoria.append((p.name, maintype, subtype, p.read_bytes()))

        enviados = 0
        errores = 0
        detalles_errores = []

        asunto_tmpl = Template(msg_cfg.get("asunto", ""))
        texto_tmpl = Template(msg_cfg.get("texto", ""))
        html_raw = msg_cfg.get("html", "")
        html_tmpl = Template(html_raw) if html_raw else None

        for i, dest in enumerate(destinatarios):
            if _cancel_event.is_set():
                _send_progress("Envío cancelado por el usuario", int((i / total) * 100))
                _send_event("envio_cancelado", {"enviados": enviados, "errores": errores, "total": total})
                break

            to_email = dest["correo"]
            variables = {
                "nombre": dest.get("nombre") or to_email.split("@")[0],
                "empresa": dest.get("empresa") or "Estimados señores",
                "correo": to_email,
            }

            pct = 10 + int((i / total) * 85)
            _send_progress(f"Enviando {i+1}/{total}: {to_email}", pct)

            try:
                msg = EmailMessage()
                msg["From"] = Address(display_name=remitente_nombre, addr_spec=remitente_correo)
                msg["To"] = Address(addr_spec=to_email)
                if responder_a:
                    msg["Reply-To"] = Address(addr_spec=responder_a)
                msg["Subject"] = asunto_tmpl.safe_substitute(variables)
                msg["Date"] = format_datetime(datetime.now(timezone.utc))
                msg.set_content(texto_tmpl.safe_substitute(variables))
                if html_tmpl:
                    msg.add_alternative(html_tmpl.safe_substitute(variables), subtype="html")

                for filename, maintype, subtype, data in adjuntos_memoria:
                    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

                conn.send_message(msg)
                enviados += 1
                _send_event("correo_enviado", {
                    "correo": to_email,
                    "numero": i + 1,
                    "total": total,
                    "enviados": enviados,
                    "errores": errores,
                })
            except Exception as ex:
                errores += 1
                detalles_errores.append({"correo": to_email, "error": str(ex)})
                _send_event("correo_error", {
                    "correo": to_email,
                    "numero": i + 1,
                    "total": total,
                    "error": str(ex),
                    "enviados": enviados,
                    "errores": errores,
                })

            if i < total - 1 and intervalo > 0:
                if _cancel_event.wait(timeout=intervalo):
                    break

        try:
            conn.quit()
        except Exception:
            pass

        _send_progress("Envío completado", 100)
        _send_result(req_id, {
            "enviados": enviados,
            "errores": errores,
            "total_intentados": enviados + errores,
            "total_solicitados": total,
            "detalles_errores": detalles_errores,
        })
    except Exception as e:
        _send_error(req_id, traceback.format_exc())


def cmd_cancelar_envio(params, req_id):
    """Cancela el envío masivo en curso."""
    global _cancel_event
    _cancel_event.set()
    _send_result(req_id, {"cancelado": True})


def cmd_cargar_contactos_archivo(params, req_id):
    """Extrae destinatarios desde un archivo Excel/CSV/TXT para el apartado de envío directo."""
    try:
        raw_path = params.get("ruta") or params.get("path") or params.get("archivo")
        if not raw_path:
            raise ValueError("No se especificó la ruta del archivo")
        path = Path(raw_path)
        correos = extraer_correos_de_archivo(path, params.get("columna", ""))
        vistos = set()
        unicos = []
        for c in correos:
            clow = c.strip().lower()
            if clow and clow not in vistos:
                vistos.add(clow)
                unicos.append(c.strip())
        _send_result(req_id, {
            "archivo": path.name,
            "total": len(unicos),
            "correos": unicos,
            "muestra": unicos[:20],
        })
    except Exception as e:
        _send_error(req_id, f"Error leyendo archivo de contactos: {e}")


def cmd_exportar_bitacora(params, req_id):
    """Exporta la bitácora de envíos a un archivo CSV."""
    try:
        import csv
        registros = params.get("registros", [])
        destino = Path(params["destino"])
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Numero", "FechaHora", "Correo", "Empresa", "Estado", "Detalle"])
            for r in registros:
                w.writerow([
                    r.get("numero", ""),
                    r.get("hora", ""),
                    r.get("correo", ""),
                    r.get("empresa", ""),
                    r.get("estado", ""),
                    r.get("detalle", ""),
                ])
        _send_result(req_id, {"exportado": str(destino), "total": len(registros)})
    except Exception as e:
        _send_error(req_id, f"Error exportando bitácora: {e}")


def cmd_sincronizar_panel(params, req_id):
    """Invoca la sincronización de métricas hacia el panel web."""
    try:
        from sync_telemetria import recolectar_metricas_locales, enviar_telemetria, DEFAULT_PANEL_URL, DEFAULT_API_KEY
        url = params.get("url") or DEFAULT_PANEL_URL
        api_key = params.get("api_key") or DEFAULT_API_KEY
        payload = recolectar_metricas_locales()
        if "envio_reciente" in params and isinstance(params["envio_reciente"], dict):
            payload["campanas"].append(params["envio_reciente"])

        res = enviar_telemetria(url, api_key, payload)
        if res["ok"]:
            _send_result(req_id, {"sincronizado": True, "resumen": payload["resumen_general"]})
        else:
            _send_error(req_id, f"No se pudo sincronizar con el panel: {res['error']}")
    except Exception as e:
        _send_error(req_id, f"Error en sincronización: {e}")


def cmd_verificar_actualizacion(params, req_id):
    """Consulta la API de actualizaciones para verificar si la versión está desactualizada."""
    try:
        import urllib.request
        import urllib.parse
        url = params.get("url") or "https://panel-web-six-plum.vercel.app/api/updates"
        ver_file = BASE_DIR / "version.json"
        current_version = "2.0.0"
        if ver_file.exists():
            try:
                data = json.loads(ver_file.read_text(encoding="utf-8"))
                current_version = data.get("version", "2.0.0")
            except Exception:
                pass

        sep = "&" if "?" in url else "?"
        query_url = f"{url}{sep}current_version={urllib.parse.quote(current_version)}"
        req = urllib.request.Request(query_url, headers={"User-Agent": "MxCorreo-Python-Server/2.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _send_result(req_id, {
                "outdated": data.get("outdated", False),
                "current_version": current_version,
                "latest_version": data.get("latest_version", current_version),
                "mandatory": data.get("mandatory", False),
                "release": data.get("release", {}),
            })
    except Exception as e:
        _send_error(req_id, f"Error comprobando actualizaciones: {e}")


def cmd_aplicar_actualizacion(params, req_id):
    """Aplica la actualización actualizando el archivo local version.json."""
    try:
        nueva_version = params.get("target_version", "2.1.0")
        ver_file = BASE_DIR / "version.json"
        data = {}
        if ver_file.exists():
            try:
                data = json.loads(ver_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        data["version"] = nueva_version
        data["last_updated"] = datetime.now().isoformat()
        ver_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        _send_result(req_id, {"ok": True, "version": nueva_version})
    except Exception as e:
        _send_error(req_id, f"Error aplicando actualización: {e}")


HANDLERS = {
    "ping": cmd_ping,
    "verificar": cmd_verificar,
    "simular": cmd_simular,
    "enviar": cmd_enviar,
    "cargar_config": cmd_cargar_config,
    "exportar_purgados": cmd_exportar_purgados,
    # Nuevos handlers para el apartado de envío directo y telemetría:
    "probar_smtp": cmd_probar_smtp,
    "enviar_prueba": cmd_enviar_prueba,
    "enviar_directo": cmd_enviar_directo,
    "cancelar_envio": cmd_cancelar_envio,
    "cargar_contactos_archivo": cmd_cargar_contactos_archivo,
    "exportar_bitacora": cmd_exportar_bitacora,
    "sincronizar_panel": cmd_sincronizar_panel,
    "verificar_actualizacion": cmd_verificar_actualizacion,
    "aplicar_actualizacion": cmd_aplicar_actualizacion,
}


# ──────────────────────────────────────────────
# Bucle principal stdin/stdout
# ──────────────────────────────────────────────

def main():
    _send_event("ready", {"version": "2.0.0"})

    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            req = json.loads(raw_line)
        except json.JSONDecodeError as e:
            _send({"type": "error", "error": f"JSON inválido: {e}"})
            continue

        cmd = req.get("cmd")
        req_id = req.get("id", 0)
        params = req.get("params", {})

        handler = HANDLERS.get(cmd)
        if handler is None:
            _send_error(req_id, f"Comando desconocido: '{cmd}'")
            continue

        # Si es cancelar envío, ejecutar inmediatamente para interrumpir de inmediato
        if cmd == "cancelar_envio":
            handler(params, req_id)
            continue

        # Ejecutar en hilo para no bloquear stdin y permitir comandos concurrentes como cancelar
        t = threading.Thread(target=handler, args=(params, req_id), daemon=True)
        t.start()


if __name__ == "__main__":
    main()
