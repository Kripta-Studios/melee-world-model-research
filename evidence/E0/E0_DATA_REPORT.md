# E0: tubería de datos `.slp` → esquema A6 (Fox ditto)

Implementador E0, 2026-11-19. Etiquetas: REPRODUCIDO (REP, medido aquí y con comando registrado), DOC, CODE, INF, PROP.
El código está en `pilot/e0/` (README con los comandos) y los datos en `/srv/mail/melee-research-data/`.
Todas las cifras salen de los JSON de este directorio. Cada uno indica el comando que lo genera (ver §7).

## 1. Qué se hizo

1. **Entorno.** venv `/srv/mail/melee-research-data/venv-e0` con `peppi-py==0.8.6`, `zstandard==0.25.0` y
   `numpy==2.5.5`. peppi-py arrastra `pyarrow==21.0.0` e `inflection`. La lista completa está en `pip_freeze.txt`.
   peppi-py instaló y funcionó en Python 3.12 sin problemas, así que no hizo falta py-slippi. Aun así escribí
   `slpraw.py`, un lector propio mínimo del flujo de eventos según el SPEC `3a85ce8b`, por tres motivos:
   filtrar en streaming sin escribir a disco, leer el C-stick crudo (que peppi 0.8.6 no expone) y verificar peppi
   byte a byte.
2. **Descarga en streaming.** Leí `FOX/FOX_diamond-diamond_a1.tar.gz` con `tarfile` en modo `r|gz` directamente
   sobre el flujo HTTP. El lector reanuda con `Range` si se corta la conexión. El tarball nunca se escribió a disco.
   - Antes hice una prueba de 50 MB (`stream_smoke_summary.json`): 59 miembros, 5 dittos.
   - Un primer intento largo se cortó dos veces con `tarfile.ReadError`. Aún no había reintentos, así que lo
     descarté, añadí reanudación por `Range` y relancé. Los 6 `.slp` de ese intento que no estaban en el manifest
     final se borraron.
   - La pasada válida leyó **2.422.722.560 B** de los 2.532.008.241 del tarball en 59,9 s, sin reintentos HTTP.
     Paró por el tope de **1 GB de `.slp` guardados** (`stop_reason: max_saved_bytes`).
   - Miembros vistos: 2.883. Aceptados: **288**. No son ditto Fox: 2.591. No Contest: 4. No hubo ninguna partida
     demasiado corta, truncada ni con huecos. La tasa de dittos en esta carpeta es (288+4)/2.883 ≈ 10,1 % (REP).
   - Filtro: 2 humanos, ambos con ID externo Fox (2), sin teams ni Nana, GameEnd TIME! o GAME!,
     `last_frame ≥ 1500`, frames contiguos desde −123 y sha1 único.
   - Hay un registro por miembro en `stream_manifest.jsonl`: nombre, sha1, bytes, versión, escenario, semilla
     inicial y motivo de descarte. Los dittos añaden además frames, eventos y método de fin.
3. **Parser → esquema A6.** Genera un `.npz` comprimido por partida en `/srv/mail/melee-research-data/parsed/`.
   - Contenido: 31 campos post-frame por puerto, 19 pre-frame por puerto (contando `raw_cx/raw_cy`, que aquí no
     existen), 5 por frame (semilla RNG, `scene_frame_counter`, `latest_finalized`, `n_copies`) e ítems en formato
     ragged.
   - Cada campo documenta tipo, unidad, offset del SPEC, versión mínima y nivel en `schema_a6.py`, y se copia en
     `dataset_card.json → fields`.
   - Rollback: se conserva la **última** copia. Las 288 partidas se parsearon sin error en 29 s, con un pico de
     RSS de 92 MB.
   - **Verificación cruzada peppi ↔ slpraw tras LAST: OK en las 288 partidas.** Se comparan `action`, `pos_x`,
     `percent`, `joy_x`, `buttons_phys`, `trig_l_phys`, `hitlag_left` y la semilla de FrameStart (REP).
4. **Tarjeta y gate:** `dataset_card.json`.
5. **Split y deduplicación:** `splits.jsonl`.
6. **Alineación y rangos:** `adapter_checks.jsonl`.
7. **Tests:** 11 `unittest` en `pilot/e0/tests/` pasan (`tests_output.txt`). Incluyen el reparseo de una partida
   real, que da arrays idénticos, es decir, el parseo es determinista.

