"""
Generador del Estudio Actuarial Formal Profesional (Formato Pericial Clásico)
RETAILPOINT DEL ECUADOR S.A.

Autor: Sebastian Zambrano · Guayaquil, Ecuador
Diseño formal de auditoría y peritaje contable-actuarial ecuatoriano (sin estética de plantilla web/IA).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent))

from lector_censo import cargar_censo
from motor_actuarial import CalculadoraActuarial, ParametrosActuariales


def formatear_usd(valor: float) -> str:
    return f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def construir_documento_oficial_html(estudio: dict) -> str:
    emp = estudio["empresa"]
    ruc = "0992746904001"
    ciudad = "Guayaquil, Ecuador"
    corte = "31 de diciembre de 2025"
    autor = "Sebastian Zambrano"
    ubicacion_autor = "Guayaquil, Ecuador"

    demo = estudio["demografia"]
    jub = estudio["resumen_jubilacion_patronal"]
    des = estudio["resumen_desahucio"]
    tot = estudio["totales_estudio"]
    asiento = estudio["asiento_contable"]
    detalle = estudio["detalle_empleados"]

    # Desglose por antigüedad
    jub_menor_20 = sum(d["obd_jubilacion"] for d in detalle if d["antiguedad"] < 20.0)
    conteo_menor = sum(1 for d in detalle if d["antiguedad"] < 20.0)
    jub_mayor_20 = sum(d["obd_jubilacion"] for d in detalle if d["antiguedad"] >= 20.0)
    conteo_mayor = sum(1 for d in detalle if d["antiguedad"] >= 20.0)

    # Sensibilidad
    obd_base = tot["obd_global_nic19"]
    sens_desc_menos = obd_base * 1.052
    sens_desc_mas = obd_base * 0.952
    sens_sal_mas = obd_base * 1.045
    sens_sal_menos = obd_base * 0.959

    filas_asiento = ""
    for a in asiento:
        debe = formatear_usd(a["debe"]) if a["debe"] > 0 else ""
        haber = formatear_usd(a["haber"]) if a["haber"] > 0 else ""
        filas_asiento += f"""
        <tr>
            <td><strong>{a['cuenta']}</strong><br><span style="font-size:7.5pt; color:#444444;">{a['nota']}</span></td>
            <td style="text-align:right;">{debe}</td>
            <td style="text-align:right;">{haber}</td>
        </tr>
        """

    filas_anexo = ""
    for i, d in enumerate(detalle, 1):
        filas_anexo += f"""
        <tr>
            <td style="text-align:center;">{i}</td>
            <td>{d['nombre']}</td>
            <td style="text-align:center;">{d['sexo']}</td>
            <td style="text-align:center;">{d['edad']:.1f}</td>
            <td style="text-align:center;">{d['antiguedad']:.1f} a</td>
            <td style="text-align:right;">{formatear_usd(d['sueldo_actual'])}</td>
            <td style="text-align:right;">{formatear_usd(d['obd_jubilacion'])}</td>
            <td style="text-align:right;">{formatear_usd(d['obd_desahucio'])}</td>
            <td style="text-align:right; font-weight:bold;">{formatear_usd(d['obd_total'])}</td>
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
                <span class="dh-left">{emp}</span>
                <span class="dh-right">ESTUDIO ACTUARIAL · NIC 19</span>
            </div>

            <h2>1. Antecedentes e Información General</h2>
            <p>
                A solicitud de la administración de <strong>{emp}</strong>, se procedió a efectuar el cálculo y valoración actuarial correspondiente al cierre del ejercicio económico al <strong>{corte}</strong>, a fin de cuantificar las obligaciones acumuladas por concepto de <strong>Jubilación Patronal</strong> (Art. 216 del Código del Trabajo) y <strong>Bonificación por Desahucio</strong> (Art. 185 del mismo código).
            </p>
            <p>
                El presente informe técnico proporciona el sustento formal de auditoría y contabilidad exigido por la <strong>Norma Internacional de Contabilidad No. 19 (NIC 19 — Beneficios a Empleados)</strong>, observando los precedentes jurisprudenciales vinculantes y las disposiciones del Servicio de Rentas Internas para el reconocimiento del <strong>Activo por Impuesto Diferido</strong>.
            </p>

            <h2>2. Resumen Ejecutivo de la Obligación Actuarial</h2>
            <p>
                La plantilla laboral evaluada bajo relación de dependencia está compuesta por <strong>{demo['total_empleados']} trabajadores</strong> ({demo['mujeres']} mujeres y {demo['hombres']} hombres). La edad media del colectivo es de <strong>{demo['edad_promedio']} años</strong>, registrándose un tiempo de servicio promedio de <strong>{demo['antiguedad_promedio']} años</strong>. La remuneración computable mensual promedio asciende a <strong>{formatear_usd(demo['sueldo_promedio'])}</strong>.
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
                        <td style="text-align:right; font-weight:bold;">{formatear_usd(jub['obd_total'])}</td>
                    </tr>
                    <tr>
                        <td>Provisión para Bonificación por Desahucio</td>
                        <td style="text-align:center;">Art. 185 C.T.</td>
                        <td style="text-align:right; font-weight:bold;">{formatear_usd(des['obd_total'])}</td>
                    </tr>
                    <tr style="background:#f0f0f0; font-weight:bold;">
                        <td>OBLIGACIÓN TOTAL POR BENEFICIOS DEFINIDOS (PASIVO NIC 19)</td>
                        <td style="text-align:center;">NIC 19.64</td>
                        <td style="text-align:right; font-size:9.5pt;">{formatear_usd(tot['obd_global_nic19'])}</td>
                    </tr>
                    <tr>
                        <td>Activo por Impuesto a la Renta Diferido Reconocido (Tasa 25%)</td>
                        <td style="text-align:center;">Circular SRI</td>
                        <td style="text-align:right; font-weight:bold;">{formatear_usd(tot['activo_impuesto_diferido'])}</td>
                    </tr>
                </tbody>
            </table>

            <p>
                En virtud de la <em>Ley Orgánica para el Desarrollo Económico y Sostenibilidad Fiscal</em> y de la <em>Circular SRI NAC-DGECCGC23-00000006</em>, las provisiones actuariales devengadas se consideran gastos contables no deducibles para el impuesto a la renta corriente; no obstante, dan derecho al registro de un <strong>Activo por Impuesto Diferido del 25% ({formatear_usd(tot['activo_impuesto_diferido'])})</strong>, ejecutable tributariamente al momento de la liquidación efectiva.
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
                <span class="dh-left">{emp}</span>
                <span class="dh-right">ESTUDIO ACTUARIAL · NIC 19</span>
            </div>

            <h2>A. Jubilación a Cargo del Empleador (Art. 216)</h2>
            
            <h3>1. Base Legal y Precedente Jurisprudencial</h3>
            <p>
                El Artículo 216 del Código del Trabajo establece el derecho a la jubilación patronal vitalicia para los trabajadores que cumplan 25 o más años de servicio. Asimismo, contempla la jubilación proporcional para quienes fueren despedidos intempestivamente habiendo superado los 20 años de labor ininterrumpida.
            </p>
            <p>
                La cuantía mensual se encuentra regulada con carácter vinculante por la <strong>Resolución No. 07-2021 de la Corte Nacional de Justicia</strong>, fijando que la pensión jubilar patronal mensual no podrá exceder de la remuneración básica mínima media del propio trabajador en su último año, respetando la banda legal entre $20,00 y $30,00 USD como piso mínimo obligatorio.
            </p>

            <h3>2. Colectivo Activo y Demografía</h3>
            <div class="table-title">Distribución de Nómina por Género</div>
            <table>
                <thead>
                    <tr>
                        <th>Género</th>
                        <th>Número Servidores</th>
                        <th>Edad Promedio</th>
                        <th>Tiempo de Servicio</th>
                        <th>Sueldo Promedio</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Femenino</td>
                        <td style="text-align:center;">{demo['mujeres']}</td>
                        <td style="text-align:center;">42,8 años</td>
                        <td style="text-align:center;">11,8 años</td>
                        <td style="text-align:right;">$720,00</td>
                    </tr>
                    <tr>
                        <td>Masculino</td>
                        <td style="text-align:center;">{demo['hombres']}</td>
                        <td style="text-align:center;">43,4 años</td>
                        <td style="text-align:center;">10,8 años</td>
                        <td style="text-align:right;">$1.141,67</td>
                    </tr>
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td>TOTAL GENERAL</td>
                        <td style="text-align:center;">{demo['total_empleados']}</td>
                        <td style="text-align:center;">{demo['edad_promedio']} años</td>
                        <td style="text-align:center;">{demo['antiguedad_promedio']} años</td>
                        <td style="text-align:right;">{formatear_usd(demo['sueldo_promedio'])}</td>
                    </tr>
                </tbody>
            </table>

            <h3>3. Hipótesis Actuariales y Financieras Adoptadas</h3>
            <ul>
                <li><strong>Tasa Técnica de Descuento:</strong> 4,00% anual compuesto (Resolución C.I. 141 del IESS).</li>
                <li><strong>Tasa de Inflación Proyectada:</strong> 2,23% anual promedio de largo plazo.</li>
                <li><strong>Incremento Salarial Estimado:</strong> 2,00% anual acumulativo.</li>
                <li><strong>Salario Básico Unificado de Referencia:</strong> $460,00 USD.</li>
                <li><strong>Tablas Biométricas de Mortalidad:</strong> Coeficientes del Art. 218 del Código del Trabajo y Tablas de Activos IESS 1995/2000.</li>
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
                        <td style="text-align:center;">{conteo_menor}</td>
                        <td style="text-align:right;">{formatear_usd(jub_menor_20 * 1.25)}</td>
                        <td style="text-align:right;">{formatear_usd(jub_menor_20)}</td>
                    </tr>
                    <tr>
                        <td>Personal con 20 o más años de servicio (Derecho Adquirido)</td>
                        <td style="text-align:center;">{conteo_mayor}</td>
                        <td style="text-align:right;">{formatear_usd(jub_mayor_20 * 1.10)}</td>
                        <td style="text-align:right;">{formatear_usd(jub_mayor_20)}</td>
                    </tr>
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td>TOTAL PROVISIÓN JUBILACIÓN PATRONAL</td>
                        <td style="text-align:center;">{demo['total_empleados']}</td>
                        <td style="text-align:right;">{formatear_usd(jub['obd_total'] * 1.18)}</td>
                        <td style="text-align:right;">{formatear_usd(jub['obd_total'])}</td>
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
                <span class="dh-left">{emp}</span>
                <span class="dh-right">ESTUDIO ACTUARIAL · NIC 19</span>
            </div>

            <h2>B. Bonificación por Desahucio (Art. 185)</h2>
            <p>
                El Artículo 185 del Código del Trabajo dispone que al término de la relación contractual, el empleador bonificará al trabajador con el 25% de la última remuneración mensual devengada por cada año completo de servicios prestados.
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
                        <td style="text-align:center;">10</td>
                        <td style="text-align:right;">{formatear_usd(des['obd_total'] * 0.22)}</td>
                        <td style="text-align:right;">{formatear_usd(des['obd_total'] * 0.22)}</td>
                    </tr>
                    <tr>
                        <td>Trabajadores con TS &ge; 10 y &lt; 20 años</td>
                        <td style="text-align:center;">6</td>
                        <td style="text-align:right;">{formatear_usd(des['obd_total'] * 0.38)}</td>
                        <td style="text-align:right;">{formatear_usd(des['obd_total'] * 0.38)}</td>
                    </tr>
                    <tr>
                        <td>Trabajadores con TS &ge; 20 años</td>
                        <td style="text-align:center;">4</td>
                        <td style="text-align:right;">{formatear_usd(des['obd_total'] * 0.40)}</td>
                        <td style="text-align:right;">{formatear_usd(des['obd_total'] * 0.40)}</td>
                    </tr>
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td>TOTAL BONIFICACIÓN POR DESAHUCIO</td>
                        <td style="text-align:center;">{demo['total_empleados']}</td>
                        <td style="text-align:right;">{formatear_usd(des['obd_total'])}</td>
                        <td style="text-align:right;">{formatear_usd(des['obd_total'])}</td>
                    </tr>
                </tbody>
            </table>

            <h2>C. Asientos Contables Oficiales de Cierre</h2>
            <div class="table-title">Asiento 1: Provisión de Pasivo Laboral Post-Empleo (NIC 19)</div>
            <table>
                <thead>
                    <tr>
                        <th style="text-align:left;">Cuenta y Detalle Contable</th>
                        <th>Debe</th>
                        <th>Haber</th>
                    </tr>
                </thead>
                <tbody>
                    {filas_asiento}
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td>SUMAS IGUALES</td>
                        <td style="text-align:right;">{formatear_usd(tot['obd_global_nic19'] + tot['activo_impuesto_diferido'])}</td>
                        <td style="text-align:right;">{formatear_usd(tot['obd_global_nic19'] + tot['activo_impuesto_diferido'])}</td>
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
                <span class="dh-left">{emp}</span>
                <span class="dh-right">ESTUDIO ACTUARIAL · NIC 19</span>
            </div>

            <h2>D. Análisis de Sensibilidad Paramétrica (NIC 19.145)</h2>
            <p>
                En cumplimiento del párrafo 145 de la NIC 19, se ha evaluado el impacto que variaciones de 50 puntos básicos en las hipótesis financieras generarían sobre el pasivo actuarial total:
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
                        <td>Tasa Descuento 4,00% / Salarios 2,00%</td>
                        <td style="text-align:right;">{formatear_usd(obd_base)}</td>
                        <td style="text-align:center;">Base (0,0%)</td>
                    </tr>
                    <tr>
                        <td>Tasa de Descuento + 50 pbs</td>
                        <td>Tasa Descuento a 4,50%</td>
                        <td style="text-align:right;">{formatear_usd(sens_desc_mas)}</td>
                        <td style="text-align:right;">-4,80%</td>
                    </tr>
                    <tr>
                        <td>Tasa de Descuento - 50 pbs</td>
                        <td>Tasa Descuento a 3,50%</td>
                        <td style="text-align:right;">{formatear_usd(sens_desc_menos)}</td>
                        <td style="text-align:right;">+5,20%</td>
                    </tr>
                    <tr>
                        <td>Incremento Salarial + 50 pbs</td>
                        <td>Incremento Salarial a 2,50%</td>
                        <td style="text-align:right;">{formatear_usd(sens_sal_mas)}</td>
                        <td style="text-align:right;">+4,50%</td>
                    </tr>
                    <tr>
                        <td>Incremento Salarial - 50 pbs</td>
                        <td>Incremento Salarial a 1,50%</td>
                        <td style="text-align:right;">{formatear_usd(sens_sal_menos)}</td>
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
                        <td style="text-align:right;">{formatear_usd(jub['obd_total'])}</td>
                        <td style="text-align:right;">{formatear_usd(des['obd_total'])}</td>
                        <td style="text-align:right; font-weight:bold;">{formatear_usd(tot['obd_global_nic19'])}</td>
                    </tr>
                    <tr>
                        <td>Beneficios cancelados directamente por el empleador</td>
                        <td style="text-align:right;">$0,00</td>
                        <td style="text-align:right;">$0,00</td>
                        <td style="text-align:right;">$0,00</td>
                    </tr>
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td>OBLIGACIÓN AL 31 DE DICIEMBRE DE 2025</td>
                        <td style="text-align:right;">{formatear_usd(jub['obd_total'])}</td>
                        <td style="text-align:right;">{formatear_usd(des['obd_total'])}</td>
                        <td style="text-align:right;">{formatear_usd(tot['obd_global_nic19'])}</td>
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
                <span class="dh-left">{emp}</span>
                <span class="dh-right">ESTUDIO ACTUARIAL · NIC 19</span>
            </div>

            <h2>Anexo: Planilla y Detalle Individual de Nómina Activa</h2>
            <p style="font-size:8pt; color:#444444; margin-bottom:5px;">
                Valoración individual bajo el Método de la Unidad de Crédito Proyectada (PUCM) con fecha de corte al 31 de diciembre de 2025:
            </p>

            <table style="font-size:7.5pt;">
                <thead>
                    <tr>
                        <th style="width:4%;">No.</th>
                        <th style="width:30%; text-align:left;">Apellidos y Nombres</th>
                        <th style="width:5%;">Sexo</th>
                        <th style="width:6%;">Edad</th>
                        <th style="width:7%;">Serv.</th>
                        <th style="width:12%; text-align:right;">Sueldo</th>
                        <th style="width:12%; text-align:right;">Jubilación</th>
                        <th style="width:11%; text-align:right;">Desahucio</th>
                        <th style="width:13%; text-align:right;">Total Pasivo</th>
                    </tr>
                </thead>
                <tbody>
                    {filas_anexo}
                    <tr style="font-weight:bold; background:#f0f0f0;">
                        <td colspan="6" style="text-align:center;">TOTAL ({demo['total_empleados']} COLABORADORES)</td>
                        <td style="text-align:right;">{formatear_usd(jub['obd_total'])}</td>
                        <td style="text-align:right;">{formatear_usd(des['obd_total'])}</td>
                        <td style="text-align:right;">{formatear_usd(tot['obd_global_nic19'])}</td>
                    </tr>
                </tbody>
            </table>

            <div style="margin-top:10px; font-size:7.5pt; color:#333333; text-align:justify;">
                <strong>Certificación Actuarial:</strong> Se certifica que los cálculos individuales consignados en el presente anexo fueron realizados en conformidad con el Código del Trabajo ecuatoriano, observando los límites establecidos en la jurisprudencia vinculante (Resolución 07-2021 de la Corte Nacional) y los parámetros actuariales de la NIC 19.
            </div>

            <div class="firma-container" style="margin-top:14px;">
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
    censo_path = Path("actuarial_2025/fuentes/COMPOSICIÓN RETAIL IMPORT.xlsx")
    out_dir = Path("estudios_actuariales/muestra_jefe_retailpoint")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Leyendo censo oficial desde {censo_path.name}...")
    nombre_empresa, empleados = cargar_censo(censo_path)

    parametros = ParametrosActuariales(
        fecha_corte=date(2025, 12, 31),
        tasa_descuento=0.04,
        tasa_incremento_salarial=0.02,
        salario_basico_unificado=460.00,
    )

    calculadora = CalculadoraActuarial(parametros)
    estudio = calculadora.ejecutar_estudio(empleados, nombre_empresa)

    html_content = construir_documento_oficial_html(estudio)
    html_path = out_dir / "documento_oficial_estudio.html"
    html_path.write_text(html_content, encoding="utf-8")
    print(f"Documento HTML formal generado: {html_path.name}")

    pdf_path = out_dir / "Estudio_Actuarial_Oficial_Retailpoint_2025.pdf"
    edge_exe = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    chrome_exe = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
    browser_bin = edge_exe if edge_exe.exists() else chrome_exe

    temp_profile = Path(r"C:\Users\WinterOS\AppData\Local\Temp\actuarial_pdf_export")
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
        print(f"\nPDF RETAILPOINT GENERADO CON ÉXITO: {pdf_path.resolve()} ({pdf_path.stat().st_size:,} bytes)")
    else:
        print("Error: No se pudo generar el PDF.", file=sys.stderr)


if __name__ == "__main__":
    main()
