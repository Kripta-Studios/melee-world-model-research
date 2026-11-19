# DESIGN — Arquitecturas para un modelo predictivo aprendido en Melee

Integrador · 2026-11-19 · Fuente de verdad: `decision/DECISION.md`. Este documento la detalla para implementarla y
no cambia la decisión. Detalle por rol: `evidence/A3/REPRESENTATIONS.md`, `evidence/A4/DYNAMICS.md` +
`model_contract.json`, `evidence/A5/PLANNING.md` + `search_budget.json`, `evidence/A6/*.json`,
`evidence/A7/FEASIBILITY.md` + `budget.json`, `evidence/A8/*`. Integración: `evidence/A1/CONTRACT.md` y
`SYSTEM_MAP.md` §5.

**Etiquetas.**
- **SOP** (soportado): código inspeccionado con SHA, o medición local con artefacto.
- **INF** (inferido): deducción sin medir el hecho.
- **PEND** (pendiente): necesita un experimento que nadie ha hecho.
- **PROP** (propuesta): diseño que no está implementado en ningún repositorio.
- **EST**: estimación sin medir.
- **DOC-autor**: cifra publicada por sus autores; está atribuida y no se ha reproducido.

**Nada de este diseño existe en código.** Todo componente nuevo es PROP. Las latencias "medidas" son de modelos proxy
con pesos aleatorios, medidos en el CPU EPYC compartido de este servidor, sin Dolphin corriendo (A7 §3).

Revisiones citadas:
- melee-llm `7e179081c6cbab139d860c998b1452ad3dee047c` (`LLM:`);
- melee-brute HEAD `9662ec973b9e077ff7b0ff89d6db950f53c11653` (`BR:`), con pin del runtime `090e54b048b7d51e82f9f6b551046c2ca8b130c7`;
- libmelee `bce21f09…` (instalado 0.47.6 = `2d63e7ee…`; cuerpo de `__pre_frame` idéntico);
- le-wm `8edfeb336732b5f3ce7b8b210d0ba370a09e2cac`;
- slippi-ai `5ada33e90c6c87fe83a1fb2d1a8105a96fd7b05b`.

---

## 0. Resumen

| | **A. Predictor del presente (ELEGIDA, MVP)** | B. Búsqueda exacta S0 (+ destilación) | C. MPC con dinámica aprendida |
|---|---|---|---|
| Qué decide | Una política BC a 0 frames aplicada al presente *predicho* bajo demora D | argmax/softmax de J sobre N candidatos evaluados con el simulador | argmax de J sobre N candidatos evaluados con W |
| Modelo aprendido en la decisión | W0-S (o W1-L) + q | solo q y V̂ (la dinámica es exacta) | W + q + V̂ |
| Primera puerta de muerte | offline, sin ISO (G1-dyn, G1-q) | con ISO y un cambio en el runner (E4) | E4 + panel de regret (E2) |
| Cuándo se ejecuta | E1 → E3 | E4 | E6, solo si E4 y el panel lo justifican |

Por qué A, tal como fija DECISION §2:
- es la única opción en la que el modelo aprendido actúa en la decisión y cuya primera puerta no necesita ISO;
- no depende de V̂, ni del `World`, ni de cambios en melee-brute;
- tiene un control que la mata limpiamente: el brazo (c), una política entrenada con demora a igual cómputo;
- todo lo que construye es prerrequisito de B y de C.

---

## 1. Lo que un ingeniero debe saber del sistema existente (SOP salvo indicación)

- **El bench solo juega en Dolphin.** `entrants.game_mode` solo devuelve `realtime|fast` (`LLM:bench/entrants.py`
  L189-191). Nunca usa `--mode sim`. El pool puntuado importa además partidas `lockstep` (`bench/imports.py`
  L85-97).
- **Fox ditto obligado.** `bench/game.make_agent` fuerza FOX (`LLM:bench/game.py` L17-28). El fichero tiene 113
  líneas, así que los localizadores L233-244 / L299-320 de A1 son falsos (A8 fila 5; `deliverables/SOURCE_AUDIT.md` §4).
  Escenarios: BF y FD.
- **Ningún modo impone plazo a un agente every-frame.** Con `blocking_input=True` Dolphin espera el mando en
  `fast` y `realtime` (`LLM:runner.py` L208-216). En `realtime`, una partida con fps medio < 50 se marca `slow`
  (`bench/game.py` L14 `MIN_FPS`, `status_of` L107-113). El único plazo duro que existe es el de bot-writer
  (`LLM:botwriter/agent.py` L79 `budget_ms=16.0`, fallback L186-190).
- **Interfaz del agente.**
  - `Agent.begin(gs)` / `Agent.step(gs) -> None`, que escriben el controlador (`LLM:agents/base.py` L32-37).
  - Variante en un venv propio: `BotAgent` (`LLM:bots/agent.py` L69-185) más un módulo `bot_<name>.py` con
    `class Bot` que expone `info()`, `set_steer(d)` y `act(gs, controller, open_loop)` (`LLM:bots/server.py` L97-134).
  - Registro: `players.KINDS` (`LLM:players.py` L25-32) y `Entrant(...)` en `bench/entrants.registry()` (L80-141),
    con `track="both"`.
