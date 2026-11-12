# Acceso al código para auditoría

El repositorio es **público** y no requiere cuenta de GitHub, token ni permisos del propietario.

- [Explorar el código](https://github.com/jelincovil/prototipo_ml_causal)
- [Descargar todo el repositorio en ZIP](https://codeload.github.com/jelincovil/prototipo_ml_causal/zip/refs/heads/main)
- [Historial de commits](https://github.com/jelincovil/prototipo_ml_causal/commits/main)

Si una herramienta externa no puede navegar por GitHub, use los enlaces **Texto directo** de esta página: devuelven el contenido en texto plano desde `raw.githubusercontent.com`.

## Código fuente

| Archivo | Contenido | GitHub | Texto directo |
|---|---|---|---|
| `rutas.py` | Raíz del proyecto y selección del escenario | [Ver](https://github.com/jelincovil/prototipo_ml_causal/blob/main/rutas.py) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/rutas.py) |
| `datos.py` | Esquema, hashes y separación de la verdad | [Ver](https://github.com/jelincovil/prototipo_ml_causal/blob/main/datos.py) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/datos.py) |
| `estimacion.py` | AIPW, OLS, diagnósticos e identificación | [Ver](https://github.com/jelincovil/prototipo_ml_causal/blob/main/estimacion.py) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/estimacion.py) |
| `sensibilidad.py` | E-value, robustez, Manski y placebos | [Ver](https://github.com/jelincovil/prototipo_ml_causal/blob/main/sensibilidad.py) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/sensibilidad.py) |
| `cobertura.py` | Simulación Monte Carlo del DGP propio | [Ver](https://github.com/jelincovil/prototipo_ml_causal/blob/main/cobertura.py) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/cobertura.py) |
| `registro.py` | Tarjeta, manifiesto y promoción de versiones | [Ver](https://github.com/jelincovil/prototipo_ml_causal/blob/main/registro.py) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/registro.py) |
| `monitor.py` | Deriva, ventanas y puerta de producción | [Ver](https://github.com/jelincovil/prototipo_ml_causal/blob/main/monitor.py) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/monitor.py) |
| `servicio_core.py` | Carga del bundle, integridad y contratos | [Ver](https://github.com/jelincovil/prototipo_ml_causal/blob/main/servicio_core.py) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/servicio_core.py) |
| `servicio.py` | Endpoints FastAPI y formulario | [Ver](https://github.com/jelincovil/prototipo_ml_causal/blob/main/servicio.py) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/servicio.py) |
| `pruebas_estimacion.py` | Pruebas de fórmulas e invariantes | [Ver](https://github.com/jelincovil/prototipo_ml_causal/blob/main/pruebas_estimacion.py) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/pruebas_estimacion.py) |
| `humo.py` | Prueba de humo del servicio | [Ver](https://github.com/jelincovil/prototipo_ml_causal/blob/main/humo.py) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/humo.py) |

## Configuración y evidencia

| Recurso | GitHub | Texto directo |
|---|---|---|
| Dependencias exactas | [requirements.txt](https://github.com/jelincovil/prototipo_ml_causal/blob/main/requirements.txt) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/requirements.txt) |
| Construcción del contenedor | [Dockerfile](https://github.com/jelincovil/prototipo_ml_causal/blob/main/Dockerfile) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/Dockerfile) |
| Comandos del sistema | [Makefile](https://github.com/jelincovil/prototipo_ml_causal/blob/main/Makefile) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/Makefile) |
| Guía de verificación | [evidencia/README.md](https://github.com/jelincovil/prototipo_ml_causal/blob/main/evidencia/README.md) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/evidencia/README.md) |
| Hashes de evidencia | [evidencia/SHA256SUMS](https://github.com/jelincovil/prototipo_ml_causal/blob/main/evidencia/SHA256SUMS) | [Raw](https://raw.githubusercontent.com/jelincovil/prototipo_ml_causal/main/evidencia/SHA256SUMS) |

## Descarga desde una terminal

Sin autenticación:

```sh
git clone --branch main --single-branch https://github.com/jelincovil/prototipo_ml_causal.git
```

O, sin Git:

```sh
curl -fL https://codeload.github.com/jelincovil/prototipo_ml_causal/zip/refs/heads/main -o prototipo_ml_causal-main.zip
unzip prototipo_ml_causal-main.zip
```

Para congelar la revisión, registre el SHA del commit mostrado en el historial o ejecute `git rev-parse HEAD` dentro del clon. Los enlaces anteriores siguen la rama `main`; un enlace a un archivo también puede fijarse sustituyendo `main` por ese SHA.
