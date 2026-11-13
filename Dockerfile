# Imagen del prototipo: el bundle viaja (registro + artefactos), los datos no.
FROM python:3.13-slim
WORKDIR /app
# El servicio consume JSON: no necesita DoWhy, pandas ni deserializar pickle/joblib.
RUN pip install --no-cache-dir numpy==2.4.2 scipy==1.17.0 fastapi==0.135.3 uvicorn==0.44.0
COPY servicio.py servicio_core.py registro.py rutas.py sensibilidad.py healthcheck.py /app/
COPY artifacts /app/artifacts
RUN chmod -R a+rX /app
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8000
ENV SIC_ESCENARIO=synthetic/ihdp SIC_VERSION_ESPERADA=v0009
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=6 \
  CMD ["python", "/app/healthcheck.py"]
CMD ["uvicorn", "servicio:app", "--host", "0.0.0.0", "--port", "8000"]
