# LEEME para un agente externo

**Alcance:** Prototipo local de estimación causal con AIPW, abstención fuera de soporte y monitoreo, con datos sintéticos. No es un sistema desplegado ni un producto clínico o laboral.

Estima un efecto promedio (ATE) con intervalo, lo publica como artefacto
versionado con hash y lo sirve por API. Los escenarios activos son
`synthetic/ihdp` y `synthetic/jobs`; las entradas históricas de la bitácora no
sustituyen la evidencia actual. La validación local descrita abajo corresponde a
IHDP y a un DGP ilustrativo propio: no revalida jobs, Docker ni los documentos.

---

## 1. Lee en este orden

| Orden | Archivo | Para qué |
|---|---|---|
| 1 | `docs/pregunta_jobs.md` · `docs/pregunta_ihdp.md` | qué se estima y bajo qué supuestos |
| 2 | `GUIA_CONSTRUCCION.md` | cómo está construido, bloque a bloque, con salidas esperadas |
| 3 | `BITACORA.md` | qué se decidió, por qué y con qué evidencia histórica |
| 4 | `data_benchmark_causal/.../datasets/manual_sistema_causal.typ` (o el `.pdf`) | manual de instalación, datos, método, API e interpretación |
| 5 | `datos.py` → `estimacion.py` → `registro.py` → `monitor.py` → `servicio_core.py` | el código, en el orden en que fluyen los datos |

`ENTREGA.md` describe el checklist del trabajo académico. Las instrucciones de
`docs/historico/` pertenecen al kit inicial y no sustituyen la guía actual del
`README.md`.

---

## 2. Qué hay dentro

```text
datos.py               esquema de roles, hashes de splits, "la pared"
estimacion.py          OLS, propensity, ESS, SMD, AIPW cross-fitting, estratos
sensibilidad.py        E-value, robustez OLS, Rosenbaum, cotas de Manski y placebos
registro.py            tarjeta, versión inmutable, manifiesto, promoción de champion
monitor.py             PSI, ventanas y puerta con acciones declaradas
servicio_core.py       bundle cacheado, /consulta y /heterogeneidad
servicio.py            FastAPI + formulario HTML + alias deprecado
humo.py                prueba de humo del servicio y de integridad
pruebas_estimacion.py  fórmulas, identificación DoWhy y contratos del bundle
cobertura.py           Monte Carlo opcional en un DGP ilustrativo propio
rutas.py               raíz del repo y escenario (SIC_ESCENARIO)
Makefile               verificar · estimar · registrar · ventanas · humo · demo
proyecto.ipynb         notebook conductor con salidas históricas
requirements.txt       dependencias fijadas con versiones exactas
artifacts/             artefactos JSON, versiones inmutables y alias champion
data_benchmark_causal/ dos escenarios sintéticos (ihdp y jobs) con metadatos
BASELINE.sha256        huella del kit original, antes de resolver los 22 TODOs
```

No se usan `pickle` ni `joblib`: los artefactos de estimación, registro, puerta,
sensibilidad y cobertura se representan como JSON.

---

## 3. Comprobación, cobertura y regeneración

Comprobaciones que no promueven una nueva versión:

```sh
python3.13 -m venv .venv_ci && . .venv_ci/bin/activate
python -m pip install -r requirements.txt
export SIC_ESCENARIO=synthetic/ihdp

make verificar
make pruebas
make humo
shasum -a 256 -c evidencia/SHA256SUMS
```

En la validación local conservada como evidencia `v0008`, las pruebas y el humo
quedaron en `PRUEBAS: OK` y `HUMO: OK`, con hashes correctos. Al revisar otro
entorno, hay que repetir las comprobaciones en lugar de dar por transferido ese
resultado.

Cobertura Monte Carlo ya ejecutada:

```sh
SIC_ESCENARIO=synthetic/ihdp .venv_ci/bin/python cobertura.py
```

La corrida usó `n = 500`, `R = 100` y semilla `20261111` para un DGP ilustrativo
propio. AIPW obtuvo cobertura 0,97 (error MC 0,01706), OLS 0,96 (error MC 0,01960)
e ingenuo 0,00 (error MC 0). AIPW queda a 0,02 del nominal 0,95 y no dentro de
±1 error MC, de modo que no se afirma calibración exacta. No mide cobertura en
IHDP/jobs ni demuestra identificación. Evidencia: `artifacts/cobertura.json` y
`evidencia/10_cobertura.txt`.

