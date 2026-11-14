"""Genera el escenario sintético IV y sus contratos; no escribe fuera de esta carpeta."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from rutas_iv import DATOS, ESCENARIO, SEMILLA, SEMILLA_SPLIT


def generar_universo(semilla=SEMILLA, escenario="valido", n=2000):
    """Devuelve observados y verdad por separado; el estimador solo recibe lo primero."""
    if escenario not in {"valido", "debil", "exclusion"}:
        raise ValueError(f"Escenario desconocido: {escenario}")
    rng = np.random.default_rng(semilla)
    x1, x2, u = (rng.normal(size=n) for _ in range(3))
    z = rng.binomial(1, 0.5, n)
    fuerza_z = 0.15 if escenario == "debil" else 1.5
    efecto_directo_z = 1.0 if escenario == "exclusion" else 0.0

    # Una latente común para D(0) y D(1) garantiza monotonicidad por construcción.
    latente = -0.2 + 0.5 * x1 - 0.4 * x2 + u
    d0 = (latente > 0).astype(int)
    d1 = (latente + fuerza_z > 0).astype(int)
    d = np.where(z == 1, d1, d0)
    tau = 2.0 + 0.5 * x1
    y0 = 1.0 + 0.8 * x1 - 0.5 * x2 + 0.9 * u + rng.normal(size=n)
    y = y0 + d * tau + efecto_directo_z * z

    observados = pd.DataFrame({
        "row_id": np.arange(n), "x1": x1, "x2": x2, "z": z, "d": d, "y": y,
    })
    compliers = (d0 == 0) & (d1 == 1)
    if not compliers.any():
        raise RuntimeError("La simulación no produjo compliers; aumenta n o la fuerza de Z")
    verdad = {
        "estimando_referencia": "LATE_compliers",
        "late_compliers": float(tau[compliers].mean()),
        "ate_poblacional": float(tau.mean()),
        "proporcion_compliers": float(compliers.mean()),
        "escenario": escenario,
        "semilla": semilla,
        "n_unidades": n,
    }
    return observados, verdad


def _escribir_json(nombre, contenido):
    (DATOS / nombre).write_text(
        json.dumps(contenido, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def guardar_escenario():
    observados, verdad = generar_universo()
    DATOS.mkdir(parents=True, exist_ok=True)
    orden = np.random.default_rng(SEMILLA_SPLIT).permutation(len(observados))
    cortes = {"train": orden[:1200], "validation": orden[1200:1600], "test": orden[1600:]}
    splits = {"split_seed": SEMILLA_SPLIT, "splits": {}}

    for nombre, indices in cortes.items():
        ruta = DATOS / f"observed_{nombre}.csv"
        observados.iloc[indices].to_csv(ruta, index=False)
        splits["splits"][nombre] = {
            "n_rows": len(indices),
            "file_sha256": hashlib.sha256(ruta.read_bytes()).hexdigest(),
        }

    _escribir_json("splits.json", splits)
    _escribir_json("metadata.json", {
        "scenario_id": ESCENARIO,
        "name": "Invitación aleatoria a tutoría y asistencia efectiva",
        "data_origin": "SYNTHETIC - generado localmente con verdad conocida",
        "treatment_column": "d",
        "treatment": "Asistencia efectiva a la tutoría",
        "outcome_column": "y",
        "outcome": "Puntaje final",
        "instrument_column": "z",
        "instrument": "Invitación aleatoria a tutoría",
        "covariates": ["x1", "x2"],
        "unobserved_confounder": "U",
        "estimand": "LATE entre compliers; no ATE poblacional",
        "num_units": len(observados),
        "seed": SEMILLA,
        "split_seed": SEMILLA_SPLIT,
    })
    _escribir_json("identification.json", {
        "scenario_id": ESCENARIO,
        "strategy": "instrumental_variables",
        "identification_status": "LATE identificable por diseño bajo los supuestos declarados",
        "instruments": ["z"],
        "treatments": ["d"],
        "outcomes": ["y"],
        "latent_variables": ["U"],
        "graph": {
            "nodes": ["z", "d", "y", "x1", "x2", "U"],
            "edges": [
                ["z", "d"], ["d", "y"],
                ["x1", "d"], ["x1", "y"], ["x2", "d"], ["x2", "y"],
                ["U", "d"], ["U", "y"],
            ],
        },
        "assumptions": {
            "relevancia": "Se examina mediante la primera etapa",
            "independencia": "Z se genera aleatoriamente",
            "exclusion": "Z solo afecta Y mediante D en el escenario válido",
            "monotonicidad": "No hay defiers por construcción del DGP",
            "SUTVA": "Declarado; no verificable con este CSV",
            "soporte": "Se declara; esta demo no emite un diagnóstico completo del soporte condicional",
        },
        "note": "La primera etapa no demuestra independencia, exclusión, monotonicidad ni SUTVA.",
    })
    _escribir_json("interventions.json", {
        **verdad,
        "uso": "SOLO evaluación posterior; prohibido como entrada de estimación o calibración",
    })
    print(f"Escenario regenerado en {DATOS}")
    print("Datos observados y referencia causal escritos por separado.")


if __name__ == "__main__":
    guardar_escenario()
