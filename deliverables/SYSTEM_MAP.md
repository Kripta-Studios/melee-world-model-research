# SYSTEM_MAP · Observación → agente → mando → motor → resultado (consolidado)

Integrador · 2026-11-19. Consolida y corrige `evidence/A1/SYSTEM_MAP.md` y `CONTRACT.md`. Integra también el
contrato temporal de A6 (`evidence/A6/timing_contract.json`), los regímenes de información de A4/A8 y el resultado de
G-01 (`evidence/A8/G01_shadow_sim_check.md`). Nada se ejecutó: no hay ISO ni Dolphin.

Etiquetas:
- `[COD]`: inspeccionado en código.
- `[DOC]`: documentado por el autor.
- `[INF]`: inferencia.
- `[PROP]`: propuesta.
- `[?]`: desconocido.
- ✔: re-verificado por el integrador contra `sources/`.

Revisiones y prefijos de ruta:

| Prefijo | Repo | Revisión |
|---|---|---|
| `LLM:` | melee-llm | `7e179081c6cbab139d860c998b1452ad3dee047c`. El runtime es idéntico al del catálogo `2bf8b0eb` ✔ |
| `BR:` | melee-brute | HEAD `9662ec973b9e077ff7b0ff89d6db950f53c11653` |
| `LM:` | libmelee | `bce21f09984b286e6d36bfd2939e4cd4691f94c2` |

Lo que el runtime de melee-llm **instala** es distinto de esos HEAD:
- melee-brute `090e54b048b7d51e82f9f6b551046c2ca8b130c7`.
- libmelee 0.47.6 = `2d63e7ee948d77ab4e73165ed4c73abbe3ba121b`.

Las diferencias relevantes se señalan donde importan. Las revisiones completas están en `sources.lock.json`.

**Correcciones aplicadas sobre A1** (según A8):
- (1) Los localizadores de `bench/game.py` estaban mal (fichero de 113 líneas ✔).
- (2) «bench.md "never waits" contradice el código» queda matizado: el doc lo reconoce en L27.
- (3) El `controller_state` del rival llega **sin** C-stick crudo ni gatillos físicos.
- (4) A4-027 (sombra desde `GameState`) es FALSA. Se sustituye por el veredicto de G-01.

## 1. Cadena completa

```
entrants.registry()  (LLM:melee_llm/bench/entrants.py L80-141)
  └─ scheduler.Bench._run(job)  (LLM:bench/scheduler.py L362-393; TIMEOUT L51) → subproceso "python -m melee_llm.bench one"
       job = {spec1, spec2, stage, mode ∈ {fast, realtime}}  (mode = entrants.game_mode L189-191)
       └─ bench/game.py play_one(job, iso, port, out)  L83-104 ✔
            ├─ make_agent(spec)  L17-28 ✔ → players.make(spec, FOX)  (LLM:players.py L41-55; KINDS L25-32)  [siempre Fox]
            └─ runner.play(agents, iso, stage, mode, 1, replay_dir, slippi_port, meta)  (LLM:runner.py L185-317)
                 ├─ mode == "sim" → sim.runner.play(agents, stage, games, observer, meta)  (L200-202; NO reenvía seed)
                 │     World(EnvBatch batch=1, action_format="raw")  (LLM:sim/world.py L55-128)
                 │     por frame: begin×2 → step×2 → pub/observer → gs = world.step()  (LLM:sim/runner.py L63-73)
                 └─ Dolphin (Slippi) + libmelee Console  (L208-216: flags por modo)
                       por frame IN_GAME: gs = console.step() (L260) → begin×2 → step×2 → pub/observer  (L279-299)
                 └─ _result(gs_final): (stock, −percent) → GameResult  (L153-169)
            └─ status_of(rec): void (>10 % llamadas fallidas, L13) | slow (realtime y fps < MIN_FPS=50, L14) | ok   L107-113 ✔
       scheduler: error | timeout → data/bench/results.jsonl → bench/ratings.py (Bradley–Terry, ancla cpu:9 = 1500)
```

Hechos clave `[COD]`:
- El **bench nunca usa `sim`**: `game_mode` solo devuelve `realtime|fast`, y las ladders de bot-writer usan `fast`
  (`botwriter/ladder.py` L122).
- El pool que se puntúa **importa** además partidas `lockstep` (pilotos coach/Jev y arena de bots;
  `bench/imports.py` L85-97, A8-009). Un Elo del bench mezcla relojes.
