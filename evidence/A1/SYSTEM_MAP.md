# A1 · Mapa del sistema Melee Bench: observación → agente → mando → motor → resultado

Agente A1 (plataforma e integración). Corte: 2026-11-19. Lectura de código y documentación; **no se ejecutó ninguna
partida, simulador ni test** (no hay ISO ni datos extraídos en esta máquina). Toda afirmación lleva etiqueta:
`[COD]` INSPECCIONADO_EN_CODIGO, `[DOC]` DOCUMENTADO_POR_AUTOR, `[INF]` INFERENCIA, `[PROP]` PROPUESTA, `[?]` DESCONOCIDO.

## 0. Revisiones usadas (detalle en `revisions.json`)

| Repo | Revisión citada aquí | Nota |
|---|---|---|
| mateo19182/melee-llm | `7e179081c6cbab139d860c998b1452ad3dee047c` (HEAD del clon) | El catálogo (A02–A13, R07) cita `2bf8b0eb…`. Entre ambas solo cambian `docs/experiments/E32*`, `docs/simulator.md` (+2 líneas), `melee_llm/web/training*` y `train/farm/*`: **todas las rutas de runtime citadas abajo son idénticas en las dos** `[COD]` (`git diff --stat 2bf8b0eb 7e179081`). |
| mateo19182/melee-brute | HEAD `9662ec973b9e…` ; pin de melee-llm `090e54b048b7…` ; E31 `d3832724ef67…` | Tres revisiones distintas, en ese orden de ancestría: `090e54b0` ⊂ `d3832724` ⊂ `9662ec97` `[COD]`. |
| kyhavlov/melee-sim-light | `eea7b5fbcd02…` (HEAD) | Es ancestro de las tres revisiones de melee-brute (rama `upstream-main` del fork) `[COD]`. |
| vladfi1/libmelee | HEAD `bce21f0998…` (master, `__version__ = '0.47.3'`) ; lock de melee-llm `melee==0.47.6` (PyPI) = tag `v0.47.6` = `2d63e7ee948d…` (rama `dev`) | El clon no es la versión instalada. `controller.py` idéntico; `console.py`/`slippstream.py` difieren (ver §7). |

Abreviaturas de rutas: `LLM:` = melee-llm@7e179081, `BR:` = melee-brute@9662ec97 (salvo que se indique otra),
`MSL:` = melee-sim-light@eea7b5fb, `LM:` = libmelee@bce21f09.

## 1. Cadena completa en una figura

```
                     ┌──────────── Melee Bench ─────────────┐
 entrants.registry() → scheduler.Bench._run() → subprocess "python -m melee_llm.bench one"
 (LLM:melee_llm/bench/entrants.py L80-141)  (LLM:bench/scheduler.py L362-393)
                                              │ job{spec1,spec2,stage,mode∈{fast,realtime}}
                                              ▼
                       bench/game.py play_one() L299-320 → players.make(spec,FOX) (LLM:players.py L41-55)
                                              ▼
                       runner.play(agents, iso, stage, mode, …) (LLM:runner.py L185-317)
                 ┌────────────── mode != "sim" ──────────────┐     ┌─────── mode == "sim" (L200-202) ───────┐
                 │ Dolphin (Slippi) + libmelee Console        │     │ sim/runner.play (LLM:sim/runner.py L31-89) │
                 │  gs = console.step()  (flush de mandos)    │     │  World(EnvBatch batch=1, action="raw")     │
                 │  agent.begin(gs) ×2 ; agent.step(gs) ×2    │     │  agent.begin(gs) ×2 ; agent.step(gs) ×2    │
                 │  step() escribe en melee.Controller /      │     │  gs = world.step(): SimController.raw_input│
                 │  ExiAIController (pipe → Dolphin)          │     │  → EnvBatch.step → StateBuilder.build      │
                 └────────────────────────────────────────────┘     └────────────────────────────────────────────┘
                                              ▼
                 _result(gs_final): stocks, luego -percent → GameResult (LLM:runner.py L153-169)
                                              ▼
            status_of(): ok | void (>10 % llamadas fallidas) | slow (<50 fps en realtime)  (bench/game.py L323-329)
            scheduler: error | timeout (proceso hijo)  → data/bench/results.jsonl → bench/ratings.py (BT, cpu:9=1500)
```

## 2. Runner y bucle de partida

