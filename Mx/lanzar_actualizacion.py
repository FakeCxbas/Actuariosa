#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lanzar_actualizacion.py — Actuariosa S.A.
Herramienta CLI para publicar nuevas versiones oficiales de MxCorreo.
Al publicar una versión, todos los clientes de escritorio que se conecten
verán la notificación de "App Desactualizada" y podrán actualizarse con 1 clic.
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime

DEFAULT_URL = "http://localhost:3000/api/updates"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Publicar actualización de MxCorreo en el servidor de Actuariosa."
    )
    parser.add_argument(
        "--version",
        "-v",
        required=True,
        help="Número de versión en formato SemVer (ej: 2.1.0, 2.2.0)",
    )
    parser.add_argument(
        "--titulo",
        "-t",
        default="",
        help="Título descriptivo de la versión",
    )
    parser.add_argument(
        "--notas",
        "-n",
        action="append",
        help="Novedad o nota de la versión. Se puede repetir --notas múltiples veces.",
    )
    parser.add_argument(
        "--obligatoria",
        action="store_true",
        help="Marcar como actualización obligatoria para los clientes.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"URL del endpoint de actualizaciones (por defecto: {DEFAULT_URL})",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    version = args.version.strip()
    titulo = args.titulo.strip() or f"Actualización Oficial v{version}"
    
    notas = args.notas or [
        "Apartado independiente y exclusivo para envíos masivos a empresas",
        "Sincronización en tiempo real con el panel web en Vercel",
        "Optimización del algoritmo de validación sintáctica de correos",
        "Módulo de auto-actualizaciones con reinicio autónomo",
    ]

    payload = {
        "version": version,
        "title": titulo,
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "mandatory": bool(args.obligatoria),
        "min_version": "2.0.0",
        "changelog": notas,
        "download_url": f"https://actuariosa.com/updates/mxcorreo-{version}.tar.gz",
        "package_size": "4.2 MB",
    }

    print("=" * 60)
    print(f"🚀 PUBLICANDO ACTUALIZACIÓN MXCORREO v{version}")
    print("=" * 60)
    print(f"📡 Destino: {args.url}")
    print(f"📦 Título:  {titulo}")
    print(f"⚠️  Obligatoria: {'SÍ' if args.obligatoria else 'NO'}")
    print("✨ Novedades:")
    for n in notas:
        print(f"   • {n}")
    print("-" * 60)

    try:
        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            args.url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MxCorreo-CLI-Publisher/2.0",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            result = json.loads(body)

            if status == 200 and result.get("ok"):
                rel = result.get("release", {})
                print("\n✅ ¡ACTUALIZACIÓN PUBLICADA CON ÉXITO!")
                print(f"   Versión transmitida: v{rel.get('version')}")
                print(f"   Fecha de registro:   {rel.get('release_date')}")
                print("\n🔔 Todos los usuarios con versiones anteriores verán ahora el aviso:")
                print("   '⚠️ Aplicación Desactualizada' y podrán actualizarse con 1 clic.\n")
                return 0
            else:
                print(f"\n❌ Error devuelto por el servidor: {result.get('error')}")
                return 1

    except urllib.error.URLError as e:
        print(f"\n❌ Error de conexión al servidor: {e}")
        print(f"   Asegúrate de que el panel web o servidor esté activo en: {args.url}")
        return 2
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        return 3

if __name__ == "__main__":
    sys.exit(main())
