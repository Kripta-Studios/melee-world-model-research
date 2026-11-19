# A7 · Sistemas, coste y viabilidad

Agente A7 · 2026-11-19 · Español. Etiquetas: **[MED]** REPRODUCIDO (medición propia, `local_experiment`, hardware
compartido y ruidoso), **[COD]** INSPECCIONADO_EN_CODIGO, **[DOC]** DOCUMENTADO_POR_AUTOR (atribuido, no reproducido),
**[INF]** INFERENCIA/estimación, **[PROP]** PROPUESTA, **[DESC]** DESCONOCIDO. IDs `A7-0xx` → `claims.jsonl`.
Presupuestos y fórmulas recalculables → `budget.json`. Crudos → `measurements/`. Scripts → `pilot/a7_bench/`.

## 0. Hallazgos (lo que cambia decisiones)

1. **El bench no impone plazo a un agente every-frame** [COD]: en `fast` y `realtime` Dolphin se lanza con
   `blocking_input=True` y espera el mando; solo `realtime` penaliza (estado `slow` si fps medio < 50). Un MPC de
   200 ms/frame juega igual en `fast`. Hay que imponer el plazo con un envoltorio tipo bot-writer y reportar
   `RT-strict`, `RT-slow` y `untimed` por separado (A7-001, A7-002).
2. **En esta CPU un MPC aprendido en tiempo real es muy pequeño** [MED]: con plazo de 16 ms caben, p99 medido,
   GRU-1M K=64×T=16 (15,3 ms) o MLP-1M K=16×T=8 (2,8 ms); a 5M solo K=16×T=4 (9,5–12,6 ms); **a 15M nada**; el
   predictor transformer de ventana (sin KV-cache) no cabe ni a 1M con K=16×T=8 (23 ms). Eso son ~1.000
   evaluaciones de predictor por decisión, frente a 45.000 por plan del CEM de LeWM y ~9.600 del MPPI de TD-MPC2
   (configs) (A7-010…A7-013).
3. **En CPU un modelo aprendido no es más barato que el simulador exacto** [MED vs DOC]: coste amortizado a batch
   grande, 3 hilos: MLP-1M 8,3 µs/transición, GRU-1M 9,6, GRU-5M 37, MLP-15M 143, TX-1M 130, TX-15M 931 µs;
   melee-brute documenta 12–15 µs/frame dentro de la búsqueda y 17 µs desde Python (otra CPU, cargada). La
   ventaja de un modelo aprendido en CPU no puede ser velocidad; solo disponibilidad (Dolphin, donde no hay
   snapshot del simulador, A1 §5.2) o abstracción (A7-014).
4. **SIGReg no es despreciable en CPU para modelos de estado pequeños** [MED]: con la config de le-wm (M=1024
   proyecciones, 17 nodos) cuesta 135 ms fwd+bwd (1 hilo, T=5, N=64, D=192) y es el 83 % del paso de
   entrenamiento de MLP-1M, el 72 % en GRU-1M y el 40 % en TX-1M (3 hilos, B=64). Escala lineal en T·N·M (M=256 →
   4× más barato). Además su tensor intermedio T·N·M·17 hace que la RAM de pico la marque SIGReg, no el modelo.
   Contradice "despreciable frente a cualquier encoder" de A3 §1.3, válido para encoders ViT de píxeles (A7-020).
5. **Entrenar aquí es inviable salvo humo** [MED+INF]: 3 hilos dan 800 muestras/s (MLP-1M) y 21–564 (5M–15M);
   1k partidas × 10 épocas = 37 h (MLP-1M) y 52–780 h (5M–15M). 15M no cabe bajo 1 GB de RAM ni con B=8. Además
   **no hay forma de leer datos reales sin instalar paquetes** (`peppi_py`, `melee`, `zstandard`, `streaming`
   ausentes). En una GPU de alquiler el mismo piloto son minutos-horas de cómputo, previsiblemente limitado por el
   dataloader (A7-030…A7-034).
6. **La evaluación, no el entrenamiento, domina la pared en tiempo real** [INF]: 40 partidas × 5 réplicas por brazo
   y reloj ≈ 2,1 M frames ≈ 9,8 h en Dolphin a 60 fps en serie (6 h en `fast` a 98 fps documentados). Aquí: 0
   partidas posibles (sin ISO) (A7-040).