### 2.1 Dolphin: `LLM:melee_llm/runner.py`
- `play(agents, iso, stage=BATTLEFIELD, mode="watch", games=1, replay_dir, slippi_port=51441, observer, meta) -> list[GameResult]` L185-317 `[COD]`.
- Modos → binario Dolphin `DOLPHIN` L24-30 y flags en L208-216 `[COD]`:
  - `fast`: headless, `emulation_speed=0` (sin tope), `blocking_input=True`.
  - `realtime`: headless, `emulation_speed=1.0` (tope 60 fps), `blocking_input=True`.
  - `paused`/`lockstep`: renderizado, `emulation_speed=1.0`, `blocking_input=True`.
  - `watch`: renderizado, `blocking_input=False` (Dolphin no espera al bot).
  - **Hallazgo** `[COD]`: en `realtime` Dolphin *sí* bloquea esperando el mando de cada frame (L208). La afirmación
    de `docs/bench.md` L19-25 «The game never waits» solo se cumple porque `LiveLLM.step` no bloquea (piensa en
    un hilo, `LLM:agents/llm_live.py` L36-83); un agente lento en `step` ralentiza la partida y la marca `slow`
    (`bench/game.py` L230, L327-328) en lugar de perder frames.
- Controladores: `ExiAIController` para el build headless (corrige la conversión de gatillos: `round(amount*140)`
  y luego `(raw+255)/510`, L92-106) y `melee.Controller` para el renderizado (L218-219) `[COD]`.
- Orden por frame en juego (L279-300) `[COD]`: `gs = console.step()` (libmelee hace `controller.flush()` de los
  mandos escritos en el frame anterior, `LM:melee/console.py` L898-908) → `begin(gs)` de cada agente no-CPU →
  `step(gs)` de cada agente → `pub.frame(gs)` → `observer("frame",{gs})`.
- Fin de partida (L248-257, L301-303): al salir de `IN_GAME`/`SUDDEN_DEATH` se puntúa el último `gs`. Time-out con
  stocks empatados → Muerte súbita como juego nuevo: se puntúa el juego cronometrado en su último frame (L264-268) y
  la muerte súbita se juega sin contar (L269-275) `[COD]`.
- Menús: `melee.MenuHelper.menu_helper_simple(...)` (L304-307); comprueba niveles de CPU (L178-182, L282-284) `[COD]`.
  **Las reglas 4 stocks / 8 min no se fijan en este código**: dependen de la configuración por defecto de
  Slippi/Melee que deja libmelee `[INF]`; en sim se fijan con `MatchConfig.stocks=4` (default, `BR:melee_sim/config.py`
  L63-73) y `max_frame=TIMER_FRAMES=28800` (`LLM:sim/world.py` L19) `[COD]`.

### 2.2 Simulador: `LLM:melee_llm/sim/`
- `runner.play(mode="sim")` despacha a `sim.runner.play(agents, stage, games, seed=None, observer, meta)`
  (`LLM:runner.py` L200-202; `LLM:sim/runner.py` L31-89) `[COD]`. Desde `runner.play` **no se puede pasar `seed`**
  (la llamada L202 no lo reenvía): la semilla se sortea con `random.getrandbits(32)` (sim/runner L43) `[COD]`.
- Rechaza CPU (`_check_agents` L25-28) y escenarios fuera de `SIM_STAGE` (FoD, PS, YS, DL, BF, FD;
  `LLM:sim/state.py` L25-28) `[COD]`.
- Bucle (sim/runner L55-79) `[COD]`: `gs = world.reset(seed+game)` → mientras `not world.done`: `begin`×2, `step`×2,
  `pub.frame`, `observer`, `gs = world.step()`. Los agentes reciben también los 123 frames de cuenta atrás
  (`frame_id` empieza en −123, `BR:API.md` L128), a diferencia de Dolphin, donde solo se llama en frames `IN_GAME`
  `[INF]` (no verificado si libmelee marca la cuenta atrás como `IN_GAME`).
- `World` (`LLM:sim/world.py` L55-128) `[COD]`: `EnvBatch(batch_size=1, length=1024, action_format="raw",
  data_dir=MSL_DATA_DIR)` L71; `reset(seed)` L74-86; `step()` L88-102 escribe la fila raw de cada
  `SimController` (`raw_input`) → `env.step()` → `StateBuilder.build(obs,row)` → `done = terminal["done"]`;
  `save() -> Snapshot(state: bytes, gs)` L112-113 usa `EnvBatch.save` (savestate serializado, no el checkpoint
  rápido); `restore(snap)` L115-125 suelta los mandos.
