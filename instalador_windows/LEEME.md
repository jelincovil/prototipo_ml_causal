# PuenteCausal.exe — Windows sin terminal

Lanzador gráfico para instalar y usar el prototipo **sin abrir PowerShell, CMD ni Terminal**.

## Uso

1. Descarga **`PuenteCausal.exe`** desde [Releases](https://github.com/jelincovil/prototipo_ml_causal/releases/latest).
2. Haz doble clic. Si SmartScreen muestra una advertencia, comprueba que la descarga procede del enlace anterior. El ejecutable **no está firmado comercialmente**.
3. Pulsa **1. Instalar / verificar** y espera el mensaje de instalación lista.
4. Pulsa **2. Iniciar servicio**.
5. Pulsa **3. Abrir ATE**. Verás el resultado del champion en el navegador.

También puedes abrir **`/docs`** para probar los endpoints y **Abrir registros** para consultar la actividad. **Detener** cierra Uvicorn y sus procesos hijos. Cerrar la ventana también detiene el servicio que haya iniciado ese lanzador.

Direcciones locales:

- ATE e incertidumbre: <http://127.0.0.1:8000/efecto>
- Estado, puerta e integridad: <http://127.0.0.1:8000/salud>
- Documentación interactiva: <http://127.0.0.1:8000/docs>

## Qué instala y dónde

Usa exclusivamente esta carpeta:

```text
%LOCALAPPDATA%\PuenteCausal
```

Normalmente corresponde a `C:\Users\<usuario>\AppData\Local\PuenteCausal`. En el Explorador puedes pegar `%LOCALAPPDATA%\PuenteCausal` en la barra de direcciones.

- `app/`: fuente de `v1.0.1` del repositorio y artefactos conservados.
- `herramientas/`: `uv` 0.13.8 y Python 3.13 administrado por `uv`.
- `cache/`: descargas de paquetes utilizadas por `uv`.
- `registros/lanzador.log`: instalación, arranque y errores del lanzador.
- `registros/servicio.log`: salida de Uvicorn/FastAPI.
- `respaldo/`: entornos anteriores si se usa la reparación o aparece una instalación incompleta.

No requiere administrador, no modifica el registro de Windows, no añade inicio automático y no altera el `PATH` persistente. El entorno que crea otros procesos se hereda solo del lanzador.

El lanzador **no ejecuta `make demo` ni `make evidencia`**, no estima un modelo nuevo y no modifica `artifacts/`, el champion `v0008`, la puerta ni la abstención. Tampoco activa `.venv`: ejecuta directamente `.venv\Scripts\python.exe -m uvicorn` con `SIC_ESCENARIO=synthetic/ihdp`.

Una instalación existente se reutiliza. **Reparar entorno** pide confirmación, conserva el entorno anterior en `respaldo/` y crea uno nuevo; no vacía el entorno en cada instalación.

## Red, privacidad y procedencia

Conexión necesaria la primera vez para obtener:

- el ZIP de `v1.0.1` desde `codeload.github.com`;
- `uv` 0.13.8 desde su release oficial en `github.com/astral-sh/uv`;
- Python 3.13 y los paquetes de `requirements.txt` desde las fuentes que resuelva `uv`.

El ZIP de `uv` se verifica contra el SHA-256 incorporado al lanzador **antes de ejecutarlo**. La descarga usa TLS de Windows. No se ejecuta código descargado como texto y no se usa `Invoke-Expression`. La procedencia y los límites de hashes del proyecto se describen en el README principal.

El ejecutable **no está firmado con un certificado de código**. GitHub Actions publica `PuenteCausal.exe.sha256` para comprobar integridad de la descarga; ese hash no sustituye una firma de autor.

Los registros no se suben a ningún servicio. Antes de compartirlos, revísalos: pueden contener tu nombre de usuario dentro de rutas y detalles técnicos del equipo.

## Desinstalar

1. Pulsa **Detener** y cierra la ventana.
2. En el Explorador, abre `%LOCALAPPDATA%`.
3. Borra la carpeta `PuenteCausal`.
4. Borra el archivo `PuenteCausal.exe` que descargaste.

Esto retira el entorno, los paquetes, los respaldos y la copia del proyecto instalada por el lanzador. No borra un clon o ZIP que hayas descargado aparte.

## Si algo falla

- Lee el mensaje de error y pulsa **Abrir registros**.
- Si Windows impide crear archivos, el registro identifica la ruta y el código del sistema. Revisa permisos, antivirus y **Control de acceso a carpetas**; no ejecutes como administrador para ocultar el problema.
- Si el entorno quedó incompleto, usa **Reparar entorno**. No necesitas borrarlo manualmente.
- Si el puerto 8000 está ocupado por otra aplicación, Uvicorn lo indicará en `servicio.log`. Cierra esa aplicación o usa su instancia si ya es este servicio. El lanzador no termina procesos que no haya iniciado.
- Si el champion o la puerta falla, el servicio conserva su comportamiento: responde con abstención en vez de inventar un efecto.

El lanzador evita instalar en `Documents`, pero no puede garantizar que una política corporativa, un antivirus o una carpeta de usuario dañada permitan escribir en `LocalAppData`. En ese caso, el error queda visible para soporte técnico.

## Compilar y probar (solo desarrolladores)

El estudiante no necesita CMake, C++, Rust, .NET SDK ni Visual Studio. El flujo `.github/workflows/instalador-windows.yml` compila con MSVC en `windows-2022`, ejecuta una autoevaluación sin GUI, conserva el ejecutable y adjunta el binario al release publicado después de la prueba integral de instalación y servicio.

Equipo de desarrollo Windows con Visual Studio 2022 y CMake:

```powershell
cmake -S instalador_windows -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release --parallel
ctest --test-dir build -C Release --output-on-failure
```

El ejecutable usa Win32, WinHTTP, BCrypt y PowerShell exclusivamente para `Expand-Archive`, oculto y sin descargar scripts. El runtime MSVC se enlaza estáticamente. La autoevaluación `--self-test` comprueba el citado de argumentos Windows, lectura del estado del servicio y SHA-256. Al publicar un release, el modo `--smoke-test` realiza además una instalación nativa completa en el runner, arranca Uvicorn y exige champion `v0008`, integridad válida, puerta `pasa` y una respuesta `/efecto` con efecto e IC antes de adjuntar el binario. Ninguna de estas pruebas equivale a validar la interacción gráfica en cada PC.
