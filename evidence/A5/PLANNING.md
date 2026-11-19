# A5 — Planificación y control: diseño concreto

Agente A5 · 2026-11-19 · Escribe solo en `evidence/A5/`. Etiquetas: **DOC** = DOCUMENTADO_POR_AUTOR, **CÓD** =
INSPECCIONADO_EN_CODIGO, **REP** = REPRODUCIDO (medición local de A4/A7, no mía), **INF** = INFERENCIA, **PROP** =
PROPUESTA, **DESC** = DESCONOCIDO. `[A5-xxx]` remite a `claims.jsonl`. Presupuestos y fórmulas: `search_budget.json`.

Construyo sobre A4 (`DYNAMICS.md`, `model_contract.json`), A1 (`SYSTEM_MAP.md`, `CONTRACT.md`), A2 (`BASELINES.md`),
A6 (`timing_contract.json`) y las mediciones de A7 (`A7/measurements/summary.json`, sha256 `6fed94ae…d512`;
`FEASIBILITY.md` aún es un esqueleto). No repito lo que ya fijaron: lo cito.

| Fuente | Revisión | Qué leí |
|---|---|---|
| mateo19182/melee-brute | `9662ec973b9e077ff7b0ff89d6db950f53c11653` | `BRUTE.md` (153 l.), `melee_brute/search.py` (`best` L35-52, `improve` L55-90, `Rules` L122-193, `Forced` L232-323, `solve` L344-421), `fox.py` (menús L12-72), `corpus.py` L21-31, `src/runtime/brute.c` (`play` L580-620, `options` L629-662) |
| mateo19182/melee-llm | `7e179081c6cbab139d860c998b1452ad3dee047c` (el catálogo A36 cita `2bf8b0eb…`; A1 verificó que entre ambas no cambia `optimal-play.md`) | `docs/optimal-play.md` (686 l., §7, §10-15), `docs/simulator.md`, `docs/delay.md`, `docs/tas.md` §6-7, `docs/bots.md` L53, `melee_llm/solver/{nash,matrix,takeback}.py` cabeceras; búsqueda de usos de take-back en `melee_llm/`, `train/`, `scripts/` |
| nicklashansen/tdmpc2 | `332f19e4aba4bffe2dc736f45ea7f7bdc585903a` | `tdmpc2/tdmpc2.py` `_estimate_value` L122-136, `_plan` L138-206; `config.yaml` L34-42 |
| lucas-maes/le-wm | `8edfeb336732b5f3ce7b8b210d0ba370a09e2cac` | `config/eval/solver/cem.yaml`, `config/eval/pusht.yaml`, `eval.py` L53-96 |
| MuZero arXiv 1911.08265v2 | PDF vía WebFetch, sha256 `25588ee1…445c`, texto con pdftotext | §3, Results, Fig. 3, Apéndices B y H (líneas citadas del texto extraído) |
| OpenSpiel | `master` (raw GitHub, 2026-11-19, sin SHA fijado) | `open_spiel/examples/mcts_example.cc`, comprobación de nodos simultáneos |

---

## 0. Resumen (lo que cambia o precisa el paquete)

1. **Nadie ha planificado con el simulador al jugar una partida.** En melee-llm toda la búsqueda (`force`, `nash`,
   `fortress`, `squeeze`) es análisis de posiciones u "optimal play" offline; ningún `Agent` ni la granja usa
   take-back (búsqueda de `takeback|melee_brute|Forced(|.checkpoint(` fuera de `melee_llm/solver/`: solo
   `scripts/solver_probes/`, CÓD). El autor lo dice: "search at training time, not at play time, the thing a 16 ms
   budget rules out live" (`docs/tas.md` L97, DOC) [A5-001]. El brazo S0 en partida es **nuevo**, no una
   reproducción.
2. **El árbol alternado da respuestas erróneas en Melee, documentado por el propio autor.** El "ciclo" de la §12
   (jab vence a esperar, shine a jab, esperar a shine) "was an artefact" de dar a un lado el input del otro en el
   mismo frame; con ambos eligiendo a la vez, un frame tarde, el defensor simplemente espera
   (`optimal-play.md` L358-359, DOC) [A5-010].
3. **La latencia de reacción domina el valor del juego.** Con inputs de 2 frames (`nash --grain 2`) el valor del
   duelo a 12,59 u pasa de 0 a 0,382 (piedra-papel-tijera) (`optimal-play.md` L367-372, DOC) [A5-011]. Cualquier
   planificador que consuma frames de cómputo (planificar cada 2 frames, pensar en otro hilo) paga en la misma
   moneda que pretende ganar.
