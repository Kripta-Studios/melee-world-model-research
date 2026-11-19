# A8 · Plan experimental congelable (preregistro propuesto)

Agente A8 · 2026-11-19 · Estado: **PROPUESTA. Nada de este documento se ha ejecutado**: no hay partidas,
entrenamientos ni benchmarks detrás de ninguna cifra salvo el cálculo de potencia sintético de
`evidence/A8/checks/power.py` → `power_result.json` (sha256 `e4650b47…1324`), que es aritmética sobre un modelo
binomial-normal, no datos de Melee. Etiquetas: DOC, CÓD, INF, PROP, DESC como en el brief. `[A8-xxx]` →
`claims.jsonl`; `[Ax-yyy]` → claims de otros roles. Revisión crítica que motiva cada decisión: `CRITICAL_REVIEW.md`.

Este plan se congela (hash del fichero en `preregistration.json` del ejecutor) **antes** de mirar cualquier
resultado de test. Las constantes marcadas *[piloto]* se fijan al cerrar E2 con datos de validación y se vuelven a
congelar antes de E3; ningún umbral se mueve tras ver el test.

---

## 0. Qué se estima y en qué régimen (separación obligatoria)

### 0.1 Estimandos

| Id | Estimando | Unidad de inferencia | Población a la que generaliza |
|---|---|---|---|
| EST-R | Efecto de **entrenar** con una receta (B1−B0, B2−B1, W2−B2) | semilla de entrenamiento independiente (≥5 por brazo) y, dentro, bloque emparejado de partidas | recetas, no checkpoints concretos |
| EST-P | Efecto de **planificar en despliegue** sobre un checkpoint congelado (S0−P0, W0−P0, W1−P0, W1−W0) | bloque emparejado de partidas del calendario; si el prior/valor son aprendidos con ≥2 semillas, la semilla es el nivel superior | **ese** checkpoint, prior, V̂ y q; para generalizar a la receta, repetir con ≥3 checkpoints independientes |
| EST-D | Calidad predictiva offline (W0-S, W1-L vs persistencia/vel. const./acciones barajadas) | partida (bootstrap por partida) | corpus/split declarado |
| EST-T | Viabilidad temporal (p99, plazos perdidos) | condición de carga × réplica de proceso | hardware medido, no otro |

**N partidas de un checkpoint no son N réplicas de entrenamiento** (06 «Cinco fallos» n.º 5). Para EST-R el
número de semillas es el tamaño muestral; las partidas solo reducen el ruido dentro de cada semilla (§6). En la
simulación de `power.py`, con desviación entre semillas σ_s = 5 pp, un test que agrupa las partidas como si fueran
independientes declara una diferencia inexistente el **26 %** de las veces (1 semilla × 200 partidas por brazo) o
el **25,5 %** (5 × 200), frente al 4,6 % de un test a nivel de semilla [A8-010].

### 0.2 Regímenes de información (se reportan por separado, nunca se agregan)

| Régimen | Qué ve la política/planificador en despliegue | Brazos elegibles |
|---|---|---|
| `I_full` | `GameState` completo de libmelee, **incluido `controller_state` del rival del frame actual** (ya aplicado) — es lo que el bench entrega hoy a todo agente salvo bot-writer (CÓD: `libmelee/melee/console.py` L1145-1212 rellena por puerto sin filtrar; `melee_llm/sim/state.py` L93-95) [A1-013, A8-003] | todos los causales; S0 solo aquí y con etiqueta de privilegio |
| `I_human` | lo anterior **sin** `controller_state` del rival (como slippi-ai `jax/embed.py` L461-463 y bot-writer `botwriter/agent.py` L6) | B*, P0, W*; S0 no ejecutable [A5-035] |
| `PRIV` | estado completo del motor (snapshot, memoria de mandos, RNG, semilla) | S0, S0-shadow; siempre como cota, nunca como competidor simétrico |
| `ORACLE` | mandos futuros reales del rival | solo diagnóstico offline (EST-D), **prohibido** en juego (07 `opponent_future_in_deployment`) |
| Privilegio de entrenamiento | V̂/crítico con estado presente bajo demora; mandos de ambos en el objetivo de dinámica | declarado por brazo; permitido solo en entrenamiento |

