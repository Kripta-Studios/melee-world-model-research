# G-01 (parte A, sin ISO): ¿es viable un «simulador sombra» en vivo sobre Dolphin?

Autor: A8 (verificación acotada). Fecha: 2026-11-19. Solo lectura de fuentes; nada ejecutado, sin ISO.
Afirmación auditada: A4-027 (declarada FALSA tal como está escrita en `CRITICAL_REVIEW.md` fila 25).

Revisiones leídas:

| Fuente | Revisión | Papel |
|---|---|---|
| project-slippi/slippi-wiki `SPEC.md` | `3a85ce8b1f2dae1b487b2529a43c80f5de5885a3` (master, raw) | formato del flujo/replay |
| vladfi1/libmelee | `bce21f09984b286e6d36bfd2939e4cd4691f94c2` (HEAD master, 0.47.3) | clon |
| vladfi1/libmelee | `2d63e7ee948d77ab4e73165ed4c73abbe3ba121b` (tag v0.47.6, rama dev) | lo que instala melee-llm (`evidence/A1/revisions.json`) |
| mateo19182/melee-brute | `9662ec973b9e077ff7b0ff89d6db950f53c11653` (HEAD) y `090e54b048b7d51e82f9f6b551046c2ca8b130c7` (pin de melee-llm) | simulador |
| kyhavlov/melee-sim-light | `eea7b5fbcd0243baf4c1956d52f3e1d0f536edc4` | simulador ancestro |
| mateo19182/melee-llm | `7e179081c6cbab139d860c998b1452ad3dee047c` | harness/bench |

---

## 1. Qué trae el flujo Slippi (spec oficial)

Fuente: https://github.com/project-slippi/slippi-wiki/blob/3a85ce8b1f2dae1b487b2529a43c80f5de5885a3/SPEC.md
[DOCUMENTADO_POR_AUTOR]

**Pre-Frame Update (0x37)**, extracto de la tabla (SPEC.md L315-342). La spec dice: «Information is collected right
before controller inputs are used to figure out the character's next action». Un evento por frame y por personaje.

| Offset | Campo | Tipo | Desde |
|---|---|---|---|
| 0x7 | Random Seed («The random seed at this point») | uint32 | 0.1.0 |
| 0x19 / 0x1D | Joystick X/Y (procesado, [-1,1]) | float | 0.1.0 |
| 0x21 / 0x25 | C-Stick X/Y (procesado, [-1,1]) | float | 0.1.0 |
| 0x29 | Trigger (procesado, [0,1]) | float | 0.1.0 |
| 0x2D | Processed Buttons | uint32 | 0.1.0 |
| 0x31 | Physical Buttons | uint16 | 0.1.0 |
| 0x33 | Physical L Trigger | float | 0.1.0 |
| 0x37 | Physical R Trigger | float | 0.1.0 |
| 0x3B | X analog for UCF («Raw X axis analog controller input») | int8 | 1.2.0 |
| 0x40 | Y analog for UCF («Raw Y axis analog controller input») | int8 | 3.15.0 |
| 0x41 | X c-stick for UCF («Raw X axis c-stick input») | int8 | 3.17.0 |
| 0x42 | Y c-stick for UCF («Raw Y axis c-stick input») | int8 | 3.17.0 |

Además:
- **Frame Start (0x3A)**, L305-313: «event added to transfer RNG seed at the very beginning of a frame's processing
  to prevent desyncs». `0x5 Random Seed uint32`, desde **2.2.0**.
- **Game Start (0x36)**, L105: `0x13D Random Seed uint32` «The random seed before the game start», desde 0.1.0.
- Eventos de escenario necesarios para el simulador en ciertos escenarios: FOD Platforms (L547) y Whispy Blow
  Direction (L557).
- Frame Bookend (L538-545): `Latest Finalized Frame` (3.7.0); sin rollback es igual al número de frame.

Respuesta a la pregunta 1: **sí, todo está**. Semilla RNG por frame (Frame Start desde 2.2.0 y Pre-Frame desde
0.1.0), ejes crudos del stick principal (X desde 1.2.0, Y desde 3.15.0), C-stick crudo (desde **3.17.0**) y gatillos
físicos L/R (floats desde 0.1.0). El único requisito de versión no trivial es ≥ 3.17.0 para el C-stick crudo.
melee-llm documenta que su Dolphin escribe 3.19.0 con payload Pre-Frame de 0x42 bytes
(`melee_llm/sim/slippi.py` L3-5 y L26-29 @ `7e179081…`: `VERSION = (3, 19, 0)`, `PRE: 0x42` «as our Dolphin's Event
Payloads lists them») [DOCUMENTADO_POR_AUTOR; no verificado contra un Dolphin real → parte B].

