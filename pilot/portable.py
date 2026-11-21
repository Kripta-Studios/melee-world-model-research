"""Sustitutos portables (Linux / Windows) de /proc, `resource` y `os.getloadavg` usados en los pilotos.

En Linux devuelve exactamente lo mismo que el código original (/proc/meminfo, ru_maxrss, /proc/loadavg).
En Windows usa psutil: memoria disponible del sistema, pico de working set del proceso y, como no hay loadavg,
el porcentaje de CPU del sistema en una ventana corta (etiquetado como tal).
"""
from __future__ import annotations

import os
import sys

LINUX = sys.platform.startswith("linux")

try:
    import psutil  # noqa: F401
except ImportError:  # Windows sin psutil: ctypes mínimo (pico/actual de working set y memoria libre)
    psutil = None
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class _PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("a", ctypes.c_size_t), ("b", ctypes.c_size_t), ("c", ctypes.c_size_t),
                        ("d", ctypes.c_size_t), ("e", ctypes.c_size_t), ("f", ctypes.c_size_t)]

        class _MSX(ctypes.Structure):
            _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("x1", ctypes.c_ulonglong), ("x2", ctypes.c_ulonglong), ("x3", ctypes.c_ulonglong),
                        ("x4", ctypes.c_ulonglong), ("x5", ctypes.c_ulonglong)]

        def _pmc():
            c = _PMC(); c.cb = ctypes.sizeof(c)
            f = ctypes.windll.kernel32.K32GetProcessMemoryInfo
            f.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
            f(wintypes.HANDLE(-1),
                                                     ctypes.byref(c), c.cb)
            return c

        def _avail():
            m = _MSX(); m.dwLength = ctypes.sizeof(m)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullAvailPhys


def mem_available_mb() -> int:
    if LINUX:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
        return 10**6
    if psutil is None:
        return int(_avail() // (1024 * 1024))
    return int(psutil.virtual_memory().available // (1024 * 1024))


def peak_rss_mb() -> float:
    if LINUX or sys.platform == "darwin":
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    if psutil is None:
        return _pmc().PeakWorkingSetSize / (1024 * 1024)
    mi = psutil.Process().memory_info()
    return getattr(mi, "peak_wset", mi.rss) / (1024 * 1024)


def rss_mb() -> float:
    if LINUX:
        for line in open("/proc/self/status"):
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024
    if psutil is None:
        return _pmc().WorkingSetSize / (1024 * 1024)
    return psutil.Process().memory_info().rss / (1024 * 1024)


def loadavg() -> str:
    if LINUX:
        return open("/proc/loadavg").read().strip()
    if psutil is None:
        return "win n/a"
    return f"win cpu_percent={psutil.cpu_percent(interval=0.1)} ncpu={os.cpu_count()}"