- `bench` **nunca usa `sim`**: `entrants.game_mode()` devuelve solo `realtime` o `fast` (`LLM:bench/entrants.py`
  L189-191) `[COD]`. `--mode sim` existe en `melee_llm.match` (`LLM:melee_llm/match.py` `--mode` choices
  `[*DOLPHIN, "sim"]`) `[COD]`.

## 3. Registro de participantes (`LLM:melee_llm/bench/entrants.py`)

- `@dataclass Entrant(id, label, category, track, spec, about, provider="none", active=True, gpu=False,
  group="main", aliases=[])` L32-56; `kind` = prefijo del `spec`; `wall_clock` = `kind ∈ WALL_CLOCK =
  {llm_live, jev_live, coach, coach_jev}` (L22) `[COD]`.
- `registry()` L80-141: CPU 1-9, Phillip silver/plat/gm, `hal:MASTER`, `mimic`, `faynt`, `reyn`, baselines
  retiradas, `_written()` (sesiones bot-writer ≥10 min) L59-77, LLM live/paused/coach ×4 modelos, Jev, controles,
  `human:mateo` (inactivo, `spec=None`), `ablations()` L147-169 `[COD]`.
- `track`: `realtime | untimed | both` (L16, L37). `game_track(a,b)` L180-186 decide si dos entrants se cruzan;
  `game_mode(a,b)` L189-191 elige el modo Dolphin `[COD]`.
- `spec` se resuelve con `players.make(spec, character)` (`LLM:players.py` L41-55) contra `KINDS` (L25-32) o los
  casos especiales `cpu`, `bot`, `baseline` `[COD]`. `bench/game.make_agent` (L233-244) fuerza siempre
  `melee.Character.FOX` `[COD]`.

## 4. Interfaz que implementa un agente (`LLM:melee_llm/agents/base.py` L16-47)

```python
@dataclass
class Agent:
    character: melee.Character = FOX; cpu_level: int = 0; costume: int = 0
    def setup(self, controller: melee.Controller, port: int, opponent_port: int) -> None
    def ready(self) -> None                      # bloquear hasta cargar
    def on_game_start(self, gs: melee.GameState, replay: Path | None) -> None
    def begin(self, gs: melee.GameState) -> None # trabajo solapable con el rival
    def step(self, gs: melee.GameState) -> None  # escribe en self.controller; el runner hace flush
    def on_game_end(self, gs: melee.GameState | None) -> None
    def close(self) -> None
    name: property
```
`[COD]`. No hay valor de retorno: **la acción es el estado del `melee.Controller` al terminar `step`**. No hay
`reset`, `seed`, presupuesto ni diagnóstico de tiempo en el contrato; los agentes que miden latencia lo hacen por
su cuenta (`BotAgent.latency()`, `LLM:bots/agent.py` L167-175; logs de decisión LLM) `[COD]`.

Plazos `[DOC]` (`LLM:docs/architecture.md` L60; docstring `base.py` L1-7): en `watch` `step` debe volver en
~16 ms; en los demás modos el juego espera. Bot-writer impone 16 ms de presupuesto propio (`BotAgent(budget_ms=16.0)`,
`LLM:melee_llm/botwriter/agent.py` L79; respuesta tardía → mantiene mandos previos, L1-7, L186-190) `[COD]`.

## 5. Punto EXACTO de integración

### 5.1 (a) Política nueva

| Paso | Archivo · símbolo · líneas | Estado |
|---|---|---|
| Clase agente | Subclase de `Agent` (`LLM:melee_llm/agents/base.py` L16-47) en un módulo nuevo, implementando `step` (y `begin` si solapa). Si necesita torch/venv propio: subclase de `BotAgent` (`LLM:melee_llm/bots/agent.py` L69-185) + `bot_<name>.py` con `class Bot(init)` exponiendo `info()`, `set_steer(d)`, `act(gs, controller, open_loop)` (contrato que usa `LLM:bots/server.py` L97-134) | `[COD]` interfaz existente; la clase nueva es `[PROP]` |
| Registro de spec | Entrada en `KINDS` (`LLM:melee_llm/players.py` L25-32) | `[COD]` punto existente |
| Registro en el bench | `Entrant(...)` dentro de `registry()` (`LLM:melee_llm/bench/entrants.py` L80-141), `track="both"` si actúa cada frame (→ modo `fast`), `gpu=True` si usa CUDA | `[COD]` punto; `[DOC]` receta en `docs/bench.md` "Adding an entrant" |
| Lanzador web (opcional) | `specs.catalog()` en `LLM:melee_llm/web/specs.py` | `[DOC]` `docs/architecture.md` "Adding things" |