- **Información.**
  - El `GameState` de libmelee trae el `controller_state` del rival del frame actual, ya aplicado. Es el régimen
    `I_full`; bot-writer es la excepción y lo oculta, `botwriter/agent.py` L6.
  - Pero solo trae el stick principal crudo, el C-stick procesado y un gatillo lógico copiado a L y R
    (`libmelee/melee/console.py` L1145-1212) [A8-003].
  - El agente **no** recibe el `World` (`LLM:sim/runner.py` L47-51).
  - No existe `GameState → estado del simulador`.
- **No hay cola de demora común.** Cada bot implementa la suya (HAL `delay`, Phillip `policy.delay`, slippi-ai
  `DelayedAgent`, `eval_lib.py` L129-140). Una demora D artificial la implementa el propio agente.
- **Alineación de filas** (A6 `timing_contract.json` `row_alignment_in_parsers`). La fila f contiene PostFrame(f)
  y PreFrame(f), y el mando de la fila f ya actuó sobre el estado de esa fila. Modelo de demora (PROP): un mando
  decidido tras ver post(f) se aplica en `f + 1 + D`.

---

## 2. Componentes comunes a A, B y C

### 2.1 Esquema de observación único (corrección A8 K5)

Un **único esquema**, el de A6 §5 sobre `.slp` reparseado con peppi, para **todos** los brazos propios: B0, π0,
W0-S, W1-L, q, V̂ y el brazo (c). Queda prohibido usar el `Game` de slippi-ai para un brazo y el esquema A6 para
otro. El `Game` de slippi-ai no lleva velocidades ni hitstun y trunca `percent` a uint16 (`slippi_db/parse_peppi.py`
L65); su embedding omite action_frame, hitlag y hitstun (`tf/embed.py` L443-447). Faynt queda solo como referencia
externa. **HAL MDS no sirve para dinámica**: le faltan velocidades, `action_state_frame`, hitstun, RNG y sticks crudos
(A6-030).

Campos por jugador y frame (de `evidence/A4/model_contract.json` `inputs`, PROP; el *since* de cada campo, de SPEC
Slippi vía A6):

| Grupo | Campos | Codificación |
|---|---|---|
| Continuos (10) | `pos_x, pos_y`, 5 velocidades (`speed_air_x_self, speed_y_self, speed_x_attack, speed_y_attack, speed_ground_x_self`; ≥ 3.5.0), `percent` (float, sin truncar), `shield`, `dist_to_nearest_ledge` | normalizados con estadísticas de train |
| Relativos | `dx, dy` | ídem |
| Categóricos | `action` (≤ 512), `character` (26), `facing` (2), `on_ground` (2), `jumps_left` (7), `stock` (5), `hurtbox_state` (3), `invulnerable` (2) | embedding |
| Contadores | `action_frame` (0..255), `hitlag_left` (0..63; ≥ 3.8.0), `hitstun_left` (0..127, **enmascarado** fuera de hitstun), `invulnerability_left` | embedding ordinal + escalar |
| Mandos (ambos puertos) | bits mantenidos A, B, X, Y, Z, L, R, D_UP; flancos derivados `b_f ∧ ¬b_{f−1}`; stick principal y C-stick int8 −80..80 crudos (C-stick crudo ≥ 3.17.0); gatillos L/R físicos 0..140 | **16 dims** tras codificar |
| Proyectiles | 4 ranuras: `exists, type, pos_x, pos_y, vel_x, vel_y, owner` | — |
| Escenario | `stage_id`, Randall, plataformas de FoD | — |

Reglas que viajan con el esquema:
- **Copia de rollback LAST.** Las copias FIRST no forman una trayectoria causal (A6 `rollback_policy`).
- **Frames −123..−1 marcados `actionable=false`.**
- **Canonicalización determinista por espejo**: x→−x, vx→−vx y `facing` invertido según la orientación del yo. Es
  una canonicalización y **nunca** una invariancia aprendida: en el juguete de A3 C5b, las vistas espejo bajan el
  probe de `facing` a 0,69 y las de fase bajan el R² de fase a 0,68.
- **Política para campos ausentes**: el `.slp` que no traiga un campo se excluye o va a un brazo `partial_schema`
  declarado. Gate de E0: ≥ 95 % de partidas con velocidades, hitstun y `action_state_frame` (DECISION §3).
- **Historia H.** Provisionalmente 16 frames para el encoder común (DECISION §2). A4 proponía H=8 para W0-S. H se
  fija con el test de aliasing de E2 (A4 §5.4): el menor H con frecuencia de divergencia de look-alikes < 0,1 %.
  Mientras no exista ese test, se usa **el mismo H en todos los brazos**.

### 2.2 Regímenes de información y reloj (A8 `EXPERIMENT_PLAN.md` §0.2-0.3)

- **Regímenes.**
  - `I_full` (primario): incluye `u^riv_f` del `GameState`.
  - `I_human` (secundario, **obligatorio** en todo brazo causal): sin `u^riv_f`, que pasa a ser una variable latente.
  - `PRIV`: snapshot y RNG; solo para S0 y S0-shadow, y siempre como cota.
  - `ORACLE`: mandos futuros reales del rival; solo como diagnóstico offline.
