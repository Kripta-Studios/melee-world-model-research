# E0: suelos triviales, prueba de humo y varianza entre semillas

Implementador E0 (paso "suelos + humo"), 2026-11-19. Etiquetas: **REP** (medido aquí, con comando registrado en
`logs/commands.log`), **INF**, **EST** (estimación no medida), **PROP**.

**Estado: INCOMPLETO en la parte de semillas.** De las 6 corridas de humo previstas (3 de W0-S y 3 de q) hay 3 válidas:
W0-S con semillas 0 y 1, y q con la semilla 0. W0-S s2, q s1 y q s2 no terminaron (ver §6.1). Las desviaciones entre
semillas de W0-S son de **n = 2** y las de q **no existen**. No sirven todavía para calibrar los gates de E1.

Todas las cifras salen de `model_diagnostics.csv`, `floors_diagnostics.csv`, `runs/*.json` y
`logs/summarize.out`. Ese último fichero tiene todas las tablas completas: todos los campos, todos los subconjuntos y
h ∈ {1, 4, 7, 8, 13, 16, 32}. Aquí solo se extrae lo esencial.

## 1. Qué se midió y cómo

- **Datos.**
  - Split `A6-split-v1` (90/5/5): suelos ajustados en las **258 partidas de train**, todo medido en las **12 de
    val**.
  - **test (18 partidas) no se exportó ni se leyó.** `common.assert_no_test` se ejecuta al exportar y al cargar, y
    contrasta cada sha1 con `splits.jsonl`.
  - Solo frames con `frame_id ≥ 0`. Caché memmap de 2.618.794 filas en `$E0_DATA/cache/e0_floors_v1/` (320 MB).
- **Anclas.** Para cada frame f de val con historia de 8 frames (f ≥ 7) y f+32 dentro de la partida. Son 135.091
  anclas por puerto; se juntan los dos puertos (n = 270.182). Dinámica, q, suelos y modelos usan las mismas anclas.
- **Convención temporal.** La fila f lleva el estado post-frame f y el mando de f. La dinámica predice x_{f+h} con
  información ≤ f. q predice el mando del rival en f+h, con h = 1 y h = D+1 ∈ {7, 13}. Así el objetivo nunca es el mando
  de f. Esto lo comprueban dos tests: `test_q_target_is_f_plus_1_and_port_swap` y `test_w0s_window_excludes_future`.
- **Subconjuntos de evento** (del jugador cuyo estado se predice; ventana (f, f+h]):
  - `ev_action_change`: hay algún cambio de acción;
  - `ev_hitstun_start`: hay un flanco de subida de `flags4 & 0x02`;
  - `ev_stock_loss`: `stocks_{f+h} < stocks_f`;
  - `event` es la unión de los tres y `non_event` su complemento.

  En q, `change` = el componente de mando en f+h difiere del de f.
- **Suelos de dinámica.**
  - `persist`.
  - `constvel`: para la posición, pos + h·v_f, con la velocidad Slippi (aire o suelo según `airborne`, más
    knockback). Para los contadores, `action_frame + h` y `hitlag/hitstun − h` acotado a 0.
  - `constvel_fd`: diferencia finita.
  - `condmean`: x_f + E_train[Δ_h | acción, ⌊action_frame⌋]. Los campos x van con el signo de `facing`.
  - `majority` (discretos): la moda en train de campo_{f+h} dada (acción, ⌊action_frame⌋, campo_f). Si la clave no
    se vio, se usa persistencia.
  - `marginal`.
  - NLL con suavizado aditivo (α = 1 sobre la marginal).
  - INF/REP: en Slippi pos_{f+1} − pos_f = v_{f+1}. Coincide al 1e-3 en el 81 % de los frames de una partida en x,
    frente al 30 % si se usa v_f. Con información ≤ f solo se dispone de v_f.
- **Suelos de q.**
  - `marginal`.
  - `persist`: la probabilidad de quedarse igual a horizonte h, estimada en train, más la marginal.
  - `cond_act`: condicionado a la acción del rival.
  - `cond_act_prev`: condicionado a la acción del rival y a su mando en f. Este no lo pedía el encargo; se añadió
    porque es el suelo más duro.
  - Componentes:
    - 8 botones físicos (A, B, X, Y, Z, L, R, D_UP) como Bernoulli, más su combinación conjunta de 8 bits;
    - stick y C-stick como celda conjunta de la rejilla 1/80, con un **vocabulario top-512 y top-64 de train + OTHER**.
      Hay 8.140 y 4.158 celdas distintas en train; el vocabulario cubre el 97,4 % y el 99,1 % (`vocab.json`).
  - Régimen `I_full` (el mando del rival en f es observable).

