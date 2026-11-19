# CRITICAL_REVIEW — refutación, confusores, discrepancias y límites

Integrador · 2026-11-19 · Consolida `evidence/A8/CRITICAL_REVIEW.md` (auditoría y contraejemplos),
`evidence/A8/G01_shadow_sim_check.md`, `evidence/A8/evidence_gaps.json`, los tres `decision/brainstorm_*.md` y
`decision/DECISION.md` §5 y §7. Incluye una pasada propia del integrador contra DECISION (§7).

**Etiquetas.**
- **SOP** soportado, **INF** inferido, **PEND** pendiente, **PROP** propuesta.
- **DOC-autor**: cifra de autores, atribuida y no reproducida.

---

## 1. Qué se intentó refutar

La conclusión emergente de A4/A5 era: *"una dinámica aprendida no aporta frente al simulador exacto en sim; su único
nicho es Dolphin tras la divergencia de RNG y el modelo del rival; V̂ y q importan más que la dinámica"*. A8 la
descompuso en tres partes:

| Parte | Afirmación | Veredicto tras la revisión |
|---|---|---|
| **C1** | En `--mode sim`, a igual conteo, una dinámica aprendida no supera al simulador exacto | **INF sólida**, casi tautológica: mismos candidatos, q y V̂ con dinámica exacta. Tiene dos debilidades. (1) El bench es solo Dolphin, así que no habla del objetivo. (2) "No aporta" nunca se planteó como equivalencia: el S0-ceiling de 40 partidas (A5 §6.3) solo detecta ~31 pp [A8-014] |
| **C2** | Su único nicho es Dolphin tras la divergencia de RNG | **El eslabón más débil; PEND.** Descansaba en una sombra que no existe y en A4-027, que es FALSA tal como está escrita (§2), y usaba como cobertura una cifra de bots (15/40, fila 24). Tras G01: la sombra es *factible solo con cambios*, y la fracción de frames en sincronía es desconocida. Si la sombra no se construye o se desincroniza, el nicho **es todo el bench**. Además, "y el modelo del rival" no es un nicho de la **dinámica**: q es una política |
| **C3** | V̂ y q importan más que la dinámica | **INF / PEND.** Solo se apoya en la aritmética de descuento (γ^32 = 0,955 con semivida de 8 s, A5-030). Que V̂ domine la *magnitud* de J no implica que domine el *ranking* entre candidatos. Se mide en el panel de E2 y en E4 (HR-2, HC-2, HC-3) |

**Refutación de DECISION por los brainstorms.**
- **Escéptico**: S0 está en el camino crítico. DECISION lo acepta para los usos de planificación, pero no para A:
  S0 veta el MPC, no la predicción bajo demora.
- **Defensor**: 40 partidas por brazo bastan. Es falso por potencia: 393 partidas por brazo para 10 pp.
- **Pragmático**: el oráculo de futuro frente a Q̂ como gate. Se rechaza, porque su ganancia es positiva por
  construcción (incluye la recompensa realizada) y queda como diagnóstico.

## 2. Resultado de la auditoría de trazabilidad de A8 (30 afirmaciones)

**Resumen declarado por A8: 20 CONFIRMADAS (6 con matiz), 9 IMPRECISAS, 1 FALSA.**

**Aviso del integrador.** Los veredictos fila a fila de la tabla de A8 suman **24 confirmadas** (6 con matiz, si se
cuenta la 21), **5 imprecisas** y **1 falsa**. Si la fila 21 se cuenta como imprecisa, suman 23/6/1. **El 20/9/1
declarado no cuadra con su propia tabla.** La discrepancia no cambia ninguna conclusión: la falsa (25) y las dos
imprecisas con consecuencias (24 y 9) son las mismas en ambos recuentos. Abajo va la lista literal.

