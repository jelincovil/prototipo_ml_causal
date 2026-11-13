"""Comprueba que el servicio Docker publica el champion íntegro y autorizado."""
from __future__ import annotations

import json
import os
import sys
import urllib.request


def main() -> int:
    url = os.environ.get("SIC_SALUD_URL", "http://127.0.0.1:8000/salud")
    version_esperada = os.environ.get("SIC_VERSION_ESPERADA", "v0009")
    try:
        with urllib.request.urlopen(url, timeout=2) as respuesta:
            if respuesta.status != 200:
                return 1
            estado = json.load(respuesta)
    except (OSError, ValueError, TypeError):
        return 1

    sano = (
        isinstance(estado, dict)
        and estado.get("estado") == "ok"
        and estado.get("integridad_valida") is True
        and estado.get("estado_puerta") == "pasa"
        and estado.get("version") == version_esperada
    )
    if not sano:
        print("Servicio no sano: revisa estado, integridad, puerta y versión en /salud.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
