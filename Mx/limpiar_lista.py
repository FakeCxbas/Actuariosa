"""Etapa 1: revisa formato y marca duplicados, sin acceso a Internet."""
import argparse
from pathlib import Path

from etapas import check_output, save_stage
from verificar_correos import prepare_lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path, help="TXT UTF-8, una dirección por línea")
    parser.add_argument("--salida", type=Path, default=Path("resultados/limpieza.json"))
    args = parser.parse_args(argv)
    try:
        check_output(args.salida)
        if args.archivo.suffix.lower() != ".txt":
            raise ValueError("La entrada debe ser un .txt UTF-8 sin encabezado.")
        rows = prepare_lines(args.archivo.read_text(encoding="utf-8-sig").splitlines())
        if not rows:
            raise ValueError("El archivo está vacío o solo contiene líneas en blanco.")
        save_stage(args.salida, "limpieza", rows)
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(1, f"No se pudo completar: {exc}\n")
    print(f"Filas: {len(rows)}. Duplicados: {sum(r['duplicado_de_linea'] is not None for r in rows)}.")
    print("No se consultó DNS ni se enviaron correos. Resultado:", args.salida.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
