# DECISIÓN — modelo del mundo aprendido (JEPA / LeWorldModel) para Melee

Fecha: 2026-11-19. Rol: decisor. Base: `decision/brainstorm_{defensor,esceptico,pragmatico}.md`, `evidence/A8/*` (incl. `G01_shadow_sim_check.md`) y comprobaciones puntuales en `evidence/A4`–`A7`. No se ha ejecutado nada nuevo. Etiquetas: **SOP** soportado (código inspeccionado o medición con artefacto), **INF** inferido, **PEND** pendiente de experimento, **HIP** estimación mía sin medir (todos los costes lo son; USD ≈ EUR).

## 0. Decisión en cinco líneas

1. **No se construye ahora un MPC con dinámica aprendida.** Tampoco se descarta el modelo del mundo: hoy no hay ninguna medición en Melee que permita afirmar ni negar su valor.
2. **MVP elegido:** modelo predictivo conjunto *dinámica + rival* sobre estado estructurado (W0-S + q), con un gemelo latente tipo LeWorldModel (W1-L) como ablación. Su primer uso en decisión es **predecir el presente bajo demora**, no buscar.
3. Las dos primeras etapas (E0, E1) son comunes a las tres posturas, no necesitan ISO y cuestan ≤ 35 €. La elección de MVP solo empieza a pesar cuando se pide la ISO.
4. La búsqueda con el simulador exacto (S0-ceiling) queda como segunda línea, independiente y posterior, con el tamaño muestral corregido (≥ 400 partidas por brazo, no 40).
5. Primer paso: E0 en esta máquina (tubería `.slp`, suelos triviales, preregistro), pendiente de un permiso del usuario (§6.1).

## 1. Respuesta a la pregunta central con lo que hoy se sabe

**Respuesta:** no se sabe. Ningún rol ha medido fuerza de juego, y la evidencia previa en Melee es débil en ambos sentidos. Lo que sí se puede afirmar es qué usos tienen un test barato y limpio y cuáles no.

**SOPORTADO**
- El bench solo se juega en Dolphin (`fast`/`realtime`); nunca en `--mode sim`. Ningún modo impone plazo a un agente every-frame: "tiempo real" solo existe con un envoltorio propio (`RT-strict`).
- Todo agente recibe el mando actual del rival (`I_full`), pero `GameState` no trae C-stick crudo, gatillos físicos ni semilla. El agente no recibe el `World`. No existe `GameState → estado del simulador`.
- Nadie planifica con el simulador durante una partida; ningún bot publicado usa predicción de estado en inferencia.
- En esta CPU un MPC aprendido en 16 ms es de ~1M parámetros y ~1.000 evaluaciones (medido sin Dolphin corriendo y sin KV-cache). Un predictor del presente (K16×T8, MLP-1M) cuesta 2,8 ms p99.
- SIGReg domina el paso de entrenamiento de modelos de estado pequeños en CPU. No hay pesos JEPA reutilizables. Solo el `.slp` crudo sirve para dinámica (HAL MDS carece de velocidades, hitstun y contadores).
- Simulador sombra en Dolphin: el flujo Slippi crudo sí lleva semilla por frame (Frame Start ≥ 2.2.0), C-stick crudo (≥ 3.17.0) y gatillos físicos, y melee-llm ya lo engancha (`ConsoleTap`). La API pública de melee-brute no acepta semilla por frame ni eventos de escenario, y no hay arranque a mitad de partida. Veredicto de A8: **factible solo con cambios** en melee-brute (C + Python) y un decodificador en vivo.

