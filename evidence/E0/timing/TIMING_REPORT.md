# E0 · Envoltorio de plazo RT-strict y banco de latencia extendido (pasos 2 y 3 de FINAL_RECOMMENDATION)

Agente E0-timing · 2026-11-19 · Español. Etiquetas: **[MED]** REPRODUCIDO (medición propia en este servidor
compartido), **[COD]** INSPECCIONADO_EN_CODIGO, **[INF]** INFERENCIA, **[PROP]** PROPUESTA.

## 0. Estado y avisos (léase primero)

- **La campaña quedó INCOMPLETA.** Claude Code (no mi script) mató la campaña en segundo plano a las ≈16:00 UTC
  "because the system is running low on memory". No la he relanzado: el aviso pide no reiniciarla sin
  autorización expresa. Lo que se completó:
  - **Banco B**: 8 ejecuciones, **1 repetición, solo 1 hilo**. Ocho núcleo×implementación; dos de ellas
    (`tx fast`, `tx_kv fast`) se cortaron por el `timeout` de 175 s (rc=124), así que les falta la celda D=18 en
    lazo cerrado. **No hay medidas a 2 hilos ni dispersión entre repeticiones.** Se pedían ≥3 repeticiones y no se
    cumple.
  - **Tarea A**: el código y los 11 tests (`tests.log`, todos OK) existen, pero **la campaña de 60 Hz (fases
    `wrapper` y `e2e`) no llegó a ejecutarse.** `timing.jsonl` **no existe**. Solo hay un humo de 300 frames por
    configuración con carga ≈100 (`smoke_wrapper_stdout.txt`, solo la salida impresa: las trazas de ese humo no se
    guardaron). `timing_summary.json` está vacío.
  - **Probe JIT**: una sola medición manual, anotada en `commands.log`.
  - Para completarla, basta con que el usuario lo pida: `bash pilot/e0_timing/run_e0_timing.sh {present|jit|e2e|wrapper} 3`
    y después `python3 -I pilot/e0_timing/summarize_timing.py`.
- **Carga de la máquina.** `load1` osciló entre 3,5 y 164 durante la sesión y la RAM disponible bajó a 191 MB.
  Cada ejecución lleva su `uptime` y `free` en `commands.log` y su `loadavg` en el registro `env`/`end` de
  `present_raw.jsonl`. Las colas p95/p99 están infladas por la contención; las medianas son más fiables.
- **Calibración** [MED]. Con load1 = 7,7 medí de nuevo la decisión proxy de A7 (MLP-1M K16·T8, `a7models.build`,
  mismo código): **2,18 ms p50 / 2,60 ms p99**, frente a los 2,3 / 2,8 ms de A7. A esa carga la máquina rinde como
  cuando A7 midió, así que las diferencias de abajo vienen de la arquitectura y no del estado del host.

## 1. Método

### 1.1 Tarea A: `RT-strict` (`pilot/e0_timing/rt_strict.py`) [PROP sobre un patrón COD]

- **Patrón de bot-writer**: `melee_llm/botwriter/agent.py` @`7e179081`, L79 `budget_ms=16.0`. En `begin()`
  (L150-167) se envía el frame y arranca el plazo. `step()` (L169-186) espera solo lo que queda del plazo; si la
  respuesta llega tarde, se mantienen los mandos previos y la respuesta vieja se descarta.
- **Trabajador**: un hilo con buzón de una plaza (por defecto) o un proceso hijo (`fork` + `Pipe`, como
  `BotAgent`). Un frame nuevo sustituye al que aún no ha empezado.
- **Fallback declarado**: L1 `best_so_far` (lo publicado con `ctx.publish`) → L2 `repeat_last` (como mucho
  `max_repeat` = 30 frames seguidos) → L3 `neutral`. Hay dos niveles opcionales, desactivados por defecto:
  `late_result` (la última respuesta completa para una observación anterior, con su edad) y `cheap_policy`
  (π0 sobre la observación envejecida, DESIGN §3.1).
