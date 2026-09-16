"""Abre resultados con la aplicación predeterminada del escritorio."""
import os
from pathlib import Path
import subprocess
import sys


def open_local_path(path):
    target = str(Path(path).resolve())
    if sys.platform == 'win32':
        os.startfile(target)
    else:
        command = 'open' if sys.platform == 'darwin' else 'xdg-open'
        subprocess.run([command, target], check=True, timeout=15,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
