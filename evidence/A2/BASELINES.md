# A2 · Políticas existentes, RL y elección de baselines

Agente A2 · 2026-11-19 · Solo lectura de código y fichas: no se descargaron pesos ni se ejecutó ninguna partida.
Etiquetas: **[COD]** INSPECCIONADO_EN_CODIGO, **[AUT]** DOCUMENTADO_POR_AUTOR, **[INF]** INFERENCIA,
**[PROP]** PROPUESTA, **[DESC]** DESCONOCIDO. Los IDs `A2-0xx` remiten a `claims.jsonl`. La tabla de checkpoints
con todos los campos está en `checkpoints.json`.

## Revisiones leídas

| Fuente | Revisión | Nota |
|---|---|---|
| ericyuegu/hal | `37045d974116405dd690efea6109a1d83a2da868` | Sin fichero LICENSE |
| erickfm/MIMIC | `3691f534194f9c2ec52f131c8ab96e3d8674c3fa` (HEAD) | melee-llm fija `bdfb629…` en `docs/bots.md:45`. No se ha comparado con HEAD |
| vladfi1/slippi-ai | `5ada33e90c6c87fe83a1fb2d1a8105a96fd7b05b` | MIT |
| vladfi1/phillip | `114aea4c446b31359c5637b271db52b200440caa` | El LICENSE es GPLv3, pero `setup.py:39` declara MIT |
| frisson-labs/Reyn | `93fa52742e43a3115a990211b3aebb31671d8fdc` | MIT, solo inferencia |
| Na00s/Faynt-Tournament | `d20961761814caf01f5db19c945d00ab757730ea` | MIT, más un parche de Dolphin GPL-2.0+ |
| Na00s/Faynt-Benchmarks | `39bc007537501c16d6e2dac6f2bcaafe3b84a8c9` | MIT. Incluye el PPO pero no el entrenamiento BC |
| mateo19182/melee-llm | **`7e179081c6cbab139d860c998b1452ad3dee047c`** (clon local) | **Discrepancia:** el catálogo fija `2bf8b0e…`, que no está en el clon shallow. Todas las rutas melee-llm de este informe se refieren a `7e17908` |
| HF: hal-base-250m-rc / MIMIC / Faynt-10M-Arena / Reyn-26C / phillip-models | `e7fb837…` / `f49879b…` / `96929127…` / `6a46ac7…` / `a5045c5…` | Fichas leídas por WebFetch. El `index-v1.json` de phillip-models se leyó en esa revisión |
| arXiv 1810.07286v1 | PDF descargado por WebFetch, sha256 `d93cb1de…19db` | Se extrajo el texto con pdftotext |

## 1. Hallazgos que corrigen o precisan el paquete

1. **El peso HAL publicado no es BC puro.** La receta 059 combina regresión ponderada por ventaja (AWR, β=150,
   peso máximo 10, solo en los offsets 1–6) con condicionamiento FiLM sobre el retorno descontado a 60 frames y una
   cabeza de valor V(s). Es **RL offline sobre datos humanos**, sin RL online
   (`experiments/059_muon_action_sequence.py` L1-22, `advantage_weights` L1216, `future_return_labels` L222-249). [COD][AUT] A2-001.
   Por tanto HAL no sirve como "baseline de imitación pura". Como mucho es "imitación condicionada por retorno".
2. **MIMIC no es solo clonación.** El checkpoint `fox/` (= `fox-20260420-baseline`) es BC puro [AUT] A2-007. El
   repositorio, en cambio, contiene PPO online en una build nativa de Melee (`rlvr/sim/ppo.py`, `tools/sim_rl.py`).
   Ese PPO no usa crítico: la línea base es la media del lote, con KL 0.01 hacia el BC congelado [COD] A2-009. Además,
   **qué es `fox-master` en HF es contradictorio**: `CLAUDE.md` L587 dice que desde 2026-10-29 es BC más 100
   actualizaciones de RL, y `README.md` L27/L40 lo describe como BC puro [COD] A2-010. No se debe usar `fox-master` como
   "BC puro" sin descargar sus metadatos y comprobarlo.