- `--mode sim` solo existe fuera del bench (`LLM:melee_llm/match.py --mode`).

## 2. Modos, relojes y quién espera a quién

| Modo runner | Dolphin | `blocking_input` | Velocidad | Uso | Plazo real para un agente every-frame |
|---|---|---|---|---|---|
| `fast` | headless | True | sin tope (`emulation_speed=0`) | bench (every-frame, untimed) | **ninguno**: el juego espera |
| `realtime` | headless | True | tope 60 fps | bench con participantes wall-clock (`llm_live`, `jev_live`, `coach*`; `WALL_CLOCK` L22) | ninguno. Un `step` lento baja los fps; si la media es < 50 la partida queda `slow` y no puntúa |
| `paused`/`lockstep` | renderizado | True | 1.0 | pilotos importados | ninguno |
| `watch` | renderizado | **False** | 1.0 | solo visualización | sí: un `step` lento pierde frames |
| `sim` | — | — | síncrono | fuera del bench | ninguno |

Fuentes: `LLM:runner.py` L208 `blocking = mode in ("fast","paused","lockstep","realtime")` y L214-215 ✔.
- **Única excepción con plazo:** bot-writer, con `BotAgent(budget_ms=16.0)` (`LLM:botwriter/agent.py` L79). Si la
  respuesta llega tarde, mantiene los mandos previos (L1-7, L186-190).
- **Consecuencia (A7-001, A8):** toda afirmación de «tiempo real» exige un envoltorio propio con plazo. Los relojes de
  reporte son `RT-strict`, `RT-slow` y `untimed` (`evidence/A8/EXPERIMENT_PLAN.md` L50-51).
- **Presupuesto de diseño (A7, INF):** 16,67 ms menos ≈3,3 ms de Dolphin+parseo+runner (`docs/performance.md` L52, en
  otra máquina) dejan ≈13 ms. Con margen, el objetivo es **10 ms p99 en Dolphin**, medido con Dolphin corriendo.

## 3. Interfaz del agente y puntos EXACTOS de integración

`LLM:melee_llm/agents/base.py` L17-47 `[COD]` ✔:
`setup(controller, port, opponent_port)`, `ready()`, `on_game_start(gs, replay)`, `begin(gs)` (trabajo solapable),
`step(gs)` (escribe en `self.controller`, sin valor de retorno), `on_game_end(gs)`, `close()`, `name`.
- La acción es el estado del `melee.Controller` al terminar `step`. El flush lo hace el **siguiente**
  `console.step()` (`LM:melee/console.py` L898-908 ✔) o `world.step()`.
- No hay `reset`, `seed`, presupuesto ni diagnóstico en el contrato. Las latencias las registra cada agente
  (`BotAgent.latency()`, `LLM:bots/agent.py` L167-175).

| Necesidad | Dónde se engancha | Estado |
|---|---|---|
| Política nueva (in-process) | Subclase de `Agent` en `melee_llm/agents/` con `step` (y `begin`) | Interfaz `[COD]`; la clase es `[PROP]` |
| Política con torch / venv propio | Subclase de `BotAgent` (`LLM:bots/agent.py` L69-185) + `bots/bot_<name>.py` con `class Bot` que expone `info()`, `set_steer(d)` y `act(gs, controller, open_loop)` (contrato de `LLM:bots/server.py` L97-134). El hijo recibe el **flujo Slippi crudo** vía `ConsoleTap` (L25-56) y lo re-parsea con su propio libmelee (`server.py Replayer` L41-60) | `[COD]` |
| Registro de spec | `KINDS` en `LLM:players.py` L25-32 | `[COD]` |
| Registro en el bench | `Entrant(...)` en `registry()` (`entrants.py` L80-141); `track="both"` si actúa cada frame (→ `fast`); `gpu=True` si usa CUDA | `[COD]`; receta en `docs/bench.md` «Adding an entrant» |
| Plazo `RT-strict` | Envoltorio estilo bot-writer (`budget_ms`, fallback = mantener mandos) alrededor del agente nuevo | `[PROP]` (el patrón existe) |
| Predictor / world model | **Dentro** de `begin/step` del agente nuevo. Es la única vía que funciona igual en Dolphin y en sim `[INF]` | No hay hook de planificación `[COD]` |
| Planificador con simulador exacto (S0) | Solo en `--mode sim`, pasando el `World` al agente: cambio en `LLM:sim/runner.py` L47-53 (hoy `a.setup(world.controllers[p], …)` L50-51) o en `Agent.setup`. Primitivos: `World.save/restore` (`sim/world.py` L112-125), `EnvBatch.checkpoint/rollback/changed_pages` (`BR:melee_sim/env_batch.py` L428-499; también en el pin `090e54b0`), `Match.checkpoint/rollback/hash/branch` (`BR:melee_brute/match.py` L113-138), `best/improve/Forced/solve` (`BR:melee_brute/search.py` L35/L55/L232/L344) y el wrapper `LLM:solver/takeback.py` | Los primitivos **existen**; el hook **no** `[COD]` |
| Sombra en Dolphin (S0-shadow) | Decodificador de los bytes de `ConsoleTap` + nueva API de paso grabado en melee-brute (§5.3) | **No existe; factible con cambios** (G-01) |
| Entrenamiento offline de encoder/dinámica | `train/farm/` (vectoriza `melee_sim`; motor de `MELEE_SIM`, revisión DESC) y `train/meleebot/build_dataset.py` (parseo `.slp`) | `[DOC]`/`[COD]` |

