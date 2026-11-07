// ENTREGABLE_FINAL_GUIA_Y_RUBRICA.typ — Sistema de Inteligencia Causal (ECO-490 / ECON-540), 2026-II
// Guía para estudiantes y rúbrica del trabajo final (una sola entrega, sin etapas).
// Autocontenido. El código verifica con assert que la rúbrica suma 20 puntos.

#set document(title: "Trabajo final: prototipo causal local, guía y rúbrica")
#set page(paper: "a4", margin: 2.2cm, numbering: "1",
  footer: context [#set text(size: 8pt, fill: luma(110));Entregable final · ECO-490 / ECON-540 · 2026-II #h(1fr) #counter(page).display()])
#set text(font: "New Computer Modern", size: 10.5pt, lang: "es")
#set par(justify: true, leading: 0.62em)
#show heading.where(level: 1): it => block(above: 1.4em, below: 0.7em, sticky: true, text(size: 15pt, fill: rgb("#1f3a5f"), it))
#show heading.where(level: 2): it => block(above: 1.1em, below: 0.5em, sticky: true, text(size: 11.5pt, fill: rgb("#1f3a5f"), it))
#show table: set par(justify: false)

#let navy = rgb("#1f3a5f")
#let fmt(x) = if calc.fract(x) == 0 { str(int(x)) } else { str(x).replace(".", ",") }
#let tabla(..args) = table(
  stroke: 0.5pt + luma(180),
  fill: (x, y) => if y == 0 { luma(235) } else { white },
  inset: 5pt,
  ..args,
)
#let caja(titulo, cuerpo) = block(width: 100%, inset: 9pt, radius: 3pt, fill: rgb("#eef3f9"), stroke: 0.6pt + rgb("#9db3cc"), breakable: false)[
  #text(weight: "bold", fill: navy)[#titulo] \ #cuerpo ]
#let cb = box(width: 0.75em, height: 0.75em, stroke: 0.7pt + luma(60), baseline: 0.1em)

La autoridad vigente para esta rúbrica es el sílabo y la
#link("../06_proyecto_final/ADENDA_CONTRATOS_EVALUACION.md")[Adenda de contratos y evaluación
(contratos-2026.10)]. HTTP y CLI son transportes equivalentes; la tarjeta usa las
clases machine-readable `observable` y `no_observable`, mientras que
`falsificable` describe el tratamiento de la evidencia.