**INFERIDO**
- A igual conteo de candidatos, q y V̂, S0 acota por arriba a cualquier W en `--mode sim`. Es lógica, no medición; no vale a igual tiempo ni para el bench.
- "En CPU el modelo aprendido no es más rápido que el simulador": las cifras cruzan máquinas (5950X cargado frente a este EPYC) y rutas (12–17 µs en C frente a ~0,35 ms por la ruta `World`+`StateBuilder`). Para 1M el cociente es ≈ 1; según la ruta, el MLP podría ser más rápido. Sin medir en la misma máquina no se usa como argumento.
- "El predictor ayuda bajo demora" (At Human Speed): confundido por días de entrenamiento (3 frente a 10), 6–8 partidas, un agente por celda, predictor que ignora al rival. "Basta entrenar con demora" (slippi-ai, `delay.md`) es opinión de autor. Nadie ha comparado a igual demora.
- BC → PPO con correa KL es lo único con mejoras documentadas, pero con cifras de autor, asimetría de demora y selección de checkpoints contaminada; el PPO propio falló dos veces.

**PENDIENTE**
- Si el nicho de la dinámica aprendida en Dolphin es estrecho o es todo el bench. Depende de la fracción de frames en sincronía de una sombra que no existe. La frase "nicho estrecho" del escéptico **no está demostrada**.
- Si planificar con dinámica exacta mejora a la política sola (S0 − P0). Nunca medido.
- Si q y V̂ pesan más que la dinámica (solo hay aritmética de descuento).
- Si el entrenamiento en imaginación fusionado en GPU compensa (contraejemplo X1, sin refutar).
- Si el latente JEPA aporta algo sobre predecir el estado explícito, y si cualquier preentrenamiento predictivo mejora la eficiencia de datos.

## 2. Arquitecturas viables y elección

Común a las tres: estado estructurado (no píxeles), Fox ditto en BF/FD, esquema de observación único de A6 (reparseo de `.slp`), régimen `I_full` primario e `I_human` secundario obligatorio, split por partida.

| Componente | **A. Predictor del presente (MVP)** | B. Búsqueda exacta S0 (+ destilación) | C. MPC con dinámica aprendida |
|---|---|---|---|
| Encoder | MLP/GRU de estado, ~1–2M, historia 16 frames | el del prior (Faynt-Expert o B0) | el de A |
| Dinámica | W0-S aprendida (cabezas por campo); W1-L latente como ablación | motor melee-brute (`checkpoint/rollback`), exacta | W0-S / W1-L |
| Rival | dentro del modelo: K=4 hipótesis muestreadas, nunca la media | q = copia del prior o BC del rival | q |
| Valor | no se usa en decisión (V̂ se entrena solo como diagnóstico) | V̂(x) imprescindible; controles S0-Vperm y S0-MC | V̂(x) imprescindible |
| Política | BC pequeño a 0 frames alimentado con el presente predicho | argmax/softmax sobre N candidatos; alumno destilado opcional | argmax sobre N candidatos |
| Búsqueda | ninguna: K×(D+1) pasos | N=16 × K=4 × T=16 | igual que B |
| Información | causal (`I_full` / `I_human`) | **PRIV**: estado exacto, RNG, mando actual del rival | causal |
| Reloj | cabe en `RT-strict` en CPU (medido el predictor, no la ruta completa) | `untimed` en sim; en vivo exige ruta en C | `untimed`; RT solo ≤1M |
| Cambios de integración | un `Agent` nuevo; nada en runner ni en melee-brute | pasar `World` y semilla en `sim/runner.py` | ninguno en Dolphin; igual que B para compararse con S0 |

**Por qué A.**
- Es la única donde el modelo aprendido actúa en la decisión **y** la primera puerta de muerte no necesita ISO (error de predecir el presente frente a suelos triviales).
- Su prueba en juego no depende de V̂ (que no existe), ni de pasar el `World`, ni de cambios en melee-brute.
- Tiene un control que la mata limpiamente: la misma política entrenada con la demora en los objetivos (receta slippi-ai), a igual cómputo total.
- Todo lo que construye (tubería, W0-S, q, V̂) es prerrequisito de B y C.

**Por qué no B ahora.** El argumento del escéptico ("S0 está en el camino crítico") es correcto para los usos de planificación y no para A: el S0-ceiling veta el MPC, no la predicción bajo demora ni la representación. B exige ISO, GPU, cambio en el runner y V̂; no contiene modelo aprendido de dinámica; y su resultado es una cota privilegiada en sim, no una afirmación sobre el bench. Su brazo estrella (destilación) tiene la misma evidencia en Melee que A: ninguna. Queda como etapa E4.

