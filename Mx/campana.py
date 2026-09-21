"""Revisión y envío individual de correo. Por defecto SIMULA; nunca envía sin confirmación."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from email import policy
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import format_datetime
import getpass
import hashlib
import html
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import smtplib
import sqlite3
import ssl
from string import Template
import tempfile
import time
import uuid

import dns.exception
from email_validator import validate_email

from verificar_correos import DNSChecker, prepare_lines, save_report, verify


def now():
    return datetime.now(timezone.utc).isoformat()


def address(value):
    parsed = validate_email(value.strip(), check_deliverability=False, allow_quoted_local=True)
    return parsed.local_part + "@" + parsed.ascii_domain


def header(value):
    if not isinstance(value, str) or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("Las cabeceras no pueden contener saltos de línea o caracteres de control.")
    return value


def load_contacts(path, column="correo", delimiter=None):
    """Lectura de datos únicamente; no modifica ni exporta hojas de cálculo."""
    if path.suffix.lower() == ".mxlista":
        from importar_contactos import load_import
        return load_import(path)
    if path.suffix.lower() in {".xlsx", ".xls", ".xlsm"}:
        from python_calamine import CalamineWorkbook
        wb = CalamineWorkbook.from_path(path)
        all_rows = []
        for sheet_name in wb.sheet_names:
            sheet = wb.get_sheet_by_name(sheet_name)
            if sheet.end is None:
                continue
            table = sheet.to_python(skip_empty_area=False)
            if not table:
                continue
            first_row = [str(c).strip().lower() for c in table[0]]
            email_col = 0
            for idx, h in enumerate(first_row):
                if h == column.lower() or h in {"correo", "email", "mail", "correos"}:
                    email_col = idx
                    break
            values = [str(r[email_col]).strip() for r in table[1:] if email_col < len(r) and r[email_col]]
            rows = prepare_lines(values)
            all_rows.extend(rows)
        return all_rows
    if path.suffix.lower() == ".txt":
        return prepare_lines(path.read_text(encoding="utf-8-sig").splitlines())
    if path.suffix.lower() != ".csv":
        raise ValueError("Entrada admitida: Excel (.xlsx, .xls), CSV UTF-8, TXT o .mxlista.")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(8192)
        stream.seek(0)
        if delimiter is None:
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
            except csv.Error:
                delimiter = ","
        reader = csv.DictReader(stream, delimiter=delimiter)
        fields = reader.fieldnames
        if not fields or len(fields) != len(set(fields)):
            raise ValueError("El CSV debe tener cabeceras únicas.")
        if column not in fields:
            candidates = [f for f in fields if f.lower() in {"correo", "email", "e-mail", "mail", "correos"}]
            if candidates:
                column = candidates[0]
            else:
                raise ValueError(f"El CSV debe tener cabeceras únicas y una columna '{column}'.")
        records = list(reader)
    values = []
    for record in records:
        if None in record or any(v is None for v in record.values()):
            raise ValueError("CSV con columnas desalineadas. Revisa separador y comillas.")
        values.append(record[column])
    rows = prepare_lines(values)
    for row in rows:
        index = row["linea"] - 1
        row["nombre"] = records[index].get("nombre", "")
        row["empresa"] = records[index].get("empresa", "")
        row["linea"] += 1  # Número de registro, contando la cabecera.
        if row["duplicado_de_linea"] is not None:
            row["duplicado_de_linea"] += 1
    return rows


def load_exclusions(path):
    if path is None:
        return set()
    # Fallar cerrado: una baja mal escrita no se ignora silenciosamente.
    result = set()
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if line.strip():
            try:
                result.add(address(line).casefold())
            except ValueError as exc:
                raise ValueError(f"Exclusión inválida en línea {number}; corrige el archivo.") from exc
    return result


def load_config(path):
    cfg = json.loads(path.read_text(encoding="utf-8-sig"))
    expected = {"campana_id", "es_ejemplo", "remitente", "mensaje", "smtp", "limites", "autorizacion"}
    if not isinstance(cfg, dict) or set(cfg) != expected:
        raise ValueError("Configuración incompleta o con claves desconocidas; usa campana.ejemplo.json.")
    if not isinstance(cfg["campana_id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", cfg["campana_id"]):
        raise ValueError("campana_id: usa 1-80 letras ASCII, números, guiones o guiones bajos.")
    if type(cfg["es_ejemplo"]) is not bool:
        raise ValueError("es_ejemplo debe ser true o false.")
    sections = {
        "remitente": {"correo", "nombre", "responder_a"},
        "mensaje": {"asunto", "archivo_texto", "archivo_html", "adjuntos"},
        "smtp": {"host", "puerto", "seguridad", "autenticacion", "usuario", "secreto_env"},
        "limites": {"max_por_ejecucion", "intervalo_segundos", "max_errores_consecutivos", "max_mensaje_mb"},
        "autorizacion": {"remitente_autorizado", "envio_aprobado", "lista_revisada", "exclusiones_revisadas", "limites_confirmados"},
    }
    for section, keys in sections.items():
        optional = {'baja_correo'} if section == 'mensaje' else {'max_24h'} if section == 'limites' else set()
        if not isinstance(cfg[section], dict) or not keys <= set(cfg[section]) or set(cfg[section]) - keys - optional:
            raise ValueError(f"Claves incorrectas en '{section}'. No guardes secretos en el JSON.")
    sender = cfg["remitente"]
    sender["correo"] = address(sender["correo"])
    header(sender["nombre"])
    if sender["responder_a"]:
        sender["responder_a"] = address(sender["responder_a"])
    header(cfg["mensaje"]["asunto"])
    if cfg['mensaje'].get('baja_correo'):
        cfg['mensaje']['baja_correo'] = address(cfg['mensaje']['baja_correo'])
    smtp = cfg["smtp"]
    for key in ("host", "seguridad", "autenticacion", "usuario", "secreto_env"):
        header(smtp[key])
    if smtp["seguridad"] not in {"starttls", "ssl"}:
        raise ValueError("Solo se admite SMTP cifrado: starttls o ssl.")
    if smtp["autenticacion"] not in {"password", "oauth2", "none"}:
        raise ValueError("autenticacion debe ser password, oauth2 o none (relay autorizado).")
    if type(smtp["puerto"]) is not int or not 1 <= smtp["puerto"] <= 65535:
        raise ValueError("Puerto SMTP inválido.")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", smtp["secreto_env"]):
        raise ValueError("secreto_env debe ser el nombre de una variable de entorno, no su valor.")
    for key, low, high in (("max_por_ejecucion", 1, 100000), ("max_errores_consecutivos", 1, 100)):
        value = cfg["limites"][key]
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{key} debe estar entre {low} y {high}.")
    for key, low, high in (("intervalo_segundos", 0.1, 3600), ("max_mensaje_mb", 0.1, 100)):
        value = cfg["limites"][key]
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{key} debe estar entre {low} y {high}.")
    cap = cfg['limites'].get('max_24h', 400)
    if type(cap) is not int or not 1 <= cap <= 2000:
        raise ValueError('max_24h debe estar entre 1 y 2000; confirma el límite real de tu cuenta.')
    if any(type(flag) is not bool for flag in cfg["autorizacion"].values()):
        raise ValueError("Los campos de autorización deben ser true o false.")
    return cfg


def load_content(cfg, base):
    message = cfg["mensaje"]
    text = (base / message["archivo_texto"]).read_text(encoding="utf-8-sig")
    rich = (base / message["archivo_html"]).read_text(encoding="utf-8-sig") if message["archivo_html"] else ""
    if not text.strip() or not message["asunto"].strip():
        raise ValueError("Asunto y mensaje de texto no pueden estar vacíos.")
    if not isinstance(message["adjuntos"], list) or any(not isinstance(p, str) for p in message["adjuntos"]):
        raise ValueError("adjuntos debe ser una lista de rutas.")
    attachments = []
    max_bytes = int(cfg["limites"]["max_mensaje_mb"] * 1024 * 1024)
    total = 0
    for item in message["adjuntos"]:
        path = base / item
        total += path.stat().st_size
        if total > max_bytes:
            raise ValueError("Los adjuntos superan max_mensaje_mb.")
        data = path.read_bytes()
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        attachments.append((path.name, mime, data))
    baja = cfg['mensaje'].get('baja_correo', '')
    if baja:
        text += f'\n\nPara no recibir más ofertas, escribe a {baja} con el asunto BAJA.\n'
        if rich:
            rich += f'<p>Para no recibir más ofertas, escribe a <a href="mailto:{html.escape(baja, quote=True)}?subject=BAJA">{html.escape(baja)}</a> con el asunto BAJA.</p>'
    content = {"texto": text, "html": rich, "adjuntos": attachments}
    # Congela contenido y adjuntos en memoria antes de la vista previa y confirmación.
    fingerprint = hashlib.sha256(json.dumps({
        "remitente": cfg["remitente"], "asunto": message["asunto"], "texto": text, "html": rich,
        "adjuntos": [(n, m, hashlib.sha256(d).hexdigest()) for n, m, d in attachments],
    }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return content, fingerprint


def build_message(cfg, content, row, campaign_id):
    recipient = address(row["normalizado"])
    variables = {"nombre": row.get("nombre", ""), "empresa": row.get("empresa", ""), "correo": recipient}
    subject = header(Template(cfg["mensaje"]["asunto"]).substitute(variables))
    text = Template(content["texto"]).substitute(variables)
    rich = Template(content["html"]).substitute({k: html.escape(v, quote=True) for k, v in variables.items()})
    sender = cfg["remitente"]
    msg = EmailMessage(policy=policy.SMTP)
    msg["From"] = Address(display_name=sender["nombre"], addr_spec=sender["correo"])
    msg["To"] = Address(addr_spec=recipient)
    if sender["responder_a"]:
        msg["Reply-To"] = Address(addr_spec=sender["responder_a"])
    msg["Subject"] = subject
    if cfg['mensaje'].get('baja_correo'):
        from urllib.parse import quote
        msg['List-Unsubscribe'] = '<mailto:' + quote(cfg['mensaje']['baja_correo'], safe='@') + '?subject=BAJA>'
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    token = hashlib.sha256((campaign_id + "\0" + recipient).encode()).hexdigest()
    msg["Message-ID"] = f"<{token}@{sender['correo'].rsplit('@', 1)[1]}>"
    msg.set_content(text)
    if rich:
        msg.add_alternative(rich, subtype="html")
    for name, mime, data in content["adjuntos"]:
        main, sub = mime.split("/", 1)
        msg.add_attachment(data, maintype=main, subtype=sub, filename=name)
    if len(msg.as_bytes()) > cfg["limites"]["max_mensaje_mb"] * 1024 * 1024:
        raise ValueError("El mensaje MIME completo supera max_mensaje_mb (incluye codificación y adjuntos).")
    return msg


class QuotaReached(ValueError):
    pass


class Ledger:
    """Registro local durable. Reserva antes del envío; evita duplicados incluso entre procesos."""
    def __init__(self, path, campaign_id, fingerprint):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10)
        self.campaign_id = campaign_id
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS campaigns (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS deliveries (
                campaign TEXT, email TEXT, status TEXT NOT NULL, code INTEGER,
                updated TEXT NOT NULL, message_id TEXT NOT NULL, PRIMARY KEY(campaign,email));
            CREATE TABLE IF NOT EXISTS events (
                campaign TEXT, email TEXT, status TEXT, code INTEGER, updated TEXT, message_id TEXT);
            CREATE TABLE IF NOT EXISTS quota_attempts (account TEXT, attempted REAL);
            CREATE INDEX IF NOT EXISTS quota_account_time ON quota_attempts(account, attempted);
        ''')
        try:
            with self.db:
                self.db.execute("INSERT OR IGNORE INTO campaigns VALUES (?,?)", (campaign_id, fingerprint))
                saved = self.db.execute("SELECT fingerprint FROM campaigns WHERE id=?", (campaign_id,)).fetchone()[0]
                if saved != fingerprint:
                    raise ValueError("Este campana_id ya tiene otro contenido/remitente. Usa un ID nuevo solo para una campaña distinta.")
        except BaseException:
            self.db.close()
            raise

    def claim(self, email, message_id, retry=False, *, account=None, limit=400):
        timestamp = now()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            cursor = self.db.execute("INSERT OR IGNORE INTO deliveries VALUES (?,?,?,?,?,?)",
                                     (self.campaign_id, email, "EN_CURSO", None, timestamp, message_id))
            claimed = cursor.rowcount == 1
            if not claimed and retry:
                cursor = self.db.execute("UPDATE deliveries SET status='EN_CURSO', code=NULL, updated=?, message_id=? WHERE campaign=? AND email=? AND status='RECHAZO_TEMPORAL'",
                                         (timestamp, message_id, self.campaign_id, email))
                claimed = cursor.rowcount == 1
            if claimed:
                if account is not None:
                    used = self.db.execute('SELECT COUNT(*) FROM quota_attempts WHERE account=? AND attempted>?', (account, time.time() - 86400)).fetchone()[0]
                    if used >= limit:
                        raise QuotaReached('Se alcanzó el límite local de intentos en 24 horas.')
                    self.db.execute('INSERT INTO quota_attempts VALUES (?,?)', (account, time.time()))
                self.db.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", (self.campaign_id, email, "EN_CURSO", None, timestamp, message_id))
        return claimed

    def finish(self, email, status, code=None):
        with self.db:
            self.db.execute("UPDATE deliveries SET status=?, code=?, updated=? WHERE campaign=? AND email=?",
                            (status, code, now(), self.campaign_id, email))
            message_id = self.db.execute("SELECT message_id FROM deliveries WHERE campaign=? AND email=?", (self.campaign_id, email)).fetchone()[0]
            self.db.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", (self.campaign_id, email, status, code, now(), message_id))

    def close(self):
        self.db.close()


def read_history(path, campaign_id, fingerprint=None):
    if not path.exists():
        return {}
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        stored = db.execute("SELECT fingerprint FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if stored and fingerprint is not None and stored[0] != fingerprint:
            raise ValueError("El contenido cambió para este campana_id. No se puede reanudar como si fuera el mismo mensaje.")
        return dict(db.execute("SELECT email,status FROM deliveries WHERE campaign=?", (campaign_id,)))
    finally:
        db.close()


def export_history(path, campaign_id, output_root):
    rows = []
    if path.exists():
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        try:
            rows = [dict(row) for row in db.execute(
                "SELECT email,status,code,updated,message_id FROM deliveries WHERE campaign=? ORDER BY email",
                (campaign_id,))]
        finally:
            db.close()
    output_root.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="estado_", dir=output_root))
    path = folder / "estado_envios.json"
    write_json(path, {"campana": campaign_id, "fecha_utc": now(), "envios": rows})
    with (folder / 'Registro de envíos.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, delimiter=';')
        writer.writerow(['Correo', 'Estado SMTP', 'Código', 'Fecha UTC', 'Identificador del mensaje'])
        for row in rows:
            writer.writerow([("'" + str(value)) if str(value).startswith(('=', '+', '-', '@')) else value
                             for value in (row['email'], row['status'], row['code'], row['updated'], row['message_id'])])
    return path


def select_recipients(rows, exclusions, history, limit, retry=False, authorized=None):
    selected = []
    audit = []
    for row in rows:
        email = address(row["normalizado"]) if row["normalizado"] and row["dominio"] else ""
        if email.casefold() in exclusions:
            reason = "EXCLUIDO"
        elif authorized is not None and email.casefold() not in authorized:
            reason = 'SIN_AUTORIZACION_EN_LISTA'
        elif row["duplicado_de_linea"] is not None:
            reason = "DUPLICADO"
        elif row["estado"] != "APTO_DNS":
            reason = "NO_APTO_DNS"
        elif email in history and not (retry and history[email] == "RECHAZO_TEMPORAL"):
            reason = "REGISTRADO_" + history[email]
        elif len(selected) >= limit:
            reason = "OTRO_LOTE"
        else:
            reason = "SELECCIONADO"
            selected.append(row)
        audit.append({"linea": row["linea"], "correo": row["normalizado"], "decision": reason})
    return selected, audit


def require_authorization(cfg, test=False):
    if cfg["es_ejemplo"]:
        raise ValueError("La configuración de ejemplo solo permite simulación. Completa tus datos y cambia es_ejemplo a false.")
    needed = {"remitente_autorizado", "limites_confirmados"} if test else set(cfg["autorizacion"])
    missing = [key for key in sorted(needed) if not cfg["autorizacion"][key]]
    if missing:
        raise ValueError("Falta aprobación de la empresa: " + ", ".join(missing))
    smtp = cfg["smtp"]
    if not smtp["host"].strip() or "://" in smtp["host"] or any(c.isspace() for c in smtp["host"]):
        raise ValueError("Configura el hostname SMTP aprobado por el administrador (sin https://).")
    if smtp["autenticacion"] != "none" and not smtp["usuario"].strip():
        raise ValueError("Falta el usuario SMTP autorizado.")


def connect_smtp(cfg, secret=None):
    smtp = cfg["smtp"]
    if smtp["autenticacion"] != "none":
        if secret is None:
            secret = os.environ.get(smtp["secreto_env"], "") or getpass.getpass("Contraseña de aplicación o token SMTP (no se mostrará): ")
        if not secret:
            raise ValueError("No se proporcionó credencial SMTP.")
    context = ssl.create_default_context()
    client = None
    try:
        if smtp["seguridad"] == "ssl":
            client = smtplib.SMTP_SSL(smtp["host"], smtp["puerto"], timeout=30, context=context)
        else:
            client = smtplib.SMTP(smtp["host"], smtp["puerto"], timeout=30)
            client.ehlo()
            client.starttls(context=context)  # Si no hay TLS, falla sin mandar credenciales.
        client.ehlo()
        if smtp["autenticacion"] == "password":
            client.login(smtp["usuario"], secret)
        elif smtp["autenticacion"] == "oauth2":
            # smtplib.auth aplica Base64. Ante challenge de error, responder vacío.
            initial = f"user={smtp['usuario']}\x01auth=Bearer {secret}\x01\x01"
            client.auth("XOAUTH2", lambda challenge=None: initial if challenge is None else "")
        return client
    except BaseException:
        if client is not None:
            client.close()
        raise


def send_batch(cfg, messages, ledger, retry=False, connector=connect_smtp, sleeper=time.sleep, *, stop_event=None):
    """No repite envíos ambiguos; un 4xx detiene el lote, un 5xx no invalida el buzón."""
    counts = Counter()
    if stop_event is not None and stop_event.is_set():
        return Counter({"DETENIDO": 1})
    client = connector(cfg)  # Autenticación falla antes de reservar destinatarios.
    errors = 0
    try:
        for index, (recipient, msg) in enumerate(messages):
            if stop_event is not None and stop_event.is_set():
                counts["DETENIDO"] += 1
                break
            account = cfg['smtp']['host'].strip().casefold() + '\0' + (cfg['smtp']['usuario'] or cfg['remitente']['correo']).strip().casefold()
            try:
                claimed = ledger.claim(recipient, str(msg['Message-ID']), retry, account=account, limit=cfg['limites'].get('max_24h', 400))
            except QuotaReached:
                counts['LIMITE_LOCAL_24H'] += 1
                break
            if not claimed:
                counts["YA_REGISTRADO"] += 1
                continue
            stop = False
            try:
                refused = client.send_message(msg, from_addr=cfg["remitente"]["correo"], to_addrs=[recipient])
                if refused:
                    raise smtplib.SMTPRecipientsRefused(refused)
            except (smtplib.SMTPRecipientsRefused, smtplib.SMTPResponseException) as exc:
                code = next(iter(exc.recipients.values()))[0] if isinstance(exc, smtplib.SMTPRecipientsRefused) else exc.smtp_code
                state = "RECHAZO_TEMPORAL" if 400 <= code < 500 else "RECHAZO_PERMANENTE" if 500 <= code < 600 else "INCIERTO"
                ledger.finish(recipient, state, code)
                errors += 1
                stop = state in {"RECHAZO_TEMPORAL", "INCIERTO"} or isinstance(exc, smtplib.SMTPSenderRefused)
                counts[state] += 1
            except smtplib.SMTPNotSupportedError:
                ledger.finish(recipient, "FALLO_LOCAL")
                counts["FALLO_LOCAL"] += 1
                stop = True
            except (OSError, smtplib.SMTPException):
                ledger.finish(recipient, "INCIERTO")
                counts["INCIERTO"] += 1
                stop = True
            else:
                # Si el proceso cae antes de persistir esto, queda EN_CURSO: no reenvía.
                ledger.finish(recipient, "ACEPTADO_SMTP", 250)
                counts["ACEPTADO_SMTP"] += 1
                errors = 0
            print(f"Procesados en este lote: {index + 1}/{len(messages)}. {dict(counts)}", flush=True)
            if stop or errors >= cfg["limites"]["max_errores_consecutivos"]:
                print("Lote detenido. Revisa el registro y al proveedor antes de continuar.")
                break
            if index + 1 < len(messages):
                if stop_event is None:
                    sleeper(cfg["limites"]["intervalo_segundos"])
                else:
                    stop_event.wait(cfg["limites"]["intervalo_segundos"])
    finally:
        # No convertir un fallo de QUIT en un fallo de entrega; los estados ya están guardados.
        try:
            client.quit()
        except OSError:
            client.close()
    return counts


def write_json(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)


class PreparedMessages:
    """Genera un mensaje por vez: no duplica adjuntos en RAM por cada destinatario."""
    def __init__(self, cfg, content, selected, campaign_id):
        self.cfg, self.content, self.selected, self.campaign_id = cfg, content, selected, campaign_id

    def __len__(self):
        return len(self.selected)

    def __getitem__(self, index):
        row = self.selected[index]
        return address(row["normalizado"]), build_message(self.cfg, self.content, row, self.campaign_id)


def preview(folder, cfg, content, selected, audit, campaign_id):
    messages = PreparedMessages(cfg, content, selected, campaign_id)
    # Verificar todos antes de enviar; no comenzar si falla una plantilla o un adjunto.
    for _recipient, _message in messages:
        pass
    write_json(folder / "seleccion.json", {"campana": campaign_id, "decisiones": audit})
    # Un EML representativo evita guardar 1200 copias de adjuntos. Datos completos en selección.
    if messages:
        with (folder / "muestra.eml").open("xb") as stream:
            stream.write(messages[0][1].as_bytes())
        sample = messages[0][1].get_body(preferencelist=("plain",)).get_content()
        view = (f"Remitente: {cfg['remitente']['correo']}\n"
                f"Primer destinatario: {messages[0][0]}\nAsunto: {messages[0][1]['Subject']}\n\n{sample}\n"
                f"Adjuntos: {', '.join(name for name, _, _ in content['adjuntos']) or '(ninguno)'}\n")
        with (folder / "vista_previa.txt").open("x", encoding="utf-8") as stream:
            stream.write(view)
    return messages


def run(args, *, confirm=None, connector=None, stop_event=None, on_output=None):
    real = args.modo in {"enviar", "prueba"}
    if real and args.sin_dns:
        raise ValueError("--sin-dns solo está disponible para revisar/simular, nunca para enviar.")
    if args.destino_prueba and args.modo != "prueba":
        raise ValueError("--destino-prueba requiere --modo prueba.")
    if args.modo == "prueba" and args.archivo:
        raise ValueError("La prueba no usa una lista: omite el archivo y especifica --destino-prueba.")
    if args.modo not in {"prueba", "estado"} and not args.archivo:
        raise ValueError("Falta la lista TXT/CSV.")
    cfg = load_config(args.config) if args.modo != "revisar" else None
    if args.modo == "estado":
        history = read_history(args.registro, cfg["campana_id"])
        print("Campaña:", cfg["campana_id"], "Estados:", dict(Counter(history.values())))
        print("ACEPTADO_SMTP no significa entregado; EN_CURSO/INCIERTO requieren revisión manual.")
        history_file = export_history(args.registro, cfg['campana_id'], args.salida)
        if on_output is not None:
            on_output(history_file.parent)
        print('Detalle JSON y CSV para Excel:', history_file.parent.resolve())
        return 0
    if real:
        require_authorization(cfg, test=args.modo == "prueba")
    exclusions = load_exclusions(args.exclusiones)
    authorized_path = getattr(args, 'autorizados', None)
    authorized = load_exclusions(authorized_path) if authorized_path else None
    content, fingerprint = load_content(cfg, args.config.parent) if cfg else (None, None)
    if args.modo == "prueba":
        if not args.destino_prueba:
            raise ValueError("Falta --destino-prueba con tu dirección de prueba autorizada.")
        rows = prepare_lines([address(args.destino_prueba)])
    else:
        rows = load_contacts(args.archivo, args.columna_correo, args.separador)
    if not rows:
        raise ValueError("La lista no contiene direcciones.")
    if args.sin_dns:
        for row in rows:
            if not row["estado"]:
                row.update(estado="REVISAR", codigo="DNS_OMITIDO", motivo="Simulación sin red: DNS no comprobado.")
    else:
        verify(rows, DNSChecker(args.timeout, args.reintentos_dns), args.workers)
    if stop_event is not None and stop_event.is_set():
        print("Detenido antes de preparar o enviar mensajes.")
        return 130
    folder, _report = save_report(rows, args.salida, dns_checked_at="NO_REALIZADA" if args.sin_dns else None)
    if on_output is not None:
        on_output(folder)
    print("Informe de revisión (previo al envío):", (folder / "informe.html").resolve())
    if args.modo == "revisar":
        return 0
    campaign_id = cfg["campana_id"]
    if args.modo == "prueba":
        campaign_id += "_prueba_" + uuid.uuid4().hex[:12]
    history = read_history(args.registro, campaign_id, fingerprint)
    selected, audit = select_recipients(rows, exclusions, history, 1 if args.modo == "prueba" else cfg["limites"]["max_por_ejecucion"], args.reintentar_temporales,
                                       authorized=None if args.modo == 'prueba' else authorized)
    messages = preview(folder, cfg, content, selected, audit, campaign_id)
    print("Selección:", dict(Counter(item["decision"] for item in audit)))
    print("Remitente:", cfg["remitente"]["correo"], "Asunto:", cfg["mensaje"]["asunto"])
    print("Vista previa y destinatarios:", folder.resolve())
    if not real:
        print("SIMULACIÓN: no se conectó a SMTP, no se solicitaron credenciales ni se enviaron mensajes.")
        return 0
    if not messages:
        print("No hay destinatarios seleccionados. No se conectó a SMTP.")
        return 0
    print(f"ENVIARÁS {len(messages)} mensajes individuales mediante {cfg['smtp']['host']}:{cfg['smtp']['puerto']}.")
    print("Revisa seleccion.json y muestra.eml antes de confirmar. APTO_DNS no garantiza buzón ni entrega.")
    phrase = f"ENVIAR {len(messages)} {campaign_id}"
    if (confirm or input)(f"Para autorizar este lote escribe exactamente '{phrase}': ").strip() != phrase:
        print("Cancelado. No se conectó a SMTP.")
        return 0
    ledger = Ledger(args.registro, campaign_id, fingerprint)
    try:
        options = {}
        if connector is not None:
            options["connector"] = connector
        if stop_event is not None:
            options["stop_event"] = stop_event
        counts = send_batch(cfg, messages, ledger, args.reintentar_temporales, **options)
    finally:
        ledger.close()
    final_history = read_history(args.registro, campaign_id)
    write_json(folder / "envio.json", {"campana": campaign_id, "fecha_utc": now(),
               "lote": dict(counts), "historial_campana": final_history,
               "aviso": "Aceptado por SMTP no equivale a entregado. No se consultaron rebotes posteriores."})
    print("Registro persistente:", args.registro.resolve())
    return 2 if any(key not in {"ACEPTADO_SMTP", "YA_REGISTRADO"} for key in counts) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", nargs="?", type=Path, help="TXT o CSV UTF-8; no se usa en prueba/estado")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("campana.ejemplo.json"))
    parser.add_argument("--modo", choices=("revisar", "simular", "enviar", "prueba", "estado"), default="simular")
    parser.add_argument("--destino-prueba", help="Único destinatario autorizado para --modo prueba")
    parser.add_argument("--exclusiones", type=Path, help="TXT UTF-8 con bajas/exclusiones, una dirección por línea")
    parser.add_argument('--autorizados', type=Path, help='TXT de destinatarios autorizados; si se indica, solo se selecciona su intersección con la base apta.')
    parser.add_argument("--columna-correo", default="correo", help="Cabecera de email del CSV")
    parser.add_argument("--separador", choices=(",", ";", "\t"), help="Separador CSV; por defecto se detecta")
    parser.add_argument("--salida", type=Path, default=Path(__file__).parent / "resultados")
    parser.add_argument("--registro", type=Path, default=Path(__file__).parent / "resultados/envios.sqlite3")
    parser.add_argument("--sin-dns", action="store_true", help="Solo limpieza offline: no selecciona destinatarios para enviar")
    parser.add_argument("--reintentar-temporales", action="store_true", help="Permite repetir rechazos SMTP 4xx conocidos; nunca estados inciertos")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=4)
    parser.add_argument("--reintentos-dns", type=int, default=1)
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 32 or not 0.1 <= args.timeout <= 30 or not 0 <= args.reintentos_dns <= 3:
        parser.error("workers 1-32, timeout 0.1-30 y reintentos-dns 0-3.")
    try:
        return run(args)
    except (smtplib.SMTPException, OSError) as exc:
        # Nunca imprimir respuestas SMTP crudas: podrían contener datos o credenciales.
        print(f"No se completó ({type(exc).__name__}). Comprueba archivos, conexión y configuración con el administrador.")
        print("Si hubo envío, consulta --modo estado antes de reintentar. No borres el registro.")
        return 1
    except (ValueError, KeyError, TypeError, AttributeError, csv.Error, sqlite3.Error, dns.exception.DNSException) as exc:
        print(f"No se completó: {exc}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("Interrumpido. Los envíos en curso quedan reservados; revisa --modo estado antes de continuar.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
