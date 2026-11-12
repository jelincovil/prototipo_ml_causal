"""pruebas_estimacion.py — asserts de las fórmulas y de los invariantes.

No usa dependencias nuevas. Se ejecuta con `make pruebas` sobre `synthetic/ihdp`.
"""
from __future__ import annotations

import hashlib
import json

from pathlib import Path

import numpy as np

import cobertura
import monitor
from datos import EsquemaCausal, leer
from estimacion import (aipw_crossfit, ate_ols, diagnosticos_positividad,
                        smd_ponderado)
from rutas import ARTEFACTOS, DATOS
from sensibilidad import (control_negativo, cotas_manski, e_value_continuo,
                          placebo_permutacion, valor_robustez)


def _comprobar_salida_monitor(resultado: dict, n: int) -> None:
    """Contrato común de evaluación y reclasificación con tratamiento variable."""
    claves = {
        "estado", "accion", "estado_puerta", "motivo", "n", "psi_max",
        "smd_max", "smd_ponderado_max", "ess_sobre_n", "solapamiento",
        "ate_ventana", "ate_champion", "estabilidad_diff",
        "estabilidad_umbral", "estabilidad_ok", "placebo_ok",
        "control_negativo_ok",
    }
    assert claves <= set(resultado)
    assert resultado["n"] == n
    assert resultado["accion"] in monitor.ORDEN
    assert resultado["estado"] == monitor.ESTADO[resultado["accion"]]
    assert resultado["estado_puerta"] == monitor.PUERTA[resultado["accion"]]
    assert isinstance(resultado["motivo"], list) and resultado["motivo"]
    assert all(isinstance(m, str) for m in resultado["motivo"])
    for clave in ("psi_max", "smd_max", "smd_ponderado_max",
                  "ess_sobre_n", "solapamiento"):
        assert np.isfinite(resultado[clave]), (clave, resultado[clave])
    assert 0.0 <= resultado["ess_sobre_n"] <= 1.0
    assert 0.0 <= resultado["solapamiento"] <= 1.0
    assert isinstance(resultado["estabilidad_ok"], bool)
    assert isinstance(resultado["placebo_ok"], bool)
    assert isinstance(resultado["control_negativo_ok"], bool)


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

    # 3. Manski: ejemplo con solución cerrada; ancho = U - L.
    m = cotas_manski(np.array([1.0, 3.0, 0.0, 2.0]),
                     np.array([1.0, 1.0, 0.0, 0.0]), soporte=(0.0, 3.0))
    np.testing.assert_allclose(m["e_y1"], [1.0, 2.5])
    np.testing.assert_allclose(m["e_y0"], [0.5, 2.0])
    np.testing.assert_allclose(m["ate"], [-1.0, 2.0])
    assert m["ancho"] == 3.0 and m["identificacion_puntual"] is False

    # 4. SMD ponderado finito y con signo.
    g = np.random.default_rng(7)
    v = g.normal(size=80)
    D = (g.random(80) < 0.5).astype(float)
    e = np.full(80, 0.5)
    assert np.isfinite(smd_ponderado(v, D, e))

    # 5. OLS devuelve t/df/n/k para el valor de robustez.
    esquema = EsquemaCausal()
    col = leer("train")
    ols = ate_ols(col, esquema)
    assert {"t", "df", "n", "k"} <= set(ols)
    assert ols["df"] > 0

    # 6. Placebo de tratamiento: n_rep exacto y p en [0, 1].
    p = placebo_permutacion(col, esquema, aipw_crossfit, n_rep=5, semilla=11)
    assert p["n_rep"] == 5
    assert 0.0 <= p["p_valor_aprox"] <= 1.0
    assert p["placebo_ic95"][0] <= p["placebo_ic95"][1]

    # 7. Placebo de resultado: devuelve efecto e IC.
    q = control_negativo(col, esquema, aipw_crossfit, variable="momage",
                         semilla=11)
    assert len(q["ic95"]) == 2
    assert q["ic95"][0] <= q["ic95"][1]

    # 8. Diagnósticos de positividad: estructura y coherencia interna.
    D_pos = np.array([0.0, 1.0] * 5)
    e_pos = np.array([0.01, 0.04, 0.05, 0.20, 0.50,
                      0.80, 0.95, 0.96, 0.99, 0.60])
    pos = diagnosticos_positividad(e_pos, D_pos)
    assert {"fuente", "recorte", "rango", "fraccion_solapamiento",
            "total", "tratados", "controles", "ess", "ess_sobre_n",
            "advertencia"} <= set(pos)
    assert pos["recorte"] == [0.05, 0.95]
    np.testing.assert_allclose(pos["rango"], [0.01, 0.99])
    assert pos["fraccion_solapamiento"] == 0.6
    assert pos["total"]["recortado_n"] == 4
    assert pos["total"]["recortado_pct"] == 40.0
    resumenes = (("total", np.ones(len(D_pos), dtype=bool)),
                 ("tratados", D_pos == 1), ("controles", D_pos == 0))
    claves_resumen = {"n", "min", "p05", "p25", "mediana", "p75", "p95",
                      "max", "recortado_n", "recortado_pct"}
    for nombre, seleccion in resumenes:
        resumen = pos[nombre]
        valores = e_pos[seleccion]
        assert claves_resumen <= set(resumen)
        assert resumen["n"] == len(valores)
        esperado_recorte = int(np.sum((valores < 0.05) | (valores > 0.95)))
        assert resumen["recortado_n"] == esperado_recorte
        assert resumen["recortado_pct"] == 100.0 * esperado_recorte / len(valores)
        assert all(np.isfinite(resumen[k]) for k in claves_resumen - {"n"})
        assert resumen["min"] <= resumen["p05"] <= resumen["p25"]
        assert resumen["p25"] <= resumen["mediana"] <= resumen["p75"]
        assert resumen["p75"] <= resumen["p95"] <= resumen["max"]
        assert resumen["min"] == float(valores.min())
        assert resumen["max"] == float(valores.max())
    assert (pos["total"]["recortado_n"]
            == pos["tratados"]["recortado_n"] + pos["controles"]["recortado_n"])
    recortadas = np.clip(e_pos, 0.05, 0.95)
    pesos = np.where(D_pos == 1, 1.0 / recortadas, 1.0 / (1.0 - recortadas))
    ess_esperado = float(pesos.sum() ** 2 / np.sum(pesos ** 2))
    np.testing.assert_allclose(pos["ess"], ess_esperado)
    np.testing.assert_allclose(pos["total"]["ess"], ess_esperado)
    np.testing.assert_allclose(pos["ess_sobre_n"], ess_esperado / len(D_pos))
    assert 0.0 < pos["ess"] <= len(D_pos)
    assert pos["ess_sobre_n"] == pos["total"]["ess_sobre_n"]

    # 9. Cobertura: mínimo coste razonable, rangos y reproducción exacta.
    cob1 = cobertura.ejecutar(n=60, repeticiones=2, semilla=20261111)
    cob2 = cobertura.ejecutar(n=60, repeticiones=2, semilla=20261111)
    assert cob1 == cob2
    serial1 = json.dumps(cob1, sort_keys=True, allow_nan=False)
    serial2 = json.dumps(cob2, sort_keys=True, allow_nan=False)
    assert serial1 == serial2
    meta = cob1["metadatos"]
    assert (meta["n"], meta["repeticiones"], meta["semilla"]) == (60, 2, 20261111)
    assert meta["K"] == 5 and meta["nominal"] == cobertura.NOMINAL
    assert meta["verdad"]["valor"] == cobertura.ATE_VERDADERO
    nombres_estimadores = {"aipw", "ols_ajustado", "ingenuo"}
    assert set(cob1["estimadores"]) == nombres_estimadores
    comparacion_cob = cob1["resumen"]["comparacion_cobertura"]
    assert set(comparacion_cob) == nombres_estimadores
    assert cob1["resumen"]["nominal"] == cobertura.NOMINAL
    for nombre in nombres_estimadores:
        metricas = cob1["estimadores"][nombre]
        assert {"n_repeticiones", "cobertura_ic95", "error_monte_carlo",
                "sesgo", "rmse", "longitud_media_ic"} <= set(metricas)
        assert metricas["n_repeticiones"] == 2
        for clave in ("cobertura_ic95", "error_monte_carlo", "sesgo",
                      "rmse", "longitud_media_ic"):
            assert np.isfinite(metricas[clave]), (nombre, clave)
        assert 0.0 <= metricas["cobertura_ic95"] <= 1.0
        assert 0.0 <= metricas["error_monte_carlo"] <= 0.5
        assert metricas["rmse"] >= 0.0
        assert metricas["longitud_media_ic"] > 0.0
        comparacion = comparacion_cob[nombre]
        np.testing.assert_allclose(
            comparacion["diferencia_vs_nominal"],
            metricas["cobertura_ic95"] - cobertura.NOMINAL)
        assert comparacion["error_monte_carlo"] == metricas["error_monte_carlo"]
        assert comparacion["dentro_de_mas_menos_1_error_mc"] == (
            abs(metricas["cobertura_ic95"] - cobertura.NOMINAL)
            <= metricas["error_monte_carlo"])

    # 10. Medir una vez y reclasificar: equivalencia y sensibilidad de umbrales.
    esquema_mon = EsquemaCausal(
        tratamiento="treatment", resultado="y", covariables=("x",))
    g_mon = np.random.default_rng(19)
    n_mon = 24
    x_mon = g_mon.normal(size=n_mon)
    D_mon = np.tile([0.0, 1.0], n_mon // 2)
    train_mon = {"x": x_mon, "treatment": D_mon,
                 "y": 0.4 * x_mon + D_mon + g_mon.normal(size=n_mon)}
    ventana_mon = {nombre: valores.copy() for nombre, valores in train_mon.items()}
    umbrales_mon = {"solape_min": 0.75, "psi_alerta": 0.25,
                    "smd_ponderado_max": 0.25, "efecto_estabilidad": 0.20}
    medidas = monitor.medir_ventana(train_mon, ventana_mon, esquema_mon)
    assert medidas["n"] == n_mon and medidas["tratamiento_varia"] is True
    clasificada = monitor.clasificar_ventana(medidas, umbrales_mon)
    evaluada = monitor.evaluar_ventana(
        train_mon, ventana_mon, esquema_mon, umbrales_mon)
    assert clasificada == evaluada
    _comprobar_salida_monitor(clasificada, n_mon)

    medidas_artificiales = {
        "n": 30, "tratamiento_varia": True, "solapamiento": 0.95,
        "ess_sobre_n": 0.90, "psis": {"x": 0.24}, "psi_max": 0.24,
        "smd_max": 0.10, "smds_w": {"x": 0.20},
        "smd_ponderado_max": 0.20, "ate_ventana": 1.19,
        "estabilidad_diff": 0.19,
    }
    reclasificadas = {}
    for factor in monitor.FACTORES_UMBRALES:
        escalados = monitor.umbrales_escalados(umbrales_mon, factor)
        con_smd = monitor.umbrales_escalados(
            dict(umbrales_mon, smd_max=0.5), factor)
        assert con_smd["smd_max"] == 0.5
        assert escalados["solape_min"] == min(
            1.0, max(0.0, umbrales_mon["solape_min"] * factor))
        reclasificadas[factor] = monitor.clasificar_ventana(
            medidas_artificiales, escalados, ate_champion=1.0, se_champion=0.0)
        _comprobar_salida_monitor(reclasificadas[factor], n=30)
    for factor, resultado in reclasificadas.items():
        for clave in ("n", "psi_max", "smd_max", "smd_ponderado_max",
                      "ess_sobre_n", "solapamiento", "ate_ventana",
                      "estabilidad_diff"):
            assert resultado[clave] == reclasificadas[1.0][clave]
    assert reclasificadas[0.8]["accion"] == "reentrenar"
    assert reclasificadas[1.0]["accion"] == "continuar"
    assert reclasificadas[1.2]["accion"] == "continuar"
    assert monitor.umbrales_escalados(
        dict(umbrales_mon, solape_min=0.95), 1.2)["solape_min"] == 1.0

    # 11. El artefacto incluye el hash correcto del dataset.
    ruta = ARTEFACTOS / "estimacion.json"
    if ruta.exists():
        est = json.loads(ruta.read_text())
        comparacion_est = est.get("comparacion_estimadores")
        assert isinstance(comparacion_est, dict), (
            "Esquema antiguo en artifacts/estimacion.json: falta "
            "comparacion_estimadores; regenerar el artefacto sin relajar la prueba")
        assert isinstance(comparacion_est.get("lectura"), str)
        assert comparacion_est["lectura"]
        campos_legados = {
            "ingenuo": ("diferencia_cruda", "se_diferencia_cruda",
                        "ic_diferencia_cruda"),
            "ols_ajustado": ("ate_ols", "se", "ic95"),
            "aipw": ("ate_aipw", "se_aipw", "ic_aipw"),
        }
        assert set(campos_legados) <= set(comparacion_est)
        for nombre, legados in campos_legados.items():
            fila = comparacion_est[nombre]
            assert isinstance(fila, dict) and {"ate", "se", "ic95"} <= set(fila)
            assert len(fila["ic95"]) == 2
            numericos = np.asarray(
                [fila["ate"], fila["se"], *fila["ic95"]], dtype=float)
            assert np.all(np.isfinite(numericos)), nombre
            assert fila["se"] > 0.0
            assert fila["ic95"][0] <= fila["ate"] <= fila["ic95"][1]
            np.testing.assert_allclose(
                fila["ic95"],
                [fila["ate"] - 1.96 * fila["se"],
                 fila["ate"] + 1.96 * fila["se"]], rtol=1e-12, atol=1e-12)
            np.testing.assert_allclose(
                numericos,
                [est[legados[0]], est[legados[1]], *est[legados[2]]],
                rtol=1e-12, atol=1e-12)
        hash_real = hashlib.sha256(
            (DATOS / "observed_train.csv").read_bytes()).hexdigest()
        assert est.get("dataset_sha256") == hash_real
        ident = est.get("identificacion") or {}
        assert ident.get("aplicable") is True, ident.get("motivo")
        assert ident.get("criterio_principal") == "backdoor"
        assert ident.get("criterio_backdoor_pasa") is True
        assert ident.get("identificacion_pasa") is True
        assert ident.get("metodos_dowhy", {}).get("conjunto_backdoor") == "default"
        assert ident.get("metodos_dowhy", {}).get("expresion_estimando") == "id-algorithm"
        assert ident.get("efecto_identificable_por_grafo") is True
        bench = json.loads((DATOS / "identification.json").read_text())
        bench_set = [str(x) for x in (bench.get("valid_adjustment_sets") or [[]])[0]]
        got = ident.get("conjunto_ajuste_estimado") or []
        assert sorted(got) == sorted(bench_set)
        assert ident.get("coincide_valid_adjustment_sets") is True

        manski = est.get("sensibilidad", {}).get("cotas_manski") or {}
        assert len(manski.get("ate", [])) == 2
        assert manski["ate"][0] <= manski["ate"][1]
        assert manski.get("identificacion_puntual") is False
        placebo = est.get("placebo", {})
        assert placebo.get("pasa") is True
        assert placebo.get("tratamiento_permutado_pasa") is True
        assert placebo.get("resultado_permutado_pasa") is True

    # 12. La pared: ni el estimador ni la sensibilidad leen interventions.json.
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
