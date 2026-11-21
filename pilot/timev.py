"""Sustituto mínimo de `/usr/bin/time -v` para Windows (requiere psutil).

Uso: python timev.py cmd args...   -> ejecuta cmd, hereda stdout/stderr y al final escribe en stderr las mismas
líneas que GNU time que leen los scripts (`User time`, `Elapsed (wall clock)`, `Maximum resident set size`).
El pico de memoria es el máximo del working set del proceso hijo y sus descendientes, muestreado cada 0,2 s
(en el hijo directo se usa además peak_wset, que es exacto).
"""
import subprocess
import sys
import time

import psutil

t0 = time.perf_counter()
p = subprocess.Popen(sys.argv[1:])
ps = psutil.Process(p.pid)
peak = 0
user = {}
while p.poll() is None:
    try:
        procs = [ps] + ps.children(recursive=True)
        tot = 0
        for q in procs:
            try:
                mi = q.memory_info()
                tot += mi.rss
                user[q.pid] = q.cpu_times().user
                if q.pid == ps.pid:
                    peak = max(peak, getattr(mi, "peak_wset", 0))
            except psutil.Error:
                pass
        peak = max(peak, tot)
    except psutil.Error:
        pass
    time.sleep(0.2)
wall = time.perf_counter() - t0
rc = p.returncode
sys.stderr.write(f"\tUser time (seconds): {sum(user.values()):.2f}\n")
sys.stderr.write(f"\tElapsed (wall clock) time (h:mm:ss or m:ss): {int(wall // 60)}:{wall % 60:05.2f}\n")
sys.stderr.write(f"\tMaximum resident set size (kbytes): {peak // 1024}\n")
sys.stderr.write(f"\tExit status: {rc}\n")
sys.exit(rc)