Mínimo adaptador propuesto (`[PROP]`, A1 CONTRACT §5):
1. `WorldModelAgent(Agent)` o `BotAgent` + `bot_wm.py`.
2. Registrar por frame `decision_frame`, `intended_application_frame = frame+1+D`, tiempos y fallback.
3. Máscara opcional del mando del rival (`I_human`).
4. `GameResult.end_reason` y `seed`, para que las partidas en sim sean reproducibles.

## 4. Observación y regímenes de información

### 4.1 Lo que recibe todo agente: `melee.GameState` (`LM:melee/gamestate.py` L68-180)

| Campo | Contenido |
|---|---|
| Partida | `frame`, `stage`, `menu_state`, `players[port]`, `projectiles`, `distance` |
| Por jugador (`PlayerState`) | `position.x/y`, `percent`, `shield_strength` (≤60), `stock`, `facing`, `action`, `action_frame` (base 1), `hitlag_left`, `hitstun_frames_left`, `jumps_left`, `on_ground`, `speed_*` (5 velocidades), `invulnerable`, `off_stage`, `ecb*`, `is_powershield`, `nana` |
| `controller_state` de **cada** puerto, incluido el rival, en el frame actual (ya aplicado) | Stick principal procesado y crudo (`raw_main_stick`, 0x3B/0x40); **C-stick solo procesado**; **un gatillo lógico copiado a L y R**; botones físicos y procesados (`LM:console.py __pre_frame` L1145-1212; idéntico en 0.47.6) `[COD]` (A8-003) |
| Lo que el `GameState` **descarta** aunque viaja en el flujo | Semilla RNG (Pre-Frame 0x7; Frame Start: `pass` en L1039-1040), gatillos físicos 0x33/0x37, C-stick crudo 0x41/0x42, Game Start 0x13D `[COD]` (G-01 §2) |

En sim, el `GameState` lo construye `StateBuilder` (`LLM:sim/state.py` L76-140) a partir de `MslObservation`. El
`controller_state` sale de la fila raw (`controller_state_from_raw` L59-73, aplicado en L93-95). Diferencias
documentadas `[DOC]` (`docs/simulator.md` L66-73):
- Sin ECB ni `is_powershield`.
- `hitstun_frames_left = 0` fuera de hitstun.
- Los agentes reciben también la cuenta atrás (`frame_id` desde −123).

Observaciones derivadas:
- **LLM/Jev:** `state.observe()`/`render()` (`LLM:melee_llm/state.py` L144-200).
- **Bots aprendidos:** flujo Slippi crudo (en Dolphin `ConsoleTap`; en sim `SlippiTap` + `sim/slippi.Encoder`, que
  escribe 0 en los campos no reportados, `sim/slippi.py` L1-14).

### 4.2 Regímenes (congelados por A8, `EXPERIMENT_PLAN.md` L36-43)