**Régimen primario congelado: `I_full`** (es el del bench objetivo y las referencias externas Faynt/slippi-ai no
usan el mando del rival, así que no las favorece) **con `I_human` como secundario obligatorio** para todos los
brazos causales. Toda afirmación lleva el régimen en el titular.

### 0.3 Relojes (se reportan por separado)

| Reloj | Definición operativa | Notas |
|---|---|---|
| `RT-strict` | Plazo impuesto por envoltorio propio (patrón bot-writer `budget_ms`, `botwriter/agent.py` L79): al vencer `C_rt` se usa el fallback declarado (L1 mejor evaluado → L2 top-1 del prior → L3 repetir); se cuentan plazos perdidos | Única categoría que puede llamarse «tiempo real». Ningún modo del bench la impone a un agente every-frame [A7-001] |
| `RT-slow` | Dolphin `realtime`/`fast` sin plazo propio; latencia medida | Equivale a pausa a efectos de decisión; **no** se reclasifica como RT ni como untimed (06 L143) |
| `untimed` | `fast` o `--mode sim` declarados como pausa | Mide calidad de decisión |
| `accelerated_training` | recolección | Nunca evaluación |

Plataforma, ortogonal al reloj: **Dolphin** (lo que usa el bench: `entrants.game_mode` solo devuelve
`realtime|fast`, `bench/entrants.py` L189-191 [A1-014, A8-009]) frente a **`--mode sim`** (no forma parte del
bench). Ninguna conclusión obtenida en sim se presenta como conclusión sobre el bench.

---

## 1. Hipótesis falsables numeradas

Familia confirmatoria (Holm sobre H1–H4, α familiar 0,05); el resto es secundario/exploratorio y se etiqueta.
Δ = diferencia de tasa de victoria macro-promediada por (rival × escenario), en puntos porcentuales. MCID = 5 pp
(§7). «Mejora» exige Δ̂ ≥ 5 pp **y** límite inferior del IC95 > 0; «sin efecto relevante» exige IC95 ⊂ (−5, +5)
(equivalencia, TOST); cualquier otro IC = **inconcluso**. La ausencia de significación nunca se lee como «no
aporta» [A8-015].