- **Nunca entran como entrada en inferencia**: `u^riv_{f+1..}` reales, `random_seed`, el snapshot y `x_{f+1..}`
  (`model_contract.json` `never_in_input`).
- **Relojes.** `RT-strict` (envoltorio con plazo `C_rt` y fallback L1→L2→L3), `RT-slow` (sin plazo; se mide la
  latencia) y `untimed`. Se reportan por separado y nunca se reclasifican.

### 2.3 Rival: separación dinámica / política (A4 §4)

`p(x_{f+1..f+T} | h_f, u^yo) = Σ_{u^riv} p_dyn(x | h_f, u^yo, u^riv) · q(u^riv | historia visible)`.

- **`p_dyn`** se entrena con los mandos reales de ambos jugadores (teacher forcing).
- **`q`** es un BC del rival a su demora de reacción `R_opp` (por defecto 12 para humanos y 0 para bots a 0 frames
  como Faynt o Reyn; `model_contract.json` `R_opp_frames_default`). Se evalúa en **bucle cerrado sobre el estado
  imaginado**: cada muestra es una secuencia coherente, no un rival "tembloroso".
- **Agregación.** Se agrega en el espacio de la utilidad o de la acción, **nunca promediando estados**. La media de
  futuros incompatibles da estados imposibles y "el valor de la media no es la media del valor" (A4 §4.2, INF).
  Phillip 2018 promedia porque ignora al rival (`phillip/model.py` L84-98, SOP).
- **Lazo abierto.** Solo es válido dentro de la ventana de reacción `D_yo + 1 + R_opp`: ahí las acciones del rival
  no pueden depender de mi decisión actual (A4-016). Contra bots a 0 frames hace falta q en lazo cerrado, lo que
  duplica el coste por paso (A5 §2.3).
- **Hipótesis.** K = 4 en tiempo real y K = 8 en `untimed`. Las mismas K semillas `hash(schedule_id, frame)` en
  todos los brazos. El contrato de A4 sugería K = 8 por defecto; DECISION fija K = 4 para A.

---

## 3. Arquitectura A — predictor del presente bajo demora (ELEGIDA)

### 3.1 Flujo por frame (PROP)

```
Frame f (agente con demora D):
  gs_f ──► featurizar (esquema §2.1, régimen I_full|I_human) ──► historia h_f (H frames)
  cola propia comprometida u^yo_{f+1..f+D} (ya enviada; conocida)
  q muestrea K hipótesis u^riv,k_{f+1..f+D} (bucle cerrado sobre x̂^k, o lazo abierto si D+1 ≤ ventana de reacción)
  W0-S despliega D(+1) pasos de 1 frame por hipótesis ──► x̂^k_{f+D}, k=1..K       [K×(D+1) pasos]
  π0 (BC a 0 frames) sobre cada x̂^k ──► p_k(a)
  p(a) = (1/K) Σ_k p_k(a)   (agregación en espacio de acción; ablación: hipótesis más probable)
  a* = muestreo o argmax ──► se encola para aplicarse en f+1+D
  plazo C_rt vencido ──► L1: última p(a) parcial · L2: π0(observación envejecida) · L3: repetir mando
```

- **Aplicación del mando.** La aplicación efectiva en Dolphin no está instrumentada (A1 §9, DESC). Se registra
  `applied_frame` como inferido (`measured=false`) hasta medirlo.
- **Agregación sobre K.** DECISION fija "K=4 hipótesis muestreadas, nunca la media", sin decir cómo se agrega en la
  acción. La mezcla de distribuciones de π0 es una **PROP del integrador**, coherente con esa regla porque agrega en
  el espacio de la acción y no en el del estado.

### 3.2 Encoder E (PROP; A3 §4, A4 §2.3)

- **Arquitectura.** Embeddings por campo → transformer de entidades (2 jugadores + 4 proyectiles) por frame → GRU o
  transformer causal sobre H. Tamaño de 0,5–2 M (DECISION: ~1–2 M).
- **El mismo módulo E sirve a todos los brazos** que lo usan (π0, W0-S, W1-L, q, V̂, E0/E0b/E1/E1-S). Solo cambian
  la inicialización y el objetivo.
- **Contrato**: `encode(history: FrameHistory[B, H]) -> ModelState`.
  - W0-S: buffer estructurado `(B, H, fields)` más mandos.
  - W1-L: `z (B, H/k, D)` más los mandos crudos del último bloque.

### 3.3 Dinámica W0-S (estructurada; brazo principal de A)

Paso de 1 frame: `h_f, u^yo_{f+1}, u^riv_{f+1} → x_{f+1}`. RNG fuera de la entrada: los campos afectados por azar
son aleatorios en las cabezas.