## 2. Cifras medidas (REP)

| Magnitud | Valor |
|---|---|
| Partidas (dittos Fox) | **288** (el plan pide ≥ 150; el objetivo era 300, pero se alcanzó antes el tope de 1 GB) |
| Frames únicos | **2.829.740** (2.794.316 con `frame_id ≥ 0`); 9.825 por partida de media, 9.756 de mediana, rango 3.476–16.017 |
| Duración jugable | mediana 160,6 s, rango 55,9–264,9 s |
| Versiones Slippi | 3.15.0: 199; 3.14.0: 89 |
| Escenarios (ID) | 31 BF: 104; 3 PS: 80; 8 YS: 66; 28 DL: 15; 32 FD: 12; 2 FoD: 11 |
| Fin / escena | 288 GAME!; 288 con major scene 8 (online) |
| Rollback | 96.371 frames con copias repetidas, el **3,41 %** de los frames; 3,57 % de filas extra; máximo 7 copias; 229/288 partidas tienen alguno; por partida, mediana 0,18 %, p90 8,5 % y máximo **62,4 %** |
| Bytes/frame (ambos puertos + cabecera + ítems) | `.slp` 354,6; arrays sin comprimir 309,1; **npz (deflate) 45,9**; zstd-3 32,7; zstd-19 25,5 (primeras 20 partidas) |
| Disco | `.slp` 1.003.332.353 B; `parsed` 129.885.401 B; venv 250.074.623 B; **total 1.383.974.956 B** (tope 3 GB) |
| Ítems | 0,54 filas de ítem por frame. Tipos más frecuentes: 210, 54, 74 y 56. No identifiqué el 210 |

### Gate del 95 %: **PASA**
El 100 % de las partidas trae velocidades (las 5, desde 3.5.0), hitstun (`misc_as` + flag 0x02 de `flags4`, desde
2.0.0) y `action_state_frame` (desde 0.2.0). Ninguno de estos campos es constante en ninguna partida.
`hitlag_left` (3.8.0) también está al 100 %. No hace falta esquema reducido.

Lo que **no** cubre el corpus (REP, `coverage_by_version`):
- `raw_y` solo existe en 3.15.0, que son 199/288 partidas (69 %).
- `raw_cx/raw_cy`, el C-stick crudo de 3.17.0, no aparece en ninguna partida.

## 3. Alineación y fuga (`adapter_checks.jsonl`)

- **Salto.** Tomé los flancos de X|Y en `PreFrame(f)` con `post(f−1)` en un estado de suelo accionable. Mido el
  desfase k hasta el inicio de KneeBend (24) en `post(f+k)`: **k = 0 en 32.616 de 33.186 casos (98,3 %)**, k = 6 en
  1 y «no aparece» en 569. En ningún caso k = 1.
  - Los casos sin KneeBend se explican por otros mandos simultáneos que ganan prioridad. Lo más frecuente es
    Dash→CatchDash (214) en 167 casos, Dash→Turn (18) en 129 y Wait→Catch (212) en 42 (diagnóstico en el JSONL).
- **Jab.** Flanco de A con stick neutro desde Wait. **k = 0 en 1.119 de 1.180 (94,8 %)**; en el resto no aparece
  el jab.
- **Fuga.** Condiciono a que `x_f` muestre el inicio de KneeBend desde un estado accionable (35.060 filas):
  - P(flanco de salto en el mando de la misma fila f) = **0,931**;
  - P(flanco en f+1) = **0,0009**;
  - tasa base por fila = 0,0133.
  Por tanto usar el mando de f como objetivo dado `x_f` es fuga: el estado «lee la respuesta». El objetivo sin
  fuga es el mando de **f+1**. Esto confirma empíricamente la convención de A6 (REP).
- **Coherencia pre/post.**
  - `pre_pos(f) == post_pos(f−1)` en el 99,57 % de las filas y `pre_percent(f) == post_percent(f−1)` en el
    99,96 %.
  - En cambio, `pre_action(f) == post_action(f−1)` solo en el **96,97 %**. Los desajustes son transiciones de fin
    de animación ya aplicadas cuando se toma el pre-frame: KneeBend→JumpF (38.721 casos), LandingFallSpecial→Wait,
    landing lag de aéreos→Wait, etc.
  - INF: el pre-frame de f se captura después de la interrupción por fin de animación de f−1. Ni `pre_action` ni
    `pre_pos` deben usarse como observación. Van marcados `training_metadata`.