Matiz: los gatillos físicos van como float, no como byte. melee-brute los reconvierte a byte con
`lrintf(value * 140)`, documentando que Melee los deriva del byte post-clamp con `scale_analogLR == 140`
(`tools/validation/native.c` L1025-1037 @ `9662ec97…`) [INSPECCIONADO_EN_CODIGO]. Es la misma conversión que usa el
validador para certificar replays humanos, así que no introduce una pérdida nueva [INFERENCIA].

## 2. Qué expone libmelee al agente en vivo

`melee/console.py`, mismo código en ambas revisiones (`__pre_frame`: HEAD L1145-1214, v0.47.6 L1170-1239; el md5 del
cuerpo es idéntico, `5bf3b139…`). El diff HEAD→v0.47.6 solo toca `console.py` (background_input, interrupt, GCPad),
`slippstream.py` (interrupt) y `version.py` [INSPECCIONADO_EN_CODIGO].

Lo que el parseo **guarda** en `ControllerState` (`melee/controller.py` L46-64):
- `main_stick`: floats procesados 0x19/0x1D reescalados a [0,1] (L1166-1168 HEAD).
- `c_stick`: **solo procesado** 0x21/0x25 (L1170-1172).
- `raw_main_stick`: 0x3B y 0x40 (L1174-1184).
- `l_shoulder = r_shoulder = trigger`: el gatillo **procesado** 0x29 copiado a ambos (L1186-1189, comentario «The game
  interprets both shoulders together»).
- `button` (físicos 0x31) y `processed_button` (0x2D) (L1205-1212).

Lo que **descarta** aunque llega en el flujo:
- Pre-Frame 0x7 (semilla), 0x33/0x37 (gatillos físicos L/R), 0x41/0x42 (C-stick crudo): ningún `np.ndarray` lee esos
  offsets en `__pre_frame`.
- Frame Start: `elif event_type == EventType.FRAME_START: pass` (HEAD L1039-1040; v0.47.6 L1063-1064).
- Game Start 0x13D: no aparece en `console.py`; `grep seed melee/*.py` solo encuentra un enum ajeno (`enums.py`
  L584). No hay campo de semilla en `GameState`.

Así que `GameState` no basta para alimentar una sombra exacta. Esto confirma A8-003 y la fila 25 de
`CRITICAL_REVIEW.md` [INSPECCIONADO_EN_CODIGO].

**Pero los bytes crudos sí son accesibles.** melee-llm ya engancha el dispatcher privado de libmelee:
`ConsoleTap` en `melee_llm/bots/agent.py` L25-56 @ `7e179081…` envuelve `console._slippstream.dispatch` y copia
cada mensaje `game_event`/`frame_end` (payload decodificado de base64) a sus suscriptores. El docstring dice «a
private libmelee attribute, stable across 0.45-0.47». Ese payload es el flujo completo: Frame Start, Pre-Frame con
0x41/0x42/0x33/0x37/0x7, eventos de escenario y Game Start con 0x13D [INSPECCIONADO_EN_CODIGO]. Que lo usen solo los
bots aprendidos (A1-012) es una decisión del harness; cualquier agente con acceso al objeto `Console` puede crear
`ConsoleTap.of(console)` [INFERENCIA].

**Temporalidad.** El cliente de libmelee devuelve el `GameState` al recibir el `FRAME_BOOKEND` del frame N (HEAD
L1051-1069). Para entonces el Pre-Frame de N de todos los puertos ya se ha procesado, y según la spec registra los
inputs que el juego usa en ese frame N. El agente decide entonces su input para N+1. Por tanto la sombra puede
avanzar exactamente hasta N (inputs de ambos puertos y semillas de N) **antes** de que el agente decida. No puede
conocer el input del rival en N+1: eso sigue requiriendo un modelo del rival [INFERENCIA sobre spec + código].
En la partida local del bench no hay rollback; `skip_rollback_frames` descarta frames antiguos (L1060-1068)
[INSPECCIONADO_EN_CODIGO].

## 3. Qué exige el simulador y qué ofrece su API pública

**Entrada por frame (API pública).** `MslInput` por jugador: `buttons` uint16, `main_x/main_y` int8 crudos, `c_x/c_y`
int8 crudos, `l/r` uint8 (`API.md` L101-108 @ `9662ec97…`). `translate_inputs` copia solo esos campos y deja a cero
`nml_*`/`nml_valid` (`src/api.c` L158-176). Para replays humanos, la admisión exige «raw main-stick/C-stick axes,
physical buttons/triggers and processed inputs… Never reconstruct missing human controller bytes from processed
floats» (`agent_docs/VALIDATION.md` L78-81 @ `9662ec97…`; L49-52 en melee-sim-light `eea7b5fb…`)
[DOCUMENTADO_POR_AUTOR]. Todos esos campos están en el flujo crudo (§1).