| Régimen | Qué entra | Quién lo usa hoy | Brazos |
|---|---|---|---|
| `I_full` (**primario**) | `GameState` completo, **incluido el `controller_state` del rival** del frame actual | Todo agente del bench salvo bot-writer. El bot propio de melee-llm lo usa con retraso (`train/meleebot/features.py`, A2-032) | Todos los causales. S0 solo aquí y etiquetado PRIV |
| `I_human` (secundario obligatorio) | Lo anterior **sin** el mando del rival | bot-writer (`botwriter/agent.py` L6 «Opponent inputs and identity are hidden»); slippi-ai (`jax/embed.py` L461-463); Faynt y HAL tampoco lo usan | B*, P0, W*. S0 no es ejecutable |
| `PRIV` | Estado completo del motor: snapshot, historial de mandos, RNG | Solo simulador | S0 y S0-shadow, siempre como **cota**, nunca como competidor simétrico |

El contrato de A6 propone `opponent_controller` como `training_metadata` y nunca como observación. Esa propuesta es
`I_human`. El estado real del bench es `I_full`. Ningún contraste mezcla regímenes.

### 4.3 Observación nativa del motor (`BR:API.md` L104-200; `BR:melee_sim/dtypes.py`)

Campos de `MslObservation`:
- `frame_id` (−123 en cuenta atrás) y `frame_pre_random_seed` (**salida**, no entrada).
- `slots[4]`: `pos`, `speed_*`, `percent`, `shield_hp`, `action_id`, `action_frame`, `hitlag/hitstun` u16, `stocks`,
  `facing`, `on_ground`, `jumps_left`, `hurtbox_state`, `invulnerable`.
- `items[15]`, `followers[4]`, `stage{randall, fod_platforms, whispy}`.
- `MslTerminal{done, match_ended, stockout, max_frame_reached}`.

`hitlag_left:<f4>` (ABI v2, 1240 B) existe **solo** desde `d3832724`. No está en el pin `090e54b0` que instala
melee-llm (1208 B) `[COD]`.

## 5. Acción, conversión al motor y G-01

### 5.1 Formatos de salida

| Agente | Formato y camino | Fuente |
|---|---|---|
| Genérico | `melee.Controller`: `press_button/release_button`, `tilt_analog(MAIN\|C, x, y ∈ [0,1])`, `press_shoulder(L\|R, amount)` | `LM:controller.py` L207-288 ✔ |
| LLM/Jev | JSON `{"action", dir, jump, …, frames 1..90, count 1..3}` → macro → `Input(main, c, buttons, l)` por frame → `Executor.step` (reflejos) → `Pad.apply`. **Sin gatillo R analógico** | `LLM:actions.py` L47-51, L614-708, L754-790 |
| Bots aprendidos | `CTRL{main, c, l, r, buttons}` → `apply_controller`; solo A, B, X, Y, Z, L, R, D_UP | `LLM:bots/protocol.py` L1-19; `bots/agent.py` L59-66 |

### 5.2 Conversiones

| Destino | Conversión | Fuente |
|---|---|---|
| Dolphin (libmelee), stick | `raw = round((x−0.5)·160)` → envía `(raw+0.1)/254+0.5` | `LM:controller.py` L11-25 |
| Dolphin (libmelee), gatillo | `raw = round(x·140)` → `(raw+0.1)/255` | `LM:controller.py` L11-25 |
| Dolphin ExiAI headless | Corrige los gatillos con `(raw+255)/510` | `LLM:runner.py` L92-106 |
| Sim | `SimController.raw_input`: sticks `clip(floor((v−0.5)·254), −80, 80)` sobre el valor ya distorsionado; gatillos `clip(floor(fix_analog_trigger(v)·255), 0, 255)` → `MslInput{buttons u16, main_x/y, c_x/c_y i8, l/r u8}` | `LLM:sim/controller.py` L22-56; `BR:API.md` L95-108 |

La paridad de procesado con libmelee es de 30.725 frames salvo 2 `[DOC]`.

