"""monitor.py — [BLOQUE 5, min 90–115] C-02 + puerta causal.

La puerta distingue cinco acciones, en orden de severidad:
``abstenerse`` > ``revisar_identificacion`` > ``reentrenar`` > ``alertar`` >
``continuar``. El servicio lee ``artifacts/monitor_estado.json``; la ventana de
producción (por defecto ``sana``) es la que fija la puerta. Las demás ventanas
son evidencias de estrés y no deben bloquear el servicio por sí solas.
"""
from __future__ import annotations

import json
import os

from datetime import datetime, timezone

import numpy as np

from datos import EsquemaCausal, leer
from estimacion import (aipw_crossfit, ess_kish, propensity, smd,
                        smd_ponderado)
from registro import champion
from rutas import ARTEFACTOS, ESCENARIO, REGISTRO

SEMILLA_VENTANA = 4242

# Ventanas por escenario: qué covariable mueve la deriva, cuál ordena la
# positividad y cuál se usa para el estrés de balance.
CONFIG = {
    "synthetic/jobs": {"sana_n": 700, "deriva": ("age", 10.0),
                       "positividad": "re74", "balance": "educ"},
    "synthetic/ihdp": {"sana_n": 300, "deriva": ("bw", 1.0),
                       "positividad": "bw", "balance": "momage"},
}

ESTADO = {"continuar": "pasa", "alertar": "alerta",
          "revisar_identificacion": "alerta", "reentrenar": "alerta",
          "abstenerse": "falla"}
PUERTA = {"continuar": "pasa", "alertar": "alerta",
          "revisar_identificacion": "revisar_identificacion",
          "reentrenar": "reentrenar", "abstenerse": "falla"}
ORDEN = {"continuar": 0, "alertar": 1, "reentrenar": 2,
         "revisar_identificacion": 3, "abstenerse": 4}
FACTORES_UMBRALES = (0.8, 1.0, 1.2)


def psi(ref: np.ndarray, nueva: np.ndarray, bins: int = 10, eps: float = 1e-4) -> float:
    """Population Stability Index entre una referencia y una ventana."""
    # Deriva: los deciles de la referencia fijan los cortes; se comparan frecuencias.
    cortes = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    a = np.histogram(ref, bins=cortes)[0] / len(ref)
    b = np.histogram(nueva, bins=cortes)[0] / len(nueva)
    a, b = np.clip(a, eps, None), np.clip(b, eps, None)
    return float(np.sum((a - b) * np.log(a / b)))


def ventana_sana(train: dict, esquema: EsquemaCausal) -> dict:
    """Otra extracción de la misma población (submuestra sin reemplazo)."""
    # Otra extracción de la misma población: sin reemplazo, semilla fija.
    g = np.random.default_rng(SEMILLA_VENTANA)
    n = len(train[esquema.tratamiento])
    idx = g.choice(n, min(CONFIG[ESCENARIO]["sana_n"], n), replace=False)
    return {columna: valores[idx] for columna, valores in train.items()}


def ventana_deriva(train: dict, esquema: EsquemaCausal) -> dict:
    """La población envejeció: la edad llega corrida diez años."""
    # Copia, no mutación: el train original queda intacto.
    variable, corrimiento = CONFIG[ESCENARIO]["deriva"]
    ventana = {columna: valores.copy() for columna, valores in train.items()}
    ventana[variable] = ventana[variable] + corrimiento
    return ventana


def ventana_positividad(train: dict, esquema: EsquemaCausal) -> dict:
    """La asignación se volvió casi determinista por ingreso previo (re74)."""
    # Asignación casi determinista: tratados altos (p75), controles bajos (p25).
    D = train[esquema.tratamiento]
    eje = train[CONFIG[ESCENARIO]["positividad"]]
    p25, p75 = np.percentile(eje, [25, 75])
    seleccion = ((D == 1) & (eje > p75)) | ((D == 0) & (eje < p25))
    return {columna: valores[seleccion] for columna, valores in train.items()}


def ventana_balance(train: dict, esquema: EsquemaCausal) -> dict:
    """Estrés de balance: tratados y controles se separan 0,3 DE en una covariable."""
    variable = CONFIG[ESCENARIO]["balance"]
    ventana = {columna: valores.copy() for columna, valores in train.items()}
    D = train[esquema.tratamiento]
    desv = float(train[variable].std())
    ventana[variable] = np.where(D == 1,
                                 train[variable] + 0.3 * desv,
                                 train[variable] - 0.3 * desv)
    return ventana


