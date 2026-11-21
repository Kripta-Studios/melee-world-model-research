# PENDIENTE — cómo continuar en otra máquina (PC con GPU)

Para un agente que acaba de hacer `git pull`. Lee antes [`HECHO.md`](HECHO.md).
El plan completo y sus puertas están en `deliverables/EXPERIMENT_PLAN.md` (§8) y `decision/DECISION.md` (§3).

## Estado a 2026-11-21 (PC con GPU, Windows)

| Paso | Estado |
|---|---|
| 0. Preparar la máquina | **Hecho.** `evidence/E1/hardware.json`. En Windows: venv de datos en `$E0_DATA/venv-e0` (con `Scripts/python.exe`) y torch de otro venv local vía `PY=...`; no se instala torch por proyecto. Usa Git Bash y `-X utf8` |
| 1. Regenerar E0 | **Hecho**, idéntico byte a byte al servidor |
| 2.1 Semillas de humo | **Hecho** (3 por modelo) |
| 2.2 Banco de latencia completo | **Pendiente.** Las medidas del PC solo sirven como razones: la CPU estaba estrangulada. Repetir con el portátil en modo rendimiento y enchufado. La ruta GPU existe (`--device cuda`), pero con K=4 la limita el lanzamiento de kernels; probar CUDA Graphs o `torch.compile`. Medir también el predictor directo (`--mode direct`) |
| 2.3 Envoltorio a 60 Hz | **Hecho en modo hilo: no cumple** (5–7 ms de exceso p99). El modo proceso falla en Windows: la factory de `fake_runner.py` es una lambda y `spawn` no la serializa, y 3 tests de modo proceso no pasan |
| 3. Ampliar corpus | **En curso**: ~2.000 de unos 3.000 dittos nuevos en `D:/melee-data/e1/slp` (se guardan los `.slp`, ~3,5 MB cada uno). Falta parsearlo a `D:/melee-data/e1/parsed` y rehacer splits y comprobaciones |
| 4. Preregistro | **Sellado** (`evidence/E1/preregistration.sha256`). No cambiar umbrales; cualquier enmienda, antes de entrenar y con aprobación del usuario |
| 5. E1 | Código en construcción en `pilot/e1/`. Sin ejecuciones de E1 todavía |
| Nuevo: E0c | Mapa de predecibilidad hecho. Propuesta abierta: enmendar G1-q (ii) para leerlo sobre frames comprometidos; decide el usuario |

## Reglas del proyecto

- **Commits:** autor único Kripta-Studios. Sin `Co-Authored-By` ni líneas de atribución a IA.
- **Evidencia:** toda cifra reportada sale de una ejecución registrada (comando, configuración, log). Las cifras de
  autores se atribuyen. Etiquetas: SOPORTADO / INFERIDO / PENDIENTE / PROPUESTA. Reglas completas en
  `swarm/AGENT_BRIEF.md` (ignora ahí los límites de recursos del servidor: no aplican al PC).
- **Datos, pesos e ISO nunca van al repo.** Solo código (`pilot/`) y resultados pequeños (`evidence/`).
- **Split de test reservado:** no se lee hasta E1. Hay un `assert` en `pilot/e0/models/common.py`; no lo quites.
- **No cambies umbrales después de ver resultados.** Los umbrales se fijan en el preregistro (paso 4).

## Paso 0 — Preparar la máquina

1. Registra el hardware real en `evidence/E1/hardware.json`: GPU y VRAM, RAM, CPU, disco libre, SO, versión de
   controladores, Python y torch (con CUDA). No lo des por supuesto.
2. Recrea los clones de fuentes (solo si vas a leer su código; hacen falta para E1 `le-wm`, `slippi-ai`, `MIMIC`):

   ```bash
   mkdir -p sources && while read -r _ repo sha _; do
     d=sources/$(echo "$repo" | tr / __)
     git clone -q "https://github.com/$repo.git" "$d" && git -C "$d" checkout -q "$sha"
   done < ops/clone_inventory.txt
   ```