7. **Varias ejecuciones mías superaron transitoriamente 1 GB de RSS** (pico 1,62 GB en el humo de SIGReg con N=512;
   1,1–1,49 GB en 12 pasos de entrenamiento 5M/15M a B=64 abortados por el guardián tras el primer paso). Ninguna
   duró > 10 s; se corrigió reduciendo configuraciones. Lo declaro como incumplimiento del límite. El import de
   torch 2.10+cu128 ya ocupa 504 MB de RSS, lo que deja < 500 MB útiles bajo el tope.

## 1. Entorno medido y revisiones

- Máquina [MED]: AMD EPYC-Genoa, 4 vCPU (1 hilo/núcleo), AVX-512 + bf16, L2 4×1 MiB, L3 32 MiB; 7,6 GiB RAM (≈5 GB
  disponibles, 1,8 GB de swap en uso); sin GPU (`nvidia-smi` no existe); Python 3.12.3; torch 2.10.0+cu128 sobre CPU,
  MKL 2024.2, oneDNN 3.7.1, OpenMP; capacidad `AVX512`. Disco: `/` 8,0 GB libres (95 %), `/srv/mail` 38 GB libres.
  `loadavg` durante las mediciones 2,6–7,7 (un proceso ajeno usaba ~190 % CPU al empezar). **Servidor compartido y
  ruidoso: las colas p95/p99 con 3 hilos están infladas por contención; con 1 hilo son más estables.**
- Límite de hilos: el encargo pedía 1 y 4 hilos, pero el tope duro es 3 hilos en total, así que medí **1 y 3**. 4
  hilos no está medido.
- No hay `nvidia-smi`, ISO, Dolphin, `peppi_py`, `melee`, `zstandard` ni `mosaicml-streaming`. `onnxruntime 1.26`,
  `numpy 2.4.6`, `pyarrow 23` y `pandas 3` sí están.
- melee-llm `7e179081c6cbab139d860c998b1452ad3dee047c` (el catálogo cita `2bf8b0eb…`; A1 comprobó que el runtime es
  idéntico), melee-brute `9662ec973b9e077ff7b0ff89d6db950f53c11653`, melee-sim-light
  `eea7b5fbcd0243baf4c1956d52f3e1d0f536edc4`, libmelee `bce21f09984b286e6d36bfd2939e4cd4691f94c2` (instalado en
  melee-llm: 0.47.6), le-wm `8edfeb336732b5f3ce7b8b210d0ba370a09e2cac`, lejepa
  `c293d291ca87cd4fddee9d3fffe4e914c7272052`, tdmpc2 `332f19e4aba4bffe2dc736f45ea7f7bdc585903a`.
- Dependencias (A13/A37) [COD]: el runtime de melee-llm (`pyproject.toml`) no trae torch; los bots viven en venvs
  propios. `train/pyproject.toml` exige `torch>=2.11` y `python <3.13`: **esta máquina (torch 2.10) no satisface el
  entorno de entrenamiento de melee-llm**. El setup fija Dolphin `v4.0.0-mainline-beta.19` (render) y
  `4.0.0-mainline-beta.14.1-ExiAI` (headless) (`scripts/setup.sh` L9-10, A47/A48/A49); hay que guardar la huella del
  binario al reproducir.

## 2. Presupuesto de latencia hasta mando aplicado

### 2.1 Qué reloj manda en cada modo (de A1, verificado en código)

| Modo / reloj | ¿Quién espera? | Qué cuesta la latencia del agente | Fuente |
|---|---|---|---|
| `fast` (bench, every-frame vs every-frame) | Dolphin sin tope y `blocking_input=True`: espera el mando de cada frame | **Nada en el resultado**: solo baja fps y alarga el wall-clock. Un planificador de 200 ms/frame juega igual de "bien" que uno de 2 ms | [COD] `LLM:melee_llm/runner.py` L208-216; A1-002, A1-014 |
| `realtime` (si algún lado es wall-clock) | Dolphin a 60 fps máx. **y** bloqueado | Si fps medio < 50 la partida se marca `slow` y no puntúa (`MIN_FPS = 50.0`, `bench/game.py` L14, L103, L111-112). Un pico aislado no penaliza; ralentiza el juego para el rival wall-clock | [COD]; A1-016 |
| `watch` | Dolphin no espera | Frames perdidos: el mando previo se mantiene | [COD] A1 §9 |
| `--mode sim` | Paso síncrono, `world.step()` tras ambos `step` | Nada (pausa implícita) | [COD] `LLM:sim/runner.py` L63-73 |
| bot-writer | `budget_ms=16.0` propio; tarde ⇒ mantiene mandos previos | Única ruta con plazo duro existente | [COD] `LLM:melee_llm/botwriter/agent.py` L3-6, L79, L186-190 |