### 5.3 G-01: ¿sombra exacta del simulador en vivo sobre Dolphin?

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| ¿Qué viaja en el flujo Slippi? | **Todo lo necesario**: semilla por frame (Frame Start 0x5 desde 2.2.0; Pre-Frame 0x7), stick crudo (0x3B desde 1.2.0, 0x40 desde 3.15.0), **C-stick crudo 0x41/0x42 desde 3.17.0**, gatillos físicos 0x33/0x37 (float; se pasan a byte con `lrintf(v·140)`, `BR:tools/validation/native.c` L1025-1037), semilla inicial de Game Start 0x13D y eventos de escenario (FoD, Whispy) | SPEC `3a85ce8b` L105, L305-342, L547-557 `[DOC]`. melee-llm declara Slippi 3.19.0 con un Pre-Frame de 0x42 bytes (`sim/slippi.py` L3-5, L26-29), sin verificar contra un Dolphin real |
| ¿Qué expone libmelee? | Un `GameState` **insuficiente** (§4.1). Los bytes crudos sí son accesibles: `ConsoleTap.of(console)` (`LLM:bots/agent.py` L25-56) envuelve el atributo **privado** `console._slippstream.dispatch` | `[COD]` |
| ¿Qué exige el simulador? | Por frame: botones físicos, ejes crudos de ambos sticks y gatillos físicos. «Never reconstruct missing human controller bytes from processed floats» (`BR:agent_docs/VALIDATION.md` L78-81). El arranque es solo desde configuración, en el frame −123, sin huecos (L97-100). No hay estado a mitad de partida desde un `GameState` | `[DOC]`/`[COD]` |
| ¿Lo admite la API pública? | **No.** El paso público reinyecta la semilla propia, `frame_seed = match->random_seed`, con `&no_stage_events` (`BR:src/runtime/batch.c` L324-326, igual en `090e54b0`). `MSL_API` (`src/api.h` L247-447) no tiene setter de RNG por frame ni de eventos. El núcleo sí lo soporta (`msl_core_match_step(…, frame_seed, stage_events)`, `scalar.c` L2385-2391), pero solo lo usa el binario de validación | `[COD]` |
| `melee_llm/sim/parity.py` | Usa la API pública con el RNG libre («a replay stays in sync only until the first random choice», L4-6). Si falta el C-stick crudo, lo reconstruye desde el procesado ×80 (L33-37, L62-71), lo que **contradice** la regla de VALIDATION | `[COD]` |
| Veredicto | **FACTIBLE CON CAMBIOS** `[PROP]`, en tres partes: (1) `msl_batch_step_recorded(inputs, frame_seeds, stage_events)` en la API C de melee-brute, pasando el *differential gate*; (2) exponerlo en `EnvBatch.step`; (3) un decodificador en vivo de `ConsoleTap` en melee-llm que avance la sombra en cada Bookend antes de llamar al agente, con la conversión de `native.c` L1025-1075. Además: exigir Slippi ≥ 3.17.0 comprobando los campos reales y abortar si se pierde un frame | G-01 §4 |
| Límites tras los cambios | La sombra reproduce el frame N, no el N+1: el mando futuro del rival sigue necesitando un modelo q. La cobertura validada es de 524 grabaciones en 148 pares, «not exhaustive». Las reglas del bench tienen que estar entre las admitidas (UCF, sin ítems, Stadium congelado). **La tasa de sincronía en partidas del bench es DESC** (puerta G4/H5: ≥ 95 %) | `[INF]`/`[?]` |

Afirmación corregida de A4-027: «la sombra es posible desde el **flujo crudo** con una ampliación de la API del
simulador; no desde el `GameState`». La cifra «15/40 partidas sin divergencia» (`docs/simulator.md` L53) es de **bots
del autor**. El 36/40 humano requiere RNG grabado (L55). No sirve como cobertura de partidas humanas.

## 6. Motor: step, snapshot, rollback

| API | Firma / ubicación | Coste documentado (otra máquina) | Límites |
|---|---|---|---|
| `EnvBatch.step(step_mask=None)` | `BR:melee_sim/env_batch.py` L331-358 ✔ | ~120k frames/s/núcleo a batch 256 (upstream, 9950X3D). En la ruta `World` de melee-llm: ~17.500 frames/s en 1 hilo a load 45 (≈57 µs), sim 0,12 ms/frame + `StateBuilder` 0,23 ms/frame (`docs/simulator.md` L20, L65). 17 µs/frame desde Python con observación (`BRUTE.md` L105, 5950X a load 15-35, tablas anteriores al build actual) | Un batch por hilo a la vez (`API.md` L8-9) |
| `EnvBatch.save(i) → bytes` / `restore(i, b)` | L393-426 ✔ | ~1 MB; ~2,5-4,5 ms (`match.py` L103; `BRUTE.md` L106) | Portable entre índices. Solo admite estados producidos por el propio simulador; «savestates hold addresses» |
| `EnvBatch.checkpoint/rollback/changed_pages` | L428-499 ✔ (también en `090e54b0`); **no existe** en melee-sim-light | «much cheaper» (`API.md` L43-62) | Solo para esa partida hasta reset/restore/copy |
| `Match.checkpoint(level)/rollback(level)/hash()/branch()` | `BR:melee_brute/match.py` L113-138 ✔ | 4,4 / 4,5 / 3,7 µs | **Solo Linux** (`mprotect`/`fork`) |
| `best/improve/Forced/solve` | `BR:melee_brute/search.py` L35/L55/L232/L344 ✔ | 25-30 µs/posición | Válidos solo para el menú y el horizonte dados. El modo look-alike fusiona estados que difieren en lo mantenido (`BRUTE.md` L74-80) |