3. Elige una carpeta de datos fuera del repo y expórtala: `export E0_DATA=/ruta/a/melee-data`.
   Las rutas del servidor (`/srv/mail/melee-research-data`) son solo el valor por defecto de los scripts.

## Paso 1 — Regenerar los datos de E0 y comprobar que todo reproduce

```bash
bash pilot/e0/run_all.sh        # venv, descarga en streaming, parser, splits, comprobaciones y 11 tests
```

Debe dar 288 partidas de Fox contra Fox y coincidir con `evidence/E0/dataset_card.json`. Si los conteos difieren,
párate y averigua por qué antes de seguir (el `stream_manifest.jsonl` trae el sha1 de cada archivo).

## Paso 2 — Terminar lo que quedó a medias en E0

Se cortó por falta de memoria en el servidor. En el PC son minutos.

1. **Semillas de humo que faltan** (W0-S semilla 2; q semillas 1 y 2):

   ```bash
   "$E0_DATA/venv-e0/bin/python" -I pilot/e0/models/export_cache.py   # caché memmap (~320 MB) en $E0_DATA/cache
   bash pilot/e0/models/run_smoke_rest.sh                             # usa el python3 del sistema, con torch
   python3 pilot/e0/models/summarize.py > evidence/E0/floors/logs/summarize.out
   ```
   Detalle de cada script en `pilot/e0/README.md`.
   Entregable: `evidence/E0/floors/model_diagnostics.csv` con 3 semillas por modelo y la desviación entre semillas.
   Los scripts fijan `cpu`; para esto no hace falta GPU. Si los pasas a GPU, declara el cambio.
2. **Banco de latencia completo** en la CPU y en la GPU del PC, con ≥ 3 repeticiones y 1 y 2 hilos:

   ```bash
   export E0_RAW="$E0_DATA/e0_timing_raw"       # trazas crudas, fuera del repo
   bash pilot/e0_timing/run_e0_timing.sh present 3
   bash pilot/e0_timing/run_e0_timing.sh jit 3
   bash pilot/e0_timing/run_e0_timing.sh e2e 3
   bash pilot/e0_timing/run_e0_timing.sh wrapper 3
   python3 -I pilot/e0_timing/summarize_timing.py "$E0_RAW"
   ```
   Entregables: `evidence/E0/timing/latency_summary.{json,md}` y `timing.jsonl` (este último no existe aún).
   Pregunta a responder: ¿cabe el predictor del presente en 10 ms p99 con demora de 6, 12 y 18 frames? En el
   servidor no cabía (13–53 ms de mediana). El banco no tiene ruta GPU: hay que añadirla (incluye el coste de
   transferencia CPU↔GPU en la medida).
3. **Verificar el envoltorio de plazo** a 60 Hz con la máquina descargada: "nunca bloquea el bucle más allá del
   plazo" está **sin verificar**.

## Paso 3 — Ampliar el corpus (necesario para E1)

288 partidas no bastan: E1 pide ~2.000 de entrenamiento, 300 de validación y ≥ 1.000 de test.

- Hay ~10 % de dittos por tarball; ~3.300 dittos suponen leer ~28 GB en streaming.
- Convierte cada partida al vuelo y **no guardes el `.slp`** (o sube `--max-saved-bytes`); ajusta
  `--max-accepted` y añade más `--tarball` en `pilot/e0/stream_filter.py`.
- Usa varios buckets de habilidad, no solo `diamond-diamond`, y regístralo en `dataset_card.json`.
- Los replays son Slippi 3.14/3.15: **no traen C-stick crudo** (existe desde 3.17). Anótalo como límite.
- Rehaz splits y comprobaciones (`splits.py`, `adapter_checks.py`). Corrige la incoherencia de proporciones
  señalada en `deliverables/CRITICAL_REVIEW.md` §7 (D-3).

## Paso 4 — Sellar el preregistro (antes de entrenar nada de E1)

Con la desviación entre semillas del paso 2, fija los umbrales de las cuatro puertas (regla: un efecto cuenta si
supera 2× esa desviación y su IC95 por partida excluye 0) y la decisión D-7 de `CRITICAL_REVIEW.md` §7.

