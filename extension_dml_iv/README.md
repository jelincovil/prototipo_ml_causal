# Extensión DML-IV

Ejemplo autocontenido para incorporar **otro dataset, otro DAG y otro método causal** sin modificar el prototipo original.

Enseña la cadena:

```text
Datos → roles y particiones → DAG instrumental → DoubleML-IV → LATE e IC → evaluación
```

No crea servicio, registro, monitor ni `champion`, y no escribe en `artifacts/`.

## Caso y método

- `z`: invitación aleatoria a tutoría (**instrumento**).
- `d`: asistencia efectiva (**tratamiento**).
- `y`: puntaje final (**resultado**).
- `x1`, `x2`: covariables observadas.
- `U`: confusora no observada; nunca entra en la estimación.

```text
Z → D → Y
    ↑   ↑
    └── U ┘
X1, X2 → D e Y
```

El método es `DoubleMLIIVM` con tres pliegues. Estima el **LATE entre compliers**, no el ATE poblacional ni efectos individuales.

## Ejecutar

Desde esta carpeta, con `uv` instalado.

### macOS o Linux

```sh
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python demo_iv.py
```

### Windows PowerShell

```powershell
uv venv --python 3.13 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\python.exe demo_iv.py
```

Los datos están incluidos; no hace falta regenerarlos.

## Otras demostraciones

```sh
# Instrumento débil
.venv/bin/python demo_iv.py --escenario debil

# Violación del supuesto de exclusión
.venv/bin/python demo_iv.py --escenario exclusion

# Evaluación Monte Carlo didáctica
.venv/bin/python demo_iv.py --repeticiones 30

# Pruebas
.venv/bin/python pruebas_iv.py
```

En Windows, sustituye `.venv/bin/python` por `.\.venv\Scripts\python.exe`.

Los escenarios alternativos se generan en memoria y no alteran los datos base. Los resultados se guardan en `salida/`.

## Cómo leer la salida

1. **Diferencia ingenua:** compara tratados y no tratados; puede estar confundida.
2. **Primera etapa:** mide cuánto cambia la asistencia con la invitación. Una etapa fuerte no demuestra que el instrumento sea válido.
3. **LATE e IC95:** estimación principal para los compliers.
4. **Referencia sintética:** se consulta solo después de estimar. Sirve para evaluar el ejemplo, no para ajustar el modelo.

La demostración de exclusión muestra que DML no corrige un efecto directo de `Z` sobre `Y`. La de instrumento débil muestra la pérdida de precisión.

## Archivos principales

| Archivo | Función |
|---|---|
| `generar_datos_iv.py` | Genera el dataset y la referencia separada |
| `datos_iv.py` | Valida roles, hashes y separación de la verdad |
| `estimacion_iv.py` | Estima el LATE con DoubleML |
| `demo_iv.py` | Ejecuta y explica el ejemplo |
| `pruebas_iv.py` | Comprueba integridad y reproducibilidad |
| `rutas_iv.py` | Mantiene las rutas dentro de esta carpeta |

El prototipo original permanece intacto.
