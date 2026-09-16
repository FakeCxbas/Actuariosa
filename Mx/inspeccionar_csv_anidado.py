import csv,collections
from pathlib import Path
from importacion_automatica import decode_text
for name in ['base completa  corve.csv','base completa actuari.csv']:
    patterns=collections.Counter(); examples={}
    for i,line in enumerate(decode_text((Path('entrega/Solo bases con correos')/name).read_bytes())[0].splitlines(),1):
        outer=next(csv.reader([line],delimiter=';' if 'corve' in name else ','))
        inner=next(csv.reader([outer[0]])) if outer else []
        pattern=(len(outer),len(inner),bool(inner and inner[0].isdigit()))
        patterns[pattern]+=1
        if not (len(inner)>=3 and inner[0].isdigit()) and not (len(outer)==1 and len(inner)<=1):
            examples.setdefault(pattern,(i,line[:300]))
    print(name,patterns,examples)