// ---------------------------------------------------------------------------
// DATOS DE LA RÚBRICA
// Cada subcriterio vale 1 o 2 puntos. Completo = máximo; Parcial = mitad; No cumple = 0.
// ---------------------------------------------------------------------------
#let criterios = (
  (id: "1", nombre: "Caso, pregunta y datos", sesiones: "S1, S4, S29", subs: (
    (id: "1.1", nombre: "Pregunta de decisión y estimando", max: 1,
      evid: "LEEME y primera sección del cierre", quien: "Persona",
      completo: "La pregunta cabe en una frase con la forma «¿debo hacer X para lograr Y?». El estimando está nombrado (ATE, CATE o valor de una política). El caso no es uno de los guiados de los labs.",
      parcial: "Hay pregunta, pero no se nombra el estimando, o el caso es una variante mínima de uno guiado.",
      cero: "No hay pregunta de decisión, o lo planteado es solo una predicción."),
    (id: "1.2", nombre: "Datos y autorización de uso", max: 1,
      evid: "datos/ o caso/ y manifest.json", quien: "Máquina y persona",
      completo: "Cada conjunto de datos tiene su hash registrado y coincide al ejecutar. Se declara el escenario, la semilla, el split y qué columnas son observadas. Si se usa un caso propio, hay autorización; el paquete no contiene registros individuales sin permiso.",
      parcial: "Hay hash y origen, pero falta declarar el escenario, la semilla, el split o la autorización.",
      cero: "No se puede reconstruir el conjunto usado, o el paquete incluye registros individuales sin autorización."),
  )),
  (id: "2", nombre: "Identificación y estimación", sesiones: "S1–S3, S5, S7, S9–S14", subs: (
    (id: "2.1", nombre: "Estrategia de identificación", max: 1,
      evid: "cierre y notebook", quien: "Persona",
      completo: "Nombra la estrategia (por ejemplo ajuste por observables, variable instrumental o diferencias en diferencias) y explica en pocas líneas por qué aplica a este caso y no otra.",
      parcial: "Nombra la estrategia, pero no la justifica para este caso.",
      cero: "No hay estrategia, o solo dice «controlar por todo»."),
    (id: "2.2", nombre: "Supuestos clasificados", max: 1,
      evid: "tabla de supuestos en el cierre y en la model card", quien: "Persona",
      completo: "Cada supuesto clave está clasificado como observable, falsificable o no observable y tiene su tratamiento con la forma «tipo · cómo se trató · resultado». Hay al menos un supuesto no observable.",
      parcial: "Los supuestos están listados, pero sin clasificar o sin tratamiento.",
      cero: "No se listan supuestos."),
    (id: "2.3", nombre: "Estimación con intervalo y validación", max: 1,
      evid: "notebook y evidencia/", quien: "Máquina y persona",
      completo: "El estimando elegido (ATE, CATE o valor de política) se reporta con incertidumbre y el documento declara qué objeto cubre el intervalo. Usa AIPW/IRM, DR-learner u otra estrategia justificada con cross-fitting o validación equivalente, y el código reproduce el número que aparece en el cierre. No llama intervalo individual a un intervalo del pseudoresultado o del CATE.",
      parcial: "Hay efecto con intervalo, pero falta validación fuera de muestra, cross-fitting o explicación de una diferencia entre el código y el cierre.",
      cero: "El efecto no tiene incertidumbre o no se puede reproducir."),
    (id: "2.4", nombre: "Interpretación y sensibilidad", max: 1,
      evid: "cierre y notebook", quien: "Persona",
      completo: "Interpreta el efecto en las unidades del negocio y usa una medida de sensibilidad compatible con el estimando y la escala (por ejemplo, E-value para una razón de riesgos bajo sus condiciones, valor de robustez, bounds o equivalente) con su lectura y sus límites.",
      parcial: "Interpreta el efecto, pero la sensibilidad no es compatible con la escala, no explica su objeto o no la lee.",
      cero: "Repite el número sin interpretarlo."),
  )),
  (id: "3", nombre: "Producción local, puerta y registro", sesiones: "S12, S17, S18", subs: (
    (id: "3.1", nombre: "Servicio y contrato", max: 1,
      evid: "servicio/ o infra/ y pruebas de humo", quien: "Máquina",
      completo: "El servicio local o CLI equivalente devuelve el estimando elegido (ATE, CATE o policy), la incertidumbre compatible con ese objeto, la versión y el estado de puerta; fuera del soporte p1–p99 devuelve `abstiene: true` o una salida equivalente con un motivo claro.",
      parcial: "Responde, pero omite la incertidumbre, la versión, el estado de puerta o la abstención fuera del soporte.",
      cero: "No ofrece un servicio local ni una interfaz CLI equivalente documentada."),
    (id: "3.2", nombre: "Model card completa y propia", max: 2,
      evid: "tarjeta.json o model_card.json y esquema JSON", quien: "Máquina y persona",
      completo: "Describe datos, estimando, método, soporte, puerta, limitaciones y uso previsto. Clasifica los supuestos como `observable` o `no_observable`; conserva la evidencia falsificable y declara cómo se trató cada uno. Todo coincide con lo que el caso realmente hizo.",
      parcial: "Algún campo importante está genérico, copiado del ejemplo o no coincide con la ejecución.",
      cero: "La tarjeta no valida, no declara los supuestos o no permite saber cuándo abstenerse."),
    (id: "3.3", nombre: "Registro con manifiesto", max: 1,
      evid: "artefactos/vXXXX/manifest.json y artefactos/alias_champion.json", quien: "Máquina",
      completo: "Cada versión inmutable contiene la estimación, la tarjeta y un `manifest.json` con hashes del dataset, la estimación y la tarjeta. `alias_champion.json` apunta a una versión íntegra; una versión con puerta `falla` nunca se promueve y una versión en `alerta` exige aceptación explícita.",
      parcial: "Hay versiones o hashes, pero el alias no coincide con lo que sirve el servicio o no se demuestra el bloqueo de una versión fallida.",
      cero: "No hay registro local verificable ni relación entre la versión promovida y el servicio."),
  )),
  (id: "4", nombre: "Falsificación y monitoreo de supuestos", sesiones: "S7, S11, S24, S25, S27", subs: (
    (id: "4.1", nombre: "Señales con umbral y acción", max: 1,
      evid: "monitor/", quien: "Persona",
      completo: "Al menos tres señales observables del prototipo —propensión extrema, ESS relativo, SMD ponderado, PSI/KS o estabilidad del efecto— tienen umbral, estado y acción asociada. El paquete declara si el umbral fue calibrado con ventanas sin cambio o si es una convención inicial; no lo presenta como ley universal.",
      parcial: "Hay señales con umbral, pero falta acción, justificación o cobertura de soporte y deriva.",
      cero: "Hay menos de dos señales o ninguna tiene umbral."),
    (id: "4.2", nombre: "Regla de decisión probada", max: 1,
      evid: "monitor/ y evidencia/", quien: "Máquina y persona",
      completo: "La regla distingue entre `continuar`, `alertar`, `revisar_identificacion`, `reentrenar` y `abstenerse`, en ese orden de precedencia cuando corresponde. Se muestra funcionando en ventanas sanas y en al menos una ventana con soporte, deriva o identificación alterada.",
      parcial: "La regla está definida, pero no se probó en ventanas contrastantes o no distingue revisión de identificación y reentrenamiento.",
      cero: "No hay regla de decisión."),
    (id: "4.3", nombre: "Control negativo o placebo", max: 1,
      evid: "notebook y monitor/", quien: "Persona",
      completo: "Hay un control negativo —o un placebo justificado— con su resultado y una lectura que dice qué se concluye y qué no. Si el control negativo rechaza, la promoción se bloquea o se revisa la identificación.",
      parcial: "Existe, pero la lectura es incorrecta o se limita a decir «pasó».",
      cero: "No hay control negativo ni placebo."),
    (id: "4.4", nombre: "Supuesto no observable", max: 1,
      evid: "cierre y model card", quien: "Persona",
      completo: "Contrasta el supuesto no observable con un holdout aleatorizado cuando existe. Si no lo hay, declara la limitación, la acota —por ejemplo con un E-value o valor de robustez— y explica por qué no fue posible. No presenta la ausencia de confusión como un hecho observado.",
      parcial: "Declara la limitación, pero no la acota o exagera lo que demuestra el holdout.",
      cero: "No trata el supuesto, o afirma que se cumple sin evidencia."),
  )),
  (id: "5", nombre: "Integración, reproducibilidad y evidencia", sesiones: "S18, S25, S28", subs: (
    (id: "5.1", nombre: "Cadena coherente", max: 1,
      evid: "LEEME y código", quien: "Máquina y persona",
      completo: "La cadena datos → estimación → diagnósticos y puerta → tarjeta → registro → servicio → monitor consume las salidas de la etapa anterior. No hay cifras escritas a mano entre etapas y se pueden reproducir los escenarios sano, soporte insuficiente y confusor oculto.",
      parcial: "Una etapa usa cifras copiadas a mano o falta una parte de la cadena.",
      cero: "Las etapas son independientes entre sí."),
    (id: "5.2", nombre: "Paquete de evidencia", max: 1,
      evid: "evidencia/", quien: "Máquina y persona",
      completo: "Cada cifra del cierre tiene en el paquete su comando, su salida y su hash.",
      parcial: "A algunas cifras les falta el comando, la salida o el hash.",
      cero: "No hay paquete de evidencia."),
    (id: "5.3", nombre: "Reutilización de lo propio", max: 1,
      evid: "código y cierre", quien: "Persona",
      completo: "Reutiliza y cita código o artefactos propios de las prácticas guiadas y del prototipo abierto (estimador, esquema de tarjeta, puerta, registro o monitor), adaptados al caso. Declara qué parte es propia y qué parte se reutiliza.",
      parcial: "Reutiliza, pero sin adaptar o sin citar los cambios.",
      cero: "No declara el origen de los artefactos."),
  )),
  (id: "6", nombre: "Autonomía, defensa y comunicación", sesiones: "S28, preparación y defensa final", subs: (
    (id: "6.1", nombre: "Decisiones propias", max: 1,
      evid: "cierre", quien: "Persona",
      completo: "El cierre lista al menos dos decisiones metodológicas propias (variables, umbrales, modelo u otras), con su razón y lo que cambia respecto del caso guiado.",
      parcial: "Lista decisiones propias, pero sin su razón.",
      cero: "Sigue el caso guiado paso a paso."),
    (id: "6.2", nombre: "Defensa en vivo", max: 1,
      evid: "defensa final", quien: "Persona",
      completo: "Explica cualquier resultado que se le pida y lo reproduce con ejecución local o con la evidencia previamente documentada.",
      parcial: "Explica, pero no logra reproducir el resultado o reproduce sin poder explicar sus decisiones.",
      cero: "No puede explicar ni reproducir sus resultados."),
    (id: "6.3", nombre: "Documento de cierre", max: 1,
      evid: "cierre.pdf", quien: "Persona",
      completo: "Un lector no técnico puede seguirlo. Dice la decisión recomendada, el efecto con su incertidumbre, los supuestos que sostienen la recomendación y cuándo dejar de confiar en ella.",
      parcial: "Cubre la decisión y el efecto, pero no los supuestos o no dice cuándo dejar de confiar.",
      cero: "No hay recomendación, o el texto solo es comprensible para especialistas."),
  )),
)

