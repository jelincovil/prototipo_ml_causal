"""servicio_core.py — [BLOQUE 6, min 115–140] El servicio: respuesta y abstención.

Se completa en vivo: la carga del bundle champion y la consulta con soporte.
"""
from __future__ import annotations

import json
import math

from registro import champion
from rutas import ARTEFACTOS, REGISTRO
from sensibilidad import e_value_continuo

_cache: dict = {}

TITULOS = {"poblacional": "EFECTO POBLACIONAL",
           "estrato": "EFECTO POR ESTRATO",
           "individual": "EFECTO PARA UN PERFIL"}


def _num(x: float, decimales: int = 1) -> str:
    """Formato español: 1.638,6 · 0,095."""
    texto = f"{x:,.{decimales}f}"
    return texto.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")


def _lectura(efecto: float, ic: list, *, individual: bool = False,
             r2: float | None = None) -> str:
    excluye_cero = ic[0] > 0 or ic[1] < 0
    if individual:
        if not excluye_cero:
            return ("El intervalo incluye el cero: con estos datos no se puede afirmar "
                    "un efecto para este perfil.")
        return ("El intervalo excluye el cero, pero la proyección apenas distingue entre "
                f"perfiles (R² = {_num(r2 or 0.0, 3)}): tómalo como orientación, no como "
                "efecto individual.")
    if not excluye_cero:
        return ("El intervalo incluye el cero: no hay evidencia de efecto con este "
                "tamaño de muestra.")
    return ("El intervalo excluye el cero: efecto positivo estimado bajo los supuestos "
            "declarados.")


def _texto_sensibilidad(sens: dict | None) -> str | None:
    if not sens:
        return None
    if sens.get("aplicable") is False:
        return sens.get("motivo", "no aplicable a este estimando")
    ev = sens.get("e_value") or {}
    rv = sens.get("valor_robustez_ols") or {}
    partes = []
    if ev:
        partes.append(f"E-value {ev.get('e_value_punto', float('nan')):.2f} "
                      f"(IC {ev.get('e_value_ic', float('nan')):.2f})")
    if rv:
        partes.append(f"RV OLS {rv.get('rv_pct', float('nan')):.1f} %")
    return "; ".join(partes) or sens.get("lectura")


def _texto_identificacion(ident: dict | None) -> str | None:
    if not ident:
        return None
    if ident.get("aplicable") is False:
        return ident.get("motivo", "identificación no disponible")
    ok = ident.get("efecto_identificable_por_grafo")
    criterio = ident.get("criterio", "")
    metodo = ident.get("metodos_dowhy") or ident.get("metodo_dowhy", "")
    partes = [f"efecto identificable según el grafo: {'sí' if ok else 'no'}"]
    if metodo:
        partes.append(f"DoWhy: {metodo}")
    if criterio:
        partes.append(criterio)
    if ident.get("conjunto_ajuste_estimado") is not None:
        n = len(ident["conjunto_ajuste_estimado"])
        partes.append(f"conjunto de ajuste ({n} vars., extraído de {ident.get('fuente_conjunto')})")
    bench = ident.get("identification_status_benchmark")
    if bench:
        partes.append(f"metadata benchmark: {bench}")
    if ident.get("coincide_valid_adjustment_sets") is not None:
        partes.append(
            "coincide con valid_adjustment_sets del benchmark: "
            f"{'sí' if ident['coincide_valid_adjustment_sets'] else 'no'}")
    return "; ".join(partes)


def _texto_placebo(placebo: dict | None) -> str | None:
    if not placebo:
        return None
    if placebo.get("aplicable") is False:
        return placebo.get("motivo", "no aplicable a este estimando")
    td = placebo.get("tratamiento_permutado") or {}
    rd = placebo.get("resultado_permutado") or {}
    partes = []
    if td:
        partes.append(f"D permutado p={td.get('p_valor_aprox', float('nan')):.3f}, "
                      f"percentil {td.get('percentil_observado', float('nan')):.1f}")
    if rd:
        ic = rd.get("ic95", [float("nan"), float("nan")])
        partes.append(f"Y permutado efecto {rd.get('efecto', float('nan')):.2f} "
                      f"[{ic[0]:.2f}, {ic[1]:.2f}]")
    return "; ".join(partes) or placebo.get("lectura")