- **Traza por decisión**, con los campos de 06 L88:
  - `obs_frame`, `decision_frame`, `target_frame` (= f+1+D), `applied_frame` (inferido, con
    `applied_frame_measured=false`);
  - `capture_ts_ns`, `ready_ts_ns`, `policy_start/end_ts_ns`, `accepted_ts_ns`, `send_ts_ns`, `applied_ts_ns`
    (`null` y su fuente, porque no hay Dolphin);
  - `latency_ms`, `deadline_missed`, `fallback_used`, `budget_spent_ms`, `overrun_ms` (cuánto se pasó del plazo
    el propio envoltorio), `wrapper_overhead_ms`, `aged_obs_frames` y `late_by_ms`.
  Una respuesta tardía completa su registro después, pero nunca se aplica. Un frame cuenta como perdido si se usa
  un fallback **o** si el mando se acepta después del plazo, porque el host desplanificó el bucle.
- **Bucle falso** (`fake_runner.py`). Imita `runner.play` L279-300: `console.step()` hace el flush y bloquea
  hasta el siguiente tick de 60 Hz, con 3,3 ms de "emulación" simulada con `sleep`; después van los `begin` de los
  dos puertos y luego los dos `step`. Si los agentes llegan tarde, el frame se retrasa: el juego se ralentiza y no
  se pierde entrada, como con `blocking_input`.
- **Agentes sintéticos** (`synthetic_agents.py`):
  - `zero` (mide el overhead);
  - `const4`;
  - `heavytail` (lognormal de 4 ms con un 2 % de picos de 12–30 ms);
  - `exceed14`;
  - `anytime13` (publica cada 1 ms);
  - `pycpu` (bucle Python que **retiene el GIL**).

### 1.2 Tarea B: banco del predictor del presente (`wm_models.py`, `bench_present.py`) [PROP; MED]

- **Pesos aleatorios.** Se mide coste, no calidad.
- **Dimensiones del contrato A4 / DESIGN §2.1**:
  - por jugador: 12 continuos, 8 categóricos (action 512, …), 4 contadores (256/64/128/64) y mando de 16;
  - 4 proyectiles × 7 y `stage`.
- **E**: embeddings por campo → transformer de entidades (7 tokens, d_e = 96, 1 bloque) → núcleo temporal con
  d = 192 y H = 16. Núcleos:
  - `mlp`: ventana aplanada;
  - `gru`: 2 capas;
  - `tx`: causal de 2 capas sobre el contexto creciente (historia + pasos), que lo recalcula todo en cada paso;
  - `tx_kv`: lo mismo con KV-cache preasignada.
- **W0-S**: E + condicionamiento por los mandos de f+1 + cabezas por campo fusionadas (two-hot con 63 bins,
  declarado) + muestreo y decodificación de vuelta a tensores de frame.
- **Parámetros**: W0-S 1,54 M (gru), 1,70 M (tx) y 1,86 M (mlp). q 0,93–1,25 M. π0 0,58–1,11 M (d = 128).
- **q en lazo cerrado**: q se evalúa en cada uno de los D+1 pasos sobre el estado imaginado, con su propio E.
- **q en lazo abierto**: **un** forward de q sobre la historia real; se muestrean K mandos y se mantienen durante
  los D+1 pasos (simplificación declarada).
- **π0**: un forward sobre las últimas H filas de cada hipótesis (reales + imaginadas). Después, mezcla en el
  espacio de la acción y argmax.
- **Una decisión** = featurize (dict Python → tensores) + encode (W0-S y q, B = 1) + K = 4 × (D+1) pasos + π0.
  Se hacen 150 decisiones tras 15 de calentamiento, con `torch.inference_mode`, fp32 y eager.
- **`impl=ref` frente a `impl=fast`**: `ref` muestrea campo a campo; `fast` lo vectoriza (un gather y un argmax
  para todos los categóricos, ambos jugadores a la vez).
- **Test de KV-cache** (`tests/test_kv_cache.py`). Con los mismos pesos y las mismas semillas, el núcleo con caché
  frente al que lo recalcula todo da una diferencia máxima < 1e-4 en 19 pasos. El predictor completo, en lazo
  abierto y cerrado y con D = 12, da **los mismos estados discretos muestreados y el mismo mando final**.
  Resultado: OK.