**Por qué no C ahora.** Sin S0 no se puede distinguir un W malo de un V̂ malo; el techo es desconocido; y solo cabe en tiempo real con modelos muy pequeños. Se reabre únicamente si E4 es positiva y el panel de regret da regret_W < regret_P0.

**Qué es "JEPA/LeWorldModel" en el MVP y qué no.**
- **Sí lo es, solo W1-L:** predicción del siguiente embedding condicionada a acciones, SIGReg (Epps–Pulley sobre proyecciones aleatorias), sin stop-grad ni EMA, pérdida `pred + λ·sigreg` (le-wm `train.py` L34-41).
- **Aun así se desvía de LeWM:** encoder de estado en vez de ViT; acciones de dos jugadores; hipótesis muestreadas del rival (LeWM es determinista); sin planificación por distancia a un embedding meta; decodificador de campos sobre `sg(ẑ)` solo para medir; si el núcleo pasa a GRU para tiempo real, W1−W0 mide "predictor + arquitectura" y deja de ser LeWM.
- **No lo son:** W0-S (regresión/clasificación de estado explícito), q (una política), V̂, el BC. I-JEPA y LeJEPA no temporales quedan fuera.
- Si W1-L ≤ W0-S y E1 ≤ E1-S, lo que sobrevive se llama "modelo predictivo aprendido", no JEPA.

## 3. Etapas y gates

Correcciones de potencia aplicadas (A8 `power.py`): sobre un checkpoint fijo hacen falta **393 partidas por brazo para 10 pp, 1.570 para 5 pp**; con 40 solo se detectan ~31 pp. Las propuestas de 40 (defensor), 120 (pragmático) y 200 (escéptico) partidas por brazo no sostienen sus gates. Con este presupuesto el efecto mínimo decidible es **10 pp**, no los 5 pp del protocolo: "mejora" = Δ̂ ≥ 10 pp con IC95 > 0; "sin efecto" = IC95 ⊂ (−10, +10); lo demás es inconcluso. Métrica primaria: margen de stocks (continua), tamaño fijado con la varianza del piloto. Para comparar recetas la unidad es la semilla: 5 semillas × 200 partidas detectan ~8–11 pp si σ_s es 3–5 pp (σ_s desconocida).

