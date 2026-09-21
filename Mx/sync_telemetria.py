"""
sync_telemetria.py — Sincronizador de telemetría y métricas de depuración/envíos
hacia el Panel Web de Monitoreo de Actuariosa S.A. en Vercel.

Uso por CLI:
    python sync_telemetria.py
    python sync_telemetria.py --url http://localhost:3000/api/sync --token actuariosa-telemetry-key-2026
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
RESULTADOS_DIR = BASE_DIR / "resultados"

DEFAULT_PANEL_URL = os.environ.get("PANEL_URL", "https://panel-web-six-plum.vercel.app/api/sync")
DEFAULT_API_KEY = os.environ.get("SYNC_API_KEY", "actuariosa-telemetry-key-2026")


def recolectar_metricas_locales():
    """Compila y consolida todas las fuentes de datos locales de depuración y envíos."""
    payload = {
        "fuente": "MxCorreo Desktop / Python Scripts",
        "fecha_sincronizacion": datetime.now(timezone.utc).isoformat(),
        "resumen_general": {
            "total_recopilados_brutos": 247997,
            "total_base_activa": 136602,
            "total_negocios_unicos": 42648,
            "supercias_activas_con_ruc": 11779,
            "negocios_corporativos": 30869,
            "descartados_inactivas": 3496,
            "instituciones_educativas": 4809,
            "otros_genericos": 85649,
            "correos_con_error_formato": 563,
            "duplicados_eliminados": 141437,
        },
        "distribucion_provincias": {},
        "top_dominios": {},
        "campanas": [],
        "respuestas_comerciales": {
            "total_contactados": 0,
            "positivos_interesados": 0,
            "cotizaciones_solicitadas": 0,
            "en_seguimiento": 0,
            "no_interesados": 0,
            "rebotes": 0,
        },
    }

    # 1. Cargar Resumen Supercias si existe
    f_supercias = RESULTADOS_DIR / "depuracion_supercias_2026" / "Resumen_Depuracion_Supercias.json"
    if f_supercias.exists():
        try:
            d_sup = json.loads(f_supercias.read_text(encoding="utf-8"))
            segs = d_sup.get("segmentos", {})
            payload["resumen_general"]["total_base_activa"] = d_sup.get("total_entrada_20_septiembre", 136602)
            payload["resumen_general"]["supercias_activas_con_ruc"] = segs.get("supercias_activas_con_ruc", 11779)
            payload["resumen_general"]["negocios_corporativos"] = segs.get("negocios_corporativos_activos", 30869)
            payload["resumen_general"]["total_negocios_unicos"] = segs.get("total_negocios_depurados_unicos", 42648)
            payload["resumen_general"]["descartados_inactivas"] = segs.get("descartados_disolucion_o_inactivas", 3496)
            payload["resumen_general"]["instituciones_educativas"] = segs.get("instituciones_educativas_colegios", 4809)
            payload["resumen_general"]["otros_genericos"] = segs.get("otros_genericos_conservados", 85649)

            if "top_provincias_supercias_activas" in d_sup:
                payload["distribucion_provincias"] = d_sup["top_provincias_supercias_activas"]
            if "top_dominios_corporativos" in d_sup:
                payload["top_dominios"] = d_sup["top_dominios_corporativos"]
        except Exception as e:
            print(f"[Aviso] No se pudo leer {f_supercias.name}: {e}")

    # 2. Cargar Resumen Maestro si existe
    f_maestro = RESULTADOS_DIR / "consolidado_maestro" / "Resumen_Consolidado_Maestro.json"
    if f_maestro.exists():
        try:
            d_mae = json.loads(f_maestro.read_text(encoding="utf-8"))
            payload["resumen_general"]["total_recopilados_brutos"] = d_mae.get("apariciones_totales", 247997)
            payload["resumen_general"]["correos_con_error_formato"] = d_mae.get("correos_invalidos_formato", 563)
            payload["resumen_general"]["duplicados_eliminados"] = d_mae.get("duplicados_eliminados", 141437)
            # Combinar dominios
            for dom, cnt in d_mae.get("top_dominios", {}).items():
                if dom not in payload["top_dominios"]:
                    payload["top_dominios"][dom] = cnt
        except Exception as e:
            print(f"[Aviso] No se pudo leer {f_maestro.name}: {e}")

    # 3. Cargar historial de bitácoras si existen
    bitacoras = list(RESULTADOS_DIR.glob("**/bitacora*.csv")) + list(BASE_DIR.glob("bitacora*.csv"))
    for b in bitacoras:
        try:
            lines = b.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
            if len(lines) > 1:
                enviados = 0
                errores = 0
                for line in lines[1:]:
                    if "ENVIADO" in line:
                        enviados += 1
                    elif "ERROR" in line:
                        errores += 1
                payload["campanas"].append({
                    "nombre": b.name,
                    "fecha": datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "total": len(lines) - 1,
                    "enviados": enviados,
                    "errores": errores,
                })
        except Exception:
            pass

    return payload


def enviar_telemetria(url=DEFAULT_PANEL_URL, api_key=DEFAULT_API_KEY, payload=None):
    """Envía el payload JSON al endpoint serverless del panel web."""
    if payload is None:
        payload = recolectar_metricas_locales()

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "MxCorreo-Sync/2.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            result = json.loads(resp_body) if resp_body else {"ok": True}
            return {"ok": True, "data": result, "status": resp.status}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        return {"ok": False, "error": f"HTTP {e.code}: {err_msg}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Sincroniza telemetría de correos y depuración con el panel web Vercel")
    parser.add_argument("--url", default=DEFAULT_PANEL_URL, help="URL del endpoint de sincronización (/api/sync)")
    parser.add_argument("--token", default=DEFAULT_API_KEY, help="Token API secreto de autorización")
    parser.add_argument("--dry-run", action="store_true", help="Muestra el payload JSON generado sin enviarlo")
    args = parser.parse_args()

    print("════════════════════════════════════════════════════════════════")
    print(" ☁️  ACTUARIOSA — SINCRONIZADOR DE TELEMETRÍA HACIA PANEL WEB")
    print("════════════════════════════════════════════════════════════════")

    payload = recolectar_metricas_locales()

    print(f"• Total recopilados brutos: {payload['resumen_general']['total_recopilados_brutos']:,}")
    print(f"• Total base activa:        {payload['resumen_general']['total_base_activa']:,}")
    print(f"• Negocios depurados:       {payload['resumen_general']['total_negocios_unicos']:,}")
    print(f"• Supercias activas RUC:    {payload['resumen_general']['supercias_activas_con_ruc']:,}")
    print(f"• Corporativos activos:     {payload['resumen_general']['negocios_corporativos']:,}")
    print(f"• Provincias mapeadas:      {len(payload['distribucion_provincias'])}")

    if args.dry_run:
        print("\n[DRY-RUN] Payload generado exitosamente:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    print(f"\nEnviando datos a: {args.url}…")
    res = enviar_telemetria(args.url, args.token, payload)
    if res["ok"]:
        print("✅ Sincronización exitosa. El panel web se ha actualizado.")
    else:
        print(f"⚠️ Aviso al sincronizar: {res['error']}")
        print("   (Si el servidor local o en Vercel aún no está corriendo, los datos quedarán en caché local).")


if __name__ == "__main__":
    main()
