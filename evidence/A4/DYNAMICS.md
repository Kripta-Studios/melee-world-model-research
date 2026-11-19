# A4 — Dinámica aprendida y modelo del rival (diseño concreto)

Agente A4 · 2026-11-19 · Escribe solo en `evidence/A4/`. Etiquetas: **DOC** = DOCUMENTADO_POR_AUTOR, **CÓD** =
INSPECCIONADO_EN_CODIGO, **REP** = REPRODUCIDO (local_check propio), **INF** = INFERENCIA, **PROP** = PROPUESTA,
**DESC** = DESCONOCIDO. Los IDs `[A4-xxx]` remiten a `claims.jsonl`. Contrato para A5: `model_contract.json`.

Construye sobre A1 (`SYSTEM_MAP.md`, `CONTRACT.md`), A3 (`REPRESENTATIONS.md`, `ablations.json`), A6
(`DATA_AND_TIME.md`, `timing_contract.json`, `split_plan.json`) y A2 (`BASELINES.md`). No repito lo que ya
establecieron; lo cito.

Revisiones de código leídas (HEAD de `ops/clone_inventory.txt`):

| Repo | SHA | Qué leí |
|---|---|---|
| lucas-maes/le-wm | `8edfeb336732b5f3ce7b8b210d0ba370a09e2cac` | `jepa.py`, `train.py`, `module.py`, `eval.py`, `config/**` |
| danijar/dreamerv3 | `e01491fad6434b2245a3b8ca201dd7faedcc458c` | `dreamerv3/rssm.py`, `agent.py`, `configs.yaml` |
| nicklashansen/tdmpc2 | `332f19e4aba4bffe2dc736f45ea7f7bdc585903a` | `tdmpc2/tdmpc2.py`, `common/world_model.py`, `common/layers.py`, `config.yaml` |
| gaoyuezhou/dino_wm | `0a9492fa12044b852ae9e001cc74604b79c8bb0c` | `models/visual_world_model.py`, `planning/objectives.py`, `conf/train.yaml` |
| facebookresearch/jepa-wms | `13cf1d9c7e476f53c17714d2e0f1dc239a883ce0` | `app/vjepa_wm/train.py` (rollout_cfg) |
| facebookresearch/vjepa2 | `204698b45b3712590f06245fbfba32d3be539812` | `app/vjepa_droid/train.py` (pérdida AC) |
| vladfi1/phillip | `114aea4c446b31359c5637b271db52b200440caa` | `phillip/model.py`, `phillip/actor.py` |
| mateo19182/melee-brute | `9662ec973b9e077ff7b0ff89d6db950f53c11653` | `BRUTE.md`, `melee_brute/match.py`, `fox.py` |
| kyhavlov/melee-sim-light | `eea7b5fbcd0243baf4c1956d52f3e1d0f536edc4` | `agent_docs/VALIDATION.md`, `tools/validation/native.c` |
| mateo19182/melee-llm | `7e179081c6cbab139d860c998b1452ad3dee047c` | `melee_llm/sim/parity.py`, `docs/simulator.md`, `docs/delay.md` |
| ericyuegu/hal | `37045d974116405dd690efea6109a1d83a2da868` | `experiments/060_compute_optimal_action_sequence.py` (`StateHead`) |

Papers (WebFetch): LeWM arXiv 2603.19312v3 (html), At Human Speed 1810.07286 (pdf → texto), MuZero 1911.08265
(pdf → texto), TD-MPC2 2310.16828v2 (html), DreamerV3 2301.04104 (abs; detalles tomados del código).

---

## 0. Resumen ejecutivo

1. **La transición se define a 1 frame sobre el estado aumentado**, no sobre `post(f)`. El estado de Markov del
   motor incluye el mando previo y temporizadores de stick que `post(f)` no expone (A6; melee-brute lo confirma:
   estados "look-alike" difieren solo en lo que cada jugador mantenía pulsado) [A4-003]. Historia mínima
   propuesta: 8 frames de estado + 8 frames de mandos crudos de **ambos** puertos; se valida con un test de
   aliasing en el simulador (§5.4).
2. **Dos predictores con el mismo contrato:** W0-S (estructurado, cabezas por campo, 1 frame, multihorizonte) y
   W1-L (latente estilo LeWM: encoder de estado + `ARPredictor` AdaLN-zero + SIGReg, bloque de k=4 frames con
   los mandos de ambos jugadores concatenados). W0-S es el control obligatorio de W1-L (es el E1-S de A3 llevado
   a dinámica).
3. **LeWM planifica hacia una imagen meta** (`jepa.py` L112-126, coste MSE del último embedding) [A4-010]. En
   Melee no hay meta: el sustituto propuesto es **recompensa + valor terminal + continuación aprendidos sobre el
   latente** (patrón TD-MPC2/Dreamer/MuZero), con la variante "fiel" (cabezas sobre `sg(z)`) y la "acoplada"
   (gradiente al encoder). La meta-prototipo se deja como ablación.
