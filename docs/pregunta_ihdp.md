# Pregunta causal y cierre — `synthetic/ihdp`

**Escenario:** `synthetic/ihdp` del benchmark local, sintético y generado con un DGP
estilo Hill (2011). Este documento distingue la pregunta, declarada antes de mirar
los efectos, de las cifras conservadas como evidencia histórica.

> **Alcance:** Prototipo local de estimación causal con AIPW, abstención fuera de soporte y monitoreo, con datos sintéticos. No es un sistema desplegado ni un producto clínico o laboral.

## 1. Pregunta didáctica, no recomendación de intervención

> **¿Cuál es el efecto promedio de `treatment` sobre `outcome` en la población
> representada por la muestra sintética, bajo los supuestos causales declarados?**

Es una pregunta metodológica para estudiar estimación e incertidumbre, no para
decidir si debe ampliarse un programa sanitario. El caso sigue siendo uno de los
casos guiados del curso; por eso el subcriterio 1.1 de la rúbrica queda en
**parcial**, no en completo. El estimando implementado es el **ATE**. Ninguna
estimación autoriza recomendaciones clínicas ni decisiones sobre niños reales.

## 2. Estimando, población y unidad

- **Estimando:** ATE de `treatment` sobre `outcome` (efecto total).
- **Unidad:** puntos del test cognitivo a los 3,5 años.
- **Población:** las 448 unidades de `observed_train.csv` del escenario
  `synthetic/ihdp` (partición de entrenamiento, hash verificado contra `splits.json`).
- **Qué cubre el IC:** el efecto **promedio** poblacional. No es un efecto
  individual ni un CATE validado. `/consulta` devuelve, como mucho, la media de
  un estrato predefinido, con su IC.
- **No es el ATT.** Preguntar por el efecto «en quienes recibieron el programa»
  describe el ATT. En la referencia agregada del escenario, ATE = 3,92 y
  ATT = 4,15; son cantidades distintas. La referencia se consulta solo al final,
  nunca para estimar ni calibrar.

### 2.1 De dónde sale este dataset

«IHDP» nombra tres cosas distintas y conviene no mezclarlas:

| Capa | Qué es | Cifras clave |
|---|---|---|
| **Ensayo real** | *Infant Health and Development Program*, RCT multicéntrico en 8 hospitales de EE. UU. (reclutamiento 1984–85, intervención hasta 1988) | 985 niños: 377 intervención / 608 seguimiento; CI de Stanford–Binet a los 36 meses |
| **Benchmark de Hill (2011)** | Covariables y tratamiento reales, resultados simulados; se borran los tratados con madre no blanca para inducir confusión | 747 unidades: 139 tratados / 608 controles (18,6 %); 25 covariables (6 continuas, 19 binarias) |
| **Este paquete** (`synthetic/ihdp`) | Escenario **íntegramente sintético**, inspirado en el anterior | 747 unidades: 319 tratados / 428 controles (42,7 %); 25 covariables simuladas, **todas continuas** |

**Lo que este paquete NO replica** (y hay que decirlo):

- Las covariables reales del ensayo: aquí son normales estándar simuladas, no
  medidas clínicas de peso, prematurez o salud neonatal.
- La composición 6 continuas + 19 binarias del benchmark: en este escenario las
  25 son continuas, así que **no hay dummies de centro** ni indicadores binarios.
- El desbalance 139/608 (18,6 % de tratados): aquí hay 42,7 % de tratados, casi
  equilibrado.
- La superficie de respuesta no lineal y no paralela del «Setting B» de Hill:
  aquí el resultado es lineal en `X` y `D`.
- El resultado real del ensayo y el CATT fijado en 4 por construcción.

**Consecuencia para la interpretación.** El DGP declara un mecanismo de asignación
basado en covariables observadas, lo que permite plantear el ATE bajo ignorabilidad,
positividad y consistencia/SUTVA. El solapamiento observado en `train` es un
diagnóstico muestral, **no una prueba de positividad poblacional ni de identificación**.
Este escenario sirve para ejercitar estimador, diagnósticos, puerta, registro y
servicio; no reproduce la dificultad científica del problema real ni habilita una
recomendación clínica.

