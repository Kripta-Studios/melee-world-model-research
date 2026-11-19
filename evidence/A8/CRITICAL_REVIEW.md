# A8 · Revisión crítica del swarm (A1–A7)

Agente A8 · 2026-11-19 · Lectura adversarial de `evidence/A1`…`A7` contra el código en `sources/` (SHAs de
`ops/clone_inventory.txt`; melee-llm `7e179081`, melee-brute `9662ec97`, libmelee `bce21f09`, le-wm `8edfeb33`,
slippi-ai `5ada33e9`, phillip `114aea4c`, HAL `37045d97`, Faynt-Benchmarks `39bc0075`, Faynt-Tournament
`d2096176`, melee-sim-light `eea7b5fb`, rliable `3ccd9f4d`) y el PDF de At Human Speed (arXiv 1810.07286v1,
sha256 `d93cb1de…19db`, el mismo que usó A2). No se ejecutó ninguna partida ni benchmark. `[A8-xxx]` →
`claims.jsonl`. Plan derivado: `EXPERIMENT_PLAN.md`; huecos priorizados: `evidence_gaps.json`.

---

## 1. Auditoría de trazabilidad (muestra de 30 afirmaciones, sesgada a las que sostienen conclusiones)

Veredictos: **CONFIRMADA** (ruta, símbolo y líneas existen y dicen eso), **IMPRECISA** (el fondo se sostiene, pero
el localizador, el alcance o un matiz están mal), **FALSA** (no se sostiene tal como está escrita).

