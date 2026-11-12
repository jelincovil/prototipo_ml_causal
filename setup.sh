#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  printf 'Instalando uv...\n'
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh | sh
  else
    printf 'Error: instala curl o wget y vuelve a ejecutar setup.sh.\n' >&2
    exit 1
  fi
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
  printf 'Error: uv quedó instalado fuera de PATH. Abre otra terminal y repite el comando.\n' >&2
  exit 1
fi

uv python install 3.13
uv venv --python 3.13 --clear .venv
uv pip install --python "$ROOT_DIR/.venv/bin/python" -r "$ROOT_DIR/requirements.txt"
uv pip check --python "$ROOT_DIR/.venv/bin/python"
"$ROOT_DIR/.venv/bin/python" --version

printf '\nInstalación lista. Ejecuta: bash arrancar.sh\n'
printf 'URL: http://127.0.0.1:8000\n'
printf 'Endpoints: http://127.0.0.1:8000/efecto\n'
printf '           http://127.0.0.1:8000/salud\n'
printf '           http://127.0.0.1:8000/docs\n'
