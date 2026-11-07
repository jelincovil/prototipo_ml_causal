# Pregunta causal y cierre — `real/ihdp`

**Escenario:** `real/ihdp` del benchmark local, sintético y generado con un DGP
estilo Hill (2011). Los identificadores `real/*` son nombres de escenario, no
datos reales. Este documento se declara antes de mirar los efectos y se completa
después con las cifras reproducibles del prototipo.

## 1. Pregunta de decisión

> **¿Debe ampliarse el programa de intervención temprana a la población del
> estudio para mejorar el puntaje cognitivo a los 3,5 años?**

Es la forma de decisión de la pregunta guiada. El caso sigue siendo uno de los
casos guiados del curso; por eso el subcriterio 1.1 de la rúbrica queda en
**parcial**, no en completo. El estimando implementado es el **ATE**.

## 2. Estimando, población y unidad

- **Estimando:** ATE de `treatment` sobre `outcome` (efecto total).
- **Unidad:** puntos del test cognitivo a los 3,5 años.
- **Población:** las 448 unidades de `observed_train.csv` del escenario
  `real/ihdp` (partición de entrenamiento, hash verificado contra `splits.json`).
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
| **Este paquete** (`real/ihdp`) | Escenario **íntegramente sintético**, inspirado en el anterior | 747 unidades: 319 tratados / 428 controles (42,7 %); 25 covariables simuladas, **todas continuas** |

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

**Consecuencia para la identificación.** Al no eliminar tratados, el soporte
común se sostiene (100 % de `train` en la zona de solape) y el ATE es
identificable. En el benchmark canónico, en cambio, el filtrado rompe el
solapamiento —no quedan madres no blancas tratadas— y el ATE deja de estar
identificado; allí el estimando defendible es el ATT. Nuestro escenario es, por
tanto, **más fácil** que el publicado: valida la maquinaria (estimador,
diagnósticos, puerta, registro, servicio), no la dificultad científica del
problema real.

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

**Límite:** la anotación de `identification.json` es una anotación del
benchmark, no una prueba independiente de identificación causal. En datos
reales, esta estrategia exige defender la ignorabilidad, no solo listar
covariables.

## 4. Supuestos: validez, evidencia y límites

| Supuesto | Enunciado formal | Por qué es plausible en este DGP | Chequeo empírico | Qué **no** prueba | Clase |
|---|---|---|---|---|---|
| Ignorabilidad condicional | $\{Y_i(0), Y_i(1)\} \perp D_i \mid X_i$ | El tratamiento se simula con un modelo logístico en `X`; el resultado, con fórmulas lineales en `X`, `D` y ruido; no hay confusor latente simulado | Balance (SMD), placebo de tratamiento y placebo de resultado | Es una propiedad del DGP sintético; no se verifica con los datos observados ni se generaliza a IHDP real | `no_observable` |
| Soporte común / positividad | $0 < P(D_i=1 \mid X_i=x) < 1$ | La propensión estimada vive en $[0{,}071; 0{,}887]$; el 100 % de `train` cae en $[0{,}05; 0{,}95]$; ESS de Kish = 388/448 (0,87) | Rango de $\hat e$, fracción en solape y ESS; el servicio se abstiene fuera del rango de entrenamiento | El solapamiento muestral no garantiza positividad poblacional ni para perfiles nuevos; $\hat e$ es estimada, no conocida | `observable` |
| Consistencia / SUTVA | $Y_i = Y_i(D_i)$; $Y_i(d)$ no depende de $D_j$ para $j \ne i$; una sola versión del tratamiento | El DGP es unitario, con ruido independiente; cada unidad depende solo de su propio tratamiento | No hay chequeo directo; se declara la limitación | En un programa real puede haber spillovers, equilibrio general o versiones distintas de implementación | `no_observable` |
| Covariables pre-tratamiento | Las 25 covariables se miden antes de `D` | `metadata.json` y `identification.json` lo declaran | La trampa `score_post` muestra qué pasa si se usa una columna derivada de `Y` | `score_post` es una fuga artificial, no una covariable real ni un placebo | `observable` |

