# EXPERIMENT_PLAN — plan congelable

Integrador · 2026-11-19 · Estado: **PROPUESTA. No se ha ejecutado nada.** No hay ninguna partida, entrenamiento ni
benchmark del juego detrás de ninguna cifra de este documento. La única aritmética es la potencia sintética de
`evidence/A8/checks/power.py` → `power_result.json` (modelo binomial-normal, p = 0,5) y dos cuentas del integrador,
marcadas **INF-int**.

Fuente de verdad: `decision/DECISION.md` §3. Este plan la operativiza. Base: `evidence/A8/EXPERIMENT_PLAN.md`
(hipótesis H1–H12 y puertas G0–G9, renumeradas aquí a E0–E6, §10), `evidence/A6/split_plan.json` y
`timing_contract.json`, y `evidence/A3/ablations.json`. Arquitecturas: `deliverables/DESIGN.md`.

**Etiquetas.**
- **SOP** soportado, **INF** inferido, **PEND** pendiente, **PROP** propuesta.
- **EST**: coste o estimación sin medir; los costes de DECISION son HIP, USD ≈ EUR.
- *[piloto]*: constante que se fija con datos de validación o de piloto y se recongela **antes** de abrir el test.

**Regla de congelación.**
1. Este fichero, junto con `preregistration.json`, `eval_schedule.csv` y el hash del split, se sella con sha256 al
   cerrar E0.
2. Las constantes *[piloto]* se recongelan al cerrar E1 (offline) y antes de E3 (juego).
3. Ningún umbral se mueve tras ver el test.
4. Una corrida exploratoria que toque el test obliga a sellar un test nuevo.

---

## 1. Estimandos y unidad de inferencia

| Id | Estimando | Unidad | Generaliza a |
|---|---|---|---|
| EST-D | Calidad predictiva offline (W0-S, W1-L, q, V̂, probes) frente a suelos triviales | **partida** (bootstrap por partida) | ese corpus y split |
| EST-P | Efecto de una pieza de despliegue sobre un checkpoint fijo: b−a en E3, S0−P0-Q en E4 | **partida** dentro de bloques emparejados `pair_id` | **ese** checkpoint, q y V̂. Para hablar de la receta hacen falta ≥ 3 checkpoints independientes |
| EST-R | Efecto de una **receta** de entrenamiento: c frente a b en E3, PPO y E1/E2 frente a E0b en E6 | **semilla de entrenamiento** (≥ 5 por brazo); las partidas solo reducen el ruido dentro de cada semilla | recetas |
| EST-T | Viabilidad temporal (p99, plazos perdidos) | condición de carga × réplica | hardware medido |

N partidas de un checkpoint no son N réplicas de entrenamiento. En la simulación de `power.py`, con σ_s = 5 pp entre
semillas, agrupar partidas como si fueran independientes da un **26 %** de falsos positivos (1 × 200) o un **25,5 %**
(5 × 200), frente al 4,6 % del test a nivel de semilla [A8-010].

## 2. Regímenes (se reportan por separado; nunca se agregan)

**Información.**
- **`I_full`** (primario): el `GameState` completo, incluido el `controller_state` del rival ya aplicado. Es lo que
  el bench entrega a todo agente salvo a bot-writer (`libmelee/melee/console.py` L1145-1212; `LLM:sim/state.py`
  L93-95).
- **`I_human`** (secundario, **obligatorio** en todo brazo causal): lo mismo sin `controller_state` del rival.
- **`PRIV`** (S0, S0-shadow): snapshot, RNG y semilla. Siempre como cota.
- **`ORACLE`** (mandos futuros reales del rival): solo diagnóstico offline, prohibido en juego.

Toda afirmación lleva el régimen en el titular. Ningún contraste mezcla regímenes, y S0 en `I_human` no se reporta
porque no es ejecutable.

