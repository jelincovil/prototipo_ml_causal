#set document(title: "Datos, estimando y método — Prototipo Puente")
#set page(paper: "a4", margin: 2.2cm, numbering: "1",
  footer: context [#set text(size: 8pt, fill: luma(110)); Prototipo Puente · semana 4 #h(1fr) #counter(page).display()])
#set text(size: 10.5pt, lang: "es")
#set par(justify: true, leading: 0.62em)
#set list(spacing: 0.45em, indent: 0.9em, body-indent: 0.25em)
#show heading.where(level: 1): it => block(above: 1.4em, below: 0.85em,
  sticky: true, text(size: 15pt, fill: rgb("#1f3a5f"), it))
#show heading.where(level: 2): it => block(above: 1.15em, below: 0.55em,
  sticky: true, text(size: 11.5pt, fill: rgb("#1f3a5f"), it))
#show table: it => {
  set par(justify: false)
  set table(stroke: 0.45pt + luma(210))
  it
}
#show raw.where(block: true): it => block(
  width: 100%,
  inset: (x: 9pt, y: 7pt),
  radius: 3pt,
  fill: rgb("#f5f6f8"),
  stroke: 0.4pt + luma(215),
  it,
)

#import "@preview/cetz:0.3.4"

= Datos, estimando y método

#v(0.2em)

#text(size: 9.5pt, fill: luma(80))[
  Prototipo «Puente» — semana 4 · escenario `real/ihdp` · documento de referencia
  del benchmark sintético, del estimando y del prototipo en producción local.
]

#v(0.5em)

// ---------------------------------------------------------------
// Figura de apertura: flujo del repositorio. Etiquetas editables.
// ---------------------------------------------------------------
#let flujo_etapas = (
  ("observed_train.csv", "datos observados + split"),
  ("datos.py",           "roles, hashes y pared"),
  ("estimacion.py",      "AIPW + IC + sensibilidad + placebo"),
  ("registro.py",        "tarjeta + versión + alias"),
  ("monitor.py",         "5 ventanas + puerta de 5 acciones"),
  ("servicio.py",        "FastAPI + bundle champion"),
)
#let flujo_api_nombre = "API"
#let flujo_api_respuesta = "respuesta: /efecto · /consulta · /efecto_individual"
#let flujo_api_abstencion = "abstención (fuera de rango o puerta falla)"
#let flujo_gate_bloqueo = "alerta / falla"