| Id | Hipótesis (forma que se intenta refutar) | Contraste | Estimando / régimen | Refutada si |
|---|---|---|---|---|
| **H1** | Planificar con dinámica exacta sobre un checkpoint fijo mejora a elegir entre las mismas propuestas sin rollouts | S0 − P0-Q (mismos N, K, semillas de muestreo, q, V̂(x)) | EST-P · sim · untimed · I_full+PRIV | IC95 ⊂ (−5,+5) → se cierra la línea MPC (W0/W1) en ese evaluador; IC < 0 → el evaluador V̂ está roto |
| **H2** | Un predictor estructurado aprendido recupera una fracción relevante del valor de S0 | (W0-S − P0-Q) / (S0 − P0-Q) ≥ 0,5 y W0-S − P0-Q ≥ 5 pp | EST-P · sim · untimed · I_full | condicionado a H1 positiva; si W0 ≈ P0 con S0 > P0, la dinámica aprendida es el cuello |
| **H3** | El latente tipo LeWM no aporta sobre el estructurado con planificador fijo | W1-L − W0-S | EST-P · sim y Dolphin · untimed | se rechaza la hipótesis nula de equivalencia si IC95 excluye (−5,+5) |
| **H4** | El preentrenamiento JEPA del encoder (sin dinámica en inferencia) mejora a BC+PPO con igual cómputo | E1/E2 − E0b, con E1-S como control (si E1-S ≥ E1 → el beneficio no es «JEPA») | EST-R · Dolphin fast · I_full | equivalencia o E1-S ≥ E1 |
| H5 | En Dolphin, un simulador sombra con los mandos de ambos jugadores mantiene el estado exacto en ≥ 95 % de los frames de las partidas del bench | tasa de frames en sincronía hasta la primera divergencia | EST-D · Dolphin · I_full | < 95 % → el nicho Dolphin de la dinámica aprendida es real y se mide H6 |
| H6 | Tras la divergencia del sombra (o en `I_human`), W0/W1 mejora a P0 | W − P0 en los tramos post-divergencia / partidas `I_human` | EST-P · Dolphin · RT-slow | equivalencia |
| H7 | El error de predicción relevante para decidir (regret frente a S0 en un panel contrafactual) de W es menor que el de P0 | regret_W < regret_P0 (bootstrap por estado raíz agrupado por partida) | EST-D · sim offline | regret_W ≥ regret_P0 → W no se despliega aunque S0 > P0 |
| H8 | La calidad del modelo del rival q domina sobre la de la dinámica: con dinámica exacta, cambiar q (copia del prior → BC del rival a su R) mueve Δ más que cambiar S0 → W0-S con q fijo | |Δ(q)| vs |Δ(dyn)| en el mismo calendario | EST-P · sim · untimed | |Δ(q)| < |Δ(dyn)| |
| H9 | El valor terminal domina el objetivo del MPC: con V̂ barajado entre candidatos (control) S0 cae a ≤ P0 | S0(V̂) − S0(V̂ permutado) | EST-P · sim | S0(V̂ permutado) ≈ S0(V̂) → V̂ no aporta y el MPC vive de la recompensa a corto plazo |
| H10 | Un MPC aprendido cabe en `RT-strict` en el hardware destino con p99 ≤ C_rt y ≤ 1 % de plazos perdidos | medición integral con Dolphin y ambos agentes en la misma máquina | EST-T | p99 > C_rt o > 1 % → el brazo solo puede afirmarse en `RT-slow` |
| H11 | Entrenar la política en imaginación (W2) iguala a B2 a igual interacción real **y** supera a B2 a igual tiempo de pared en GPU | W2 − B2 en dos presupuestos | EST-R · Dolphin fast | equivalencia en ambos |
| H12 | Un pipeline fusionado en GPU (política + dinámica aprendida) genera ≥ 10× transiciones/s por dólar que la granja simulador+política del autor | throughput medido | EST-T · GPU | < 10× → el argumento «imaginación masiva» cae (contraejemplo X1 de la revisión) |

---

## 2. Matriz mínima de brazos y qué se iguala en cada comparación

### 2.1 Brazos

