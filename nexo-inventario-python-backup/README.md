# Nexo Inventario

Software nuevo de inventario, desarrollado como proyecto independiente a partir de los conceptos de bodega y catálogo encontrados en FacturacionBillarClub, VeraFacturacionSANVIERNES y ContaNova. No reutiliza sus credenciales, bases de datos, marcas de clientes ni registros comerciales. Implementación nueva con Python, SQLite y una interfaz de navegador sin dependencias externas.

## Ejecutar

```powershell
python server.py
```

Abre `http://127.0.0.1:8765`. Los datos se guardan por defecto en `%LOCALAPPDATA%\NexoInventario\data\nexo.sqlite3`. Para un entorno de pruebas separado:

```powershell
python server.py --no-browser --port 8766 --data-dir data-pruebas
```

Para el lanzador de escritorio: `python desktop.py`. Para distribuirlo, usa el ZIP de `dist/`; contiene un ejecutable y su carpeta de dependencias, sin datos de usuario.

## Funciones implementadas

- Alta de empresas independientes, moneda por empresa y bodega inicial.
- Catálogo con SKU, código de barras, categorías/unidades libres, costo, precio, notas y mínimo global por producto.
- Edición de productos. Unidad bloqueada cuando ya existen movimientos o compras para evitar reinterpretar cantidades.
- Existencias por bodega; entradas, salidas, traslados y ajustes por conteo físico.
- Operaciones transaccionales, rechazo del stock negativo e identificadores contra reintentos duplicados.
- Proveedores y órdenes con varias líneas; cancelación y recepción completa e idempotente.
- Panel, búsqueda, filtros, alertas y valoración a costo de referencia.
- Exportación CSV de catálogo e historial completo. Impresión de reportes.
- Importación atómica de CSV: valida todas las filas; no sobreescribe SKU ni descarta stock silenciosamente.
- Respaldo consistente mediante la API de backup de SQLite.
- Empresa demo separada. Formularios adaptables a móvil y escritorio.

## Integridad y límites

Las cantidades se guardan como enteros en milésimas y los importes unitarios como centavos. No se usa aritmética binaria de punto flotante para persistir cantidades. Cada cambio de existencias y su movimiento se confirman dentro de un `BEGIN IMMEDIATE`. Un traslado realiza ambos cambios o ninguno. El descuento de stock no fuerza el saldo a cero cuando falta inventario.

La API valida que los productos, bodegas, proveedores y órdenes pertenezcan a la misma empresa. Esta separación es organizativa, no autorización entre usuarios: la edición local no implementa cuentas ni roles. Escucha únicamente en loopback, valida Host y exige un token de la sesión local en las solicitudes de datos. No publicarla por un proxy ni cambiarla a 0.0.0.0 como sustituto de un diseño SaaS.

Los movimientos se consultan en una instantánea consistente; la pantalla presenta los últimos 500 y el CSV contiene todo el historial. La gráfica usa ese mismo conjunto y lo indica cuando está truncado. El panel contabiliza operaciones para no sumar kg, metros y unidades como una cantidad indistinta.

El mínimo es global por producto. En el filtro de una bodega se muestra como referencia, no como política de reposición específica por ubicación. Las órdenes tienen recepción completa: no hay recepciones parciales ni cuentas por pagar. La valoración es existencias por costo de referencia, sin impuestos ni FIFO/promedio; los costos de la orden permanecen en sus líneas y no sustituyen automáticamente el costo del catálogo.

## Comprobaciones

```powershell
python -m unittest discover -s tests -v
node --check static/app.js
```

Las pruebas cubren decimales exactos, concurrencia, traslados, rollback, aislamiento de referencias por empresa, idempotencia, conteos, compras, importación, exportación, persistencia, respaldos y protección HTTP local.

## Empaquetar Windows

Instala PyInstaller 6.21.0 en el entorno de construcción y ejecuta:

```powershell
python build_windows.py
```

Genera `dist/NexoInventario-Windows-0.1.0.zip`. No incluye la carpeta de datos. El usuario final no necesita Python ni Node. Ver `LEEME_WINDOWS.txt` para uso y restauración de respaldos.

## Evolución del producto

La base común admite comercios, ferreterías, distribuidores, textiles e insumos medidos por peso, volumen o longitud. La promesa de servir a todos los sectores requiere módulos especializados; no se presentan como implementados:

1. Operación empresarial: usuarios, roles, auditoría por operador, archivado de artículos/proveedores, conteos por sesión, mínimos por bodega y recepciones parciales.
2. Trazabilidad especializada: lotes, vencimientos, números de serie, conversiones, variantes estructuradas, devoluciones y reservas.
3. Costeo: promedio ponderado/FIFO, costos de importación y conciliación de valoración.
4. Producción y gastronomía: recetas, listas de materiales, consumos y mermas.
5. Comercialización en nube: base PostgreSQL, autenticación, aislamiento verificable por cliente, observabilidad, recuperación, licenciamiento y actualizaciones firmadas. La API de dominio y la interfaz están separadas, pero esta migración requiere trabajo explícito.

No se modificaron ni conectaron los proyectos originales. El nombre Nexo es provisional.