def formatear(payload: dict) -> str:
    """Versión legible de una respuesta, alineada para leer en terminal."""
    titulo = TITULOS.get(payload.get("tipo", ""), "RESPUESTA")
    version = payload.get("version", "")
    encabezado = f"{titulo} — versión {version}"
    if payload.get("estado") != "respuesta":
        puerta = payload.get("estado_puerta")
        extra = f"\nPuerta: {puerta}" if puerta else ""
        return (f"{encabezado}\n" + "-" * len(encabezado) +
                f"\n\nABSTENCIÓN: {payload.get('motivo')}{extra}\n"
                "No se devuelve ningún número: la consulta no puede responderse con "
                "la evidencia declarada.\n")

    unidad = payload.get("unidad", "")
    ic = payload["ic95"]
    filas = [("Estimando", payload.get("estimando", "")),
             ("Efecto", f"{_num(payload['efecto'])} {unidad}"),
             ("IC 95 %", f"{_num(ic[0])} a {_num(ic[1])}")]
    if payload.get("estado_puerta"):
        filas.append(("Puerta", payload["estado_puerta"]))
    if payload.get("tipo") == "estrato":
        estrato = payload["estrato"]
        filas.append(("Estrato", f"{estrato['variable']} = {estrato['valor']} "
                                  f"(n = {estrato['n']})"))
        filas.append(("Nota", payload.get("nota_heterogeneidad", "")))
    if payload.get("tipo") == "individual":
        filas.append(("Ajuste", f"R² = {_num(payload.get('ajuste_r2', 0.0), 3)} "
                                 f"(discriminación {payload.get('confianza_discriminacion')})"))
        if payload.get("aviso"):
            filas.append(("Aviso", payload["aviso"]))
    sens = _texto_sensibilidad(payload.get("sensibilidad"))
    if sens:
        filas.append(("Sensibilidad", sens))
    placebo = _texto_placebo(payload.get("placebo"))
    if placebo:
        filas.append(("Placebo", placebo))
    ident = _texto_identificacion(payload.get("identificacion"))
    if ident:
        filas.append(("Identificación causal", ident))
    filas.append(("Lectura", payload.get("interpretacion", "")))
    filas.append(("Alcance", payload.get("que_cubre_el_ic", "")))
    limites = payload.get("limitaciones") or []
    if limites:
        filas.append(("Límites", " · ".join(limites)))

    ancho = max(len(etiqueta) for etiqueta, _ in filas)
    cuerpo = "\n".join(f"{etiqueta.ljust(ancho)} : {valor}" for etiqueta, valor in filas)
    return f"{encabezado}\n" + "-" * len(encabezado) + f"\n\n{cuerpo}\n"


def _cargar() -> dict:
    """Lee la versión champion (una vez): estimación, tarjeta, manifiesto y monitor."""
    # El bundle viaja: el servicio NO lee los CSV, solo los artefactos con hash.
    if "bundle" not in _cache:
        version = champion()
        carpeta = REGISTRO / version
        manifest = json.loads((carpeta / "manifest.json").read_text())
        monitor = None
        ruta_monitor = ARTEFACTOS / "monitor_estado.json"
        if ruta_monitor.exists():
            monitor = json.loads(ruta_monitor.read_text())
            if monitor.get("version") != version:
                monitor = None
        _cache["bundle"] = {
            "version": version,
            "estimacion": json.loads((carpeta / "estimacion.json").read_text()),
            "tarjeta": json.loads((carpeta / "tarjeta.json").read_text()),
            "manifest": manifest,
            "monitor": monitor,
        }
    return _cache["bundle"]


def _estado_puerta(bundle: dict) -> str:
    monitor = bundle.get("monitor") or {}
    if monitor.get("estado_puerta"):
        return str(monitor["estado_puerta"])
    return str(bundle.get("manifest", {}).get("puerta", "desconocido"))


def _abstencion_por_puerta(bundle: dict, tipo: str) -> dict | None:
    estado = _estado_puerta(bundle)
    if estado == "falla":
        return {
            "estado": "abstencion",
            "tipo": tipo,
            "motivo": ("la versión champion tiene puerta 'falla': no se devuelve "
                       "ningún número"),
            "estado_puerta": estado,
            "version": bundle["version"],
        }
    return None


def _placebo_resumen(estimacion: dict) -> dict:
    placebo = estimacion.get("placebo", {})
    td = placebo.get("tratamiento_permutado", {})
    rd = placebo.get("resultado_permutado", {})
    return {
        "tratamiento_permutado_p": td.get("p_valor_aprox"),
        "tratamiento_permutado_ok": td.get("placebo_ok"),
        "resultado_permutado_ok": rd.get("control_negativo_ok"),
    }


def salud() -> dict:
    b = _cargar()
    return {"estado": "ok", "version": b["version"],
            "estimando": b["tarjeta"]["estimando"],
            "estado_puerta": _estado_puerta(b)}