**Reloj.**
- **`RT-strict`**: plazo `C_rt` impuesto por un envoltorio propio con fallback L1 (mejor evaluado) → L2 (top-1 del
  prior u observación envejecida) → L3 (repetir mando), y conteo de plazos perdidos. Es lo único que puede llamarse
  "tiempo real". Criterio: p99 ≤ `C_rt` y ≤ 1 % de plazos perdidos (A7 §2.1).
- **`RT-slow`**: Dolphin `realtime`/`fast` sin plazo propio, con la latencia medida. No se reclasifica.
- **`untimed`**: `fast` o `--mode sim` declarados como pausa; mide calidad de decisión.

`C_rt` por defecto es 10 ms p99 en Dolphin y 16 ms en sim/fast con plazo (A7 `budget.json` `agent_budget_ms`);
*[piloto]* tras medir el bucle real en E3.

**Plataforma.** Es ortogonal al reloj: Dolphin (lo que usa el bench) frente a `--mode sim` (fuera del bench). Nada
obtenido en sim se presenta como conclusión sobre el bench.

## 3. Hipótesis falsables numeradas

Δ = diferencia en la métrica primaria (§6). **Efecto mínimo decidible = 10 pp** (DECISION §3; el MCID de 5 pp del
protocolo 06 no tiene potencia con este presupuesto). Reglas:
- "**Mejora**": Δ̂ ≥ 10 pp **y** IC95 > 0.
- "**Sin efecto**": IC95 ⊂ (−10, +10).
- Cualquier otro resultado es "**inconcluso**". La no significación nunca se lee como "no aporta".

| Id | Etapa | Hipótesis (forma que se intenta refutar) | Contraste | Estimando · régimen · reloj | Refutada o decidida si | A8 |
|---|---|---|---|---|---|---|
| **HD-1** | E1 | W0-S predice eventos mejor que cualquier suelo trivial | error de eventos a h ∈ {4, 8} frente al mejor de persistencia, velocidad constante, mayoritaria condicionada y acciones barajadas | EST-D · I_full e I_human por separado | mejora < 10 % relativo → **G1-dyn** falla | parte de G2 |
| **HD-2** | E1 | q predice al rival mejor que la marginal | NLL del mando del rival frente a la marginal; acierto de acción del rival en frames de cambio a h = D+1 frente al mejor suelo, D ∈ {6, 12} | EST-D | no supera en ambas → **G1-q** falla | parte de G2 |
| **HD-3** | E1 | El latente LeWM-like aporta sobre el estructurado | W1-L frente a W0-S y E1 frente a E1-S en ≥ 2 de 3 tareas (BC, q, V̂) | EST-D | no gana → **G1-jepa** falla; se cierra la etiqueta JEPA | H3 (offline) |
| **HD-4** | E1 | El preentrenamiento predictivo mejora la representación | E1 o E1-S frente a E0b (igual cómputo) al 10 % y al 100 % de datos | EST-D (BC/probes) | ninguno gana → **G1-rep** falla | H4 (offline) |
| **HT-1** | E1b | Un pipeline fusionado en GPU (política + dinámica 1–5M) da ≥ 10× la granja documentada | transiciones/s sincronizadas frente a 6.337 frames/s (Faynt, 8 procesos, RTX 3090; DOC-autor, otra máquina) | EST-T | < 10× → W2 (imaginación) descartado | H12 / G1 |
| **HR-1** | E2 | La dinámica aprendida sirve para decidir, no solo para predecir | regret_W < regret_P0 frente a S0, con ≥ 2.000 raíces (bootstrap por raíz agrupado por partida) | EST-D · sim offline | regret_W ≥ regret_P0 → W no se usa para MPC (no afecta a E3) | H7 / G3 |
| **HR-2** | E2 | q y V̂ pesan más que la dinámica en el ranking | en el panel: S0 con V̂ permutado; S0 con q copia frente a q BC; S0 frente a W0-S con q fijo | EST-D | exploratoria | H8/H9 offline |
| **HS-1** | E2 | Una sombra con RNG inyectado mantiene la sincronía en partidas del bench | primer frame de divergencia de `validate_replay.py` frente a `parity.py` sobre ≥ 50 `.slp` del bench | EST-D · Dolphin | cota superior para E5 (no es gate de muerte) | H5 (cota) / G4 |
| **HP-1** | E3 | **(MVP)** Bajo demora D, la misma π0 juega mejor con el presente predicho que con la observación envejecida | b0 − a (y b1 − a si G1-jepa pasó) | **EST-P** · sim untimed, D = 12; confirmación en Dolphin RT-slow y RT-strict | IC ⊂ ±10 pp → el predictor no aporta | nueva (X4) |
| **HP-2** | E3 | **(control asesino)** Entrenar con demora basta | c − b0 a igual cómputo total | **EST-R** (5 semillas × 200) | c − b0 ≥ 10 pp → se cierra la dinámica aprendida para control bajo demora | nueva (X4) |
| HP-3 | E3 | Techo | d − b0 | EST-P | descriptiva | — |
| **HC-1** | E4 | Planificar con dinámica exacta mejora a elegir entre las mismas propuestas sin rollouts | S0 − P0-Q (mismos N, K, T, semillas, q, V̂) | EST-P · sim untimed · I_full + PRIV | sin efecto, y S0-MC también → se cierra el MPC con cualquier dinámica en ese evaluador | H1 / G5 |
| HC-2 | E4 | V̂ es el cuello | S0-MC − P0 frente a S0 − P0; S0 − S0-Vperm | EST-P | S0-MC > P0 y S0 + V̂ no → el culpable es V̂ | H9 |
| HC-3 | E4 | q domina sobre la dinámica | \|Δ(q)\| frente a \|Δ(dyn)\| en el mismo calendario | EST-P | exploratoria | H8 |
| HL-1 | E5 | Sombra en vivo | fracción de frames en sincronía | EST-D · Dolphin | ≥ 99 % → desaparece el nicho Dolphin (queda `I_human`); < 95 % → nicho real | H5 / G4 |
| HL-2 | E6 | W mejora a P0 tras la divergencia o en `I_human` | W − P0 | EST-P · Dolphin RT-slow | — | H6 |
| HM-1…4 | E6 | MPC aprendido (H2), W1−W0 en juego (H3), MPC en RT-strict (H10), imaginación (H11), recetas PPO y E1/E2 (H4) | según A8 §1 | EST-P / EST-R / EST-T | solo si E4 (y E1b para W2) lo justifican | H2, H3, H4, H10, H11 |