4. **A igualdad de pasos de 1 frame, un predictor aprendido ~1M en esta CPU no es más rápido que el simulador**:
   ~10-12 µs por candidato-paso a lote 64 (A7, REP: rollout mlp 1M K=64 T=8 = 6,17 ms p50) frente a 12-17 µs/frame
   documentados del simulador (otra máquina). El ARPredictor de LeWM (transformer por ventana) es 10× más lento
   (tx 1M K=64 T=8 = 77,7 ms) y **no cabe en tiempo real** [A5-020, A5-021]. Solo un W1-L con núcleo recurrente/MLP
   y bloques de 4 frames da más horizonte por ms.
5. **Faynt-10M no puede ser a la vez prior y dejar presupuesto de búsqueda en tiempo real en CPU**: 8,1/11,5 ms
   p50/p99 con 8 hilos (melee-llm `docs/bots.md` L53, DOC) contra C_rt≈12 ms. En realtime el prior ha de ser un
   B0 pequeño con el encoder compartido; Faynt solo en paused [A5-022].
6. **Con horizonte corto y semivida de 8 s, J ≈ V̂(x_T)**: γ=0,99856/frame ⇒ γ^32 = 0,955. El MPC de 8-32 frames
   es, en la práctica, "V̂ compuesto con la dinámica" — su ventaja sobre P0-Q (un Q̂ de la secuencia sin rollout) es
   exactamente lo que hay que medir, y es muy sensible a V̂ [A5-030].
7. **Veredicto corto:** en `--mode sim` el modelo aprendido no puede superar a S0 en igualdad de candidatos,
   rival y V̂ salvo por abstracción temporal; su única ventana defendible es Dolphin/netplay sin simulador sombra
   (régimen `I_human` o tras divergencia de RNG) y situaciones casi monoagente (recuperación). **S0 es la cota
   superior de W** a igual conteo: si S0 no supera a P0, ningún W lo hará (§6) [A5-040, A5-041].

---

## 1. Familias comparadas

Notación: N candidatos propios, K hipótesis del rival, T frames de horizonte, B=N·K ramas, `step` frames por paso
de modelo, C plazo de cómputo. Costes de `search_budget.json` (INF sobre REP de A7 y DOC del simulador).

| Familia (brazo) | Modelo usado al decidir | Información que requiere | Coste por decisión (CPU, 1 hilo) | Qué atribuye su contraste |
|---|---|---|---|---|
| **Política directa** (B0/B1/B2) | π(h) | observación causal (I_full o I_human) | 1 forward: ~0,1-1,4 ms para ~1M (A7 encode); Faynt-10M 8,1 ms DOC | Piso; B1−B0 = RL, B2−B1 = representación |
| **P0** (mismas propuestas, sin rollouts) | prior + `s0(c)` = log π(c) (**P0-logp**) o Q̂(h,c) de la secuencia (**P0-Q**) | igual que la política | t_prior + t_Q(N) ≈ 0,2-2 ms | Control de búsqueda instantánea: W−P0 = sistema de planificación; con P0-Q, W−P0-Q aísla "rollout + V̂" frente a "Q̂ directo" |
| **S0** (motor conocido) | simulador exacto + q + V̂(x) | `simulator_snapshot` (incl. memoria de mandos y RNG) + semilla; **solo `--mode sim` pasando el `World`** (A1-007, A1-008) o simulador sombra en Dolphin | B·(T·c_sim + 9 µs)/P; RT-a (B=64,T=8): 8,3-9,3 ms con c_sim 15-17 µs (DOC otra máquina); búsqueda en Python ~43 ms | S0−P0 = **cota superior** del valor de los rollouts con esos candidatos/q/V̂; S0−W = coste del error de dinámica (con privilegio declarado) |
| **MPC estructurado** (W0 = W0-S) | W0-S a 1 frame + q + V̂ | observación; mando del rival del frame en I_full | RT-a: 7,0/7,9 ms (rival lazo abierto); 13 ms con q en lazo cerrado → no cabe | W0−P0 = sistema; W0 vs W0-shuffle/persist = sensibilidad a acciones |
| **MPC latente** (W1 = W1-L) | W1-L bloque 4 + q + V̂ (sobre campos decodificados) | igual que W0 | GRU 1M: 2,7-4,2 ms en RT-a; **ARPredictor transformer: 20-25 ms → no cabe** | W1−W0 = latente vs estructurado (planificador fijo); W1−S0 = error de dinámica + abstracción |
| **Imaginación tipo Dreamer** (W2) | ninguno al decidir (actor) | igual que la política | igual que la política directa | W2−B2 = valor de entrenar con rollouts aprendidos; MuZero/Dreamer muestran que la política absorbe parte del beneficio de la búsqueda (MuZero Atari: "even with a single simulation… performed well", L335-337, DOC) |
| **Híbrido situacional** (H0) | B1 + MPC (W o S0) solo en estados predefinidos | igual que su MPC | coste del MPC × frecuencia de activación | H0−B1; candidato natural: recuperación/borde, casi monoagente (§6.3) |
| **Etiquetado por búsqueda** (S-teach, propuesto como brazo secundario) | política entrenada con etiquetas de búsqueda offline (DAgger / "search as teacher") | búsqueda privilegiada solo en entrenamiento | igual que la política directa | separa "conocimiento de búsqueda" de "búsqueda en vivo"; es la vía que el autor de melee-llm propone (tas.md L97) y ExPhil documenta (research.md L327, DOC) |

