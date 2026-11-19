#!/usr/bin/env bash
# A7 bench driver. Sequential (never more than 3 compute threads at once), each run capped at 120 s, nice 10.
# Usage: bash run_all.sh {infer|sigreg|train|all}
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/../../evidence/A7/measurements"
mkdir -p "$OUT"
LOG="$OUT/commands.log"
run() {  # $1 = output file, rest = python args
  local f="$1"; shift
  local cmd="timeout 120 nice -n 10 python3 -I $HERE/$*"
  echo "$(date -u +%FT%TZ) START $cmd -> $f | $(cat /proc/loadavg)" >> "$LOG"
  eval "$cmd --out $OUT/$f" >> "$OUT/stderr.log" 2>&1
  local rc=$?
  echo "$(date -u +%FT%TZ) END rc=$rc $cmd | $(cat /proc/loadavg)" >> "$LOG"
}
phase="${1:-all}"
if [[ $phase == infer || $phase == all ]]; then
  for th in 1 3; do for arch in mlp gru tx; do for tier in 1M 5M 15M; do
    run infer.jsonl "bench_infer.py --arch $arch --tier $tier --threads $th --budget_s 70"
  done; done; done
fi
if [[ $phase == sigreg || $phase == all ]]; then
  for th in 1 3; do run sigreg.jsonl "bench_sigreg.py --threads $th"; done
fi
if [[ $phase == train || $phase == all ]]; then
  for arch in mlp gru tx; do for tier in 1M 5M 15M; do for H in 8 32; do
    run train.jsonl "bench_train.py --arch $arch --tier $tier --threads 3 --H $H --B 64 --budget_s 35 --max_steps 15"
  done; done; done
  for arch in mlp gru tx; do
    run train.jsonl "bench_train.py --arch $arch --tier 5M --threads 1 --H 8 --B 64 --budget_s 35 --max_steps 10"
  done
  for arch in mlp gru tx; do for tier in 1M 15M; do
    run train.jsonl "bench_train.py --arch $arch --tier $tier --threads 3 --H 8 --B 64 --budget_s 35 --max_steps 15 --no_sigreg"
  done; done
fi
# Phase added after the first train pass: configs that crossed 950 MB RSS at B=64 (aborted after 1 step) are
# re-measured with a smaller batch so that >=10 steps fit under the 1 GB cap.
if [[ $phase == train_small ]]; then
  for cfg in "gru 5M 16" "tx 5M 16" "gru 15M 8" "mlp 15M 8" "tx 15M 8"; do
    set -- $cfg
    run train.jsonl "bench_train.py --arch $1 --tier $2 --threads 3 --H 8 --B $3 --budget_s 40 --max_steps 12"
    run train.jsonl "bench_train.py --arch $1 --tier $2 --threads 3 --H 8 --B $3 --budget_s 40 --max_steps 12 --no_sigreg"
  done
  run train.jsonl "bench_train.py --arch tx --tier 5M --threads 3 --H 32 --B 16 --budget_s 40 --max_steps 12"
fi