| # | Claim | Veredicto A8 | Qué se corrige |
|---|---|---|---|
| 1 | A1-013 / A4-017 mando del rival en `GameState` | CONFIRMADA con matiz | sin C-stick crudo ni gatillos físicos; gatillo lógico copiado a L y R [A8-003] |
| 2 | A1-002 / A7-001 Dolphin bloquea en `realtime` | CONFIRMADA | `runner.py` L208, L214 |
| 3 | A1-014 el bench nunca usa sim | CONFIRMADA con matiz | el pool importa partidas `lockstep` (`bench/imports.py` L85-97) |
| 4 | A1-003 "never waits" contradice el código | **IMPRECISA** | `docs/bench.md` L27 ya lo matiza |
| 5 | A1-016 localizadores de `bench/game.py` | **IMPRECISA** (localizador falso) | el fichero tiene 113 líneas: `MIN_FPS` L14, `make_agent` L17-28, `play_one` L83-104, `status_of` L107-113 |
| 6 | A1-001 `runner.play(mode="sim")` no reenvía `seed` | CONFIRMADA | L200-202 |
| 7 | A1-007 el agente no recibe el `World` | CONFIRMADA | `sim/runner.py` L47-51 |
| 8 | A1-018 / A4-026 12–17 µs/frame del simulador | CONFIRMADA | 5950X con carga 15–35; tablas anteriores al perfil de build actual; la ruta `World` + `StateBuilder` cuesta ≈ 0,35 ms/frame [A8-008] |
| 9 | A4/A5/A7 "aprendido no más rápido que el simulador en CPU" | **IMPRECISA** en el cociente | ≈ 1× para 1M; 50–300× solo para un ARPredictor de tamaño LeWM sin caché; las máquinas y rutas no son comparables |
| 10 | A5-001 nadie planifica con el simulador al jugar | CONFIRMADA | `docs/tas.md` L97 |
| 11 | A5-010 el ciclo de §12 era un artefacto | CONFIRMADA | `optimal-play.md` L358-359; `nash.py` L4 |
| 12 | A5-011 valor 0 → 0,382 | CONFIRMADA con matiz | sin escudo, horizontes 8/12; con escudo vuelve a 0 |
| 13 | A3-SIG-001 SIGReg = Epps–Pulley | CONFIRMADA | `le-wm/module.py` L10-36 |
| 14 | A3-LWM-001 / A4-004 sin stop-grad, λ = 0,09 | CONFIRMADA | `train.py` L34-41; `lewm.yaml` |
| 15 | A4-010 planificación por distancia a la meta | CONFIRMADA | `jepa.py` L112-126 |
| 16 | A3-LWM-003 split por ventanas | CONFIRMADA con matiz | las ventanas vienen de `stable_worldmodel` |
| 17 | A2-014 slippi-ai excluye el mando del rival | CONFIRMADA | `jax/embed.py` L461-463 |
| 18 | A3-MEL-001 slippi-ai omite action_frame, hitlag y hitstun | CONFIRMADA | `tf/embed.py` L443-447 |
| 19 | A2-001 HAL = AWR + V(s), no BC puro | CONFIRMADA | `059_muon_action_sequence.py` L1-6 |
| 20 | A4-007 / A2-018 el predictor de Phillip solo usa la acción propia | CONFIRMADA | `phillip/model.py` L84-98 |
| 21 | A2-019 / A6-026 At Human Speed | CONFIRMADA en cifras, **IMPRECISA por omisión** | "Days Trained" 3 frente a 10 frente a 7; 6–8 partidas por agente; un agente por celda [A8-004] |
| 22 | A4-003 `post(f)` no es Markov | CONFIRMADA | `BRUTE.md` L74-80 |
| 23 | A6-029 cita de VALIDATION.md | **IMPRECISA** | está bajo "Recorded CPU inputs"; la conclusión se sostiene por `BRUTE.md` |
| 24 | A4-021 15/40 partidas sin divergencia | **IMPRECISA en su uso** | son replays de bots del autor (`simulator.md` L53); el 36/40 humano es **con** RNG grabado |
| 25 | A4-027 sombra desde `GameState` | **FALSA tal como está escrita** | ver §3 |
| 26 | A2-025 Faynt: los rivales informaron la selección | CONFIRMADA | `Faynt-Benchmarks/README.md` L48-55 [A8-006] |
| 27 | A2-005 HAL 91–5 / 24–72 con demora asimétrica | CONFIRMADA + matiz | el RNG de Melee no se siembra en el h2h [A8-007] |
| 28 | A5-022 / A2-029 Faynt-10M en CPU | CONFIRMADA | 8,1/10,3/11,5 ms; ~16 ms en CUDA en esa máquina |
| 29 | A7-003 ~3,3 ms/frame de Dolphin + parseo + runner | CONFIRMADA | `docs/performance.md` L52 |
| 30 | Artefactos REPRODUCIDO | CONFIRMADA | 25 artefactos con SHA-256 coincidente. Defectos menores: los scripts de A7 están fuera de `evidence/A7/`, picos de RSS de 1,62 GB por encima del tope, y A5-020 re-etiqueta como REPRODUCIDO una medición de A7 |

