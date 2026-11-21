#!/usr/bin/env bash
# Uso: logrun.sh NOMBRE cmd...   -> ejecuta con nice 19 y 2 hilos, guarda stdout/stderr y una línea en commands.log
# Linux: /usr/bin/time -v y espera a avail >= 600 MB (servidor compartido).
# Windows (Git Bash): sin /proc; mide con pilot/timev.py (psutil) usando $TIMEV_PY (por defecto el python del venv
# de datos) y no espera memoria.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
L=${FLOORS_LOGS:-$HERE/../../../evidence/E0/floors/logs}
mkdir -p "$L"
name=$1; shift
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2} MKL_NUM_THREADS=${MKL_NUM_THREADS:-2} OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-2}
if [ -x /usr/bin/time ] && command -v free >/dev/null; then
  # espera a que haya >= 600 MB disponibles (máx. 30 min)
  for i in $(seq 1 180); do
    av=$(free -m | awk '/Mem:/{print $7}'); [ "$av" -ge 600 ] && break
    [ "$i" -eq 1 ] && echo "$(date -u +%FT%TZ) WAIT $name avail=${av}MB" >> "$L/commands.log"
    sleep 10
  done
  echo "$(date -u +%FT%TZ) START $name | $* | $(free -m | awk '/Mem:/{print "avail="$7"MB"}') | load=$(cut -d' ' -f1 /proc/loadavg)" >> "$L/commands.log"
  /usr/bin/time -v nice -n 19 "$@" > "$L/$name.out" 2> "$L/$name.err"
else
  TP=${TIMEV_PY:-${E0_DATA:-D:/melee-data}/venv-e0/Scripts/python.exe}
  echo "$(date -u +%FT%TZ) START $name | $* | host=$(hostname) os=windows threads=$OMP_NUM_THREADS" >> "$L/commands.log"
  "$TP" -I "$HERE/../../timev.py" "$@" > "$L/$name.out" 2> "$L/$name.err"
fi
rc=$?
rss=$(grep "Maximum resident" "$L/$name.err" | awk '{print $NF}')
wall=$(grep "Elapsed (wall" "$L/$name.err" | awk '{print $NF}')
cpu_u=$(grep "User time" "$L/$name.err" | awk '{print $NF}')
echo "$(date -u +%FT%TZ) END $name rc=$rc wall=$wall user_s=$cpu_u maxrss_kb=$rss" >> "$L/commands.log"
exit $rc
