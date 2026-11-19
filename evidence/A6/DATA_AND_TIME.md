# A6 — Datos y tiempo

Agente A6 · 2026-11-19 · Español. Etiquetas según el brief: DOCUMENTADO_POR_AUTOR (DOC), INSPECCIONADO_EN_CODIGO (CODE), INFERENCIA (INF), PROPUESTA (PROP), DESCONOCIDO (UNK). No descargué ningún dataset. Las cifras de tamaño vienen de la API de Hugging Face (`/api/datasets/<id>` y `/tree/<sha>?recursive=true`, paginado completo) y de cuatro ficheros pequeños de metadatos de HAL (`projection.json`, `selection.json`, `stats.json` y `val/index.json` de `ranked-anonymized-1`), más los primeros 3 KB del `manifest.jsonl` (petición por rango). Contratos: `timing_contract.json` y `split_plan.json`. Evidencia: `claims.jsonl`.

Revisiones inspeccionadas: slippi-ai `5ada33e90c6c87fe83a1fb2d1a8105a96fd7b05b`, libmelee (fork vladfi1) `bce21f09984b286e6d36bfd2939e4cd4691f94c2`, HAL `37045d974116405dd690efea6109a1d83a2da868`, MIMIC `3691f534194f9c2ec52f131c8ab96e3d8674c3fa`, melee-llm `7e179081c6cbab139d860c998b1452ad3dee047c`, melee-sim-light `eea7b5fbcd0243baf4c1956d52f3e1d0f536edc4`, SPEC de slippi-wiki `3a85ce8b1f2dae1b487b2529a43c80f5de5885a3`. El catálogo fija melee-llm en `2bf8b0eb…`. Con `git diff` comprobé que `docs/delay.md`, `train/meleebot/build_dataset.py` y `hal_mds.py` son idénticos entre esa revisión y HEAD.

---

## 1. Hallazgos principales (resumen)

1. **Alineación de filas (CODE, coincide en las cinco canalizaciones).** La fila `f` guarda el estado `PostFrame(f)` junto al mando `PreFrame(f)`, y ese mando ya actuó sobre el estado de su misma fila. Un objetivo de imitación sin fuga es el mando de `f+1` o posterior. MIMIC sufrió esta fuga: el modelo «leía la respuesta» desde `self_action` hasta que pasó a los shards v2 (CLAUDE.md:124-145).
2. **No hay acuerdo sobre qué copia de un frame repetido por rollback se usa (CODE).** slippi-ai y libmelee usan la **primera** copia (especulativa). HAL offline y melee-llm usan la **última** (la comprometida). HAL online ingiere la primera. Así, HAL entrena con datos comprometidos y juega con percepción especulativa. Para una dinámica, la secuencia de primeras copias no tiene por qué ser una trayectoria causal (INF).
3. **El RNG solo sobrevive en el .slp crudo (CODE).** Ningún formato derivado revisado guarda `random_seed`: HAL MDS, el parquet de slippi-ai, `frames.bin` de melee-llm y los shards de MIMIC. Tampoco guardan los ejes raw del stick. melee-sim-light exige ambas cosas para reproducir partidas y prohíbe reconstruir bytes raw a partir de floats procesados.
4. **HAL MDS es el corpus estructurado más grande y barato, pero pobre como estado de dinámica (DOC+CODE).** Tiene unos 1,3 M de partidas y 13,5 G frames en 172,5 GB (≈12,6 B/frame comprimido). Por jugador solo guarda posición, porcentaje, escudo, hitlag y un `state` empaquetado (acción, stock, saltos, hurtbox, aire, dirección). Le faltan velocidades, `action_state_frame`, hitstun, RNG, raw stick y frame_id explícito.
5. **El README de `erickfm/melee-ranked-replays` está desactualizado respecto a su propia revisión (DOC+CODE).** Habla de `ZELDA_SHEIK` y de `metadata/`. En `ef54ddc2` hay carpetas `SHEIK` y `ZELDA` separadas y no existe `metadata/`. Las notas de MIMIC del 2026-06-15 explican por qué: las carpetas estaban mal etiquetadas en a1/a2/a4/a5/a6 por mezclar IDs externos de peppi con valores de libmelee, se corrigió todo in situ y se borraron los metadatos. Las revisiones anteriores en el historial de HF siguen mal etiquetadas.
6. **No se puede separar por jugador en ranked anónimo (DOC).** Los nombres se sustituyen por el tier, y `code`, `timestamp` y `played_on` son null. Solo `pro/<player>` de HAL (38 jugadores) permite reservar jugadores, y aun así solo para el jugador de la carpeta.
7. **El split por defecto de slippi-ai mezcla perspectivas de una misma partida entre train y test (CODE).** Con `swap=True` (por defecto) genera las dos perspectivas antes de barajar y cortar (`data.py:559-583, 609`).
8. **Los dos corpus HF salen de la misma fuente**: los seis volcados anónimos de ranked de Fizzi. El nombre de archivo `{rank}-{rank}-{24hex}.slp` aparece en los dos, así que se pueden cruzar, pero ninguno sirve como test del otro (DOC+INF).

