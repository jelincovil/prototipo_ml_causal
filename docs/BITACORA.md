# Bitácora de construcción — «Puente» (semana 4)

Registro histórico del trabajo sobre el kit: qué se hizo, por qué, y la evidencia que lo
respaldó en aquel momento. Convención de cada entrada: **qué · por qué · evidencia**.
Las cifras, versiones `v0001`, pruebas de contenedor y salidas de esta bitácora no sustituyen
una validación nueva ni describen por sí solas el contrato activo; véase §16 y `README.md`.

> **Alcance activo:** Prototipo local de estimación causal con AIPW, abstención fuera de soporte y monitoreo, con datos sintéticos. No es un sistema desplegado ni un producto clínico o laboral.
>
> Los escenarios activos son `synthetic/ihdp` y `synthetic/jobs`. Los artefactos se
> serializan como JSON, no `pickle`/`joblib`, y las dependencias quedan fijadas con
> versiones exactas en `requirements.txt`.

---

## 1. Estado de partida

| Pieza | Valor |
|---|---|
| Repositorio | `sistema-inteligencia-causal-estudiante-main` |
| Rama de trabajo | `semana4/proyecto` (desde `main`, que sigue a `origin/main`) |
| Commit baseline | `78486ad` — 33 archivos, 6401 líneas |
| Tag anotado | `semana4-kit-original` |
| Manifiesto | `BASELINE.sha256` — 32 archivos |
| Verificación del manifiesto | 32/32 `OK` |
| `git diff semana4-kit-original` | vacío (el árbol **es** el kit distribuido) |
| Arranque del kit | `make verificar` falla con `TODO-1` (correcto) |

Evidencia del estado de arranque:

```text
Esquema C-01: EsquemaCausal(tratamiento='treatment', resultado='re78',
             covariables=('age','educ','black','hispan','married','nodegree','re74','re75'))
  File "datos.py", line 35, in validar
    raise NotImplementedError("TODO-1 pendiente de completar")
NotImplementedError: TODO-1 pendiente de completar
make: *** [verificar] Error 1
```

Copia externa (capa 3 del protocolo): `tar.gz` generado desde el tag,
sha256 `141760578f6bf87ccf744d08284c0fa689eee8d51c3c7a80ba366b92567fbfd1`,
**pendiente de mover** de `/tmp` a `~/backups/` (el sandbox del agente no escribe fuera del proyecto).

Cómo comprobar el baseline en cualquier momento:

```sh
git diff --stat semana4-kit-original          # cambios respecto al original
git worktree add /tmp/kit-original semana4-kit-original   # árbol prístino aparte
git show semana4-kit-original:07_docencia/semana_4_proyecto/datos.py
```

`BASELINE.sha256` es la huella del **kit original**: verifica el árbol prístino, no el de
trabajo. Ejecutado sobre el directorio de trabajo marca como `FAILED` exactamente los
archivos que se tocaron — eso es lo que documenta, no un error:

```sh
cd /tmp/kit-original/07_docencia/semana_4_proyecto && shasum -a 256 -c BASELINE.sha256
# 32/32 OK
```

---

## 2. Entorno

| Componente | Valor |
|---|---|
| Env | `temp_causal_env` (`/opt/homebrew/Caskroom/miniforge/base/envs/temp_causal_env`) |
| Python | 3.13.18 |
| numpy / scipy | 2.3.5 / 1.17.0 |
| fastapi / starlette / uvicorn | 0.115.12 / 0.46.2 / 0.34.0 |
| httpx / matplotlib / ipykernel | 0.28.1 / 3.11.2 / 7.0.0 |

Decisiones:

- **No se crea `.venv` propio**: el env anterior ya cubre `requirements.txt` completo
  (incluido `fastapi`, que es lo único que falta en `causal_env` y en miniforge base).
- **Kernel del notebook**: el `.ipynb` pide `sic-estudiante`, que no estaba registrado.
  Como las celdas `!make` heredan el `PATH` del kernel, el kernel determina qué
  `python3` ejecuta los scripts. Quedó registrado (un puntero, no una instalación):

```sh
/opt/homebrew/Caskroom/miniforge/base/envs/temp_causal_env/bin/python \
  -m ipykernel install --user --name sic-estudiante \
  --display-name "Python (SIC estudiante)"
```

Ejecutar siempre con ese env al frente del `PATH`:

```sh
PATH=/opt/homebrew/Caskroom/miniforge/base/envs/temp_causal_env/bin:/usr/bin:/bin make verificar
```

---

## 3. Datos del escenario (lo que el kit entrega)

| | `synthetic/jobs` (clase) | `synthetic/ihdp` (entrega) |
|---|---|---|
| Unidades (train / val / test) | 1033 / 344 / 345 | 448 / 149 / 150 |
| Tratados en train | 262 | 191 (42,7 %) |
| Resultado | `re78` (USD 1978) | `outcome` |
| Covariables | 8 | 25 |
| `observed_train.csv` sha256 | `cd5a772e…5d7ae2` (== `splits.json`) | `9af86718…` (== `splits.json`) |
| `truth_*.csv` | no existe (la pared) | no existe (la pared) |

---

## 4. Estado de los bloques

