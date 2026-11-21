# Panorama de agentes de Melee a 2026-11-21

Agentes de IA para Super Smash Bros. Melee que compiten con nuestro proyecto o con los entrantes del benchmark
de Mateo. Quedan fuera los repos de mateo19182 y el leaderboard (https://melee.m19182.dev), que cubren otros
agentes.

**Etiquetas.**
- **SOPORTADO**: leído en la fuente citada (commit, documento, model card o paper).
- **INFERIDO**: deducción nuestra a partir de esas fuentes.

Todas las cifras de fuerza son de sus autores. No se ha descargado ningún peso ni se ha jugado ninguna partida. No se
ha clonado nada en `sources/`: bastó con `gh api`, la API de Hugging Face y la web.

## 1. Repos ya estudiados: qué ha cambiado desde la revisión fijada

Revisiones fijadas tomadas de `ops/clone_inventory.txt`. Para cada repo se consultaron los commits desde esa fecha en
todas las ramas activas, los eventos, las releases, los PR y los issues.

| Repo | Fijada (fecha) | Actividad posterior | Qué cambia para nosotros |
|---|---|---|---|
| vladfi1/slippi-ai | `5ada33e9` (2026-10-20) | `main` no ha cambiado. Hay trabajo en ramas: `rl` (`de37acf9`, 2026-11-20), `mamba` (`59121895`, 11-04), `netplay-dev` (`a2758eaa`, 11-20) y `gui`. Releases del lanzador de Windows 0.3.0–0.3.4 (10-09 → 10-31). PR #56: LSTM fusionado, 1,5× más rápido. Issue #55: los modelos del instalador se autodestruyen al ser lanzados fuera del escenario. | **SOPORTADO:**<br>- `eval_db`: base de datos de agentes desplegados con ratings (`6a3ebca0`). `train_many` hace juego cruzado entre agentes. El bot de Twitch elige agentes por rating (`d062800e`).<br>- RL de autojuego con Mamba2 en el simulador (`sim-env`) a unos 70k fps de entorno con 256 entornos. **Diverge en unas 50 actualizaciones**; la hipótesis de los autores es que las ventajas están sesgadas por el crítico (`docs/experiments/mamba_rl.md`, rama `mamba`).<br>- Ya en la revisión fijada, y no recogido en nuestra auditoría: `docs/plans/nash_policy_delay.md` define un «juego de cadenas» bajo retraso. Cada jugador conoce su propia cola de acciones y **no la del rival**, y se resuelve un Nash sobre cadenas de acciones muestreadas. |
| vladfi1/phillip | `114aea4c` (2026-07-06) | Ninguna | — |
| vladfi1/libmelee | `bce21f09` (2026-07-29) | `master` no ha cambiado. La rama `dev` sube a 0.47.6 (2026-10-17). | Nada relevante. HAL fija su propia variante `0.47.0+hal.realtime.1` (SOPORTADO, `hal/sim/NATIVE.md`). |
| ericyuegu/hal | `37045d97` (2026-10-15) | `main` no ha cambiado. La rama `o63-delay-posttrain` (`2121c13d`, 11-15) va **276 commits por delante**. Ramas `o65-*` y `o64-*`. Los pesos de HF siguen en `e7fb8378`. | **SOPORTADO:**<br>- O63: condicionamiento por percentil del retorno (proxies de 17M; métrica primaria `net_stock_lcb` sobre 96 emparejamientos).<br>- O64: PPO con recompensa de resultado sobre 247M.<br>- **O65: PPO de autojuego en melee-sim-light** (rama de MSL `o65-hal-parity`), con crítico HL-Gauss separado, liga PFSP con *exploiters*, ablaciones de colapso y una sonda de explotabilidad contra un rival congelado.<br>- Brazos con retraso de 16 frames (`3d43e777`, `2121c13d`).<br>- Servicio de netplay para humanos: 8 plazas, retraso 2 o 3, p99 de 15,32 ms (`deploy/netplay/status.md`).<br>- Despliegue con «prediction 4, delay 2, replan 2» (`experiments/o63/treatment.md`).<br>- **No publica resultados contra humanos.** |
| erickfm/MIMIC | `3691f534` (2026-11-17) | `main` lleva un commit más (11-17). La rama `coach` va 84 commits por delante. HF sigue en `f49879b6`. | **SOPORTADO:**<br>- `coach` rl-v4 (S, 5,4M, 200 actualizaciones): Fox 162–30, Falco 169–23, Marth 181–11 y Sheik 178–14, **cada uno contra su propio padre BC** (192 partidas; `docs/research-notes-2026-11-17.md`).<br>- `docs/findings.md`:<br>&nbsp;&nbsp;· RL en el simulador nativo de la decompilación;<br>&nbsp;&nbsp;· sin crítico, porque su varianza explicada era negativa;<br>&nbsp;&nbsp;· las mejoras en el simulador **se trasladan a Dolphin** (109–83 en el simulador y 130–70 en Dolphin contra fox-master);<br>&nbsp;&nbsp;· el modelo L (44M) empata con el M (20M);<br>&nbsp;&nbsp;· la atención por ventana deslizante pierde en juego. |
| frisson-labs/Reyn | `93fa5274` (2026-11-13) | Ninguna en el repo. En HF aparecen **Reyn-Pair** y **Wombo-Combo** (11-13, MIT). | Dirección por lenguaje en 2v2 y combos cooperativos contra un muñeco. Las fichas lo dicen: no hay evidencia de fuerza (SOPORTADO). |
| Na00s/Faynt-Tournament / Faynt-Benchmarks | `d2096176` / `39bc0075` (2026-09-29) | Ninguna. Los pesos de Faynt en HF son de 09-30. El paper solo tiene la v1. | Ver la fila de Faynt en §2. |
| kyhavlov/melee-sim-light | `eea7b5fb` (2026-10-20) | `main` no ha cambiado. PR abiertos: visor, sonido Wasm (briandle00) y el **#102 «In-place checkpoint and rollback of one environment»** (mateo19182, 11-16). | Es la base de RL de HAL O65 y de slippi-ai `sim-env`. El #102 habilitaría la búsqueda por bifurcación del estado (INFERIDO). |

## 2. Tabla de agentes

Incluye los entrantes ya conocidos con su estado actualizado y los proyectos nuevos de 2025–2026 hallados con
`gh search repos` (consultas: melee, «melee ai», «melee bot», «slippi ai», ssbm, «fighting game agent»…), con la API
de modelos de HF y con búsqueda web.

| Nombre | Enlace | Método | Evidencia de fuerza | Fecha | Licencia |
|---|---|---|---|---|---|
| **Faynt-10M/75M** (Base, Expert, Arena) | [arXiv 2610.02144](https://arxiv.org/abs/2610.02144) · [HF](https://huggingface.co/collections/frisson-labs/faynt) | Transformer multipersonaje: BC sobre unas 840k partidas, currículo, destilación de 75M a 10M y PPO en Dolphin (96 emuladores, solo Fox ditto, autojuego más CPU-9). 0 frames de retraso. **Solo predice acciones**, más un valor durante el RL. Sin búsqueda (§2.3, §4.4, §5.5). | SOPORTADO: 240/244 contra 14 releases que juegan con 21–24 f de retraso, y 68/68 contra un slippi-ai privado a 0 f. **Ninguna partida contra humanos.** Selección de checkpoints contaminada (§4.4). | 2026-10-01 | MIT, «offline use only» |
| **slippi-ai / Phillip II** | [GitHub](https://github.com/vladfi1/slippi-ai) | BC con retraso de 18–24 f seguida de PPO con KL al maestro en autojuego. Ramas nuevas: Mamba2 y RL en el simulador. Q/Nash con retraso. | SOPORTADO: **el único con partidas grabadas contra humanos de élite** (Zain, aMSa, Cody, Moky y Aklo; README §Recordings), sin cómputo de resultados publicado. Juega en abierto en Twitch. | Activo (11-20) | MIT |
| **HAL** | [GitHub](https://github.com/ericyuegu/hal) | Transformer 250M con AWR y condicionamiento por retorno. Ejecuta trozos de acciones (predice 4 y replanifica cada 2). Ahora PPO de autojuego en liga sobre MSL. | SOPORTADO: h2h contra Phillip ya auditado (`deliverables/BASELINES.md`). Hay servicio para humanos, pero **sin resultados publicados**. | Activo (11-15) | Código sin licencia; pesos MIT |
| **MIMIC** (coach) | [GitHub](https://github.com/erickfm/MIMIC) · [HF](https://huggingface.co/erickfm/MIMIC) | BC por personaje (5,4M/20M, Shaw RPE, 180 f) más PPO sin crítico en el simulador nativo. | SOPORTADO: solo contra su padre BC y contra CPU-9. No hay pesos rl-v4 en HF (la sha no ha cambiado). | Activo (11-17) | MIT |
| **Reyn-26C / Reyn-Pair / Wombo-Combo** | [HF](https://huggingface.co/frisson-labs) | Tronco Faynt con adaptadores dirigidos por órdenes o lenguaje | Ninguna (lo declaran las fichas) | 2026-11-13 | MIT |
| **mrcal17/melee-sim** | [GitHub](https://github.com/mrcal17/melee-sim) | Simulador sin interfaz sobre melee-pc (decompilación), «bit-exact» en los conjuntos de repeticiones que verifica. Entorno por lotes, PPO de autojuego y liga con *exploiters* (GRU con 3 cabezas). | Ninguna publicada | Creado 2026-11-18 | Sin LICENSE; el código decompilado no tiene licencia |
| **4Stockfish** | [GitHub](https://github.com/noahpodgurski/4Stockfish) | «Motor de ajedrez» de Melee: **búsqueda en árbol con el simulador real** (melee-pc) para encontrar combos, ordenados por daño, KO o ventaja posicional. Es una herramienta de análisis, no un agente. | Probado solo contra CPU. **La búsqueda no incluye el DI ni el tech del rival** (README, «Current limitations») | 2026-10-19 → 11-07 | Mixta; el código decompilado no tiene licencia |
| **justincg/melee-wm-weights** | [HF](https://huggingface.co/justincg/melee-wm-weights) | Modelo del mundo en **píxeles** sobre el latente congelado de DINOv3 ViT-L: 20 fps, 38–39 frames de contexto, 20 desenrollados y *dropout* de acción del 10 % (`world_model_config.yaml`). Código «mira», no publicado. | Ninguna. Los `eval.log` acaban en un error de carga. Sin ficha. | 2026-09-04 | No declarada |
| ExPhil | [GitHub](https://github.com/blasphemetheus/exphil) | Laboratorio de arquitecturas en Elixir: BC con más de 30 troncos (MLP, LSTM, Mamba…). PPO pendiente. | Ninguna. Benchmarks de troncos sin fecha. | 2026-01 → 11 | MIT |
| fax (tesis de máster, LIACS) | [GitHub](https://github.com/Josef-Hlink/fax) · [tesis](https://theses.liacs.nl/pdf/2025-2026-HamelinkJJosef.pdf) | Imitación con un GPT: generalista frente a especialista en Fox ditto | Académica, sin rivales fuertes (INFERIDO) | 2025–2026 | MIT |
| melee-rl-fox-mango | [HF](https://huggingface.co/Mathoo1/melee-rl-fox-mango) | PPO en un motor de física propio y luego ajuste fino en Dolphin, Fox contra Puff | Ninguna | 2026-03 | No declarada |
| aimelee / nojohns / slippi-ai-app | [aimelee](https://github.com/zurgace/aimelee) · [nojohns](https://github.com/ScavieFae/nojohns) | Envoltorios para jugar contra Phillip (en nativo, en un arena entre agentes o en una app) | No son agentes nuevos | 2026 | Varias |
| **Juegos de lucha en general** | [COMBAT, 2603.00825](https://arxiv.org/abs/2603.00825) · [Fight World Model, 2610.40607](https://arxiv.org/abs/2610.40607) · [GenBR, 2302.00797](https://arxiv.org/abs/2302.00797) | COMBAT: modelo del mundo de difusión en Tekken 3 que simula un rival reactivo. FWM: vídeo condicionado por reglas de combate. GenBR: MCTS con un modelo generativo del rival. | Según los resúmenes de búsqueda, ninguno informa de fuerza competitiva contra humanos (INFERIDO, sin leer los PDF) | 2026 | — |

No se encontró ningún agente ni paper de 2025–2026 que use JEPA, MCTS o un modelo del mundo aprendido **para jugar** a
Melee (INFERIDO: búsqueda en GitHub, HF y web; no es exhaustiva).

## 3. Qué predicen y si separan lo predecible de lo impredecible

| Agente | Qué predice en inferencia | ¿Separa la mecánica de la decisión del rival? |
|---|---|---|
| Faynt | Solo el mando propio en el frame siguiente (SOPORTADO, §2.3) | No |
| slippi-ai | El mando propio con 18–24 f de antelación. En entrenamiento, Q y Nash sobre «cadenas» | **Parcialmente, y en el eje de la información, no en el de la mecánica.** El juego de cadenas distingue la cola propia, conocida, de la del rival, oculta (SOPORTADO, `nash_policy_delay.md`). No modela qué frames del rival están ya comprometidos. |
| HAL | Un trozo de 4 acciones propias. La cabeza de retorno, el valor y el `StateHead` son auxiliares | No |
| MIMIC | El mando propio, con cabezas condicionadas en cadena | No |
| 4Stockfish | Simula exactamente con el motor | **Implícitamente:** busca combos suponiendo que el rival no actúa (sin DI ni tech). Explota solo la parte comprometida, sin saber dónde termina (SOPORTADO, README; la lectura es INFERIDA). |
| justincg WM | Frames futuros en un latente de píxeles, condicionados por la acción | No: lo predice todo por igual (INFERIDO, por la configuración) |
| Phillip 2017 | Su propio estado, ignorando al rival (`deliverables/BASELINES.md`) | No |

**Lectura (INFERIDO).** Nuestro E0c mide que un jugador tiene su acción fijada por la mecánica a 7 frames solo el
15,5 % del tiempo (8,3 % a 13 f), y que en esos frames el estado acierta ~99 %
(`evidence/E0/predictability/PREDICTABILITY.md`). Ningún competidor trata esa ventana como objeto de predicción.
- Los que juegan con retraso (slippi-ai, HAL a 16 f) absorben la incertidumbre en la política sin hacerla explícita.
- 4Stockfish es el único que explota la ventana comprometida con un simulador exacto, pero sin un modelo que diga
  cuándo se cierra ni qué hace el rival después.

## 4. Conclusiones

### Estado del arte en fuerza de juego

- **Entre bots, el mejor documentado es Faynt-10M-Arena (SOPORTADO, atribuido).** Le gana a todas las releases públicas, a
  0 f frente a 21–24 f, y a un slippi-ai privado a 0 f (68/68). El efecto del retraso no está aislado y la selección
  está contaminada (`deliverables/BASELINES.md` §2).
- **Contra humanos, el único con evidencia pública es Phillip II de slippi-ai, a 18–24 f.** Tiene sets grabados
  contra jugadores de primer nivel, pero ningún recuento publicado. Ni Faynt, ni HAL, ni MIMIC publican una sola
  partida contra humanos (SOPORTADO).
- **Nadie usa búsqueda ni dinámica aprendida en juego** (SOPORTADO para Faynt, MIMIC y HAL, por sus documentos y
  código; INFERIDO para el resto).

### Qué métodos funcionan

Todo lo siguiente está atribuido a sus autores y no se ha reproducido.

1. **BC sobre un corpus grande de repeticiones humanas más PPO con KL hacia BC.** Es la receta común de Faynt,
   slippi-ai, MIMIC y HAL O64/O65, y el RL da los saltos grandes: Faynt Expert 23/68 → Arena 68/68; MIMIC 162–30
   contra su padre BC.
2. **Migración del RL a simuladores nativos** (melee-sim-light, la decompilación o melee-pc): HAL O65, MIMIC,
   slippi-ai `sim-env` y mrcal17. MIMIC muestra que lo ganado en el simulador se mantiene en Dolphin. Es la tendencia
   de octubre y noviembre de 2026.
3. **Problemas abiertos de estabilidad:**
   - el autojuego colapsa o diverge (ablaciones de colapso y liga PFSP con *exploiters* en HAL; divergencia de Mamba
     en slippi-ai);
   - el crítico es frágil (MIMIC lo quita; slippi-ai sospecha de ventajas sesgadas).
4. **Más escala no da más fuerza por sí sola:**
   - Faynt: tras el posentrenamiento supervisado, el 10M gana al 75M preentrenado (69,7 % frente a 45,4 %);
   - MIMIC: el L empata con el M.

### Qué implica para nuestro MVP (PROPUESTA)

- **Qué copiar:**
  - La receta B0→B1 (BC + PPO con KL) ya está decidida y la valida todo el campo.
  - El **protocolo de evaluación de HAL O65**: pares semilla/salida con cambio de puerto, `net_stock_lcb` como cota
    inferior al 95 % y **sonda de explotabilidad contra un rival congelado**.
  - El **juego de cadenas de slippi-ai** como formulación correcta de la información bajo retraso. Encaja con el
    predictor del presente (W0-S + q): la cola propia es conocida y la del rival es una distribución.
- **Contra quién compararse:**
  - Faynt-10M-Arena y Expert a 0 f;
  - Phillip `fox_d18_*` en el eje de retraso;
  - MIMIC fox S como segunda referencia BC.
  - HAL sigue fuera por licencia, aunque sus brazos de retraso 16 son el rival natural si los publica.
  - Para afirmar algo «contra humanos» no hay ancla pública cuantificada: habría que crearla.
- **Qué hueco queda (INFERIDO):**
  - Nadie modela **cuándo está comprometido el rival y qué distribución tiene en sus puntos de decisión**, ni combina
    eso con el simulador exacto.
  - El diseño natural es híbrido: simulador o melee-brute para el ~15 % comprometido, donde 4Stockfish demuestra que
    la búsqueda exacta es útil, y un modelo del rival **calibrado** (NLL, ECE) para el resto.
  - Ese es el único hueco que un modelo del mundo aprendido puede ocupar sin competir con el simulador, y nadie lo
    ocupa hoy.
  - El PR #102 de melee-sim-light (checkpoint y rollback en el sitio) abarataría esa búsqueda.
- **Riesgos:**
  - El campo avanza deprisa en RL sobre simulador (HAL, MIMIC, slippi-ai y mrcal17 en el último mes).
  - Un MVP que solo aporte «RL sin dinámica» no se distinguirá.
  - El valor diferencial tiene que medirse a **igual retraso** y con la descomposición entre frames comprometidos y
    de decisión.

## Fuentes

**Repos (vía `gh api`, a 2026-11-21):**
- vladfi1/slippi-ai: ramas `rl`, `mamba` (`docs/experiments/mamba_rl.md`) y `netplay-dev`; `docs/plans/nash_policy_delay.md`; README §Recordings; releases.
- ericyuegu/hal: rama `o63-delay-posttrain`; `experiments/o63/treatment.md`; `experiments/o65/README.md`; `experiments/o65/exploiter-league-protocol.md`; `hal/eval/O65.md`; `hal/sim/NATIVE.md`; `deploy/netplay/status.md`.
- erickfm/MIMIC: `docs/findings.md` y, en la rama `coach`, `docs/research-notes-2026-11-17.md`.
- kyhavlov/melee-sim-light: PR #88–#102.
- mrcal17/melee-sim: README y `rl/README.md`.
- noahpodgurski/4Stockfish: README.
- blasphemetheus/exphil: README y `docs/planning/CURRENT_STATUS.md`.
- zurgace/aimelee, ScavieFae/nojohns y Josef-Hlink/fax: README.

**Hugging Face (API de modelos):**
- frisson-labs: Faynt-*, Reyn-26C, Reyn-Pair y Wombo-Combo.
- erickfm/MIMIC (`f49879b6`).
- ericyuegu/hal-base-250m-rc (`e7fb8378`).
- justincg/melee-wm-weights (`6eb57727`): `world_model_config.yaml` y `gate_*/eval.log`.
- Mathoo1/melee-rl-fox-mango.

**Papers y web:**
- Faynt, [arXiv 2610.02144v1](https://arxiv.org/html/2610.02144v1): leído hasta ~100k caracteres de la versión HTML.
- [COMBAT](https://arxiv.org/abs/2603.00825), [Fight World Model](https://arxiv.org/abs/2610.40607),
  [GenBR](https://arxiv.org/abs/2302.00797) y [Metamon/Pokémon](https://arxiv.org/abs/2504.04395): solo resúmenes.
- [Tesis LIACS](https://theses.liacs.nl/pdf/2025-2026-HamelinkJJosef.pdf) y [project nabla](https://bycn.github.io/2022/08/19/project-nabla.html):
  sin leer en detalle.
- El informe de Stanford CS224R devolvió 404.
