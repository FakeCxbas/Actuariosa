# Verificador inicial de correos

## Linux y trabajo entre dos personas

Consulta [la guía de Linux](GUIA_LINUX.md) para instalar Python y Tk, ejecutar la interfaz y compartir el código sin compartir credenciales o historiales.

## Aplicación portable para Windows

Para usarlo en otra computadora **sin instalar Python ni escribir comandos**, usa el ZIP más reciente de `entrega/`. Extrae todo, conserva la carpeta `_internal` y abre `MxCorreo.exe`. Pulsa **Cargar archivos** o **Cargar carpeta**, confirma las columnas detectadas y elige **Revisar dominios**. Lee `LEEME_WINDOWS.txt`.

La importación automática recorre todas las hojas de Excel y admite CSV sin encabezado, varias columnas y varias direcciones por celda. Conserva archivo, hoja y celda de origen. Incluye vista previa, selección de columnas, avisos por archivo, lectura en segundo plano y cancelación. La selección manual de Excel sigue disponible.

La pantalla de resultados tiene contadores, búsqueda, filtros y páginas de 200 entradas. **Exportar listas CSV** genera listas completas sin repeticiones exactas de dirección normalizada, separadas en todos, dominio apto, problemas y pendientes. Los pendientes nunca se presentan como buzones inexistentes. Importar y exportar no envían correo.

La aplicación tiene pestañas de lista/resultados, mensaje, cuenta y envío autorizado. Crea una carpeta `datos` junto al ejecutable para guardar configuración e historial. Conserva esa carpeta al trasladarlo después de usarlo. No incluye credenciales ni datos privados. La versión generada es para Windows x64 y no tiene firma comercial; si la empresa la bloquea, pide revisión de TI, sin desactivar protecciones.

Para desarrolladores, `mxcorreo_app.py` es la interfaz y `empaquetar_windows.py` genera una entrega nueva usando `requirements-build.txt`. Las pruebas SMTP no envían correo real.

Prueba 7, 23 de julio del 2024
VALIDÓ AL MENOS 25 CORREOS (ESO ES MAS DE LO QUE CREÍ QUE PODIA ASI QUE AHI QUEDA ESA HVD)
El verificador original prevalida una lista, por ejemplo de 1200 direcciones, sin enviar mensajes ni borrar datos.

**Nuevo: para revisar y preparar/enviar desde un único comando, usa `campana.py`.** Arranca en simulación y reutiliza el verificador original. Consulta [GUIA_CAMPANA.md](GUIA_CAMPANA.md) para los modos de revisión, simulación, prueba, envío y consulta del registro. Los comandos de esta sección siguen siendo de revisión únicamente.

## Uso en Windows

