"""Lectura y escritura de resultados intermedios, sin sobrescribir archivos."""
from datetime import datetime, timezone
import json
from pathlib import Path


def check_output(path):
    if path.exists():
        raise FileExistsError(f"Ya existe {path}. Elige otro nombre con --salida; no se sobrescribirá.")


def save_stage(path, stage, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"version": 1, "etapa": stage,
            "fecha_utc": datetime.now(timezone.utc).isoformat(), "resultados": rows}
    content = json.dumps(data, ensure_ascii=False, indent=2)
    # Modo exclusivo: protege también si otro proceso crea el archivo mientras tanto.
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)


def load_stage(path, expected_stage):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("etapa") != expected_stage:
        raise ValueError(f"Se necesita un JSON de la etapa '{expected_stage}', versión 1.")
    if not isinstance(data.get("fecha_utc"), str):
        raise ValueError("Falta la fecha de ejecución de la etapa.")
    if datetime.fromisoformat(data["fecha_utc"]).tzinfo is None:
        raise ValueError("La fecha de la etapa debe incluir zona horaria.")
    rows = data.get("resultados")
    if not isinstance(rows, list) or not rows:
        raise ValueError("El JSON no contiene resultados válidos.")
    string_fields = ("original", "normalizado", "dominio", "buzon", "catch_all", "estado", "codigo", "motivo")
    valid_states = {"", "INVALIDO", "REVISAR"} if expected_stage == "limpieza" else {"APTO_DNS", "INVALIDO", "REVISAR"}
    previous_line = 0
    lines_seen = set()
    for row in rows:
        if (not isinstance(row, dict)
                or any(not isinstance(row.get(key), str) for key in string_fields)
                or type(row.get("linea")) is not int or row["linea"] <= previous_line
                or type(row.get("requiere_smtputf8")) is not bool
                or not isinstance(row.get("mx"), list)
                or any(not isinstance(host, str) for host in row["mx"])
                or row["estado"] not in valid_states
                or (not row["estado"] and not row["dominio"])
                or "duplicado_de_linea" not in row):
            raise ValueError("El JSON contiene una fila incompleta o incompatible; vuelve a generar la etapa anterior.")
        duplicate = row["duplicado_de_linea"]
        if duplicate is not None and (type(duplicate) is not int or duplicate not in lines_seen):
            raise ValueError("Referencia de duplicado inválida.")
        previous_line = row["linea"]
        lines_seen.add(previous_line)
    return data
