# Nexo · Inventario

Aplicación web privada en español para PC, teléfono y tablet. Catálogo, sucursales, proveedores, entradas, salidas, transferencias, conteos, alertas, gráficos, historial paginado y exportaciones. Acceso de propietario a través de Sites; no se ha abierto a otras personas.

## Portabilidad y control (segunda versión)

- Manifest e iconos para instalación PWA compatible. Control → Instalar. El service worker solo responde con una pantalla informativa cuando una navegación falla; no almacena páginas privadas, datos, tokens ni respuestas API. Sin conexión se bloquea el envío y no se simulan operaciones guardadas.
- Revisión ligera cada minuto solo con la pestaña visible, más al volver o reconectar. Una versión central cambia con cada mutación mediante triggers. Sin cambios no se transmiten catálogo ni historial. No se promete tiempo real.
- Historial completo paginado en servidor (25 filas), CSV coherente de hasta 10.000 movimientos filtrados en una consulta y gráfico con agregados diarios UTC de 31 días. El catálogo y saldos siguen siendo una instantánea completa en cada cambio; hace falta particionarlos para volúmenes grandes.
- Conteos con versión esperada, ediciones optimistas, movimientos idempotentes con huella de contenido y protección ante salidas simultáneas. El costo de referencia en centavos queda fijado en cada movimiento nuevo. Una unidad de medida no cambia después del primer movimiento.
- Conciliación entre saldo y libro de movimientos; bitácora de altas y cambios de productos, proveedores y sucursales (antes/después), desde esta versión. No es atribución de identidad por empleado.
- Respaldo completo JSON + SHA-256 hasta 50.000 registros / 16 MB de payload. Exportaciones más grandes requieren un proceso administrado. Restauración a SQLite NUEVO con verificación de huella, referencias y esquema: `python3 scripts/restore-backup.py copia.json nueva-base.sqlite`. No restaura ni sobrescribe producción. Para migrar a otro alojamiento también hay que adaptar el acceso, el binding de datos y el despliegue.
- Análisis y calculadora económica en `/viabilidad.html`, con tarifas de infraestructura directa como referencia; no son la tarifa de Sites ni una factura real.

## Desarrollo y validación

`npm install`, `npm run dev`. Aplicar las migraciones de `drizzle/` a la base local antes de usar la API. `npm run db:generate` genera deltas; no modificar migraciones ya publicadas. Sites aplica migraciones al desplegar.

`npx tsc --noEmit`, `npm run build`.

`node tests/inventory.mjs` y `node tests/hardening.mjs` contra localhost:3000 o `INVENTORY_TEST_URL`. **Solo contra una base de pruebas**: crean datos y prueban movimientos.

Se probaron entradas, salidas, transferencias atómicas, conteos, unicidad SKU, idempotencia simultánea, conflicto de payload, conteos y salidas simultáneos, ediciones obsoletas, bloqueo de unidades con historial, conciliación, bitácora, paginación, conservación del costo y checksum. Se restauró una copia local a SQLite y se compararon conteos, foreign keys e integridad; se rechazaron sobrescritura y archivo alterado. Se verificó que la consulta de últimos movimientos usa su índice.

No hubo pruebas visuales ni instalación real en iOS/Android en este turno; el soporte varía por navegador. La herramienta WebMCP opcional `search_inventory` mantiene el registro condicionado al soporte de `document.modelContext`; no se dispuso de un contexto de validación WebMCP.

## Límites antes de escalar a una gran cadena

Usuarios y roles por sucursal, separación por empresa, identidad de auditoría, transferencias con recepción, órdenes de compra, reservas, lotes/series, variantes, unidades fraccionarias, integraciones POS, copias externas programadas, monitoreo y pruebas de carga aún pendientes. Las transferencias actualizan ambos saldos al confirmar, no modelan tránsito físico. Vencimiento por producto, no lote. Valoración al costo de referencia, no método contable FIFO/promedio. Moneda USD. No hay escrituras offline ni cola de sincronización. La conciliación valida registros, no sustituye conteos físicos.