| # | Claim | Afirmación (resumida) | Veredicto | Detalle de la verificación |
|---|---|---|---|---|
| 1 | A1-013 / A4-017 | (a) El `GameState` entrega el mando actual del rival | **CONFIRMADA** con matiz | libmelee `melee/console.py` `__pre_frame` L1145-1212 rellena `controller_state` para **cada** puerto del PreFrame sin filtrar; sim lo copia en `melee_llm/sim/state.py` L93-95 vía `controller_state_from_raw` L59-73. Matiz no recogido: libmelee solo da `raw_main_stick` (L1174-1184), C-stick **procesado**, y un gatillo **lógico** copiado a L y R (L1186-1189); no hay C-stick crudo ni gatillos físicos [A8-003] |
| 2 | A1-002 / A7-001 | (b) Dolphin bloquea esperando input en `realtime` | **CONFIRMADA** | `melee_llm/runner.py` L208: `blocking = mode in ("fast","paused","lockstep","realtime")`; L214 `emulation_speed=0 if fast else 1.0` |
| 3 | A1-014 | (b) El bench nunca usa el simulador | **CONFIRMADA** con matiz | `bench/entrants.py` L189-191 `game_mode` → `realtime|fast`; `scheduler.py` L207, L326; bot-writer ladder `play(..., mode="fast")` (`botwriter/ladder.py` L122). Matiz: el pool que se puntúa también **importa** partidas `lockstep` (pilotos coach/Jev, arena de bots; `bench/imports.py` L85-97) — ninguna en sim [A8-009] |
| 4 | A1-003 | `bench.md` «the game never waits» contradice el código | **IMPRECISA** | El mismo `docs/bench.md` L27 dice «The runner waits for a late bot… A real-time game with a mean below 50 fps is marked slow». No es una contradicción oculta: el doc describe que la no-espera depende de que el jugador piense en otro hilo y documenta el mecanismo `slow` |
| 5 | A1-016 | `status_of` L323-329, `MIN_FPS` L230 en `bench/game.py` | **IMPRECISA** (localizador falso) | `bench/game.py` tiene **113 líneas**: `status_of` L107-112, `MIN_FPS` L14, `play_one` L83, `make_agent` L17. SYSTEM_MAP repite localizadores inexistentes (L299-320, L233-244, L230, L327-328). El contenido sí es correcto (A7-001 cita bien L14/L103/L111-112) |
| 6 | A1-001 | `runner.play(mode="sim")` no reenvía `seed` | **CONFIRMADA** | `runner.py` L200-202 llama `play_sim(agents, stage, games, observer=, meta=)`; `sim/runner.py` L43 `random.getrandbits(32)` |
| 7 | A1-007 | El agente no recibe el `World` en sim | **CONFIRMADA** | `sim/runner.py` L47-51: `a.setup(world.controllers[p], p, …)` |
| 8 | A1-018 / A4-026 | (d) 12–17 µs/frame del simulador | **CONFIRMADA**; hardware: Ryzen 9 5950X (16 núcleos) «busy with other work (load 15 to 35)» | `melee-brute/BRUTE.md` L84 (condiciones), L100-106 (tabla: 12–15 µs/frame dentro de la búsqueda; 17 µs desde Python con observación; checkpoint/rollback 4,4/4,5 µs). L108-110: «The tables above predate the current build profile» (posición buscada 19,9→18 µs en máquina más tranquila; 16,5 µs con PGO). **Otra condición relevante no usada por el swarm**: en la ruta `World` de melee-llm el simulador cuesta 0,12 ms/frame y el `StateBuilder` 0,23 ms/frame (`docs/simulator.md` L65), y 17.500 frames/s a load 45 ≈ 57 µs/frame (L20) [A8-008] |
| 9 | A4-025/A4-026, A5-021, A7-014 | Un modelo aprendido no es más rápido que el simulador en CPU | **IMPRECISA** en el cociente, conclusión cualitativa sostenida | Se compara un bucle C secuencial en otra CPU (17 µs) con torch por lotes en esta (8–10 µs/transición a lote 16k para MLP/GRU-1M, REP de A7). Para 1M el cociente es ≈1, no 50–300×; el 50–300× solo vale para el ARPredictor tamaño LeWM sin KV-cache. Si S0 usa la ruta `World`+`StateBuilder`, su coste por frame es ~0,35 ms y el MLP-1M sería *más rápido*. La comparación honesta exige medir ambos en la misma máquina (hueco G-01) |
| 10 | A5-001 | Nadie planifica con el simulador al jugar | **CONFIRMADA** | `grep takeback|melee_brute|Forced(|.checkpoint(` → solo `melee_llm/solver/{nash,squeeze,force,takeback,fortress}.py`, `scripts/solver_probes/**` y `scripts/optimal_play_animations.py`; ningún `Agent`. Cita «search at training time, not at play time» en `docs/tas.md` L97 (verbatim) |
| 11 | A5-010 | (c) Minimax alternado: el ciclo de §12 era un artefacto | **CONFIRMADA** | `docs/optimal-play.md` L358-359 «The cycle of section 12 was an artefact. One frame late, the defender simply waits…»; `solver/nash.py` L4 «`force.py` gave one side the other's input on the same frame, which only bounds the answer» |
| 12 | A5-011 | (c) Valor 0 → 0,382 con inputs de 2 frames | **CONFIRMADA** con matiz | `optimal-play.md` L367-372: a 12,59 u **sin escudo**, horizontes 8 y 12, mezcla 38/38/24. Omitido por A5 en §0.3: «With shield allowed the two-frame game is 0 again over 12 frames, but only because the shield's cost (the one-way door) lies beyond the horizon» (L371-372). Es un resultado de menús y horizonte concretos, no del juego |
| 13 | A3-SIG-001 | (e) SIGReg = Epps–Pulley sobre M proyecciones aleatorias | **CONFIRMADA** | `le-wm/module.py` L10-36: `A=randn(D, num_proj)` normalizado por columna en cada llamada; `t=linspace(0,3,17)`; pesos trapezoidales × `exp(-t²/2)`; `statistic=(err@weights)*proj.size(-2)` (= B, pues `proj` es T×B×D); media sobre proyecciones y tiempo; comentario «single-GPU!» |
| 14 | A3-LWM-001 / A4-004 | (e) LeWM sin stop-grad ni EMA, λ=0,09 | **CONFIRMADA** | `train.py` L34-41: `tgt_emb = emb[:, n_preds:]` sin `detach`; `loss = pred_loss + lambd*sigreg_loss`; `config/train/lewm.yaml` `weight: 0.09`, `num_proj: 1024`, `knots: 17`, `max_epochs: 100`, `history_size: 3` |
| 15 | A4-010 | (f) Planificación por distancia al embedding objetivo | **CONFIRMADA** | `jepa.py` L112-126 `criterion`: MSE del **último** embedding predicho contra `goal_emb[..., -1:, :].detach()` sumada por candidato; `get_cost` L128-153 codifica `goal["pixels"]=goal["goal"]`. No hay recompensa ni valor |
| 16 | A3-LWM-003 | Split de LeWM por ventanas | **CONFIRMADA** con matiz | `train.py` L73-76 `spt.data.random_split(dataset, …)`; el dataset se carga con `num_steps = num_preds + history_size` (`config/train/data/pusht.yaml` L2) en `stable_worldmodel` (externo): los ítems son ventanas |
| 17 | A2-014 | slippi-ai excluye el mando del rival | **CONFIRMADA** | `slippi_ai/jax/embed.py` L461-463 «# don't use opponent's controller / with_controller: bool = False»; también `tf/embed.py` L503-505 |
| 18 | A3-MEL-001 | slippi-ai omite action_frame/hitlag/hitstun | **CONFIRMADA** | `tf/embed.py` L443, L446-447 comentados |
| 19 | A2-001 | Peso HAL = AWR + retorno + V(s), no BC puro | **CONFIRMADA** | `experiments/059_muon_action_sequence.py` L1-6 «trains AWR… A learned value head… advantage weights the policy objective» |
| 20 | A4-007 / A2-018 | El predictor de Phillip solo usa la acción propia | **CONFIRMADA** | `phillip/model.py` L84 `current_actions = tfl.windowed(actions, predict_steps)`, L95-98 `inputs = concat([prev_core, current_action])` |
| 21 | A2-019 / A6-026 | At Human Speed, Tabla 1 y «p = d» | **CONFIRMADA** en cifras, **IMPRECISA** por omisión | Texto extraído: Tabla 1 (6,0) 0–6, (6,6) 3–5, (7,7) 2–5; «best results are achieved with p = d»; el predictor «ignores the opponent» (§5.2); (9,9,2) no llega a tiempo real (§5.1). **Omitido por todos los roles**: la columna «Days Trained» es 3 para (6,0) frente a 10 para (6,6) (y 7 para (7,7)): la comparación con el profesional está confundida por tiempo de entrenamiento, con 6–8 partidas por agente y un agente por celda [A8-004] |
| 22 | A4-003 | `post(f)` no es Markov: look-alike difieren en lo mantenido | **CONFIRMADA** | `BRUTE.md` L74-80: «States that look the same differ in what each fighter was holding… Every difference we found between merged states was of this kind» |
| 23 | A6-029 | VALIDATION.md «before input edges/timers» como afirmación general | **IMPRECISA** (A4 tenía razón) | `melee-sim-light/agent_docs/VALIDATION.md` L152-158 está bajo «## Recorded CPU inputs». La conclusión (Markov exige historia de mandos) se sostiene por BRUTE.md, no por esa cita |
| 24 | A4-021 | 15/40 partidas nunca divergen en el simulador | **IMPRECISA** en su uso | `docs/simulator.md` L53: son «40 random replays **of ours between controller-driven players**» (bots del autor), no partidas humanas. A4/A5 lo usan como cobertura de «replay-to-reach» de estados humanos (C2) y de la sombra en Dolphin; para humanos sin RNG inyectado la tasa es DESC. El 36/40 humano es **con** semillas RNG grabadas (L55) |
| 25 | A4-027 | Sombra en Dolphin: «el `GameState` trae los mandos de ambos jugadores» | **FALSA tal como está escrita** | Para admitir un replay humano el simulador exige «raw main-stick/C-stick axes, physical buttons/triggers and processed inputs… Never reconstruct missing human controller bytes from processed floats» (`VALIDATION.md` L49-52). El `GameState` de libmelee no tiene C-stick crudo ni gatillos físicos (fila 1). La sombra solo es posible desde el **flujo Slippi crudo** que reciben los bots (A1-012) y si la versión de replay trae esos campos (`parity.py` L35 los lee con `getattr` «por si faltan»); la inyección de RNG por frame en la API pública es DESC [A8-003] |
| 26 | A2-025 / A2 §4 | Faynt: rivales slippi-ai informaron selección | **CONFIRMADA** | `Faynt-Benchmarks/README.md` L50 «Some releases also informed RL run or checkpoint selection»; L48 «Opponents retain 21- or 24-frame action queues. The report does not isolate the effect»; L53-55 panel 0 frames = 68 partidas contra **un** checkpoint privado [A8-006] |
| 27 | A2-005 | HAL 91–5 / 24–72 con retraso asimétrico | **CONFIRMADA** + matiz útil al protocolo | `hal/experiments/slippi-ai-h2h/README.md` L216-221; L32-36: «Melee RNG is not seeded, so port swaps are not exact mirrored emulator trajectories» [A8-007] |
| 28 | A5-022 / A2-029 | Faynt-10M CPU 8 hilos 8,1/10,3/11,5 ms | **CONFIRMADA** | `docs/bots.md` L53; añade «10M on CUDA: about 16» — en GPU es más lento que en CPU en esa máquina |
| 29 | A7-003 | ~3,3 ms/frame de Dolphin+parseo+runner | **CONFIRMADA** | `docs/performance.md` L52 (98 fps HAL vs Phillip; 63 fps en pico de carga) |
| 30 | Todos los `REPRODUCIDO` | Artefactos de medición | **CONFIRMADA** | Los 25 `result_artifacts` existen y su SHA-256 coincide; IDs únicos; todas las `inference_basis_claim_ids` resuelven. Defectos menores: A7-033 usa `FEASIBILITY.md §1` como `config_artifact`; los scripts de A7 viven en `pilot/a7_bench/`, **fuera de `evidence/A7/`** (contra la regla de escritura del brief); A5-020 re-etiqueta como REPRODUCIDO una medición de A7 |