| Campo | Cabeza | Pérdida |
|---|---|---|
| `action` | categórica 512 + binaria "cambia" | CE (+BCE), peso ×w en frames de cambio |
| `facing, on_ground, invulnerable, hurtbox` | Bernoulli / categórica | BCE / CE |
| `jumps_left, stock` | categórica | CE |
| `action_frame, hitlag_left, hitstun_left` | modo {continúa ±1, reinicia, cero} + valor de reinicio (análogo a la compuerta *forget* de Phillip, `model.py` L53-60) | CE |
| `Δpos`, velocidades | two-hot sobre bins symlog (estilo DreamerV3 `symexp_twohot`); ablación: gaussiana con log-escala por campo (HAL `StateHead`) | CE / NLL |
| `pos` absoluta | activada por *teleport* (muerte, reaparición, agarre de borde) | NLL |
| `Δpercent` | categórica 0..60 por bins | CE |
| `shield` | two-hot | CE |
| eventos (12) | multi-etiqueta: cambio de acción yo/riv, golpe a yo/riv, escudo golpeado, agarre, muerte yo/riv, reaparición, agarre de borde, tech, rotura de escudo | BCE |

- **Ponderación**: la NLL de cada campo se normaliza por la NLL de un suelo trivial en validación (alternativa:
  log-escala aprendida).
- **Máscaras**: el jugador muerto no aporta pérdida de pos/vel, y `hitstun_left` se enmascara fuera de hitstun.
- **Multihorizonte, con los dos modos obligatorios.**
  - (i) AR a 1 frame con pérdida de despliegue de 8 pasos y pesos ρ^t, ρ = 0,5 (TD-MPC2 `config.yaml` `rho`),
    realimentando categóricos muestreados y la media two-hot, con *scheduled sampling*.
  - (ii) Cabezas directas a offsets {1, 4, 8, 16, 32}.
- **Suelos triviales que debe batir**: persistencia, velocidad constante, la acción siguiente mayoritaria dada
  (acción, action_frame) y acciones barajadas.
- **Incertidumbre.** Ensamble de 5 (o 5 cabezas sobre un tronco compartido); el desacuerdo se mide con la varianza
  (continuos) o JS (categóricos), y se marca `out_of_support`. En A solo es diagnóstico y fallback: la política no
  usa J.

### 3.4 Dinámica W1-L (latente tipo LeWM; ablación de A) — A4 §3

| Elemento | Valor | Etiqueta |
|---|---|---|
| Objetivo | `MSE(ẑ_{t+1}, z_{t+1}) + λ·SIGReg(z)` por paso, **sin stop-grad ni EMA** (`le-wm/train.py` L34-41: `tgt_emb = emb[:, n_preds:]` sin `detach`) | FIEL, SOP |
| SIGReg | Epps–Pulley sobre M proyecciones aleatorias renovadas en cada llamada, 17 nodos en [0, 3] (`le-wm/module.py` L10-36). λ = 0,09 (barrido {0,01; 0,03; 0,09; 0,2; 0,5}); M = 1024 por defecto | FIEL, SOP |
| Predictor | `ARPredictor` causal con `ConditionalBlock` AdaLN-zero (`module.py` L244-285, L88-111). d = 128, profundidad 4, 8 cabezas × 16, mlp 512 = **1.186.816 parámetros** (medido); brazo grande tamaño LeWM de 10.788.096 | FIEL (estructura) / MOD (tamaño) |
| Proyector | MLP con BatchNorm | FIEL |
| Encoder | E de estado (§3.2), no ViT | MOD |
| Paso | bloque de k = 4 frames con los 4 mandos de ambos concatenados (como `frameskip`, `train.py` L68); ablación k ∈ {1, 2, 4, 8} | MOD |
| Historia | 4 bloques × 4 frames = 16 frames | MOD |
| Acción | `c_t = Emb_yo(u^yo_bloque) + Emb_riv(u^riv_bloque) + Emb_rol`; `UNK` del rival con p = 0,25 **solo** para el diagnóstico marginal | MOD |
| Pérdida temporal | 1 paso con teacher forcing + despliegue AR de 2–4 bloques (estilo V-JEPA 2-AC `auto_steps`) | MOD |
| Cabezas | decodificador de campos sobre `sg(ẑ)`, **solo para medir** y para alimentar π0 en el brazo (b1) | MOD |
| D latente | 128 (barrido {64, 128, 192, 256}); riesgo de baja dimensión intrínseca (A3 §1.5) | MOD |
| Split | por partida (`evidence/A6/split_plan.json`) y no por ventanas (`train.py` L73-76) | MOD (corrección de fuga) |

- **En el brazo (b1)**, el presente predicho por W1-L es la decodificación de campos de `ẑ_{f+D}` sobre `sg(ẑ)`. Así
  π0 recibe la misma entrada que en (b0).
- **Corrección A8 (K2): el transformer se midió sin KV-cache.** La cifra tx-1M K16·T8 de 23 ms p99 recodifica la
  ventana en cada paso (A7 §3.1). Es un artefacto de implementación. Reglas:
  - W1-L **transformer** se usa en `untimed` (E1, E3 en sim).
  - Antes de sustituirlo por GRU para `RT-strict`, se mide con KV-cache (hueco G-08, local en CPU).
  - Si se pasa a GRU, la etiqueta es "W1-L-GRU" y W1−W0 mide "predictor + arquitectura", ya no LeWM.
