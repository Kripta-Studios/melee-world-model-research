#!/usr/bin/env bash
# E0 timing driver (steps 2 and 3 of deliverables/FINAL_RECOMMENDATION.md). System python3, no venv, no installs.
# Sequential, nice -n 19, <= 2 torch threads, each run capped at 175 s, RSS guard ~1.05 GB inside the scripts.
# Before every run: waits until MemAvailable >= MIN_AVAIL_MB (and load1 < MAX_LOAD, for at most WAIT_S), and logs
# `uptime` + `free -m` to commands.log.
# Usage: bash run_e0_timing.sh {tests|wrapper|present|e2e|jit} [REPS]
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
EV="$HERE/../../evidence/E0/timing"
RAW="${E0_RAW:-/srv/mail/melee-research-data/e0_timing_raw}"
mkdir -p "$EV" "$RAW"
LOG="$EV/commands.log"
MIN_AVAIL_MB="${MIN_AVAIL_MB:-900}"; MAX_LOAD="${MAX_LOAD:-16}"; WAIT_S="${WAIT_S:-600}"
REPS="${2:-3}"

guard() {
  local t0=$SECONDS
  while :; do
    local av ld; av=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo); ld=$(cut -d' ' -f1 /proc/loadavg)
    if (( av >= MIN_AVAIL_MB )) && awk -v l="$ld" -v m="$MAX_LOAD" 'BEGIN{exit !(l < m)}'; then return 0; fi
    if (( SECONDS - t0 > WAIT_S )) && (( av >= 700 )); then
      echo "$(date -u +%FT%TZ) WAIT-TIMEOUT running anyway avail=${av}MB load1=$ld" >> "$LOG"; return 0; fi
    sleep 5
  done
}
run() {  # $1 threads, rest = command (relative to $HERE)
  local th="$1"; shift
  guard
  echo "$(date -u +%FT%TZ) START $* | uptime: $(uptime) | free: $(free -m | awk 'NR==2{print "used="$3" avail="$7}')" >> "$LOG"
  ( cd "$HERE" && OMP_NUM_THREADS=$th MKL_NUM_THREADS=$th OPENBLAS_NUM_THREADS=$th timeout 175 nice -n 19 python3 -I "$@" ) >> "$EV/stderr.log" 2>&1
  local rc=$?
  echo "$(date -u +%FT%TZ) END rc=$rc $* | $(cat /proc/loadavg)" >> "$LOG"
}

phase="${1:-}"
case "$phase" in
  tests)
    guard
    echo "$(date -u +%FT%TZ) START unittest | uptime: $(uptime)" >> "$LOG"
    ( cd "$HERE/../.." && OMP_NUM_THREADS=1 timeout 175 nice -n 19 python3 -I -m unittest discover -s pilot/e0_timing/tests -v ) > "$EV/tests.log" 2>&1
    echo "$(date -u +%FT%TZ) END rc=$? unittest" >> "$LOG" ;;
  wrapper)  # Task A: synthetic agents in the fake 60 Hz loop. 1800 frames = 30 s per run.
    for rep in $(seq 0 $((REPS-1))); do
      for ag in zero const4 heavytail exceed14 anytime13 pycpu; do for m in thread process; do
        run 1 fake_runner.py --agent $ag --mode $m --frames 1800 --rep $rep --out "$RAW/wrapper.jsonl"
      done; done
      run 1 fake_runner.py --agent pycpu --mode thread --switch_ms 0.5 --frames 1800 --rep $rep --out "$RAW/wrapper.jsonl"
      run 1 fake_runner.py --agent zero --mode inline --frames 1800 --rep $rep --out "$RAW/wrapper.jsonl"
    done ;;
  present)  # Task B: predictor of the present, random weights.
    for rep in $(seq 0 $((REPS-1))); do for th in 1 2; do for core in mlp gru tx tx_kv; do for impl in ref fast; do
      run $th bench_present.py --core $core --threads $th --impl $impl --rep $rep --n 150 --out "$EV/present_raw.jsonl"
    done; done; done; done ;;
  e2e)  # Task B, whole route: predictor inside RT-strict inside the fake loop (thread backend).
    for rep in $(seq 0 $((REPS-1))); do for th in 1 2; do
      for spec in gru:6:open tx_kv:12:closed; do
        run $th fake_runner.py --agent present:$spec:$th:fast --mode thread --frames 1200 --rep $rep --out "$RAW/e2e.jsonl"
      done
    done; done ;;
  jit)  # exploratory: TorchScript trace+freeze of one closed-loop rollout step (inductor breaches the RAM cap)
    for rep in $(seq 0 $((REPS-1))); do for th in 1 2; do for core in gru tx_kv mlp; do
      guard; echo "$(date -u +%FT%TZ) START compile_probe $th $core jit | uptime: $(uptime)" >> "$LOG"
      ( cd "$HERE" && OMP_NUM_THREADS=$th timeout 175 nice -n 19 python3 -I compile_probe.py $th $core jit ) 2>>"$EV/stderr.log" | grep '^{' >> "$EV/jit_probe.jsonl"
      echo "$(date -u +%FT%TZ) END compile_probe" >> "$LOG"
    done; done; done ;;
  *) echo "usage: $0 {tests|wrapper|present|e2e} [REPS]"; exit 2 ;;
esac
