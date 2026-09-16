"""Auditoría de una lista local: solo sintaxis y DNS, nunca SMTP. """
import csv
import io
import json
import hashlib
import difflib
import html
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import argparse

import dns.resolver
from verificar_correos import DNSChecker, prepare_lines

PUBLIC = set('gmail.com googlemail.com hotmail.com hotmail.es hotmail.it hotmail.fr hotmail.co.uk hotmail.de outlook.com outlook.es live.com live.com.ar live.com.mx live.fr live.co.uk msn.com yahoo.com yahoo.es yahoo.com.mx yahoo.com.ar yahoo.co.uk yahoo.fr yahoo.it yahoo.de yahoo.ca yahoo.com.br ymail.com rocketmail.com aol.com aim.com icloud.com me.com mac.com proton.me protonmail.com pm.me gmx.com gmx.de gmx.net mail.com email.com zoho.com qq.com 163.com 126.com yandex.com yandex.ru tutanota.com tuta.com fastmail.com hushmail.com mail.ru inbox.ru bk.ru list.ru terra.com terra.es latinmail.com mixmail.com'.split())
ISP = set('ecutel.net andinanet.net telconet.net ecua.net.ec iclaro.com.ec on.net.ec impsat.net.ec trans-telco.net punto.net.ec puntonet.ec satnet.net porta.net ecuaenlace.com transt elco.ec'.replace('transt elco.ec', 'transtelco.ec').split())
COMMON = ['hotmail.com', 'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.es', 'yahoo.es']

def classify(domain):
    if not domain:
        return 'NO_CLASIFICABLE', 'Formato no admitido; no se presupone un dominio correcto.', ''
    if domain in PUBLIC:
        return 'PROVEEDOR_PUBLICO', 'Proveedor público. Puede pertenecer a una persona o a un negocio; titular no comprobado.', ''
    if any(domain == d or domain.endswith('.' + d) for d in ISP):
        return 'PROVEEDOR_O_TELECOM', 'Dominio de proveedor/telecom: puede ser cliente o empleado; titular no comprobado.', ''
    if '.edu.' in domain or domain.endswith('.edu') or '.ac.' in domain:
        return 'EDUCATIVO_PROBABLE', 'Inferencia por sufijo educativo, sin comprobar la identidad del titular.', ''
    if '.gob.' in domain or '.gov.' in domain or domain.endswith('.gov') or '.mil.' in domain:
        return 'PUBLICO_INSTITUCIONAL_PROBABLE', 'Inferencia por sufijo gubernamental/institucional.', ''
    matches = difflib.get_close_matches(domain, COMMON, n=1, cutoff=0.87)
    if matches:
        return 'POSIBLE_ERROR_DE_DOMINIO', 'Se parece a un proveedor público; revisar manualmente incluso si tiene MX. No se corrigió.', matches[0]
    if '.org.' in domain or domain.endswith('.org'):
        return 'ORGANIZACION_PROBABLE', 'Dominio propio con sufijo de organización; no demuestra que sea empresa comercial.', ''
    return 'DOMINIO_PROPIO_POR_CONFIRMAR', 'Posible empresa, institución o persona con dominio propio. No se verificó identidad comercial.', ''