## 2. Suelos de dinámica (REP, val)

Acierto de `action`, el campo clave de G1-dyn:

| subconjunto | suelo | h=1 | h=4 | h=7 | h=8 | h=13 | h=16 | h=32 |
|---|---|---|---|---|---|---|---|---|
| all | persist | 0.895 | 0.688 | 0.550 | 0.513 | 0.375 | 0.314 | 0.135 |
| all | majority | **0.922** | **0.747** | **0.635** | **0.604** | **0.473** | **0.415** | **0.239** |
| event | persist | 0.001 | 0.055 | 0.059 | 0.057 | 0.052 | 0.049 | 0.048 |
| event | majority | **0.283** | **0.289** | **0.288** | **0.282** | **0.234** | **0.223** | **0.178** |
| event | marginal | 0.127 | 0.142 | 0.140 | 0.138 | 0.128 | 0.120 | 0.097 |
| ev_hitstun_start | majority | 0.114 | 0.116 | 0.102 | 0.103 | 0.098 | 0.095 | 0.099 |
| non_event | persist | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

- Fracción de anclas con evento: 10,5 % a h=1 y 90,9 % a h=32. A h=1, event tiene n = 28.380; ev_hitstun_start, 950;
  ev_stock_loss, 68.
- NLL de la acción en eventos: majority 2,50 / 2,28 / 2,50 a h = 1 / 4 / 8; marginal ≈ 4,1.
- Como se esperaba, **la persistencia gana trivialmente fuera de eventos** (acierto 1,0) y es inútil dentro de ellos.
  El suelo que hay que batir en eventos es `majority`.
- Para el criterio de acción del rival de G1-q, el suelo en frames de cambio de acción es `majority`: **0,287 a h = 7**
  y **0,233 a h = 13**.

MAE de la posición en eventos (unidades de mundo; el mejor suelo en negrita):

| campo | suelo | h=1 | h=4 | h=8 | h=16 | h=32 |
|---|---|---|---|---|---|---|
| pos_x | persist | 0.960 | 3.271 | 5.907 | 10.56 | 18.42 |
| pos_x | constvel | **0.617** | **2.168** | 4.669 | 10.55 | 24.45 |
| pos_x | condmean | 0.800 | 2.359 | **4.629** | **8.607** | **15.60** |
| pos_y | persist | 1.248 | 2.586 | 4.846 | 9.374 | 14.08 |
| pos_y | constvel | 1.471 | 3.290 | 6.428 | 14.42 | 30.39 |
| pos_y | condmean | **1.183** | **2.235** | **4.217** | **8.370** | **12.82** |

- En todos los frames, pos_x con constvel da 0,18 / 1,16 / 3,22 a h = 1 / 4 / 8.
- La velocidad constante gana en x a corto plazo. La media condicionada a la acción gana en y, y en x a partir de h ≥ 8.
- `percent`: la persistencia es el mejor suelo en eventos (0,57 / 0,73 / 0,94 a h = 1 / 4 / 8).
- `airborne`: el mejor suelo en eventos es `majority` (0,843 / 0,803 / 0,765).
- El resto de campos (velocidades, contadores, escudo, saltos, stocks, hurtbox) está en `logs/summarize.out`.

## 3. Suelos del rival q (REP, val)

NLL por frame. "buttons" es la suma de las NLL de los 8 bits; el stick usa top-512 + OTHER.

| componente | subconj. | h | marginal | persist | cond_act | cond_act_prev |
|---|---|---|---|---|---|---|
| buttons | all | 1 / 7 / 13 | 1.232 / 1.232 / 1.231 | 0.441 / 1.600 / 1.933 | 0.915 / 1.067 / 1.116 | **0.295 / 0.884 / 1.035** |
| buttons | change | 1 / 7 / 13 | **2.393** / 2.290 / 2.235 | 6.28 / 5.28 / 5.13 | 2.467 / **2.139 / 2.116** | 3.312 / 2.289 / 2.218 |
| stick | all | 1 / 7 / 13 | 3.484 / 3.483 / 3.483 | 2.144 / 3.179 / **3.375** | 3.190 / 3.326 / 3.378 | **1.726 / 3.157** / 3.508 |
| stick | change | 1 / 7 / 13 | 5.514 / 4.243 / 4.081 | 6.82 / 4.76 / 4.46 | 5.358 / **4.157 / 4.026** | **5.213** / 4.650 / 4.572 |
| cstick | all | 1 / 7 / 13 | 0.311 / 0.311 / 0.311 | 0.176 / 0.382 / 0.449 | 0.232 / 0.282 / 0.296 | **0.095 / 0.240 / 0.278** |

