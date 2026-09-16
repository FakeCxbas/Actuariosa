# MxCorreo en Linux

MxCorreo importa Excel, CSV y texto, revisa formato y DNS, exporta listas y permite preparar campañas y enviar por SMTP con confirmación. DNS no confirma que exista el buzón ni que se entregue el mensaje.

## Instalación (Ubuntu, Debian o Linux Mint)

Requiere escritorio gráfico y Python 3.10 o posterior. Para los scripts de procesamiento por carpeta, utiliza Python 3.11 o posterior.

```bash
sudo apt update
sudo apt install git python3 python3-venv python3-tk xdg-utils
```

Descarga o clona el repositorio y abre una terminal dentro de su carpeta. Luego:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python mxcorreo_app.py
```

En otras distribuciones instala los paquetes equivalentes de Python, Tk y entornos virtuales. No uses el ejecutable Windows en Linux. No ejecutes la aplicación con sudo.

## Uso

1. En la lista, carga tus Excel, CSV o archivos de texto. Revisa las columnas detectadas y la vista previa.
2. Ejecuta la revisión de dominios y exporta las listas. Esto no envía mensajes.
3. Para preparar una campaña, configura mensaje y cuenta y utiliza primero la simulación.
4. El envío real requiere una cuenta autorizada, destinatarios autorizados y confirmar los controles de envío.

La importación interactiva tiene un límite de un millón de entradas por lote. Las exportaciones con un CSV incrustado dentro de otro pueden requerir preparación previa; comprueba siempre las columnas antes de revisar. La aplicación no incorpora automáticamente las correcciones específicas de una ejecución externa.

Los datos e historial se guardan en `datos/`. Puedes separar el perfil:

```bash
.venv/bin/python mxcorreo_app.py --datos "$HOME/.local/share/mxcorreo"
```

## Cómo usarlo entre dos personas

Cada uno instala su copia y ejecuta los mismos comandos. Si el repositorio es privado, su propietario debe invitar al amigo como colaborador. Git comparte el código, no las listas ni los resultados.

Compartan los archivos de trabajo por un medio privado autorizado y acuerden quién envía cada campaña. No ejecuten la misma campaña en dos equipos: cada copia tiene su historial local y podrían duplicar mensajes o superar los límites de la cuenta. No sincronicen una base SQLite mientras está abierta.

Para actualizar una copia sin modificaciones locales:

```bash
git pull --ff-only
.venv/bin/python -m pip install -r requirements.txt
```

Si van a modificar código, trabajen en ramas distintas y revisen los cambios antes de incorporarlos. No suban `datos/`, listas de contactos, contraseñas, archivos de configuración reales ni resultados.

## Cómo se hizo el ZIP anterior

`empaquetar_windows.py` ejecuta PyInstaller sobre `mxcorreo_app.py` con `--onedir` (una carpeta completa), `--windowed` (sin consola) y las dependencias y ejemplos necesarios. Luego incluye las guías y comprime la carpeta con `shutil.make_archive`.

El ZIP es el embalaje; PyInstaller es quien prepara el ejecutable y su entorno. Por eso hay que extraer y conservar toda la carpeta, incluida `_internal`. No es un instalador ni un ejecutable universal: el que se construyó en Windows es para Windows. Para distribuir un binario Linux habría que construirlo y probarlo en Linux; esta entrega permite ejecutar el código fuente.

## Comprobaciones

```bash
.venv/bin/python -m unittest discover -s tests -v
python3 -m tkinter
```

El segundo comando debe abrir una ventana de prueba. Si falla, revisa la instalación de Tk o la sesión gráfica. Las pruebas automatizadas de SMTP usan simulaciones: no envían correos reales.