#figure(
  cetz.canvas(length: 1cm, {
    import cetz.draw: *

    let w = 13.4
    let h = 2.4
    let gap = 0.45
    let step = h + gap
    let n = flujo_etapas.len()
    let split-x = 4.8
    let y-api-extra = 0.45

    for (i, (nombre, desc)) in flujo_etapas.enumerate() {
      let y0 = -i * step
      let y1 = y0 + h
      let id = "b" + str(i)
      let fill = if i == 4 { rgb("#fdf6e3") } else { rgb("#eef3f9") }
      let ym = (y0 + y1) / 2
      rect((0, y0), (w, y1), fill: fill, stroke: 0.5pt + luma(170), name: id)
      content((0.4, ym), text(font: "DejaVu Sans Mono", weight: "bold", size: 10pt)[#nombre],
        anchor: "west")
      content((split-x, ym), text(size: 10pt)[#desc], anchor: "west")
    }

    // La caja de la API lleva un hueco propio respecto de la última etapa.
    let y-api-1 = -((n - 1) * step + gap)
    let y-api-0 = y-api-1 - (h + y-api-extra)
    rect((0, y-api-0), (w, y-api-1), fill: rgb("#e0f2f1"),
         stroke: 0.6pt + rgb("#0e7490"), name: "bapi")
    let y-api-m = (y-api-0 + y-api-1) / 2
    content((0.4, y-api-m + 0.3),
            text(font: "DejaVu Sans Mono", weight: "bold", size: 10pt)[#flujo_api_nombre],
            anchor: "west")
    content((split-x, y-api-m + 0.26),
            text(size: 8.5pt)[#flujo_api_respuesta], anchor: "west")
    content((split-x, y-api-m - 0.3),
            text(size: 8.5pt)[#flujo_api_abstencion], anchor: "west")

    for i in range(n - 1) {
      line("b" + str(i) + ".south", "b" + str(i + 1) + ".north", mark: (end: ">"))
    }
    line("b5.south", "bapi.north", mark: (end: ">"))

    line(
      "b4.east",
      (w + 0.45, -4 * step + h / 2),
      (w + 0.45, -5 * step + h / 2),
      "b5.east",
      mark: (end: ">"),
      stroke: (dash: "dashed", paint: rgb("#b45309")),
    )
    content(
      (w + 0.6, (-4 * step - 5 * step + h) / 2),
      text(size: 9pt, fill: rgb("#b45309"))[#flujo_gate_bloqueo],
      anchor: "west",
    )
  }),
  caption: [
    *Flujo del trabajo.* Cada etapa consume los artefactos de la anterior. Azul:
    pipeline; ámbar: puerta; verde: servicio. La flecha discontinua indica que
    `alerta` o `falla` detiene el despliegue.
  ],
)

#pagebreak()

#figure(
  image("figuras/modulos.svg", width: 100%),
  caption: [
    *Dependencias entre módulos.* La flecha va del módulo importado al que importa:
    `A -> B` significa que `B` hace `import A`. Azul: configuración común; ámbar:
    el monitor; verde: el servicio. La flecha discontinua es el import perezoso de
    `registro.py`, que solo ocurre al ejecutarlo como programa.
  ],
)

#v(0.9em)

*Tres cosas que el dibujo no deja ver.*

- *Ningún módulo orquesta a los demás.* El orden del pipeline no está en Python:
  está en el `Makefile` (`make demo`). Cada etapa es un proceso aparte que lee los
  JSON de la anterior y escribe los suyos.
- *`monitor.py` importa el código de estimación*, no solo su JSON
  (`aipw_crossfit`, `propensity`, `smd`). Reutilizar el monitor arrastra
  `estimacion.py` y, con él, `scipy`.
- *El import de `registro.py` es perezoso a propósito.* Vive dentro de
  `if __name__ == "__main__":`, no en la cabecera. Como `servicio_core.py` importa
  `registro`, un import de nivel superior haría que levantar la API cargara
  `numpy` y `scipy` sin necesidad.

`rutas.py` es la hoja del grafo y el único punto de configuración: rutas, escenario
y `SIC_ESCENARIO`.

#pagebreak()

#block(width: 100%, inset: 9pt, radius: 3pt,
  fill: rgb("#eef3f9"), stroke: 0.6pt + rgb("#9db3cc"))[
  *Alcance.* `real/ihdp` y `real/jobs` son nombres de escenario; todos los
  valores son sintéticos. Los resultados son una demostración metodológica, no
  una recomendación clínica, laboral o de política pública. El caso es uno de
  los casos guiados del curso: el subcriterio 1.1 queda en parcial y no se
  presenta como trabajo final autónomo.
]

== 1. Escenarios y archivos

#table(
  columns: (1.4fr, 2.4fr, 2.4fr),
  inset: 6pt,
  align: (left, left, left),
  table.header([*Dato*], [*`real/ihdp`*], [*`real/jobs`*]),
  [Inspiración], [Hill (2011), JCGS 20(1)], [LaLonde (1986), AER 76(4)],
  [Unidades (total; train / validation / test)],
    [747 (448 / 149 / 150)], [1722 (1033 / 344 / 345)],
  [Covariables], [25 continuas (`bw` … `was`)], [8 (`age` … `re75`)],
  [Tratados (train)], [191 (42,7 %)], [262 (25,4 %)],
  [Resultado], [`outcome`: puntaje cognitivo a 3,5 años],
    [`re78`: ingresos de 1978 (USD)],
  [Escala del resultado], [puntos], [dólares de 1978],
)

Cada carpeta contiene:

- `observed.csv`, el conjunto completo, y `observed_train.csv`,
  `observed_validation.csv` y `observed_test.csv`, las particiones 60/20/20
  generadas con semilla `20240701`. `splits.json` registra tamaños y hashes
  SHA-256; `datos.py` los recalcula.
- `metadata.json` describe el escenario; `identification.json` declara el
  conjunto de ajuste válido según el diseño del benchmark. Es una anotación del
  benchmark, no una prueba independiente de identificación causal.
- `interventions.json` incluye referencias agregadas (`ate`, `att` y resumen de
  `tau`). Se reserva para la comparación final: no se consulta para estimar ni
  calibrar.
- No se incluyen columnas observadas de resultados potenciales ni archivos
  `truth_*.csv`. No hay verdad causal individual disponible para el análisis
  unidad por unidad.

*Datos y autorización.* El paquete es sintético y no contiene registros
personales; no requiere autorización. Si se usara un caso propio, habría que
declarar la autorización y mantener los datos fuera del paquete. El hash de
`observed_train.csv` viaja en `artifacts/estimacion.json` y en el manifiesto de
la versión registrada.

=== 1.1 Origen del dato: tres capas que no conviene confundir

«IHDP» nombra a la vez un ensayo clínico, un benchmark semi-sintético construido
a partir de él y, en este paquete, un escenario sintético inspirado en ambos.
Confundir las capas es el error más frecuente al citar este dataset: cambia el
tamaño muestral, el desbalance entre brazos y hasta la identificabilidad del
estimando.

*Capa 1 — el ensayo real.* El _Infant Health and Development Program_ fue un
ensayo aleatorizado multicéntrico en 8 hospitales universitarios de EE. UU.,
financiado por la Robert Wood Johnson Foundation, con reclutamiento entre
noviembre de 1984 y agosto de 1985 e intervención entre 1985 y 1988. Se
eligieron lactantes con peso al nacer de 2.500 g o menos y 37 semanas de
gestación o menos. De 4.551 nacidos, 1.302 fueron elegibles y 985 se
aletorizaron: *377 al brazo de intervención y 608 al de seguimiento*. La
intervención combinó visitas domiciliares (semanales el primer año, quincenales
después), un centro de desarrollo infantil a tiempo completo entre los 12 y los
36 meses, y grupos de apoyo para padres. El resultado primario fue el *CI de
Stanford–Binet a los 36 meses*; el ensayo reportó una ganancia media cercana a
9 puntos, con 13,2 en el estrato de mayor peso y 6,6 en el de menor, que se
atenuó a los 5 y a los 8 años.

*Capa 2 — el benchmark de Hill (2011).* Hill conservó las _covariables reales_ y
la _asignación de tratamiento del ensayo_, y sustituyó los resultados por
simulaciones. Para inducir confusión eliminó a todos los tratados cuya madre no
era blanca, lo que deja *139 tratados y 608 controles (747 unidades)*. El precio
de ese filtrado es alto: destruye el solapamiento, de modo que en el benchmark
canónico el estimando defendible es el ATT o el CATT, no el ATE. Las 25
covariables son 6 continuas —peso al nacer, perímetro cefálico, prematurez,
orden de nacimiento, índice de salud neonatal y edad de la madre— y 19 binarias,
siete de ellas dummies de centro. La superficie de respuesta habitual («Setting
B») es no lineal y no paralela: el potencial bajo control se genera como
exponencial de una combinación lineal, y el efecto sobre los tratados se calibra
en 4.

*Capa 3 — este paquete.* `real/ihdp` *no contiene ningún registro del ensayo*.
`metadata.json` lo declara sin ambigüedad: `SYNTHETIC - generated from scratch
using formula-based simulation (Hill 2011 style)`. Se conservan el nombre del
escenario, el número de unidades (747), el número y los nombres de las
covariables y el orden de magnitud del efecto de referencia. Todo lo demás
—covariables, tratamiento y resultado— se simula: covariables de distribución
normal estándar, tratamiento por un modelo logístico en `X` y resultado lineal
con efectos heterogéneos, con semilla de generación 400. La partición 60/20/20
usa otra semilla, 20240701, y es estratificada por tratamiento.

#table(
  columns: (1.5fr, 3.6fr),
  inset: 6pt,
  align: (left, left),
  table.header([*Rasgo*], [*`real/ihdp`*]),
  [Unidades], [747 en total: 448 en `train`, 149 en `validation`, 150 en `test`],
  [Covariables], [25, todas continuas y simuladas],
  [Tratamiento: columna `treatment`],
    [binaria 0/1: 1 = programa de intervención temprana (visitas domiciliares,
    centro infantil a tiempo completo y grupos de padres, del alta a los 36 meses);
    319 tratados de 747 (42,7 %)],
  [Resultado: columna `outcome`],
    [puntaje cognitivo a los 3,5 años, en puntos; mayor es mejor],
  [Efecto de referencia], [ATE 3,92 y ATT 4,15 en `interventions.json`],
)

*Nota.* El escenario es sintético: sirve para validar la cadena —estimador,
diagnósticos, puerta, registro y servicio—, no para concluir nada sobre el
programa.

*Fuentes.* Hill, J. L. (2011). Bayesian Nonparametric Modeling for Causal
Inference. _Journal of Computational and Graphical Statistics_ 20(1), 217–240.
doi:10.1198/jcgs.2010.08162. Infant Health and Development Program (1990).
Enhancing the outcomes of low-birth-weight, premature infants: a multisite,
randomized trial. _JAMA_ 263(22), 3035–3042. Brooks-Gunn y cols. (1994), _JAMA_
272(16), 1257–1262. Para el uso del benchmark en aprendizaje automático causal:
Shalit, Johansson y Sontag (2017), _PMLR_ 70, 3076–3085; Curth y cols. (2021),
_NeurIPS Datasets and Benchmarks_.

=== 1.2 Anatomía de los datos: covariables, tratamiento y resultado

El escenario tiene 747 filas y 27 columnas: 25 covariables pre-tratamiento, una
columna de tratamiento y una de resultado. Las covariables llevan nombre clínico,
pero aquí son normales estándar simuladas: el nombre indica qué papel juega la
variable en el diseño, no una medición.

*Las 25 covariables, por bloque.* La agrupación es semántica, no de tipo: en este
escenario las 25 son continuas, así que no hay indicadores binarios ni dummies de
centro en sentido estricto.

#block(breakable: false)[
#table(
  columns: (1.15fr, 2.45fr, 2.6fr),
  inset: 6pt,
  align: (left, left, left),
  table.header([*Bloque*], [*Variables*], [*Por qué se ajusta por ellas*]),
  [Neonatal (5)],
    [`bw`, `b.head`, `preterm`, `birth.o`, `nnhealth`],
    [Determinan quién entra al programa y predicen el desarrollo cognitivo],
  [Del niño (2)], [`sex`, `twin`],
    [Moderadores del desarrollo; entran en el modelo de tratamiento],
  [Materno (6)],
    [`momage`, `prenatal`, `cig`, `booze`, `drugs`, `first`],
    [Conducta y cuidado prenatal: afectan al tratamiento y al resultado],
  [Socioeconómico (5)],
    [`mom.lths`, `mom.hs`, `mom.scoll`, `b.marr`, `work.dur`],
    [Estrato social: selecciona al tratamiento y condiciona el resultado],
  [Sitio (7)],
    [`ark`, `ein`, `har`, `mia`, `pen`, `tex`, `was`],
    [Centro de reclutamiento: práctica clínica distinta en cada sede],
)
]

La suma cuadra: cinco bloques, veinticinco variables, ninguna fuera de un bloque.

*El tratamiento es la columna `treatment`.* Vale 1 si la unidad recibió el
programa de intervención temprana —visitas domiciliares, centro infantil a tiempo
completo y grupos de padres, del alta a los 36 meses— y 0 si solo recibió
seguimiento. Es binaria, fija en el tiempo y de una sola versión, como exige
SUTVA. Hay 319 tratados de 747 (42,7 %), y 191 de 448 en `train` (42,6 %). Aquí
el programa es solo la etiqueta del brazo: la columna se genera con un modelo
logístico en `X`, sin simular visitas ni dosis.

*El resultado es la columna `outcome`.* Es el puntaje cognitivo a los 3,5 años:
continuo, medido una sola vez después del tratamiento y en el que mayor es mejor.
En `train` la media es 46,6 en control y 57,0 en tratados. Sobre una desviación
típica de 15,0 puntos, el efecto de 5,2 equivale a 0,34 desviaciones típicas: una
magnitud pequeña-media.

*La brecha de confusión.* El contraste bruto mezcla efecto y composición:

#table(
  columns: (2.2fr, 1.2fr, 2.6fr),
  inset: 6pt,
  align: (left, left, left),
  table.header([*Cantidad*], [*Valor*], [*Lectura*]),
  [Diferencia cruda de medias], [10,33], [lo que se ve sin ajustar],
  [OLS con las 25 covariables], [4,8], [el mismo contraste, ajustado linealmente],
  [*AIPW con cross-fitting*], [*5,2*],
    [estimando principal, IC de 3,9 a 6,4 (sección 6)],
  [Atribuible a composición], [≈ 5,2], [cerca de la mitad del contraste bruto],
)

*Quién es confusor.* Las 25 covariables lo son *por construcción*: cada una es
causa del tratamiento y del resultado. La pregunta no es «¿ajusté por lo
correcto?» —eso lo fija el diseño— sino «¿la maquinaria corrige una confusión que
sé que existe?». El residuo se mide: el SMD máximo cae de 0,43 sin ponderar a 0,03
ponderado por IPW, y el ESS de Kish es 388 de 448.

== 2. Pregunta, estimando y población

#block(width: 100%, inset: 8pt, radius: 3pt,
  fill: rgb("#f7fafc"), stroke: 0.5pt + luma(190))[
  *Pregunta de decisión.* ¿Debe ampliarse el programa de intervención temprana
  a la población del estudio para mejorar el puntaje cognitivo a los 3,5 años?
]