- Acierto del stick (all): persistencia 0,712 / 0,386 / 0,294 y cond_act_prev 0,721 / 0,447 / 0,381.
- En frames de cambio de stick, la persistencia acierta 0 por construcción y el mejor suelo es la marginal
  (0,101 / 0,231 / 0,241). En el cambio, la marginal acierta bastante porque muchos cambios son "soltar a neutro".
- Tasa de cambio del stick: 70,6 % de las anclas a h = 13.

## 4. Prueba de humo (REP; verifica el ciclo, NO decide G1)

**Configuración.**
- W0-S: MLP de **687.502 parámetros**. Historia H = 8 (estado y mando de ambos), u_{f+1} de ambos y el escenario →
  x_{f+1} de ambos.
  - Cabezas: acción (175 clases), facing, airborne, saltos, stocks y hurtbox (CE), más los Δ de 12 continuos
    normalizados (Huber).
  - Peso ×4 de la CE de acción en frames de cambio.
- q: MLP de **764.878 parámetros**, con cabezas directas a f+1, f+7 y f+13.
- Entrenamiento:
  - **40 partidas de train** (las primeras por sha1; 372.732 frames), 2 épocas, batch 512, AdamW con OneCycle y
    lr 2e-3;
  - 2 hilos y `nice 19`; CPU compartida con load average entre 17 y 75.
- Rollout autorregresivo a h ∈ {4, 8}: realimenta el argmax de los discretos y la media de los Δ. Hay tres variantes
  de mandos futuros:
  - **oracle_u**: los mandos reales de ambos jugadores. Es régimen ORACLE: el modelo ve u_{f+1..f+h}, que ningún suelo
    ve, así que es una cota y no un rival justo de los suelos;
  - **persist_u**: u_{f+k} = u_f. Tiene la misma información que los suelos;
  - **shuffled_u**: la secuencia real de otra ancla del mismo lote. Es el control de "acciones barajadas".
- Simplificaciones declaradas frente a DESIGN §3.3: MLP en lugar de un transformer de entidades, sin two-hot ni modo
  de contadores, sin espejo, sin proyectiles y sin entrenar el despliegue (solo h = 1).

### 4.1 W0-S frente al mejor suelo (media ± sd, n = 2 semillas; IC95 bootstrap por partida, 12 partidas)

Acierto de `action` en eventos (mejor suelo: majority):

| h | suelo | oracle_u | persist_u | shuffled_u |
|---|---|---|---|---|
| 1 | 0.283 | 0.696 ± 0.0015 | 0.404 ± 0.0068 | 0.346 ± 0.012 |
| 4 | 0.289 | 0.639 ± 0.0008 (Δ +0.350, IC [+0.341, +0.360]) | 0.324 ± 0.0048 (Δ +0.035, IC [+0.030, +0.039]; 7× sd) | 0.266 ± 0.0071 |
| 8 | 0.282 | 0.551 ± 0.0001 (Δ +0.269, IC [+0.259, +0.279]) | 0.225 ± 0.0031 (Δ −0.057, IC [−0.063, −0.051]) | 0.197 ± 0.0054 |

MAE de la posición en eventos:

| campo | h | mejor suelo | oracle_u | persist_u | shuffled_u |
|---|---|---|---|---|---|
| pos_x | 4 | constvel 2.168 | 2.189 ± 0.041 (IC Δ [−0.03, +0.07]) | 2.480 ± 0.017 | 2.942 ± 0.026 |
| pos_x | 8 | condmean 4.629 | **3.918 ± 0.087** (−15.4 %, IC Δ [−0.84, −0.58]; 8× sd) | 4.890 ± 0.028 | 5.553 ± 0.032 |
| pos_y | 4 | condmean 2.235 | 2.821 ± 0.015 | 3.045 ± 0.012 | 3.238 ± 0.013 |
| pos_y | 8 | condmean 4.217 | 4.892 ± 0.029 | 5.576 ± 0.023 | 5.857 ± 0.014 |

Otros campos:
- En `percent` el modelo es peor que la persistencia en todos los h (eventos h = 8: 1,064 frente a 0,938). INF:
  la regresión Huber de Δ predice derivas pequeñas donde casi siempre Δ = 0.