Resumen: 30 auditadas → 20 CONFIRMADAS (6 con matiz), 9 IMPRECISAS, 1 FALSA. Ninguna IMPRECISA invierte una
conclusión de A1–A3; las dos que sí afectan a la conclusión de conjunto son la 25 (sombra en Dolphin) y la 24
(cobertura de C2/sombra), porque sostienen el «nicho estrecho» de la dinámica aprendida en Dolphin.

### Verificaciones pedidas explícitamente

- **(a)** Sí, el mando actual del rival llega a todo agente (salvo bot-writer, `botwriter/agent.py` L6 «Opponent
  inputs and identity are hidden»). Lo que llega es procesado + stick principal crudo; no basta para una sombra
  bit-exacta desde `GameState`.
- **(b)** Sí, el scheduler del bench nunca usa sim; y en `realtime` Dolphin bloquea (el doc lo admite en L27).
- **(c)** Citas verbatim correctas (tabla, filas 10–12); el 0,382 es sin escudo, horizontes 8/12.
- **(d)** 12–15 µs (búsqueda) y 17 µs (desde Python) en un 5950X cargado (load 15–35), con tablas anteriores al
  perfil de build actual; no medido en ninguna máquina del swarm (no hay ISO).
- **(e)** SIGReg en le-wm verificado línea a línea.
- **(f)** Objetivo de LeWM = MSE al embedding de la meta en el último paso; sin recompensa.

