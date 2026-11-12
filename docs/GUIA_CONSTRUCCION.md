# Guía docente — construcción de «Puente» (semana 4)

Guía para **construir** este repositorio desde el kit vacío y para **producir el entregable**
sobre `synthetic/ihdp`. Cada paso declara el objetivo de aprendizaje, el concepto, qué se escribe,
el comando, la salida esperada y el checkpoint de clase.

> **Alcance activo:** Prototipo local de estimación causal con AIPW, abstención fuera de soporte y monitoreo, con datos sintéticos. No es un sistema desplegado ni un producto clínico o laboral.
>
> **Lectura histórica y estado validado:** las cifras, salidas y versiones `v0001` de los checkpoints describen el ejercicio original; no constituyen una validación nueva. La validación local posterior dejó **`v0008` como champion actual**, con `v0001`–`v0007` intactas; sus resultados y rutas de evidencia están en `BITACORA.md` §17 y `pregunta_ihdp.md` §6/§11. Esta revisión documental no ejecuta ese flujo ni promueve versiones nuevas.
>
> **Formato de la guía.** Los pasos están pensados para dos sesiones de 2 h más la tarea:
> sesión 1 = bloques 2 y 3; sesión 2 = bloques 4, 5 y 6; tarea = adaptación a `ihdp`.
> El pipeline histórico corre en **≈ 2 s**: el tiempo de clase se gasta en decidir y leer,
> no en esperar.

---

## Parte 0 — Antes de empezar (para el docente)

**Qué se construye:** un prototipo causal local —estimador con incertidumbre,
tarjeta de modelo, registro inmutable con hashes, servicio que se abstiene fuera de soporte
y una puerta `pasa / alerta / falla`— sobre dos escenarios sintéticos. Completar el ejercicio
no equivale a desplegar un sistema ni habilita decisiones clínicas o laborales.

**Las cinco ideas que hay que dejar instaladas:**

1. El **estimando se declara antes** de mirar datos (`pregunta_jobs.md`).
2. La estimación viene con **incertidumbre** y con la declaración de qué cubre el IC.
3. Un artefacto publicado se refiere a un **sujeto con hash**; si cambia, es otra versión.
4. **Abstenerse es una respuesta** de primera clase, no un error.
5. Los **umbrales se declaran antes** del desenlace; moverlos después es elegir el resultado.

**Estado de arranque correcto:** `make verificar` **falla** con `TODO-1`.

```sh
git checkout semana4-kit-original   # opcional: ver el kit prístino
make verificar                       # NotImplementedError: TODO-1 pendiente de completar
```

---

## Parte 1 — Preparación del entorno

### Paso 1.1 — Crear el entorno

```sh
cd semana_4_proyecto
python3.13 -m venv .venv && . .venv/bin/activate
python -m pip install -r requirements.txt
```

`requirements.txt` fija con versiones exactas lo que el kit usa de verdad: `numpy`,
`scipy`, `fastapi`, `uvicorn`, `httpx` (pipeline y servicio), `matplotlib` (gráfico
del notebook), `ipykernel` y `jupyterlab`.

**Verificar:**

```sh
python -V
python -c "import numpy, scipy, fastapi, matplotlib; print('ok')"
```

### Paso 1.2 — Registrar el kernel (una sola vez)

```sh
python -m ipykernel install --user --name sic-estudiante \
  --display-name "Python (SIC estudiante)"
jupyter kernelspec list
```

**Concepto que hay que explicar:** las celdas `!make` heredan el `PATH` del kernel, así que
**el kernel es el entorno del proyecto**. Con otro kernel, `make humo` muere con
`ModuleNotFoundError: fastapi` aunque el paquete esté instalado.

### Paso 1.3 — Mapa de la construcción