| Etapa | Recurso | Entregable | Coste (HIP) | Desbloquea | Mata la línea si… |
|---|---|---|---|---|---|
| **E0** Tubería, suelos, humo, preregistro | Local, sin ISO, sin GPU | Venv con `peppi_py`; ≥ 150 Fox dittos de `melee-ranked-replays`; esquema A6; split por sha1; suelos triviales por campo y h; test de fuga de alineación; humo ≤ 1M; envoltorio de plazo con agente sintético; plan congelado con hash | 15–25 h-persona; 3–8 h-CPU a ≤ 2 hilos; 0 € | Alquilar GPU | No mata. Si < 95 % de partidas traen velocidades/hitstun/`action_state_frame`, se redefine el esquema |
| **E1** Diagnóstico offline a escala | GPU alquilada, sin ISO | ~2.000 train / 300 val / ≥ 1.000 test. W0-S, W1-L, q, V̂; BC con E0/E0b/E1/E1-S al 10/30/100 % de datos; error por h ∈ {1,4,8,16,32} y de "predecir el presente" con D ∈ {6,12,18}; rival oracle / q / marginal; `I_full` e `I_human` por separado | 30–45 h-persona; 10–35 h-GPU; 10–25 €, parada dura a 35 € | Pedir la ISO; qué brazos siguen | Ver gates G1 |
| **E1b** Throughput fusionado en GPU (H12) | Misma instancia | Transiciones/s de política + dinámica 1–5M con CUDA graphs, sincronizado | 4–6 h-persona; 1–2 h-GPU; 1–2 € | Si W2 (imaginación) sigue vivo | < 10× la granja documentada (6.337 frames/s; otra máquina, así que solo vale un cociente grande) → W2 descartado |
| **E2** Mediciones baratas con ISO, sin tocar repos | ISO; CPU | `python -m melee_brute bench` y banco A7 en la misma máquina; test de aliasing (historia mínima); panel de regret con ≥ 2.000 raíces (W / P0 / S0, S0-Vperm, q copia frente a q BC); `validate_replay.py` frente a `parity.py` sobre ≥ 50 partidas del bench grabadas (cota de sincronía de una sombra) | 20–30 h-persona; < 15 h-núcleo; 0 € | Coste real de S0; si W es desplegable en MPC; si la sombra merece el cambio en C | regret_W ≥ regret_P0 → W no se usa para MPC (no afecta a E3) |
| **E3** MVP en juego: predictor del presente | ISO; `Agent` nuevo en melee-llm | Brazos: (a) observación envejecida, (b0) presente predicho por W0-S, (b1) por W1-L si pasó G1-jepa, (c) política entrenada con demora, (d) D=0 como techo. Piloto con D=12, ≥ 400 partidas por brazo en sim `untimed`; c con 5 semillas × 200; confirmación en Dolphin `RT-slow` y `RT-strict` | 40–60 h-persona; 30–60 h-núcleo por D; 0–15 € | Veredicto del MVP | b − a sin efecto (IC ⊂ ±10 pp) → el predictor no aporta; c − b ≥ 10 pp a igual cómputo → "basta entrenar con demora", se cierra la dinámica aprendida para control bajo demora |
| **E4** S0-ceiling | ISO; **cambio en melee-llm** (`sim/runner.py` L47-53: pasar `World` y fijar/registrar semilla) | S0 − P0-Q, S0-Vperm, S0-MC; ≥ 400 partidas por brazo; margen de stocks primario | 30–50 h-persona; ~200 h-núcleo (INF de A5 sobre cifras de otra CPU: se recalcula con E2); 0–15 € | Línea de búsqueda (C, destilación) | S0 − P0-Q sin efecto y S0-MC también → se cierra el MPC con cualquier dinámica en ese evaluador. Si S0-MC > P0 pero S0+V̂ no, el culpable es V̂ |
| **E5** Sombra en vivo | ISO; **cambios en melee-brute** (API C `step` con semilla por frame y eventos de escenario, binding Python) y decodificador en vivo sobre `ConsoleTap` | Fracción de frames en sincronía en partidas del bench | días de ingeniería; no presupuestado | Si el nicho Dolphin existe | ≥ 99 % en sincronía → el nicho Dolphin desaparece; queda `I_human` |
| **E6** MPC aprendido, recetas con PPO (≥ 5 semillas), imaginación | ISO + GPU días | — | no presupuestado | — | solo si E4 (y E1b para W2) lo justifican |

**Gates de E1** (umbrales recalibrados: antes de congelarlos se mide la varianza entre semillas con 3 corridas de E0; un efecto cuenta si supera 2× esa desviación y su IC95 por partida excluye 0; 5 semillas para cualquier resultado que cambie la decisión):
- **G1-dyn.** W0-S mejora ≥ 10 % relativo al mejor suelo trivial (persistencia, velocidad constante, mayoritaria condicionada, acciones barajadas) en error de eventos a h ∈ {4, 8}. Si no: no hay dinámica aprendida útil con este corpus; se paran W0/W1.
- **G1-q.** q mejora la NLL del mando del rival sobre la marginal, y el acierto de acción del rival en frames de cambio a h = D+1 supera al mejor suelo para D = 6 y 12. Si no: el predictor del presente no tiene nada que ofrecer; E3 no se ejecuta y la ISO solo se justifica por E4.
- **G1-jepa.** W1-L frente a W0-S y E1 frente a E1-S, en ≥ 2 de 3 tareas (BC, q, V̂). Si no gana: se cierra la etiqueta JEPA y sigue solo W0-S.
- **G1-rep.** E1 o E1-S frente a E0b (igual cómputo) al 10 % y al 100 % de datos. Si ninguno gana: el preentrenamiento predictivo no aporta a la representación offline en este corpus.
- Lectura obligada: pasar G1 es condición necesaria, no prueba de ventaja al jugar.

