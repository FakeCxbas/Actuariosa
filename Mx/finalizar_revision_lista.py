"""Reconsulta los resultados DNS no aptos y genera el informe final."""
import json
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from analizar_lista_zip import write_html, classify
from verificar_correos import DNSChecker

folder=Path('resultados/revision_lista_20260901')
data=json.loads((folder/'detalle.json').read_text(encoding='utf-8'))
rows=data['correos']
initial={r['dominio']: dict(estado=r['estado'],codigo=r['codigo'],motivo=r['motivo'],mx=r['mx']) for r in rows if r['dominio'] and r['estado']!='APTO_DNS'}
checker=DNSChecker(timeout=4,retries=1)
checked={}
with (folder/'segunda_consulta_dns.jsonl').open('w',encoding='utf-8') as stream:
    with ThreadPoolExecutor(max_workers=24) as pool:
        futures={pool.submit(checker.check,d):d for d in initial}
        for n,f in enumerate(as_completed(futures),1):
            domain=futures[f]
            try:
                value=f.result()
            except Exception as exc:
                value=dict(estado='REVISAR',codigo='ERROR_CONSULTA',motivo=type(exc).__name__,mx=[])
            value['fecha_utc']=datetime.now(timezone.utc).isoformat()
            checked[domain]=value
            stream.write(json.dumps(dict(dominio=domain,**value),ensure_ascii=False)+'\n')
            stream.flush()
            if n%100==0 or n==len(initial):
                print(f'Segunda consulta {n}/{len(initial)}',flush=True)
for r in rows:
    r['tipo'],r['criterio_tipo'],r['sugerencia_revisar']=classify(r['dominio'])
    if r['dominio'] in checked:
        previous=initial[r['dominio']]
        latest=checked[r['dominio']]
        r['primera_consulta']=previous
        r['segunda_consulta']=latest
        r.update(latest)
        if previous['estado']=='INVALIDO' and latest['estado']!='INVALIDO':
            r.update(estado='REVISAR',codigo='DNS_DISCREPANTE',motivo='Las dos consultas no coinciden: '+previous['codigo']+' / '+latest['codigo']+'. Revisar antes de descartar o usar.')
summary=data['resumen']
summary.update(fecha_utc=datetime.now(timezone.utc).isoformat(),dominios_reconsultados=len(checked),
               estados=dict(Counter(r['estado'] for r in rows)),tipos=dict(Counter(r['tipo'] for r in rows)),
               estados_por_tipo={t:dict(Counter(r['estado'] for r in rows if r['tipo']==t)) for t in sorted({r['tipo'] for r in rows})},
               codigos=dict(Counter(r['codigo'] for r in rows)))
assert sum(summary['estados'].values())==summary['unicos']==len(rows)
assert sum(len(r['apariciones']) for r in rows)==summary['entradas']
assert all(r['buzon']=='NO_COMPROBADO' for r in rows)
(folder/'resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
(folder/'detalle.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
for state in ('APTO_DNS','INVALIDO','REVISAR'):
    (folder/f'{state}.txt').write_text('\n'.join(r['normalizado'] or r['original'] for r in rows if r['estado']==state),encoding='utf-8')
for kind in summary['tipos']:
    (folder/f'{kind}.txt').write_text('\n'.join(r['normalizado'] or r['original'] for r in rows if r['tipo']==kind),encoding='utf-8')
write_html(folder,summary,rows)
print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