**Consecuencia [INF]:** ningún modo del bench impone el plazo de 16,67 ms a un agente every-frame. El criterio
"tiempo real" del protocolo (p99 < plazo, ≤1 % plazos perdidos) **hay que imponerlo nosotros** con un envoltorio de
plazo tipo bot-writer (fallback declarado al vencer) o, como mínimo, medirlo y reportarlo; si no, "real-time lento"
(fast con cómputo ilimitado) se confunde con tiempo real. Se distinguen tres regímenes y se reportan por separado:
`RT-strict` (plazo impuesto con fallback, cuenta de plazos perdidos), `RT-slow` (sin plazo, se mide la latencia;
equivale a reloj en pausa) y `untimed` explícito (pausa/sim, latencia irrelevante por diseño).

### 2.2 Descomposición por frame (camino Dolphin, `runner.play` L279-300)

```
t0  console.step() vuelve con gs_t          (libmelee: flush de mandos de t-1, parseo Slippi de t)
t1  agent.begin(gs_t)  [p1, p2]              (BotAgent: envía eventos por pipe → proceso hijo infiere en paralelo)
t2  agent.step(gs_t)   [p1, p2]              (recibe respuesta; escribe melee.Controller)
      dentro de step:  feat(gs)→tensor | encode | propuestas (prior) | rollouts K×T | score | argmax | escribir pad
t3  pub.frame / observer
t4  siguiente console.step(): controller.flush() envía el pad → Dolphin emula t+1 con él → evento Slippi
```

| Tramo | Símbolo donde instrumentar | Coste conocido | Etiqueta |
|---|---|---|---|
| Emulación + parseo Slippi + runner | `console.step()` (`LM:melee/console.py` L898-908); `console.processingtime` = tiempo fuera de `step` (L435-436, L904, L979; clon 0.47.3, verificar en 0.47.6) | ≈3,3 ms/frame "Dolphin, the Slippi parse and the runner" (5950X con load 18-51) | [DOC] `LLM:docs/performance.md` §Per frame |
| Un Dolphin sin tope | — | ≈2 núcleos; 254 fps CPU-9 vs CPU-9 solo | [DOC] `performance.md` §How many games |
| IPC a bot en venv propio | `BotAgent.begin/step`, `round_trip_ms` vs `model_ms` (`LLM:melee_llm/bots/agent.py` L135-166, `latency()` L167-175; `bots/server.py` L122-130) | ~0,35 ms ida y vuelta (sandbox bot-writer en sim) | [DOC] `LLM:docs/simulator.md` L65 |
| Construcción de estado en sim | `StateBuilder.build` (`LLM:sim/state.py`) | 0,23 ms/frame; simulador 0,12 ms/frame | [DOC] `simulator.md` L65 |
| Simulador desde Python con observación | `EnvBatch.step` | 17 µs/frame (5950X cargado) | [DOC] `BR:BRUTE.md` L105 |
| Featurización `gs → tensor` | nuevo (`WorldModelAgent.step`) | no medido; Python puro sobre ~40 campos | [DESC] |
| Encode historia H | nuevo | medido §3 | [MED] |
| Propuestas (prior) | nuevo; si es Faynt-10M: 8,1/10,3/11,5 ms p50/p95/p99 en CPU 8 hilos | [DOC] `LLM:docs/bots.md` L53 |
| Rollouts K×T + score | nuevo | medido §3 | [MED] |
| Envío del mando | `Controller.flush()` (`LM:controller.py` L367-378), lo dispara `console.step()` | "a few microseconds" | [DOC] `performance.md` L94 |
| Aplicación efectiva | frame en que PreFrame(t+1) registra el pad | no instrumentado en el runner | [DESC] (A1 §9) |

