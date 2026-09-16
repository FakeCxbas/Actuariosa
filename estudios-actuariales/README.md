# Plataforma de Estudios Actuariales — Ecuador (NIC 19 / NIIF)

Sistema para valoración de pasivos laborales contingentes y emisión de estudios actuariales oficiales.
**Consultoría y Valoración:** Sebastian Zambrano (Guayaquil, Ecuador)

## Estructura
- `estudios_actuariales/`: Motor actuarial (PUCM), tablas biométricas IESS, topes jurisprudenciales (Res. 07-2021 Corte Nacional) y generadores de PDF oficiales.
- `actuarial_2025/fuentes/`: Censos oficiales y estudios de referencia en Excel/PDF.
- `memoria_actuarial/`: Tablas y normativas del Registro Oficial.

## Cómo ejecutar un estudio y generar el PDF oficial:
```powershell
.\.venv\Scripts\python.exe estudios_actuariales/generar_estudio_magisterio_pdf.py
.\.venv\Scripts\python.exe estudios_actuariales/generar_estudio_oficial_pdf.py
```
