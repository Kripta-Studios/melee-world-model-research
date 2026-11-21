#!/usr/bin/env bash
# Reproduce E0 desde cero. Uso: bash pilot/e0/run_all.sh   (desde la raíz del repo)
set -euo pipefail
D=${E0_DATA:-/srv/mail/melee-research-data}
E=evidence/E0
P=$D/venv-e0/bin/python; [ -x "$P" ] || [ ! -x "$D/venv-e0/Scripts/python.exe" ] || P=$D/venv-e0/Scripts/python.exe  # Windows
export OMP_NUM_THREADS=2

# 1. venv
[ -x "$P" ] || { python3 -m venv "$D/venv-e0"; "$D/venv-e0/bin/pip" install --no-cache-dir peppi-py==0.8.6 zstandard==0.25.0 numpy==2.5.5; }
"$P" -m pip freeze > $E/pip_freeze.txt

# 2. streaming + filtro de dittos (nada del tarball se guarda)
rm -f $E/stream_manifest.jsonl
nice -n 19 $P -X utf8 -I pilot/e0/stream_filter.py \
  --tarball FOX/FOX_diamond-diamond_a1.tar.gz --tarball FOX/FOX_diamond-diamond_a5.tar.gz \
  --out-dir $D/slp --manifest $E/stream_manifest.jsonl --summary $E/stream_summary.json \
  --max-accepted 300 --max-saved-bytes 1000000000 --max-stream-bytes 6000000000

# 3. parser -> esquema A6 (npz por partida)
nice -n 19 $P -X utf8 -I pilot/e0/parse_a6.py --slp-dir $D/slp --out-dir $D/parsed --index $E/parsed_index.jsonl

# 4-6. splits/dedup, comprobaciones del adaptador, tarjeta del dataset
nice -n 19 $P -X utf8 -I pilot/e0/splits.py --parsed-dir $D/parsed --out $E/splits.jsonl
nice -n 19 $P -X utf8 -I pilot/e0/adapter_checks.py --parsed-dir $D/parsed --out $E/adapter_checks.jsonl
nice -n 19 $P -X utf8 -I pilot/e0/dataset_card.py --index $E/parsed_index.jsonl --parsed-dir $D/parsed \
  --stream-summary $E/stream_summary.json --data-root $D --out $E/dataset_card.json

# 7. tests
(cd pilot/e0 && E0_DATA=$D $P -X utf8 -m unittest discover -s tests -v)
