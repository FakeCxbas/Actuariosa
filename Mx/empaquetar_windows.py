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
    
    icon_path = root / "mxcorreo.ico"
    if not icon_path.exists():
        # Generar icono si no existe
        from generar_icono import generate_ico
        generate_ico(icon_path)

    command = [
        sys.executable, "-m", "PyInstaller",
        "--onedir", "--windowed", "--noupx",
        "--name", "MxCorreo",
        "--distpath", str(output),
        "--workpath", str(root / "build" / stamp),
        "--specpath", str(root / "build" / stamp),
        "--icon", str(icon_path),
        "--collect-submodules", "dns",
        "--collect-all", "python_calamine",
        "--copy-metadata", "email-validator",
        "--copy-metadata", "python-calamine"
    ]
    
    data_files = [
        "campana.ejemplo.json",
        "mensaje.ejemplo.txt",
        "ejemplo.txt",
        "GUIA_CAMPANA.md",
        "LEEME_WINDOWS.txt",
        "Guía de campañas.txt",
        "mxcorreo.ico"
    ]
    for filename in data_files:
        src = root / filename
        if src.exists():
            command.extend(["--add-data", f"{src}:."])
            
    command.append(str(root / "mxcorreo_app.py"))
    
    print("Iniciando compilación con PyInstaller...")
    subprocess.run(command, cwd=root, check=True)
    
    app_folder = output / "MxCorreo"
    for filename in ("LEEME_WINDOWS.txt", "GUIA_CAMPANA.md", "Guía de campañas.txt", "mxcorreo.ico"):
        src = root / filename
        if src.exists():
            shutil.copy2(src, app_folder / filename)
            
    # Crear lanzador rápido .bat dentro de la carpeta
    launcher = app_folder / "Iniciar_MxCorreo.bat"
    launcher.write_text('@echo off\r\nstart "" "%~dp0MxCorreo.exe"\r\n', encoding="ansi")

    # Crear lanzador rápido .bat en la raíz de output
    root_launcher = output / "Iniciar_MxCorreo.bat"
    root_launcher.write_text('@echo off\r\nstart "" "%~dp0MxCorreo\\MxCorreo.exe"\r\n', encoding="ansi")

    archive = shutil.make_archive(str(output), "zip", root_dir=output)
    print("==================================================================")
    print("COMPILACIÓN EXITOSA")
    print("CARPETA DE LA APP:", app_folder)
    print("EJECUTABLE:", app_folder / "MxCorreo.exe")
    print("ARCHIVO ZIP:", archive)
    print("==================================================================")


if __name__ == "__main__":
    main()