**Multiplicidad** (PROP-int, coherente con DECISION).
- Familia confirmatoria de E3 = {HP-1 (b0−a), HP-2}, con Holm y α familiar 0,05.
- Familia de E4 = {HC-1}.
- Los gates de E1 no son tests de juego: se aplican con su regla (§8).
- El resto es exploratorio y lleva esa etiqueta.

## 4. Matriz mínima de brazos y qué se iguala en cada comparación

### 4.1 Brazos por etapa

| Etapa | Brazos |
|---|---|
| E1 (offline) | Dinámica: W0-S, W1-L y los suelos (persistencia, velocidad constante, mayoritaria condicionada, acciones barajadas). Rival: oracle, q (O2, K = 4/8) y marginal (O1/UNK, diagnóstico). Representación: E-rand (congelado), E0, E0b, E1 (J-T congelado), E1-S (S-T) al 10/30/100 % de datos. Cabezas: BC, q y V̂ sobre cada encoder |
| E3 (juego) | (a) π0 con observación envejecida · (b0) π0 + presente W0-S · (b1) π0 + presente W1-L si pasó G1-jepa · (c) π_delay con la receta slippi-ai · (d) π0 con D = 0 |
| E4 (juego, sim) | P0-Q · S0 · S0-Vperm · S0-MC (sin V̂, rollouts de 120–240 frames) · P0-logp secundario |
| E6 | W0-S/W1-L + MPC, W-persist, W-shuffle, B0, B1 (PPO con correa KL), E0b/E1/E2/E1-S con PPO, W2, H0 |

