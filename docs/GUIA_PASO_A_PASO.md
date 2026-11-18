# Reconstrucción paso a paso — de la versión base a la mejora «Puente»

Guía para el estudiante: reconstruir, por etapas verificables, las seis
mejoras que la rama `demo/mejora-paso-a-paso` incorpora a la versión base del
prototipo. No es una lista de comandos para copiar a ciegas: es un ejercicio
de ingeniería de datos con criterios de aceptación.

- *Base pública:* `main` (equivalente funcional a `v1.0.4` en este punto de partida).
- *Solución de referencia:* rama `demo/mejora-paso-a-paso`, un commit por paso.
- *Alcance:* no se añaden datos externos ni se toca la separación
  observables / evaluación reservada. Ninguna cifra de esta guía demuestra
  identificación causal.

## Cómo obtener la base

```bash
git clone https://github.com/jelincovil/prototipo_ml_causal.git
cd prototipo_ml_causal
git switch main            # la versión base que ves en GitHub
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
make verificar pruebas      # la base debe pasar antes de empezar
```

En el monorepo docente: `07_docencia/prototipo_ml_causal` (copia de lectura)
y `07_docencia/prototipo_paso_a_paso` (worktree con la rama de trabajo).

## Método de trabajo por paso

Para cada paso, en orden:

1. Lee el *problema* del paso (qué falla hoy).
2. Intenta resolverlo tú mismo, sin mirar la solución.
3. Verifica con los criterios de aceptación del paso (`make pruebas`, y la
   compuerta u otras herramientas indicadas).
4. Recién entonces compara con la solución: `git show <hash-del-paso>`.
5. Anota qué decides distinto y por qué.

## Los seis pasos

| Paso | Commit | Problema que resuelve |
|---|---|---|
| 1/6 | `0d872a0` | La cobertura Monte Carlo era evidencia, no compuerta: un estimador mal calibrado podía promoverse igual. |
| 2/6 | `404cab5` | Tras el trimming, la tarjeta decía "ATE" a secas: el estimando efectivo (poblacional vs solapamiento) no quedaba declarado. |
| 3/6 | `f9f84cc` | No había forma de medir el coste de evaluar con datos vistos (sin cross-fitting) dentro del propio benchmark. |
| 4/6 | `63bc8d2` | El invariante del cross-fitting (pliegues disjuntos que cubren todo) no estaba testeado. |
| 5/6 | `0e76662` | La puerta del servicio ignoraba el ESS: podía servir un IC sobre un puñado de unidades efectivas. |
| 6/6 | este commit | La evidencia y la documentación no mostraban el proceso; la guía del método no estaba enlazada. |

### 1/6 — Puerta por cobertura (`0d872a0`)

**Problema.** `cobertura.py` producía `artifacts/cobertura.json` y nadie lo
consumía: la promoción de versiones no exigía cobertura ni sesgo.

**Qué cambió.** `verificar_compuerta()` evalúa el estimador principal (AIPW):
cobertura IC95 dentro de `[0.90, 0.99]` y `|sesgo| ≤ 0.10` (5 % del ATE del
DGP). `--compuerta` sale con código 1 si falla; `make cobertura-compuerta`;
CI ejecuta la compuerta. Es una **convención declarada**, no una calibración
universal: léelo en la nota del JSON.

**Verifica.** `make cobertura-compuerta` → `COMPUERTA: PASA`. Provoca un
fallo cambiando `COBERTURA_MIN` y observa que la promoción se bloquearía.

### 2/6 — Estimando efectivo tras el trimming (`404cab5`)

**Problema.** Con ê recortado a `[0.05, 0.95]`, el estimador deja de
identificar el ATE poblacional, pero la tarjeta seguía diciendo "ATE".

**Qué cambió.** `aipw_crossfit` declara `estimando_efectivo` y `trimming`
(unidades recortadas). `estimar()` lo propaga. La tarjeta
(`version_esquema` 1.3) exige el campo; `validar_tarjeta` rechaza tarjetas
sin él o con él vacío.

**Verifica.** `make pruebas` → los tests 12c pasan. Borra el campo en una
tarjeta manual y comprueba el `ValueError`.

### 3/6 — El brazo sin cross-fitting (`f9f84cc`)

**Problema.** El benchmark no medía cuánto se degrada AIPW si ajustas y
predices en la misma muestra.

**Qué cambió.** Nueva función `aipw_sin_crossfit` (misma especificación,
evaluación in-sample) y nueva rama en la Monte Carlo. Los números de la
corrida `synthetic/ihdp` son: AIPW 0,97 · sin cross-fitting 0,96 ·
OLS 0,96 · ingenuo 0,00. **Con nuisance bien especificados el coste es
pequeño (~1 punto): léelo así, no como "el cross-fitting es opcional".** El
caso severo es el del boosting profundo del capítulo 10 del libro.

**Verifica.** `python cobertura.py --repeticiones 10` y lee
`aipw_sin_crossfit` en el JSON; corre `make pruebas`.

### 4/6 — Invariantes de cross-fitting (`63bc8d2`)

**Problema.** El supuesto operativo "ninguna unidad predice con un modelo
que la vio" no estaba verificado por tests.

**Qué cambió.** `folds_crossfit()` es la única fuente de particiones
(refactor, sin duplicación); el test 12d comprueba pliegues disjuntos,
cobertura exacta de `{0..n-1}` y reproducibilidad con semilla fija.

**Verifica.** `make pruebas` → tests 12d. Muta `folds_crossfit` (p. ej. sin
permutar) y observa el fallo.

### 5/6 — Abstención por ESS en la puerta (`0e76662`)

**Problema.** Aunque el monitor dijera `pasa`, el servicio podía servir un
ATE respaldado por un ESS/n minúsculo.

**Qué cambió.** `servicio_core._abstencion_por_puerta` se abstiene si el
`soporte.ess_sobre_n` de la tarjeta está bajo el **piso declarado**
`0.25` (convención inicial, sensibilidad ±20 % documentada, no ley
universal). El campeón actual (`ess_sobre_n ≈ 0.74`) no se ve afectado.

**Verifica.** `make pruebas` → tests 12e. En un bundle artificial con
`ess_sobre_n = 0.10`, la respuesta es `abstencion` con el motivo impreso.

### 6/6 — Evidencia y documentación (`este commit`)

**Qué cambió.** `docs/SESION_DML_40MIN.pdf` (guía del método para el
operador) y esta guía quedan enlazados desde el README; `evidencia/` se
regenera con las nuevas compuertas; hashes en `evidencia/SHA256SUMS`.

**Verifica.** `make evidencia` reproduce byte a byte salvo los campos que
agregan los pasos 1–6; `sha256sum -c evidencia/SHA256SUMS` todo OK.

## Cierre del ejercicio

```bash
git log --oneline main..demo/mejora-paso-a-paso   # los seis pasos
git diff v1.0.4..demo/mejora-paso-a-paso          # la solución completa
```

Criterios de aceptación finales: pruebas en verde, compuerta en verde,
la tarjeta del champion declara `estimando_efectivo`, el README enlaza la
guía del método y la evidencia es reproducible.

## Límites honestos

- Estas mejoras fortalecen **puerta, declaración y evidencia**; no tocan la
  identificación, que sigue apoyándose en los supuestos del diseño/DGP.
- Las compuertas y pisos son convenciones **declaradas**, no calibración
  universal ni garantía fuera de este DGP ni de datos reales.
- Nada de esto habilita decisiones clínicas, laborales o de política pública.