- **Rangos y cuantización.**
  - Sticks procesados y C-stick: en [−1, 1] y **100 % en la rejilla 1/80**.
  - Gatillo procesado y gatillos físicos L/R: en [0, 1] y **100 % en la rejilla 1/140**.
  - Ningún bit físico no documentado.
  - La mitad baja de `buttons` (procesado) coincide con `buttons_phys` en el 98,7 % de las filas.
  - `round(joy_x·80) == raw_x` solo en el 47 % (55 % recortando a ±80): el stick procesado **no** es raw/80, lo
    que confirma la regla de melee-sim-light de no reconstruir raw desde procesado.
  - Una partida tiene solo 11 valores distintos de stick. INF: posible mando digital o caja.
- **Mantenido frente a pulsado** (botones físicos, frames mantenidos / flancos): A 221.938/29.692, B 272.134/29.620,
  X 214.278/32.807, Y 256.644/42.549, Z 75.509/11.604, L 357.813/26.394, R 331.358/29.148. Slippi guarda el estado
  mantenido. Los flancos se derivan como `b_f ∧ ¬b_{f−1}`.
- **Campos del futuro.** La lista de campos de nivel `observation` no contiene ningún campo pre-frame ni
  privilegiado (`rng_seed`, `pre_rng_seed`, `latest_finalized`, `n_copies`, `scene_frame_counter`): `passed`.
  Además, la verificación cruzada garantiza que cada fila f proviene de los eventos con `frame_id = f`.

## 4. Split y deduplicación (`splits.jsonl`)

- 0 duplicados exactos por sha1: el stream ya colapsa por sha1.
- 0 grupos de casi-duplicados, buscados por semilla inicial + sha256 de las 600 primeras filas post-cuenta atrás
  (pos, acción, stick, botones de ambos puertos).
- Ninguna semilla inicial repetida.
- Asignación con `bucket = int(sha256('A6-split-v1|'+sha1)[:8],16)/2^32`:
  - `A6-split-v1` (90/5/5): 258 / 12 / 18;
  - `A6-split-v1-E1` (umbrales 0,606 / 0,697 de EXPERIMENT_PLAN §5.3): 180 / 24 / 84.
- Con 288 partidas, el test de E1 (≥ 1.000) **no** se alcanza: hay que ampliar el corpus (§6).

## 5. Discrepancias frente a lo que A6 dedujo leyendo código

1. **peppi-py 0.8.6 no tiene `rollback_mode`.** `read_slippi(path, skip_frames)` devuelve **todas** las copias en
   orden de llegada: los ids no son monótonos, con 11.339 filas para 7.876 frames en una partida (REP). El
   `RollbackMode.FIRST` que A6 cita en slippi-ai pertenece a otra API de peppi-py. Con 0.8.6 la deduplicación es
   responsabilidad del adaptador; aquí se hace LAST con `n_copies`.
2. **Frecuencia de rollback.** Mido un 3,41 % de frames con copias, frente al «~2 %» de MIMIC que A6 citó. Es
   además muy heterogénea: una partida llega al 62 % y otra a 7 copias de un mismo frame.
3. **El elemento `metadata` de UBJSON está vacío (`{}`) en las 288 partidas** (REP,
   `metadata_items_check.txt`). No hay `lastFrame`, `startAt`, `playedOn` ni `players`. La duración sale del
   flujo de eventos. Esto refuerza que en este corpus no se puede agrupar por fecha ni por set.
4. **Bytes/frame.** A6 estimó ≈122 B sin comprimir y 12–26 B en zstd para su esquema mínimo. Este esquema guarda
   más: pre-frame completo, semillas, flags, `animation_index`, ítems y todo en f4. Ocupa 309 B sin comprimir,
   45,9 B en npz, 32,7 B en zstd-3 y 25,5 B en zstd-19. El `.slp` mide 354,6 B/frame, en línea con los «≈330+» de
   A6.
5. **C-stick crudo.** DESIGN §2.1 lo pide (≥ 3.17.0), pero no está en ninguna partida. `raw_y` (3.15.0) falta en
   el 31 %. El esquema de mandos debe usar C-stick **procesado**, que es exacto en la rejilla 1/80. El stick
   principal crudo solo puede ser obligatorio si se restringe a 3.15+.