---

## 2. Inventario de datasets

### 2.1 `erickfm/melee-ranked-replays` @ `ef54ddc230e01373ff2a179b49a7e559af788081`

| Campo | Valor | Procedencia / etiqueta |
|---|---|---|
| Formato | `.slp` crudo en `tar.gz` por `(personaje, par de rangos, volcado aN)` | README (DOC) |
| Tamaño publicado | 936 ficheros, **1.429.763.661.491 B (1,43 TB)** | árbol HF paginado (CODE: suma propia) |
| `usedStorage` HF | 2.150.462.262.669 B (incluye historial previo a la corrección) | API (DOC) |
| Carpetas | 26: BOWSER … ZELDA, con SHEIK y ZELDA separadas; KIRBY tiene 34 tarballs y el resto 36 (6 rangos × 6 volcados) | árbol HF |
| Mayores / menores | FOX 301 GB, FALCO 244 GB, MARTH 154 GB, SHEIK 128 GB … PICHU 0,9 GB, KIRBY 1,9 GB | árbol HF |
| Nº de partidas | «~850k» (README); 850.005 filas de metadatos antes de borrarlas (MIMIC notes 2026-06-15) | DOC; sin verificar en esta revisión |
| Duplicación | Cada partida no-ditto está en las carpetas de ambos personajes («~90% duplication») | README (DOC) |
| Rango de habilidad | platinum+; 6 pares de rangos | README (DOC) |
| Identidad | anónima; el rango va en el nombre de archivo | README (DOC) |
| Fechas | no publicadas | UNK |
| Escenarios | sin filtrar en el empaquetado | CODE (`shard_and_upload_ranked.py` solo filtra 2 jugadores y personajes no legales) |
| Licencia | «MIT» declarada por quien redistribuye; los replays originales los publicó «la comunidad Slippi/ranked en forma anónima» | README. Los derechos del origen son UNK |
| Estado de etiquetas | En esta revisión el autor dice que las carpetas están verificadas («zero duplicates»); `metadata/` se borró y no se regeneró | MIMIC `docs/research-notes-2026-06-15.md` (DOC) |

### 2.2 `ericyuegu/hal-mds-dataset` @ `46ca723efd1de791c06300ed62c9278ecdb2f34a`