**Nota importante:** `score_post` no es un placebo. Es una prueba de fuga de
información: una columna construida con `Y` que vacía el coeficiente del
tratamiento. El placebo real es la permutación de `D` y la permutación de una
covariable como pseudo-resultado (sección 7).

## 5. Por qué el ATE es identificable

Con los supuestos A1–A3:

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
al menos uno de los dos modelos auxiliares. La referencia del DGP (ATE ≈ 3,92)
no interviene en la prueba ni en la estimación; se compara solo al final.

**Por qué A2 no es un adorno aquí.** En el benchmark canónico de Hill el filtrado
elimina a todos los tratados con madre no blanca: en ese estrato no queda ninguna
unidad tratada, la positividad falla y el ATE deja de estar identificado. En este
paquete el DGP no borra unidades tratadas —solo simula un tratamiento logístico
en `X`—, así que A2 se sostiene sobre `train` y el ATE es identificable. La
diferencia es del escenario, no del estimador (sección 2.1).

## 6. Estimación, intervalo y validación

Estimador principal: **AIPW con cross-fitting** $K=5$, semilla 4242. Los
nuisances se ajustan fuera del pliegue que predicen. El OLS con las 25
covariables es el comparador.

| Cantidad | `real/ihdp` |
|---|---|
| Diferencia cruda | 10,3 puntos |
| ATE OLS (comparador) | 4,8 puntos, IC 95 % [3,8; 5,8] |
| **ATE AIPW** | **5,2 puntos, IC 95 % [3,9; 6,4]** |
| ESS de Kish / n | 388 / 448 (0,87) |
| Rango de $\hat e$ | [0,071; 0,887] |
| Fracción en solape $[0{,}05; 0{,}95]$ | 100 % |
| SMD máximo sin ponderar | 0,43 |
| SMD máximo ponderado por IPW | 0,03 |
| Trampa `score_post` | −0,1 (el coeficiente se vació) |
| $R^2$ de la proyección individual | 0,095 (discriminación baja) |

**Validación por particiones.** El estimando primario es el de `train`. Las
otras particiones son un chequeo de estabilidad, no un holdout aleatorizado ni
una prueba de ignorabilidad:

| Partición | n | ATE AIPW | IC 95 % |
|---|---:|---:|---|
| train | 448 | 5,16 | [3,93; 6,38] |
| validation | 149 | 1,93 | [−2,45; 6,31] |
| test | 150 | 1,63 | [−3,91; 7,18] |

Los ATE de `validation` y `test` son más bajos y sus intervalos son anchos; los
IC se solapan con el de `train`, pero la evidencia no confirma una estabilidad
precisa. Se reporta así, sin ocultar la diferencia.

**Estratos predeclarados.** El corte es `bw` en la mediana de `train`, declarado
antes de mirar los efectos:

| Estrato | n | Efecto | IC 95 % |
|---|---:|---:|---|
| `bw` alto (> mediana) | 224 | 7,2 | [5,5; 8,8] |
| `bw` bajo (≤ mediana) | 224 | 3,2 | [1,4; 4,9] |

No es un CATE: son dos medias de scores AIPW con su IC. El corte no se eligió
por ganancia de varianza.

## 7. Sensibilidad y placebo

### 7.1 E-value (aproximado para resultado continuo)

- Efecto estandarizado: $d = 5{,}16 / 15{,}04 = 0{,}343$.
- **E-value puntual: 2,07.**
- **E-value del límite del IC más cercano a cero: 1,85.**
- Lectura: un confusor no medido tendría que asociarse con `D` y `Y`,
  condicionando en `X`, con una razón de riesgos aproximada de al menos 2,07
  para explicar el efecto puntual; el límite del IC exige al menos 1,85.
- Límite: el resultado es continuo; la RR es una aproximación vía efecto
  estandarizado, no una RR literal. Es una heurística, no una cota exacta.

### 7.2 Valor de robustez (Cinelli–Hazlett, OLS)

- $t = 9{,}71$, $df = 421$.
- **RV = 37,4 %.**
- Lectura: un confusor no medido tendría que explicar al menos el 37,4 % del
  R² parcial de `D` y de `Y`, después de condicionar en `X`, para llevar el
  coeficiente OLS a cero.
