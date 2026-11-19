"""Fake 60 Hz blocking loop that mimics melee-llm `runner.play` (melee_llm/runner.py @7e179081, L279-300):

    while ...:
        gs = console.step()          # flushes the controllers (mando de t-1 enviado), blocks until frame t is ready
        for a in stepping: a.begin(gs)
        for a in stepping: a.step(gs)
        pub.frame(gs) / observer

FakeConsole.step(): flush -> "emulate" for `emu_ms` (sleep: there is no Dolphin here) -> wait for the next 60 Hz
tick (realtime pacing with blocking_input: the emulator never runs ahead, and if the agents are late the frame
simply comes later, i.e. the game slows down instead of dropping input). Port 1 = agent under test (RT-strict),
port 2 = a trivial unwrapped agent, both called in runner order.

CLI: python3 -I fake_runner.py --agent heavytail --mode thread --frames 1800 --out raw.jsonl
"""
import argparse, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rt_strict import RTStrict, now  # noqa: E402
import synthetic_agents  # noqa: E402

FRAME_NS = int(1e9 / 60)


class FakeController:
    def __init__(self):
        self.state, self.flushed = None, None

    def write(self, cmd):
        self.state = cmd

    def flush(self):
        self.flushed = self.state


class FakeConsole:
    def __init__(self, controllers, emu_ms=3.3, listeners=()):
        self.controllers, self.emu_ns = controllers, int(emu_ms * 1e6)
        self.listeners = listeners
        self.frame = -124
        self.t0 = None
        self.lateness = []  # ns the frame came after its nominal tick (0 when on time)

    def step(self):
        t = now()
        if self.t0 is None:
            self.t0 = t
        else:  # libmelee: controller.flush() happens inside console.step()
            for c in self.controllers:
                c.flush()
            for l in self.listeners:
                l.on_send(t, self.frame + 1)
        self.frame += 1
        tick = self.t0 + (self.frame + 124) * FRAME_NS
        ready = max(tick, t + self.emu_ns)
        while True:
            left = ready - now()
            if left <= 0:
                break
            time.sleep(left / 1e9 if left > 3e5 else 0)
        t_cap = now()
        self.lateness.append(max(0, t_cap - tick))
        if t_cap - tick > FRAME_NS:  # fell behind: re-anchor so that one spike does not cascade (slow game)
            self.t0 = t_cap - (self.frame + 124) * FRAME_NS
        return {"frame": self.frame, "capture_ts_ns": t_cap,
                "players": {1: {"x": 0.0}, 2: {"x": 0.0}}}


class Noop:
    def begin(self, gs):
        pass

    def step(self, gs):
        pass


def run_loop(wrapped, frames, emu_ms=3.3, other=None, loadavg_every_s=1.0):
    c1, c2 = FakeController(), FakeController()
    wrapped.setup(c1)
    console = FakeConsole([c1, c2], emu_ms=emu_ms, listeners=[wrapped])
    stepping = [wrapped, other or Noop()]
    loads, t_last = [], 0.0
    iter_ns = []
    while console.frame < frames - 124:
        gs = console.step()
        t_it = now()
        for a in stepping:
            if a is wrapped:
                a.begin(gs, capture_ts_ns=gs["capture_ts_ns"])
            else:
                a.begin(gs)
        for a in stepping:
            a.step(gs)
        iter_ns.append(now() - t_it)
        if time.monotonic() - t_last > loadavg_every_s:
            t_last = time.monotonic()
            with open("/proc/loadavg") as fh:
                loads.append((time.time(), fh.read().split()[0]))
    trace = wrapped.close()
    return trace, {"lateness_ns": console.lateness, "agent_section_ns": iter_ns, "loadavg_samples": loads}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True, help="one of synthetic_agents.AGENTS or present:<core>:<D>:<q>[:threads]")
    ap.add_argument("--mode", default="thread", choices=("thread", "process", "inline"))
    ap.add_argument("--budget_ms", type=float, default=10.0)
    ap.add_argument("--frames", type=int, default=1800)
    ap.add_argument("--emu_ms", type=float, default=3.3)
    ap.add_argument("--switch_ms", type=float, default=None, help="sys.setswitchinterval (GIL) in ms")
    ap.add_argument("--chain", default="best_so_far,repeat_last,neutral")
    ap.add_argument("--rep", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.switch_ms is not None:
        sys.setswitchinterval(a.switch_ms / 1000)
    label = f"{a.agent}|{a.mode}|sw={a.switch_ms}|rep{a.rep}"
    if a.agent.startswith("present:"):
        import present_agent
        factory = lambda: present_agent.from_spec(a.agent, seed=a.rep)
    else:
        factory = lambda: synthetic_agents.make(a.agent, seed=a.rep)
    w = RTStrict(factory=factory, budget_ms=a.budget_ms, mode=a.mode,
                 chain=a.chain.split(","), label=label)
    up0 = open("/proc/loadavg").read().strip()
    trace, aux = run_loop(w, a.frames, emu_ms=a.emu_ms)
    with open(a.out, "a") as f:
        f.write(json.dumps({"kind": "run", "label": label, "agent": a.agent, "mode": a.mode, "rep": a.rep,
                            "budget_ms": a.budget_ms, "frames": a.frames, "emu_ms": a.emu_ms,
                            "switch_ms": a.switch_ms, "chain": a.chain, "loadavg_start": up0,
                            "loadavg_end": open("/proc/loadavg").read().strip(),
                            "loadavg_samples": aux["loadavg_samples"],
                            "frame_lateness_ms": [x / 1e6 for x in aux["lateness_ns"]],
                            "agent_section_ms": [x / 1e6 for x in aux["agent_section_ns"]]}) + "\n")
        for r in trace:
            f.write(json.dumps({"kind": "decision", **r}) + "\n")


if __name__ == "__main__":
    main()
