"""Etiquetas, filtros y exportación del resultado visible, sin consultas de red."""
import csv
from pathlib import Path
import tempfile

LABELS = {'APTO_DNS': 'Dominio apto', 'INVALIDO': 'Con problemas', 'REVISAR': 'Por revisar', '': 'Sin revisar'}
FILTERS = ('Todos', 'Dominio apto', 'Con problemas', 'Por revisar', 'Sin revisar', 'Duplicados')


def matches(row, category='Todos', search=''):
    if category == 'Duplicados':
        valid = row.get('duplicado_de_linea') is not None
    else:
        valid = category == 'Todos' or LABELS.get(row.get('estado', ''), 'Por revisar') == category
    origin = row.get('origen', {})
    haystack = ' '.join(str(row.get(k, '')) for k in ('original', 'normalizado', 'motivo')) + ' ' + str(origin.get('archivo', ''))
    return valid and search.casefold() in haystack.casefold()


def export_lists(rows, destination):
    """Four one-column lists; unresolved rows never enter the problem list."""
    if not rows:
        raise ValueError('Primero importa o revisa una lista.')
    folder = Path(tempfile.mkdtemp(prefix='Listas ', dir=destination))
    specs = [('Todos los correos', 'Todos'), ('Correos con dominio apto', 'Dominio apto'),
             ('Correos con problemas', 'Con problemas'), ('Correos por revisar', 'Pendientes')]
    counts = {}
    for name, category in specs:
        seen, count = set(), 0
        with (folder / (name + '.csv')).open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.writer(stream)
            for row in rows:
                chosen = category == 'Todos' or (category == 'Pendientes' and row.get('estado', '') in {'', 'REVISAR'}) or matches(row, category)
                if not chosen:
                    continue
                value = row.get('normalizado') or row['original'].strip()
                if value in seen:
                    continue
                seen.add(value)
                # CSV cannot carry Excel text types. Prefix risky literals so
                # opening an invalid source value cannot execute a formula.
                writer.writerow(["'" + value if value.startswith(('=', '+', '-', '@', '\t', '\r')) else value])
                count += 1
        counts[name] = count
    (folder / 'Leer primero.txt').write_text(
        'CSV de una columna, sin encabezado, sin repeticiones exactas de dirección normalizada.\n'
        'Dominio apto no confirma que exista el buzón. Con problemas refleja formato o DNS, no rebotes observados.\n'
        'Por revisar incluye consultas inconclusas y entradas sin revisar. No se han enviado correos al exportar.\n'
        'Las entradas que empiezan por =, +, -, @ u otros prefijos de fórmula llevan un apóstrofo de protección para Excel.\n'
        + '\n'.join(f'{name}: {count}' for name, count in counts.items()), encoding='utf-8-sig')
    return folder, counts
