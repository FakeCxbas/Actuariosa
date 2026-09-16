"""Reproducible portable Windows bundle. Requires PyInstaller 6.21.0."""
import subprocess
import sys
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--windowed', '--onedir',
    '--name', 'NexoInventario', '--add-data', f'{root / "static"};static',
    '--distpath', str(root / 'dist'), '--workpath', str(root / 'build'),
    str(root / 'desktop.py')], cwd=root, check=True)
folder = root / 'dist' / 'NexoInventario'
(folder / 'LEEME.txt').write_text((root / 'LEEME_WINDOWS.txt').read_text(encoding='utf-8'), encoding='utf-8')
with zipfile.ZipFile(root / 'dist' / 'NexoInventario-Windows-0.1.0.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for file in folder.rglob('*'):
        if file.is_file():
            archive.write(file, file.relative_to(folder.parent))
print('Paquete creado:', root / 'dist' / 'NexoInventario-Windows-0.1.0.zip')