3. **Faynt-10M-Arena tiene dos etapas de RL**, no una (`step 1318`, y después `step 632` con correa KL 0.003). El código BC
   que produjo Base y Expert **se eliminó de la publicación** (`evaluation/SOURCE_MANIFEST.json` lo enumera, pero queda fuera
   de `runtime_files`) [COD] A2-021, A2-022.
4. **Componentes de dinámica (predicción de estados futuros).** Ningún peso moderno publicado los usa en
   inferencia. Existen tres, y ninguno está en un checkpoint actual [COD][AUT] A2-004, A2-018, A2-034:
   - `vladfi1/phillip` `phillip/model.py` clase `Model` (L7-155).
     - Qué predice: el **embedding del siguiente estado de ambos jugadores**, a partir de la salida de la GRU y de la
       **acción propia en cola**. El modelo residual con compuerta es `forget*(last+delta)+(1-forget)*new` (L53-60).
     - Pérdida: L2 en las componentes continuas y entropía cruzada en las one-hot.
     - Se entrena conjuntamente con el actor-crítico.
     - **Se usa en inferencia**: `actor.py` L30-36 lo desenrolla sobre los primeros `predict_steps` de la cola. El
       agente `agents/delay18/FalcoBF/params` usa `predict_steps 6`, `delay 6` y `act_every 3`, es decir 18 frames
       predichos por completo.
     - Limitaciones: **ignora al rival** (paper §5.2), y los pesos no están en el repositorio (Drive).
   - HAL `archive/experiments/029_game_state_flow.py` `GameStateExpert` (L939). Es un experto *flow matching*,
     condicionado a acciones, que predice el estado estructurado futuro en offsets dispersos. Es solo auxiliar en
     entrenamiento (peso 0.25). El blog lo cifra en −0.05 NSM, "within noise".
   - HAL `experiments/060_compute_optimal_action_sequence.py` `StateHead` (L1185) y `state_objective` (L1662). Predice
     deltas de x, y, porcentaje y escudo (NLL gaussiana), *facing* y *airborne* (BCE) y estado de acción (CE, 512 clases)
     del ego y del rival, en los offsets 1–30, con 21 frames de retraso. Es auxiliar, no tiene checkpoint publicado y su
     README dice que la cualificación no está establecida.
   - slippi-ai: no tiene predictor de estado. Sus `jax/q/` y `jax/nash/` predicen Q y valores, no estados. Su `sim_env/`
     envuelve un **simulador programado** (melee-sim-light), no uno aprendido [COD] A2-012.
5. **Asimetría de retraso en casi todas las cifras cruzadas publicadas.** Afecta a Faynt (0 frames contra 18–24), a
   HAL (2 frames de transporte contra 21) y a la mayoría de los resultados de MIMIC contra Phillip (MIMIC a 0, Phillip a 18).
   Los propios autores avisan de que no lo aíslan [AUT] A2-005, A2-025. Ninguna de esas cifras sirve como estimación de
   fuerza a igual retraso.
6. **El RL online no es posible en esta máquina.** melee-sim-light necesita datos extraídos de una ISO NTSC 1.02
   (`README.md` L47-61). La build nativa de MIMIC también se compila contra una ISO, y Dolphin la necesita igualmente.
   Aquí no hay ISO ni GPU [COD] A2-031.
7. **Las observaciones no son comparables entre políticas.** slippi-ai **excluye** el mando del rival
   (`embed.py` L463, "don't use opponent's controller"). El bot propio de melee-llm lo **incluye** (con retraso de
   `delay` frames, `train/meleebot/features.py` `assemble`). HAL no tiene velocidades. MIMIC no tiene proyectiles. Faynt
   y slippi-ai tienen 15 *items* [COD] A2-014, A2-032. Esto afecta directamente a la regla del protocolo de no comparar
   accesos a información distintos.
