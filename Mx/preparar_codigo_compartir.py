"""Copia únicamente archivos públicos del programa; nunca recorre datos de clientes."""
from pathlib import Path
import shutil

root=Path(__file__).resolve().parent
target=root/'entrega'/'MxCorreo Codigo'
target.mkdir(exist_ok=False)
names=['abrir_archivo.py','mxcorreo_app.py','campana.py','centro_campanas.py',
       'dialogos_importacion.py','importar_contactos.py','importacion_automatica.py',
       'resultados_interfaz.py','verificar_correos.py','analizar_lista_zip.py',
       'procesar_carpeta.py','etapas.py','limpiar_lista.py','revisar_dns.py',
       'generar_informe.py','empaquetar_windows.py','requirements.txt',
       'requirements-build.txt','GUIA_LINUX.md','GUIA_CAMPANA.md',
       'Guía de campañas.txt','LEEME_WINDOWS.txt','campana.ejemplo.json',
       'mensaje.ejemplo.txt','ejemplo.txt']
for name in names:
    shutil.copy2(root/name,target/name)
(target/'tests').mkdir()
for path in (root/'tests').glob('test_*.py'):
    shutil.copy2(path,target/'tests'/path.name)
shutil.copy2(root/'GUIA_LINUX.md',target/'README.md')
print(target)