| Bloque | TODOs | Archivo | Estado |
|---|---|---|---|
| 2 · roles y pared | 1, 2, 3 | `datos.py` | cerrado (checkpoint 1 en verde) |
| 3 · efecto e incertidumbre | 4–8, 21, 22 | `estimacion.py` | cerrado (checkpoint 2 en verde) |
| 4 · tarjeta y registro | 9–13 | `registro.py` | cerrado (checkpoint 3 en verde) |
| 5 · ventanas y puerta | 14–18 | `monitor.py` | cerrado (checkpoint 4 en verde) |
| 6 · servicio | 19, 20 | `servicio_core.py` | cerrado (checkpoint 5 en verde) |
| 7 · adaptación | — | esquema, corte, ventanas, umbrales | cerrado (demo ihdp en verde) |

Cada bloque se cierra cuando su checkpoint coincide con la salida esperada del
notebook **y** queda registrado aquí con su evidencia.

---

## 5. Entradas por bloque

**Contexto temporal:** esta sección conserva la construcción original y sus
diagnósticos **previos a los análisis OOF**. Sus cifras no son el estado actual de
`v0008`; la validación local posterior está en §17.

### Bloque 2 — `datos.py` (TODO-1…3)

- **Qué:** `validar` rechaza con tres `if` que nombran la columna culpable (ausente en
  los datos, asignada a más de un rol, tratamiento sin variación); `verificar_splits`
  recomputa el SHA-256 de cada partición y lo compara con `splits.json`;
  `comprobar_pared` traduce el `FileNotFoundError` de `truth_train.csv` en confirmación
  y lanza `RuntimeError` si el archivo apareciera.
- **Por qué:** C-01 exige un rol único por columna; el chequeo de doble rol se hace a
  nivel de **esquema** (`EsquemaCausal.columnas()`), porque el error real es declarar
  `re78` como resultado *y* covariable, o `treatment` como resultado. C-10 exige no
  confiar en lo declarado: el hash se recomputa, no se lee. La pared no es una
  convención: su ausencia se comprueba con código, y si alguien reintroduce la verdad
  en el paquete el programa falla en vez de seguir.
- **Evidencia:** checkpoint 1 idéntico a la salida esperada del notebook (3 hashes `OK`,
  `n = 1033`, `tratados = 262`, pared OK). Pruebas negativas:

```text
columna ausente       -> columna(s) del esquema ausentes en los datos: ['educ','hispan','married','nodegree','re74','re75']
doble rol             -> columna(s) con más de un rol: ['re78']
tratamiento constante -> el tratamiento 'treatment' no varía en los datos
caso válido           -> OK
```

```text
$ make verificar
esquema valida contra observed_train: OK (n = 1033, tratados = 262)
  train        hash OK  (1033 filas, semilla 20240701)
  validation   hash OK  (344 filas, semilla 20240701)
  test         hash OK  (345 filas, semilla 20240701)
  pared OK: truth_train.csv no existe en el paquete (reservado)
```

### Bloque 3 — `estimacion.py` (TODO-4…8, 21, 22)

- **Qué:** OLS con SE clásico (`sigma2 * (M'M)⁻¹[1,1]`); logística por BFGS para el
  propensity; ESS de Kish con `e` recortada a `[1e-6, 1-1e-6]`; SMD con desviación
  común; trampa `score_post` (0,6·Y + 0,4·D + ruido N(0,500)); **AIPW con cross-fitting**
  K=5 (outcome por brazo y propensity ajustados fuera del fold que predicen, trimming
  `[0,05, 0,95]`, score = influence function del ATE); estratos `nodegree` con su IC.
- **Por qué:** dos piernas estimadas fuera de muestra son la exigencia del Cap. 9:
  ningún nuisance ve a la unidad que predice. El trimming es una decisión **declarada**,
  no un ajuste a posteriori. El estrato promedia scores AIPW: es heterogeneidad
  sugerida, no un CATE, y su IC se declara como tal.
- **Evidencia:** salida idéntica a la esperada del notebook:

```text
diferencia cruda = 1600.8 USD
ATE OLS (8 controles) = 1596.0 | SE = 301.6 | IC95 = [1004.8, 2187.3]
AIPW cross-fitting K=5 = 1638.6 | SE = 325.0 | IC95 = [1001.6, 2275.7]
trampa score_post      = 172.4  <- el coeficiente se vació
nodegree=1 (n=568): 1060.1 IC95 [233.1, 1887.2]
nodegree=0 (n=465): 2345.2 IC95 [1356.9, 3333.4]
ESS = 729 (0.71) | rango e = [0.092, 0.530] | solapamiento = 100% | SMD máx = 0.19
```

### Bloque 4 — `registro.py` (TODO-9…13)

- **Qué:** tarjeta con los 7 campos de C-09 (supuestos clasificados
  `observable`/`no_observable`, umbrales 0,25/0,25/0,50, heterogeneidad declarada);
  validación de la tarjeta; manifiesto con `version`, `dataset_sha256`, `puerta` y hash
  de cada JSON; `verificar_integridad` que recomputa; promoción atómica
  (`champion.tmp` → `replace`), que rechaza `falla` y `alerta` sin aceptación explícita.
- **Por qué:** la afirmación publicada se refiere a un sujeto con hash: si el hash no
  coincide, la versión no es la misma. La versión es inmutable (nunca se edita en
  sitio) y la promoción es un rename atómico: no hay estado intermedio.
- **Evidencia:**

