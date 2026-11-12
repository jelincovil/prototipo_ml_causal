"""Simulación Monte Carlo de cobertura de IC95 en un DGP ilustrativo propio.

El ejercicio compara AIPW con cross-fitting, OLS ajustado y la diferencia
ingenua de medias cuando las seis covariables observadas confunden D e Y.
NO reproduce el DGP de Hill/IHDP, no lee ``interventions.json`` ni ningún dato
del benchmark. En particular, la cobertura estimada solo describe este DGP:
no demuestra identificación ni calibración para los escenarios IHDP o jobs.

DGP, con X_1,...,X_6 iid N(0,1) y epsilon iid N(0,1):

    D | X ~ Bernoulli(expit(-0.20 + 0.70 X1 - 0.50 X2 + 0.40 X3
                            + 0.30 X4 - 0.20 X5 + 0.15 X6))
    Y = 1 + 0.90 X1 - 0.70 X2 + 0.50 X3 + 0.40 X4 - 0.30 X5
        + 0.20 X6 + 2.0 D + epsilon.

El efecto individual es constante, por lo que el ATE poblacional verdadero es
exactamente 2.0 por construcción. Las probabilidades de tratamiento suelen ser
moderadas, pero una muestra degenerada o un fallo numérico detiene el estudio
con su repetición identificada; nunca se descartan repeticiones selectivamente.

``ejecutar`` no escribe archivos. La escritura de ``artifacts/cobertura.json``
solo ocurre mediante el CLI, que también permite elegir otra ruta con
``--salida``. Se omiten marcas de tiempo para que el diccionario y el JSON sean
reproducibles exactamente con la misma semilla y versiones del software.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from datos import EsquemaCausal
from estimacion import aipw_crossfit, ate_ols

K = 5
NOMINAL = 0.95
Z_95 = 1.96
ATE_VERDADERO = 2.0
COVARIABLES = tuple(f"x{i}" for i in range(1, 7))

ADVERTENCIA = (
    "La cobertura solo aplica a este DGP ilustrativo propio. No demuestra "
    "identificación, ausencia de confusión, positividad ni calibración de IC "
    "en los escenarios IHDP/jobs ni en datos reales."
)


def _simular(n: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Genera una muestra del DGP declarado en el docstring del módulo."""
    X = rng.normal(size=(n, len(COVARIABLES)))
    eta = (
        -0.20 + 0.70 * X[:, 0] - 0.50 * X[:, 1] + 0.40 * X[:, 2]
        + 0.30 * X[:, 3] - 0.20 * X[:, 4] + 0.15 * X[:, 5]
    )
    probabilidad = 1.0 / (1.0 + np.exp(-eta))
    D = rng.binomial(1, probabilidad).astype(int)
    epsilon = rng.normal(size=n)
    y = (
        1.0 + 0.90 * X[:, 0] - 0.70 * X[:, 1] + 0.50 * X[:, 2]
        + 0.40 * X[:, 3] - 0.30 * X[:, 4] + 0.20 * X[:, 5]
        + ATE_VERDADERO * D + epsilon
    )
    col = {nombre: X[:, i] for i, nombre in enumerate(COVARIABLES)}
    col.update({"treatment": D, "y": y})
    return col


def _ingenuo(col: dict[str, np.ndarray]) -> dict[str, Any]:
    """Diferencia de medias con SE de Welch e IC95 normal ate +/- 1.96*SE."""
    D, y = col["treatment"], col["y"]
    y1, y0 = y[D == 1], y[D == 0]
    if len(y1) < 2 or len(y0) < 2:
        raise ValueError(
            "la diferencia ingenua exige al menos dos tratados y dos controles; "
            f"se obtuvieron n1={len(y1)} y n0={len(y0)}"
        )
    ate = float(y1.mean() - y0.mean())
    se = float(math.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0)))
    return {"ate": ate, "se": se, "ic": [ate - Z_95 * se, ate + Z_95 * se]}


