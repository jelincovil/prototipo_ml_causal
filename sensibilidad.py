"""sensibilidad.py — E-value, robustez, Rosenbaum, Manski y placebos.

Módulo de la aplicación (no es un script auxiliar). No lee CSV ni
`interventions.json`: recibe las columnas ya cargadas por `estimacion.py` y
devuelve diccionarios listos para viajar en el bundle.

Las medidas de sensibilidad son complementarias y tienen límites distintos:

- E-value: aproximación para un resultado continuo estandarizado. La razón de
  riesgos se aproxima con ``RR ~ exp(0.91 * d)`` (Chinn 2000; VanderWeele &
  Ding 2017). No es una RR literal ni una cota exacta.
- Valor de robustez: exacto bajo el modelo lineal de sesgo por omisión para el
  comparador OLS (Cinelli & Hazlett 2020). No es una propiedad exacta del AIPW.
- Rosenbaum: acota el p-valor de la prueba de rangos con signo de Wilcoxon bajo
  odds de asignación oculta dentro de pares emparejados. No acota el ATE AIPW.
- Cotas de Manski: acotan el ATE sin suponer ignorabilidad, usando consistencia y
  un soporte acotado del resultado. No identifican un efecto puntual.

El placebo de tratamiento permutado y el placebo de resultado permutado son
controles negativos: evalúan calibración del estimador, no prueban
ignorabilidad.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Callable

import numpy as np
from scipy.stats import norm, rankdata

if TYPE_CHECKING:
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
        "que_responde": (
            "Fuerza mínima de asociación que un confusor no observado tendría "
            "que tener con tratamiento y resultado, bajo los supuestos y "
            "aproximaciones de la medida, para explicar el estimando o el "
            "límite del intervalo."
        ),
        "limites": (
            "Para resultado continuo usa RR ≈ exp(0.91·d): no es una RR "
            "literal ni una cota exacta. No demuestra ausencia de confusión "
            "ni cubre mala especificación, selección, error de medición, falta "
            "de positividad o dependencia entre unidades. Se complementa con "
            "el valor de robustez del OLS."
        ),
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


def cotas_manski(y: np.ndarray, d: np.ndarray,
                  soporte: tuple[float, float] | None = None) -> dict:
    """Cotas de Manski para el ATE sin suponer ignorabilidad condicional.

    Descompone cada media potencial en la parte observada en su brazo y la parte
    no observada en el otro brazo, acotada por ``[L, U]``. Si no se proporciona
    ``soporte``, usa el rango observado de ``y``: en ese caso las cotas son una
    ilustración de sensibilidad, pues los extremos muestrales no garantizan el
    soporte poblacional. El ancho del intervalo del ATE es siempre ``U - L``.
    """
    y = np.asarray(y, dtype=float).reshape(-1)
    d = np.asarray(d, dtype=float).reshape(-1)
    if y.size == 0 or y.size != d.size:
        raise ValueError("y y d deben tener el mismo tamaño, mayor que cero")
    if not np.all(np.isfinite(y)) or not np.all(np.isfinite(d)):
        raise ValueError("y y d deben ser finitos")
    if not np.all(np.isin(d, [0.0, 1.0])):
        raise ValueError("d debe ser binario (0/1)")

    n = int(y.size)
    n1 = int(d.sum())
    n0 = n - n1
    if n1 == 0 or n0 == 0:
        raise ValueError("se necesitan unidades tratadas y controles")

    if soporte is None:
        limite_inferior, limite_superior = float(y.min()), float(y.max())
        fuente_soporte = "mínimo y máximo observados en observed_train.csv"
        soporte_observado = True
    else:
        if len(soporte) != 2:
            raise ValueError("soporte debe ser (limite_inferior, limite_superior)")
        limite_inferior, limite_superior = map(float, soporte)
        fuente_soporte = "soporte poblacional declarado"
        soporte_observado = False
    if not np.isfinite([limite_inferior, limite_superior]).all():
        raise ValueError("el soporte del resultado debe ser finito")
    if limite_inferior > limite_superior:
        raise ValueError("el límite inferior no puede superar al superior")
    if y.min() < limite_inferior or y.max() > limite_superior:
        raise ValueError("los resultados observados quedan fuera del soporte declarado")

    p = n1 / n
    media1 = float(y[d == 1].mean())
    media0 = float(y[d == 0].mean())
    e_y1 = [p * media1 + (1 - p) * limite_inferior,
            p * media1 + (1 - p) * limite_superior]
    e_y0 = [(1 - p) * media0 + p * limite_inferior,
            (1 - p) * media0 + p * limite_superior]
    ate = [e_y1[0] - e_y0[1], e_y1[1] - e_y0[0]]
    ancho = float(ate[1] - ate[0])

    return {
        "metodo": "cotas de Manski sin ignorabilidad condicional",
        "aplicable": True,
        "n": n,
        "p_tratados": float(p),
        "media_y_d1": media1,
        "media_y_d0": media0,
        "soporte_y": [limite_inferior, limite_superior],
        "fuente_soporte": fuente_soporte,
        "soporte_observado": soporte_observado,
        "e_y1": [float(v) for v in e_y1],
        "e_y0": [float(v) for v in e_y0],
        "ate": [float(ate[0]), float(ate[1])],
        "ancho": ancho,
        "incluye_cero": bool(ate[0] <= 0 <= ate[1]),
        "identificacion_puntual": False,
        "supuestos": (
            "Consistencia/SUTVA, tratamiento binario y resultado acotado en el "
            "soporte indicado. No se supone ignorabilidad condicional."
        ),
        "lectura": (
            f"Sin ignorabilidad condicional, el ATE queda entre {ate[0]:.2f} y "
            f"{ate[1]:.2f}; el intervalo tiene ancho {ancho:.2f} y no identifica "
            "un valor puntual."
        ),
        "limites": (
            "El rango observado no garantiza el soporte poblacional: sin un "
            "soporte externo declarado, estas cotas son una ilustración de "
            "sensibilidad y pueden ser más estrechas que las cotas poblacionales."
            if soporte_observado else
            "Las cotas no identifican el ATE puntual; dependen de que el soporte "
            "poblacional declarado sea correcto."
        ),
    }


def p_superior_rosenbaum(diferencias: np.ndarray, gamma: float = 1.0) -> dict:
    """Cota pesimista de p para rangos con signo en diseño de pares.

    Prueba unilateral ``H0: sin efecto`` contra diferencias tratado-control
    positivas. Los ceros se eliminan y los empates reciben rango promedio.
    Bajo el modelo de Rosenbaum, ``p = Gamma/(1+Gamma)`` maximiza la media
    nula y produce la cota superior del p-valor con aproximación normal sin
    corrección de continuidad (Rosenbaum 1987; 2002, sección 4.3.3).
    """
    if not np.isfinite(gamma) or gamma < 1.0:
        raise ValueError("gamma debe ser finito y mayor o igual que 1")
    d = np.asarray(diferencias, dtype=float).reshape(-1)
    if not np.all(np.isfinite(d)):
        raise ValueError("las diferencias emparejadas deben ser finitas")
    d = d[np.abs(d) > np.finfo(float).eps * max(1.0, float(np.max(np.abs(d),
                                                                   initial=0.0)))]
    n = int(d.size)
    if n < 2:
        raise ValueError("se necesitan al menos dos diferencias emparejadas no nulas")
    q = rankdata(np.abs(d), method="average")
    observado = float(q[d > 0.0].sum())
    p = float(gamma / (1.0 + gamma))
    media = float(p * q.sum())
    varianza = float(p * (1.0 - p) * np.sum(q ** 2))
    sd = math.sqrt(varianza)
    z = (observado - media) / sd
    return {
        "gamma": float(gamma),
        "p_superior": float(norm.sf(z)),
        "estadistico": observado,
        "media_peimista": media,
        "desviacion_pesimista": sd,
        "z": float(z),
        "n_diferencias_no_nulas": n,
    }


def cota_gamma_rosenbaum(y: np.ndarray, d: np.ndarray,
                          propensiones_oof: np.ndarray,
                          caliper_sd: float = 0.2, alpha: float = 0.05,
                          gamma_max: float = 100.0) -> dict:
    """Γ crítica de Rosenbaum, tras emparejamiento por propensión sin reemplazo.

    Cada tratado se asigna en orden determinista al control disponible con
    menor distancia absoluta en el logit de la propensión, sujeto a
    ``caliper_sd * sd(logits)``. Los tratados empatados se resuelven por su
    índice original. Γ es la primera cota superior de p > ``alpha``.
    Este análisis se refiere al contraste emparejado retenido, no al AIPW.
    """
    y = np.asarray(y, dtype=float).reshape(-1)
    d = np.asarray(d, dtype=float).reshape(-1)
    e = np.asarray(propensiones_oof, dtype=float).reshape(-1)
    if y.size == 0 or y.size != d.size or y.size != e.size:
        raise ValueError("y, d y propensiones_oof deben tener igual tamaño positivo")
    if not all(np.all(np.isfinite(x)) for x in (y, d, e)):
        raise ValueError("y, d y propensiones_oof deben ser finitos")
    if not np.all(np.isin(d, [0.0, 1.0])):
        raise ValueError("d debe ser binario (0/1)")
    if np.any((e <= 0.0) | (e >= 1.0)):
        raise ValueError("las propensiones OOF deben estar estrictamente entre 0 y 1")
    if not 0.0 < caliper_sd < float("inf"):
        raise ValueError("caliper_sd debe ser positivo y finito")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha debe estar estrictamente entre 0 y 1")
    if not np.isfinite(gamma_max) or gamma_max < 1.0:
        raise ValueError("gamma_max debe ser finito y mayor o igual que 1")

    tratados = np.flatnonzero(d == 1.0)
    controles = np.flatnonzero(d == 0.0)
    if tratados.size < 2 or controles.size < 1:
        raise ValueError("se necesitan al menos dos tratados y un control")
    logits = np.log(e / (1.0 - e))
    sd_logit = float(logits.std(ddof=1))
    caliper = float(caliper_sd * sd_logit)
    libres: set[int] = set(map(int, controles))
    diferencias = []
    pares = []
    for i in tratados:
        if not libres:
            break
        candidato = min(libres, key=lambda j: (abs(logits[i] - logits[j]), j))
        distancia = float(abs(logits[i] - logits[candidato]))
        if distancia <= caliper:
            libres.remove(candidato)
            diferencias.append(float(y[i] - y[candidato]))
            pares.append({"tratado": int(i), "control": int(candidato),
                          "distancia_logit": distancia})
    if len(diferencias) < 2:
        raise ValueError("el caliper no retiene suficientes pares para Wilcoxon")

    dif = np.asarray(diferencias, dtype=float)
    if np.count_nonzero(np.abs(dif) > np.finfo(float).eps * max(
            1.0, float(np.max(np.abs(dif), initial=0.0)))) < 2:
        raise ValueError("los pares retenidos no contienen dos diferencias no nulas")
    p1 = p_superior_rosenbaum(dif, 1.0)["p_superior"]
    if p1 > alpha:
        gamma = 1.0
        pcota = p1
    else:
        # Busca el primer entero que cruza alpha y luego interpola el cruce.
        gamma_entero = next((g for g in range(2, int(math.floor(gamma_max)) + 1)
                             if p_superior_rosenbaum(dif, g)["p_superior"] > alpha),
                            None)
        if gamma_entero is None:
            gamma = None
            pcota = p_superior_rosenbaum(dif, gamma_max)["p_superior"]
        elif gamma_entero == 2:
            gamma = 2.0
            pcota = p_superior_rosenbaum(dif, gamma)["p_superior"]
        else:
            lo, hi = float(gamma_entero - 1), float(gamma_entero)
            for _ in range(60):
                medio = (lo + hi) / 2.0
                if p_superior_rosenbaum(dif, medio)["p_superior"] <= alpha:
                    lo = medio
                else:
                    hi = medio
            gamma = hi
            pcota = p_superior_rosenbaum(dif, gamma)["p_superior"]
    lectura = (
        f"El contraste emparejado deja de rechazar la nula al 5 % en Γ ≈ {gamma:.2f}: "
        "odds de asignación desiguales de esa magnitud ya podrían explicar el "
        "resultado de Wilcoxon." if gamma is not None else
        f"Ninguna Γ ≤ {gamma_max:g} hace que la cota superior de p supere {alpha:g}."
    )
    return {
        "metodo": "Rosenbaum Γ: Wilcoxon signed-rank en pares 1:1, aproximación normal",
        "aplicable": True,
        "objeto": "contraste de pares emparejados retenidos; no es una cota del ATE AIPW",
        "gamma": gamma,
        "p_gamma_1": p1,
        "p_gamma_cota": pcota,
        "alpha": float(alpha),
        "gamma_max_busqueda": float(gamma_max),
        "n_pares": len(diferencias),
        "n_diferencias_cero": int(np.sum(np.isclose(dif, 0.0))),
        "n_tratados_original": int(tratados.size),
        "n_controles_original": int(controles.size),
        "n_pares_descartados": int(tratados.size - len(diferencias)),
        "diseno_emparejamiento": {
            "metodo": "greedy por orden de tratado, vecino más próximo, sin reemplazo",
            "distancia": "distancia absoluta en logit de propensiones OOF sin trimming",
            "caliper_sd": float(caliper_sd),
            "sd_logit": sd_logit,
            "caliper": caliper,
            "criterio_ties": "índice original creciente del control",
            "pares_indices": pares,
        },
        "estadistico": "suma de rangos promedio de diferencias positivas; ceros excluidos",
        "direccion": "unilateral: efecto positivo, sin corrección de continuidad",
        "supuestos": (
            "Consistencia/SUTVA, independencia entre pares y asignación dentro de cada "
            "par; las odds ocultas dentro de un par están acotadas entre 1/Γ y Γ."
        ),
        "lectura": lectura,
        "referencia": (
            "Rosenbaum (1987), Biometrika 74(1), 13–26; Rosenbaum (2002), "
            "Observational Studies, 2.ª ed., sección 4.3.3."
        ),
        "limites": (
            "No es una cota de sensibilidad del ATE AIPW ni cubre mala especificación "
            "o falta de soporte. El resultado depende del emparejamiento, caliper y "
            "aproximación normal; Γ=1 supone asignación aleatoria dentro de los pares."
        ),
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