```text
registrada v0001 | integridad: OK
mutación detectada: SÍ (hash distinto del manifiesto -> bloqueado)
champion -> v0001
champion resuelve a: v0001
```

### Bloque 5 — `monitor.py` (TODO-14…18)

- **Qué:** PSI con deciles de la referencia como cortes y `clip` en 1e-4; ventana sana
  (submuestra de 700 sin reemplazo); deriva (`age + 10` sobre copia); positividad
  (tratados con `re74 > p75`, controles con `re74 < p25`); puerta con prioridad
  `falla` (soporte) > `alerta` (PSI o balance).
- **Por qué:** el soporte es condición de identificación, no de calidad: si se rompe,
  no hay número que reportar. La deriva y el desbalance son señales de proceso
  (revisar antes de reentrenar), no fallos del estimando. La puerta nombra la
  covariable culpable para que la alerta sea accionable. Los umbrales son
  convenciones iniciales, no calibración universal. En aquella etapa quedó prevista
  una sensibilidad de ±20 % con factores `.8`, `1` y `1.2`; su implementación y
  validación posterior se documentan en §17.
- **Evidencia:**

```text
[sana        ] pasa   | PSI máx 0.005 | SMD 0.21 | ESS/n 0.69 | solape 100%
[deriva      ] alerta | PSI máx 1.347 | SMD 0.19 | ESS/n 0.71 | solape 100%
              - deriva: PSI de age = 1.35 (umbral 0.25)
[positividad ] falla  | PSI máx 3.237 | SMD 5.24 | ESS/n 1.0  | solape 0%
              - solapamiento roto: 0% de unidades con e en [0.05, 0.95] (mínimo 50%)
```

### Bloque 6 — `servicio_core.py` (TODO-19…20)

- **Qué:** carga del bundle `champion` (estimación + tarjeta, cacheada, sin leer CSV);
  `/consulta` devuelve el efecto del **estrato** declarado y, fuera del rango de
  entrenamiento de cualquier covariable, se abstiene con HTTP 200 y sin ningún número.
- **Por qué:** abstención de primera clase: «no sé» es una respuesta válida y no un
  error 4xx/5xx. El servicio declara **qué cubre** su intervalo (media del estrato, no
  ATE ni efecto individual) porque el mismo endpoint podría sugerir lo contrario.
- **Corrección fuera de los TODOs (declarada):** `efecto()` servía `ate_ols`/`ic95`
  mientras la tarjeta declara el AIPW como estimador principal y el notebook espera
  `1638.6`. Se cambió a `ate_aipw`/`ic_aipw` y se añadió `estimador` a la respuesta.
  Es el hallazgo 2, resuelto aquí.
- **Evidencia:**

```text
/salud: 200 {'estado': 'ok', 'version': 'v0001', ...}
/efecto: 200 efecto=1638.6 ic95=[1001.6, 2275.7] version=v0001
/consulta dentro: 200 estado=respuesta efecto=1060.1
/consulta fuera (age=99): 200 estado=abstencion motivo=age=99 fuera de [18.0, 54.0] (sin número)
determinismo: dos llamadas idénticas -> iguales
HUMO: OK
```

---

## 6. Hallazgos sobre el kit (a resolver o declarar en la entrega)

1. **La pared tiene un hueco**: `interventions.json` incluye `ate`, `att` y
   `tau_summary` (media, desviación y cuantiles del efecto unitario) en ambos
   escenarios. La verdad poblacional viaja en el paquete: la regla «no se usa para
   estimar ni calibrar» es disciplina declarada, no garantía del sistema de archivos.
2. **`/efecto` publicaba el OLS, no el AIPW**: `estimar()` guarda `ate_ols`/`ic95` y
   `ate_aipw`/`ic_aipw` por separado; `servicio_core.efecto()` devolvía los primeros
   mientras la tarjeta declara el AIPW como principal. **Resuelto** en el bloque 6
   (sirve `ate_aipw`/`ic_aipw` y declara `estimador`); ver evidencia allí.
3. **`smd` del monitor mide balance interno de la ventana**, no deriva contra
   `train`: por eso `deriva` (edad +10 en ambos brazos) solo la detecta el PSI.
4. **ESS/n ≈ 1 no es buena señal** en la ventana `positividad`: con asignación casi
   determinista, los pesos son casi constantes dentro de cada brazo. La señal que
   rompe la puerta es el solapamiento.
5. **`requirements.txt` no cubre la experiencia del notebook** (faltan `matplotlib`
   y `ipykernel`/`jupyter`, que sí usa la celda del gráfico y el kernel).
6. **`verificar_integridad` no se invoca al cargar el bundle**: el servicio confía en
   el `champion` sin recomputar hashes, aunque el discurso del prototipo sea
   «todo se afirma sobre artefactos con hash».
7. **Partes cableadas a `jobs`** al adaptar a `ihdp`: `EsquemaCausal`, el corte de
   `estratos_nodegree`, `ventana_deriva` (`age`), `ventana_positividad` (`re74`),
   `humo.py` (perfil con `age`/`nodegree`/`re74`) y el texto de `/efecto`
   («USD de 1978»).

---

## 7. Reproducción

```sh
# flujo completo (el criterio de la rúbrica)
make demo

# el mismo flujo sobre la entrega
SIC_ESCENARIO=synthetic/ihdp make demo

# equivalencias si no hay make
python3 datos.py && python3 estimacion.py && python3 registro.py \
  && python3 monitor.py && python3 humo.py
```

