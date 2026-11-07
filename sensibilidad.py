"""sensibilidad.py — E-value, valor de robustez, placebo y control negativo.

Módulo de la aplicación (no es un script auxiliar). No lee CSV ni
`interventions.json`: recibe las columnas ya cargadas por `estimacion.py` y
devuelve diccionarios listos para viajar en el bundle.

Las dos medidas de sensibilidad son complementarias y tienen límites distintos:

- E-value: aproximación para un resultado continuo estandarizado. La razón de
  riesgos se aproxima con ``RR ~ exp(0.91 * d)`` (Chinn 2000; VanderWeele &
  Ding 2017). No es una RR literal ni una cota exacta.
- Valor de robustez: exacto bajo el modelo lineal de sesgo por omisión para el
  comparador OLS (Cinelli & Hazlett 2020). No es una propiedad exacta del AIPW.

El placebo de tratamiento permutado y el placebo de resultado permutado son
controles negativos: evalúan calibración del estimador, no prueban
ignorabilidad.
"""
from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np

from datos import EsquemaCausal

AipwFn = Callable[..., dict[str, Any]]


def e_value_continuo(ate: float, sd_y: float, ic: list[float]) -> dict:
    """E-value aproximado para un efecto continuo estandarizado.

    ``d = |ATE| / sd(Y)`` y ``RR = exp(0.91 * d)``. Para el límite del IC más
    cercano a cero se repite el cálculo; si el IC contiene el cero, el E-value
    del límite es 1.
    """
    if sd_y <= 0:
        raise ValueError("sd_y debe ser positiva para estandarizar el efecto")
    if len(ic) != 2 or ic[0] > ic[1]:
        raise ValueError("ic debe ser [limite_inferior, limite_superior]")

    def _e_para(valor: float) -> tuple[float, float]:
        d = abs(float(valor)) / sd_y
        rr = math.exp(0.91 * d)
        e = rr + math.sqrt(rr * (rr - 1.0)) if rr > 1.0 else 1.0
        return float(d), float(e)

    d, e_punto = _e_para(ate)
    if ic[0] <= 0 <= ic[1]:
        limite = 0.0
        e_ic = 1.0
    else:
        limite = ic[0] if abs(ic[0]) < abs(ic[1]) else ic[1]
        _, e_ic = _e_para(limite)

    return {
        "metodo": ("E-value para efecto continuo estandarizado "
                   "(aprox. RR de Chinn/VanderWeele)"),
        "ate": float(ate),
        "sd_y": float(sd_y),
        "efecto_estandarizado": d,
        "e_value_punto": e_punto,
        "e_value_ic": float(e_ic),
        "limite_ic_usado": float(limite),
        "supuestos": ("Resultado continuo; RR aproximada vía d estandarizado. "
                      "No es una razón de riesgos literal."),
        "lectura": (
            f"Un confusor no medido tendría que asociarse con D y Y, condicionando "
            f"en X, con una razón de riesgos aproximada de al menos {e_punto:.2f} "
            f"para explicar el efecto puntual; el límite del IC más cercano a cero "
            f"exige al menos {e_ic:.2f}."
        ),
        "limites": ("Aproximación para resultado continuo; no es una cota exacta. "
                    "Se complementa con el valor de robustez del OLS."),
    }


def valor_robustez(t: float, df: int, q: float = 1.0) -> dict:
    """Valor de robustez de Cinelli & Hazlett (2020) para el coeficiente OLS.

    ``RV_q`` es el R² parcial mínimo que un confusor no medido tendría que
    explicar, tanto en D como en Y, para reducir el coeficiente en ``q`` veces.
    Con ``q=1`` se reduce a cero.
    """
    if df <= 0:
        raise ValueError("df debe ser positivo")
    if q <= 0:
        raise ValueError("q debe ser positivo")
    f = q * abs(float(t)) / math.sqrt(df)
    rv = 0.5 * (math.sqrt(f ** 4 + 4.0 * f ** 2) - f ** 2)
    rv = float(np.clip(rv, 0.0, 1.0))
    return {
        "metodo": "Valor de robustez de Cinelli & Hazlett (2020)",
        "t": float(t),
        "df": int(df),
        "q": float(q),
        "rv": rv,
        "rv_pct": 100.0 * rv,
        "lectura": (
            f"Un confusor no medido tendría que explicar al menos {100.0 * rv:.1f} % "
            "del R² parcial de D y de Y, después de condicionar en X, para llevar "
            "el coeficiente OLS a cero."
        ),
        "limites": ("Exacto bajo el modelo lineal de sesgo por omisión para el OLS; "
                    "no es una propiedad exacta del AIPW."),
    }