El estimando declarado antes de mirar los efectos es el *efecto promedio del
tratamiento* (ATE):

$ tau = E[Y(1) - Y(0)] $

- *Unidad:* puntos del test cognitivo en `real/ihdp`; dólares de 1978 en
  `real/jobs`.
- *Población objetivo:* las 448 unidades de `observed_train.csv` en `real/ihdp`.
  El AIPW promedia scores sobre esta muestra; la interpretación causal requiere
  los supuestos de la sección 4.
- *Qué cubre el IC del ATE:* incertidumbre del efecto promedio, no un efecto
  individual ni un CATE. `/consulta` devuelve, como máximo, la media de un
  estrato predefinido; tampoco es un efecto individual.
- *No es el ATT.* Preguntar por el efecto «en quienes recibieron el programa»
  describe el ATT. En la referencia agregada de `real/ihdp`, ATE = 3,92 y
  ATT = 4,15; se comparan solo al final.

== 3. Identificación y por qué el ATE es identificable

La estrategia es *ajuste por covariables observadas (backdoor)*: las 25
covariables pre-tratamiento bloquean los caminos traseros entre `D` y `Y`. Es la
estrategia natural porque el benchmark es un corte transversal sintético,
`metadata.json` declara que el tratamiento se genera con un modelo logístico en
`X` y el resultado con fórmulas lineales en `X`, `D` y ruido, y
`identification.json` lista las 25 covariables como conjunto de ajuste válido.
No se usa variable instrumental, diferencias en diferencias ni regresión
discontinua: no hay instrumento, panel pre/post ni umbral de asignación.

