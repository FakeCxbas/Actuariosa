"""Pruebas unitarias para la extracción universal de correos en celdas de Excel, CSV y TXT."""
import tempfile
import unittest
import zipfile
from pathlib import Path

from mxcorreo_server import extract_emails_from_cell, extraer_correos_de_archivo
from verificar_correos import prepare_lines


def make_test_xlsx(filepath, rows_data):
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    wb = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Hoja1" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""
    wb_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
    rows_xml = []
    for r_idx, row in enumerate(rows_data, 1):
        cols_xml = []
        for c_idx, val in enumerate(row, 1):
            col_letter = chr(64 + c_idx)
            ref = f"{col_letter}{r_idx}"
            cols_xml.append(f'<c r="{ref}" t="inlineStr"><is><t>{val}</t></is></c>')
        rows_xml.append(f'<row r="{r_idx}">{" ".join(cols_xml)}</row>')
    sheet1 = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{" ".join(rows_xml)}</sheetData>
</worksheet>"""
    with zipfile.ZipFile(filepath, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", wb)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet1)


class TestCellExtraction(unittest.TestCase):
    def test_extract_emails_from_cell_clean(self):
        self.assertEqual(extract_emails_from_cell("usuario@dominio.com"), ["usuario@dominio.com"])
        self.assertEqual(extract_emails_from_cell("mailto:admin@actuariosa.com"), ["admin@actuariosa.com"])

    def test_extract_emails_multiple_in_cell(self):
        cell = "a@empresa.com; b@empresa.com, c@empresa.com"
        self.assertEqual(extract_emails_from_cell(cell), ["a@empresa.com", "b@empresa.com", "c@empresa.com"])

    def test_ignore_non_email_data(self):
        self.assertEqual(extract_emails_from_cell("Juan Perez"), [])
        self.assertEqual(extract_emails_from_cell("0991234567"), [])
        self.assertEqual(extract_emails_from_cell("Av. 9 de Octubre 100"), [])
        self.assertEqual(extract_emails_from_cell(None), [])

    def test_extract_embedded_email(self):
        cell = "Escribir a ventas@actuariosa.ec para información"
        self.assertEqual(extract_emails_from_cell(cell), ["ventas@actuariosa.ec"])

    def test_extract_from_csv_no_header(self):
        csv_text = "Juan,0991234567,juan@test.com\nPedro,0997654321,pedro@test.com\n"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8-sig", suffix=".csv", delete=False) as f:
            f.write(csv_text)
            tmp_path = Path(f.name)
        try:
            emails = extraer_correos_de_archivo(tmp_path)
            self.assertEqual(emails, ["juan@test.com", "pedro@test.com"])
        finally:
            tmp_path.unlink()

    def test_extract_from_xlsx(self):
        with tempfile.NamedTemporaryFile("w", suffix=".xlsx", delete=False) as f:
            tmp_path = Path(f.name)
        try:
            make_test_xlsx(tmp_path, [
                ["RUC", "Nombre", "Correo", "Ciudad"],
                ["0999999999001", "Acme Corp", "contacto@acme.com", "Quito"],
                ["0998888888001", "Beta S.A.", "info@beta.com; gerencia@beta.com", "Guayaquil"],
            ])
            emails = extraer_correos_de_archivo(tmp_path)
            self.assertEqual(emails, ["contacto@acme.com", "info@beta.com", "gerencia@beta.com"])
        finally:
            tmp_path.unlink()

    def test_prepare_lines_categorization(self):
        lines = ["valido@test.com", "duplicado@test.com", "duplicado@test.com", "invalido@"]
        rows = prepare_lines(lines)
        validos = [r for r in rows if r.get("estado") != "INVALIDO" and bool(r.get("normalizado"))]
        invalidos = [r for r in rows if r.get("estado") == "INVALIDO"]
        dups = [r for r in validos if r.get("duplicado_de_linea") is not None]

        self.assertEqual(len(validos), 3)
        self.assertEqual(len(invalidos), 1)
        self.assertEqual(len(dups), 1)
        self.assertEqual(invalidos[0]["original"], "invalido@")


if __name__ == "__main__":
    unittest.main()
