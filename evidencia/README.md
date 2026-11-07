# Paquete de evidencia — prototipo «Puente» (`real/ihdp`)

Cada cifra del cierre tiene aquí su comando, su salida y su hash. Los hashes
están en `SHA256SUMS`; se verifican con:

```sh
shasum -a 256 -c evidencia/SHA256SUMS
```

| Archivo | Comando | Qué contiene |
|---|---|---|
| `01_datos.txt` | `SIC_ESCENARIO=real/ihdp python3 datos.py` | esquema C-01, hashes de splits, pared |
| `02_estimacion.txt` | `SIC_ESCENARIO=real/ihdp python3 estimacion.py` | ATE AIPW/OLS, IC, ESS, SMD, validación |
| `03_sensibilidad.txt` | `cp artifacts/sensibilidad.json` | E-value y valor de robustez |
| `04_placebo.txt` | `cp artifacts/placebo.json` | placebo de tratamiento y de resultado |
| `05_puerta.txt` | `SIC_ESCENARIO=real/ihdp python3 monitor.py` | cinco ventanas, señales y acciones |
| `06_registro.txt` | `SIC_ESCENARIO=real/ihdp python3 registro.py` | tarjeta, manifiesto, mutación, alias |
| `07_servicio.txt` | `SIC_ESCENARIO=real/ihdp python3 humo.py` | contrato del servicio y abstención |
| `08_dag.txt` | `make dag` + `shasum` | hashes de los SVG del DAG |
| `09_pruebas.txt` | `SIC_ESCENARIO=real/ihdp python3 pruebas_estimacion.py` | asserts de fórmulas e invariantes |

## Trazabilidad de cifras del cierre

| Cifra | Archivo |
|---|---|
| ATE AIPW 5,2 [3,9; 6,4] | `02_estimacion.txt` |
| E-value 2,07 / RV 37,4 % | `03_sensibilidad.txt` |
| Placebo D p=0,005; placebo Y 0,04 [-0,23; 0,32] | `04_placebo.txt` |
| ESS 388/448; rango e [0,071; 0,887] | `02_estimacion.txt` |
| Puerta de producción `pasa`; peor estrés `abstenerse` | `05_puerta.txt` |
| Versión champion y alias | `06_registro.txt` |
| Servicio: puerta, sensibilidad, placebo, abstención | `07_servicio.txt` |
| DAG de una página y detalle | `08_dag.txt` |
| Pruebas de fórmulas e invariantes | `09_pruebas.txt` |

## Nota de alcance

Los datos son sintéticos. La evidencia demuestra reproducibilidad y
coherencia interna del prototipo; no demuestra validez externa ni
identificación causal en datos reales.
