#!/usr/bin/env bash
set -euo pipefail

NEXO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Necesitas Python 3.10 o posterior. Instálalo con el gestor de paquetes de tu distribución."
  exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else "Necesitas Python 3.10 o posterior.")'
cd -- "$NEXO_ROOT"
exec python3 server.py --port "${NEXO_PORT:-8766}" --data-dir "${NEXO_DATA_DIR:-$NEXO_ROOT/data}" "$@"