- **Coste de SIGReg en CPU** (SOP, A7 §3.3; A3 C3). Escala con T·N·M·17 operaciones trigonométricas, sin depender
  del tamaño del encoder: 135 ms fwd+bwd con 1 hilo a T·N = 5·64 y M = 1024. Es el 83 % del paso de entrenamiento de
  MLP-1M y el 72 % del de GRU-1M. Bajar M a 256–512 es un cambio de configuración declarado. En GPU no se ha medido.

### 3.5 Modelo del rival q (PROP; pieza crítica de A)

- **Entrada**: historia visible para un humano (esquema §2.1). En `I_full` incluye `u^riv_f` como dato pasado.
- **Salida**: distribución factorizada del mando del rival en `f+1`, con el mismo códec que π0.
- **Entrenamiento**: BC del rival a `R_opp` sobre el split train, con los mismos datos y el mismo encoder.
- **Muestreo**: autorregresivo sobre el estado imaginado de W0-S; K secuencias.
- **Métricas que deciden G1-q**: NLL frente a la marginal, y acierto de la acción del rival en frames de cambio a
  h = D+1 frente al mejor suelo (para D = 6 y D = 12).

### 3.6 V̂ (solo diagnóstico en A)

- **Entrenamiento**: V̂(x) sobre el estado estructurado, con la recompensa de slippi-ai (stocks + daño, suma cero,
  semivida de 8 s ⇒ γ = 0,5^(1/480) = 0,998557) **sin** términos de modelado.
- **Sesgo declarado**: es un valor "humano contra humano" (A4 §3.3). En entrenamiento con demora, ver el presente es
  un privilegio declarado (Firoiu §4.4).
- **Uso**: A no lo usa para decidir. Se entrena porque B y C lo necesitan, y se evalúan su calibración (ECE) y su
  ranking.

### 3.7 Política π0 y brazos de control de A (E3)

| Brazo | Política | Entrada en el frame f con demora D | Qué aísla |
|---|---|---|---|
| (a) | π0, BC a 0 frames | observación envejecida `x_f` | suelo: ignorar la demora |
| (b0) | el mismo π0 | presente predicho por W0-S + q (K = 4) | valor del predictor estructurado |
| (b1) | el mismo π0 | presente predicho por W1-L (solo si pasó G1-jepa) | latente frente a estructurado |
| (c) | π_delay, receta slippi-ai: estado t + cola propia comprometida, predice t+D+1 (`slippi_ai/data.py` `delayed_frames` L267-326; `DelayedAgent`) | `x_f` + cola | **control que mata A** a igual cómputo total |
| (d) | π0 con D = 0 | `x_f` sin demora | techo |

- **π0**: el BC propio sobre E, con la cabeza de mando factorizada (botones × stick × gatillo) y el vocabulario
  congelado en E0. Bucle supervisado de MIMIC `3691f534` (MIT).
- **Igual cómputo total en (c) frente a (b0)**: los FLOPs de entrenamiento de π0 + W0-S + q se igualan con pasos
  extra de π_delay. Se reportan a igual frames y a igual cómputo.

### 3.8 Interfaz de cada componente → símbolo real

| Componente | Símbolo real que se reutiliza o se toca | Estado |
|---|---|---|
| Lectura de `.slp` | `peppi_py` (no instalado); referencias de alineación: slippi-ai `slippi_db/parse_peppi.py` L64-119, HAL `hal/data/extract.py` L205-238 | parser nuevo PROP; referencias SOP |
| Split y deduplicación | `evidence/A6/split_plan.json`: sha1 del `.slp`; `bucket = int(sha256('A6-split-v1\|'+sha1)[:8],16)/2^32` | PROP (véase la nota de proporciones en EXPERIMENT_PLAN §5) |
| Encoder / W0-S / q / π0 / V̂ | ninguno existe; se implementan en torch | PROP |
| W1-L | `SIGReg`, `ARPredictor`, `ConditionalBlock`, `Embedder` de `le-wm/module.py` (L10-36, L244-285, L88-111, L189-214) y la pérdida de `train.py` L17-45. Requiere `einops`; A7 extrajo `SIGReg` con `ast` | reutilizar SOP (MIT) |
| Brazo (c) | slippi-ai `data.py` `delayed_frames` L267-326 y `eval_lib.py` L129-140 (receta, no su parser) | reutilizar SOP (MIT) |
| Agente | `PresentPredictorAgent(Agent)` en `melee_llm/agents/`, con el trabajo en `begin(gs)`/`step(gs)` (`agents/base.py` L32-37). Si necesita torch en un venv propio: `BotAgent` + `bots/bot_wm.py` con `class Bot` (`info`, `set_steer`, `act`) según `bots/server.py` L97-134 | clase nueva PROP; interfaz SOP |
| Registro | `players.KINDS` L25-32; `bench/entrants.registry()` L80-141 con `track="both"` (y `gpu=True` si usa CUDA) | punto SOP |
| Régimen `I_human` | filtrar `gs.players[rival].controller_state` antes de featurizar (patrón bot-writer, `botwriter/agent.py` L6) | PROP |
| Cola de demora D | interna al agente; fallback neutral al inicio (patrón `dummy_sample_outputs` de slippi-ai, `eval_lib.py` L138-139) | PROP |
| Plazo `RT-strict` | patrón `budget_ms` de bot-writer (`botwriter/agent.py` L79, L186-190) | PROP sobre patrón SOP |
| Trazas | `time.perf_counter_ns()`; `BotAgent.latency()` (`bots/agent.py` L167-175); `console.processingtime` (libmelee; verificar en 0.47.6); campos de `06_EXPERIMENT_PROTOCOL.md` (`obs_frame … applied_ts_ns`) | PROP |
| Lo que A **no** toca | runner, scheduler, melee-brute, `sim/runner.py` | — |

