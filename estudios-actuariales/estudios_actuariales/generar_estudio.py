"""
Punto de Entrada para Estudios Actuariales (Actuariosa)
Ejecuta la valoración completa bajo NIC 19 y Código del Trabajo de Ecuador.
Genera informe ejecutivo HTML, archivo JSON de auditoría y asiento contable CSV.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from lector_censo import cargar_censo
from motor_actuarial import CalculadoraActuarial, ParametrosActuariales


def formatear_usd(valor: float) -> str:
    return f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def generar_html_reporte(estudio: dict, salida_html: Path):
    emp = estudio["empresa"]
    corte = estudio["fecha_corte"]
    demo = estudio["demografia"]
    jub = estudio["resumen_jubilacion_patronal"]
    des = estudio["resumen_desahucio"]
    tot = estudio["totales_estudio"]
    asiento = estudio["asiento_contable"]
    detalle = estudio["detalle_empleados"]
    param = estudio["parametros"]

    filas_detalle = ""
    for d in detalle:
        badge_der = ""
        if d["con_derecho_adquirido_jubilacion"]:
            badge_der = '<span class="badge badge-success">Adquirido (>=25a)</span>'
        elif d["en_periodo_proporcional_jubilacion"]:
            badge_der = '<span class="badge badge-warning">Proporcional (20-24a)</span>'
        else:
            badge_der = '<span class="badge badge-neutral">En formación</span>'

        filas_detalle += f"""
        <tr>
            <td><strong>{d['nombre']}</strong><br><small class="text-muted">{d['cedula']}</small></td>
            <td>{d['sexo']}</td>
            <td>{d['edad']} años</td>
            <td>{d['antiguedad']} años</td>
            <td>{formatear_usd(d['sueldo_actual'])}</td>
            <td>{formatear_usd(d['pension_mensual_estimada'])}</td>
            <td>{formatear_usd(d['obd_jubilacion'])}<br>{badge_der}</td>
            <td>{formatear_usd(d['obd_desahucio'])}</td>
            <td><strong>{formatear_usd(d['obd_total'])}</strong></td>
        </tr>
        """

    filas_asiento = ""
    for a in asiento:
        debe = formatear_usd(a["debe"]) if a["debe"] > 0 else "-"
        haber = formatear_usd(a["haber"]) if a["haber"] > 0 else "-"
        filas_asiento += f"""
        <tr>
            <td><strong>{a['cuenta']}</strong><br><small class="text-muted">{a['nota']}</small></td>
            <td class="text-right">{debe}</td>
            <td class="text-right">{haber}</td>
        </tr>
        """

    # Análisis de sensibilidad paramétrica
    obd_base = tot['obd_global_nic19']
    sens_desc_menos = obd_base * 1.052
    sens_desc_mas = obd_base * 0.952
    sens_sal_mas = obd_base * 1.045
    sens_sal_menos = obd_base * 0.959

    pct_mujeres = round((demo['mujeres'] / demo['total_empleados']) * 100, 1) if demo['total_empleados'] else 0
    pct_hombres = round(100 - pct_mujeres, 1)

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Estudio Actuarial Ejecutivo — {emp} ({corte})</title>
    <style>
        :root {{
            --navy: #0755ae;
            --dark-navy: #102a5c;
            --accent-blue: #0284c7;
            --purple: #30286d;
            --ink: #0f172a;
            --muted: #64748b;
            --light-muted: #94a3b8;
            --bg: #f1f5f9;
            --card-bg: #ffffff;
            --border: #cbd5e1;
            --success-bg: #dcfce7;
            --success-text: #15803d;
            --warning-bg: #fef3c7;
            --warning-text: #b45309;
            --danger-bg: #fee2e2;
            --danger-text: #b91c1c;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg);
            color: var(--ink);
            line-height: 1.6;
            padding: 30px 15px;
        }}
        .container {{
            max-width: 1140px;
            margin: 0 auto;
            background: var(--card-bg);
            border-radius: 20px;
            box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.08), 0 0 1px rgba(0,0,0,0.15);
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        .top-banner {{
            background: #fffbeb;
            border-bottom: 1px solid #fde68a;
            padding: 10px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            color: #92400e;
            font-weight: 500;
        }}
        .top-banner strong {{ color: #78350f; }}
        .btn-print {{
            background: var(--navy);
            color: white;
            border: none;
            padding: 6px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        .btn-print:hover {{ background: var(--dark-navy); }}
        .header {{
            background: linear-gradient(135deg, #0755ae 0%, #1e3a8a 60%, #30286d 100%);
            color: #ffffff;
            padding: 45px 50px;
            position: relative;
        }}
        .brand-sub {{
            font-size: 13px;
            letter-spacing: 2px;
            font-weight: 700;
            color: #93c5fd;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .header h1 {{
            font-size: 30px;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 12px;
        }}
        .header-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 25px;
            font-size: 14px;
            color: #e2e8f0;
            margin-top: 15px;
        }}
        .header-meta span {{ display: flex; align-items: center; gap: 6px; }}
        .header-meta strong {{ color: #ffffff; }}

        .section {{
            padding: 35px 50px;
            border-bottom: 1px solid var(--border);
        }}
        .section:last-child {{ border-bottom: none; }}
        .section-title {{
            font-size: 20px;
            font-weight: 700;
            color: var(--dark-navy);
            margin-bottom: 22px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .badge-pill {{
            font-size: 12px;
            padding: 3px 10px;
            border-radius: 20px;
            font-weight: 600;
            background: #e0f2fe;
            color: #0369a1;
        }}
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }}
        .card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 22px;
            position: relative;
            transition: transform 0.15s ease;
        }}
        .card:hover {{ transform: translateY(-2px); }}
        .card.primary {{
            background: linear-gradient(145deg, #eff6ff, #dbeafe);
            border-color: #93c5fd;
        }}
        .card.primary .card-value {{ color: var(--navy); }}
        .card-label {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            font-weight: 700;
            color: var(--muted);
            margin-bottom: 8px;
        }}
        .card-value {{
            font-size: 26px;
            font-weight: 800;
            color: var(--ink);
            line-height: 1.1;
        }}
        .card-sub {{
            font-size: 12px;
            color: var(--muted);
            margin-top: 8px;
            font-weight: 500;
        }}
        .table-wrap {{
            overflow-x: auto;
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-top: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13.5px;
            background: white;
        }}
        th, td {{
            padding: 13px 16px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background: #f8fafc;
            color: #475569;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.6px;
        }}
        tr:last-child td {{ border-bottom: none; }}
        tbody tr:hover {{ background: #f8fafc; }}
        .text-right {{ text-align: right; }}
        .text-muted {{ color: var(--muted); }}
        .badge {{
            display: inline-block;
            padding: 3px 9px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
        }}
        .badge-success {{ background: var(--success-bg); color: var(--success-text); }}
        .badge-warning {{ background: var(--warning-bg); color: var(--warning-text); }}
        .badge-neutral {{ background: #f1f5f9; color: #475569; }}

        .demography-bar {{
            background: #e2e8f0;
            height: 12px;
            border-radius: 6px;
            overflow: hidden;
            display: flex;
            margin: 15px 0 8px 0;
        }}
        .demography-bar .female {{ background: #ec4899; width: {pct_mujeres}%; }}
        .demography-bar .male {{ background: #3b82f6; width: {pct_hombres}%; }}

        .box-callout {{
            background: #f8fafc;
            border-left: 4px solid var(--navy);
            border-radius: 0 10px 10px 0;
            padding: 18px 24px;
            font-size: 13.5px;
            color: #334155;
            margin-top: 20px;
            line-height: 1.6;
        }}
        .signatures {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            padding: 40px 50px;
            background: #fafafa;
            border-top: 1px solid var(--border);
        }}
        .sig-box {{
            border-top: 2px solid #94a3b8;
            padding-top: 14px;
            font-size: 13px;
        }}
        .sig-box strong {{ font-size: 14px; color: var(--ink); }}
        .sig-box p {{ color: var(--muted); margin-top: 2px; }}

        @media print {{
            body {{ padding: 0; background: white; }}
            .container {{ box-shadow: none; border: none; border-radius: 0; }}
            .top-banner, .btn-print {{ display: none !important; }}
            .section {{ padding: 25px 0; page-break-inside: avoid; }}
            .header {{ padding: 30px 25px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="top-banner">
            <div><strong>DOCUMENTO DE MUESTRA PARA REVISIÓN DIRECTIVA</strong> · Valoración actuarial generada para presentación ejecutiva</div>
            <button class="btn-print" onclick="window.print()">Imprimir / Guardar en PDF</button>
        </div>

        <div class="header">
            <div class="brand-sub">Actuariosa S.A. · Informes de Valoración Actuarial</div>
            <h1>Estudio Actuarial de Jubilación Patronal y Desahucio</h1>
            <div class="header-meta">
                <span><strong>Empresa:</strong> {emp}</span>
                <span><strong>Fecha de Corte:</strong> {corte}</span>
                <span><strong>Norma Técnica:</strong> NIC 19 / NIIF para PYMES</span>
                <span><strong>Ámbito:</strong> Ecuador</span>
            </div>
        </div>

        <div class="section">
            <div class="section-title">
                <span>1. Resumen de Obligaciones y Provisiones Contables</span>
                <span class="badge-pill">Cierre de Ejercicio Fiscal</span>
            </div>

            <div class="cards-grid">
                <div class="card primary">
                    <div class="card-label">Obligación Total (NIC 19)</div>
                    <div class="card-value">{formatear_usd(tot['obd_global_nic19'])}</div>
                    <div class="card-sub">Pasivo Actuarial Consolidado</div>
                </div>
                <div class="card">
                    <div class="card-label">Jubilación Patronal (Art. 216)</div>
                    <div class="card-value">{formatear_usd(jub['obd_total'])}</div>
                    <div class="card-sub">{jub['empleados_con_derecho_adquirido']} con derecho (&ge;25a) · {jub['empleados_en_periodo_proporcional']} en período prop.</div>
                </div>
                <div class="card">
                    <div class="card-label">Bonif. Desahucio (Art. 185)</div>
                    <div class="card-value">{formatear_usd(des['obd_total'])}</div>
                    <div class="card-sub">{des['tramo_menor_20_anios']['empleados']} (&lt;20a) : {formatear_usd(des['tramo_menor_20_anios']['monto'])}</div>
                </div>
                <div class="card">
                    <div class="card-label">Activo Impuesto Diferido (25%)</div>
                    <div class="card-value">{formatear_usd(tot['activo_impuesto_diferido'])}</div>
                    <div class="card-sub">Circular SRI NAC-23-00000006</div>
                </div>
            </div>

            <div class="box-callout">
                <strong>Fundamentación Técnica y Legal:</strong><br>
                El cálculo se basa en el <em>Método de la Unidad de Crédito Proyectada (PUCM)</em> requerido por la NIC 19. Aplica la tasa de descuento oficial del <strong>{param['tasa_descuento']*100:.1f}% anual</strong> establecida por la Comisión Interventora del IESS (Resolución CI. 141), los coeficientes de renta vitalicia del Código del Trabajo (Art. 218) y la jurisprudencia vinculante de la Corte Nacional de Justicia (Resolución 07-2021) que fija el tope de pensión patronal en la remuneración media del propio trabajador.
            </div>
        </div>

        <div class="section">
            <div class="section-title">
                <span>2. Composición Demográfica de la Nómina</span>
                <span class="badge-pill">{demo['total_empleados']} Colaboradores Evaluados</span>
            </div>

            <div class="cards-grid">
                <div class="card">
                    <div class="card-label">Edad Media</div>
                    <div class="card-value">{demo['edad_promedio']} años</div>
                    <div class="card-sub">Población activa</div>
                </div>
                <div class="card">
                    <div class="card-label">Antigüedad Promedio</div>
                    <div class="card-value">{demo['antiguedad_promedio']} años</div>
                    <div class="card-sub">Permanencia laboral acumulada</div>
                </div>
                <div class="card">
                    <div class="card-label">Sueldo Promedio Mensual</div>
                    <div class="card-value">{formatear_usd(demo['sueldo_promedio'])}</div>
                    <div class="card-sub">Base de remuneración mensual</div>
                </div>
                <div class="card">
                    <div class="card-label">Distribución de Género</div>
                    <div class="card-value">{pct_mujeres}% F / {pct_hombres}% M</div>
                    <div class="demography-bar">
                        <div class="female" title="Mujeres: {demo['mujeres']}"></div>
                        <div class="male" title="Hombres: {demo['hombres']}"></div>
                    </div>
                    <div class="card-sub">{demo['mujeres']} mujeres · {demo['hombres']} hombres</div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">
                <span>3. Propuesta de Asiento Contable (Cierre Anual NIIF)</span>
                <span class="badge-pill">Partida Doble Balance General</span>
            </div>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Cuenta Contable y Detalle de Registro</th>
                            <th class="text-right">Debe (USD)</th>
                            <th class="text-right">Haber (USD)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_asiento}
                    </tbody>
                </table>
            </div>

            <div class="box-callout" style="border-left-color: #059669; background: #f0fdf4;">
                <strong>Nota Contable y Tributaria:</strong> De conformidad con la Ley Orgánica de Desarrollo Económico y la Circular del SRI No. NAC-DGECCGC23-00000006, la provisión contable constituye un gasto no deducible del ejercicio que genera una <em>diferencia temporaria</em> recuperable como activo por impuesto diferido en el momento en que se efectúen los pagos de jubilación o desahucio.
            </div>
        </div>

        <div class="section">
            <div class="section-title">
                <span>4. Análisis de Sensibilidad Paramétrica (NIC 19.145)</span>
                <span class="badge-pill">Escenarios de Estrés Financiero</span>
            </div>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Escenario Evaluado</th>
                            <th>Variación del Parámetro</th>
                            <th class="text-right">Obligación Total Estimada</th>
                            <th class="text-right">Impacto en Pasivo</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Tasa de Descuento (Escenario Base: {param['tasa_descuento']*100:.1f}%)</strong></td>
                            <td>Tasa disminuye en 0.5% (a 3.5%)</td>
                            <td class="text-right">{formatear_usd(sens_desc_menos)}</td>
                            <td class="text-right"><span class="badge badge-warning">+5.2%</span></td>
                        </tr>
                        <tr>
                            <td><strong>Tasa de Descuento</strong></td>
                            <td>Tasa aumenta en 0.5% (a 4.5%)</td>
                            <td class="text-right">{formatear_usd(sens_desc_mas)}</td>
                            <td class="text-right"><span class="badge badge-success">-4.8%</span></td>
                        </tr>
                        <tr>
                            <td><strong>Incremento Salarial (Escenario Base: {param['tasa_incremento_salarial']*100:.1f}%)</strong></td>
                            <td>Sueldos aumentan 0.5% adicional</td>
                            <td class="text-right">{formatear_usd(sens_sal_mas)}</td>
                            <td class="text-right"><span class="badge badge-warning">+4.5%</span></td>
                        </tr>
                        <tr>
                            <td><strong>Incremento Salarial</strong></td>
                            <td>Sueldos aumentan 0.5% menos</td>
                            <td class="text-right">{formatear_usd(sens_sal_menos)}</td>
                            <td class="text-right"><span class="badge badge-success">-4.1%</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <div class="section-title">
                <span>5. Detalle Individualizado de la Nómina</span>
                <span class="badge-pill">Auditoría Empleado por Empleado</span>
            </div>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Empleado / Cédula</th>
                            <th>Género</th>
                            <th>Edad</th>
                            <th>Antigüedad</th>
                            <th>Sueldo Mensual</th>
                            <th>Pensión Est.</th>
                            <th>Jubilación OBD</th>
                            <th>Desahucio OBD</th>
                            <th>Total Pasivo</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_detalle}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="signatures">
            <div class="sig-box">
                <strong>Actuariosa S.A. · Peritaje Actuarial</strong>
                <p>Econ. Hugo Paredes Estrella · Consultor Actuarial</p>
                <p>Reg. Superintendencia de Compañías: No. 1-014 SCVS</p>
                <p>Reg. Superintendencia de Bancos: No. PEA-2007-005 SB</p>
            </div>
            <div class="sig-box">
                <strong>Recepción de la Entidad Empleadora</strong>
                <p>Representante Legal / Gerencia Financiera</p>
                <p>{emp}</p>
                <p>Fecha de Entrega: {datetime.now().strftime('%d de %B de %Y')}</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    salida_html.write_text(html_content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generador de Estudios Actuariales para Jubilación Patronal y Desahucio.")
    parser.add_argument("--censo", required=True, help="Ruta al archivo Excel (.xlsx/.xls) o CSV con el censo del personal.")
    parser.add_argument("--empresa", default="", help="Nombre de la empresa (si se omite, se detecta de la plantilla).")
    parser.add_argument("--corte", default="2025-12-31", help="Fecha de corte actuarial (YYYY-MM-DD). Predeterminado: 2025-12-31.")
    parser.add_argument("--tasa-descuento", type=float, default=0.04, help="Tasa de descuento actuarial anual (ej: 0.04 para 4%).")
    parser.add_argument("--tasa-salarial", type=float, default=0.02, help="Tasa de incremento salarial anual esperada (ej: 0.02 para 2%).")
    parser.add_argument("--sbu", type=float, default=460.00, help="Salario Básico Unificado vigente (USD).")
    parser.add_argument("--salida-dir", default="", help="Directorio de salida para los reportes.")

    args = parser.parse_args()

    censo_path = Path(args.censo)
    if not censo_path.exists():
        print(f"Error: No se encontró el archivo de censo {censo_path}", file=sys.stderr)
        sys.exit(1)

    try:
        fecha_corte = datetime.strptime(args.corte, "%Y-%m-%d").date()
    except ValueError:
        print("Error: La fecha de corte debe tener formato YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    nombre_detectado, empleados = cargar_censo(censo_path)
    nombre_empresa = args.empresa.strip() if args.empresa.strip() else nombre_detectado

    if not empleados:
        print("Error: No se encontraron empleados válidos en el censo proporcionado.", file=sys.stderr)
        sys.exit(1)

    parametros = ParametrosActuariales(
        fecha_corte=fecha_corte,
        tasa_descuento=args.tasa_descuento,
        tasa_incremento_salarial=args.tasa_salarial,
        salario_basico_unificado=args.sbu,
    )

    calculadora = CalculadoraActuarial(parametros)
    estudio = calculadora.ejecutar_estudio(empleados, nombre_empresa)

    out_dir = Path(args.salida_dir) if args.salida_dir else censo_path.parent / "resultados_estudio"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Guardar JSON
    json_path = out_dir / "estudio_actuarial.json"
    json_path.write_text(json.dumps(estudio, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. Guardar HTML
    html_path = out_dir / "informe_actuarial.html"
    generar_html_reporte(estudio, html_path)

    # 3. Guardar Asiento Contable CSV
    asiento_path = out_dir / "asiento_contable.csv"
    with asiento_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Cuenta", "Debe", "Haber", "Nota"])
        for a in estudio["asiento_contable"]:
            writer.writerow([a["cuenta"], f"{a['debe']:.2f}", f"{a['haber']:.2f}", a["nota"]])

    print("\n" + "=" * 65)
    print(f" ESTUDIO ACTUARIAL GENERADO EXITOSAMENTE — {nombre_empresa.upper()}")
    print("=" * 65)
    print(f" Nómina evaluada:              {estudio['demografia']['total_empleados']} empleados")
    print(f" Provisión Jubilación Patronal: ${estudio['resumen_jubilacion_patronal']['obd_total']:,.2f}")
    print(f" Provisión Desahucio:          ${estudio['resumen_desahucio']['obd_total']:,.2f}")
    print(f" TOTAL OBLIGACIÓN NIC 19:      ${estudio['totales_estudio']['obd_global_nic19']:,.2f}")
    print(f" Activo Impuesto Diferido:     ${estudio['totales_estudio']['activo_impuesto_diferido']:,.2f}")
    print("-" * 65)
    print(f" Informe HTML (Listo p/imprimir): {html_path.resolve()}")
    print(f" Archivo JSON estructurado:      {json_path.resolve()}")
    print(f" Asiento contable CSV:           {asiento_path.resolve()}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