`artifacts/` es generado (`make limpiar` lo borra) y se versiona al cerrar la
entrega, porque `ENTREGA.md` lo exige. Estos comandos reproducen el flujo histórico;
no son comprobaciones de solo lectura. Después, la validación documentada en §17
generó y promovió **`v0008`**, champion actual, con `v0001`–`v0007` intactas.
Esta actualización documental no promueve versiones nuevas.

> **Acoplamiento a tener en cuenta:** el servicio lee el `champion` del registro, que
> pertenece a un escenario. `SIC_ESCENARIO` y los artefactos deben coincidir; si no,
> `humo` falla con una abstención por falta de la covariable del corte. No es un bug:
> es el bundle de otro escenario.

---

## 8. Adaptación histórica a `synthetic/ihdp` (entrega)

**Decisión de diseño:** la adaptación es **por escenario** (`SIC_ESCENARIO`), no un
reemplazo destructivo. `COVARIABLES`/`RESULTADO` en `datos.py`, `CORTES` en
`estimacion.py`, `CONFIG` en `monitor.py` y `UMBRALES` en `registro.py` seleccionan la
configuración. Motivo: el notebook exige los cinco checkpoints de `jobs` **y** la
tarea sobre `ihdp`; con un reemplazo, `jobs` dejaría de reproducirse. Verificado: tras
la refactorización, `make demo` sobre `jobs` devuelve exactamente los mismos números.

### 8.1 Esquema

- `resultado = "outcome"`, `tratamiento = "treatment"`, **25 covariables** tomadas de
  `identification.json` (`bw … was`). `n = 448` en train, 191 tratados (42,7 %).
- Prefijos con punto (`b.head`, `mom.lths`, `b.marr`) se copian literalmente: son los
  nombres del CSV.

### 8.2 Corte de heterogeneidad (declarado antes de mirar efectos)

- **Corte:** `bw` (nombre inspirado en peso al nacer, pero covariable sintética) dicotomizado en la **mediana de train** (`−0,0133`).
- **Regla histórica:** `bw` se interpretó por su nombre inspirado en peso al nacer,
  aunque aquí es una covariable simulada y no una medida clínica; la mediana preserva
  tamaño en ambas hojas y **no** se eligió por ganancia de varianza. Queda escrito en
  la tarjeta (`heterogeneidad.regla`) y el servicio lo usa para asignar el estrato.

### 8.3 Umbrales históricos (convenciones iniciales, con justificación)

| Umbral | jobs | ihdp | Justificación |
|---|---|---|---|
| `solape_min` | 0,50 | **0,30** | Con 25 covariables y P(D=1)=0,43 puede estrecharse el soporte; en esta corrida histórica se consideró demasiado exigente 0,50 y se fijó 0,30 como convención inicial. Medido: sana 100 %, positividad 0 % → discrimina en esas ventanas. |
| `smd_max` | 0,25 | **0,50** | El máximo sobre 25 SMD tiene más ruido: EE(SMD) ≈ √(1/191 + 1/257) ≈ 0,096; el máximo esperado de 25 ≈ 3–4 EE ≈ 0,3–0,4. Medido: train 0,43 (por debajo), positividad 5,16 (muy por encima). |
| `psi_alerta` | 0,25 | **0,25** | Umbral estándar de industria (0,10 moderado, 0,25 significativo) y la deriva sintética cae muy por encima. |

Estas decisiones son convenciones iniciales del ejercicio, no calibración universal.
En esta etapa histórica se previó una rejilla de sensibilidad ±20 % (`.8`, `1`,
`1.2`). La rejilla ya implementada y sus 0 cambios de acción en la corrida actual se
registran en §17, sin reinterpretar como actuales las cifras históricas anteriores.

### 8.4 Ventanas

- **Sana:** 300 de 448 (≈2/3, mismo criterio que 700 de 1033 en `jobs`).
- **Deriva:** `bw + 1,0` (las covariables de IHDP vienen estandarizadas, así que +1 ≈
  una desviación estándar) → PSI 0,88 → **alerta**.
- **Positividad:** eje `bw`, por ser la covariable con mayor |SMD| de tratamiento en
  train (0,43): es la que gobierna la asignación. Tratados con `bw > p75` y controles
  con `bw < p25` → 140 unidades, solape 0 % → **falla**. Criterio de **diseño** de la
  ventana, no resultado del estimador.

### 8.5 Trampa `score_post`

El ruido estaba calibrado en dólares (σ = 500). En la escala de `outcome` eso aplastaba
la señal y la trampa **no** colapsaba (4,8 ≈ OLS). Se reescala por escenario
(σ = 1,0 punto) y vuelve a enseñar lo que debe: **−0,1**, el coeficiente se vacía.

### 8.6 Números históricos de `ihdp`

Esta tabla reproduce la corrida histórica entonces registrada, **anterior a los
diagnósticos OOF**. Sus cifras no describen el estado actual de `v0008` ni resultados
de cobertura Monte Carlo; esos hechos validados se consignan aparte en §17.