- Límite: es exacto bajo el modelo lineal de sesgo por omisión para el OLS; no
  es una propiedad exacta del AIPW. Se reporta como lente complementaria.

### 7.3 Placebo de tratamiento permutado

- 200 réplicas, semilla 4242, pliegues fijos.
- ATE observado: 5,16. Placebo: media −0,04, DE 0,62, IC 95 % [−1,42; 1,06].
- Percentil del ATE observado: 100. **p Monte Carlo = 0,005.**
- Lectura: bajo efecto cero, los placebo se centran en 0; el ATE observado es
  extremo. Esto evalúa calibración e implementación.
- **No prueba ignorabilidad**: un estimador confundido también puede rechazar
  la nula de placebo.

### 7.4 Placebo de resultado permutado

- Se permutó `momage` y se usó como pseudo-resultado, manteniendo `X` original.
- Efecto: 0,04; IC 95 % [−0,23; 0,32]; umbral material: 0,10.
- Lectura: el placebo de resultado no muestra un efecto material.
- **No prueba ausencia de confusión**: es un diagnóstico de calibración con un
  resultado sin relación causal con `D`.

### 7.5 Acción de la puerta

- Si el placebo de tratamiento falla o el placebo de resultado es material:
  `revisar_identificacion`.
- Si el soporte se rompe: `abstenerse` (sin número).
- Si hay deriva de covariables: `reentrenar`.
- Si el balance ponderado o la estabilidad del efecto se deterioran: `alertar`.
- Si todo está dentro de umbral: `continuar`.

## 8. Decisiones propias y diferencias con el caso guiado

1. **Corte de heterogeneidad en `bw`.** Se usa la mediana de `train` porque el
   bajo peso al nacer define la población clínica del IHDP; se declara antes de
   mirar los efectos y no se elige por ganancia de varianza. En el caso guiado
   (`jobs`) el corte es `nodegree`.
2. **Umbrales recalibrados para `ihdp`.** `smd_max = 0,50`,
   `smd_ponderado_max = 0,25`, `psi_alerta = 0,25`, `solape_min = 0,30`,
   `efecto_estabilidad = 0,20`. Son convenciones iniciales, no leyes
   universales; se documentan en la tarjeta.
3. **Ventanas de estrés.** Deriva de `bw` en +1 DE, positividad sobre `bw`,
   balance sobre `momage` y un confusor oculto simulado. En `jobs` las ventanas
   son `age`, `re74` y `educ`.
4. **Sensibilidad y placebo.** Se eligió E-value + valor de robustez y placebo
   de tratamiento + placebo de resultado, en lugar de una única medida, porque
   el resultado es continuo y ninguna medida individual es exacta para el AIPW.

**Reutilización declarada:** se reutilizan el estimador AIPW con cross-fitting,
el esquema de tarjeta, la puerta, el registro con manifiesto y el monitor del
prototipo abierto. Se adaptan las 25 covariables, el corte `bw`, los umbrales,
las ventanas y la capa de sensibilidad/placebo. El caso sigue siendo guiado; por
eso 1.1 queda en parcial.

## 9. Cierre para un lector no técnico

**Decisión recomendada (en el escenario sintético).** El programa muestra un
efecto promedio positivo de unos **5,2 puntos** en el test cognitivo, con un
intervalo de confianza de **3,9 a 6,4 puntos**. La estimación es compatible con
un beneficio promedio, pero no es una garantía para un niño concreto ni para
una población real.

**Qué sostiene la recomendación.** El resultado se apoya en un ajuste por 25
covariables observadas, un buen solapamiento entre tratados y controles, un
placebo de tratamiento que se comporta como se espera y un placebo de resultado
sin efecto material. La sensibilidad indica que un confusor no medido tendría
que ser moderadamente fuerte (RR aproximada ≥ 2,07) para explicar el efecto.

**Cuándo dejar de confiar.**

- Si la población cambia y el monitor detecta deriva (`reentrenar`).
- Si el solapamiento se rompe (`abstenerse`): el servicio no devuelve número.
- Si el placebo o el control negativo fallan (`revisar_identificacion`).
- Si la validación en otras particiones sigue mostrando estimaciones muy
  distintas y los intervalos no permiten decidir.