Diferencias de información que **invalidan** comparaciones par a par si no se declaran: S0 frente a cualquier W
(snapshot+RNG+semilla), I_full frente a I_human (A4 §4.4), valor entrenado con estado presente (A2 D3).

---

## 2. Especificación del planificador a evaluar (común a P0/S0/W0/W1)

### 2.1 Unidad de acción

- **Ejecución:** un mando crudo por frame (`MslInput`: botones u16, sticks −80..80, gatillos 0..255; A1 §7.3),
  igual que bots y melee-brute (`Match.step(p1,p2)`, CÓD).
- **Candidato:** secuencia de **T frames** de mandos propios, construida como
  `[cola comprometida D frames (fija)] + [bloque de decisión k=4 frames] + [continuación T−D−4]`.
  - El bloque de decisión se elige de un **vocabulario congelado de movimientos de 1 frame con menús por
    estado**, el de `fox.frame_rules()` (`MOVES1`/`MENUS1`, `fox.py` L46-72: 6-11 opciones por estado,
    "a decision every frame") ampliado con los añadidos de `nash.py` (`MOVES`, L35-48: smashes, tilts, walk,
    crouch, wavedash). Se repite o encadena hasta 4 frames.
  - Más **muestras del prior** (B0 pequeño) del mismo bloque de 4 frames.
  - Continuación: el **prior en lazo cerrado** (S0, y W0 si cabe) o la **repetición del último mando** (lazo
    abierto). Elegir uno y fijarlo para todos los brazos en el mismo tramo de presupuesto.
- Justificación: un input por frame es lo que hace válida la semántica "un frame tarde" (§3); macros largas tipo
  LLM (`actions.py`, frames 1..90) ocultan la reacción. `k=4` coincide con el paso de W1-L (A4) para que el
  bloque de decisión no se parta entre pasos del modelo.

### 2.2 Generador de candidatos (N)

`N = N_prior + N_menu`, por defecto 16 = 8 + 8 (RT-a), 32 = 16 + 16 (RT-b, PU-a):
1. top-1 del prior (siempre el primero: es el fallback L2);
2. N_prior−1 muestras del prior a temperatura τ=1 (factorizado botones×stick, como Faynt 728×85, A2 D3), sin
   reemplazo;
3. N_menu movimientos del menú del estado actual (completo si cabe), con "wait" siempre incluido;
4. warm start: el plan elegido en t−1 desplazado un frame (patrón `_prev_mean[1:]` de TD-MPC2, `tdmpc2.py`
   L166-167, CÓD).
Semillas de muestreo fijadas por `(schedule_id, frame)` y **compartidas entre brazos**.

### 2.3 Hipótesis del rival (K)

- `K=4` en realtime, `K=8` en paused. q = BC del rival a su demora de reacción R_opp (A4 §4.1), sobre historia
  visible; mismas K semillas en todos los brazos.
- **Lazo abierto válido solo dentro de la ventana de reacción**: las acciones del rival en los primeros
  `D_self+1+R_opp` frames no pueden depender de mi decisión actual (A4-016). Para rivales tipo humano (R_opp≈12)
  y T≤13 basta con secuencias muestreadas en la raíz; para bots a 0 frames (Faynt, Reyn: "zero added delay",
  A1 §9) el rival reacciona cada frame y hace falta q en lazo cerrado (coste ×2 en W0, ver JSON).
- Agregación en utilidad (nunca en estado, A4 §4.2): media (principal), CVaR_0.25 (secundaria),
  mín. con reacción O3' solo en H0.

### 2.4 Función objetivo

`J(c,k) = Σ_{t<T} γ^t r_t · Π cont + γ^T V̂(x_T) − β·σ_ens` y
`J_total(c) = λ_b·s0(c) + λ_r·mean_k J(c,k)`.
- r: recompensa de slippi-ai/Faynt (stocks + daño, suma cero; A2 §Faynt), **sin** los términos de modelado
  (aproximación, *stalling*) en la versión principal; con ellos como variante declarada.
- **V̂ definido sobre el estado estructurado x**, no sobre z: S0 lo aplica a x_T exacto, W0 a x̂_T, W1 a la
  decodificación de ẑ_T (cabeza de campos de A4). Así el evaluador es idéntico; V̂(z) nativo de W1 es una
  variante "sistema" (`W1-L-native`), reportada aparte (06 Control de puntuación).