Referencias externas: Faynt-10M-Expert/Arena, MIMIC fox y Phillip `*_d18`. Solo son descriptivas y **nunca** entran
en una afirmación de efecto. Todos los brazos propios comparten el esquema único de A6 (DESIGN §2.1).

### 4.2 Igualaciones

| Contraste | Igual en ambos brazos | Lo único que varía | Si no se puede igualar |
|---|---|---|---|
| W0-S / W1-L frente a suelos (E1) | split, ventanas, horizontes, régimen, partidas de test | predictor | — |
| W1-L − W0-S | encoder E, datos, H, parámetros (±10 %), pasos, régimen y fuente del rival | objetivo latente frente a explícito | si el núcleo cambia (GRU frente a transformer) se declara "predictor + arquitectura" |
| E1/E1-S − E0b | corpus (solo train), E, D, cabeza, receta BC, **cómputo total** | objetivo de preentrenamiento | reportar a igual frames y a igual cómputo |
| E1 − E1-S | todo lo anterior + mismo predictor | latente frente a estado explícito | — |
| b0 − a, b1 − a, d − b0 | **el mismo checkpoint π0**, D, rivales, calendario, puertos, semillas `hash(schedule_id, frame)`, régimen, reloj | entrada de π0 (envejecida o predicha) | — |
| c − b0 | corpus, esquema, encoder, D, rivales, calendario, **cómputo total de entrenamiento** (π0 + W0-S + q frente a π_delay con pasos extra) | receta | reportar también a igual frames |
| S0 − P0-Q | checkpoint/prior, N = 16, K = 4, T = 16, semillas de muestreo, q y sus K semillas, V̂(x), λ_b | término de rollout | dos tablas: a igual conteo y a igual tiempo |
| S0 − W (E6) | todo lo de S0 − P0-Q; `I_full`; privilegio declarado | fuente de dinámica | S0 se presenta como cota, no como competidor |

**Controlabilidad.**
- El RNG de Melee no se siembra en Dolphin (HAL h2h README L32-33 [A8-007]), y en sim `runner.play` no reenvía la
  semilla (L200-202).
- Hasta que E4 registre y fije la semilla, el emparejamiento solo controla las semillas de la política.
- Por tanto **no** se supone ganancia de varianza por emparejamiento.

## 5. Splits (A6 `split_plan.json` + precisiones de A8 §4)

1. **Identidad y duplicados.** La identidad es el sha1 del `.slp`. Se deduplica **entre** carpetas de personaje de
   `melee-ranked-replays` (cada partida no-ditto aparece en dos carpetas) y se detectan casi-duplicados hasheando las
   primeras 600 filas post-cuenta atrás. Todo esto va **antes** de asignar el split.
2. **Asignación.** `bucket = int(sha256('A6-split-v1|'+sha1)[:8],16)/2^32`. Perspectivas, espejo, intercambio de
   puertos y ventanas se generan **después** del split. Quedan prohibidos el `swap=True` previo de slippi-ai y el
   `random_split` por ventanas de LeWM.
3. **Proporciones.** **Discrepancia detectada:** A6 fija 90/5/5, pero E1 pide ~2.000 train / 300 val / ≥ 1.000 test
   (DECISION §3). Con 90/5/5, 1.000 partidas de test exigirían ~20.000 partidas.
   - **PROP-int**: preregistrar umbrales de bucket específicos de E1 sobre ~3.300 dittos deduplicados (train
     < 0,606, val < 0,697, test el resto) y versionar el split como `A6-split-v1-E1`.
   - Si el corpus de dittos es mayor, se mantienen esos umbrales.
4. **Población.** Hay fuga por set inevitable en ranked anónimo (sin `match_id`, códigos ni fechas). El test se
   titula "partidas no vistas de la misma población". MRR y HAL ranked salen de los mismos volcados de Fizzi y nunca
   se usa uno como test del otro.
