# BASELINES · Políticas existentes, objetivos, checkpoints y comparación justa (consolidado)

Integrador · 2026-11-19. Consolida y corrige `evidence/A2/BASELINES.md` y `checkpoints.json` con las advertencias
de A8 (`CRITICAL_REVIEW.md` §1, §2 K3/K5, §3.2) y de A7 (`FEASIBILITY.md` §0 y §3). No se descargó ningún peso ni se
jugó ninguna partida: todas las cifras de fuerza y latencia están **atribuidas a sus autores** `[AUT]` o son
mediciones propias de torch en CPU `[MED]`. Las revisiones completas están en `sources.lock.json`. Los claims están en
`evidence/A2/claims.jsonl`.

## 1. Inventario de políticas

| Política · peso | Revisión | Objetivo del **peso** (≠ proyecto) | Obs. (mando rival) | Retraso nativo | Licencia código / pesos | Coste de inferencia | Rol |
|---|---|---|---|---|---|---|---|
| HAL `hal-base-250m-rc` (`hal-250m.hal`) | repo `37045d97`; HF `e7fb8378` | **No es BC pura**: AWR (β=150) + condicionamiento por retorno a 60 f + V(s), es decir, RL offline (receta 059, L1-22) | Estructurada sin velocidades; 4 ranuras de jugador; identidad del ego (no) | 0 en el modelo; *real-time chunking*; 3 en la escalera | **Ninguna** / MIT | Requiere CUDA: p95 6,49 ms en una 3060; p50 4,35 ms en una 3090 | Referencia externa de «imitación condicionada por retorno». **No** sirve de baseline BC |
| MIMIC `fox-20260420-baseline` (`fox/`) | repo HEAD `3691f534` (melee-llm integra `bdfb6293`, con 302 ficheros de diferencia); HF `f49879b6` | BC pura (ficha) | 184 dims con 5 velocidades, sin proyectiles (no) | 0 (`target[i]=buttons[i+1]`) | MIT / MIT (simulador nativo GPL-3) | ~0,5 ms con bf16 y CUDA graphs; p50 3,4 ms en una 3090. En CPU, DESC | Segunda referencia BC, pequeña |
| MIMIC `fox-master` | HF `f49879b6` | **Contradictorio**: BC pura (README) o BC + 100 actualizaciones de RL (CLAUDE.md L587) | — | 0 | MIT | — | No usar sin verificar sus metadatos |
| Phillip II `phillip-models` (gm, master, diamond…) | slippi-ai `5ada33e9`; HF `a5045c53` (`index-v1.json`, unas 188 entradas) | BC con retraso + PPO con KL al maestro, autojuego | Sin mando del rival (`embed.py` L461-463) | **18-24 frames incrustados** (gm 21) | MIT / MIT | diamond (~98M) 10,8-12,7 ms en CPU a batch 1 `[AUT]`; gm p50 2,2 ms en una 3090 | Rival con retraso nativo; nunca baseline a igual retraso |
| Phillip `fox_d18_imitation_v3` → `fox_d18_*` RL | HF `a5045c53` | BC a 18 f → RL | igual | 18 | MIT | ~10,6M parámetros `[INF]` | Par BC→RL para un **eje de retraso** aparte. Hay que fijar el sha256 del índice |
| Phillip histórico (`agents/delay18/FalcoBF`) | `vladfi1/phillip` `114aea4c` | Actor-crítico asíncrono, autojuego, sin datos humanos; **predictor de estado usado en inferencia** (`phillip/model.py` L84, L95-98: solo la acción propia; ignora al rival) | RAM sin ítems | 6 pasos × 3 = 18 f | **Ambigua** (GPLv3 frente a MIT) | TF1 con bit-rot; pesos en Drive | Precedente histórico de dinámica. No reutilizable |
| Faynt-10M-Arena | HF `96929127`; código `Faynt-Tournament d2096176` y `Faynt-Benchmarks 39bc0075` | Base BC → currículo y destilación (Expert) → PPO run 1 (`step 1318`, KL 0,1, 72 lanes de autojuego + 24 contra CPU-9) → run 2 (`step 632`, KL 0,003 directa e inversa, 100 % autojuego) | `Game` de slippi-ai, 15 ítems (no) | 0 | MIT / MIT, «Offline use only» | 5,2 ms en una T4; **CPU 8 hilos p50/p95/p99 8,1/10,3/11,5 ms** (`docs/bots.md` L53); ~16 ms en CUDA en esa máquina | Referencia externa de RL sin dinámica |
| Faynt-10M-Expert | HF **revisión no fijada** | BC + currículo + destilación 75M, sin RL | igual | 0 | MIT | ≈ Arena | Referencia externa BC del mismo linaje. Hay que fijar el SHA |
| Reyn-26C | repo `93fa5274`; HF `6a46ac79` | No documentado; tronco Faynt congelado `[INF]` + adaptadores de órdenes | — | 0 | MIT | — | Fuera de baselines: jerarquía de control, no predictor |
| Bot propio melee-llm (`train/meleebot`) | `7e179081`, sin publicar | BC (5,4M / 20,7M) + PPO en el simulador | Estructurada **con** mando del rival en t−delay (sí) | Embedding de delay 0-12 | Sin LICENSE | PPO con `cuda` fijado en el código | **No reutilizar la receta**: E09/E10 no transfiere, E11 «holds inputs», detenido. Sí el entorno y la recompensa |