*Supuestos de identificación.*

- *A1. Ignorabilidad condicional:* $Y(0), Y(1)$ independientes de $D$ dado $X$.
- *A2. Positividad:* $0 < e(X) < 1$ para todo $X$ en la población objetivo.
- *A3. Consistencia / SUTVA:* $Y = Y(D)$ y no hay interferencia.

Con A1–A3:

$ E[Y(1)] = E_X[E[Y(1) | X]] = E_X[E[Y(1) | X, D = 1]] = E_X[E[Y | X, D = 1]] $

$ E[Y(0)] = E_X[E[Y(0) | X]] = E_X[E[Y(0) | X, D = 0]] = E_X[E[Y | X, D = 0]] $

Por tanto:

$ tau = E_X[E[Y | X, D = 1] - E[Y | X, D = 0]] $

El AIPW es un análogo muestral de ese funcional:

$ psi_i = hat(mu)_1 (X_i) - hat(mu)_0 (X_i)
  + frac(D_i (Y_i - hat(mu)_1 (X_i)), hat(e)(X_i))
  - frac((1 - D_i)(Y_i - hat(mu)_0 (X_i)), 1 - hat(e)(X_i)) $

$ hat(tau) = 1/n sum_(i=1)^n psi_i , quad
  hat("se") = frac("sd"(psi), sqrt(n)) $

La identificabilidad es una propiedad del modelo causal y de A1–A3, no del
estimador. El AIPW es consistente bajo regularidad y especificación correcta de
al menos uno de los dos modelos auxiliares. La referencia del DGP (ATE ≈ 3,92)
no interviene en la prueba ni en la estimación.

*Por qué A2 no es un adorno.* En el benchmark canónico de Hill el filtrado elimina
a todos los tratados con madre no blanca: en ese estrato no queda ninguna unidad
tratada, la positividad falla y el ATE deja de estar identificado. En este paquete
el DGP no borra unidades tratadas —solo simula un tratamiento logístico en `X`—,
así que A2 se sostiene sobre `train` y el ATE es identificable. La diferencia es
del escenario, no del estimador (sección 1.1).

*Límite.* `identification.json` es una anotación del benchmark. En datos reales
la ignorabilidad no se verifica con los datos; se defiende o se acota. El DAG
completo de la sección 14 explicita la amenaza de confusión no medida.

== 4. Supuestos: validez, evidencia y límites

