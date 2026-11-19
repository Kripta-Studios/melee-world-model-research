# A3 — Representaciones JEPA para Melee (estado estructurado)

Agente A3 · 2026-11-19 · Escribe solo en `evidence/A3/`. Etiquetas: DOC = DOCUMENTADO_POR_AUTOR, CÓD = INSPECCIONADO_EN_CODIGO, REP = REPRODUCIDO (local_check propio), INF = INFERENCIA, PROP = PROPUESTA, DESC = DESCONOCIDO. IDs de afirmación entre corchetes → `claims.jsonl`.

Revisiones inspeccionadas (HEAD de `ops/clone_inventory.txt`):

| Repo | SHA | Licencia del código (archivo LICENSE) |
|---|---|---|
| galilai-group/lejepa | `c293d291ca87cd4fddee9d3fffe4e914c7272052` | **CC BY-NC 4.0** |
| lucas-maes/le-wm | `8edfeb336732b5f3ce7b8b210d0ba370a09e2cac` | MIT |
| facebookresearch/ijepa | `52c1ae95d05f743e000e8f10a1f3a79b10cff048` | **CC BY-NC 4.0** |
| facebookresearch/vjepa2 | `204698b45b3712590f06245fbfba32d3be539812` | MIT (+3 archivos Apache-2.0) |
| MLO-lab/LeVJEPA | `a748e0fbaa0ec548cad283978b818779708a3bd7` | MIT (pesos HF: CC BY-NC 4.0) |
| facebookresearch/jepa-wms | `13cf1d9c7e476f53c17714d2e0f1dc239a883ce0` | **CC BY-NC 4.0** |

Papers leídos vía arxiv.org/html o /abs: 2511.08544v3 (LeJEPA), 2603.19312v3 (LeWM), 2506.09985v1 (V-JEPA 2/2-AC), 2301.08243 (I-JEPA, abs), 2603.14482 (V-JEPA 2.1, abs), 2608.27395 (LeVJEPA, abs), 2512.24497 (JEPA-WMs, abs). Lectura parcial donde se indica.

---

## Resumen ejecutivo (decisiones)

1. **SIGReg es un test de normalidad de Epps–Pulley aplicado a M proyecciones 1-D aleatorias del batch de embeddings**, promediado sobre proyecciones (y sobre pasos temporales o vistas). Penaliza que la distribución *marginal del batch* se aleje de N(0, I). Impide el colapso completo y el dimensional; **no garantiza que el embedding contenga ninguna variable concreta**. Un embedding de ruido puro independiente de la entrada obtiene la misma puntuación que uno perfecto (REP, C4). Lo que se conserva lo decide el término predictivo/de invariancia, no SIGReg.
2. **Solo LeWM aprende la representación con un objetivo temporal condicionado a acciones.** En I-JEPA, LeJEPA, V-JEPA 2, V-JEPA 2.1 y LeVJEPA el objetivo de representación no es temporal (enmascarado espacial o espacio-temporal, o invariancia entre vistas). En V-JEPA 2-AC y JEPA-WMs la dinámica se entrena **sobre un encoder congelado**. LeVJEPA no predice el futuro: es invariancia multi-crop sobre un clip con atención causal.
3. **Con estado estructurado, un JEPA no temporal tiene poca justificación a priori.** El estado de libmelee ya es una descripción compacta y casi suficiente del frame. Las "vistas" con sentido son ventanas temporales y el objetivo con sentido es J-T: predecir el embedding de t+k desde la historia, más acciones propias y del rival registradas. Las vistas por aumento clásico (espejo, jitter de fase, recortes temporales, intercambio de jugadores) inducirían **invariancias que borran información de control** (orientación, frame exacto de animación, hitstun/hitlag). En un juguete, las vistas espejo bajan el probe de facing a 0.69 y las de fase bajan el R² de la fase a 0.68 (REP, C5b). La simetría izquierda/derecha se trata por canonicalización, no por invariancia.
4. **B2 (encoder JEPA + BC/PPO) es un test de representación, no de modelo del mundo.** El predictor se descarta tras el preentrenamiento. El brazo de control decisivo es **E1-S**: la misma arquitectura preentrenada prediciendo el *siguiente estado estructurado explícito*. Si E1-S ≥ E1, la parte "latente/JEPA" no aporta nada en estado estructurado. Ablaciones en `ablations.json`.
5. **No hay pesos JEPA reutilizables para Melee-estado.** Todos los checkpoints publicados son encoders de píxeles (ImageNet, vídeo web, robótica) o modelos de entornos 2D/3D de control continuo. Lo reutilizable es *código pequeño*: `SIGReg`, `ARPredictor` y bloques AdaLN-zero de le-wm (MIT). La librería `lejepa` y los repos ijepa/jepa-wms son **no comerciales**.
6. **Tamaño de LeWM según los autores:** ~15M parámetros (encoder ViT-Tiny ~5M + predictor ~10M), D = 192, "un solo GPU en unas horas", sin modelo de GPU ni horas exactas. Mi recuento desde el código da ≈18M (predictor 10.79M exactos). Hay discrepancias paper↔config en λ, épocas e historia (§6).

