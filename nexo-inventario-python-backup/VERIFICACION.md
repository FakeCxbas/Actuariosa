# Verificación de la versión 0.1.0

Realizada el 6 de septiembre de 2026 (hora de Ecuador).

## Resultados

- 28 pruebas automáticas: todas aprobadas con `python -m unittest discover -s tests -v`.
- Sintaxis JavaScript: aprobada con `node --check static/app.js`.
- Ejecutable Windows: aprobado con `python tests/smoke_distribution.py`.
- El ejecutable inició con datos temporales, sirvió todos sus recursos, creó una empresa y un producto, registró 4,125 unidades, exportó CSV, generó un respaldo íntegro y conservó las existencias al reiniciar el proceso.

## Recorridos de interfaz realizados

- Crear una empresa demo independiente.
- Crear producto con SKU y unidad kg.
- Registrar entrada de 12,375 kg.
- Intentar salida de 100 kg: rechazo visible por stock insuficiente, sin alteración del saldo.
- Crear una compra de 2,125 kg y recibirla: saldo resultante 14,5 kg.
- Recargar la aplicación: datos conservados.
- Crear una bodega y un proveedor desde la interfaz móvil.
- Crear otra empresa: catálogo vacío, una bodega inicial y saldos en cero.
- Navegar por el menú móvil y revisar el panel en 390 px y 1440 px.
- Sin errores de consola detectados durante los recorridos.

Las pruebas de interfaz se realizaron en una base de desarrollo dentro de `data/`. Esa base no se distribuye en el ZIP. La demo abierta para presentación es independiente de los registros utilizados durante la validación.

## Límites de la validación

No se efectuaron pruebas con usuarios externos, cargas masivas sostenidas, permisos multiusuario o despliegue en nube, porque esta entrega es una edición local para un operador. El empaquetado se ejecutó y verificó en este equipo Windows; no se probó en otras versiones del sistema operativo. Las capacidades especializadas pendientes se enumeran en README.md.