| Bloque | TODOs | Archivo | Concepto | Artefacto que produce |
|---|---|---|---|---|
| 2 | 1–3 | `datos.py` | Rol único por columna, splits con hash, la pared | verificación en pantalla |
| 3 | 4–8, 21, 22 | `estimacion.py` | OLS, propensity, ESS, SMD, **AIPW cross-fitting**, estratos, trampa | `artifacts/estimacion.json` |
| 4 | 9–13 | `registro.py` | Tarjeta, versión inmutable, manifiesto, promoción atómica | `artifacts/registro/v0001/` + `champion` |
| 5 | 14–18 | `monitor.py` | PSI, ventanas, puerta causal | estados por ventana |
| 6 | 19–20 | `servicio_core.py` | Bundle cacheado, abstención | `/efecto`, `/consulta` |

---

## Parte 2 — Entender el dato antes de escribir código

### Paso 2.1 — Leer la pregunta (10 min, sin teclado)

Abrir `pregunta_jobs.md`: pregunta, estimando, población, supuestos con su clase y qué **no**
afirma el prototipo. Discusión de clase: *¿la pregunta pide un promedio o un efecto
individual?*

### Paso 2.2 — Inventariar el escenario

```sh
ls data_benchmark_causal/causal_benchmark_synthetic/datasets/synthetic/jobs/
head -2 data_benchmark_causal/causal_benchmark_synthetic/datasets/synthetic/jobs/observed_train.csv
```

**Qué hay y qué no:**

| Archivo | Uso |
|---|---|
| `observed_{train,validation,test}.csv` | datos; solo `train` alimenta decisiones |
| `splits.json` | hashes y recuentos de las particiones |
| `metadata.json` / `identification.json` | ficha y conjunto de ajuste válido |
| `interventions.json` | **contiene `ate`/`att`**: no se usa (hueco de la pared) |
| `truth_*.csv` | **no existe**: eso es la pared |

---

## Parte 3 — Bloque 2: roles, hashes y la pared (`datos.py`)

### Paso 3.1 — `TODO-1`: un rol por columna

**Concepto (C-01):** cada columna tiene *un* papel. Si `re78` es resultado, no puede ser
también covariable; si `treatment` no varía, no hay nada que estimar.

```python
def validar(self, columnas_datos, valores_tratamiento):
    esquema = self.columnas()
    ausentes = [c for c in esquema if c not in columnas_datos]
    if ausentes:
        raise ValueError(f"columna(s) del esquema ausentes en los datos: {ausentes}")
    dobles = sorted({c for c in esquema if esquema.count(c) > 1})
    if dobles:
        raise ValueError(f"columna(s) con más de un rol: {dobles}")
    if np.unique(np.asarray(valores_tratamiento)).size < 2:
        raise ValueError(f"el tratamiento '{self.tratamiento}' no varía en los datos")
```

**Enseñar:** el mensaje de error **nombra la culpable**. Un `assert` genérico no sirve en
producción: quien lo lea a las 3 a.m. tiene que saber qué arreglar.

### Paso 3.2 — `TODO-2`: recomputar, no confiar

```python
coincide = (hashlib.sha256((DATOS / f"observed_{parte}.csv").read_bytes()).hexdigest()
            == declarados["splits"][parte]["file_sha256"])
```

**Concepto (C-10):** el productor declara hashes; el consumidor los **recomputa**. Es la
diferencia entre creer y verificar.

### Paso 3.3 — `TODO-3`: la pared

```python
try:
    with open(DATOS / "truth_train.csv"):
        pass
except FileNotFoundError:
    print("  pared OK: truth_train.csv no existe en el paquete (reservado)")
    return
raise RuntimeError("pared rota: truth_train.csv SÍ existe en el paquete")
```

**Concepto:** la pared no es una convención, es una comprobación ejecutable. Si alguien
reintroduce la verdad, el programa falla.

### Checkpoint 1

```sh
make verificar
```

```text
esquema valida contra observed_train: OK (n = 1033, tratados = 262)
  train        hash OK  (1033 filas, semilla 20240701)
  validation   hash OK  (344 filas, semilla 20240701)
  test         hash OK  (345 filas, semilla 20240701)
  pared OK: truth_train.csv no existe en el paquete (reservado)
```

