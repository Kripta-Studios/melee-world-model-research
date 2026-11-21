# HECHO — estado del trabajo a 2026-11-21

Documento de traspaso. Dice qué existe, dónde está y cuánto se puede confiar en ello.
Lo que falta está en [`PENDIENTE.md`](PENDIENTE.md).

## Pregunta y respuesta actual

**Pregunta:** ¿aporta valor medible un modelo del mundo aprendido (JEPA / LeJEPA / LeWorldModel) a un agente de
Super Smash Bros. Melee, frente a imitación, RL sin dinámica explícita y búsqueda con el simulador exacto?

**Respuesta hoy:** no se sabe. Nadie ha medido fuerza de juego. La decisión es no construir todavía un planificador
(MPC) con dinámica aprendida, y probar primero un **predictor del presente bajo demora**: un modelo conjunto de
dinámica + rival sobre estado estructurado (W0-S + q), con un gemelo latente tipo LeWorldModel (W1-L) como
ablación. Solo W1-L es "JEPA" de verdad.

## Límites que hay que tener presentes

- **Nada se ha ejecutado en el juego.** No había ISO de Melee ni GPU. No hay ni una partida jugada.
- Todo lo de la fase de investigación sale de leer código, documentación y papers en revisiones fijadas.
- Las mediciones propias son de CPU en un servidor compartido y cargado (4 vCPU, 7,6 GiB): ruidosas.
- Las cifras de papers y de autores de repos están atribuidas, no reproducidas.

## 1. Fase de investigación (cerrada)

| Qué | Dónde | Estado |
|---|---|---|
| Paquete de encargo original | `handoff/melee_swarm/` | Íntegro (SHA-256 verificado) |
| Informes de los 8 roles (plataforma, políticas, JEPA, dinámica, planificación, datos, sistemas, crítica) | `evidence/A1` … `evidence/A8` | Completos |
| Verificación del "simulador sombra" | `evidence/A8/G01_shadow_sim_check.md` | Completa (solo lectura de fuentes) |
| Brainstorming con tres posturas y decisión | `decision/` | Completo |
| Los ocho entregables consolidados | `deliverables/` | Completos |
| Revisiones exactas de todas las fuentes | `deliverables/sources.lock.json`, `ops/clone_inventory.txt` | 66 fuentes |
| Afirmaciones con evidencia | `deliverables/EVIDENCE.jsonl` | 240, válidas contra el esquema |

**Orden de lectura recomendado:** `deliverables/FINAL_RECOMMENDATION.md` → `decision/DECISION.md` →
`deliverables/CRITICAL_REVIEW.md` (§7 corrige errores de la decisión) → `deliverables/DESIGN.md` →
`deliverables/EXPERIMENT_PLAN.md`.

**Hallazgos que condicionan todo lo demás:**

- El benchmark (melee-llm) solo puntúa partidas en Dolphin, nunca en el simulador, y no impone plazo por frame.
- Un agente recibe el `GameState` con el mando actual del rival, pero no el estado del simulador (`World`). No hay
  punto de integración para un planificador; habría que modificar `sim/runner.py`.
- Ningún bot moderno publicado predice estados futuros al jugar. No hay pesos JEPA reutilizables para estado
  estructurado; de le-wm solo sirve el código pequeño (`SIGReg`, `ARPredictor`), con licencia MIT.
- El simulador exacto (melee-brute) acota por arriba a cualquier dinámica aprendida en modo simulador, a igual
  número de candidatos. Lo que el simulador no puede dar es el modelo del rival.
- Para dinámica solo sirve el `.slp` crudo: HAL MDS carece de velocidades, hitstun y contadores.
- Con 40 partidas por brazo solo se detectan diferencias de ~31 puntos. Hacen falta ~400 por brazo para 10 puntos.

## 2. Etapa E0 (datos reales, sin ISO ni GPU) — parcialmente hecha

### 2.1 Tubería de datos — hecha y verificada

Código en `pilot/e0/`, resultados en `evidence/E0/`, informe en `evidence/E0/E0_DATA_REPORT.md`.

- Lee en streaming los tarballs de `erickfm/melee-ranked-replays` (revisión `ef54ddc2`), filtra Fox contra Fox y
  convierte cada partida al esquema acordado (`pilot/e0/schema_a6.py`).
- **288 partidas, ~2,8 M de frames**, todas del tarball `FOX_diamond-diamond_a1`.
- Puerta del 95 %: pasa al 100 % (velocidades, hitstun y contador de frames de la acción presentes).
- Test de alineación: el mando del frame f actúa sobre el estado del mismo frame (98,3 % de 33.186 saltos). El
  objetivo de imitación sin fuga es el mando de f+1.
- 45,9 bytes por frame en npz comprimido. Sin duplicados. Splits por partida en `evidence/E0/splits.jsonl`.
- Rollback: `peppi-py` devuelve todas las copias de un frame; la tubería se queda con la última (3,41 % de frames).
- 11 tests en `pilot/e0/tests/`, todos pasan. Se reproduce con `bash pilot/e0/run_all.sh`.

**Los datos NO están en el repo** (1,7 GB en el servidor). Hay que regenerarlos; ver `PENDIENTE.md`.

