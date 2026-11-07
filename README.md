# prototipo_ml_causal

[![CI](https://github.com/jelincovil/prototipo_ml_causal/actions/workflows/ci.yml/badge.svg)](https://github.com/jelincovil/prototipo_ml_causal/actions/workflows/ci.yml)

Prototipo local de **inteligencia causal en producción**: estimación AIPW con
cross-fitting, identificación con DoWhy, sensibilidad (E-value), placebos,
registro versionado, monitor con puerta de cinco acciones y servicio FastAPI con
abstención cuando la puerta falla.

Escenarios **sintéticos** del benchmark `real/jobs` (estilo LaLonde/NSW) y
`real/ihdp` (estilo Hill 2011). Los nombres `real/*` son convención del
dataset; no son datos clínicos ni laborales reales.

> **No usar** para decisiones clínicas, laborales o de política pública.

## Inicio rápido

Requisitos: **Python 3.13**. Opcional: Graphviz (`dot`) para `make dag`.

```bash
git clone https://github.com/jelincovil/prototipo_ml_causal.git
cd prototipo_ml_causal
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
SIC_ESCENARIO=real/ihdp make demo
```

`make demo` ejecuta verificación de datos, estimación, registro, monitor y prueba
de humo del servicio.

## Comandos

```sh
make verificar                       # esquema, hashes de splits y pared
SIC_ESCENARIO=real/ihdp make demo    # flujo completo
make pruebas                         # asserts de sensibilidad, placebo y OLS
make dag                             # figuras DAG (Graphviz)
make evidencia                       # trazas y SHA256 del cierre
make servir                          # API en http://127.0.0.1:8000
make humo                            # contrato HTTP del servicio
```

Escenario por defecto: `real/jobs`. Para IHDP: `export SIC_ESCENARIO=real/ihdp`.

## API

| Ruta | Descripción |
|------|-------------|
| `GET /salud` | estado, versión, puerta |
| `GET /efecto` | ATE, IC, sensibilidad, placebo, identificación |
| `POST /consulta` | efecto en estrato o abstención fuera de soporte |
| `POST /efecto_individual` | proyección lineal del score AIPW |
| `GET /`, `GET /calcular` | formulario web |

## Evidencia reproducible

```sh
shasum -a 256 -c evidencia/SHA256SUMS
```

La carpeta `evidencia/` enlaza cada cifra del cierre con comando, salida y hash.

## Módulos

| Archivo | Rol |
|---------|-----|
| `datos.py` | esquema C-01, splits, pared sin `truth` |
| `estimacion.py` | AIPW, OLS, DoWhy, sensibilidad, placebo |
| `sensibilidad.py` | E-value, robustez, placebos |
| `registro.py` | tarjeta, manifiesto, champion |
| `monitor.py` | ventanas y puerta de producción |
| `servicio.py` / `servicio_core.py` | FastAPI y lógica de abstención |
| `humo.py` | prueba de humo |
| `pruebas_estimacion.py` | invariantes |

## Docker

```bash
docker build -t prototipo-ml-causal .
docker run --rm -p 8000:8000 prototipo-ml-causal
```

La imagen empaqueta el bundle en `artifacts/`; no incluye datos de entrenamiento.

## Documentación

- `pregunta_ihdp.md` — pregunta causal, supuestos y defensa (IHDP)
- `pregunta_jobs.md` — mismo marco para jobs
- `ENTREGA.md` — checklist de entrega formativa

## Origen

Desarrollado en el marco del curso *Sistema de Inteligencia Causal*; este
repositorio es una **copia pública autocontenida** del prototipo «Puente».
