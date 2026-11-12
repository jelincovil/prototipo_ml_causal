# Prototipo causal local — semana 4 (make <objetivo>)
.PHONY: verificar estimar registrar ventanas monitor servir serve humo pruebas cobertura dag evidencia cierre demo limpiar

PYTHON ?= python3
UVICORN ?= uvicorn

verificar:          ## esquema C-01 + hashes de splits + la pared
	$(PYTHON) datos.py

estimar:            ## ATE + IC + diagnósticos + sensibilidad + placebo + estimacion.json
	$(PYTHON) estimacion.py

registrar:          ## tarjeta + versión + champion + alias + demo de mutación
	$(PYTHON) registro.py

ventanas:           ## ventanas -> 5 acciones + monitor_estado.json
	$(PYTHON) monitor.py

monitor: ventanas   ## alias de la rúbrica

servir:             ## levanta el servicio (Ctrl-C para parar)
	$(UVICORN) servicio:app --port 8000

serve: servir       ## alias de la rúbrica

humo:               ## prueba de humo del servicio
	$(PYTHON) humo.py

pruebas:            ## asserts de sensibilidad, placebo, positividad, monitor y cobertura
	$(PYTHON) pruebas_estimacion.py

cobertura:          ## Monte Carlo del DGP ilustrativo propio; no evalúa IHDP/jobs
	$(PYTHON) cobertura.py

FIG = data_benchmark_causal/causal_benchmark_synthetic/datasets/figuras
dag:                ## genera el DAG de una página, el detalle y el grafo de módulos
	mkdir -p $(FIG)
	dot -Tsvg $(FIG)/dag_ihdp_plate.dot -o $(FIG)/dag_ihdp_plate.svg
	dot -Tsvg $(FIG)/dag_ihdp_detalle.dot -o $(FIG)/dag_ihdp_detalle.svg
	dot -Tsvg $(FIG)/dag_jobs.dot -o $(FIG)/dag_jobs.svg
	dot -Tsvg $(FIG)/modulos.dot -o $(FIG)/modulos.svg

evidencia:          ## comando, salida y hash por cifra del cierre
	mkdir -p evidencia
	SIC_ESCENARIO=synthetic/ihdp $(PYTHON) datos.py > evidencia/01_datos.txt 2>&1
	SIC_ESCENARIO=synthetic/ihdp $(PYTHON) estimacion.py > evidencia/02_estimacion.txt 2>&1
	cp artifacts/sensibilidad.json evidencia/03_sensibilidad.txt
	cp artifacts/placebo.json evidencia/04_placebo.txt
	SIC_ESCENARIO=synthetic/ihdp $(PYTHON) cobertura.py > evidencia/10_cobertura.txt 2>&1
	cp artifacts/cobertura.json evidencia/10_cobertura.json
	SIC_ESCENARIO=synthetic/ihdp $(PYTHON) registro.py > evidencia/06_registro.txt 2>&1
	SIC_ESCENARIO=synthetic/ihdp $(PYTHON) monitor.py > evidencia/05_puerta.txt 2>&1
	SIC_ESCENARIO=synthetic/ihdp $(PYTHON) humo.py > evidencia/07_servicio.txt 2>&1
	shasum -a 256 $(FIG)/*.svg > evidencia/08_dag.txt
	SIC_ESCENARIO=synthetic/ihdp $(PYTHON) pruebas_estimacion.py > evidencia/09_pruebas.txt 2>&1
	shasum -a 256 evidencia/*.txt evidencia/*.json evidencia/README.md > evidencia/SHA256SUMS

cierre:             ## compila el documento Typst
	typst compile data_benchmark_causal/causal_benchmark_synthetic/datasets/dataset_y_metodo.typ

demo: verificar estimar registrar ventanas humo  ## el flujo completo

limpiar:            ## borra artifacts (las versiones son regenerables)
	rm -rf artifacts