**RNG: la API pública fija solo la semilla inicial.**
- `MslMatchConfig.random_seed`, «deterministic reset seed» (`API.md` L72). En Python:
  `EnvBatch.configure_match(seed=…)` → `row["random_seed"]` (`melee_sim/env_batch.py` L578).
- `frame_pre_random_seed` es un campo de **salida** de `MslObservation` (`API.md` L129), no una entrada.
- El paso público reinyecta la semilla propia del simulador y no recibe eventos de escenario:
  `uint32_t frame_seed = match->random_seed; msl_core_match_step(match, …, frame_seed, &no_stage_events)`
  (`src/runtime/batch.c` L324-326, igual en el pin `090e54b0…` L324). Tras cada frame se cumple
  `match->random_seed = *seed_ptr` (`src/runtime/scalar.c` L2605), es decir, la semilla corre libre.
- La lista completa de `MSL_API` (`src/api.h` L247-447) no tiene ningún setter de RNG por frame ni de eventos de
  escenario. `EnvBatch.step(step_mask)` (L331) tampoco. Lo mismo ocurre en melee-sim-light `eea7b5fb…`
  (`src/api.h` L245-287, `batch.c` L323).
[INSPECCIONADO_EN_CODIGO]

**El núcleo sí sabe inyectarlo (camino interno de validación).** `msl_core_match_step(match, input, frame_seed,
stage_events)` (`src/runtime/scalar.h` L136-138) hace `*seed_ptr = frame_seed` al inicio del frame
(`scalar.c` L2385-2391, comentario «Slippi's pre-frame row owns the RNG value used by replay playback»).
`MslCoreStageEvents` lleva `fighter_pre_random_seed`, plataformas FoD, Whispy y entradas CPU (`src/runtime/wire.h`
L46-73), y `msl_slippi_apply_fighter_pre_random_seed` lo aplica (`src/platform/slippi.c` L87-99). Solo lo usa el
binario de validación por stdin (`src/runtime/main.c` L89-96, L164-172), y `Makefile` L151 lo excluye de la
librería. El validador lo rellena así (`tools/validation/native.c` L1840-1844, L872):
- `frame_pre_random_seed` ← `frames.start.random_seed` (Frame Start 0x3A, 0x5);
- `fighter_pre_random_seed` ← `pre.random_seed` (Pre-Frame 0x7) del primer jugador presente.

`VALIDATION.md` L33-34 lo confirma: «Validation supplies recorded RNG observations… It does not establish an unseeded
rollout» [INSPECCIONADO_EN_CODIGO + DOCUMENTADO_POR_AUTOR].

**`parity.py` de melee-llm** (`melee_llm/sim/parity.py` @ `7e179081…`):
- Usa la API pública: `EnvBatch(action_format="raw")`, `configure_match(seed=game.start.random_seed)` (L53-57).
- Reinyecta por frame botones físicos, ejes crudos y gatillos físicos ×140. El C-stick crudo lo lee con
  `getattr(…, None)` y, si falta, lo reconstruye desde el procesado ×80 (L33-37, L62-71). Eso contradice la regla
  «Never reconstruct» para replays antiguos.
- **No** inyecta semilla por frame, y su docstring lo dice: «melee_sim's RNG runs free… a replay stays in sync only
  until the first random choice that comes out differently» (L4-6).

Es decir, el autor del harness ya chocó con esta limitación [INSPECCIONADO_EN_CODIGO].

**Estado a mitad de partida: no existe.**
- Solo hay `reset` desde configuración (frame -123), y `save/restore/checkpoint/rollback` de savestates **producidos
  por el propio simulador** (`src/api.h` L292-307; `API.md` L55-62).
- No hay API para construir estado desde un `GameState` ni desde un Post-Frame.
- La admisión rechaza «midgame/savestate-injected captures» y exige «the normal -123 seed, contiguous finalized rows»
  (`VALIDATION.md` L97-100).
- «Savestates hold addresses» (L62-63), así que parchear bytes de un savestate no es una vía soportada.

La sombra tiene que arrancar en Game Start con la configuración completa (escenario, personajes, puertos, semilla
0x13D, UCF/reglas) y avanzar todos los frames sin hueco. Si pierde un solo frame, la sombra queda irrecuperable para
esa partida [INSPECCIONADO_EN_CODIGO + INFERENCIA].

## 4. Veredicto

**FACTIBLE CON CAMBIOS.** No es factible con las APIs públicas actuales. El bloqueo no está en Slippi ni en Dolphin:
el flujo crudo trae todo lo necesario. Está en la API pública del simulador, que no acepta la semilla por frame ni
los eventos de escenario, y en que `GameState` descarta campos (eso se esquiva leyendo bytes crudos).

Cambios necesarios [PROPUESTA]:
1. **melee-brute, API C** (`src/api.h`/`src/api.c`/`src/runtime/batch.c`): añadir algo como
   `msl_batch_step_recorded(batch, inputs[], frame_seeds[], stage_events[])` que pase `frame_seed`, y
   `MslCoreStageEvents` (`fighter_pre_random_seed`, FoD, Whispy) a `msl_core_match_step` en vez de
   `match->random_seed`/`no_stage_events` (batch.c L324-326). El núcleo ya lo soporta (camino de `main.c`). Es una
   ampliación de ABI que debe pasar el *differential gate*.
2. **melee-brute, Python** (`melee_sim/env_batch.py`, `dtypes.py`, `src/python_api.c`): exponer esos buffers en
   `EnvBatch.step`.
3. **melee-llm**: un decodificador en vivo de los bytes de `ConsoleTap` (`bots/agent.py` L25-56; el parseo puede
   reutilizar `PRE_FIELDS` de `sim/slippi.py` L32-37). Debe extraer:
   - Game Start: 0x13D y la configuración de la partida;
   - por frame: Frame Start 0x5, Pre-Frame 0x7/0x31/0x33/0x37/0x3B/0x40/0x41/0x42 y FoD/Whispy;
   - con todo eso, avanzar la sombra al recibir cada Bookend, antes de llamar al agente.

   La conversión de entradas es la de `tools/validation/native.c` L1025-1075, no la de `parity.py` L68-70: nada de
   reconstruir el C-stick desde el procesado.
4. Exigir Slippi ≥ 3.17.0 en el Dolphin del bench, comprobando los campos reales y no solo la versión, como pide
   `VALIDATION.md` L80. Abortar la sombra si falta un frame (sin reinicio a mitad de partida).
5. Opcional: dejar de depender de `console._slippstream.dispatch`, un atributo privado.

Límites que siguen tras los cambios [INFERENCIA/DESCONOCIDO]:
- La sombra va 0 frames por delante: reproduce N, no N+1. El input futuro del rival sigue sin conocerse.
- Su exactitud queda acotada por la cobertura validada del simulador: «524 exact recordings across 148
  manifest-listed fighter/stage pairs… not a claim of exhaustive move/branch coverage» (`VALIDATION.md` L105-107,
  DOCUMENTADO_POR_AUTOR).
- Las reglas y parches del bench tienen que estar dentro de los admitidos (UCF, sin ítems, Stadium congelado, parche
  offscreen…; `VALIDATION.md` L82-96).
- La fracción de frames en sincronía en partidas del bench es **DESCONOCIDO**.

Consecuencia para A4-027 y C2: A4-027 sigue FALSA tal como está escrita, porque se basa en `GameState`. La
afirmación corregida sería: «posible desde el flujo crudo con una ampliación de la API del simulador». C2 deja de
depender de A5-036, porque el seed por frame **sí** viaja en Frame Start desde 2.2.0. Ahora depende de la ampliación
de API y de la tasa de sincronía medida (parte B).

## 5. Prueba mínima con ISO (parte B) que lo confirmaría

1. Sin tocar el simulador, a modo de control: grabar ≥ 50 partidas del bench (Dolphin, .slp) con humanos/bots de
   ambos puertos. Para cada una, reproducir con la herramienta de validación existente
   (`tools/validation/validate_replay.py` @ `9662ec97…`, que ya inyecta semillas y eventos) y medir el primer frame
   de divergencia. Esto da la cota superior de sincronía alcanzable por una sombra con RNG inyectado.
2. Contraste: `melee_llm/sim/parity.py` sobre las mismas partidas (RNG libre). La diferencia entre ambos mide cuánto
   aporta la inyección por frame.
3. Prueba en vivo: implementar los cambios 1-3 y, en partidas Dolphin en vivo, comparar en cada Bookend la
   observación de la sombra con el Post-Frame recibido (posición/acción, tolerancia 1e-4 como `parity.py` L92-94).
   Registrar la fracción de frames sincronizados y la latencia añadida por frame. Criterio de G4/H5 del plan: ≥ 95 %
   de frames en sincronía.
4. Comprobar en el primer `.slp` grabado que el Pre-Frame mide 0x42 bytes y que los campos 0x41/0x42 no son
   constantes, lo que confirma la versión del Dolphin del bench.