- **RNG:** `MatchConfig.random_seed`/`configure_match(seed=…)` fija solo la semilla inicial. Después corre libre
  (`scalar.c` L2605) `[COD]`. Que el snapshot incluya el RNG es `[INF]` (A1).
- **`runner.play(mode="sim")` no reenvía `seed`:** la semilla se sortea con `random.getrandbits(32)`
  (`sim/runner.py` L43) y **no se registra** en `GameResult` ✔. Dolphin tampoco se siembra (HAL h2h README L32-36).
  Los «pares» de evaluación no comparten el RNG del juego.
- **Límites del motor** `[DOC]`:
  - Versus, UCF, sin ítems, Pokémon Stadium congelado, **sin CPU** (`_check_agents`).
  - Escenarios FoD, PS, YS, DL, BF, FD.
  - **Sin `.slp`** en sim (`replay=None`).
  - Requiere la ISO NTSC 1.02 para extraer `data/`.
  - melee-brute y melee-sim-light proveen ambos el paquete `melee_sim`: no se pueden instalar juntos.

## 7. Contrato temporal (A6 integrado con el código)

**Reloj:**
- `frame_id` int32 a 60 Hz (16,67 ms). −123 es el primer frame registrado; en el 0 arranca el temporizador.
- Los frames < 0 se marcan `actionable=false`. HAL MDS los conserva; melee-llm los descarta.

**Orden dentro del frame f** (SPEC) `[DOC]`:

| Paso | Contenido | Nivel |
|---|---|---|
| `FrameStart(f)` | semilla | PRIV |
| `PreFrame(f, port)` | Mandos que el juego usa en f, de todos los puertos, más la semilla | Mando propio: cola ya comprometida. Mando del rival: `I_full` o metadato |
| — | El motor procesa f | — |
| `PostFrame(f, port)` | Estado de f. Velocidades desde 3.5.0; hitlag desde 3.8.0 | Observación |
| `ItemUpdate(f)` | Ítems | Observación |
| `FrameBookend(f)` | `latest_finalized_frame` (3.7.0+) | Diagnóstico en vivo |

**Cuándo se ve y cuándo se aplica:**
- libmelee devuelve `gs_f` al recibir `FRAME_BOOKEND(f)` (`LM:console.py` L1051-1069) `[COD]`.
- El agente decide en `step(gs_f)`. El mando se envía en el flush del siguiente `console.step()` y lo registra
  `PreFrame(f+1)`.
- Regla A6: **`application_frame = observation_frame + 1 + D_total`**, con
  `D_total = D_reaction + D_transport + D_compute_consumed` `[PROP]`.
- En sim es directo: `step(gs_t)` → `world.step()` → `gs_{t+1}` (`sim/world.py` L88-102) `[COD]`.
- En Dolphin, el frame exacto de aplicación no está instrumentado `[?]`.

**Alineación de filas en datos** `[COD]`: las cinco canalizaciones (slippi-ai, HAL, MIMIC, melee-llm, libmelee)
guardan `PostFrame(f)` junto a `PreFrame(f)`. El mando de la fila f **ya** influyó en el estado de f. El objetivo de
imitación sin fuga es el mando de f+1 o posterior.

**Dónde entra el retraso hoy** `[COD]`:

| Agente | Mecanismo | Fuente |
|---|---|---|
| HAL | `delay=N` (0..11) → `FrameTiming`, con prefijo de acciones ya enviadas | `bots/bot_hal.py` L75-93 |
| Phillip | `policy.delay` 18-24 frames incrustado en el peso; `console_delay=0` | `bot_phillip.py` L36-42, L64-66 |
| meleebot | steer `delay` 0..12 | — |
| LLM live | Latencia real; descarta las respuestas con `stale > 120` y entre respuestas actúa `_default` | `llm_live.py` L22-24, L48-53, L71-75 |
| Faynt / Reyn | 0 añadido | — |
| Runner | No pasa `online_delay` (0); netplay usa 2 | — |