## 3. Discrepancias entre roles y cómo se resolvieron (por fuente, no por votación)

| K | Roles | Discrepancia | Resolución |
|---|---|---|---|
| K1 | A3 frente a A7 | SIGReg "despreciable" frente a "83 % del paso" | Las mediciones coinciden (69 frente a 72 ms). El coste es T·N·M·17 operaciones trigonométricas, independiente del encoder. **Gana A7** para estado en CPU; en GPU no se ha medido |
| K2 | A4 frente a A5/A7 | transformer frente a GRU en RT | La medición de A7 es **sin KV-cache**. El transformer queda en `untimed`; se mide con caché (G-08) antes de cambiar; GRU cuenta como cambio de arquitectura |
| K3 | A2 frente a A5/A7 | Faynt-10M como prior | No cabe en `RT-strict` en CPU (8,1/11,5 ms con 8 hilos); solo en `untimed` o con GPU dedicada |
| K4 | A1/A2/A4/A5/A6 | régimen de información | Congelado: `I_full` primario, `I_human` secundario obligatorio, S0 solo en `I_full` + PRIV |
| K5 | A2 frente a A4/A6 | `Game` de slippi-ai frente al esquema A6 | **Esquema único A6** para todos los brazos propios |
| K6 | A4 frente a A5 | "W frente a S0 es decisivo" frente a "S0 es cota" | S0 es cota a igual conteo; la tabla a igual tiempo se reporta aparte |
| K7 | A4 frente a A7 | 50–300× frente a ~1× | Ambos son correctos en su alcance (10,8M frente a 1M); ninguno se midió en la misma máquina que el simulador |
| K8/K9/K10 | A1 / A6 / A4-A5 | `bench.md`, cita de VALIDATION, uso de 15/40 | Filas 4, 23 y 24 |
| K11 | A2/A6 frente a A4/A6 | HAL MDS frente a `.slp` crudo | HAL MDS solo sirve de prototipo; el resultado exige reparsear `.slp` de `melee-ranked-replays` |
| A4-027 | A4 frente a A8 | "el `GameState` trae los mandos de ambos" | **FALSA** (G01). El `GameState` descarta el C-stick crudo, los gatillos físicos y la semilla (`console.py` `__pre_frame`; `FRAME_START: pass`). El flujo crudo sí los trae (SPEC `3a85ce8b`: Frame Start 0x5 ≥ 2.2.0, Pre-Frame 0x41/0x42 ≥ 3.17.0, 0x33/0x37) y es accesible por `ConsoleTap` (`LLM:bots/agent.py` L25-56). La API pública de melee-brute no acepta semilla por frame ni eventos de escenario (`batch.c` L324-326; `api.h` L247-447), y no hay arranque a mitad de partida. Veredicto: **factible solo con cambios** (E5) |
| Brainstorms | defensor / escéptico / pragmático | MVP | DECISION §2 elige A; B pasa a E4 y C a E6 |
| Umbrales de sombra | escéptico (50 %) frente a A8 (95 %) | nicho real | se adopta el de A8: < 95 % hay nicho, ≥ 99 % desaparece |

## 4. Confusores y fugas que cualquier conclusión debe controlar

