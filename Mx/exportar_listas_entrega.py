"""Exporta las tres listas solicitadas desde el análisis guardado; no consulta DNS ni envía."""
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile
from collections import Counter

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / 'resultados/revision_lista_20260901/detalle.json').read_text(encoding='utf-8'))
summary = data['resumen']
rows = data['correos']
source = Path(summary['archivo'])
assert hashlib.sha256(source.read_bytes()).hexdigest() == summary['sha256']
assert Counter(row['estado'] for row in rows) == summary['estados']
all_entries = []
with zipfile.ZipFile(source) as archive:
    for entry in archive.infolist():
        assert entry.filename.lower().endswith('.csv')
        for record in csv.reader(io.StringIO(archive.read(entry).decode('utf-8-sig'))):
            assert len(record) <= 1
            if record and record[0].strip():
                all_entries.append(record[0].strip())
assert len(all_entries) == summary['entradas'] == 36040
assert Counter(all_entries) == Counter(item['original'].strip() for row in rows for item in row['apariciones'])

exports = {
    'Correos con dominio apto.txt': [row['normalizado'] or row['original'].strip() for row in rows if row['estado'] == 'APTO_DNS'],
    'Todos los correos recibidos.txt': all_entries,
    'Correos con problemas de dominio.txt': [row['normalizado'] or row['original'].strip() for row in rows if row['estado'] == 'INVALIDO'],
}
assert len(exports['Correos con dominio apto.txt']) == 22973
assert len(exports['Correos con problemas de dominio.txt']) == 1205
assert len(set(exports['Correos con dominio apto.txt'])) == 22973
assert len(set(exports['Correos con problemas de dominio.txt'])) == 1205
assert not set(exports['Correos con dominio apto.txt']) & set(exports['Correos con problemas de dominio.txt'])
target = ROOT / 'output/listas'
target.mkdir(parents=True, exist_ok=True)
for name, values in exports.items():
    assert all(value and '\n' not in value and '\r' not in value for value in values)
    path = target / name
    with path.open('x', encoding='utf-8', newline='') as stream:
        stream.write('\r\n'.join(values) + '\r\n')
    assert path.read_text(encoding='utf-8').splitlines() == values
    print(f'{name}: {len(values)} entradas')
print('Pendientes: 426; incluidos únicamente en la lista completa.')
print('Resultados DNS del análisis del 1 de septiembre de 2026.')
