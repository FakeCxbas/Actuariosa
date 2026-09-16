"""Reúne, depura y revisa por DNS una carpeta de Excel/CSV/TXT. Nunca usa SMTP."""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import tempfile

import dns.resolver

from analizar_lista_zip import classify
from importacion_automatica import EXTENSIONS, scan_files
from verificar_correos import DNSChecker, prepare_lines


def write_json_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        temporary = Path(stream.name)
    temporary.replace(path)


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_csv_value(value):
    return "'" + value if value.startswith(('=', '+', '-', '@', '\t', '\r')) else value


def collect(folder):
    paths = sorted(p for p in Path(folder).rglob('*') if p.is_file() and p.suffix.lower() in EXTENSIONS
                   and not p.name.startswith(('~$', '._')))
    groups, issues = scan_files(paths, progress=print)
    contacts = [contact for group in groups for contact in group['contacts']]
    raw = {}
    for contact in contacts:
        value = contact['correo'].strip()
        if not value:
            continue
        item = raw.setdefault(value, {'count': 0, 'sources': Counter(), 'samples': []})
        item['count'] += 1
        location = f"{contact['archivo_origen']} / {contact['hoja_origen']} / {contact['celda_origen']}"
        item['sources'][contact['archivo_origen']] += 1
        if len(item['samples']) < 5:
            item['samples'].append(location)
    print(f'Archivos: {len(paths)} · columnas: {len(groups)} · apariciones: {len(contacts):,} · textos distintos: {len(raw):,}', flush=True)
    prepared = prepare_lines(raw)
    unique = {}
    for row in prepared:
        source = raw[row['original']]
        key = row['normalizado'] or row['original'].strip()
        if key not in unique:
            unique[key] = {**row, 'apariciones': 0, 'archivos': Counter(), 'muestras_origen': []}
        target = unique[key]
        target['apariciones'] += source['count']
        target['archivos'].update(source['sources'])
        for sample in source['samples']:
            if len(target['muestras_origen']) < 5 and sample not in target['muestras_origen']:
                target['muestras_origen'].append(sample)
    rows = list(unique.values())
    for row in rows:
        row['archivos'] = dict(row['archivos'])
        row['tipo'], row['criterio_tipo'], row['sugerencia_revisar'] = classify(row['dominio'])
    sources = [{'archivo': str(path), 'sha256': file_hash(path), 'tamaño': path.stat().st_size} for path in paths]
    return rows, issues, sources, len(contacts), len(groups)


def load_dns(path):
    results = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            item = json.loads(line)
            domain = item.pop('dominio')
            results[domain] = item
    return results


def check_domains(rows, path, workers=24, timeout=3, retries=1):
    cached = load_dns(path)
    domains = sorted({row['dominio'] for row in rows if row['dominio'] and not row['estado']} - set(cached))
    resolver = dns.resolver.Resolver()
    resolver.cache = dns.resolver.Cache()
    checker = DNSChecker(timeout=timeout, retries=retries, resolver=resolver)
    print(f'Dominios pendientes de DNS: {len(domains):,} · ya guardados: {len(cached):,}', flush=True)
    with path.open('a', encoding='utf-8') as stream, ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(checker.check, domain): domain for domain in domains}
        for number, future in enumerate(as_completed(futures), 1):
            domain = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {'estado': 'REVISAR', 'codigo': 'ERROR_CONSULTA', 'motivo': type(exc).__name__, 'mx': []}
            result['fecha_utc'] = datetime.now(timezone.utc).isoformat()
            cached[domain] = result
            stream.write(json.dumps({'dominio': domain, **result}, ensure_ascii=False) + '\n')
            stream.flush()
            if number % 100 == 0 or number == len(domains):
                print(f'DNS {number:,}/{len(domains):,}', flush=True)
    for row in rows:
        if not row['estado']:
            row.update(cached[row['dominio']])
    return len(cached)