| Pieza | Resultado histórico |
|---|---|
| Diferencia cruda (train) | 10,3 puntos |
| ATE OLS + IC95 | 4,8 [3,8; 5,8] (SE 0,5) |
| **ATE AIPW (cross-fitting) + IC95** | **5,2 [3,9; 6,4]** (SE 0,6) |
| ESS / n y rango de ê | 388 (0,87) · [0,071; 0,887] · solape 100 % |
| Estrato `bw` alto (> mediana) | 7,2 [5,5; 8,8] (n = 224) |
| Estrato `bw` bajo (≤ mediana) | 3,2 [1,4; 4,9] (n = 224) |
| ¿Se solapan los intervalos? | **No** (7,2 vs 3,2; IC disjuntos) |
| Ventana sana | `pasa` (PSI 0,02 · SMD 0,33 · solape 100 %) |
| Ventana deriva | `alerta` — PSI de `bw` = 0,88 |
| Ventana positividad | `falla` — solape 0 % (mínimo 30 %) |
| Humo | `/efecto` 5,2 [3,9; 6,4] · `/consulta` 7,2 · fuera → abstención 200 |

La referencia del DGP (~3,92) no se usó para estimar, decidir ni calibrar; solo se
compara al final: el IC del AIPW la contiene. La pared se mantiene.

### 8.7 Artefactos de la entrega

`artifacts/estimacion.json` y `artifacts/registro/v0001/` (`estimacion.json`,
`tarjeta.json`, `manifest.json`) + `champion` → `v0001`, generados con
`SIC_ESCENARIO=synthetic/ihdp make demo` desde cero (`make limpiar` previo). Versión
inmutable: no se edita, se audita.

---

## 9. Notebook ejecutado

**Qué:** `proyecto.ipynb` ejecutado de punta a punta (13 celdas de código, 0 errores,
5 checkpoints en verde, gráfico PNG embebido) y con las celdas de respuesta rellenas:
- sección 5: las 3 respuestas de ventanas;
- sección 7: tabla de números de `ihdp` + reglas de la tarea cumplidas;
- sección 8: las 5 respuestas de cierre;
- sección 0: nota de que el fallo inicial con `TODO-1` quedó registrado aquí (§1) y en
  el tag `semana4-kit-original`.

**Por qué así:** los checkpoints del notebook corren sobre `synthetic/jobs` (el escenario
por defecto) y la sección 7 documenta `ihdp`; los artefactos que se entregan son los de
`ihdp`. Para que ambas cosas convivan:

1. `make limpiar` antes de ejecutar (registro vacío → los checkpoints crean `v0001` de
   `jobs`).
2. Ejecución con el env correcto: `nbconvert` solo existe en `/usr/bin/python3`, así que
   se lanzó desde ahí con un **kernelspec temporal** dentro del proyecto
   (`JUPYTER_PATH=.tmp_notebook/jupyter`, kernel `sic-estudiante` apuntando a
   `temp_causal_env`). No se escribió nada en `~/Library/Jupyter`.
3. Al terminar, se regeneraron los artefactos de `ihdp` desde cero y se verificó el
   manifiesto: **ambos hashes `OK`** y `dataset_sha256 = 9af86718…`, idénticos a los
   comprometidos.

Comando reproducible (con el kernelspec temporal en su sitio, o registrándolo con
`ipykernel install --user --name sic-estudiante`):

```sh
JUPYTER_PATH=$PWD/.tmp_notebook/jupyter \
PATH=/opt/homebrew/Caskroom/miniforge/base/envs/temp_causal_env/bin:/usr/bin:/bin \
/usr/bin/python3 -m nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=sic-estudiante proyecto.ipynb
```

**Evidencia:**

```text
[deriva      ] estado = alerta | acción: alertar (revisar antes de reentrenar)
[positividad ] estado = falla  | acción: abstenerse (bloquear la promoción)
/efecto: 200 efecto=1638.6 ic95=[1001.6, 2275.7] version=v0001
/consulta dentro: 200 estado=respuesta efecto=1060.1
/consulta fuera (age=99): 200 estado=abstencion motivo=age=99 fuera de [18.0, 54.0]
HUMO: OK
```

---

## 10. Cierre

**Guía docente.** `GUIA_CONSTRUCCION.md`: construcción paso a paso pensada para clase
(14 partes, 31 pasos): instalación y kernel, inventario del dato, los cinco bloques con
concepto + qué escribir + salida esperada + checkpoint + errores típicos, la adaptación a
`ihdp` como entregable, notebook, extensión de servicio y contenedor, rúbrica formativa y
fuera de alcance.

**Ensayo cronometrado (dos veces, desde `make limpiar`):**

| Ensayo | Tiempo | Resultado |
|---|---|---|
| A — `jobs` | **1,55 s** | 5/5 checkpoints · AIPW 1638.6 · ventanas `pasa/alerta/falla` · HUMO OK |
| B — `ihdp` (estado final) | **1,52 s** | AIPW 5,2 [3,9; 6,4] · estratos 7,2 / 3,2 · ventanas `pasa/alerta/falla` · HUMO OK |

Conclusión de calibración: el presupuesto de 2 h **no** se gasta en cómputo (≈2 s), sino en
ensayo, guion y recorte de alcance.

**Corrección de dependencias.** `requirements.txt` no cubría lo que el propio kit pide:
se añadieron `matplotlib` (celda del gráfico), `ipykernel` (kernel del notebook) y
`jupyterlab` (el `LEEME_PRIMERO` invoca `jupyter lab`). Sin ellas, una instalación limpia
falla en la celda 11 y no hay kernel. Hallazgo 5, resuelto.

