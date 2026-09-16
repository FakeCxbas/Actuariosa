# Revisar, preparar y enviar con un solo comando

`campana.py` es el punto de entrada integrado. Conserva `verificar_correos.py` a su lado porque reutiliza sus comprobaciones. No tienes que ejecutar los scripts de etapas separados. El modo predeterminado es **simular**, nunca enviar.

## Pruébalo ahora sin enviar nada

En PowerShell, desde la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe campana.py ejemplo.txt
```

En este equipo las dependencias ya están instaladas. En otro equipo con Python 3.10 o superior:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

La simulación consulta DNS, pero no abre conexiones SMTP, no solicita credenciales y no registra mensajes como enviados. Crea una carpeta nueva dentro de `resultados/` con:

- `informe.html` e `informe.json`: revisión de formato, duplicados y DNS, previa al envío.
- `seleccion.json`: decisión para cada fila (seleccionada, duplicada, excluida, pendiente para otro lote, no apta o ya registrada).
- `vista_previa.txt`: primer mensaje, legible sin cliente de correo.
- `muestra.eml`: primer mensaje completo, con su HTML y adjuntos si existen; ábrelo en un cliente de correo sin pulsar enviar. Solo se genera si hay seleccionados.

Solo se seleccionan direcciones `APTO_DNS`, no duplicadas, no excluidas y no registradas previamente para esa campaña. `APTO_DNS` no confirma que exista el buzón. Los casos `REVISAR` no se envían automáticamente.

## Situaciones cubiertas

| Necesidad | Opción |
| --- | --- |
| Revisar sin preparar mensajes | `--modo revisar` (no necesita configuración) |
| Preparar y ver lo que se enviaría | `--modo simular` (predeterminado) |
| Probar el mensaje en una dirección autorizada | `--modo prueba --destino-prueba tu-direccion@tu-dominio` |
| Enviar un lote de la lista revisada | `--modo enviar` |
| Consultar y exportar el registro | `--modo estado` |
| Revisar sin Internet | `--sin-dns`; no aprueba destinatarios ni produce muestra de envío |
| Omitir bajas y contactos excluidos | `--exclusiones exclusiones.txt` |
| Reintentar rechazos SMTP temporales ya revisados | `--reintentar-temporales`; solo 4xx confirmados |

La prueba real también necesita SMTP configurado, remitente autorizado, límites confirmados y confirmación escrita. Consulta DNS para esa única dirección y solo continúa si es `APTO_DNS`. No admite una lista junto con `--destino-prueba` y usa un identificador separado para no marcar la campaña real como enviada. Cada prueba deliberada es un nuevo envío de prueba.

## Preparar la entrada

En la aplicación portable puedes pulsar **Importar Excel** para abrir un `.xlsx` o `.xls`, elegir hoja, fila de títulos y columnas de correo, nombre y empresa. También puedes pulsar **Pegar correos** para introducir una lista separada por líneas, comas, punto y coma o tabulaciones. La aplicación crea una copia local `.mxlista` en `datos/importaciones`; el Excel original no se modifica y este paso no consulta DNS ni envía mensajes.

Desde la línea de comandos: TXT UTF-8 usa una dirección por línea, sin encabezado. CSV UTF-8 debe tener cabecera `correo`; admite columnas opcionales `nombre` y `empresa`. El comando acepta además una `.mxlista` creada por la aplicación. Para archivos Excel, usa la opción de importación de la aplicación primero.

Ejemplo del formato CSV (contenido ilustrativo, no destinatarios para contactar):

```text
correo;nombre;empresa
persona@example.com;Ana;Empresa de ejemplo
```

Detecta coma, punto y coma o tabulación. Para indicar otro nombre de columna o forzar separador:

```powershell
.\.venv\Scripts\python.exe campana.py entradas/contactos.csv --columna-correo Email --separador ";"
```

No agrupa correos en Para/CC/CCO: cada destinatario recibe un mensaje individual. No cambia la parte local a minúsculas ni elimina puntos o etiquetas `+`; por ello algunas variantes que un proveedor trata como equivalentes no se fusionan. Las exclusiones sí se comparan sin distinguir mayúsculas para evitar contactar a alguien dado de baja por una diferencia de capitalización.

## Configurar cuando responda la empresa

Guarda una copia de `campana.ejemplo.json` como `campana.json`, sin modificar el ejemplo. Guarda el texto aprobado como `mensaje.txt`. Ajusta las rutas de `mensaje.archivo_texto`, `mensaje.archivo_html` y `mensaje.adjuntos` en tu configuración. Las rutas de contenido se interpretan respecto a la carpeta del JSON.

| Campo | Qué completar |
| --- | --- |
| `campana_id` | Identificador único del comunicado, por ejemplo `aviso_septiembre_2026`. Mantenerlo al reanudar. |
| `es_ejemplo` | Cambiar a `false` solamente al completar datos reales y mensaje aprobado. |
| `remitente.correo` | Cuenta o alias autorizado desde el que se enviará. |
| `remitente.nombre` | Nombre que verán los destinatarios. |
| `remitente.responder_a` | Dirección de respuesta, o vacío para usar el remitente. |
| `mensaje.asunto` | Asunto aprobado. |
| `mensaje.archivo_texto` | Ruta del mensaje de texto; obligatorio incluso si usas HTML. |
| `mensaje.archivo_html` | Ruta HTML opcional, o vacío. |
| `mensaje.adjuntos` | Lista de archivos, por ejemplo `["adjuntos/comunicado.pdf"]`. |
| `smtp.host`, `smtp.puerto` | Servidor y puerto de envío que confirme el administrador. No son los MX de los destinatarios. |
| `smtp.seguridad` | `starttls` o `ssl`; no se admite conexión sin cifrar. |
| `smtp.autenticacion` | `password`, `oauth2` o `none` para un relay explícitamente autorizado. |
| `smtp.usuario` | Usuario que confirme el administrador; vacío solo en relay sin autenticación. |
| `smtp.secreto_env` | Nombre de la variable de entorno que contiene el secreto. Nunca pegues el secreto en este JSON. |

### Mensajes personalizados

Texto, HTML y asunto admiten `${nombre}`, `${correo}` y `${empresa}`. En TXT, nombre y empresa están vacíos. Un marcador desconocido detiene la preparación antes de enviar cualquier mensaje. Para escribir un dólar literal en una plantilla, usa `$$`. Los valores insertados en HTML se escapan.

Los adjuntos y el contenido se leen antes de pedir confirmación: se envía esa copia en memoria, aunque alguien cambie después el archivo. La muestra es del primer destinatario; revisa también las columnas de personalización de toda la lista. Se comprueba el tamaño MIME completo antes de iniciar el lote.

### Autorización y límites

Los campos de `autorizacion` son declaraciones explícitas de la persona que configura el envío; el programa no puede comprobarlas por su cuenta. Para enviar a la lista, todos deben ser `true` tras confirmarlo con la empresa:

- `remitente_autorizado`: la cuenta está autorizada para este remitente y uso.
- `envio_aprobado`: el asunto, contenido y adjuntos están aprobados.
- `lista_revisada`: los destinatarios están autorizados y el mensaje corresponde a la relación con ellos.
- `exclusiones_revisadas`: se aplicaron bajas/exclusiones, o se confirmó que no hay ninguna. El archivo de exclusiones no se descubre ni descarga automáticamente: hay que pasarlo en cada ejecución.
- `limites_confirmados`: el administrador confirmó que este envío y su ritmo cumplen los límites del proveedor.

Valores iniciales: **50 mensajes por ejecución**, 2 segundos entre mensajes, parada tras 3 errores consecutivos y máximo MIME de 10 MiB. Son límites preventivos de ejemplo, no cuotas garantizadas por el proveedor. Ajusta el lote y ritmo solo con los datos de la empresa. Los límites diarios y el uso de la cuenta por otros programas no se consultan ni controlan automáticamente.

No utilices múltiples procesos, cuentas o IDs para acelerar o eludir cuotas. No existe un planificador: el usuario inicia cada lote y espera a que termine. El script evita duplicar una dirección por campaña mediante una reserva atómica, pero el ritmo es por proceso, no un limitador global.

### Contraseña, OAuth o relay

- `password`: usa la credencial de aplicación o SMTP que autorice el servicio. El administrador debe confirmar si está permitida; no asumas que funciona la contraseña normal del correo.
- `oauth2`: soporta autenticación SMTP XOAUTH2 con un **access token ya emitido**. No registra aplicaciones, inicia sesiones OAuth, obtiene ni renueva tokens. El administrador debe proporcionar el flujo autorizado y renovar el token cuando corresponda. No confundas un access token con client secret o refresh token.
- `none`: para relay autorizado por el administrador, por ejemplo por IP. Siempre exige TLS; no busca relays abiertos ni intenta enviar directamente a los MX de cada destinatario.

En modo real se lee la variable indicada por `secreto_env`; si está ausente se pide la credencial sin mostrarla. No se guarda en los informes ni en el registro. No hace falta escribir contraseñas en el comando ni compartirlas en el chat. No actives logs de depuración SMTP con credenciales reales.

## Ejecutar en orden

Primero simula con tu configuración real:

```powershell
.\.venv\Scripts\python.exe campana.py correos.txt --config campana.json --exclusiones exclusiones.txt
```

Después prueba con **una dirección autorizada por ti/la empresa** (reemplaza el ejemplo):

```powershell
.\.venv\Scripts\python.exe campana.py --modo prueba --destino-prueba tu-direccion@tu-dominio.com --config campana.json
```

Cuando hayan comprobado la prueba y aprobado la lista:

```powershell
.\.venv\Scripts\python.exe campana.py correos.txt --modo enviar --config campana.json --exclusiones exclusiones.txt
```

Si no hay exclusiones y la empresa lo confirmó, omite `--exclusiones`; no indiques un archivo inexistente. No se conecta a SMTP hasta que escribas la frase exacta que muestra el programa, con cantidad de mensajes y campaña. Una respuesta distinta cancela sin enviar. No hay opción `--yes` que suprima esta revisión.

## Reanudar y entender los fallos

El registro está en `resultados/envios.sqlite3`. **Consérvalo y usa siempre la misma ruta e identificador para reanudar una campaña.** No lo borres ni cambies `--registro` para forzar reintentos. Guarda una copia de respaldo cuando no haya un envío en ejecución.

Para enviar el siguiente lote, repite el comando de envío con la misma lista, exclusiones, configuración y registro. Se vuelve a revisar DNS y se omiten direcciones que ya tengan estado, salvo los rechazos temporales si has pedido expresamente reintentarlos.

```powershell
.\.venv\Scripts\python.exe campana.py --modo estado --config campana.json
```

Este comando no envía ni consulta DNS; muestra cantidades y exporta un JSON con direcciones, estados, códigos y Message-ID para que el administrador investigue.

| Estado de envío | Significado y tratamiento |
| --- | --- |
| `ACEPTADO_SMTP` | El servidor de salida aceptó el mensaje. No confirma entrega al destinatario, lectura ni ausencia de rebote. Se omite al reanudar. |
| `RECHAZO_TEMPORAL` | Respuesta SMTP explícita 4xx: el lote se detiene. Solo permite reintento manual con `--reintentar-temporales`, tras revisar causa y espera necesaria. |
| `RECHAZO_PERMANENTE` | Respuesta explícita 5xx. No se reenvía automáticamente y no se interpreta necesariamente como buzón inexistente: puede ser una política o problema del remitente/contenido. |
| `INCIERTO` | Corte o fallo durante SMTP; puede que se haya aceptado. No reenvía automáticamente. |
| `EN_CURSO` | Se reservó antes de enviar y el proceso no registró resultado final. Tras una caída debe tratarse como incierto. |
| `FALLO_LOCAL` | Falta una capacidad SMTP necesaria, por ejemplo SMTPUTF8. Se detiene para revisión. |

Los errores de conexión/autenticación previos al envío dejan los destinatarios sin reservar. Ante un 4xx se detiene todo el lote para no insistir sobre un posible límite. Los fallos ambiguos no se reintentan porque SMTP no proporciona garantía general de «exactamente una vez». Un Message-ID estable ayuda a investigar, pero no obliga al proveedor a deduplicar.

El programa guarda una huella del remitente, asunto, plantillas y adjuntos. Si cambian para una campaña registrada, bloquea la reanudación con ese ID. La lista puede ampliarse manteniendo el ID, y los ya registrados se omiten. Cambiar los datos personalizados de un destinatario registrado no provoca un reenvío. Una campaña nueva con ID nuevo sí podría volver a escribir a todos: debe corresponder a un envío nuevo aprobado, no a un intento de recuperar estados inciertos.

No hay un botón para borrar estados inciertos. El administrador debe contrastar el Message-ID en su servidor antes de decidir una corrección. Los registros SQLite incluyen también el historial de intentos; el JSON de estado muestra el estado más reciente.

## Qué todavía depende de la empresa

No es un servicio universal de entregabilidad: no descubre credenciales/proveedor, no configura SPF/DKIM/DMARC, no evade límites, no comprueba buzones/catch-all, no procesa automáticamente rebotes posteriores y no gestiona un sistema de bajas. Tampoco integra APIs de proveedores sin SMTP ni renueva OAuth automáticamente.

Si el uso es marketing, la empresa debe resolver consentimiento, mecanismo de baja, lista de supresión y requisitos de su plataforma antes de activar el envío. Puedes incluir instrucciones de baja aprobadas en el cuerpo, pero este script no proporciona por sí solo un servicio de desuscripción.

Los informes, EML, registros, listas y adjuntos contienen datos privados. `resultados/`, `entradas/`, `adjuntos/`, `campana.json`, `mensaje.txt`, `mensaje.html` y `exclusiones.txt` están excluidos de Git; protege otros nombres que utilices. En simulación DNS recibe únicamente dominios; en modo real el servidor SMTP configurado recibe remitente, destinatario, mensaje y adjuntos.

Pruebas automatizadas:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas SMTP usan dobles de prueba: no envían correo real. Códigos de salida: 0 finalizado/cancelado/simulado; 1 error de preparación o conexión; 2 lote con rechazos o incertidumbre; 130 interrupción.

Referencias técnicas: [SMTP en Python](https://docs.python.org/3/library/smtplib.html), [SMTP OAuth de Microsoft](https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth), [relay de Google Workspace](https://support.google.com/a/answer/2956491).