Abre PowerShell en esta carpeta. Requiere Python 3.10 o superior.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe verificar_correos.py ejemplo.txt
```

No hace falta activar el entorno virtual ni cambiar la política de ejecución de Windows. La consola muestra la ruta de `informe.html`: ábrelo con doble clic. También se crea `informe.json` para procesamiento posterior. Cada ejecución usa una carpeta nueva dentro de `resultados`.

En la aplicación portable puedes importar directamente un Excel `.xlsx`/`.xls`: eliges hoja, fila de títulos y columnas de correo, nombre y empresa. También permite pegar una lista de correos separada por líneas, comas, punto y coma o tabulaciones. Esta importación solo crea una copia local para revisar; no modifica el Excel ni envía correos.

Para usar únicamente el verificador de consola, crea `correos.txt` guardado como UTF-8, con una dirección por línea, sin encabezado ni nombres de personas. También puedes usar CSV con `campana.py` o importar el Excel desde la aplicación portable primero.

```powershell
.\.venv\Scripts\python.exe verificar_correos.py correos.txt
```

Las direcciones de `ejemplo.txt` son ilustrativas, no destinatarios para enviar mensajes.

## Ejecutar por etapas separadas

También puedes ejecutar cada paso por separado. Comparten la lógica de `verificar_correos.py`, que sigue disponible como opción de un solo comando. No necesitas reinstalar las dependencias.

```powershell
.\.venv\Scripts\python.exe limpiar_lista.py correos.txt
.\.venv\Scripts\python.exe revisar_dns.py resultados/limpieza.json
.\.venv\Scripts\python.exe generar_informe.py resultados/dns.json
```

- `limpiar_lista.py`: formato, normalización y marcas de duplicados. Conserva todas las filas no vacías; no consulta Internet. Los registros con estado vacío en el JSON intermedio están pendientes de DNS, no aprobados.
- `revisar_dns.py`: lee el resultado anterior, consulta dominios y clasifica resultados. No consulta buzones ni envía correos.
- `generar_informe.py`: transforma el resultado DNS en HTML y JSON legibles. No vuelve a consultar DNS y conserva la fecha de la comprobación.

Los archivos intermedios no se sobrescriben. Para una nueva lista o un reintento, usa nombres distintos con `--salida`:

```powershell
.\.venv\Scripts\python.exe limpiar_lista.py correos.txt --salida resultados/lote2_limpieza.json
.\.venv\Scripts\python.exe revisar_dns.py resultados/lote2_limpieza.json --salida resultados/lote2_dns.json
.\.venv\Scripts\python.exe generar_informe.py resultados/lote2_dns.json
```

Para repetir solo DNS, vuelve a usar el JSON de limpieza y escribe en otro archivo de salida. No pases un informe final al script DNS. Los JSON intermedios también contienen datos privados y deben permanecer dentro de `resultados/` o en otra ubicación protegida y excluida de Git.

Estos tres pasos por separado no envían correos. El nuevo punto de entrada `campana.py` integra la revisión con envío SMTP opcional, protegido por configuración y confirmación. Falta completar los datos y aprobaciones reales de la empresa antes de usar el modo de envío; consulta `GUIA_CAMPANA.md`.

## Cómo interpretar el resultado

| Estado | Significado | Siguiente paso |
| --- | --- | --- |
| APTO_DNS | Sintaxis admitida y al menos un MX resuelve a una IP | Sigue sin confirmar existencia del buzón o entrega |
| REVISAR | DNS temporal, MX implícito, configuración inconsistente o IP literal | Reintentar o revisar; no descartar automáticamente |
| INVALIDO | Formato no admitido, dominio inexistente, Null MX o ausencia de ruta DNS | Revisar el motivo y corregir o excluir del envío; se conserva el original |

Los duplicados se marcan por separado con la línea de primera aparición, sin eliminarlos. Se normaliza el dominio, pero no se convierte la parte anterior al `@` a minúsculas, ni se quitan puntos o etiquetas `+`. Direcciones internacionalizadas que necesitan SMTPUTF8 se señalan en el motivo. Formatos ajenos al uso público de Internet pueden requerir revisión manual aunque la biblioteca los rechace.

Una consulta DNS es una fotografía del momento: incluso resultados negativos pueden cambiar. Si muchos dominios fallan a la vez, revisa tu conexión o DNS antes de tomar decisiones sobre la lista.

## Qué comprueba realmente

1. Valida sintaxis usando `email-validator`, sin sus consultas de entregabilidad.
2. Agrupa dominios para consultar cada dominio una vez por ejecución, aunque aparezca en cientos de direcciones.
3. Consulta MX mediante el DNS configurado en el equipo; resuelve A/AAAA de los servidores publicados.
4. Un MX `0 .` (Null MX) declara que el dominio no recibe correo.
5. Si no hay MX, busca A/AAAA del propio dominio. La existencia de estos registros permite un MX implícito, pero no prueba recepción SMTP: se marca REVISAR.
6. Separa NXDOMAIN/ausencia de registros de errores temporales como timeout o SERVFAIL. Reintenta estos últimos y, si persisten, no los clasifica como direcciones inválidas.

No comprueba buzones, catch-all, spam traps, reputación, consentimiento ni listas de supresión. No produce una lista llamada «correos verificados» porque DNS no permite afirmar eso. No deduce el proveedor final solo por los nombres MX: pueden ser pasarelas de filtrado.

Para completar una limpieza empresarial, cruza después los resultados con las bajas y rebotes históricos de tu plataforma de envío. Cualquier verificación externa de buzones necesita una decisión separada sobre servicio, coste y tratamiento de datos; este script no sube tu lista a ninguno.

## Privacidad y límites

Solo los dominios y nombres de servidores se consultan al resolvedor DNS del equipo; las partes locales de las direcciones no se transmiten. Los informes contienen las direcciones completas y deben tratarse como datos privados. `.gitignore` excluye `correos.txt`, `resultados/` y el entorno virtual; si usas otro nombre de entrada, exclúyelo también antes de hacer un commit.

Por defecto trabaja con 8 dominios simultáneos, 4 segundos por intento DNS y un reintento por consulta fallida. Cada dominio puede requerir varias consultas, por lo que el tiempo total depende de los dominios únicos y los fallos DNS.

```powershell
.\.venv\Scripts\python.exe verificar_correos.py correos.txt --workers 4 --timeout 6 --reintentos 2
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Referencias: [SMTP, RFC 5321 §5.1](https://www.rfc-editor.org/rfc/rfc5321.html#section-5.1), [Null MX, RFC 7505](https://www.rfc-editor.org/rfc/rfc7505.html), [email-validator](https://github.com/JoshData/python-email-validator), [dnspython](https://dnspython.readthedocs.io/en/stable/resolver-class.html).
