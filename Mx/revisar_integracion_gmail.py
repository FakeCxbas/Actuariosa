from pathlib import Path
import json, shutil
from importar_contactos import open_excel
from importacion_automatica import scan_files
root=Path('resultados/actualizacion Gmail 13 septiembre 2026')
manifest=json.loads((root/'Integracion.json').read_text(encoding='utf-8'))
for item in manifest:
    p=Path(item['descarga'])
    if 'extraccion' in item:
        source=root/'extracciones'/(p.name+'.txt')
        shutil.copy2(source, item['extraccion'])
        groups,issues=scan_files([source])
        item.update(contactos_extraidos=sum(len(g['contacts']) for g in groups),incidencias=issues)
    if p.name.endswith('MERCO.xlsx'):
        book=open_excel(p)
        cells=[str(c) for name in book.sheet_names for row in book.get_sheet_by_name(name).to_python() for c in row if c is not None]
        print('MERCO',len(cells),'celdas',sum('@' in c for c in cells),'con arroba')
        assert not any('@' in c for c in cells)
        item['accion']='sin correos; original conservado en descargas'
    if 'GRANJAS' in p.name:
        item['accion']='sin correos en texto; original conservado en descargas'
    if 'SRI_CATASTRO' in p.name:
        groups,issues=scan_files([p])
        print('SRI candidatos', [c['correo'] for g in groups for c in g['contacts']])
        candidates=[c['correo'] for g in groups for c in g['contacts']]
        assert candidates == ['DEL@GRO', 'E@SY NET CIA LTDA']
        if item.get('destino'):
            target=Path(item['destino']).resolve()
            assert target.parent == Path('entrega/Solo bases con correos').resolve()
            excluded=root/'Sin direcciones de correo'
            excluded.mkdir(exist_ok=True)
            shutil.move(str(target), str(excluded/target.name))
            item['destino']=str(excluded/target.name)
        item['accion']='sin correos; arrobas pertenecen a razones sociales'
(root/'Integracion.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Fuentes reunidas', len(list(Path('entrega/Solo bases con correos').iterdir())))
