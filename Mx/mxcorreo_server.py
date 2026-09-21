"""
mxcorreo_server.py — Backend JSON-RPC por stdin/stdout para la interfaz Electron.
Envuelve campana.py y verificar_correos.py con comunicación en tiempo real.
"""
from __future__ import annotations

import json
import sys
import os
import threading
import traceback
from pathlib import Path

# Asegurar que el directorio del script esté en el path
_here = Path(__file__).parent
sys.path.insert(0, str(_here))


def _send(obj: dict):
    """Emite un objeto JSON al renderer (stdout)."""
    line = json.dumps(obj, ensure_ascii=False)
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


def cmd_verificar(params, req_id):
    """Verifica y depura una lista de correos. Retorna estadísticas."""
    try:
        from verificar_correos import prepare_lines, verify, DNSChecker
        import csv

        lista_path = Path(params["lista"])
        column = params.get("columna", "correo")

        _send_progress("Leyendo lista de correos…", 5)

        # Cargar correos
        if lista_path.suffix.lower() == ".csv":
            with lista_path.open(encoding="utf-8-sig", newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    delim = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
                except csv.Error:
                    delim = ","
                reader = csv.DictReader(f, delimiter=delim)
                rows = list(reader)
            correos = [r.get(column, "") for r in rows]
        elif lista_path.suffix.lower() == ".txt":
            correos = lista_path.read_text(encoding="utf-8-sig").splitlines()
        elif lista_path.suffix.lower() == ".mxlista":
            from importar_contactos import load_import
            items = load_import(lista_path)
            correos = [i["normalizado"] for i in items if i.get("normalizado")]
        else:
            _send_error(req_id, f"Formato no soportado: {lista_path.suffix}")
            return

        _send_progress(f"Analizando {len(correos)} correos…", 15)
        preparados = prepare_lines(correos)

        # Estadísticas básicas sin DNS
        validos = [r for r in preparados if r["estado"] == "valido"]
        invalidos = [r for r in preparados if r["estado"] != "valido"]
        duplicados = [r for r in preparados if r.get("duplicado_de_linea")]

        _send_progress("Verificando dominios DNS…", 40)

        # Verificación DNS opcional
        dns_resultados = []
        if params.get("verificar_dns", True):
            checker = DNSChecker()
            dominios = list(set(r["normalizado"].split("@")[1] for r in validos if "@" in r.get("normalizado", "")))
            total = len(dominios)
            for i, dom in enumerate(dominios):
                pct = 40 + int((i / max(total, 1)) * 45)
                _send_progress(f"DNS {i+1}/{total}: {dom}", pct)
                try:
                    ok, _ = checker.check(dom)
                    dns_resultados.append({"dominio": dom, "mx_ok": ok})
                except Exception:
                    dns_resultados.append({"dominio": dom, "mx_ok": False})

        dominios_sin_mx = {r["dominio"] for r in dns_resultados if not r["mx_ok"]}
        validos_final = [r for r in validos if r["normalizado"].split("@")[-1] not in dominios_sin_mx]
        purgados = len(preparados) - len(validos_final)

        _send_progress("Completado", 100)
        _send_result(req_id, {
            "total_entrada": len(preparados),
            "validos": len(validos_final),
            "invalidos": len(invalidos),
            "duplicados": len(duplicados),
            "sin_mx": len([r for r in validos if r["normalizado"].split("@")[-1] in dominios_sin_mx]),
            "purgados": purgados,
            "lista_validos": [r["normalizado"] for r in validos_final],
            "lista_invalidos": [{"correo": r.get("original", ""), "razon": r.get("estado", "")} for r in invalidos],
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
        validos = [r for r in rows if r["estado"] == "valido" and not r.get("duplicado_de_linea")]

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
        validos = [r for r in rows if r["estado"] == "valido" and not r.get("duplicado_de_linea")]

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


HANDLERS = {
    "ping": cmd_ping,
    "verificar": cmd_verificar,
    "simular": cmd_simular,
    "enviar": cmd_enviar,
    "cargar_config": cmd_cargar_config,
    "exportar_purgados": cmd_exportar_purgados,
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

        # Ejecutar en hilo para no bloquear el stdin loop
        t = threading.Thread(target=handler, args=(params, req_id), daemon=True)
        t.start()
        t.join()  # Serializado por ahora para simplicidad


if __name__ == "__main__":
    main()