---

## 1. SIGReg con precisión de implementación

### 1.1 Qué calcula (CÓD)

Implementaciones casi idénticas en tres repos:

- `le-wm/module.py:10-36` `SIGReg(knots=17, num_proj=1024)`; uso en `train.py:40` sobre `emb.transpose(0,1)` (forma T×B×D).
- `lejepa/univariate/epps_pulley.py:62-99` `EppsPulley(t_max=3, n_points=17)` + `lejepa/multivariate/slicing.py:91-153` `SlicingUnivariateTest(univariate_test, num_slices)`.
- `LeVJEPA/loss.py:4-42` `SIGReg(knots=17, num_proj=1024, normalize_by_n=False)`.
- `lejepa/MINIMAL.md:57-75` (versión de 130 líneas, 256 proyecciones, `device="cuda"` fijo).

Algoritmo por llamada:

1. `A = randn(D, M)` y se normaliza cada columna a norma 1. Son M direcciones nuevas en **cada** llamada.
   - le-wm y LeVJEPA usan el RNG global.
   - La librería usa un `torch.Generator` sembrado con `global_step`, sincronizado entre rangos (slicing.py:131-143).
2. Se proyecta: `x = proj @ A`, de forma (…, N, M).
3. Se calcula la función característica empírica en K = 17 nodos `t ∈ linspace(0, 3, 17)`: `mean_N cos(t·x)` y `mean_N sin(t·x)`.
4. Error frente a la función característica de N(0,1), φ(t) = e^{−t²/2}: `(mean cos − φ)² + (mean sin)²`.
5. Integral trapezoidal en [0, 3], con pesos ×2 por simetría (la mitad en los extremos) y ventana gaussiana `w(t) = e^{−t²/2}` (los pesos ya incluyen φ).
6. Se multiplica por N (el tamaño de batch, `proj.size(-2)`) y se promedia sobre proyecciones y sobre la dimensión externa (tiempo en LeWM, vistas en LeVJEPA/LeJEPA).

Precisiones y discrepancias detectadas:

- Fórmula del paper LeJEPA: `EP = N ∫ |φ̂_X(t) − φ(t)|² w(t) dt`, con w(t) = e^{−t²/σ²} y σ = 1 (DOC). El paper menciona 17 puntos en [−5, 5], pero el código integra en [0, 3] (CÓD vs DOC; los autores dicen que el dominio tiene impacto "despreciable").
- Mi chequeo C2 confirma que le-wm `SIGReg` y `lejepa` `EppsPulley` dan **el mismo valor** con las mismas direcciones (REP).
- **Bug en el README de lejepa:** `README.md:108` documenta `EppsPulley(num_points=17)`, pero la firma es `n_points` (`epps_pulley.py:62-64`). La llamada del README lanza `TypeError` (REP, C1).
- **le-wm no está preparado para DDP:** su `SIGReg` lleva el comentario "single-GPU!" y no hace all_reduce. En multi-GPU cada rango evaluaría su batch local con direcciones distintas.
  - LeVJEPA sí hace `broadcast(A)` y `all_reduce` de la función característica empírica (loss.py:25-35).
  - La librería hace all_reduce de las medias cos/sin (epps_pulley.py:91-93).

### 1.2 Hiperparámetros declarados y convenciones de λ (no comparables entre sí)

| Fuente | Pérdida total | λ | M (proyecciones) | Nodos |
|---|---|---|---|---|
| Paper LeJEPA (DOC) | pred + λ·SIGReg (recomendado) | 0.05 "robust default" | 1024 recomendado (512 competitivo) | 17 |
| MINIMAL.md:172-174, 218 (CÓD) | λ·SIGReg + (1−λ)·inv | 0.02 | 256 | 17 |
| le-wm `config/train/lewm.yaml:38-43` (CÓD) | pred + λ·SIGReg (`train.py:41`) | **0.09** | 1024 | 17 |
| Paper LeWM (DOC) | ídem | **0.1** (texto); barrido: >80 % éxito para λ∈[0.01, 0.2], pico ≈0.09, caída en 0.5 | 1024 (insensible) | 17 |
| LeVJEPA `configs/config.yaml:27` (CÓD) | inv + λ·SIGReg (`train.py:97`) | 0.06 | 1024 | 17 |

### 1.3 Coste computacional