| Brazo | Qué es | Dinámica en decisión | Dinámica en entrenamiento | Notas de diseño congeladas |
|---|---|---|---|---|
| B0 | BC, encoder E aleatorio, esquema de observación A6 completo (reparseo .slp) | no | no | Mismo esquema para **todos** los brazos propios (resuelve K5 de la revisión: no usar el `Game` de slippi-ai para B0 y el esquema A6 para W0) |
| B1 = E0 | B0 + PPO con KL a B0, valor separado, recompensa congelada (slippi-ai sin términos de modelado en la versión principal) | no | no | receta Faynt/slippi-ai [A2-036] |
| E0b | E0 con pasos extra de BC = cómputo de preentrenamiento de E1 | no | no | control de cómputo |
| E-rand | encoder aleatorio congelado + cabeza | no | no | suelo |
| E1 | encoder preentrenado J-T (LeWM-like, SIGReg) **congelado** + BC+PPO | no (predictor descartado; verificar parámetros del forward exportado) | solo preentrenamiento | B2 del protocolo |
| E2 | E1 ajustado (LR encoder 0,1×) | no | idem | |
| E1-S | mismo encoder preentrenado prediciendo el **siguiente estado explícito** | no | idem | control decisivo de «JEPA» [A3-PROP-001] |
| P0-logp / P0-Q | mismas N propuestas que W/S0; puntúa con log π(c) o Q̂(h,c) sin rollout | no | — | **P0-Q es el control principal** de H1–H2 (mismo evaluador «valor» que el MPC); P0-logp, secundario |
| W-persist / W-shuffle | MPC con dinámica de persistencia / secuencias barajadas, mismo evaluador | degenerada | — | comprobación de implementación y de sensibilidad a acciones |
| W0-S + MPC | predictor estructurado 1 frame (A4 §2) + q + V̂(x) | sí (aprendida) | — | |
| W1-L + MPC | latente LeWM-like (A4 §3), V̂ sobre campos decodificados | sí | — | **Variante transformer en `untimed`**; la variante GRU solo en `RT-strict` y etiquetada como cambio de arquitectura (K2). Antes de sustituir por GRU, medir el transformer con KV-cache (hueco G-08) |
| W2 | actor-crítico en imaginación con el predictor de W1, misma inicialización de encoder que E1/E2 | no | sí | igual corpus offline e igual interacción real que E1/E2; reportar también a igual cómputo total |
| S0 | simulador (melee-brute `checkpoint/rollback`) + mismo q + mismo V̂(x) | exacta | — | `--mode sim` pasando el `World` (cambio propuesto en `sim/runner.py` L47-53, no existe [A1-007]); **PRIV** |
| S0-Vperm | S0 con V̂ permutado entre candidatos | exacta | — | H9 |
| S0-shadow | Dolphin + simulador alimentado con mandos de ambos | exacta hasta divergencia | — | requiere canal crudo Slippi (no `GameState`: sin C-stick crudo ni gatillos físicos, [A8-003]); **PRIV** |
| H0 | B1 + MPC solo en recuperación/borde | condicional | — | exploratorio E4 |
| Referencias externas | Faynt-10M-Expert/Arena, MIMIC fox, Phillip `*_d18` en eje de demora | — | — | nunca entran en una afirmación de «efecto del algoritmo»; cada una con su demora nativa y, si se puede, igualada |

### 2.2 Qué se iguala en cada contraste

| Contraste | Igual | Distinto (lo único que varía) | Si no se puede igualar |
|---|---|---|---|
| B1−B0 | esquema, encoder, códec, datos BC, pasos BC, calendario | PPO (N frames de interacción) | — |
| E1/E2−E0b | corpus offline (solo split train), arquitectura E, D, cabeza, receta BC/PPO, frames PPO, rivales, semillas de partida, **cómputo total** | objetivo de preentrenamiento | reportar a igual frames y a igual cómputo |
| E1−E1-S | todo lo anterior + mismo predictor | objetivo latente vs explícito | — |
| S0−P0-Q | checkpoint/prior, N, K, T, semillas de muestreo `(schedule_id, frame)`, q y sus K semillas, V̂(x), λ_b | término de rollout | a igual conteo **y** a igual tiempo (dos tablas) |
| W0−P0-Q, W1−P0-Q | idem | dinámica aprendida | idem |
| W1−W0 | planificador, N, K, T, q, V̂(x), presupuesto | predictor | si el núcleo cambia (GRU vs transformer) se declara «predictor+arquitectura» |
| S0−W | idem; **I_full**; privilegio declarado | fuente de dinámica | S0 se presenta como cota, no como competidor |
| W2−B2 | corpus offline, interacción real, inicialización de encoder, cabezas actor/crítico, receta | rollouts imaginados | si cambia el algoritmo de control: «algoritmo+imaginación» |
| Cualquier brazo vs externo | — | — | solo como referencia descriptiva |