6. **`pre_action(f) ≠ post_action(f−1)` en el 3 %** (ver §3). Ningún documento de A6 lo anticipaba. No cambia la
   convención de filas, pero sí qué campos pre-frame son observables.
7. **Tasa de dittos.** ~10 % de la carpeta FOX en diamond-diamond. Para 3.300 dittos (E1) harían falta unas
   33.000 partidas de FOX, unos 28 GB de flujo leído a esta densidad (INF a partir de 2,42 GB → 288). Con el tope
   de 1 GB de `.slp` hay que convertir y borrar cada `.slp` sobre la marcha (§6).

## 6. Limitaciones y siguientes pasos

- **El corpus es pequeño para E1.** Son 288 partidas de un solo volcado (a1) y un solo par de rangos (diamond).
  Para escalar sin superar el tope de disco, PROP: fusionar `stream_filter` y `parse_a6` para que cada ditto se
  convierta a npz/zstd al vuelo, guardando solo el sha1 y opcionalmente un `.slp` de cada N para auditoría. A
  ~46 B/frame, 3.300 partidas ocupan ≈1,5 GB en npz y ≈1,05 GB en zstd-3.
- **Fuga por set inevitable**, como dice A6: no hay `match_id`, fechas ni códigos, y la metadata está vacía.
- **Ítems.** Se guardan en formato ragged pero sin las 4 ranuras densas que pide DESIGN. El ID 210 domina y no lo
  identifiqué: puede ser un objeto de escenario.
- Faltan `instance_id` / `instance_hit_by` (3.16.0, ausentes aquí) y los eventos de escenario de 3.18.0, que
  tampoco aparecen en 3.14/3.15. Randall y las plataformas de FoD habría que calcularlos.
- **Alcance de las pruebas de alineación.** Solo cubren dos acciones de Fox (salto y jab). La generalización a
  otras acciones y personajes es INF.
- **Formato.** Para la versión escalada conviene zstd: 32,7 frente a 45,9 B/frame (−29 %).
- **Recursos.** No toqué servicios. Todo corrió con `nice -n 19` y el mayor RSS fue de 92 MB. Durante la prueba de
  50 MB la RAM disponible llegó a ~106 MB por otros procesos del servidor. El filtro pausa si `MemAvailable` baja
  de 300 MB, pero la pausa no llegó a activarse.

## 7. Comandos y artefactos

Desde `/home/kripta/melee-research`, con `D=/srv/mail/melee-research-data` y `P=$D/venv-e0/bin/python`:

| Paso | Comando | Artefacto |
|---|---|---|
| stream | `nice -n 19 $P -I pilot/e0/stream_filter.py --tarball FOX/FOX_diamond-diamond_a1.tar.gz --tarball FOX/FOX_diamond-diamond_a5.tar.gz --out-dir $D/slp --manifest evidence/E0/stream_manifest.jsonl --summary evidence/E0/stream_summary.json --max-stream-bytes 6000000000` | `stream_manifest.jsonl`, `stream_summary.json` |
| parse | `nice -n 19 $P -I pilot/e0/parse_a6.py --slp-dir $D/slp --out-dir $D/parsed --index $D/parsed_index.jsonl` (copiado a `evidence/E0/parsed_index.jsonl`) | `parsed_index.jsonl` |
| split | `nice -n 19 $P -I pilot/e0/splits.py --parsed-dir $D/parsed --out evidence/E0/splits.jsonl` | `splits.jsonl` |
| checks | `nice -n 19 $P -I pilot/e0/adapter_checks.py --parsed-dir $D/parsed --out evidence/E0/adapter_checks.jsonl` | `adapter_checks.jsonl` |
| card | `nice -n 19 $P -I pilot/e0/dataset_card.py --index evidence/E0/parsed_index.jsonl --parsed-dir $D/parsed --stream-summary evidence/E0/stream_summary.json --data-root $D --out evidence/E0/dataset_card.json` | `dataset_card.json` |
| tests | `cd pilot/e0 && $P -m unittest discover -s tests -v` | `tests_output.txt` |

Script equivalente de principio a fin: `pilot/e0/run_all.sh`.
