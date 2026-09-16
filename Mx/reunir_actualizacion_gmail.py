"""Añade bases nuevas por contenido y conserva trazabilidad de originales."""
from pathlib import Path
import hashlib, json, shutil
from importacion_automatica import scan_files, EXTENSIONS

root = Path('resultados/actualizacion Gmail 13 septiembre 2026')
dest = Path('entrega/Solo bases con correos')
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
known = {sha(p): str(p) for p in dest.rglob('*') if p.is_file()}
before = dict(known)
manifest = []
for p in sorted((root/'descargas').iterdir()):
    digest = sha(p)
    item = {'descarga':str(p),'sha256':digest,'bytes':p.stat().st_size}
    if digest in known:
        item.update(accion='duplicado exacto', destino=known[digest])
        manifest.append(item)
        continue
    source = p if p.suffix.lower() in EXTENSIONS else root/'extracciones'/(p.name+'.txt')
    if not source.exists():
        item['accion']='formato no procesado'
        manifest.append(item)
        continue
    groups, issues = scan_files([source])
    count = sum(len(g['contacts']) for g in groups)
    item.update(contactos_extraidos=count, incidencias=issues)
    if issues:
        item['accion']='pendiente por incidencia'
    elif not count:
        item['accion']='sin correos extraidos; original conservado en descargas'
    else:
        name = p.name.split(' ',2)[2]
        target = dest/name
        if target.exists():
            target = dest/(target.stem+' Gmail septiembre 2026'+target.suffix)
        if target.exists():
            raise RuntimeError('Conflicto de nombre: '+str(target))
        shutil.copy2(p, target)
        known[digest] = str(target)
        item.update(accion='añadido', destino=str(target))
        if source != p:
            extracted = dest/(target.name+' correos extraidos.txt')
            shutil.copy2(source,extracted)
            item['extraccion']=str(extracted)
    manifest.append(item)
    print(item['accion'], p.name, count, flush=True)
assert all(Path(path).is_file() and sha(Path(path))==h for h,path in before.items())
(root/'Integracion.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('RESUMEN', {a:sum(i['accion']==a for i in manifest) for a in set(i['accion'] for i in manifest)}, flush=True)