### 1.3 Comandos exactos

```
bash pilot/e0_timing/run_e0_timing.sh tests            # 11 tests OK (evidence/E0/timing/tests.log)
bash pilot/e0_timing/run_e0_timing.sh present 3        # cortado tras 8 ejecuciones (rep 0, 1 hilo)
#  -> cada ejecución: OMP_NUM_THREADS=1 timeout 175 nice -n 19 python3 -I bench_present.py --core C --threads 1 --impl I --rep 0 --n 150
python3 -I pilot/e0_timing/summarize_timing.py         # -> latency_summary.{json,md}
# exploratorios manuales (commands.log): compile_probe.py 1 gru {inductor|jit}; humo fake_runner.py --frames 300
```

Antes de cada ejecución, el driver espera a que haya `MemAvailable` ≥ 900 MB y `load1` < 16, con un máximo de
10 min; si vence ese tiempo, ejecuta igualmente y lo registra (`WAIT-TIMEOUT`). El RSS de pico fue de 499–544 MB
por proceso.

## 2. Cifras

### 2.1 Predictor del presente, 1 hilo, 1 repetición (ms; tabla completa en `latency_summary.md`)

| núcleo / impl | D=6 abierto p50 / p99 | D=6 cerrado | D=12 abierto | D=12 cerrado | D=18 abierto | D=18 cerrado |
|---|---|---|---|---|---|---|
| gru fast | **13,0 / 19,5** | 19,2 / 28,6 | 20,9 / 33,6 | 33,1 / 67,0 | 30,9 / 62,4 | 43,6 / 72,9 |
| gru ref | 15,8 / 26,3 | 21,1 / 70,8 | 26,0 / 32,6 | 37,6 / 46,1 | 32,8 / 37,0 | 52,7 / 146 |
| mlp fast | 13,3 / 19,9 | 18,0 / 36,3 | 21,8 / 55,7 | 32,5 / 174 | 30,3 / 164 | 46,8 / 87,8 |
| mlp ref | 14,8 / 23,3 | 21,9 / 28,5 | 24,4 / 28,7 | 36,9 / 55,7 | 32,5 / 38,0 | 50,5 / 68,3 |
| tx ref (sin caché) | 28,0 / 61,5 | 46,9 / 92,2 | 47,5 / 110 | 88,1 / 252 | 68,4 / 198 | 125 / 227 |
| tx_kv ref (con caché) | 18,7 / 52,6 | 29,6 / 67,5 | 27,5 / 93,8 | 43,6 / 82,0 | 42,5 / 190 | 107 / 21 381* |

\* Parada del host: load1 llegó a 78 durante esa ejecución. Las filas `tx fast` y `tx_kv fast` se midieron con
load1 = 7–45 y están en el `.md`; no las uso para comparar.

**Coste por componente de UN paso a batch K = 4** (p50 en µs, 1 hilo; registro `components`):

| Componente | Coste |
|---|---|
| embedding de frame (entidades) | 271–296; se paga **dos veces** en lazo cerrado (W0-S y q) |
| cabezas de W0-S | 192–225 |
| muestreo y decodificación | 299–308 (fast) / 518–973 (ref) |
| paso de núcleo: gru | 129–131 |
| paso de núcleo: mlp | 192–205 |
| paso de núcleo: tx_kv | 268 |
| paso de núcleo: tx sin caché | 1.343 con contexto 17 y **2.416 con contexto 35** |
| cabeza de q + muestreo | 80 + 53–144 |
| encode de la historia (B = 1, H = 16) | 640 (mlp), 1.220 (gru), 1.166 (tx_kv), 2.018 (tx) |
| π0 sobre la observación envejecida | 0,64–2,1 ms p50 |

⇒ El paso de un frame cuesta ≈ 1,0 ms en lazo abierto y ≈ 1,5 ms en lazo cerrado. **El núcleo temporal es la
parte menor**; dominan el embedding de entidades, las cabezas estructuradas y el muestreo [MED + INF aritmética].

