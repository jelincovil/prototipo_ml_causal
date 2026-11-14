"""Rutas locales de la extensión; no importa ni modifica rutas.py."""
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
DATOS = CARPETA / "datos" / "iv_tutoria"
SALIDA = CARPETA / "salida"
ESCENARIO = "synthetic/iv_tutoria"
SEMILLA = 20261113
SEMILLA_SPLIT = 20240701