**Prueba negativa de clase** (celda del notebook):

```python
esquema.validar(["treatment", "re78", "age", "black"], [0, 1, 0, 1])
# ValueError: columna(s) del esquema ausentes en los datos: ['educ', 'hispan', ...]
```

**Errores típicos:** hashear el texto normalizado en vez de los bytes; aceptar columnas
ausentes sin nombrarlas; confundir «no hay `truth`» con «no hay verdad».

---

## Parte 4 — Bloque 3: el efecto con incertidumbre (`estimacion.py`)

### Paso 4.1 — `TODO-4`: la referencia ingenua (OLS)

```python
beta = np.linalg.lstsq(M, Y, rcond=None)[0]
residuo = Y - M @ beta
sigma2 = float(residuo @ residuo / (n - M.shape[1]))
cov = sigma2 * np.linalg.inv(M.T @ M)
ate, se = float(beta[1]), float(np.sqrt(cov[1, 1]))
```

**Concepto:** el coeficiente del tratamiento es el ATE *bajo un modelo lineal*. Sirve como
referencia, no como respuesta. La coincidencia entre diferencia ingenua, OLS y AIPW puede
ser un diagnóstico de estabilidad, pero **no prueba identificación**: los estimadores pueden
compartir confusión o errores de especificación.

### Paso 4.2 — `TODO-5`: el propensity

```python
def nll(w):
    eta = Z @ w[1:] + w[0]
    return float(np.sum(np.logaddexp(0, eta) - D * eta))
r = minimize(nll, np.zeros(Z.shape[1] + 1), method="BFGS")
```

**Concepto:** `ê(X)` es la probabilidad de tratamiento. Se estandarizan las covariables para
que BFGS converja; `logaddexp` evita desbordes.

### Paso 4.3 — `TODO-6` y `TODO-7`: ESS y SMD

```python
e = np.clip(e, 1e-6, 1 - 1e-6)
w = np.where(D == 1, 1 / e, 1 / (1 - e))
ess = float(w.sum() ** 2 / np.sum(w ** 2))

smd = float((v[D == 1].mean() - v[D == 0].mean())
            / np.sqrt((v[D == 1].var() + v[D == 0].var()) / 2))
```

**Concepto:** el ESS dice cuántas unidades «cuentan» de verdad; el SMD mide desequilibrio en
unidades de desviación común.

### Paso 4.4 — `TODO-21`: **la pieza del día** (AIPW con cross-fitting)

```python
for fold in folds:
    fuera = np.ones(n, bool); fuera[fold] = False
    dentro = ~fuera
    b1 = _ajustar_lineal(X[fuera & (D == 1)], Y[fuera & (D == 1)])
    b0 = _ajustar_lineal(X[fuera & (D == 0)], Y[fuera & (D == 0)])
    mu1[dentro] = np.column_stack([np.ones(dentro.sum()), X[dentro]]) @ b1
    mu0[dentro] = np.column_stack([np.ones(dentro.sum()), X[dentro]]) @ b0
    e[dentro] = _propensity_fit(X[fuera], D[fuera])(X[dentro])

e = np.clip(e, 0.05, 0.95)                       # trimming declarado
score = mu1 - mu0 + D * (Y - mu1) / e - (1 - D) * (Y - mu0) / (1 - e)
ate, se = float(score.mean()), float(score.std(ddof=1) / np.sqrt(n))
```

**Tres conceptos que hay que verbalizar:**

1. **Ningún nuisance ve a la unidad que predice** (cross-fitting). Es la exigencia del cap. 9.
2. **Doble robustez:** basta que una de las dos piernas esté bien especificada.
3. **El score es la influence function:** su media es el ATE y su desviación da el IC.

### Paso 4.5 — `TODO-22`: estratos (y lo que **no** son)

```python
sel = (col[variable] > umbral).astype(int) == int(clave)
media = float(score[sel].mean())
se = float(score[sel].std(ddof=1) / np.sqrt(sel.sum()))
```

