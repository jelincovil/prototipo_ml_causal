# Proyecto — «Puente» (semana 4)

## Windows sin terminal (recomendado)

1. Descarga **[PuenteCausal.exe](https://github.com/jelincovil/prototipo_ml_causal/releases/latest/download/PuenteCausal.exe)**. También está disponible su [SHA-256](https://github.com/jelincovil/prototipo_ml_causal/releases/latest/download/PuenteCausal.exe.sha256).
2. Haz doble clic y pulsa **Instalar / verificar**.
3. Pulsa **Iniciar servicio** y después **Abrir ATE**.

El navegador mostrará **http://127.0.0.1:8000/efecto**. El lanzador instala en `%LOCALAPPDATA%\PuenteCausal`, muestra sus errores y registros, y no exige abrir una terminal, permisos de administrador, .NET SDK ni herramientas de compilación. Usa de forma oculta el PowerShell incluido en Windows solo para descomprimir archivos. Lee [uso, desinstalación y diagnóstico](instalador_windows/LEEME.md). El binario no está firmado comercialmente, por lo que Windows SmartScreen puede advertir. Este lanzador está fijado al release `v1.0.3` y conserva su champion `v0008`; para usar el champion `v0009` de `main`, emplea los scripts o Docker.

## Puesta en marcha en 1 comando

Linux/Mac:

```sh
bash setup.sh && bash arrancar.sh
```

Windows PowerShell (alternativa a la interfaz gráfica):

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
if ($LASTEXITCODE -eq 0) {
    powershell -ExecutionPolicy Bypass -File arrancar.ps1
}
```

Es compatible con Windows PowerShell 5.1: no usa `&&` y no arranca el servicio si la instalación falla. Este flujo ha recibido revisión estática, pero no se ha ejecutado en Windows nativo; consulta [Estado de la segunda verificación](#estado-de-la-segunda-verificación-multiplataforma).

Docker (opcional):

```sh
docker compose up
```

Los scripts usan `uv`: instalan `uv` y Python 3.13 si faltan, **recrean `.venv`** e instalan `requirements.txt`. Son idempotentes, pero descartan paquetes adicionales o personalizaciones del entorno anterior. El lanzador gráfico, en cambio, reutiliza un entorno válido y solo lo recrea al elegir **Reparar entorno**. Todas las vías usan `synthetic/ihdp`, sin ejecutar `make demo` ni `make evidencia` y sin modificar `artifacts/`; los scripts y Docker sirven el champion **`v0009`**, mientras el lanzador conserva el de su release. Con los scripts, deja la terminal abierta y visita **http://127.0.0.1:8000/efecto**; también están disponibles **/salud** y **/docs**. Pulsa Ctrl-C para detenerlo. Con el lanzador, cierra la ventana o pulsa **Detener**.

Repositorio público del prototipo: **[github.com/jelincovil/prototipo_ml_causal](https://github.com/jelincovil/prototipo_ml_causal)**.

**Acceso para auditoría (sin cuenta ni token):** [índice del código fuente y enlaces de texto directo](AUDITORIA.md) · [descargar ZIP](https://codeload.github.com/jelincovil/prototipo_ml_causal/zip/refs/heads/main).

**Alcance:** Prototipo local de estimación causal con AIPW, abstención fuera de soporte y monitoreo, con datos sintéticos. No es un sistema desplegado ni un producto clínico o laboral.

Usa los escenarios `synthetic/ihdp` y `synthetic/jobs`. Estima el ATE con AIPW y
cross-fitting, declara los supuestos de identificación, acompaña el resultado con
sensibilidad y placebos, y lo publica mediante un registro versionado, un monitor
y una API con abstención. No usar para decisiones clínicas, laborales o de
política pública.

## Supuestos y consecuencias

| Supuesto | Cómo se verifica | Qué pasa si falla |
|---|---|---|
| **Ignorabilidad condicional** | No se verifica con los datos observados: se defiende mediante el diseño/DGP y se explora con placebos y análisis de sensibilidad. | El ATE ajustado puede quedar confundido; AIPW, OLS y la diferencia ingenua no recuperan por sí solos identificación causal. |
| **Positividad / soporte común** | Se examinan propensiones, ESS y solapamiento, se someten ventanas a estrés y el servicio se abstiene ante perfiles fuera de soporte. | No hay ATE identificado para toda la población objetivo sin restricciones o información adicional; corresponde abstenerse o acotar, no extrapolar. |
| **Consistencia / SUTVA** | No tiene un chequeo empírico directo: exige tratamiento bien definido, una sola versión relevante y ausencia de interferencia, justificados por el diseño. | El efecto estimado puede no corresponder a una intervención bien definida; cambian los resultados potenciales y el estimando. |
| **Nuisance models** (resultado y propensión) | Cross-fitting, diagnósticos de ajuste, balance y comparación con OLS/estimación ingenua; la doble robustez exige que al menos una pierna esté bien especificada, además de los supuestos causales. | Si ambas piernas fallan, AIPW puede sesgarse y su IC puede resultar inadecuado; cross-fitting no corrige una mala especificación. |

### Qué no demuestran los diagnósticos

- **DoWhy/DAG no verifica ignorabilidad.** El DAG y la coincidencia con un
  `valid_adjustment_set` comprueban coherencia algebraica con el grafo declarado,
  no la ausencia de confusores no observados ni la validez empírica del grafo.
- **Los rangos marginales no garantizan soporte multivariable.** Que cada
  covariable esté dentro de su rango de entrenamiento no asegura que el vector
  completo tenga tratados y controles comparables.
- **La coincidencia entre estimación ingenua, OLS y AIPW no prueba
  identificación.** Es, como mucho, un diagnóstico de estabilidad entre
  estimadores; los tres pueden compartir sesgo de confusión o especificación.
- **El E-value solo cuantifica confusión no observada bajo sus supuestos.** No
  cubre errores de especificación, fallos de positividad ni violaciones de
  consistencia/SUTVA, y su aproximación para resultado continuo no es una RR literal.
- **Los umbrales del monitor son convenciones iniciales**, no una calibración
  universal. El monitor incluye un análisis de sensibilidad de ±20 % con
  factores `.8`, `1` y `1.2`. En la corrida conservada hubo **0 cambios de
  acción** fuera de la clasificación base; esa estabilidad local tampoco prueba
  identificación.

### Cobertura Monte Carlo

`make cobertura` genera `artifacts/cobertura.json` para un **DGP ilustrativo
propio**, con `n = 500`, `R = 100` y semilla `20261111`. La corrida conservada
obtuvo coberturas IC95 de **0,97 (AIPW)**, **0,96 (OLS ajustado)** y **0,00
(ingenuo)**, con errores Monte Carlo de 0,01706, 0,01960 y 0. El AIPW difiere
0,02 del nominal y no queda dentro de ±1 error Monte Carlo: no es una
calibración exacta. Estas cifras solo se refieren a ese DGP, no a IHDP/jobs ni
a datos reales.

## Instalación manual alternativa (sin los scripts)

No ejecutes este bloque después de `setup`: es una alternativa para quien ya administra su entorno. Requiere **Python 3.13**:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export SIC_ESCENARIO=synthetic/ihdp
```

`requirements.txt` fija versiones exactas de las **dependencias directas**, pero no es un lockfile de todas las dependencias transitivas. `uv pip check` comprueba compatibilidad del entorno instalado; no garantiza una reconstrucción byte a byte. Graphviz (`dot`) solo se necesita para `make dag`; Typst, para `make cierre`; `make` y las herramientas de hashes solo para comprobaciones o mantenimiento, no para instalar.

## Comprobar el paquete existente

No hace falta activar el entorno ni tener `make`. En Linux/macOS, desde la raíz:

```sh
SIC_ESCENARIO=synthetic/ihdp .venv/bin/python datos.py
SIC_ESCENARIO=synthetic/ihdp .venv/bin/python pruebas_estimacion.py
SIC_ESCENARIO=synthetic/ihdp .venv/bin/python humo.py
shasum -a 256 -c evidencia/SHA256SUMS
# En Linux, si shasum no está disponible:
sha256sum -c evidencia/SHA256SUMS
```

En Windows PowerShell:

```powershell
$env:SIC_ESCENARIO = "synthetic/ihdp"
.\.venv\Scripts\python.exe datos.py
.\.venv\Scripts\python.exe pruebas_estimacion.py
.\.venv\Scripts\python.exe humo.py
```

`Get-FileHash -Algorithm SHA256 <archivo>` permite contrastar un archivo individual con `evidencia/SHA256SUMS`; no procesa automáticamente toda la lista. Con `make` y el entorno activado, los atajos equivalentes son `make verificar`, `make pruebas` y `make humo`.

Estas comprobaciones no cambian el champion. Resultado esperado: esquema, splits y pared de verdad correctos, `PRUEBAS: OK`, `HUMO: OK` y todos los hashes correctos. Los hashes detectan diferencias respecto de la lista conservada, pero no firman ni autentican el origen de los archivos.

## Regenerar el flujo

```sh
make demo         # datos → estimación → registro → monitor → humo
make evidencia    # además reconstruye las salidas y hashes de evidencia/
make pruebas      # conviene ejecutarlo después de regenerar
```

**Atención:** `make demo` y `make evidencia` crean una nueva versión inmutable
`vNNNN` y promueven un nuevo champion. No son comandos de solo lectura.
`make demo` verifica los CSV incluidos y luego ejecuta estimación → registro → monitor → humo; **no genera el dataset IHDP desde cero**. `cobertura.py` simula otro DGP ilustrativo, no regenera IHDP.
`make evidencia` también sobrescribe los archivos generados dentro de `evidencia/`.

El orden registro → monitor **no es transaccional**: `registro.py` puede promover antes de que corra el monitor y no hay rollback automático si una etapa posterior falla. `promover()` bloquea únicamente una versión cuyo `manifest.puerta` ya sea `falla`; `alerta` requiere aceptación explícita. Tras regenerar, comprueba alias, `monitor_estado.json` y `/salud`.

El champion conservado es **`v0009`**; las versiones históricas **`v0001`–`v0008`**
permanecen intactas. La versión actual sirve Rosenbaum Γ, cotas de Manski y ambos
placebos con sus interpretaciones y límites en `/efecto` y `/salud`. Editar documentación o hashes de `evidencia/` no promueve
una versión nueva.

Otros objetivos útiles:

```sh
make dag          # regenera los SVG con Graphviz
make cierre       # compila manual_sistema_causal.typ a PDF
make cobertura    # opcional: Monte Carlo del DGP propio; escribe cobertura.json
make limpiar      # borra TODO artifacts/, incluidos champion y versiones
```

`make limpiar` no es una limpieza rutinaria de cachés: elimina el resultado completo.

## Levantar el servicio

Con el entorno activado:

```sh
export SIC_ESCENARIO=synthetic/ihdp
make servir
```

Equivalente manual, con el entorno activado:

```sh
SIC_ESCENARIO=synthetic/ihdp uvicorn servicio:app --host 127.0.0.1 --port 8000
```

Abrir:

- <http://127.0.0.1:8000/> — formulario para consultar un perfil.
- <http://127.0.0.1:8000/efecto> — ATE e incertidumbre del champion.
- <http://127.0.0.1:8000/salud> — versión, puerta, integridad e identificación.
- <http://127.0.0.1:8000/docs> — documentación interactiva de FastAPI.

Pulsar **Ctrl-C** para detenerlo. El bundle válido se carga en la **primera consulta** y se cachea hasta reiniciar; una carga fallida no se cachea, de modo que puede recuperarse tras corregir el artefacto. Reinicia después de cambiar de escenario, champion o monitor cuando ya exista una caché válida.

## Qué devuelve la API

- `GET /efecto` — ATE, IC, identificación backdoor/DoWhy, E-value, valor de
  robustez, cotas de Manski y resultados de los placebos, todos sujetos a los
  límites de interpretación declarados arriba.
- `POST /consulta` — media de un estrato declarado con IC; no es un CATE.
- `POST /heterogeneidad` — devuelve `proyeccion`, un IC **condicional al ajuste**
  y advertencias; nunca un CATE o efecto individual identificado. El bloque separado
  `diagnosticos_globales` reúne el ATE, su IC, Rosenbaum, Manski y los placebos como
  referencia poblacional: no son medidas del perfil ni validan su proyección.
- `POST /efecto_individual` — alias deprecado de `/heterogeneidad`, conservado por
  compatibilidad y con la misma advertencia causal.
- `GET /salud` — estado del servicio, versión, puerta, integridad del manifiesto y
  resumen de identificación, sensibilidad y placebos.
- `GET /` y `GET /calcular` — formulario web.

El servicio no lee CSV: usa únicamente el bundle del champion. Si la integridad
falla, la puerta activa es `falla` o un perfil queda fuera de soporte, se
abstiene sin inventar un número. Los artefactos son **JSON**, no `pickle` ni `joblib`; los hashes verifican diferencias, pero no autentican su procedencia.

Las entradas deben ser objetos JSON con números finitos. La validación actual no define un esquema Pydantic por covariable: un valor como `{"bw":"alto"}` puede producir **HTTP 500**, no una abstención. Los clientes deben validar tipos y distinguir errores HTTP de abstenciones causales.

## Orden de lectura

1. [`docs/pregunta_ihdp.md`](docs/pregunta_ihdp.md) — pregunta, estimando, supuestos, resultados históricos y límites.
2. [`data_benchmark_causal/causal_benchmark_synthetic/datasets/manual_sistema_causal.pdf`](data_benchmark_causal/causal_benchmark_synthetic/datasets/manual_sistema_causal.pdf)
   — explicación completa; el fuente editable es el `.typ` vecino.
3. `datos.py` → `estimacion.py` → `registro.py` → `monitor.py` →
   `servicio_core.py` → `servicio.py` — recorrido del dato a la API.
4. [`evidencia/README.md`](evidencia/README.md) — trazabilidad de comandos, salidas y hashes.
5. [`docs/GUIA_CONSTRUCCION.md`](docs/GUIA_CONSTRUCCION.md) y su versión
   [`docs/GUIA_CONSTRUCCION.pdf`](docs/GUIA_CONSTRUCCION.pdf) — guía de construcción.
6. [`docs/LEEME_AGENTE.md`](docs/LEEME_AGENTE.md) — operación e invariantes.

## Estructura breve

```text
rutas.py                 raíz del proyecto y selección de escenario
datos.py                 esquema, hashes de splits y pared de verdad
estimacion.py            AIPW, OLS, diagnósticos e identificación DoWhy
sensibilidad.py          E-value, robustez, Manski y placebos
registro.py              tarjeta, manifiesto y promoción con comprobaciones locales
monitor.py               ventanas, deriva y puerta
servicio_core.py         carga del bundle, integridad y contratos de respuesta
servicio.py              endpoints FastAPI y formulario
pruebas_estimacion.py    pruebas de fórmulas e invariantes
humo.py                  prueba de humo del servicio
cobertura.py             simulación opcional en el DGP ilustrativo propio
artifacts/               artefactos JSON, champion v0009 y versiones históricas
evidencia/               salidas y hashes del cierre
data_benchmark_causal/   escenarios sintéticos y documentación
docs/                    guía, bitácora, preguntas causales y material docente
docs/historico/          material original y archivos auxiliares no operativos
```

La raíz conserva el código fuente y el notebook; `README.md` es la entrada y
`ENTREGA.md` registra el estado académico. Los escenarios y sus documentos están en
`data_benchmark_causal/`; los resultados versionados en `artifacts/`; y las salidas
y hashes de verificación en `evidencia/`. El material histórico no operativo está
separado en `docs/historico/`; no interviene en la ejecución del prototipo.

Las versiones de `artifacts/registro/` son inmutables. Los entornos `.venv*` y los
cachés `__pycache__/` son locales y regenerables; no forman parte del entregable.

## Estado de la segunda verificación multiplataforma

| Plataforma | Verificación realizada | Resultado / alcance |
|---|---|---|
| **macOS arm64** | Copia limpia en una ruta con espacios; `setup.sh` ejecutado dos veces; datos, pruebas y humo; `arrancar.sh` y consultas HTTP reales | Python 3.13.14, 140 paquetes y `uv pip check` correctos. `PRUEBAS: OK`, `HUMO: OK`; ATE e IC, estrato y abstención fuera de soporte correctos con `v0009`. |
| **Linux arm64 mediante Docker Engine (Colima)** | `docker build`, `docker run`, healthcheck y endpoints HTTP | Imagen construida y contenedor `healthy`; ATE, consulta y abstención correctos. No implica prueba en Windows ni en todas las arquitecturas Linux. |
| **Docker Compose** | Revisión estática de `docker-compose.yml` | No ejecutado: el plugin Compose no estaba instalado. El healthcheck exige `estado=ok`, integridad válida, puerta `pasa` y versión esperada. |
| **Windows / lanzador gráfico** | Compilación MSVC y `ctest --self-test` en `windows-2022`, [ejecución 43322853322](https://github.com/jelincovil/prototipo_ml_causal/actions/runs/43322853322) | Superadas con `v0008`. La publicación del release exige además una instalación nativa `--smoke-test`, arranque real, integridad válida, puerta `pasa` y `/efecto` con efecto e IC; los assets no se adjuntan si esta prueba falla. La interacción gráfica en el PC del usuario y la repetición integral con `v0009` aún deben comprobarse. |
| **Windows / PowerShell** | Revisión estática de `setup.ps1`, `arrancar.ps1` y comandos del manual | Los scripts no han sido ejecutados en Windows nativo. Están escritos para Windows PowerShell 5.1; el lanzador gráfico es la vía recomendada y no depende de ellos. |

La segunda auditoría no ejecutó `make demo` ni `make evidencia`, y no modificó el champion ni los artefactos conservados. Persisten la falta de pruebas del flujo PowerShell y de la GUI en el equipo del usuario, además de dos límites de reproducibilidad: no hay lockfile transitivo ni digest fijado para la imagen base de Docker. Estas pruebas verifican instalación y contratos del prototipo; no certifican identificación causal ni preparación para exposición pública.