### 5.2 (b) Predictor / planificador con modelo del mundo

**No existe ningún hook de planificación, de modelo del mundo ni de acceso del agente al motor durante una partida**
`[COD]` (búsqueda de `World(` en `melee_llm/`, `train/`, `tests/`: solo `sim/runner.py` L47, `solver/game.py` L104 y
tests). Opciones reales:

1. **Dentro de `Agent.step`/`begin`** del agente nuevo (mismo punto que 5.1). El predictor recibe solo `gs`
   (libmelee `GameState`). Es la única vía que funciona igual en Dolphin y sim `[INF]`.
2. **Planificador con el simulador como modelo (S0)**: los primitivos existen fuera del bucle de partida:
   `World.save/restore` (`LLM:sim/world.py` L112-125), `EnvBatch.checkpoint/rollback/changed_pages`
   (`BR:melee_sim/env_batch.py` L428-499), `melee_brute.Match.checkpoint/rollback/branch/hash`
   (`BR:melee_brute/match.py` L113-138), búsquedas `best/improve/Forced/solve` (`BR:melee_brute/search.py`
   L35, L55, L232, L344) y el wrapper `LLM:melee_llm/solver/takeback.py` (`make_env`, `Rollback`). **Pero:**
   - El agente no recibe el `World` (solo `world.controllers[p]`, `LLM:sim/runner.py` L50-51) `[COD]`.
   - No hay API para construir un estado del simulador a partir de un `GameState` arbitrario (solo
     `configure_match` con personaje/escenario/semilla/`start_percent`, `BR:melee_sim/config.py` L52-73) `[COD]`.
     En Dolphin, un planificador con simulador tendría que reconstruir la partida desde inputs + semilla, y el RNG
     del simulador no es el de Dolphin (`LLM:docs/simulator.md` L72) `[DOC]`.
   - Por tanto, **un `simulator_snapshot` accesible a un planificador durante una partida del bench es INEXISTENTE**;
     solo es viable en `--mode sim` pasando el `World` al agente, lo cual exige cambiar `sim/runner.play`
     (L47-53) o `Agent.setup` `[PROP]`.
3. **Fuera de línea** (farm/entrenamiento): `train/farm/` vectoriza `melee_sim` y reconstruye observaciones por bot
   (`LLM:docs/simulator.md` "Farm") `[DOC]`; es el lugar natural para entrenar un encoder/dinámica, no para evaluarlo
   en el bench `[INF]`.

## 6. Observación

### 6.1 Lo que recibe todo agente: `melee.GameState` (libmelee)
`LM:melee/gamestate.py` L68-180 `[COD]`. Campos usados por el código de melee-llm: `frame:int` (frames, puede ser
negativo), `stage:Stage`, `menu_state`, `players: dict[port, PlayerState]`, `projectiles`, `distance:float`.
`PlayerState`: `character`, `position.x/.y` (float, unidades de Melee; y=0 suelo principal), `percent` (float),
`shield_strength` (float, máx 60), `stock` (int), `facing` (bool, True=derecha), `action` (`Action` o
`UnknownAnimation`), `action_frame` (int, indexado desde 1), `invulnerable`, `hitlag_left`, `hitstun_frames_left`,
`jumps_left`, `on_ground`, `speed_air_x_self`, `speed_y_self`, `speed_x_attack`, `speed_y_attack`,
`speed_ground_x_self` (float, unidades/frame), `off_stage`, `moonwalkwarning`, `controller_state`, `ecb*`,
`is_powershield`, `nana`.

**Privilegio a vigilar** `[COD]`: `controller_state` del **rival** viene en el `GameState` en ambos modos —
Dolphin lo rellena desde el evento pre-frame de Slippi; sim lo construye desde la fila raw del frame
(`LLM:sim/state.py` L93-95, `controller_state_from_raw` L59-73). Son inputs ya aplicados, no futuros, pero son
información que un humano no ve. Bot-writer los oculta explícitamente (`LLM:botwriter/agent.py` L5-6); el resto
de agentes los recibe.

