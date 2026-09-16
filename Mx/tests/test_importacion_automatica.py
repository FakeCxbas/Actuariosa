import csv
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch
import zipfile

from importacion_automatica import ImportCancelled, cell_contacts, decode_text, header_kind, scan_files, scan_table
from importar_contactos import load_import, save_import
from resultados_interfaz import export_lists, matches
from verificar_correos import prepare_lines


def fixture_xlsx(path):
    # Tiny OOXML fixture with data starting in B3; a second empty sheet.
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Clientes" sheetId="1" r:id="rId1"/><sheet name="Vacía" sheetId="2" r:id="rId2"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="B3:C5"/><sheetData><row r="3"><c r="B3" t="inlineStr"><is><t>Correo</t></is></c><c r="C3" t="inlineStr"><is><t>Nombre</t></is></c></row><row r="4"><c r="B4" t="inlineStr"><is><t>ana@example.com</t></is></c><c r="C4" t="inlineStr"><is><t>Ana</t></is></c></row><row r="5" hidden="1"><c r="B5" t="inlineStr"><is><t>mal@@example</t></is></c></row></sheetData></worksheet>')
        z.writestr('xl/worksheets/sheet2.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>')


class AutoImportTests(unittest.TestCase):
    def test_headers(self):
        for value in ('Correo electrónico', 'EMAIL', 'E-mail 2', 'Correos', 'email_1'):
            self.assertEqual(header_kind(value), 'correo')
        self.assertEqual(header_kind('Correo enviado el martes'), '')

    def test_no_header_and_late_email(self):
        table = [['Teléfono', 'Dato']] + [['123', 'nada']] * 60 + [['123', 'ana@example.com']]
        groups = scan_table(lambda: enumerate(table, 1), 'a.csv', 'CSV')
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['columna'], 'B')
        self.assertEqual(groups[0]['contacts'][0]['celda_origen'], 'B62')

    def test_multiple_columns_and_invalids(self):
        table = [['Nombre', 'Correo', 'E-mail 2', 'Empresa'], ['Ana', 'a@example.com; b@example.com', 'invalid@@example', 'ABC'], ['Luis', 'sin arroba', '', 'DEF']]
        groups = scan_table(lambda: enumerate(table, 1), 'a.csv', 'CSV')
        self.assertEqual([len(g['contacts']) for g in groups], [3, 1])
        self.assertEqual(groups[0]['contacts'][0]['nombre'], 'Ana')
        self.assertEqual(groups[0]['contacts'][0]['empresa'], 'ABC')
        self.assertEqual(groups[0]['contacts'][-1]['correo'], 'sin arroba')

    def test_cell_split_preserves_names_and_errors(self):
        self.assertEqual([r['correo'] for r in cell_contacts('a@example.com b@example.com')], ['a@example.com', 'b@example.com'])
        self.assertEqual(cell_contacts('Ana <a@example.com>')[0]['nombre'], 'Ana')
        self.assertEqual(cell_contacts('mal@@example')[0]['correo'], 'mal@@example')

    def test_encodings(self):
        text = 'correo\nniño@ejemplo.com'
        for encoding in ('utf-8-sig', 'utf-16', 'cp1252'):
            self.assertEqual(decode_text(text.encode(encoding))[0], text)

    def test_scan_csv_without_header_keeps_first_record(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'a.csv'
            path.write_text('a@example.com\nb@example.com\n', encoding='utf-8')
            before = path.read_bytes()
            groups, issues = scan_files([path])
            self.assertFalse(issues)
            self.assertEqual(len(groups[0]['contacts']), 2)
            self.assertEqual(path.read_bytes(), before)

    def test_real_xlsx_empty_sheet_hidden_rows_and_coordinates(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.xlsx'
            fixture_xlsx(path)
            groups, issues = scan_files([path])
            self.assertFalse(issues, issues)
            self.assertEqual(groups[0]['columna'], 'B')
            self.assertEqual([c['celda_origen'] for c in groups[0]['contacts']], ['B4', 'B5'])
            self.assertEqual(groups[0]['contacts'][0]['nombre'], 'Ana')

    def test_cancellation(self):
        event = threading.Event()
        event.set()
        with self.assertRaises(ImportCancelled):
            scan_files(['x.csv'], event)
        with self.assertRaises(ValueError):
            prepare_lines(['a@example.com'], stop_event=event)

    def test_limit_and_failed_file_are_explicit(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'a.csv'
            path.write_text('a@example.com\nb@example.com', encoding='utf-8')
            with patch('importacion_automatica.MAX_ROWS', 1):
                groups, issues = scan_files([path])
            self.assertFalse(groups)
            self.assertEqual(len(issues), 1)

    def test_multifile_provenance_roundtrip(self):
        with TemporaryDirectory() as tmp:
            table = [['correo'], ['ana@example.com']]
            contacts = scan_table(lambda: enumerate(table, 1), 'a.csv', 'CSV')[0]['contacts']
            path = save_import(contacts, {'archivo': '1 archivo'}, tmp)
            row = load_import(path)[0]
            self.assertEqual(row['origen']['archivo'], 'a.csv')
            self.assertEqual(row['celda_origen'], 'A2')

    def test_filter_and_export(self):
        rows = prepare_lines(['a@example.com', 'a@example.com', 'b@example.com', '=bad', 'c@example.com'])
        rows[0]['estado'] = rows[1]['estado'] = 'APTO_DNS'
        rows[2]['estado'] = 'REVISAR'
        self.assertTrue(matches(rows[1], 'Duplicados', 'example'))
        self.assertFalse(matches(rows[0], 'Con problemas'))
        with TemporaryDirectory() as tmp:
            folder, counts = export_lists(rows, tmp)
            self.assertEqual(counts['Todos los correos'], 4)
            self.assertEqual(counts['Correos con dominio apto'], 1)
            self.assertEqual(counts['Correos con problemas'], 1)
            self.assertEqual(counts['Correos por revisar'], 2)
            with (folder / 'Correos con problemas.csv').open(encoding='utf-8-sig', newline='') as stream:
                self.assertEqual(list(csv.reader(stream)), [["'=bad"]])


if __name__ == '__main__':
    unittest.main()