- Si el coste o el riesgo de la intervención exige un efecto mayor que el que
  el IC permite descartar.

**Lo que este cierre no dice.** No dice que el programa funcione en niños
reales, no reemplaza un ensayo aleatorizado y no autoriza decisiones clínicas,
laborales o de política pública. Es una demostración metodológica sobre datos
sintéticos.

## 10. Qué no afirma esta entrega

- No estima un CATE validado: la respuesta por perfil es una proyección lineal
  del score AIPW, con $R^2 = 0,095$ y discriminación baja.
- No estima políticas ni efectos de intervenciones distintas de la observada.
- No prueba ignorabilidad, positividad poblacional ni SUTVA: las declara o las
  acota.
- No usa la verdad del escenario para estimar, decidir ni calibrar umbrales.
- No generaliza a IHDP real ni a otra población.

## 11. Reproducibilidad y evidencia

Desde la raíz del repositorio:

```sh
SIC_ESCENARIO=real/ihdp make demo
SIC_ESCENARIO=real/ihdp make pruebas
make evidencia
shasum -a 256 -c evidencia/SHA256SUMS
```

Artefactos principales:

- `artifacts/estimacion.json` — ATE, IC, diagnósticos, sensibilidad, placebo,
  validación por particiones.
- `artifacts/sensibilidad.json` y `artifacts/placebo.json` — bloques separados
  para evidencia.
- `artifacts/registro/v0004/` — estimación, tarjeta y manifiesto de la versión
  campeona al momento de escribir este documento.
- `artifacts/alias_champion.json` — alias de la versión campeona.
- `artifacts/monitor_estado.json` — ventana de producción y ventanas de estrés.

| Cifra | Evidencia |
|---|---|
| ATE 5,2 [3,9; 6,4] | `evidencia/02_estimacion.txt` |
| E-value 2,07 / RV 37,4 % | `evidencia/03_sensibilidad.txt` |
| Placebo D p=0,005; placebo Y 0,04 [−0,23; 0,32] | `evidencia/04_placebo.txt` |
| ESS 388/448; rango e [0,071; 0,887] | `evidencia/02_estimacion.txt` |
| Puerta de producción y ventanas | `evidencia/05_puerta.txt` |
| Versión, manifiesto y alias | `evidencia/06_registro.txt` |
| Servicio y abstención | `evidencia/07_servicio.txt` |
| DAG | `evidencia/08_dag.txt` |
| Pruebas | `evidencia/09_pruebas.txt` |

`v0001` a `v0003` se conservan inmutables; `v0004` es la versión campeona de
esta corrida. Si se vuelve a ejecutar la cadena, se crea una versión nueva y el
alias se actualiza.

## 12. Defensa (15 minutos)

10 minutos de exposición y 5 de preguntas. Las tres preguntas fijas, con el
artefacto que se mostraría:

1. **Muestre el artefacto que justifica la abstención o el estado de la puerta.**
   Mostrar `artifacts/monitor_estado.json` (ventana de producción y ventanas de
   estrés) y `evidencia/05_puerta.txt`. Para la abstención por soporte, mostrar
   `evidencia/07_servicio.txt`.
2. **Nombre un supuesto no observable y explique cómo lo acotó.**
   Ignorabilidad condicional; se acota con E-value 2,07 (IC 1,85) y valor de
   robustez OLS 37,4 %, en `evidencia/03_sensibilidad.txt`. Explicar que no es
   una prueba y que en datos reales no se verifica.
3. **¿Qué cambio mínimo en la evidencia, la población o el umbral haría que
   dejara de recomendar la intervención?**
   Un confusor no medido con asociación aproximada menor que 2,07; un fallo del
   placebo o del control negativo; una ruptura de solapamiento; o una deriva
   que el monitor clasifique como `reentrenar` o `abstenerse`. Mostrar
   `evidencia/04_placebo.txt` y `evidencia/05_puerta.txt`.

Si no se puede mostrar el artefacto o reproducir la cifra, ese resultado no
cuenta como evidencia propia.