### 6.2 Construcción en sim (`LLM:sim/state.py StateBuilder` L76-140) `[COD]`
Copia campo a campo de la fila `MslObservation`: `pos_x/pos_y`, `action_id` (con +1 para acciones indexadas en 0),
`percent`, `shield_hp`, `stocks`, `hitstun`, `hitlag` (u16 → `int`), `on_ground`, `jumps_left`, `invulnerable`,
velocidades (float32); calcula `moonwalkwarning`, `off_stage`, `distance`, proyectiles desde `items`, plataformas
de FoD. Diferencias documentadas: sin ECB, sin `is_powershield`, `hitstun_frames_left=0` fuera de hitstun,
`controller_status` siempre HUMAN `[COD]`/`[DOC]` (`docs/simulator.md` L66-73).

### 6.3 Observaciones derivadas
- LLM/Jev: `state.observe(gs, port, opp_port) -> dict` (`LLM:melee_llm/state.py` L144-158; `player_obs` L128-141)
  con `x,y` redondeados a 0,1, `vx,vy` a 0,01, `pct` entero, `time_left = 480 − max(frame,0)//60` s, `rel`,
  3 proyectiles más cercanos; `render()` → texto ~120-200 tokens (L184-200); `EventTracker` (L203-256) `[COD]`.
- Bots aprendidos: **no reciben el `GameState` del padre**; reciben los eventos Slippi crudos (Dolphin:
  `ConsoleTap`, `LLM:bots/agent.py` L25-56; sim: `SlippiTap` + `sim/slippi.Encoder`, `LLM:sim/world.py` L32-46,
  `LLM:sim/slippi.py` L107) y los reparsean con su propio libmelee (`LLM:bots/server.py Replayer` L41-60) `[COD]`.
  En sim, campos no reportados se escriben como 0 (`LLM:sim/slippi.py` L1-14) `[COD]`.

### 6.4 Observación nativa del motor (`BR:API.md` L104-200; `BR:melee_sim/dtypes.py`) `[DOC]`/`[COD]`
`frame_id:int32` (−123 en cuenta atrás), `frame_pre_random_seed:uint32` (**valor del RNG expuesto en la
observación**), `stage_id`, `slots[4]` relativos al viewpoint (`present, source_player, pos_x/y, speed_*, percent
0..999.9, shield_hp 0..60, action_id u16, action_frame i16, hitlag/hitstun u16, char_id, stocks, facing, on_ground,
jumps_left, hurtbox_state, invulnerable`), `items[15]`, `followers[4]`, `stage{randall, fod_platforms, whispy}`;
`MslTerminal{frame_id, stage_id, done, match_ended, stockout, max_frame_reached}` (L189-200). En `9662ec97`/`d3832724`
se añade `hitlag_left:<f4>` (tamaño 1208→1240 B, ABI v2); **no existe en el pin `090e54b0`** `[COD]`.

## 7. Acción y conversión a mando del motor

### 7.1 Formato que emite un agente
- Genérico: llamadas a `melee.Controller` — `press_button/release_button(Button)`, `tilt_analog(BUTTON_MAIN|C, x, y)`
  con x,y ∈ [0,1] (0,5 neutro), `press_shoulder(L|R, amount∈[0,1])` (`LM:melee/controller.py` L240-288) `[COD]`.
- LLM/Jev: decisión JSON `{"action": <ACTIONS>, dir, jump, fastfall, throw, then, ledge, frames 1..90, count 1..3}`
  (`LLM:actions.py ACTIONS` L614-646, `SCHEMA_FIELDS` L648-657, `tool_schema` L660-674, `make` L688-708) → macro
  generador que produce un `Input(main, c, buttons, l)` por frame (L47-51, `Macro` L129) → `Executor.step(gs)`
  (L774-790) con reflejos (tech, mash, recover; L754-769) y `max_frames` por macro → `Pad.apply` escribe solo
  diferencias (L67-87). **No hay gatillo R analógico en `Input`** (solo `l`) `[COD]`.
