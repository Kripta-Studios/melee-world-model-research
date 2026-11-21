#!/usr/bin/env bash
# Relanzamiento de las corridas abortadas por el watchdog de RSS (tras reducir la memoria de Block).
set -uo pipefail
cd "$(dirname "$0")/../../.."
pilot/e0/models/logrun.sh smoke_q_s1 "${PY:-python3}" pilot/e0/models/smoke.py --model q --seed 1 --games 40 --epochs 2
pilot/e0/models/logrun.sh smoke_w0s_s2 "${PY:-python3}" pilot/e0/models/smoke.py --model w0s --seed 2 --games 40 --epochs 2
pilot/e0/models/logrun.sh smoke_q_s2 "${PY:-python3}" pilot/e0/models/smoke.py --model q --seed 2 --games 40 --epochs 2