def efecto() -> dict:
    """El efecto poblacional del prototipo, con su incertidumbre y su versión."""
    b = _cargar()
    abst = _abstencion_por_puerta(b, "poblacional")
    if abst:
        return abst
    e = b["estimacion"]
    efecto = round(e["ate_aipw"], 1)
    ic = [round(x, 1) for x in e["ic_aipw"]]
    return {
        "estado": "respuesta",
        "tipo": "poblacional",
        "estimando": b["tarjeta"]["estimando"],
        "efecto": efecto,
        "unidad": e["unidad"],
        "efecto_texto": (f"{_num(efecto)} {e['unidad']} "
                         f"(IC 95 %: {_num(ic[0])} a {_num(ic[1])})"),
        "ic95": ic,
        "interpretacion": _lectura(efecto, ic),
        "que_cubre_el_ic": "el ATE poblacional (no un efecto individual)",
        "estimador": e["estimador_principal"],
        "poblacion": b["tarjeta"]["poblacion"],
        "estado_puerta": _estado_puerta(b),
        "sensibilidad": e.get("sensibilidad", {}),
        "placebo": e.get("placebo", {}),
        "identificacion": e.get("identificacion", {}),
        "limitaciones": b["tarjeta"].get("limitaciones", []),
        "version": b["version"],
    }


def consulta(perfil: dict) -> dict:
    """Responde una consulta individual: dentro del soporte, o abstención.

    La abstención es una respuesta de primera clase: no devuelve ningún
    número cuando el perfil cae fuera del rango de entrenamiento de alguna
    covariable (el soporte que la tarjeta declara).
    """
    b = _cargar()
    abst = _abstencion_por_puerta(b, "estrato")
    if abst:
        return abst
    rangos = b["estimacion"]["rangos_covariables"]
    # Abstención de primera clase: fuera del soporte no se devuelve ningún número.
    motivos = []
    for covariable, (lo, hi) in rangos.items():
        if covariable not in perfil:
            continue
        valor = float(perfil[covariable])
        if valor < lo or valor > hi:
            motivos.append(f"{covariable}={valor:g} fuera de "
                           f"[{round(lo, 4)}, {round(hi, 4)}]")
    if motivos:
        return {"estado": "abstencion", "tipo": "estrato",
                "motivo": "; ".join(motivos),
                "estado_puerta": _estado_puerta(b),
                "version": b["version"]}

    estratos = b["estimacion"]["estratos"]
    corte = estratos["variable"]
    if corte not in perfil:
        return {"estado": "abstencion", "tipo": "estrato",
                "motivo": (f"falta la covariable del corte de heterogeneidad "
                           f"({corte}) para asignar el estrato"),
                "estado_puerta": _estado_puerta(b),
                "version": b["version"]}
    clave = "1" if float(perfil[corte]) > estratos["umbral"] else "0"
    hoja = estratos["hojas"][clave]
    efecto = round(hoja["efecto"], 1)
    ic = [round(x, 1) for x in hoja["ic"]]

    sd_y = b["estimacion"].get("sd_resultado")
    if sd_y:
        sens = {"aplicable": True,
                **e_value_continuo(hoja["efecto"], float(sd_y), hoja["ic"])}
    else:
        sens = {"aplicable": False,
                "motivo": "el bundle no trae sd_resultado para estandarizar"}

    return {
        "estado": "respuesta",
        "tipo": "estrato",
        "estimando": (f"media del efecto del programa en el estrato "
                      f"{corte}={clave} ({hoja['etiqueta']})"),
        "efecto": efecto,
        "unidad": b["estimacion"]["unidad"],
        "efecto_texto": (f"{_num(efecto)} {b['estimacion']['unidad']} "
                         f"(IC 95 %: {_num(ic[0])} a {_num(ic[1])})"),
        "ic95": ic,
        "interpretacion": _lectura(efecto, ic),
        "que_cubre_el_ic": ("la media del efecto en este estrato; NO el ATE "
                            "poblacional ni un efecto individual"),
        "estrato": {"variable": corte, "valor": int(clave),
                    "n": hoja["n"]},
        "nota_heterogeneidad": estratos["nota"],
        "estado_puerta": _estado_puerta(b),
        "sensibilidad": sens,
        "placebo": {"aplicable": False,
                    "referencia": "poblacional",
                    "motivo": ("el placebo aplica al ATE poblacional, no a la "
                               "media de un estrato"),
                    "resumen_poblacional": _placebo_resumen(b["estimacion"])},
        "identificacion": b["estimacion"].get("identificacion", {}),
        "version": b["version"],
    }