**KV-cache** [MED]. Divide el paso del transformer por 5–9 (268 µs frente a 1.343–2.416 µs) y baja la mediana de la
decisión ≈ 1,7–2× (por ejemplo, D = 12 abierto: 27,5 frente a 47,5 ms). Aun así no deja al transformer por debajo
de GRU/MLP.

**Probe JIT / compile** [MED, n = 1]:
- TorchScript `trace` + `freeze` de un paso en lazo cerrado (gru): 1.872 → 1.315 µs p50 (−30 %).
- `torch.compile` (inductor) **superó el tope de RAM al compilar**: el watchdog lo mató a 1.097 MB. No se pudo
  medir aquí.

### 2.2 Ruta completa y veredicto "¿cabe en 10 ms p99 en esta CPU?"

**NO en ninguna de las 46 configuraciones medidas** (núcleos mlp, gru, tx y tx_kv; D 6/12/18; q abierto y cerrado;
ref y fast; 1 hilo).
- La mejor es `gru fast`, D = 6, lazo abierto: p50 = 13,0 ms y p99 = 19,5 ms, **solo predictor + π0, sin sumar el
  envoltorio ni Dolphin**. Ninguna mediana baja de 13 ms.
- El overhead del envoltorio no se midió en campaña. En el humo con carga ≈100 (hilo, agente `zero`) fue de
  0,25 ms p50. Con el envoltorio sumado, el veredicto solo empeora. No hacía falta sumarlo para concluir "NO".
- Medidas que faltan: a 2 hilos, ≥3 repeticiones y e2e dentro del envoltorio. Ninguna puede convertir un p50 de
  13 ms en un p99 ≤ 10 ms, salvo que 2 hilos rindan más de 2× [INF; A7 midió 1,2–2× en medianas con 3 hilos].
  Habría que medirlo.

### 2.3 Qué confirma o refuta de D-2 (CRITICAL_REVIEW §7)

- **D-2 se confirma en lo cualitativo y se refuta en lo cuantitativo, por optimista.**
  - **Confirmado**: los 2,8 ms de la decisión proxy MLP-1M K16·T8 no son el coste del predictor del presente. La
    re-medí: 2,18 / 2,60 ms. Pero A con su arquitectura real cuesta un orden de magnitud más.
  - **Refutado** [MED]:
    - "≈ 3–6 ms con D = 12 y rival humano": medido 20,9–26,0 ms p50 y 28,7–33,6 ms p99 (gru/mlp, lazo abierto).
    - "hasta ≈ 17 ms con D = 18 y q en lazo cerrado": medido 43,6–52,7 ms p50 y 68–146 ms p99.
    - "Cabe en RT-strict para D ≤ 12 con rival humano" (INF en DESIGN §3.9) **no se sostiene** con estos módulos
      en eager a 1 hilo.
- **Por qué falló la estimación** [INF sobre MED]. Usaba un paso de 0,165–0,40 ms (el `MLPPred` de A7: un MLP
  residual sobre un latente de 192 dimensiones). El paso de W0-S con el esquema real incluye:
  - re-embebido del frame imaginado por el transformer de entidades, × 2 con q en lazo cerrado;
  - cabezas por campo (≈ 3.300 salidas);
  - muestreo y decodificación.
  Eso suma ≈ 1,0–1,5 ms a K = 4, que el coste fijo por operación de eager domina a este batch. A eso se añaden
  ≈ 2–3 ms fijos de encode y π0.
- **Qué haría falta para caber** [INF, sin medir]: bajar el paso a ≲ 0,4 ms (≈ 3×) y el encode + π0 a ≲ 1,5 ms.
  Vías posibles:
  - compilar (TorchScript da −30 %; inductor no cabe en RAM aquí);
  - compartir el embedding de frame entre W0-S y q;
  - un encode incremental entre frames;
  - cabezas más pequeñas;
  - o pasar a una predicción directa multi-offset (las cabezas a {1, 4, 8, 16, 32} de DESIGN §3.3) en lugar del
    despliegue autoregresivo de D+1 pasos.
  Ninguna está medida. Pero el cambio de diseño sí está justificado.

### 2.4 Envoltorio (solo humo y tests; NO es la campaña pedida)

