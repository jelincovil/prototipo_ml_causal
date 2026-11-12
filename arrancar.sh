#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .venv/bin/activate ]]; then
  printf 'No existe .venv. Ejecuta primero: bash setup.sh\n' >&2
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate
export SIC_ESCENARIO="synthetic/ihdp"

printf 'Escenario: %s\n' "$SIC_ESCENARIO"
printf 'URL: http://127.0.0.1:8000\n'
printf 'Endpoints: http://127.0.0.1:8000/efecto\n'
printf '           http://127.0.0.1:8000/salud\n'
printf '           http://127.0.0.1:8000/docs\n'
printf 'Detén el servicio con Ctrl-C.\n'

exec uvicorn servicio:app --host 127.0.0.1 --port 8000