### 2.2 Líneas base triviales y prueba de humo — hecha a medias

Código en `pilot/e0/models/`, informe en `evidence/E0/floors/FLOORS_REPORT.md`.

- Líneas base completas (persistencia, velocidad constante, mayoritaria condicionada) por campo y horizonte.
- Prueba de humo con modelos de 0,7 M de parámetros: **solo terminaron 3 de 6 ejecuciones** (2 semillas de W0-S,
  1 de q). El servidor se quedó sin memoria. No hay desviación entre semillas.
- Lectura provisional (12 partidas de validación; no decide ninguna puerta):
  - con mandos futuros reales, W0-S acierta la acción a 4 frames en 0,639 frente a 0,289 de la mejor línea base;
  - con la misma información que las líneas base, mejora solo un 4,9 % relativo (la puerta pide 10 %) y a 8 frames
    es peor;
  - el modelo del rival supera a la mejor línea base un 6–10 % a 7 y 13 frames, no a 1 frame.

### 2.3 Latencia y envoltorio de plazo — hecha a medias

Código en `pilot/e0_timing/`, informe en `evidence/E0/timing/TIMING_REPORT.md`.

- Envoltorio de plazo por frame (`rt_strict.py`) implementado, con 11 tests que pasan.
- Banco de latencia del predictor del presente con pesos aleatorios: **1 repetición, 1 hilo, servidor cargado.**
- Resultado provisional: **ninguna de las 46 configuraciones baja de 10 ms p99 en esa CPU.** La mejor (GRU, demora
  de 6 frames) da 13,0 ms de mediana y 19,5 ms p99; con 12 frames, 21–26 ms de mediana.
- La caché KV del transformer da la misma salida numérica que sin caché (test) y divide el paso entre 5 y 9.

## 3. Trabajo en el PC con GPU (2026-11-21)

Máquina en `evidence/E1/hardware.json`: RTX 5070 Ti laptop de 12 GB, Ryzen 9 9955HX, 31 GiB y Windows 11. Datos en
`E0_DATA=D:/melee-data`.

| Qué | Dónde | Estado |
|---|---|---|
| Pilotos portables a Windows (`pilot/portable.py`, `pilot/timev.py`, `$PY`, `-X utf8`) | `pilot/` | Hecho; en Linux el comportamiento no cambia |
| Datos de E0 regenerados | `D:/melee-data` | **Idénticos byte a byte** al servidor (índice, splits y manifiesto); 21 tests OK |
| Semillas de humo que faltaban | `evidence/E0/floors/FLOORS_REPORT.md` §8 | **3 semillas por modelo**; sd entre semillas 0,002–0,007 |
| Mapa de predecibilidad (E0c) | `evidence/E0/predictability/PREDICTABILITY.md` | Hecho; ver abajo |
| Revisión de 4 papers de 2611 | `research/sota_2611/SYNTHESIS.md` | Hecho: 2 útiles (Fast-JEPA, SADL) y 2 marginales; ninguno cambia la decisión |
| Preregistro de E1 | `evidence/E1/PREREGISTRATION.md`, `preregistration.json`, `eval_schedule.csv`, `.sha256` | **Sellado**: el usuario aceptó los valores por defecto |
| Envoltorio de plazo a 60 Hz | `evidence/E0/timing/pc_probe/README.md` | Verificado en modo hilo: **excede el plazo 5–7 ms p99 con agentes lentos**. El modo proceso queda pendiente en Windows |
| Predictor directo (P1 de Fast-JEPA) en el banco | `pilot/e0_timing/`, `pc_probe/` | Su coste no depende de D; 2,3–7× más rápido que el rollout (solo coste) |
| Corpus para E1 | `evidence/E1/stream_manifest.jsonl` | Descarga en curso; ver PENDIENTE |
| Código de entrenamiento de E1 | `pilot/e1/` | En construcción |
| Panorama: repos de Mateo, leaderboard y competidores | `research/landscape_2611/` | En curso |

Hallazgos nuevos:

- **Dos regímenes (E0c, REP).**
  - En los frames comprometidos (hitstun, lag, animaciones), el estado predice la acción ~99 % a cualquier horizonte
    y ningún mando añade nada. Son el 15 % del tiempo a 7 frames y el 8 % a 13.
  - Los mandos propios casi duplican el acierto en eventos; los del rival añaden ≤ 0,004.
  - Del rival solo es predecible su ventana comprometida. En sus decisiones, lo honesto es medir calibración.
- **La CPU de este portátil rindió 4–10× por debajo de lo normal** durante la sesión (probable perfil de energía). Los
  milisegundos absolutos medidos aquí no valen; las razones entre variantes, sí.
- **En GPU con K=4,** el predictor rollout es más lento que en CPU: está limitado por el lanzamiento de kernels.
- **En Windows,** el temporizador de 15,6 ms rompía el plazo. `rt_strict` usa ahora `timeBeginPeriod(1)`.

## 4. Repositorios externos usados

Clonados en `sources/` (no versionado). Para recrearlos con las mismas revisiones, ver `ops/clone_inventory.txt`
(`owner/repo` + SHA de HEAD) y `deliverables/sources.lock.json`.