4. **El rival se separa en dinámica conjunta p(s'|s,a_yo,a_rival) y política q(a_rival|historia).** Se planifica
   con K hipótesis coherentes muestreadas de q (bucle cerrado sobre el estado imaginado), agregadas por media o
   CVaR; el peor caso sobre un menú se restringe a lo que el rival puede hacer **después de su tiempo de
   reacción**. Promediar futuros (lo que hace un modelo L2 que ignora al rival, como Phillip 2018) produce estados
   imposibles [A4-007, A4-015].
5. **Contrafactuales con verdad de terreno sí son posibles, con límites.** No hay `GameState → estado del
   simulador` (A1), pero sí **"replay-to-reach"**: reinyectar los mandos crudos de un `.slp` en el simulador con la
   semilla de la partida reproduce el estado humano exactamente hasta la primera divergencia de RNG (melee-llm
   `sim/parity.py`; 15/40 partidas no divergieron nunca, DOC) y desde ahí se ramifica con acciones arbitrarias
   [A4-020, A4-021]. Más estados simulados alcanzados por políticas BC. Nada de esto es ejecutable aquí (no hay ISO).
6. **La pregunta incómoda, respuesta corta:** en `--mode sim`, un modelo de dinámica aprendido **no aporta nada que
   el simulador no haga mejor**: en esta CPU un predictor del tamaño de LeWM tarda ≈0,9 ms por candidato-paso
   (REP) frente a 12-17 µs/frame documentados para el simulador [A4-025, A4-026]. Lo irreemplazable es el
   **modelo del rival** (una política, no una dinámica) y, en Dolphin/netplay, la ausencia de estado del simulador.
   Incluso ahí existe la alternativa "simulador sombra" alimentado con los mandos de ambos jugadores, exacta hasta
   la primera divergencia de RNG (PROP) [A4-027]. El nicho real del modelo aprendido es estrecho y está en §6.

---

## 1. Definición de transición para Melee

### 1.1 Índices y alineación (sobre A6)

- Fila `f` = `PostFrame(f)` de ambos puertos + `PreFrame(f)` de ambos puertos; el mando de la fila `f` **ya**
  actuó sobre el estado de la fila `f` (A6 `timing_contract.json` `row_alignment_in_parsers`, CÓD).
- Por tanto la transición del motor es:

  `x_{f+1} = F( x_f, m_f, u^yo_{f+1}, u^riv_{f+1}, ρ_f )`

  con `x_f` = estado observable post(f), `m_f` = memoria oculta del motor que importa para el siguiente frame
  (mando previo de ambos para flancos, temporizadores de stick, contadores no exportados), `u_{f+1}` = mandos de
  `PreFrame(f+1)` y `ρ_f` = estado del RNG (`frame_pre_random_seed`, que el simulador expone en su observación
  nativa — A1 §6.4 — y que en datos solo sobrevive en el `.slp` crudo — A6 hallazgo 3).
- **Estado aumentado que usa el modelo** (PROP): `h_f = (x_{f-H+1..f}, u^yo_{f-H+1..f}, u^riv_{f-H+1..f})`.
  `m_f` se aproxima con la ventana de mandos; `ρ_f` **no** entra (ver §1.4). En el régimen de información
  `I_human` (§4.4) `u^riv_{f}` tampoco entra y se convierte en variable latente a inferir.
- Decisión bajo demora (A6, PROP): mando decidido tras ver post(f) se aplica en `f+1+D`. Para predecir el
  "presente" del frame de aplicación, el modelo se despliega `D+1` frames con la cola propia comprometida
  `u^yo_{f+1..f+D}` (conocida) y con **hipótesis** del rival `u^riv_{f+1..f+D}` (desconocidas). Esto es
  exactamente el esquema (d,p) de Firoiu 2018 §4.2, salvo que Firoiu no condiciona al rival (§5.2) [A4-006].

### 1.2 Paso de predicción

| Opción | Qué es | Pros | Contras | Decisión |
|---|---|---|---|---|
| 1 frame | `h_f, u_{f+1} → x_{f+1}` | Granularidad del motor; contadores (hitlag, hitstun, action_frame) avanzan de 1 en 1, lo que da cabezas casi deterministas; verdad de terreno directa | Horizonte 32 = 32 pasos AR; acumulación | **W0-S** (base) |
| Bloque de k frames | `h_f, u_{f+1..f+k} → x_{f+k}` (los k mandos de ambos concatenados, como `frameskip` de LeWM: `train.py` L68 `input_dim = frameskip * action_dim`, `pusht.yaml` `frameskip: 5`) | 8 pasos para 32 frames; planificador sobre macro-acciones | Pierde estados intermedios (un golpe en el frame 2 del bloque); los k mandos deben guardarse todos (A6 §5) | **W1-L** con k=4, ablación k∈{1,2,4,8} |
| Duración variable (por evento) | saltar hasta el siguiente frame en que algún jugador es accionable | Comprime hitstun/animaciones comprometidas | Durante hitlag y hitstun **los mandos sí importan** (SDI/ASDI/DI y deriva) [INF, conocimiento del juego no verificado en código]; complica el lote y la planificación; necesita cabeza de duración | Solo como ablación posterior (W1-evt) |

Regla (PROP): los mandos **nunca** se resumen a "el último del bloque": se pasan los k mandos de ambos jugadores
(A6 `transition_spec_joint`). Frame skip del agente (decisiones cada n frames) es una propiedad del planificador
(A5), no del modelo: el modelo siempre recibe mandos por frame.

### 1.3 Acciones efectivas de ambos puertos

- **Canal de entrada del modelo:** mandos del `PreFrame` en espacio **físico/crudo** cuantizado — botones
  A,B,X,Y,Z,L,R,D_UP como bits (el subconjunto que aplican los bots, `LLM:bots/agent.py APPLIED_BUTTONS`, A1 §7.1),
  stick principal y C-stick en la rejilla entera −80..80 por eje, gatillos L/R 0..140 (rejilla 1/140, A6). Se
  añaden **flancos derivados** `pressed_f = b_f ∧ ¬b_{f-1}` (A6 `controller_semantics`) como features, pero la
  verdad son los estados mantenidos.
- Razón: el simulador y melee-brute se manejan con mandos crudos (`Match.step(p1, p2)` con `pad(buttons,x,y,…)`,
  `match.py` L24-25, L76-85, CÓD) y la validación prohíbe reconstruir crudos desde procesados
  (`VALIDATION.md` L49-52, DOC). Si el corpus solo tiene procesados (slippi-ai), el modelo usa procesados y se
  declara que no es comparable bit a bit con el simulador (A6).
- **Ambos puertos son simétricos en el modelo**: misma codificación para `u^yo` y `u^riv`, con un embedding de
  rol (yo/rival). La perspectiva se canonicaliza (espejo x→−x si el yo mira a la izquierda… solo como
  canonicalización determinista, nunca como invariancia, A3 §3.1).

### 1.4 Hitlag, hitstun, RNG y eventos discretos

| Fenómeno | Tratamiento en el modelo (PROP) | Base |
|---|---|---|
| Hitlag (`hitlag_left`, f32 desde Slippi 3.8.0; `BR ≥ d3832724`) | Cabeza de contador: {decrementa 1, reinicia a v, 0}. Durante hitlag la posición no avanza salvo SDI; los mandos se siguen pasando | A6 `per_frame_fields`; A1 §6.4 (`hitlag_left` no existe en el pin `090e54b0`) |
| Hitstun (`hitstun_remaining`, válido solo con su flag) | Igual; **máscara** fuera de hitstun: libmelee reporta basura y el simulador 0 (melee-llm `docs/simulator.md` L53, DOC) | A6; `simulator.md` L53 |
| `action_frame` | Cabeza de contador {+1, reinicia a 1 (cambio de acción), otro} condicionada a la cabeza de acción | A1 §6.1 (indexado desde 1) |
| Cambio de estado de acción | Cabeza **categórica** de acción (vocabulario ≤512, como HAL `StateHead` CE 512 clases, A2) + cabeza binaria "cambia/no cambia". El cambio es el evento que más pesa en la métrica | — |
| Golpe | Evento derivado: Δpercent>0 o entrada en acción de daño; cabeza multi-etiqueta de eventos | — |
| Muerte / reaparición | Evento `death` (stock−1); posición **no** se regresa por delta: tras muerte se predice por la cabeza "absoluta" (plataforma de reaparición); el jugador muerto se enmascara en las pérdidas de pos/vel durante la espera | INF |
| RNG | **No se modela como entrada.** Los campos afectados por eventos aleatorios se tratan como aleatorios (cabezas de distribución). Se mide su peso con el test de "gemelos de RNG" (§5.5). En el simulador el RNG no se re-siembra por frame (A1 §8) y no coincide con el de Dolphin (`docs/simulator.md` L72, DOC) | A1, A6 |
| Rollback de netplay | Entrenar dinámica solo con copias LAST (comprometidas); FIRST no es una trayectoria causal (A6, CÓD+INF) | A6 `rollback_policy` |

### 1.5 Terminación vs truncamiento

- `terminated` = fin por reglas: stocks de un jugador a 0 (GAME!), o temporizador interno agotado (TIME!, 8 min;
  `max_frame=28800` en sim, `LLM:sim/world.py` L19, A1) → resultado por stocks y porcentaje (09 §TransitionSpec).
- `truncated` = fin de ventana de entrenamiento, horizonte del planificador o corte externo. **Nunca** se entrena
  la cabeza de continuación con un truncamiento como si fuera fin de partida (es el error que el `con` de
  DreamerV3 evita usando `is_terminal` y no `is_last`: `agent.py` L174-177, CÓD) [A4-012].
- `invalid` (No Contest, LRAS, frames no contiguos, crash) = se excluye del entrenamiento de continuación y
  valor (A6).
- Muerte súbita: Dolphin la juega como partida nueva no contada; el simulador no la tiene (A1 §2.1, §8). La
  continuación se define hasta el fin de la partida cronometrada.
- Cabeza `cont(z)` = P(no terminated en el paso) — en Melee casi siempre 1; lo útil es la cabeza de **evento de
  muerte** por jugador, que alimenta la recompensa.

---

## 2. Predictor ESTRUCTURADO W0-S (baseline de dinámica)

### 2.1 Entradas (por frame de la ventana H=8; PROP)

Por jugador (yo, rival), en perspectiva canonicalizada:
- Continuos (normalizados por estadísticas de train): `pos_x, pos_y`, 5 velocidades (`speed_air_x_self,
  speed_y_self, speed_x_attack, speed_y_attack, speed_ground_x_self`), `percent`, `shield`, distancia al borde
  más cercano, `dx, dy` relativos.
- Categóricos (embedding): `action` (≤512), `character`, `facing`, `on_ground`, `jumps_left` (0..6), `stock`
  (0..4), `hurtbox_state`, `invulnerable`.
- Contadores (embedding ordinal + escalar): `action_frame` (recorte 0..255), `hitlag_left`, `hitstun_left`
  (enmascarado), `invulnerability_left` si existe.
- Mandos de ambos (§1.3) en los H frames, más el mando **siguiente** `u_{f+1}` de ambos (el que causa la
  transición). Proyectiles: 4 ranuras (como HAL MDS) con existencia, tipo, pos, vel, dueño.
- Escenario: `stage_id` + dinámica (Randall, plataformas de FoD) como en A6.
- **Advertencia de corpus:** HAL MDS no tiene velocidades, `action_state_frame`, hitstun ni crudos (A6 hallazgo
  4). Un W0-S entrenado solo con HAL MDS tiene un suelo de error irreducible por aliasing en knockback/hitstun:
  sirve de prototipo, no de resultado. El esquema completo exige reparsear `.slp` (A6 §5).

### 2.2 Salidas / cabezas por campo

| Campo | Cabeza | Pérdida | Comentario |
|---|---|---|---|
| `action` | categórica 512 + binaria "cambia" | CE (+ BCE) | La CE se pondera ×w en frames de cambio (los "sin cambio" son ~triviales) |
| `facing, on_ground, invulnerable, hurtbox` | Bernoulli/categórica | BCE/CE | |
| `jumps_left, stock` | categórica | CE | `stock` solo cambia en muerte |
| `action_frame, hitlag_left, hitstun_left` | **modo** {continúa (±1), reinicia, cero} + categórica del valor de reinicio | CE | Estructura residual explícita, análoga a la compuerta *forget* de Phillip (`model.py` L53-60: `forget*(last+delta)+(1-forget)*new`, CÓD) |
| `Δpos_x, Δpos_y`, velocidades | **two-hot** sobre bins symlog (estilo `symexp_twohot` de DreamerV3, `configs.yaml` `rewhead.output`) o mezcla de 3 logísticas | CE sobre bins / NLL | Multimodal por naturaleza (golpe/no golpe, snap a borde). Gaussiana unimodal solo como ablación (HAL 060 usa NLL gaussiana con log-escala aprendida por campo y offset, `StateHead` L1185-1197, CÓD) |
| `pos` absoluta | cabeza activada por `teleport` (muerte, reaparición, agarre de borde) | NLL | |
| `Δpercent` | categórica 0..60 en pasos de 0,01 agrupados (bins) | CE | `percent` ≥ 0, reinicia en reaparición |
| `shield` | two-hot | CE | |
| eventos | multi-etiqueta {cambio de acción yo/riv, golpe a yo/riv, escudo golpeado, agarre, muerte yo/riv, reaparición, tech, rotura de escudo, agarre de borde} | BCE | Derivados de la diferencia de estados; son la métrica principal (§5) |

Pérdida total: suma de NLL por campo con **peso por campo normalizado por la NLL de una línea base trivial**
(persistencia / velocidad constante) en validación, para que ningún campo domine por escala. Alternativa: log-escala
aprendida por campo (como HAL `StateHead`) [PROP].

### 2.3 Arquitectura y multihorizonte

- Tronco: embedding por jugador → transformer pequeño sobre los 2 jugadores + 4 proyectiles por frame (atención
  entre entidades) → GRU o transformer causal sobre H=8 frames → cabezas. ~0,5-2 M parámetros (en CPU la cabeza
  MLP de 0,7 M tarda ~10 µs por candidato con lote 512, REP §6.1).
- **Dos modos de multihorizonte**, ambos obligatorios en la evaluación:
  1. **Autorregresivo a 1 frame** con pérdida de despliegue de K=8 pasos durante el entrenamiento (como el
     `auto_steps` de V-JEPA 2-AC, `app/vjepa_droid/train.py` L417-449; `rollout_steps` de jepa-wms,
     `app/vjepa_wm/train.py` L132-142; K=5 de MuZero; horizonte con descuento ρ=0,5 en TD-MPC2, `tdmpc2.py`
     L272-275, `config.yaml` `rho: 0.5`) [A4-009]. Realimentación: estado muestreado (categóricos) + media de
     two-hot (continuos), con *scheduled sampling*. Pesos ρ^t.
  2. **Cabezas directas** a offsets {1,4,8,16,32} condicionadas a la secuencia de mandos de ambos (como HAL 060,
     offsets 1-30). Sin acumulación, pero no componen; sirven para evaluar y como valor de "ancla".
- Líneas base triviales que W0-S debe batir por campo y horizonte: **persistencia** (copiar `x_f`), **velocidad
  constante** (`pos += vel`, contadores ±1), y **mayoritaria condicionada** (acción siguiente más frecuente dada
  (acción, action_frame) en train).

### 2.4 Qué es irreducible sin RNG ni memoria oculta

1. Eventos que consumen RNG (aleatoriedad del juego). Peso empírico: en 25 de 40 partidas del autor de melee-llm
   el simulador sin RNG inyectado diverge en algún momento (15/40 nunca), `docs/simulator.md` L53 (DOC) [A4-021].
   Qué movimientos/personajes consumen RNG en juego: DESC en esta auditoría (no localicé una lista en código).
2. Memoria del mando (flancos, temporizadores de stick) más allá de H. melee-brute documenta que todos los
   estados "look-alike" distintos que encontró difieren en eso (`BRUTE.md` §"Exact or look-alike", DOC) [A4-003].
3. En `I_human`: el mando actual del rival `u^riv_f` (necesario para los flancos del frame siguiente) — ver §4.4.
4. Por corpus: velocidades/hitstun/action_frame si se entrena con HAL MDS; decimales de `percent` con slippi-ai
   (uint16) (A6).
5. **El mando futuro del rival** — no es ruido de la dinámica, es otra variable (§4). Un modelo que no lo recibe
   mezcla las dos fuentes (Phillip 2018).

---

## 3. Predictor LATENTE W1-L inspirado en LeWorldModel

### 3.1 Qué hace LeWM en el código (CÓD, le-wm `8edfeb33`)

- `JEPA.encode` (`jepa.py` L29-45): ViT → CLS → `projector` (MLP con BatchNorm). Acciones → `Embedder`
  (Conv1d k=1 + MLP, `module.py` L189-214).
- `ARPredictor` (`module.py` L244-285): `pos_embedding` aprendido de `num_frames = history_size = 3` + transformer
  de `ConditionalBlock` (AdaLN-zero, `module.py` L88-111: el embedding de acción del **mismo paso** modula
  shift/scale/gate de atención y MLP; inicializado a cero) con atención causal; profundidad 6, 16 cabezas,
  `mlp_dim` 2048 (`config/train/model/lewm.yaml`).
- Pérdida (`train.py` L17-45): `ctx = emb[:, :3]`, `tgt = emb[:, 1:]` (num_preds=1), `pred_loss = MSE`
  teacher-forcing en las 3 posiciones + `0.09 · SIGReg(emb.transpose(0,1))`; **sin stop-grad ni EMA** (A3).
- `rollout` (`jepa.py` L61-110): codifica la historia, despliega autorregresivamente truncando a `history_size`
  y concatena; `criterion` (L112-126): **MSE del último embedding predicho con el embedding de la meta**;
  `get_cost` (L128-153) codifica la imagen meta.
- Planificación: el solver CEM vive en `stable_worldmodel` (dependencia externa, no en el repo):
  `config/eval/solver/cem.yaml` 300 muestras, top-30, 30 iteraciones; `config/eval/pusht.yaml` horizonte 5,
  `receding_horizon 5`, `action_block 5`. Hay además `config/eval/solver/adam.yaml` (planificación por gradiente).
- Paper (DOC, 2603.19312v3): coste "terminal latent goal-matching" ‖ẑ_H − z_g‖²; entrenamiento solo
  teacher-forcing a 1 paso; predictor determinista; "planning remains restricted to short horizons"; plan
  < 1 s, 48× más rápido que DINO-WM, hardware no especificado; no discute multiagente ni estocasticidad [A4-010].
- Split por ventanas, no por episodio (`train.py` L73-76) → en Melee sería fuga (A3, A6).

### 3.2 Diseño W1-L (fiel vs modificado)

| Elemento | LeWM | W1-L | Etiqueta |
|---|---|---|---|
| Objetivo de representación | MSE siguiente embedding + λ·SIGReg, sin stop-grad, extremo a extremo | Igual. λ=0,09 por defecto, barrido de A3 {0.01…0.5} | **FIEL** |
| Predictor | `ARPredictor` AdaLN-zero causal | Igual estructura; d=128, profundidad 4, 8 cabezas×16, mlp 512 (≈1,2 M; REP §6.1). El tamaño LeWM (10,8 M) como brazo grande | FIEL (estructura) / **MOD** (tamaño) |
| Proyector BN | sí | sí | FIEL |
| Encoder | ViT-Tiny sobre píxeles | **Encoder de estado estructurado** de A3 (embeddings por campo → transformer de entidades) por frame; **el mismo E que B2/E1** | **MOD** |
| Historia | 3 pasos | **H=4 bloques de k=4 frames** (16 frames) + ventana de mandos crudos de 8 frames dentro de cada token | **MOD** (justificación §1.1) |
| Acción | bloque de `frameskip` acciones de un agente concatenadas | `c_t = Emb_yo(u^yo_{bloque}) + Emb_riv(u^riv_{bloque}) + Emb_rol`; el rival puede sustituirse por un token `UNK` (dropout p=0,25) para entrenar también el modo marginal **solo como diagnóstico** | **MOD** (dos jugadores) |
| Pérdida temporal | 1 paso TF | 1 paso TF **+ despliegue AR de 2-4 bloques** (estilo V-JEPA 2-AC `auto_steps`; `jepa-wms rollout_steps`) | **MOD** |
| Cabezas adicionales | ninguna (decodificador solo post hoc para visualizar) | decodificador de campos estructurados sobre `sg(ẑ)` (sondas para medir error por campo y para comparar con W0-S), **recompensa, valor, eventos/continuación** (§3.3) | **MOD** |
| Coste de planificación | ‖ẑ_H − z_g‖² | Σ γ^k r̂ + γ^H V̂ (§3.3) | **MOD** (central) |
| Split | ventanas aleatorias | por partida (A6 `split_plan.json`) | **MOD** (corrección) |
| Dimensión latente | 192 | **D=128** por defecto, barrido {64,128,192,256} con A3; riesgo de baja dimensión intrínseca/categórica (A3 §1.5) | MOD |

Riesgo específico del método en dos jugadores (INF, sobre A3 §1.5): sin stop-grad, el encoder puede "gaussianizar"
la información del rival que no es predecible desde el contexto. Si el predictor recibe `u^riv` real en
entrenamiento, esa información sí es predecible y se conserva; si en inferencia se le dan hipótesis de q, el
latente no debería haber descartado nada. Se comprueba con sondas de campos del rival (A3).

### 3.3 Sustituto de la imagen meta: recompensa/valor, y por qué

Opciones:

| Opción | Cómo puntúa un candidato | Ventaja | Problema en Melee |
|---|---|---|---|
| (a) Meta-prototipo (fiel a LeWM) | `min_g ‖ẑ_H − z_g‖²` sobre un banco de "situaciones ventajosas" (rival en hitstun cerca del límite, yo en centro…) | Cero cabezas nuevas; mantiene la pureza "reward-free" | La distancia euclídea en un latente SIGReg no está calibrada como utilidad; un juego adversarial no tiene un estado meta; fácil de explotar por el planificador (Firoiu §5.1: "likely to exploit flaws in the model") |
| (b) **TD-MPC2**: r̂(z,a), Q(z,a) (5 Q's), política previa, MPPI | `_estimate_value` (`tdmpc2.py` L123-136): Σ γ^t r̂ + γ^H Q(z_H, π(z_H)) con terminación | Patrón probado sin decodificador; consistencia latente con `sg` del objetivo (paper §3.1 Eq.3; código L272-275) | Diseñado para MDP de un agente con acción continua; no trata al rival; el Q depende de la política propia |
| (c) **MuZero**: recompensa, valor, política por paso, K=5, MCTS | árbol sobre acciones discretas | Estado latente "sin semántica" (texto MuZero), entrenado solo por valor/política/recompensa | Juegos por turnos: el rival es otro nodo del árbol; Melee es **simultáneo** (A1; OpenSpiel B22: MCTS estándar excluye nodos simultáneos, DOC catálogo) |
| (d) **DreamerV3**: r̂ (symexp two-hot), `con`, actor-crítico en imaginación H=15 | sin búsqueda en ejecución | Imaginación barata para entrenar política | Imagina con muestreo estocástico del RSSM; el rival entraría como parte del "entorno" igual que en Phillip |

**Decisión (PROP):** (b)-estilo sobre el latente W1-L, con dos variantes:
- **W1-L-frozen (fiel):** encoder+predictor entrenados solo con el objetivo LeWM; cabezas r̂, V̂, eventos sobre
  `sg(z)`. Aísla "¿el latente JEPA contiene lo necesario para puntuar?".
- **W1-L-coupled:** gradiente de r̂/V̂ al encoder (como TD-MPC2/MuZero). Deja de ser LeWM; se reporta aparte.
- (a) como ablación barata; (c)/(d) no como brazos (simultaneidad y entrenamiento en imaginación — ver §6).

Recompensa: la de slippi-ai (daño y stocks, simétrica de suma cero; A2 señala términos de modelado que el valor
hereda). Se aprende `r̂` desde las cabezas de eventos/Δpercent (casi determinista dado el estado predicho) en vez de
una cabeza opaca: menos parámetros y evaluable por campo.

Valor terminal: **V̂(z) aprendido offline sobre datos humanos es el valor de "humano contra humano"**, no el del
planificador: sesgo de política conocido; A2 propone V offline o el valor del PPO de B1. Bajo demora, el valor ve
el estado presente en entrenamiento (Firoiu §4.4; slippi-ai) — información privilegiada a declarar (A2, A8).
Continuación: `cont = 1 − P(terminated)` como en DreamerV3 `con` (`agent.py` L174-177) / TD-MPC2 `termination`
(`world_model.py` L28, `episodic`).

Puntuación de un plan (para A5): `J = Σ_{k<H} γ^k r̂_k · Π cont + γ^H V̂(ẑ_H)`, agregada sobre hipótesis del rival
(§4.3).

---

## 4. El rival

### 4.1 Separación

`p(x_{f+1..f+T} | h_f, u^yo_{f+1..f+T}) = Σ_{u^riv} p_dyn(x | h_f, u^yo, u^riv) · q(u^riv_{f+1..f+T} | h_f, x_{f+1..})`

- **Dinámica conjunta p_dyn**: se entrena con los mandos reales de ambos (training_metadata, A6). Es casi
  determinista (salvo RNG y memoria oculta) y es lo que el simulador hace exactamente.
- **Política del rival q**: se entrena aparte por imitación (BC del rival a su demora de reacción R_riv) sobre la
  historia **visible para un humano**. En bucle cerrado q se evalúa sobre el estado **imaginado**, de modo que
  cada muestra es una trayectoria coherente.
- Littman 1994 (B16, catálogo) formaliza la transición con una acción por jugador; Firoiu §5.2 propone
  exactamente esta separación como trabajo futuro: "With privileged post-facto information of the opponent's
  actions, one could train a model that conditions on both players' actions" (DOC) [A4-006].

### 4.2 Por qué no promediar futuros incompatibles

- Un modelo que no recibe `u^riv` y se entrena con L2 aprende la **media condicional** sobre las acciones del
  rival. Es lo que hace Phillip 2018: `Model.distances` solo usa `current_actions` propias (`model.py` L85, L95-99)
  y la pérdida es L2/CE por componente (paper §4.4); el paper lo dice: "our predictive model ignores the opponent,
  effectively pretending that the opponent is a part of the environment" (§5.2) [A4-007].
- En Melee las alternativas del rival son discretas y mutuamente excluyentes (salta / escuda / ataca). La media
  de posiciones es un estado que no es ninguno; las cabezas categóricas factorizadas dan marginales por campo que
  juntas son inconsistentes (acción "salto" con y de "suelo"); realimentar ese estado medio en un despliegue AR lo
  saca del soporte de la dinámica, y **el valor de la media no es la media del valor** (golpe/fallo es una
  discontinuidad) [INF, A4-015]. Lo mismo para la MSE del latente: predice el embedding medio, que no tiene por
  qué decodificar a un estado posible.
- Por tanto: **muestrear hipótesis discretas y propagar cada una**; agregar en el espacio de la utilidad, nunca en
  el del estado.

### 4.3 Opciones para el planificador (A5 elige; todas con el mismo p_dyn)

| Opción | Implementación | Cuándo tiene sentido | Riesgo |
|---|---|---|---|
| O1 Marginal (diagnóstico) | `u^riv = UNK` | Solo para medir cuánto se pierde al ignorar al rival | Promedia futuros (§4.2); **no se usa para decidir** |
| O2 **K muestras de un prior BC** | K=8 trayectorias del rival muestreadas de q en bucle cerrado; utilidad = media o CVaR_α (α=0,25) | Por defecto | Si q es malo, el plan es malo; la varianza de K pequeño |
| O3 Peor caso sobre un menú | M macro-acciones del rival (esperar, escudo, salto atrás, ataque rápido, agarre…) por bloque; utilidad = min | Situaciones de castigo / "¿es seguro?" (lo que hace `Forced.safe` de melee-brute con su menú, `BRUTE.md`) | Pesimismo excesivo: el rival real no reacciona instantáneamente |
| O3' **Peor caso con reacción** (PROP) | En los primeros `D_yo + 1 + R_riv` frames (A6: R humano ~12-15) las acciones del rival **no pueden depender** de mi decisión de ahora → se muestrean de q (ruido exógeno); el min sobre el menú solo se aplica después | Recomendada para "¿es seguro?" | Requiere fijar R_riv por política rival (bots a 0 frames: Faynt/Reyn, A1 §9) |
| O4 Rival = copia de mi política | q = mi prior BC/política (ditto Fox, que es lo que fuerza el bench: `bench/game.make_agent` fuerza FOX, A1 §3) | Autojuego, evaluación en sim contra sí mismo | Sesgo optimista contra humanos distintos |

Coherencia temporal: una hipótesis es una **secuencia** (o una política en bucle cerrado), no una acción por paso
muestreada independientemente; si no, se generan rivales "temblorosos" imposibles.

### 4.4 Qué es oracle (solo diagnóstico) y regímenes de información

| Elemento | Nivel | Uso permitido |
|---|---|---|
| `u^riv_{f+1..}` reales del log | training_metadata | Teacher forcing de p_dyn; **cota oracle** en evaluación ("con acciones reales del rival") |
| `u^riv_f` (mando ya aplicado, en `GameState.controller_state` del rival) | **Presente en lo que recibe todo agente** (A1 §6.1, CÓD) aunque un humano no lo ve; A6 propone excluirlo | Define dos regímenes: `I_full` (lo incluye; es lo que hoy reciben los agentes del bench salvo bot-writer) e `I_human` (lo excluye, como slippi-ai `embed.py` L463, A2). Todas las métricas se reportan bajo ambos y A8 decide cuál cuenta |
| `frame_pre_random_seed` / snapshot del simulador | simulator_snapshot | Nunca al modelo. Solo para generar verdad de terreno |
| Estado presente bajo demora | training_metadata | Valor/crítico en entrenamiento (Firoiu §4.4); prohibido en inferencia |

**Reconciliación A1↔A6:** no se contradicen. A1 constata que el `GameState` trae el mando del rival del frame
actual (pasado, ya aplicado); A6 propone que no forme parte de `observation`. Para la dinámica, `u^riv_f` es parte
del estado de Markov (flancos del frame f+1); en `I_human` el modelo debe inferirlo de su efecto en `x_f` y eso
añade incertidumbre irreducible al frame siguiente. Es medible (§5.3: diferencia de error `I_full − I_human` a h=1).

---

## 5. Incertidumbre, error acumulado y contrafactuales

### 5.1 Incertidumbre

- **Aleatoria**: las propias cabezas de distribución (two-hot, categóricas) de W0-S; en W1-L, cabezas de campos
  sobre `ẑ` dan la misma lectura.
- **Epistémica**: ensamble de 5 predictores (el mismo número de Q's que usa TD-MPC2, `num_q: 5`, como
  referencia de coste) o 5 cabezas sobre tronco compartido; desacuerdo = varianza de las predicciones por campo
  (continuos) o JS entre categóricas.
- **Rival**: dispersión de la utilidad entre las K hipótesis (O2). Se reporta por separado: no es incertidumbre del
  modelo.
- Uso: penalizar candidatos con desacuerdo alto (`J − β·σ_ens`) y marcar "fuera de soporte" (A6 §7: soporte del
  par (estado, mando) en train).

### 5.2 Métricas por horizonte h ∈ {1, 4, 8, 16, 32} frames

Para cada h, W0-S y W1-L (vía decodificador de campos), contra las tres líneas base triviales, **con IC bootstrap
por partida**:

| Grupo | Métricas |
|---|---|
| Continuos | MAE de `pos` en unidades de juego; % dentro de tolerancia (≤1 u, ≤5 u); MAE de `percent`, `shield`; NLL y cobertura del intervalo 80 % (calibración) |
| Categóricos | Acc. top-1 y NLL de `action` **solo en frames donde cambia** y en total; ECE; acc. de `facing/on_ground/jumps` |
| Contadores | exact-match y MAE de `action_frame`, `hitlag_left`, `hitstun_left` (enmascarado) |
| Eventos | Por tipo (cambio de acción, golpe, escudo, agarre, muerte, reaparición, borde, tech): precisión/recall dentro de una ventana de ±1 y ±3 frames; error de *timing* en frames |
| Coherencia | % de estados predichos inválidos (acción incompatible con `on_ground`, contador fuera de rango) |
| Incertidumbre | AUROC del desacuerdo del ensamble para detectar errores grandes (p. ej. |Δpos| > 5 u o evento perdido) |
| **Relevante para decidir** | Sobre un menú de M candidatos propios desde el mismo estado: acuerdo top-1 del argmax de `J` con el del simulador, correlación de rangos de Spearman, y **regret** en el valor del simulador (§5.4) |

Desgloses obligatorios: (i) rival oracle vs O2 (K muestras) vs O1 marginal; (ii) `I_full` vs `I_human`;
(iii) fase de juego (neutral, en hitstun, fuera del escenario, borde, escudo); (iv) en distribución (replays) vs
contrafactual (§5.4); (v) personaje/escenario reservado (A6 `S_matchup/S_stage`). Las métricas a 1 frame con
acciones del log en replays humanos **no** validan un planificador (A6 §7; A3 §3.2).

### 5.3 Pruebas mínimas en distribución (datos humanos)

1. Curva error-vs-h para cada campo con rival oracle → error de dinámica pura.
2. Misma curva con O2 → coste de la incertidumbre del rival. La diferencia por horizonte es el resultado que
   decide si "dinámica conjunta + q" es útil más allá de ~R_riv frames.
3. `I_full − I_human` a h=1 → valor del mando actual del rival.

### 5.4 Contrafactuales fuera de la distribución humana

Problema: los replays solo contienen las acciones elegidas; un planificador consulta pares (estado, acción) sin
soporte (A6 §7; Firoiu §5.1). Verdad de terreno exacta solo la da el simulador, y **no se puede construir un estado
del simulador desde un `GameState`** (A1 §5.2, CÓD: solo `configure_match`). Consecuencias y alternativas:

| Fuente de estados | Cómo | Cobertura | Límites |
|---|---|---|---|
| **C1 Estados alcanzados en el simulador** | Partidas sim con políticas BC (Faynt-Expert o B0, ambas en ditto) desde `configure_match`; en frames muestreados `checkpoint`, ramificar M secuencias propias × K del rival, `rollback` (melee-brute 4,4/4,5 µs, `BRUTE.md`; `EnvBatch.checkpoint/rollback`, A1 §8). Posiciones guionizadas como `fox.corner` (`fox.py` L75-95) para casos de borde | A demanda, exacta | Distribución de bots, no humana; reglas del simulador (UCF, sin ítems, Stadium congelado) |
| **C2 "Replay-to-reach" de estados humanos** (PROP, sobre código existente) | Reinyectar los mandos **crudos** de un `.slp` en `EnvBatch` con `seed = game.start.random_seed` (exactamente lo que hace `melee_llm/sim/parity.py sim_frames` L41-60); comparar con el `.slp` frame a frame; mientras coincidan, el estado del simulador **es** el estado humano; `checkpoint` y ramificar | Estados humanos reales, incluido el contexto de mandos | Válido solo hasta la primera divergencia de RNG (15/40 partidas sin divergencia, `simulator.md` L53, DOC) → **sesgo de selección** hacia tramos sin eventos aleatorios; exige `.slp` con crudos de ambos sticks, historia completa desde −123 y reglas soportadas (`VALIDATION.md` L49-52, L61-70, DOC) — HAL MDS y parquet de slippi-ai **no** sirven (A6) |
| C2' Validador con RNG grabado | El carril de validación inyecta las observaciones de RNG grabadas y reproduce 36/40 partidas humanas ranked hasta el final (E31, `simulator.md` L55, DOC; `VALIDATION.md` L33-34, L159-163) | Casi todo el corpus admisible | Es una herramienta de validación (`tools/validation/native.c`), no la API RL; si permite guardar estado a mitad y ramificar es **DESC**; tras ramificar, el RNG del simulador corre libre |
| C3 Datos humanos sin simulador | Solo pares (estado, acción humana) | — | No hay verdad contrafactual; solo soporte/desacuerdo como proxy |

Consecuencias que deben reportarse:
- El test contrafactual mide la dinámica **del simulador** (RNG del simulador, reglas UCF). En ramas que consumen
  RNG, el simulador da una verdad válida para el simulador y no para Dolphin; se reportan aparte (§5.5).
- Un modelo entrenado con replays humanos y evaluado en C1 sufre cambio de dominio de **estados**; en C2, solo de
  **acciones** (lo que se quiere medir). C2 es la prueba limpia; C1 la amplía.
- Protocolo (PROP): desde cada estado raíz, menú propio de M=32 secuencias de 8-32 frames (de A5) × K=4 rivales;
  verdad = simulador; métricas de §5.2 + acuerdo de argmax/regret. El conjunto de test contrafactual se fija una vez
  y se congela (sha256) antes de entrenar.

**Test de aliasing / historia mínima** (PROP): en C1/C2, agrupar estados por la clave "look-alike" de melee-brute
(pos/vel a 0,01, acción y frame, hitlag, escudo, facing, saltos; `BRUTE.md`) extendida con los últimos H mandos de
ambos; aplicar el mismo mando y contar con qué frecuencia el siguiente estado difiere (hash exacto `Match.hash`).
Esa frecuencia es el **error irreducible de un modelo que solo ve esa historia**; se elige H como el menor con
frecuencia < 0,1 %. Es la forma más barata de fijar H con verdad exacta.

### 5.5 Gemelos de RNG (PROP)

Reproducir el mismo prefijo de mandos con S semillas iniciales distintas; conservar los gemelos cuyo estado
observable a frame t coincide exactamente con el original (difieren solo en RNG, verificable en
`frame_pre_random_seed`); aplicar idénticas secuencias de mandos y medir la dispersión de resultados. Da la parte
de la varianza atribuible a RNG por tipo de situación, y la cota de error que **ningún** modelo sin RNG puede
bajar. Limitación: la semilla solo se fija al inicio (`configure_match`), no a mitad; no localicé API para
escribir el RNG (DESC).

Nada de §5.4-5.5 es ejecutable en esta máquina (sin ISO; A1, A6).

---

## 6. La pregunta incómoda: con un simulador exacto, ¿cuándo aporta algo un modelo aprendido?

### 6.1 Velocidad (medida local + cifras del autor)

`evidence/A4/checks/predictor_latency.py` → `predictor_latency_result.json` (REP, local_check; CPU compartida, 2
hilos, forward sin gradiente, pesos aleatorios, lote 512 candidatos, pico RSS 0,97 GB):

| Modelo | Parámetros | ms por paso (lote 512) | µs por candidato-paso |
|---|---|---|---|
| MLP 256×3 (cabezas estructuradas) | 0,69 M | 5,0 | 9,8 |
| MLP 512×4 | 1,90 M | 18,4 | 36 |
| ARPredictor d128 L4, ventana 16 | 1,19 M | 401 | 783 |
| ARPredictor tamaño LeWM (d192 L6 16×64 mlp2048), ventana 3 | 10,79 M | 469 | 916 |
| ídem, ventana 16 | 10,79 M | 2.752 | 5.375 |

Simulador (DOC, otra máquina: Ryzen 5950X cargado): 12-15 µs por frame dentro de la búsqueda, 17 µs desde Python,
checkpoint/rollback 4,4/4,5 µs (`BRUTE.md` "How fast"); ~120 k frames/s/núcleo en lote (melee-sim-light README,
A1 §8). Lectura (INF): en CPU un predictor latente tipo LeWM es **50-300× más lento por frame-candidato** que el
simulador incluso contando bloques de 4 frames (916/4 ≈ 229 µs/frame); un MLP estructurado está en el mismo orden
que el simulador, pero es aproximado. **La velocidad no es un argumento en esta plataforma.** En GPU con lotes
grandes y KV-cache la relación puede invertirse — no medido aquí (A7) [A4-025, A4-026].

### 6.2 Condiciones concretas, una a una

| Condición | ¿Aporta un modelo aprendido? | Por qué |
|---|---|---|
| Partida en `--mode sim` con acceso al `World` | **No** para la dinámica | El simulador es exacto y más rápido en CPU. Requiere solo pasar el `World` al agente (A1 §5.2) |
| Partida en Dolphin / bench / netplay | **Sí, en principio**, porque no hay estado del simulador (A1 §5.2) | Pero existe la alternativa **simulador sombra** (PROP): el `GameState` trae los mandos de ambos jugadores en cada frame (A1 §6.1); reproducirlos en el simulador desde la semilla mantiene el estado exacto hasta la primera divergencia de RNG (mismo mecanismo que `sim/parity.py`; 15/40 partidas nunca divergen, DOC). Limitaciones: hace falta el canal crudo de ambos sticks (no reconstruir de procesados, `VALIDATION.md` L52), y el RNG de Dolphin se avanza fuera del juego (`parity.py` L4-5). El nicho del modelo aprendido en Dolphin es **después** de la divergencia |
| Información parcial / sin RNG | Parcial | Un planificador con snapshot "sabe" el RNG: es privilegio (A8). El modelo aprendido sin semilla representa el RNG como ruido de forma natural. Pero el simulador también puede usarse "a ciegas" muestreando gemelos de RNG (§5.5) si se resuelve fijar semillas |
| Demora (predecir el presente) | **Lo necesario es q, no p_dyn** | Con la cola propia conocida, el simulador predice el presente exactamente si conoce los mandos del rival; lo desconocido son los mandos del rival → hace falta un **modelo de política del rival**, que el simulador no da. Firoiu 2018: el predictor ayudó solo con p=d y solo frente a rivales que aprenden (§4.5); slippi-ai lo abandonó y melee-llm recomienda no usarlo (`delay.md` L70) — opiniones de autor, no pruebas |
| Modelo del rival | **Sí** (irreemplazable) | Es una política aprendida; se combina igual de bien con el simulador (S0 + q) que con un modelo aprendido. **Control decisivo para A5/A8: W(p_dyn aprendido + q) vs S0(simulador + mismo q), mismo presupuesto** |
| Diferenciabilidad | Casi nada | Mandos discretos/cuantizados y dinámica discontinua (golpe/fallo); LeWM ofrece `solver/adam.yaml`, pero el gradiente a través de un golpe no informa (INF) |
| Entrenar política en imaginación (Dreamer) | No, mientras el simulador corra | El simulador genera experiencia exacta más rápido en CPU. Excepción estrecha: **arrancar imaginación desde estados humanos a mitad de partida** posteriores a la divergencia de RNG, que el simulador no puede alcanzar (C2) |
| Plataformas sin simulador | Sí | El simulador requiere datos extraídos de una ISO NTSC 1.02, GCC/Linux; take-back y búsqueda solo Linux (A1 §8). Esta máquina no puede ejecutarlo. Un modelo aprendido corre en cualquier sitio (pero se entrena con datos que también derivan del juego) |
| Abstracción temporal | Posible, sin evidencia | Un modelo de bloque/evento salta 4-30 frames por paso; el simulador no. Solo vale si su error a 16-32 frames es aceptable para decidir (métrica de regret §5.2) |
| Representación | Es la pregunta de A3 (B2), no de dinámica | El encoder JEPA puede servir a la política sin usar el predictor |
| Detección de sorpresa | Marginal | LeWM documenta picos de sorpresa ante teletransporte (2603.19312v3 §5.2, DOC); en Melee podría detectar comportamientos inesperados del rival; sin evidencia de valor de control |

**Conclusión de A4 (INF):** el experimento que puede justificar W0/W1 no es "W vs B1", sino **"W(p_dyn aprendido +
q) vs S0(simulador + mismo q)"** con mismo presupuesto en `--mode sim`, y "W vs simulador sombra" en Dolphin. Si W
no supera a S0 en sim (esperable por exactitud y velocidad), su único valor defendible es en Dolphin tras la
divergencia de RNG o en plataformas sin simulador, y hay que medirlo allí. Lo que sí merece inversión con
independencia del resultado es **q (modelo del rival)** y el **test contrafactual C2**.

---

## 7. Orden de trabajo propuesto

1. W0-S en Fox ditto (lo que fuerza el bench, A1 §3), 1-2 escenarios, datos `.slp` reparseados con crudos (A6), H
   por test de aliasing (§5.4) cuando haya ISO; sin ISO, H=8 provisional.
2. q (BC del rival a R_riv) — compartido con A5 como prior.
3. Evaluación §5.2-5.3 en replays (rival oracle / O2 / O1; `I_full` / `I_human`).
4. W1-L-frozen y W1-L-coupled con el encoder de A3 (E1/E2); misma evaluación vía decodificador de campos.
5. Con ISO: C1, C2, gemelos de RNG; regret de decisión vs simulador.
6. S0+q vs W0-S+q vs W1-L+q en sim; simulador sombra vs W en Dolphin.

## 8. Dudas, contradicciones y bloqueos

- **A1:** confirmar si libmelee expone el stick C crudo del rival en `controller_state` (necesario para el
  simulador sombra); `parity.py` lo lee de peppi (`raw_analog_cstick_x`) con `getattr` por si falta (L33-34).
- **A1/A5:** el `World` no llega al agente (A1 §5.2): el brazo S0 y el simulador sombra requieren ese cambio.
- **A6:** la decisión LAST/FIRST para datos de dinámica es LAST (coincido). Frecuencia real de rollback en el
  corpus: DESC.
- **A3:** acordado D=128 (barrido {64…256}), H=16 frames en 4 bloques, acciones de ambos en el predictor en
  entrenamiento (como pidió A3 §8); `UNK` del rival solo diagnóstico.
- **A7:** medir en GPU el ARPredictor con KV-cache; mi medida es CPU, sin caché, servidor compartido.
- **A8:** el oracle de acciones del rival y el `u^riv_f` del `GameState` deben declararse por brazo; el control
  decisivo es W vs S0 con el mismo q.
- **Contradicción con el paquete:** la ficha B03 dice que "CEM busca una meta visual"; el código del repo no
  contiene el CEM (está en `stable_worldmodel`), solo su configuración (CÓD). El paper es inconsistente sobre MPC
  (App. D ejecuta la secuencia completa; §3.2 ejecuta las K primeras), DOC vía WebFetch.
- **Contradicción:** A6 cita en `VALIDATION.md` "entradas restauradas before input edges/timers"; el texto está en
  la sección de entradas CPU (`agent_docs/VALIDATION.md` L156-160), no es una afirmación general sobre humanos.
  La conclusión (el estado de Markov incluye el mando previo) se sostiene igualmente por `BRUTE.md` [A4-003].