**Concepto:** la media de scores AIPW dentro de una hoja es un efecto **de estrato**, no un
CATE. El corte se declara antes y va en la tarjeta.

### Paso 4.6 — `TODO-8`: la trampa de fuga

```python
score = 0.6 * Y + 0.4 * D + g.normal(0, RUIDO_TRAMPA[ESCENARIO], len(Y))
return ate_ols(col, esquema, extra={"valores": score})
```

**Concepto:** una columna derivada del resultado **mejora** el ajuste y **vacía** el
coeficiente del tratamiento. Ninguna métrica predictiva la detecta; solo el diseño.

### Checkpoint 2

```sh
make estimar
```

```text
diferencia cruda E[Y|D=1]-E[Y|D=0] = 1600.8 USD
ATE OLS (8 controles) = 1596.0 | SE = 301.6 | IC95 = [1004.8, 2187.3]
AIPW cross-fitting K=5 = 1638.6 | SE = 325.0 | IC95 = [1001.6, 2275.7]
trampa score_post      = 172.4  <- el coeficiente se vació
estrato nodegree=1 (sin título, n=568): efecto 1060.1 IC95 [233.1, 1887.2]
estrato nodegree=0 (con título, n=465): efecto 2345.2 IC95 [1356.9, 3333.4]
ESS = 729 (ESS/n = 0.71) | rango e = [0.092, 0.530] | solapamiento = 100%
SMD máx = 0.19
```

**Pregunta de clase:** AIPW 1638,6 y OLS 1596,0 difieren en 42 USD con SE ≈ 300.
*¿Es una discrepancia preocupante o está dentro del ruido?*

**Errores típicos:** ajustar y predecir con el mismo pliegue; usar `ddof=0` y sorprenderse del
IC; **recortar `ê` sin declararlo en la tarjeta** (el *trimming* es una decisión, no un
detalle de implementación); llamar CATE al estrato.

---

## Parte 5 — Bloque 4: tarjeta, versión y champion (`registro.py`)

### Paso 5.1 — `TODO-9`: la tarjeta

Siete campos (`CAMPOS_TARJETA`): `estimando`, `poblacion`, `supuestos`, `umbrales`,
`semilla`, `dataset_sha256`, `estimador`. Además `heterogeneidad` con **corte, umbral y
regla**.

**Concepto:** la tarjeta es el contrato público. Lo que no está ahí, no está prometido.

### Paso 5.2 — `TODO-10`: validar la tarjeta

Falta un campo o una clase de supuesto que no es `observable`/`no_observable` → error.

### Paso 5.3 — `TODO-11`: el manifiesto

```python
archivos = {n: sha256_archivo(carpeta / n) for n in ("estimacion.json", "tarjeta.json")}
_escribir(carpeta / "manifest.json", {
    "version": version, "dataset_sha256": tarjeta["dataset_sha256"],
    "puerta": estado_puerta, "archivos": archivos})
```

### Paso 5.4 — `TODO-12`: integridad que recomputa

```python
return all(sha256_archivo(carpeta / n) == h for n, h in m["archivos"].items())
```

### Paso 5.5 — `TODO-13`: promoción atómica

```python
if manifest["puerta"] == "falla":
    raise RuntimeError(f"{version} tiene puerta 'falla': no se promueve")
tmp = REGISTRO / "champion.tmp"
tmp.write_text(version + "\n")
tmp.replace(REGISTRO / "champion")     # rename atómico, nunca editar en sitio
```

### Checkpoint 3

```sh
make registrar
```

```text
registrada v0001 | integridad: OK
mutación detectada: SÍ (hash distinto del manifiesto -> bloqueado)
champion -> v0001
champion resuelve a: v0001
```

**Enseñar con la mutación:** un byte añadido a una copia rompe el hash. La afirmación
publicada se refiere a un sujeto con hash; si el hash cambia, es otra cosa.

**Errores típicos:** escribir `champion` en sitio (estado intermedio); omitir
`dataset_sha256`; promover una versión en `alerta` sin aceptación explícita.

---