**Presupuesto del agente [INF]:** en `realtime` el ciclo es serie (Dolphin espera el mando antes de emular t+1):
`T_frame = T_emul+parse+runner + max(T_agente_p1, T_agente_p2) + T_IPC ≤ 16,67 ms` para sostener 60 fps. Con la
cifra documentada (3,3 ms en otra máquina) quedan **≈13 ms** para el agente; con margen para jitter de una máquina
compartida, el presupuesto de diseño es **10 ms p99** en Dolphin y **16 ms p99** en sim/fast con plazo impuesto
(`agent_budget_ms` en `budget.json`). En una máquina de 4 vCPU, Dolphin (~2 núcleos) + dos agentes compiten por
CPU: los hilos de torch del agente deben fijarse (≤2) y medirse **con Dolphin corriendo**, no aislados.

### 2.3 Cómo medir p50/p95/p99 [PROP]

- Reloj: `time.perf_counter_ns()` (monotónico) en el proceso del agente; `capture_ts_ns` = retorno de
  `console.step()`/`world.step()`; `policy_start/end`, y dentro `encode_start/end`, `propose_start/end`,
  `rollout_start/end`, `score_end`; `send_ts_ns` = `controller.flush()` del siguiente `console.step()` (envolver
  `Controller.flush`); `applied_frame` = frame del PreFrame cuyo pad coincide (inferido; marcar `measured=false`).
  Campos exactamente los de `06_EXPERIMENT_PROTOCOL.md` L88 y `A6/timing_contract.json` `measurements_required`.
- GPU: sincronizar o usar `torch.cuda.Event(enable_timing=True)` + `synchronize()` antes de leer; sin eso las
  medidas no son precisas ("time measurements without synchronizations are not accurate", R05). CUDA graphs
  reducen sobre todo el coste de CPU de lanzamiento (R05), que es lo que domina en modelos pequeños [INF].
- Protocolo: descartar 300 frames de calentamiento (y el frame −123 de compilación/CUDA-graph, que en MIMIC cuesta
  ~120 ms, `bots.md` L53); ≥ 20k frames por condición para p99 estable (≥200 colas); registrar `loadavg` cada 1 s,
  hilos, frecuencia de decisiones y de inputs aplicados, plazos perdidos, fallback usado y observación envejecida.
  Reportar por tramo y extremo a extremo; p99 de suma ≠ suma de p99 (reportar ambos).
- Carga representativa: Dolphin + los dos agentes en la misma máquina, más una condición "máquina cargada" con
  `loadavg` registrado. En esta máquina compartida (load 3-5 sobre 4 vCPU durante mis mediciones) las cifras son
  pesimistas y con colas largas.

## 3. Mediciones propias (REPRODUCIDO, `local_experiment`)

**Qué se midió.** Modelos proxy de coste, no arquitecturas propuestas (`pilot/a7_bench/a7models.py`): estado S=192
floats/frame (2 jugadores; rango supuesto 100–300), acción conjunta A=32, latente D=192 (como LeWM). Encoder sobre
H frames de [estado, acción] → z; predictor de un paso (z, a) → z′. Familias: `mlp` (encoder sobre ventana aplanada
y predictor residual de 4 capas), `gru` (GRU de 2 capas y predictor de 2 `GRUCell`) y `tx` (transformer pre-norm;
predictor autorregresivo sobre una ventana de W=8 latentes, sin KV-cache, acción sumada al token en vez de
AdaLN-zero). Tamaños totales: 0,94–1,11M, 4,97–5,28M y 14,55–15,30M (tabla completa en `measurements/summary.md`).
fp32, eager, `torch.inference_mode`, `set_num_threads(n)`, `set_num_interop_threads(1)`, `nice 10`, `timeout 120`,
ejecuciones en serie. Tiempos con `perf_counter_ns`, 2 de calentamiento y repeticiones adaptativas (n en las tablas;
n=5 o n=1 = pocas muestras, solo orden de magnitud).

Comandos: `bash pilot/a7_bench/run_all.sh {infer|sigreg|train|train_small}`; cada invocación y su `rc` y `loadavg`
quedan en `measurements/commands.log` (las 58 terminaron `rc=0`). Crudos: `measurements/infer.jsonl`,
`sigreg.jsonl`, `train.jsonl` (cada fichero empieza por un registro `env` con `uptime`, CPU, versiones e hilos);
tablas: `summary.md`/`summary.json` (`summarize.py`); estimaciones: `estimates.json` (`estimate.py`).

### 3.1 Decisión MPC completa en CPU (encode H=32 + K candidatos × T pasos + score lineal + argmax)

p99 en ms (p50 entre paréntesis). La generación de propuestas no está incluida.