| Campo | Valor | Procedencia |
|---|---|---|
| Formato | MosaicML Streaming (MDS) con zstd; una fila por partida y columnas ndarray por frame | README, `index.json` (DOC) |
| Tamaño | 7.742 ficheros, **172.502.111.208 B**; MDS ranked 112,5 GB, MDS pro 58,4 GB, manifests 1,52 GB | árbol HF (suma propia) |
| Partidas | ranked 821.525 / 8.281 / 8.211 (train/val/test); pro 473.845 / 4.878 / 4.784 | README (DOC) |
| Frames | ranked ~8,9 G; pro ~4,6 G; ra-1: train 1.203.888.017, val 12.703.030, test 12.410.809 | README y `selection.json` (DOC) |
| Bytes/frame | ≈12,6 comprimido (112,5 GB / 8,9 G); **144,3 sin comprimir** (ra-1/val: 1.832.528.720 B raw frente a 161.113.342 B zstd, 12.703.030 frames) | cálculo propio sobre `index.json` |
| Filtro | 1v1 humano, 4 stocks, 6 escenarios legales, ≥1.500 frames, ≥3 muertes, ≥100% de daño hecho y recibido, cada jugador >50% | README y `selection.json` (DOC) |
| Discrepancia | El README dice «at most one cheap death per player», pero `selection.json` tiene `max_cheap_deaths: 2`. Puede ser semántica de «<» o un error | DOC, sin resolver |
| Procedencia del build | `git_sha 03c7a168…`, `git_dirty: true`, `source r2:hal/processed/...-v7`, artefacto `mds-policy-world-v8` | `selection.json` (DOC) |
| Campos | Ver §3.3. Por jugador y por Nana: `position_x/y`, `percent`, `shield`, `hitlag_left` (f32) y `state` (u32 empaquetado). Mandos: sticks int8 (rejilla 1/80), gatillos L/R uint8 (1/140), `buttons` uint8. 4 ranuras de ítem | `projection.json`, `policy_schema.py:14-70` (CODE) |
| Identidad | ranked: tier 1–3 y nombre «Diamond Player»; pro: rank 4 para el jugador de la carpeta y 0 para el rival; `player_codes.jsonl.gz` (11,4 MB) con connect codes | README (DOC) |
| Fechas | `timestamp: null`, `played_on: null` en el manifest ranked | manifest, cabecera (DOC) |
| Splits | por hash de 32 bits de la ruta (`mds_materialization.py:133-145`); las dos perspectivas siempre van juntas porque la fila es la partida | CODE |
| Licencia | `license: other` sin texto; el repo HAL no tiene LICENSE; «Melee is © Nintendo» | ficha y repo (DOC); términos UNK |
| Privacidad | `player_codes` contiene connect codes de Slippi de jugadores reales | DOC; tratarlo como dato personal |

### 2.3 Datos de slippi-ai / Phillip

- No hay dataset público enlazado. El README dice que Fizzi aportó «most of the imitation training data in the form of anonymized ranked collections (link in the Slippi discord)», más replays cedidos por jugadores (DOC, README:52-55). Tamaño, fechas y licencia: UNK.
- Formato: `slippi_db/parse_local.py` → un parquet comprimido con zlib por `.slp` (nombre = MD5), más `parsed.sqlite` y `meta.json`. El esquema SQLite tiene `start_at`, `played_on`, `match_id`, `match_game`, `p*_netplay_code`, `p*_netplay_suid` y `p*_name_tag` (`parse_local.py:43-87`, CODE). Con datos no anónimos permitiría splits por set y por jugador.
- Campos (`parse_peppi.py:46-119`): `percent` (convertido a **uint16**: pierde decimales), `facing`, `x`, `y`, `action`, `invulnerable`, `character`, `jumps_left`, `shield_strength`, `on_ground`, Nana, ítems, Randall y plataformas de FoD. Mandos: sticks procesados en [0,1], gatillo lógico único y **botones procesados**. Sin velocidades, sin hitstun, sin RNG.

---

## 3. Formato .slp y semántica pre-frame / post-frame

### 3.1 Orden dentro de un frame (DOC, SPEC `3a85ce8b`)