8. **Las unidades de retraso difieren entre proyectos.** En phillip, `delay` se cuenta en pasos de agente
   (× `act_every`). En slippi-ai, Faynt y MIMIC se cuenta en frames. Firoiu 2018 usa la notación (d,p,f) con un tiempo
   de reacción de d·f frames [COD][AUT] A2-040.

## 2. Ficha por política

En cada política se separan tres planos: el **método del proyecto**, el **método del peso concreto** y el **resultado publicado**.

### HAL (ericyuegu) · `hal-base-250m-rc` / `hal-250m.hal`
- **Proyecto:**
  - Familia de experimentos de BC, AWR, IQL, *flow matching* y cabezas de estado. Están en el archivo (`archive/README.md`:
    "not a supported runtime").
  - No hay RL online en todo el repositorio [COD].
- **Peso:**
  - Receta 059, 246,862,205 parámetros (L396-431). El tronco tiene 12 capas, d=1024 y 16 cabezas, con 256 frames de
    contexto. El decodificador temporal tiene 6 capas, d=1024. Hay además cabeza de valor y condicionador de retorno.
  - Observación estructurada:
    - Flotantes: pos x/y, %, escudo, facing, hitlag.
    - Categóricas: acción (vocabulario de 1024), stock, saltos, hurtbox, airborne.
    - Cuatro ranuras de jugador: ego, nana ego, nana rival, rival.
    - Cuatro *items*.
    - Identidad del ego (código o rango) y mando propio previo.
    - Sin velocidades (`hal/representation/features.py` L19-76).
  - Acción:
    - Botones: 256 combinaciones. Stick: 65 clusters. C-stick: 9. Gatillos: 25.
    - Orden autorregresivo c→main→triggers→buttons.
    - **Chunking** en los offsets `(1..12,16,20,24,28)` (059 L369).
    - Despliegue: predicción 4, prefijo 2, *replan* cada 2 frames. Sin frame skip.
  - Datos: ~1.3 M partidas, 44 fuentes (6 volcados *ranked* anonimizados y 38 pros), formato MDS. Entrenado con 131,072
    actualizaciones a batch 512 en una B200 durante unas 16 h [AUT].
  - **El repositorio no nombra explícitamente qué run es el fichero de HF.** El candidato es W&B `vywk3cih` [DESC].
- **Retraso:**
  - No se entrena con retraso. En inferencia, los primeros d pasos del chunk se fuerzan a las acciones ya enviadas
    (*real-time chunking*).
  - En la escalera usa 3 frames. La ficha de HF dice que en `play` local Dolphin espera a HAL, así que el retraso añadido es 0.
- **Resultados [AUT]:**
  - Frente a slippi-ai `all_d21_imitation_v3`: 91–5. Frente a `gm-v1`: 24–72. Son 96 partidas, solo dittos de Fox
    en FD, y **HAL juega a 2 frames contra 21** (`experiments/slippi-ai-h2h/README.md` L34-36, L220-221).
  - Unos 2200 de Elo en escalera (blog). El propio repositorio dice que "not a controlled strength evaluation".
- **Licencia:** el código no tiene licencia, así que todos los derechos están reservados. Los pesos son MIT según la ficha.
  melee-llm lo usa en local sin redistribuir (`docs/bots.md` L46).
- **Coste:**
  - Necesita CUDA (ficha). Con KV-cache y CUDA graphs: p95 de 6.49 ms en una RTX 3060 (`docs/kv-cache.md`).
  - melee-llm mide p50 4.35 ms en una 3090 y 992 MiB de VRAM [AUT de melee-llm].
  - No es viable en esta máquina (sin GPU, 7.6 GiB de RAM).

