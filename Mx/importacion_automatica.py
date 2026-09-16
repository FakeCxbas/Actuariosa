"""Detección local de columnas. No evalúa fórmulas ni conecta a correo o DNS."""
import csv
import io
from pathlib import Path
import re
import unicodedata

from importar_contactos import MAX_ROWS, column_letter, extract_pasted, open_excel

EXTENSIONS = {'.csv', '.txt', '.xlsx', '.xls'}


class ImportCancelled(Exception):
    pass


def check_stop(stop):
    if stop is not None and stop.is_set():
        raise ImportCancelled('Importación cancelada. La lista anterior se conserva.')


def header_kind(value):
    text = ''.join(c for c in unicodedata.normalize('NFD', str(value).lower()) if not unicodedata.combining(c))
    text = re.sub(r'[^a-z0-9]+', ' ', text).strip()
    if re.fullmatch(r'(?:correo(?:s)?(?: electronico(?:s)?)?|e mail|email|emails|mail)(?: \d+)?', text):
        return 'correo'
    if text in {'nombre', 'nombres', 'name', 'nombre completo', 'contacto'}:
        return 'nombre'
    if text in {'empresa', 'company', 'razon social', 'institucion'}:
        return 'empresa'
    return ''


def decode_text(raw):
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        return raw.decode('utf-16'), 'UTF-16'
    try:
        return raw.decode('utf-8-sig'), 'UTF-8'
    except UnicodeDecodeError:
        return raw.decode('cp1252'), 'Windows-1252'


def cell_contacts(value):
    value = str(value).strip()
    # Split whitespace-delimited bare addresses without damaging display names
    # or quoted local parts. Keep malformed tokens for syntax review.
    words = value.split()
    if len(words) > 1 and all('@' in w for w in words) and not any(c in value for c in '<>";,'):
        value = '\n'.join(words)
    return extract_pasted(value)


def scan_table(rows_factory, filename, sheet, stop=None, max_contacts=MAX_ROWS):
    """Two passes, no dense table allocation. Return selectable column groups."""
    columns, headers, counts = {}, {}, {}
    for number, row in rows_factory():
        check_stop(stop)
        for col, value in enumerate(row):
            text = '' if value is None else str(value).strip()
            if number <= 50 and '@' not in text:
                kind = header_kind(text)
                if kind and col not in headers:
                    headers[col] = (number, kind, text)
            if '@' in text:
                counts[col] = counts.get(col, 0) + 1
    for col in sorted(set(counts) | {c for c, (_, kind, _) in headers.items() if kind == 'correo'}):
        title = headers.get(col, (0, '', ''))
        columns[col] = {'archivo': filename, 'hoja': sheet, 'columna': column_letter(col),
                        'titulo': title[2], 'contacts': [], 'con_arroba': counts.get(col, 0)}
    total = 0
    for number, row in rows_factory():
        check_stop(stop)
        for col, group in columns.items():
            value = str(row[col]).strip() if col < len(row) and row[col] is not None else ''
            header = headers.get(col)
            if not value or (header and number <= header[0]):
                continue
            if '@' not in value and not (header and header[1] == 'correo'):
                continue
            if header_kind(value) == 'correo':
                continue  # repeated header inside a long exported table
            related = {kind: i for i, (n, kind, _) in headers.items() if kind in {'nombre', 'empresa'} and n < number}
            for item in cell_contacts(value):
                total += 1
                if total > max_contacts:
                    raise ValueError(f'La selección supera {MAX_ROWS:,} entradas. Importa menos archivos por lote.')
                for key, i in related.items():
                    if i < len(row) and row[i] is not None:
                        item[key] = str(row[i])
                item.update(archivo_origen=filename, hoja_origen=sheet,
                            fila_origen=number, celda_origen=f'{column_letter(col)}{number}')
                group['contacts'].append(item)
    return [g for g in columns.values() if g['contacts']]


def scan_files(paths, stop=None, progress=None):
    groups, issues, total = [], [], 0
    seen = set()
    for index, raw_path in enumerate(paths, 1):
        check_stop(stop)
        path = Path(raw_path).resolve()
        if path in seen:
            continue
        seen.add(path)
        if progress:
            progress(f'Leyendo {index}/{len(paths)}: {path.name}')
        before = len(groups)
        try:
            if path.suffix.lower() not in EXTENSIONS:
                raise ValueError('Formato no admitido; usa Excel, CSV o TXT.')
            if path.stat().st_size > 50 * 1024 * 1024:
                raise ValueError('El archivo supera 50 MB. Divídelo antes de importarlo.')
            if path.suffix.lower() in {'.xls', '.xlsx'}:
                with open_excel(path) as workbook:
                    for name in workbook.sheet_names:
                        check_stop(stop)
                        if progress:
                            progress(f'{path.name} · Hoja {name}')
                        sheet = workbook.get_sheet_by_name(name)
                        if sheet.end is None:
                            continue
                        # Calamine iter_rows includes leading empty rows but
                        # trims leading columns. Restore absolute coordinates.
                        start_col = sheet.start[1] if sheet.start else 0
                        factory = lambda sh=sheet, col=start_col: enumerate(([None] * col + row for row in sh.iter_rows()), 1)
                        found = scan_table(factory, path.name, name, stop, MAX_ROWS - total)
                        groups.extend(found)
                        total += sum(len(g['contacts']) for g in found)
            else:
                text, encoding = decode_text(path.read_bytes())
                if path.suffix.lower() == '.txt':
                    factory = lambda: enumerate(([line] for line in text.splitlines()), 1)
                else:
                    try:
                        dialect = csv.Sniffer().sniff(text[:64000], delimiters=',;\t')
                    except csv.Error:
                        dialect = csv.excel
                    factory = lambda: enumerate(csv.reader(io.StringIO(text), dialect), 1)
                found = scan_table(factory, path.name, 'Texto' if path.suffix.lower() == '.txt' else 'CSV', stop, MAX_ROWS - total)
                for group in found:
                    group['codificacion'] = encoding
                groups.extend(found)
                total += sum(len(g['contacts']) for g in found)
            if before == len(groups):
                issues.append(f'{path.name}: no se detectaron columnas con correos. Puedes usar la selección manual para revisar el Excel.')
        except ImportCancelled:
            raise
        except Exception as exc:
            # A file is atomic: never silently import only its first worksheets.
            total -= sum(len(g['contacts']) for g in groups[before:])
            del groups[before:]
            issues.append(f'{path.name}: {exc}')
    return groups, issues