- Análisis (CÓD): una matmul N×D×M más N·M·K evaluaciones de cos y de sin. El tensor intermedio mayor tiene N·M·K floats: N = 256, M = 1024, K = 17 → 17 MiB. El coste es lineal en N, D y M, como declara el paper (DOC: "linear in dimension and sample size").
- Medido en esta máquina (REP, C3): ver §7. Es despreciable frente a cualquier encoder.

### 1.4 Qué garantiza (DOC, paper LeJEPA §teoría; resultados asintóticos y bajo supuestos de regularidad)

- Por Cramér–Wold, si *todas* las proyecciones 1-D son N(0,1), la distribución conjunta es N(0, I). Con |A| = O(K) direcciones basta bajo suavidad Sobolev alta (Thm 5). El test tiene nivel y potencia asintóticos (Thm 2).
- Entre distribuciones con restricción de covarianza escalar, la gaussiana isotrópica minimiza el sesgo/varianza integrado de probes lineales, kNN y kernel en el peor caso sobre tareas (Lemas 1–2, Thm 1). Es una optimalidad *minimax sobre tareas desconocidas*, **no** para una tarea concreta.
- El gradiente está acotado, |∂EP/∂z_i| ≤ 4σ²/N (Thm 4). El estimador por minibatch tiene un sesgo O(1/N) (Thm 6).
- En la práctica, excluye el colapso completo (embedding constante) y el dimensional (rango bajo), y fija la escala a varianza unitaria por dirección. Los valores de C4 lo cuantifican (REP).

### 1.5 Qué NO garantiza

- **Contenido informativo (REP, C4).** SIGReg solo ve la distribución del batch. Un encoder que emite ruido gaussiano independiente de la entrada puntúa igual que uno ideal. Toda la información la aporta el término predictivo o de invariancia, y cualquier invariancia que este induzca se mantiene.
- **Variables discretas o de baja dimensión intrínseca (INF + REP C4).** Con D alto y direcciones aleatorias, una coordenada binaria (p. ej. `facing`) casi no altera las proyecciones (efecto TCL), así que SIGReg apenas la penaliza ni la protege. En cambio, *si* el estado tiene pocas dimensiones efectivas, el encoder debe "inventar" dimensiones para llenar N(0, I_D). Los autores de LeWM atribuyen a esto su peor resultado (Two-Room: "low intrinsic dimensionality", DOC). El estado de Melee es de dimensión moderada y muy categórico (acción ≈400 clases, booleanos, contadores enteros), un riesgo análogo que debe medirse con el barrido de D.
- **Sensibilidad a acciones, suavidad temporal o utilidad para control.** Nada de eso está en el objetivo.
- **Atajos sin stop-grad (INF).** En LeWM el gradiente pasa también por el embedding objetivo (`train.py:35-41`: `tgt_emb = emb[:, n_preds:]` sin `detach`). El encoder está incentivado a hacer predecible su propio embedding, y SIGReg solo impone varianza. En Melee la variabilidad causada por el rival es exógena al contexto si no se le dan las acciones del rival. El encoder podría entonces atenuar o "gaussianizar" justo la información del rival. Mitigación: condicionar P a las acciones de ambos jugadores en entrenamiento y comprobarlo con probes de campos del rival.
- **Precisión finita.** Los resultados son asintóticos. Con N = 128 el estadístico es ruidoso, y las direcciones cambian en cada paso.

### 1.6 Mecanismo anticolapso por método (CÓD salvo indicación)