**Fuentes.** Hill, J. L. (2011), *Journal of Computational and Graphical
Statistics* 20(1):217–240, doi:10.1198/jcgs.2010.08162. Infant Health and
Development Program (1990), *JAMA* 263(22):3035–3042. Brooks-Gunn et al. (1994),
*JAMA* 272(16):1257–1262. Para el uso del benchmark en aprendizaje automático
causal: Shalit, Johansson y Sontag (2017), *PMLR* 70:3076–3085; Curth et al.
(2021), *NeurIPS Datasets and Benchmarks*.

## 3. Estrategia de identificación

La estrategia es **ajuste por covariables observadas (backdoor)**: se supone que
las 25 covariables pre-tratamiento bloquean todos los caminos traseros entre
`D` y `Y`. Es la estrategia natural porque:

- el benchmark es un corte transversal sintético;
- `metadata.json` declara que el tratamiento se genera con un modelo logístico
  de propensión en `X` y que los resultados se generan con fórmulas lineales en
  `X`, `D` y ruido;
- `identification.json` lista las 25 covariables como conjunto de ajuste válido.

No se usa variable instrumental, diferencias en diferencias ni regresión
discontinua: no hay instrumento, no hay panel pre/post y no hay umbral que
asigne el tratamiento. «Controlar por todo» no es la justificación; la
justificación es que el diseño del benchmark declara ese conjunto de ajuste.

**Comprobación algebraica ejecutable.** `identificacion_dowhy()` construye el DAG
y ejecuta DoWhy con `method_name="default"`, que aplica el **criterio backdoor**
y extrae el conjunto de ajuste. La evidencia histórica registró
`identificacion_pasa = true`: DoWhy devolvió las 25 covariables y
`coincide_valid_adjustment_sets = true`. La expresión `id-algorithm` es un resumen
algebraico complementario, no una segunda prueba.

**Límite decisivo:** DoWhy/DAG solo comprueba coherencia con el grafo declarado;
**no verifica ignorabilidad** ni ausencia de confusores no observados. La anotación
de `identification.json` describe el benchmark y tampoco es una prueba empírica
independiente de identificación causal. El indicador `pasa`, cuando aparece en la
API, debe leerse con este alcance algebraico.

## 4. Supuestos: validez, evidencia y límites

| Supuesto | Enunciado formal | Por qué es plausible en este DGP | Chequeo empírico | Qué **no** prueba | Clase |
|---|---|---|---|---|---|
| Ignorabilidad condicional | $\{Y_i(0), Y_i(1)\} \perp D_i \mid X_i$ | El tratamiento se simula con un modelo logístico en `X`; el resultado, con fórmulas lineales en `X`, `D` y ruido; no hay confusor latente simulado | Balance (SMD), placebo de tratamiento y placebo de resultado | Es una propiedad del DGP sintético; no se verifica con los datos observados ni se generaliza a IHDP real | `no_observable` |
| Soporte común / positividad | $0 < P(D_i=1 \mid X_i=x) < 1$ | En la validación local de `v0008`, las propensiones **OOF antes del trimming** quedaron en $[0{,}043; 0{,}916]$, con solape 0,99777 (≈99,8 %; la CLI puede redondearlo a 100 %) y ESS = 332,2076/448 = 0,7415 (≈332/448 y 0,74) | Rango OOF de $\hat e$, fracción en solape antes del trimming, ESS y unidades recortadas; el servicio se abstiene fuera del rango de entrenamiento | El solapamiento muestral no garantiza positividad poblacional; los rangos marginales no garantizan soporte multivariable; $\hat e$ es estimada | `observable` |
| Consistencia / SUTVA | $Y_i = Y_i(D_i)$; $Y_i(d)$ no depende de $D_j$ para $j \ne i$; una sola versión del tratamiento | El DGP es unitario, con ruido independiente; cada unidad depende solo de su propio tratamiento | No hay chequeo directo; se declara la limitación | En un programa real puede haber spillovers, equilibrio general o versiones distintas de implementación | `no_observable` |
| Covariables pre-tratamiento | Las 25 covariables se miden antes de `D` | `metadata.json` y `identification.json` lo declaran | La trampa `score_post` muestra qué pasa si se usa una columna derivada de `Y` | `score_post` es una fuga artificial, no una covariable real ni un placebo | `observable` |
| Nuisance models | Al menos el modelo de resultado o el de propensión está bien especificado, además de los supuestos causales | El DGP usa formas lineales; eso no valida automáticamente ambos ajustes muestrales | Cross-fitting, ajuste, balance y comparación de estimadores | Si ambas piernas fallan, AIPW puede sesgarse; coincidir con OLS o con la diferencia ingenua no prueba identificación | `supuesto_de_estimacion` |