---

## 2. Contradicciones entre roles y resolución por fuente

| K | Roles | Contradicción | Resolución (fuente) |
|---|---|---|---|
| K1 | A3 vs A7 | SIGReg «despreciable frente a cualquier encoder» (A3 §1.3) vs «83 % del paso de entrenamiento de MLP-1M» (A7-021) | **Las mediciones coinciden** (A3: 69 ms, N=256, 2 hilos; A7: 72 ms, T·N=320, 3 hilos; ambas con M=1024, K=17). La diferencia es interpretativa: el coste es T·N·M·17 trigonométricas (`module.py` L33-34), independiente del tamaño del encoder; frente a un ViT de píxeles es menor, frente a un encoder de estado ≤1M domina en CPU. **Gana A7** para Melee-estado en CPU; en GPU no medido. Bajar M a 256–512 es un cambio de configuración declarado (A3 §1.2: el paper LeJEPA dice 512 «competitivo») |
| K2 | A4 vs A5/A7 | W1-L con ARPredictor transformer (A4) vs «no cabe en tiempo real; usar GRU» (A5 §7) | A7 midió transformer **sin KV-cache**, ventana re-codificada en cada paso (tx-1M K16·T8 p99 23 ms). Es un artefacto de implementación: en despliegue AR con caché el coste por paso se acerca al de un token. **Resolución:** el transformer se mantiene en `untimed`; antes de sustituirlo por GRU en RT, medir con KV-cache (hueco G-08). Si se cambia a GRU, W1−W0 pasa a medir «predictor+arquitectura», y deja de ser LeWM |
| K3 | A2 vs A5/A7 | Faynt-10M como prior de propuestas (A2-037) vs «no cabe como prior en RT en CPU» | `docs/bots.md` L53: 8,1/10,3/11,5 ms en CPU de 8 hilos (y ~16 ms en CUDA en esa máquina). **Gana A5/A7** para `RT-strict` en CPU; Faynt como prior solo en `untimed` o GPU dedicada |
| K4 | A1, A2, A4, A5, A6 | Régimen de información: el bench entrega el mando del rival (A1); slippi-ai lo excluye (A2); A6 propone excluirlo; A4 crea I_full/I_human; A5: S0 solo en I_full; el bot propio de melee-llm lo usa (A2-032) | No es contradicción de hecho sino de decisión. **Congelado en el plan**: primario `I_full` (régimen real del bench; las referencias fuertes no lo usan), `I_human` secundario obligatorio, S0 solo en I_full + PRIV. Ningún contraste mezcla regímenes |
| K5 | A2 vs A4/A6 | B0 con el parser/`Game` de slippi-ai (A2 D1) vs W0-S con esquema completo reparseado de .slp (velocidades, contadores, crudos; A4 §2.1, A6 §5) | El `Game` de slippi-ai no tiene velocidades ni hitstun y trunca % a uint16 (A6-030, CÓD `parse_peppi.py`); su embedding omite action_frame/hitlag/hitstun (fila 18). Si B0 y W0 usan esquemas distintos se viola «iguales observaciones». **Resolución:** un único esquema (A6) para todos los brazos propios; Faynt queda como referencia externa |
| K6 | A4 vs A5 | «W vs S0 es el control decisivo» (A4-028) vs «S0 es cota superior, no comparación simétrica» (A5-040) | A5 es más preciso, pero solo **a igual conteo y evaluador**. A igual tiempo, una dinámica aprendida en GPU podría evaluar más candidatos que S0 en CPU y superarlo (no medido). Resolución: S0 como cota en la tabla de igual conteo; tabla separada a igual tiempo/hardware |
| K7 | A4 vs A7 | 50–300× (A4) vs ~1× (A7) más lento que el simulador | Distintos modelos (10,8M ventana 3–16 vs 1M), lotes e hilos. Ambos correctos en su alcance; ninguno compara con el simulador en la misma máquina (fila 9) |
| K8 | A1 vs `bench.md` | «never waits» | Ver fila 4: el doc ya lo matiza |
| K9 | A4 vs A6 | Cita de VALIDATION.md | Ver fila 23: A4 tiene razón |
| K10 | A4/A5 (uso de 15/40) vs fuente | Cobertura de la sombra/C2 | Ver fila 24: la cifra es de bots del autor |
| K11 | Corpus para dinámica | HAL MDS (A2/A6: barato, 1,3M partidas) vs .slp crudo (A4/A6) | HAL MDS carece de velocidades, `action_state_frame`, hitstun, RNG y crudos (A6-030, CÓD `policy_schema.py`): solo prototipo con suelo de error irreducible; el resultado exige reparsear `.slp` de `erickfm/melee-ranked-replays` (FOX 301 GB) o `pro/`. Ninguno cabe completo aquí |