1. **Selección de checkpoints de Faynt con rivales slippi-ai.** El panel a 0 frames enfrenta 68 partidas a un único
   checkpoint privado.
2. **Fuga por set en ranked anónimo** y origen común de MRR y HAL ranked.
3. **Splits por defecto con fuga**: `swap=True` de slippi-ai, ventanas de LeWM y duplicados entre carpetas de HAL
   pro y de MRR.
4. **Demora asimétrica** en todas las cifras cruzadas publicadas: HAL 2 frente a 21, Faynt 0 frente a 21–24, MIMIC 0
   frente a 18.
5. **Pseudorreplicación**: 26 % de falsos positivos con σ_s = 5 pp [A8-010].
6. **Tiempo de entrenamiento** en Firoiu: 3 frente a 10 días.
7. **RNG no controlable** en Dolphin y semilla no reenviada en sim: los "pares" no son números aleatorios comunes
   del juego.
8. **Motores distintos**: el pin `090e54b0` (sin `hitlag_left`, ABI de 1208 B), la HEAD `9662ec97` y el checkout
   `MELEE_SIM` de la granja, sin revisión registrada. Además, libmelee 0.47.6 instalado frente a 0.47.3 clonado.
9. **Canales privilegiados latentes**: el `controller_state` del rival (`I_full`), el `random_seed` en el flujo
   Slippi que reciben los bots y V̂ con estado presente en entrenamiento.
10. **Reloj**: sin `RT-strict`, todo "tiempo real" es `RT-slow`.
11. **CPU-9 explotable**: no sirve de ancla.
12. **El pool del bench mezcla relojes** (`lockstep` importado).
13. **Hardware cruzado**: el simulador y Dolphin se midieron en 5950X/9950X3D/3090, y torch en este EPYC con load
    2,6–7,7.
14. **(Integrador, específico de A) Desplazamiento de distribución de π0.** π0 se entrena con estados reales y en
    (b) recibe estados predichos, mientras que (c) se entrena en su propia distribución. Un "c gana" puede deberse a
    ese desajuste y no a que la predicción sea inútil. Es diagnóstico exploratorio, no un brazo de DECISION: π0
    ajustado con estados predichos de val, o medir el error de π0 en estados predichos frente a reales en E1.
15. **(Integrador) En A el aporte puede ser de q, no de `p_dyn`.** Con la cola propia conocida, lo único desconocido
    es el mando del rival. Un E3 positivo no prueba que haga falta una dinámica *aprendida*: un presente vía
    simulador + q (en sim) sería la cota.

## 5. Contraejemplos a favor del world model

| X | Contraejemplo | Estado |
|---|---|---|
| **X1** | **Imaginación masivamente paralela en GPU.** Política y modelo fusionados en GPU, sin viaje CPU↔GPU por frame | **El más fuerte y sin refutar.** El swarm lo descartó comparando coste por frame en CPU. En la ruta actual el cuello es la política (8,6 ms frente a 0,66 ms del simulador más la conversión, `docs/simulator.md`; granja Faynt 6.337 frames/s, DOC-autor). En contra: la interacción real es barata aquí, el modelo introduce sesgo explotable (Firoiu §5.1) y Dreamer/MuZero brillan con muestras escasas. **PEND → E1b** (1–2 €) |
| X2 | Planificación por gradiente | prior bajo (discontinuidad golpe/fallo); sin evidencia |
| X3 | Personajes o escenarios no soportados por el simulador | refutado en el alcance del bench (Fox ditto BF/FD) |
| X4 | Robustez a la demora vía predicción (At Human Speed) | la evidencia a favor y en contra es débil e indirecta; es la pregunta de **E3** |
| X5 | Representación para eficiencia de datos | PEND (G1-rep); no es dinámica en decisión |
| X6 | Planificar en el carril causal (`I_human`) | el competidor es P0/B1, no S0; PEND (HL-2) |
| X7 | Abstracción temporal (bloques o eventos) | PEND; solo importa si V̂ no basta |
| X8 | Plataformas sin simulador | nicho de despliegue real, irrelevante para la fuerza de juego |

## 6. Los 7 desacuerdos no resueltos (DECISION §7)