Componentes de dinámica en pesos modernos: **ninguno se usa en inferencia** `[COD]`.
- HAL `029 GameStateExpert`: auxiliar, −0,05 NSM, «within noise».
- HAL `060 StateHead`: auxiliar, sin checkpoint.
- slippi-ai `jax/q`, `jax/nash`: predicen Q y valores, no estados. `sim_env` envuelve melee-sim-light, no un modelo
  aprendido.

Esta conclusión es **INFERIDA**: viene de inspeccionar el código, sin cargar pesos (A8 §4 #9).

## 2. Advertencias que condicionan cualquier comparación (A8, A7)

1. **Contaminación por selección de checkpoints.**
   - Faynt-Benchmarks L50: «Some releases also informed RL run or checkpoint selection».
   - Cualquier test que use esas versiones de slippi-ai como rival, con Faynt como prior o referencia, está
     contaminado.
   - Las 240/244 victorias son contra rivales con 21-24 frames de cola (L48, «does not isolate the effect»).
   - El panel a 0 frames es **un** checkpoint privado: 68 partidas son 1 réplica de rival.
   - Regla: la prueba reservada no participa en la selección; los rivales de test van separados de los de selección.
2. **Retrasos distintos.** Todas las cifras cruzadas publicadas son asimétricas:
   - HAL 2 f contra 21 (h2h README L216-221).
   - Faynt 0 contra 21-24.
   - MIMIC 0 contra Phillip 18.

   Ninguna estima la fuerza a igual retraso. Las unidades también difieren (Phillip en pasos × `act_every`; el resto
   en frames). Se reporta el retraso nativo **y** el igualado, cuando el peso lo admite (Faynt, MIMIC, HAL), en filas
   separadas.
3. **Observaciones no comparables.**
   - Mando del rival: slippi-ai, Faynt y HAL lo excluyen; el bot propio lo incluye; el bench lo entrega a todos
     (`I_full`).
   - HAL no tiene velocidades; MIMIC no tiene proyectiles; slippi-ai trunca el % a uint16 y omite
     action_frame/hitlag/hitstun (`tf/embed.py` L443-447).
   - **Corrección K5:** A2 D1 proponía B0 «con el parser de slippi-ai». Se sustituye por **un único esquema propio
     (A6, reparseado de `.slp`) para B0, B1, B2 y W\***. Faynt y las demás quedan como referencias externas
     registradas con su observación.
4. **Pseudorreplicación.**
   - HAL: 96 partidas por par. MIMIC: 30-0 contra CPU-9. Faynt: 68 contra un rival. Firoiu: 6-8 partidas por agente.
   - Simulación de A8 (A8-010): tratar las partidas de una semilla como independientes da **26 % de falsos
     positivos**.
   - Unidad de inferencia: la **semilla de entrenamiento** para recetas y el bloque emparejado para planificación
     sobre un checkpoint fijo.
   - Con 5 semillas, la diferencia mínima detectable es ≈8-11 pp a 200 partidas por semilla (A8-011). La MCID
     preregistrada es 5 pp, con TOST ±5 pp para afirmar «no aporta» (A8-015, A8-021).
5. **Firoiu 2018 (At Human Speed) es evidencia débil a favor de predecir.**
   - Tabla 1: (6,0) 0-6, (6,6) 3-5, (7,7) 2-5. Pero los días de entrenamiento son **3, 10 y 7**.
   - Un agente por celda, 6-8 partidas, y un predictor que ignora al rival (A8-004). «p = d» es la conclusión de los
     autores.
6. **El RNG no se controla.** Dolphin no se siembra (HAL h2h L32-36). `runner.play(mode="sim")` no reenvía la
   semilla. Los «pares» solo comparten semillas de la política.
7. **CPU-9 es explotable** (Firoiu): no sirve como ancla de fuerza, aunque el bench ancle BT en `cpu:9 = 1500`.
8. **Motor distinto entre la farm y el runtime** (melee-brute `MELEE_SIM` DESC frente a `090e54b0`). Los resultados de
   farm (E28-E32) y `--mode sim` pueden no ser comparables.
9. **Qué cabe en tiempo real** (A7 `[MED]` en esta CPU de 4 vCPU; A8 K3):
   - No hay latencias de ninguna política publicada medidas en 4 vCPU.
   - Faynt-10M (8,1/10,3/11,5 ms en 8 hilos) más rollouts **no cabe en 16 ms**. Como prior de propuestas solo vale en
     `untimed` o con GPU dedicada.
   - En `RT-strict` en CPU el prior debe ser una cabeza barata sobre el encoder compartido (B0).
   - HAL exige GPU. Phillip diamond (10,8-12,7 ms) apenas deja margen frente a los 10 ms p99 de diseño con Dolphin.
   - Un MPC aprendido en RT aquí es ≈1M parámetros con K·T ≈ 1.000 evaluaciones (GRU-1M K64×T16, p99 15,3 ms;
     MLP-1M K16×T8, 2,8 ms). A 15M no cabe nada.
   - Sin plazo impuesto, todo es `RT-slow`: el bench no impone plazo (`SYSTEM_MAP.md` §2).
10. **No ejecutable aquí:** PPO, simulador y partidas. No hay ISO ni GPU; `train/` exige torch ≥ 2.11 (aquí 2.10), y
    faltan `peppi_py`, `melee` y `zstandard`. Solo cabe un piloto del bucle BC en CPU.

## 3. Decisiones (PROPUESTA, con las correcciones integradas)

### D1 · Baselines

| Rol | Elección | Motivo / condición |
|---|---|---|
| **B0 (BC propia, control principal)** | BC con la misma arquitectura y códec que Faynt-10M (escala reducida si el presupuesto lo exige), sobre el **esquema único de A6** | Comparte encoder, datos (split por partida antes de ventanas, `evidence/A6/split_plan.json`) y calendario con B1, B2 y W\* |
| **B1 (RL propio sin dinámica)** | B0 + PPO con KL hacia B0 y valor separado (receta Faynt/slippi-ai), en el simulador | Es el único RL con mejora documentada en Melee desde BC (Faynt Expert 23/68 → Arena 68/68 a 0 f; MIMIC 279-105), todo `[AUT]` |
| Referencia externa BC | Faynt-10M-Expert (hay que fijar el SHA de HF). Alternativa: MIMIC `fox-20260420-baseline` | Nunca en la misma afirmación de «efecto del algoritmo» que B0/B1 |
| Referencia externa RL | Faynt-10M-Arena (`96929127`) | Arena − Expert aísla el RL dentro de un linaje y ambos juegan a 0 f. Contaminación (§2.1): rivales de test ≠ versiones de slippi-ai usadas para seleccionar |
| Eje de retraso (aparte) | Phillip `fox_d18_imitation_v3` → RL `fox_d18_*` | Hay que fijar el sha256 desde `index-v1.json`. No se mezcla con la tabla a 0 f |
| Descartados como baseline | HAL (no es BC, código sin licencia, GPU), `fox-master` (linaje), Phillip histórico, meleebot | — |

### D2 · Código reutilizable

| Pieza | Fuente | Veredicto |
|---|---|---|
| PPO, learner, actor, valor, recompensa | `Faynt-Benchmarks/evaluation/melee_rl/` (MIT) y su port a melee-sim-light en melee-llm `train/farm/{rl,learner}.py` (`rl.py`, `learner.py` y `rl_eval.py` son **nuevos en `7e179081`** y no existen en el catálogo `2bf8b0eb` ✔) | Primario para B1 |
| Bucle y dataloader BC | MIMIC `train.py` (MIT, *fallback* a CPU, presets de 5,4M y 20M), sobre `MeleePolicy.loss` de Faynt (`model.py` L1942) | Faynt no publica su bucle BC. Habría que reescribirlo, unas centenas de líneas `[INF]` |
| Semántica de retraso, valor y recompensa | slippi-ai (JAX, MIT) | Referencia, no base: obligaría a mantener JAX junto a torch |
| Entorno y recompensa de autojuego | melee-llm `train/meleebot/rl/env.py` | Reutilizable. La receta, no |
| HAL 059 | — | No reutilizable: sin licencia y con configuración rígida |

**Presupuesto comparable:**
- B0/B1/W\* comparten arquitectura, encoder, códec, frames offline y número de pasos de BC.
- B1 y W\* reciben el **mismo N** de frames de interacción (o 0) y se contabiliza el preentrenamiento.
- Órdenes de magnitud `[AUT]`, no transferibles: E10 = 101M frames en 3,6 h en una 3090; Faynt = 1.950 pasos de RL
  con 96 Dolphins.

### D3 · Prior de propuestas y valor terminal

- **Prior:**
  - En `untimed` o GPU: Faynt-10M Expert (prior «humano») y Arena (prior fuerte). Su códec factorizado 728×85 permite
    muestrear K candidatos.
  - En `RT-strict` en CPU: una cabeza sobre el encoder de B0 (corrección K3).
  - Control P0 (mismas propuestas sin rollouts): **mismo** prior, K y temperatura que el planificador.
- **Valor terminal:**
  - Ningún peso auditado trae un V(s) reutilizable con licencia y en CPU. HAL tiene uno, sin licencia y con GPU. Los
    valores de Faynt (~2,3M) y slippi-ai no constan en los paquetes publicados.
  - Propuesta: entrenar V̂ sobre el encoder compartido, (a) offline con la recompensa de slippi-ai y semivida de 8 s,
    o (b) desde el crítico de B1.
  - Con retraso, V̂ ve el **estado presente** (Firoiu §4.4, slippi-ai). Eso es información privilegiada en
    entrenamiento y hay que declararlo. La recompensa de slippi-ai incluye términos de modelado (aproximación,
    *stalling*), y V̂ los hereda.

## 4. Reglas de comparación justa (resumen operativo)

1. Iguales: observación (esquema A6), régimen de información (`I_full` primario; `I_human` secundario obligatorio;
   nunca se mezclan), controlador y códec, retraso declarado (D_reaction + D_transport + D_compute), datos offline y
   frames de interacción.
2. La selección de checkpoints e hiperparámetros solo usa la validación. Test y rivales de test quedan reservados,
   incluidas las versiones de slippi-ai que influyeron en Faynt.
3. Reportar por reloj (`RT-strict`, `RT-slow`, `untimed`), por motor (Dolphin `fast`/`realtime`, sim con la revisión
   del motor) y por retraso, en tablas separadas.
4. Distinguir las semillas de entrenamiento de las partidas de evaluación. Las referencias externas son **un** peso:
   0 réplicas de receta.
5. Toda cifra publicada sigue atribuida a su autor y nunca entra como resultado propio.

## 5. Pendiente (no verificado)

| Pendiente | Acción |
|---|---|
| Linaje de MIMIC `fox-master` | Descargar sus metadatos |
| SHA de HF de Faynt Expert, Base y 75M | Fijarlos |
| sha256 de los `.onnx` de Phillip elegidos | Tomarlos del índice |
| Qué run es `hal-250m.hal` | Candidato W&B `vywk3cih` |
| Latencias de cualquier política en 4 vCPU con Dolphin corriendo | Medir (A7 H10) |
| Si MIMIC `bdfb6293` (el que integra melee-llm) y `3691f534` (el auditado) difieren en `train.py`/modelo de forma relevante | Comparar; hay 302 ficheros de diferencia, sobre todo `runs/` |