---

## 3. Intentos de refutación de la conclusión emergente

Conclusión emergente (A4 §6, A5 §0.7/§6): *«un modelo de dinámica aprendido no aporta frente al simulador exacto en
modo sim; su único nicho es Dolphin/netplay tras la divergencia de RNG y el modelo del rival; el valor terminal y
el modelo del rival importan más que la dinámica».* La descompongo:

**C1 — En `--mode sim`, a igual conteo, una dinámica aprendida no supera al simulador exacto.**
Casi tautológica (mismo candidato, mismo q, mismo V̂, dinámica exacta) salvo errores de modelo que
«regularicen» por azar. **INFERIDA**, sólida. Pero tiene dos debilidades:
1. **No es el objetivo.** El bench es solo Dolphin (fila 3). Una afirmación sobre sim no dice nada del bench.
2. **«No aporta» nunca se ha medido** ni se ha planteado como equivalencia. Ningún rol propuso un test de
   equivalencia; el «S0-ceiling» de 40 partidas (A5 §6.3) detecta solo ~31 pp [A8-014].

**C2 — Su único nicho es Dolphin tras la divergencia de RNG.**
Este es el eslabón más débil. Descansa en un «simulador sombra» que **no existe** (PROPUESTA de A4-027) y cuya
viabilidad está mal fundada (fila 25: el `GameState` no trae los mandos crudos necesarios; fila 24: la tasa de
divergencia citada es de bots, no de humanos ni de partidas del bench). Además:
- Si el flujo Slippi crudo trae el `random_seed` de FrameStart (A5-036, DESC) **y** la API del simulador permite
  inyectarlo por frame (DESC; hoy solo el carril de validación lo hace, `VALIDATION.md` L33-34), la sombra sería
  exacta casi siempre y el nicho de la dinámica aprendida sería pequeño.
- Si alguna de las dos cosas falla, el nicho **no es estrecho: es todo el bench**. Ninguna evidencia del swarm
  decide entre los dos casos. **PENDIENTE** (puerta G4 del plan).
- Hay además un argumento normativo que el swarm no pesa: si la pregunta es «agente con información de jugador»,
  S0 y la sombra están en la categoría **PRIV** (estado completo + RNG). En el carril causal (`I_human`, sin
  snapshot), la dinámica aprendida no compite con S0 sino con P0/B1, y ahí su valor está sin medir.
- «Y el modelo del rival» no es un nicho de la **dinámica**: q es una política (A4 §4.1 lo dice). Mezclarlo en la
  frase oculta que la recomendación real es «invertir en q, no en p_dyn».

**C3 — El valor terminal y el modelo del rival importan más que la dinámica.**
Base: γ^32 ≈ 0,955 con semivida de 8 s (A5-030, aritmética correcta: 0,5^(32/480) = 0,9549), Firoiu ignora al
rival, `nash --grain 2` muestra que la reacción cambia el valor. Es **INFERIDA**: que V̂ domine la *magnitud* de J
no implica que domine el *ranking* entre candidatos (lo que decide es la diferencia entre ramas, y un golpe dentro
del horizonte la cambia). No hay ningún experimento, ni siquiera offline, que compare la sensibilidad del resultado
a q, a V̂ y a la dinámica. **PENDIENTE** (H8, H9 del plan).

### 3.1 Contraejemplos más fuertes a favor del world model