### MIMIC (erickfm) · `fox-20260420-baseline` (carpeta HF `fox/`)
- **Proyecto:** BC por personaje (`train.py`, CE sumada sobre 4 cabezas, L201-244), seguido de PPO en la build nativa
  (`rlvr/sim/ppo.py` L239-253). El PPO no tiene crítico y su rival es el BC congelado. La build es GPL-3 y se compila
  contra la ISO del usuario [COD].
- **Peso:**
  - BC puro. 20 M parámetros: d=512, 6 capas, 8 cabezas, atención relativa de Shaw. Contexto de 180 frames.
  - Entrada de 184 dimensiones:
    - 18 valores por jugador, con 5 velocidades, hitstun, escudo y flags.
    - Embeddings de escenario, personaje y acción.
    - One-hot de 56 dimensiones con el mando propio previo.
    - Sin proyectiles ni Nana.
  - Cabezas 3/9/37/7 (shoulder→c→main→buttons). Una acción por frame.
  - Datos: 31,030 partidas *master* de Fox, 32,768 pasos, pérdida de validación 0.7144 (ficha de HF).
- **Retraso:** 0. El objetivo es `target[i]=buttons[i+1]`. El repositorio no añade retraso artificial.
- **Resultados [AUT]:**
  - 30–0 contra CPU-9 en FD (notas del 2026-05-14).
  - Las cifras de RL se refieren a **otros** pesos: RL vs `fox-master` 279–105; RL vs Phillip `master` 11–9 y vs `gm` 2–18.
- **Licencia:** MIT.
- **Coste:**
  - Unos 0.5 ms por frame con bf16 y CUDA graphs según el autor.
  - melee-llm mide p50 3.4 ms en una 3090.
  - En CPU no está documentado.

### Phillip II (slippi-ai) · `phillip-models` (ONNX)
- **Proyecto:**
  - Primero BC sobre réplicas *ranked*, con retraso D integrado en los objetivos de entrenamiento: en el paso t ve el
    estado t y la última acción comprometida, y predice t+D+1 (`data.py` L267-326).
  - Después PPO en Dolphin o en melee-sim-light. La función de pérdida es
    `−pg·ppo + β·actorKL + kl_teacher·KL + rev_kl·KL − ent·H` (`jax/rl/learner.py` L680-687), con `kl_teacher_weight`
    por defecto 0.1 (L44). El maestro debe tener el mismo retraso (L407-409).
  - Las ventajas se desplazan por el retraso, y el valor ve el emparejamiento sin retraso.
  - Hay autojuego (SELF, OTHER, `train_many`). No hay liga con PFSP.
  - Framework JAX/Flax.
- **Peso:** el índice `index-v1.json` contiene unas 188 entradas [AUT].
  - **Imitación:** 11 entradas `*_d18_imitation_v2/v3`, todas a 18 frames, de unos 21.2 MB.
  - **RL:** el resto, a 18, 21 o 24 frames.
    - Multipersonaje `gm`, `master`, `diamond`, `bronze`…: 21 frames, 195,786,742 bytes.
    - Por personaje `*_v6.x`: unos 89.6 MB.
    - `*_v4`: unos 21.4 MB.
  - Tamaño estimado a partir de los bytes en fp16 [INF] A2-016: gm unos 98 M parámetros, v6.x unos 45 M, imitation_v3
    unos 10.6 M. Coincide con `docs/plans/windows_install.md` L65 ("medium-v1 (10.6M params") y L130 ("diamond (~98M").
  - Arquitectura usada (`imitation_tx_like.py`): un `tx_like` que **no es atención**, sino LSTM o GRU residuales alternadas
    con FFW, de 3×512. La cabeza autorregresiva usa LSTM.
  - Observación: 15 *items* y el mando propio previo; sin el mando del rival. Durante 4–7 frames enmascara la dirección
    de *tech* del rival.
  - Acción: `custom_v1`, 416 combinaciones de botones×c-stick y 85 de stick.
- **Retraso:** cola de acciones (`eval_lib.DelayedAgent` L97-192) de 18–24 frames. Es inherente al peso: no se puede
  evaluar a 0 frames sin reentrenar.