**Pendiente para el usuario (fuera del alcance del trabajo):** mover el `tar.gz` del
baseline de `/tmp` a `~/backups/`. El kernel `sic-estudiante` **ya quedó registrado**
(`~/Library/Jupyter/kernels/sic-estudiante`, apuntando a `temp_causal_env`), así que el
notebook abre con el kernel que pide su metadata sin tocar nada más.

**Estado final.** Artefactos `ihdp` `v0001` con manifiesto verificado
(`dataset_sha256 = 9af86718…`); árbol limpio; tags
`semana4-kit-original` → `semana4-ihdp-v1` → `semana4-entrega-v1` → `semana4-final` → `v1.0.0`.

---

## 11. Prueba histórica de contenedor local (hallazgos 8–10)

Al intentar correr el artefacto como servicio local aparecieron tres defectos que impedían
usarlo, corregidos y verificados entonces con un contenedor. Aquella prueba **no fue un
despliegue** ni convierte el prototipo en producto clínico o laboral:

| # | Defecto | Arreglo |
|---|---|---|
| 8 | `rutas.py` resolvía `DATOS` al importar ⇒ en el contenedor (sin `data_benchmark_causal/`) fallaba el arranque | `DATOS` tolera la ausencia; el servicio solo necesita `artifacts/` |
| 9 | `servicio_core` importa `registro`, que el `Dockerfile` no copiaba | se añade `registro.py` al `COPY`; imagen con usuario no-root y `HEALTHCHECK` |
| 10 | `/consulta` afirmaba «los intervalos se solapan» incluso en `ihdp`, donde **no** se solapan (7,2 vs 3,2) | la nota se **deriva** de los IC en `estimacion.py` |

Además, los archivos estaban en modo `600`: con usuario no-root la imagen no podía leerlos
(`PermissionError`), resuelto con `chmod -R a+rX`.

Verificación (contenedor real, `colima`):

```text
/salud  -> {"estado":"ok","version":"v0001","estimando":"ATE de treatment sobre outcome (efecto total)"}
/efecto -> efecto 5.2, ic95 [3.9, 6.4], estimador AIPW cross-fitting K=5
/consulta (dentro)  -> efecto 7.2, ic95 [5.5, 8.8], bw=1
/consulta (fuera)   -> abstencion, bw=99 fuera de [-3.1332, 3.0532], sin número
nota_heterogeneidad -> «no se solapan: diferencia consistente con el corte declarado»
healthcheck -> healthy
```

Pendiente si el servicio sale del ámbito interno: verificación de hash al cargar el bundle,
autenticación, TLS y métricas (ver §12 del `GUIA_CONSTRUCCION.md`).

---

## 12. Endpoint de heterogeneidad (API)

**Contrato activo:** `POST /heterogeneidad` recibe un perfil completo de covariables y
devuelve `proyeccion`, un IC **condicional al ajuste** y advertencias, con abstención fuera
de soporte. Nunca devuelve un CATE ni un efecto individual identificado.
`POST /efecto_individual` queda como **alias deprecado** por compatibilidad.

**Cómo:** `estimacion.modelo_individual` ajusta una **proyección lineal del score AIPW**
sobre las covariables y guarda intercepto, coeficientes, medias/desviaciones y la matriz de
covarianza (27×27) en `estimacion.json`. El IC del ajuste usa `z' Cov(β) z` incluyendo el
intercepto; condiciona en ese ajuste y no cubre toda la incertidumbre causal o de especificación.

**Por qué así y no guardando los scores:** la regla de la entrega prohíbe `tau`, `y0` ni `y1`
en el bundle. Un modelo de 27 coeficientes es auditable y no expone pseudo-resultados por
unidad.

**Límite declarado y evidencia histórica:** no es un CATE validado. En la corrida histórica,
la proyección apenas discriminó (`r2 = 0,095` en `ihdp` y `0,012` en `jobs`), por lo que se
añadieron advertencias y `que_cubre_el_ic`. Estas cifras no constituyen una nueva validación.

**Evidencia histórica del endpoint original:**

```text
ihdp  perfil dentro -> 9.1 [6.1, 12.0] · r2 0.095 · "baja"
jobs  perfil dentro -> 398.8 [-1663.3, 2461.0] · r2 0.012 · "muy baja"
ahora fuera de rango -> abstencion (HTTP 200, sin número)
contenedor rebuild -> healthy; /docs incluye la ruta nueva
```

---

## 13. Salidas legibles (formato estadístico)

**Qué:** las tres rutas aceptan `?formato=texto` y devuelven un informe alineado; el JSON
gana `tipo`, `efecto_texto` (número + unidad + IC en formato español) e `interpretacion`
(si el intervalo excluye el cero).

**Por qué:** un `8.2` suelto no es una salida estadística. El número solo significa algo con
su unidad, su IC y una lectura explícita de si el cero queda fuera. Y en el caso individual,
con la advertencia de que el R² es bajo.

**Evidencia:**

```text
EFECTO POR ESTRATO — versión v0001
Estimando : media del efecto del programa en el estrato bw=0 (bw bajo (<= mediana de train))
Efecto    : 3,2 puntos de test cognitivo
IC 95 %   : 1,4 a 4,9
Estrato   : bw = 0 (n = 224)
Lectura   : El intervalo excluye el cero: efecto positivo estimado bajo los supuestos declarados.
Alcance   : la media del efecto en este estrato; NO el ATE poblacional ni un efecto individual
```