Semillas de muestreo comunes: las propuestas, las K hipótesis del rival y las semillas de partida se derivan de
`hash(schedule_id, frame)` y son idénticas entre brazos (números aleatorios comunes). **Advertencia de
controlabilidad**: en Dolphin el RNG de Melee no se siembra (HAL lo declara en su protocolo h2h,
`experiments/slippi-ai-h2h/README.md` L32-33 [A8-007]) y en `--mode sim` la semilla no se reenvía desde
`runner.play` (L200-202 [A1-001]). Hasta que el adaptador registre y fije la semilla en sim, el emparejamiento
solo controla las semillas de la política, no el RNG del juego; el plan no supone más reducción de varianza que
esa.

---

## 3. Métricas

**Primaria (todas las hipótesis de juego):** tasa de victoria macro-promediada por (rival × escenario), en el reloj
y régimen preregistrados; empate exacto (`winner=None`, `runner.py` `_result`) cuenta 0,5; muerte súbita no
contada (como el runner).

**Secundarias:** margen de stocks (stocks propios − rivales al final, continuo: más potencia que la victoria);
diferencia de porcentaje en partidas a tiempo; tasa de autodestrucción (SD) y de timeout (límites congelados
*[piloto]*; un brazo que gana subiendo SD > límite no pasa la puerta); frames hasta un umbral de fuerza
(curva de aprendizaje, EST-R); cómputo total (preentreno+ajuste+búsqueda+refresco); entropía de la política de
decisión y caída frente a una sonda de mejor respuesta (explotabilidad [A5-016]).

**Offline (EST-D):** por horizonte {1,4,8,16,32} y fase de juego: MAE posición/porcentaje, exact-match de
contadores, precisión/recall de eventos ±1/±3 frames, NLL/Brier y ECE, % estados inválidos, rango efectivo del
latente, AUROC del desacuerdo del ensamble; **métricas de decisión**: acuerdo top-1 y Spearman de ranking frente
a S0 y regret en valor del simulador [A4-024]. Siempre frente a persistencia, velocidad constante, mayoritaria
condicionada y acciones barajadas; siempre separado `ORACLE` / q-muestras / marginal y `I_full` / `I_human`.

**Temporales (EST-T):** p50/p95/p99 por tramo y extremo a extremo (campos de 06 L126 y A6 `timing_contract.json`),
plazos perdidos, nivel de fallback usado, N efectivo evaluado, `loadavg` por segundo.

**Operativas (separadas del resultado de Melee):** `void`, `slow`, `error`, `timeout`, crashes, desincronías;
todos los intentos se cuentan; un fallo nunca inventa un resultado; repetición de un caso de infraestructura solo
si el fallo es del proceso (no del agente) y se registra.

---

## 4. Splits (datos offline)

Se adopta `A6/split_plan.json` con estas precisiones de auditoría:
1. Identidad = sha1 del .slp; deduplicación **entre** carpetas de personaje de melee-ranked-replays («~90 %
   duplication») y **entre** carpetas pro de HAL (HAL deduplica solo dentro de cada jugador [A6-017]) antes de
   asignar split. Perspectivas, espejo, intercambio de puertos y ventanas **después** del split (prohibido el
   `swap=True` previo de slippi-ai [A6-019] y el `random_split` por ventanas de LeWM [A3-LWM-003]).
2. MRR y HAL ranked salen de los mismos volcados de Fizzi: nunca uno como test del otro [A6-023].
3. **Fuga por set inevitable en ranked** (sin `match_id`, códigos ni fechas): el test `S_game` mide «partidas no
   vistas de la misma población», y así se titula. Generalización a jugadores solo en `pro/` (jugador de carpeta).
4. Preentrenamiento JEPA, BC, q y V̂ usan solo `train`; selección de λ, D, H y checkpoints solo en `val`; el test
   sellado se abre una vez. Una corrida exploratoria que lo vea obliga a un test nuevo.
5. Panel contrafactual (C1/C2 de A4) congelado por sha256 antes de entrenar cualquier W.
6. Rivales de test: excluir del pool de test los rivales usados en currículo/selección. **Faynt declara que
   «some releases also informed RL run or checkpoint selection»** (`Faynt-Benchmarks/README.md` L50 [A8-006]):
   si Faynt-Arena es prior o referencia, las versiones de slippi-ai que lo seleccionaron no pueden ser rivales de
   test sin etiqueta de parentesco.