def _validar_estimacion(nombre: str, resultado: dict[str, Any]) -> dict[str, Any]:
    """Convierte a escalares/listas de Python y rechaza resultados degenerados."""
    try:
        ate = float(resultado["ate"])
        se = float(resultado["se"])
        if len(resultado["ic"]) != 2:
            raise ValueError("el IC no tiene exactamente dos extremos")
        ic = [float(resultado["ic"][0]), float(resultado["ic"][1])]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{nombre}: resultado incompleto o inválido") from exc
    if not all(math.isfinite(v) for v in (ate, se, *ic)):
        raise ValueError(f"{nombre}: ATE, SE o IC no finito")
    if se <= 0.0:
        raise ValueError(f"{nombre}: SE no positivo ({se})")
    if ic[0] > ic[1]:
        raise ValueError(f"{nombre}: extremos del IC invertidos")
    return {"ate": ate, "se": se, "ic": ic}


def _resumir_estimador(repeticiones: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula métricas frente al ATE verdadero usando solo tipos serializables."""
    R = len(repeticiones)
    ates = [r["ate"] for r in repeticiones]
    coberturas = [r["ic"][0] <= ATE_VERDADERO <= r["ic"][1] for r in repeticiones]
    longitudes = [r["ic"][1] - r["ic"][0] for r in repeticiones]
    cobertura = math.fsum(coberturas) / R
    return {
        "n_repeticiones": R,
        "cobertura_ic95": float(cobertura),
        "error_monte_carlo": float(math.sqrt(cobertura * (1.0 - cobertura) / R)),
        "sesgo": float(math.fsum(ate - ATE_VERDADERO for ate in ates) / R),
        "rmse": float(math.sqrt(math.fsum((ate - ATE_VERDADERO) ** 2 for ate in ates) / R)),
        "longitud_media_ic": float(math.fsum(longitudes) / R),
    }


def _metadatos(n: int, repeticiones: int, semilla: int) -> dict[str, Any]:
    """Describe la verdad y todas las decisiones necesarias para reproducirla."""
    return {
        "dgp": {
            "nombre": "ilustrativo_propio_logistico_lineal_6x",
            "covariables": "X1,...,X6 iid N(0,1), independientes entre sí",
            "tratamiento": (
                "D|X ~ Bernoulli(expit(-0.20 + 0.70*x1 - 0.50*x2 + 0.40*x3 "
                "+ 0.30*x4 - 0.20*x5 + 0.15*x6))"
            ),
            "resultado": (
                "Y = 1 + 0.90*x1 - 0.70*x2 + 0.50*x3 + 0.40*x4 - 0.30*x5 "
                "+ 0.20*x6 + 2.0*D + epsilon; epsilon iid N(0,1)"
            ),
            "confusion": (
                "Las seis X afectan conjuntamente a D e Y y están observadas; "
                "no hay confusión no observada por construcción."
            ),
            "asignacion_moderada": (
                "Coeficientes logísticos moderados para favorecer solapamiento; "
                "las muestras degeneradas producen un error explícito, no se omiten."
            ),
            "origen": "DGP ilustrativo propio; no es Hill/IHDP ni usa datos del benchmark",
        },
        "verdad": {
            "parametro": "ATE poblacional E[Y(1)-Y(0)]",
            "valor": ATE_VERDADERO,
            "naturaleza": (
                "Conocida exactamente por construcción: Y(1)-Y(0)=2.0 para cada "
                "unidad; no se estima a partir de un benchmark."
            ),
            "formula": "ATE = E[2.0] = 2.0",
        },
        "semilla": semilla,
        "n": n,
        "repeticiones": repeticiones,
        "K": K,
        "nominal": NOMINAL,
        "z_ic95": Z_95,
        "semillas_independientes": (
            "Flujos NumPy derivados de SeedSequence([semilla, 0]) para datos y "
            "SeedSequence([semilla, 1]) para los pliegues de AIPW."
        ),
        "ingenuo_se_ic": (
            "SE de Welch sqrt(s1^2/n1 + s0^2/n0); IC95 = ATE +/- 1.96*SE"
        ),
        "ols_se_ic": "SE e IC devueltos por ate_ols: IC95 = ATE +/- 1.96*SE",
        "aipw_se_ic": (
            "SE e IC devueltos por aipw_crossfit con K=5 y su trimming declarado; "
            "IC95 = ATE +/- 1.96*SE"
        ),
    }


def ejecutar(n: int = 500, repeticiones: int = 100, semilla: int = 20261111) -> dict:
    """Ejecuta la simulación y devuelve un diccionario JSON-serializable.

    No lee ni escribe archivos. Todas las repeticiones deben completarse: los
    errores se relanzan con contexto en vez de excluir simulaciones incómodas.
    ``repeticiones`` puede ser pequeño para pruebas, aunque entonces el error
    Monte Carlo será grande. Se recomienda un ``n`` moderado; valores muy
    pequeños pueden impedir el ajuste de los modelos por pliegue.
    """
    if n < 10:
        raise ValueError("n debe ser al menos 10 para K=5 y un OLS con gl positivos")
    if repeticiones < 1:
        raise ValueError("repeticiones debe ser un entero positivo")
    if semilla < 0:
        raise ValueError("semilla debe ser un entero no negativo")

    esquema = EsquemaCausal(
        tratamiento="treatment",
        resultado="y",
        covariables=COVARIABLES,
    )
    rng_datos = np.random.default_rng(np.random.SeedSequence([semilla, 0]))
    rng_pliegues = np.random.default_rng(np.random.SeedSequence([semilla, 1]))
    resultados = {"aipw": [], "ols_ajustado": [], "ingenuo": []}

    for repeticion in range(repeticiones):
        try:
            col = _simular(n, rng_datos)
            esquema.validar(list(col), col["treatment"])
            semilla_folds = int(rng_pliegues.integers(0, 2**31 - 1))
            estimaciones = {
                "aipw": _validar_estimacion(
                    "aipw", aipw_crossfit(
                        col, esquema, k=K, semilla_folds=semilla_folds
                    )
                ),
                "ols_ajustado": _validar_estimacion(
                    "ols_ajustado", ate_ols(col, esquema)
                ),
                "ingenuo": _validar_estimacion("ingenuo", _ingenuo(col)),
            }
        except Exception as exc:
            raise RuntimeError(
                f"Fallo en la repetición {repeticion} (base cero); no se omitió "
                "ninguna simulación. Revise la excepción encadenada."
            ) from exc
        for nombre, estimacion in estimaciones.items():
            resultados[nombre].append(estimacion)

    metricas = {nombre: _resumir_estimador(filas) for nombre, filas in resultados.items()}
    comparacion = {
        nombre: {
            "cobertura_ic95": filas["cobertura_ic95"],
            "diferencia_vs_nominal": float(filas["cobertura_ic95"] - NOMINAL),
            "error_monte_carlo": filas["error_monte_carlo"],
            "dentro_de_mas_menos_1_error_mc": bool(
                abs(filas["cobertura_ic95"] - NOMINAL) <= filas["error_monte_carlo"]
            ),
        }
        for nombre, filas in metricas.items()
    }
    return {
        "metadatos": _metadatos(n, repeticiones, semilla),
        "estimadores": metricas,
        "resumen": {
            "nominal": NOMINAL,
            "comparacion_cobertura": comparacion,
            "interpretacion": (
                "La diferencia cobertura-nominal debe leerse junto con el error "
                "Monte Carlo sqrt(p(1-p)/R); una coincidencia aproximada con 0.95 "
                "en esta simulación no es una garantía general de cobertura."
            ),
            "advertencia": ADVERTENCIA,
        },
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: ejecuta la simulación y es el único punto que escribe el artefacto."""
    parser = argparse.ArgumentParser(
        description=(
            "Cobertura Monte Carlo de IC95 en el DGP ilustrativo propio; "
            "no evalúa identificación en IHDP/jobs."
        )
    )
    parser.add_argument("--n", type=int, default=500, help="unidades por repetición")
    parser.add_argument(
        "--repeticiones", type=int, default=100,
        help="número de repeticiones Monte Carlo (puede ser pequeño para probar)",
    )
    parser.add_argument("--semilla", type=int, default=20261111, help="semilla reproducible")
    parser.add_argument(
        "--salida", type=Path, default=Path("artifacts/cobertura.json"),
        help="ruta del JSON (por defecto: artifacts/cobertura.json)",
    )
    args = parser.parse_args(argv)

    resultado = ejecutar(n=args.n, repeticiones=args.repeticiones, semilla=args.semilla)
    contenido = json.dumps(resultado, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(contenido, encoding="utf-8")
    print(json.dumps(resultado["resumen"], ensure_ascii=False, indent=2, allow_nan=False))
    print(f"Resultados guardados en: {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
