# Proyecto — «Puente» (semana 4)

Repositorio público del prototipo: **[github.com/jelincovil/prototipo_ml_causal](https://github.com/jelincovil/prototipo_ml_causal)**.

**Acceso para auditoría (sin cuenta ni token):** [índice del código fuente y enlaces de texto directo](AUDITORIA.md) · [descargar ZIP](https://codeload.github.com/jelincovil/prototipo_ml_causal/zip/refs/heads/main).

**Alcance:** Prototipo local de estimación causal con AIPW, abstención fuera de soporte y monitoreo, con datos sintéticos. No es un sistema desplegado ni un producto clínico o laboral.

Usa los escenarios `synthetic/ihdp` y `synthetic/jobs`. Estima el ATE con AIPW y
cross-fitting, declara los supuestos de identificación, acompaña el resultado con
sensibilidad y placebos, y lo publica mediante un registro versionado, un monitor
y una API con abstención. No usar para decisiones clínicas, laborales o de
política pública.

## Supuestos y consecuencias

| Supuesto | Cómo se verifica | Qué pasa si falla |
|---|---|---|
| **Ignorabilidad condicional** | No se verifica con los datos observados: se defiende mediante el diseño/DGP y se explora con placebos y análisis de sensibilidad. | El ATE ajustado puede quedar confundido; AIPW, OLS y la diferencia ingenua no recuperan por sí solos identificación causal. |
| **Positividad / soporte común** | Se examinan propensiones, ESS y solapamiento, se someten ventanas a estrés y el servicio se abstiene ante perfiles fuera de soporte. | No hay ATE identificado para toda la población objetivo sin restricciones o información adicional; corresponde abstenerse o acotar, no extrapolar. |
| **Consistencia / SUTVA** | No tiene un chequeo empírico directo: exige tratamiento bien definido, una sola versión relevante y ausencia de interferencia, justificados por el diseño. | El efecto estimado puede no corresponder a una intervención bien definida; cambian los resultados potenciales y el estimando. |
| **Nuisance models** (resultado y propensión) | Cross-fitting, diagnósticos de ajuste, balance y comparación con OLS/estimación ingenua; la doble robustez exige que al menos una pierna esté bien especificada, además de los supuestos causales. | Si ambas piernas fallan, AIPW puede sesgarse y su IC puede resultar inadecuado; cross-fitting no corrige una mala especificación. |

### Qué no demuestran los diagnósticos

- **DoWhy/DAG no verifica ignorabilidad.** El DAG y la coincidencia con un
  `valid_adjustment_set` comprueban coherencia algebraica con el grafo declarado,
  no la ausencia de confusores no observados ni la validez empírica del grafo.
- **Los rangos marginales no garantizan soporte multivariable.** Que cada
  covariable esté dentro de su rango de entrenamiento no asegura que el vector
  completo tenga tratados y controles comparables.
- **La coincidencia entre estimación ingenua, OLS y AIPW no prueba
  identificación.** Es, como mucho, un diagnóstico de estabilidad entre
  estimadores; los tres pueden compartir sesgo de confusión o especificación.
- **El E-value solo cuantifica confusión no observada bajo sus supuestos.** No
  cubre errores de especificación, fallos de positividad ni violaciones de
  consistencia/SUTVA, y su aproximación para resultado continuo no es una RR literal.
- **Los umbrales del monitor son convenciones iniciales**, no una calibración
  universal. El monitor incluye un análisis de sensibilidad de ±20 % con
  factores `.8`, `1` y `1.2`. En la corrida conservada hubo **0 cambios de
  acción** fuera de la clasificación base; esa estabilidad local tampoco prueba
  identificación.

### Cobertura Monte Carlo

`make cobertura` genera `artifacts/cobertura.json` para un **DGP ilustrativo
propio**, con `n = 500`, `R = 100` y semilla `20261111`. La corrida conservada
obtuvo coberturas IC95 de **0,97 (AIPW)**, **0,96 (OLS ajustado)** y **0,00
(ingenuo)**, con errores Monte Carlo de 0,01706, 0,01960 y 0. El AIPW difiere
0,02 del nominal y no queda dentro de ±1 error Monte Carlo: no es una
calibración exacta. Estas cifras solo se refieren a ese DGP, no a IHDP/jobs ni
a datos reales.

## Empezar

Requisitos: **Python 3.13**. Las dependencias tienen versiones exactas fijadas en
`requirements.txt`. Graphviz (`dot`) solo se necesita para `make dag`; Typst, para
`make cierre`.

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export SIC_ESCENARIO=synthetic/ihdp
```

Si ya tienes un entorno con esas dependencias, actívalo y úsalo en lugar de
crear `.venv`.

## Comprobar el paquete existente

Con el entorno y `SIC_ESCENARIO=synthetic/ihdp` activos:

```sh
make verificar    # esquema, hashes de splits y separación de la verdad
make pruebas      # fórmulas, identificación, sensibilidad y contratos del servicio
make humo         # carga e integridad del champion; respuestas y abstenciones
shasum -a 256 -c evidencia/SHA256SUMS
```

Estas comprobaciones no cambian el champion. Resultado esperado: `PRUEBAS: OK`,
`HUMO: OK` y todos los hashes correctos.

## Regenerar el flujo

```sh
make demo         # datos → estimación → registro → monitor → humo
make evidencia    # además reconstruye las salidas y hashes de evidencia/
make pruebas      # conviene ejecutarlo después de regenerar
```

**Atención:** `make demo` y `make evidencia` crean una nueva versión inmutable
`vNNNN` y promueven un nuevo champion. No son comandos de solo lectura.
`make evidencia` también sobrescribe los archivos generados dentro de `evidencia/`.
El champion conservado es **`v0008`**; las versiones históricas **`v0001`–`v0007`**
permanecen intactas. Editar documentación o hashes de `evidencia/` no promueve
una versión nueva.

Otros objetivos útiles:

```sh
make dag          # regenera los SVG con Graphviz
make cierre       # compila dataset_y_metodo.typ a PDF
make cobertura    # opcional: Monte Carlo del DGP propio; escribe cobertura.json
make limpiar      # borra TODO artifacts/, incluidos champion y versiones
```

`make limpiar` no es una limpieza rutinaria de cachés: elimina el resultado completo.

## Levantar el servicio

Con el entorno activado:

```sh
export SIC_ESCENARIO=synthetic/ihdp
make servir
```

Equivalente manual, con el entorno activado:

```sh
SIC_ESCENARIO=synthetic/ihdp uvicorn servicio:app --host 127.0.0.1 --port 8000
```

Abrir:

- <http://127.0.0.1:8000/> — formulario para consultar un perfil.
- <http://127.0.0.1:8000/efecto> — ATE e incertidumbre del champion.
- <http://127.0.0.1:8000/salud> — versión, puerta, integridad e identificación.
- <http://127.0.0.1:8000/docs> — documentación interactiva de FastAPI.

Pulsar **Ctrl-C** para detenerlo. Reiniciar después de cambiar de escenario o de
champion: el bundle se carga en memoria al arrancar.

## Qué devuelve la API

- `GET /efecto` — ATE, IC, identificación backdoor/DoWhy, E-value, valor de
  robustez, cotas de Manski y resultados de los placebos, todos sujetos a los
  límites de interpretación declarados arriba.
- `POST /consulta` — media de un estrato declarado con IC; no es un CATE.
- `POST /heterogeneidad` — devuelve `proyeccion`, un IC **condicional al ajuste**
  y advertencias; nunca un CATE o efecto individual identificado.
- `POST /efecto_individual` — alias deprecado de `/heterogeneidad`, conservado por
  compatibilidad y con la misma advertencia causal.
- `GET /salud` — estado del servicio, versión, puerta, integridad del manifiesto y
  resumen de identificación, sensibilidad y placebos.
- `GET /` y `GET /calcular` — formulario web.

El servicio no lee CSV: usa únicamente el bundle del champion. Si la integridad
falla, la puerta de producción es `falla` o un perfil queda fuera de soporte, se
abstiene sin inventar un número. Los artefactos se serializan como **JSON**; no se
usan `pickle` ni `joblib`.

## Orden de lectura

1. [`docs/pregunta_ihdp.md`](docs/pregunta_ihdp.md) — pregunta, estimando, supuestos, resultados históricos y límites.
2. [`data_benchmark_causal/causal_benchmark_synthetic/datasets/dataset_y_metodo.pdf`](data_benchmark_causal/causal_benchmark_synthetic/datasets/dataset_y_metodo.pdf)
   — explicación completa; el fuente editable es el `.typ` vecino.
3. `datos.py` → `estimacion.py` → `registro.py` → `monitor.py` →
   `servicio_core.py` → `servicio.py` — recorrido del dato a la API.
4. [`evidencia/README.md`](evidencia/README.md) — trazabilidad de comandos, salidas y hashes.
5. [`docs/GUIA_CONSTRUCCION.md`](docs/GUIA_CONSTRUCCION.md) y
   [`docs/LEEME_AGENTE.md`](docs/LEEME_AGENTE.md) — construcción y operación.

## Estructura breve

```text
rutas.py                 raíz del proyecto y selección de escenario
datos.py                 esquema, hashes de splits y pared de verdad
estimacion.py            AIPW, OLS, diagnósticos e identificación DoWhy
sensibilidad.py          E-value, robustez, Manski y placebos
registro.py              tarjeta, manifiesto y promoción segura
monitor.py               ventanas, deriva y puerta
servicio_core.py         carga del bundle, integridad y contratos de respuesta
servicio.py              endpoints FastAPI y formulario
pruebas_estimacion.py    pruebas de fórmulas e invariantes
humo.py                  prueba de humo del servicio
cobertura.py             simulación opcional en el DGP ilustrativo propio
artifacts/               artefactos JSON, champion v0008 y versiones históricas
evidencia/               salidas y hashes del cierre
data_benchmark_causal/   escenarios sintéticos y documentación
docs/                    guía, bitácora, preguntas causales y material docente
docs/historico/          material original y archivos auxiliares no operativos
```

La raíz conserva el código fuente y el notebook; `README.md` es la entrada y
`ENTREGA.md` registra el estado académico. Los escenarios y sus documentos están en
`data_benchmark_causal/`; los resultados versionados en `artifacts/`; y las salidas
y hashes de verificación en `evidencia/`. El material histórico no operativo está
separado en `docs/historico/`; no interviene en la ejecución del prototipo.

Las versiones de `artifacts/registro/` son inmutables. Los entornos `.venv*` y los
cachés `__pycache__/` son locales y regenerables; no forman parte del entregable.
