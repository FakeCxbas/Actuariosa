"""Procesamiento, recopilación y fusión del 3er pendrive (STORE N GO)."""
import csv
import json
import shutil
from pathlib import Path
from email_validator import validate_email, EmailNotValidError
from importacion_automatica import EXTENSIONS, scan_files


def main():
    pendrive_src = Path('/run/media/fakecxbas/STORE N GO')
    local_p3 = Path('entradas/pendrive_3')
    recop_mx = Path('entradas/recopilacion_archivos')
    recop_proy = Path('/home/fakecxbas/Proyectos/correos')

    local_p3.mkdir(parents=True, exist_ok=True)
    recop_mx.mkdir(parents=True, exist_ok=True)
    recop_proy.mkdir(parents=True, exist_ok=True)

    print('=== 1. Copiando archivos a las carpetas de recopilación ===')
    paths = sorted(
        p for p in pendrive_src.rglob('*')
        if p.is_file() and not p.name.startswith(('~$', '._')) and 'System Volume Information' not in p.parts
    )
    for p in paths:
        rel = p.relative_to(pendrive_src)
        target_local = local_p3 / rel
        target_local.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target_local)

        # Si ya existe en la recopilación un archivo con el mismo nombre y contenido diferente, diferenciar
        target_mx = recop_mx / rel
        target_proy = recop_proy / rel
        if target_mx.exists() and target_mx.stat().st_size != p.stat().st_size:
            target_mx = recop_mx / f"{p.stem} (Pendrive 3){p.suffix}"
            target_proy = recop_proy / f"{p.stem} (Pendrive 3){p.suffix}"
        target_mx.parent.mkdir(parents=True, exist_ok=True)
        target_proy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target_mx)
        shutil.copy2(p, target_proy)

    print(f'Copia lista. Total archivos copiados: {len(paths)}')

    print('=== 2. Extrayendo correos de los archivos del 3er pendrive ===')
    data_files = sorted(
        p for p in local_p3.rglob('*')
        if p.is_file() and p.suffix.lower() in EXTENSIONS and not p.name.startswith(('~$', '._'))
    )
    groups, issues = scan_files(data_files, progress=lambda m: None)
    contacts = [c for g in groups for c in g['contacts']]
    print(f'Contactos leídos en 3er pendrive: {len(contacts):,}')

    print('=== 3. Fusionando con la base maestra del 17 de septiembre ===')
    path_master = Path('/home/fakecxbas/Descargas/Correos aptos totales 17 septiembre 2026.csv')
    with path_master.open('r', encoding='utf-8-sig') as f:
        master_emails = {line.strip().lower(): line.strip() for line in f if line.strip()}

    initial_master_count = len(master_emails)
    new_unique_emails = []

    for c in contacts:
        val = c['correo'].strip().strip("/'\"` -+")
        if not val:
            continue
        try:
            parsed = validate_email(val, check_deliverability=False, allow_quoted_local=True)
            norm = parsed.normalized
            key = norm.lower()
            if key not in master_emails:
                master_emails[key] = norm
                new_unique_emails.append((norm, c['archivo_origen']))
        except EmailNotValidError:
            pass

    sorted_master = sorted(master_emails.values())
    total_master = len(sorted_master)
    added_count = total_master - initial_master_count

    print(f'Total maestro anterior: {initial_master_count:,}')
    print(f'Nuevos correos únicos aportados por el 3er pendrive: {added_count:,}')
    print(f'NUEVO TOTAL MAESTRO AL 17 DE SEPTIEMBRE: {total_master:,}')

    if new_unique_emails:
        print('Muestra de nuevos correos añadidos:')
        for email, src in new_unique_emails[:10]:
            print(f'  {email} (de {src})')

    print('=== 4. Guardando archivos actualizados ===')
    # 1. En Descargas
    with path_master.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        for email in sorted_master:
            writer.writerow([email])

    # 2. En Drive
    drive_dir = Path('resultados/Para_Google_Drive')
    drive_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path_master, drive_dir / path_master.name)

    # 3. En el pendrive
    pendrive_out = pendrive_src / 'Correos_Depurados'
    pendrive_out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path_master, pendrive_out / path_master.name)

    # 4. Actualizar ZIP para Drive y copiar al pendrive
    zip_local = Path('resultados/Correos_Depurados_Google_Drive')
    archive = shutil.make_archive(str(zip_local), 'zip', str(drive_dir))
    shutil.copyfile(archive, pendrive_src / 'Correos_Depurados_Google_Drive.zip')

    print('=== Todo completado y sincronizado con éxito ===')


if __name__ == '__main__':
    main()