- **Resultados:** el repositorio solo publica grabaciones contra pros, sin cifras [AUT]. Las cifras externas proceden de
  HAL, MIMIC, Faynt y melee-llm, todas con retrasos asimétricos.
- **Licencia:** MIT (código y ficha).
- **Coste [AUT]:** con batch 1 en CPU de escritorio, medium-v1 tarda 1.9–2.5 ms y diamond 10.8–12.7 ms. ONNX con pesos
  fp16 y cómputo fp32. Es la única política con tiempos de CPU documentados por su autor.

### Phillip histórico (vladfi1/phillip, 2017–2018) · agentes `delay0`/`delay12`/`delay18`
- **Proyecto y peso:**
  - Actor-crítico asíncrono con λ-returns recortados por la razón de importancia (`critic.py` L277-294). Sin datos
    humanos. Autojuego y PBT.
  - Acciones: 35 acciones discretas (`custom`) con `act_every=3`.
  - Observación: estado de RAM sin *items* ni escenario.
  - Red: GRU de 512.
  - Predictor de estado: ver §1.4.
- **Resultado (paper 1810.07286, Tabla 1) [AUT]:** contra un pro (top 41), (d=6,p=0) 0–6, (6,6) 3–5 y (7,7) 2–5. Frente
  a la CPU, el agente predictivo rinde algo peor. En población, (4,4) supera a (4,0) y a (4,2), y "best results are
  achieved with p = d".
- **Disponibilidad:** pesos solo en Google Drive. TF1 con `python_requires<3.12`, y el README avisa de *bit-rot*.
- **Licencia:** ambigua (GPLv3 frente a MIT).

### Faynt (frisson-labs) · `Faynt-10M-Arena` (y Base/Expert/75M)
- **Proyecto:** pretrain BC sobre 839,942 réplicas *ranked* (`erickfm/melee-ranked-replays@ef54ddc2`), seguido de
  currículo de rango y resultado y destilación 75M→10M (Expert). Después viene el PPO Arena en dittos de Fox.
- **Peso Arena 10M:**
  - 10,163,629 parámetros: d=384, 5 bloques, GQA 6/2, RoPE, SwiGLU, anillo de 256 frames.
  - Observación: `Game` de slippi-ai con 15 *items* y el mando previo.
  - Acción: códec 728 (botones×hombro×c-stick) × 85 (stick), con offset de 1 frame.
  - El RL se hizo en dos runs:
    1. Run 1 (`evaluation/configs/rl/dolphin_10m_pt_stages_day.toml` L57-105): 72 lanes de autojuego y 24 contra CPU-9, Fox contra Fox
       en 6 escenarios, KL hacia el maestro 0.1, semivida 4 s. Produce `step 1318`.
    2. Run 2 (`evaluation/configs/rl/dolphin_10m_leash_kl0p003_day.toml` L106-130): 100 % autojuego, KL directa e inversa de 0.003
       hacia el Expert, `pg_weight` 3, ε 0.01 en espacio logarítmico, semivida 8 s. Produce `step 632`.
  - El valor es una red separada de unos 2.3 M parámetros (`melee_rl/value.py` L1-17). **No consta que esté en el
    paquete de HF** [DESC].
  - La recompensa es la de slippi-ai portada, de suma cero: stocks, daño, *ledge grab*, *stalling* y aproximación
    (`melee_rl/reward.py` L1-30).
- **Retraso:** el peso Arena es de 0 frames. El actor admite una cola de D (`actor.py`), y hay experimentos no
  publicados a 18 frames con "hindsight teacher".
- **Resultados [AUT], sin intervalos de confianza:**
  - 240/244 en espejos soportados contra 14 versiones de slippi-ai que **conservan 21/24 frames**.
  - Contra un slippi-ai **privado a 0 frames**: Arena 68/68 y Expert 23/68.
  - Panel inicial: 10M Base 49/152 y 10M Expert 106/152.