def ventana_confusor_oculto(train: dict, esquema: EsquemaCausal) -> dict:
    """Estrés de identificación: U no medida afecta a D y a Y.

    El monitor no observa U; esta ventana sirve para mostrar el sesgo y para
    comprobar que la estabilidad del efecto o la sensibilidad lo delatan. No es
    una prueba de detección universal: un confusor oculto puede ser indetectable
    con los datos observados.
    """
    g = np.random.default_rng(SEMILLA_VENTANA + 1)
    n = len(train[esquema.tratamiento])
    U = g.normal(size=n)
    prob = 1.0 / (1.0 + np.exp(-(U - np.median(U))))
    D_nuevo = (g.random(n) < prob).astype(float)
    if np.unique(D_nuevo).size < 2:
        D_nuevo[: n // 2] = 1.0
        D_nuevo[n // 2:] = 0.0
    ventana = {columna: valores.copy() for columna, valores in train.items()}
    ventana[esquema.tratamiento] = D_nuevo
    ventana[esquema.resultado] = train[esquema.resultado] + 0.8 * U
    return ventana


VENTANAS = {
    "sana": ventana_sana,
    "deriva": ventana_deriva,
    "positividad": ventana_positividad,
    "balance": ventana_balance,
    "confusor_oculto": ventana_confusor_oculto,
}


def medir_ventana(train: dict, ventana: dict, esquema: EsquemaCausal, *,
                   ate_champion: float | None = None) -> dict:
    """Calcula las señales una vez; la clasificación puede variar los umbrales."""
    Dw = ventana[esquema.tratamiento]
    n = int(len(Dw))
    if np.unique(Dw).size < 2:
        return {"n": n, "tratamiento_varia": False}

    Xw = np.column_stack([ventana[c] for c in esquema.covariables])
    e = propensity(Xw, Dw)
    psis = {c: psi(train[c], ventana[c]) for c in esquema.covariables}
    smds_w = {c: smd_ponderado(ventana[c], Dw, e)
              for c in esquema.covariables}
    ate_ventana = None
    estabilidad_diff = None
    if ate_champion is not None and n >= 20:
        res = aipw_crossfit(ventana, esquema, k=5 if n >= 100 else 3)
        ate_ventana = float(res["ate"])
        estabilidad_diff = abs(ate_ventana - float(ate_champion))
    return {
        "n": n,
        "tratamiento_varia": True,
        "solapamiento": float(((e >= 0.05) & (e <= 0.95)).mean()),
        "ess_sobre_n": ess_kish(Dw, e) / n,
        "psis": psis,
        "psi_max": max(psis.values()),
        "smd_max": max(abs(smd(ventana[c], Dw)) for c in esquema.covariables),
        "smds_w": smds_w,
        "smd_ponderado_max": max(
            (abs(v) for v in smds_w.values() if np.isfinite(v)), default=0.0),
        "ate_ventana": ate_ventana,
        "estabilidad_diff": estabilidad_diff,
    }


def clasificar_ventana(medidas: dict, umbrales: dict, *,
                       ate_champion: float | None = None,
                       se_champion: float | None = None,
                       placebo_ok: bool = True,
                       control_negativo_ok: bool = True) -> dict:
    """Convierte señales ya calculadas en una de las cinco acciones."""
    n = medidas["n"]
    if not medidas["tratamiento_varia"]:
        return {"estado": "falla", "accion": "abstenerse",
                "estado_puerta": "falla", "n": n,
                "motivo": ["el tratamiento no varía en la ventana"],
                "psi_max": None, "smd_max": None,
                "smd_ponderado_max": None, "ess_sobre_n": None,
                "solapamiento": None}

    solape = medidas["solapamiento"]
    psi_max = medidas["psi_max"]
    smd_w_max = medidas["smd_ponderado_max"]
    psis, smds_w = medidas["psis"], medidas["smds_w"]
    ate_ventana = medidas["ate_ventana"]
    estabilidad_diff = medidas["estabilidad_diff"]
    estabilidad_umbral = None
    estabilidad_ok = True
    if estabilidad_diff is not None:
        se_ref = float(se_champion) if se_champion is not None else 0.0
        estabilidad_umbral = max(
            2.0 * se_ref,
            float(umbrales.get("efecto_estabilidad", 0.20)) * abs(float(ate_champion)))
        estabilidad_ok = estabilidad_diff <= estabilidad_umbral

    motivo = []
    if solape < float(umbrales["solape_min"]):
        accion = "abstenerse"
        motivo.append(f"solapamiento roto: {solape:.0%} de unidades con e en "
                      f"[0.05, 0.95] (mínimo {umbrales['solape_min']:.0%})")
    elif not placebo_ok or not control_negativo_ok:
        accion = "revisar_identificacion"
        motivo.append("placebo o control negativo falla: revisar identificación")
    elif psi_max > float(umbrales["psi_alerta"]):
        accion = "reentrenar"
        culpable = max(psis, key=psis.get)
        motivo.append(f"deriva: PSI de {culpable} = {psi_max:.2f} "
                      f"(umbral {umbrales['psi_alerta']})")
    elif smd_w_max > float(umbrales.get("smd_ponderado_max", 0.25)):
        accion = "alertar"
        culpable = max(smds_w, key=lambda c: abs(smds_w[c]))
        motivo.append(f"balance ponderado: SMD de {culpable} = {smd_w_max:.2f} "
                      f"(umbral {umbrales.get('smd_ponderado_max', 0.25)})")
    elif not estabilidad_ok:
        accion = "alertar"
        motivo.append(f"estabilidad: |ATE ventana - ATE champion| = "
                      f"{estabilidad_diff:.2f} (umbral {estabilidad_umbral:.2f})")
    else:
        accion = "continuar"
        motivo.append("todo dentro de umbral")

    return {
        "estado": ESTADO[accion],
        "accion": accion,
        "estado_puerta": PUERTA[accion],
        "motivo": motivo,
        "n": n,
        "psi_max": round(float(psi_max), 3),
        "smd_max": round(float(medidas["smd_max"]), 2),
        "smd_ponderado_max": round(float(smd_w_max), 2),
        "ess_sobre_n": round(float(medidas["ess_sobre_n"]), 2),
        "solapamiento": round(float(solape), 2),
        "ate_ventana": None if ate_ventana is None else round(ate_ventana, 2),
        "ate_champion": None if ate_champion is None else round(float(ate_champion), 2),
        "estabilidad_diff": (None if estabilidad_diff is None
                             else round(float(estabilidad_diff), 2)),
        "estabilidad_umbral": (None if estabilidad_umbral is None
                               else round(float(estabilidad_umbral), 2)),
        "estabilidad_ok": bool(estabilidad_ok),
        "placebo_ok": bool(placebo_ok),
        "control_negativo_ok": bool(control_negativo_ok),
    }


def evaluar_ventana(train: dict, ventana: dict, esquema: EsquemaCausal,
                    umbrales: dict, *, ate_champion: float | None = None,
                    se_champion: float | None = None,
                    placebo_ok: bool = True,
                    control_negativo_ok: bool = True) -> dict:
    """Mide y clasifica una ventana; conserva la interfaz del prototipo."""
    medidas = medir_ventana(train, ventana, esquema, ate_champion=ate_champion)
    return clasificar_ventana(
        medidas, umbrales, ate_champion=ate_champion, se_champion=se_champion,
        placebo_ok=placebo_ok, control_negativo_ok=control_negativo_ok)


def umbrales_escalados(umbrales: dict, factor: float) -> dict:
    """Escala los cortes que participan en la puerta, sin tocar el diagnóstico SMD.

    ``smd_max`` se conserva porque se informa pero no clasifica. ``solape_min``
    es una fracción y queda acotada a [0, 1].
    """
    if factor <= 0:
        raise ValueError("el factor de los umbrales debe ser positivo")
    escalados = dict(umbrales)
    for clave in ("psi_alerta", "smd_ponderado_max", "efecto_estabilidad"):
        escalados[clave] = float(umbrales[clave]) * factor
    escalados["solape_min"] = min(
        1.0, max(0.0, float(umbrales["solape_min"]) * factor))
    return escalados


def sensibilidad_umbrales(medidas_por_ventana: dict, umbrales: dict, *,
                          ate_champion: float, se_champion: float,
                          placebo_ok: bool, control_negativo_ok: bool,
                          resultados_base: dict) -> dict:
    """Reclasifica medidas ya calculadas con umbrales ±20 %.

    No vuelve a ajustar AIPW. Los factores exploran sensibilidad local a las
    convenciones iniciales de la tarjeta; no las calibran ni validan.
    """
    resultados = {}
    n_cambios = 0
    for nombre, medidas in medidas_por_ventana.items():
        variantes = {}
        for factor in FACTORES_UMBRALES:
            clasificacion = clasificar_ventana(
                medidas, umbrales_escalados(umbrales, factor),
                ate_champion=ate_champion, se_champion=se_champion,
                placebo_ok=placebo_ok, control_negativo_ok=control_negativo_ok)
            if factor == 1.0:
                assert clasificacion == resultados_base[nombre], (
                    f"la clasificación base de {nombre} no es reproducible")
            cambia = clasificacion["accion"] != resultados_base[nombre]["accion"]
            if factor != 1.0:
                n_cambios += int(cambia)
            variantes[str(factor)] = {
                "accion": clasificacion["accion"],
                "estado_puerta": clasificacion["estado_puerta"],
                "cambia_respecto_base": cambia,
                "motivo": clasificacion["motivo"],
            }
        resultados[nombre] = variantes
    return {
        "factores": list(FACTORES_UMBRALES),
        "resultados": resultados,
        "n_cambios": n_cambios,
        "interpretacion": (
            "Los factores 0.8 y 1.2 muestran sensibilidad local a umbrales que "
            "son convenciones iniciales; no constituyen calibración universal "
            "ni una garantía de detección."
        ),
    }


if __name__ == "__main__":
    esquema = EsquemaCausal()
    train = leer("train")
    v = champion()
    tarjeta = json.loads((REGISTRO / v / "tarjeta.json").read_text())
    umbrales = dict(tarjeta["umbrales"])
    umbrales.setdefault("smd_ponderado_max", 0.25)
    umbrales.setdefault("efecto_estabilidad", 0.20)

    estimacion = json.loads((REGISTRO / v / "estimacion.json").read_text())
    placebo = estimacion.get("placebo", {})
    td = placebo.get("tratamiento_permutado", {})
    rd = placebo.get("resultado_permutado", {})
    ate_champion = float(estimacion["ate_aipw"])
    se_champion = float(estimacion["se_aipw"])
    placebo_ok = bool(td.get("placebo_ok", True))
    control_negativo_ok = bool(rd.get("control_negativo_ok", True))

    print(f"ventanas de producción (contra champion = {v}, "
          f"umbrales de la tarjeta: {umbrales})\n")

    resultados = {}
    medidas_por_ventana = {}
    for nombre, fn in VENTANAS.items():
        medidas = medir_ventana(
            train, fn(train, esquema), esquema, ate_champion=ate_champion)
        medidas_por_ventana[nombre] = medidas
        r = clasificar_ventana(
            medidas, umbrales, ate_champion=ate_champion, se_champion=se_champion,
            placebo_ok=placebo_ok, control_negativo_ok=control_negativo_ok)
        resultados[nombre] = r
        print(f"[{nombre:15s}] estado = {r['estado']:6s} | "
              f"acción: {r['accion']}")
        if r.get("n") is not None:
            print(f"                  n={r['n']} | PSI máx = {r['psi_max']} | "
                  f"SMD máx = {r['smd_max']} | SMD pond. = {r['smd_ponderado_max']} | "
                  f"ESS/n = {r['ess_sobre_n']} | solape = {r['solapamiento']:.0%}")
            if r.get("ate_ventana") is not None:
                print(f"                  ATE ventana = {r['ate_ventana']} | "
                      f"ATE champion = {r['ate_champion']} | "
                      f"diff = {r['estabilidad_diff']} "
                      f"(umbral {r['estabilidad_umbral']})")
        for m in r["motivo"]:
            print(f"                  - {m}")
        print()

    sensibilidad = sensibilidad_umbrales(
        medidas_por_ventana, umbrales, ate_champion=ate_champion,
        se_champion=se_champion, placebo_ok=placebo_ok,
        control_negativo_ok=control_negativo_ok, resultados_base=resultados)
    print(f"sensibilidad de umbrales ±20 %: {sensibilidad['n_cambios']} "
          "cambios de acción fuera de la clasificación base")
    print("son convenciones iniciales, no umbrales calibrados universalmente\n")

    produccion = os.environ.get("SIC_VENTANA", "sana")
    if produccion not in resultados:
        produccion = "sana"
    r_prod = resultados[produccion]
    peor = max(resultados.values(), key=lambda r: ORDEN[r["accion"]])
    estado = {
        "version": v,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ventana_produccion": produccion,
        "estado": r_prod["estado"],
        "accion": r_prod["accion"],
        "estado_puerta": r_prod["estado_puerta"],
        "peor_accion": peor["accion"],
        "peor_estado_puerta": peor["estado_puerta"],
        "ventanas": resultados,
        "sensibilidad_umbrales": sensibilidad,
    }
    ARTEFACTOS.mkdir(exist_ok=True)
    (ARTEFACTOS / "monitor_estado.json").write_text(
        json.dumps(estado, indent=2, ensure_ascii=False) + "\n")
    print(f"puerta de producción ({produccion}): {r_prod['estado_puerta']} "
          f"({r_prod['accion']})")
    print(f"peor acción entre ventanas de estrés: {peor['accion']} "
          f"({peor['estado_puerta']})")
    print("artefacto: artifacts/monitor_estado.json")