Verificado históricamente en el contenedor (`?formato=texto` en `/efecto`, `/consulta` y
la ruta por perfil, incluida la abstención) y en `make humo`. La ruta activa es
`/heterogeneidad`; `/efecto_individual` se conserva solo como alias deprecado.

---

## 14. Formulario web

**Qué:** `GET /` sirve un formulario con las 25 covariables (rango de entrenamiento como
`min`/`max`, valores sugeridos en el punto medio) y `GET /calcular` devuelve el informe del
perfil en HTML.

**Por qué:** el JSON de entrada tiene sentido para un cliente; para una persona, 25 claves
son una barrera. El formulario reutiliza el núcleo de `heterogeneidad` (también accesible
por el alias deprecado), así que no duplica lógica ni relaja controles: el servidor revalida
el soporte aunque el navegador
ya limite los valores.

**Evidencia:** `GET /` → 200 con 25 `<input>`; `/calcular` con perfil válido → «EFECTO PARA
UN PERFIL»; con `bw=99` → «ABSTENCIÓN». `make humo` lo cubre con dos comprobaciones.

**Corrección (15):** los campos salieron con `step="0.001"` y un `min` de −3,133210…, así
que la validación HTML exigía múltiplos exactos del paso desde el mínimo y **bloqueaba los
valores por defecto**. Se cambió a `step="any"`, el `min`/`max` va con precisión completa y
cada campo muestra su rango. Verificado: envío con los valores sugeridos → «9,1 puntos»;
`bw=0` → respuesta válida.

---

## 15. Primera versión funcional (tag `v1.0.0`)

**Qué se congela:** el commit que hace funcionar el artefacto de punta a punta, por CLI, por
API y por formulario, con los mismos números que declara la documentación.

| Componente | Estado |
|---|---|
| Pipeline (`make demo`) | 5/5 checkpoints en `jobs`; demo `ihdp` en verde; ≈ 2 s |
| Estimador | AIPW cross-fitting K=5 → **5,2** [`3,9`; `6,4`] en `ihdp` |
| Artefactos | `v0001` inmutable, manifiesto verificado, `dataset_sha256 = 9af86718…` |
| Servicio histórico | `/salud`, `/efecto`, `/consulta`, ruta por perfil (hoy `/heterogeneidad`, con `/efecto_individual` como alias deprecado), `?formato=texto` |
| Formulario web | `GET /` con 25 campos validados + `GET /calcular` |
| Contenedor | `puente:0.1.0` (`sha256:dbe3453abc5b`, 561 MB), no-root, `HEALTHCHECK` → `healthy` |
| Pruebas | `make humo` verde, incluidos los dos casos de abstención |
| Documentación | `BITACORA.md`, `GUIA_CONSTRUCCION.md` (guía) + `.rtf` derivado, `pregunta_ihdp.md`, ficha Typst + PDF |

**Límites conocidos de esta versión** (no son defectos ocultos, están declarados):
proyección individual con `R² = 0,095`; sin verificación de hash al cargar el bundle; sin
autenticación ni TLS; un escenario por artefacto; piernas lineales.

**Cómo verificar la versión desde cero:**

```sh
make limpiar && SIC_ESCENARIO=synthetic/ihdp make demo   # ≈ 2 s en la corrida histórica
jq -r '.archivos | to_entries[] | "\(.value)  artifacts/registro/v0001/\(.key)"' \
  artifacts/registro/v0001/manifest.json > /tmp/v1.sha256
shasum -a 256 -c /tmp/v1.sha256                    # 2/2 OK
docker build -t puente:0.1.0 . && docker run -d -p 8000:8000 --name puente puente:0.1.0
curl -s localhost:8000/salud                        # {"estado":"ok",...}
```

---

## 16. Actualización documental: alcance y contrato activo

Esta sección registra una revisión documental **previa a la validación de §17**. Aquella
revisión no ejecutó `make demo`, `make evidencia` ni `make cobertura`, no regeneró
artefactos y no cambió el champion. El estado validado posterior se remite a §17 sin
borrar esta historia.

### Alcance y lectura de la evidencia

**Prototipo local de estimación causal con AIPW, abstención fuera de soporte y monitoreo, con datos sintéticos. No es un sistema desplegado ni un producto clínico o laboral.**

Las referencias activas son `synthetic/ihdp` y `synthetic/jobs`. Las estimaciones, pruebas
de contenedor, salidas de notebook y versiones `v0001` descritas arriba son antecedentes
históricos. El paquete histórico llegó a incluir `v0007`; posteriormente la validación de
§17 dejó **`v0008` como champion actual**, con `v0001`–`v0007` intactas.

### Límites de diagnóstico e identificación

- DoWhy/DAG comprueba coherencia backdoor con el grafo declarado; **no verifica
  ignorabilidad** ni ausencia de confusores no observados.
- Los rangos marginales utilizados para abstenerse **no garantizan soporte multivariable**.
- La coincidencia entre diferencia ingenua, OLS y AIPW **no prueba identificación**; tampoco
  cross-fitting corrige dos nuisance models mal especificados.
