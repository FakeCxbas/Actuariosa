"""Construcción reproducible: solo incluye código y ejemplos públicos, nunca datos de la empresa."""
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parent
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = root / "entrega" / ("MxCorreo_Windows_x64_" + stamp)
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-m", "PyInstaller", "--onedir", "--windowed", "--noupx",
               "--name", "MxCorreo", "--distpath", str(output),
               "--workpath", str(root / "build" / stamp), "--specpath", str(root / "build" / stamp),
               "--collect-submodules", "dns", "--collect-all", "python_calamine",
               "--copy-metadata", "email-validator", "--copy-metadata", "python-calamine"]
    for filename in ("campana.ejemplo.json", "mensaje.ejemplo.txt", "ejemplo.txt", "GUIA_CAMPANA.md", "LEEME_WINDOWS.txt", "Guía de campañas.txt"):
        command.extend(["--add-data", str(root / filename) + ":."])
    command.append(str(root / "mxcorreo_app.py"))
    subprocess.run(command, cwd=root, check=True)
    app_folder = output / "MxCorreo"
    for filename in ("LEEME_WINDOWS.txt", "GUIA_CAMPANA.md", "Guía de campañas.txt"):
        shutil.copy2(root / filename, app_folder / filename)
    archive = shutil.make_archive(str(output), "zip", root_dir=output)
    print("CARPETA:", app_folder)
    print("ZIP:", archive)


if __name__ == "__main__":
    main()
