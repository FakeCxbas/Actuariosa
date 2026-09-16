"""Procesa cada archivo por separado y fusiona antes de DNS; no envía correo."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import json
import csv, io
import procesar_carpeta as engine
from importacion_automatica import decode_text, scan_table

source=Path('entrega/Solo bases con correos')
output=Path('resultados/actualizacion Gmail 13 septiembre 2026/revision_carpeta_20260913_030031_6pif1oje')
unique={}
issues=[]
sources=[]
appearances=columns=0
original_scan=engine.scan_files
def batches(paths, stop=None, progress=None):
    groups=[]
    failures=[]
    for path in paths:
        if path.name in {'base completa  corve.csv', 'base completa actuari.csv'}:
            text,encoding=decode_text(path.read_bytes())
            parsed=[]
            nested=0
            for number,line in enumerate(text.splitlines(),1):
                if not line.strip():
                    continue
                outer=next(csv.reader([line],delimiter=';' if path.name=='base completa  corve.csv' else ','))
                inner=next(csv.reader([outer[0]])) if len(outer)>=1 else []
                if len(inner)>=3 and inner[0].isdigit():
                    parsed.append((number,[inner[2]]))
                    nested+=1
                else:
                    # Plain addresses occur before the nested export in actuari.csv.
                    if len(outer)!=1 and any(outer[1:]):
                        raise RuntimeError(f'Estructura CSV no reconocida: {path.name}:{number}')
                    if len(inner)>1:
                        raise RuntimeError(f'Exportación interna no reconocida: {path.name}:{number}')
                    parsed.append((number,[outer[0]]))
            found=scan_table(lambda:iter(parsed),path.name,'Correo del CSV interno',stop)
            errors=[]
            print(f'{path.name}: {len(parsed)} filas, {nested} filas con CSV anidado',flush=True)
        else:
            found, errors=original_scan([path], stop=stop,progress=progress)
        groups.extend(found)
        failures.extend(errors)
    return groups,failures

# Each batch stays below the interactive importer's limit. No limit is removed.
engine.scan_files=batches
rows,issues,sources,appearances,columns=engine.collect(source)
if issues:
    raise RuntimeError(json.dumps(issues,ensure_ascii=False))
metadata={'fuentes':sources,'incidencias':issues,'apariciones':appearances,'columnas':columns}
engine.write_json_atomic(output/'Preparación.json', {'metadatos':metadata,'correos':rows})
checked=engine.check_domains(rows,output/'Consultas DNS.jsonl',workers=32)
rechecked,disagreements=engine.recheck_negative_domains(rows,output/'Segunda consulta DNS.jsonl',workers=32)
summary={'fecha_utc':datetime.now(timezone.utc).isoformat(),'carpeta_origen':str(source.resolve()),
    'archivos_examinados':len(sources),'columnas_detectadas':columns,'incidencias':issues,
    'apariciones':appearances,'direcciones_distintas':len(rows),'repeticiones':appearances-len(rows),
    'dominios_consultados_o_recuperados':checked,'estados':dict(Counter(r['estado'] for r in rows)),
    'dominios_negativos_reconsultados':rechecked,'resultados_dns_discrepantes':disagreements,
    'codigos':dict(Counter(r['codigo'] for r in rows)),'tipos':dict(Counter(r['tipo'] for r in rows)),
    'fuentes':sources,'alcance':'Sintaxis y DNS. Buzones y entrega no comprobados. Sin SMTP ni envíos.'}
engine.export(output,rows,summary)
print(json.dumps({k:v for k,v in summary.items() if k!='fuentes'},ensure_ascii=False,indent=2),flush=True)