En esa corrida, el trimming $[0{,}05; 0{,}95]$ recortó **1 unidad de 448 en total (0,2232 %)**, íntegramente del grupo control (0,3891 % de los controles) y **0 tratadas**. El SMD máximo ponderado OOF fue **0,11**, frente a **0,43** sin ponderar. El rango, el solape y el ESS de la tabla son OOF **antes** del trimming: el 100 % que puede mostrar la CLI es redondeo de 0,99777, no solape perfecto.

**Nota importante:** `score_post` no es un placebo. Es una prueba de fuga de
información: una columna construida con `Y` que vacía el coeficiente del
tratamiento. El placebo real es la permutación de `D` y la permutación de una
covariable como pseudo-resultado (sección 7). Ninguno de estos controles verifica
ignorabilidad. Del mismo modo, la coincidencia entre diferencia ingenua, OLS y AIPW
no prueba identificación: puede deberse a sesgos compartidos.

## 5. Condiciones bajo las cuales el ATE sería identificable

Si se sostienen los supuestos A1–A3:

- **A1. Ignorabilidad condicional:** $\{Y(0), Y(1)\} \perp D \mid X$.
- **A2. Positividad:** $0 < e(X) < 1$ para todo $X$ en la población objetivo.
- **A3. Consistencia/SUTVA:** $Y = Y(D)$ y no hay interferencia.

Entonces:

$$
\begin{aligned}
E[Y(1)] &= E_X\big[E[Y(1) \mid X]\big] \\
        &= E_X\big[E[Y(1) \mid X, D=1]\big] && \text{(A1)} \\
        &= E_X\big[E[Y \mid X, D=1]\big] && \text{(A3)}
\end{aligned}
$$

Análogamente, $E[Y(0)] = E_X[E[Y \mid X, D=0]]$. Por tanto:

$$
\tau = E[Y(1) - Y(0)]
    = E_X\big[E[Y \mid X, D=1] - E[Y \mid X, D=0]\big].
$$

El AIPW es un análogo muestral de ese funcional:

$$
\hat\tau = \frac{1}{n}\sum_i \left[
  \hat\mu_1(X_i) - \hat\mu_0(X_i)
  + \frac{D_i(Y_i - \hat\mu_1(X_i))}{\hat e(X_i)}
  - \frac{(1-D_i)(Y_i - \hat\mu_0(X_i))}{1-\hat e(X_i)}
\right].
$$

La identificabilidad es una propiedad del modelo causal y de A1–A3, no del
estimador. El AIPW es consistente bajo regularidad y especificación correcta de
al menos uno de los dos modelos auxiliares; si ambos nuisance models fallan, puede
sesgarse. La referencia del DGP (ATE ≈ 3,92) no interviene en el argumento ni en
la estimación; se conserva únicamente como antecedente histórico.

**Por qué A2 no es un adorno.** Sin positividad, los contrafactuales no están
identificados para toda la población objetivo aunque el algoritmo produzca un número.
En este paquete se examinan propensiones, ESS y ventanas de estrés, pero esas señales
muestrales no demuestran A2 en la población. Los rangos marginales del servicio
tampoco garantizan que el vector completo de covariables tenga soporte multivariable.

## 6. Estimación, intervalo y evidencia validada localmente

Estimador principal: **AIPW con cross-fitting** $K=5$, semilla 4242. Los
nuisances se ajustan fuera del pliegue que predicen. El OLS con las 25
covariables es el comparador. Las cifras principales proceden de la validación
local ya ejecutada, cuyo champion actual es **`v0008`**; `v0001`–`v0007`
permanecen intactas.

