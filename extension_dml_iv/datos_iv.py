"""Contrato de datos IV: roles, particiones verificadas y separación de la verdad."""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass

import numpy as np

from rutas_iv import DATOS


@dataclass(frozen=True)
class EsquemaIV:
    """Z, D, Y y X tienen un único rol; U nunca aparece entre los observados."""

    instrumento: str = "z"
    tratamiento: str = "d"
    resultado: str = "y"
    covariables: tuple[str, ...] = ("x1", "x2")
    latente_no_observada: str = "U"

    def columnas(self) -> list[str]:
        return [self.instrumento, self.tratamiento, self.resultado, *self.covariables]

    def validar(self, columnas: list[str], valores: dict[str, np.ndarray]) -> None:
        esquema = self.columnas()
        ausentes = [c for c in esquema if c not in columnas]
        if ausentes:
            raise ValueError(f"Columnas ausentes: {ausentes}")
        repetidas = sorted({c for c in esquema if esquema.count(c) > 1})
        if repetidas:
            raise ValueError(f"Columnas con más de un rol: {repetidas}")
        if self.latente_no_observada in columnas:
            raise ValueError("U es latente: no puede entrar como covariable observada")
        for rol in (self.instrumento, self.tratamiento):
            niveles = np.unique(valores[rol])
            if not np.all(np.isin(niveles, [0, 1])) or len(niveles) < 2:
                raise ValueError(f"{rol} debe ser binario y variar en los datos")


def leer(particion: str = "train") -> dict[str, np.ndarray]:
    """Lee solo un observed_*.csv; nunca abre interventions.json."""
    with open(DATOS / f"observed_{particion}.csv", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    if not filas:
        raise ValueError(f"La partición {particion} está vacía")
    return {
        nombre: np.array([float(fila[nombre]) for fila in filas])
        for nombre in filas[0]
        if nombre != "row_id"
    }


def verificar_splits() -> bool:
    declarado = json.loads((DATOS / "splits.json").read_text(encoding="utf-8"))
    correcto = True
    for parte in ("train", "validation", "test"):
        ruta = DATOS / f"observed_{parte}.csv"
        hash_real = hashlib.sha256(ruta.read_bytes()).hexdigest()
        ficha = declarado["splits"][parte]
        coincide = hash_real == ficha["file_sha256"]
        correcto &= coincide
        print(f"  {parte:10s}: hash {'OK' if coincide else 'NO COINCIDE'}; n={ficha['n_rows']}")
    return correcto


def comprobar_pared() -> None:
    prohibidas = {"U", "u", "d0", "d1", "y0", "y1", "tau"}
    for parte in ("train", "validation", "test"):
        with open(DATOS / f"observed_{parte}.csv", encoding="utf-8") as archivo:
            columnas = set(csv.DictReader(archivo).fieldnames or [])
        filtradas = sorted(columnas & prohibidas)
        if filtradas:
            raise RuntimeError(f"Pared rota en {parte}: {filtradas}")
    if (DATOS / "truth_train.csv").exists():
        raise RuntimeError("Pared rota: truth_train.csv no debe existir")
    print("  Pared OK: no hay U, potenciales por unidad ni truth_train.csv")


if __name__ == "__main__":
    esquema = EsquemaIV()
    entrenamiento = leer("train")
    esquema.validar(list(entrenamiento), entrenamiento)
    print(f"Esquema IV válido: {esquema.columnas()}; n={len(entrenamiento['y'])}")
    print("Verificación de particiones:")
    assert verificar_splits()
    comprobar_pared()