- Bots aprendidos: dict `CTRL{main:(x,y), c:(x,y), l, r, buttons:[names]}` en convención libmelee
  (`LLM:bots/protocol.py` L1-19) → `apply_controller` (`LLM:bots/agent.py` L59-66); solo A,B,X,Y,Z,L,R,D_UP
  (`APPLIED_BUTTONS` L21-22) `[COD]`.

### 7.2 Dolphin
libmelee pre-distorsiona: `fix_analog_stick(x)`: `raw=round((x−0.5)*160)`, envía `(raw+0.1)/254+0.5`
(`LM:controller.py` L11-19); `fix_analog_trigger(x)`: `raw=round(x*140)`, envía `(raw+0.1)/255` (L21-25). El build
ExiAI headless leía mal los gatillos; `ExiAIController.press_shoulder` envía `(raw+255)/510` con
`raw=round(amount*140)` (`LLM:runner.py` L92-106; medido en E30 según el docstring) `[COD]`. `flush()` envía
`FLUSH` y copia `current→prev` (`LM:controller.py` L367-378); el runner no lo llama: lo hace `console.step()`
(`LM:console.py` L905-908) `[COD]`.

### 7.3 `--mode sim`
`SimController(melee.Controller)` sin pipe (`LLM:sim/controller.py` L30-56). `raw_input(out)` (L49-56) `[COD]`:
`buttons` = OR de bits (`_BUTTON_BITS`, `LLM:sim/state.py` L31-36); sticks `clip(floor((v−0.5)*254), −80, 80)`
(L22-23) aplicados a los valores ya distorsionados por libmelee; gatillos `clip(floor(fix_analog_trigger(v)*255),
0, 255)` (L26-27, L55-56). Llega al motor como `MslInput.players[i] {buttons u16, main_x/y i8 −80..80, c_x/y,
l/r u8 0..255}` (`BR:API.md` L95-102). melee_brute directo: `pad(buttons, x, y, cx, cy, l, r)` con los mismos
rangos crudos (`BR:melee_brute/match.py` L24-25). Paridad de sticks/gatillos procesados con libmelee: 30.725
frames salvo 2 (`LLM:docs/simulator.md` "Learned bots in it") `[DOC]`.

## 8. Snapshot / rollback / step

| API | Firma | Coste documentado | Estado incluido | Límites |
|---|---|---|---|---|
| `EnvBatch.step(step_mask=None)` | `BR:melee_sim/env_batch.py` L331-358 (`MSL:` L330) | ~120k frames/s/núcleo batch 256, 9950X3D (`MSL:README.md` L26-29, autor); ~17.500 frames/s 1 hilo en la máquina de melee-llm (`LLM:docs/simulator.md` L20); 17 µs/frame desde Python con observación (`BR:BRUTE.md` L105) | Escribe `gamestate[t+1]`, `terminal[t]` | Un batch por hilo a la vez (`BR:API.md` L8-9, L238-241) |
| `EnvBatch.save(i) -> bytes` / `restore(i, bytes)` | `BR:` L393-426 (`MSL:` L392-425); C `msl_batch_save/restore` (`BR:src/api.h` L305-308) | ~1 MB, 2,5 ms (`BR:melee_brute/match.py` L103); «save and restore ~4.500 µs» (`BR:BRUTE.md` L106); «lane copy ~300 µs» (`LLM:docs/simulator.md` L28) | «complete gameplay state plus public episode/viewpoint metadata», restaurable en cualquier índice (`BR:API.md` L23-25); cabecera con `game_data_fingerprint`, `layout_hash` (`BR:src/runtime/savestate.c` L24-46) | Portable entre índices; versión de savestate 4 |
| `EnvBatch.checkpoint(i, out=None, pages=None)` / `rollback(i, ckpt, pages=None)` / `changed_pages(i, ckpt)` | `BR:melee_sim/env_batch.py` L428-499 (idéntico en `090e54b0`); **no existe en `MSL:`** | no medido aparte; la doc lo llama «much cheaper» (`BR:API.md` L43-62) | Copia en sitio de la memoria de la partida, páginas de 4 KiB | Válido solo para esa partida hasta reset/restore/copy; parcial exacto solo si se listan todas las páginas cambiadas |
| `msl_brute_create/checkpoint/rollback/hash/reset` · `Match.checkpoint(level)/rollback(level)/branch()/hash()` | `BR:src/api.h` L310-320, L403-409; `BR:melee_brute/match.py` L113-138 | 4,4/4,5 µs checkpoint/rollback, hash 3,7 µs, Ryzen 5950X cargado (`BR:BRUTE.md` L100-106) | Exacto por construcción (protección de escritura, copia de páginas escritas); test de savestate byte-idéntico tras rollback+mismos inputs (`BR:tests/test_brute.py` L26) | **Solo Linux** (`mprotect`/`fork`; fuera de Linux devuelve `MSL_INVALID_STATE`, `api.h` L310); destruir antes del batch; `msl_brute_reset` tras reset/restore/copy |
| Búsquedas `best/improve/Forced.win/safe/solve` | `BR:melee_brute/search.py` L35, L55, L232-329, L344 | 25-30 µs/posición (`BR:BRUTE.md` L86-98) | — | Pruebas válidas solo para menú y horizonte dados; modo look-alike puede fusionar estados distintos (L74-80) |