```bash
sha256sum deliverables/EXPERIMENT_PLAN.md evidence/E1/preregistration.json evidence/E1/eval_schedule.csv \
  > evidence/E1/preregistration.sha256
```
Haz commit del preregistro **antes** de lanzar E1.

## Paso 5 — E1: diagnóstico offline en GPU (sin ISO)

Entrena W0-S, W1-L (latente tipo LeWorldModel con SIGReg), q y V̂, más BC con los brazos E0 / E0b / E1 / E1-S al
10, 30 y 100 % de datos. Diseño en `deliverables/DESIGN.md` §2–3; contrato en `evidence/A4/model_contract.json`.

Puertas (definición exacta en `decision/DECISION.md` §3):

| Puerta | Pasa si | Si falla |
|---|---|---|
| G1-dyn | W0-S mejora ≥ 10 % relativo a la mejor línea base trivial en eventos a 4 y 8 frames | Se paran W0-S y W1-L |
| G1-q | q mejora al mando marginal y a la mejor línea base en cambios de acción del rival, demoras 6 y 12 | No se ejecuta E3 |
| G1-jepa | W1-L supera a W0-S, y E1 a E1-S, en ≥ 2 de 3 tareas | Se cierra la etiqueta JEPA; sigue solo W0-S |
| G1-rep | El preentrenamiento predictivo supera al control de igual cómputo | No aporta a la representación offline |

Además **E1b**: mide transiciones por segundo de política + dinámica juntas en GPU (decide si entrenar en
imaginación sigue vivo; referencia documentada por el autor: 6.337 frames/s en su granja, otra máquina).

Reporta por separado los regímenes de información `I_full` (con mando actual del rival) e `I_human` (sin él).
Pasar G1 es condición necesaria, no prueba de ventaja al jugar.

## Paso 6 — Con ISO (decisión del usuario)

Requiere una ISO NTSC 1.02 propia del usuario; nunca se sube a terceros ni al repo.

- **E2:** `python -m melee_brute bench` y el banco de latencia en la misma máquina; panel de regret con ≥ 2.000
  estados; `validate_replay.py` frente a `parity.py` sobre ≥ 50 partidas grabadas del benchmark.
- **E3 (el MVP en juego):** predictor del presente frente a (a) observación envejecida, (c) la misma política
  entrenada con demora, (d) demora 0 como techo. ≥ 400 partidas por brazo; el brazo (c) con 5 semillas × 200.
- **E4:** búsqueda con el simulador exacto frente a las mismas propuestas sin rollouts. Exige modificar
  `sim/runner.py` de melee-llm para pasar el `World` y fijar la semilla.
- **E5 / E6:** solo si sus disparadores se cumplen.

## Decisiones que siguen siendo del usuario

| Decisión | Valor por defecto asumido |
|---|---|
| Aportar la ISO y dónde reside | No se pide hasta pasar las puertas de E1 |
| ¿Importa el régimen con demora de 6–18 frames? | Sí, como eje secundario |
| ¿Responder la pregunta o publicar un entrante en el benchmark? | Responder la pregunta |
| Cambios en melee-llm y melee-brute | melee-llm al llegar a E4; melee-brute solo si E2 lo justifica |
| 400 o 525 partidas por brazo para poder cerrar líneas con "sin efecto" | 400 |

## Cosas sabidas que conviene no redescubrir

- `train/pyproject.toml` de melee-llm exige torch ≥ 2.11, y su PPO tiene `cuda` fijado en el código.
- melee-llm fija melee-brute en `090e54b0`, pero el HEAD es `9662ec97` y el layout de observación cambió entre
  ambos. Fija una sola revisión para todo lo que midas.
- melee-llm, melee-brute, melee-sim-light y HAL no tienen fichero de licencia. `lejepa`, `ijepa` y `jepa-wms` son
  CC BY-NC: usa la copia MIT de SIGReg de le-wm.
- SIGReg con la configuración de le-wm (1024 proyecciones) domina el paso de entrenamiento en modelos pequeños en
  CPU; en GPU hay que volver a medirlo.
- le-wm divide train/val por ventanas aleatorias, no por episodio: no reutilices su split.
