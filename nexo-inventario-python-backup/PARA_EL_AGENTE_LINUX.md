Quiero continuar el mismo software de inventario para comercializarlo y adaptarlo a distintos negocios. Esta carpeta contiene Nexo Inventario, la versión desarrollada en Windows. En CachyOS ya creaste antes otra versión desde cero, pero no sé en qué carpeta quedó. Te autorizo a localizarla, comparar ambas e integrar lo mejor con tu criterio técnico.

Primero localiza el proyecto de CachyOS en las carpetas de trabajo o tareas accesibles y confirma cuál es. No supongas que esta copia de Windows es la otra versión ni que ambas bases comparten el mismo esquema. Conserva copias de los originales; trabaja en una carpeta o rama de integración separada. Si no encuentras el otro código, informa qué buscaste y pide su ubicación antes de afirmar que integraste ambas versiones.

Decide la base por funciones reales, integridad de datos, facilidad de mantenimiento, diseño y posibilidad de crecer hacia un producto comercial. Puedes descartar partes inferiores o incompatibles explicando brevemente por qué. No hace falta combinar todos los archivos. No reinicies el producto desde cero sin una razón técnica concreta.

## Versión recibida de Windows

- Python estándar + SQLite + HTML/CSS/JavaScript sin framework ni dependencias externas en ejecución.
- `inventory.py`: dominio y esquema SQLite.
- `server.py`: API HTTP y servidor local.
- `static/app.js`, `static/style.css`, `static/index.html`: interfaz.
- `desktop.py` y `build_windows.py`: lanzador y distribución Windows; no son necesarios para ejecutar en Linux.
- `iniciar-linux.sh`: arranque Linux con Python 3; usa puerto 8766 y carpeta data de esta copia por defecto.
- `README.md`: alcance y evolución.
- `VERIFICACION.md`: verificación original.
- `EMPEZAR_EN_LINUX.md`: traslado y arranque.

## Funciones implementadas

Empresas con catálogos separados, varias bodegas, productos/SKU/códigos de barras, categorías y unidades libres, mínimos globales, costos y precios, proveedores, compras multilínea con recepción completa, entradas/salidas/traslados/conteos, alertas, reportes, CSV y respaldo SQLite.

Las cantidades se almacenan como enteros en milésimas, y costos/precios unitarios como centavos. Las operaciones de inventario usan transacciones `BEGIN IMMEDIATE`, impiden saldo negativo y registran el movimiento junto con su efecto. Traslados y recepciones deben conservar su atomicidad. Los reintentos de movimientos/compras y la recepción duplicada están protegidos. Las referencias entre entidades se validan por empresa. Mantén estas garantías al integrar.

No conectar ni reutilizar credenciales, datos comerciales o bases de FacturacionBillarClub, VeraFacturacionSANVIERNES o ContaNova. Se usaron como referencias conceptuales, no se migraron sus registros.

## Límites conocidos

Edición local para un operador, no SaaS comercial completo. No hay autenticación ni roles; la separación por empresa es organizativa, todas son accesibles al operador local. Servidor en 127.0.0.1 con validación Host/token. No exponerlo a Internet como sustituto de implementar autenticación y autorización.

No hay lotes, vencimientos, series, conversiones de unidades, reservas, recetas, recepciones parciales, FIFO/costo promedio ni facturación fiscal. Valoración a costo de referencia del catálogo; compras conservan su costo de línea sin actualizar automáticamente ese costo. Pantalla de movimientos limitada a 500 recientes; exportación completa. No asumir que estas funciones ya están hechas.

## Validación y entrega

En Windows pasaron 28 pruebas de dominio/HTTP, comprobación de sintaxis JS y una prueba del ejecutable con persistencia y respaldo. Se probaron altas, stock decimal, rechazo de salidas excesivas, recepción de compra y separación de empresas en navegador. No se ha probado esta entrega ejecutándose en CachyOS.

Ejecuta `python3 -m unittest discover -s tests -v`, arranca con `bash iniciar-linux.sh` y verifica los flujos de interfaz en Linux. Adapta y añade pruebas cuando la integración cambie comportamiento. No ejecutes `tests/smoke_distribution.py` en Linux: comprueba un .exe Windows.

Un respaldo opcional `nexo-datos-windows.sqlite3` se entrega fuera del ZIP de código. No importarlo encima del proyecto de CachyOS ni mezclarlo automáticamente con su base. Usa una base temporal o una copia aislada para comparar.

Deja una única versión principal con documentación de qué se tomó de cada proyecto. Usa Git local para mantener la historia y preparar la sincronización entre Windows y Linux. No publiques un repositorio ni subas bases/secretos sin que yo indique el destino y autorice su publicación.