- γ = 0,5^{1/480} = 0,998557 (semivida 8 s, A2). Consecuencia: J está dominado por V̂ (§0.6).
- β·σ_ens solo en W; β=0 en S0. `out_of_support` (A4 §5.1) descarta el candidato si p(soporte) < umbral
  preregistrado.
- P0: λ_r=0. W/S0: λ_r=1, λ_b fijado en validación **igual para todos**. Ablaciones con evaluador fijo:
  `W-shuffle` (secuencias de acción permutadas entre candidatos antes del rollout) y `W-persist` (x̂_T = x_f;
  con V̂ fijo esto colapsa a P0, lo que lo convierte en una comprobación de implementación).

### 2.5 Algoritmo

- **Principal (todas las categorías): random shooting con prior + menú**, una iteración, argmax de J_total.
  Elegido porque los mandos son híbridos discretos (botones) y cuantizados (sticks); el MPPI gaussiano de TD-MPC2
  (`_plan` L172-206: 512 muestras, 64 élites, 6 iteraciones, 24 trayectorias de política, H=3, CÓD) y el CEM de
  LeWM (300 muestras, top-30, 30 iteraciones, H=5, `cem.yaml`; ejecuta los 5 bloques sin replanificar,
  `pusht.yaml` `receding_horizon: 5`, CÓD) asumen acciones continuas y presupuestos (45.000 evaluaciones por plan
  en LeWM) fuera de alcance en 12 ms.
- **Ablación paused: CEM categórico** de 2 iteraciones (distribución por frame sobre el menú, inicializada con el
  prior, top-25 %), mismo B total.
- **Árbol / matriz solo en paused** (`PU-matrix`, §3.3).
- Selección final: argmax (determinista) en la principal; **muestreo softmax de temperatura τ_sel** (o de la
  estrategia mixta en `PU-matrix`) como ablación contra explotabilidad (§3.4).

### 2.6 Recesión, delay y plazo

- Replanificar **cada frame**, comprometer **1 frame** (`RT-a/b/c`). Variante `RT-2f`: replanificar cada 2 y
  comprometer 2 con presupuesto 2·C_rt, registrada como reloj distinto (cambia la reacción efectiva, §0.3).
- Delay: decisión tras ver post(f) se aplica en `f+1+D` (A6 `delay_model`). El rollout arranca en h_f con los D
  mandos ya comprometidos (no optimizados) y las K hipótesis del rival para esos D frames; el horizonte efectivo
  de decisión es `T−D`. Se exige `T ≥ D+4`; con D=18 (Phillip) T ≥ 24 ⇒ solo cabe W1-L-GRU o paused.
- **Plazo y fallback** (A6 `fallback`): el planificador tiene un temporizador propio `C_rt`, evalúa candidatos en
  orden del prior (anytime) y al vencer usa L1 mejor evaluado → L2 top-1 del prior (calculado antes que nada) →
  L3 repetir/neutral. Nunca bloquea: en realtime Dolphin espera el mando y un paso lento ralentiza la partida y la
  marca `slow` (A1-002, A1-016). Se registra nivel de fallback, `N_eff`, `t_dec` y los campos de A6.
- Integración: `WorldModelAgent(Agent)` con el trabajo en `begin(gs)`/`step(gs)` (A1 CONTRACT §5). S0 exige
  pasar el `World` al agente (cambio en `sim/runner.play` L47-53, PROP de A1).

### 2.7 Tramos de presupuesto (resumen; detalle y estimaciones en `search_budget.json`)

| Tramo | Reloj | N×K×T | Cabe en C (estimación INF) |
|---|---|---|---|
| RT-a | realtime, C_rt=12 ms | 16×4×8 | W0-S GRU (rival lazo abierto), W1-L GRU, S0 P=1 a 15-17 µs/frame |
| RT-b | realtime | 32×4×8 | W1-L GRU, S0 con P=3 réplicas |
| RT-c | realtime | 16×4×16 | W1-L GRU, S0 P=3 |
| RT-2f | realtime, 2 frames | 32×4×16 | 2·C_rt; reloj distinto |
| PU-a | paused, C_pu=250 ms | 32×8×16 | todos salvo W1-L transformer |
| PU-b | paused | 64×8×32 | W1-L GRU, S0 P=1-3, W0-S |
| PU-matrix | paused | 8×8 macros × 16 | todos los rápidos; LP de 8×8 |

---

## 3. Simultaneidad

### 3.1 Por qué minimax alternado es incorrecto

