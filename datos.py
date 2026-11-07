"""datos.py — [BLOQUE 2, min 10–35] Contrato C-01 (roles) + C-10 (splits y la pared).

Se completa en vivo: tres funciones con TODO. Todo lo demás ya está.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field

import numpy as np

from rutas import DATOS, ESCENARIO

# Adaptación por escenario: el esquema se declara una vez y viaja con los datos.
COVARIABLES = {
    "real/jobs": ("age", "educ", "black", "hispan",
                  "married", "nodegree", "re74", "re75"),
    "real/ihdp": ("bw", "b.head", "preterm", "birth.o", "nnhealth", "momage",
                  "sex", "twin", "b.marr", "mom.lths", "mom.hs", "mom.scoll",
                  "cig", "first", "booze", "drugs", "work.dur", "prenatal",
                  "ark", "ein", "har", "mia", "pen", "tex", "was"),
}
RESULTADO = {"real/jobs": "re78", "real/ihdp": "outcome"}


# ---------------------------------------------------------------- esquema C-01

@dataclass(frozen=True)
class EsquemaCausal:
    """Cada columna, un solo rol. El esquema viaja con los datos (C-01)."""

    tratamiento: str = "treatment"
    resultado: str = field(default_factory=lambda: RESULTADO[ESCENARIO])
    covariables: tuple = field(default_factory=lambda: COVARIABLES[ESCENARIO])

    def columnas(self) -> list[str]:
        return [self.tratamiento, self.resultado, *self.covariables]

    def validar(self, columnas_datos: list[str], valores_tratamiento) -> None:
        # C-01: cada columna, un solo rol; el rechazo nombra a la culpable.
        esquema = self.columnas()
        ausentes = [c for c in esquema if c not in columnas_datos]
        if ausentes:
            raise ValueError(
                f"columna(s) del esquema ausentes en los datos: {ausentes}")
        dobles = sorted({c for c in esquema if esquema.count(c) > 1})
        if dobles:
            raise ValueError(f"columna(s) con más de un rol: {dobles}")
        if np.unique(np.asarray(valores_tratamiento)).size < 2:
            raise ValueError(
                f"el tratamiento '{self.tratamiento}' no varía en los datos")


# ------------------------------------------------------------------ carga CSV

def leer(particion: str = "train") -> dict[str, np.ndarray]:
    """Lee una partición observada. Solo observed_*: la pared es literal."""
    with open(DATOS / f"observed_{particion}.csv") as f:
        filas = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in filas])
            for k in filas[0] if k != "row_id"}


# ------------------------------------------------------- splits por hash (C-10)

def verificar_splits() -> bool:
    """Recomputa el SHA-256 de cada partición y lo compara con splits.json."""
    declarados = json.loads((DATOS / "splits.json").read_text())
    ok = True
    for parte in ("train", "validation", "test"):
        # C-10: el hash se recomputa; no se confía en el declarado.
        coincide = (hashlib.sha256(
            (DATOS / f"observed_{parte}.csv").read_bytes()).hexdigest()
            == declarados["splits"][parte]["file_sha256"])
        ok &= coincide
        print(f"  {parte:12s} hash {'OK' if coincide else 'NO COINCIDE'}"
              f"  ({declarados['splits'][parte]['n_rows']} filas,"
              f" semilla {declarados['split_seed']})")
    return ok


# --------------------------------------------------------------- la pared (C-10)

def comprobar_pared() -> None:
    """La verdad del escenario no está en el paquete: intentar cargarla falla."""
    # La pared: la verdad del escenario no está en el paquete.
    try:
        with open(DATOS / "truth_train.csv"):
            pass
    except FileNotFoundError:
        print("  pared OK: truth_train.csv no existe en el paquete (reservado)")
        return
    raise RuntimeError("pared rota: truth_train.csv SÍ existe en el paquete")


if __name__ == "__main__":
    esquema = EsquemaCausal()
    print("Esquema C-01:", esquema)
    train = leer("train")
    esquema.validar(list(train), train[esquema.tratamiento])
    print(f"esquema valida contra observed_train: OK "
          f"(n = {len(train[esquema.tratamiento])},"
          f" tratados = {int(train[esquema.tratamiento].sum())})")
    print("Verificación de splits (C-10):")
    assert verificar_splits()
    print("La pared (C-10):")
    comprobar_pared()
