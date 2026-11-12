# Paquete de evidencia — prototipo «Puente» (`synthetic/ihdp`)

Cada cifra del cierre tiene aquí su comando, su salida y su hash. La corrida
conservada usa el champion **`v0008`**; `v0001`–`v0007` permanecen intactas.
Los hashes se verifican con:

```sh
shasum -a 256 -c evidencia/SHA256SUMS
```

| Archivo | Comando | Qué contiene |
|---|---|---|
| `01_datos.txt` | `SIC_ESCENARIO=synthetic/ihdp python3 datos.py` | esquema C-01, hashes de splits, pared |
| `02_estimacion.txt` | `SIC_ESCENARIO=synthetic/ihdp python3 estimacion.py` | ATE ingenuo/OLS/AIPW, IC, positividad OOF, SMD, validación |
| `03_sensibilidad.txt` | `cp artifacts/sensibilidad.json` | E-value, valor de robustez y cotas de Manski |
| `04_placebo.txt` | `cp artifacts/placebo.json` | placebo de tratamiento y de resultado |
| `05_puerta.txt` | `SIC_ESCENARIO=synthetic/ihdp python3 monitor.py` | cinco ventanas, acciones y sensibilidad de umbrales ±20 % |
| `06_registro.txt` | `SIC_ESCENARIO=synthetic/ihdp python3 registro.py` | tarjeta, manifiesto, mutación, alias y `v0008` |
| `07_servicio.txt` | `SIC_ESCENARIO=synthetic/ihdp python3 humo.py` | backdoor, sensibilidad, placebos, integridad y abstención |
| `08_dag.txt` | `make dag` + `shasum` | hashes de los SVG del DAG |
| `09_pruebas.txt` | `SIC_ESCENARIO=synthetic/ihdp python3 pruebas_estimacion.py` | asserts de fórmulas e invariantes |
| `10_cobertura.txt` | `SIC_ESCENARIO=synthetic/ihdp python3 cobertura.py` | resumen de la simulación Monte Carlo |
| `10_cobertura.json` | `cp artifacts/cobertura.json` | cobertura, sesgo, RMSE y errores Monte Carlo |

## Trazabilidad de cifras del cierre

| Cifra | Archivo |
|---|---|
| Diferencia cruda 10,3 [7,60; 13,05]; OLS 4,8 [3,8; 5,8]; AIPW 5,2 [3,9; 6,4] | `02_estimacion.txt` |
| E-value 2,07 / RV 37,4 % / Manski [−37,66; 48,48] | `03_sensibilidad.txt` |
| Placebo D p=0,005; placebo Y 0,04 [-0,23; 0,32] | `04_placebo.txt` |
| Propensiones OOF antes del trimming: ESS 332/448 (0,74); rango [0,043; 0,916]; solape 0,99777 (≈99,8 %; CLI redondea 100 %) | `02_estimacion.txt` y `artifacts/estimacion.json` |
| Un recorte de control (0,3891 % de controles; 0,2232 % del total); ninguno tratado; SMD ponderado OOF 0,11 | `artifacts/estimacion.json` |
| Puerta de producción `pasa`; positividad de estrés `falla` / `abstenerse`; 0 cambios con umbrales ±20 % | `05_puerta.txt` |
| Cobertura IC95 en DGP propio: AIPW 0,97; OLS 0,96; ingenuo 0,00 | `10_cobertura.txt` y `10_cobertura.json` |
| Champion `v0008` y alias | `06_registro.txt` |
| Servicio: backdoor pasa, sensibilidad, placebos pasan, integridad y abstención | `07_servicio.txt` |
| DAG de una página y detalle | `08_dag.txt` |
| Pruebas de fórmulas e invariantes | `09_pruebas.txt` |

## Notas de alcance

Los datos son sintéticos. La evidencia demuestra reproducibilidad y coherencia
interna del prototipo; no demuestra validez externa ni identificación causal en
datos reales. La coincidencia entre estimadores es estabilidad, no identificación.
Las cotas de Manski usan el rango observado de `Y` como ilustración; no garantizan
el soporte poblacional ni identifican el ATE puntual sin ignorabilidad.

La cobertura corresponde a un DGP ilustrativo propio (`n = 500`, `R = 100`,
semilla `20261111`), no a IHDP/jobs. Los errores Monte Carlo son 0,01706 (AIPW),
0,01960 (OLS) y 0 (ingenuo). AIPW difiere 0,02 del nominal y no queda dentro de
±1 error Monte Carlo: no se afirma calibración exacta. Los 0 cambios al variar
los umbrales ±20 % describen solo estabilidad local en esta corrida, no una
calibración universal.