## Parte 6 — Bloque 5: ventanas y puerta causal (`monitor.py`)

### Paso 6.1 — `TODO-14`: PSI

```python
cortes = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
a = np.histogram(ref, bins=cortes)[0] / len(ref)
b = np.histogram(nueva, bins=cortes)[0] / len(nueva)
return float(np.sum((np.clip(a, eps, None) - np.clip(b, eps, None))
                    * np.log(np.clip(a, eps, None) / np.clip(b, eps, None))))
```

**Concepto:** los cortes son de la **referencia**; el `clip` evita `log(0)`. Bandas
convencionales: <0,1 estable · 0,1–0,25 moderado · ≥0,25 significativo. Todos los umbrales
son **convenciones iniciales**, no una calibración universal. El monitor ya incluye el análisis
de sensibilidad de ±20 % con factores `.8`, `1` y `1.2`. En la corrida validada produjo 0
cambios de acción fuera de la clasificación base (`evidencia/05_puerta.txt`), pero esa
estabilidad local no prueba calibración universal ni identificación.

### Paso 6.2 — `TODO-15` a `TODO-17`: las tres ventanas

| Ventana | Construcción | Qué enseña |
|---|---|---|
| `sana` | submuestra sin reemplazo (700 de 1033) | el ruido de muestreo no debe alertar |
| `deriva` | `age + 10` sobre una **copia** | la población cambió, no la relación |
| `positividad` | tratados con `re74 > p75`, controles con `re74 < p25` | el soporte se rompe |

### Paso 6.3 — `TODO-18`: la puerta

```python
if solape < umbrales["solape_min"]:
    estado = "falla"; motivo.append(f"solapamiento roto: {solape:.0%} …")
elif psi_max > umbrales["psi_alerta"]:
    estado = "alerta"; motivo.append(f"deriva: PSI de {culpable} = {psi_max:.2f} …")
if estado == "pasa" and smd_max > umbrales["smd_max"]:
    estado = "alerta"; motivo.append(...)
```

**Concepto:** prioridad `falla > alerta`. Una alerta **nombra la covariable**; sin nombre no
es accionable.

### Checkpoint 4

```sh
make ventanas
```

```text
[sana        ] estado = pasa   | acción: continuar
[deriva      ] estado = alerta | acción: alertar (revisar antes de reentrenar)
              - deriva: PSI de age = 1.35 (umbral 0.25)
[positividad ] estado = falla  | acción: abstenerse (bloquear la promoción)
              - solapamiento roto: 0% de unidades con e en [0.05, 0.95] (mínimo 50%)
```

**Preguntas de clase (obligatorias en el notebook):**

1. En `positividad`, `ESS/n = 1.0`: ¿por qué no es buena señal? *(Los pesos son casi
   constantes dentro de cada brazo; lo que se rompió es el solapamiento.)*
2. En `deriva`, el SMD queda en 0,19: ¿por qué no alerta por balance? *(El SMD de la puerta
   es interno a la ventana; envejecer a todos no cambia el contraste.)*
3. ¿Qué acción corresponde y qué **no** se puede afirmar sobre la causa?

**Errores típicos:** calcular los cortes del PSI con la ventana; confundir SMD interno con
deriva; mover el umbral después de ver la ventana.

---

## Parte 7 — Bloque 6: servicio y abstención (`servicio_core.py`)

### Paso 7.1 — `TODO-19`: el bundle

```python
if "bundle" not in _cache:
    version = champion()
    carpeta = REGISTRO / version
    _cache["bundle"] = {"version": version,
                        "estimacion": json.loads((carpeta / "estimacion.json").read_text()),
                        "tarjeta": json.loads((carpeta / "tarjeta.json").read_text())}
```

**Concepto:** el bundle viaja; el servicio **no lee los CSV**. Por eso puede correr en un
contenedor sin datos.

### Paso 7.2 — `TODO-20`: la consulta y la abstención

