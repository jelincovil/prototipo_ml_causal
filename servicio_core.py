"""servicio_core.py — [BLOQUE 6, min 115–140] El servicio: respuesta y abstención.

Se completa en vivo: la carga del bundle champion y la consulta con soporte.
"""
from __future__ import annotations

import json
import math

from registro import champion, verificar_alias
from rutas import ARTEFACTOS, REGISTRO
from sensibilidad import e_value_continuo

_cache: dict = {}

TITULOS = {"poblacional": "EFECTO POBLACIONAL",
           "estrato": "EFECTO POR ESTRATO",
           "heterogeneidad_estimada": "HETEROGENEIDAD ESTIMADA PARA UN PERFIL"}

ADVERTENCIAS_HETEROGENEIDAD = [
    "La proyección describe heterogeneidad estimada; no es un CATE individual identificado.",
    ("El IC es condicional al ajuste lineal y a los scores AIPW del bundle; "
     "no cubre error de especificación ni incertidumbre de esos scores."),
]


def _num(x: float, decimales: int = 1) -> str:
    """Formato español: 1.638,6 · 0,095."""
    texto = f"{x:,.{decimales}f}"
    return texto.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")


def _lectura(efecto: float, ic: list, *, individual: bool = False,
             r2: float | None = None) -> str:
    excluye_cero = ic[0] > 0 or ic[1] < 0
    if individual:
        if not excluye_cero:
            return ("El intervalo condicional incluye el cero: la proyección para este "
                    "perfil es compatible con ausencia de heterogeneidad estimada.")
        return ("El intervalo condicional excluye el cero, pero la proyección apenas "
                f"distingue entre perfiles (R² = {_num(r2 or 0.0, 3)}): describe "
                "heterogeneidad estimada; no es un CATE individual identificado.")
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
    manski = sens.get("cotas_manski") or {}
    partes = []
    if ev:
        partes.append(f"E-value {ev.get('e_value_punto', float('nan')):.2f} "
                      f"(IC {ev.get('e_value_ic', float('nan')):.2f})")
    if rv:
        partes.append(f"RV OLS {rv.get('rv_pct', float('nan')):.1f} %")
    if manski:
        cotas = manski.get("ate", [float("nan"), float("nan")])
        partes.append(f"Manski ATE [{cotas[0]:.2f}, {cotas[1]:.2f}] "
                      "(sin ignorabilidad; soporte Y observado)")
    return "; ".join(partes) or sens.get("lectura")