- `airborne` en eventos: persist_u supera a majority a h = 4 (0,836 frente a 0,803) y empata a h = 8.
- NLL de la acción a h = 1:
  - en eventos: oracle_u 0,99, persist_u 2,39 y majority 2,50;
  - en todos los frames: oracle_u 0,30 y majority 0,33.

**Lectura honesta.**
1. **El ciclo funciona.** Hay entrenamiento, rollout AR, tres variantes de mandos y las mismas métricas, anclas y
   subconjuntos que los suelos. Las salidas tienen sentido: el error crece con h y el modelo bate claramente a la
   persistencia en eventos.
2. **Sí usa las acciones.** Barajar los mandos futuros empeora todas las métricas frente a oracle_u. En la acción en
   eventos a h = 4 la caída es de 0,639 a 0,266, unas 50 veces la sd. El modelo no ignora la entrada de acción.
3. **¿Supera al mejor suelo en eventos a h ∈ {4, 8}?**
   - Solo con mandos oráculo. Mejora la acción en eventos, con una reducción relativa del error de 49 % a h = 4 y de
     37 % a h = 8. Ambos efectos superan con mucho 2× sd y su IC95 por partida excluye 0. También mejora pos_x a h = 8
     (−15 %).
   - **Con la información justa (persist_u) no lo supera de forma útil.**
     - Acción a h = 4: +3,5 pp, una reducción relativa del error de solo el 4,9 % (< 10 % de G1-dyn), aunque es 7× sd
       y el IC excluye 0.
     - Acción a h = 8: peor que majority (−5,7 pp).
     - Posición: peor que el mejor suelo a h = 4 y 8.
   - Con ≤ 1M parámetros, 40 partidas y 2 épocas, esto **no decide G1**. Además G1-dyn en E1 se medirá con el rival
     modelado por q, que no es ni oracle ni persist.
4. **q** (1 semilla, sin dispersión):
   - Mejora la NLL sobre la marginal en todos los componentes y horizontes. Por ejemplo, el stick a h = 7 pasa de
     3,483 a 2,830 y los botones a h = 13 de 1,231 a 0,962.
   - En `all` bate al mejor suelo a h = 7 y 13 en botones, stick y C-stick, con mejoras relativas del 6–10 % en NLL y
     el IC por partida excluyendo 0.
   - Es **peor que cond_act_prev a h = 1** (stick: NLL 1,915 frente a 1,726, acierto 0,52 frente a 0,72). INF: no
     aprendió a copiar u_f en 2 épocas. A E1 le conviene darle u_f como entrada residual.
   - En frames de cambio de mando el acierto queda por debajo de la marginal (stick h = 7: 0,223 frente a 0,231),
     aunque la NLL es mejor.
5. **Desviación entre semillas (W0-S, n = 2).** En estas métricas va de 1e-4 a 1e-2 en acierto y de 0,005 a 0,09 u
   en MAE de posición. Por ejemplo, la acción en eventos con persist_u tiene sd 0,005 a h = 4 y 0,003 a h = 8.
   **Con n = 2 la sd es muy poco fiable** (el IC de una sd con 1 grado de libertad abarca ~0,45×–32×). El IC
   bootstrap por partida, con 12 partidas, suele ser más ancho que 2× sd. La varianza por partida domina sobre la
   varianza por semilla, así que en E1 el factor limitante será el número de partidas de test, no las semillas (INF).

## 5. Tiempos y memoria (REP) y extrapolación a E1 (EST)

| corrida | parámetros | muestras/s de entrenamiento (época 1 / 2) | s/época | muestras fwd/s en evaluación | RSS pico (MB) | total (s) | CPU user (s) |
|---|---|---|---|---|---|---|---|
| w0s s0 | 687.502 | 5.466 / 21.032 | 68 / 18 | 16.057 | 636 | 290 | 181 |
| w0s s1 | 687.502 | 2.168 / 2.741 | 172 / 136 | 10.970 | 557 | 610 | 235 |
| q s0 | 764.878 | 3.980 / 12.025 | 93 / 31 | 10.049 | 612 | 155 | 118 |

- Una muestra es un ancla de 8 frames: en W0-S con los dos jugadores; en q, un par (ancla, rival).
- El throughput varía **~10×** según la carga del servidor compartido (load average entre 17 y 75 durante las
  corridas). La cifra útil es el rango, 2.200–21.000 muestras/s para un MLP de 0,7M con 2 hilos, no un valor puntual.
