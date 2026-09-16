"""
Lector y Normalizador de Censos de Empleados
Soporta:
1. Plantillas oficiales Excel de Actuariosa ('FORMA CONFIG' / 'FORMATO DE INFORMACION ACTUARIAL').
2. Hojas de cálculo Excel personalizadas (.xlsx / .xls).
3. Archivos CSV UTF-8 o Windows-1252.
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any

from motor_actuarial import EmpleadoCenso

try:
    from python_calamine import CalamineWorkbook
    HAS_CALAMINE = True
except ImportError:
    HAS_CALAMINE = False


def normalizar_fecha(valor: Any) -> date | None:
    if isinstance(valor, (date, datetime)):
        return valor if isinstance(valor, date) and not isinstance(valor, datetime) else valor.date()
    if not valor:
        return None
    
    texto = str(valor).strip()
    # Si viene como flotante de días o timestamp
    if re.match(r"^\d{4,5}$", texto):
        try:
            # Días desde 1899-12-30 (convención Excel)
            from datetime import timedelta
            return date(1899, 12, 30) + timedelta(days=int(texto))
        except Exception:
            pass

    # Formatos comunes: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
    formatos = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
        "%Y/%m/%d", "%d.%m.%Y", "%m/%d/%Y"
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(texto[:10], fmt).date()
        except ValueError:
            continue
    return None


def parsear_numero(valor: Any, default: float = 0.0) -> float:
    if valor is None:
        return default
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("$", "").replace("USD", "").strip()
    if not texto:
        return default
    # Manejar formatos 1.234,56 o 1,234.56
    if "," in texto and "." in texto:
        if texto.find(",") > texto.find("."):
            # Formato latino: 1.234,56
            texto = texto.replace(".", "").replace(",", ".")
        else:
            # Formato anglo: 1,234.56
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return default


def cargar_censo_csv(ruta: Path) -> list[EmpleadoCenso]:
    lineas = ruta.read_text(encoding="utf-8-sig").splitlines()
    if not lineas:
        raise ValueError(f"El archivo {ruta.name} está vacío.")
    
    delimitador = ";" if ";" in lineas[0] else ("," if "," in lineas[0] else "\t")
    lector = csv.DictReader(lineas, delimiter=delimitador)
    
    # Mapeo flexible de columnas
    empleados: list[EmpleadoCenso] = []
    for fila in lector:
        normalizado = {k.strip().lower(): (v.strip() if v else "") for k, v in fila.items() if k}
        
        cedula = (
            normalizado.get("cedula")
            or normalizado.get("no. cedula")
            or normalizado.get("identificacion")
            or normalizado.get("id")
            or ""
        )
        nombre = (
            normalizado.get("nombre")
            or normalizado.get("nombres")
            or normalizado.get("empleado")
            or normalizado.get("trabajador")
            or "Empleado"
        )
        sexo = normalizado.get("sexo") or normalizado.get("genero") or "M"
        sexo = "F" if sexo.upper().startswith("F") or sexo.upper().startswith("M") and "UJER" in sexo.upper() else "M"

        f_nac = normalizar_fecha(normalizado.get("fecha_nacimiento") or normalizado.get("fecha de nacimiento") or normalizado.get("nacimiento"))
        f_ing = normalizar_fecha(normalizado.get("fecha_ingreso") or normalizado.get("fecha de entrada") or normalizado.get("ingreso"))

        sueldo = parsear_numero(normalizado.get("sueldo") or normalizado.get("sueldo_mensual") or normalizado.get("total") or normalizado.get("remuneracion"))
        res_jub = parsear_numero(normalizado.get("reserva_jubilacion") or normalizado.get("reserva_anterior_jubilacion"))
        res_des = parsear_numero(normalizado.get("reserva_desahucio") or normalizado.get("reserva_anterior_desahucio"))

        if f_nac and f_ing and sueldo > 0:
            empleados.append(
                EmpleadoCenso(
                    cedula=cedula,
                    nombre=nombre,
                    sexo=sexo,
                    fecha_nacimiento=f_nac,
                    fecha_ingreso=f_ing,
                    sueldo_mensual=sueldo,
                    reserva_anterior_jubilacion=res_jub,
                    reserva_anterior_desahucio=res_des,
                )
            )
    return empleados


def cargar_censo_excel(ruta: Path) -> tuple[str, list[EmpleadoCenso]]:
    if not HAS_CALAMINE:
        raise RuntimeError("Se requiere 'python-calamine' para leer archivos Excel.")
    
    wb = CalamineWorkbook.from_path(ruta)
    hoja_nombre = wb.sheet_names[0]
    filas = wb.get_sheet_by_name(hoja_nombre).to_python()

    nombre_empresa = "Empresa Evaluada"
    fila_encabezados = -1

    # Detectar encabezados y nombre de empresa en plantilla 'FORMA CONFIG'
    for i, fila in enumerate(filas[:25]):
        textos = [str(c).strip() for c in fila if c is not None]
        linea_completa = " ".join(textos).upper()
        if "NOMBRE DE LA EMPRESA" in linea_completa or "EMPRESA:" in linea_completa:
            partes = linea_completa.split("EMPRESA")
            if len(partes) > 1 and ":" in partes[1]:
                posible_nombre = partes[1].replace(":", "").strip()
                if posible_nombre:
                    nombre_empresa = posible_nombre
        if any("CÉDULA" in t.upper() or "CEDULA" in t.upper() or "NOMBRES" in t.upper() for t in textos):
            fila_encabezados = i
            break

    if fila_encabezados == -1:
        # Fallback a fila 0 o 10
        fila_encabezados = 10 if len(filas) > 10 else 0

    cabeceras = [str(c).strip().upper() if c is not None else "" for c in filas[fila_encabezados]]

    # Localizar índices de columnas
    idx_cedula = next((i for i, c in enumerate(cabeceras) if "CÉDULA" in c or "CEDULA" in c or "IDENT" in c), 1)
    idx_nombre = next((i for i, c in enumerate(cabeceras) if "NOMBRE" in c), 2)
    idx_sexo = next((i for i, c in enumerate(cabeceras) if "SEXO" in c or "GÉNERO" in c or "GENERO" in c), 3)
    idx_nacimiento = next((i for i, c in enumerate(cabeceras) if "NACIMIENTO" in c), 4)
    idx_ingreso = next((i for i, c in enumerate(cabeceras) if "ENTRADA" in c or "INGRESO" in c), 5)
    
    # Localizar columna SUELDO y columna TOTAL
    idx_sueldo = next((i for i, c in enumerate(cabeceras) if "SUELDO" in c or "REMUNERAC" in c), 8)
    idx_total = next((i for i, c in enumerate(cabeceras) if c == "TOTAL" or "TOTAL REMUNER" in c), None)

    idx_res_jub = next((i for i, c in enumerate(cabeceras) if "JUBILACI" in c and "RESERVA" in c), 11)
    idx_res_des = next((i for i, c in enumerate(cabeceras) if "DESAHUCIO" in c and "RESERVA" in c), 12)

    empleados: list[EmpleadoCenso] = []
    for fila in filas[fila_encabezados + 1:]:
        if not any(c is not None for c in fila):
            continue
        
        cedula = str(fila[idx_cedula]).strip() if idx_cedula < len(fila) and fila[idx_cedula] is not None else ""
        nombre = str(fila[idx_nombre]).strip() if idx_nombre < len(fila) and fila[idx_nombre] is not None else ""
        if not nombre or nombre.upper() in {"TOTAL", "SUMA", "PROMEDIO"}:
            continue

        raw_sexo = str(fila[idx_sexo]).strip().upper() if idx_sexo < len(fila) and fila[idx_sexo] is not None else "M"
        sexo = "F" if raw_sexo.startswith("F") or "MUJER" in raw_sexo else "M"

        f_nac = normalizar_fecha(fila[idx_nacimiento]) if idx_nacimiento < len(fila) else None
        f_ing = normalizar_fecha(fila[idx_ingreso]) if idx_ingreso < len(fila) else None

        # Priorizar TOTAL si tiene valor, si no usar SUELDO
        sueldo = 0.0
        if idx_total is not None and idx_total < len(fila):
            sueldo = parsear_numero(fila[idx_total])
        if sueldo <= 0 and idx_sueldo < len(fila):
            sueldo = parsear_numero(fila[idx_sueldo])
        res_jub = parsear_numero(fila[idx_res_jub]) if idx_res_jub < len(fila) else 0.0
        res_des = parsear_numero(fila[idx_res_des]) if idx_res_des < len(fila) else 0.0

        if f_nac and f_ing and sueldo > 0:
            empleados.append(
                EmpleadoCenso(
                    cedula=cedula,
                    nombre=nombre,
                    sexo=sexo,
                    fecha_nacimiento=f_nac,
                    fecha_ingreso=f_ing,
                    sueldo_mensual=sueldo,
                    reserva_anterior_jubilacion=res_jub,
                    reserva_anterior_desahucio=res_des,
                )
            )

    return nombre_empresa, empleados


def cargar_censo(ruta_archivo: str | Path) -> tuple[str, list[EmpleadoCenso]]:
    path = Path(ruta_archivo)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo {path}")
    
    if path.suffix.lower() in {".xlsx", ".xls", ".xlsb"}:
        return cargar_censo_excel(path)
    elif path.suffix.lower() in {".csv", ".txt"}:
        empleados = cargar_censo_csv(path)
        nombre = path.stem.replace("_", " ").title()
        return nombre, empleados
    else:
        raise ValueError(f"Formato no admitido: {path.suffix}. Usa Excel (.xlsx) o CSV.")