def run(source, folder):
    folder.mkdir(parents=True, exist_ok=False)
    occurrences, source_counts, hashes = [], {}, {}
    with zipfile.ZipFile(source) as archive:
        for entry in archive.infolist():
            if not entry.filename.lower().endswith('.csv'):
                continue
            raw = archive.read(entry)
            hashes[entry.filename] = hashlib.sha256(raw).hexdigest()
            text = raw.decode('utf-8-sig')
            count = 0
            reader = csv.reader(io.StringIO(text))
            for line in reader:
                if len(line) > 1:
                    raise ValueError(f'Columnas inesperadas en {entry.filename}:{reader.line_num}')
                if line and line[0].strip():
                    occurrences.append({'archivo': entry.filename, 'fila': reader.line_num, 'original': line[0]})
                    count += 1
            source_counts[entry.filename] = count
    rows = prepare_lines([r['original'] for r in occurrences])
    unique = {}
    for row in rows:
        key = row['normalizado'] or row['original'].strip()
        if key not in unique:
            unique[key] = dict(row, apariciones=[], id=len(unique) + 1)
        unique[key]['apariciones'].append(occurrences[row['linea'] - 1])
    result = list(unique.values())
    for row in result:
        row['tipo'], row['criterio_tipo'], row['sugerencia_revisar'] = classify(row['dominio'])
    domains = sorted({r['dominio'] for r in result if r['dominio'] and not r['estado']})
    print(f'Entradas {len(rows)}; únicas {len(result)}; dominios a consultar {len(domains)}', flush=True)
    resolver = dns.resolver.Resolver()
    resolver.cache = dns.resolver.Cache()
    checker = DNSChecker(timeout=3, retries=1, resolver=resolver)
    cache = {}
    with (folder / 'consultas_dns.jsonl').open('w', encoding='utf-8') as stream:
        with ThreadPoolExecutor(max_workers=24) as pool:
            futures = {pool.submit(checker.check, domain): domain for domain in domains}
            for count, future in enumerate(as_completed(futures), 1):
                domain = futures[future]
                try:
                    value = future.result()
                except Exception as exc:
                    value = dict(estado='REVISAR', codigo='ERROR_CONSULTA', motivo=type(exc).__name__, mx=[])
                value['fecha_utc'] = datetime.now(timezone.utc).isoformat()
                cache[domain] = value
                stream.write(json.dumps(dict(dominio=domain, **value), ensure_ascii=False) + '\n')
                stream.flush()
                if count % 100 == 0 or count == len(domains):
                    print(f'DNS {count}/{len(domains)}', flush=True)
    for row in result:
        if not row['estado']:
            row.update(cache[row['dominio']])
    identical = []
    for filename, digest in hashes.items():
        prior = [other for other in hashes if other != filename and hashes[other] == digest]
        if prior:
            identical.append([filename, *prior])
    summary = dict(fecha_utc=datetime.now(timezone.utc).isoformat(), archivo=str(source), sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                   entradas=len(rows), unicos=len(result), repetidos=len(rows)-len(result), dominios_consultados=len(domains),
                   estados=dict(Counter(r['estado'] for r in result)), tipos=dict(Counter(r['tipo'] for r in result)),
                   estados_por_tipo={t: dict(Counter(r['estado'] for r in result if r['tipo']==t)) for t in sorted({r['tipo'] for r in result})},
                   codigos=dict(Counter(r['codigo'] for r in result)), archivos=source_counts, archivos_identicos=identical,
                   alcance='Sintaxis y DNS. Buzones NO COMPROBADOS. Clasificación de dominio orientativa, identidad empresarial no comprobada. Sin SMTP ni envíos.',
                   fuentes=['https://www.rfc-editor.org/rfc/rfc5321.html', 'https://www.rfc-editor.org/rfc/rfc7505.html'])
    (folder/'resumen.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder/'detalle.json').write_text(json.dumps(dict(resumen=summary, correos=result), ensure_ascii=False), encoding='utf-8')
    for state in ('APTO_DNS', 'INVALIDO', 'REVISAR'):
        (folder/f'{state}.txt').write_text('\n'.join(r['normalizado'] or r['original'] for r in result if r['estado']==state), encoding='utf-8')
    write_html(folder, summary, result)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)

