"""Verifica exhaustividad y entrega la lista consolidada compatible con Excel."""
from pathlib import Path
import csv, hashlib, json, shutil
root=Path('resultados/actualizacion Gmail 13 septiembre 2026')
run=root/'revision_carpeta_20260913_030031_6pif1oje'
current=json.loads((run/'Detalle.json').read_text(encoding='utf-8'))
old=json.loads(Path('resultados/revision_carpeta_20260904_133417_5c6wa7lz/Detalle.json').read_text(encoding='utf-8'))
rows=current['correos']
summary=current['resumen']
key=lambda r:r['normalizado'] or r['original'].strip()
previous={key(r) for r in old['correos']}
now={key(r) for r in rows}
assert previous <= now, 'Faltan contactos de la revisión anterior'
assert not summary['incidencias'], summary['incidencias']
for source in summary['fuentes']:
    assert hashlib.sha256(Path(source['archivo']).read_bytes()).hexdigest()==source['sha256']
for source in old['resumen']['fuentes']:
    assert hashlib.sha256(Path(source['archivo']).read_bytes()).hexdigest()==source['sha256']
apt={r['normalizado'] for r in rows if r['estado']=='APTO_DNS'}
source=run/'Correos con dominio apto.csv'
with source.open(encoding='utf-8-sig',newline='') as stream:
    data=list(csv.reader(stream))
assert all(len(row)==1 for row in data)
values=[row[0][1:] if row[0].startswith("'") else row[0] for row in data]
assert len(values)==len(set(values))==len(apt)
assert set(values)==apt
assert source.read_bytes().startswith(b'\xef\xbb\xbf')
target=Path('entrega/Correos aptos totales 13 septiembre 2026.csv')
if target.exists():
    # Only replace the preliminary output created by this same update.
    prior=json.loads((root/'Resumen de actualización.json').read_text(encoding='utf-8'))
    assert str(target.resolve()) == prior['csv']
shutil.copy2(source,target)
manifest=json.loads((root/'Integracion.json').read_text(encoding='utf-8'))
result={'previos':len(previous),'total_distintos':len(now),'direcciones_nuevas':len(now-previous),
    'aptos_totales':len(apt),'aptos_nuevos':len(apt-previous),'estados':summary['estados'],
    'apariciones':summary['apariciones'],'archivos_procesados':len(summary['fuentes']),
    'archivos_originales_nuevos':sum(x['accion']=='añadido' for x in manifest),
    'integridad_originales':'comprobada SHA256; ninguna pérdida respecto al resultado anterior',
    'adjuntos_faltantes':0,'sri_repetido':'Bytes MIME idénticos en los tres mensajes',
    'csv':str(target.resolve()),'alcance':summary['alcance']}
(root/'Resumen de actualización.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
note=(f"ACTUALIZACIÓN DE LA BASE DE CORREOS - 13 DE SEPTIEMBRE DE 2026\n\n"
      f"Entradas distintas evaluadas: {len(now):,}\nNuevas frente a la revisión anterior: {len(now-previous):,}\n"
      f"Aptas por formato y DNS: {len(apt):,}\nCon problemas: {summary['estados'].get('INVALIDO',0):,}\n"
      f"Por revisar: {summary['estados'].get('REVISAR',0):,}\n\n"
      "Se incorporaron las bases de Gmail a la carpeta Solo bases con correos. Los archivos idénticos no se copiaron dos veces.\n"
      "Los PDF y Word con correos se conservaron junto con extracciones de texto para el programa.\n"
      "MERCO, el catastro del SRI y el listado de granjas no aportaron correos; sus originales se conservaron aparte.\n"
      "La importación se ejecutó por archivo para respetar el límite por lote, sin perder las bases anteriores.\n"
      "En los dos CSV de base completa se leyó la columna de correo de la exportación interna, excluyendo identificadores y fechas.\n"
      "Se comprobaron formato y DNS; los resultados DNS negativos se consultaron dos veces.\n"
      "Apto NO confirma existencia del buzón, entrega ni autorización comercial. No se enviaron mensajes ni se borraron correos de Gmail.\n"
      f"Detalle auditable: {run.resolve()}\n")
Path('entrega/Resumen de actualización 13 septiembre 2026.txt').write_text(note,encoding='utf-8-sig')
print(json.dumps(result,ensure_ascii=False,indent=2))
