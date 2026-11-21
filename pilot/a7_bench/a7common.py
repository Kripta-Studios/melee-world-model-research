"""Shared helpers: thread pinning, environment capture, adaptive timing with percentiles."""
import json, os, platform, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import portable as _P  # noqa: E402  (Linux/Windows)


def pin_threads(n):
    for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[k] = str(n)
    import torch
    torch.set_num_threads(n)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    return torch


def env_info(threads):
    import torch
    def sh(c):
        try:
            return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception as e:  # noqa
            return f"ERR {e}"
    return {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "uptime": sh("uptime") if _P.LINUX else "n/a (windows)",
        "loadavg": _P.loadavg(),
        "cpu": sh("grep -m1 'model name' /proc/cpuinfo") if _P.LINUX else platform.processor(),
        "nproc": os.cpu_count(),
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "cpu_capability": torch.backends.cpu.get_cpu_capability(),
        "torch_threads": torch.get_num_threads(),
        "requested_threads": threads,
        "platform": platform.platform(),
        "mem_available_mb": _P.mem_available_mb(),
    }


def peak_rss_mb():
    return _P.peak_rss_mb()


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def timeit(fn, warmup=2, min_time=0.4, max_reps=200, min_reps=5, max_single=1.5):
    """Calls fn repeatedly; returns dict of ms stats. Stops early if a call is slow."""
    for _ in range(warmup):
        t0 = time.perf_counter(); fn(); dt = time.perf_counter() - t0
        if dt > max_single:
            break
    ts = []
    tstart = time.perf_counter()
    while len(ts) < max_reps:
        t0 = time.perf_counter_ns(); fn(); ts.append((time.perf_counter_ns() - t0) / 1e6)
        el = time.perf_counter() - tstart
        if (el > min_time and len(ts) >= min_reps) or ts[-1] / 1e3 > max_single or el > 4 * max_single:
            break
    return {"n": len(ts), "p50_ms": pct(ts, .5), "p95_ms": pct(ts, .95), "p99_ms": pct(ts, .99),
            "min_ms": min(ts), "max_ms": max(ts), "mean_ms": sum(ts) / len(ts)}


class Out:
    def __init__(self, path):
        self.f = open(path, "a")

    def w(self, rec):
        self.f.write(json.dumps(rec) + "\n"); self.f.flush()
