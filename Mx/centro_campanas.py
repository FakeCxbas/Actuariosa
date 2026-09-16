"""Puentes entre las revisiones, las listas importadas y las campañas locales."""
import json
from pathlib import Path

from importar_contactos import save_import, load_import


def import_report(path, data_dir, stop_event=None):
    path = Path(path)
    report = json.loads(path.read_text(encoding='utf-8-sig'))
    entries = report.get('correos', report.get('resultados'))
    if not isinstance(entries, list) or not entries:
        raise ValueError('Elige Detalle.json o informe.json de una revisión de correos.')
    contacts = []
    for row in entries:
        if stop_event is not None and stop_event.is_set():
            raise ValueError('Importación cancelada.')
        if not isinstance(row, dict) or not isinstance(row.get('original'), str):
            raise ValueError('El informe contiene entradas no reconocidas.')
        contacts.append({'correo': row.get('normalizado') or row['original'],
                         'nombre': row.get('nombre', ''), 'empresa': row.get('empresa', ''),
                         'fila_origen': len(contacts) + 1, 'celda_origen': '',
                         'archivo_origen': str(path)})
    saved = save_import(contacts, {'tipo': 'informe previo', 'archivo': str(path)}, Path(data_dir))
    rows = load_import(saved, stop_event)
    # El estado histórico sirve para visualizar; el motor consulta DNS otra vez al enviar.
    for current in rows:
        previous = entries[current['linea'] - 1]
        if current.get('estado') != 'INVALIDO' and previous.get('estado') in {'APTO_DNS', 'INVALIDO', 'REVISAR'}:
            for key in ('estado', 'codigo', 'motivo', 'mx', 'tipo'):
                if key in previous:
                    current[key] = previous[key]
    return saved, rows, f'Revisión anterior: {path.parent.name}'


OFFER_TEMPLATE = '''Hola ${nombre},

Soy [TU NOMBRE], de [NOMBRE DE LA EMPRESA].

Ofrecemos [SERVICIO] para ayudar a [TIPO DE CLIENTE] con [NECESIDAD CONCRETA].

[EXPLICA EN UNA O DOS FRASES QUÉ INCLUYE EL SERVICIO, SIN PROMESAS NO COMPROBADAS].

Si es de su interés, puede responder a este correo y coordinamos una conversación.

Saludos,
[TU NOMBRE Y CARGO]
[EMPRESA · TELÉFONO · DIRECCIÓN]
'''