La "etapa 2" del pragmático (oráculo de futuro frente a Q̂) no se usa como gate: el oráculo incluye la recompensa realizada del propio objetivo, así que su ganancia G es positiva por construcción. Queda como diagnóstico exploratorio.

## 4. Reutilizar, construir, descartar

**Reutilizar**

| Qué | Revisión | Licencia | Para |
|---|---|---|---|
| melee-llm: runner, bench, `ConsoleTap` (`bots/agent.py` L25-56), `sim/slippi.py`, patrón `budget_ms` de bot-writer | `7e179081c6cbab139d860c998b1452ad3dee047c` | sin LICENSE | integración, envoltorio de plazo, decodificador |
| melee-brute: `Match.checkpoint/rollback`, `bench`, `tools/validation/validate_replay.py` | HEAD `9662ec973b9e077ff7b0ff89d6db950f53c11653`; el runtime fija `090e54b048b7d51e82f9f6b551046c2ca8b130c7` — fijar una sola | sin LICENSE | E2, E4, E5 |
| le-wm: `SIGReg`, `ARPredictor`, lógica de pérdida | `8edfeb336732b5f3ce7b8b210d0ba370a09e2cac` | MIT | W1-L |
| slippi-ai: receta de entrenamiento con demora, recompensa con semivida de 8 s | `5ada33e90c6c87fe83a1fb2d1a8105a96fd7b05b` | MIT | brazo c, V̂ (no su parser: sin velocidades ni hitstun) |
| MIMIC: bucle supervisado | `3691f534194f9c2ec52f131c8ab96e3d8674c3fa` | MIT | BC |
| Datos `erickfm/melee-ranked-replays`, carpeta FOX | `ef54ddc230e01373ff2a179b49a7e559af788081` | MIT declarada; derechos de origen desconocidos | corpus |
| Faynt-10M-Expert/Arena | Faynt-Benchmarks `39bc007537501c16d6e2dac6f2bcaafe3b84a8c9` | MIT, "offline use only" | rival y referencia externa, nunca en una afirmación de efecto |
| `evidence/A8/checks/power.py`, `evidence/A6/split_plan.json`, `timing_contract.json` | locales | — | preregistro |

**Construir:** parser `.slp` → esquema A6 con test de fuga; W0-S; W1-L; q; V̂; BC a 0 frames y BC con demora; `Agent` predictor del presente; envoltorio `RT-strict` con trazas; bootstrap por bloques (≈ 50 líneas, en vez de `rliable`, archivado). Más adelante: paso del `World` (E4) y API de semilla por frame (E5).

**Descartar explícitamente**
- Píxeles, encoders de vídeo y pesos JEPA publicados: ninguno sirve para estado (A3 §5).
- JEPA no temporal con vistas por aumento: espejo y fase borran información de control (A3).
- Librería `lejepa`, `ijepa`, `jepa-wms`: CC BY-NC; existen copias MIT de SIGReg.
- HAL MDS para dinámica: sin velocidades ni contadores, licencia `other`, connect codes de jugadores reales.
- Entrenar aquí más que humo: 37 h por 1k partidas × 10 épocas con MLP-1M (A7).
- MPC con dinámica aprendida antes de E4 y del panel de regret; W2 antes de E1b.
- PPO propio ahora: falló dos veces, exige ISO + GPU, y con 5 semillas solo se detectan ~10 pp.
- Sombra a partir de `GameState` (A4-027 es falsa tal como está escrita) y la conversión de `parity.py` que reconstruye el C-stick.
- CPU-9 como ancla de fuerza; cifras cruzadas publicadas como fuerza esperada (asimetría de demora).

## 5. Qué observación cambiaría la decisión