5. **Uso de cada split.** Preentrenamiento, BC, q y V̂ usan solo `train`. λ, D, H, k y checkpoints se seleccionan
   solo en `val`. El test se abre una vez.
6. **Panel contrafactual de E2.** Se congela por sha256 antes de entrenar cualquier W que se vaya a evaluar en él.
7. **Rivales de test.** Se excluyen los usados en currículo o selección. Faynt declara que "some releases also
   informed RL run or checkpoint selection" (`Faynt-Benchmarks/README.md` L50): las versiones de slippi-ai que lo
   seleccionaron no son rivales de test sin etiqueta de parentesco.

## 6. Métricas

**Primaria de juego** (DECISION §3): **margen de stocks** al final (stocks propios − rivales; continua). Su tamaño
muestral se fija con la varianza del piloto *[piloto]*.

**Co-primaria de victoria**: tasa de victoria macro-promediada por (rival × escenario).
- Requiere **≥ 400 partidas por brazo**.
- El empate exacto (`winner=None`) cuenta 0,5.
- La muerte súbita no se cuenta.

**Secundarias.**
- Diferencia de porcentaje en partidas a tiempo.
- Tasas de autodestrucción y de timeout con límites congelados *[piloto]*. Un brazo que gana subiendo SD por encima
  del límite no pasa.
- Entropía de la política.
- Caída frente a una sonda de mejor respuesta (explotabilidad).
- Cómputo total.

**Offline (EST-D)**, por h ∈ {1, 4, 8, 16, 32}, por fase de juego (neutral, hitstun, fuera, borde, escudo) y siempre
contra los suelos:
- MAE de pos/% y % dentro de tolerancia (≤ 1 u y ≤ 5 u);
- acierto y NLL de `action` en frames de cambio; ECE;
- exact-match de contadores;
- precisión/recall de eventos a ±1 y ±3 frames;
- % de estados inválidos;
- AUROC del desacuerdo del ensamble;
- error de "predecir el presente" con D ∈ {6, 12, 18}, desglosado en rival oracle / q / marginal y `I_full` /
  `I_human`;
- para probes de representación: techo (entrada cruda), suelo (encoder aleatorio) y pares mínimos
  (`evidence/A3/ablations.json`).

**De decisión (E2):** acuerdo top-1 y Spearman frente a S0, y regret en valor del simulador.

**Temporales (EST-T).**
- p50/p95/p99 por tramo y extremo a extremo, con los campos de `06_EXPERIMENT_PROTOCOL.md` (`obs_frame,
  decision_frame, target_frame, applied_frame, capture_ts_ns … applied_ts_ns`, medido/inferido).
- Plazos perdidos, nivel de fallback, `N_eff` y `loadavg` por segundo.
- Protocolo: 300 frames de calentamiento descartados y ≥ 20.000 frames por condición.

**Operativas** (separadas del resultado): `void`, `slow`, `error`, `timeout`, crashes y desincronías. Se cuentan
todos los intentos; un fallo nunca inventa un resultado.

## 7. Tamaño muestral, semillas y equivalencia

| Caso | Requisito | Fuente |
|---|---|---|
| EST-P, checkpoint fijo, victoria | **393 partidas por brazo para 10 pp** (1.570 para 5 pp; 99 para 20 pp). Con 40 solo se detectan ~31 pp | `power_result.json` |
| Propuestas previas | 40 (defensor), 120 (pragmático) y 200 (escéptico) partidas por brazo **no** sostienen sus gates | DECISION §3 |
| EST-R, recetas | unidad = semilla. 5 semillas × 200 partidas → MDE 8,2 pp (σ_s = 3 pp), 10,9 pp (σ_s = 5 pp); 16,6 pp con 40 partidas por semilla. Para 5 pp harían falta 14–24 semillas | `power_result.json` |
| σ_s | **desconocida en Melee**. Se estima en el piloto; si σ_s > 5 pp, 5 semillas no alcanzan 10 pp y el resultado de HP-2 se declara inconcluso | DECISION §3, G-05 |
| Gates de E1 | antes de congelar se mide la varianza entre semillas con 3 corridas de E0. Un efecto cuenta si supera 2× esa desviación y su IC95 por partida excluye 0. 5 semillas para cualquier resultado que cambie la decisión | DECISION §3 |
| EST-D | ≥ 1.000 partidas de test; ≥ 2.000 raíces en el panel de E2 | DECISION §3 |