**RNG** `[DOC]`+`[INF]`: la semilla es `MatchConfig.seed`/`random_seed` (`BR:API.md` L72) y la observación expone
`frame_pre_random_seed`. Que el savestate/checkpoint incluya el estado del RNG se infiere de «complete gameplay
state» y del test de savestate byte-idéntico; no localicé el símbolo del RNG en la memoria serializada `[INF]`.
El RNG del simulador **no** se re-siembra por frame como Slippi online (`LLM:docs/experiments/E31-sim-faithful.md`
"What this means") `[DOC]`.

**Límites del motor** `[DOC]`:
- Upstream: «full playable roster and all six competitive stages, in singles and teams» (`MSL:README.md` L12-13);
  enum de 26 personajes y 6 escenarios (`BR:melee_sim/config.py` L7-41) `[COD]`.
- melee-brute/melee-llm: solo Versus, UCF, sin ítems, Pokémon Stadium congelado, **sin CPU** (`BR:BRUTE.md` L149;
  `LLM:docs/simulator.md` L33-34, L68) — `sim/runner._check_agents` lo impone `[COD]`.
- **Sin `.slp`**: `GameResult.replay=None` en sim (`LLM:docs/simulator.md` L69; `sim/runner.py` L57-61) `[COD]`.
- **ISO NTSC 1.02 (GALE01 rev 2)** para extraer `data/` (`MSL:README.md` L47-50; `BR:BRUTE.md` L13) `[DOC]`.
- Toolchain: Python ≥3.11, GCC, Make, binutils (`MSL:README.md` L33); take-back y búsqueda solo Linux `[DOC]`.
- Sin ECB ni flag de powershield; sin Sudden Death; time-out por `max_frame` puntuado por stocks y porcentaje
  (`LLM:docs/simulator.md` L66-73) `[DOC]`.
- melee-brute y melee-sim-light proveen ambos el paquete `melee_sim`: no se pueden instalar juntos (`BR:BRUTE.md` L19).

## 9. Relojes y delay

| Reloj (bench) | Modo runner | Qué espera a quién | Código |
|---|---|---|---|
| Real time (`llm_live`, `jev_live`, `coach*`) | `realtime` | Dolphin a 60 fps máx. **y** bloqueado por el mando de cada frame; el agente debe devolver `step` rápido y pensar en otro hilo | `runner.py` L208-216; `llm_live.py` L36-83 |
| Untimed (`llm_paused`, `jev_paused`) | `fast` | Dolphin sin tope y bloqueado; `step` bloquea durante la llamada al LLM (`latency_frames=0`) | `llm_paused.py` L22-37 |
| Every frame (CPU, aprendidos, escritos) | `fast` (si ningún rival es wall-clock) o `realtime` | Igual que arriba; el resultado no depende del reloj salvo por el presupuesto de 16 ms de bot-writer | `entrants.py` L189-191; `bench.md` L17-29 |
| (fuera del bench) `watch` | rendered, `blocking_input=False` | Dolphin no espera: un `step` lento pierde frames | `runner.py` L208 |
| (fuera del bench) `sim` | — | Paso a paso síncrono: el juego avanza cuando los dos `step` vuelven | `sim/runner.py` L63-73 |

