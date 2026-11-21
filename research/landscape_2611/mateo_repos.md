# Repos de Mateo (`mateo19182`) desde las revisiones estudiadas

Consulta: 2026-11-21 (13:52 UTC). Fuentes: `gh api users/mateo19182/repos --paginate`, clones en `sources/`
(no versionado), `gh pr list --state all`, `gh issue list --state all`.

Etiquetas: **SOPORTADO** = leído en código o docs del repo, con ruta y SHA. **INFERIDO** = deducción nuestra.
Las cifras de Mateo son **del autor, no reproducidas**.

## 1. Resumen

El intervalo es muy corto: nuestra revisión fijada de melee-llm (`7e179081`) es del 2026-11-19 12:21 (+01:00), y
melee-brute (`9662ec97`) sigue siendo HEAD de `main`. Desde entonces:

- **melee-brute:** sin cambios en `main`. El simulador, su API de paso y el pin `090e54b0` siguen igual.
- **melee-llm:** 2 PR fusionados (#110 SEO de la web, #111 resultados de E32 + Faynt bajo retraso). No cambian el
  bench, el registro de entrantes, el runner, el simulador, la interfaz del agente ni `docs/bench.md`/`docs/delay.md`.
- Lo único con peso para nosotros es **E32**: una medición del autor de que una política fuerte sin retraso se
  hunde con 1 frame de retraso. Refuerza la premisa del "predictor del presente bajo demora".
- Además, una rama no fusionada (`origin/student`, PR #99 abierto, E25) que no habíamos leído: un "student" de HAL
  que recibe los mandos pendientes como entrada para jugar con retraso.

## 2. Repos públicos de `mateo19182`

79 repos (incluidas forks). Marcados los relacionados con Melee o IA de juegos/benchmarks de agentes.

| Repo | Fork de | Último push | Relación | Acción |
|---|---|---|---|---|
| **melee-llm** | — | 2026-11-21 | **Melee**: bench, bots, farm, web (melee.m19182.dev) | Clonado y analizado |
| **melee-brute** | kyhavlov/melee-sim-light | 2026-11-19 | **Melee**: simulador + búsqueda | Clonado y analizado |
| **melee** | doldecomp/melee | 2026-11-19 | **Melee**: decompilación. `master` idéntico a upstream (0 por delante, 0 por detrás); una rama `refactor/motion-id-literals` (`e8a4a22a`, constantes en comparaciones de `motion_id`) | Solo inspeccionado vía API; sin interés para el plan |
| escobaBenchmark | — | 2025-02-06 | Benchmark de LLM jugando a la Escoba (cartas) | No clonado (no es Melee) |
| ee-bench | — | 2026-04-03 | Benchmark explore/exploit para LLM (bandits, etc.) | No clonado |
| gym-agents | — | 2025-02-28 | Pese al nombre, agente smolagents (gimnasio deportivo), no Gym/RL | No clonado |
| agame | — | 2026-06-22 | Juego de trivia/minijuegos para dos (Cloudflare) | No relacionado |
| arcus-ctf | — | 2026-06-13 | CTF de ML (diff de checkpoints) | No relacionado |
| Resto (≈71) | — | — | Música, finanzas, mapas, LLM en castellano, utilidades, forks varios | No relacionados |

## 3. Revisiones

| Repo | Revisión fijada (nuestra) | HEAD actual | Fecha HEAD | Commits nuevos |
|---|---|---|---|---|
| mateo19182/melee-llm | `7e179081c6cbab139d860c998b1452ad3dee047c` (2026-11-19 12:21 +01:00) | `f274f930508af32498912d4583ed6040c7d196b9` | 2026-11-21 12:50 +01:00 | 4 (2 merges) |
| mateo19182/melee-brute | `9662ec973b9e077ff7b0ff89d6db950f53c11653` | `9662ec973b9e077ff7b0ff89d6db950f53c11653` | 2026-11-19 12:04 +01:00 | 0 |
| melee-brute fijado por melee-llm | `090e54b048b7d51e82f9f6b551046c2ca8b130c7` | sigue `090e54b0` en `pyproject.toml` L38 y `uv.lock` L587 @ `f274f930` | — | — |
| mateo19182/melee (fork decomp) | — | `master` = upstream | 2026-11-19 | — |

Clones: `sources/mateo19182__melee-llm`, `sources/mateo19182__melee-brute`.

Ramas de melee-brute: ninguna rama remota tiene commits posteriores a `main` con contenido nuevo (las más recientes,
`goal-zones`, `zone-frames`, `coverage-competitive`, `upstream-checkpoint`, ya están contenidas en `main`; las que van
por delante son de septiembre-octubre: visor, Mewtwo, escenario Stadium, `legacy-sim`). Upstream
`kyhavlov/melee-sim-light` sigue en `eea7b5fb` (2026-10-20), igual que en `ops/clone_inventory.txt`. **SOPORTADO**.

## 4. Cambios en melee-llm `7e179081..f274f930`

| Commit / PR | Qué cambia | Archivos |
|---|---|---|
| [`912602e6`](https://github.com/mateo19182/melee-llm/commit/912602e64afee352cba935e776330495a58ec5cc) / PR #110 | SEO: `<title>`, Open Graph, canónicas, `robots.txt`, `sitemap.xml`. Sin efecto en el bench | `melee_llm/web/server.py`, `web/static/index.html`, `pages/brute.js`, `pages/docs.js`, `tests/test_web_public.py`, `writeup/*` |
| [`339b6a0b`](https://github.com/mateo19182/melee-llm/commit/339b6a0baf82e8390eccf472b83ca647c876da2c) / PR #111 | Resultados de E32 (RL estilo Faynt para Yoshi en la farm); `delay=N` y `own=1` en el cerebro Faynt de la farm; opción `own` en `bot_faynt.py`; `meleebot.stomped` sirve checkpoints Faynt (`HalBrain` → `ServerBrain`) | `docs/experiments/E32-yoshi-rl.md`, `docs/experiments/README.md`, `docs/status.md`, `docs/bots.md`, `docs/web-ui.md`, `melee_llm/bots/bot_faynt.py`, `train/farm/faynt.py`, `train/farm/run.py`, `train/meleebot/stomped.py` |

Comprobado con `git diff --stat 7e179081 f274f930 -- melee_llm/bench melee_llm/sim melee_llm/runner.py
melee_llm/bots/agent.py melee_llm/bots/server.py docs/bench.md docs/delay.md docs/simulator.md pyproject.toml uv.lock`:
**salida vacía**. **SOPORTADO**.

### 4.1 Por pregunta

| Pregunta | Respuesta | Etiqueta |
|---|---|---|
| ¿Entrantes nuevos (`melee_llm/bench/entrants.py`, registro)? | **No.** `entrants.py` sin cambios. El entrante `faynt` (L98-100 @ `f274f930`) no pasa `own`, que por defecto es `False` (`bots/bot_faynt.py` L59), así que su comportamiento en el bench no cambia | SOPORTADO |
| ¿Protocolo del bench (relojes, Elo, retraso)? | **Sin cambios** en `docs/bench.md`, `docs/delay.md` ni en `melee_llm/bench`. El retraso nuevo (`delay=N`) está solo en la farm de entrenamiento (`train/farm/faynt.py`, docstring de `FayntBrain`: "the pad chosen after reading frame F is applied on frame F + 1 + N"), no en el bench | SOPORTADO |
| ¿Simulador: semilla RNG por frame, arranque a mitad de partida, API de paso nueva? | **No.** melee-brute sin commits; el pin sigue en `090e54b0`; `src/runtime/batch.c` L324-326 @ `9662ec97` sigue pasando `frame_seed = match->random_seed` con `&no_stage_events`. `melee_llm/sim/` sin cambios | SOPORTADO |
| ¿Interfaz del agente: expone `World` o el flujo Slippi crudo? | **Sin cambios.** `sim/runner.py` L47-56 @ `f274f930` sigue llamando `a.setup(world.controllers[p], p, …)` sin pasar el `World`. El flujo crudo sigue llegando solo a bots con venv propio vía `ConsoleTap` (`bots/agent.py`, sin cambios). `stomped.py` ya leía el flujo de eventos `.slp` en el pin; ahora además lo reenvía a Faynt | SOPORTADO |
| ¿Rendimiento declarado? | E32 (autor): 1.000 pasos PPO, 131 M frames, 25,5 h; ~1.850 frames/s en la farm. En Dolphin sin retraso, paso 1000 gana 85/88 a diez rivales; Elo de liga 1299 (CPU 9 Fox = 0) frente a 1193 de Faynt Arena con Fox. **Con retraso:** 0/48 desde 1 frame; con `own=1`, 42/48 a 1 frame, 20/48 a 2, 0 desde 4 (`docs/experiments/E32-yoshi-rl.md` §Result @ `f274f930`) | DOCUMENTADO POR EL AUTOR |
| ¿Algún entrante con modelo del mundo, búsqueda o predicción de estados? | **No** en `main`. Lo más cercano: (a) `own=1`, que sustituye el mando aplicado por el último elegido (no predice estado); (b) E25 en rama `student` (abajo), que condiciona la política a los mandos pendientes, sin predecir estados; (c) rama `nash-solver-run-in` (`bf4ddfe`, 2026-11-16): sondas del solver de búsqueda, ya contenida en lo que conocíamos salvo un commit de scripts | SOPORTADO |
| Plazo del proyecto | `docs/status.md` L51 @ `f274f930`: "Mateo gives the project one or two more weeks (decided 2026-11-14)". Próximo paso declarado: E33, la misma RL con retraso 10 | SOPORTADO |

### 4.2 Rama no fusionada que no habíamos leído: `origin/student` (PR #99, abierto)

`963f3dd` (2026-11-18), 8 commits por delante de `main`. `docs/experiments/E25-student.md` @ `963f3dd`:

- Un modelo pequeño (6,7 M y 14,8 M) que reutiliza el codificador y el tronco de HAL y recibe **los d mandos ya
  enviados y el número d** en una cabeza de dos capas; emite la acción del frame t+d+1. El tronco no ve d.
- Etiquetas de los juegos con retraso: lo que haría el maestro **viendo el presente** (`train/haltrain/relabel.py`;
  paso tipo DIDA).
- Velocidad (autor, pesos aleatorios): ~15.000 frames/s con 1.024 partidas; el límite pasa a ser el simulador.
- Resultado (autor): todos los students sobreajustan los juegos con retraso; el primero, pesos finales, gana 0/64 al
  Fox Master de HAL con retraso 10. "Best checkpoints: running". Sin veredicto.

No hemos encontrado mención de E25, `student` ni `haltrain` en `evidence/`, `deliverables/` ni `decision/`.
**SOPORTADO** (lectura del doc del autor; números no reproducidos).

### 4.3 Issues y PR

- melee-llm: issues habilitados pero **ninguno** (abierto ni cerrado). Últimos PR: #97-#111, todos fusionados salvo
  #99 (abierto, E25). #106-#109 ya estaban en nuestro pin.
- melee-brute: issues deshabilitados. Últimos PR #12-#19 (2026-11-17/19), todos ya en `9662ec97`; #15 cerrado sin
  fusionar ("solve: one process a core by default").

## 5. Impacto en nuestro plan

| Conclusión o plan nuestro | Estado tras los cambios | Etiqueta |
|---|---|---|
| Simulador sombra (G-01, E5): "factible con cambios" = API C `msl_batch_step_recorded` con semilla por frame y eventos de escenario + binding + decodificador de `ConsoleTap` | **Sigue igual, ni resuelto ni empeorado.** La API pública no ha cambiado (`batch.c` L324-326 @ `9662ec97`), ni el pin de melee-llm (`090e54b0`). Seguimos teniendo que hacer los tres cambios | SOPORTADO |
| Punto de integración del planificador: no hay hook; hay que tocar `sim/runner.py` L47-53 | **Sigue igual.** `sim/runner.py` sin cambios en `f274f930` | SOPORTADO |
| Exigencia de Slippi ≥ 3.17.0 (C-stick crudo) para la sombra y para el esquema de mandos | **Sin novedades.** Nada en el diff toca `sim/slippi.py`, la versión declarada (3.19.0) ni la lectura del flujo | SOPORTADO |
| `runner.play(mode="sim")` no reenvía `seed`; los pares de evaluación no comparten RNG | **Sigue igual** (sin cambios en `runner.py` ni en `sim/`) | SOPORTADO |
| Premisa de la decisión: probar primero un **predictor del presente bajo demora** | **Reforzada, con evidencia del autor.** E32: Faynt (sin entrada de retraso) pasa de 48/48 a 0/48 con 1 frame; darle sus propios mandos recupera 1 frame pero no 4. Es exactamente el hueco que un predictor del presente cubriría. No es una medición nuestra ni de un predictor | DOCUMENTADO POR EL AUTOR + INFERIDO |
| `own=1` como línea base | **Nueva línea base barata a incluir** en los brazos con retraso: "alimentar a la política con su último mando elegido". Cualquier predictor del presente debería superarla a ≥ 2 frames | INFERIDO |
| Riesgo de solapamiento con Mateo | **Moderado y creciente.** E33 (RL con retraso 10, mandos propios, crédito desde el frame de aterrizaje) y E25 (política condicionada a mandos pendientes) atacan el mismo problema por la vía de la política, sin modelo explícito de dinámica. Si E33 funciona, nuestra comparación debe incluir "RL con retraso" como brazo, no solo imitación | INFERIDO |
| Brazos B*/RL sin dinámica explícita | El autor confirma que la farm (melee-brute) ya sirve para RL estilo Faynt a ~1.850 frames/s y que lo aprendido se transfiere a Dolphin (E32). Refuerza usar la farm para generar datos con retraso; no cambia el diseño | DOCUMENTADO POR EL AUTOR |
| Licencia de Faynt (A2-027: "Do not use or adapt Faynt for Slippi Online") | Mateo adapta Faynt para stomped.dev (no desplegado). No nos afecta directamente, pero si usamos checkpoints derivados de Faynt (p. ej. `yoshi-rl-1`) hay que revisar esa restricción | INFERIDO |
| Estabilidad de la plataforma | `docs/status.md` L51: el proyecto tenía "una o dos semanas más" desde el 2026-11-14. Es probable que melee-llm se congele pronto: conviene mantener nuestros pines y no esperar que Mateo añada el hook o la API de paso grabado | INFERIDO |
| Ninguna conclusión de `HECHO.md` queda **obsoleta** | Correcto a `f274f930` / `9662ec97` | SOPORTADO |

### Acciones sugeridas (no ejecutadas)

1. Añadir `own=1` (último mando propio) como línea base en el plan de experimentos con retraso.
2. Leer E25 y seguir PR #99 y E33; si E33 publica resultados, añadir "RL con retraso" como comparador.
3. Mantener los pines `7e179081` / `9662ec97` / `090e54b0`; los cambios nuevos no obligan a moverlos.
