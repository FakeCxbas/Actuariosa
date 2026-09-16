from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from procesar_carpeta import export, load_dns, safe_csv_value


class FolderProcessingTests(unittest.TestCase):
    def test_excel_formula_protection(self):
        self.assertEqual(safe_csv_value('=cmd'), "'=cmd")
        self.assertEqual(safe_csv_value('a@example.com'), 'a@example.com')

    def test_partial_dns_log_can_resume(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'dns.jsonl'
            path.write_text('{"dominio":"example.com","estado":"APTO_DNS"}\n', encoding='utf-8')
            self.assertEqual(load_dns(path)['example.com']['estado'], 'APTO_DNS')

    def test_export_never_puts_review_in_problem_list(self):
        rows = [
            {'original': 'a@example.com', 'normalizado': 'a@example.com', 'estado': 'APTO_DNS'},
            {'original': 'b@example.com', 'normalizado': 'b@example.com', 'estado': 'REVISAR'},
            {'original': 'bad', 'normalizado': '', 'estado': 'INVALIDO'},
        ]
        summary = {'fecha_utc': 'x', 'archivos_examinados': 1, 'apariciones': 3,
                   'direcciones_distintas': 3, 'repeticiones': 0, 'estados': {}, 'fuentes': []}
        with TemporaryDirectory() as directory:
            counts = export(Path(directory), rows, summary)
            self.assertEqual(counts['Correos con problemas.csv'], 1)
            self.assertEqual(counts['Correos por revisar.csv'], 1)


if __name__ == '__main__':
    unittest.main()