#table(
  columns: (1.8fr, 0.9fr, 3.3fr),
  inset: 5pt,
  table.header([*Supuesto (formal)*], [*Clase*], [*Evidencia, tratamiento y límite*]),
  [Ignorabilidad condicional: $Y(0), Y(1)$ independientes de $D$ dado $X$],
    [`no_observable`],
    [El DGP simula el tratamiento con un logístico en `X` y el resultado con
     fórmulas lineales en `X`, `D` y ruido; no hay confusor latente simulado.
     Se chequea con balance, placebo de tratamiento y placebo de resultado.
     No se verifica con los datos observados ni se generaliza a IHDP real.],
  [Positividad / soporte común: $0 < e(X) < 1$],
    [`observable`],
    [En `train`, la propensión estimada vive en [0,071; 0,887], el 100 % cae en
     [0,05; 0,95] y el ESS de Kish es 388/448 (0,87). Son diagnósticos
     muestrales; no prueban positividad poblacional ni para perfiles nuevos.
     El servicio se abstiene fuera del rango de entrenamiento.],
  [Consistencia / SUTVA: $Y = Y(D)$ y no interferencia],
    [`no_observable`],
    [El DGP es unitario, con ruido independiente. No hay chequeo directo; se
     declara la limitación. En un programa real puede haber spillovers,
     equilibrio general o versiones distintas de implementación.],
  [Covariables medidas antes del tratamiento],
    [`observable`],
    [`metadata.json` e `identification.json` lo declaran. `score_post` es una
     columna construida con `Y` para demostrar fuga de información: no es una
     covariable real ni un placebo.],
)

*Clasificación y evidencia falsificable.* La tarjeta (`tarjeta.json`) y el
código del kit clasifican cada supuesto como `observable` o `no_observable`. En
la guía del curso, *falsificable* nombra el tratamiento de la evidencia
(placebos, diagnósticos de soporte, sensibilidad): aquí está en §5–§8 y en
`evidencia/`. La tabla anterior enlaza cada supuesto con su clase en tarjeta y
con lo que se hizo para contrastarlo, sin presentar la ignorabilidad como un
hecho verificado por los datos.

*Nota sobre `score_post`.* La trampa vacía el coeficiente del tratamiento
(ATE ≈ −0,1) porque introduce el resultado en el ajuste. Es una prueba de fuga de
información, no un control negativo. El placebo real se describe en la sección
5.

== 5. Sensibilidad y placebo

#table(
  columns: (1.4fr, 1.7fr, 3.0fr),
  inset: 5pt,
  table.header([*Medida*], [*Resultado*], [*Lectura y límite*]),
  [E-value (aprox. continuo)],
    [2,07; IC 1,85],
    [Un confusor no medido tendría que asociarse con `D` y `Y`, condicionando
     en `X`, con una RR aproximada de al menos 2,07 para explicar el efecto
     puntual; el límite del IC exige 1,85. Es una aproximación vía efecto
     estandarizado; no es una RR literal ni una cota exacta.],
  [Valor de robustez (Cinelli–Hazlett)],
    [37,4 %],
    [Un confusor no medido tendría que explicar al menos el 37,4 % del R²
     parcial de `D` y de `Y`, después de condicionar en `X`, para llevar el
     coeficiente OLS a cero. Es exacto para el OLS; no es una propiedad exacta
     del AIPW.],
  [Placebo de tratamiento permutado],
    [p = 0,005; percentil 100],
    [200 réplicas, pliegues fijos. Placebo: media −0,04, DE 0,62, IC
     [−1,42; 1,06]. El ATE observado (5,16) es extremo. Evalúa calibración e
     implementación; no prueba ignorabilidad.],
  [Placebo de resultado permutado],
    [0,04; IC [−0,23; 0,32]],
    [Se permutó `momage` y se usó como pseudo-resultado, manteniendo `X`
     original. El umbral material es 0,10. No prueba ausencia de confusión; es
     un diagnóstico de calibración.],
)

*Acción de la puerta.* Si el placebo de tratamiento falla o el placebo de
resultado es material: `revisar_identificacion`. Si el soporte se rompe:
`abstenerse` (sin número). Si hay deriva: `reentrenar`. Si el balance ponderado
o la estabilidad del efecto se deterioran: `alertar`. Si todo está dentro de
umbral: `continuar`.

== 6. Estimación, diagnósticos y resultados

Estimador principal: *AIPW con cross-fitting* $K = 5$, semilla `4242`. Los
nuisances se ajustan fuera del pliegue que predicen. El OLS con las 25
covariables es el comparador.

#table(
  columns: (2.8fr, 2.2fr),
  inset: 6pt,
  table.header([*Cantidad*], [*`real/ihdp`*]),
  [Diferencia cruda], [10,3 puntos],
  [ATE OLS (comparador)], [4,8 puntos; IC [3,8; 5,8]],
  [*ATE AIPW*], [*5,2 puntos; IC [3,9; 6,4]*],
  [ESS de Kish / n], [388 / 448 (0,87)],
  [Rango de la propensión estimada], [[0,071; 0,887]],
  [Fracción en solape [0,05; 0,95]], [100 %],
  [SMD máximo sin ponderar], [0,43],
  [SMD máximo ponderado por IPW], [0,03],
  [Trampa `score_post`], [−0,1; el coeficiente se vació],
  [$R^2$ de la proyección individual], [0,095; discriminación baja],
)

*Validación por particiones.* El estimando primario es el de `train`. Las otras
particiones son un chequeo de estabilidad, no un holdout aleatorizado ni una
prueba de ignorabilidad:

#table(
  columns: (1.4fr, 1.0fr, 1.4fr, 2.0fr),
  inset: 6pt,
  table.header([*Partición*], [*n*], [*ATE AIPW*], [*IC 95 %*]),
  [train], [448], [5,16], [[3,93; 6,38]],
  [validation], [149], [1,93], [[−2,45; 6,31]],
  [test], [150], [1,63], [[−3,91; 7,18]],
)