def recheck_negative_domains(rows, path, workers=24):
    """Require two negative observations before retaining a DNS invalid result."""
    cached = load_dns(path)
    first = {row['dominio']: {'estado': row['estado'], 'codigo': row['codigo'],
                              'motivo': row['motivo'], 'mx': row['mx']}
             for row in rows if row['dominio'] and row['estado'] == 'INVALIDO'}
    domains = sorted(set(first) - set(cached))
    resolver = dns.resolver.Resolver()
    resolver.cache = dns.resolver.Cache()
    checker = DNSChecker(timeout=4, retries=1, resolver=resolver)
    print(f'Dominios negativos para segunda consulta: {len(domains):,} · ya guardados: {len(cached):,}', flush=True)
    with path.open('a', encoding='utf-8') as stream, ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(checker.check, domain): domain for domain in domains}
        for number, future in enumerate(as_completed(futures), 1):
            domain = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {'estado': 'REVISAR', 'codigo': 'ERROR_CONSULTA', 'motivo': type(exc).__name__, 'mx': []}
            result['fecha_utc'] = datetime.now(timezone.utc).isoformat()
            cached[domain] = result
            stream.write(json.dumps({'dominio': domain, **result}, ensure_ascii=False) + '\n')
            stream.flush()
            if number % 100 == 0 or number == len(domains):
                print(f'Segunda consulta {number:,}/{len(domains):,}', flush=True)
    disagreements = 0
    for row in rows:
        domain = row['dominio']
        if domain not in first:
            continue
        latest = cached[domain]
        row['primera_consulta'] = first[domain]
        row['segunda_consulta'] = latest
        if latest['estado'] != 'INVALIDO':
            disagreements += 1
            row.update(estado='REVISAR', codigo='DNS_DISCREPANTE',
                       motivo=f"Las dos consultas no coinciden: {first[domain]['codigo']} / {latest['codigo']}. Revisar antes de usar o descartar.",
                       mx=latest.get('mx', []))
    return len(cached), disagreements


def export(folder, rows, summary):
    folder.mkdir(parents=True, exist_ok=True)
    specs = {
        'Todos los correos recopilados.csv': lambda row: True,
        'Correos con dominio apto.csv': lambda row: row['estado'] == 'APTO_DNS',
        'Correos con problemas.csv': lambda row: row['estado'] == 'INVALIDO',
        'Correos por revisar.csv': lambda row: row['estado'] == 'REVISAR',
    }
    counts = {}
    for name, predicate in specs.items():
        selected = [row for row in rows if predicate(row)]
        with (folder / name).open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerows([[safe_csv_value(row['normalizado'] or row['original'].strip())] for row in selected])
        counts[name] = len(selected)
    summary['archivos_exportados'] = counts
    write_json_atomic(folder / 'Resumen.json', summary)
    write_json_atomic(folder / 'Detalle.json', {'resumen': summary, 'correos': rows})
    notes = [
        'RESULTADO DE LA REVISIÓN DE CORREOS', '',
        f"Fecha UTC: {summary['fecha_utc']}", f"Archivos examinados: {summary['archivos_examinados']}",
        f"Apariciones encontradas: {summary['apariciones']:,}", f"Direcciones distintas: {summary['direcciones_distintas']:,}",
        f"Repeticiones adicionales: {summary['repeticiones']:,}", '',
        *[f'{key}: {value:,}' for key, value in summary['estados'].items()], '',
        'Dominio apto significa que se admitió el formato y se encontró infraestructura DNS para recibir correo.',
        'No confirma que el buzón exista ni que el mensaje vaya a entregarse.',
        'Con problemas refleja el formato o DNS de esta consulta; no son rebotes observados.',
        'Por revisar contiene resultados no concluyentes y no debe descartarse automáticamente.',
        'No se conectó a SMTP y no se envió ningún mensaje.', '',
        'Los CSV tienen una columna, sin encabezado, y no repiten direcciones normalizadas.',
        'Los originales no se modificaron. Resumen.json conserva sus rutas y huellas SHA-256.',
    ]
    (folder / 'Leer primero.txt').write_text('\n'.join(notes), encoding='utf-8-sig')
    table = ''.join(f'<tr><td>{html.escape(name)}</td><td>{count:,}</td></tr>' for name, count in counts.items())
    page = f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>Resultado de la revisión</title>