---

## 5. Calendario emparejado de evaluación

- `pair_id` = (escenario, rival, semilla inicial, repetición, reloj, régimen); `schedule_id` = (pair_id, asignación
  de puertos, brazo, semilla de entrenamiento). Las dos asignaciones de puerto de un `pair_id` van juntas en el
  remuestreo.
- Rivales (mínimo): pool de validación (para ajustar), pool de test fuera de entrenamiento (≥2 estilos: Faynt-Expert
  a 0 frames, Phillip `fox_d18_*` en el eje de demora), CPU-9 como humo/ancla local solamente (Firoiu: el in-game
  AI «is mostly deterministic and easily exploitable», PDF 1810.07286v1, sección «Experiments» [A8-004]), y en H1-H3/H8 la copia del
  prior (ditto en sim, que no ofrece CPU).
- Escenarios: Battlefield y Final Destination (las del bench). Fox ditto (lo que fuerza `bench/game.make_agent`).
- Orden de ejecución aleatorizado por bloques; carga de la máquina registrada; partidas `slow` en realtime se
  reportan, no se reclasifican.

---

## 6. Tamaño de muestra y potencia

Cálculo en `evidence/A8/checks/power.py` (aritmética + Monte Carlo sintético; p=0,5; α=0,05 bilateral; potencia
0,80; sin ganancia por emparejamiento, que no está garantizada sin RNG controlable). σ_s = desviación entre
semillas de la tasa de victoria verdadera: **desconocida en Melee** y estimada en E2.

**EST-R (recetas), semillas por brazo necesarias** (G = partidas por semilla):

| Δ | σ_s=0 | σ_s=3 pp | σ_s=5 pp | σ_s=8 pp |
|---|---|---|---|---|
| 5 pp, G=200 | 8 | 14 | 24 | 49 |
| 5 pp, G=1000 | 2 | 8 | 18 | 42 |
| 10 pp, G=200 | 2 | 4 | 6 | 13 |
| 10 pp, G=40 | 10 | 12 | 14 | 20 |

**Diferencia mínima detectable con 5 semillas** (el mínimo del protocolo): 8,2 pp (σ_s=3, G=200), 10,9 pp
(σ_s=5, G=200), 16,6 pp (σ_s=5, G=40). Con 1 semilla: 24–35 pp. **Conclusión:** con 5 semillas el protocolo solo
puede detectar efectos de ~10 pp; para el MCID de 5 pp hacen falta 14–24 semillas si σ_s es de 3–5 pp. Se
preregistran 5 semillas como mínimo y se declara que H4/H11 solo tienen potencia para ≥ 10 pp salvo que E2 mida
σ_s ≤ 2 pp. El calendario piloto de 06 (40 partidas por brazo y semilla) es para depurar y estimar σ_s, no para
decidir.

**EST-P (planificación sobre un checkpoint fijo):** aquí las partidas sí son la unidad (el estimando es ese
checkpoint). Partidas por brazo: 1.570 para 5 pp, 393 para 10 pp, 99 para 20 pp. **Las 40 partidas por brazo del
«S0-ceiling» de A5 §6.3 solo detectan ~31 pp** [A8-014]: no pueden falsar H1 en la forma «S0−P0 ≤ 0». Se
preregistra: (i) primaria con el margen de stocks (continuo, varianza menor; tamaño fijado con la varianza del
piloto), (ii) victoria con ≥ 400 partidas por brazo (10 pp) en `untimed` sim, que según la estimación de A5
(~10 min·núcleo por partida a N·K·T=16·4·16, INF) son ≈ 200 h·núcleo para S0+P0-Q+B — un día en 8–16 núcleos;
(iii) para generalizar a la receta, repetir con ≥ 3 checkpoints/priors independientes.

