# Módulo de Estudios Actuariales — Actuariosa S.A.

Motor de cálculo actuarial para la provisión contable de **Jubilación Patronal** y **Bonificación por Desahucio** en Ecuador, bajo **Normas Internacionales de Información Financiera (NIC 19 / NIIF para PYMES)** y la legislación ecuatoriana.

---

## 1. Marco Legal y Técnico Aplicable

- **Código del Trabajo:**
  - **Artículos 216 al 219:** Jubilación a cargo del empleador (derecho adquirido con 25 años de servicio, o proporcional entre 20 y 24 años).
  - **Artículo 185:** Bonificación por desahucio (25% de la última remuneración mensual por año de servicio completo).
  - **Artículo 218:** Tabla de coeficientes oficiales de renta vitalicia según la edad cumplida.
- **Resolución No. 07-2021 de la Corte Nacional de Justicia:**
  - Jurisprudencia vinculante: la pensión patronal máxima no excederá la remuneración básica media del propio trabajador en su último año.
- **Resolución CI. 141 del IESS (Registro Oficial 650, 2002):**
  - Tasa técnica de interés actuarial: **4% anual**.
  - Tablas biométricas de mortalidad de pensionistas y método analítico Gompertz-Makeham.
- **NIC 19 / NIIF:**
  - Método de cálculo: **Unidad de Crédito Proyectada (Projected Unit Credit Method - PUCM)**.
  - Reconocimiento de la Obligación por Beneficios Definidos (OBD / Pasivo Actuarial), Costo del Servicio Actual y Costo Financiero.
- **Tributario (Circular SRI No. NAC-DGECCGC23-00000006):**
  - Gasto no deducible en el ejercicio en que se provisiona contablemente, con reconocimiento de **Activo por Impuesto Diferido (25%)**.

---

## 2. Estructura del Módulo

- [`generar_estudio.py`](generar_estudio.py): Punto de entrada CLI para ejecutar valoraciones y generar informes.
- [`motor_actuarial.py`](motor_actuarial.py): Motor matemático y actuarial con PUCM, cálculo de pensiones y asientos contables.
- [`tablas_actuariales.py`](tablas_actuariales.py): Coeficientes del Código del Trabajo, anualidades vitalicias $\ddot{a}_x$ y tasas de rotación.
- [`lector_censo.py`](lector_censo.py): Lector universal compatible con plantillas Excel oficiales de Actuariosa (`FORMA CONFIG`) y CSVs.
- [`censo_ejemplo.csv`](censo_ejemplo.csv): Archivo de censo con 18 empleados de prueba.
- [`test_estudios_actuariales.py`](test_estudios_actuariales.py): Pruebas unitarias automatizadas.

---

## 3. Modo de Uso

### A. Ejecutar con censo de ejemplo:
```powershell
.\.venv\Scripts\python.exe estudios_actuariales/generar_estudio.py --censo estudios_actuariales/censo_ejemplo.csv --empresa "Mi Empresa S.A." --corte 2025-12-31
```

### B. Ejecutar con la plantilla Excel de un cliente (`FORMA CONFIG`):
```powershell
.\.venv\Scripts\python.exe estudios_actuariales/generar_estudio.py --censo "ruta/al/censo_cliente.xlsx" --corte 2025-12-31
```

### Parámetros opcionales:
- `--corte YYYY-MM-DD`: Fecha de valoración actuarial (predeterminado: `2025-12-31`).
- `--tasa-descuento 0.04`: Tasa de descuento anual (predeterminado: `0.04` o 4%).
- `--tasa-salarial 0.02`: Tasa de crecimiento salarial esperada (predeterminado: `0.02` o 2%).
- `--sbu 460.00`: Salario Básico Unificado vigente en USD.
- `--salida-dir <carpeta>`: Directorio donde guardar los informes.

---

## 4. Entregables Generados

Cada ejecución produce automáticamente tres archivos listos para auditoría y contabilidad:

1. **`informe_actuarial.html`**:
   - Informe ejecutivo completo con la identidad corporativa de Actuariosa.
   - Resumen de provisiones, indicadores demográficos, propuesta de asiento contable y detalle individual por empleado.
   - Optimizado para imprimir directamente o exportar a PDF (Ctrl + P).
2. **`estudio_actuarial.json`**:
   - Estructura JSON completa y auditable con todos los valores actuariales calculados.
3. **`asiento_contable.csv`**:
   - Asiento contable de cierre fiscal (Debe a Gastos por Beneficios / Haber a Provisiones de Jubilación y Desahucio, más Activo por Impuesto Diferido).