| Cantidad | `synthetic/ihdp` (evidencia `v0008`) |
|---|---|
| Diferencia cruda | 10,3 puntos, IC 95 % aproximado [7,60; 13,05] |
| ATE OLS (comparador) | 4,8 puntos, IC 95 % [3,8; 5,8] |
| **ATE AIPW** | **5,2 puntos, IC 95 % [3,9; 6,4]** |
| Rango de $\hat e$ OOF antes del trimming | [0,043; 0,916] |
| Solape OOF antes del trimming en $[0{,}05; 0{,}95]$ | 0,99777 (≈99,8 %; la CLI puede redondear 100 %) |
| ESS de Kish OOF antes del trimming / n | 332,2076 / 448 = 0,7415 (≈332/448 y 0,74) |
| Unidades recortadas | 1/448 (0,2232 %); todas controles: 0,3891 % de los controles; 0 tratadas |
| SMD máximo sin ponderar | 0,43 |
| SMD máximo ponderado OOF | 0,11 |

Los diagnósticos de rango, solape y ESS de esta tabla son **OOF anteriores al
trimming**. El porcentaje de solape no es exactamente 100 %: se trata de 0,99777
redondeado por la presentación de la CLI.

La trampa `score_post` (−0,1) y el $R^2$ de 0,095 de la proyección de
heterogeneidad se conservan como antecedentes históricos en `BITACORA.md`
§5/§8.6, no como cifras nuevas atribuidas aquí a `v0008`.

**Validación por particiones (registro histórico).** La tabla siguiente conserva
las cifras de la corrida original, anteriores a la validación OOF de `v0008`. El
estimando primario es el de `train`. Las otras particiones son un chequeo de
estabilidad, no un holdout aleatorizado ni una prueba de ignorabilidad:

| Partición | n | ATE AIPW | IC 95 % |
|---|---:|---:|---|
| train | 448 | 5,16 | [3,93; 6,38] |
| validation | 149 | 1,93 | [−2,45; 6,31] |
| test | 150 | 1,63 | [−3,91; 7,18] |

Los ATE de `validation` y `test` son más bajos y sus intervalos son anchos; los
IC se solapan con el de `train`, pero la evidencia no confirma una estabilidad
precisa. Se reporta así, sin ocultar la diferencia.

**Estratos predeclarados (registro histórico).** Estas cifras también pertenecen
a la corrida original. El corte es `bw` en la mediana de `train`, declarado antes
de mirar los efectos:

| Estrato | n | Efecto | IC 95 % |
|---|---:|---:|---|
| `bw` alto (> mediana) | 224 | 7,2 | [5,5; 8,8] |
| `bw` bajo (≤ mediana) | 224 | 3,2 | [1,4; 4,9] |

No es un CATE: son dos medias de scores AIPW con su IC. El corte no se eligió
por ganancia de varianza.

## 7. Sensibilidad y placebo

Los valores de esta sección pertenecen a la evidencia histórica. Son análisis de
sensibilidad y diagnósticos, no pruebas de identificación ni resultados de cobertura
Monte Carlo.

### 7.1 E-value (aproximado para resultado continuo)

- Efecto estandarizado: $d = 5{,}16 / 15{,}04 = 0{,}343$.
- **E-value puntual: 2,07.**
- **E-value del límite del IC más cercano a cero: 1,85.**
- Lectura: un confusor no medido tendría que asociarse con `D` y `Y`,
  condicionando en `X`, con una razón de riesgos aproximada de al menos 2,07
  para explicar el efecto puntual; el límite del IC exige al menos 1,85.
- Límite: el resultado es continuo; la RR es una aproximación vía efecto
  estandarizado, no una RR literal. Es una heurística, no una cota exacta.
- **Alcance:** el E-value solo cuantifica confusión no observada bajo sus supuestos.
  No cubre errores de especificación de los nuisance models, fallos de positividad
  ni violaciones de consistencia/SUTVA, y no demuestra que exista ignorabilidad.

### 7.2 Valor de robustez (Cinelli–Hazlett, OLS)

- $t = 9{,}71$, $df = 421$.
- **RV = 37,4 %.**
- Lectura: un confusor no medido tendría que explicar al menos el 37,4 % del
  R² parcial de `D` y de `Y`, después de condicionar en `X`, para llevar el
  coeficiente OLS a cero.
- Límite: es exacto bajo el modelo lineal de sesgo por omisión para el OLS; no
  es una propiedad exacta del AIPW. Se reporta como lente complementaria.

### 7.3 Cotas de Manski sin ignorabilidad

