"""humo.py — Prueba de humo del servicio (TestClient, sin levantar puerto).

Cubre los invariantes del servicio del prototipo:
  1. /efecto devuelve efecto + IC + versión (el bundle viaja).
  2. /heterogeneidad devuelve una proyección, nunca un CATE individual identificado.
  3. Fuera del soporte o con puerta fallida se abstiene SIN estimación numérica.
  4. Dos llamadas idénticas devuelven exactamente lo mismo.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

import servicio_core as nucleo
from servicio import app
from rutas import ESCENARIO

c = TestClient(app)

# Perfil dentro del soporte de synthetic/jobs (el del kit). Para otros escenarios
# se construye desde los rangos del bundle: el humo no lee CSV.
PERFIL_JOBS = {"age": 30, "educ": 10, "black": 1, "hispan": 0,
               "married": 0, "nodegree": 1, "re74": 2000, "re75": 1500}
PERFIL_JOBS_FUERA = dict(PERFIL_JOBS, age=99)


def _perfil_desde_bundle(fuera: bool) -> dict:
    b = nucleo._cargar()
    est = b["estimacion"]
    rangos = est["rangos_covariables"]
    corte, umbral = est["estratos"]["variable"], est["estratos"]["umbral"]
    perfil = {c: (lo + hi) / 2 for c, (lo, hi) in rangos.items()}
    perfil[corte] = umbral + (rangos[corte][1] - umbral) / 2
    if fuera:
        primera = next(iter(rangos))
        perfil[primera] = rangos[primera][1] + 1.0
    return perfil


def perfiles() -> tuple[dict, dict]:
    if ESCENARIO == "synthetic/jobs":
        return PERFIL_JOBS, PERFIL_JOBS_FUERA
    return _perfil_desde_bundle(False), _perfil_desde_bundle(True)


def _diagnosticos_ok(j: dict) -> bool:
    pos = j.get("diagnosticos_positividad")
    comp = j.get("comparacion_estimadores")
    return (isinstance(pos, dict)
            and all(k in pos for k in
                    ("tratados", "controles", "recorte", "ess", "ess_sobre_n"))
            and all(isinstance(pos.get(k), dict) for k in ("tratados", "controles"))
            and isinstance(comp, dict)
            and all(k in comp for k in ("ingenuo", "ols_ajustado", "aipw")))


def _heterogeneidad_ok(j: dict) -> bool:
    texto = str(j).lower()
    texto_sin_negacion = texto.replace("no es un cate individual identificado", "")
    estimando = j.get("estimando", "").lower()
    return (j.get("estado") == "respuesta"
            and j.get("tipo") == "heterogeneidad_estimada"
            and "proyeccion" in j and "efecto" not in j
            and len(j.get("ic95", [])) == 2
            and "heterogeneidad" in estimando and "proyección" in estimando
            and "no es un cate individual identificado" in texto
            and "cate individual identificado" not in texto_sin_negacion
            and "efecto individual identificado" not in texto_sin_negacion
            and "efecto causal individual identificado" not in texto_sin_negacion
            and bool(j.get("advertencias")))


def _abstencion_heterogeneidad_ok(j: dict) -> bool:
    return (j.get("estado") == "abstencion"
            and j.get("tipo") == "heterogeneidad_estimada"
            and "proyeccion" not in j and "efecto" not in j
            and bool(j.get("advertencias")))


def _probar_puerta_falla() -> bool:
    """Fuerza la puerta a 'falla' y exige abstención para ATE y heterogeneidad."""
    b = nucleo._cargar()
    original_manifest = b.get("manifest", {}).get("puerta")
    original_monitor = b.get("monitor")
    b["manifest"]["puerta"] = "falla"
    b["monitor"] = None
    try:
        ate = nucleo.efecto()
        hetero = nucleo.heterogeneidad({})
        return (ate.get("estado") == "abstencion" and "efecto" not in ate
                and _abstencion_heterogeneidad_ok(hetero))
    finally:
        b["manifest"]["puerta"] = original_manifest
        b["monitor"] = original_monitor


def _probar_integridad_falla() -> bool:
    """Simula un bundle no verificado y exige abstención sin número."""
    b = nucleo._cargar()
    original = b.get("integridad_valida")
    b["integridad_valida"] = False
    try:
        j = nucleo.efecto()
        return (j.get("estado") == "abstencion" and "efecto" not in j
                and j.get("integridad_valida") is False)
    finally:
        b["integridad_valida"] = original


def _probar_archivos_defectuosos() -> bool:
    """Un bundle incompleto o corrupto cierra todas las salidas sin excepciones.

    Las copias viven en directorios temporales: nunca se mutan los artefactos reales.
    """
    bundle_real = nucleo._cargar()
    artefactos_real = nucleo.ARTEFACTOS
    registro_real = nucleo.REGISTRO
    champion_real = nucleo.champion
    verificar_real = nucleo.verificar_alias
    cache_real = dict(nucleo._cache)
    version = bundle_real["version"]
    origen = registro_real / version

    def champion_temporal() -> str:
        alias = nucleo.ARTEFACTOS / "alias_champion.json"
        return json.loads(alias.read_text())["version"]

    resultados = []
    try:
        for caso in ("alias_ausente", "json_corrupto",
                     "manifiesto_ausente", "monitor_corrupto"):
            try:
                with tempfile.TemporaryDirectory(prefix=f"sic_humo_{caso}_") as tmp:
                    base = Path(tmp)
                    artefactos = base / "artifacts"
                    registro = artefactos / "registro"
                    destino = registro / version
                    destino.mkdir(parents=True)
                    for nombre in ("estimacion.json", "tarjeta.json", "manifest.json"):
                        shutil.copyfile(origen / nombre, destino / nombre)
                    (artefactos / "alias_champion.json").write_text(
                        json.dumps({"version": version}))
                    shutil.copyfile(artefactos_real / "monitor_estado.json",
                                    artefactos / "monitor_estado.json")

                    if caso == "alias_ausente":
                        (artefactos / "alias_champion.json").unlink()
                    elif caso == "json_corrupto":
                        (destino / "estimacion.json").write_text("{")
                    elif caso == "manifiesto_ausente":
                        (destino / "manifest.json").unlink()
                    else:
                        (artefactos / "monitor_estado.json").write_text("{")

                    nucleo.ARTEFACTOS = artefactos
                    nucleo.REGISTRO = registro
                    nucleo.champion = champion_temporal
                    nucleo.verificar_alias = lambda: True
                    nucleo._cache.clear()

                    respuestas = [
                        c.get("/salud"),
                        c.get("/efecto"),
                        c.post("/consulta", json={}),
                        c.post("/heterogeneidad", json={}),
                    ]
                    sin_numeros = all(
                        r.status_code == 200
                        and r.json().get("estado") == "abstencion"
                        and "efecto" not in r.json()
                        and "proyeccion" not in r.json()
                        and r.json().get("estado_puerta") == "falla"
                        for r in respuestas)
                    salud = respuestas[0].json()
                    raiz = c.get("/")
                    caso_ok = (sin_numeros
                               and salud.get("integridad_valida") is False
                               and raiz.status_code == 200
                               and "champion no está disponible" in raiz.text)
                    resultados.append(caso_ok)
                    print(f"carga defectuosa ({caso}): "
                          f"{'abstención fail-closed OK' if caso_ok else 'FALLÓ'}")
            except Exception as exc:
                resultados.append(False)
                print(f"carga defectuosa ({caso}): EXCEPCIÓN {type(exc).__name__}: {exc}")
            finally:
                nucleo._cache.clear()
    finally:
        nucleo.ARTEFACTOS = artefactos_real
        nucleo.REGISTRO = registro_real
        nucleo.champion = champion_real
        nucleo.verificar_alias = verificar_real
        nucleo._cache.clear()
        nucleo._cache.update(cache_real)
    return all(resultados)


def main() -> int:
    ok = True
    ok &= nucleo.efecto_lista_de_prueba() == [
        "/salud", "/efecto", "/consulta", "/heterogeneidad", "/efecto_individual"]

    r = c.get("/salud")
    js = r.json()
    ok &= r.status_code == 200 and js["estado"] == "ok"
    ok &= "estado_puerta" in js and js.get("integridad_valida") is True
    ok &= (js.get("identificacion", {}).get("criterio") == "backdoor"
           and js.get("identificacion", {}).get("pasa") is True)
    ok &= (js.get("sensibilidad", {}).get("cotas_manski_ate") is not None
           and js.get("placebo", {}).get("pasa") is True)
    ok &= _diagnosticos_ok(js)
    print(f"/salud: {r.status_code} {js}")

    r = c.get("/efecto")
    j = r.json()
    ok &= r.status_code == 200 and "efecto" in j and "ic95" in j and "version" in j
    ok &= ("estado_puerta" in j and "sensibilidad" in j and "placebo" in j
           and "identificacion" in j
           and "e_value" in j.get("sensibilidad", {})
           and bool(j.get("sensibilidad", {}).get("e_value", {}).get("limites"))
           and "cotas_manski" in j.get("sensibilidad", {})
           and "tratamiento_permutado" in j.get("placebo", {})
           and j.get("placebo", {}).get("pasa") is True
           and j.get("identificacion", {}).get("identificacion_pasa") is True
           and j.get("integridad_valida") is True)
    ok &= _diagnosticos_ok(j)
    print(f"/efecto: {r.status_code} efecto={j['efecto']} ic95={j['ic95']} "
          f"version={j['version']} puerta={j.get('estado_puerta')}")

    dentro, fuera = perfiles()
    r1 = c.post("/consulta", json=dentro)
    j1 = r1.json()
    ok &= r1.status_code == 200 and j1["estado"] == "respuesta"
    ok &= ("estado_puerta" in j1 and "sensibilidad" in j1 and "placebo" in j1)
    print(f"/consulta dentro: {r1.status_code} estado={j1['estado']} "
          f"efecto={j1.get('efecto')} puerta={j1.get('estado_puerta')}")

    r2 = c.post("/consulta", json=fuera)
    j2 = r2.json()
    cambiada = next(cov for cov in dentro if dentro[cov] != fuera[cov])
    ok &= (r2.status_code == 200 and j2["estado"] == "abstencion"
           and "efecto" not in j2 and "estado_puerta" in j2)
    print(f"/consulta fuera ({cambiada}={fuera[cambiada]:g}): {r2.status_code} "
          f"estado={j2['estado']} motivo={j2['motivo']} (sin número)")

    r3 = c.post("/consulta", json=dentro)
    ok &= r3.json() == j1
    print(f"determinismo: dos llamadas idénticas -> {'iguales' if r3.json() == j1 else 'DISTINTAS'}")

    r4 = c.post("/heterogeneidad", json=dentro)
    j4 = r4.json()
    ok &= r4.status_code == 200 and _heterogeneidad_ok(j4)
    ok &= (j4.get("estado_puerta") is not None
           and j4.get("sensibilidad", {}).get("aplicable") is False)
    print(f"/heterogeneidad dentro: {r4.status_code} estado={j4.get('estado')} "
          f"proyeccion={j4.get('proyeccion')} ic95={j4.get('ic95')} "
          f"r2={j4.get('ajuste_r2')}")

    r5 = c.post("/efecto_individual", json=dentro)
    j5 = r5.json()
    nucleo_alias = {k: v for k, v in j5.items()
                    if k not in ("deprecacion", "endpoint_recomendado")}
    ok &= r5.status_code == 200 and _heterogeneidad_ok(j5)
    ok &= (nucleo_alias == j4 and bool(j5.get("deprecacion"))
           and j5.get("endpoint_recomendado") == "/heterogeneidad")
    print(f"/efecto_individual (alias): {r5.status_code} tipo={j5.get('tipo')} "
          f"deprecacion={j5.get('deprecacion')}")

    r6 = c.post("/heterogeneidad", json=fuera)
    j6 = r6.json()
    ok &= r6.status_code == 200 and _abstencion_heterogeneidad_ok(j6)
    print(f"/heterogeneidad fuera ({cambiada}={fuera[cambiada]:g}): "
          f"{r6.status_code} estado={j6.get('estado')} (sin proyección)")

    r7 = c.post("/efecto_individual", json=fuera)
    j7 = r7.json()
    ok &= (r7.status_code == 200 and _abstencion_heterogeneidad_ok(j7)
           and bool(j7.get("deprecacion"))
           and j7.get("endpoint_recomendado") == "/heterogeneidad")
    print(f"/efecto_individual fuera (alias): {r7.status_code} "
          f"estado={j7.get('estado')} (sin proyección)")

    r8 = c.get("/efecto?formato=texto")
    ok &= (r8.status_code == 200 and "IC 95" in r8.text
           and "Sensibilidad" in r8.text and "Placebo" in r8.text
           and "Manski" in r8.text and "criterio backdoor: pasa" in r8.text
           and "D permutado: pasa" in r8.text and "Y permutado: pasa" in r8.text
           and r8.headers["content-type"].startswith("text/plain"))
    print(f"/efecto?formato=texto: {r8.status_code} "
          f"({len(r8.text.splitlines())} líneas) — lecturas legibles OK")

    puerta_ok = _probar_puerta_falla()
    ok &= puerta_ok
    print("puerta falla: ATE y heterogeneidad se abstienen sin estimación OK"
          if puerta_ok else "puerta falla: FALLÓ")
    integridad_ok = _probar_integridad_falla()
    ok &= integridad_ok
    print("integridad rota: abstención sin número OK" if integridad_ok
          else "integridad rota: FALLÓ")

    r9 = c.post("/heterogeneidad?formato=texto", json=dentro)
    ok &= (r9.status_code == 200
           and "HETEROGENEIDAD ESTIMADA PARA UN PERFIL" in r9.text
           and "Proyección" in r9.text and "Advertencias" in r9.text)
    print(f"/heterogeneidad?formato=texto: {r9.status_code} encabezado OK")

    r10 = c.post("/efecto_individual?formato=texto", json=dentro)
    ok &= (r10.status_code == 200
           and "HETEROGENEIDAD ESTIMADA PARA UN PERFIL" in r10.text
           and "Deprecación" in r10.text and "/heterogeneidad" in r10.text)
    print(f"/efecto_individual?formato=texto: {r10.status_code} alias deprecado OK")

    r11 = c.get("/")
    ok &= (r11.status_code == 200 and "<form" in r11.text and "Estimar" in r11.text
           and "POST /heterogeneidad" in r11.text)
    print(f"/ (formulario): {r11.status_code} — {r11.text.count('<input')} campos")

    lectura_negativa = nucleo._lectura(-2.0, [-3.0, -1.0])
    ok &= "negativo" in lectura_negativa and "positivo" not in lectura_negativa
    print("lectura de IC negativo: OK" if "negativo" in lectura_negativa
          else "lectura de IC negativo: FALLÓ")

    carga_ok = _probar_archivos_defectuosos()
    ok &= carga_ok
    print("archivos ausentes/corruptos: fail-closed OK" if carga_ok
          else "archivos ausentes/corruptos: FALLÓ")

    r12 = c.get("/calcular", params=dentro)
    ok &= (r12.status_code == 200
           and "HETEROGENEIDAD ESTIMADA PARA UN PERFIL" in r12.text)
    print(f"/calcular: {r12.status_code} informe de heterogeneidad generado")

    print("\nHUMO:", "OK" if ok else "FALLÓ")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