def resumen_sensibilidad(ate: float, ic: list[float], sd_y: float,
                         ols: dict) -> dict:
    """Combina E-value y valor de robustez con una lectura conjunta."""
    ev = e_value_continuo(ate, sd_y, ic)
    rv = valor_robustez(ols["t"], ols["df"])
    return {
        "e_value": ev,
        "valor_robustez_ols": rv,
        "lectura": (
            f"E-value puntual {ev['e_value_punto']:.2f} "
            f"(IC {ev['e_value_ic']:.2f}); valor de robustez OLS "
            f"{rv['rv_pct']:.1f} %."
        ),
        "limites": (
            "Las dos medidas son cotas de sensibilidad, no pruebas de "
            "ignorabilidad. El E-value es aproximado para resultado continuo; "
            "el valor de robustez es exacto solo para el OLS."
        ),
    }


def placebo_permutacion(col: dict, esquema: EsquemaCausal, aipw_fn: AipwFn,
                        n_rep: int = 200, semilla: int = 4242) -> dict:
    """Placebo de tratamiento permutado.

    Permuta D, mantiene X e Y y los pliegues fijos, y reestima AIPW. Bajo la
    hipótesis nula fuerte de efecto cero, los placebo deben centrarse en 0.
    """
    if n_rep < 2:
        raise ValueError("n_rep debe ser al menos 2")
    D = col[esquema.tratamiento]
    if len(np.unique(D)) < 2:
        raise ValueError("el tratamiento no varía: no se puede permutar")

    ate_obs = float(aipw_fn(col, esquema)["ate"])
    rng = np.random.default_rng(semilla)
    placebos = np.empty(n_rep, dtype=float)
    for i in range(n_rep):
        col_perm = dict(col)
        col_perm[esquema.tratamiento] = rng.permutation(D)
        placebos[i] = float(aipw_fn(col_perm, esquema)["ate"])

    media = float(placebos.mean())
    sd = float(placebos.std(ddof=1))
    ic = [float(np.percentile(placebos, 2.5)),
          float(np.percentile(placebos, 97.5))]
    p_valor = float((1 + np.sum(np.abs(placebos) >= abs(ate_obs))) / (n_rep + 1))
    percentil = float(100.0 * np.mean(placebos <= ate_obs))
    dentro = ic[0] <= ate_obs <= ic[1]
    ok = not (p_valor > 0.05 or dentro)

    return {
        "metodo": "placebo de tratamiento permutado (AIPW, pliegues fijos)",
        "n_rep": int(n_rep),
        "semilla": int(semilla),
        "ate_observado": ate_obs,
        "placebo_media": media,
        "placebo_sd": sd,
        "placebo_ic95": ic,
        "percentil_observado": percentil,
        "p_valor_aprox": p_valor,
        "dentro_del_ic_placebo": bool(dentro),
        "placebo_ok": bool(ok),
        "lectura": (
            f"Bajo efecto cero, los placebo se centran en {media:.2f} "
            f"(DE {sd:.2f}); el ATE observado ({ate_obs:.2f}) está en el "
            f"percentil {percentil:.1f} (p Monte Carlo = {p_valor:.3f})."
        ),
        "que_no_prueba": (
            "No prueba ignorabilidad: un estimador confundido también puede "
            "rechazar la nula de placebo. Evalúa calibración e implementación."
        ),
    }


def control_negativo(col: dict, esquema: EsquemaCausal, aipw_fn: AipwFn,
                     variable: str = "momage", semilla: int = 4242) -> dict:
    """Placebo de resultado: permuta una covariable pre-tratamiento.

    Se permuta ``variable`` para romper cualquier relación con D y X y se usa
    como pseudo-resultado. El efecto causal verdadero es cero por construcción.
    No se reemplaza la covariable original en X: el pseudo-resultado viaja en
    una clave aparte para evitar que el modelo de resultado se ajuste a sí mismo.
    """
    if variable not in col:
        raise ValueError(f"variable de placebo ausente: {variable}")
    rng = np.random.default_rng(semilla)
    clave = "__placebo_outcome__"
    col_neg = dict(col)
    col_neg[clave] = rng.permutation(col[variable])
    res = aipw_fn(col_neg, esquema, resultado=clave)

    sd = float(np.std(col[variable], ddof=1))
    umbral = 0.1 * sd
    dentro = res["ic"][0] <= 0 <= res["ic"][1]
    material = abs(float(res["ate"])) > umbral
    ok = bool(dentro or not material)

    return {
        "metodo": "placebo de resultado permutado",
        "variable_base": variable,
        "variable_permutada": clave,
        "efecto": float(res["ate"]),
        "ic95": [float(res["ic"][0]), float(res["ic"][1])],
        "sd_variable": sd,
        "umbral_material": umbral,
        "dentro_de_cero": bool(dentro),
        "material": bool(material),
        "control_negativo_ok": ok,
        "lectura": (
            f"Se permutó {variable} y se usó como pseudo-resultado: efecto "
            f"{res['ate']:.2f} (IC 95 % [{res['ic'][0]:.2f}, {res['ic'][1]:.2f}]). "
            f"Umbral material: {umbral:.2f}."
        ),
        "que_no_prueba": (
            "No prueba ignorabilidad ni ausencia de confusión. Es un diagnóstico "
            "de calibración con un resultado sin relación causal con D."
        ),
    }