| X | Contraejemplo | ¿Lo descartó el swarm? | Evaluación A8 |
|---|---|---|---|
| **X1** | **Entrenamiento en imaginación masivamente paralelo en GPU** (Dreamer/TD-MPC2): no se trata de que la dinámica sea más rápida por frame, sino de **fusionar política y modelo en la GPU** y eliminar el viaje CPU↔GPU por frame | Solo con inferencia: A4 §6.2 «No, mientras el simulador corra… más rápido en CPU»; A7 admite «en GPU la relación puede invertirse — no medido» | Es el contraejemplo más fuerte y **no está refutado**. Evidencia que lo apoya (DOC): en la ruta actual el cuello es la política, no el simulador — Phillip-vs-Phillip en sim: simulador+conversión 0,66 ms/frame frente a 8,6 ms de cada política (`docs/simulator.md` «Phillip vs Phillip in the simulator»); granja Faynt 6.337 frames/s con 8 procesos (A7-015) frente a 120k frames/s/núcleo del simulador desnudo. Evidencia en contra: la interacción real aquí es barata (no hay escasez de muestras que la imaginación resuelva), el modelo introduce sesgo explotable (Firoiu §5.1 «likely to exploit flaws in the model») y MuZero/Dreamer brillan en régimen de muestras escasas. **PENDIENTE**; prueba barata sin ISO: throughput de un pipeline fusionado en GPU con datos sintéticos (G1/H12) |
| X2 | Diferenciabilidad (planificación por gradiente, `le-wm/config/eval/solver/adam.yaml`) | Por inferencia (A4 §6.2: discontinuidad golpe/fallo) | Argumento plausible; prior bajo. Sin evidencia en ninguna dirección. Baja prioridad |
| X3 | Generalización a personajes/escenarios que el simulador no soporta | Parcialmente con evidencia | melee-sim-light declara roster completo y los 6 escenarios (`README.md` L12-13, DOC); los límites reales son ítems, UCF, Stadium congelado, sin CPU (`BRUTE.md` L149). El bench es Fox ditto BF/FD: el contraejemplo **no aplica al bench**. SOPORTADA la refutación en ese alcance |
| X4 | Robustez a la demora vía predicción (At Human Speed) | Con evidencia débil: «p = d mejor», Phillip lo usa, slippi-ai lo abandonó, melee-llm aconseja «Skip the predictive model» (`delay.md` L70, opinión) | La evidencia **a favor** es más débil de lo que el swarm dice: Tabla 1 confundida por días de entrenamiento (3 vs 10), 6–8 partidas, un agente por celda, predictor que ignora al rival (fila 21). La evidencia **en contra** también es indirecta: Faynt/slippi-ai consiguen fuerza a 18–24 frames sin predictor explícito, pero nadie ha comparado a igual demora con y sin predictor. **INFERIDA** la refutación; medible offline sin ISO (error de «predecir el presente» por D con q vs marginal, G2) |
| X5 | Representación para eficiencia de datos (B2/E1) | No: A3 lo deja como hipótesis a falsar con E1-S | Legítimo, no testado, y **no es la dinámica en decisión**. **PENDIENTE** (H4). Matiz de A3 correcto: si E1-S ≥ E1, no es «JEPA» |
| X6 | Planificar en el carril causal (`I_human`, sin snapshot) | No | El swarm compara siempre con S0, que es PRIV. En el carril que un estudio de «agente con información humana» debería priorizar, el competidor es P0/B1, y ahí no hay prior empírico (Firoiu sí: modelo propio ayudó contra rivales que aprenden). **PENDIENTE** (H6) |
| X7 | Abstracción temporal (bloques/eventos) | Reconocido como posible por A4/A5 | Más horizonte por ms; solo importa si V̂ no basta (C3). **PENDIENTE**, depende de H9 |
| X8 | Plataformas sin simulador (take-back solo Linux; ISO necesaria; `train/` exige torch ≥ 2.11) | Reconocido (A4 §6.2) | Nicho práctico real pero el modelo también se entrena con datos del juego. SOPORTADA como nicho de despliegue, irrelevante para la fuerza de juego |

### 3.2 Confusores y fugas que debe controlar cualquier conclusión

1. **Selección de checkpoints de Faynt con rivales slippi-ai** (fila 26): cualquier test con esas versiones como
   rivales y Faynt como prior/referencia está contaminado. Además las 240/244 victorias son contra rivales con 21–24
   frames de cola; el panel a 0 frames es un único checkpoint rival (68 partidas = 1 réplica de rival).
2. **Fuga por set en ranked** (sin `match_id`, códigos ni fechas, A6-015) y **origen común** de MRR y HAL ranked
   (A6-023): `S_game` no mide generalización a jugadores ni a sets.
