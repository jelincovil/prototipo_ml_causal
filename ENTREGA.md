# ENTREGA — Semana 4: el puente sobre `real/ihdp`

**Qué se entrega:** tu `proyecto/` completo con el notebook ejecutado, los TODOs
resueltos y adaptados a `real/ihdp`, y los artefactos que tu prototipo produjo.
Formato igual al del curso: sin cuentas externas, todo corre local.

## Checklist de entrega

- [ ] **Notebook con salidas** (`proyecto.ipynb`): ejecutado de punta a punta
      sobre `real/jobs` (los cinco checkpoints en verde) y con la sección 7
      completada sobre `real/ihdp`.
- [ ] **TODOs resueltos** en `datos.py`, `estimacion.py`, `registro.py`,
      `monitor.py` y `servicio_core.py` (los 22 del kit).
- [ ] **Adaptación a ihdp** declarada: qué cambiaste y por qué (esquema con las
      25 covariables, tu corte de heterogeneidad con su regla, tus ventanas de
      deriva y positividad, tus umbrales recalibrados con justificación).
- [ ] **Tu pregunta para ihdp** (sección 7 del notebook o archivo propio):
      pregunta, estimando, población, supuestos con su clase, qué NO afirma.
- [ ] **Tabla de números** completa (sección 7 del notebook).
- [ ] **Respuestas** de ventanas (3) y de cierre (5), en las celdas del notebook.
- [ ] **Artefactos de ihdp**: `artifacts/estimacion.json` y `artifacts/registro/`
      con `vNNNN/manifest.json` y `champion` (no borres nada: la versión es
      inmutable y la entrega la audita).
- [ ] `make humo` en verde sobre ihdp (la salida pegada en el notebook).

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
| Umbrales justificados | dos líneas por umbral, calibrados para ihdp |
