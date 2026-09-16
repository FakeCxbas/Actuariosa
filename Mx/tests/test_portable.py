from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import Mock, patch

import campana
from mxcorreo_app import default_data_dir, resources, save_json_atomic
from test_campana import config, content, valid_rows


class PortableTests(unittest.TestCase):
    def test_frozen_data_is_outside_internal_folder(self):
        executable = Path('portable').resolve() / 'MxCorreo.exe'
        with patch("mxcorreo_app.sys.frozen", True, create=True), patch("mxcorreo_app.sys.executable", str(executable)):
            self.assertEqual(default_data_dir(), executable.parent / 'datos')

    def test_example_resources_exist(self):
        for name in ("campana.ejemplo.json", "mensaje.ejemplo.txt", "ejemplo.txt", "LEEME_WINDOWS.txt"):
            self.assertTrue((resources() / name).is_file())

    def test_atomic_settings_save(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_json_atomic(path, {"a": 1})
            save_json_atomic(path, {"a": 2})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 2})

    def test_explicit_gui_secret_does_not_read_environment_or_console(self):
        client = Mock()
        with patch.dict(os.environ, {"CORREO_SMTP_SECRET": "should-not-use"}), patch("campana.smtplib.SMTP", return_value=client), patch("campana.getpass.getpass") as prompt:
            campana.connect_smtp(config(), secret="explicit-test-secret")
        prompt.assert_not_called()
        self.assertEqual(client.login.call_args.args[1], "explicit-test-secret")

    def test_empty_gui_secret_never_falls_back(self):
        with patch.dict(os.environ, {"CORREO_SMTP_SECRET": "should-not-use"}), patch("campana.smtplib.SMTP") as client:
            with self.assertRaises(ValueError):
                campana.connect_smtp(config(), secret="")
        client.assert_not_called()

    def test_stop_before_connect(self):
        event = threading.Event()
        event.set()
        connector = Mock()
        result = campana.send_batch(config(), [], Mock(), connector=connector, stop_event=event)
        self.assertEqual(result["DETENIDO"], 1)
        connector.assert_not_called()

    def test_stop_after_current_message_is_recorded(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()):
            path = Path(directory) / "db.sqlite3"
            ledger = campana.Ledger(path, "test", "hash")
            event = threading.Event()
            client = Mock()
            def sent(*args, **kwargs):
                event.set()
                return {}
            client.send_message.side_effect = sent
            cfg = config()
            messages = [(row["normalizado"], campana.build_message(cfg, content(), row, "test")) for row in valid_rows("a@example.com", "b@example.com")]
            try:
                counts = campana.send_batch(cfg, messages, ledger, connector=lambda _: client, stop_event=event)
            finally:
                ledger.close()
            self.assertEqual(counts["ACEPTADO_SMTP"], 1)
            self.assertEqual(campana.read_history(path, "test"), {"a@example.com": "ACEPTADO_SMTP"})
            self.assertEqual(client.send_message.call_count, 1)


if __name__ == "__main__":
    unittest.main()