<style>body{{font:16px Arial;margin:36px;color:#17324d;background:#f6f8fb}}main{{max-width:900px;margin:auto;background:white;padding:32px}}h1{{margin-top:0}}table{{border-collapse:collapse;width:100%}}th{{background:#184e77;color:white}}td,th{{padding:12px;border-bottom:1px solid #cad9e6;text-align:left}}.note{{background:#fff5d9;padding:16px;border-radius:6px;line-height:1.5}}</style><main><h1>Resultado de la revisión de correos</h1>
<p>{summary['archivos_examinados']} archivos · {summary['apariciones']:,} apariciones · {summary['direcciones_distintas']:,} direcciones distintas.</p>
<table><tr><th>Lista</th><th>Direcciones</th></tr>{table}</table><p class="note"><b>Alcance:</b> formato y DNS. No se comprobó la existencia de los buzones, no se observaron rebotes y no se enviaron mensajes.</p></main></html>'''
    (folder / 'Informe.html').write_text(page, encoding='utf-8')
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('carpeta', type=Path)
    parser.add_argument('--salida', type=Path, default=None)
    parser.add_argument('--reanudar', type=Path, default=None, help='Carpeta de una ejecución interrumpida')
    parser.add_argument('--workers', type=int, default=24)
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 32:
        parser.error('Usa entre 1 y 32 consultas simultáneas.')
    if args.reanudar:
        output = args.reanudar
        rows = json.loads((output / 'Preparación.json').read_text(encoding='utf-8'))['correos']
        metadata = json.loads((output / 'Preparación.json').read_text(encoding='utf-8'))['metadatos']
    else:
        root = args.salida or Path('resultados')
        root.mkdir(parents=True, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix=datetime.now().strftime('revision_carpeta_%Y%m%d_%H%M%S_'), dir=root))
        rows, issues, sources, appearances, columns = collect(args.carpeta)
        metadata = {'fuentes': sources, 'incidencias': issues, 'apariciones': appearances, 'columnas': columns}
        write_json_atomic(output / 'Preparación.json', {'metadatos': metadata, 'correos': rows})
    checked = check_domains(rows, output / 'Consultas DNS.jsonl', args.workers)
    rechecked, disagreements = recheck_negative_domains(rows, output / 'Segunda consulta DNS.jsonl', args.workers)
    summary = {
        'fecha_utc': datetime.now(timezone.utc).isoformat(), 'carpeta_origen': str(args.carpeta.resolve()),
        'archivos_examinados': len(metadata['fuentes']), 'columnas_detectadas': metadata['columnas'],
        'incidencias': metadata['incidencias'], 'apariciones': metadata['apariciones'],
        'direcciones_distintas': len(rows), 'repeticiones': metadata['apariciones'] - len(rows),
        'dominios_consultados_o_recuperados': checked, 'estados': dict(Counter(row['estado'] for row in rows)),
        'dominios_negativos_reconsultados': rechecked, 'resultados_dns_discrepantes': disagreements,
        'codigos': dict(Counter(row['codigo'] for row in rows)), 'tipos': dict(Counter(row['tipo'] for row in rows)),
        'fuentes': metadata['fuentes'],
        'alcance': 'Sintaxis y DNS. Buzones y entrega no comprobados. Sin SMTP ni envíos.',
    }
    counts = export(output, rows, summary)
    assert sum(summary['estados'].values()) == len(rows)
    assert counts['Todos los correos recopilados.csv'] == len(rows)
    print(json.dumps({**summary, 'fuentes': f"{len(summary['fuentes'])} registros"}, ensure_ascii=False, indent=2))
    print('RESULTADO:', output.resolve())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