| modelo | hilos | K16·T4 | K16·T8 | K64·T8 | K64·T16 | K256·T8 |
|---|---|---|---|---|---|---|
| mlp 1M | 1 | 1,4 (1,2) | 2,8 (2,3) | 14,2 (6,3) | 18,4 (12,5) | 22,4 (22,0) |
| gru 1M | 1 | 25,8* (2,4) | 7,9 (3,5) | 8,5 (7,6) | **15,3** (14,0) | 25,1 (24,1) |
| tx 1M | 1 | 11,7 (10,8) | 23,3 (21,5) | 79 (75) | 158 (153) | 299 (293) |
| mlp 5M | 1 | 9,5 (8,5) | 17,6 (15,9) | 56 (47) | 100 (95) | 166 (165) |
| gru 5M | 1 | 12,6 (11,4) | 17,5 (15,9) | 42 (38) | 71 (69) | 129 (123) |
| tx 5M | 1 | 51 (48) | 104 (93) | 340 (334) | 679 (676) | — |
| mlp 15M | 1 | 31 (29) | 59 (57) | 164 (149) | 299 (298) | 529 (522) |
| gru 15M | 1 | 38 (34) | 107 (58) | 116 (111) | 221 (212) | 387 (346) |
| tx 15M | 1 | 130 (128) | 265 (250) | — | — | — |
| gru 1M | 3 | 4,4 (2,4) | 9,0 (3,0) | 9,0 (5,9) | 16,0 (10,4) | 24,5 (16,6) |
| mlp 1M | 3 | 27* (1,0) | 29* (1,7) | 33* (4,1) | 22 (10,0) | 85 (16) |

\* cola dominada por contención de la máquina (p50 bajo, p99 alto). Con 3 hilos la mediana mejora 1,2–2× a batch
grande, pero las colas empeoran: en un servidor compartido, **1–2 hilos fijos son la opción de tiempo real**.
Las celdas — se saltaron por presupuesto de tiempo (registro `skip`).

### 3.2 Paso de predictor y coste amortizado

Un paso a batch B escala casi lineal desde B≈16 (tabla `pstep` en `summary.md`). A batch 1 el coste lo marca la
lectura de pesos: MLP-15M 2,2 ms/paso, GRU-15M 1,3 ms, TX-15M 4,6 ms (1 hilo), coherente con mover ~60 MB de
pesos fp32 por paso fuera de L2 [INF sobre MED]. Coste amortizado al mayor batch medido (3 hilos, p50):

| modelo | µs/transición | batch |
|---|---|---|
| mlp 1M | 8,3 | 16384 |
| gru 1M | 9,6 | 16384 |
| gru 5M | 37 | 16384 |
| mlp 5M | 62 | 4096 |
| gru 15M | 89 | 4096 |
| tx 1M | 130 | 4096 |
| mlp 15M | 143 | 4096 |
| tx 5M | 543 | 2048 |
| tx 15M | 931 | 512 |

Comparación [DOC, otra CPU]: melee-brute 12–15 µs por frame dentro de la búsqueda, 4,4/4,5 µs
checkpoint/rollback y 17 µs por frame desde Python con observación (Ryzen 5950X cargado, `BR:BRUTE.md` L100-106);
melee-llm 17.500 frames/s en un hilo a load 45 (≈57 µs) y 21.600 frames/s con 64 carriles en un núcleo ocupado
(`LLM:docs/simulator.md` L20; `E24-sim-farm.md` L46); upstream 124.142 frames/s por núcleo a batch 256 en un
9950X3D (`MSL:README.md` L26-29). La verificación del rollout secuencial (tabla `rollout`) confirma que
T·paso(K) predice el rollout real dentro del ruido (p. ej. GRU-1M K64: 8 pasos 6,0 ms frente a 32 pasos 24,3 ms).

### 3.3 SIGReg (clase de le-wm, no reimplementada)

`SIGReg` se extrae con `ast` de `sources/lucas-maes_le-wm/module.py` L10-36 @`8edfeb33`, porque `einops` no está
instalado y el módulo lo importa. Comprobación cruzada: con las mismas direcciones, igual a `lejepa`
`EppsPulley(n_points=17)` (diferencia 0,0). fwd+bwd, ms p50:

