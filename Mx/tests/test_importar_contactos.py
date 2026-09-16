import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import campana
from importar_contactos import column_letter, extract_excel, extract_pasted, load_import, read_sheet, save_import


class _Sheet:
    def __init__(self, table):
        self.end = (len(table) - 1, max(len(row) for row in table) - 1) if table else None
        self.table = table

    def to_python(self, *, skip_empty_area):
        self.skip_empty_area = skip_empty_area
        return self.table


class _Workbook:
    def __init__(self, table):
        self.sheet = _Sheet(table)

    def get_sheet_by_name(self, name):
        return self.sheet


class ContactImportTests(unittest.TestCase):
    def test_excel_selection_preserves_source_and_duplicates(self):
        table = [["Nombre", "Correo", "Empresa"], ["Ana", "ana@example.com", "Uno"], ["Otra", "ana@EXAMPLE.com", "Dos"], ["Sin", "", "Tres"]]
        contacts = extract_excel(table, first_row=1, has_header=True, email_column=1, name_column=0, company_column=2)
        self.assertEqual([item["celda_origen"] for item in contacts], ["B2", "B3"])
        self.assertEqual(contacts[0]["nombre"], "Ana")
        with TemporaryDirectory() as directory:
            path = save_import(contacts, {"tipo": "excel", "archivo": "contactos.xlsx", "hoja": "Clientes"}, directory)
            rows = load_import(path)
            self.assertEqual(rows[0]["nombre"], "Ana")
            self.assertEqual(rows[1]["duplicado_de_linea"], 1)
            self.assertEqual(rows[1]["celda_origen"], "B3")
            self.assertEqual(campana.load_contacts(path)[0]["empresa"], "Uno")

    def test_paste_supports_names_and_separators(self):
        contacts = extract_pasted('Ana <ana@example.com>; mailto:b@example.com\ninvalid@@example')
        self.assertEqual([item["correo"] for item in contacts], ["ana@example.com", "b@example.com", "invalid@@example"])
        self.assertEqual(contacts[0]["nombre"], "Ana")

    def test_sheet_keeps_coordinates_when_empty_cells_precede_data(self):
        workbook = _Workbook([[None, None], [None, "correo"], [None, "ana@example.com"]])
        table = read_sheet(workbook, "Hoja 1")
        self.assertFalse(workbook.sheet.skip_empty_area)
        contacts = extract_excel(table, first_row=2, has_header=True, email_column=1)
        self.assertEqual(contacts[0]["celda_origen"], "B3")

    def test_column_letters(self):
        self.assertEqual([column_letter(index) for index in (0, 25, 26, 27, 701)], ["A", "Z", "AA", "AB", "ZZ"])

    def test_rejects_tampered_import(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.mxlista"
            path.write_text(json.dumps({"version": 1, "origen": {}, "contactos": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_import(path)


if __name__ == "__main__":
    unittest.main()