- **Tests (11, OK).** Cubren:
  - el orden del fallback (neutral → repeat_last → neutral al superar `max_repeat`);
  - `best_so_far`;
  - `late_result` con edad 1;
  - el fallo del agente → neutral;
  - los campos de 06 y su coherencia (`target_frame = f+1+D`, `send ≥ accepted`);
  - un agente que siempre excede el plazo nunca retiene el bucle más de plazo + 6 ms de tolerancia;
  - la KV-cache.
- **Humo** (300 frames por configuración, load1 ≈ 100–164, `nice -n 19`; `smoke_wrapper_stdout.txt`):

  | Agente / modo | Resultado |
  |---|---|
  | `zero` / hilo | latencia p50 0,25 ms; p99 7,5 ms; overrun máx. 10,7 ms |
  | `zero` / proceso | p50 2,4 ms; overrun máx. 852 ms |
  | `exceed14` / hilo | fallbacks 290 repeat_last + 10 neutral; overrun máx. 4,4 ms |
  | `anytime13` / hilo | 299/300 `best_so_far` |

  `pycpu` / hilo, en una ejecución aparte de 120 frames con load1 ≈ 27: overrun máx. 5,2 ms, el intervalo de cambio
  del GIL (5 ms).
- **Lectura** [INF]:
  - la lógica del plazo funciona;
  - **con `nice 19` en un host saturado, el SO desplanifica el bucle decenas o cientos de ms**, y ningún
    envoltorio en espacio de usuario puede evitarlo;
  - un agente que retiene el GIL en modo hilo añade hasta `sys.getswitchinterval()` (por eso existe la opción
    `--switch_ms`).
  El "nunca bloquea más allá del plazo" **no está verificado en campaña**. Queda pendiente la fase `wrapper`.

## 3. Limitaciones

- **Sin Dolphin, sin el rival corriendo y sin `GameState` real.** La featurización usa un dict Python con el mismo
  número de campos.
- **Pesos aleatorios.** El coste no depende de los valores, salvo en ramas como `respawn`.
- **Ni ISO ni datos.**
- **Servidor compartido con producción activa** y carga muy variable, además de `nice -n 19`. Medí 1 repetición a
  1 hilo en lugar de ≥3 × {1, 2}.
- **Implementación eager propia (PROP).** Otra implementación podría ser más rápida (véase §2.3). La cifra es "el
  diseño tal como está especificado, implementado de forma directa en torch 2.10 CPU", no una cota inferior.
- **Simplificaciones declaradas**: two-hot con 63 bins; proyectiles regresados; q en lazo abierto con el mando
  mantenido; `dist_to_ledge` aproximada; el código de mando con 2 dimensiones de relleno.
- `applied_frame` y `applied_ts_ns` son inferidos o `null`.

## 4. Archivos

Código (todo en `pilot/e0_timing/`):

| Archivo | Contenido |
|---|---|
| `rt_strict.py` | el envoltorio |
| `fake_runner.py` | el bucle falso |
| `synthetic_agents.py` | los agentes sintéticos |
| `present_agent.py` | el predictor como agente del envoltorio |
| `wm_models.py` | W0-S, q, π0, cores y KV-cache |
| `bench_present.py` | el banco del predictor |
| `compile_probe.py` | el probe JIT / compile |
| `summarize_timing.py` | el resumen |
| `run_e0_timing.sh` | el driver |
| `tests/` | los tests |

Además, `pilot/a7_bench/run_all.sh` tiene una fase nueva `e0` que delega en `run_e0_timing.sh`, sin cambiar las
fases que ya existían.

Evidencia (todo en `evidence/E0/timing/`):

| Archivo | Contenido |
|---|---|
| `latency_summary.json` / `.md` | resumen del banco |
| `present_raw.jsonl` | crudos, con `raw_total_ms` por decisión y `env` con `uptime` |
| `commands.log` | registro de comandos |
| `tests.log` | salida de los tests |
| `smoke_wrapper_stdout.txt` | humo del envoltorio |
| `timing_summary.json` | vacío: falta la campaña A |
| `claims.jsonl` | claims |

Trazas crudas previstas: `/srv/mail/melee-research-data/e0_timing_raw/`, vacío.
