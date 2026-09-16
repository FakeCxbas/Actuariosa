"""Etapa 2: consulta DNS para una lista previamente procesada. No envía correos."""
import argparse
from pathlib import Path

import dns.exception

from etapas import check_output, load_stage, save_stage
from verificar_correos import DNSChecker, verify


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path, help="JSON generado por limpiar_lista.py")
    parser.add_argument("--salida", type=Path, default=Path("resultados/dns.json"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=4)
    parser.add_argument("--reintentos", type=int, default=1)
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 32 or not 0.1 <= args.timeout <= 30 or not 0 <= args.reintentos <= 3:
        parser.error("Usa workers 1-32, timeout 0.1-30 y reintentos 0-3.")
    try:
        check_output(args.salida)
        data = load_stage(args.archivo, "limpieza")
        rows = verify(data["resultados"], DNSChecker(args.timeout, args.reintentos), args.workers)
        save_stage(args.salida, "dns", rows)
    except (ValueError, OSError, UnicodeError, dns.exception.DNSException) as exc:
        parser.exit(1, f"No se pudo completar: {exc}\n")
    print("DNS terminado; buzones no comprobados. Resultado:", args.salida.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
