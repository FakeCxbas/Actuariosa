#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add Mx directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mxcorreo_server import cmd_verificar_actualizacion, cmd_aplicar_actualizacion

results = []

def dummy_send_result(req_id, data):
    results.append(("result", req_id, data))

def dummy_send_error(req_id, err):
    results.append(("error", req_id, err))

# Override _send_result and _send_error for testing
import mxcorreo_server
mxcorreo_server._send_result = dummy_send_result
mxcorreo_server._send_error = dummy_send_error

print("1. Probando cmd_verificar_actualizacion:")
cmd_verificar_actualizacion({"url": "http://localhost:3000/api/updates"}, 101)
print("Resultado:", results)

assert len(results) == 1, "Debe haber 1 resultado"
res_type, req_id, data = results[0]
assert res_type == "result", f"Esperado result, obtenido: {res_type}"
print(f"✅ Éxito: outdated={data.get('outdated')}, latest_version={data.get('latest_version')}, current_version={data.get('current_version')}")

print("\n2. Probando cmd_aplicar_actualizacion:")
results.clear()
cmd_aplicar_actualizacion({"target_version": "2.1.0"}, 102)
res_type, req_id, data = results[0]
assert res_type == "result"
assert data.get("ok") is True
assert data.get("version") == "2.1.0"
print(f"✅ Éxito aplicación de versión: {data}")

# Restaurar version.json a 2.0.0 para que el usuario pueda ver la app como desactualizada
ver_file = Path(__file__).parent.parent / "version.json"
ver_data = json.loads(ver_file.read_text(encoding="utf-8"))
ver_data["version"] = "2.0.0"
ver_file.write_text(json.dumps(ver_data, indent=2, ensure_ascii=False), encoding="utf-8")
print("\n✅ version.json restaurado a 2.0.0 para prueba en vivo de desactualizada.")
