"""
Generador del Estudio Actuarial Formal Profesional (Formato Pericial Clásico)
COOPERATIVA DE AHORRO Y CRÉDITO MAGISTERIO MANABITA LTDA.

Autor: Sebastian Zambrano · Guayaquil, Ecuador
Diseño formal de auditoría y peritaje contable-actuarial ecuatoriano (sin estética de plantilla web/IA).
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def formatear_usd(valor: float) -> str:
    return f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def construir_documento_magisterio_html() -> str:
    emp = "COOPERATIVA DE AHORRO Y CRÉDITO MAGISTERIO MANABITA LTDA."
    ruc = "1390027763001"
    ciudad = "Portoviejo, Manabí, Ecuador"
    corte = "31 de diciembre de 2025"
    autor = "Sebastian Zambrano"
    ubicacion_autor = "Guayaquil, Ecuador"

    # Los 18 colaboradores reales de Magisterio Manabita
    empleados_data = [
        {"num": 1, "nombre": "MENDOZA ZAMBRANO BIELKA MARIA", "antiguedad": "1 a 9 m", "jubilacion": 664.62, "desahucio": 369.28},
        {"num": 2, "nombre": "CASTRO ANZULEZ LUIS MANUEL", "antiguedad": "1 a 9 m", "jubilacion": 483.41, "desahucio": 312.47},
        {"num": 3, "nombre": "CEDEÑO JARAMILLO JESSENIA ELIZABETH", "antiguedad": "3 a 7 m", "jubilacion": 1599.91, "desahucio": 824.83},
        {"num": 4, "nombre": "ESMENJAUD PONCE ELIANA MAILY", "antiguedad": "3 a 9 m", "jubilacion": 1468.86, "desahucio": 697.53},
        {"num": 5, "nombre": "PARRAGA RIVAS HENRY GEOVANNY", "antiguedad": "6 a 4 m", "jubilacion": 1649.88, "desahucio": 1121.52},
        {"num": 6, "nombre": "VERA ALAVA ANGEL GABRIEL", "antiguedad": "9 a 8 m", "jubilacion": 3020.75, "desahucio": 1411.89},
        {"num": 7, "nombre": "GARCIA SONOZA MARIA CRISTINA", "antiguedad": "10 a 8 m", "jubilacion": 4881.69, "desahucio": 2874.33},
        {"num": 8, "nombre": "ZAMBRANO RIVERA BRENSKIN PASKALINE", "antiguedad": "14 a 8 m", "jubilacion": 9224.06, "desahucio": 5205.25},
        {"num": 9, "nombre": "MENENDEZ LOPEZ GILMA DANIELA", "antiguedad": "16 a 8 m", "jubilacion": 13288.43, "desahucio": 5975.82},
        {"num": 10, "nombre": "CEDEÑO MOREIRA FREDDY WILSON", "antiguedad": "18 a 6 m", "jubilacion": 9618.35, "desahucio": 4077.87},
        {"num": 11, "nombre": "MORAN CASTRO STELA MARIA", "antiguedad": "18 a 8 m", "jubilacion": 11953.53, "desahucio": 4933.55},
        {"num": 12, "nombre": "ZAMORA HERNANDEZ SONIA GEOCONDA", "antiguedad": "21 a 1 m", "jubilacion": 12962.35, "desahucio": 5291.05},
        {"num": 13, "nombre": "ZAMBRANO INTRIAGO KAREN VANESSA", "antiguedad": "25 a 3 m", "jubilacion": 21014.77, "desahucio": 6312.49},
        {"num": 14, "nombre": "CEDEÑO CEDEÑO LILIANA MARIA", "antiguedad": "30 a 11 m", "jubilacion": 24029.67, "desahucio": 8086.73},
        {"num": 15, "nombre": "BARRAGAN OZAETA ANGELA MARIA", "antiguedad": "34 a 11 m", "jubilacion": 35683.55, "desahucio": 12328.76},
        {"num": 16, "nombre": "AZUA SANTANA VICENTA JASMINA", "antiguedad": "38 a 0 m", "jubilacion": 41492.09, "desahucio": 14629.04},
        {"num": 17, "nombre": "VELIZ GARCIA JUANA ALEXANDRA", "antiguedad": "39 a 5 m", "jubilacion": 39204.09, "desahucio": 13895.24},
        {"num": 18, "nombre": "LOOR MARIA IVANOBA", "antiguedad": "41 a 2 m", "jubilacion": 17798.50, "desahucio": 6312.49},
    ]

    filas_anexo = ""
    for emp_row in empleados_data:
        tot_ind = emp_row["jubilacion"] + emp_row["desahucio"]
        filas_anexo += f"""
        <tr>
            <td style="text-align:center;">{emp_row['num']}</td>
            <td>{emp_row['nombre']}</td>
            <td style="text-align:center;">{emp_row['antiguedad']}</td>
            <td style="text-align:right;">{formatear_usd(emp_row['jubilacion'])}</td>
            <td style="text-align:right;">{formatear_usd(emp_row['desahucio'])}</td>
            <td style="text-align:right; font-weight:bold;">{formatear_usd(tot_ind)}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title></title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 0;
        }}
        @media print {{
            @page {{
                size: A4 portrait;
                margin: 0;
            }}
        }}
        * {{
            box-sizing: border-box;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}
        body {{
            font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
            color: #111111;
            background: #ffffff;
            margin: 0;
            padding: 0;
            font-size: 9.5pt;
            line-height: 1.4;
        }}

        .page {{
            page-break-after: always;
            page-break-inside: avoid;
            box-sizing: border-box;
            width: 210mm;
            height: 297mm;
            max-height: 297mm;
            padding: 16mm 18mm 16mm 18mm;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            background: #ffffff;
            overflow: hidden;
        }}

        /* PORTADA PERICIAL CLÁSICA */
        .portada {{
            text-align: center;
            justify-content: space-between;
            padding: 35mm 20mm 25mm 20mm;
        }}
        .portada-header {{
            margin-bottom: 20px;
        }}
        .portada-empresa {{
            font-size: 15pt;
            font-weight: bold;
            color: #000000;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            line-height: 1.3;
        }}
        .portada-sub {{
            font-size: 9.5pt;
            color: #333333;
            margin-top: 6px;
        }}
        .portada-cuerpo {{
            margin: 40px 0;
        }}
        .portada-subtitulo {{
            font-size: 11pt;
            font-weight: bold;
            color: #222222;
            letter-spacing: 1px;
            margin-bottom: 12px;
            text-transform: uppercase;
        }}
        .portada-titulo {{
            font-size: 14pt;
            font-weight: bold;
            color: #000000;
            line-height: 1.4;
            text-transform: uppercase;
            margin-bottom: 14px;
        }}
        .portada-norma {{
            font-size: 10pt;
            font-weight: bold;
            color: #222222;
            letter-spacing: 0.5px;
            margin-bottom: 18px;
        }}
        .portada-corte {{
            font-size: 10.5pt;
            font-weight: bold;
            color: #111111;
            text-transform: uppercase;
            border-top: 1px solid #444444;
            border-bottom: 1px solid #444444;
            display: inline-block;
            padding: 6px 20px;
            margin-top: 10px;
        }}
        .portada-footer {{
            border-top: 1px solid #666666;
            padding-top: 14px;
            font-size: 10pt;
            line-height: 1.4;
        }}
        .author-name {{
            font-size: 12pt;
            font-weight: bold;
            color: #000000;
        }}
        .author-title {{
            font-size: 9.5pt;
            color: #333333;
        }}

        /* ENCABEZADOS DISCRETOS DE AUDITORÍA */
        .doc-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            border-bottom: 1px solid #222222;
            padding-bottom: 4px;
            margin-bottom: 14px;
            font-size: 8pt;
            color: #444444;
            text-transform: uppercase;
        }}
        .doc-header .dh-left {{
            font-weight: bold;
            color: #000000;
            max-width: 60%;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .doc-header .dh-right {{
            text-align: right;
            white-space: nowrap;
        }}

        /* PIE DE PÁGINA */
        .doc-footer {{
            display: flex;
            justify-content: space-between;
            border-top: 1px solid #888888;
            padding-top: 4px;
            font-size: 7.5pt;
            color: #555555;
            margin-top: auto;
        }}

        /* TIPOGRAFÍA FORMAL */
        h2 {{
            font-size: 11pt;
            font-weight: bold;
            color: #000000;
            text-transform: uppercase;
            margin: 10px 0 6px 0;
            padding-bottom: 2px;
            border-bottom: 0.5pt solid #888888;
        }}
        h3 {{
            font-size: 9.5pt;
            font-weight: bold;
            color: #111111;
            margin: 8px 0 4px 0;
        }}
        p {{
            text-align: justify;
            margin-bottom: 6px;
            font-size: 9pt;
            line-height: 1.38;
        }}
        ul {{
            margin: 4px 0 8px 18px;
            font-size: 9pt;
        }}
        li {{
            margin-bottom: 2px;
        }}

        /* TABLAS FORMALES CLÁSICAS DE AUDITORÍA */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 8px 0 10px 0;
            font-size: 8.5pt;
        }}
        th, td {{
            border: 0.5pt solid #555555;
            padding: 4px 6px;
        }}
        th {{
            background: #f0f0f0;
            color: #000000;
            font-weight: bold;
            text-align: center;
        }}
        .table-title {{
            font-size: 8.5pt;
            font-weight: bold;
            text-align: center;
            margin-top: 6px;
            margin-bottom: 3px;
            text-transform: uppercase;
        }}

        /* CAJAS RESUMEN CLÁSICAS (SIN ESTÉTICA IA NI CARDS) */
        .tabla-resumen {{
            margin: 10px 0;
        }}
        .tabla-resumen td {{
            padding: 5px 8px;
        }}

        /* FIRMAS */
        .firma-container {{
            margin-top: 25px;
            display: flex;
            justify-content: space-around;
            text-align: center;
        }}
        .firma-box {{
            width: 44%;
            border-top: 1px solid #000000;
            padding-top: 6px;
            font-size: 8.5pt;
            line-height: 1.35;
        }}
    </style>
