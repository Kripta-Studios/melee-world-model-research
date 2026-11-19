# E0: tubería `.slp` → esquema A6 (Fox ditto)

Este directorio guarda solo código. Los datos van en `$E0_DATA` (por defecto `/srv/mail/melee-research-data`) y los
resultados pequeños en `evidence/E0/`.

| Script | Qué hace |
|---|---|
| `slpraw.py` | Lector propio mínimo del flujo de eventos (SPEC slippi-wiki `3a85ce8b`). Lo usan el filtro en streaming, la extracción del C-stick crudo (peppi-py 0.8.6 no lo expone) y la verificación cruzada byte a byte |
| `stream_filter.py` | Lee el flujo HTTP de un tarball de `erickfm/melee-ranked-replays@ef54ddc2` con `tarfile` en modo `r\|gz` y nunca guarda el tarball. Si la conexión se corta, reanuda con `Range`. Guarda solo dittos Fox-Fox válidos, con nombre `<sha1>.slp` |
| `parse_a6.py` | Convierte cada partida a un `.npz` comprimido. Usa peppi-py (Arrow), se queda con la copia LAST de cada frame si hay rollback y cuenta las copias. Añade el C-stick crudo vía slpraw y contrasta 8 campos con slpraw |
| `schema_a6.py` | Fuente única de los campos: dtype, unidad, offset en el SPEC, versión mínima y nivel (observation / control / training_metadata / simulator_snapshot) |
| `splits.py` | Deduplica por sha1 y por (semilla inicial + hash de las primeras 600 filas) y asigna el split por hash del sha1 (`A6-split-v1` y `A6-split-v1-E1`) |
| `adapter_checks.py` | Test empírico de alineación y fuga, coherencia pre/post, rangos y cuantización, pulsado frente a mantenido, y que no entran campos privilegiados en la observación |
| `dataset_card.py` | Tarjeta del dataset, cobertura por versión, bytes/frame medidos y gate del 95 % |
| `tests/` | `unittest`: `.slp` sintéticos (cabecera, rollback LAST, clasificador), checks y splits. Sobre datos reales comprueba que reparsear da arrays idénticos |

## Reproducir desde cero

Desde la raíz del repo (`/home/kripta/melee-research`):

```bash
bash pilot/e0/run_all.sh
```

O paso a paso, que es lo que se ejecutó el 2026-11-19:

```bash
D=/srv/mail/melee-research-data; P=$D/venv-e0/bin/python
python3 -m venv $D/venv-e0 && $D/venv-e0/bin/pip install --no-cache-dir peppi-py zstandard numpy
nice -n 19 $P -I pilot/e0/stream_filter.py --tarball FOX/FOX_diamond-diamond_a1.tar.gz \
   --tarball FOX/FOX_diamond-diamond_a5.tar.gz --out-dir $D/slp \
   --manifest evidence/E0/stream_manifest.jsonl --summary evidence/E0/stream_summary.json \
   --max-stream-bytes 6000000000
nice -n 19 $P -I pilot/e0/parse_a6.py --slp-dir $D/slp --out-dir $D/parsed --index evidence/E0/parsed_index.jsonl
nice -n 19 $P -I pilot/e0/splits.py --parsed-dir $D/parsed --out evidence/E0/splits.jsonl
nice -n 19 $P -I pilot/e0/adapter_checks.py --parsed-dir $D/parsed --out evidence/E0/adapter_checks.jsonl
nice -n 19 $P -I pilot/e0/dataset_card.py --index evidence/E0/parsed_index.jsonl --parsed-dir $D/parsed \
   --stream-summary evidence/E0/stream_summary.json --data-root $D --out evidence/E0/dataset_card.json
cd pilot/e0 && $P -m unittest discover -s tests -v
```

Para probar solo el parser con los primeros ~50 MB del flujo, añade `--max-stream-bytes 50000000` (y `--dry-run`
si no quieres escribir los `.slp`).

## Formato de un `.npz`

- Campos globales con forma `[T]`: `frame_id`, `n_copies`, `rng_seed`, `scene_frame_counter`, `latest_finalized`.
- Campos por puerto con forma `[T, 2]`: los post-frame (`action`, `pos_x`, …, `hitstun_left`, `hitlag_left`) y los
  pre-frame (`joy_x`, `buttons_phys`, `trig_l_phys`, `raw_x`, …).
- Ítems en formato ragged: `item_row` indica la fila y le siguen `item_*`.
- `meta_json`: sha1, versión, escenario, puertos, rollback, campos presentes y resultado de la verificación cruzada.

Convención de filas (verificada en `adapter_checks.jsonl`): la fila `f` contiene `PostFrame(f)` y `PreFrame(f)`, y
el mando de `f` ya actuó sobre el estado de `f`. El objetivo de imitación sin fuga dado `x_{≤f}` es el mando de
`f+1`. Los frames con `frame_id < 0` corresponden a la cuenta atrás y no son accionables.

Lectura: `a6io.load(path) -> (arrays, meta)`.