`FrameStart(f)` (seed del RNG, 2.2.0+) → `PreFrame(f, puerto)` («right before controller inputs are used to figure out the character's next action») → el motor procesa el frame → `PostFrame(f, puerto)` («at the end of the Collision detection») → `ItemUpdate(f)` (máximo 15) → `FrameBookend(f, latest_finalized_frame)` (3.7.0+). Los frames empiezan en −123, y en el 0 arranca el temporizador. `Major Scene = 0x8` marca una partida online «(has rollbacks)».

Tamaños útiles (calculados con las tablas de offsets del SPEC): PreFrame 67 B y PostFrame 85 B por personaje, FrameBookend 9 B y FrameStart ≥9 B. Sin ítems salen unos **326 B por frame en 1v1** (INF).

### 3.2 Cómo lo leen las cuatro canalizaciones

| Aspecto | libmelee `bce21f09` | slippi-ai `5ada33e9` | HAL `37045d97` | MIMIC `3691f534` | melee-llm `7e179081` |
|---|---|---|---|---|---|
| Parser | propio (`console.py`) | peppi-py | peppi-py | libmelee `Console(is_dolphin=False)` | peppi-py |
| Fila f | post(f) + pre(f) (`__pre_frame` / `__post_frame`, 1145-1230) | igual | igual | igual | igual |
| Rollback | descarta el frame si `frame <= último` → **primera copia** (1058-1071) | `RollbackMode.FIRST` (parse_peppi 168-170) | **última** (`wire.dedupe_keep_idx`, 77-83); online, primera (docs/inference 100-102) | hereda la primera de libmelee («~2% of frames», notes 10-23:45-46) | **última** y exige frames contiguos (72-77) |
| Countdown | se devuelve | se conserva | se conserva desde −123 | — | se descarta (`uniq>=0`) |
| Botones | físicos (0x31, u16) y procesados (0x2D, u32) | procesados | físicos | ambos vía libmelee | físicos |
| Sticks | procesados, x/2+0,5 (1166-1172); `raw_main_stick` | procesados en [0,1] | procesados en [−1,1], int8 ×80 exacto | — | procesados ×80 redondeado |
| Gatillos | lógico único, copiado a L y R | lógico único | físicos L/R ×140 con deadzone 43/140 (wire.py:164) | — | físicos L/R ×140 |
| Objetivo de imitación | — | estado t, última acción t+D, predice t+D+1 (data.py:267-327) | contexto [cs−L, cs), bloque [cs, cs+L_chunk) | v2: target[i] = inputs[i+1], reaction_delay = 0 | f+1 o posterior |
| RNG | no lo lee | no | no | no | no |

**Off-by-one conocidos.** (a) MIMIC: con los shards antiguos y `reaction_delay=0` el modelo copiaba la acción desde el estado de la misma fila. Con los v2 la combinación correcta es `reaction_delay=0`, y añadir 1 desplazaría dos veces (CLAUDE.md:124-145). Sus notas del 2026-04-11 dicen lo contrario («Training used REACTION_DELAY=1… Fix: --reaction-delay 0 --controller-offset»), así que el historial interno se contradice y vale la regla vigente de CLAUDE.md. (b) El delay de slippi-ai se cuenta **además** del +1 natural: con D=0 se predice t+1.

**Botones mantenidos o pulsados (CODE+INF).** Slippi registra el estado mantenido en cada frame. La pulsación es un flanco derivado (`pressed[1:] = ~b[:-1] & b[1:]`, HAL conversions.py:557). El motor calcula flancos y temporizadores de stick a partir de su historial: melee-sim-light restaura las entradas «before input edges/timers» (VALIDATION.md:157-162). Por tanto post(f) no es un estado de Markov para la dinámica. Hacen falta como mínimo el mando de f−1 y una historia corta de sticks (INF).

**Cuantización (CODE).** Los sticks procesados caen en la rejilla 1/80, y HAL falla si un valor no es exacto (`policy_schema.py:142-154`). Los gatillos físicos caen en la rejilla 1/140. libmelee pasa a [0,1] con un float, lo que es exacto en binario para k/160. melee-llm usa float16 en velocidades, porcentaje y escudo, con pérdida (≈0,25 de resolución a 300 %). slippi-ai trunca el porcentaje a entero.

**RNG y semilla (DOC).** La semilla aparece en `GameStart` 0x13D (antes de la partida), en `FrameStart` 0x5 y en `PreFrame` 0x7. El simulador la recibe por partida (`MslMatchConfig.random_seed`), pero su validación «supplies recorded RNG observations… does not establish an unseeded rollout». Reproducir un replay en el simulador exige el .slp crudo.

### 3.3 Decodificación del `state` de HAL MDS (CODE, `policy_schema.py:50-58`)

`action` ocupa los bits 0-16 (17 bits, centinela 65536), `stock` los bits 17-19, `jumps_used` los 20-23, `hurtbox_state` los 24-25, `airborne` los 26-27 y `direction` los 28-29 (−1→0, 0→1, +1→2). El README lo describe solo como «Action state», lo cual se queda corto.

---

## 4. Demoras: dónde entra cada una

Convención propuesta (PROP, detalle en `timing_contract.json`): **frame_aplicación = frame_observación + 1 + D_total**, con D_total = D_reacción + D_transporte + D_cómputo_consumido.

| Fuente | Modelo de retraso | Dónde entra | Etiqueta |
|---|---|---|---|
| Firoiu, Ju y Tenenbaum 2018 (arXiv 1810.07286v1) | Cola de longitud d en pasos de agente. Cada paso abarca f frames, así que la reacción es d·f frames más (f−1)/2 de media (§4.2). La cola se pasa al agente (estado aumentado, §3.1). El modelo predictivo P(s, a) se despliega p pasos con las acciones pendientes y la política actúa sobre s_{t,p} (§4.2). El retorno se toma desde t+d y el crítico ve el estado real s_{t+d} (§4.3) | salida del agente | DOC |
| — referencias de reacción | «12 frames … lowest human-plausible»; ~15 frames ≈ 250 ms de media (§2) | — | DOC |
| — resultados contra «Professor Pro» | (6,0,2): 0-6; (6,6,2): 3-5; (7,7,2): 2-5 (Tabla 1). Con (9,9,2) no llegaba a tiempo real (§5.1). El modelo ignora al rival (§5.2) | — | DOC (atribuido a los autores) |
| slippi-ai | D en frames, múltiplo de frame_skip (jax/policies.py:70-72). Entrena con el estado t, la acción comprometida t+D y el objetivo t+D+1. En vivo, cola de `policy.delay − console_delay` acciones neutras (eval_lib.py:129-140). El ejemplo RL usa D=18 (`rl_example.sh`). Oculta al agente la dirección de tech del rival durante 2-9 frames según el personaje (observations.py:68-140) | cola de salida + buffer de consola; máscara de observación | CODE |
| HAL | Sin delay en el entrenamiento. Predice bloques de acciones. En vivo, `FrameTiming` define physical_delay 0/2/3, allowance 1 en netplay, prefijo fijo d+1, replan 4 y horizonte 8. Un objetivo t es aceptable si t ≥ f + physical_delay + 1 (docs/inference.md:68-90) | consola/netplay + cómputo | DOC |
| MIMIC | reaction_delay = 0 con shards v2 (train.py:62); el desplazamiento de +1 va incorporado en los datos | datos | CODE |
| melee-llm (delay.md) | Igual que slippi-ai. Sus mediciones propias (HAL pierde fuerza con 3-10 frames de delay; E16, E22) son DOC del autor, no reproducidas | — | DOC |

Equivalencia: la demora de acción y la de observación se suman y son intercambiables (melee-llm §1). Aun así hay que registrarlas por separado, porque el adaptador implementa una u otra (PROP).

---

## 5. Esquema de transición para dinámica conjunta (PROP)

- **x_f** = post(f) de ambos puertos, más ítems y dinámica del escenario. Campos mínimos: posición, velocidades (3.5.0+), dirección, porcentaje, escudo, stocks, acción, `action_state_frame`, hitstun (con su flag), hitlag (3.8.0+), aire, saltos, hurtbox, más ítems y escenario.
- **u_f** = PreFrame(f) de **ambos** puertos (raw si existe, procesado y físico).
- **Transición**: (x_{f−k..f−1}, u_{f−k..f}) → x_f. El mando de f−1 entra siempre por los flancos. Con frame_skip k se guardan los k mandos, nunca solo el último.
- **Metadatos por transición**: `source_game_id` (sha1), `source_revision` (dataset@sha, parser@sha, rollback_mode = LAST), `frame_id`, `n_rollback_copies`, `terminated` (GAME!/TIME!), `truncated` (fin de ventana), `invalid_reason` (No Contest, LRAS, frames no contiguos).
- **Niveles**: los mandos del rival son `training_metadata`. El RNG es `simulator_snapshot`. En `observation` solo entra la cola de acciones propias ya comprometidas.
- **Qué fuente alimenta qué**: HAL MDS sirve para un prototipo de dinámica parcial, y hay que derivar velocidades por diferencias, lo que es impreciso en hitlag y en transiciones. El esquema completo exige reparsear .slp crudo con peppi (estilo melee-llm `build_dataset.py`), añadiendo RNG, raw stick y `n_copies`.

---

## 6. Splits, deduplicación y qué generalización queda reservada

Detalle en `split_plan.json`. En resumen:

1. Identidad de partida = sha1 del .slp. Se deduplica entre carpetas de personaje (MRR), entre carpetas pro (HAL deduplica solo dentro de cada jugador: `professional_replays.py:95-113, 415`) y entre fuentes. Después se buscan casi-duplicados.
2. Una fila por partida con ambos puertos. Las perspectivas, el intercambio de puertos, el espejo y las ventanas se generan **después** de asignar el split.
3. Qué reserva cada nivel:
   - `S_game` reserva partidas no vistas de la misma población. No reserva jugadores, sets ni épocas.
   - Sets: en ranked no se pueden agrupar, por falta de match_id, códigos y fechas. Quedan fugas por set (INF).
   - Jugador: solo es posible con `pro/` y solo para el jugador de la carpeta. El rival suele ser desconocido (rank 0). Los splits de HAL en pro son por partida, no por jugador, y HAL condiciona en identidad.
   - Tiempo: no hay fechas. Como proxy se puede usar `slp_version`, controlando por los campos que cada versión incluye.
   - OOD estructural: reservar un matchup o un escenario.
4. Contaminación: si se usan pesos de HAL o de Phillip como baseline o encoder, hay que evaluar en partidas que no vieron. No está verificado qué splits entrenaron los pesos publicados (UNK).

---

## 7. Cobertura de acciones y contrafactuales fuera de distribución

- Los replays contienen solo las acciones humanas elegidas (más las especulativas, si se usa FIRST). Un planificador que puntúa candidatos consulta pares (estado, acción) sin soporte. Firoiu §5.1 ya avisa de que la búsqueda «is likely to exploit flaws in the model» (DOC).
- Medida propuesta (PROP), en dos partes. Primera, para cada (personaje, acción, aire/suelo), el histograma de la clase de mando cuantizado del frame siguiente. Se toman las clases de HAL o MIMIC (por ejemplo 37 clusters de stick y 7 combinaciones de botones, en `tools/meta` de MIMIC) y se reporta la fracción de candidatos del planificador con un soporte mayor que un umbral N. Segunda, la discrepancia de un ensemble de dinámicas sobre los candidatos como señal de incertidumbre. **No calculé estas coberturas:** no hay datos locales.
- Comprobación obligatoria antes de atribuirle una ventaja al planificador: evaluar los errores de predicción sobre acciones contrafactuales con verdad de referencia del simulador (sección 8). La pérdida en replays humanos no mide esto.

## 8. Generar datos con el simulador (melee-brute / melee-sim-light)

- **Capacidad (DOC):** «exact equivalence to Melee's engine», 120-124 k FPS por núcleo en un Ryzen 9 9950X3D (README), semilla por partida, entradas raw (por ejemplo `main_x = 80`), save/restore y, en melee-brute, take-back exacto. Requiere extraer datos de una ISO NTSC 1.02, **que esta máquina no tiene**: no se puede generar nada en local.
- **Ventaja para contrafactuales:** desde un estado del simulador se pueden ramificar acciones arbitrarias con verdad exacta, es decir, cobertura a demanda.
- **Cambio de dominio respecto a los replays humanos (INF):**
  1. La distribución de entradas viene de bots o de exploración, no de humanos: distinta frecuencia de técnicas y de neutral.
  2. Los estados iniciales no se pueden tomar de replays. Un replay no restaura la memoria completa (faltan RNG en los formatos derivados, temporizadores de entrada y bytes no inicializados), y el simulador no restaura estado desde post-frames: su carril de validación «never restores position, action, damage or velocity».
  3. No hay rollback ni jitter de netplay.
  4. Reglas fijas: UCF, Stadium congelado, sin ítems aleatorios. Los replays ranked pueden diferir.
  5. Las diferencias de reproducción conocidas por el autor son redondeos históricos, raw ausentes y bytes no inicializados.
- **Combinación propuesta (PROP):** preentrenar con replays (distribución humana de estados) y calibrar o ampliar con ramificaciones del simulador desde estados alcanzados por políticas de imitación, dejando un conjunto de test contrafactual verificado por simulador. Reportar los dos dominios por separado.

## 9. Estimación de tamaño para un corpus piloto (ESTIMACIÓN, INF)

Supuestos:
- Partida media ranked HAL: 8,9 G frames / 838.017 partidas ≈ **10.620 frames**, countdown incluido. En pro: 4,6 G / 483.507 ≈ 9.510.
- Sin Ice Climbers (las columnas de Nana van vacías).
- La ratio de compresión de HAL (144→12,6 B, ≈11×) es específica de su esquema. Para un esquema con velocidades asumo entre 5× y 10×, sin medirlo.

| Formato | B/frame (partida, ambos puertos) | 1k partidas | 10k partidas | Base |
|---|---|---|---|---|
| HAL MDS zstd (medido) | 12,7 | **≈136 MB** (ra-1/val: 1.189 partidas = 161 MB) | ≈1,36 GB | medido en `index.json` |
| HAL MDS decodificado | 144,3 | ≈1,5 GB | ≈15 GB | medido |
| melee-llm `frames.bin` (84 B por perspectiva; guarda las 2) | 168 (84 con una sola perspectiva) | ≈1,8 GB (0,9 con una) | ≈18 GB (8,9 con una) | dtype de `schema.py` (34+34+8+8 B) |
| Esquema A6 completo sin ítems (2×56 B + 10 B de cabecera con frame_id, seed, n_copies y finalized) | ≈122 | ≈1,3 GB raw; 0,13–0,26 GB zstd | ≈13 GB raw; 1,3–2,6 GB zstd | PROP + supuesto de compresión |
| Esquema A6 con 4 ranuras de ítem densas (+81 B) | ≈203 | ≈2,2 GB raw; 0,2–0,43 GB zstd | ≈21,5 GB raw; 2,2–4,3 GB zstd | ídem |
| .slp crudo (≈326 B/frame más ítems) | ≈330+ | ≈3,5 GB extraído; ≈0,9 GB en tar.gz | ≈35 GB; ≈9 GB | SPEC; MRR 1,43 TB / (850k × ~1,9) ≈ 0,89 MB por partida |

Conclusiones con ~8 GB libres, el tope de 300 MB por agente y ~1 GB de RAM:
- El piloto de 1k partidas solo cabe **comprimido y leído en streaming**. P1k = HAL ra-1/val (161 MB) cabe en disco pero no decodificado en RAM, porque 1,5 GB supera el tope.
- Un corpus de 10k partidas en esquema completo (1,3–4,3 GB zstd) cabe en disco, pero no junto con los .slp de origen (unos 9 GB en tar.gz). Habría que convertir tarball a tarball y borrar cada .slp después.
- Guardar las dos perspectivas duplica el tamaño sin aportar información.

## 10. Licencias por componente

| Componente | Licencia | Etiqueta |
|---|---|---|
| melee-ranked-replays | MIT declarada; origen «published by the Slippi/ranked community in anonymized form» | DOC; derechos de origen UNK |
| hal-mds-dataset | `other` sin texto; incluye connect codes de jugadores reales | DOC; términos UNK; privacidad |
| Melee (juego, ISO, datos del motor) | © Nintendo / HAL Laboratory | DOC (ficha HAL) |
| slippi-ai | MIT | CODE (LICENSE) |
| libmelee (fork) | LGPL-3.0 | CODE (LICENSE.txt) |
| MIMIC | MIT | CODE (LICENSE) |
| HAL, melee-llm, melee-sim-light, melee-brute | sin fichero LICENSE en las revisiones clonadas | CODE (ausencia); UNK |
| Datos de slippi-ai | no publicados; vía Discord de Slippi | DOC; UNK |

## 11. Dudas abiertas y bloqueos para otros roles

- **A1:** decidir FIRST frente a LAST para el adaptador en vivo y para los datos (yo propongo LAST para la dinámica y FIRST como vista de evaluación). Decidir también si el ActionSpec lleva sticks raw o procesados. Integrar `timing_contract.json`.
- **A3/A4/A5:** el estado de HAL MDS no contiene velocidades ni temporizadores. Una dinámica entrenada solo con él tendrá un error irreducible en hitlag, hitstun y knockback. Hay que decidir si se reparsea .slp crudo.
- **A7:** usar las cifras de la §9. La lectura de MDS exige el paquete `mosaicml-streaming`, que no comprobé si está instalado.
- **A8:** ninguna separación por jugador es posible en ranked. Hay fugas por set y el origen es común a los dos corpus. El split por defecto de slippi-ai no es válido para test.
- Sin verificar: el nº de partidas de MRR en esta revisión, la proporción de dittos (y por tanto la duplicación real), qué puerto es local en los replays ranked (afecta a la calidad de las copias especulativas), los splits que entrenaron `hal-base-250m-rc` y la frecuencia real de rollback en el corpus (MIMIC dice ~2% en sus replays).