def campos_formulario() -> dict:
    """Covariables del escenario con rango y valor sugerido (para el formulario)."""
    est = _cargar()["estimacion"]
    campos = {}
    for covariable, (lo, hi) in est["rangos_covariables"].items():
        umbral = est["estratos"]["umbral"]
        sugerido = (umbral + (hi - umbral) / 2) if covariable == est["estratos"]["variable"] \
            else (lo + hi) / 2
        campos[covariable] = {"min": lo, "max": hi, "valor": round(sugerido, 2)}
    return campos


def efecto_individual(perfil: dict) -> dict:
    """Efecto esperado para un perfil nuevo, o abstención fuera de soporte.

    Devuelve la proyección lineal del score AIPW sobre las covariables del perfil.
    No es un CATE validado: el IC es condicional al modelo y al ajuste lineal.
    """
    b = _cargar()
    abst = _abstencion_por_puerta(b, "individual")
    if abst:
        return abst
    est = b["estimacion"]
    modelo = est.get("modelo_individual")
    if modelo is None:
        return {"estado": "abstencion", "tipo": "individual",
                "motivo": "el bundle de esta versión no trae modelo_individual",
                "estado_puerta": _estado_puerta(b),
                "version": b["version"]}

    covariables = list(modelo["coeficientes"])
    faltan = [c for c in covariables if c not in perfil]
    if faltan:
        return {"estado": "abstencion", "tipo": "individual",
                "motivo": f"faltan covariables del perfil: {faltan}",
                "estado_puerta": _estado_puerta(b),
                "version": b["version"]}

    motivos = []
    for covariable, (lo, hi) in est["rangos_covariables"].items():
        valor = float(perfil[covariable])
        if valor < lo or valor > hi:
            motivos.append(f"{covariable}={valor:g} fuera de "
                           f"[{round(lo, 4)}, {round(hi, 4)}]")
    if motivos:
        return {"estado": "abstencion", "tipo": "individual",
                "motivo": "; ".join(motivos),
                "estado_puerta": _estado_puerta(b),
                "version": b["version"]}

    z = [(float(perfil[c]) - modelo["medias"][c]) / modelo["desviaciones"][c]
         for c in covariables]
    beta = [modelo["coeficientes"][c] for c in covariables]
    tau = modelo["intercepto"] + sum(bj * zj for bj, zj in zip(beta, z))

    # Varianza de la predicción: z' Cov(beta) z (incluye el intercepto).
    v = [1.0, *z]
    cov = modelo["cov_beta"]
    var = sum(v[i] * cov[i][j] * v[j]
              for i in range(len(v)) for j in range(len(v)))
    se = float(math.sqrt(max(var, 0.0)))

    aviso = None
    if max(abs(zj) for zj in z) > 2.5:
        aviso = ("perfil en el borde del soporte: la proyección lineal extrapola "
                 "y el IC subestima la incertidumbre")

    r2 = float(modelo["r2"])
    discriminacion = ("muy baja" if r2 < 0.05 else
                      "baja" if r2 < 0.15 else "moderada")

    return {
        "estado": "respuesta",
        "tipo": "individual",
        "estimando": ("efecto esperado del programa para un perfil con estas "
                      "covariables (proyección lineal del score AIPW)"),
        "efecto": round(float(tau), 1),
        "unidad": est["unidad"],
        "efecto_texto": (f"{_num(tau)} {est['unidad']} "
                         f"(IC 95 %: {_num(tau - 1.96 * se)} a {_num(tau + 1.96 * se)})"),
        "ic95": [round(float(tau - 1.96 * se), 1), round(float(tau + 1.96 * se), 1)],
        "interpretacion": _lectura(tau, [tau - 1.96 * se, tau + 1.96 * se],
                                   individual=True, r2=r2),
        "que_cubre_el_ic": ("la proyección lineal, condicional a los scores AIPW; "
                            "NO cubre el sesgo de especificación lineal ni es un CATE validado"),
        "ajuste_r2": round(r2, 3),
        "confianza_discriminacion": discriminacion,
        "n_entrenamiento": modelo["n"],
        "aviso": aviso,
        "estado_puerta": _estado_puerta(b),
        "sensibilidad": {"aplicable": False,
                         "motivo": ("la proyección individual no es un estimando "
                                    "causal validado; usa /efecto para la "
                                    "sensibilidad poblacional")},
        "placebo": {"aplicable": False,
                    "motivo": ("el placebo aplica al ATE poblacional, no a una "
                               "proyección individual")},
        "identificacion": est.get("identificacion", {}),
        "limitaciones": b["tarjeta"].get("limitaciones", []),
        "version": b["version"],
    }


def efecto_lista_de_prueba() -> list[str]:
    """Auxiliar para el humo: las rutas que la prueba de humo ejercita."""
    return ["/salud", "/efecto", "/consulta", "/efecto_individual"]
