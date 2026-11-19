# A1 · Contrato de integración: interfaces lógicas ↔ símbolos reales

Versión 0.1 (2026-11-19). Mapea `handoff/melee_swarm/09_INTEGRATION_CONTRACT.md` a código real. Revisiones:
melee-llm `7e179081c6cbab139d860c998b1452ad3dee047c` (runtime idéntico a `2bf8b0eb…`), melee-brute HEAD
`9662ec973b9e077ff7b0ff89d6db950f53c11653` (pin de melee-llm `090e54b048b7d51e82f9f6b551046c2ca8b130c7`, E31
`d3832724ef67f67db4bb4672ff46ae6c134dbad7`), melee-sim-light `eea7b5fbcd0243baf4c1956d52f3e1d0f536edc4`, libmelee
`bce21f09984b286e6d36bfd2939e4cd4691f94c2` (instalado: `v0.47.6` = `2d63e7ee948d77ab4e73165ed4c73abbe3ba121b`).

Estados: **EXISTE** (símbolo real con esa semántica), **PARCIAL** (existe algo cercano; se indica la diferencia),
**INEXISTENTE** (no hay símbolo), **PROPUESTA** (diseño de este contrato, no implementado). Nada marcado PROPUESTA
está implementado en ninguna de las revisiones citadas.

## 1. Interfaces lógicas

| Interfaz lógica (09) | Estado | Símbolo real más cercano | Diferencias / conversión necesaria |
|---|---|---|---|
| `env.reset(seed, matchup, initial_state)` | **PARCIAL** (solo sim) | `melee_llm/sim/world.py World.__init__(characters, stage, seed, costumes, max_frame, percents)` L56-72 + `World.reset(seed) -> GameState` L74-86; nativo `EnvBatch.configure_match(...)`+`reset_all()` (`melee_sim/env_batch.py` L210-254); `melee_brute.Match(p1,p2,stage,seed,percents)` (`melee_brute/match.py` L31-53) | No devuelve metadatos; `initial_state` arbitrario **INEXISTENTE** (solo `World.restore(Snapshot)` de un estado alcanzado por inputs, o `start_percent`). En Dolphin no hay `reset`: `runner.play` gestiona menús y la partida entera (`runner.py` L185-317). `runner.play(mode="sim")` no reenvía `seed` (L202). |
| `env.step(joint_action)` | **PARCIAL** | sim: `World.step() -> GameState` (L88-102) lee el estado actual de los dos `SimController`; nativo `EnvBatch.step(step_mask)` lee `raw_action_view[t]` (L331-358); `Match.step(p1, p2, frames)` (L76-85) | La acción conjunta no es argumento: se escribe antes en los controladores. Dolphin: no existe step externo, el bucle está dentro de `runner.play` (L279-300). |
| `agent.act(observation, memory, budget)` | **PARCIAL** | `Agent.step(gs) -> None` (`melee_llm/agents/base.py` L36-37), con `begin(gs)` previo (L32-34) | Sin `memory` explícita (estado en el objeto), sin `budget`, sin diagnóstico devuelto; la acción es el estado del controlador. Presupuesto solo en bot-writer (`botwriter/agent.py` `budget_ms=16.0` L79). Latencias: `BotAgent.latency()` (`bots/agent.py` L167-175), logs LLM (`latency_s`, `latency_frames`, `stale_frames`, `llm_live.py` L71-75). |
| `encoder.encode(history)` | **INEXISTENTE** en melee-llm runtime | Más cercano: `state.observe()`/`render()` (`melee_llm/state.py` L144-200), textual; codificadores propios de cada bot en su venv | Debe proveerlo A3/A4 dentro de un `Agent`. |
| `dynamics.predict(latent, own_actions, opponent_hypotheses, elapsed_frames)` | **INEXISTENTE** (aprendido) | Dinámica exacta no aprendida: el propio simulador (`EnvBatch.step`, `Match.step` + `checkpoint/rollback`) | `docs/delay.md` §5.4 recomienda no usar modelo predictivo (opinión del autor, no prueba). |
| `evaluator.score(prediction, goal)` | **INEXISTENTE** como interfaz | `score: Callable[[Match], float]` de `melee_brute.best/improve` (`search.py` L35, L55); `first_hit` (L196); recompensa de farm (doc `11_PLATFORM_MAP`) | El bench puntúa partidas (BT), no estados. |
| `planner.propose(observation, model, prior, budget)` | **INEXISTENTE** en partida; **PARCIAL** fuera de línea | `best`, `improve`, `Forced.win/safe`, `solve` (`melee_brute/search.py` L35-344) sobre un `Match`, no sobre una observación | No hay ruta `GameState → estado del simulador`; el agente no recibe el `World` (`sim/runner.py` L50-51). Ver §4. |
| ObservationSpec | **PARCIAL** | libmelee `GameState`/`PlayerState` (`melee/gamestate.py` L68-180); nativo `MslObservation` (`API.md` L104-187) | Sin `schema_version`, `episode_id`, `observation_timestamp`, `visibility_mask`, `own_committed_action_queue` (las colas de HAL/Phillip son internas al bot). Incluye `controller_state` del rival (inputs aplicados en t). |
| ActionSpec | **PARCIAL** | libmelee `Controller` (`melee/controller.py` L240-378); `actions.Input` (`actions.py` L47-51); `MslInput` (`API.md` L95-102); protocolo bots `CTRL` (`bots/protocol.py` L1-19) | Sin `decision_frame`, `intended/actual_application_frame`, `fallback` explícitos; fallback implícito: mantener controlador (bot-writer tardío), `_default` (LLM live), reflejos del `Executor`. |
| TransitionSpec | **INEXISTENTE** en runtime | Datos de farm/entrenamiento en `train/` (no auditado por A1) | `GameResult` no separa `terminated`/`truncated`; ver §3. |
| simulator_snapshot | **EXISTE** (sim) | `World.save() -> Snapshot(state: bytes, gs)` (`world.py` L48-53, L112-125); `EnvBatch.save/restore` (L393-426); `EnvBatch.checkpoint/rollback/changed_pages` (L428-499, también en `090e54b0`); `Match.checkpoint/rollback/branch/hash` (`match.py` L113-138, Linux) | Contiene estado completo (RNG incluido por inferencia). **No** debe entregarse a una política de observación limitada: hoy no se entrega (el agente solo ve `gs`). En Dolphin: **INEXISTENTE**. |
| training_metadata | **PARCIAL** | `.slp` de Dolphin (mandos de ambos jugadores); logs de decisión `*.p<port>.llm.jsonl`; `results.jsonl` (`bench/game.py` L299-320) | Sim no produce `.slp`. |

