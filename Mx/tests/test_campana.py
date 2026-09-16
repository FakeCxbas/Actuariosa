from contextlib import redirect_stdout
from email import policy
from email.parser import BytesParser
from io import StringIO
import json
import os
from pathlib import Path
import smtplib
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import campana as c
from verificar_correos import prepare_lines


ROOT = Path(__file__).resolve().parents[1]


def config():
    return c.load_config(ROOT / "campana.ejemplo.json")


def valid_rows(*values):
    rows = prepare_lines(values)
    for row in rows:
        if not row["estado"]:
            row.update(estado="APTO_DNS", codigo="MX_RESUELVE", motivo="DNS")
    return rows


def content():
    return {"texto": "Hola ${nombre}; ${correo}", "html": "<p>${nombre}</p>", "adjuntos": []}


class InputAndMessageTests(unittest.TestCase):
    def test_example_cannot_send(self):
        with self.assertRaises(ValueError):
            c.require_authorization(config())

    def test_flags_cannot_be_string(self):
        cfg = config()
        cfg["autorizacion"]["envio_aprobado"] = "false"
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            with self.assertRaises(ValueError):
                c.load_config(path)

    def test_no_plaintext_smtp(self):
        cfg = config()
        cfg["smtp"]["seguridad"] = "none"
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            with self.assertRaises(ValueError):
                c.load_config(path)

    def test_csv_semicolon_names_and_duplicate(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            path.write_text('correo;nombre;empresa\na@example.com;Ana;Empresa\na@EXAMPLE.COM;Ana;Empresa\n', encoding="utf-8-sig")
            rows = c.load_contacts(path)
            self.assertEqual(rows[0]["nombre"], "Ana")
            self.assertEqual(rows[0]["linea"], 2)
            self.assertEqual(rows[1]["duplicado_de_linea"], 2)

    def test_csv_wrong_column_fails(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            path.write_text("correo,nombre\na@example.com,Ana,extra\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                c.load_contacts(path)

    def test_bad_exclusion_fails_closed(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "exclude.txt"
            path.write_text("bad-email", encoding="utf-8")
            with self.assertRaises(ValueError):
                c.load_exclusions(path)

    def test_selection_excludes_duplicates_and_bad_dns(self):
        rows = valid_rows("a@example.com", "a@EXAMPLE.COM", "b@example.com", "malformado", "c@example.com")
        selected, audit = c.select_recipients(rows, {"b@example.com"}, {}, 1)
        self.assertEqual(len(selected), 1)
        self.assertEqual([r["decision"] for r in audit], ["SELECCIONADO", "DUPLICADO", "EXCLUIDO", "NO_APTO_DNS", "OTRO_LOTE"])

    def test_only_known_temporary_can_retry(self):
        rows = valid_rows("a@example.com", "b@example.com", "c@example.com", "d@example.com")
        history = dict(zip([r["normalizado"] for r in rows], ["ACEPTADO_SMTP", "INCIERTO", "EN_CURSO", "RECHAZO_TEMPORAL"]))
        self.assertEqual(c.select_recipients(rows, set(), history, 10)[0], [])
        self.assertEqual(c.select_recipients(rows, set(), history, 10, True)[0][0]["normalizado"], "d@example.com")

    def test_1200_contacts_in_nonoverlapping_batches(self):
        rows = valid_rows(*(f"persona{i}@example.com" for i in range(1200)))
        history = {}
        for _ in range(24):
            selected, _audit = c.select_recipients(rows, set(), history, 50)
            self.assertEqual(len(selected), 50)
            for row in selected:
                self.assertNotIn(row["normalizado"], history)
                history[row["normalizado"]] = "ACEPTADO_SMTP"
        self.assertEqual(len(history), 1200)
        self.assertEqual(c.select_recipients(rows, set(), history, 50)[0], [])

    def test_message_private_and_html_escaped(self):
        row = valid_rows("a@example.com")[0]
        row["nombre"] = '<script>alert("x")</script>'
        msg = c.build_message(config(), content(), row, "test")
        self.assertEqual(str(msg["To"]), "a@example.com")
        self.assertNotIn("Cc", msg)
        self.assertNotIn("Bcc", msg)
        self.assertIn("&lt;script&gt;", msg.get_body(preferencelist=("html",)).get_content())

    def test_header_injection_rejected(self):
        cfg = config()
        cfg["mensaje"]["asunto"] = "Hola ${nombre}"
        row = valid_rows("a@example.com")[0]
        row["nombre"] = "Ana\r\nBcc: evil@example.com"
        with self.assertRaises(ValueError):
            c.build_message(cfg, content(), row, "test")

    def test_unknown_placeholder_fails(self):
        payload = content()
        payload["texto"] = "Hola ${unknown}"
        with self.assertRaises(KeyError):
            c.build_message(config(), payload, valid_rows("a@example.com")[0], "test")

    def test_attachment_survives_mime(self):
        payload = content()
        payload["adjuntos"] = [("dato.txt", "text/plain", b"contenido")]
        msg = c.build_message(config(), payload, valid_rows("a@example.com")[0], "test")
        parsed = BytesParser(policy=policy.default).parsebytes(msg.as_bytes())
        self.assertEqual(next(parsed.iter_attachments()).get_payload(decode=True), b"contenido")

    def test_size_limit_before_send(self):
        cfg = config()
        cfg["limites"]["max_mensaje_mb"] = 0.001
        payload = content()
        payload["adjuntos"] = [("dato.bin", "application/octet-stream", b"x" * 2048)]
        with self.assertRaises(ValueError):
            c.build_message(cfg, payload, valid_rows("a@example.com")[0], "test")


class LedgerAndSendingTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / "ledger.sqlite3"
        self.ledger = c.Ledger(self.path, "test", "fingerprint")
        self.cfg = config()
        self.messages = [(r["normalizado"], c.build_message(self.cfg, content(), r, "test")) for r in valid_rows("a@example.com", "b@example.com")]
        self.client = Mock()
        self.client.send_message.return_value = {}

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def send(self, **kwargs):
        with redirect_stdout(StringIO()):
            return c.send_batch(self.cfg, self.messages, self.ledger, connector=lambda _: self.client, sleeper=lambda _: None, **kwargs)

    def test_success_individual_envelopes_and_resume(self):
        counts = self.send()
        self.assertEqual(counts["ACEPTADO_SMTP"], 2)
        self.assertEqual(self.client.send_message.call_args_list[0].kwargs["to_addrs"], ["a@example.com"])
        self.assertEqual(self.send()["YA_REGISTRADO"], 2)
        self.assertEqual(self.client.send_message.call_count, 2)

    def test_connection_failure_does_not_reserve(self):
        with self.assertRaises(OSError):
            c.send_batch(self.cfg, self.messages, self.ledger, connector=Mock(side_effect=OSError("offline")))
        self.assertEqual(c.read_history(self.path, "test"), {})

    def test_disconnect_uncertain_and_no_retry(self):
        self.client.send_message.side_effect = smtplib.SMTPServerDisconnected("lost")
        self.assertEqual(self.send()["INCIERTO"], 1)
        self.assertEqual(c.read_history(self.path, "test"), {"a@example.com": "INCIERTO"})
        self.assertFalse(self.ledger.claim("a@example.com", "id", True))

    def test_4xx_stops_and_can_explicitly_retry(self):
        self.client.send_message.side_effect = smtplib.SMTPRecipientsRefused({"a@example.com": (450, b"later")})
        self.assertEqual(self.send()["RECHAZO_TEMPORAL"], 1)
        self.assertFalse(self.ledger.claim("a@example.com", "id"))
        self.assertTrue(self.ledger.claim("a@example.com", "id", True))

    def test_5xx_is_not_bounce_or_automatic_retry(self):
        self.client.send_message.side_effect = [smtplib.SMTPRecipientsRefused({"a@example.com": (550, b"policy")}), {}]
        counts = self.send()
        self.assertEqual(counts["RECHAZO_PERMANENTE"], 1)
        self.assertEqual(counts["ACEPTADO_SMTP"], 1)
        self.assertFalse(self.ledger.claim("a@example.com", "id", True))

    def test_data_rejection(self):
        self.client.send_message.side_effect = smtplib.SMTPDataError(451, b"temporary")
        self.assertEqual(self.send()["RECHAZO_TEMPORAL"], 1)

    def test_unsupported_utf8_not_recorded_as_sent(self):
        self.client.send_message.side_effect = smtplib.SMTPNotSupportedError("SMTPUTF8")
        self.assertEqual(self.send()["FALLO_LOCAL"], 1)

    def test_quit_failure_does_not_undo_success(self):
        self.client.quit.side_effect = smtplib.SMTPServerDisconnected("quit")
        self.assertEqual(self.send()["ACEPTADO_SMTP"], 2)

    def test_interruption_stays_reserved(self):
        self.client.send_message.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.send()
        self.assertEqual(c.read_history(self.path, "test")["a@example.com"], "EN_CURSO")
        self.assertFalse(self.ledger.claim("a@example.com", "id", True))

    def test_fingerprint_mismatch(self):
        with self.assertRaises(ValueError):
            c.read_history(self.path, "test", "changed")
        with self.assertRaises(ValueError):
            c.Ledger(self.path, "test", "changed")

    def test_two_connections_cannot_claim_same_recipient(self):
        second = c.Ledger(self.path, "test", "fingerprint")
        try:
            self.assertTrue(self.ledger.claim("a@example.com", "id"))
            self.assertFalse(second.claim("a@example.com", "id"))
        finally:
            second.close()


class ConnectionTests(unittest.TestCase):
    def test_tls_before_login(self):
        cfg = config()
        client = Mock()
        with patch.dict(os.environ, {"CORREO_SMTP_SECRET": "fake"}), patch("campana.smtplib.SMTP", return_value=client):
            c.connect_smtp(cfg)
        self.assertEqual([x[0] for x in client.method_calls], ["ehlo", "starttls", "ehlo", "login"])

    def test_tls_failure_never_authenticates(self):
        client = Mock()
        client.starttls.side_effect = smtplib.SMTPNotSupportedError("no TLS")
        with patch.dict(os.environ, {"CORREO_SMTP_SECRET": "fake"}), patch("campana.smtplib.SMTP", return_value=client):
            with self.assertRaises(smtplib.SMTPNotSupportedError):
                c.connect_smtp(config())
        client.login.assert_not_called()
        client.close.assert_called_once()

    def test_oauth2_initial_response_and_empty_error_challenge(self):
        cfg = config()
        cfg["smtp"].update(autenticacion="oauth2", usuario="sender@example.com")
        client = Mock()
        with patch.dict(os.environ, {"CORREO_SMTP_SECRET": "fake-token"}), patch("campana.smtplib.SMTP", return_value=client):
            c.connect_smtp(cfg)
        mechanism, callback = client.auth.call_args.args
        self.assertEqual(mechanism, "XOAUTH2")
        self.assertEqual(callback(), "user=sender@example.com\x01auth=Bearer fake-token\x01\x01")
        self.assertEqual(callback(b"error"), "")
        client.login.assert_not_called()

    def test_ssl_relay_no_password(self):
        cfg = config()
        cfg["smtp"].update(seguridad="ssl", autenticacion="none")
        client = Mock()
        with patch("campana.smtplib.SMTP_SSL", return_value=client), patch("campana.getpass.getpass") as prompt:
            c.connect_smtp(cfg)
        client.starttls.assert_not_called()
        client.login.assert_not_called()
        prompt.assert_not_called()


class CLITests(unittest.TestCase):
    def test_full_send_and_second_run_only_pending_with_fake_smtp(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()):
            root = Path(directory)
            cfg = config()
            cfg.update(campana_id="integration", es_ejemplo=False)
            cfg["autorizacion"] = {key: True for key in cfg["autorizacion"]}
            cfg["smtp"].update(host="smtp.example.com", usuario="user@example.com")
            cfg["mensaje"]["archivo_texto"] = str(ROOT / "mensaje.ejemplo.txt")
            path = root / "cfg.json"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            client = Mock()
            client.send_message.return_value = {}
            arguments = [str(ROOT / "ejemplo.txt"), "--modo", "enviar", "--config", str(path), "--salida", str(root / "out"), "--registro", str(root / "ledger.sqlite3")]
            with patch("campana.DNSChecker.check", return_value={"estado": "APTO_DNS", "codigo": "MX_RESUELVE", "motivo": "DNS", "mx": []}), patch("builtins.input", return_value="ENVIAR 3 integration"), patch.dict(os.environ, {"CORREO_SMTP_SECRET": "test-only"}), patch("campana.smtplib.SMTP", return_value=client) as factory, patch.object(c.send_batch, "__defaults__", (False, c.connect_smtp, lambda _: None)):
                self.assertEqual(c.main(arguments), 0)
                self.assertEqual(c.main(arguments), 0)
            self.assertEqual(client.send_message.call_count, 3)
            factory.assert_called_once()
            self.assertEqual(set(c.read_history(root / "ledger.sqlite3", "integration").values()), {"ACEPTADO_SMTP"})
            self.assertEqual(len(list((root / "out").glob("*/envio.json"))), 1)

    def test_test_mode_only_sends_to_explicit_address(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()):
            root = Path(directory)
            cfg = config()
            cfg.update(campana_id="production", es_ejemplo=False)
            cfg["autorizacion"].update(remitente_autorizado=True, limites_confirmados=True)
            cfg["smtp"].update(host="smtp.example.com", usuario="user@example.com")
            cfg["mensaje"]["archivo_texto"] = str(ROOT / "mensaje.ejemplo.txt")
            path = root / "cfg.json"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            client = Mock()
            client.send_message.return_value = {}
            with patch("campana.DNSChecker.check", return_value={"estado": "APTO_DNS", "codigo": "MX_RESUELVE", "motivo": "DNS", "mx": []}), patch("builtins.input", side_effect=lambda prompt: prompt.split("'")[1]), patch.dict(os.environ, {"CORREO_SMTP_SECRET": "test-only"}), patch("campana.smtplib.SMTP", return_value=client):
                self.assertEqual(c.main(["--modo", "prueba", "--destino-prueba", "test@example.com", "--config", str(path), "--salida", str(root / "out"), "--registro", str(root / "ledger.sqlite3")]), 0)
            self.assertEqual(client.send_message.call_args.kwargs["to_addrs"], ["test@example.com"])
            self.assertEqual(c.read_history(root / "ledger.sqlite3", "production"), {})

    def test_status_exports_details_without_smtp(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()):
            root = Path(directory)
            cfg = config()
            ledger = c.Ledger(root / "db.sqlite3", cfg["campana_id"], "hash")
            ledger.claim("a@example.com", "<id@example.com>")
            ledger.finish("a@example.com", "INCIERTO")
            ledger.close()
            with patch("campana.smtplib.SMTP") as smtp, patch("campana.DNSChecker.check") as dns:
                self.assertEqual(c.main(["--modo", "estado", "--registro", str(root / "db.sqlite3"), "--salida", str(root / "out")]), 0)
            smtp.assert_not_called()
            dns.assert_not_called()
            details = json.loads(next((root / "out").glob("*/estado_envios.json")).read_text(encoding="utf-8"))
            self.assertEqual(details["envios"][0]["status"], "INCIERTO")
            self.assertEqual(details["envios"][0]["message_id"], "<id@example.com>")

    def test_default_simulation_never_connects_or_mutates_ledger(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()):
            root = Path(directory)
            with patch("campana.DNSChecker.check", return_value={"estado": "APTO_DNS", "codigo": "MX_RESUELVE", "motivo": "DNS", "mx": []}), patch("campana.smtplib.SMTP") as smtp, patch("campana.getpass.getpass") as prompt:
                result = c.main([str(ROOT / "ejemplo.txt"), "--salida", str(root / "out"), "--registro", str(root / "ledger.sqlite3")])
            self.assertEqual(result, 0)
            smtp.assert_not_called()
            prompt.assert_not_called()
            self.assertFalse((root / "ledger.sqlite3").exists())
            self.assertEqual(len(list((root / "out").glob("*/muestra.eml"))), 1)

    def test_real_send_with_example_is_blocked_before_network(self):
        with redirect_stdout(StringIO()), patch("campana.DNSChecker.check") as dns, patch("campana.smtplib.SMTP") as smtp:
            self.assertEqual(c.main([str(ROOT / "ejemplo.txt"), "--modo", "enviar"]), 1)
        dns.assert_not_called()
        smtp.assert_not_called()

    def test_cancel_confirmation_does_not_connect(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()):
            root = Path(directory)
            cfg = config()
            cfg["es_ejemplo"] = False
            cfg["autorizacion"] = {key: True for key in cfg["autorizacion"]}
            cfg["smtp"].update(host="smtp.example.com", usuario="user@example.com")
            cfg["mensaje"]["archivo_texto"] = str(ROOT / "mensaje.ejemplo.txt")
            path = root / "cfg.json"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            with patch("campana.DNSChecker.check", return_value={"estado": "APTO_DNS", "codigo": "MX_RESUELVE", "motivo": "DNS", "mx": []}), patch("builtins.input", return_value="NO"), patch("campana.smtplib.SMTP") as smtp:
                result = c.main([str(ROOT / "ejemplo.txt"), "--modo", "enviar", "--config", str(path), "--salida", str(root / "out"), "--registro", str(root / "ledger.sqlite3")])
            self.assertEqual(result, 0)
            smtp.assert_not_called()
            self.assertFalse((root / "ledger.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