- **ATE ∈ [−37,66; 48,48] puntos**, ancho 86,13; incluye cero.
- Se calculan con `E[Y|D=d]` en cada brazo y acotan la parte no observada del
  resultado potencial mediante el soporte de `Y`. No suponen ignorabilidad
  condicional, aunque sí consistencia/SUTVA y resultado acotado.
- Aquí se usa el rango observado de entrenamiento, **Y ∈ [10,41; 96,54]**. Es un
  supuesto explícito de ilustración: los extremos muestrales no garantizan el
  soporte poblacional, por lo que no son cotas poblacionales garantizadas.
- Lectura: sin ignorabilidad no hay identificación puntual ni evidencia de un
  signo; estas cotas no sustituyen al AIPW ni sirven como puerta automática.

### 7.4 Placebo de tratamiento permutado — **pasa**

- 200 réplicas, semilla 4242, pliegues fijos.
- ATE observado: 5,16. Placebo: media −0,04, DE 0,62, IC 95 % [−1,42; 1,06].
- Percentil del ATE observado: 100. **p Monte Carlo = 0,005.**
- Lectura: bajo efecto cero, los placebo se centran en 0; el ATE observado es
  extremo. Esto evalúa calibración e implementación.
- **No prueba ignorabilidad**: un estimador confundido también puede rechazar
  la nula de placebo.

### 7.5 Placebo de resultado permutado — **pasa**

- Se permutó `momage` y se usó como pseudo-resultado, manteniendo `X` original.
- Efecto: 0,04; IC 95 % [−0,23; 0,32]; umbral material: 0,10.
- Lectura: el placebo de resultado no muestra un efecto material.
- **No prueba ausencia de confusión**: es un diagnóstico de calibración con un
  resultado sin relación causal con `D`.

### 7.6 Acción de la puerta

- Si el placebo de tratamiento falla o el placebo de resultado es material:
  `revisar_identificacion`.
- Si el soporte se rompe: `abstenerse` (sin número).
- Si hay deriva de covariables: `reentrenar`.
- Si el balance ponderado o la estabilidad del efecto se deterioran: `alertar`.
- Si todo está dentro de umbral: `continuar`.

## 8. Decisiones propias y diferencias con el caso guiado

1. **Corte de heterogeneidad en `bw`.** Se usa la mediana de `train` como regla
   didáctica predeclarada. El nombre está inspirado en peso al nacer, pero aquí es
   una covariable simulada, no una medida clínica. No se elige por ganancia de
   varianza. En el caso guiado (`jobs`) el corte es `nodegree`.
2. **Umbrales iniciales para `ihdp`.** `smd_max = 0,50`,
   `smd_ponderado_max = 0,25`, `psi_alerta = 0,25`, `solape_min = 0,30`,
   `efecto_estabilidad = 0,20`. Son convenciones iniciales, no leyes
   universales; se documentan en la tarjeta.
3. **Ventanas de estrés.** Deriva de `bw` en +1 DE, positividad sobre `bw`,
   balance sobre `momage` y un confusor oculto simulado. En `jobs` las ventanas
   son `age`, `re74` y `educ`.
4. **Sensibilidad y placebo.** Se eligió E-value + valor de robustez + cotas de
   Manski, y placebo de tratamiento + placebo de resultado. Las primeras miden
   sensibilidad a confusores no observados bajo supuestos distintos; Manski
   muestra qué queda sin ignorabilidad. Ninguna medida prueba la identificación.

**Reutilización declarada:** se reutilizan el estimador AIPW con cross-fitting,
el esquema de tarjeta, la puerta, el registro con manifiesto y el monitor del
prototipo abierto. Se adaptan las 25 covariables, el corte `bw`, los umbrales,
las ventanas y la capa de sensibilidad/placebo. El caso sigue siendo guiado; por
eso 1.1 queda en parcial.

## 9. Cierre para un lector no técnico

**Lectura didáctica de la evidencia histórica.** La corrida conservada produjo un
ATE AIPW de unos **5,2 puntos**, con IC 95 % de **3,9 a 6,4 puntos**. Describe una
salida del DGP sintético bajo los supuestos declarados; no es una recomendación de
ampliar ningún programa ni una estimación validada de nuevo por esta actualización.

