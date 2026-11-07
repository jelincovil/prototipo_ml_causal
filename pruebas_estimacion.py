"""pruebas_estimacion.py — asserts de las fórmulas y de los invariantes.

No usa dependencias nuevas. Se ejecuta con `make pruebas` sobre `real/ihdp`.
"""
from __future__ import annotations

import hashlib
import json

from pathlib import Path

import numpy as np

from datos import EsquemaCausal, leer
from estimacion import aipw_crossfit, ate_ols, smd_ponderado
from rutas import ARTEFACTOS, DATOS
from sensibilidad import (control_negativo, e_value_continuo,
                          placebo_permutacion, valor_robustez)


def main() -> int:
    # 1. E-value: siempre >= 1; el límite que cruza cero da 1.
    ev = e_value_continuo(5.0, 10.0, [3.0, 7.0])
    assert ev["e_value_punto"] >= 1.0
    assert ev["e_value_ic"] >= 1.0
    assert ev["e_value_punto"] >= ev["e_value_ic"]
    ev0 = e_value_continuo(5.0, 10.0, [-1.0, 11.0])
    assert ev0["e_value_ic"] == 1.0

    # 2. Valor de robustez en [0, 1].
    rv = valor_robustez(5.0, 100)
    assert 0.0 <= rv["rv"] <= 1.0
    assert rv["rv_pct"] == 100.0 * rv["rv"]

    # 3. SMD ponderado finito y con signo.
    g = np.random.default_rng(7)
    v = g.normal(size=80)
    D = (g.random(80) < 0.5).astype(float)
    e = np.full(80, 0.5)
    assert np.isfinite(smd_ponderado(v, D, e))

    # 4. OLS devuelve t/df/n/k para el valor de robustez.
    esquema = EsquemaCausal()
    col = leer("train")
    ols = ate_ols(col, esquema)
    assert {"t", "df", "n", "k"} <= set(ols)
    assert ols["df"] > 0

    # 5. Placebo de tratamiento: n_rep exacto y p en [0, 1].
    p = placebo_permutacion(col, esquema, aipw_crossfit, n_rep=5, semilla=11)
    assert p["n_rep"] == 5
    assert 0.0 <= p["p_valor_aprox"] <= 1.0
    assert p["placebo_ic95"][0] <= p["placebo_ic95"][1]

    # 6. Placebo de resultado: devuelve efecto e IC.
    q = control_negativo(col, esquema, aipw_crossfit, variable="momage",
                         semilla=11)
    assert len(q["ic95"]) == 2
    assert q["ic95"][0] <= q["ic95"][1]

    # 7. El artefacto incluye el hash correcto del dataset.
    ruta = ARTEFACTOS / "estimacion.json"
    if ruta.exists():
        est = json.loads(ruta.read_text())
        hash_real = hashlib.sha256(
            (DATOS / "observed_train.csv").read_bytes()).hexdigest()
        assert est.get("dataset_sha256") == hash_real
        ident = est.get("identificacion") or {}
        assert "aplicable" in ident
        if ident.get("aplicable"):
            assert ident.get("metodos_dowhy", {}).get("conjunto_backdoor") == "default"
            assert ident.get("metodos_dowhy", {}).get("expresion_estimando") == "id-algorithm"
            assert ident.get("efecto_identificable_por_grafo") is True
            bench = json.loads((DATOS / "identification.json").read_text())
            bench_set = [str(x) for x in (bench.get("valid_adjustment_sets") or [[]])[0]]
            got = ident.get("conjunto_ajuste_estimado") or []
            assert sorted(got) == sorted(bench_set)
            assert ident.get("coincide_valid_adjustment_sets") is True

    # 8. La pared: ni el estimador ni la sensibilidad leen interventions.json.
    #    Se permite mencionarlo en un docstring; se rechazan lecturas reales.
    for nombre in ("estimacion.py", "sensibilidad.py"):
        for linea in Path(nombre).read_text().splitlines():
            if "interventions" in linea:
                assert not any(k in linea for k in ("open(", "read_text", "read_bytes")), (
                    f"{nombre} lee interventions.json: {linea.strip()}")

    print("PRUEBAS: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
