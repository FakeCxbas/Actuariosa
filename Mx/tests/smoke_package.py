"""Prueba del ejecutable empaquetado: importa una lista local, sin DNS ni SMTP."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from importar_contactos import save_import


def main(executable):
    with TemporaryDirectory(prefix='mxcorreo-smoke-') as tmp:
        folder = Path(tmp)
        source = save_import([{'correo': 'smoke@example.com', 'nombre': 'Prueba',
                               'empresa': '', 'fila_origen': 1, 'celda_origen': ''}],
                             {'archivo': 'Prueba local'}, folder)
        session = folder / 'sesion.json'
        session.write_text(json.dumps({'lista': str(source)}), encoding='utf-8')
        process = subprocess.Popen([str(Path(executable).resolve()), '--datos', str(folder)])
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f'El ejecutable se cerró: {process.returncode}')
                data = json.loads(session.read_text(encoding='utf-8'))
                if data.get('audiencia') == 'Solo autorizados':
                    print('OK: ejecutable inició Tk, importó la lista y procesó sus eventos. Sin DNS ni SMTP.')
                    return
                time.sleep(0.2)
            raise RuntimeError('La importación de arranque no finalizó en 30 segundos.')
        finally:
            # Solo el proceso de prueba creado aquí; no toca otras instancias.
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    main(sys.argv[1])