- Melee es un juego estocástico de movimientos simultáneos: cada frame ambos mandos se leen a la vez (Littman
  1994, ficha B16; A4 §4.1). Un árbol alternado da al segundo en mover el input del primero **en el mismo frame**,
  información que ningún jugador tiene. Con ∃a∀d (atacante mueve primero) se infravalora al atacante; con ∀d∃a se
  sobrevalora. El valor del juego simultáneo queda entre ambos y en general requiere **estrategias mixtas**.
- Evidencia de Melee (DOC, melee-llm): el ciclo de la §12 obtenido con `force --safe` desaparece en el juego
  simultáneo de `nash.py` (`optimal-play.md` L358-359); `nash.py` lo explica en su cabecera: "`force.py` gave one
  side the other's input on the same frame, which only bounds the answer" (L4-6, CÓD).
- MuZero/AlphaZero: búsqueda para "two-player zero sum games" con valores en [0,1] y turnos (MuZero Apéndice B,
  texto extraído L618-620; "Imperfect information games such as Poker are not directly addressed", nota 2, L192;
  dinámica determinista, "extension to stochastic transitions is left for future work", L144) (DOC). OpenSpiel:
  el ejemplo MCTS aborta con "MCTS not supported for games with simultaneous actions." (`mcts_example.cc`,
  `IsSimultaneousNode()`, DOC/CÓD sin SHA) [A5-012, A5-013].

### 3.2 Qué garantiza exactamente melee-brute (y qué no)

| Herramienta | Pregunta | Orden de información | Garantía válida | Límites exactos |
|---|---|---|---|---|
| `best(match, choices, depth, score)` (`search.py` L35-52) | máx. de `score` sobre todas las secuencias de `depth` elecciones de **P1** | monoagente: P2 recibe `NEUTRAL` por defecto (`Match.step` L170) o lo que imponga `play` | óptimo exacto para ese menú, profundidad, score y rival fijo | |choices|^depth; nada sobre un rival que reacciona (tas.md L100: "optimal against a fixed opponent") |
| `improve(...)` (L55-90) | mejora local por cambios aleatorios | monoagente | ninguna de optimalidad: hill-climbing | `tries`, semilla |
| `Forced.win(frames)` (L232-323; C `brute.c`) | ¿P1 fuerza el **primer golpe** (o agarre de `caught`) haga lo que haga P2, **viendo P2 cada movimiento de P1 antes de responder**? | ∃a∀d por **movimiento nombrado** (los movimientos multi-frame se juegan juntos hasta que uno acaba o hay golpe, `brute.c play` L580-620) | "sí" ⇒ victoria de primer golpe también en el juego simultáneo (cota prudente) | Solo para `Rules` dados (movimientos, menús por `action_id`, `trap`, `zones`, `timeout`), `frames` dados, pago "primer golpe" — no stocks ni daño acumulado ni partida; RNG del simulador ("replays on Dolphin only while no random event differs", BRUTE.md L150); `exact=False` puede fusionar estados distintos (L74-80); "proves things about the moves you give it and the frames you allow, no more" (L151) |
| `Forced.safe(frames)` | ¿P2 evita ser golpeado primero viendo P1 cada movimiento de P2? | ∃d∀a | "sí" ⇒ defensa garantizada en el simultáneo; "no/no" ⇒ "decided by guessing" (L50-51) | mismos límites |
| `nash.py` (melee-llm) | valor exacto del juego simultáneo "un frame tarde" | matriz por posición, LP (`matrix.py`) | exacto **para los menús, el horizonte y el pago** (`hit`, `net` o `percent`) | horizonte 6-16 frames; menús de 6-9 movimientos de 1 frame; Fox ditto FD a 0 %; clave de posición sin RNG/ECB/temporizadores de intangibilidad ("no difference seen", L391-394) |

Resultados citables y su alcance (DOC, melee-llm `optimal-play.md`):
- Corpus de regresión: 360 posiciones Fox vs Fox acorralado en FD, gaps {6,9,11.5,14,20,30}, hop {0..12},
  ledge {12,40}, frames {4,6,8} (`corpus.py` L21-31, CÓD).
- "Standing at close range is a proven draw at this depth" (14 frames, §11 L296-301) y la tabla de 16 frames
  "only shield": **anteriores a dos bugs de menú** (jump out of shield, shine en jumpsquat) que "weaken sections 9
  to 12 for the defender… the earlier tables were not rerun" (L343-346); BRUTE.md confirma: "The 16-frame run
  published earlier used the old search and menus and has not been repeated" (L63) [A5-014].
- Mapa de posiciones de pie: "a proof for these menus and 8 frames" (§14 L482-484); el "fortress" **no converge**
  (5 de 21 rondas con grietas nuevas, L591-592) y todo el juego se hizo a lookahead 6 (L639).