```python
motivos = [f"{c}={float(perfil[c]):g} fuera de [{round(lo, 4)}, {round(hi, 4)}]"
           for c, (lo, hi) in rangos.items() if c in perfil
           and not (lo <= float(perfil[c]) <= hi)]
if motivos:
    return {"estado": "abstencion", "motivo": "; ".join(motivos), "version": b["version"]}
```

**Concepto:** abstención = HTTP **200 sin ningún número**. No es un error del cliente ni del
servidor: es una respuesta válida. Los rangos se comprueban marginalmente; que cada
covariable esté dentro de rango **no garantiza soporte multivariable**.

### Checkpoint 5

```sh
make humo
```

```text
/salud: 200 {'estado': 'ok', 'version': 'v0001', ...}
/efecto: 200 efecto=1638.6 ic95=[1001.6, 2275.7] version=v0001
/consulta dentro: 200 estado=respuesta efecto=1060.1
/consulta fuera (age=99): 200 estado=abstencion motivo=age=99 fuera de [18.0, 54.0]
determinismo: dos llamadas idénticas -> iguales
HUMO: OK
```

**Errores típicos:** devolver 4xx en la abstención; redondear distinto en cada llamada
(rompe el determinismo); cargar el CSV en el servicio.

---

## Parte 8 — El entregable: adaptar todo a `synthetic/ihdp`

La tarea es **cambiar de escenario sin reescribir el método**. El código quedó paramétrico
(`SIC_ESCENARIO`), así que el trabajo es decidir y declarar. Las cifras de esta parte son
salidas históricas del ejercicio original. La validación local posterior, con champion `v0008`,
se documenta por separado en `BITACORA.md` §17 y en la evidencia actual.

### Paso 8.1 — Descubrir el escenario (sin mirar el efecto)

```python
import json, pathlib
meta = json.loads((esc / "metadata.json").read_text())
ident = json.loads((esc / "identification.json").read_text())
meta["description"], meta["outcome"], ident["valid_adjustment_sets"][0]
```

### Paso 8.2 — Declarar el esquema

`resultado = "outcome"`, **25 covariables** (`bw … was`). En el código: `RESULTADO` y
`COVARIABLES` por escenario; `EsquemaCausal()` los toma de ahí.

### Paso 8.3 — Declarar el corte **antes** de estimar

| Decisión | Regla | Por qué |
|---|---|---|
| Corte | `bw` en la mediana de train | nombre inspirado en peso al nacer dentro del DGP sintético, no una medida clínica observada; la mediana preserva tamaño en ambas hojas; **no** se eligió por ganancia de varianza |

### Paso 8.4 — Declarar umbrales iniciales con justificación

| Umbral | jobs | ihdp | Justificación |
|---|---|---|---|
| `solape_min` | 0,50 | **0,30** | 25 covariables y P(D=1)=0,43 pueden estrechar el soporte; en esta corrida histórica se consideró demasiado exigente 0,50 |
| `smd_max` | 0,25 | **0,50** | máximo de 25 SMD tiene EE ≈ 0,096; el ruido esperado llega a 0,3–0,4 |
| `psi_alerta` | 0,25 | 0,25 | convención; la deriva sintética cae muy por encima (0,88) |

Estos valores son **convenciones iniciales** para el ejercicio, no calibración universal.
El análisis de sensibilidad ±20 % (`.8`, `1`, `1.2`) ya está implementado para exponer la
dependencia de la puerta respecto de esas elecciones. La evidencia `v0008` registra 0 cambios
de acción fuera de la clasificación base en esta corrida; no generaliza ese resultado.

### Paso 8.5 — Adaptar ventanas y la trampa

- Deriva: `bw + 1` (covariables estandarizadas, +1 ≈ una desviación estándar).
- Positividad: eje `bw`, la covariable con mayor |SMD| de tratamiento en train.
- Sana: 300 de 448 (mismo criterio que 700 de 1033).
- Trampa: ruido reescalado a la unidad del resultado (σ = 1,0 punto).

### Paso 8.6 — Generar y auditar

```sh
make limpiar && SIC_ESCENARIO=synthetic/ihdp make demo
```