- El E-value solo cuantifica confusión no observada bajo sus supuestos. No cubre errores de
  especificación, fallos de positividad ni violaciones de consistencia/SUTVA.
- Los umbrales son convenciones iniciales, no calibración universal. En esta revisión previa
  se anunció la sensibilidad de ±20 % (factores `.8`, `1`, `1.2`); §17 documenta que ya está
  implementada y el resultado observado en la corrida actual.

### Cobertura opcional: estado en esta revisión previa

En el momento de esta revisión se documentó `make cobertura` como comando previsto:

```sh
make cobertura
```

El objetivo estaba planteado para generar `artifacts/cobertura.json` en un DGP ilustrativo
propio (`n = 500`, `R = 100`, semilla `20261111`), sin atribuirlo a IHDP/jobs ni a datos
reales. Entonces todavía no se afirmaban resultados concretos. Ese estado quedó superado
por la ejecución real registrada en §17.

### API, artefactos y entorno

- `POST /heterogeneidad` devuelve `proyeccion`, IC condicional al ajuste y advertencias;
  nunca CATE/efecto individual identificado.
- `POST /efecto_individual` queda como alias deprecado con el mismo núcleo y advertencias.
- Los artefactos son JSON; no se usan `pickle` ni `joblib`.
- Las dependencias tienen versiones exactas fijadas en `requirements.txt`.

---

## 17. Validación local real: evidencia `v0008`

Se ejecutó localmente la validación con estos comandos:

```sh
SIC_ESCENARIO=synthetic/ihdp .venv_ci/bin/python cobertura.py
SIC_ESCENARIO=synthetic/ihdp make PYTHON=.venv_ci/bin/python evidencia
```

- **Registro y comprobaciones:** el champion actual es **`v0008`**; `v0001`–`v0007`
  permanecen intactas. Pruebas y humo quedaron verdes: **`PRUEBAS: OK` y `HUMO: OK`**.
  La evidencia está en `evidencia/06_registro.txt`, `evidencia/07_servicio.txt` y
  `evidencia/09_pruebas.txt`.
- **Estimación:** diferencia cruda 10,3 con IC 95 % aproximado [7,60; 13,05]; OLS
  4,8 [3,8; 5,8]; AIPW 5,2 [3,9; 6,4] (`evidencia/02_estimacion.txt`).
- **Positividad OOF antes del trimming:** rango [0,043; 0,916]; solape 0,99777
  (≈99,8 %, aunque la CLI puede redondear 100 %); ESS 332,2076/448 = 0,7415
  (≈332/448 y 0,74). El trimming recortó 1 unidad en total (0,2232 %),
  íntegramente de control (0,3891 % de los controles), y 0 tratadas. SMD ponderado
  OOF 0,11; sin ponderar 0,43. No confundir estos diagnósticos OOF con los valores
  históricos de §5/§8.6.
- **Cobertura Monte Carlo ya ejecutada:** DGP ilustrativo propio, `n = 500`,
  `R = 100`, semilla `20261111`; AIPW 0,97 (error MC 0,01706), OLS 0,96
  (error MC 0,01960), ingenuo 0,00 (error MC 0). La diferencia de AIPW respecto
  del nominal 0,95 es 0,02 y **no está dentro de ±1 error MC**; no se afirma
  calibración exacta ni se atribuye esta cobertura a IHDP/jobs. Evidencia:
  `evidencia/10_cobertura.txt` y `evidencia/10_cobertura.json`.
- **Monitor:** la sensibilidad ±20 % está implementada. Con timestamp
  **`2026-11-12T01:04:37Z`**, produjo **0 cambios de acción fuera de la
  clasificación base** en esta corrida (`evidencia/05_puerta.txt`). No es una
  calibración universal.

- **Validación adicional de `synthetic/jobs`:** se ejecutaron `datos.py` y la función
  de aplicación `estimacion.estimar()` sin invocar el CLI de escritura. Hashes, esquema,
  pared, identificación backdoor y placebos pasaron. Diferencia ingenua 1600,7723
  [996,4466; 2205,0980]; OLS 1596,0422 [1004,8127; 2187,2718]; AIPW 1638,6029
  [1001,5516; 2275,6542]. Propensiones OOF [0,0681763; 0,5595719], solape 1,0,
  ESS 702,6543 y cero recortes. No se creó ninguna versión ni se escribieron artefactos.

- **Diagramas y PDF actualizados:** `make dag && make cierre` regeneró los cuatro SVG y
  compiló `dataset_y_metodo.pdf` (14 páginas). Se actualizaron `evidencia/08_dag.txt` y
  `evidencia/SHA256SUMS`; los 12 archivos de evidencia verificaron OK.
- **Docker verificado con `v0008`:** se construyó una imagen temporal y se ejecutó con
  `SIC_ESCENARIO=synthetic/ihdp` como usuario no-root `app`; alcanzó estado `healthy`.
  `/salud`, `/efecto` y `/heterogeneidad` respondieron HTTP 200. El perfil dentro de
  soporte devolvió proyección 9,1 [6,1; 12,0] con advertencias; al llevar `bw` a 1 000 000,
  `/heterogeneidad` respondió `abstencion` y omitió `proyeccion`. El contenedor, la imagen
  temporal y los payloads de prueba fueron eliminados.

Esta actualización documental y las validaciones de solo lectura no promueven versiones
nuevas: el champion sigue siendo `v0008`.
