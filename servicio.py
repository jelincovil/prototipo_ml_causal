"""servicio.py — FastAPI del prototipo (envoltorio fino de servicio_core).

Arranque:  uvicorn servicio:app --port 8000
Humo:      python humo.py

Cada ruta entrega JSON por defecto y un informe legible con `?formato=texto`.
La raíz `/` sirve un formulario para proyectar heterogeneidad en un perfil.
"""
from __future__ import annotations

import html

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

import servicio_core as nucleo

app = FastAPI(title="Puente — prototipo causal local (semana 4)")

ESTILO = """
body{font-family:-apple-system,Segoe UI,sans-serif;max-width:760px;margin:2rem auto;
     padding:0 1rem;color:#1f2933;background:#fbfbfd}
h1{font-size:1.3rem;margin-bottom:.2rem}
p.sub{color:#52606d;margin-top:0}
fieldset{border:1px solid #d9e2ec;border-radius:8px;padding:1rem;margin-top:1rem}
legend{padding:0 .4rem;color:#486581;font-size:.9rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:.6rem}
label{display:flex;flex-direction:column;font-size:.78rem;color:#334e68;gap:.2rem}
.rango{font-size:.68rem;color:#829ab1}
input{font:inherit;padding:.35rem .45rem;border:1px solid #bcccdc;border-radius:6px}
button{margin-top:1rem;font:inherit;padding:.55rem 1.1rem;border:0;border-radius:8px;
       background:#0e7490;color:#fff;cursor:pointer}
button:hover{background:#155e75}
pre{background:#0f172a;color:#e2e8f0;padding:1rem;border-radius:8px;
    white-space:pre-wrap;overflow-wrap:break-word;overflow-x:hidden;
    font-size:.85rem;line-height:1.55}
a{color:#0e7490}
.bad{background:#fde8e8;border-left:4px solid #c81e1e;padding:.7rem 1rem;border-radius:6px}
"""


def _responder(payload: dict, formato: str):
    if formato.lower() in ("texto", "txt", "plain"):
        return PlainTextResponse(nucleo.formatear(payload))
    return payload


@app.get("/", response_class=HTMLResponse)
def formulario() -> str:
    """Formulario para estimar heterogeneidad en un perfil (una covariable por campo)."""
    campos = nucleo.campos_formulario()
    aviso = "" if campos else (
        '<div class="bad">El champion no está disponible o no supera la verificación '
        'de integridad. El servicio se abstiene; consulta <a href="/salud">/salud</a>.</div>')
    controles = "\n".join(
        f'<label>{html.escape(nombre)}'
        f'<input name="{html.escape(nombre)}" type="number" step="any" '
        f'inputmode="decimal" value="{d["valor"]}" '
        f'min="{d["min"]}" max="{d["max"]}" '
        f'title="rango de entrenamiento: {d["min"]:.3f} a {d["max"]:.3f}" required>'
        f'<span class="rango">{d["min"]:.2f} … {d["max"]:.2f}</span></label>'
        for nombre, d in campos.items())
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Heterogeneidad por perfil — prototipo causal</title><style>{ESTILO}</style></head><body>
<h1>Heterogeneidad estimada para un perfil</h1>
<p class="sub">Ajusta las covariables (escala del escenario, ~N(0,1)) y pulsa
<strong>Estimar</strong>. El resultado es una proyección, no un CATE individual
identificado. Fuera del rango de entrenamiento la respuesta es abstención.</p>
{aviso}
<form action="/calcular" method="get">
  <fieldset><legend>{len(campos)} covariables</legend>
    <div class="grid">{controles}</div>
  </fieldset>
  <button type="submit">Estimar</button>
</form>
<p class="sub">API: <a href="/docs">/docs</a> ·
<code>POST /heterogeneidad</code> ·
<a href="/efecto?formato=texto">efecto poblacional</a></p>
</body></html>"""


@app.get("/calcular", response_class=HTMLResponse)
def calcular(request: Request) -> str:
    """Recibe el formulario y devuelve el informe del perfil."""
    campos = nucleo.campos_formulario()
    faltan = [c for c in campos if c not in request.query_params]
    if faltan:
        cuerpo = (f'<div class="bad">Faltan covariables: {html.escape(", ".join(faltan))}</div>')
    else:
        try:
            perfil = {c: float(request.query_params[c]) for c in campos}
        except ValueError:
            cuerpo = '<div class="bad">Algún valor no es numérico.</div>'
        else:
            payload = nucleo.heterogeneidad(perfil)
            cuerpo = f"<pre>{html.escape(nucleo.formatear(payload))}</pre>"
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Resultado — prototipo causal</title><style>{ESTILO}</style></head><body>
<h1>Resultado</h1>
{cuerpo}
<p class="sub"><a href="/">&larr; otro perfil</a> · <a href="/docs">/docs</a></p>
</body></html>"""


@app.get("/salud")
def salud() -> dict:
    return nucleo.salud()


@app.get("/efecto")
def efecto(formato: str = Query("json", description="json | texto")):
    """Efecto poblacional (ATE) con su IC, o su versión legible."""
    return _responder(nucleo.efecto(), formato)


@app.post("/consulta")
def consulta(perfil: dict, formato: str = Query("json", description="json | texto")):
    """Perfil: {age, educ, black, hispan, married, nodegree, re74, re75}."""
    return _responder(nucleo.consulta(perfil), formato)


@app.post("/heterogeneidad")
def heterogeneidad(perfil: dict,
                   formato: str = Query("json", description="json | texto")):
    """Proyección de heterogeneidad para un perfil; no identifica un CATE individual.

    Perfil: todas las covariables del escenario. Fuera del soporte de
    entrenamiento responde abstención (HTTP 200, sin proyección).
    """
    return _responder(nucleo.heterogeneidad(perfil), formato)


@app.post("/efecto_individual", deprecated=True)
def efecto_individual(perfil: dict,
                      formato: str = Query("json", description="json | texto")):
    """Alias deprecado de /heterogeneidad, con idéntico núcleo de respuesta."""
    return _responder(nucleo.efecto_individual(perfil), formato)