**Qué aportan los controles.** El ajuste por 25 covariables implementa una estrategia
backdoor condicional, el solapamiento y ESS describen el soporte observado y los
placebos examinan calibración. Ninguno verifica ignorabilidad. El E-value explora
confusión no observada bajo supuestos, pero no errores de especificación, positividad
o SUTVA. Las cotas de Manski recuerdan que, sin ignorabilidad, no hay identificación
puntual con esos supuestos de acotación.

**Cuándo abstenerse o revisar.**

- Si el monitor detecta deriva que exige revisión antes de reentrenar.
- Si el soporte se rompe: el servicio se abstiene sin devolver un número.
- Si un placebo o control negativo falla: se revisa la estrategia, no se declara
  automáticamente refutada o probada la ignorabilidad.
- Si particiones adicionales muestran inestabilidad o intervalos demasiado anchos.
- Si cambian la población, el tratamiento o sus versiones: hay que reabrir el
  estimando y los supuestos de consistencia/SUTVA.

**Lo que este cierre no dice.** No afirma efectos en niños reales ni sustituye un
ensayo aleatorizado. No autoriza decisiones clínicas, laborales o de política pública.
Es una demostración metodológica local sobre datos sintéticos, no un sistema desplegado.

## 10. Qué no afirma esta entrega

- No estima un CATE ni un efecto individual identificado. `POST /heterogeneidad`
  devuelve `proyeccion`, IC **condicional al ajuste** y advertencias. El $R^2 = 0,095$
  citado es un valor histórico de discriminación baja, no una validación causal.
  `POST /efecto_individual` queda como **alias deprecado** con el mismo núcleo.
- No estima políticas ni efectos de intervenciones distintas de la observada.
- DoWhy/DAG no verifica ignorabilidad; los rangos marginales no garantizan soporte
  multivariable; la coincidencia ingenuo/OLS/AIPW no prueba identificación.
- El E-value no cubre error de especificación, positividad ni consistencia/SUTVA.
- No usa la verdad del escenario para estimar, decidir ni calibrar umbrales.
- No generaliza a IHDP real ni a otra población, y no recomienda intervenciones
  clínicas o laborales.

## 11. Reproducibilidad y evidencia

La validación local ya ejecutada utilizó, desde la raíz del repositorio:

```sh
SIC_ESCENARIO=synthetic/ihdp .venv_ci/bin/python cobertura.py
SIC_ESCENARIO=synthetic/ihdp make PYTHON=.venv_ci/bin/python evidencia
```

El segundo comando regenera artefactos y evidencia y promovió `v0008`; no es una
comprobación de solo lectura. Las pruebas y el humo quedaron verdes (`PRUEBAS: OK`,
`HUMO: OK`). El champion actual es **`v0008`** y las versiones `v0001`–`v0007`
permanecen intactas. Esta actualización documental no promovió versiones nuevas.

### Cobertura Monte Carlo ya ejecutada

Se ejecutó con `n = 500`, `R = 100` y semilla `20261111` en un **DGP ilustrativo
propio**. Los resultados son:

| Intervalo | Cobertura | Error Monte Carlo |
|---|---:|---:|
| AIPW | 0,97 | 0,01706 |
| OLS | 0,96 | 0,01960 |
| Ingenuo | 0,00 | 0 |

La cobertura AIPW difiere del nominal 0,95 en **0,02**, desviación que **no está
dentro de ±1 error MC** (0,01706). Por tanto, no se afirma calibración exacta.
Estas coberturas pertenecen únicamente al DGP ilustrativo propio: no son coberturas
de IHDP/jobs ni demuestran identificación.

Las dependencias están fijadas con versiones exactas en `requirements.txt`. Los
artefactos son JSON, no `pickle`/`joblib`.

Artefactos principales:

- `artifacts/estimacion.json` — ATE, IC y diagnósticos OOF.
- `artifacts/sensibilidad.json` y `artifacts/placebo.json` — bloques separados
  para evidencia.
- `artifacts/registro/v0008/` — estimación, tarjeta y manifiesto del champion actual.
- `artifacts/registro/v0001/` a `artifacts/registro/v0007/` — versiones históricas
  intactas.
- `artifacts/alias_champion.json` — alias que apunta a `v0008`.
- `artifacts/monitor_estado.json` — ventanas y sensibilidad de umbrales ±20 % ya
  implementada.
- `artifacts/cobertura.json` — cobertura Monte Carlo del DGP ilustrativo propio.

