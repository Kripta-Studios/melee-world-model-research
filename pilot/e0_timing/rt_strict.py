"""RT-strict: per-frame deadline wrapper for an every-frame agent (E0, step 2 of FINAL_RECOMMENDATION).

PROP. Pattern taken from melee-llm bot-writer (`melee_llm/botwriter/agent.py` @7e179081, L79 `budget_ms=16.0`,
`begin()` L150-167 sends the frame and starts the budget, `step()` L169-186 waits only for what is left of it, a late
answer keeps the previous inputs and the stale answer is dropped). Differences, declared:
  * the work runs in a worker THREAD (default) or a worker PROCESS (`mode="process"`, like BotAgent);
  * a declared fallback chain when the deadline passes. Default (encargo E0):
        L1 best_so_far : the partial answer the current job published through `ctx.publish()`
        L2 repeat_last : repeat the last command written to the controller (at most `max_repeat` frames in a row)
        L3 neutral     : release everything
    Optional, off by default: `late_result` (the most recent COMPLETED answer for an older observation, if its age is
    <= `late_max_age` frames) and `cheap_policy` (a callable run inline on the aged observation, DESIGN §3.1 L2).
  * every decision leaves one trace record with the timing fields of `06_EXPERIMENT_PROTOCOL.md` L88.

Agent contract (synthetic agents and PresentPredictorAgent alike):
    decide(obs, ctx) -> command          # command: any picklable object (dict of buttons/sticks)
    ctx.deadline_ns                      # perf_counter_ns() deadline of this frame
    ctx.expired() -> bool                # cooperative early stop (anytime agents)
    ctx.publish(command)                 # best-so-far partial answer (L1)

Clock: time.perf_counter_ns() (CLOCK_MONOTONIC on Linux, same clock across fork()ed processes on one host).
"""
from __future__ import annotations

import multiprocessing as mp
import threading
import time
import traceback
from collections import deque
import sys

if sys.platform == "win32":
    # Windows: los waits con timeout (Condition.wait, Pipe.poll) van atados al temporizador del sistema (15,6 ms por
    # defecto), lo que rompía el plazo por frame en ~11 ms. 1 ms mientras viva el proceso (se restaura al salir).
    import ctypes
    ctypes.windll.winmm.timeBeginPeriod(1)

NEUTRAL = {"buttons": 0, "main": (0, 0), "c": (0, 0), "trig": (0, 0)}
DEFAULT_CHAIN = ("best_so_far", "repeat_last", "neutral")
now = time.perf_counter_ns


class Ctx:
    __slots__ = ("frame", "deadline_ns", "_pub")

    def __init__(self, frame, deadline_ns, pub):
        self.frame, self.deadline_ns, self._pub = frame, deadline_ns, pub

    def expired(self):
        return now() >= self.deadline_ns

    def publish(self, command):
        self._pub(self.frame, command)


# ----------------------------------------------------------------------------------------------- thread backend
class _ThreadWorker:
    """Single worker thread with a one-slot mailbox: a new frame replaces a job that has not started yet."""

    def __init__(self, agent):
        self.agent = agent
        self.cv = threading.Condition()
        self.job = None            # (frame, obs, deadline_ns) waiting to start
        self.busy_frame = None     # frame being computed
        self.done = deque()        # (frame, command, t_start, t_end, err)
        self.partial = {}          # frame -> latest published command
        self.alive = True
        self.th = threading.Thread(target=self._loop, name="rt-strict-worker", daemon=True)
        self.th.start()

    def _pub(self, frame, cmd):
        with self.cv:
            self.partial[frame] = cmd

    def _loop(self):
        while True:
            with self.cv:
                while self.job is None and self.alive:
                    self.cv.wait()
                if not self.alive:
                    return
                frame, obs, dl = self.job
                self.job, self.busy_frame = None, frame
            t0 = now(); err = None; cmd = None
            try:
                cmd = self.agent.decide(obs, Ctx(frame, dl, self._pub))
            except Exception:  # an agent crash must never take the loop down
                err = traceback.format_exc(limit=3)
            t1 = now()
            with self.cv:
                self.busy_frame = None
                self.done.append((frame, cmd, t0, t1, err))
                self.cv.notify_all()

    def submit(self, frame, obs, deadline_ns):
        with self.cv:
            replaced = self.job[0] if self.job is not None else None
            busy = self.busy_frame
            self.job = (frame, obs, deadline_ns)
            self.cv.notify_all()
        return busy, replaced

    def wait(self, frame, deadline_ns):
        """Wait until the answer for `frame` is in or the deadline passes. Returns list of finished records."""
        out = []
        with self.cv:
            while True:
                while self.done:
                    out.append(self.done.popleft())
                if any(r[0] == frame for r in out):
                    break
                left = (deadline_ns - now()) / 1e9
                if left <= 0:
                    break
                self.cv.wait(left)
            part = self.partial.pop(frame, None)
            for k in [k for k in self.partial if k < frame]:
                del self.partial[k]
        return out, part

    def drain(self):
        with self.cv:
            out = list(self.done); self.done.clear()
        return out

    def close(self):
        with self.cv:
            self.alive = False
            self.cv.notify_all()
        self.th.join(timeout=1.0)


