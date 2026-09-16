"""Recupera bytes MIME y extrae texto de documentos, sin ejecutar adjuntos."""
from pathlib import Path
import base64, json, zipfile, xml.etree.ElementTree as ET
from pypdf import PdfReader
import pdfplumber

root = Path('resultados/actualizacion Gmail 13 septiembre 2026')
for item in json.loads((root/'Recuperacion.json').read_text(encoding='utf-8')):
    encoded = ''.join(Path(p).read_text().strip() for p in item['chunks'])
    data = base64.b64decode(encoded, validate=True)
    target = root/'descargas'/('1a0988dea0f23c8e recuperado '+item['name'])
    target.write_bytes(data)
    print(item['name'], len(data))
extracts = root/'extracciones'
extracts.mkdir(exist_ok=True)
for p in (root/'descargas').iterdir():
    if p.suffix.lower() == '.pdf':
        with pdfplumber.open(p) as pdf:
            words = [w['text'] for page in pdf.pages for w in page.extract_words()]
        text = '\n'.join(w for w in words if '@' in w)
    elif p.suffix.lower() == '.docx':
        with zipfile.ZipFile(p) as z:
            ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            tree = ET.fromstring(z.read('word/document.xml'))
            text = '\n'.join(''.join(t.text or '' for t in para.iter(ns+'t')) for para in tree.iter(ns+'p'))
    else:
        continue
    (extracts/(p.name+'.txt')).write_text(text, encoding='utf-8')
    print(p.name, 'texto', len(text), 'arrobas', text.count('@'))