def write_html(folder, summary, rows):
    data = json.dumps(rows, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    stats = ''.join(f'<li>{html.escape(k)}: <b>{v:,}</b></li>' for k,v in summary['estados'].items())
    page = '''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Revisión de la lista de correos</title>
<style>body{font:15px system-ui;margin:28px;color:#172b40;background:#f7f9fc}h1{font-size:28px}p{max-width:1100px;line-height:1.5}.note{padding:16px;background:#fff2cb;border-radius:8px}select,input,button{font:inherit;padding:9px;margin:4px}table{border-collapse:collapse;width:100%;background:white}th,td{padding:10px;text-align:left;border-bottom:1px solid #ddd;vertical-align:top;overflow-wrap:anywhere}th{background:#e7edf6}td:nth-child(1){min-width:240px}small{display:block;color:#52637b}#counter{margin:14px}a{color:#075daf}</style>
<h1>Revisión de la lista de correos</h1><p>FECHA · ENTRADAS entradas · UNICOS direcciones únicas · REPETIDOS repeticiones adicionales · 20 archivos de origen.</p>
<div class="note"><b>No hay buzones confirmados.</b> APTO_DNS indica formato admitido y un servidor de correo publicado con IP; no acredita que exista esa cuenta. INVALIDO indica un fallo de formato o DNS en esta consulta. REVISAR señala casos no concluyentes. No se enviaron mensajes.<br><br>La clasificación es por dominio: un Gmail puede ser de empresa y un dominio propio puede ser personal. Los dominios propios requieren confirmar su titular. Las sugerencias de errores NO se aplicaron automáticamente.</div>
<ul>STATS</ul><p>Comprueba los casos de <b>posible error de dominio</b> incluso cuando aparezcan como APTO_DNS. Algunos errores tipográficos conducen a dominios reales distintos del destinatario deseado.</p>
<input id="q" placeholder="Buscar dirección o archivo…" size="35"><select id="state"><option value="">Todos los estados</option></select><select id="type"><option value="">Todos los tipos de dominio</option></select><button id="download">Descargar selección TXT</button><div id="counter"></div><button id="prev">Anterior</button><button id="next">Siguiente</button>
<div style="overflow:auto"><table><thead><tr><th>Correo</th><th>Comprobación</th><th>Clasificación</th><th>Origen</th></tr></thead><tbody id="body"></tbody></table></div>
<p>Referencias del método: <a href="https://www.rfc-editor.org/rfc/rfc5321.html">SMTP, RFC 5321</a> · <a href="https://www.rfc-editor.org/rfc/rfc7505.html">Null MX, RFC 7505</a>. Los datos completos y todas las apariciones están en detalle.json.</p>
<script>const rows=DATA;let filtered=rows,page=0;const $=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
for(const [id,key] of [['state','estado'],['type','tipo']])for(const v of [...new Set(rows.map(r=>r[key]))].sort()){const o=document.createElement('option');o.value=v;o.textContent=v;$ (id).append(o)}
function draw(){const start=page*100;$('body').innerHTML=filtered.slice(start,start+100).map(r=>'<tr><td>'+esc(r.normalizado||r.original)+'<small>'+esc(r.dominio)+'</small></td><td><b>'+esc(r.estado)+'</b><small>'+esc(r.codigo)+'</small>'+esc(r.motivo)+'<small>MX: '+esc(r.mx.join('; '))+'</small></td><td>'+esc(r.tipo)+'<small>'+esc(r.criterio_tipo)+'</small>'+(r.sugerencia_revisar?'<b>¿Quiso decir '+esc(r.sugerencia_revisar)+'?</b>':'')+'</td><td>'+r.apariciones.length+' aparición(es)<details><summary>Ver archivos y filas</summary>'+r.apariciones.map(a=>esc(a.archivo)+' · fila '+a.fila+' · '+esc(a.original)).join('<br>')+'</details></td></tr>').join('');$('counter').textContent=filtered.length+' resultados · página '+(page+1)+' de '+Math.max(1,Math.ceil(filtered.length/100));$('prev').disabled=!page;$('next').disabled=start+100>=filtered.length}
function filter(){const q=$('q').value.toLowerCase();filtered=rows.filter(r=>(!$('state').value||r.estado===$('state').value)&&(!$('type').value||r.tipo===$('type').value)&&(!q||(r.normalizado||r.original).toLowerCase().includes(q)||r.apariciones.some(a=>a.archivo.toLowerCase().includes(q))));page=0;draw()}
for(const id of ['q','state','type'])$(id).addEventListener('input',filter);$('prev').onclick=()=>{page--;draw()};$('next').onclick=()=>{page++;draw()};$('download').onclick=()=>{const blob=new Blob([filtered.map(r=>r.normalizado||r.original).join('\\r\\n')],{type:'text/plain;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='seleccion_revision.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};draw();</script></html>'''
    for key,value in [('FECHA',summary['fecha_utc']),('ENTRADAS',f"{summary['entradas']:,}"),('UNICOS',f"{summary['unicos']:,}"),('REPETIDOS',f"{summary['repetidos']:,}"),('STATS',stats),('DATA',data)]:
        page=page.replace(key,value)
    (folder/'informe.html').write_text(page,encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('zip',type=Path)
    parser.add_argument('salida',type=Path)
    args=parser.parse_args()
    run(args.zip,args.salida)
