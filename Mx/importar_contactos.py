"""Importación local, de solo lectura, de Excel y direcciones pegadas."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tempfile

from python_calamine import CalamineWorkbook

from verificar_correos import prepare_lines

EXCEL_EXTENSIONS = {".xlsx", ".xls"}
MAX_ROWS = 1_000_000


def column_letter(index):
    result = ""
    while index >= 0:
        index, digit = divmod(index, 26)
        result = chr(65 + digit) + result
        index -= 1
    return result


def open_excel(path):
    path = Path(path)
    if path.suffix.lower() not in EXCEL_EXTENSIONS:
        raise ValueError("Selecciona un archivo Excel .xlsx o .xls.")
    if path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError("El Excel supera 50 MiB. Crea una copia con solo las columnas de contactos.")
    try:
        return CalamineWorkbook.from_path(path)
    except Exception as exc:
        raise ValueError("No se pudo leer el Excel. Comprueba que no esté cifrado, protegido por contraseña o dañado.") from exc


def read_sheet(workbook, name):
    sheet = workbook.get_sheet_by_name(name)
    if sheet.end is None:
        return []
    last_row, last_column = sheet.end
    if last_row >= MAX_ROWS or last_column >= 1024 or (last_row + 1) * (last_column + 1) > 5_000_000:
        raise ValueError("La hoja es demasiado grande. Usa una copia con solo las columnas y filas de contactos.")
    # No desplazar coordenadas: B3 debe seguir siendo B3 aunque A1 esté vacío.
    return sheet.to_python(skip_empty_area=False)


def cell_text(value):
    return "" if value is None else str(value)


def extract_excel(table, *, first_row=1, has_header=True, email_column=0, name_column=None, company_column=None):
    if type(first_row) is not int or not 1 <= first_row <= len(table):
        raise ValueError("La fila inicial no existe en esta hoja.")
    width = max((len(row) for row in table), default=0)
    columns = [email_column, name_column, company_column]
    if email_column is None or any(type(c) is not int or not 0 <= c < width for c in columns if c is not None):
        raise ValueError("Selecciona una columna de correo válida.")
    contacts = []
    start = first_row if has_header else first_row - 1
    for index in range(start, len(table)):
        row = table[index]
        get = lambda c: cell_text(row[c]) if c is not None and c < len(row) else ""
        email = get(email_column)
        if not email.strip():
            continue
        contacts.append({"correo": email, "nombre": get(name_column), "empresa": get(company_column),
                         "fila_origen": index + 1, "celda_origen": f"{column_letter(email_column)}{index + 1}"})
    return contacts


def split_pasted(text):
    """Separa fuera de comillas; conserva errores en vez de extraer solo coincidencias válidas."""
    if len(text) > 5_000_000:
        raise ValueError("El texto es demasiado grande. Importa la lista desde un archivo.")
    tokens, current = [], []
    quoted, escaped, angle = False, False, False
    for char in text:
        if char in "\r\n" or (char in ",;\t" and not quoted and not angle):
            value = "".join(current).strip()
            if value:
                tokens.append(value)
            current = []
            quoted = escaped = angle = False
            continue
        current.append(char)
        if escaped:
            escaped = False
        elif char == "\\" and quoted:
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted and char in "<>":
            angle = char == "<"
    if "".join(current).strip():
        tokens.append("".join(current).strip())
    if len(tokens) > MAX_ROWS:
        raise ValueError(f"La lista supera {MAX_ROWS:,} entradas.")
    return tokens


def extract_pasted(text):
    result = []
    for number, token in enumerate(split_pasted(text), 1):
        match = re.fullmatch(r"([^<>]*)<([^<>]+)>", token)
        name, email = (match[1].strip().strip('"'), match[2].strip()) if match else ("", token)
        if email.lower().startswith("mailto:"):
            email = email[7:]
        result.append({"correo": email, "nombre": name, "empresa": "", "fila_origen": number, "celda_origen": ""})
    return result


def validate_snapshot(data):
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("origen"), dict):
        raise ValueError("Importación incompatible. Vuelve a importar la lista.")
    if any(not isinstance(k, str) or not isinstance(v, str) for k, v in data["origen"].items()):
        raise ValueError("Metadatos de importación inválidos.")
    contacts = data.get("contactos")
    if not isinstance(contacts, list) or not 1 <= len(contacts) <= MAX_ROWS:
        raise ValueError("No hay contactos o se supera el límite de importación.")
    for contact in contacts:
        if (not isinstance(contact, dict)
            or any(not isinstance(contact.get(k), str) for k in ("correo", "nombre", "empresa", "celda_origen"))
            or type(contact.get("fila_origen")) is not int or contact["fila_origen"] < 1):
            raise ValueError("Una fila de la importación es incompatible.")
        if any(key in contact and not isinstance(contact[key], str) for key in ("archivo_origen", "hoja_origen")):
            raise ValueError("El origen de una fila es incompatible.")
    return contacts


def save_import(contacts, source, data_dir):
    data = {"version": 1, "origen": source, "contactos": contacts,
            "fecha_utc": datetime.now(timezone.utc).isoformat()}
    validate_snapshot(data)
    folder = Path(data_dir) / "importaciones"
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=folder, prefix="lista_", suffix=".mxlista", delete=False) as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        return Path(stream.name)


def load_import(path, stop_event=None, on_progress=None):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    contacts = validate_snapshot(data)
    rows = prepare_lines((contact["correo"] for contact in contacts), stop_event=stop_event, on_progress=on_progress)
    for row in rows:
        contact = contacts[row["linea"] - 1]
        row.update(nombre=contact["nombre"], empresa=contact["empresa"],
                   fila_origen=contact["fila_origen"], celda_origen=contact["celda_origen"],
                   origen={**data["origen"], **({"archivo": contact["archivo_origen"], "hoja": contact.get("hoja_origen", "")}
                           if contact.get("archivo_origen") else {})})
    return rows