Los ATE de `validation` y `test` son más bajos y sus intervalos son anchos; los
IC se solapan con el de `train`, pero la evidencia no confirma una estabilidad
precisa. Se reporta así, sin ocultar la diferencia.

*Estratos predeclarados.* El corte es `bw` en la mediana de `train`, declarado
antes de mirar los efectos:

#table(
  columns: (2.8fr, 1.0fr, 1.4fr, 1.8fr),
  inset: 6pt,
  table.header([*Estrato*], [*n*], [*Efecto*], [*IC 95 %*]),
  [`bw` alto (> mediana)], [224], [7,2], [[5,5; 8,8]],
  [`bw` bajo (≤ mediana)], [224], [3,2], [[1,4; 4,9]],
)

No es un CATE: son dos medias de scores AIPW con su IC. El corte no se eligió
por ganancia de varianza.

*Diagnósticos.* El rango de propensión, el ESS y el solapamiento de la tabla se
calculan sobre `train` con una propensión ajustada en toda la muestra; no son
las predicciones cross-fit del score AIPW. El SMD sin ponderar es el máximo
entre tratados y controles; el SMD ponderado usa pesos IPW y es el que usa la
puerta. Ningún diagnóstico demuestra que los supuestos causales se cumplan.

== 7. Servicio, tarjeta y registro

*Contrato del servicio.* El servicio carga el bundle campeón y no lee CSV ni
`interventions.json`.

#table(
  columns: (1.5fr, 4.4fr),
  inset: 5pt,
  table.header([*Ruta*], [*Respuesta*]),
  [`/efecto`],
    [ATE, IC, versión, `estado_puerta`, `sensibilidad`, `placebo` y
     `limitaciones`; si la puerta es `falla`, abstención sin número.],
  [`/consulta`],
    [media del estrato con IC, `estado_puerta`, E-value del estrato y referencia
     al placebo poblacional; fuera de soporte, abstención sin número.],
  [`/efecto_individual`],
    [proyección lineal del score AIPW; `sensibilidad.aplicable = false` y
     `placebo.aplicable = false` porque no es un estimando causal validado;
     fuera de soporte, abstención.],
  [`/salud`],
    [estado del servicio, versión y `estado_puerta`.],
)

*Tarjeta.* `tarjeta.json` incluye estimando, población, supuestos, umbrales,
semilla, hash del dataset, estimador, uso previsto, limitaciones, soporte,
puerta, sensibilidad, placebo, validación por particiones y versión de esquema.
Clasifica los supuestos como `observable` o `no_observable`.

*Registro.* Cada corrida crea `artifacts/registro/vNNNN/` con
`estimacion.json`, `tarjeta.json` y `manifest.json` con hashes. El alias
`artifacts/alias_champion.json` apunta a la versión campeona y
`artifacts/registro/champion` se mantiene por compatibilidad. Una versión con
puerta `falla` nunca se promueve; una versión en `alerta` exige aceptación
explícita. `v0001` a `v0003` se conservan inmutables; la corrida de este
documento promovió `v0004`.

== 8. Monitoreo y regla de decisión

*Cinco acciones, en orden de severidad:* `abstenerse` > `revisar_identificacion`
> `reentrenar` > `alertar` > `continuar`. La tabla de la rúbrica las lista de
menor a mayor severidad; la puerta aplica primero la más severa.

#table(
  columns: (2.2fr, 3.6fr),
  inset: 5pt,
  table.header([*Acción*], [*Cuándo y qué hace el servicio*]),
  [`continuar`], [todo dentro de umbral; `estado_puerta = pasa`.],
  [`alertar`], [balance ponderado o estabilidad del efecto; responde con número
    y advertencia (`estado_puerta = alerta`).],
  [`reentrenar`], [PSI de covariables sobre umbral; responde con advertencia
    (`estado_puerta = reentrenar`).],
  [`revisar_identificacion`], [placebo o control negativo falla; responde con
    advertencia (`estado_puerta = revisar_identificacion`).],
  [`abstenerse`], [soporte insuficiente o tratamiento constante; no devuelve
    número (`estado_puerta = falla`).],
)

*Ventanas de la corrida (`real/ihdp`).* La ventana de producción es `sana`; las
demás son evidencias de estrés y no bloquean el servicio por sí solas.

#table(
  columns: (1.5fr, 1.1fr, 1.1fr, 1.2fr, 1.6fr),
  inset: 5pt,
  table.header([*Ventana*], [*PSI máx*], [*SMD pond.*], [*ATE ventana*], [*Acción*]),
  [`sana`], [0,024], [0,07], [5,64], [`continuar` / `pasa`],
  [`deriva`], [0,883], [0,03], [5,16], [`reentrenar`],
  [`positividad`], [3,069], [5,16], [7,2], [`abstenerse` / `falla`],
  [`balance`], [0,029], [0,05], [3,63], [`alertar`],
  [`confusor_oculto`], [0,0], [0,03], [1,0], [`alertar`],
)

La ventana `sana` tiene ATE 5,64 frente al campeón 5,16 y una diferencia de 0,49,
por debajo del umbral de 1,25: `continuar`. La ventana de positividad rompe el
solapamiento (0 %) y obliga a `abstenerse`. La ventana de balance y la de
confusor oculto se detectan por estabilidad del efecto (diferencias 1,52 y 4,16),
no por el SMD ponderado. El confusor oculto es un *stress test*: el monitor no
observa `U`; la sensibilidad de la sección 5 es la que acota su fuerza.

*Umbrales.* `smd_max = 0,50`, `smd_ponderado_max = 0,25`,
`psi_alerta = 0,25`, `solape_min = 0,30`, `efecto_estabilidad = 0,20`. Son
convenciones iniciales, no leyes universales; están en la tarjeta y se
declaran como tales.

