#!/usr/bin/env bash
# Uso: logrun.sh NOMBRE cmd...   -> ejecuta con nice 19 y 2 hilos, guarda stdout/stderr y una línea en commands.log
set -uo pipefail
L=${FLOORS_LOGS:-/home/kripta/melee-research/evidence/E0/floors/logs}
mkdir -p "$L"
name=$1; shift
# espera a que haya >= 600 MB disponibles (máx. 30 min)
for i in $(seq 1 180); do
  av=$(free -m | awk '/Mem:/{print $7}'); [ "$av" -ge 600 ] && break
  [ "$i" -eq 1 ] && echo "$(date -u +%FT%TZ) WAIT $name avail=${av}MB" >> "$L/commands.log"
  sleep 10
done
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
echo "$(date -u +%FT%TZ) START $name | $* | $(free -m | awk '/Mem:/{print "avail="$7"MB"}') | load=$(cut -d' ' -f1 /proc/loadavg)" >> "$L/commands.log"
/usr/bin/time -v nice -n 19 "$@" > "$L/$name.out" 2> "$L/$name.err"
rc=$?
rss=$(grep "Maximum resident" "$L/$name.err" | awk '{print $NF}')
wall=$(grep "Elapsed (wall" "$L/$name.err" | awk '{print $NF}')
cpu_u=$(grep "User time" "$L/$name.err" | awk '{print $NF}')
echo "$(date -u +%FT%TZ) END $name rc=$rc wall=$wall user_s=$cpu_u maxrss_kb=$rss" >> "$L/commands.log"
exit $rc