def _texto_identificacion(ident: dict | None) -> str | None:
    if not ident:
        return None
    if ident.get("aplicable") is False:
        return "criterio backdoor: no evaluado; " + ident.get(
            "motivo", "identificación no disponible")
    pasa = ident.get("identificacion_pasa")
    if pasa is None:
        pasa = bool(ident.get("efecto_identificable_por_grafo")
                    and ident.get("coincide_valid_adjustment_sets"))
    criterio = ident.get("criterio_principal", "backdoor")
    metodos = ident.get("metodos_dowhy") or {}
    metodo = metodos.get("conjunto_backdoor", "default")
    partes = [f"criterio {criterio}: {'pasa' if pasa else 'falla'}",
              f"DoWhy: {metodo}"]
    if ident.get("conjunto_ajuste_estimado") is not None:
        n = len(ident["conjunto_ajuste_estimado"])
        partes.append(f"conjunto de ajuste: {n} covariables")
    if ident.get("coincide_valid_adjustment_sets") is not None:
        partes.append(
            "coincide con valid_adjustment_sets: "
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
        estado = "pasa" if td.get("placebo_ok") else "falla"
        partes.append(f"D permutado: {estado}; "
                      f"p={td.get('p_valor_aprox', float('nan')):.3f}, "
                      f"percentil {td.get('percentil_observado', float('nan')):.1f}")
    if rd:
        estado = "pasa" if rd.get("control_negativo_ok") else "falla"
        ic = rd.get("ic95", [float("nan"), float("nan")])
        partes.append(f"Y permutado: {estado}; "
                      f"efecto {rd.get('efecto', float('nan')):.2f} "
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
        if payload.get("deprecacion"):
            extra += f"\nDeprecación: {payload['deprecacion']}"
        for advertencia in payload.get("advertencias") or []:
            extra += f"\nAdvertencia: {advertencia}"
        return (f"{encabezado}\n" + "-" * len(encabezado) +
                f"\n\nABSTENCIÓN: {payload.get('motivo')}{extra}\n"
                "No se devuelve ningún número: la consulta no puede responderse con "
                "la evidencia declarada.\n")

    unidad = payload.get("unidad", "")
    ic = payload["ic95"]
    es_heterogeneidad = payload.get("tipo") == "heterogeneidad_estimada"
    filas = [("Estimando", payload.get("estimando", ""))]
    if es_heterogeneidad:
        filas.append(("Proyección", f"{_num(payload['proyeccion'])} {unidad}"))
    else:
        filas.append(("Efecto", f"{_num(payload['efecto'])} {unidad}"))
    filas.append(("IC 95 %", f"{_num(ic[0])} a {_num(ic[1])}"))
    if payload.get("estado_puerta"):
        filas.append(("Puerta", payload["estado_puerta"]))
    if payload.get("tipo") == "estrato":
        estrato = payload["estrato"]
        filas.append(("Estrato", f"{estrato['variable']} = {estrato['valor']} "
                                  f"(n = {estrato['n']})"))
        filas.append(("Nota", payload.get("nota_heterogeneidad", "")))
    if es_heterogeneidad:
        filas.append(("Ajuste", f"R² = {_num(payload.get('ajuste_r2', 0.0), 3)} "
                                 f"(discriminación {payload.get('confianza_discriminacion')})"))
        filas.append(("Advertencias", " · ".join(payload.get("advertencias") or [])))
    if payload.get("deprecacion"):
        filas.append(("Deprecación", payload["deprecacion"]))
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
        try:
            integridad_valida = verificar_alias()
        except (OSError, ValueError, KeyError, TypeError):
            integridad_valida = False
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
            "integridad_valida": bool(integridad_valida),
        }
    return _cache["bundle"]


def _estado_puerta(bundle: dict) -> str:
    monitor = bundle.get("monitor") or {}
    if monitor.get("estado_puerta"):
        return str(monitor["estado_puerta"])
    return str(bundle.get("manifest", {}).get("puerta", "desconocido"))


def _abstencion_por_puerta(bundle: dict, tipo: str) -> dict | None:
    if bundle.get("integridad_valida") is False:
        return {
            "estado": "abstencion",
            "tipo": tipo,
            "motivo": ("el alias champion o los hashes del bundle no verifican: "
                       "no se devuelve ningún número"),
            "integridad_valida": False,
            "estado_puerta": _estado_puerta(bundle),
            "version": bundle["version"],
        }
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


def _identificacion_resumen(ident: dict) -> dict:
    pasa = ident.get("identificacion_pasa")
    if pasa is None:
        pasa = bool(ident.get("efecto_identificable_por_grafo")
                    and ident.get("coincide_valid_adjustment_sets"))
    metodos = ident.get("metodos_dowhy") or {}
    return {
        "criterio": ident.get("criterio_principal", "backdoor"),
        "pasa": bool(pasa),
        "estado": "pasa" if pasa else "falla",
        "metodo_dowhy": metodos.get("conjunto_backdoor"),
        "criterio_backdoor_pasa": ident.get("criterio_backdoor_pasa"),
        "n_covariables_ajuste": len(ident.get("conjunto_ajuste_estimado") or []),
        "coincide_valid_adjustment_sets": ident.get("coincide_valid_adjustment_sets"),
        "motivo": ident.get("motivo"),
    }


def _sensibilidad_resumen(sens: dict) -> dict:
    ev = sens.get("e_value") or {}
    rv = sens.get("valor_robustez_ols") or {}
    manski = sens.get("cotas_manski") or {}
    return {
        "e_value_punto": ev.get("e_value_punto"),
        "e_value_ic": ev.get("e_value_ic"),
        "valor_robustez_ols_pct": rv.get("rv_pct"),
        "cotas_manski_ate": manski.get("ate"),
        "manski_ancho": manski.get("ancho"),
        "manski_incluye_cero": manski.get("incluye_cero"),
        "manski_fuente_soporte": manski.get("fuente_soporte"),
    }


def _placebo_resumen(estimacion: dict) -> dict:
    placebo = estimacion.get("placebo", {})
    td = placebo.get("tratamiento_permutado", {})
    rd = placebo.get("resultado_permutado", {})
    pasa = placebo.get("pasa")
    if pasa is None:
        pasa = bool(td.get("placebo_ok") and rd.get("control_negativo_ok"))
    return {
        "pasa": bool(pasa),
        "tratamiento_permutado_p": td.get("p_valor_aprox"),
        "tratamiento_permutado_ok": td.get("placebo_ok"),
        "resultado_permutado_ok": rd.get("control_negativo_ok"),
        "tratamiento_permutado": {
            "pasa": td.get("placebo_ok"),
            "p_valor_aprox": td.get("p_valor_aprox"),
            "percentil_observado": td.get("percentil_observado"),
        },
        "resultado_permutado": {
            "pasa": rd.get("control_negativo_ok"),
            "efecto": rd.get("efecto"),
            "ic95": rd.get("ic95"),
            "umbral_material": rd.get("umbral_material"),
        },
    }


def salud() -> dict:
    b = _cargar()
    estimacion = b["estimacion"]
    integridad = b.get("integridad_valida", False)
    return {
        "estado": "ok" if integridad else "abstencion",
        "version": b["version"],
        "estimando": b["tarjeta"]["estimando"],
        "estado_puerta": _estado_puerta(b),
        "integridad_valida": integridad,
        "diagnosticos_positividad": estimacion.get("diagnosticos_positividad", {}),
        "comparacion_estimadores": estimacion.get("comparacion_estimadores", {}),
        "identificacion": _identificacion_resumen(
            estimacion.get("identificacion", {})),
        "sensibilidad": _sensibilidad_resumen(
            estimacion.get("sensibilidad", {})),
        "placebo": _placebo_resumen(estimacion),
    }


def efecto() -> dict:
    """El efecto poblacional del prototipo, con su incertidumbre y su versión."""
    b = _cargar()
    abst = _abstencion_por_puerta(b, "poblacional")
    if abst:
        return abst
    e = b["estimacion"]
    efecto = round(e["ate_aipw"], 1)
    ic = [round(x, 1) for x in e["ic_aipw"]]
    sensibilidad = dict(e.get("sensibilidad", {}))
    e_value = dict(sensibilidad.get("e_value") or {})
    if e_value and not e_value.get("limites"):
        e_value["limites"] = (
            "Aproximación para resultado continuo: no es una razón de riesgos literal "
            "ni una cota exacta. No demuestra ausencia de confusión ni cubre mala "
            "especificación, selección, error de medición o falta de positividad.")
        sensibilidad["e_value"] = e_value
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
        "integridad_valida": b.get("integridad_valida", False),
        "diagnosticos_positividad": e.get("diagnosticos_positividad", {}),
        "comparacion_estimadores": e.get("comparacion_estimadores", {}),
        "sensibilidad": sensibilidad,
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


def _salida_heterogeneidad(payload: dict) -> dict:
    payload["tipo"] = "heterogeneidad_estimada"
    payload["advertencias"] = [
        *ADVERTENCIAS_HETEROGENEIDAD, *(payload.get("advertencias") or [])]
    return payload


def heterogeneidad(perfil: dict) -> dict:
    """Proyección de heterogeneidad para un perfil, o abstención fuera de soporte.

    Usa la proyección lineal del score AIPW almacenada en el bundle. El IC es
    condicional a ese ajuste: no identifica un CATE individual.
    """
    b = _cargar()
    abst = _abstencion_por_puerta(b, "heterogeneidad_estimada")
    if abst:
        return _salida_heterogeneidad(abst)
    est = b["estimacion"]
    modelo = est.get("modelo_individual")
    if modelo is None:
        return _salida_heterogeneidad({
            "estado": "abstencion",
            "motivo": "el bundle de esta versión no trae modelo_individual",
            "estado_puerta": _estado_puerta(b),
            "version": b["version"]})

    covariables = list(modelo["coeficientes"])
    faltan = [c for c in covariables if c not in perfil]
    if faltan:
        return _salida_heterogeneidad({
            "estado": "abstencion",
            "motivo": f"faltan covariables del perfil: {faltan}",
            "estado_puerta": _estado_puerta(b),
            "version": b["version"]})

    motivos = []
    for covariable, (lo, hi) in est["rangos_covariables"].items():
        valor = float(perfil[covariable])
        if valor < lo or valor > hi:
            motivos.append(f"{covariable}={valor:g} fuera de "
                           f"[{round(lo, 4)}, {round(hi, 4)}]")
    if motivos:
        return _salida_heterogeneidad({
            "estado": "abstencion",
            "motivo": "; ".join(motivos),
            "estado_puerta": _estado_puerta(b),
            "version": b["version"]})

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

    advertencias = []
    if max(abs(zj) for zj in z) > 2.5:
        advertencias.append(
            "Perfil en el borde del soporte: la proyección lineal extrapola "
            "y el IC subestima la incertidumbre.")

    r2 = float(modelo["r2"])
    discriminacion = ("muy baja" if r2 < 0.05 else
                      "baja" if r2 < 0.15 else "moderada")

    return _salida_heterogeneidad({
        "estado": "respuesta",
        "estimando": ("heterogeneidad estimada mediante proyección lineal del score "
                      "AIPW para este perfil; NO es un CATE individual identificado"),
        "proyeccion": round(float(tau), 1),
        "unidad": est["unidad"],
        "proyeccion_texto": (
            f"{_num(tau)} {est['unidad']} "
            f"(IC 95 %: {_num(tau - 1.96 * se)} a {_num(tau + 1.96 * se)})"),
        "ic95": [round(float(tau - 1.96 * se), 1), round(float(tau + 1.96 * se), 1)],
        "interpretacion": _lectura(tau, [tau - 1.96 * se, tau + 1.96 * se],
                                   individual=True, r2=r2),
        "que_cubre_el_ic": (
            "la incertidumbre condicional de la proyección lineal, dados el ajuste "
            "y los scores AIPW del bundle; NO identifica un CATE individual ni cubre "
            "el error de especificación lineal"),
        "ajuste_r2": round(r2, 3),
        "confianza_discriminacion": discriminacion,
        "n_entrenamiento": modelo["n"],
        "advertencias": advertencias,
        "estado_puerta": _estado_puerta(b),
        "sensibilidad": {"aplicable": False,
                         "motivo": ("la proyección describe heterogeneidad y no es un "
                                    "CATE individual identificado; usa /efecto para la "
                                    "sensibilidad poblacional")},
        "placebo": {"aplicable": False,
                    "motivo": ("el placebo aplica al ATE poblacional, no a una "
                               "proyección de heterogeneidad")},
        "identificacion": est.get("identificacion", {}),
        "limitaciones": b["tarjeta"].get("limitaciones", []),
        "version": b["version"],
    })


def efecto_individual(perfil: dict) -> dict:
    """Alias deprecado de heterogeneidad; conserva exactamente el mismo núcleo."""
    payload = heterogeneidad(perfil)
    payload["deprecacion"] = "alias deprecado; usa /heterogeneidad"
    payload["endpoint_recomendado"] = "/heterogeneidad"
    return payload


def efecto_lista_de_prueba() -> list[str]:
    """Auxiliar para el humo: las rutas que la prueba de humo ejercita."""
    return ["/salud", "/efecto", "/consulta", "/heterogeneidad", "/efecto_individual"]