**Semillas de entrenamiento frente a semillas de partida.**
- `train_seed` es la semilla de inicialización y orden de datos de un brazo aprendido.
- `pair_id = (escenario, rival, semilla inicial, repetición, reloj, régimen)` define el calendario de partidas.
- `schedule_id = (pair_id, asignación de puertos, brazo, train_seed)`.
- Las dos asignaciones de puerto de un `pair_id` se remuestrean juntas.

**Equivalencia.**
- La regla "IC95 ⊂ (−10, +10)" equivale a TOST con margen ±10 pp y α = 0,025 por cola.
- **INF-int:** con 400 partidas por brazo, sin emparejamiento y p = 0,5, la semiamplitud del IC95 es ≈ 6,9 pp. Si
  Δ = 0, la probabilidad de declarar "sin efecto" es solo ≈ 61 %. Hacen falta **≈ 525 partidas por brazo** para un
  80 % (cuenta con `statistics.NormalDist`).
- Con ≥ 400 el veredicto "sin efecto" será a menudo "inconcluso". Subir a 525 cuando el objetivo sea cerrar una línea
  es una decisión de presupuesto. No cambia los gates de DECISION.

**Análisis.**
1. Bootstrap jerárquico propio (≈ 50 líneas, 10.000 réplicas): semillas por brazo y, dentro de cada una, bloques
   `pair_id`, estratificado por celda. Para EST-P solo el nivel de bloques.
2. Se reporta también la IQM y P(X > Y) a la manera de rliable, y cada semilla individualmente.
3. Sensibilidad: con y sin `slow`/`void`, con y sin la semilla extrema, y por celda.

## 8. Etapas E0–E6, gates y costes (DECISION §3)