## 2. Tipos y unidades (fuente → contrato)

| Campo | Fuente | Tipo / unidad | Transformación |
|---|---|---|---|
| frame | `GameState.frame` / `MslObservation.frame_id` | int, frames a 60 Hz; −123 en cuenta atrás (sim) | ninguna |
| posición | `PlayerState.position.x/y` ← `pos_x/pos_y` | float32, unidades de mundo Melee, y=0 suelo | copia (`sim/state.py` L115) |
| velocidades | `speed_*` | float32, unidades/frame | copia (L129-133); `state.velocity()` suma self+attack (`state.py` L123-125) |
| porcentaje | `percent` | float32, 0..999.9 | copia; `observe()` redondea a entero |
| escudo | `shield_strength` ← `shield_hp` | float32, 0..60 | copia |
| acción | `action` ← `action_id` | enum `Action` (u16 GALE01) | `UnknownAnimation` si no está en el enum |
| action_frame | `action_frame` | int, indexado desde 1 en libmelee | +1 si la acción está en `zeroindex` (`sim/state.py` L121-123) |
| hitlag / hitstun | `hitlag_left`, `hitstun_frames_left` ← `hitlag`, `hitstun` | int frames (u16 nativo); `hitlag_left` f32 solo en BR ≥ `d3832724` | `hitstun=0` fuera de hitstun en sim |
| stick | `Controller.tilt_analog(x,y)` | float [0,1], 0,5 neutro | libmelee `raw=round((x−0.5)*160)`, envía `(raw+0.1)/254+0.5`; sim `clip(floor((v−0.5)*254),−80,80)` → i8 |
| gatillo | `press_shoulder(amount)` | float [0,1] | `raw=round(amount*140)`; Dolphin rendered `(raw+0.1)/255`; ExiAI `(raw+255)/510`; sim `clip(floor(((raw+0.1)/255)*255),0,255)` → u8 |
| botones | `press_button` | `melee.Button` | bits `_BUTTON_BITS` (`sim/state.py` L31-36) → u16 |
| macro LLM | `{"action":…}` | enum `ACTIONS` + campos con rangos (`frames` 1..90, `count` 1..3) | `actions.make()` recorta enteros a rango y descarta valores fuera de enum (L688-708) |