| Método | Anticolapso | Localizador |
|---|---|---|
| I-JEPA | Target encoder **EMA** (0.996→1.0 lineal) + **stop-grad** (`torch.no_grad`) + layer_norm de targets + predictor estrecho (384 dim, profundidad 12); smooth-L1 | `ijepa/src/train.py:169,224-229,295-311,332-336`; `configs/in1k_vith14_ep300.yaml` (`ema: [0.996, 1.0]`, `pred_emb_dim: 384`) |
| V-JEPA 2 | EMA (0.99925 constante en ViT-L) + stop-grad + layer_norm; L1 (`loss_exp: 1.0`) | `vjepa2/app/vjepa/train.py:298-302,429-450,471-479`; `configs/train/vitl16/pretrain-256px-16f.yaml:40,87-89` |
| V-JEPA 2-AC | **Encoder congelado** (solo se usa `target_encoder` con `requires_grad=False`; el contexto también sale de él); el predictor aprende L1 teacher-forcing + rollout AR de 2 pasos | `app/vjepa_droid/train.py:276-278,408-449`; `configs/train/vitg16/droid-256px-8f.yaml` (`auto_steps: 2`, `context_encoder_key: target_encoder`) |
| V-JEPA 2.1 | EMA + stop-grad; targets de 4 niveles intermedios con layer_norm; pérdida densa también sobre tokens visibles (`predict_all`, λ_ctx = 0.5) | `app/vjepa_2_1/train.py:110-116,169-171,590-705,736-737`; `configs/train_2_1/vitl16/pretrain-256px-16f.yaml:41,112-113` |
| LeJEPA | **Solo SIGReg**; sin predictor (invarianza al centroide de las vistas globales), sin EMA ni stop-grad | `MINIMAL.md:172-174`; paper §3 (DOC) |
| LeWM | **Solo SIGReg** (λ = 0.09), extremo a extremo, sin stop-grad ni EMA; BatchNorm en el proyector; dropout 0.1 en el predictor | `le-wm/train.py:17-45`; `config/train/model/lewm.yaml:11-45` |
| LeVJEPA | SIGReg (λ = 0.06) + invariancia local→global; **la EMA (0.9998) solo sirve a la evaluación**, no entra en la pérdida; 95 % de tokens descartados | `LeVJEPA/train.py:79-102` (comentario L82); `configs/config.yaml:12-31` |
| JEPA-WMs / DINO-WM | Encoder preentrenado **congelado** (DINOv2/v3 o V-JEPA); 51 configs con `freeze_encoder: true` y 0 con `false` | `jepa-wms/app/vjepa_wm/utils.py:642-699`; `train.py:86` |
| PLDM (baseline en LeWM) | Estilo VICReg: 7 términos (var, cov, sus versiones temporales, IDM), 6 coeficientes | DOC, arXiv 2603.19312v3, ap. C.2 |

---

## 2. Separación: representación / predicción temporal / predicción condicionada a acciones

| Método | Objetivo de representación | ¿Predicción temporal? | ¿Condicionado a acciones? | Encoder durante la dinámica |
|---|---|---|---|---|
| I-JEPA | Predecir embeddings (EMA) de 4 bloques objetivo (15–20 % del área) desde 1 bloque de contexto (85–100 %) de la **misma imagen** | No | No | — |
| LeJEPA | Invariancia de cada vista al centroide de las vistas globales + SIGReg (2 globales 224 px, hasta 8 locales 96 px) | No | No | — |
| V-JEPA 2 | Predicción enmascarada en espacio de representación. `temporal_scale: [1.0, 1.0]` → las máscaras cubren **todo el eje temporal**: es inpainting espacio-temporal, **no** pronóstico del futuro (CÓD, `pretrain-256px-16f.yaml:49-66`) | No (en sentido de futuro) | No | — |
| V-JEPA 2-AC | Ninguno nuevo (usa V-JEPA 2 congelado) | Sí: siguiente frame latente, teacher forcing + rollout de 2 pasos | Sí: acción 7-D (Δ efector) + estado 7-D (DOC) | Congelado |
| V-JEPA 2.1 | Como V-JEPA 2 + pérdida densa sobre visibles + supervisión profunda multinivel | No | No en el preentrenamiento; los experimentos robóticos son posteriores (DOC, abs) | — |
| LeVJEPA | Invariancia de 4 crops locales al crop global del **mismo clip** (cada crop compartido por todos sus frames) + SIGReg; atención causal por bloques; un token de lectura por clip | **No**; la causalidad es arquitectónica | No | — |
| LeWM | **El único objetivo de representación es la predicción del siguiente embedding condicionada a acciones** + SIGReg | Sí: 1 paso (`num_preds: 1`), historia 3, teacher forcing en las 3 posiciones (`train.py:32-39`) | Sí: bloques de 5 acciones concatenadas (`frameskip: 5`, `train.py:68`) vía `Embedder` → AdaLN-zero | Entrenado conjuntamente |
| JEPA-WMs | Ninguno (encoder congelado) | Sí | Sí | Congelado |

Consecuencia (INF): para el brazo B2 el único precedente "JEPA temporal sin encoder congelado" es LeWM. Ahí la representación *es* un subproducto del modelo de dinámica. Usar ese encoder sin el predictor (B2) aísla el efecto de representación, pero el encoder heredó un sesgo hacia lo que es predecible dadas las acciones.

Detalle LeWM (CÓD):

- `JEPA.encode` usa **solo píxeles y acciones**; `proprio`/`state` se cargan y normalizan pero no entran al modelo (`jepa.py:29-45`; `config/train/data/pusht.yaml`).
- La representación es el token CLS del ViT seguido de un proyector MLP con BatchNorm.
- El coste de planificación es la MSE del último embedding predicho frente al embedding de la meta (`jepa.py:112-126`).
- El split train/val es `random_split` sobre **ventanas**, no sobre episodios (`train.py:73-76`). Para Melee esto sería fuga entre partidas; A6 y A8 lo deben evitar.

---

## 3. Transferencia a Melee con estado estructurado

