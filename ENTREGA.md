# ENTREGA — Semana 4: el puente sobre `synthetic/ihdp`

**Alcance:** Prototipo local de estimación causal con AIPW, abstención fuera de soporte y monitoreo, con datos sintéticos. No es un sistema desplegado ni un producto clínico o laboral.

**Qué se entrega:** tu `proyecto/` completo con el notebook ejecutado, los TODOs
resueltos y adaptados a `synthetic/ihdp`, y los artefactos que tu prototipo produjo.
Formato igual al del curso: sin cuentas externas, todo corre local.

## Checklist de entrega

Las marcas reflejan el estado documentado en `docs/BITACORA.md` y las salidas
conservadas en `evidencia/`; no sustituyen una nueva ejecución de las comprobaciones.

- [x] **Notebook con salidas históricas** (`proyecto.ipynb`): cinco checkpoints
      en verde y sección 7 completada. Las rutas se actualizaron a `synthetic/*`;
      sus salidas no se volvieron a ejecutar tras ese cambio de nombres.
- [x] **TODOs resueltos** en `datos.py`, `estimacion.py`, `registro.py`,
      `monitor.py` y `servicio_core.py` (los 22 del kit).
- [x] **Adaptación a ihdp** declarada: qué cambiaste y por qué (esquema con las
      25 covariables, tu corte de heterogeneidad con su regla, tus ventanas de
      deriva y positividad, tus umbrales iniciales con justificación y sin
      presentarlos como calibración universal).
- [x] **Tu pregunta para ihdp** (sección 7 del notebook o archivo propio):
      pregunta, estimando, población, supuestos con su clase, qué NO afirma.
- [x] **Tabla de números** completa (sección 7 del notebook).
- [x] **Respuestas** de ventanas (3) y de cierre (5), en las celdas del notebook.
- [x] **Artefactos de ihdp**: `artifacts/estimacion.json` y `artifacts/registro/`
      con `vNNNN/manifest.json` y `champion` (no borres nada: la versión es
      inmutable y la entrega la audita).
- [x] `make humo` en verde sobre ihdp (la salida pegada en el notebook).

## Estado y límites de la actualización

- `POST /heterogeneidad` devuelve `proyeccion`, IC condicional al ajuste y
  advertencias; nunca un CATE o efecto individual identificado.
  `POST /efecto_individual` queda como alias deprecado.
- El monitor incluye sensibilidad de umbrales de ±20 % (factores `.8`, `1`,
  `1.2`): la corrida conservada tuvo **0 cambios de acción** fuera de la
  clasificación base. Los umbrales siguen siendo convenciones iniciales, no una
  calibración universal.
- `make cobertura` generó `artifacts/cobertura.json` para el DGP ilustrativo
  propio (`n = 500`, `R = 100`, semilla `20261111`). Coberturas IC95: **0,97
  AIPW**, **0,96 OLS** y **0,00 ingenuo**, con errores Monte Carlo 0,01706,
  0,01960 y 0. AIPW difiere 0,02 del nominal y no está dentro de ±1 error Monte
  Carlo. No evalúa IHDP/jobs ni demuestra calibración general.
- La validación del champion **`v0009`** dio `PRUEBAS: OK` y `HUMO: OK`;
  `v0001`–`v0008` permanecen intactas. Esta versión incorpora Rosenbaum Γ,
  cotas de Manski y placebos con interpretación en `/efecto` y `/salud`.
  Las ediciones documentales por sí solas no promueven versiones.
- Los artefactos son JSON, no `pickle`/`joblib`, y las dependencias están
  fijadas con versiones exactas en `requirements.txt`.
- DoWhy/DAG no verifica ignorabilidad; los rangos marginales no garantizan
  soporte multivariable; y la coincidencia ingenuo/OLS/AIPW no prueba
  identificación. El E-value solo cuantifica confusión no observada bajo supuestos:
  no detecta errores de especificación ni fallos de positividad o SUTVA.

## Reglas

1. **La pared se mantiene**: `truth_*.csv` no existe en el paquete y la
   referencia del DGP (~4,0) no se usa para estimar, decidir ni calibrar.
2. El corte de heterogeneidad y los umbrales se **declaran antes de mirar**
   resultados; la justificación es parte de la entrega.
3. El estimador principal es el AIPW con cross-fitting; el OLS queda como
   referencia. No se pide DML completo (eso es el proyecto final).
4. Nada de `truth`, `y0`, `y1` ni `tau` en entrenamiento, bundle o servicio.

## Criterios de revisión (formativos)

| Criterio | Señal |
|---|---|
| Estimando declarado y cubierto | la tabla distingue ATE de estrato y dice qué cubre cada IC |
| Reproducibilidad | `make demo` desde cero regenera tus números |
| Puerta honesta | la ventana de positividad bloquea y el motivo nombra la señal |
| Abstención | `/consulta` fuera de soporte responde sin número (HTTP 200) |
| Corte pre-declarado | la regla está en la tarjeta, no elegida por ganancia |
| Umbrales justificados | dos líneas por umbral; convenciones iniciales para ihdp, no calibración universal |