- **Licencia y uso:** MIT. La ficha dice "Offline use only. Do not use or adapt Faynt for Slippi Online".
- **Coste:**
  - 5.2 ms por decisión en T4 según la ficha.
  - melee-llm mide **en CPU, con 8 hilos, p50 8.1 / p95 10.3 / p99 11.5 ms** para la 10M (`docs/bots.md` L53). Es el
    único peso fuerte medido en CPU por terceros.

### Reyn-26C (frisson-labs)
- **Proyecto y peso:**
  - Tronco de Faynt (por dimensiones, probablemente 10M [INF]) **congelado**. Sobre él, un `ConditioningAdapter` de
    atención cruzada sobre tokens de órdenes, un `StateAdapter` con 16 rasgos y un `TauntHead`.
  - Un *router* BERT traduce frases a una de unas 100 órdenes generales o a 104 especiales de `commands.csv`.
  - No hay código de entrenamiento, y el método (BC con etiquetas de órdenes, RL…) **no está documentado** [DESC].
  - melee-llm lo cifra en 33 M parámetros [AUT de melee-llm].
- **Resultado [AUT]:** 81.8 % de casos de seguimiento de órdenes (1,368/1,672). No hay métrica de fuerza 1v1.
- **Relevancia:** es una jerarquía de control (entrenador→cuerpo). **No es un predictor de transiciones.**

### Bot propio de melee-llm (`train/meleebot`), no publicado
- **BC:** `model.py`, un transformer causal de 6×256 (5.4 M) o 20.7 M parámetros, con embedding de `delay` 0–12,
  embeddings de rango y resultado, y cuatro cabezas 3/9/40/32. `train.py` es BC con condicionamiento que se descarta el
  10 % de las veces.
- **PPO:** `rl/ppo.py` en melee-sim-light (`rl/env.py`, `EnvBatch`).
  - Recompensa: stocks + 0.01·daño (L82-91).
  - Pérdida: doble recorte, KL hacia el maestro de 0.1 y bonificación de entropía con objetivo. La cabeza de valor se
    separa del tronco con `detach`.
  - El dispositivo `cuda` está fijado en el código (L142).
- **Resultados [AUT]:**
  - E09: un 77 % contra el maestro en el simulador no se trasladó a Dolphin.
  - E10: cayó del 77 % al 31 %.
  - E11: un Fox propio ganó 2 de 24 contra CPU-9, porque "holds inputs". **El autor detuvo este pipeline**
    (`docs/status.md` L60).
  - La línea actual es `train/farm/rl.py`, que porta la receta Faynt sobre los pesos de Faynt (E32, en curso, sin
    resultado).

## 3. Decisiones

### D1 · Baselines para la comparación con un world model [PROP] A2-035

El protocolo (06, B0/B1) exige que **B0 y B1 sean propios**, con la misma entrada, controlador y calendario que el world
model. Las políticas publicadas entran como **referencias externas fijas**, nunca como el control principal, porque sus
observaciones, retrasos y datos difieren.