| T·N (D=192) | M | 1 hilo | 3 hilos | RSS pico |
|---|---|---|---|---|
| 5·64 | 1024 | 135 | 72 | 734 MB |
| 5·128 | 1024 | 384 | 203 | 861 MB |
| 1·128 | 1024 | 57 | 30 | — |
| 1·512 | 1024 | 310 | 148 | — |
| 5·128 | 256 | 67 | 33 | — |
| 5·128 | 512 | 135 | 66 | — |
| 5·128 (D=64) | 1024 | 377 | 168 | — |

Es lineal en T·N·M y casi no depende de D: el coste son los cos/sin sobre T·N·M·17 elementos, no la proyección.
En GPU esas trascendentales son baratas [INF], así que esta conclusión es **específica de CPU**.

### 3.4 Entrenamiento en CPU con datos sintéticos (LeWM-like)

Una muestra = ventana de H+4 frames, rollout abierto de P=4 pasos, MSE + 0,09·SIGReg(M=1024, 17 nodos) sin
stop-grad (como `le-wm/train.py`), AdamW lr 5e-5. 3 hilos salvo que se indique. Muestras/s en p50 de paso:

| modelo | H | B | con SIGReg | sin SIGReg | RSS pico | pasos |
|---|---|---|---|---|---|---|
| mlp 1M | 8 | 64 | 800 | 4.721 | 811 MB | 15 |
| mlp 1M | 32 | 64 | 783 | — | 832 MB | 15 |
| gru 1M | 8 | 64 | 573 | 2.042 | 822 MB | 15 |
| gru 1M | 32 | 64 | 423 | — | 843 MB | 15 |
| tx 1M | 8 | 64 | 307 | 510 | 905 MB | 15 |
| tx 1M | 32 | 64 | 211 | — | 933 MB | 15 |
| mlp 5M | 8 | 64 | 564 (1 hilo: 275) | — | 891 MB | 15 |
| gru 5M | 8 | 64 | 256 (1 hilo: 181) | — | 927 MB | 15 |
| gru 5M | 8 | 16 | 167 | 233 | 767 MB | 12 |
| tx 5M | 8 | 16 | 110 | 135 | 808 MB | 12 |
| tx 5M | 32 | 16 | 90 | — | 819 MB | 12 |
| mlp 15M | 8 | 8 | 110 | 103 | 950 MB | 12 |
| gru 15M / tx 15M | 8 | 8 | 59 / 21 (1 paso) | 71 / 36 | 961–967 MB | 1–2 |

15M no cabe de forma fiable bajo 1 GB: pesos + Adam son 12 B/parámetro ≈ 180 MB, más 504 MB de torch, más
activaciones. Las filas de 1–2 pasos son solo orden de magnitud. Las muestras son sintéticas (`torch.randn`): **no
incluye dataloader ni decodificación**, que con datos reales puede dominar [INF].

## 4. Estimaciones (INFERENCIA; fórmulas y supuestos en `budget.json`)

### 4.1 Qué MPC aprendido cabe en tiempo real

**CPU de esta máquina (1 hilo, p99, sin propuestas).** `max_T = ⌊(presupuesto − 0,5 ms − enc_p99(H=32)) /
paso_p99(K)⌋`:

| modelo | 16 ms (sim/fast con plazo) | 10 ms (Dolphin conservador) |
|---|---|---|
| gru 1M | K16·T53, K64·T17, K256·T4 | K16·T31, K64·T9, K256·T2 |
| mlp 1M | K16·T36, K64·T11, K256·T2 | K16·T21, K64·T6 |
| tx 1M | K16·T3, K64·T1 | K16·T1 |
| mlp 5M / gru 5M | K16·T7–8, K64·T2 | K16·T3–4, K64·T1 |
| tx 5M | K16·T1 | — |
| 15M (cualquiera) | ≤ K16·T1 | nada |

Con un prior de propuestas aprendido hay que restar su coste: Faynt-10M mide 8,1/10,3/11,5 ms p50/p95/p99 en CPU
con 8 hilos (`LLM:docs/bots.md` L53, DOC). Con 4 vCPU compartidas, **Faynt como prior + rollouts no cabe en 16 ms**
[INF]. El prior debe ser una cabeza barata sobre el mismo encoder (B0), con coste ≈ el del encoder.