- No se debe citar ningún resultado como "Fox no puede ser golpeado" ni "garantía" fuera de: esos menús, ese
  horizonte, pago de primer golpe, FD, 0 %, UCF, RNG del simulador [A5-015].

### 3.3 Opciones prácticas para el planificador

| Opción | Qué resuelve | Coste | Riesgo | Uso |
|---|---|---|---|---|
| **BR-q**: mejor respuesta a K muestras del prior del rival (O2) | maximiza E_q[J] | B=N·K rollouts | si q es malo, el plan es malo; determinista ⇒ predecible; **explotable** por un rival que adapte (humano/LLM); contra bots fijos el riesgo es solo el sesgo de q | principal |
| **Maximin con reacción (O3')**: rival muestreado de q en los primeros D+1+R_opp frames, mín. sobre un menú M_opp después | "¿es seguro?" sin suponer lectura de mente | N·M (+K para la fase exógena) | pesimista si M_opp está mal elegido; con R_opp=0 se acerca a `Forced.safe` (rival que ve mi input), demasiado pesimista según el propio autor (§3.1) | H0, castigo/defensa |
| **Matriz de pagos por paso**: N macros propias × M del rival en la raíz, hoja = rollout de continuación (prior ambos) + V̂, LP de N×M y muestreo de la estrategia mixta | equilibrio de un paso con hoja aprendida; no explotable **dentro de esa abstracción** | N·M rollouts + LP (≤ docenas de filas, `matrix.py` simplex denso, CÓD) | la hoja fija sesga como el "idle/shield leaf" de §7 (L205-207: "the two leaves bracket the truth"); un solo nivel de simultaneidad | `PU-matrix` (paused) |
| Juego simultáneo exacto a H frames (`nash.py`) | valor exacto en menús/horizonte | (|M|²)^H; 1-4 s/frame a H=6, 30-60 s a H=8 (L474-476, DOC) | inviable en vivo por 60-3.600× | etiquetado offline / brazo S-teach |

### 3.4 Explotabilidad

- Un argmax determinista sobre E_q es una estrategia pura: contra un rival que lo modele es explotable aunque
  contra q gane. En el Fox ditto la explotabilidad es concreta: a 12,59 u con un frame de reacción el valor es 0
  con espera pura, pero con dos frames es 0,382 y la mezcla óptima es 38/38/24 (L367-372, DOC); una pura ahí
  pierde contra la mejor respuesta.
- Medidas propuestas: (i) ablación de selección estocástica (softmax τ_sel, mezcla con el prior); (ii) rivales de
  test fuera de entrenamiento y un "best-response probe": entrenar/afinar brevemente un rival contra el brazo
  congelado (presupuesto declarado) y medir la caída; (iii) reportar entropía de la política de decisión.
- Los evaluadores fijos (bots) no explotan online; los humanos y LLM sí. La métrica principal frente a B1 no mide
  explotabilidad: se reporta aparte (PROP) [A5-016].

---

## 4. Presupuestos igualados (`search_budget.json`)

- **Dos reglas, ambas publicadas** (06 Control de puntuación): igual conteo (N, K, T, semillas) e igual tiempo
  (K, T fijos; N_max por brazo con p99 ≤ C).
- **C_rt = 16,667 − t_obs_io − t_send − m_p99** (PROP 12 ms en sim; Dolphin DESC hasta medir
  `t_obs_available → policy_start`, A6). C_pu por defecto 250 ms con barrido {50, 250, 1000, 4000}.
- Fórmulas (JSON `decision_cost_formulas`): W: `Σ_s c_step(B)` con `c_step` interpolado de A7; q en lazo cerrado
  añade `ceil(T/step)·c_q(B)`; S0: `B·(T·c_sim + c_ckpt + c_rb)/P`; si q de S0 necesita `GameState` de libmelee,
  `+B·T·0,23 ms` (StateBuilder, DOC) ⇒ inviable: q debe leer filas nativas por lote.
- Cifras: medidas (REP, A7/A4, esta máquina, pesos aleatorios) frente a documentadas (DOC, simulador en 5950X;
  Faynt CPU 8 hilos). Ninguna latencia del simulador está medida aquí (sin ISO): primera tarea de E2 es
  `python -m melee_brute bench` en la máquina objetivo y medir `t_dec` integral por brazo bajo carga.
- Paridad de núcleos: S0 con P réplicas usa P núcleos; el W correspondiente recibe los mismos P hilos de torch
  (A7 midió 1 y 3 hilos: con 3 hilos el p99 empeora por carga compartida — p. ej. mlp 1M K=16 T=4: 27 ms p99).

---

## 5. Información privilegiada y experimento de información equiparada

| Brazo | Snapshot | Semilla / RNG | Mando actual del rival | Mandos futuros del rival | Categoría |
|---|---|---|---|---|---|
| B*, P0 | no | no | I_full sí / I_human no | no | causal |
| W0, W1 | no | no | según régimen | no (q) | causal |
| S0 (`--mode sim`) | **sí** (estado exacto incl. memoria de mandos y temporizadores, A4-003) | **sí** (el RNG va en el estado, A1-022 INF) | implícito en el estado | no (q) | **privilegiado** |
| S0-shadow (Dolphin) | reconstruido desde mandos aplicados de ambos + semilla | RNG por frame del flujo Slippi (FrameStart `random_seed`, A6 nivel `simulator_snapshot`); los bots ya reciben el flujo Slippi crudo (A1-012) | **requiere I_full** | no | privilegiado (RNG) |
| Diagnóstico oracle | — | — | — | sí | excluido del juego (07) |
| V̂ con estado presente | solo en entrenamiento | — | — | — | privilegio de entrenamiento declarado |

Nota INF: en netplay Slippi el RNG se reinicia por frame a `base + 65536·frame` (E31 L19, DOC), lo que haría
predecible el RNG futuro de un simulador sombra; no verificado para partidas locales de Dolphin.

**Experimento de información equiparada (PROP):**
1. **Mismo q, mismos candidatos, mismo V̂(x), I_full para todos** en `--mode sim`: S0 vs W0 vs W1 vs P0, a igual
   conteo (PU-a) y a igual tiempo (RT-a). La única diferencia es la fuente de dinámica + el privilegio de S0.
2. **Cuantificar el privilegio de S0 por separado**: (a) *S0-blind-RNG*: en cada decisión, ramas evaluadas bajo
   el RNG real frente a "gemelos" de RNG (A4 §5.5); como no hay API para escribir el RNG a mitad de partida
   (A4: DESC), la variante ejecutable es medir en el panel contrafactual la fracción de decisiones cuyo argmax
   cambia entre la rama con el RNG exacto y la media sobre semillas de partida distintas que alcanzan el mismo
   estado observable; (b) *S0-memless*: imposible en exacto; se acota con el test de aliasing de A4 §5.4
   (frecuencia con que estados look-alike divergen).
3. **I_human**: S0 no es ejecutable sin el mando actual del rival (el estado de Markov lo incluye, A4-017). Por
   tanto la comparación W vs S0 **solo es equiparable en I_full**; en I_human, el contraste válido es W vs P0
   vs B1, y S0 queda como cota privilegiada.

---

## 6. Veredicto razonado

### 6.1 ¿Puede la planificación con modelo APRENDIDO superar a la búsqueda con el simulador?

| Régimen | Veredicto | Razón |
|---|---|---|
| `--mode sim`, I_full, igual conteo | **No** (salvo azar o regularización accidental) | S0 usa la dinámica exacta con los mismos candidatos, q y V̂: es la cota superior de cualquier W bajo ese evaluador [A5-040] |
| `--mode sim`, igual tiempo, realtime | **Improbable**; posible solo W1-L con núcleo GRU/MLP y bloques de 4 si su regret de decisión a 16-32 frames es bajo | a 1 frame por paso el coste por candidato-paso es comparable (10-12 µs vs 12-17 µs); la ventaja de W1 es 4× horizonte por paso. Los golpes son discontinuos dentro del bloque (A4 §1.2) |
| Dolphin, I_full, con simulador sombra | **No** hasta la primera divergencia de RNG; después, quizá | sombra exacta con mandos+semilla+RNG grabado (E31: 36/40 humanas al final con RNG inyectado, DOC); sin RNG inyectado 25/40 divergen (A4-021) |
| Dolphin, I_human / sin simulador en la máquina | **Sí por defecto** (S0 no existe) | el contraste relevante pasa a ser W vs P0/B1 |
| Con delay D grande (18-24) | La pieza útil es **q**, no p_dyn | con la cola propia conocida, el simulador predice el presente si conoce los mandos del rival (A4 §6.2) |

### 6.2 ¿Puede superar a la política sola?

Prior de evidencia (todo DOC, fuera de Melee salvo Firoiu): la planificación en Atari "plateaued at around 100
simulations… with a single simulation… MuZero performed well" (MuZero L333-337); en Go el modelo aprendido igualó
al simulador perfecto en escalado de búsqueda (Fig. 3A, L366-368) — pero con 800 simulaciones ≈ 0,1 s en TPU (L368)
y turnos alternos. En Melee: predictor de Firoiu 2018 ayuda solo con p=d y contra rivales que aprenden (A2-019);
slippi-ai lo abandonó; el autor de melee-llm recomienda "Skip the predictive model" (`delay.md` L70, opinión);
cabezas de estado de HAL sin ganancia (A2-004). Ningún bot publicado planifica en vivo (A2-034).

Régimen donde podría ganar (INF, ordenado por plausibilidad):
1. **paused_untimed**, prior débil (B0 pequeño), V̂ bueno: más candidatos y horizonte que la política, sin coste de
   reacción. Es donde S0 debe probarse primero.
2. **H0 en recuperación/borde**: problema casi monoagente (la simultaneidad pesa poco), horizontes 30-60 frames,
   física determinista; `best`/`improve` son exactamente esto (monoagente) y A4 propone W1-evt.
3. **Realtime sin delay contra bots fijos** con W1-L-GRU en RT-a/b: margen pequeño; el coste de reacción (§0.3)
   y q imperfecto pueden anularlo.
4. **Con delay**: improbable que supere a una política entrenada con la cola como entrada (Phillip, Faynt).

### 6.3 Experimento más barato que lo falsaría

**"S0-ceiling" en `--mode sim`, paused, igual conteo** (requiere ISO + el cambio de A1 para pasar el `World`):
B1 (o Faynt-10M-Expert como prior/política si B1 no existe) vs **P0-Q** vs **S0** con N=16, K=4 (q = copia del
prior, O4, ditto), T=16, mismo V̂(x), calendario piloto de 06 (2 escenarios × 2 rivales × 2 puertos × 5 rep.
= 40 partidas por brazo).
- Si **S0 − P0 ≤ 0** (IC 95 % por bloque emparejado, o mejora < umbral preregistrado), **la planificación con
  modelo aprendido queda falsada en ese régimen y evaluador**: ningún W con los mismos candidatos/q/V̂ puede
  hacerlo mejor que la dinámica exacta. Se cierra W0/W1 para MPC y se redirige a S-teach o W2.
- Si S0 > P0, el siguiente corte barato es offline: **panel de regret de decisión** (A4 §5.4 C1, ~2.000 estados
  alcanzados por el prior, mismas N, K, T): regret de argmax_W frente a argmax_S0; si regret_W ≥ regret_P0, W no
  aporta sobre P0 aunque S0 sí.
- Coste estimado (INF): 16·4·16 = 1.024 frames simulados por decisión ≈ 15-18 ms (DOC c_sim) + V̂ ⇒ ~20 ms/frame;
  28.800 frames/partida ⇒ ~10 min/partida/núcleo; 120 partidas (3 brazos) ≈ 20 h·núcleo ≈ 1,3 h en 16 núcleos.
  El panel offline: 2.000 × 64 ramas × 16 frames ≈ 2M frames ≈ 35 s de simulador + inferencia de W.
- Lo más barato **sin ISO** (aquí): nada falsable en juego. Solo se puede medir latencia integral de P0/W con
  pesos reales y el coste de q en lazo cerrado (extensión de A7).

---

## 7. Dudas, contradicciones y bloqueos

- **A1/coordinador:** S0 y el simulador sombra requieren pasar el `World` al agente (no existe). ¿Se aprueba el
  cambio en `sim/runner.play` L47-53 y el registro de semilla (`runner.play` no la reenvía, A1-§11.6)?
- **A1:** ¿expone el flujo Slippi que reciben los bots en Dolphin el `random_seed` de FrameStart? Si sí, es un
  canal privilegiado que hoy llega a todo bot aprendido (A1-012); hay que declararlo o filtrarlo.
- **A4:** el W1-L especificado (ARPredictor transformer) no cabe en realtime en CPU (A7: tx 1M 20-25 ms en RT-a).
  Propongo una variante `W1-L-GRU` (mismo encoder y SIGReg, núcleo recurrente) para el brazo realtime; el
  transformer queda para paused. Afecta a la comparabilidad W1 vs W0 (cambiar núcleo cambia capacidad).
- **A2:** sin valor terminal publicado reutilizable (A2 D3): V̂(x) hay que entrenarlo; es el componente crítico
  (§0.6) y debería tener su propia evaluación (calibración y ranking de candidatos) antes de cualquier MPC.
- **A7:** `FEASIBILITY.md` está vacío (solo cabecera); usé `summary.json`. Falta: latencia de q en lazo cerrado,
  cabezas reales de W0-S, prior B0 pequeño, y jitter p99 bajo la carga del bench.
- **A8:** S0 vs W1 (contraste de 07) solo es comparable en I_full y con privilegio declarado; propongo reformularlo
  como "S0 = cota superior" y no como comparación simétrica.
- **Contradicción con la ficha A14:** BRUTE.md presenta "prueba de primer golpe y defensa"; el resultado de 16
  frames "only shield" que difunde `optimal-play.md` §11 es anterior a correcciones de menú y no se ha repetido
  (BRUTE.md L63; optimal-play.md L343-346).
- **Contradicción con 06 (S0):** "Usar idénticos candidatos… si la interfaz lo permite": la interfaz no lo permite
  hoy (A1-007); es un requisito de ingeniería, no un detalle.