### 3.9 Presupuesto de latencia (medido por A7; extrapolación para A marcada)

Medido (SOP, A7 §3; proxies MLP/GRU/TX, pesos aleatorios, fp32, eager, `nice 10`, load 2,6–7,7, **sin Dolphin**):

| Medición | p99 (p50) |
|---|---|
| Paso de predictor MLP-1M, 1 hilo, batch 1 / 16 | 0,165 (0,068) / 0,397 (0,258) ms |
| Paso de predictor GRU-1M, 1 hilo, batch 1 / 16 | 0,081 / 0,262 ms |
| Encoder MLP-1M, H = 32, batch 1, 1 hilo | 1,05 (0,074) ms |
| Decisión MPC proxy MLP-1M K16·T8, 1 hilo | **2,8 (2,3) ms**: la cifra que cita DECISION |
| GRU-1M K64·T16, 1 hilo | 15,3 (14,0) ms |
| TX-1M K16·T8, 1 hilo, **sin KV-cache** | 23,3 (21,5) ms |
| Con 3 hilos | medianas 1,2–2× mejores, colas peores por contención; usar 1–2 hilos fijos |

Coste fijo del bucle de Dolphin, documentado por el autor en otra máquina (5950X con carga): ≈ 3,3 ms/frame
(`LLM:docs/performance.md` L52). Queda **≈ 13 ms** para el agente. Presupuesto de diseño de A7: **10 ms p99 en
Dolphin** y 16 ms en sim/fast con plazo.

**Estimación para A** (INF del integrador sobre las tablas de A7). Coste ≈ `enc + K·(D+1)` pasos a batch K = 4,
más π0 sobre K estados:

| D | Lazo abierto (rival humano, D+1 ≤ ventana) | q en lazo cerrado (rival bot a 0 frames) |
|---|---|---|
| 6 | ≈ 2–4 ms | ≈ 3–7 ms |
| 12 | ≈ 3–6 ms | ≈ 4–12 ms |
| 18 | ≈ 4–9 ms | ≈ 6–17 ms ⇒ **puede no caber** en 10 ms |

Cotas usadas: p99 por paso entre 0,165 y 0,40 ms, más el encoder, más π0. **Corrección a DECISION §0/§1**: la cifra
"2,8 ms p99" corresponde a la decisión MPC proxy K16·T8, que equivale a D ≈ 7 con K = 16. No es el predictor del
presente con la arquitectura real de W0-S, ni con D = 12–18, ni con q en lazo cerrado, ni con Dolphin y el rival
corriendo en las mismas 4 vCPU. La conclusión "cabe en RT-strict" sigue en pie para D ≤ 12 con rival humano (INF),
y es **PEND** para D = 18 contra bots a 0 frames. Se mide en E0 (banco local, arquitectura real) y en E3 (con Dolphin).

### 3.10 Contrato completo de A (PROP; extiende `evidence/A4/model_contract.json`)

```
present.predict(
  history: FrameHistory[B, H],              # esquema §2.1, ambos puertos, régimen aplicado
  own_queue: Tensor[B, D, 16],              # mandos propios ya comprometidos f+1..f+D
  D: int,                                   # demora de decisión (6 | 12 | 18)
  K: int = 4,                               # hipótesis del rival (8 en untimed)
  opponent: OpponentPolicy | Tensor[B,K,D,16] | 'UNK',   # 'UNK' = solo diagnóstico O1
  regime: 'I_full' | 'I_human',
  seed: (schedule_id, frame)                # números aleatorios comunes entre brazos
) -> PresentPrediction {
  fields: dict[campo -> distribución [B, K, ...]] en f+D,   # W1-L: vía cabezas sobre sg(ẑ)
  sample: x̂ [B, K, fields],                                # lo que consume π0
  ensemble_std: [B, K, n_fields], out_of_support: [B],
  diagnostics: {compute_ms, steps=K*(D+1), q_closed_loop: bool, oracle_used: false, regime}
}
policy.act(x̂: [B, K, fields]) -> mixture p(a) -> a*  (se aplica en f+1+D)
```

Invariantes:
- (i) `oracle_used` es siempre falso en juego.
- (ii) Ningún campo de `never_in_input` entra.
- (iii) El forward exportado de π0 no contiene parámetros de W ni de q en los brazos (a), (c) y (d); se comprueba
  contando parámetros.
- (iv) Mismas semillas de muestreo en todos los brazos.
- (v) Fallback registrado por frame.