**EST-D:** bootstrap por partida; ≥ 1.000 partidas de test y ≥ 2.000 estados raíz en el panel contrafactual
(agrupados por partida de origen para el IC).

---

## 7. Análisis

1. **Nivel 1 (semilla)** para EST-R: puntuación por semilla y celda (rival × escenario) = tasa de victoria sobre
   sus partidas. Matriz (semillas × celdas) por brazo.
2. **Bootstrap jerárquico** (implementación propia, 10.000 réplicas): remuestrear semillas por brazo
   (independientes) y, dentro de cada semilla, bloques `pair_id` completos (ambos puertos juntos); estratificado por
   celda para conservar denominadores. Para EST-P, solo el nivel de bloques.
3. **Agregados estilo rliable** (Agarwal et al. 2108.13264 [R01]): media macro (primaria), IQM sobre la matriz
   semillas × celdas (secundaria, robusta a semillas atípicas), probabilidad de mejora P(X>Y) y perfiles de
   rendimiento; IC por bootstrap estratificado. `rliable` (`library.py` `StratifiedBootstrap` L26, espera forma
   `(num_runs, num_tasks)`; `metrics.aggregate_iqm` L61) depende de `arch>=5.3.1,<8` (no instalado aquí) y el
   repositorio está archivado: congelar versión o reimplementar (≈50 líneas) y verificar contra rliable en un
   caso de prueba. **Con 5 semillas × 4 celdas = 20 valores, la IQM recorta 5 por cola: reportar también todas
   las semillas individualmente** (06 §4).
4. **Multiplicidad:** Holm sobre H1–H4; el resto exploratorio sin ajuste pero etiquetado.
5. **Equivalencia:** TOST con margen ±5 pp para afirmar «no aporta».
6. **Sensibilidad:** con y sin partidas `slow`/`void`; con y sin la semilla más extrema; por celda.
7. **Diferencia mínima relevante (MCID): 5 pp** de victoria macro (06 L97) y, para el margen de stocks, el valor
   equivalente estimado en el piloto *[piloto]*. Offline: mejora sobre persistencia ≥ 10 % relativo en el error
   de eventos a h=8 *[piloto]*; regret de decisión ≥ 20 % menor que P0 *[piloto]*.

---

## 8. Etapas y puertas (del experimento más barato al más caro)

Recursos: **[local]** esta máquina (CPU, sin ISO ni GPU, sin poder leer .slp sin instalar `peppi_py`),
**[datos]** descarga autorizada de replays + venv con `peppi_py`/`zstandard`, **[ISO]** ISO NTSC 1.02 para
melee-sim-light/melee-brute/Dolphin, **[GPU]** GPU de ≥ 24 GB.

