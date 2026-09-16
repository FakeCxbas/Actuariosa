"""Etapa 3: crea HTML y JSON a partir de la revisión DNS, sin nuevas consultas."""
import argparse
from pathlib import Path

from etapas import load_stage
from verificar_correos import save_report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path, help="JSON generado por revisar_dns.py")
    parser.add_argument("--salida", type=Path, default=Path("resultados"))
    args = parser.parse_args(argv)
    try:
        data = load_stage(args.archivo, "dns")
        folder, report = save_report(data["resultados"], args.salida, dns_checked_at=data["fecha_utc"])
    except (ValueError, OSError, UnicodeError, KeyError) as exc:
        parser.exit(1, f"No se pudo completar: {exc}\n")
    print("Resultado:", report["resumen"])
    print("Abre en tu navegador:", (folder / "informe.html").resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
