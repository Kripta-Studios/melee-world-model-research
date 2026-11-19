"""Unit tests for the RT-strict wrapper (stdlib unittest; pytest is not installed).
Run: nice -n 19 python3 -I -m unittest discover -s pilot/e0_timing/tests -v
Timing tolerances are loose on purpose: the server is shared (see TIMING_REPORT.md)."""
import os, sys, time, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rt_strict import RTStrict, NEUTRAL  # noqa: E402
from synthetic_agents import Synthetic  # noqa: E402
from fake_runner import run_loop  # noqa: E402

TOL_MS = 6.0  # allowed overstay beyond the deadline on a loaded shared host


class Fixed:
    def __init__(self, ms, publish=False):
        self.ms, self.publish = ms, publish

    def decide(self, obs, ctx):
        if self.publish:
            ctx.publish({"tag": "partial", "f": obs["frame"]})
        time.sleep(self.ms / 1000)
        return {"tag": "final", "f": obs["frame"]}


class Boom:
    def decide(self, obs, ctx):
        raise RuntimeError("x")


def one(w, frame):
    gs = {"frame": frame}
    w.begin(gs)
    return w.step(gs)


class TestRTStrict(unittest.TestCase):
    def _modes(self):
        return ("thread", "process")

    def test_on_time_answer_is_used(self):
        for m in self._modes():
            w = RTStrict(factory=lambda: Fixed(1.0), budget_ms=30, mode=m)
            cmd = one(w, 0)
            tr = w.close()
            self.assertEqual(cmd["tag"], "final", m)
            self.assertEqual(tr[0]["fallback_used"], "none")
            self.assertFalse(tr[0]["fallback_used"] != "none")
            self.assertIsNotNone(tr[0]["compute_ms"])

    def test_late_answer_falls_back_in_order_and_never_blocks(self):
        for m in self._modes():
            w = RTStrict(factory=lambda: Fixed(40.0), budget_ms=5, mode=m, max_repeat=1)
            c0 = one(w, 0)  # nothing before: neutral
            c1 = one(w, 1)  # repeat_last (neutral again, but declared as repeat)
            c2 = one(w, 2)  # max_repeat=1 reached -> neutral
            tr = w.close(settle_s=0.3)
            self.assertEqual([r["fallback_used"] for r in tr], ["neutral", "repeat_last", "neutral"], m)
            self.assertEqual(c0, NEUTRAL)
            for r in tr:
                self.assertTrue(r["deadline_missed"])
                self.assertLess(r["overrun_ms"], TOL_MS, (m, r["overrun_ms"]))
            # the late answer for frame 0 completes its record later, and is never applied
            self.assertIsNotNone(tr[0]["policy_end_ts_ns"], m)
            self.assertGreater(tr[0]["late_by_ms"], 0)

    def test_best_so_far(self):
        for m in self._modes():
            w = RTStrict(factory=lambda: Fixed(40.0, publish=True), budget_ms=10, mode=m)
            cmd = one(w, 0)
            tr = w.close(settle_s=0.3)
            self.assertEqual(cmd["tag"], "partial", m)
            self.assertEqual(tr[0]["fallback_used"], "best_so_far")

    def test_late_result_option_uses_aged_answer(self):
        w = RTStrict(factory=lambda: Fixed(12.0), budget_ms=5, mode="thread",
                     chain=("best_so_far", "late_result", "repeat_last", "neutral"), late_max_age=3)
        one(w, 0)
        time.sleep(0.02)  # frame 0 answer arrives while we wait for the next frame
        cmd = one(w, 1)
        tr = w.close(settle_s=0.3)
        self.assertEqual(tr[1]["fallback_used"], "late_result")
        self.assertEqual(cmd["f"], 0)
        self.assertEqual(tr[1]["aged_obs_frames"], 1)

    def test_crash_goes_to_fallback(self):
        for m in self._modes():
            w = RTStrict(factory=Boom, budget_ms=20, mode=m)
            cmd = one(w, 0)
            tr = w.close()
            self.assertEqual(cmd, NEUTRAL, m)
            self.assertIn("agent_error", tr[0])

    def test_trace_has_protocol_fields(self):
        need = ["obs_frame", "decision_frame", "target_frame", "applied_frame", "applied_frame_measured",
                "capture_ts_ns", "ready_ts_ns", "policy_start_ts_ns", "policy_end_ts_ns", "send_ts_ns",
                "applied_ts_ns", "accepted_ts_ns", "latency_ms", "deadline_missed", "fallback_used",
                "budget_ms", "budget_spent_ms", "overrun_ms", "wrapper_overhead_ms"]
        w = RTStrict(factory=lambda: Synthetic("const", ms=2.0), budget_ms=10, mode="thread", D=6)
        tr, aux = run_loop(w, 30)
        self.assertEqual(len(tr), 30)
        for r in tr[:-1]:
            for k in need:
                self.assertIn(k, r)
            self.assertEqual(r["target_frame"], r["obs_frame"] + 7)
            self.assertEqual(r["applied_frame"], r["obs_frame"] + 1)
            self.assertIsNotNone(r["send_ts_ns"])
            self.assertGreaterEqual(r["send_ts_ns"], r["accepted_ts_ns"])

    def test_fake_loop_bounded_by_budget(self):
        """An agent that always exceeds the budget never holds the loop beyond the deadline (+ tolerance)."""
        w = RTStrict(factory=lambda: Synthetic("exceed", ms=14.0), budget_ms=10, mode="thread")
        tr, aux = run_loop(w, 60)
        lat = sorted(r["latency_ms"] for r in tr)
        self.assertTrue(all(r["deadline_missed"] for r in tr[1:]))
        self.assertTrue(all(r["fallback_used"] != "none" or r["answer_after_deadline"] for r in tr[1:]))
        self.assertLess(lat[len(lat) // 2], 10 + TOL_MS)


if __name__ == "__main__":
    unittest.main()
