"""
depurar_correos_supercias.py
Filtra, depura y clasifica los correos del 20 de septiembre contra el Directorio Oficial de la
Superintendencia de Compañías del Ecuador (SCVS).
"""
import csv
import json
import re
import shutil
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from python_calamine import CalamineWorkbook


def normalize_clean(text: str) -> str:
    if not text:
        return ""
    text = str(text).strip()
    return re.sub(r"\s+", " ", text)


def main():
    root_dir = Path(__file__).resolve().parent
    workspace_dir = root_dir.parent

    db_path = Path("/home/fakecxbas/.gemini/antigravity-ide/scratch/supercias-directorio/directorio_companias.db")
    if not db_path.exists():
        raise FileNotFoundError(f"No se encontró la base de datos de Supercias en: {db_path}")

    print("=== 1. Cargando Directorio Oficial de Compañías (SCVS) ===")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT ruc, expediente, nombre, situacion_legal, provincia, canton, ciudad, calle, numero, telefono, representante, cargo, ciiu_nivel_1
        FROM companias
        WHERE ruc IS NOT NULL
    """)
    supercias_db = {}
    active_company_names = {}

    for row in cur.fetchall():
        ruc_clean = str(row[0]).split(".")[0].strip().zfill(13)
        situacion = (row[3] or "").strip()
        nombre = (row[2] or "").strip()
        provincia = (row[4] or "").strip()
        canton = (row[5] or "").strip()
        ciudad = (row[6] or "").strip()
        calle = (row[7] or "").strip()
        num = (row[8] or "").strip()
        tel = (row[9] or "").strip()
        rep = (row[10] or "").strip()
        cargo = (row[11] or "").strip()
        ciiu = (row[12] or "").strip()

        data = {
            "ruc": ruc_clean,
            "expediente": row[1],
            "nombre": nombre,
            "situacion_legal": situacion,
            "provincia": provincia,
            "canton": canton,
            "ciudad": ciudad,
            "direccion": f"{calle} {num}".strip(),
            "telefono": tel,
            "representante": rep,
            "cargo": cargo,
            "ciiu": ciiu,
        }
        supercias_db[ruc_clean] = data

        if situacion == "ACTIVA":
            # Extraer palabras clave representativas del nombre (mínimo 4 caracteres)
            tokens = re.findall(r"[A-Z0-9]{4,}", nombre.upper())
            for t in tokens:
                if t not in {
                    "CIA.", "LTDA", "S.A.", "CORP", "SOCIEDAD", "ANONIMA", "ECUADOR",
                    "COMPANIA", "COMPAÑIA", "GRUPO", "COMERCIAL", "SERVICIOS", "INDUSTRIAL",
                    "EXPORTADORA", "IMPORTADORA", "NEGOCIOS", "CONSULTING", "PRODUCCIONES"
                }:
                    active_company_names[t] = data

    print(f"Total compañías cargadas de Supercias: {len(supercias_db):,}")
    print(f"Compañías con estado ACTIVA: {sum(1 for c in supercias_db.values() if c['situacion_legal'] == 'ACTIVA'):,}")

    print("\n=== 2. Mapeando correos a RUCs desde fuentes locales ===")
    email_meta = {}  # correo -> {ruc, empresa, fuente}

    def registrar(email_str, ruc_val, emp_val, fuente_val):
        if not email_str:
            return
        parts = re.split(r"[\s,;]+", str(email_str).strip().strip("'\" /;:,<>"))
        for p in parts:
            p_clean = p.strip().strip("'\" /;:,<>").lower()
            if "@" in p_clean and len(p_clean) > 5 and "." in p_clean.split("@")[-1]:
                r_clean = ""
                if ruc_val:
                    r_raw = str(ruc_val).split(".")[0].strip()
                    if len(r_raw) == 13:
                        r_clean = r_raw
                    elif len(r_raw) == 10:
                        r_clean = r_raw + "001"
                    elif 0 < len(r_raw) < 13:
                        r_clean = r_raw.zfill(13)

                if p_clean not in email_meta or (not email_meta[p_clean]["ruc"] and r_clean):
                    email_meta[p_clean] = {
                        "ruc": r_clean,
                        "empresa": normalize_clean(emp_val),
                        "fuente": fuente_val,
                    }

    carpetas_inspeccion = [
        root_dir / "entradas/recopilacion_archivos",
        root_dir / "entradas/pendrive_2",
        root_dir / "entradas/pendrive_3",
        Path("/home/fakecxbas/.gemini/antigravity-ide/scratch/supercias-directorio"),
        Path("/home/fakecxbas/Descargas"),
    ]

    for c_dir in carpetas_inspeccion:
        if not c_dir.exists():
            continue
        for fpath in c_dir.rglob("*"):
            if not fpath.is_file() or fpath.name.startswith(("~$", "._")):
                continue

            if fpath.suffix.lower() in [".xlsx", ".xls"]:
                try:
                    wb = CalamineWorkbook.from_path(fpath)
                    for sname in wb.sheet_names:
                        sheet = wb.get_sheet_by_name(sname)
                        rows = sheet.to_python(skip_empty_area=False)
                        if not rows or len(rows) < 2:
                            continue
                        ruc_col, mail_col, nom_col = None, None, None
                        for r_idx in range(min(12, len(rows))):
                            r = rows[r_idx]
                            for c_idx, val in enumerate(r):
                                v = str(val).lower() if val else ""
                                if ("ruc" in v or "identificacion" in v or "identificación" in v) and ruc_col is None:
                                    ruc_col = c_idx
                                if ("correo" in v or "email" in v or "e-mail" in v) and mail_col is None:
                                    mail_col = c_idx
                                if ("nombre" in v or "razon" in v or "denominacion" in v or "empresa" in v) and nom_col is None:
                                    nom_col = c_idx
                            if mail_col is not None and (ruc_col is not None or nom_col is not None):
                                break
                        if mail_col is not None:
                            start_row = r_idx + 1 if r_idx is not None else 1
                            for r in rows[start_row:]:
                                if len(r) > mail_col and r[mail_col]:
                                    m_val = str(r[mail_col])
                                    r_val = str(r[ruc_col]) if ruc_col is not None and len(r) > ruc_col and r[ruc_col] else ""
                                    n_val = str(r[nom_col]) if nom_col is not None and len(r) > nom_col and r[nom_col] else ""
                                    registrar(m_val, r_val, n_val, f"{fpath.name} [{sname}]")
                except Exception:
                    pass

            elif fpath.suffix.lower() == ".csv":
                try:
                    with fpath.open("r", encoding="utf-8-sig", errors="ignore") as f:
                        sample = f.read(4096)
                        f.seek(0)
                        delim = ";" if ";" in sample and "," not in sample else ","
                        reader = csv.reader(f, delimiter=delim)
                        headers = None
                        for r in reader:
                            if not headers:
                                headers = [h.lower() for h in r]
                                ruc_col = next((i for i, h in enumerate(headers) if "ruc" in h or "identif" in h), None)
                                mail_col = next((i for i, h in enumerate(headers) if "correo" in h or "email" in h or "mail" in h), None)
                                nom_col = next((i for i, h in enumerate(headers) if "nombre" in h or "empresa" in h or "razon" in h), None)
                                if mail_col is None:
                                    break
                                continue
                            if mail_col is not None and len(r) > mail_col and r[mail_col]:
                                m_val = r[mail_col]
                                r_val = r[ruc_col] if ruc_col is not None and len(r) > ruc_col else ""
                                n_val = r[nom_col] if nom_col is not None and len(r) > nom_col else ""
                                registrar(m_val, r_val, n_val, fpath.name)
                except Exception:
                    pass

    print(f"Total correos mapeados con metadatos de fuentes: {len(email_meta):,}")
    print(f"Correos con RUC asociado: {sum(1 for v in email_meta.values() if v['ruc']):,}")

    print("\n=== 3. Procesando lista maestra del 20 de septiembre ===")
    master_path = root_dir / "resultados/Para_Google_Drive/Correos aptos totales 20 septiembre 2026.csv"
    if not master_path.exists():
        raise FileNotFoundError(f"No existe el archivo maestro en: {master_path}")

    free_webmails = {
        "hotmail.com", "gmail.com", "yahoo.com", "yahoo.es", "hotmail.es",
        "outlook.com", "live.com", "outlook.es", "icloud.com", "yahoo.com.ar",
        "msn.com", "aol.com", "latinmail.com", "ymail.com", "terra.com.ec"
    }

    typo_webmails = {
        "gmal.com", "gmaill.com", "gmial.com", "gmai.com", "gamil.com", "hotmial.com",
        "hotmai.com", "hotmal.com", "hotmaill.com", "outlok.com", "outloo.com", "yaho.com",
        "yahooo.com", "yaho.es", "hotmail.con", "gmail.con", "gemail.com"
    }

    list_supercias_activas = []
    list_negocios_corp_activos = []
    list_descartados_inactivas = []
    list_educativos = []
    list_otros_conservados = []

    seen_totales_negocios = set()

    with master_path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            email = line.strip().lower()
            if not email or "@" not in email:
                continue

            local_part, domain = email.split("@", 1)
            meta = email_meta.get(email)
            ruc = meta["ruc"] if meta else ""

            # Caso A: Tiene RUC conocido en Supercias
            if ruc and ruc in supercias_db:
                sc = supercias_db[ruc]
                estado = sc["situacion_legal"]
                item = {
                    "correo": email,
                    "ruc": ruc,
                    "razon_social": sc["nombre"],
                    "situacion_legal": estado,
                    "provincia": sc["provincia"],
                    "canton": sc["canton"],
                    "ciudad": sc["ciudad"],
                    "telefono": sc["telefono"],
                    "representante_legal": sc["representante"],
                    "cargo": sc["cargo"],
                    "sector_ciiu": sc["ciiu"],
                    "fuente_origen": meta["fuente"] if meta else "Supercias",
                }
                if estado == "ACTIVA":
                    list_supercias_activas.append(item)
                    seen_totales_negocios.add(email)
                else:
                    list_descartados_inactivas.append(item)
                continue

            # Caso B: Si es correo de entidad educativa / colegio / código AMIE
            is_edu = (
                domain.endswith(".edu.ec")
                or "educacion.gob.ec" in domain
                or bool(re.search(r"^\d{2}[hdb]\d{3,}", local_part))
                or "educ12" in email or "educ0" in email or "educ1" in email or "educ2" in email
                or any(k in local_part for k in ["colegio", "escuela", "col.", "unidadeducativa"])
            )
            if is_edu:
                list_educativos.append({
                    "correo": email,
                    "dominio": domain,
                    "tipo": "Educación / Colegio / Escuela (AMIE)",
                    "fuente_origen": meta["fuente"] if meta else "Consolidado"
                })
                continue

            # Caso C: Typos de webmails comunes (guardar en otros conservados)
            if domain in typo_webmails or any(t in domain for t in ["gmal.", "hotmial.", "gmial."]):
                list_otros_conservados.append({
                    "correo": email,
                    "dominio": domain,
                    "empresa_referencial": "Error de escritura de webmail (typo)",
                    "fuente_origen": meta["fuente"] if meta else "Base Maestro Histórica"
                })
                continue

            # Caso D: Dominio corporativo propio (no webmail genérico)
            if domain not in free_webmails:
                # Comprobar si el dominio coincide con alguna empresa activa en Supercias
                dom_key = domain.split(".")[0].upper()
                sc_match = active_company_names.get(dom_key)
                empresa_sug = sc_match["nombre"] if sc_match else ""
                prov_sug = sc_match["provincia"] if sc_match else ""
                ciu_sug = sc_match["ciudad"] if sc_match else ""

                item_corp = {
                    "correo": email,
                    "dominio": domain,
                    "empresa_asociada": empresa_sug or (meta["empresa"] if meta else ""),
                    "provincia": prov_sug or (sc_match["provincia"] if sc_match else ""),
                    "ciudad": ciu_sug or (sc_match["ciudad"] if sc_match else ""),
                    "fuente_origen": meta["fuente"] if meta else "Dominio Corporativo Empresarial",
                }
                list_negocios_corp_activos.append(item_corp)
                seen_totales_negocios.add(email)
                continue

            # Caso E: Webmail genérico sin RUC explícito (SE CONSERVA ÍNTEGRO)
            list_otros_conservados.append({
                "correo": email,
                "dominio": domain,
                "empresa_referencial": meta["empresa"] if meta else "",
                "fuente_origen": meta["fuente"] if meta else "Base Maestro Histórica"
            })

    print("\n=== 4. Exportando listas segmentadas ===")
    out_dir = root_dir / "resultados/depuracion_supercias_2026"
    drive_dir = root_dir / "resultados/Para_Google_Drive"
    out_dir.mkdir(parents=True, exist_ok=True)
    drive_dir.mkdir(parents=True, exist_ok=True)

    # 1. Correos Supercias Activas con RUC
    f1 = out_dir / "1_Correos_Supercias_Activas_con_RUC.csv"
    with f1.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "correo", "ruc", "razon_social", "situacion_legal", "provincia",
            "canton", "ciudad", "telefono", "representante_legal", "cargo",
            "sector_ciiu", "fuente_origen"
        ])
        writer.writeheader()
        writer.writerows(list_supercias_activas)

    # 2. Correos Negocios Corporativos Activos
    f2 = out_dir / "2_Correos_Negocios_Corporativos_Activos.csv"
    with f2.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "correo", "dominio", "empresa_asociada", "provincia", "ciudad", "fuente_origen"
        ])
        writer.writeheader()
        writer.writerows(list_negocios_corp_activos)

    # 3. Consolidado Total Negocios (1 + 2)
    f3_detalle = out_dir / "3_Correos_Negocios_Totales_Depurados_Detallado.csv"
    f3_simple = out_dir / "3_Correos_Negocios_Totales_Depurados_Solo_Correos.csv"

    sorted_totales = sorted(seen_totales_negocios)
    with f3_simple.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for m in sorted_totales:
            writer.writerow([m])

    supercias_activas_set = {x["correo"] for x in list_supercias_activas}
    with f3_detalle.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["correo", "tipo_segmento", "identificador_o_dominio", "empresa_o_razon_social", "provincia", "ciudad"])
        for item in list_supercias_activas:
            writer.writerow([item["correo"], "Supercias ACTIVA con RUC", item["ruc"], item["razon_social"], item["provincia"], item["ciudad"]])
        for item in list_negocios_corp_activos:
            if item["correo"] not in supercias_activas_set:
                writer.writerow([item["correo"], "Corporativo Empresarial", item["dominio"], item["empresa_asociada"], item["provincia"], item["ciudad"]])

    # 4. Descartados Inactivas / Liquidación
    f4 = out_dir / "4_Correos_Descartados_Disolucion_o_Inactivas.csv"
    with f4.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "correo", "ruc", "razon_social", "situacion_legal", "provincia",
            "canton", "ciudad", "telefono", "representante_legal", "cargo",
            "sector_ciiu", "fuente_origen"
        ])
        writer.writeheader()
        writer.writerows(list_descartados_inactivas)

    # 5. Instituciones Educativas / Colegios
    f5 = out_dir / "5_Correos_Instituciones_Educativas_Colegios.csv"
    with f5.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["correo", "dominio", "tipo", "fuente_origen"])
        writer.writeheader()
        writer.writerows(list_educativos)

    # 6. Otros Genéricos Conservados (Para no perderlos jamás)
    f6 = out_dir / "6_Correos_Otros_Genericos_Conservados.csv"
    with f6.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["correo", "dominio", "empresa_referencial", "fuente_origen"])
        writer.writeheader()
        writer.writerows(list_otros_conservados)

    # Copiar archivos clave a Para_Google_Drive
    archivos_drive = [f1, f2, f3_detalle, f3_simple, f4, f5, f6]
    for af in archivos_drive:
        shutil.copy2(af, drive_dir / af.name)

    # Resumen JSON
    resumen = {
        "fecha_depuracion": datetime.now(timezone.utc).isoformat(),
        "total_entrada_20_septiembre": 136602,
        "segmentos": {
            "supercias_activas_con_ruc": len(list_supercias_activas),
            "negocios_corporativos_activos": len(list_negocios_corp_activos),
            "total_negocios_depurados_unicos": len(sorted_totales),
            "descartados_disolucion_o_inactivas": len(list_descartados_inactivas),
            "instituciones_educativas_colegios": len(list_educativos),
            "otros_genericos_conservados": len(list_otros_conservados),
        },
        "top_provincias_supercias_activas": dict(Counter(x["provincia"] for x in list_supercias_activas if x["provincia"]).most_common(10)),
        "top_dominios_corporativos": dict(Counter(x["dominio"] for x in list_negocios_corp_activos).most_common(15)),
        "rutas_salida": {
            "carpeta_local": str(out_dir),
            "carpeta_google_drive": str(drive_dir),
        }
    }

    resumen_path = out_dir / "Resumen_Depuracion_Supercias.json"
    with resumen_path.open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    shutil.copy2(resumen_path, drive_dir / resumen_path.name)

    print("\n================ RESULTADOS FINALES ================")
    print(f"1. Empresas Supercias ACTIVAS (con RUC y razón social): {len(list_supercias_activas):,}")
    print(f"2. Correos Negocios Corporativos Activos:             {len(list_negocios_corp_activos):,}")
    print(f"3. TOTAL NEGOCIOS DEPURADOS (1 + 2 únicos):           {len(sorted_totales):,}")
    print(f"4. Descartados (Disolución, Liquidación, Inactiva):    {len(list_descartados_inactivas):,}")
    print(f"5. Educación y colegios filtrados:                    {len(list_educativos):,}")
    print(f"6. Otros genéricos conservados (sin perder nada):     {len(list_otros_conservados):,}")
    print(f"\nArchivos guardados en:")
    print(f" - {out_dir}")
    print(f" - {drive_dir}")


if __name__ == "__main__":
    main()