- La RAM la domina torch: solo importarlo ocupa ~500 MB de VmRSS, de los que ~250 MB son librerías mapeadas.
- CPU total consumida en este paso: **≈ 10 min de CPU user** de las ~3 h presupuestadas. A eso se suman las corridas
  abortadas, que son despreciables.

**Extrapolación (EST, no medida).**
- E1 tiene ~2.000 partidas de train, unos 19,4 M de frames a la media de 9.700 frames por partida.
- Una época del MLP de 0,7M en esta CPU con 2 hilos tardaría **15 min – 2,5 h**.
- Con 1–5M parámetros, el coste por muestra crece aproximadamente con el número de parámetros (INF para MLP): ×1,5–7,
  es decir, **0,4–17 h por época**.
- 10 épocas × 3–5 semillas no caben en esta máquina, lo que es coherente con EXPERIMENT_PLAN §9.
- En GPU no se ha medido nada. La evaluación con rollout de 8 pasos y 3 variantes cuesta 24 forwards por ancla: unos
  200 s para 135 k anclas aquí.

## 6. Limitaciones y problemas

1. **Semillas incompletas.**
   - `smoke_q_s1` y `smoke_w0s_s2` las abortó mi watchdog interno de VmRSS (> 880 MB). La causa fue una copia doble
     en `Block` y retener vistas del memmap: se corrigió.
   - El relanzamiento (`run_smoke_rest.sh`) lo **detuvo el entorno de Claude Code por memoria del sistema
     críticamente baja**: la RAM disponible bajaba a 90–450 MB por otros procesos.
   - No lo relancé sin permiso. Para completar: `bash pilot/e0/models/run_smoke_rest.sh` y después `summarize.py`.
     Son unos 4–7 min de CPU por corrida.
   - Las semillas 0–1 de W0-S se entrenaron con el código anterior al cambio de `Block`. Ese cambio afecta solo a la
     memoria y a cómo se calculan μ/σ, que pasan a hacerse por campo (mismos valores salvo redondeo float32).
   - Hasta en tres arranques lancé procesos con "available" < 600 MB (`floors`, `bench_w0s`, `smoke_w0s_s0`, ver
     `commands.log`). Después añadí la espera en `logrun.sh`.
2. **Corpus.** 288 partidas de un solo volcado y un solo bucket (diamond-diamond, Fox ditto). Val tiene solo 12
   partidas, así que el IC por partida es grueso y la fuga por set es inevitable.
3. **C-stick crudo ausente.** Se usa el procesado, exacto en la rejilla 1/80. Tampoco se usa `raw_y` ni los gatillos
   analógicos en q (L y R solo como botón digital), ni se calcula `dist_to_nearest_ledge`. Faltan proyectiles,
   Randall y FoD.
4. **Stick top-K + OTHER.** La NLL del stick no es la de la rejilla completa de 8.140 celdas. Suelos y modelo usan
   el mismo vocabulario, así que la comparación entre ellos sí es válida.
5. **Subconjuntos de evento.** Se definen con el futuro real, igual para suelos y modelo, que es lo estándar. `event`
   lo domina el cambio de acción: hitstun y pérdida de stock son menos del 4 % de los eventos a h = 1.
6. **El humo no es G1.** El régimen oracle_u no es comparable a los suelos. persist_u es una cota inferior pesimista
   del modelo con q. Faltan `I_human`, ECE, la tolerancia ±1/±3 de eventos y los estados inválidos.
7. **No se escribió `claims.jsonl`.** El de `evidence/E0/` pertenece al paso anterior y el encargo no lo pedía.

## 7. Artefactos

- `floors_diagnostics.csv`: suelos, 2.406 filas.
- `model_diagnostics.csv`: suelos + humo por semilla + filas `seed=mean` y `seed=std`; 6.492 filas.
- `floors_per_game.csv` y `runs/*_per_game.csv`: métricas por partida para el bootstrap.
- `runs/smoke_*.json`: tiempos, RSS y lista de sha1 de train.
- `vocab.json`: vocabularios de acción y stick.
- `floors_side.json`: probabilidades de persistencia y tiempos.
- `logs/`: `commands.log`, más el stdout/stderr y `/usr/bin/time -v` de cada ejecución, `summarize.out` y los tests.
- Código: `pilot/e0/models/`. Tests: `pilot/e0/tests/test_floors_metrics.py`, 10 tests, OK con torch
  (`logs/tests_floors.out`). La suite completa en el venv da 21 OK y 2 saltados (`logs/tests_all_venv.out`).