### 3.1 Qué son las "vistas" sobre estado tabular/secuencial (INF/PROP)

Estado disponible por jugador (CÓD, `libmelee/melee/gamestate.py:111-160` @ `bce21f09…`): position, percent, shield_strength, is_powershield, stock, facing, action, action_frame, invulnerable, invulnerability_left, hitlag_left, hitstun_frames_left, jumps_left, on_ground, cinco velocidades, ECB, más el estado de Nana.

Aviso para A2/A6: el embedding por defecto de slippi-ai **no incluye** action_frame, hitlag ni hitstun (líneas comentadas en `slippi_ai/tf/embed.py:443,446,447` @ `5ada33e9…`), y las velocidades son opcionales (`with_speeds`).

| Familia de vistas | Qué invariancia induce | Valor esperado en Melee |
|---|---|---|
| **Ventanas temporales** (contexto x_{t−H+1..t} → objetivo z_{t+k}, con acciones) = J-T | Ninguna explícita; conserva lo predecible desde historia + acciones | **El único con sentido**: puede codificar variables latentes no observadas por frame (inercia de decisiones del rival, ventanas de RNG no visibles, momentum de la historia) |
| Enmascarado de campos o de un jugador (I-JEPA tabular) = J-M | Robustez a campos ausentes | Bajo: la mayoría de campos son deducibles o ya están en la entrada; útil como control negativo barato |
| Ruido gaussiano en continuos | Invariancia a precisión fina de posición | Peligroso si la escala supera las tolerancias de juego (espaciado, borde, ledge) |
| **Espejo izquierda/derecha** | Borra `facing`, el signo de x y vx | **Prohibido como invariancia**; usar canonicalización equivariante |
| Jitter de fase / frames vecinos como "misma vista" | Borra action_frame exacto (ventanas de punish, IASA, L-cancel) | **Prohibido** |
| Recortes temporales del mismo clip (estilo LeVJEPA) | Invariancia a la posición en el clip → borra contadores (hitstun/hitlag/invuln) | **Prohibido** |
| Intercambio de puertos/jugadores | Borra quién es "yo" | **Prohibido** |
| Invariancia a personaje | Borra frame data específica | Prohibido salvo que se condicione explícitamente |

**Respuesta:** un JEPA no temporal sobre un estado que ya es casi suficiente se reduce a reparametrizar la entrada. Su único beneficio plausible es un embedding suave de los categóricos, que BC ya aprende. El JEPA con sentido es el temporal (J-T), y aun así su rival natural es **predecir el siguiente estado estructurado explícito (S-T)**, que en estado bajo-dimensional no necesita latente ni anticolapso. Que J-T supere a S-T es la hipótesis a falsar (PROP; brazo E1-S).

### 3.2 Información crítica para control y cómo detectar su pérdida (PROP)

Probes sobre el encoder congelado, con dos referencias siempre:

- **techo**: el mismo probe sobre la entrada cruda (≈ perfecto si el campo está en la entrada);
- **suelo**: un encoder aleatorio de la misma arquitectura.

Cada probe se evalúa en lineal y en MLP 1×256, y en test por partida con intervalo bootstrap por partida.

| Campo | Métrica | Umbral de rechazo sugerido |
|---|---|---|
| facing (ambos) | accuracy | < techo − 0.5 pp |
| action (~400 clases) | top-1 balanceada | < techo − 2 pp |
| action_frame | exact-match por acción, MAE | exact < techo − 5 pp |
| hitlag_left, hitstun_frames_left | exact-match, MAE | MAE > 1 frame |
| invulnerability_left | MAE | > 1 frame |
| shield_strength | R², accuracy de umbral (< 15) | R² < 0.95 |
| on_ground, jumps_left, contacto con borde | accuracy | < techo − 1 pp |
| dx/dy relativos y distancia al borde | R², error en unidades | — |
| percent, stock | R² / accuracy | — |

Probes complementarios:

- **Pares mínimos:** estados que difieren en un solo campo (facing; action_frame ±1; hitstun 0 vs 1; escudo 14 vs 16). Se mide `‖z − z′‖ / dispersión media`. Un ratio ≈0 indica una invariancia aprendida.
- **Probes futuros:** campos en t+1, t+4 y t+12 desde z_t. Miden información dinámica, *no* validan control (una pérdida predictiva baja no demuestra ventaja jugando).

Evidencia de juguete (REP, C5/C5b, §7): entrenar el objetivo LeJEPA de MINIMAL.md sobre un estado sintético con vistas "espejo" hace que z(s) ≈ z(espejo(s)) (ratio de distancias 0.05) y que el probe lineal de `facing` baje a 0.69. Con vistas de "jitter de fase", el R² de la fase baja a 0.68. Con solo ruido pequeño ambos se conservan (1.00 / 0.98). Con entrenamiento corto, los probes lineales todavía no detectaban la pérdida; de ahí el test de pares mínimos. Es un juguete: muestra el mecanismo, no magnitudes para Melee.

