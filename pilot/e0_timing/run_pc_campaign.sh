#!/usr/bin/env bash
# Campaña de latencia en el PC (Windows, Git Bash). Escribe en evidence/E0/timing/pc/ para no mezclar con el servidor.
# Uso: PY=<python con torch> bash pilot/e0_timing/run_pc_campaign.sh [REPS]
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
EV="$HERE/../../evidence/E0/timing/pc"
RAW="${E0_RAW:-D:/melee-data/e0_timing_raw_pc}"
mkdir -p "$EV" "$RAW"
REPS="${1:-3}"
LOG="$EV/commands.log"
run() {  # $1 hilos, resto = comando relativo a $HERE
  local th="$1"; shift
  echo "$(date -u +%FT%TZ) START th=$th $*" >> "$LOG"
  ( cd "$HERE" && OMP_NUM_THREADS=$th MKL_NUM_THREADS=$th timeout 300 "${PY:-python3}" -X utf8 -I "$@" ) >> "$EV/stderr.log" 2>&1
  echo "$(date -u +%FT%TZ) END rc=$? $*" >> "$LOG"
}
# 1) envoltorio 60 Hz (solo hilo e inline: el modo proceso no funciona en Windows todavía)
for rep in $(seq 0 $((REPS-1))); do
  for ag in zero const4 heavytail exceed14 anytime13 pycpu; do
    run 1 fake_runner.py --agent $ag --mode thread --frames 1800 --rep $rep --out "$RAW/wrapper.jsonl"
  done
  run 1 fake_runner.py --agent zero --mode inline --frames 1800 --rep $rep --out "$RAW/wrapper.jsonl"
done
# 2) predictor del presente: CPU rollout (4 núcleos × 2 impl × 1-2 hilos) y directo; GPU rollout y directo
for rep in $(seq 0 $((REPS-1))); do
  for th in 1 2; do
    for core in mlp gru tx tx_kv; do for impl in ref fast; do
      run $th bench_present.py --core $core --threads $th --impl $impl --rep $rep --n 150 --out "$EV/present_raw.jsonl"
    done; done
    for core in mlp gru tx_kv; do
      run $th bench_present.py --core $core --threads $th --impl fast --mode direct --rep $rep --n 150 --out "$EV/present_raw.jsonl"
    done
  done
  for core in gru tx_kv; do
    run 1 bench_present.py --core $core --threads 1 --impl fast --device cuda --rep $rep --n 150 --out "$EV/present_raw.jsonl"
    run 1 bench_present.py --core $core --threads 1 --impl fast --device cuda --mode direct --rep $rep --n 150 --out "$EV/present_raw.jsonl"
  done
done
echo "$(date -u +%FT%TZ) CAMPAIGN DONE" >> "$LOG"