1. **Nicho en Dolphin: estrecho o todo el bench.** La viabilidad de la sombra está aclarada (factible con cambios);
   la fracción de frames en sincronía es desconocida. Lo deciden E2 (cota) y E5.
2. **Predictor del presente frente a política entrenada con demora.** No existe ninguna comparación a igual demora.
   Lo decide E3 (HP-1, HP-2).
3. **¿Vale algo la búsqueda con dinámica exacta?** Nunca medido; la destilación tampoco tiene evidencia en Melee. Lo
   decide E4.
4. **¿Pesan más q y V̂ que la dinámica?** Solo hay aritmética de descuento. Lo deciden el panel de E2 y E4.
5. **Velocidad relativa del modelo aprendido y del simulador.** Sin medición en la misma máquina ni por la misma
   ruta. Lo decide E2.
6. **Imaginación fusionada en GPU.** A4 la descarta por inferencia en CPU; A8 la mantiene abierta. Lo decide E1b.
7. **¿Bastan 1–2k partidas para ver un efecto de preentrenamiento?** Desconocido. Un G1-rep negativo no cierra la
   pregunta a 10k+ partidas.

## 7. Pasada del integrador contra DECISION.md (errores e imprecisiones)

No cambian la decisión, pero se corrigen en los entregables.

| # | Texto de DECISION | Problema | Corrección |
|---|---|---|---|
| D-1 | §1 SOPORTADO: "ningún bot publicado usa predicción de estado en inferencia" | **Error factual.** A2-034 dice "ninguno de los pesos **modernos** publicados auditados (HAL 250M, MIMIC, Phillip II ONNX, Faynt, Reyn)…; el único caso es el **Phillip histórico** con predictor de estado, cuyos pesos no están en el repositorio". Además A2-034 está etiquetada INFERENCIA, y A8 la clasifica INFERIDA (conclusión 9). La propia DECISION cita ese predictor en §1 INF | "Ningún peso moderno publicado auditado usa predicción de estado en inferencia; el Phillip histórico (Firoiu 2018) sí lo hacía, y sus pesos no están publicados." **INFERIDO**, no SOPORTADO |
| D-2 | §0/§1: "Un predictor del presente (K16×T8, MLP-1M) cuesta 2,8 ms p99" | **Imprecisión.** La cifra es la decisión MPC *proxy* de A7: encode H = 32 + 16 candidatos × 8 pasos, pesos aleatorios, sin Dolphin. A con D = 12–18 son K(4) × 13–19 pasos, más q (posiblemente en lazo cerrado) y π0 | INF-int: ≈ 3–6 ms (D = 12, rival humano) y hasta ≈ 17 ms (D = 18, q en lazo cerrado). "Cabe en RT-strict" es INF para D ≤ 12 y PEND para D = 18 (DESIGN §3.9) |
| D-3 | §3 E1: "~2.000 train / 300 val / ≥ 1.000 test" con "split por sha1" de A6 | **Incoherencia** con `split_plan.json` (90/5/5): 1.000 partidas de test exigirían ~20.000 | Umbrales de bucket específicos y versionados para E1 (EXPERIMENT_PLAN §5.3) |
| D-4 | §3 E4: "~200 h-núcleo" | **Subestimación probable.** Esa cifra de A8/A5 cubre S0 + P0-Q + B a T = 16; S0-MC (T = 120–240) cuesta ~8–15× por decisión | EST: +500–1.000 h-núcleo para S0-MC a 400 partidas; se recalcula con el coste medido en E2 |
| D-5 | §3 "sin efecto = IC95 ⊂ (−10, +10)" con ≥ 400 por brazo | **Potencia de equivalencia baja**, no mencionada | INF-int: P(declarar "sin efecto" \| Δ = 0) ≈ 61 % con 400; ≈ 525 por brazo para el 80 % |
| D-6 | §1 SOPORTADO: "Todo agente recibe el mando actual del rival" | Matiz omitido | salvo bot-writer (`botwriter/agent.py` L6) |
| D-7 | §3 E3: "c con 5 semillas × 200" | **Asimetría de inferencia.** c − b compara recetas (EST-R), pero b usa un único π0/W0-S/q | O se declara que HP-2 generaliza solo al checkpoint de b, o b también se entrena con ≥ 5 juegos de semillas. Queda como decisión abierta del ejecutor, para preregistrar en E0 |