---

## 4. Encoder congelado vs ajustado vs conjunto, y el control B2 (PROP)

Diseño completo en `ablations.json`. Lo esencial:

**Invariantes comunes a todos los brazos:**

- el mismo corpus offline, con split por partida antes de ventanear;
- el preentrenamiento usa **solo** frames del split de entrenamiento BC;
- la misma entrada, la misma canonicalización, la misma arquitectura de encoder E y la misma dimensión D;
- la misma cabeza y receta BC/PPO, los mismos frames PPO, rivales y semillas de partida.

**Sin dinámica en inferencia:** el predictor P se descarta, y se verifica contando los parámetros del forward exportado.

**Brazos mínimos:**

| Brazo | Qué es | Qué aísla |
|---|---|---|
| E0 | B1: E aleatorio entrenado con BC/PPO | Línea base |
| E0b | E0 con pasos extra de BC equivalentes al cómputo de preentrenamiento | Cómputo frente a objetivo |
| E1 | E preentrenado con J-T, congelado | Representación sin adaptación |
| E2 | E preentrenado con J-T, ajustado (LR del encoder ≈ 0.1× la de la cabeza) | Valor de la inicialización |
| E1-S | E preentrenado prediciendo el siguiente estado explícito | Control decisivo: ¿aporta la parte latente/JEPA? |

**Brazos adicionales:**

- E-rand-frozen: suelo de features aleatorias.
- E3: pérdida J-T auxiliar *simultánea* a BC. Es la "pérdida auxiliar temporal declarada" que exige el MASTER_PROMPT; se reporta aparte y no cuenta como B2.
- E1-noact: valor de condicionar a acciones.
- E1-ema: SIGReg frente a EMA/stop-grad.
- E1-M: control no temporal.

**Barridos:** λ ∈ {0.01, 0.03, 0.09, 0.2, 0.5} y D ∈ {64, 128, 192, 256}. Se seleccionan con probes en validación, **antes** de PPO.

**Interpretación:**

- Si E1/E2 > E0 y E0b en fuerza de juego, con intervalo por partida que excluye 0, y E1 ≥ E1-S, se atribuye el efecto a la representación JEPA *en esta comparación*.
- Si solo mejoran los probes, la conclusión es "representación informativa sin beneficio de control".

**Contrato con A4/A5 (PROP):** `encoder.encode(history) → z ∈ R^D` (D a fijar por barrido; 192 es el valor LeWM). Si A4 usa el mismo E para la dinámica latente (W1/W2), la inicialización común es E1 o E2. Hay que fijar si E se actualiza en W2 (06_EXPERIMENT_PROTOCOL.md L29).

---

## 5. Qué es reutilizable (código, pesos, licencias)

| Recurso | Reutilizable para Melee-estado | Razón |
|---|---|---|
| le-wm `module.py` (`SIGReg`, `ARPredictor`, `ConditionalBlock` AdaLN-zero, `Embedder`, `MLP`) y la lógica de pérdida de `train.py:17-45` — **MIT** | **Sí (código)** | Agnóstico a la modalidad: basta sustituir el ViT por un encoder de estado. Dependencias: einops y, para entrenar, stable-pretraining/stable-worldmodel/lightning (no instalados aquí) |
| LeVJEPA `loss.py` `SIGReg` — **MIT** | Sí (código) | La única versión con DDP correcto (broadcast + all_reduce) |
| Librería `lejepa` (otros tests univariantes, slicing) — **CC BY-NC 4.0** | Solo uso no comercial; preferir las copias MIT | Además, la API del README es errónea (C1) |
| ijepa — CC BY-NC 4.0 | Solo como referencia | Enmascarado espacial de imágenes; nada específico de estado |
| vjepa2 (MIT): código de pérdida AC (teacher forcing + rollout AR) | Como **diseño** de pérdida para A4 | El código está muy acoplado a vídeo y tubelets. La licencia de los *pesos* no consta en el README (DESC) |
| jepa-wms — CC BY-NC 4.0 | Referencia de ablaciones (planificador, predictor) | Encoders congelados de píxeles; datos y pesos robóticos |
| Pesos LeWM (HF `quentinll/lewm-*`, MIT según la ficha) | **No** | Push-T/Cube/TwoRoom/Reacher: píxeles 224 px y acciones continuas de otra semántica |
| Pesos V-JEPA 2 (300M–1B), 2.1 (80M–2B), 2-AC (ViT-g, Franka) | **No** para estado; dudosos incluso para píxeles | Dominio (vídeo web/robot), tamaño incompatible con 16.67 ms/frame en CPU (A7), acción robótica 7-D |
| LeVJEPA-1.5-Large / VideoMix-Large (303M, CC BY-NC 4.0) | **No** para estado | Encoder de vídeo; no comercial |
| I-JEPA ViT-H/14 (ImageNet) | No | Imagen estática |

