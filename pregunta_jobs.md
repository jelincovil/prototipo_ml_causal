# Pregunta causal del prototipo (se declara ANTES de mirar los datos)

**Escenario:** `real/jobs` del benchmark local (sintético estilo LaLonde 1986, NSW).

## Pregunta

> ¿Cuál es el efecto del programa de capacitación laboral sobre los ingresos
> de 1978 de quienes lo recibieron?

## Estimando

- **ATE** de `treatment` sobre `re78` (efecto total, en dólares de 1978).
- Población: los 1 033 individuos de `observed_train.csv` del escenario
  (la versión de entrenamiento, con hash verificado).
- El intervalo cubre **el efecto promedio poblacional**; no es un efecto
  individual ni un CATE. Este prototipo no estima heterogeneidad.

## Supuestos (y su clase)

| Supuesto | Clase | Cómo se trata aquí |
|---|---|---|
| No confusión condicional en las 8 covariables pre-tratamiento | `no_observable` | Se declara; la identificación lo exige y ningún dato lo verifica |
| Soporte común (0 < e(X) < 1) | `observable` | Se mide: rango de e, ESS de Kish, fracción en zona de solapamiento |
| Consistencia / SUTVA | `no_observable` | Se declara; heredado del diseño del escenario |
| Covariables medidas antes del tratamiento | `observable` | El benchmark lo declara (`identification.json`); la trampa `score_post` demuestra qué pasa si no |

## Qué NO afirma este prototipo

- El estimador principal es **AIPW con cross-fitting** (K=5, semilla declarada):
  doblemente robusto y con nuisances fuera de muestra — la exigencia central
  del Cap. 9 cumplida en miniatura. Sin learners no lineales ni repeated
  cross-fitting: eso es el proyecto final. El OLS queda como referencia.
- No estima un CATE continuo ni políticas: `/consulta` responde la media de
  scores AIPW de **un estrato**, con un solo corte (`nodegree`) cuya regla está
  pre-declarada en la tarjeta. Los intervalos de los estratos se solapan:
  heterogeneidad sugerida, no concluyente.
- La verdad del escenario (`truth_*.csv`) no existe en este paquete y no se
  usa para nada: la pared se mantiene.

## Regla del prototipo

Solo `observed_*` alimenta decisiones. El registro, la tarjeta, el servicio
y el monitor trabajan sobre artefactos con hash, nunca sobre datos sueltos.