# ---------------------------------------------------------------------------------------------- process backend
def _proc_main(conn, factory):
    agent = factory()
    send = conn.send

    def pub(frame, cmd):
        send(("partial", frame, cmd))

    while True:
        msg = conn.recv()
        # one-slot mailbox: skip to the newest queued frame
        while conn.poll():
            msg = conn.recv()
        if msg is None:
            return
        frame, obs, dl = msg
        t0 = now(); err = None; cmd = None
        try:
            cmd = agent.decide(obs, Ctx(frame, dl, pub))
        except Exception:
            err = traceback.format_exc(limit=3)
        send(("done", frame, cmd, t0, now(), err))


class _ProcWorker:
    def __init__(self, factory):
        ctx = mp.get_context("fork" if "fork" in mp.get_all_start_methods() else "spawn")  # Windows: spawn
        self.conn, child = ctx.Pipe()
        self.p = ctx.Process(target=_proc_main, args=(child, factory), daemon=True)
        self.p.start()
        self.inflight = set()

    def submit(self, frame, obs, deadline_ns):
        busy = min(self.inflight) if self.inflight else None
        self.conn.send((frame, obs, deadline_ns))
        self.inflight.add(frame)
        return busy, None

    def _take(self, out, part, frame):
        m = self.conn.recv()
        if m[0] == "done":
            out.append(m[1:])
            # frames older than this one will never be answered (child skipped them)
            self.inflight = {f for f in self.inflight if f > m[1]}
        elif m[1] == frame:
            part[0] = m[2]
        return part

    def wait(self, frame, deadline_ns):
        out, part = [], [None]
        while not any(r[0] == frame for r in out):
            left = (deadline_ns - now()) / 1e9
            if left <= 0 or not self.conn.poll(left):
                break
            self._take(out, part, frame)
        while self.conn.poll(0):  # drain whatever else is ready without blocking
            self._take(out, part, frame)
        return out, part[0]

    def drain(self):
        out, part = [], [None]
        while self.conn.poll(0):
            self._take(out, part, -1)
        return out

    def close(self):
        try:
            self.conn.send(None)
        except Exception:
            pass
        self.p.join(timeout=1.0)
        if self.p.is_alive():
            self.p.kill()