Las cifras de capacidad de estos pesos son de sus autores en sus tareas y no indican rendimiento en Melee.

---

## 6. Tamaños y coste de LeWorldModel (para A7; atribuidos)

**Declarado por los autores (DOC):**

| Concepto | Valor | Fuente |
|---|---|---|
| Parámetros totales | ~15M | arXiv 2603.19312v3, abstract y §3; le-wm README L7 |
| Encoder | ~5M: ViT-Tiny, patch 14, 12 capas, 3 cabezas, dim 192 | Paper |
| Predictor | ~10M: 6 capas, 16 cabezas, dropout 10 %. El apéndice D lo llama "ViT-S", lo que es inconsistente con el texto | Paper |
| Embedding | D = 192; rendimiento cae por debajo de ~184 y satura por encima (Fig. 15) | Paper |
| Entrenamiento | "a single GPU in a few hours"; **no se indica el modelo de GPU ni las horas exactas** | Abstract; le-wm.github.io |
| Esquema | Batch 128, sub-trayectorias de 4 frames, 10 épocas por entorno | Paper |
| Datos | TwoRoom 10k episodios (~92 pasos); Push-T 20k (~196); Cube 10k×200; Reacher 10k×200 | Paper |
| Planificación | CEM: 300 muestras, top-30, 30 iteraciones (Push-T) / 10 (resto); horizonte 5 bloques × frameskip 5 = 25 pasos | Paper |
| Tiempo de plan | ~1 s frente a 47 s de DINO-WM ("48×"); no se especifica el hardware | le-wm.github.io |
| Tamaño del predictor | Push-T: Tiny 80.7 %, Small 96.0 %, Base 86.7 % de éxito (Tabla 6) | Paper |

**Inspeccionado en el código (CÓD) y recuento propio:**

- `config/train/lewm.yaml`: `max_epochs: 100` (el paper dice 10), `batch_size: 128`, `lr: 5e-5`, `weight_decay: 1e-3`, `precision: bf16`, `gradient_clip_val: 1.0`, `history_size: 3` (global; el paper usa 1 en TwoRoom), `sigreg.weight: 0.09` (el texto del paper dice 0.1).
- `config/train/model/lewm.yaml`: `vit_hf size: tiny, patch 14, pretrained: false`; predictor `depth 6, heads 16, dim_head 64, mlp_dim 2048`; proyector y pred_proj MLP 192→2048(BN)→192.
- Recuento exacto con torch (INF a partir del código): predictor `ARPredictor` = **10,791,360** parámetros; cada proyector = 792,768 (×2); `Embedder` de acciones ≈156k. Con un ViT-Tiny/14 de ≈5.5M el total ronda **≈18M**, no 15M. La diferencia puede deberse a si se cuentan los proyectores; el paper no lo aclara.
- Implicación para Melee (INF): con un encoder de estado (MLP/transformer pequeño, <1M) en lugar del ViT, el coste lo domina el predictor (~10.8M con la config LeWM). En B2 el predictor no se usa en inferencia, así que el coste de inferencia es solo el del encoder.

---

## 7. Comprobaciones locales (REP, local_check)

Script: `evidence/A3/checks/sigreg_checks.py`. Resultado: `evidence/A3/checks/sigreg_checks_result.json`. CPU con 2 hilos, torch 2.10.0. Comando: `python3 -I evidence/A3/checks/sigreg_checks.py /home/kripta/melee-research`.

Script complementario: `evidence/A3/checks/toy_invariance_long.py` → `toy_invariance_long_result.json`. Pico de RSS 0.86 GB; 4 min + 2 min de reloj.

**C1, API (REP).** `EppsPulley(num_points=17)` → `TypeError: unexpected keyword argument 'num_points'`. `EppsPulley(n_points=17)` funciona; sus valores por defecto son t_max = 3, n_points = 17.

**C2, equivalencia (REP).** le-wm `SIGReg` y lejepa `EppsPulley(...).mean()` con las mismas direcciones dan 1.09178 los dos (diferencia 0.0).

**C3, coste en CPU (2 hilos, forward+backward, solo SIGReg; servidor compartido):**

| N | D | M | ms | intermedio mayor |
|---|---|---|---|---|
| 128 | 192 | 1024 | 45 | 8.5 MiB |
| 256 | 192 | 1024 | 69 | 17 MiB |
| 256 | 192 | 256 | 7.4 | 4.2 MiB |
| 256 | 64 | 1024 | 57 | 17 MiB |