| Rol | Elección | Por qué | Descartes |
|---|---|---|---|
| Imitación, referencia externa | **Faynt-10M-Expert**, con **MIMIC `fox-20260420-baseline`** como segunda opción de BC puro y pequeño | Expert es la etapa supervisada (BC, currículo y destilación, sin PPO) del mismo linaje, observación y códec que Arena. MIMIC fox es BC puro verificado en la ficha | HAL: es AWR con retorno, no BC, y además no tiene licencia de código y exige GPU. `fox-master`: linaje contradictorio. Phillip `*_imitation_v3`: es BC, pero está atado a 18 frames |
| RL sin dinámica explícita, referencia externa | **Faynt-10M-Arena** | Hereda de Expert por PPO con correa KL. La diferencia **Arena − Expert aísla el RL dentro de un linaje** con la misma arquitectura, y ambos juegan a 0 frames. Funciona en CPU a unos 8 ms (medido por melee-llm). Es MIT y está integrado en la granja del simulador (E28) | Phillip gm: el retraso de 21 frames está incrustado. Se usa solo como par **retardado** `fox_d18_imitation_v3` → RL `fox_d18_*` en un eje de retraso aparte. El Phillip histórico es TF1 sin pesos en el repositorio |
| Imitación propia (B0) | BC de la misma arquitectura y códec que Faynt-10M (a menor escala, si el presupuesto lo exige), sobre estado estructurado con el parser de slippi-ai | Comparte el encoder con B1, B2 y W*. Faynt-10M-Base sirve de referencia de techo para la misma arquitectura | — |
| RL propio (B1) | B0 + PPO con KL hacia B0 y valor separado, siguiendo la receta Faynt y slippi-ai, en melee-sim-light | Es el único RL con evidencia de mejora en Melee a partir de BC. Lo documentan slippi-ai, Faynt (Expert 23/68 frente a Arena 68/68 a 0 frames) y MIMIC (279–105) | PPO desde cero queda como ablación secundaria |

Condiciones de uso de las referencias externas:
- Se evalúan con **su propio retraso nativo declarado** y, cuando lo admiten (Faynt, MIMIC, HAL), también a un retraso
  igualado.
- Nunca se mezclan con B0/B1 en una misma afirmación de "efecto del algoritmo".
- Hay que registrar la observación que usa cada una (§1.7).

### D2 · Código de entrenamiento reutilizable para BC y BC+PPO con presupuesto comparable [PROP] A2-036

| Código | BC | PPO | Torch | Licencia | Entorno RL | Veredicto |
|---|---|---|---|---|---|---|
| **Faynt** (`Faynt-Tournament/sources/faynt/268031e7…/model.py` + `Faynt-Benchmarks/evaluation/melee_rl/`) | Hay pérdida NLL (`MeleePolicy.loss` L1942, `AutoregressiveControllerHead.loss` L1838-1883), pero **falta el bucle y el dataloader** | Completo: learner, actor, valor, recompensa y unas 80 TOML | Sí | MIT | Dolphin con Modal. melee-llm `train/farm/rl.py` + `learner.py` ya lo porta a melee-sim-light | **Primario para B1.** El bucle BC se reescribe: unas centenas de líneas sobre `MeleePolicy.loss` y el parser de slippi-ai [INF] |
| **MIMIC** (`train.py`, `rlvr/sim/`) | Completo, con *fallback* a CPU (`train.py:55`) y presets S de 5.4 M y M de 20 M | Completo pero sin crítico, con la línea base de la media | Sí | MIT, y la build nativa GPL-3 | Build nativa propia a partir de la ISO, **distinta** de melee-sim-light | **Primario para el bucle BC** (o para tomar su dataloader). Como PPO, solo es una alternativa |
| slippi-ai | Completo, con retraso integrado | Completo, con la referencia de la correa KL | **JAX** | MIT | Dolphin o melee_sim | Es la **referencia de semántica** (alineación del retraso, recompensa, valor con estado presente). No se adopta como base porque obliga a mantener JAX junto a torch |
| melee-llm `train/meleebot` | Completo | Completo | Sí | Sin LICENSE (es el proyecto del usuario) | melee-sim-light | Su integración es útil (`rl/env.py` con `SelfPlay`, recompensa y semillas). Como receta no se reutiliza: el BC "holds inputs" (E11/E12) y el PPO falló (E09/E10), y el autor lo detuvo |
| HAL 059 | Configuración rígida (batch 512 y 44 fuentes congeladas en `validate_config` L605-789) | No | Sí | **Ninguna** | — | No es reutilizable para entrenar ni para redistribuir |

Presupuesto comparable [PROP]:
- B0 y B1 comparten arquitectura, encoder, códec, datos offline (split por partidas de A6) y número de pasos de BC.
- B1 añade N frames de interacción en el simulador. Los world models (W*) reciben **los mismos frames offline** y **el
  mismo N** de interacción, o 0 si el planificador no aprende online, y se contabiliza el cómputo de preentrenamiento.
