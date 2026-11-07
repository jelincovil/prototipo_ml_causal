# Imagen del prototipo: el bundle viaja (registro + artefactos), los datos no.
FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir numpy scipy fastapi "uvicorn[standard]"
COPY servicio.py servicio_core.py registro.py rutas.py /app/
COPY artifacts /app/artifacts
RUN chmod -R a+rX /app
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/salud').status==200 else 1)"
CMD ["uvicorn", "servicio:app", "--host", "0.0.0.0", "--port", "8000"]