Domina el término N·M·K de trigonometría, no D. Con M = 256 el coste baja ~9×. El paper indica que 512 slices ya es "competitivo". En GPU el coste será menor; no se ha medido.

**C4, qué ve SIGReg (REP; N = 256, D = 192, M = 1024, media de 5 sorteos de direcciones):**

| Embedding | Valor |
|---|---|
| Gaussiano i.i.d. | 0.96 |
| **Ruido independiente de la entrada (cero información)** | **1.21** (mismo orden que el anterior: indistinguible) |
| Constante (colapso) | 122 |
| Rango 8 con varianza total reescalada | 8.7 |
| Isotrópico en 8 dims, cero en el resto | 88 |
| 1 coordenada binaria ±1 + resto gaussiano | 1.08 |
| 16 coordenadas binarias | 1.09 |
| 192 coordenadas binarias | 1.03 |
| Gaussiano ×3 (escala incorrecta) | 132 |

Conclusiones:

- SIGReg castiga con fuerza el colapso, el rango bajo y la escala incorrecta.
- Es **ciego** al contenido informativo y casi ciego a la estructura discreta por coordenada.

**C5/C5b, invariancias en un juguete "tipo Melee" (REP).**

Montaje:

- Estado sintético de 9 dimensiones: x, y, facing ±1, vx, fase de animación como (sin, cos), y 3 dimensiones de ruido.
- Encoder MLP de dimensión 32.
- Pérdida LeJEPA de MINIMAL.md, con λ = 0.05 y 256 slices.
- Tres familias de vistas: jitter pequeño; espejo (x, facing, vx invertidos con p = 0.5); jitter de fase (±¼ de ciclo).

Corrida corta (C5: 400 pasos, N = 256, V = 4, 3 semillas):

- Los probes lineales de facing (acc = 1.0) y de fase (R² ≥ 0.95) **no detectan** la pérdida.
- La invariancia aún no había convergido (`final_inv` ≈ 0.05–0.08, frente a 0.003 del control).

Corrida larga (C5b: 2000 pasos, N = 128, V = 2, semilla 0):

| Vistas | dist(z, z_espejo) / dist media | dist(z, z_fase+⅛) / dist media | acc. lineal facing | R² lineal fase |
|---|---|---|---|---|
| jitter | 0.84 | 0.31 | 1.00 | 0.98 |
| espejo | **0.05** | 0.37 | **0.69** | 0.99 |
| jitter de fase | 0.94 | **0.05** | 1.00 | **0.68** |

Lectura:

- Las invariancias inducidas por las vistas borran justamente la información de control correspondiente.
- Un probe lineal puede seguir "aprobando" mientras la invariancia está a medio formar. Por eso `ablations.json` exige también el **test de pares mínimos** (ratio de distancias), no solo probes.
- Límites: es un juguete con una sola semilla en la corrida larga. Muestra el mecanismo, no magnitudes para Melee.

---

## 8. Dudas abiertas y dependencias

- **A6:** ¿los logs .slp del corpus contienen action_frame, hitlag, hitstun, invulnerability_left y las velocidades para ambos jugadores en todas las versiones? Determina la entrada común y los probes.
- **A4:** si W1 reutiliza E (LeWM-like), conviene acordar D, historia H, k de predicción y si las acciones del rival entran en P durante el entrenamiento (recomiendo que sí, solo en entrenamiento y con etiqueta oracle en diagnóstico).
- **A7:** el coste del preentrenamiento J-T en esta máquina sin GPU no se ha medido. El de SIGReg sí (§7) y es menor.
- **A8:** el control E1-S (predicción de estado explícito) es el que puede refutar el valor de "JEPA" en estado estructurado; propongo que sea obligatorio.
- **Discrepancias de fuente (para SOURCE_AUDIT):**
  - LeWM: paper ↔ config en λ (0.1 vs 0.09), épocas (10 vs 100) e historia de TwoRoom (1 vs 3).
  - LeWM: el apéndice D llama "ViT-S" al predictor; el recuento desde el código da ≈18M frente a los ~15M declarados.
  - LeJEPA: el paper integra en [−5, 5] y el código en [0, 3]; el README usa una API errónea.
  - LeVJEPA: la ficha B07 enlaza `LeVJEPA-VideoMix-Large`, mientras que el README apunta a `LeVJEPA-1.5-Large`. Ambas páginas existen (303M, CC BY-NC 4.0). La ficha HF dice "no EMA target encoder", y el README dice que los tensores publicados son la copia EMA. Son compatibles: la EMA es solo de evaluación (`train.py:82`).
  - LeWM: el pseudocódigo de la Fig. 9 llama `F.mse_loss` con un solo argumento (errata del paper; el código real usa `(pred − tgt).pow(2).mean()`).
