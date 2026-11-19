#!/usr/bin/env bash
# 3 semillas × {W0-S, q}, secuencial, con logrun (nice 19, 2 hilos, espera si avail < 600 MB).
set -uo pipefail
cd "$(dirname "$0")/../../.."
G=${SMOKE_GAMES:-40}; E=${SMOKE_EPOCHS:-2}
for s in 0 1 2; do
  for m in w0s q; do
    pilot/e0/models/logrun.sh smoke_${m}_s$s python3 pilot/e0/models/smoke.py --model $m --seed $s --games $G --epochs $E
  done
done