#let pts(c) = c.subs.map(s => s.max).sum()
#let total = criterios.map(pts).sum()
#assert(total == 20, message: "La rúbrica suma " + str(total) + ", no 20")

// ---------------------------------------------------------------------------
// PORTADA
// ---------------------------------------------------------------------------
#align(center)[
  #v(0.4cm)
  #text(size: 9pt, tracking: 0.12em, fill: luma(110))[SISTEMA DE INTELIGENCIA CAUSAL · ECO-490 / ECON-540 · 2026-II] \
  #v(0.3cm)
  #text(size: 22pt, weight: "bold", fill: navy)[Entregable final] \
  #text(size: 13pt)[Guía para estudiantes y rúbrica de evaluación]
]
#v(0.5cm)

#caja[En una página][
  Entregas *un solo paquete*, una sola vez, en una fecha única. Vale *70 % de la nota final*. Se califica en dos pasos: primero se revisan las condiciones técnicas mínimas (no dan puntos); después una persona lo puntúa con una rúbrica de *19 subcriterios, 20 puntos*. Cada subcriterio tiene tres niveles escritos de antemano: *completo*, *parcial* (mitad de puntos) y *no cumple* (cero). Si lees la rúbrica antes de empezar, sabes exactamente qué cuenta.
]

#v(0.4cm)