**GPU modesta (sin medir; supuestos en `budget.json`).** Para modelos ≤5M y K≤256 el paso queda limitado por
lanzamiento de kernels, no por FLOPs: en eager (≈10 µs/kernel) un paso MLP/GRU ≈ 0,1–0,14 ms y TX ≈ 0,5–0,8 ms;
con CUDA graphs (≈2 µs/kernel) ≈ 0,02–0,03 ms y 0,1–0,16 ms. Eso permite en 12 ms ≈ T=80–110 (eager) o 120–550 (CUDA graph) a K=256 en MLP/GRU 1–5M
(10⁴–10⁵ evaluaciones/decisión, del orden de TD-MPC2 y LeWM) y T≈5–16 en TX 5–15M. Precedentes [DOC]: Faynt usa
CUDA graph en la granja (`E28-faynt-farm.md` L23, L58) y HAL p95 6,49 ms en una 3060 con KV-cache + CUDA graphs
(A2). **La medición debe sincronizar** (`torch.cuda.synchronize()` o `torch.cuda.Event(enable_timing=True)`; R05:
"time measurements without synchronizations are not accurate").

### 4.2 Horas de entrenamiento de un modelo de dinámica piloto

Muestras = partidas × 10.620 frames (A6 §9) × épocas, con una ventana por frame (stride 1). 1k partidas = 10,6 M
muestras/época y 10k = 106 M.

| modelo (H=8) | CPU 3 hilos aquí, 1k × 1 época | 1k × 10 | 10k × 10 | 4090, cómputo puro (×1–×10), 10k × 10 |
|---|---|---|---|---|
| mlp 1M | 3,7 h | 37 h | 369 h | 0,2–2 h |
| gru 1M | 5,2 h | 52 h | 515 h | 0,4–4 h |
| tx 1M | 9,6 h | 96 h | 960 h | 1,3–13 h |
| mlp/gru 5M | 5–12 h | 52–115 h | 520–1.150 h | 1,1–23 h |
| tx 5M | 27 h | 269 h | 2.690 h | 6–63 h |
| 15M | 26–64 h | 260–640 h | 2.600–6.400 h | 3–180 h |

GPU (precio/hora **SUPUESTO A VERIFICAR**, orden de mercado 2026): L4 24 GB ≈ 0,4–0,8 USD/h (~3× más lenta que la
4090 en el modelo); RTX 4090 24 GB ≈ 0,3–0,7 USD/h; A100 80 GB ≈ 1,2–2,0 USD/h (~1,7× la 4090). Las horas de GPU
salen de FLOPs ≈ 6·(params·tokens) y de un rendimiento sostenido supuesto (12/35/60 TFLOP/s). El factor ×10 cubre
dataloader y lanzamientos: con modelos de 1–5M la GPU no se satura y el cuello será leer y decodificar datos. 10k
partidas en esquema A6 son ≈13 GB crudos: no caben enteros en 24 GB de VRAM junto al modelo si se decodifican a
fp16 por campo [INF]. Ancla de escala [DOC]: HAL 247M, 131.072 pasos × 512 × 256 frames en ~16 h de B200 (A2), que
equivale a ~20 % de MFU según mi cuenta [INF].

**Por réplica.** El protocolo pide ≥5 semillas por brazo aprendido (06 L67): multiplicar por 5 y por brazos (B0,
B2, W0, W1, más el ajuste). Un piloto de 1k partidas, 3 épocas, 1–5M y 5 semillas cuesta ≈ 5×(0,1–1 h) en una 4090,
pero ≈ 5×(11–35 h) en esta CPU [INF].

### 4.3 Disco (tope 20 GB en `/srv/mail`, compartido con el correo)

| Elemento | 1k partidas | 10k partidas | Fuente |
|---|---|---|---|
| .slp de origen (tar.gz) | ≈0,9 GB | ≈9 GB | A6 §9 |
| Esquema A6 completo, zstd | 0,13–0,43 GB | 1,3–4,3 GB | A6 §9 (compresión supuesta) |
| Caché decodificada cruda (122–203 B/frame) | 1,3–2,2 GB | 13–21,5 GB | A6 §9 |
| HAL MDS zstd (alternativa pobre en estado) | ≈0,14 GB | ≈1,4 GB | A6 §9 (medido por A6) |
| Checkpoints (12 B/param, 10 guardados) | 0,1–1,7 GB | igual | `budget.json` `checkpoint_mb` (11–175 MB c/u) |
| Trazas de latencia (≈100 B/frame × 2·10⁵ frames por condición) | <0,1 GB | <0,1 GB | INF |