### 3.11 Límites de A (lo que no puede afirmar)

- **Solo aporta con demora D > 0.** Con D = 0 coincide con (d). Si al usuario solo le importa el bench a 0 frames
  (decisión de usuario n.º 4), E3 pierde sentido.
- **No es planificación.** Un resultado positivo dice "predecir el presente ayuda bajo demora"; no dice "un world
  model ayuda a buscar".
- **El valor está en q tanto como en `p_dyn`.** Con la cola propia conocida, lo desconocido es el mando del rival
  (A4 §6.2). El simulador predeciría el presente exactamente si conociera esos mandos, así que A no demuestra que la
  dinámica *aprendida* sea necesaria. Una variante S0+q del presente en sim sería la cota (no está en DECISION; se
  deja como diagnóstico opcional).
- **Riesgo de deriva AR.** Con D = 18 se despliegan 19 pasos. Se controla con el error de "predecir el presente"
  por D en E1.
- **Evidencia previa débil en ambos sentidos.**
  - A favor: At Human Speed, pero confundido por 3 frente a 10 días de entrenamiento, 6–8 partidas y un predictor
    que ignora al rival (A8-004).
  - En contra: que "basta entrenar con demora" es opinión de autor (`LLM:docs/delay.md` L70).

### 3.12 Qué es y qué no es JEPA / LeWorldModel en A

- **Es LeWM-like solo W1-L.** Tiene predicción del siguiente embedding condicionada a acciones, SIGReg sin stop-grad
  ni EMA y la pérdida `pred + λ·sigreg`.
- **No lo son**: W0-S (regresión/clasificación de estado explícito), q (una política), V̂ y π0/BC. I-JEPA y LeJEPA no
  temporales quedan fuera, porque sus vistas por aumento borran información de control (A3 §3.1).
- **Regla de nombre.** Si W1-L ≤ W0-S (G1-jepa) y E1 ≤ E1-S (G1-rep), lo que sobrevive se llama "modelo predictivo
  aprendido", no JEPA.

Desviaciones respecto a LeWM, etiquetadas:

| # | Desviación | Etiqueta | Por qué |
|---|---|---|---|
| L1 | Encoder de estado estructurado en vez de ViT sobre píxeles | MOD | No hay píxeles útiles ni pesos JEPA reutilizables (A3 §5) |
| L2 | Acciones de dos jugadores y rol | MOD | Juego simultáneo de dos agentes |
| L3 | Hipótesis muestreadas del rival; LeWM es determinista | MOD | Futuros incompatibles (A4 §4.2) |
| L4 | Sin planificación por distancia a un embedding meta (`jepa.py` L112-126); en A no hay planificación | MOD (central) | En Melee no hay estado meta |
| L5 | Decodificador de campos sobre `sg(ẑ)` (en LeWM solo para visualizar) | MOD | Medir error por campo y alimentar π0 en (b1) |
| L6 | Historia de 4 bloques × 4 frames, frente a 3 pasos | MOD | Memoria de mandos no Markov (`BR:BRUTE.md` L74-80) |
| L7 | Despliegue AR de 2–4 bloques en la pérdida; LeWM solo usa teacher forcing a 1 paso | MOD | Despliegues de D+1 frames |
| L8 | Split por partida; LeWM parte por ventanas | MOD (corrección) | Fuga entre partidas |
| L9 | Tamaño ≈ 1,2 M frente a ≈ 10,8 M de predictor | MOD | Presupuesto de CPU |
| L10 | Núcleo GRU para RT, si llega a hacer falta | MOD fuerte: deja de ser LeWM | Latencia; antes se mide KV-cache |
| L11 | M de SIGReg = 256–512, si se baja | MOD de configuración declarada | Coste en CPU |

---

## 4. Arquitectura B — búsqueda exacta S0 (+ destilación); etapa E4 (PROP sobre SOP)

