"""humo.py — Prueba de humo del servicio (TestClient, sin levantar puerto).

Cubre los tres invariantes del servicio del prototipo:
  1. /efecto devuelve efecto + IC + versión (el bundle viaja).
  2. /consulta fuera del soporte se abstiene SIN ningún número.
  3. Dos llamadas idénticas devuelven exactamente lo mismo.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

import servicio_core as nucleo
from servicio import app
from rutas import ESCENARIO

c = TestClient(app)

# Perfil dentro del soporte de real/jobs (el del kit). Para otros escenarios se
# construye desde los rangos del bundle: el humo no lee CSV.
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
    if ESCENARIO == "real/jobs":
        return PERFIL_JOBS, PERFIL_JOBS_FUERA
    return _perfil_desde_bundle(False), _perfil_desde_bundle(True)


def _probar_puerta_falla() -> bool:
    """Fuerza temporalmente la puerta a 'falla' y verifica abstención sin número."""
    b = nucleo._cargar()
    original_manifest = b.get("manifest", {}).get("puerta")
    original_monitor = b.get("monitor")
    b["manifest"]["puerta"] = "falla"
    b["monitor"] = None
    try:
        j = nucleo.efecto()
        return j.get("estado") == "abstencion" and "efecto" not in j
    finally:
        b["manifest"]["puerta"] = original_manifest
        b["monitor"] = original_monitor


def main() -> int:
    ok = True

    r = c.get("/salud")
    js = r.json()
    ok &= r.status_code == 200 and js["estado"] == "ok"
    ok &= "estado_puerta" in js
    print(f"/salud: {r.status_code} {js}")

    r = c.get("/efecto")
    j = r.json()
    ok &= r.status_code == 200 and "efecto" in j and "ic95" in j and "version" in j
    ok &= ("estado_puerta" in j and "sensibilidad" in j and "placebo" in j
           and "identificacion" in j
           and "e_value" in j.get("sensibilidad", {})
           and "tratamiento_permutado" in j.get("placebo", {}))
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

    r4 = c.post("/efecto_individual", json=dentro)
    j4 = r4.json()
    ok &= r4.status_code == 200 and j4.get("estado") == "respuesta" and "efecto" in j4
    ok &= (j4.get("estado_puerta") is not None
           and j4.get("sensibilidad", {}).get("aplicable") is False)
    print(f"/efecto_individual dentro: {r4.status_code} estado={j4.get('estado')} "
          f"efecto={j4.get('efecto')} ic95={j4.get('ic95')} r2={j4.get('ajuste_r2')}")

    r5 = c.post("/efecto_individual", json=fuera)
    j5 = r5.json()
    ok &= (r5.status_code == 200 and j5.get("estado") == "abstencion"
           and "efecto" not in j5)
    print(f"/efecto_individual fuera ({cambiada}={fuera[cambiada]:g}): "
          f"{r5.status_code} estado={j5.get('estado')} (sin número)")

    r6 = c.get("/efecto?formato=texto")
    ok &= (r6.status_code == 200 and "IC 95" in r6.text
           and "Sensibilidad" in r6.text and "Placebo" in r6.text
           and r6.headers["content-type"].startswith("text/plain"))
    print(f"/efecto?formato=texto: {r6.status_code} "
          f"({len(r6.text.splitlines())} líneas) — lecturas legibles OK")
    ok &= _probar_puerta_falla()
    print("puerta falla: abstención sin número OK" if ok else "puerta falla: FALLÓ")

    r7 = c.post("/efecto_individual?formato=texto", json=dentro)
    ok &= (r7.status_code == 200 and "EFECTO PARA UN PERFIL" in r7.text)
    print(f"/efecto_individual?formato=texto: {r7.status_code} encabezado OK")

    r8 = c.get("/")
    ok &= r8.status_code == 200 and "<form" in r8.text and "Estimar" in r8.text
    print(f"/ (formulario): {r8.status_code} — {r8.text.count('<input')} campos")

    r9 = c.get("/calcular", params={k: v for k, v in dentro.items()})
    ok &= r9.status_code == 200 and "EFECTO PARA UN PERFIL" in r9.text
    print(f"/calcular: {r9.status_code} informe generado")

    print("\nHUMO:", "OK" if ok else "FALLÓ")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