== 9. Flujo del trabajo

La figura de la página 1 resume la cadena completa. Cada etapa consume los
artefactos de la anterior, sin saltos:

- `observed_train.csv`: datos observados con hash y particiones.
- `datos.py`: roles de las columnas, verificación de hashes y la pared.
- `estimacion.py`: AIPW con cross-fitting, IC, diagnósticos, sensibilidad y placebo.
- `registro.py`: tarjeta, versión inmutable y alias del campeón.
- `monitor.py`: ventanas de vigilancia y puerta de decisión (sección 8).
- `servicio.py`: FastAPI con el bundle del campeón en memoria.

El estado de la puerta y la regla de abstención están en la sección 8.

== 10. Evidencia y reproducibilidad

Desde la raíz del repositorio:

```sh
SIC_ESCENARIO=real/ihdp make demo
SIC_ESCENARIO=real/ihdp make pruebas
make evidencia
shasum -a 256 -c evidencia/SHA256SUMS
```

#table(
  columns: (2.8fr, 3.2fr),
  inset: 5pt,
  table.header([*Cifra*], [*Evidencia*]),
  [ATE 5,2 [3,9; 6,4]], [`evidencia/02_estimacion.txt`],
  [E-value 2,07 / RV 37,4 %], [`evidencia/03_sensibilidad.txt`],
  [Placebo D p=0,005; placebo Y 0,04 [−0,23; 0,32]], [`evidencia/04_placebo.txt`],
  [ESS 388/448; rango e [0,071; 0,887]], [`evidencia/02_estimacion.txt`],
  [Puerta de producción y ventanas], [`evidencia/05_puerta.txt`],
  [Versión, manifiesto y alias], [`evidencia/06_registro.txt`],
  [Servicio y abstención], [`evidencia/07_servicio.txt`],
  [DAG], [`evidencia/08_dag.txt`],
  [Pruebas], [`evidencia/09_pruebas.txt`],
)

No hay cifras inventadas: las de este documento salen de
`artifacts/estimacion.json`, `artifacts/monitor_estado.json` y
`artifacts/registro/v0004/`. Si se vuelve a ejecutar la cadena, se crea una
versión nueva y el alias cambia; la evidencia conserva los hashes de la corrida.

== 11. Cierre para un lector no técnico

*Decisión recomendada (en el escenario sintético).* El programa muestra un
efecto promedio positivo de unos *5,2 puntos* en el test cognitivo, con un
intervalo de confianza de *3,9 a 6,4 puntos*. La estimación es compatible con un
beneficio promedio, pero no es una garantía para un niño concreto ni para una
población real.

*Qué sostiene la recomendación.* El resultado se apoya en un ajuste por 25
covariables observadas, un buen solapamiento entre tratados y controles, un
placebo de tratamiento que se comporta como se espera y un placebo de resultado
sin efecto material. La sensibilidad indica que un confusor no medido tendría
que ser moderadamente fuerte (RR aproximada ≥ 2,07) para explicar el efecto.

*Cuándo dejar de confiar.* Si la población cambia y el monitor detecta deriva
(`reentrenar`); si el solapamiento se rompe (`abstenerse`); si el placebo o el
control negativo fallan (`revisar_identificacion`); si la validación en otras
particiones sigue mostrando estimaciones muy distintas; o si el coste o el
riesgo de la intervención exige un efecto mayor que el que el IC permite
descartar.

*Lo que este cierre no dice.* No dice que el programa funcione en niños reales,
no reemplaza un ensayo aleatorizado y no autoriza decisiones clínicas,
laborales o de política pública. Es una demostración metodológica sobre datos
sintéticos.

== 12. Reutilización y decisiones propias

*Reutilización.* Se reutilizan el estimador AIPW con cross-fitting, el esquema
de tarjeta, la puerta, el registro con manifiesto y el monitor del prototipo
abierto. Se adaptan las 25 covariables, el corte `bw`, los umbrales, las
ventanas y la capa de sensibilidad/placebo.

*Herramientas externas.* Las cifras reproducibles provienen de la ejecución
local y de los comandos de §10 con sus salidas en `evidencia/`. Este cierre y
`BITACORA.md` pueden editarse con apoyo de asistentes de texto; ese apoyo no
sustituye el cómputo ni los hashes de evidencia.

*Decisiones propias.*

- Corte de heterogeneidad en `bw` en la mediana de `train`: el bajo peso al
  nacer define la población clínica del IHDP; se declara antes de mirar los
  efectos y no se elige por ganancia de varianza. En `jobs` el corte es
  `nodegree`.
- Umbrales recalibrados para `ihdp`: `smd_max = 0,50`,
  `smd_ponderado_max = 0,25`, `psi_alerta = 0,25`, `solape_min = 0,30`,
  `efecto_estabilidad = 0,20`. Son convenciones iniciales, documentadas.
- Ventanas de estrés: deriva de `bw` en +1 DE, positividad sobre `bw`, balance
  sobre `momage` y confusor oculto simulado. En `jobs`: `age`, `re74`, `educ`.
- Sensibilidad y placebo: E-value + valor de robustez y placebo de tratamiento +
  placebo de resultado, porque el resultado es continuo y ninguna medida
  individual es exacta para el AIPW.

El caso sigue siendo guiado; por eso 1.1 queda en parcial.

== 13. Defensa (15 minutos)

10 minutos de exposición y 5 de preguntas. Las tres preguntas fijas, con el
artefacto que se mostraría:

1. *Muestre el artefacto que justifica la abstención o el estado de la puerta.*
   `artifacts/monitor_estado.json` y `evidencia/05_puerta.txt`; para la
   abstención por soporte, `evidencia/07_servicio.txt`.
2. *Nombre un supuesto no observable y explique cómo lo acotó.* Ignorabilidad
   condicional; E-value 2,07 (IC 1,85) y valor de robustez OLS 37,4 %, en
   `evidencia/03_sensibilidad.txt`. Explicar que no es una prueba.
3. *¿Qué cambio mínimo haría que dejara de recomendar la intervención?* Un
   confusor no medido con asociación aproximada menor que 2,07; un fallo del
   placebo o del control negativo; una ruptura de solapamiento; o una deriva
   que el monitor clasifique como `reentrenar` o `abstenerse`.

Si no se puede mostrar el artefacto o reproducir la cifra, ese resultado no
cuenta como evidencia propia.

#page(flipped: true, margin: (x: 1cm, y: 1cm))[
  == 14. DAG completo de `real/ihdp`

  // Graphviz → SVG (`figuras/dag_ihdp_detalle.dot`); página apaisada dedicada.
  #grid(
    rows: (1fr, auto),
    row-gutter: 0.55em,
    align(center + horizon)[
      #image("figuras/dag_ihdp_detalle.svg", width: 100%, fit: "contain")
    ],
    align(center)[
      #text(size: 9pt, fill: luma(55))[
        *DAG* (`dag_ihdp_detalle.svg`): un nodo por covariable pre-tratamiento (25),
        tratamiento `D` y resultado `Y`; aristas según el benchmark. `U` es una
        amenaza hipotética de confusión no medida, no una variable documentada en
        el DGP del benchmark.
      ]
    ],
  )
]

*Grupos de covariables.* Nacimiento / niño: `bw`, `b.head`, `preterm`,
`birth.o`, `nnhealth`, `sex`, `twin`. Conducta prenatal: `cig`, `first`,
`booze`, `drugs`, `work.dur`, `prenatal`. Madre / hogar: `momage`,
`mom.lths`, `mom.hs`, `mom.scoll`, `b.marr`. Sitio / contexto: `ark`, `ein`,
`har`, `mia`, `pen`, `tex`, `was`.

La versión resumida (plate), con covariables agrupadas, está en
`figuras/dag_ihdp_plate.svg`. La versión de `real/jobs`, con 8 covariables,
está en `figuras/dag_jobs.svg`.

== 15. Rúbrica: estado del prototipo

#text(size: 8.2pt)[
#table(
  columns: (0.6fr, 2.6fr, 1.0fr, 3.0fr),
  inset: 4pt,
  table.header([*ID*], [*Subcriterio*], [*Estado*], [*Evidencia / límite*]),
  [1.1], [Pregunta de decisión y estimando], [Parcial],
    [Pregunta de decisión y ATE en §2; el caso es guiado, así que no puede ser completo],
  [1.2], [Datos y autorización], [Completo],
    [§1; hashes de splits; datos sintéticos sin registros personales],
  [2.1], [Estrategia de identificación], [Completo],
    [§3: backdoor por observables; por qué no IV/DiD/RD],
  [2.2], [Supuestos clasificados], [Completo],
    [§4: `observable` / `no_observable` en tarjeta; evidencia falsificable §5–§8],
  [2.3], [Estimación con intervalo y validación], [Completo],
    [§6: AIPW K=5, IC, validación por particiones y reproducibilidad],
  [2.4], [Interpretación y sensibilidad], [Completo],
    [§5: E-value y RV con lectura y límites],
  [3.1], [Servicio y contrato], [Completo],
    [§7: puerta, sensibilidad, placebo y abstención; `humo.py`],
  [3.2], [Model card completa y propia], [Completo],
    [§7; `tarjeta.json` con uso previsto, limitaciones, soporte y puerta],
  [3.3], [Registro con manifiesto], [Completo],
    [§7; `v0004`, manifiesto, `alias_champion.json`; bloqueo de `falla` probado],
  [4.1], [Señales con umbral y acción], [Completo],
    [§8: PSI, SMD ponderado, ESS, solape y estabilidad; umbrales declarados],
  [4.2], [Regla de decisión probada], [Completo],
    [§8: cinco acciones y cinco ventanas contrastantes],
  [4.3], [Control negativo o placebo], [Completo],
    [§5: placebo de tratamiento y placebo de resultado con lectura],
  [4.4], [Supuesto no observable], [Completo],
    [§4–§5: ignorabilidad declarada y acotada con E-value/RV],
  [5.1], [Cadena coherente], [Completo],
    [§9–§10: datos, estimación, puerta, tarjeta, registro y servicio],
  [5.2], [Paquete de evidencia], [Completo],
    [`evidencia/` con comando, salida y hash por cifra],
  [5.3], [Reutilización de lo propio], [Completo],
    [§12: qué se reutiliza y qué se adapta],
  [6.1], [Decisiones propias], [Completo],
    [§12: corte `bw`, umbrales, ventanas y elección de sensibilidad],
  [6.2], [Defensa en vivo], [Completo],
    [§13: guion de 15 min y tres preguntas fijas],
  [6.3], [Documento de cierre], [Completo],
    [§11: decisión, efecto, supuestos y cuándo dejar de confiar],
)
]

*Lectura.* El prototipo cubre los contratos técnicos y la evidencia. La meta
realista es *19,5 / 20*: 1.1 queda en parcial porque el caso es guiado. No se
declara completo ningún subcriterio sin evidencia en `evidencia/`. La rúbrica
sigue siendo una guía; la nota final la asigna una persona.
