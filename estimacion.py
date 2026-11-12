"""estimacion.py — [BLOQUE 3, min 35–60] El efecto con incertidumbre + diagnósticos.

Se completa en vivo: ate_ols, propensity, ess_kish, smd y la trampa.
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
from scipy.optimize import minimize

from datos import EsquemaCausal, leer
from rutas import ARTEFACTOS, DATOS, ESCENARIO
from sensibilidad import (control_negativo, cotas_manski,
                          placebo_permutacion, resumen_sensibilidad)

SEMILLA = 4242

# Corte de heterogeneidad por escenario: se declara ANTES de mirar los efectos.
CORTES = {
    "synthetic/jobs": {
        "variable": "nodegree", "umbral": 0.5,
        "etiquetas": {"1": "sin título", "0": "con título"},
        "regla": ("corte único por nodegree (título): criterio administrativo y de "
                  "interpretabilidad, declarado antes de mirar los efectos; "
                  "NO elegido por ganancia de varianza"),
    },
    "synthetic/ihdp": {
        "variable": "bw", "umbral": None,  # None -> mediana de la muestra de train
        "etiquetas": {"1": "bw alto (> mediana de train)",
                      "0": "bw bajo (<= mediana de train)"},
        "regla": ("corte único por peso al nacer (bw) en la mediana de train: es el eje "
                  "clínico del IHDP (bajo peso al nacer define la población del estudio), "
                  "declarado antes de mirar los efectos y NO elegido por ganancia de "
                  "varianza; la mediana preserva tamaño en ambas hojas"),
    },
}

UNIDAD = {"synthetic/jobs": "USD de 1978",
          "synthetic/ihdp": "puntos de test cognitivo"}
ETIQUETA_UNIDAD = {"synthetic/jobs": "USD", "synthetic/ihdp": "puntos"}
# La trampa se escala con la unidad del resultado (no tiene sentido en puntos).
RUIDO_TRAMPA = {"synthetic/jobs": 500.0, "synthetic/ihdp": 1.0}
# Covariable pre-tratamiento que se permuta como placebo de resultado.
VARIABLE_PLACEBO = {"synthetic/jobs": "educ", "synthetic/ihdp": "momage"}


def ate_ols(col: dict, esquema: EsquemaCausal, extra=None,
            resultado: str | None = None) -> dict:
    """ATE por OLS con los controles del esquema (+ columna trampa opcional).

    Devuelve también ``t`` y ``df`` para el valor de robustez de Cinelli-Hazlett.
    ``resultado`` permite usar un pseudo-resultado (placebo).
    """
    y_key = resultado or esquema.resultado
    n = len(col[esquema.tratamiento])
    D, Y = col[esquema.tratamiento], col[y_key]
    columnas = [col[c] for c in esquema.covariables] + (
        [extra["valores"]] if extra else [])
    M = np.column_stack([np.ones(n), D, *columnas])
    # OLS: el coeficiente del tratamiento es el ATE bajo el modelo lineal.
    beta = np.linalg.lstsq(M, Y, rcond=None)[0]
    residuo = Y - M @ beta
    df = int(n - M.shape[1])
    sigma2 = float(residuo @ residuo / df)
    cov = sigma2 * np.linalg.inv(M.T @ M)
    ate = float(beta[1])
    se = float(np.sqrt(cov[1, 1]))
    t = float(ate / se) if se > 0 else float("inf")
    return {"ate": ate, "se": se, "ic": [ate - 1.96 * se, ate + 1.96 * se],
            "t": t, "df": df, "n": int(n), "k": int(len(columnas))}


def propensity(X: np.ndarray, D: np.ndarray) -> np.ndarray:
    """Logística por máxima verosimilitud (BFGS, covariables estandarizadas)."""
    Z = (X - X.mean(0)) / X.std(0)
    # Soporte: la logística se ajusta por máxima verosimilitud (BFGS).
    def nll(w):
        eta = Z @ w[1:] + w[0]
        return float(np.sum(np.logaddexp(0, eta) - D * eta))

    r = minimize(nll, np.zeros(Z.shape[1] + 1), method="BFGS")
    eta = Z @ r.x[1:] + r.x[0]
    return 1 / (1 + np.exp(-eta))


def ess_kish(D: np.ndarray, e: np.ndarray) -> float:
    """Tamaño efectivo de la ponderación IPW: ESS = (sum w)^2 / sum w^2."""
    # ESS: cuántas unidades "cuentan" de verdad bajo los pesos IPW.
    e = np.clip(e, 1e-6, 1 - 1e-6)
    w = np.where(D == 1, 1 / e, 1 / (1 - e))
    return float(w.sum() ** 2 / np.sum(w ** 2))


def diagnosticos_positividad(e: np.ndarray, D: np.ndarray) -> dict:
    """Resume las propensiones fuera de pliegue antes del trimming.

    Los cuantiles y el porcentaje recortado describen el soporte observado; no
    demuestran positividad poblacional ni solapamiento multivariable.
    """
    e = np.asarray(e, dtype=float).reshape(-1)
    D = np.asarray(D, dtype=float).reshape(-1)
    if e.size == 0 or e.size != D.size:
        raise ValueError("e y D deben tener el mismo tamaño, mayor que cero")
    if not np.all(np.isfinite(e)) or not np.all(np.isfinite(D)):
        raise ValueError("e y D deben ser finitos")
    if np.any((e < 0.0) | (e > 1.0)):
        raise ValueError("las propensiones deben estar en [0, 1]")
    if not np.all(np.isin(D, [0.0, 1.0])):
        raise ValueError("D debe ser binario (0/1)")

    def resumen(valores: np.ndarray) -> dict:
        n = int(valores.size)
        if n == 0:
            return {"n": 0, "min": None, "p05": None, "p25": None,
                    "mediana": None, "p75": None, "p95": None, "max": None,
                    "recortado_n": 0, "recortado_pct": 0.0}
        q05, q25, q50, q75, q95 = np.quantile(
            valores, [0.05, 0.25, 0.50, 0.75, 0.95])
        recortado = int(np.sum((valores < 0.05) | (valores > 0.95)))
        return {
            "n": n,
            "min": float(valores.min()), "p05": float(q05),
            "p25": float(q25), "mediana": float(q50),
            "p75": float(q75), "p95": float(q95),
            "max": float(valores.max()),
            "recortado_n": recortado,
            "recortado_pct": float(100.0 * recortado / n),
        }

    total = resumen(e)
    ess = ess_kish(D, np.clip(e, 0.05, 0.95))
    total["ess"] = ess
    total["ess_sobre_n"] = float(ess / len(D))
    return {
        "fuente": "propensiones fuera de pliegue, antes del trimming",
        "recorte": [0.05, 0.95],
        "rango": [float(e.min()), float(e.max())],
        "fraccion_solapamiento": float(
            np.mean((e >= 0.05) & (e <= 0.95))),
        "total": total,
        "tratados": resumen(e[D == 1]),
        "controles": resumen(e[D == 0]),
        "ess": ess,
        "ess_sobre_n": float(ess / len(D)),
        "advertencia": (
            "El recorte limita pesos extremos, pero no garantiza positividad "
            "poblacional ni solapamiento multivariable; los rangos marginales "
            "del servicio tampoco descartan extrapolación conjunta."
        ),
    }


def smd(v: np.ndarray, D: np.ndarray) -> float:
    """Diferencia media estandarizada: tratados vs controles (Cap. 7)."""
    # Balance: la diferencia de medias en unidades de desviación común.
    t, c = v[D == 1], v[D == 0]
    return float((t.mean() - c.mean()) / np.sqrt((t.var() + c.var()) / 2))


def smd_ponderado(v: np.ndarray, D: np.ndarray, e: np.ndarray) -> float:
    """SMD ponderado por IPW: balance después de ponderar por propensión.

    Es un diagnóstico muestral; no corrige el estimador ni prueba balance
    poblacional. Se recorta e a [0,05; 0,95] para evitar pesos extremos.
    """
    e = np.clip(np.asarray(e, dtype=float), 0.05, 0.95)
    w = np.where(D == 1, 1.0 / e, 1.0 / (1.0 - e))
    t, c = D == 1, D == 0
    if not t.any() or not c.any():
        return float("nan")

    def _media_var(x: np.ndarray, pesos: np.ndarray) -> tuple[float, float]:
        m = float(np.average(x, weights=pesos))
        var = float(np.average((x - m) ** 2, weights=pesos))
        return m, var

    m1, v1 = _media_var(v[t], w[t])
    m0, v0 = _media_var(v[c], w[c])
    denom = math.sqrt((v1 + v0) / 2.0)
    return float((m1 - m0) / denom) if denom > 0 else float("nan")


def _ajustar_lineal(Xm: np.ndarray, y: np.ndarray) -> np.ndarray:
    M = np.column_stack([np.ones(len(y)), Xm])
    return np.linalg.lstsq(M, y, rcond=None)[0]


def _propensity_fit(Xm: np.ndarray, d: np.ndarray):
    """Logística ajustada en Xm/d; devuelve una función que predice en nuevas filas."""
    med, desv = Xm.mean(0), Xm.std(0)
    Z = (Xm - med) / desv
    def nll(w):
        eta = Z @ w[1:] + w[0]
        return float(np.sum(np.logaddexp(0, eta) - d * eta))
    r = minimize(nll, np.zeros(Xm.shape[1] + 1), method="BFGS")
    def predecir(Xn: np.ndarray) -> np.ndarray:
        Zn = (Xn - med) / desv
        return 1 / (1 + np.exp(-(Zn @ r.x[1:] + r.x[0])))
    return predecir


def aipw_crossfit(col: dict, esquema: EsquemaCausal, k: int = 5,
                  resultado: str | None = None,
                  semilla_folds: int = SEMILLA) -> dict:
    """ATE doblemente robusto con cross-fitting (el DML del Cap. 9 en miniatura).

    Ningún nuisance ve a la unidad que predice: los folds se ajustan fuera y
    predicen dentro. El score por unidad es la influence function del ATE.
    ``resultado`` permite usar un pseudo-resultado (placebo).
    """
    y_key = resultado or esquema.resultado
    n = len(col[esquema.tratamiento])
    D, Y = col[esquema.tratamiento], col[y_key]
    X = np.column_stack([col[c] for c in esquema.covariables])
    if k < 2 or n < k:
        raise ValueError(f"cross-fitting inválido: n={n}, k={k}")
    g = np.random.default_rng(semilla_folds)
    folds = np.array_split(g.permutation(n), k)
    mu1, mu0, e = np.empty(n), np.empty(n), np.empty(n)
    for fold in folds:
        # Cross-fitting: ningún nuisance ve a la unidad que predice.
        fuera = np.ones(n, dtype=bool)
        fuera[fold] = False
        dentro = np.zeros(n, dtype=bool)
        dentro[fold] = True
        b1 = _ajustar_lineal(X[fuera & (D == 1)], Y[fuera & (D == 1)])
        b0 = _ajustar_lineal(X[fuera & (D == 0)], Y[fuera & (D == 0)])
        Xf = np.column_stack([np.ones(dentro.sum()), X[dentro]])
        mu1[dentro], mu0[dentro] = Xf @ b1, Xf @ b0
        e[dentro] = _propensity_fit(X[fuera], D[fuera])(X[dentro])

    positividad = diagnosticos_positividad(e, D)
    propensiones_oof = e.copy()
    e = np.clip(e, 0.05, 0.95)  # trimming declarado en la tarjeta
    score = (mu1 - mu0 + D * (Y - mu1) / e - (1 - D) * (Y - mu0) / (1 - e))
    ate = float(score.mean())
    se = float(score.std(ddof=1) / np.sqrt(n))
    return {"ate": ate, "se": se, "ic": [ate - 1.96 * se, ate + 1.96 * se],
            "scores": score, "propensiones_oof": propensiones_oof,
            "diagnosticos_positividad": positividad}


def estratos_heterogeneidad(score: np.ndarray, col: dict,
                            esquema: EsquemaCausal) -> dict:
    """Un solo corte de heterogeneidad, pre-declarado en la tarjeta.

    No es un CATE: es la media de scores AIPW de cada estrato, con su IC.
    """
    corte = CORTES[ESCENARIO]
    variable = corte["variable"]
    umbral = corte["umbral"]
    if umbral is None:
        umbral = float(np.median(col[variable]))
    grupo = (col[variable] > umbral).astype(int)
    hojas = {}
    for clave in ("1", "0"):
        sel = grupo == int(clave)
        s = score[sel]
        media = float(s.mean())
        se = float(s.std(ddof=1) / np.sqrt(len(s)))
        hojas[clave] = {"etiqueta": corte["etiquetas"][clave], "n": int(sel.sum()),
                        "efecto": media, "se": se,
                        "ic": [media - 1.96 * se, media + 1.96 * se]}
    # La nota se deriva de los IC: no se afirma lo contrario de lo que muestran.
    ic_alto, ic_bajo = hojas["1"]["ic"], hojas["0"]["ic"]
    solapan = ic_alto[0] <= ic_bajo[1] and ic_bajo[0] <= ic_alto[1]
    nota = ("los intervalos de los estratos se solapan: heterogeneidad sugerida, "
            "no concluyente" if solapan else
            "los intervalos de los estratos no se solapan: diferencia consistente "
            "con el corte declarado, pero no es un CATE")
    return {"variable": variable, "umbral": umbral, "regla": corte["regla"],
            "nota": nota, "hojas": hojas}





def trampa_score_post(col: dict, esquema: EsquemaCausal) -> dict:
    """Columna derivada del resultado: 'score de éxito' calculado con re78."""
    g = np.random.default_rng(SEMILLA)
    D, Y = col[esquema.tratamiento], col[esquema.resultado]
    # La trampa: una columna calculada CON el resultado (Cap. 6).
    score = 0.6 * Y + 0.4 * D + g.normal(0, RUIDO_TRAMPA[ESCENARIO], len(Y))
    return ate_ols(col, esquema, extra={"valores": score})


def modelo_individual(score: np.ndarray, col: dict, esquema: EsquemaCausal) -> dict:
    """Proyección lineal del score AIPW sobre X: efecto esperado para un perfil.

    No es un CATE validado: es la mejor aproximación lineal al score doblemente
    robusto. Se registra el modelo (coeficientes y covarianza), nunca los scores
    por unidad (la regla del kit prohíbe `tau` en el bundle).
    """
    X = np.column_stack([col[c] for c in esquema.covariables])
    medias, desviaciones = X.mean(0), X.std(0)
    Z = (X - medias) / desviaciones
    M = np.column_stack([np.ones(len(score)), Z])
    beta = np.linalg.lstsq(M, score, rcond=None)[0]
    residuo = score - M @ beta
    gl = len(score) - M.shape[1]
    sigma2 = float(residuo @ residuo / gl)
    cov_beta = sigma2 * np.linalg.pinv(M.T @ M)
    ss_total = float(((score - score.mean()) ** 2).sum())
    r2 = 1.0 - float(residuo @ residuo) / ss_total if ss_total > 0 else 0.0
    return {
        "tipo": "proyección lineal del score AIPW sobre las covariables",
        "intercepto": float(beta[0]),
        "coeficientes": {c: float(b) for c, b in zip(esquema.covariables, beta[1:])},
        "medias": {c: float(m) for c, m in zip(esquema.covariables, medias)},
        "desviaciones": {c: float(s) for c, s in zip(esquema.covariables, desviaciones)},
        "cov_beta": [[float(v) for v in fila] for fila in cov_beta],
        "r2": r2,
        "n": int(len(score)),
        "semilla": SEMILLA,
    }


def _grafo_backdoor_networkx(esquema: EsquemaCausal):
    """DAG (networkx.DiGraph) con covariables observadas → D y Y; D → Y.

    DoWhy acepta el grafo como DiGraph de forma fiable; un string DOT largo con
    nombres con punto puede rechazarse según la versión del parseo.
    """
    import networkx as nx

    t, y = esquema.tratamiento, esquema.resultado
    g = nx.DiGraph()
    for c in esquema.covariables:
        g.add_edge(c, t)
        g.add_edge(c, y)
    g.add_edge(t, y)
    return g


def _grafo_dot_desde_networkx(g) -> str:
    """Serializa el DiGraph a DOT cuando pydot está disponible (dependencia de networkx)."""
    try:
        from networkx.drawing.nx_pydot import write_dot
        import io

        buf = io.StringIO()
        write_dot(g, buf)
        return buf.getvalue()
    except Exception:
        return ""


def aristas_grafo(g) -> list[tuple[str, str]]:
    return [(str(u), str(v)) for u, v in g.edges()]


def identificacion_dowhy(col: dict, esquema: EsquemaCausal) -> dict:
    """Identificación del ATE con DoWhy sobre un DAG explícito (covariables observadas).

    - ``method_name='default'`` devuelve un ``IdentifiedEstimand`` con
      ``get_backdoor_variables()`` (criterio backdoor en el grafo).
    - ``method_name='id-algorithm'`` devuelve una ``IDExpression`` (Pearl); sirve
      como resumen algebraico del estimando identificado, sin reemplazar el
      conjunto de ajuste anterior.
    """
    g = _grafo_backdoor_networkx(esquema)
    grafo_dot = _grafo_dot_desde_networkx(g)
    aristas = aristas_grafo(g)
    nota_grafo = (
        "Solo covariables observadas pre-tratamiento → backdoor clásico; "
        "amenazas no observadas se acotan con E-value/placebos, no con este DAG.")
    benchmark = json.loads((DATOS / "identification.json").read_text())
    valid_sets = benchmark.get("valid_adjustment_sets") or []

    try:
        import pandas as pd
        from dowhy import CausalModel
    except ImportError as exc:
        return {
            "aplicable": False,
            "criterio_principal": "backdoor",
            "criterio_backdoor_pasa": False,
            "identificacion_pasa": False,
            "motivo": f"dependencias ausentes: {exc}",
            "grafo_dot": grafo_dot,
            "aristas": aristas,
            "nota_grafo": nota_grafo,
        }

    try:
        df = pd.DataFrame({c: col[c] for c in esquema.columnas()})
        model = CausalModel(
            data=df,
            treatment=esquema.tratamiento,
            outcome=esquema.resultado,
            graph=g,
        )
        identified_default = model.identify_effect(method_name="default")
        expr_id = model.identify_effect(method_name="id-algorithm")
    except Exception as exc:
        return {
            "aplicable": False,
            "criterio_principal": "backdoor",
            "criterio_backdoor_pasa": False,
            "identificacion_pasa": False,
            "motivo": str(exc),
            "grafo_dot": grafo_dot,
            "aristas": aristas,
            "metodos_dowhy": {"conjunto": "default", "expresion_id": "id-algorithm"},
            "nota_grafo": nota_grafo,
        }

    conjunto = sorted({str(v) for v in (identified_default.get_backdoor_variables()
                                         or [])})
    texto_default = str(identified_default)
    texto_id = str(expr_id)
    coincide = False
    if conjunto and valid_sets:
        bench0 = [str(x) for x in valid_sets[0]]
        coincide = sorted(conjunto) == sorted(bench0)

    return {
        "aplicable": True,
        "criterio_principal": "backdoor",
        "criterio_backdoor_pasa": len(conjunto) > 0,
        "identificacion_pasa": len(conjunto) > 0 and coincide,
        "metodos_dowhy": {
            "conjunto_backdoor": "default",
            "expresion_estimando": "id-algorithm",
        },
        "criterio": (
            "Grafo causal explícito (X→D, X→Y, D→Y con X pre-tratamiento): "
            "DoWhy `default` aplica criterio backdoor y devuelve el conjunto de "
            "ajuste; `id-algorithm` devuelve la expresión ID (Pearl) del ATE."),
        "fuente_conjunto": "IdentifiedEstimand.get_backdoor_variables()",
        "conjunto_ajuste_estimado": conjunto,
        "efecto_identificable_por_grafo": len(conjunto) > 0,
        "coincide_valid_adjustment_sets": coincide,
        "identification_status_benchmark": benchmark.get("identification_status"),
        "grafo_dot": grafo_dot,
        "aristas": aristas,
        "nota_grafo": nota_grafo,
        "resumen_identified_estimand": texto_default[:8000],
        "resumen_id_algorithm": texto_id[:12000],
    }


def validacion_particiones(esquema: EsquemaCausal) -> dict:
    """Estabilidad del ATE en train/validation/test (chequeo, no estimando).

    El estimando primario sigue siendo el de train. Las otras particiones se
    usan para mostrar que el número no depende de una partición concreta; no
    son un holdout aleatorizado ni una prueba de ignorabilidad.
    """
    salida = {}
    for parte in ("train", "validation", "test"):
        col = leer(parte)
        n = len(col[esquema.tratamiento])
        k = 5 if n >= 100 else 3
        res = aipw_crossfit(col, esquema, k=k)
        salida[parte] = {"n": int(n), "ate": res["ate"], "se": res["se"],
                         "ic": res["ic"]}
    return salida


def estimar() -> dict:
    esquema = EsquemaCausal()
    col = leer("train")
    D, Y = col[esquema.tratamiento], col[esquema.resultado]
    X = np.column_stack([col[c] for c in esquema.covariables])

    crude = float(Y[D == 1].mean() - Y[D == 0].mean())
    se_crude = float(math.sqrt(Y[D == 1].var(ddof=1) / int(D.sum())
                              + Y[D == 0].var(ddof=1) / int((1 - D).sum())))
    ic_crude = [crude - 1.96 * se_crude, crude + 1.96 * se_crude]
    ajustado = ate_ols(col, esquema)
    trampa = trampa_score_post(col, esquema)
    aipw = aipw_crossfit(col, esquema)
    estratos = estratos_heterogeneidad(aipw["scores"], col, esquema)
    individual = modelo_individual(aipw["scores"], col, esquema)

    e = aipw["propensiones_oof"]
    positividad = aipw["diagnosticos_positividad"]
    smds = {c: smd(col[c], D) for c in esquema.covariables}
    smds_w = {c: smd_ponderado(col[c], D, e) for c in esquema.covariables}
    smd_w_max = max((abs(v) for v in smds_w.values() if np.isfinite(v)),
                    default=0.0)

    sd_y = float(Y.std(ddof=1))
    sens = resumen_sensibilidad(aipw["ate"], aipw["ic"], sd_y, ajustado)
    sens["cotas_manski"] = cotas_manski(Y, D)
    placebo_d = placebo_permutacion(col, esquema, aipw_crossfit, n_rep=200,
                                    semilla=SEMILLA)
    placebo_y = control_negativo(col, esquema, aipw_crossfit,
                                 variable=VARIABLE_PLACEBO[ESCENARIO],
                                 semilla=SEMILLA)
    validacion = validacion_particiones(esquema)
    identificacion = identificacion_dowhy(col, esquema)
    comparacion = {
        "ingenuo": {"ate": crude, "se": se_crude, "ic95": ic_crude},
        "ols_ajustado": {"ate": ajustado["ate"], "se": ajustado["se"],
                         "ic95": ajustado["ic"]},
        "aipw": {"ate": aipw["ate"], "se": aipw["se"], "ic95": aipw["ic"]},
        "lectura": (
            "La coincidencia no prueba identificación; una discrepancia orienta "
            "la revisión de confusión, especificación y soporte."
        ),
    }
    dataset_sha256 = hashlib.sha256(
        (DATOS / "observed_train.csv").read_bytes()).hexdigest()

    return {
        "escenario": ESCENARIO,
        "estimando": f"ATE de {esquema.tratamiento} sobre {esquema.resultado} (efecto total)",
        "unidad": UNIDAD[ESCENARIO],
        "n": int(len(D)),
        "tratados": int(D.sum()),
        "diferencia_cruda": crude,
        "se_diferencia_cruda": se_crude,
        "ic_diferencia_cruda": ic_crude,
        "comparacion_estimadores": comparacion,
        "diagnosticos_positividad": positividad,
        "ate_ols": ajustado["ate"], "se": ajustado["se"], "ic95": ajustado["ic"],
        "estimador_principal": "AIPW con cross-fitting (K=5, nuisances fuera de muestra)",
        "ate_aipw": aipw["ate"], "se_aipw": aipw["se"], "ic_aipw": aipw["ic"],
        "estratos": estratos,
        "modelo_individual": individual,
        "ate_trampa_score_post": trampa["ate"],
        "ess": positividad["ess"],
        "ess_sobre_n": positividad["ess_sobre_n"],
        "rango_e": positividad["rango"],
        "fraccion_solapamiento": positividad["fraccion_solapamiento"],
        "smd_max": max(abs(v) for v in smds.values()),
        "smd_por_covariable": {k: round(v, 3) for k, v in smds.items()},
        "smd_ponderado_max": float(smd_w_max),
        "smd_ponderado_por_covariable": {
            k: (round(float(v), 3) if np.isfinite(v) else None)
            for k, v in smds_w.items()},
        "sd_resultado": sd_y,
        "dataset_sha256": dataset_sha256,
        "sensibilidad": sens,
        "placebo": {
            "pasa": bool(placebo_d["placebo_ok"]
                         and placebo_y["control_negativo_ok"]),
            "tratamiento_permutado_pasa": bool(placebo_d["placebo_ok"]),
            "resultado_permutado_pasa": bool(placebo_y["control_negativo_ok"]),
            "tratamiento_permutado": placebo_d,
            "resultado_permutado": placebo_y,
        },
        "validacion_particiones": validacion,
        "identificacion": identificacion,
        "rangos_covariables": {c: [float(col[c].min()), float(col[c].max())]
                               for c in esquema.covariables},
        "semilla": SEMILLA,
    }


if __name__ == "__main__":
    r = estimar()
    ARTEFACTOS.mkdir(exist_ok=True)
    (ARTEFACTOS / "estimacion.json").write_text(
        json.dumps(r, indent=2, ensure_ascii=False))
    (ARTEFACTOS / "sensibilidad.json").write_text(
        json.dumps(r["sensibilidad"], indent=2, ensure_ascii=False) + "\n")
    (ARTEFACTOS / "placebo.json").write_text(
        json.dumps(r["placebo"], indent=2, ensure_ascii=False) + "\n")
    print(f"diferencia cruda E[Y|D=1]-E[Y|D=0] = {r['diferencia_cruda']:.1f} "
          f"{ETIQUETA_UNIDAD[ESCENARIO]}")
    print(f"ATE OLS ({len(EsquemaCausal().covariables)} controles) = {r['ate_ols']:.1f} "
          f"| SE = {r['se']:.1f} "
          f"| IC95 = [{r['ic95'][0]:.1f}, {r['ic95'][1]:.1f}]")
    print(f"AIPW cross-fitting K=5 = {r['ate_aipw']:.1f} | SE = {r['se_aipw']:.1f} "
          f"| IC95 = [{r['ic_aipw'][0]:.1f}, {r['ic_aipw'][1]:.1f}]")
    print(f"trampa score_post      = {r['ate_trampa_score_post']:.1f}  "
          "<- el coeficiente se atenúa (fuga de información)")
    for v, h in r["estratos"]["hojas"].items():
        print(f"estrato {r['estratos']['variable']}={v} "
              f"({h['etiqueta']}, n={h['n']}): "
              f"efecto {h['efecto']:.1f} IC95 [{h['ic'][0]:.1f}, {h['ic'][1]:.1f}]")
    print(f"ESS = {r['ess']:.0f} (ESS/n = {r['ess_sobre_n']:.2f}) | "
          f"rango e = [{r['rango_e'][0]:.3f}, {r['rango_e'][1]:.3f}] | "
          f"solapamiento = {r['fraccion_solapamiento']:.0%}")
    print(f"SMD máx (sin ponderar) = {r['smd_max']:.2f} | "
          f"SMD ponderado máx = {r['smd_ponderado_max']:.2f}")
    ev = r["sensibilidad"]["e_value"]
    rv = r["sensibilidad"]["valor_robustez_ols"]
    print(f"sensibilidad: E-value = {ev['e_value_punto']:.2f} "
          f"(IC {ev['e_value_ic']:.2f}) | RV OLS = {rv['rv_pct']:.1f} %")
    manski = r["sensibilidad"]["cotas_manski"]
    print(f"Manski ATE (sin ignorabilidad) = [{manski['ate'][0]:.2f}, "
          f"{manski['ate'][1]:.2f}] | soporte Y observado = "
          f"[{manski['soporte_y'][0]:.2f}, {manski['soporte_y'][1]:.2f}]")
    ident = r["identificacion"]
    print(f"identificación: criterio backdoor = "
          f"{'pasa' if ident.get('identificacion_pasa') else 'falla'} | "
          f"DoWhy = {ident.get('aplicable', False)}")
    p_d = r["placebo"]["tratamiento_permutado"]
    p_y = r["placebo"]["resultado_permutado"]
    print(f"placebo D: p = {p_d['p_valor_aprox']:.3f} | "
          f"percentil = {p_d['percentil_observado']:.1f} | "
          f"ok = {p_d['placebo_ok']}")
    print(f"placebo Y ({p_y['variable_base']}): efecto = {p_y['efecto']:.2f} "
          f"IC95 = [{p_y['ic95'][0]:.2f}, {p_y['ic95'][1]:.2f}] | "
          f"ok = {p_y['control_negativo_ok']}")
    for parte, v in r["validacion_particiones"].items():
        print(f"validación {parte:10s}: ATE = {v['ate']:.2f} "
              f"IC95 = [{v['ic'][0]:.2f}, {v['ic'][1]:.2f}] (n = {v['n']})")
    print("artefacto: artifacts/estimacion.json")