**Alineación base** `[DOC]`+`[COD]`: con delay d, la acción decidida en el frame t la lee el juego en t+d+1
(`LLM:docs/delay.md` L7). En sim se ve directamente: los mandos escritos en `step(gs_t)` se leen en el siguiente
`world.step()` y producen `gs_{t+1}` (`LLM:sim/world.py` L88-102). En Dolphin, el flush ocurre en el siguiente
`console.step()` (`LM:console.py` L905-908) `[COD]`; el frame exacto en que Dolphin aplica el pad no se mide en el
código `[?]`.

**Dónde se introduce el delay** `[COD]`:
- HAL: `delay=N` (0..11) en el spec → `FrameTiming(delay, 0, delay, min(2,12−delay), min(delay+4,12))`, prefijo fijo
  de las acciones ya enviadas (`LLM:bots/bot_hal.py` L75-93; spec en `bots/__init__.py` L13-30). Opción `ahead`
  devuelve la acción para t+1+delay y deja que el llamador la entregue antes.
- Phillip: delay interno del checkpoint `policy.delay` (18-24 frames) con `console_delay=0`
  (`LLM:bots/bot_phillip.py` L36-42, L64-66).
- meleebot: steer `delay` 0..12 (`bots/__init__.py` L84-100; `bot_meleebot.py` L34).
- LLM live: latencia de red/modelo efectiva; respuestas con `stale > max_stale` (120 por defecto) se descartan
  (`llm_live.py` L22-24, L71-75); entre respuestas actúa el `_default` (dash dance/escudo) (L48-53).
- Dolphin `online_delay`: el runner no lo pasa (default libmelee 0, `LM:console.py` L350); netplay usa 2
  (`LLM:netplay/host.py` L49) `[COD]`.
- Faynt y Reyn: «zero added delay» (`bot_faynt.py` L5, `bot_reyn.py` L4) `[COD]`.

## 10. Resultado y terminación

`_result(gs, frames, t0, agents)` (`LLM:runner.py` L164-169): ganador por `(stock, −percent)`; empate exacto →
`winner=None`. `GameResult{stocks, percent, frames, seconds, winner, agents, replay}` (L153-161). **No distingue**
fin por stocks, time-out del reloj, `max_frame` externo, ni truncamiento: en sim `world.done` agrupa
`match_ended` y `max_frame_reached` (`LLM:sim/world.py` L100; `BR:src/runtime/observation.c` L524-558) `[COD]`.
Fallos operativos se registran fuera del `GameResult`: `void`/`slow` (`bench/game.py` L323-329), `error`/`timeout`
del proceso (`bench/scheduler.py` L362-393, `TIMEOUT` L51) `[COD]`.

## 11. Contradicciones y huecos detectados

1. `LLM:docs/simulator.md` L7 dice que `pyproject.toml` fija melee-sim-light `eea7b5fb`; el `pyproject.toml` real
   fija **melee-brute `090e54b0`** (`[tool.uv.sources]`) y `uv.lock` coincide; el párrafo L28 del mismo doc lo
   reconoce `[COD]`.
2. E31 afirma compilar melee-brute `d3832724` pero usa `--played-on`/`--no-ucf` «de PR #19», que solo existen en
   `9662ec97` (0 apariciones en `090e54b0` y `d3832724`, 4 en `9662ec97` de `tools/validation/validate_replay.py`)
   `[COD]`. La farm carga el simulador de `MELEE_SIM` (`/mnt/data/melee/native/melee-brute`, `train/farm/common.py`
   L24), checkout cuya revisión no consta en el repo `[?]`.
3. Runtime de melee-llm (pin `090e54b0`) no tiene `hitlag_left` ni ABI v2; HAL en la farm sí usa `hitlag_left`
   (`train/meleebot/hal_mds.py` L86) vía el checkout `MELEE_SIM` `[COD]`. Los resultados de farm (E28-E32) y del
   runtime `--mode sim` pueden venir de motores distintos `[INF]`.
4. libmelee: el clon (master 0.47.3) no es lo instalado (0.47.6 de la rama `dev`) `[COD]`.
5. `bench.md` «The game never waits» en real time vs `blocking_input=True` (§2.1) `[COD]`.
6. `sim/runner.play` admite `seed`, pero `runner.play(mode="sim")` no lo reenvía: partidas sim lanzadas vía
   `match.py`/runner no son reproducibles salvo que se registre la semilla aleatoria (no se registra en `GameResult`)
   `[COD]`.
7. `evidence/A6/timing_contract.json` no existe aún: `CONTRACT.md` deja los tiempos como pendientes de integrar.