3. **Splits por defecto con fuga**: slippi-ai `swap=True` mezcla perspectivas (fila verificada `data.py`
   L559-583/L609); LeWM por ventanas; HAL pro duplica entre carpetas de jugadores (A6-017/A6-018).
4. **Asimetría de demora** en todas las cifras cruzadas publicadas (HAL 2 vs 21; Faynt 0 vs 21–24; MIMIC 0 vs 18).
5. **Pseudorreplicación**: HAL 96 partidas por par, MIMIC 30–0 vs CPU-9, Faynt 68 partidas vs un checkpoint, Firoiu
   6–8 partidas por agente. Simulación propia: agrupar partidas de una semilla da 26 % de falsos positivos con
   σ_s = 5 pp [A8-010].
6. **Tiempo de entrenamiento** en Firoiu (3 vs 10 días).
7. **RNG no controlable**: Dolphin no se siembra (A8-007); sim no reenvía semilla (fila 6) → los «pares» del
   protocolo no son números aleatorios comunes del juego.
8. **Motores distintos**: runtime de melee-llm fija melee-brute `090e54b0` (sin `hitlag_left`, ABI 1208 B) y la
   granja usa un checkout `MELEE_SIM` de revisión no registrada (A1 §11.3); resultados de farm y de `--mode sim`
   pueden no ser comparables. libmelee instalado 0.47.6 ≠ clonado 0.47.3 (A1-026).
9. **Canales privilegiados latentes**: `controller_state` del rival (I_full); FrameStart `random_seed` en el flujo
   Slippi que reciben los bots (A5-036, DESC); V̂ con estado presente en entrenamiento (A2 D3).
10. **Reloj**: `fast` y `realtime` sin plazo permiten cómputo ilimitado (A7-001); sin `RT-strict` toda afirmación
    de tiempo real es `RT-slow`.
11. **CPU-9 explotable** (Firoiu): no sirve como ancla de fuerza.
12. **El pool puntuado del bench importa partidas `lockstep` externas** (fila 3): un Elo del bench mezcla relojes
    de ejecución distintos.
13. **Hardware**: todas las cifras de simulador y Dolphin son de otras máquinas (5950X/9950X3D/3090); las de torch
    son de este EPYC compartido con load 2,6–7,7.

### 3.3 Qué evidencia concreta cambiaría la recomendación

| Si se observa… | …la recomendación pasa a |
|---|---|
| G1/H12: pipeline fusionado GPU ≥ 10× transiciones/s por coste que la granja | priorizar W2 (imaginación) sobre MPC; la dinámica aprendida deja de ser «sin valor en sim» |
| G4/H5: sombra exacta < 95 % de frames en partidas del bench, o imposibilidad de inyectar RNG por API | el nicho de la dinámica aprendida es el bench entero; W0/W1 en Dolphin pasan a línea principal |
| G4/H5: sombra exacta ≥ 99 % con RNG inyectable | el nicho Dolphin desaparece en la práctica; queda solo `I_human`/PRIV-free |
| G3/H7: regret_W ≤ regret_S0 + pequeño margen y < regret_P0 | MPC aprendido viable donde S0 no existe; seguir a G6 |
| G5/H1: S0 − P0 equivalente a 0 (±5 pp) con ≥ 400 partidas | cerrar MPC (W0/W1) en ese evaluador; invertir en q, V̂ y S-teach |
| G5/H8–H9: |Δ(q)| ≫ |Δ(dyn)| y S0-Vperm ≈ P0 | confirmar C3: prioridad absoluta a q y V̂ |
| G2: W0-S no bate persistencia en eventos a h=4–8 | no hay dinámica aprendida útil con el corpus disponible; parar W0/W1 |
| G7/H4: E1-S ≥ E1 | el beneficio, si existe, no es «JEPA» |
| Medición en la misma máquina: S0 por la ruta real ≥ 10× más caro que W0-S-1M | reabrir la comparación a igual tiempo (K6) |

---

## 4. Clasificación de las conclusiones del swarm

**SOPORTADA** = sostenida por código inspeccionado o medición propia con artefacto; **INFERIDA** = deducción
razonable sin medición del hecho; **PENDIENTE** = requiere un experimento que nadie ha hecho.