| Puerta | Trabajo | Recurso | Pasa si | Si falla |
|---|---|---|---|---|
| G0 Congelar | este plan + `preregistration.json`; esquema de observación único (A6); envoltorio `RT-strict` y trazas probados con agente sintético en bucle falso (A7 §5) | [local] | esquema, calendario y análisis versionados con hash; envoltorio registra los 11 campos temporales | no se avanza |
| G1 Throughput GPU (contraejemplo X1) | medir transiciones/s de política+dinámica fusionadas (MLP/GRU 1–5M, batch 4k–64k, CUDA graphs, sincronizando) con datos sintéticos | [GPU] sin ISO | H12: ≥ 10× la granja documentada (Faynt farm 6.337 frames/s con 8 procesos, DOC) por coste | si < 10×, W2 baja a E4 opcional |
| G2 Diagnóstico offline | parseo .slp (esquema A6, LAST) de ≥ 1k partidas; W0-S, W1-L, q (BC del rival) y V̂ en replays; probes E1/E1-S; I_full vs I_human; **error de «predecir el presente» bajo demora D∈{0,6,18}** con q vs marginal | [datos], CPU suficiente para ≤ 1M y ≤ 100 partidas; [GPU] para 1k+ | W0-S bate persistencia y acciones barajadas en eventos a h∈{4,8} por el umbral *[piloto]*; q mejora NLL del rival sobre la marginal; V̂ calibrado (ECE ≤ umbral) | predictor que no pasa no se despliega en MPC (06 E2); se puede seguir con el otro |
| G3 Simulador y panel contrafactual | `python -m melee_brute bench` en el hardware destino; test de aliasing (H); panel C1 (≥ 2.000 raíces) con ramas M×K; **regret W vs S0 vs P0** (H7); S0-Vperm offline (H9 en panel) | [ISO] CPU | H7: regret_W < regret_P0 (IC95) | si regret_W ≥ regret_P0 → W no se despliega aunque S0 sea bueno |
| G4 Sombra en Dolphin | reproducir partidas del bench con simulador sombra vía flujo Slippi crudo; medir frames en sincronía y causa de divergencia; comprobar si el RNG por frame del flujo puede inyectarse por API pública | [ISO] | H5 | si < 95 %: el nicho Dolphin existe y se programa H6 |
| G5 S0-ceiling | H1, H8, H9 en sim `untimed`, checkpoint fijo (Faynt-Expert o B0), ≥ 400 partidas/brazo, margen de stocks primario | [ISO] CPU (≈ 200 h·núcleo, INF) | H1 positiva | equivalencia → cerrar W0/W1-MPC en ese evaluador; redirigir a S-teach/W2 |
| G6 MPC aprendido | H2, H3 en sim `untimed`; luego Dolphin `RT-slow` y `RT-strict` (H10) | [ISO] + CPU/[GPU] | H2 (y H10 para afirmar RT) | si solo en `untimed`, afirmación acotada a ese reloj |
| G7 Recetas | B0, B1, E0b, E1, E2, E1-S con ≥ 5 semillas (más si σ_s del piloto lo exige) | [ISO]+[GPU] | H4 | atribuir solo lo que pase |
| G8 Imaginación | W2 vs E1/E2 (H11), solo si G1 y G2 pasan | [ISO]+[GPU] | H11 | — |
| G9 Extensión | H6 post-divergencia, H0, rivales/escenarios fuera de piloto | [ISO]+[GPU] | preregistro propio | — |

Orden de coste: G0 < G1 (horas de GPU, sin ISO) < G2 (datos) < G3 (ISO, minutos de simulador) < G4 < G5 (~1 día
de CPU) < G6 < G7 (días de GPU × semillas) < G8. G1 y G2 no dependen de la ISO; G3 es el experimento de mayor
reducción de incertidumbre por coste una vez hay ISO (ver `evidence_gaps.json`).

### Ejecutable hoy (sin ISO, sin GPU)
Solo G0: congelar el plan, el esquema y el calendario; probar el envoltorio de plazo con un agente sintético;
ampliar el banco de coste de A7 a las arquitecturas finales (incluido transformer con KV-cache en CPU); y,
con permiso para instalar `peppi_py` en un venv propio, un humo de G2 con ≤ 100 partidas y modelos ≤ 1M (37 h por
época de 1k partidas para MLP-1M según A7, así que en esta máquina G2 solo es humo).

### Requiere ISO
G3–G9 (simulador, Dolphin, cualquier partida, PPO, panel contrafactual con verdad exacta).

### Requiere GPU
G1 entera; G2 a escala ≥ 1k partidas; G7/G8; cualquier W1-L transformer de tamaño LeWM en tiempo real.

---

## 9. Criterios de parada global

- Puerta de adaptador o de fuga fallada (06 E1) → se detiene toda comparación que dependa de ella.
- Presupuesto agotado → se conservan resultados parciales y solo se analiza lo comparable.
- Comparación inválida por reloj o acceso (p. ej. S0 en `I_human`) → no se reporta como contraste.
- Si G5 da equivalencia y G1 da < 10×, la línea «dinámica aprendida» se cierra en sim y solo sigue H5/H6 en
  Dolphin y H4 (representación).