- Órdenes de magnitud de referencia, todas [AUT], no transferibles:
  - E10 de melee-llm: 101 M frames en 3.6 h en una 3090 con el modelo de 20 M.
  - Faynt: 1,950 pasos de RL con 96 Dolphins.
  - MIMIC: 100–200 actualizaciones.
- **En esta máquina solo cabe preparar y probar el bucle BC con un subconjunto mínimo**, en CPU y sin ISO. Todo PPO
  requiere la ISO y, en la práctica, la GPU del usuario (dispositivo `cuda` fijado en `meleebot/rl/ppo.py` L142 y en
  `farm/rl.py`).

### D3 · Generador de propuestas (prior) y valor terminal para un planificador [PROP] A2-037
- **Prior y propuestas: Faynt-10M (Expert y Arena) como pareja.**
  - Su distribución factorizada 728×85 permite muestrear K candidatos por frame, o tomar los K principales de botones y
    después de stick.
  - Funciona en CPU a unos 8 ms por paso, y en la granja a 6,337 frames/s con 8 procesos (E28 [AUT]).
  - Expert es el prior "humano", que el RL no ha explotado. Arena es el prior fuerte.
  - Para que el control P0 (las mismas propuestas sin rollouts) sea justo, el planificador y P0 deben usar el **mismo**
    prior, la misma K y la misma temperatura.
  - Alternativa ligera: el B0 propio, que comparte encoder con el world model.
- **Valor terminal: ninguno de los pesos publicados auditados trae un valor reutilizable con licencia y en CPU.**
  - HAL tiene una cabeza V(s) dentro de 059 (se supone en el `.hal` [INF]), pero el código no tiene licencia y exige GPU.
  - Faynt y slippi-ai usan valores separados que no constan en los paquetes publicados [DESC].
  - Propuesta: entrenar V(s) sobre el encoder compartido, de dos maneras:
    - (a) Offline, con la recompensa de slippi-ai y una semivida de 8 s, siguiendo el objetivo de valor de HAL 059 o el de
      slippi-ai `value_function.py`.
    - (b) Tomar el valor del PPO de B1.
  - Si hay retraso, el valor debe ver el **estado presente**, como hacen Firoiu §4.4 y slippi-ai. Fuera del
    entrenamiento eso es información privilegiada, y A5 y A8 deben declararlo.
  - Cuidado: la recompensa de suma cero de slippi-ai incluye términos de modelado (aproximación, *stalling*). El valor
    terminal hereda esos sesgos.

## 4. Dudas que bloquean a otros roles
- **A1/A6:**
  - ¿Qué parser y qué `Game` usará el pipeline propio? Faynt exige el de slippi-ai (`577965a`), y melee-llm usa libmelee
    0.47.6 frente al 0.47.3 de Faynt (`docs/bots.md` L82).
  - ¿Se incluye el mando del rival en la observación? En vivo es observable vía Slippi, pero slippi-ai lo excluye a propósito.
- **A4:**
  - El único predictor de estado probado en una política de Melee (Firoiu 2018) **ignora al rival** y solo ayuda con
    p=d contra rivales que aprenden.
  - Las cabezas de estado de HAL (029, 060) no han mostrado ganancia de juego.
- **A7:** no hay latencias en CPU de 4 vCPU para ninguna política. Las de melee-llm son de una CPU de 8 hilos con carga.
  Faynt-10M es la única candidata realista a prior en CPU.
- **A8:**
  - Cada cifra cruzada publicada lleva asimetría de retraso, y ninguna de las de Faynt tiene intervalos de confianza.
  - Algunas versiones de slippi-ai "also informed RL run or checkpoint selection" (Faynt), lo que contamina un test que
    use esos rivales.
  - Sigue abierto el linaje de MIMIC `fox-master`.
