"""Estima el LATE con DoubleMLIIVM usando únicamente variables observadas."""
from __future__ import annotations

import numpy as np
import pandas as pd
from doubleml import DoubleMLData, DoubleMLIIVM
from sklearn.linear_model import LinearRegression, LogisticRegression

from datos_iv import EsquemaIV, leer
from rutas_iv import SEMILLA


def diagnosticos_observados(observados, esquema: EsquemaIV) -> dict:
    """Contrastes descriptivos; ninguno prueba la validez del instrumento."""
    z = np.asarray(observados[esquema.instrumento], dtype=float)
    d = np.asarray(observados[esquema.tratamiento], dtype=float)
    y = np.asarray(observados[esquema.resultado], dtype=float)

    p1, p0 = d[z == 1].mean(), d[z == 0].mean()
    n1, n0 = int((z == 1).sum()), int((z == 0).sum())
    diferencia = p1 - p0
    se_primera = np.sqrt(p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)
    f_descriptivo = (diferencia / se_primera) ** 2 if se_primera > 0 else 0.0
    ingenuo = y[d == 1].mean() - y[d == 0].mean()
    return {
        "diferencia_ingenua": float(ingenuo),
        "primera_etapa": {
            "prob_d_si_z1": float(p1),
            "prob_d_si_z0": float(p0),
            "diferencia": float(diferencia),
            "error_estandar": float(se_primera),
            "f_descriptivo_sin_covariables": float(f_descriptivo),
            "nota": "F aproximado: no resume todas las primeras etapas condicionales de DML",
        },
    }


def estimar(observados, semilla: int = SEMILLA, esquema: EsquemaIV | None = None) -> dict:
    """Ajusta DML-IV; no recibe ni consulta la verdad causal del escenario."""
    esquema = esquema or EsquemaIV()
    datos = pd.DataFrame(observados).copy()
    esquema.validar(
        list(datos.columns),
        {nombre: datos[nombre].to_numpy() for nombre in esquema.columnas()},
    )
    diagnosticos = diagnosticos_observados(datos, esquema)

    # La semilla precede también a la construcción: define el sorteo de pliegues.
    np.random.seed(semilla)
    datos_dml = DoubleMLData(
        datos[esquema.columnas()],
        y_col=esquema.resultado,
        d_cols=esquema.tratamiento,
        z_cols=esquema.instrumento,
        x_cols=list(esquema.covariables),
    )
    modelo = DoubleMLIIVM(
        datos_dml,
        ml_g=LinearRegression(),
        ml_m=LogisticRegression(max_iter=1000),
        ml_r=LogisticRegression(max_iter=1000),
        n_folds=3,
        score="LATE",
    )
    modelo.fit()
    intervalo = modelo.confint(level=0.95).iloc[0]

    return {
        "metodo": "DoubleMLIIVM",
        "estimando": "LATE entre compliers; no ATE poblacional",
        "coeficiente": float(modelo.coef[0]),
        "error_estandar": float(modelo.se[0]),
        "ic95": [float(intervalo.iloc[0]), float(intervalo.iloc[1])],
        "n_observaciones": int(len(datos)),
        "n_pliegues": 3,
        "semilla": semilla,
        **diagnosticos,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(estimar(leer("train")), ensure_ascii=False, indent=2))