Fuera de DECISION, la cuenta 20/9/1 de A8 no cuadra con su tabla (§2).

## 8. Qué evidencia cambiaría la recomendación

**Hacia más modelo del mundo.**
- E3: b − a ≥ 10 pp y b no peor que c → se amplía a más D y a Dolphin `RT-strict`.
- E2/E5: sombra < 95 % de frames en sincronía, o cambio de API inviable → W en MPC pasa a línea principal si E4 es
  positiva.
- E2: regret_W cercano a regret_S0 y menor que regret_P0.
- E2: S0 por su ruta real ≥ 10× más caro que W0-S en la misma máquina → se reabre la comparación a igual tiempo.
- E1b: ≥ 10× de throughput → W2 (imaginación) sube de prioridad.
- G1-jepa positivo → se mantiene el brazo latente y se justifica B2 (encoder JEPA + PPO).

**Hacia menos modelo del mundo.**
- G1-dyn falla → se paran W0/W1; quedan q, V̂ y la búsqueda exacta.
- G1-q falla → no hay predictor del presente ni MPC útil.
- E3: c gana por ≥ 10 pp → se cierra la dinámica aprendida para demora.
- E4: S0 − P0-Q sin efecto y S0-MC igual → se cierra todo MPC; el esfuerzo va a RL convencional y a la demora.
- E5: sombra ≥ 99 % → la dinámica aprendida en Dolphin solo conserva el carril `I_human`.

## 9. Límites de esta investigación

- **No se ejecutó nada en el juego.** No hubo ninguna partida, ni Dolphin, ni el simulador melee-brute, ni PPO, ni
  BC con datos reales. Toda afirmación de fuerza de juego es PEND.
- **Sin ISO ni GPU.**
  - No hay ISO NTSC 1.02, así que no se pudo compilar ni medir el simulador.
  - No hay GPU, así que las cifras de GPU son EST (A7 §4.1) y el contraejemplo X1 sigue abierto.
  - Sin `peppi_py` no se leyó ni un `.slp`: la cobertura de campos por versión del corpus es desconocida.
- **Mediciones de CPU en un servidor compartido.**
  - Todas las latencias son de torch en un EPYC-Genoa de 4 vCPU con load 2,6–7,7, modelos proxy con pesos aleatorios
    y sin Dolphin corriendo. Las colas p99 con 3 hilos están infladas por contención, y 4 hilos no se midieron.
  - A7 superó transitoriamente el tope de 1 GB de RSS (pico de 1,62 GB).
- **Cifras de autores no reproducidas.**
  - Simulador: 12–17 µs/frame y 124.142 frames/s/núcleo.
  - Dolphin: 3,3 ms/frame.
  - Faynt: 8,1/11,5 ms, 6.337 frames/s y 240/244 victorias.
  - HAL: 91–5 / 24–72.
  - At Human Speed: Tabla 1.
  - LeWM: ~15M parámetros y 48× más rápido que DINO-WM.
  - E31: 36/40 partidas.

  Todas quedan atribuidas y **no** son rendimiento esperado en Melee con este diseño.
- **Corpus sin verificar.** El número de partidas de `melee-ranked-replays@ef54ddc2` (~850k) y el de Fox dittos no se
  han contado, y los derechos del origen son DESC.
- **Licencias.** melee-llm, melee-brute, melee-sim-light y HAL no tienen LICENSE: solo uso local, sin redistribuir.
- **Las cifras de potencia son sintéticas** (p = 0,5, sin ganancia por emparejamiento) y σ_s es desconocida.
- **Revisión de fuentes.** Varias referencias de HF no tienen SHA fijado (Faynt-10M-Expert, lewm-pusht, LeVJEPA); véase
  `deliverables/SOURCE_AUDIT.md` §5.