| Componente | Detalle |
|---|---|
| Encoder / prior | Faynt-10M-Expert (solo en `untimed`; 8,1/10,3/11,5 ms p50/p95/p99 en CPU de 8 hilos, `LLM:docs/bots.md` L53, DOC-autor) o el B0 propio |
| Dinámica | melee-brute exacta: `EnvBatch.checkpoint/rollback` (`BR:melee_sim/env_batch.py` L428-499) o `Match.checkpoint/rollback/branch/hash` (`BR:melee_brute/match.py` L113-138). 12–15 µs/frame en búsqueda y 17 µs desde Python; checkpoint/rollback 4,4/4,5 µs (`BRUTE.md` L100-106, DOC-autor en un 5950X con carga 15–35). Por la ruta `World` + `StateBuilder` cuesta ≈ 0,35 ms/frame (`LLM:docs/simulator.md` L65) |
| Candidatos | N = 16 = 8 del prior + 8 del menú del estado (`BR:fox.py` L46-72 `MOVES1/MENUS1`, más `nash.py` `MOVES` L35-48); "wait" siempre presente; warm start desplazado |
| Rival | q = copia del prior (O4, ditto) o BC del rival; K = 4 |
| Horizonte | T = 16 frames: `[cola D] + [bloque de decisión de 4] + [continuación]`; T ≥ D+4 |
| Objetivo | `J = Σ γ^t r_t Π cont + γ^T V̂(x_T)`; `J_total = λ_b s0(c) + λ_r mean_k J`. Con γ^32 = 0,955, J ≈ V̂ (A5-030) |
| Selección | argmax (principal); softmax τ_sel como ablación de explotabilidad |
| Controles | P0-Q (mismas propuestas con Q̂ sin rollout), S0-Vperm (V̂ permutado entre candidatos) y S0-MC (sin V̂: rollouts de ambos priors hasta T = 120–240 con retorno Monte Carlo) |
| Información | **PRIV**: snapshot, RNG y mando actual del rival. Solo es equiparable en `I_full`; en `I_human` S0 no es ejecutable |
| Cambio necesario | `LLM:sim/runner.py` L47-53: pasar `World` y fijar/registrar la semilla (`runner.play` no reenvía `seed`, L200-202). Elegir **una** revisión de melee-brute (HEAD `9662ec97` o el pin `090e54b0`, que no tiene `hitlag_left`) |
| Destilación | S-teach: política entrenada con etiquetas de búsqueda offline (`LLM:docs/tas.md` L97 "search at training time"). Sin evidencia en Melee |

S0 es la cota superior de cualquier W **a igual conteo**, candidatos, q y V̂ (INF, lógica). **No** lo es a igual
tiempo ni dice nada del bench, que se juega en Dolphin.

## 5. Arquitectura C — MPC con dinámica aprendida; etapa E6

- **Planificador y controles.** El mismo planificador que B (N = 16, K = 4, T = 16, random shooting con prior + menú,
  una iteración). Cambia la fuente de dinámica: W0-S, o W1-L con V̂ sobre los campos decodificados.
- **Controles adicionales**:
  - W-persist (x̂_T = x_f; con V̂ fijo colapsa a P0, así que sirve de prueba de implementación);
  - W-shuffle (secuencias permutadas).
- **Penalización.** `J − β·σ_ens`; `out_of_support` descarta el candidato.
- **Qué cabe en esta CPU** (SOP, A7 §4.1, 1 hilo, 16 ms): GRU-1M K16·T53 / K64·T17; MLP-1M K16·T36. A 5M solo
  K16·T7–8; a 15M nada. Son ~1.000 evaluaciones por decisión, frente a 45.000 del CEM de LeWM y ~9.600 del MPPI de
  TD-MPC2. Con un prior aprendido hay que restar su coste.
- **GPU.** Sin medir (A7 §4.1, EST): 10⁴–10⁵ evaluaciones por decisión con CUDA graphs.
- **Se reabre solo si** E4 es positiva y regret_W < regret_P0 en el panel de E2 (DECISION §2).

## 6. Correcciones de A8 incorporadas en este diseño

| Corrección | Dónde se aplica |
|---|---|
| **A4-027 FALSA tal como está escrita.** El `GameState` no trae C-stick crudo, gatillos físicos ni semilla, así que una sombra **no** puede alimentarse de él. Versión corregida (G01 §4): es posible desde el flujo Slippi crudo (`ConsoleTap`, `LLM:bots/agent.py` L25-56; Frame Start 0x5 ≥ 2.2.0, C-stick crudo ≥ 3.17.0, gatillos físicos), pero exige ampliar la API C/Python de melee-brute (semilla por frame y eventos de escenario: hoy `batch.c` L324-326 pasa `match->random_seed` y `no_stage_events`) y un decodificador en vivo. No se usa la conversión de `parity.py` L62-71, que reconstruye el C-stick; la correcta es `tools/validation/native.c` L1025-1075 | §1, §2.1; E2/E5 del plan |
| **Transformer sin KV-cache** (K2) | §3.4: transformer en `untimed`; KV-cache antes de pasar a GRU; GRU = cambio de arquitectura |
| **Esquema de observación único** (K5) | §2.1 |
| **Velocidad modelo/simulador sin medir en la misma máquina** (fila 9, K7) | No se usa como argumento de diseño (§4, §5) |
| **15/40 partidas sin divergencia son de bots del autor** (fila 24) | No se usa como cobertura de estados humanos |
| SIGReg domina en CPU (K1) | §3.4 |
| Faynt-10M no cabe como prior en RT en CPU (K3) | §4 (solo en `untimed`) |

## 7. Riesgos de diseño abiertos

- **R1.** q de mala calidad hace inútil A sea cual sea la dinámica (lo detecta G1-q).
- **R2.** El latente "gaussianiza" la información del rival si en algún régimen no recibe `u^riv` (A3 §1.5). Se
  comprueba con probes de campos del rival.
- **R3.** El corpus ranked es anónimo: hay fuga por set inevitable (A6-015). `S_game` mide "partidas no vistas de la
  misma población".
- **R4.** Melee-brute tiene dos revisiones (HEAD y pin), y la granja usa un checkout `MELEE_SIM` de revisión no
  registrada (G-13).
- **R5.** El presupuesto RT es incierto con Dolphin y el rival en 4 vCPU (§3.9).