</head>
<body>

    <!-- PÁGINA 1: CARÁTULA FORMAL -->
    <div class="page portada">
        <div class="portada-header">
            <div class="portada-empresa">{emp}</div>
            <div class="portada-sub">RUC: {ruc} · {ciudad}</div>
        </div>

        <div class="portada-cuerpo">
            <div class="portada-subtitulo">INFORME DE VALORACIÓN ACTUARIAL</div>
            <div class="portada-titulo">
                PROVISIÓN PARA JUBILACIÓN PATRONAL<br>
                Y BONIFICACIÓN POR DESAHUCIO
            </div>
            <div class="portada-norma">NORMA INTERNACIONAL DE CONTABILIDAD No. 19 (NIC 19 / NIIF)</div>
            <div class="portada-corte">AL {corte.upper()}</div>
        </div>

        <div class="portada-footer">
            <div class="author-name">{autor}</div>
            <div class="author-title">Consultoría Actuarial</div>
            <div style="font-size:9pt; color:#444444; margin-top:4px;">{ubicacion_autor}</div>
        </div>
    </div>

    <!-- PÁGINA 2: ANTECEDENTES Y RESUMEN EJECUTIVO -->
    <div class="page">
        <div>
            <div class="doc-header">
                <span class="dh-left">COOP. DE AHORRO Y CRÉDITO MAGISTERIO MANABITA LTDA.</span>
                <span class="dh-right">ESTUDIO ACTUARIAL · NIC 19</span>
            </div>

            <h2>1. Antecedentes e Información General</h2>
            <p>
                La <strong>COOPERATIVA DE AHORRO Y CRÉDITO MAGISTERIO MANABITA LTDA.</strong> fue legalmente constituida el 7 de agosto de 1952, en la ciudad de Portoviejo, capital de la provincia de Manabí, con estatutos sociales aprobados mediante Acuerdo Ministerial No. 2492 de fecha 24 de febrero de 1955. La institución tiene como objeto social la intermediación financiera y prestación de servicios de ahorro y crédito para los servidores de la educación y comunidad en general.
            </p>
            <p>
                A fin de dar estricto cumplimiento a lo preceptuado en el Código del Trabajo y en la <strong>Norma Internacional de Contabilidad No. 19 (NIC 19 — Beneficios a los Empleados)</strong>, la administración de la institución dispuso la elaboración del presente informe técnico de valoración actuarial, con fecha de corte al <strong>{corte}</strong>, destinado a determinar las provisiones y obligaciones por <strong>Jubilación Patronal</strong> (Art. 216) y <strong>Bonificación por Desahucio</strong> (Art. 185).
            </p>

            <h2>2. Resumen Ejecutivo de la Obligación Actuarial</h2>
            <p>
                El colectivo de servidores evaluado bajo relación de dependencia está integrado por <strong>dieciocho (18) personas activas</strong> (14 mujeres y 4 hombres). La edad actual de los trabajadores oscila entre los 26 y 60 años, situándose la edad promedio en <strong>47,0 años</strong>. La permanencia ininterrumpida dentro de la empresa comprende desde 1 año 9 meses hasta 41 años 2 meses, con un promedio de <strong>19,0 años de servicio</strong>. El sueldo mensual computable promedio asciende a <strong>$981,00 USD</strong>.
            </p>

            <table class="tabla-resumen">
                <thead>
                    <tr>
                        <th style="text-align:left; width:55%;">Concepto de Prestación Laboral (NIC 19)</th>
                        <th style="width:20%;">Base Legal</th>
                        <th style="width:25%; text-align:right;">Provisión al 31/12/2025</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Provisión por Jubilación Patronal a cargo del Empleador</td>
                        <td style="text-align:center;">Art. 216 C.T.</td>
                        <td style="text-align:right; font-weight:bold;">$250.038,48</td>
                    </tr>
                    <tr>
                        <td>Provisión para Bonificación por Desahucio</td>
                        <td style="text-align:center;">Art. 185 C.T.</td>
                        <td style="text-align:right; font-weight:bold;">$94.660,12</td>
                    </tr>
                    <tr style="background:#f0f0f0; font-weight:bold;">
                        <td>OBLIGACIÓN TOTAL POR BENEFICIOS DEFINIDOS (PASIVO NIC 19)</td>
                        <td style="text-align:center;">NIC 19.64</td>
                        <td style="text-align:right; font-size:9.5pt;">$344.698,60</td>
                    </tr>
                    <tr>
                        <td>Activo por Impuesto a la Renta Diferido Reconocido (Tasa 25%)</td>
                        <td style="text-align:center;">Circular SRI</td>
                        <td style="text-align:right; font-weight:bold;">$86.174,65</td>
                    </tr>
                </tbody>
            </table>

            <p>
                La institución no mantiene a la fecha ex-empleados percibiendo pensión patronal activa. Se identifican <strong>siete (7) colaboradores</strong> con más de veinte años de antigüedad (seis de ellos superando los 25 años), quienes poseen el derecho perfeccionado para acogerse a la jubilación patronal al momento de su retiro voluntario.
            </p>
            <p>
                Conforme a la <em>Ley Orgánica para el Desarrollo Económico y Sostenibilidad Fiscal</em>, la provisión total calculada constituye gasto no deducible del ejercicio fiscal corriente; no obstante, genera una diferencia temporaria deducible que da origen al registro de un <strong>Activo por Impuesto Diferido del 25% por un valor de $86.174,65</strong>, amortizable tributariamente al momento del pago efectivo de la prestación.
            </p>
        </div>

        <div class="doc-footer">
            <span>{autor} · Consultoría Actuarial ({ubicacion_autor})</span>
            <span>Página 2</span>
        </div>
    </div>

    <!-- PÁGINA 3: SECCIÓN A - JUBILACIÓN PATRONAL -->
    <div class="page">
        <div>
            <div class="doc-header">
                <span class="dh-left">COOP. DE AHORRO Y CRÉDITO MAGISTERIO MANABITA LTDA.</span>
                <span class="dh-right">ESTUDIO ACTUARIAL · NIC 19</span>
            </div>

            <h2>A. Jubilación a Cargo del Empleador (Art. 216)</h2>
            
            <h3>1. Base Legal y Precedente Jurisprudencial</h3>
            <p>
                El Artículo 216 del Código del Trabajo establece que los trabajadores que por 25 años o más hubieren prestado servicios continua o interrumpidamente, tendrán derecho a ser jubilados por sus empleadores. Quienes cumplieren 20 años y menos de 25 años y fueren separados intempestivamente, tienen derecho a la parte proporcional de dicha prestación.
            </p>
            <p>
                En estricta observancia de la <strong>Resolución No. 07-2021 expedida por el Pleno de la Corte Nacional de Justicia</strong> (precedente vinculante), la pensión mensual de jubilación patronal no podrá exceder de la remuneración básica mínima unificada media percibida por el trabajador en el último año de servicio, sujetándose al límite mínimo de $20,00 USD (doble jubilación) o $30,00 USD (jubilación única).
            </p>

            <h3>2. Colectivo Activo y Demografía</h3>
            <div class="table-title">Distribución del Colectivo por Género</div>
            <table>
                <thead>
                    <tr>
                        <th>Género</th>
                        <th>Número Servidores</th>
                        <th>Edad Promedio</th>
                        <th>Tiempo de Servicio</th>
                        <th>Remuneración Promedio</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Femenino</td>
                        <td style="text-align:center;">14</td>
                        <td style="text-align:center;">46,5 años</td>
                        <td style="text-align:center;">19,4 años</td>
                        <td style="text-align:right;">$1.076,00</td>
                    </tr>
                    <tr>
                        <td>Masculino</td>
                        <td style="text-align:center;">4</td>
                        <td style="text-align:center;">49,0 años</td>
                        <td style="text-align:center;">17,5 años</td>
                        <td style="text-align:right;">$650,00</td>
                    </tr>
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td>TOTAL GENERAL</td>
                        <td style="text-align:center;">18</td>
                        <td style="text-align:center;">47,0 años</td>
                        <td style="text-align:center;">19,0 años</td>
                        <td style="text-align:right;">$981,00</td>
                    </tr>
                </tbody>
            </table>

            <h3>3. Hipótesis Actuariales y Financieras</h3>
            <ul>
                <li><strong>Tasa Técnica de Descuento Actuarial:</strong> 4,00% efectivo anual (Resolución CI. 141 del IESS).</li>
                <li><strong>Tasa de Interés Financiero Pasiva:</strong> 6,34% anual (Promedio referencial publicado por el BCE).</li>
                <li><strong>Tasa de Inflación a Largo Plazo:</strong> 2,23% anual promedio bajo dolarización.</li>
                <li><strong>Crecimiento Salarial Futuro:</strong> 3,00% anual constante para sueldos menores a $984 USD; constante para remuneraciones superiores.</li>
                <li><strong>Incremento Anual de RBU:</strong> 2,90% anual constante.</li>
                <li><strong>Tablas Biométricas de Mortalidad:</strong> Coeficientes del Art. 218 del Código del Trabajo y Tabla de Activos IESS 1995/2000.</li>
            </ul>

            <h3>4. Provisión Acumulada según Segmentación de Antigüedad</h3>
            <table>
                <thead>
                    <tr>
                        <th>Segmento de Antigüedad</th>
                        <th>No. Personas</th>
                        <th>Obligación Financiera Acumulada</th>
                        <th>Provisión Asentada en Balance</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Personal con menos de 20 años de servicio</td>
                        <td style="text-align:center;">11</td>
                        <td style="text-align:right;">$82.410,20</td>
                        <td style="text-align:right;">$57.853,47</td>
                    </tr>
                    <tr>
                        <td>Personal con 20 o más años de servicio (Derecho Adquirido)</td>
                        <td style="text-align:center;">7</td>
                        <td style="text-align:right;">$235.321,15</td>
                        <td style="text-align:right;">$192.185,01</td>
                    </tr>
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td>TOTAL PROVISIÓN JUBILACIÓN PATRONAL</td>
                        <td style="text-align:center;">18</td>
                        <td style="text-align:right;">$317.731,35</td>
                        <td style="text-align:right;">$250.038,48</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="doc-footer">
            <span>{autor} · Consultoría Actuarial ({ubicacion_autor})</span>
            <span>Página 3</span>
        </div>
    </div>

    <!-- PÁGINA 4: SECCIÓN B Y REGISTRO CONTABLE -->
    <div class="page">
        <div>
            <div class="doc-header">
                <span class="dh-left">COOP. DE AHORRO Y CRÉDITO MAGISTERIO MANABITA LTDA.</span>
                <span class="dh-right">ESTUDIO ACTUARIAL · NIC 19</span>
            </div>

            <h2>B. Bonificación por Desahucio (Art. 185)</h2>
            <p>
                El Artículo 185 del Código del Trabajo preceptúa que en los casos de terminación del contrato individual, el empleador bonificará al trabajador con el 25% del equivalente a la última remuneración mensual por cada año de servicios prestados.
            </p>

            <div class="table-title">Distribución de Provisión por Desahucio</div>
            <table>
                <thead>
                    <tr>
                        <th>Tiempo de Servicio (TS)</th>
                        <th>No. Servidores</th>
                        <th>Costo del Período</th>
                        <th>Provisión Acumulada</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Trabajadores con TS &lt; 10 años</td>
                        <td style="text-align:center;">6</td>
                        <td style="text-align:right;">$4.737,52</td>
                        <td style="text-align:right;">$4.737,52</td>
                    </tr>
                    <tr>
                        <td>Trabajadores con TS &ge; 10 y &lt; 20 años</td>
                        <td style="text-align:center;">5</td>
                        <td style="text-align:right;">$23.066,81</td>
                        <td style="text-align:right;">$23.066,81</td>
                    </tr>
                    <tr>
                        <td>Trabajadores con TS &ge; 20 años</td>
                        <td style="text-align:center;">7</td>
                        <td style="text-align:right;">$66.855,79</td>
                        <td style="text-align:right;">$66.855,79</td>
                    </tr>
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td>TOTAL BONIFICACIÓN POR DESAHUCIO</td>
                        <td style="text-align:center;">18</td>
                        <td style="text-align:right;">$94.660,12</td>
                        <td style="text-align:right;">$94.660,12</td>
                    </tr>
                </tbody>
            </table>

            <h2>C. Asientos Contables Oficiales de Cierre</h2>
            <div class="table-title">Asiento 1: Provisión de Pasivo Laboral Post-Empleo (NIC 19)</div>
            <table>
                <thead>
                    <tr>
                        <th style="text-align:left;">Cuenta y Detalle Contable</th>
                        <th>Parcial</th>
                        <th>Debe</th>
                        <th>Haber</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>GASTOS GENERALES NO DEDUCIBLES</strong></td>
                        <td></td>
                        <td style="text-align:right; font-weight:bold;">$344.698,60</td>
                        <td></td>
                    </tr>
                    <tr>
                        <td style="padding-left:14px;">- Provisión Jubilación Patronal (&lt; 20 años de servicio)</td>
                        <td style="text-align:right;">$57.853,47</td>
                        <td></td>
                        <td></td>
                    </tr>
                    <tr>
                        <td style="padding-left:14px;">- Provisión Jubilación Patronal (&ge; 20 años de servicio)</td>
                        <td style="text-align:right;">$192.185,01</td>
                        <td></td>
                        <td></td>
                    </tr>
                    <tr>
                        <td style="padding-left:14px;">- Provisión Bonificación por Desahucio</td>
                        <td style="text-align:right;">$94.660,12</td>
                        <td></td>
                        <td></td>
                    </tr>
                    <tr>
                        <td><strong>OBLIGACIONES BENEFICIOS POST-EMPLEO (NIC 19)</strong></td>
                        <td></td>
                        <td></td>
                        <td style="text-align:right; font-weight:bold;">$344.698,60</td>
                    </tr>
                    <tr>
                        <td style="padding-left:14px;">- Pasivo Jubilación Patronal Acumulado</td>
                        <td style="text-align:right;">$250.038,48</td>
                        <td></td>
                        <td></td>
                    </tr>
                    <tr>
                        <td style="padding-left:14px;">- Pasivo Bonificación por Desahucio Acumulado</td>
                        <td style="text-align:right;">$94.660,12</td>
                        <td></td>
                        <td></td>
                    </tr>
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td>SUMAS IGUALES</td>
                        <td></td>
                        <td style="text-align:right;">$344.698,60</td>
                        <td style="text-align:right;">$344.698,60</td>
                    </tr>
                </tbody>
            </table>

            <div class="table-title">Asiento 2: Reconocimiento del Activo por Impuesto Diferido (25%)</div>
            <table>
                <thead>
                    <tr>
                        <th style="text-align:left;">Cuenta y Detalle Contable</th>
                        <th>Parcial</th>
                        <th>Debe</th>
                        <th>Haber</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>ACTIVO POR IMPUESTO DIFERIDO (Diferencias Temporarias)</strong></td>
                        <td></td>
                        <td style="text-align:right; font-weight:bold;">$86.174,65</td>
                        <td></td>
                    </tr>
                    <tr>
                        <td style="padding-left:14px;">- 25% sobre Provisión Jubilación Patronal ($250.038,48)</td>
                        <td style="text-align:right;">$62.509,62</td>
                        <td></td>
                        <td></td>
                    </tr>
                    <tr>
                        <td style="padding-left:14px;">- 25% sobre Provisión Desahucio ($94.660,12)</td>
                        <td style="text-align:right;">$23.665,03</td>
                        <td></td>
                        <td></td>
                    </tr>
                    <tr>
                        <td><strong>INGRESO POR IMPUESTO DIFERIDO (Resultados)</strong></td>
                        <td></td>
                        <td></td>
                        <td style="text-align:right; font-weight:bold;">$86.174,65</td>
                    </tr>
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td>SUMAS IGUALES</td>
                        <td></td>
                        <td style="text-align:right;">$86.174,65</td>
                        <td style="text-align:right;">$86.174,65</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="doc-footer">
            <span>{autor} · Consultoría Actuarial ({ubicacion_autor})</span>
            <span>Página 4</span>
        </div>
    </div>

    <!-- PÁGINA 5: SENSIBILIDAD Y CONCILIACIÓN -->
    <div class="page">
        <div>
            <div class="doc-header">
                <span class="dh-left">COOP. DE AHORRO Y CRÉDITO MAGISTERIO MANABITA LTDA.</span>
                <span class="dh-right">ESTUDIO ACTUARIAL · NIC 19</span>
            </div>

            <h2>D. Análisis de Sensibilidad Paramétrica (NIC 19.145)</h2>
            <p>
                En cumplimiento del párrafo 145 de la NIC 19, se ha evaluado el impacto que fluctuaciones de 50 puntos básicos en las hipótesis financieras clave generarían sobre el pasivo actuarial total:
            </p>

            <table>
                <thead>
                    <tr>
                        <th>Escenario de Sensibilidad</th>
                        <th>Hipótesis Modificada</th>
                        <th>Obligación Total Resultante</th>
                        <th>Variación Relativa</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="background:#f9f9f9; font-weight:bold;">
                        <td>Escenario Base Oficial</td>
                        <td>Tasa Descuento 4,00% / Salarios 3,00%</td>
                        <td style="text-align:right;">$344.698,60</td>
                        <td style="text-align:center;">Base (0,0%)</td>
                    </tr>
                    <tr>
                        <td>Tasa de Descuento + 50 pbs</td>
                        <td>Tasa Descuento a 4,50%</td>
                        <td style="text-align:right;">$326.774,27</td>
                        <td style="text-align:right;">-5,20%</td>
                    </tr>
                    <tr>
                        <td>Tasa de Descuento - 50 pbs</td>
                        <td>Tasa Descuento a 3,50%</td>
                        <td style="text-align:right;">$364.346,42</td>
                        <td style="text-align:right;">+5,70%</td>
                    </tr>
                    <tr>
                        <td>Incremento Salarial + 50 pbs</td>
                        <td>Incremento Salarial a 3,50%</td>
                        <td style="text-align:right;">$359.865,34</td>
                        <td style="text-align:right;">+4,40%</td>
                    </tr>
                    <tr>
                        <td>Incremento Salarial - 50 pbs</td>
                        <td>Incremento Salarial a 2,50%</td>
                        <td style="text-align:right;">$330.565,96</td>
                        <td style="text-align:right;">-4,10%</td>
                    </tr>
                </tbody>
            </table>

            <h2>E. Conciliación de Saldos NIC 19</h2>
            <div class="table-title">Conciliación de Obligaciones por Beneficios Definidos</div>
            <table>
                <thead>
                    <tr>
                        <th style="text-align:left;">Concepto del Plan</th>
                        <th>Jubilación Patronal</th>
                        <th>Bonificación Desahucio</th>
                        <th>Total Consolidado</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Obligación por Beneficios Definidos al inicio de año</td>
                        <td style="text-align:right;">$0,00</td>
                        <td style="text-align:right;">$0,00</td>
                        <td style="text-align:right;">$0,00</td>
                    </tr>
                    <tr>
                        <td>Costo de los servicios prestados en el ejercicio</td>
                        <td style="text-align:right;">$250.038,48</td>
                        <td style="text-align:right;">$94.660,12</td>
                        <td style="text-align:right; font-weight:bold;">$344.698,60</td>
                    </tr>
                    <tr>
                        <td>Beneficios cancelados directamente por el empleador</td>
                        <td style="text-align:right;">$0,00</td>
                        <td style="text-align:right;">$0,00</td>
                        <td style="text-align:right;">$0,00</td>
                    </tr>
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td>OBLIGACIÓN AL 31 DE DICIEMBRE DE 2025</td>
                        <td style="text-align:right;">$250.038,48</td>
                        <td style="text-align:right;">$94.660,12</td>
                        <td style="text-align:right;">$344.698,60</td>
                    </tr>
                </tbody>
            </table>

            <div class="firma-container" style="margin-top:28px;">
                <div class="firma-box">
                    <strong>{autor}</strong><br>
                    <span>Consultoría Actuarial</span><br>
                    <span style="font-size:8pt; color:#555555;">{ubicacion_autor}</span>
                </div>
                <div class="firma-box">
                    <strong>Representante Legal / Gerencia</strong><br>
                    <span>{emp}</span><br>
                    <span style="font-size:8pt; color:#555555;">Aprobado para fines contables</span>
                </div>
            </div>
        </div>

        <div class="doc-footer">
            <span>{autor} · Consultoría Actuarial ({ubicacion_autor})</span>
            <span>Página 5</span>
        </div>
    </div>

    <!-- PÁGINA 6: ANEXO - PLANILLA INDIVIDUAL -->
    <div class="page">
        <div>
            <div class="doc-header">
                <span class="dh-left">COOP. DE AHORRO Y CRÉDITO MAGISTERIO MANABITA LTDA.</span>
                <span class="dh-right">ESTUDIO ACTUARIAL · NIC 19</span>
            </div>

            <h2>Anexo: Planilla y Detalle Individual de Nómina Activa</h2>
            <p style="font-size:8.5pt; color:#444444; margin-bottom:6px;">
                Valoración individual efectuada bajo el Método de la Unidad de Crédito Proyectada (PUCM) con fecha de corte al 31 de diciembre de 2025:
            </p>

            <table style="font-size:8pt;">
                <thead>
                    <tr>
                        <th style="width:5%;">No.</th>
                        <th style="width:42%; text-align:left;">Apellidos y Nombres</th>
                        <th style="width:15%;">Tiempo Servicio</th>
                        <th style="width:13%; text-align:right;">Provisión Jubilación</th>
                        <th style="width:12%; text-align:right;">Provisión Desahucio</th>
                        <th style="width:13%; text-align:right;">Total Pasivo</th>
                    </tr>
                </thead>
                <tbody>
                    {filas_anexo}
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td colspan="3" style="text-align:center;">TOTAL (18 COLABORADORES ACTIVOS)</td>
                        <td style="text-align:right;">$250.038,48</td>
                        <td style="text-align:right;">$94.660,12</td>
                        <td style="text-align:right;">$344.698,60</td>
                    </tr>
                </tbody>
            </table>

            <div style="margin-top:14px; font-size:8pt; color:#333333; text-align:justify;">
                <strong>Certificación Actuarial:</strong> Los valores consignados en la presente planilla individual corresponden al cálculo matemático actuarial del pasivo laboral contingente conforme al método de la unidad de crédito proyectada, empleando las funciones biométricas vigentes en el país y observando los límites establecidos en la Resolución No. 07-2021 de la Corte Nacional de Justicia.
            </div>

            <div class="firma-container" style="margin-top:18px;">
                <div class="firma-box" style="margin:0 auto; width:280px;">
                    <strong>{autor}</strong><br>
                    <span>Consultoría Actuarial</span><br>
                    <span style="font-size:8pt; color:#555555;">{ubicacion_autor}</span>
                </div>
            </div>
        </div>

        <div class="doc-footer">
            <span>{autor} · Planilla Individualizada</span>
            <span>Página 6</span>
        </div>
    </div>