**No hay cola de retraso común en el runner.** Las unidades difieren entre proyectos: Phillip cuenta pasos × `act_every`;
slippi-ai, Faynt y MIMIC cuentan frames (A2-040).

**Rollback** (solo netplay):

| Proyecto | Copia que conserva |
|---|---|
| libmelee y slippi-ai | La **primera** (`skip_rollback_frames`, L1060-1068) |
| HAL offline y melee-llm | La **última** |

Propuesta A6: LAST para dinámica, y FIRST solo como vista de evaluación. En la partida local del bench no hay
rollback.

**Semántica del mando:**
- El motor calcula flancos y temporizadores a partir del historial de entradas: `post(f)` **no es Markov**
  (`BRUTE.md` L74-80; esta es la cita correcta, la de `VALIDATION.md` L152-158 que usaba A6 es de inputs de CPU,
  A8 fila 23).
- La dinámica necesita el mando de f−1 como contexto.
- Rejillas: stick 1/80, gatillo 1/140.

**Mediciones obligatorias** (A6 `measurements_required` + A7 §2.3) `[PROP]`:
- `t_obs_available` y `t_action_accepted`.
- `t_action_applied`, con su método; si es inferido, `measured=false`.
- Fallbacks y frames consumidos.
- p50/p95/p99 con `perf_counter_ns`.
- En GPU, sincronizar antes de medir.

## 8. Resultado y terminación

- `GameResult{stocks, percent, frames, seconds, winner, agents, replay}` (`LLM:runner.py` L153-161).
- El ganador sale de `(stock, −percent)`; en empate exacto, `None`.
- **No distingue** el fin por stocks, el time-out, `max_frame` ni el truncamiento: en sim `done` agrupa `match_ended`
  y `max_frame_reached=28800`.
- Time-out con stocks empatados en Dolphin: se puntúa el último frame del juego cronometrado y la muerte súbita no
  cuenta (L264-275) ✔.
- Las reglas 4 stocks / 8 min no se fijan en el código de Dolphin (configuración por defecto) `[INF]`.
- Fallos operativos fuera de `GameResult`: `void`/`slow` (`bench/game.py` L107-113) y `error`/`timeout` (scheduler).
- `terminated` y `truncated` separados: **INEXISTENTE**.

## 9. Qué existe y qué no

| Componente | Estado |
|---|---|
| Bucle de partida Dolphin / sim con dos `Agent` | EXISTE |
| Registro de participantes, scheduler, BT | EXISTE (solo Dolphin `fast`/`realtime` + importaciones `lockstep`) |
| Plazo por frame para agentes every-frame | Solo bot-writer (16 ms); para el resto **INEXISTENTE** |
| Encoder / dinámica aprendida / evaluador / planificador como interfaz | **INEXISTENTE** (hay codificadores propios de cada bot en su venv) |
| Snapshot/rollback exacto del simulador | EXISTE (sim, Linux), fuera del bucle de partida |
| Acceso del agente al `World` en sim | **INEXISTENTE** (cambio en `sim/runner.py` L47-53) |
| `GameState` → estado del simulador | **INEXISTENTE** (solo `configure_match`/restore de estados propios) |
| Sombra en vivo sobre Dolphin | **INEXISTENTE**; factible con la API de paso grabado (§5.3) |
| Flujo Slippi crudo accesible a un agente | EXISTE (`ConsoleTap`, atributo privado de libmelee) |
| Semilla del sim registrada por partida | **INEXISTENTE** |
| Separación `terminated`/`truncated`, `end_reason` | **INEXISTENTE** |
| `.slp` en sim | **INEXISTENTE** |

## 10. Incoherencias de revisión que afectan a la integración

1. Runtime (melee-brute `090e54b0`, sin `hitlag_left`) frente a farm (`MELEE_SIM`, revisión DESC, usa `hitlag_left`
   en `train/meleebot/hal_mds.py` L86). Los resultados de farm y de `--mode sim` pueden no ser comparables.
2. E31 declara `d3832724`, pero usa flags que solo existen en `9662ec97` ✔.
3. libmelee instalado 0.47.6 (`2d63e7ee`) frente al clonado 0.47.3. Faynt fija 0.47.3; HAL necesita campos de su
   fork (`docs/bots.md` L24, L82).
4. `docs/simulator.md` L7 atribuye el pin a melee-sim-light: desactualizado ✔.
