# E0: suelos triviales, prueba de humo y varianza entre semillas

Implementador E0 (paso "suelos + humo"), 2026-11-19. Etiquetas: **REP** (medido aquí, con comando registrado en
`logs/commands.log`), **INF**, **EST** (estimación no medida), **PROP**.

**Estado: cerrado con lo que hay en disco, por orden del coordinador** (servidor sin memoria; no se lanza ningún
proceso más con torch).

> **Actualización 2026-11-21: las 3 semillas están completas.** Las tres corridas que faltaban (`smoke_q_s1`,
> `smoke_q_s2`, `smoke_w0s_s2`) se ejecutaron en el PC del usuario. Está en el anexo [§8](#8-anexo-2026-11-21-semillas-completadas-en-el-pc).
> Las cifras de §4 basadas en 2 semillas siguen siendo válidas; la desviación entre semillas ya está estimada.

Los suelos triviales están **completos**. Del humo terminaron **3 de 6 corridas**:

| modelo | semillas terminadas | semillas cortadas y motivo |
|---|---|---|
| W0-S (`w0s_*`) | **2**: s0, s1 | s2: abortada por mi watchdog de VmRSS (> 880 MB) al arrancar; su relanzamiento lo paró el entorno por memoria baja |
| q (`q_mlp`) | **1**: s0 | s1: abortada por el watchdog; relanzada y muerta (casi seguro por el OOM-killer del servidor hacia las 17:09 hora local, un proceso de ~970 MB, probablemente esta corrida). s2: nunca llegó a terminar (matada a mano para no tener dos procesos; el relanzamiento lo paró el entorno) |

**La desviación entre semillas queda SIN ESTIMAR para ambos modelos (< 3 semillas).** El insumo "2× la desviación
entre semillas" para los gates de E1 sigue pendiente. `model_diagnostics.csv` solo trae filas `seed=mean` (con
`n_seeds`) y ninguna `seed=std`. Para W0-S doy los dos valores por semilla como información, no como estimación de
la dispersión.

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

### 4.1 W0-S frente al mejor suelo (media de 2 semillas, valores s0 / s1; sd sin estimar; IC95 bootstrap por partida, 12 partidas)

Acierto de `action` en eventos (mejor suelo: majority):

| h | suelo | oracle_u | persist_u | shuffled_u |
|---|---|---|---|---|
| 1 | 0.283 | 0.696 (0.697 / 0.695) | 0.404 (0.399 / 0.408) | 0.346 (0.338 / 0.355) |
| 4 | 0.289 | 0.639 (0.639 / 0.640); Δ +0.350, IC [+0.341, +0.360] | 0.324 (0.320 / 0.327); Δ +0.035, IC [+0.030, +0.039] | 0.266 (0.261 / 0.271) |
| 8 | 0.282 | 0.551 (0.551 / 0.551); Δ +0.269, IC [+0.259, +0.279] | 0.225 (0.223 / 0.227); Δ −0.057, IC [−0.063, −0.051] | 0.197 (0.193 / 0.201) |

MAE de la posición en eventos:

| campo | h | mejor suelo | oracle_u | persist_u | shuffled_u |
|---|---|---|---|---|---|
| pos_x | 4 | constvel 2.168 | 2.189 (2.160 / 2.218); IC Δ [−0.03, +0.07] | 2.480 (2.467 / 2.492) | 2.942 |
| pos_x | 8 | condmean 4.629 | **3.918 (3.856 / 3.979)**; −15.4 %, IC Δ [−0.84, −0.58] | 4.890 (4.870 / 4.910) | 5.553 |
| pos_y | 4 | condmean 2.235 | 2.821 (2.811 / 2.832) | 3.045 (3.036 / 3.053) | 3.238 |
| pos_y | 8 | condmean 4.217 | 4.892 (4.872 / 4.913) | 5.576 (5.560 / 5.592) | 5.857 |

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
   eventos a h = 4 la caída es de 0,639 a 0,266 (en ambas semillas: 0,639/0,261 y 0,640/0,271). El modelo no ignora la
   entrada de acción.
3. **¿Supera al mejor suelo en eventos a h ∈ {4, 8}?**
   - Solo con mandos oráculo. Mejora la acción en eventos, con una reducción relativa del error de 49 % a h = 4 y de
     37 % a h = 8, y pos_x a h = 8 (−15 %). Su IC95 por partida excluye 0. El criterio "> 2× sd entre semillas" no
     se puede evaluar porque la sd está sin estimar, aunque las dos semillas difieren ≤ 0,2 pp frente a efectos de
     27–35 pp.
   - **Con la información justa (persist_u) no lo supera de forma útil.**
     - Acción a h = 4: +3,5 pp, una reducción relativa del error de solo el 4,9 % (< 10 % de G1-dyn). El IC por
       partida excluye 0, y las dos semillas difieren en 0,7 pp.
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
5. **Desviación entre semillas: SIN ESTIMAR** (W0-S tiene 2 semillas y q, 1; hacen falta ≥ 3). Como dato, la
   diferencia |s0 − s1| de W0-S en las métricas de arriba es de 0,0001–0,01 en acierto y de 0,02–0,12 u en MAE de
   posición. El IC bootstrap por partida (12 partidas) es del mismo orden o más ancho. INF: la variación entre
   partidas pesará al menos tanto como la variación entre semillas, pero con 2 semillas no se puede afirmar.

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