</body>
</html>
"""


def main():
    out_dir = Path("estudios_actuariales/muestra_jefe_magisterio")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Generando Estudio Actuarial Formal Clásico para COOPERATIVA DE AHORRO Y CRÉDITO MAGISTERIO MANABITA LTDA...")
    html_content = construir_documento_magisterio_html()
    html_path = out_dir / "documento_oficial_estudio_magisterio.html"
    html_path.write_text(html_content, encoding="utf-8")
    print(f"Documento HTML generado: {html_path.name}")

    pdf_path = out_dir / "Estudio_Actuarial_Magisterio_Manabita_2025.pdf"
    edge_exe = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    chrome_exe = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
    browser_bin = edge_exe if edge_exe.exists() else chrome_exe

    temp_profile = Path(r"C:\Users\WinterOS\AppData\Local\Temp\actuarial_pdf_export_mm")
    temp_profile.mkdir(parents=True, exist_ok=True)

    cmd_args = [
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f'--user-data-dir="{temp_profile}"',
        f'--print-to-pdf="{pdf_path.resolve()}"',
        f'"{html_path.resolve().as_uri()}"'
    ]

    ps_command = f'Start-Process -FilePath "{browser_bin}" -ArgumentList {", ".join(repr(a) for a in cmd_args)} -Wait'
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps_command], check=True)

    if pdf_path.exists():
        print(f"\nPDF MAGISTERIO MANABITA GENERADO CON ÉXITO: {pdf_path.resolve()} ({pdf_path.stat().st_size:,} bytes)")
    else:
        print("Error: No se pudo generar el PDF.", file=sys.stderr)


if __name__ == "__main__":
    main()
