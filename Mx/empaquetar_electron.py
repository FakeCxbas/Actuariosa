"""
empaquetar_electron.py — Script de empaquetado de MxCorreo con Electron.

Uso:
  python empaquetar_electron.py

Genera en Mx/entrega/:
  - MxCorreo Setup.exe  (instalador NSIS)
  - MxCorreo.exe        (portable, sin instalación)
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ELECTRON_DIR = HERE / "electron"


def run(cmd, cwd=None):
    print(f"\n>>> {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd or HERE, check=True, text=True)
    return result


def main():
    print("=" * 60)
    print("  MxCorreo — Empaquetado con Electron")
    print("=" * 60)

    # 1. Verificar Node.js
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        subprocess.run(["cmd", "/c", "npm --version"], capture_output=True, check=True)
    except Exception:
        print("[ERROR] Node.js o npm no encontrados. Instala Node.js desde https://nodejs.org")
        sys.exit(1)

    # 2. Instalar dependencias de Electron (por si acaso)
    print("\n[1/3] Instalando dependencias npm…")
    run(["cmd", "/c", "npm install"], cwd=ELECTRON_DIR)

    # 3. Empaquetar con electron-builder
    print("\n[2/3] Generando ejecutable Windows…")
    run(["cmd", "/c", "npm run build:win"], cwd=ELECTRON_DIR)

    # 4. Confirmar resultados
    entrega = HERE / "entrega"
    exes = list(entrega.glob("**/*.exe"))
    print("\n[3/3] Ejecutables generados:")
    for exe in exes:
        size_mb = exe.stat().st_size / 1_000_000
        print(f"  ✅  {exe.name}  ({size_mb:.1f} MB)")
        print(f"       → {exe}")

    print("\n" + "=" * 60)
    print("  ¡Empaquetado completado!")
    print("=" * 60)


if __name__ == "__main__":
    main()