| Etapa | Recurso | Trabajo y entregable | Coste (EST/HIP) | Gate: pasa / mata |
|---|---|---|---|---|
| **E0** Tubería, suelos, humo, preregistro | local, sin ISO ni GPU (≤ 2 hilos, `nice`, ≤ 1 GB RAM, datos en el segundo disco) | venv con `peppi_py` y `zstandard` (**permiso del usuario**); ≥ 150 Fox dittos de `erickfm/melee-ranked-replays@ef54ddc2` carpeta FOX; parser al esquema A6; split por sha1 + dedup; suelos triviales por campo y h; test de fuga de alineación (objetivo = mando de f+1, nunca de f); humo ≤ 1M; envoltorio de plazo con agente sintético en un bucle falso que imite `runner.play` L279-300; banco A7 extendido a la arquitectura real de W0-S, al transformer con KV-cache (G-08) y a la estimación DESIGN §3.9; 3 corridas de E0 para la varianza; este plan sellado con hash | 15–25 h-persona; 3–8 h-CPU; 0 € | No mata. Si < 95 % de las partidas traen velocidades, hitstun y `action_state_frame`, se redefine el esquema |
| **E1** Diagnóstico offline a escala | GPU alquilada (24 GB), sin ISO | ~2.000 train / 300 val / ≥ 1.000 test (§5.3). W0-S, W1-L, q y V̂; BC con E0/E0b/E1/E1-S al 10/30/100 %; error por h ∈ {1, 4, 8, 16, 32}; "presente" con D ∈ {6, 12, 18}; rival oracle / q / marginal; `I_full` e `I_human` | 30–45 h-persona; 10–35 h-GPU; 10–25 €, **parada dura a 35 €** (E1 + E1b) | **G1-dyn**: W0-S ≥ 10 % relativo mejor que el mejor suelo en error de eventos a h ∈ {4, 8}; si no, se paran W0/W1. **G1-q**: q mejora la NLL sobre la marginal y el acierto de acción del rival en frames de cambio a h = D+1 supera al mejor suelo para D = 6 y 12; si no, E3 no se ejecuta y la ISO solo se justifica por E4. **G1-jepa**: W1-L frente a W0-S y E1 frente a E1-S en ≥ 2 de 3 tareas (BC, q, V̂); si no gana, se cierra la etiqueta JEPA. **G1-rep**: E1 o E1-S frente a E0b al 10 % y al 100 %; si ninguno gana, no hay aporte offline del preentrenamiento. *Pasar G1 es condición necesaria, no prueba de ventaja al jugar* |
| **E1b** Throughput fusionado | misma instancia | política + dinámica 1–5M, CUDA graphs, batch 4k–64k, sincronizado (`torch.cuda.Event`) | 4–6 h-persona; 1–2 h-GPU; 1–2 € | < 10× 6.337 frames/s → W2 descartado. Como es otra máquina, solo vale un cociente grande |
| **E2** Mediciones baratas con ISO | ISO; CPU; sin tocar repos | `python -m melee_brute bench` y banco A7 en la **misma** máquina; test de aliasing (H mínimo); panel de regret con ≥ 2.000 raíces (W / P0 / S0, S0-Vperm, q copia frente a q BC); `tools/validation/validate_replay.py` frente a `melee_llm/sim/parity.py` sobre ≥ 50 partidas del bench grabadas | 20–30 h-persona; < 15 h-núcleo; 0 € | regret_W ≥ regret_P0 → W no se usa para MPC (no afecta a E3) |
| **E3** MVP en juego | ISO; `Agent` nuevo en melee-llm (sin tocar runner ni melee-brute) | brazos a / b0 / b1 / c / d. Piloto con D = 12, ≥ 400 partidas por brazo en sim `untimed`; c con 5 semillas × 200; confirmación en Dolphin `RT-slow` y `RT-strict` | 40–60 h-persona; 30–60 h-núcleo por D; 0–15 € | b − a sin efecto (IC ⊂ ±10 pp) → el predictor no aporta. c − b ≥ 10 pp a igual cómputo → "basta entrenar con demora" y se cierra la dinámica aprendida para control bajo demora |
| **E4** S0-ceiling | ISO; **cambio en melee-llm** (`sim/runner.py` L47-53: pasar `World` y fijar/registrar la semilla) | S0 − P0-Q, S0-Vperm, S0-MC; ≥ 400 partidas por brazo; margen de stocks primario | 30–50 h-persona; ~200 h-núcleo (INF de A5 sobre cifras de otra CPU; se recalcula con E2); 0–15 €. **Nota del integrador:** esos 200 h-núcleo cubren S0 + P0-Q + B a T = 16. S0-MC con T = 120–240 cuesta ~8–15× S0 por decisión (EST ≈ +500–1.000 h-núcleo para 400 partidas) y S0-Vperm ≈ +65 h | S0 − P0-Q sin efecto y S0-MC también → se cierra el MPC con cualquier dinámica en ese evaluador. S0-MC > P0 pero S0 + V̂ no → el culpable es V̂ |
| **E5** Sombra en vivo | ISO; **cambios en melee-brute** (API C `step` con semilla por frame y eventos de escenario, binding Python) + decodificador en vivo sobre `ConsoleTap` | fracción de frames en sincronía en partidas del bench | días de ingeniería; no presupuestado | ≥ 99 % → el nicho Dolphin desaparece (queda `I_human`); < 95 % → nicho real |
| **E6** MPC aprendido, PPO (≥ 5 semillas), imaginación | ISO + días de GPU | HM-1…4 | no presupuestado | solo si E4 (y E1b para W2) lo justifican |

Lectura de E3 en los cuatro casos posibles (DECISION §5):
- b − a ≥ 10 pp y b no peor que c → el modelo aprendido aporta bajo demora; se amplía a más D y a Dolphin `RT-strict`.
- c − b ≥ 10 pp → se cierra.
- b − a sin efecto → el predictor no aporta.
- El resto es inconcluso y se reporta así.

