"""Build a source-only transfer archive and a separate consistent local backup."""
import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path

from inventory import Inventory

root = Path(__file__).resolve().parent
out = root / 'entrega-linux'
out.mkdir(exist_ok=True)
sources = [root / name for name in (
    '.gitignore', 'inventory.py', 'server.py', 'desktop.py', 'build_windows.py',
    'README.md', 'VERIFICACION.md', 'LEEME_WINDOWS.txt', 'iniciar-linux.sh',
    'EMPEZAR_EN_LINUX.md', 'PARA_EL_AGENTE_LINUX.md',
)]
sources += sorted(p for p in (root / 'static').iterdir() if p.is_file())
sources += sorted((root / 'tests').glob('*.py'))
archive = out / 'Nexo-para-Linux.zip'
manifest = {}
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
    for source in sources:
        content = source.read_bytes()
        if source.suffix == '.sh':
            content = content.replace(b'\r\n', b'\n')
        relative = source.relative_to(root).as_posix()
        manifest[relative] = hashlib.sha256(content).hexdigest()
        bundle.writestr('nexo-desde-windows/' + relative, content)
    bundle.writestr('nexo-desde-windows/MANIFEST_SHA256.json', json.dumps(manifest, indent=2))
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    for relative, digest in manifest.items():
        assert hashlib.sha256(bundle.read('nexo-desde-windows/' + relative)).hexdigest() == digest
    assert not any(name.endswith(('.sqlite3', '.db', '.env', '.exe')) for name in bundle.namelist())

database = root / 'data' / 'nexo.sqlite3'
if database.is_file():
    backup = out / 'nexo-datos-windows.sqlite3'
    Inventory(database).backup(backup)
    conn = sqlite3.connect(backup)
    try:
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    finally:
        conn.close()
    print('Respaldo SQLite verificado:', backup)

for name in ('EMPEZAR_EN_LINUX.md', 'PARA_EL_AGENTE_LINUX.md'):
    (out / name).write_bytes((root / name).read_bytes())
(out / 'SHA256.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n', encoding='utf-8')
print('ZIP verificado:', archive)
print('Archivos de código/documentación:', len(manifest))
print('Tamaño:', archive.stat().st_size, 'bytes')