Regeneración del flujo (**modifica artefactos y champion**):

```sh
SIC_ESCENARIO=synthetic/ihdp make PYTHON=.venv_ci/bin/python demo
SIC_ESCENARIO=synthetic/ihdp make PYTHON=.venv_ci/bin/python evidencia
```

El flujo de evidencia generó y promovió históricamente **`v0008`**.
El champion actual, **`v0009`**, incorpora Rosenbaum y las interpretaciones separadas
del ATE y de la proyección de perfil; `v0001`–`v0008` permanecen intactas. No uses
`make demo` o `make evidencia` como simples comprobaciones de solo lectura ni
promuevas versiones nuevas solo por cambios documentales.

La estimación validada reporta diferencia cruda 10,3 (IC aproximado
[7,60; 13,05]), OLS 4,8 [3,8; 5,8] y AIPW 5,2 [3,9; 6,4]. Antes del trimming,
los diagnósticos OOF son rango [0,043; 0,916], solape 0,99777 (≈99,8 %, aunque la
CLI puede redondear 100 %) y ESS 332,2076/448 = 0,7415. Se recortó 1 unidad
(0,2232 %), de control (0,3891 % de los controles), y 0 tratadas; el SMD ponderado
OOF es 0,11 frente a 0,43 sin ponderar. Consulta `evidencia/02_estimacion.txt`.

---

## 4. Invariantes que no se pueden romper

1. **Nada de `truth_*.csv`, `y0`, `y1` ni `tau`** en entrenamiento, bundle o servicio.
2. `interventions.json` **contiene la verdad** (`ate`, `att`): no se usa para estimar,
   decidir ni calibrar umbrales.
3. El servicio **no lee CSV**: solo el bundle JSON del `champion`.
4. Abstención = **HTTP 200 sin número**, nunca un 4xx.
5. **Un artefacto, un escenario**: cambiar `SIC_ESCENARIO` exige regenerar y reiniciar.
   El servicio verifica alias y hashes al cargar; si no coinciden, se abstiene.
6. Los umbrales y el corte de heterogeneidad se declaran **antes** de ver resultados.
7. `POST /heterogeneidad` devuelve `proyeccion`, IC condicional y advertencias;
   nunca un CATE o efecto individual identificado. `diagnosticos_globales` separa
   el ATE, Rosenbaum, Manski y los placebos: son referencia poblacional, no medidas
   del perfil. `POST /efecto_individual` es un alias deprecado de la misma proyección.

---

## 5. Límites declarados (no son defectos ocultos)

- **Ignorabilidad no verificable con DoWhy/DAG.** El criterio backdoor actúa sobre
  el grafo declarado; no prueba ausencia de confusión no observada.
- Los rangos marginales usados para abstenerse **no garantizan soporte
  multivariable**; tampoco el rango de propensiones prueba positividad poblacional.
- La coincidencia ingenuo/OLS/AIPW **no prueba identificación**. La doble robustez
  no salva el estimador si fallan ambas piernas ni si fallan los supuestos causales.
- El E-value solo cuantifica confusión no observada bajo supuestos; no cubre error
  de especificación, falta de positividad ni violaciones de consistencia/SUTVA.
- Los umbrales del monitor son **convenciones iniciales**, no calibración universal.
  La sensibilidad de ±20 % con factores `.8`, `1` y `1.2` ya está implementada.
  En esta corrida produjo 0 cambios de acción fuera de la clasificación base, sin
  que ello constituya una calibración universal (`evidencia/05_puerta.txt`).
- Las dos piernas del AIPW son **lineales** (OLS por brazo y logística en los logits).
- La proyección de `/heterogeneidad` tiene discriminación limitada y un IC
  condicional al ajuste; no identifica un CATE individual ni cubre todo el error
  de especificación.
- Sin autenticación ni TLS. La integridad se verifica al cargar el bundle: hay
  que reiniciar el servicio después de cambiar el champion.
- Sin learners no lineales ni *repeated cross-fitting*: eso queda fuera del alcance.

---

## 6. Si algo no cuadra

`BITACORA.md` §11–§16 documenta los fallos históricos, su corrección y la
actualización de alcance; §17 registra la validación local real de `v0008`.
`GUIA_CONSTRUCCION.md`, sección «Errores frecuentes», relaciona fallos con su
causa y corrección. No cambies el champion ni ejecutes los flujos de regeneración
solo para resolver una discrepancia documental.