## 9. Qué se puede ejecutar con cada recurso

| Recurso | Etapas o partes ejecutables |
|---|---|
| **Esta máquina, sin ISO ni GPU, sin permiso de venv** | sellar el plan; envoltorio `RT-strict` y trazas con agente sintético; banco de latencia A7 extendido (W0-S real con pesos aleatorios, transformer con KV-cache, estimación §3.9 de DESIGN); script de bootstrap jerárquico comprobado con datos sintéticos |
| **Esta máquina con permiso de venv** (`peppi_py`, `zstandard`, ≤ 1 GB de replays) | todo E0 (humo ≤ 1M, ≤ 150–300 partidas). Entrenar a escala aquí **no**: 37 h por 1k partidas × 10 épocas con MLP-1M (A7 §4.2) |
| **GPU alquilada, sin ISO** | E1, E1b (y E0 si no hay permiso local, +2–4 €) |
| **ISO, CPU, sin tocar repos** | E2; E3 (un `Agent` nuevo no es un cambio en el runner) |
| **ISO + cambio en melee-llm** (`sim/runner.py` L47-53) | E4 |
| **ISO + cambios en melee-brute** (API C/Python) **+ decodificador en melee-llm** | E5 |
| **ISO + días de GPU** | E6 |

## 10. Correspondencia entre las puertas de A8 (G0–G9) y las etapas E0–E6 de DECISION

| Puerta A8 | Contenido A8 | Etapa DECISION | Diferencia |
|---|---|---|---|
| G0 Congelar | plan, esquema, envoltorio con agente sintético | **E0** | E0 añade la tubería `.slp`, los suelos y el humo |
| G1 Throughput GPU | H12 | **E1b** | — |
| G2 Diagnóstico offline | W0-S, W1-L, q, V̂, probes, "presente" con D ∈ {0, 6, 18} | **E1** (G1-dyn / G1-q / G1-jepa / G1-rep) | D ∈ {6, 12, 18}; umbral 10 % relativo; G1-q explícito |
| G3 Simulador + panel | bench del simulador, aliasing, regret (H7), S0-Vperm offline | **E2** | — |
| G4 Sombra | H5 (≥ 95 %) | **E2** (cota con `validate_replay` frente a `parity`) + **E5** (sombra en vivo) | se parte en una cota sin cambios y una implementación con cambios; umbrales < 95 % / ≥ 99 % |
| G5 S0-ceiling | H1, H8, H9, ≥ 400 por brazo | **E4** | se añade S0-MC |
| — | (sin equivalente en A8) | **E3** | nueva: MVP del predictor del presente (X4 / G-07) |
| G6 MPC aprendido | H2, H3, H10 | **E6** | — |
| G7 Recetas | B0, B1, E0b, E1, E2, E1-S con ≥ 5 semillas | **E6** (en E1 solo la parte offline) | — |
| G8 Imaginación | H11 | **E6** | condicionado a E1b |
| G9 Extensión | H6, H0, rivales fuera de piloto | **E6** | — |

El MCID de A8 era 5 pp; DECISION lo sube a **10 pp** como efecto mínimo decidible. Las hipótesis H1–H12 de A8 se
conservan con su número en la columna "A8" de §3.

## 11. Criterios de parada global

- Si falla una puerta de adaptador o de fuga (test de alineación de E0, split), se detiene todo lo que dependa de ella.
- Al agotar el techo de gasto (35 € en E1 + E1b) se conservan los parciales y solo se analiza lo comparable.
- Una comparación inválida por reloj o por acceso (p. ej. S0 en `I_human`) no se reporta como contraste.
- Si G1-dyn y G1-q fallan, solo queda la línea de búsqueda exacta (E2 → E4).
- Si E4 resulta "sin efecto" y E1b da < 10×, la dinámica aprendida se cierra en sim. Solo siguen E5 / `I_human` y la
  representación (HD-4).
