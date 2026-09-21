"""Consolidación, depuración y exportación maestra de correos."""
import csv
import json
import shutil
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from email_validator import validate_email, EmailNotValidError
from importacion_automatica import EXTENSIONS, scan_files


def main():
    dirs = [
        Path('entradas/pendrive_correos'),
        Path('entradas/pendrive_2'),
    ]

    all_paths = []
    for d in dirs:
        all_paths.extend([
            p for p in d.rglob('*')
            if p.is_file() and p.suffix.lower() in EXTENSIONS and not p.name.startswith(('~$', '._'))
        ])
    all_paths = sorted(all_paths)
    print(f'Procesando {len(all_paths)} archivos...')

    groups, issues = scan_files(all_paths, progress=lambda m: None)
    contacts = [c for g in groups for c in g['contacts']]
    print(f'Apariciones totales encontradas: {len(contacts):,}')

    unique_valid = {}
    unique_invalid = {}

    for c in contacts:
        val = c['correo'].strip()
        val = val.strip('/\"\'` ')
        if not val:
            continue
        file_name = c['archivo_origen']
        try:
            parsed = validate_email(val, check_deliverability=False, allow_quoted_local=True, allow_domain_literal=True)
            norm = parsed.normalized
            domain = parsed.ascii_domain.lower()
            key = norm.lower()
            if key not in unique_valid:
                unique_valid[key] = {
                    'correo': norm,
                    'dominio': domain,
                    'apariciones': 0,
                    'archivos': Counter(),
                }
            unique_valid[key]['apariciones'] += 1
            unique_valid[key]['archivos'][file_name] += 1
        except EmailNotValidError as exc:
            key = val.lower()
            if key not in unique_invalid:
                unique_invalid[key] = {
                    'original': val,
                    'motivo': str(exc),
                    'apariciones': 0,
                    'archivos': Counter(),
                }
            unique_invalid[key]['apariciones'] += 1
            unique_invalid[key]['archivos'][file_name] += 1

    sorted_valid = sorted(unique_valid.values(), key=lambda x: x['correo'])
    sorted_invalid = sorted(unique_invalid.values(), key=lambda x: x['original'])

    print(f'Correos válidos únicos: {len(sorted_valid):,}')
    print(f'Correos con formato inválido: {len(sorted_invalid):,}')
    print(f'Duplicados eliminados/consolidados: {len(contacts) - (len(sorted_valid) + len(sorted_invalid)):,}')

    domain_counts = Counter(item['dominio'] for item in sorted_valid)

    out_dir = Path('resultados/consolidado_maestro')
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Correos depurados maestro.csv
    master_csv = out_dir / 'Correos depurados maestro.csv'
    with master_csv.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        for item in sorted_valid:
            writer.writerow([item['correo']])

    # 2. Correos depurados maestro con detalle.csv
    detail_csv = out_dir / 'Correos depurados maestro con detalle.csv'
    with detail_csv.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['correo', 'dominio', 'apariciones', 'archivos_origen'])
        for item in sorted_valid:
            sources_str = '; '.join(f'{k} ({v})' for k, v in item['archivos'].items())
            writer.writerow([item['correo'], item['dominio'], item['apariciones'], sources_str])

    # 3. Correos con problemas de formato.csv
    invalid_csv = out_dir / 'Correos con problemas de formato.csv'
    with invalid_csv.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['correo_original', 'motivo', 'apariciones', 'archivos_origen'])
        for item in sorted_invalid:
            sources_str = '; '.join(f'{k} ({v})' for k, v in item['archivos'].items())
            writer.writerow([item['original'], item['motivo'], item['apariciones'], sources_str])

    # 4. Resumen
    summary = {
        'fecha_utc': datetime.now(timezone.utc).isoformat(),
        'archivos_procesados': len(all_paths),
        'apariciones_totales': len(contacts),
        'correos_validos_unicos': len(sorted_valid),
        'correos_invalidos_formato': len(sorted_invalid),
        'duplicados_eliminados': len(contacts) - (len(sorted_valid) + len(sorted_invalid)),
        'top_dominios': dict(domain_counts.most_common(25)),
    }
    with (out_dir / 'Resumen_Consolidado_Maestro.json').open('w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Copia a destinos
    drive_dir = Path('resultados/Para_Google_Drive')
    pendrive_dir = Path('/run/media/fakecxbas/C67C-AEC3/Correos_Depurados')
    drive_dir.mkdir(parents=True, exist_ok=True)
    pendrive_dir.mkdir(parents=True, exist_ok=True)

    for f in out_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, drive_dir / f.name)
            shutil.copy2(f, pendrive_dir / f.name)

    # Generar ZIP para Drive
    zip_local = Path('resultados/Correos_Depurados_Google_Drive')
    archive = shutil.make_archive(str(zip_local), 'zip', str(drive_dir))
    shutil.copyfile(archive, '/run/media/fakecxbas/C67C-AEC3/Correos_Depurados_Google_Drive.zip')
    print('Consolidación y copia completadas con éxito.')


if __name__ == '__main__':
    main()