## 3. Terminación y resultado (estado actual vs contrato)

| Caso del contrato | Código real | Estado |
|---|---|---|
| Fin por reglas (stocks a 0) | Dolphin: salida de `IN_GAME` (`runner.py` L301-303); sim: `terminal.match_ended`/`stockout` → `world.done` | EXISTE, pero el motivo no se guarda en `GameResult` |
| Time-out del reloj interno | Dolphin: reloj de Melee; muerte súbita no contada (L264-275). Sim: `max_frame=28800` (`world.py` L19) → `max_frame_reached` | PARCIAL: en sim el reloj es un corte externo puntuado como si fuera el del juego |
| Truncamiento externo sin resultado | Timeout de proceso del scheduler (`TIMEOUT`, `scheduler.py` L51) → `status: timeout` | PARCIAL (a nivel de proceso, no de entorno) |
| Crash / cancelación | `status: error` con mensaje (`scheduler.py` L379-384); `void` si >10 % llamadas fallidas | EXISTE |
| `terminated` vs `truncated` separados | — | INEXISTENTE |

## 4. Semántica temporal (lo que hay; tiempos finos pendientes de A6)

- Observación: `gs` del frame t tras `console.step()`/`world.step()`; incluye los inputs que el juego leyó en t.
- Aplicación: mando escrito en `step(gs_t)` → leído en t+1 (sim, inspeccionado en `world.py` L88-102; Dolphin según
  `docs/delay.md` L7 y flush en `console.step()` L905-908). Momento exacto en Dolphin: DESCONOCIDO.
- Delay adicional: dentro de cada bot (HAL `delay`, Phillip `policy.delay`, meleebot `delay`); LLM live por latencia
  real con descarte `max_stale=120`. No existe una cola de delay común del runner. `online_delay` de Dolphin = 0
  en `runner.play`.
- Latencia del planner: en `fast`/`paused`/`lockstep`/`realtime`/`sim` **pausa** el entorno (bloqueo); solo en
  `watch` consume frames. En `realtime` el bench marca `slow` si fps medio < 50.
- Frame skip: no existe en el runner; los macros LLM agrupan decisiones (`interval=30` por defecto).
- **Pendiente**: `evidence/A6/timing_contract.json` no existe a 2026-11-19; los intervalos observación→aceptación y
  observación→aplicación no están instrumentados en el runner.

## 5. Propuesta mínima de adaptador (PROPUESTA, no implementado)

Para que A3/A4/A5 integren un encoder/dinámica/planner sin tocar el bench:

1. `class WorldModelAgent(Agent)` en `melee_llm/agents/` (o `BotAgent` + `bots/bot_wm.py` si requiere torch en venv
   propio), registrado en `players.KINDS` y en `bench/entrants.registry()` con `track="both"`.
2. Dentro de `begin(gs)`: `encoder.encode(historia propia de gs)`; en `step(gs)`: `planner.propose(...)` y escribir
   el controlador. Registrar por frame `decision_frame=gs.frame`, `intended_application_frame=gs.frame+1+delay`,
   tiempo de cómputo, fallback usado.
3. Excluir de la observación `controller_state` del rival si la comparación lo exige (como bot-writer).
4. Brazo S0 (simulador como modelo): solo en `--mode sim`, pasando `World` al agente mediante un cambio en
   `sim/runner.play` L47-53 (nuevo parámetro) y reproduciendo semilla registrada; no comparable con Dolphin por RNG.
5. Añadir a `GameResult` `end_reason ∈ {stocks, timer, max_frame, error}` y `seed` (sim).

Ningún punto de esta sección existe hoy.
