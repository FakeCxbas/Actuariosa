from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from etapas import load_stage, save_stage
from generar_informe import main as report_main
from limpiar_lista import main as clean_main
from revisar_dns import main as dns_main
from verificar_correos import prepare_lines


class StageTests(unittest.TestCase):
    def test_full_pipeline_and_preserved_rows(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()):
            root = Path(directory)
            source = root / "entrada.txt"
            source.write_text("a@example.com\n\na@EXAMPLE.COM\nmalformado\n", encoding="utf-8")
            clean = root / "limpieza.json"
            dns = root / "dns.json"
            with patch("verificar_correos.DNSChecker.check", side_effect=AssertionError("Sin DNS en limpieza")):
                self.assertEqual(clean_main([str(source), "--salida", str(clean)]), 0)
            self.assertEqual(load_stage(clean, "limpieza")["resultados"][0]["estado"], "")
            with patch("revisar_dns.DNSChecker.check", return_value={"estado": "APTO_DNS", "codigo": "MX_RESUELVE", "motivo": "DNS", "mx": []}) as check:
                self.assertEqual(dns_main([str(clean), "--salida", str(dns)]), 0)
                check.assert_called_once_with("example.com")
            checked = load_stage(dns, "dns")
            with patch("verificar_correos.DNSChecker.check", side_effect=AssertionError("Sin DNS en informe")):
                self.assertEqual(report_main([str(dns), "--salida", str(root / "informes")]), 0)
            report = json.loads(next((root / "informes").glob("*/informe.json")).read_text(encoding="utf-8"))
            self.assertEqual(report["total"], 3)
            self.assertEqual(report["duplicados"], 1)
            self.assertEqual(report["resultados"][1]["linea"], 3)
            self.assertEqual(report["fecha_dns_utc"], checked["fecha_utc"])
            self.assertEqual(source.read_text(encoding="utf-8"), "a@example.com\n\na@EXAMPLE.COM\nmalformado\n")

    def test_refuse_overwrite(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "stage.json"
            save_stage(target, "limpieza", prepare_lines(["a@example.com"]))
            original = target.read_bytes()
            with self.assertRaises(FileExistsError):
                save_stage(target, "limpieza", [])
            self.assertEqual(target.read_bytes(), original)

    def test_wrong_stage(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "stage.json"
            save_stage(target, "limpieza", prepare_lines(["a@example.com"]))
            with self.assertRaises(ValueError):
                load_stage(target, "dns")

    def test_bad_rows(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "stage.json"
            save_stage(target, "limpieza", [{"original": "a@example.com"}])
            with self.assertRaises(ValueError):
                load_stage(target, "limpieza")

    def test_wrong_duplicate_reference(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "stage.json"
            rows = prepare_lines(["a@example.com"])
            rows[0]["duplicado_de_linea"] = 55
            save_stage(target, "limpieza", rows)
            with self.assertRaises(ValueError):
                load_stage(target, "limpieza")

    def test_empty_file_fails_without_output(self):
        with TemporaryDirectory() as directory, redirect_stderr(StringIO()):
            root = Path(directory)
            source = root / "empty.txt"
            source.write_text("\n", encoding="utf-8")
            target = root / "stage.json"
            with self.assertRaises(SystemExit) as error:
                clean_main([str(source), "--salida", str(target)])
            self.assertEqual(error.exception.code, 1)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
