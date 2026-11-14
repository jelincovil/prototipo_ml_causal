"""Demostración por terminal del nuevo contrato: datos + DAG + DML-IV + evaluación."""
from __future__ import annotations

import argparse
import json

import numpy as np

from datos_iv import EsquemaIV, comprobar_pared, leer, verificar_splits
from estimacion_iv import estimar
from generar_datos_iv import generar_universo
from rutas_iv import DATOS, SALIDA, SEMILLA, SEMILLA_SPLIT


def datos_demostracion(escenario: str):
    """El escenario válido usa el CSV; los contrafactuales se generan en memoria."""
    if escenario == "valido":
        observados = leer("train")
        return observados, None
    universo, verdad = generar_universo(escenario=escenario)
    orden = np.random.default_rng(SEMILLA_SPLIT).permutation(len(universo))
    muestra = universo.iloc[orden[:1200]].reset_index(drop=True)
    return muestra, verdad


def evaluacion_repetida(escenario: str, repeticiones: int) -> dict:
    """Monte Carlo didáctico: la verdad entra solo después de cada ajuste."""
    errores_ingenuos, errores_dml, cubiertos = [], [], []
    for repeticion in range(repeticiones):
        semilla = SEMILLA + 1009 * repeticion
        observados, verdad = generar_universo(semilla=semilla, escenario=escenario, n=1200)
        resultado = estimar(observados, semilla=semilla)
        referencia = verdad["late_compliers"]
        errores_ingenuos.append(resultado["diferencia_ingenua"] - referencia)
        errores_dml.append(resultado["coeficiente"] - referencia)
        inferior, superior = resultado["ic95"]
        cubiertos.append(inferior <= referencia <= superior)
    errores_dml = np.asarray(errores_dml)
    return {
        "n_repeticiones": repeticiones,
        "sesgo_medio_ingenuo": float(np.mean(errores_ingenuos)),
        "sesgo_medio_dml": float(np.mean(errores_dml)),
        "rmse_dml": float(np.sqrt(np.mean(errores_dml**2))),
        "cobertura_ic95_empirica": float(np.mean(cubiertos)),
        "advertencia": "Simulación didáctica, no garantía teórica ni validación con datos reales",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--escenario", choices=["valido", "debil", "exclusion"], default="valido")
    parser.add_argument("--repeticiones", type=int, default=0)
    args = parser.parse_args()
    if args.repeticiones < 0:
        parser.error("--repeticiones no puede ser negativo")

    print("1. CONTRATO DE DATOS")
    if args.escenario == "valido":
        esquema = EsquemaIV()
        entrenamiento = leer("train")
        esquema.validar(list(entrenamiento), entrenamiento)
        assert verificar_splits()
        comprobar_pared()
    else:
        print(f"  Escenario alternativo '{args.escenario}' generado en memoria; CSV base intacto.")

    print("\n2. NUEVO DAG Y ESTIMANDO")
    print("  Z → D → Y        Z: invitación; D: asistencia; Y: puntaje")
    print("       ↑   ↑        X1, X2 → D e Y; U → D e Y (U no observada)")
    print("       └── U ──────┘")
    print("  Estimando: LATE entre compliers, no ATE poblacional.")

    observados, verdad_memoria = datos_demostracion(args.escenario)
    print("\n3. ESTIMACIÓN (sin consultar la verdad)")
    resultado = estimar(observados)
    print(f"  Diferencia ingenua E[Y|D=1]−E[Y|D=0]: {resultado['diferencia_ingenua']:.3f}")
    primera = resultado["primera_etapa"]
    print(f"  Primera etapa: {primera['diferencia']:.3f}; F descriptivo: {primera['f_descriptivo_sin_covariables']:.1f}")
    print(f"  LATE DoubleMLIIVM: {resultado['coeficiente']:.3f}")
    print(f"  IC 95 %: [{resultado['ic95'][0]:.3f}; {resultado['ic95'][1]:.3f}]")
    if args.escenario == "debil":
        print("  Lectura: instrumento débil; el intervalo y la inferencia pueden volverse inestables.")
    elif args.escenario == "exclusion":
        print("  Lectura: Z tiene efecto directo sobre Y; DML no detecta ni corrige esa violación.")

    # La referencia se incorpora al informe únicamente después de completar la estimación.
    if args.escenario == "valido":
        with open(DATOS / "interventions.json", encoding="utf-8") as archivo:
            verdad = json.load(archivo)
    else:
        verdad = verdad_memoria
    resultado["evaluacion_posterior"] = verdad
    print("\n4. EVALUACIÓN POSTERIOR (referencia sintética separada)")
    print(f"  LATE verdadero de compliers: {verdad['late_compliers']:.3f}")
    print(f"  Proporción de compliers: {verdad['proporcion_compliers']:.1%}")
    print("  Una sola proximidad a la verdad no demuestra validez general.")

    if args.repeticiones:
        print(f"\n5. MONTE CARLO ({args.repeticiones} repeticiones)")
        resultado["evaluacion_repetida"] = evaluacion_repetida(args.escenario, args.repeticiones)
        rep = resultado["evaluacion_repetida"]
        print(f"  Sesgo medio ingenuo: {rep['sesgo_medio_ingenuo']:.3f}")
        print(f"  Sesgo medio DML: {rep['sesgo_medio_dml']:.3f}")
        print(f"  RMSE DML: {rep['rmse_dml']:.3f}")
        print(f"  Cobertura empírica del IC 95 %: {rep['cobertura_ic95_empirica']:.1%}")

    SALIDA.mkdir(exist_ok=True)
    nombre = "resultado_iv.json" if args.escenario == "valido" else f"resultado_iv_{args.escenario}.json"
    ruta = SALIDA / nombre
    ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nResultado guardado en {ruta}")
    print("No se modificó el prototipo original ni se promovió ningún champion.")


if __name__ == "__main__":
    main()