Salida histórica ilustrativa del ejercicio con `v0001`, no una salida afirmada para la
actualización:

```text
esquema valida contra observed_train: OK (n = 448, tratados = 191)
ATE OLS (25 controles) = 4.8 | SE = 0.5 | IC95 = [3.8, 5.8]
AIPW cross-fitting K=5 = 5.2 | SE = 0.6 | IC95 = [3.9, 6.4]
estrato bw=1 (bw alto, n=224): efecto 7.2 IC95 [5.5, 8.8]
estrato bw=0 (bw bajo, n=224): efecto 3.2 IC95 [1.4, 4.9]
[sana] pasa · [deriva] alerta (PSI de bw = 0.88) · [positividad] falla (solape 0%)
HUMO: OK
```

**Auditoría:**

```sh
cat artifacts/registro/champion
jq -r '.archivos | to_entries[] | "\(.value)  artifacts/registro/v0001/\(.key)"' \
  artifacts/registro/v0001/manifest.json > /tmp/v1.sha256
shasum -a 256 -c /tmp/v1.sha256          # 2/2 OK
jq -r '.dataset_sha256' artifacts/registro/v0001/manifest.json   # 9af86718…
```

Todos estos artefactos se serializan como **JSON**, nunca con `pickle`/`joblib`. La salida
anterior con `v0001` es histórica. Después, la ejecución local de `make evidencia` generó y
promovió **`v0008`**, que es el champion actual; `v0001`–`v0007` permanecen intactas. La versión,
el manifiesto y el alias constan en `evidencia/06_registro.txt`; no se promueven versiones
nuevas solo por editar documentación.

### Paso 8.7 — Escribir la pregunta propia

`pregunta_ihdp.md` con el mismo formato: pregunta, estimando, población, supuestos con su
clase y qué **no** afirma. **Cuidado con la redacción:** «de los niños que lo recibieron»
describe el ATT, no el ATE que se estima. Escribir «efecto promedio en la población del
estudio» o cambiar el estimando de forma explícita. En la versión entregada la pregunta ya
está redactada como efecto promedio.

---

## Parte 9 — Notebook y evidencias

```sh
jupyter lab proyecto.ipynb        # kernel: "Python (SIC estudiante)"
```

o sin interfaz:

```sh
jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=sic-estudiante proyecto.ipynb
```

Esperado: 13 celdas de código, **0 errores**, 19 salidas, gráfico con los dos estratos y sus IC.

**Qué debe quedar escrito en el notebook:** las 3 respuestas de ventanas, la tabla de números
de `ihdp`, las 5 respuestas de cierre y la salida de `make humo` sobre `ihdp`.

> **Advertencia operativa:** los checkpoints del notebook corren sobre `jobs` y sobrescriben
> los artefactos. Al terminar: `make limpiar && SIC_ESCENARIO=synthetic/ihdp make demo`.
> Son comandos de regeneración, no comprobaciones de solo lectura.

### Cobertura Monte Carlo ya ejecutada

La validación local ejecutó `SIC_ESCENARIO=synthetic/ihdp .venv_ci/bin/python cobertura.py`
para un **DGP ilustrativo propio**, con `n = 500`, `R = 100` y semilla `20261111`. El resultado
conservado en `artifacts/cobertura.json` y `evidencia/10_cobertura.txt` es: AIPW 0,97
(error MC 0,01706), OLS 0,96 (error MC 0,01960) e ingenuo 0,00 (error MC 0).

La cobertura AIPW difiere del nominal 0,95 en 0,02 y no está dentro de ±1 error MC; no se
afirma calibración exacta. Estos valores solo aplican al DGP ilustrativo propio, no a IHDP/jobs
ni a datos reales. Los detalles y comandos de la evidencia `v0008` están en `BITACORA.md` §17.

---

## Parte 10 — Extensión: servicio utilizable (opcional, si hay tiempo)

### 10.1 — Rutas adicionales