# ------------------------------------------------------------------------------------------------------ wrapper
class RTStrict:
    """Wraps an agent with a per-frame compute budget. Same begin/step split as melee-llm's runner (L279-300)."""

    def __init__(self, agent=None, *, factory=None, budget_ms=10.0, frame_ms=1000 / 60, mode="thread",
                 chain=DEFAULT_CHAIN, max_repeat=30, late_max_age=2, cheap_policy=None, D=0, trace=None,
                 label=""):
        assert mode in ("thread", "process", "inline")
        self.budget_ns = int(budget_ms * 1e6)
        self.budget_ms, self.frame_ms, self.mode, self.chain = budget_ms, frame_ms, mode, tuple(chain)
        self.max_repeat, self.late_max_age, self.cheap_policy, self.D = max_repeat, late_max_age, cheap_policy, D
        self.trace = trace if trace is not None else []
        self.label = label
        if mode == "thread":
            self.w = _ThreadWorker(agent if agent is not None else factory())
        elif mode == "process":
            self.w = _ProcWorker(factory)
        else:  # inline: no deadline enforcement, the RT-slow reference (latency only)
            self.agent = agent if agent is not None else factory()
        self.last_cmd, self.last_src_frame, self.repeats = None, None, 0
        self.latest_done = None   # (frame, cmd) most recent completed answer
        self.cur = None
        self.controller = None
        self.pending = {}         # frame -> record still waiting for its (late) policy_end

    def setup(self, controller):
        self.controller = controller

    # --- runner contract ---------------------------------------------------------------------
    def begin(self, gs, capture_ts_ns=None):
        t_ready = now()
        f = gs["frame"]
        dl = t_ready + self.budget_ns
        rec = {"label": self.label, "mode": self.mode, "obs_frame": f, "decision_frame": f,
               "target_frame": f + 1 + self.D, "applied_frame": None, "applied_frame_measured": False,
               "capture_ts_ns": capture_ts_ns, "ready_ts_ns": t_ready, "deadline_ts_ns": dl,
               "budget_ms": self.budget_ms, "policy_start_ts_ns": None, "policy_end_ts_ns": None,
               "accepted_ts_ns": None, "send_ts_ns": None, "applied_ts_ns": None,
               "applied_ts_source": "null: no Dolphin; fake console emulates obs_frame+1 right after flush"}
        if self.mode == "inline":
            self.cur = (rec, gs)
            return
        busy, replaced = self.w.submit(f, gs, dl)
        rec["worker_busy_with_frame"] = busy
        rec["replaced_unstarted_frame"] = replaced
        rec["begin_cost_ns"] = now() - t_ready
        self.cur = (rec, gs)

    def _finish_records(self, done, frame):
        mine = None
        for fr, cmd, t0, t1, err in done:
            r = self.pending.pop(fr, None)
            if fr == frame:
                mine = (cmd, t0, t1, err)
                continue
            if r is not None:  # late answer for an older frame: completes that record, then is stale
                r["policy_start_ts_ns"], r["policy_end_ts_ns"] = t0, t1
                r["late_by_ms"] = (t1 - r["deadline_ts_ns"]) / 1e6
                r["compute_ms"] = (t1 - t0) / 1e6
                if err:
                    r["agent_error"] = err
            if err is None and (self.latest_done is None or fr > self.latest_done[0]):
                self.latest_done = (fr, cmd)
        return mine

    def step(self, gs):
        rec, gs0 = self.cur
        f = rec["obs_frame"]
        src, cmd, fb = f, None, None
        if self.mode == "inline":
            t0 = now()
            cmd = self.agent.decide(gs0, Ctx(f, rec["deadline_ts_ns"], lambda *_: None))
            t1 = now()
            rec["policy_start_ts_ns"], rec["policy_end_ts_ns"] = t0, t1
            part, err = None, None
        else:
            done, part = self.w.wait(f, rec["deadline_ts_ns"])
            mine = self._finish_records(done, f)
            err = None
            if mine is not None:
                cmd, t0, t1, err = mine
                rec["policy_start_ts_ns"], rec["policy_end_ts_ns"] = t0, t1
                if err:
                    rec["agent_error"], cmd = err, None
        if cmd is None:
            for lvl in self.chain:
                if lvl == "best_so_far" and part is not None:
                    cmd, fb = part, lvl; break
                if lvl == "late_result" and self.latest_done is not None and f - self.latest_done[0] <= self.late_max_age:
                    cmd, fb, src = self.latest_done[1], lvl, self.latest_done[0]; break
                if lvl == "cheap_policy" and self.cheap_policy is not None:
                    cmd, fb = self.cheap_policy(gs0), lvl; break
                if lvl == "repeat_last" and self.last_cmd is not None and self.repeats < self.max_repeat:
                    cmd, fb, src = self.last_cmd, lvl, self.last_src_frame; break
                if lvl == "neutral":
                    cmd, fb, src = NEUTRAL, lvl, None; break
            if cmd is None:
                cmd, fb, src = NEUTRAL, "neutral", None
            self.repeats = self.repeats + 1 if fb == "repeat_last" else 0
            if mine is None and self.mode != "inline":
                self.pending[f] = rec
        else:
            self.repeats = 0
            if self.latest_done is None or f > self.latest_done[0]:
                self.latest_done = (f, cmd)
        if self.controller is not None:
            self.controller.write(cmd)
        t_acc = now()
        self.last_cmd, self.last_src_frame = cmd, src
        rec["accepted_ts_ns"] = t_acc
        # missed = a fallback was used, or the accepted command came after the deadline (e.g. the host descheduled
        # the loop thread; the on-time answer is then still used but the frame counts as missed)
        rec["accepted_after_deadline"] = t_acc > rec["deadline_ts_ns"]
        rec["answer_after_deadline"] = (rec["policy_end_ts_ns"] is not None and fb is None
                                        and rec["policy_end_ts_ns"] > rec["deadline_ts_ns"])
        rec["deadline_missed"] = fb is not None or rec["accepted_after_deadline"]
        rec["fallback_used"] = fb or "none"
        rec["command_source_frame"] = src
        rec["aged_obs_frames"] = None if src is None else f - src
        rec["latency_ms"] = (t_acc - rec["ready_ts_ns"]) / 1e6
        rec["budget_spent_ms"] = min(rec["latency_ms"], self.budget_ms) if fb is None else self.budget_ms
        rec["overrun_ms"] = (t_acc - rec["deadline_ts_ns"]) / 1e6  # > 0 only if the wrapper itself overstayed
        if rec["policy_end_ts_ns"] is not None:
            rec["compute_ms"] = (rec["policy_end_ts_ns"] - rec["policy_start_ts_ns"]) / 1e6
            rec["wrapper_overhead_ms"] = rec["latency_ms"] - rec["compute_ms"]
        else:
            rec["compute_ms"] = None
            rec["wrapper_overhead_ms"] = None
        self.trace.append(rec)
        self.cur = None
        return cmd

    def on_send(self, send_ts_ns, applied_frame):
        """Called by the (fake) console when the controller state is flushed to the emulator."""
        if self.trace and self.trace[-1]["send_ts_ns"] is None:
            self.trace[-1]["send_ts_ns"] = send_ts_ns
            self.trace[-1]["applied_frame"] = applied_frame

    def close(self, settle_s=0.2):
        if self.mode != "inline":
            t_end = time.perf_counter() + settle_s
            while self.pending and time.perf_counter() < t_end:
                self._finish_records(self.w.drain(), -1)
                time.sleep(0.005)
            self._finish_records(self.w.drain(), -1)
            self.w.close()
        return self.trace