**Hacia más modelo del mundo**
- E3: b − a ≥ 10 pp y b no peor que c → el modelo aprendido aporta bajo demora; se amplía a más D y a Dolphin `RT-strict`.
- E2/E5: sombra < 95 % de frames en sincronía, o el cambio de API inviable → en Dolphin no hay simulador en vivo; W en MPC pasa a línea principal si además E4 es positiva.
- E2: regret_W cercano al de S0 y menor que el de P0.
- E2: S0 por su ruta real ≥ 10× más caro que W0-S en la misma máquina → se reabre la comparación a igual tiempo.
- E1b: ≥ 10× de throughput → W2 (imaginación) sube de prioridad.
- G1-jepa positivo → se mantiene el brazo latente y se justifica B2 (encoder JEPA + PPO) más adelante.

**Hacia menos**
- G1-dyn falla → se paran W0/W1; quedan q, V̂ y la línea de búsqueda exacta.
- G1-q falla → sin modelo de rival no hay predictor del presente ni MPC útil.
- E3: c gana por ≥ 10 pp → se cierra la dinámica aprendida para demora.
- E4: S0 − P0-Q sin efecto con S0-MC igual → se cierra todo MPC; el esfuerzo va a RL convencional y demora.
- E5: sombra ≥ 99 % → la dinámica aprendida en Dolphin solo conserva el carril `I_human`.

## 6. Decisiones que solo puede tomar el usuario

| # | Decisión | Por defecto si no responde |
|---|---|---|
| 1 | Permiso para un venv de usuario con `peppi_py`/`zstandard` y ≤ 1 GB de replays en el segundo disco de este servidor (≤ 2 hilos, prioridad baja) | Se planifica con "sí", pero no se instala nada sin confirmación; si es "no", E0 se hace en la instancia alquilada (+2–4 €) |
| 2 | Techo de gasto en GPU | 35 € para E1 + E1b, parada dura |
| 3 | Aportar una ISO NTSC 1.02 propia y dónde puede residir (este servidor, su PC, instancia alquilada) | No se pide hasta pasar G1; entonces solo en máquina propia, sin subirla a terceros |
| 4 | ¿Importa el régimen con demora (reacción tipo humano, 6–18 frames) o solo el bench a 0 frames? | Sí importa, como eje secundario. Si es "no", E3 pierde sentido y tras G1 el siguiente paso es E4 |
| 5 | Objetivo: responder la pregunta o publicar un entrante en el bench | Responder la pregunta |
| 6 | Aprobar cambios en melee-llm (pasar `World` y semilla) y en melee-brute (API de semilla por frame) | melee-llm sí al llegar a E4; melee-brute no hasta que E2 lo justifique |
| 7 | Datos: solo `melee-ranked-replays`, sin HAL MDS | Sí |

## 7. Desacuerdos no resueltos con la evidencia disponible

1. **Nicho en Dolphin: estrecho (escéptico) o todo el bench (defensor).** La viabilidad de la sombra ya está aclarada (factible con cambios); la fracción de frames en sincronía es desconocida. Los umbrales tampoco coinciden (50 % frente a 95 %); se adopta el de A8 (< 95 % nicho real, ≥ 99 % desaparece).
2. **Predictor del presente frente a política entrenada con demora.** Defensor: prior bajo-medio; A5: "improbable". No existe ninguna comparación a igual demora. Lo decide E3.
3. **¿Vale algo la búsqueda con dinámica exacta?** Nunca medido; la destilación del escéptico tampoco tiene evidencia en Melee. Lo decide E4.
4. **¿Pesan más q y V̂ que la dinámica?** Solo aritmética de descuento; el ranking entre candidatos puede depender de golpes dentro del horizonte. Panel de E2 y E4.
5. **Velocidad relativa modelo aprendido / simulador.** Sin medición en la misma máquina ni por la misma ruta. E2.
6. **Imaginación fusionada en GPU.** A4 la descarta por inferencia en CPU; A8 la mantiene abierta. E1b.
7. **¿Bastan 1–2k partidas para ver un efecto de preentrenamiento?** Desconocido; un G1-rep negativo con este corpus no cierra la pregunta a 10k+.