#tabla(
  columns: (1.3fr, 2.4fr),
  table.header([*Dato de la entrega*], [*Lo completa el profesor*]),
  [Fecha y hora límite], [#h(1fr)],
  [Canal de entrega], [#h(1fr)],
  [Fecha de la defensa final], [#h(1fr)],
  [Plazo para pedir revisión de la nota], [#h(1fr)],
)

= 1. Qué es el entregable

Es un prototipo causal completo, funcionando en tu computador, para un caso que tú eliges. Parte de una pregunta de decisión («¿debo hacer X para lograr Y?») y termina en una recomendación respaldada por un estimando, su incertidumbre, una puerta causal, un registro de versión, un servicio que devuelve el efecto o se abstiene, y un monitor que indica cuándo revisar la identificación.

*Es una sola entrega.* No hay entregas parciales calificadas ni obligatorias. Las sesiones de trabajo autónomo y revisión cruzada son prácticas formativas. Lo que sí hay es una fecha única y una defensa final en la fecha comunicada por el curso.

*Todo se ejecuta en local.* No se usa nube ni cuentas externas. El prototipo se prueba en el equipo del evaluador con los comandos documentados en el README. Como referencia, la secuencia del prototipo abierto es `make ci`, `make demo`, `make monitor` y, para la API, `make serve`.

== 1.1 Qué contiene el paquete

#text(size: 9pt, fill: luma(100))[Estructura sugerida. Si la plantilla del repositorio dice otra cosa, manda la plantilla. Lo importante son los contratos y la evidencia, no el nombre exacto de cada carpeta.]
#v(0.3em)

#tabla(
  columns: (1.5fr, 2.5fr),
  table.header([*Elemento*], [*Para qué sirve*]),
  [README.md], [Caso, comando de ejecución, limitaciones y forma de reproducir la demo],
  [cierre.pdf o cierre.md], [Documento de cierre para un lector no técnico (criterio 6.3)],
  [datos/ o caso/], [Datos observados, escenario y hashes; nunca columnas `truth` en el bundle],
  [servicio/ o infra/], [Servicio FastAPI local o CLI equivalente, con pruebas de humo],
  [tarjeta.json], [Model card causal validada contra el esquema JSON],
  [artefactos/v0001/], [Estimación, tarjeta y `manifest.json` con hashes],
  [artefactos/alias_champion.json], [Versión que queda promovida como `champion`],
  [monitor/ o artefactos/], [Señales, umbrales, regla de decisión y ventanas simuladas],
  [evidencia/], [Comandos, salidas y hashes de las cifras que aparecen en el cierre],
  [bitacora_causal.md], [Bitácora recomendada para explicar el razonamiento; no es filtro de admisibilidad],
  [respaldo.mp4], [Video opcional de 3 a 5 minutos si el equipo falla durante la defensa],
)

= 2. Cómo se califica

// <!-- OPS:EVA-01:inicio -->
== Paso 1: filtro técnico (no da puntos)

El filtro bloquea la rúbrica completa, pero no asigna puntos. El informe debe indicar la ruta o el campo exacto que falla; «falló el schema» no basta.

- *FORMATO:* schema, ruta, nombre de archivo, comando documentado o hash que puede recalcularse sin cambiar cifras, estimandos ni decisiones.
- *SUSTANCIA:* falta la pregunta, el estimando, el estado de puerta o una abstención; o el paquete incluye `truth`, `y0`, `y1` o `tau` en el entrenamiento o bundle.

Un error `FORMATO` abre 48 horas para corregir solo archivos de forma. No permite cambiar cifras, estimandos, supuestos ni decisiones de la puerta. Un error `SUSTANCIA` no tiene esa ventana y se rige por la recuperación parcial de esta guía.

#tabla(
  columns: (2.4fr, 2fr),
  table.header([*Comprobación*], [*Si falla*]),
  [La demo o el comando principal corre en un equipo limpio], [El informe identifica la salida o comando que falla],
  [La tarjeta causal valida contra el esquema JSON], [El informe identifica la ruta del campo ausente o inválido],
  [La demo muestra un caso sano, un bloqueo por soporte y un bloqueo o alerta por confusión], [Falta evidencia sustantiva del ciclo causal],
  [El manifiesto verifica hashes y `alias_champion.json` apunta a una versión permitida], [No se demuestra promoción segura],
  [El servicio local o CLI devuelve estimando, incertidumbre, metadatos y abstención], [Falta el contrato mínimo de servicio],
  [El monitor genera ventanas y una acción operativa], [Falta evidencia de operación posterior],
)
// <!-- OPS:EVA-01:fin -->

== Paso 2: rúbrica (20 puntos)

Una persona puntúa los 19 subcriterios de la sección 3. Solo puntúa lo que exige criterio: si la identificación es creíble, si la decisión se sigue del número, si la lectura de un supuesto no observable es honesta. Lo que la máquina ya verificó (que el JSON valide, que el código corra) *no vuelve a puntuarse*.

== Dónde están los puntos

#let colores = (rgb("#1f3a5f"), rgb("#3e6a9c"), rgb("#6f95bd"), rgb("#9db3cc"), rgb("#5b7a99"), rgb("#2c4f7a"))
#table(
  columns: (2.6fr, 3.4fr, 0.5fr),
  stroke: none, inset: 4pt, align: (left, left, right),
  ..criterios.enumerate().map(((i, c)) => (
    [#c.id. #c.nombre],
    box(width: pts(c) / 5 * 100%, height: 0.9em, fill: colores.at(i), radius: 1pt),
    [*#fmt(pts(c))*],
  )).flatten()
)

El monitoreo y la falsificación (criterio 4) pesan tanto como la estimación (criterio 2) y la producción (criterio 3), 4 puntos cada uno: el curso evalúa tanto estimar el efecto como reconocer cuándo deja de estar respaldado.

== Cómo se calcula tu nota

#tabla(
  columns: (1fr, 2.5fr),
  table.header([*Paso*], [*Cálculo*]),
  [1], [Suma los puntos de los 19 subcriterios. El máximo es 20.],
  [2], [El trabajo final aporta el 70 % de la nota final: *aporte = 0,70 × puntos*.],
  [Ejemplo], [Con 16 puntos, el trabajo final aporta 0,70 × 16 = 11,2 puntos sobre 20 a la nota final. El 30 % restante corresponde a los tres quizzes online.],
)

// <!-- OPS:EVA-04:inicio -->
== Defensa final (15 minutos)

La defensa dura 15 minutos: 10 minutos de exposición y 5 minutos de preguntas. Las preguntas fijas son, en este orden:

1. Muéstrame el artefacto, log o fila que justifica la abstención o el estado de la puerta. Si no puedes mostrarlo, ese resultado no cuenta como evidencia propia.
2. Nombra un supuesto no observable de tu caso y explica cómo lo acotaste o por qué no pudiste hacerlo. «Puede haber confusión» sin acotar es una respuesta parcial.
3. ¿Qué cambio mínimo en la evidencia, la población o el umbral de decisión haría que dejaras de recomendar esta intervención? Señala el artefacto o cálculo que cambiaría y el supuesto que dejaría de sostenerse.

El resto de las preguntas es libre. Si el equipo falla durante la defensa, se usa la evidencia técnica ya entregada y el video de respaldo solo como constancia; no se depura ni se cambian cifras durante la defensa.
// <!-- OPS:EVA-04:fin -->

// <!-- OPS:EVA-05:inicio -->
== Si el filtro no pasa

Si el fallo es solo de formato y no se corrige en 48 horas, pero el cierre documenta pregunta, estimando, incertidumbre y supuesto, y la defensa los sostiene, se pueden puntuar los criterios 1 y 2. En la rúbrica vigente esos criterios suman *6 de los 20 puntos del proyecto*; el resto queda en cero.

Si no hay pregunta de decisión, solo hay un modelo predictivo o no se puede defender la autoría, el proyecto obtiene cero según las reglas del curso. No hay reentrega de código para «hacerlo funcionar después»: la ventana de 48 horas es solo para formato.
// <!-- OPS:EVA-05:fin -->

// ---------------------------------------------------------------------------
// RÚBRICA (apaisada)
// ---------------------------------------------------------------------------
#page(flipped: true, margin: (x: 1.6cm, y: 1.8cm))[
  = 3. Rúbrica

  #text(size: 9.5pt)[
  *Cómo leerla.* Cada fila es un subcriterio. Compara tu trabajo con las tres columnas y ubícate en la primera que describa lo que hiciste, de izquierda a derecha. *Completo* da el máximo. *Parcial* da la mitad. *No cumple* da cero. No existen otros niveles. «Se comprueba» dice qué archivo mira el evaluador y si lo verifica una máquina, una persona o ambas. «Sesiones» indica dónde se enseña el criterio. La rúbrica no exige una plataforma concreta: exige que el prototipo local sea reproducible y que sus decisiones causales queden justificadas.
  ]

  #for c in criterios [
    == Criterio #c.id: #c.nombre — #fmt(pts(c)) #if pts(c) == 1 [punto] else [puntos] #h(1fr) #text(size: 9pt, weight: "regular", fill: luma(100))[Sesiones: #c.sesiones]
    #set text(size: 8.8pt)
    #table(
      columns: (1.45fr, 2.6fr, 1.9fr, 1.6fr, 0.55fr),
      stroke: 0.5pt + luma(180),
      fill: (x, y) => if y == 0 { luma(232) } else if x == 1 { rgb("#f1f7ee") } else { white },
      inset: 4.5pt,
      align: (left, left, left, left, center),
      table.header([*Subcriterio*], [*Completo (máximo)*], [*Parcial (mitad)*], [*No cumple (0)*], [*Pts.*]),
      ..c.subs.map(s => (
        [*#s.id #s.nombre* \ #text(size: 7.6pt, fill: luma(100))[Se comprueba: #s.evid · #s.quien]],
        [#s.completo],
        [#s.parcial],
        [#s.cero],
        [#fmt(s.max) / #fmt(s.max / 2)],
      )).flatten()
    )
  ]
]

// ---------------------------------------------------------------------------
= 4. Un ejemplo para calibrar

El caso es inventado y solo sirve para ver la diferencia entre niveles: un programa de retención que ofrece un descuento a clientes con riesgo de baja.

#tabla(
  columns: (0.9fr, 1.7fr, 1.7fr),
  table.header([*Subcriterio*], [*Completo*], [*Parcial*]),
  [1.1 Pregunta], [«¿Debo ofrecer el descuento a clientes con riesgo alto para reducir la baja a 90 días?» Estimando: CATE del descuento sobre la baja.], [«Quiero entender qué clientes se van.» No hay decisión ni estimando: es predicción.],
  [4.3 Control negativo], [«El descuento no debería afectar el número de reclamos del mes anterior. Efecto estimado: 0,2 con intervalo que incluye 0. Esto no prueba que no haya confusión, solo no la delata.»], [«Control negativo: pasó.» No dice qué se concluye ni qué no.],
  [4.4 No observable], [«No tengo grupo aleatorizado. Si el resultado se expresa en una razón de riesgos y el análisis aplica, el E-value es 2,1; resume una fuerza conjunta mínima bajo sus supuestos, no exige que cada asociación sea 2,1. La limitación se declara en la model card.»], [«Puede haber confusión no medida.» No se acota ni se explica por qué no hay grupo aleatorizado.],
)

= 5. Antes de la entrega final

Marca cada punto. Si todos están marcados, el filtro técnico debería pasar y la rúbrica no tendrá sorpresas.

#let item(t) = [#cb #h(0.4em) #t \ ]
#item[El comando único del LEEME corre de principio a fin en una carpeta nueva.]
#item[La model card valida contra el JSON Schema y ningún campo está copiado del ejemplo.]
#item[Cada cifra del cierre aparece en evidencia/ con comando, salida y hash.]
#item[El cierre dice la decisión, el efecto con su incertidumbre, los supuestos y cuándo dejar de confiar.]
#item[Hay al menos tres señales con umbral y acción, y una regla de decisión probada con un escenario de violación.]
#item[Hay un control negativo o placebo y su lectura dice qué no se concluye.]
#item[El supuesto no observable está contrastado con un holdout aleatorizado cuando existe, o está acotado con una medida compatible con el estimando y declarado.]
#item[La bitácora, si la usé, y el documento final declaran las herramientas externas que utilicé.]
#item[No hay registros individuales de datos en el paquete.]
#item[Puedo explicar y reproducir cualquier resultado con la ejecución local o con la evidencia documentada.]
#item[El video de respaldo (3 a 5 minutos) está incluido solo si necesito usarlo por una falla durante la defensa.]

= 6. Reglas que conviene conocer

#tabla(
  columns: (1.2fr, 3fr),
  table.header([*Tema*], [*Regla*]),
  [Plazo], [Hay una única fecha oficial para el trabajo final, según el cronograma. No hay entregas parciales calificadas.],
  [Trabajo individual], [El trabajo es personal. Puedes conversar sobre ideas y participar en la revisión formativa, pero el código, las cifras y el cierre son tuyos.],
  [Asistentes de IA], [Se permiten como apoyo en las prácticas y en el trabajo final con tres condiciones: se declaran, puedes defender cada resultado y las cifras salen de artefactos que ejecutaste tú.],
  [Defensa], [La defensa dura 15 minutos: 10 de exposición y 5 de preguntas. Comprueba que puedes explicar y reproducir los resultados. Si no puedes hacerlo, el resultado no acredita el subcriterio correspondiente. Cualquier procedimiento de integridad académica se tramita por separado y con sus propias reglas.],
  [Datos propios], [Solo con autorización. Los datos se quedan en tu equipo; al curso entregas código, hashes y resultados agregados. Si no puedes usar datos propios, elige un caso del benchmark documentado.],
  [Video de respaldo], [Se usa únicamente si tu equipo falla el día de la defensa y la evidencia técnica ya fue entregada. No suma puntos.],
  [Integridad], [Compartir las columnas reservadas de verdad del benchmark (y0, y1, tau) o copiar trabajo ajeno puede activar el procedimiento institucional de integridad. La calificación técnica y ese procedimiento son decisiones separadas.],
  [Revisión], [Recibes la rúbrica marcada, subcriterio por subcriterio, con el nivel asignado. Puedes pedir revisión dentro del plazo que fija el profesor, indicando el subcriterio y la evidencia.],
)

= 7. Qué no se evalúa

#item[La belleza del documento o del código más allá de lo que pide cada subcriterio.]
#item[Los contenidos marcados con ◇ en el sílabo (extensiones): se enseñan, pero no puntúan.]
#item[Que tu efecto sea grande o «positivo». Se evalúa cómo lo estimaste y cuánto cuidaste su validez, no el resultado.]
#item[Que tengas un grupo aleatorizado. Se evalúa que sepas decir qué pasa cuando no lo tienes.]