| Ruta | Semántica |
|---|---|
| `GET /efecto` | ATE poblacional bajo los supuestos declarados |
| `POST /consulta` | media del **estrato** declarado |
| `POST /heterogeneidad` | `proyeccion`, IC condicional al ajuste y advertencias para un perfil |
| `POST /efecto_individual` | **alias deprecado** de `/heterogeneidad` |
| `?formato=texto` | informe legible en lugar de JSON |
| `GET /` | formulario con las covariables del escenario |

`/heterogeneidad` usa `modelo_individual` (proyección del score sobre X) y registra
coeficientes + covarianza en JSON; **no** guarda scores por unidad (la regla prohíbe
`tau`/`y0`/`y1` en el bundle). Su IC es condicional al ajuste y sus advertencias hacen
explícita la discriminación limitada. **Nunca devuelve un CATE ni un efecto individual
identificado.** Los valores históricos de ajuste no demuestran heterogeneidad causal.

### 10.2 — Contenedor

```sh
docker build -t puente:0.1.0 .
docker run -d --name puente -p 8000:8000 puente:0.1.0
docker inspect --format '{{.State.Health.Status}}' puente   # healthy
```

**Las tres trampas (buen ejercicio de depuración):**

| Síntoma | Causa | Arreglo |
|---|---|---|
| `FileNotFoundError: No encontré data_benchmark_causal/` | `DATOS` se resolvía al importar y el contenedor no trae el benchmark | tolerar su ausencia: el servicio solo usa `artifacts/` |
| `ModuleNotFoundError: No module named 'registro'` | `servicio_core` importa `champion` y el `Dockerfile` no copiaba `registro.py` | añadirlo al `COPY` |
| `PermissionError: /app/servicio.py` | archivos en modo `600` con usuario no-root | `RUN chmod -R a+rX /app` |

---

## Parte 11 — Qué se evalúa (rúbrica formativa)

| Criterio | Señal observable |
|---|---|
| Estimando declarado y cubierto | la tabla distingue ATE de estrato y dice qué cubre cada IC |
| Reproducibilidad | `make demo` desde cero regenera los números |
| Puerta honesta | la ventana de positividad bloquea y el motivo nombra la señal |
| Abstención | `/consulta` fuera de soporte responde 200 **sin** número |
| Corte pre-declarado | la regla está en la tarjeta, no elegida por ganancia |
| Umbrales justificados | dos líneas por umbral; convenciones iniciales para `ihdp`, no calibración universal |
| Artefactos | `v0001` con manifiesto verificado y `champion` |
| Prohibiciones | nada de `truth`, `y0`, `y1` ni `tau` en bundle o servicio |

---

## Parte 12 — Errores frecuentes (y qué enseñan)

| Síntoma | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: fastapi` en `make humo` | kernel o `python3` distinto del entorno | activar el entorno o registrarlo como `sic-estudiante` |
| `/consulta` se abstiene con un perfil válido | `SIC_ESCENARIO` ≠ artefactos del registro | `make limpiar` y regenerar con el escenario correcto |
| `make ventanas` dice que falta `tarjeta.json` | no se ejecutó `make registrar` | el registro precede a la puerta y al servicio |
| `ValueError: truth_train.csv` | alguien reintrodujo la verdad | es la pared funcionando: retirar el archivo |
| `docker build` falla con `docker.sock` | daemon apagado | `colima start` |
| El notebook abre con otro kernel | `sic-estudiante` sin registrar | Paso 1.2 |
| El formulario rechaza los valores por defecto | `step` fijo con `min` decimal | `step="any"` |

---

## Parte 13 — Fuera de alcance (por diseño)

- Learners no lineales y *repeated cross-fitting*: eso es el proyecto final.
- CATE continuo o políticas: el corte es de dos hojas y se informa como tal.
- Autenticación, TLS, persistencia, monitorización en vivo.
- `interventions.json` contiene `ate`/`att`: es el hueco de la pared; no se usa para estimar,
  decidir ni calibrar.
- Un escenario por artefacto: cambiar de escenario exige regenerar y reiniciar el servicio.