**1k partidas cabe holgado (<5 GB)**. 10k cabe si se convierte tarball a tarball, borrando cada .slp, y se lee
zstd en streaming (≈2–6 GB más checkpoints). La caché cruda de 10k (13–21,5 GB) **no cabe** con el tope de 20 GB.
En `/` (8 GB libres, 95 % usado) no se debe guardar nada.

## 5. Camino local compacto y ampliación

**Local (esta máquina, sin GPU ni ISO), hacer:**
1. Envoltorio de plazo y trazas (§2.3) probado con un agente sintético dentro de un bucle falso que imite
   `runner.play` L279-300 (no necesita Dolphin) → valida campos y percentiles. [PROP]
2. Este banco de coste ampliado a la arquitectura real que propongan A4/A5 (mismo script, cambiando `a7models.py`),
   con 1–2 hilos fijos y una condición con carga de fondo controlada.
3. Smoke de entrenamiento a ≤1M y ≤100 partidas **solo si** el usuario autoriza instalar `peppi_py`/`zstandard` en
   un venv propio (hoy no se pueden leer datos reales). Sin eso, solo datos sintéticos.
4. Nada de PPO, partidas, simulador ni MPC contra rivales: todo exige la ISO (A2-031).

**Ampliación opcional:** una GPU de 24 GB (4090 o L4 alquilada, o la del usuario si la tiene; no se debe suponer)
con ISO y Dolphin local. 1k partidas + B0/W0/W1 a 1–5M + 5 semillas ≈ 10–50 h de GPU estimadas (≈5–35 USD a precio
supuesto); la evaluación en Dolphin `realtime` (≈10 h por brazo y reloj en serie) pesa más que el entrenamiento;
paralelizar con ~2 núcleos por Dolphin (`LLM:docs/performance.md`, 8 partidas sin tope saturan 16 núcleos).

## 6. Piloto de dimensionamiento (E2) con las 5 medidas [PROP]

| # | Medida | Cómo | Umbral para escalar |
|---|---|---|---|
| 1 | Frames de juego/s | runner real por brazo y reloj (Dolphin `fast`/`realtime`, `--mode sim`), ambos agentes, 3 réplicas de 1 partida, `loadavg` registrado; `fps` ya lo calcula `bench/game.py` L103 | `realtime` ≥ 59 fps medio y ≤1 % de plazos perdidos |
| 2 | Muestras/s | este banco con el **dataloader real** (decodificar + ventanas), por arquitectura/tamaño/H/B, con y sin SIGReg | dataloader ≥ 2× el consumo del modelo |
| 3 | RAM/VRAM pico | `ru_maxrss`; `torch.cuda.max_memory_allocated` por fase | < 80 % del equipo destino |
| 4 | Tamaños | corpus por formato, caché, checkpoint, trazas (`du -sb`), con hashes | total < 20 GB |
| 5 | Horas | pared por entrenamiento, por réplica (semilla) y por evaluación de brazo/reloj; total = preentreno + ajuste + búsqueda + refresco | dentro del techo congelado por brazo (`budget.json` `configurable_ceilings_per_arm`) |

Orden: (a) latencia y plazos con agente nulo en Dolphin → coste fijo del runner en el hardware destino; (b) B0 1M
→ fps con agente aprendido; (c) W0 1M MPC con K·T del §4.1 → p99 y plazos perdidos; (d) solo entonces subir
tamaño o K·T. Un brazo que no cumple el p99 en `RT-strict` se reporta como `RT-slow` y no entra en la comparación
de tiempo real.

## 7. Dudas y bloqueos

- **A4/A5:** fijar S, A, H, horizonte, K, iteraciones y si el predictor es recurrente o de ventana. Mis tablas
  muestran que un transformer de ventana sin caché es 10–50× más caro por paso que GRU/MLP de igual tamaño en CPU.
  Si se elige TX, hace falta KV-cache o una GPU.
- **A3/A4:** SIGReg con M=1024 domina el coste de entrenamiento en CPU para 1M. Si se baja M (256–512, que el paper
  dice insensible, A3 §1.2) hay que declararlo como cambio de configuración.
- **A1:** el frame de aplicación real en Dolphin y `T_emul` en el hardware destino no están medidos; la cifra de
  3,3 ms es del autor en un 5950X con carga. Comprobar `console.processingtime` en libmelee 0.47.6.
- **Coordinador/usuario:** hardware destino (GPU, VRAM, CPU, núcleos), permiso para instalar `peppi_py`/`zstandard`
  en un venv, y precio real de la GPU.

