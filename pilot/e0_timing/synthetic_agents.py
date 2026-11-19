"""Synthetic agents with controlled latency for the RT-strict wrapper (E0). They do no Melee work.

All return a command dict; `latency` is the target compute time of one decision.
  zero      : returns at once (measures the wrapper's own overhead)
  const     : sleeps a constant time (GIL released, like a torch forward)
  heavytail : lognormal body + rare spikes (models GC / page faults / contention)
  exceed    : always longer than the budget
  anytime   : refines in 1 ms slices, publishes best-so-far after each, stops early if ctx.expired() is not honoured
  pycpu     : pure-Python busy loop (HOLDS the GIL: worst case for the thread backend), with rare long calls
  crash     : raises every N-th call
"""
import math
import random
import time

now = time.perf_counter_ns


def _cmd(frame, tag):
    return {"buttons": frame & 0xFF, "main": (frame % 161 - 80, 0), "c": (0, 0), "trig": (0, 0), "tag": tag}


def _sleep_until(t_ns):
    while True:
        left = t_ns - now()
        if left <= 0:
            return
        time.sleep(left / 1e9 if left > 2e5 else 0)


def _spin_until(t_ns):  # pure Python, holds the GIL
    x = 0
    while now() < t_ns:
        x += 1
    return x


class Synthetic:
    def __init__(self, kind, ms=4.0, seed=0, spike_p=0.02, spike_ms=(20.0, 40.0), sigma=0.35, crash_every=50,
                 honour_deadline=False):
        self.kind, self.ms, self.rng = kind, ms, random.Random(seed)
        self.spike_p, self.spike_ms, self.sigma, self.crash_every = spike_p, spike_ms, sigma, crash_every
        self.honour, self.calls = honour_deadline, 0

    def target_ms(self):
        k, r = self.kind, self.rng
        if k == "zero":
            return 0.0
        if k in ("const", "exceed", "anytime", "crash"):
            return self.ms
        if k in ("heavytail", "pycpu"):
            if r.random() < self.spike_p:
                return r.uniform(*self.spike_ms)
            return self.ms * math.exp(self.sigma * r.gauss(0, 1) - self.sigma ** 2 / 2)
        raise ValueError(k)

    def decide(self, obs, ctx):
        self.calls += 1
        f = obs["frame"]
        t0 = now()
        ms = self.target_ms()
        if self.kind == "zero":
            return _cmd(f, "zero")
        if self.kind == "crash" and self.calls % self.crash_every == 0:
            raise RuntimeError("synthetic crash")
        if self.kind == "pycpu":
            _spin_until(t0 + int(ms * 1e6))
            return _cmd(f, "pycpu")
        if self.kind == "anytime":
            end = t0 + int(ms * 1e6)
            it = 0
            while now() < end:
                _sleep_until(min(end, now() + 1_000_000))
                it += 1
                ctx.publish(_cmd(f, f"partial{it}"))
                if self.honour and ctx.expired():
                    return _cmd(f, f"stopped{it}")
            return _cmd(f, "anytime_final")
        _sleep_until(t0 + int(ms * 1e6))
        return _cmd(f, self.kind)


AGENTS = {  # name -> kwargs (budget 10 ms by default)
    "zero": dict(kind="zero"),
    "const4": dict(kind="const", ms=4.0),
    "heavytail": dict(kind="heavytail", ms=4.0, spike_p=0.02, spike_ms=(12.0, 30.0)),
    "exceed14": dict(kind="exceed", ms=14.0),
    "anytime13": dict(kind="anytime", ms=13.0),
    "pycpu": dict(kind="pycpu", ms=5.0, spike_p=0.03, spike_ms=(12.0, 20.0)),
}


def make(name, seed=0):
    return Synthetic(seed=seed, **AGENTS[name])
