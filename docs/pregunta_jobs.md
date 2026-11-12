# Pregunta causal del prototipo (se declara ANTES de mirar los datos)

**Escenario:** `synthetic/jobs` del benchmark local (sintético estilo LaLonde 1986, NSW).

**Alcance:** Prototipo local de estimación causal con AIPW, abstención fuera de soporte y monitoreo, con datos sintéticos. No es un sistema desplegado ni un producto clínico o laboral.

## Pregunta

> ¿Cuál es el efecto promedio del programa de capacitación laboral sobre los
> ingresos de 1978 en la población representada por la muestra del escenario?

## Estimando

- **ATE** de `treatment` sobre `re78` (efecto total, en dólares de 1978).
- Población: los 1 033 individuos de `observed_train.csv` del escenario
  (la versión de entrenamiento, con hash verificado).
- El intervalo cubre **el efecto promedio poblacional** bajo los supuestos
  declarados; no es un efecto individual ni un CATE identificado. La proyección
  por perfil describe heterogeneidad estimada, no heterogeneidad causal
  identificada.

## Supuestos (y su clase)

| Supuesto | Clase | Cómo se trata aquí |
|---|---|---|
| No confusión condicional en las 8 covariables pre-tratamiento | `no_observable` | Se declara y se defiende por el diseño; DoWhy/DAG comprueba coherencia backdoor con el grafo, pero no verifica ignorabilidad |
| Soporte común (0 < e(X) < 1) | `observable` | Se miden rango de e, ESS de Kish y solapamiento; los rangos marginales del servicio no garantizan soporte multivariable |
| Consistencia / SUTVA | `no_observable` | Se declara; exige ausencia de interferencia y versiones no ambiguas del tratamiento y no tiene chequeo empírico directo |
| Covariables medidas antes del tratamiento | `observable` | El benchmark lo declara (`identification.json`); la trampa `score_post` demuestra qué pasa si no |
| Nuisance models bien especificados según la doble robustez | `supuesto_de_estimacion` | Cross-fitting y diagnósticos; si fallan tanto resultado como propensión, AIPW puede sesgarse aunque la identificación sea válida |

## Qué NO afirma este prototipo

- El estimador principal es **AIPW con cross-fitting** (K=5, semilla declarada):
  es doblemente robusto respecto de las dos piernas solo bajo los supuestos
  causales y de regularidad. No usa learners no lineales ni *repeated
  cross-fitting*: eso queda para el proyecto final. El OLS es una referencia.
- La coincidencia entre diferencia ingenua, OLS y AIPW **no prueba
  identificación**: puede coexistir con confusión o errores de especificación.
- No estima un CATE continuo ni políticas. `POST /consulta` responde la media de
  scores AIPW de **un estrato**, con un solo corte (`nodegree`) predeclarado en
  la tarjeta. `POST /heterogeneidad` devuelve `proyeccion`, un IC condicional al
  ajuste y advertencias; nunca un CATE o efecto individual identificado.
  `POST /efecto_individual` queda como alias deprecado.
- El E-value, cuando se reporta para el ATE, solo cuantifica confusión no
  observada bajo supuestos; no evalúa errores de especificación, positividad o
  consistencia/SUTVA.
- La verdad del escenario (`truth_*.csv`) no existe en este paquete y no se
  usa para nada: la pared se mantiene.
- Ningún resultado se generaliza a decisiones laborales reales.

## Regla del prototipo

Solo `observed_*` alimenta decisiones. El registro, la tarjeta, el servicio
y el monitor trabajan sobre artefactos JSON con hash, nunca sobre datos sueltos
ni serializaciones `pickle`/`joblib`. Las dependencias están fijadas en
`requirements.txt`.