1. **Semillas incompletas** (tabla al principio).
   - `smoke_q_s1` y `smoke_w0s_s2` las abortó mi watchdog interno de VmRSS (> 880 MB). La causa fue una copia doble
     en `Block` y retener vistas del memmap: se corrigió.
   - El relanzamiento (`run_smoke_rest.sh`) lo detuvo el entorno de Claude Code por memoria del sistema críticamente
     baja, y el coordinador informó de un proceso de ~970 MB muerto por el OOM-killer a las 17:09. Es probablemente
     el `smoke_q_s1` relanzado. Como VmRSS incluye ~250 MB de librerías de torch mapeadas, el watchdog no bastó
     para evitarlo.
   - Por orden del coordinador no se lanza nada más con torch. Completar las 3 semillas es tarea pendiente para
     cuando el servidor tenga memoria (o en la GPU de E1): `bash pilot/e0/models/run_smoke_rest.sh` y después
     `summarize.py`, unos 4–7 min de CPU por corrida.
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
- `model_diagnostics.csv`: suelos + humo por semilla + filas `seed=mean` con `n_seeds` (sin `seed=std`, porque
  hay < 3 semillas); 5.454 filas.
- `floors_per_game.csv` y `runs/*_per_game.csv`: métricas por partida para el bootstrap.
- `runs/smoke_*.json`: tiempos, RSS y lista de sha1 de train.
- `vocab.json`: vocabularios de acción y stick.
- `floors_side.json`: probabilidades de persistencia y tiempos.
- `logs/`: `commands.log`, más el stdout/stderr y `/usr/bin/time -v` de cada ejecución, `summarize.out` y los tests.
- Código: `pilot/e0/models/`. Tests: `pilot/e0/tests/test_floors_metrics.py`, 10 tests, OK con torch
  (`logs/tests_floors.out`). La suite completa en el venv da 21 OK y 2 saltados (`logs/tests_all_venv.out`).

## 8. Anexo 2026-11-21: semillas completadas en el PC

**Qué se ejecutó (REP).** Las tres corridas que faltaban se lanzaron en paralelo con el mismo comando y la misma
configuración que en el servidor: CPU, 2 hilos, `--games 40 --epochs 2`. La máquina era el PC del usuario (Windows 11,
Ryzen 9 9955HX, 31 GiB; `evidence/E1/hardware.json`), con torch 2.10.0, la misma versión que en el servidor. Antes se
regeneró el dataset con `run_all.sh`: salieron las mismas 288 partidas y los mismos 2.829.740 frames, con
`parsed_index.jsonl`, `splits.jsonl` y `stream_manifest.jsonl` idénticos byte a byte. Después se reexportó la caché:
270 partidas, test excluido. Registro completo en `logs/commands.log`: unos 2–2,6 min de reloj y unos 880 MB de pico
por corrida.

**Mezcla de máquinas.** W0-S s0 y s1 y q s0 vienen del servidor (Linux); W0-S s2, q s1 y q s2, del PC. La varianza
entre semillas incluye por tanto la que pueda haber entre máquinas. Si existe, aumenta la desviación, de modo que el
umbral "2× sd" queda del lado conservador (INF).

**Resultados (REP, val de 12 partidas; tablas completas en `logs/summarize.out`).**

| Medida | Mejor suelo | Media (sd entre 3 semillas) | Por semilla | Mejora relativa |
|---|---|---|---|---|
| W0-S, acción en eventos, h=4, `oracle_u` | 0,289 | 0,642 (0,0049) | 0,639 / 0,640 / 0,648 | +49,7 % |
| W0-S, acción en eventos, h=4, `persist_u` | 0,289 | 0,324 (0,0034) | 0,320 / 0,327 / 0,324 | +4,9 % |
| W0-S, acción en eventos, h=8, `persist_u` | 0,282 | 0,226 (0,0027) | 0,223 / 0,227 / 0,228 | −7,8 % |
| W0-S, acción en eventos, h=4, `shuffled_u` | 0,289 | 0,268 (0,0060) | 0,261 / 0,271 / 0,272 | −2,9 % |
| q, NLL de botones, todo, h=7 | 0,884 | 0,798 (0,0015) | 0,800 / 0,797 / 0,799 | +9,7 % |
| q, NLL de botones, cambio de acción, h=7 | 2,139 | 2,020 (0,0042) | 2,025 / 2,018 / 2,018 | +5,5 % |
| q, NLL del stick, cambio de acción, h=1 | 5,213 | 4,053 (0,0063) | — | +22,3 % |

**Lectura.**
- La semilla nueva confirma lo que se veía con 2 semillas (REP).
- **La desviación entre semillas es muy pequeña** (0,002–0,007 en acierto y NLL) frente a los efectos de interés.
  Con la regla "2× sd", el umbral de ruido es de unos 0,01. En la práctica, las puertas de E1 las decidirán la mejora
  relativa mínima y el IC95 por partida, no la varianza entre semillas (INF).
- Esta desviación es de modelos de humo (40 partidas, 2 épocas). En E1, con más datos y más épocas, hay que volver a
  estimarla con las semillas de E1 (PROP).
- La conclusión de §4 no cambia: W0-S sin los mandos futuros reales queda por debajo del 10 % de G1-dyn a h=4 y es
  peor que el suelo a h=8 (REP, humo; no decide G1).