| Resultado o evidencia | Archivo |
|---|---|
| Cruda 10,3 [7,60; 13,05] aprox.; OLS 4,8 [3,8; 5,8]; AIPW 5,2 [3,9; 6,4] | `evidencia/02_estimacion.txt` |
| OOF antes del trimming: rango [0,043; 0,916], solape 0,99777, ESS 332,2076/448; 1 unidad recortada; SMD ponderado 0,11 | `evidencia/02_estimacion.txt` |
| E-value 2,07 / RV 37,4 % / Manski [−37,66; 48,48] | `evidencia/03_sensibilidad.txt` |
| Placebo D p=0,005; placebo Y 0,04 [−0,23; 0,32] | `evidencia/04_placebo.txt` |
| Puerta, ventanas y sensibilidad ±20 %: 0 cambios de acción fuera de la clasificación base | `evidencia/05_puerta.txt` |
| `v0008`, manifiesto y alias champion | `evidencia/06_registro.txt` |
| Servicio, abstención y humo | `evidencia/07_servicio.txt` |
| DAG | `evidencia/08_dag.txt` |
| Pruebas verdes | `evidencia/09_pruebas.txt` |
| Cobertura Monte Carlo y errores MC | `evidencia/10_cobertura.txt`, `evidencia/10_cobertura.json` |

Los 0 cambios de acción al variar los umbrales ±20 % describen solo esta corrida;
no constituyen una calibración universal. Además, `synthetic/jobs` pasó validación de
datos y estimación sin escribir artefactos: AIPW 1638,6029 [1001,5516; 2275,6542],
propensiones OOF [0,0681763; 0,5595719], solape 1,0, ESS 702,6543 y cero recortes.
Docker alcanzó `healthy` como usuario no-root; los endpoints y la abstención fueron
verificados, y sus recursos temporales se eliminaron. `make dag && make cierre`
regeneró los cuatro SVG y el PDF de 14 páginas. Los detalles están en
`docs/BITACORA.md` §17; estas comprobaciones no promovieron versiones nuevas.

## 12. Defensa (15 minutos)

10 minutos de exposición y 5 de preguntas. Las tres preguntas fijas, con el
artefacto que se mostraría:

1. **Muestre el artefacto que justifica la abstención o el estado de la puerta.**
   Mostrar `artifacts/monitor_estado.json` y `evidencia/05_puerta.txt`, junto con
   `evidencia/06_registro.txt` para identificar el champion `v0008`. Para la
   abstención por soporte, mostrar `evidencia/07_servicio.txt`. En positividad,
   distinguir el rango, solape y ESS OOF antes del trimming de la unidad recortada
   y del SMD ponderado OOF 0,11 en `evidencia/02_estimacion.txt`.
2. **Nombre un supuesto no observable y explique cómo exploró su sensibilidad.**
   Ignorabilidad condicional; la evidencia conservada usa E-value 2,07 (IC 1,85) y
   valor de robustez OLS 37,4 % bajo sus respectivos supuestos, complementados con
   Manski [−37,66; 48,48], en `evidencia/03_sensibilidad.txt`. Explicar que no
   verifican ignorabilidad ni cubren errores de especificación, positividad o SUTVA.
3. **¿Qué cambio mínimo en la evidencia, la población o el umbral exigiría
   abstenerse o revisar la estimación?**
   Una ruptura de soporte; una deriva que el monitor clasifique como revisión o
   abstención; un fallo de placebo que obligue a revisar la estrategia; o sensibilidad
   material a confusión no observada bajo los supuestos del análisis. Mostrar
   `evidencia/04_placebo.txt` y `evidencia/05_puerta.txt`. La sensibilidad ±20 % ya
   está implementada con factores `.8`, `1` y `1.2`: produjo 0 cambios de acción
   fuera de la clasificación base en esta corrida, sin demostrar calibración universal.

Para defender cobertura, mostrar `evidencia/10_cobertura.txt` y limitar la afirmación
al DGP ilustrativo propio: AIPW 0,97 con error MC 0,01706 está a 0,02 del nominal
0,95 y no dentro de ±1 error MC; no corresponde a IHDP/jobs.

Si no se puede mostrar el artefacto o reproducir la cifra, ese resultado no
cuenta como evidencia propia.