| # | Conclusión | Origen | Clase | Comentario |
|---|---|---|---|---|
| 1 | El bench solo corre en Dolphin (`fast`/`realtime`), nunca en sim | A1 | SOPORTADA | fila 3 |
| 2 | En `realtime` Dolphin espera el mando; ningún modo impone plazo a un agente every-frame | A1/A7 | SOPORTADA | fila 2; bot-writer es la excepción |
| 3 | Todo agente recibe el mando actual del rival | A1 | SOPORTADA | sin crudos completos (A8-003) |
| 4 | No hay hook para planificar ni para pasar el `World` al agente | A1 | SOPORTADA | fila 7 |
| 5 | No existe `GameState → estado del simulador` | A1/A4 | SOPORTADA (CÓD) | solo `configure_match`/restore |
| 6 | SIGReg no garantiza contenido informativo; vistas espejo/fase borran control | A3 | SOPORTADA (REP en juguete) | magnitudes no transferibles |
| 7 | SIGReg domina el coste de entrenamiento de modelos de estado pequeños en CPU | A7 | SOPORTADA (REP) | K1 |
| 8 | No hay pesos JEPA reutilizables para Melee-estado | A3 | SOPORTADA (inspección de fichas) | |
| 9 | Ningún bot moderno publicado usa predicción de estado en inferencia | A2 | INFERIDA | inspección de código, sin cargar pesos |
| 10 | El predictor de Firoiu ayuda con p = d frente a rivales que aprenden | A2 | INFERIDA (DOC débil) | confundido por días de entrenamiento (A8-004) |
| 11 | El juego es simultáneo; el árbol alternado acota pero no resuelve | A5 | SOPORTADA (DOC+CÓD) | fila 11 |
| 12 | Reaccionar un frame tarde cambia el valor (0 → 0,382) | A5 | SOPORTADA en su alcance | menús, horizonte, sin escudo |
| 13 | En CPU un modelo aprendido no es más rápido que el simulador | A4/A5/A7 | INFERIDA | sin medición del simulador en la misma máquina (fila 9) |
| 14 | Un MPC aprendido en RT en esta CPU es pequeño (≈1M, K·T ≈ 1.000) | A7 | SOPORTADA (REP) | sin Dolphin corriendo; sin KV-cache |
| 15 | S0 es cota superior de W a igual conteo | A5 | INFERIDA (lógica) | no a igual tiempo |
| 16 | En sim la dinámica aprendida no aporta frente a S0 | A4/A5 | INFERIDA | y fuera del objetivo (bench = Dolphin) |
| 17 | El nicho de la dinámica aprendida es Dolphin tras divergencia de RNG | A4/A5 | **PENDIENTE** | depende de una sombra no construida, mal fundada (filas 24–25) |
| 18 | q (rival) y V̂ importan más que la dinámica | A4/A5 | **PENDIENTE** | H8/H9 |
| 19 | Entrenar en imaginación no aporta mientras corra el simulador | A4 | **PENDIENTE** | X1 sin refutar |
| 20 | B2 aísla representación; E1-S es el control decisivo | A3 | SOPORTADA como diseño | resultado PENDIENTE (H4) |
| 21 | HAL publicado no es BC puro; MIMIC `fox-master` de linaje dudoso | A2 | SOPORTADA (CÓD) / INFERIDA | |
| 22 | El post-frame no es Markov; la dinámica necesita historia de mandos | A4/A6 | SOPORTADA (DOC del autor del simulador) | H se fija con test de aliasing, PENDIENTE |
| 23 | Solo el .slp crudo conserva RNG y crudos; HAL MDS es pobre para dinámica | A6 | SOPORTADA (CÓD) | |
| 24 | Separación por jugador imposible en ranked; fuga por set inevitable | A6 | SOPORTADA (DOC) | |
| 25 | Nada de PPO, simulador ni partidas es ejecutable aquí | A2/A6/A7 | SOPORTADA | sin ISO, sin GPU, sin `peppi_py` |
| 26 | La evaluación (no el entrenamiento) domina la pared en RT | A7 | INFERIDA | aritmética sobre fps documentados |
| 27 | El «S0-ceiling» de 40 partidas es el experimento más barato que falsa MPC | A5 | **INFERIDA y mal dimensionada** | 40 partidas → MDE ≈ 31 pp (A8-014) |

---

## 5. Problemas de proceso detectados

- Localizadores inexistentes en A1 para `bench/game.py` (fila 5) — el consolidador no los detectaría: validar el
  esquema no comprueba que las líneas existan (06 L145). Recomiendo un chequeo automático «la ruta existe y el
  rango de líneas ≤ longitud del fichero» para todos los `source_refs` con SHA local.
- Scripts de A7 en `pilot/a7_bench/` fuera de `evidence/A7/`; A7 declara picos de RSS de hasta 1,62 GB (> tope de
  1 GB del brief).
- El brief dice `sources/<owner>__<repo>`; en disco es `sources/<owner>_<repo>`.
- El catálogo fija melee-llm `2bf8b0eb`, no presente en el clon shallow; A1 afirma que el runtime es idéntico a
  `7e179081` vía `git diff --stat`, lo que exige haber traído ese commit: no lo repetí.
