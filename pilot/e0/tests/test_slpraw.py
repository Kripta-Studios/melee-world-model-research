import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402

import slpraw  # noqa: E402
import stream_filter  # noqa: E402
import synth  # noqa: E402


class TestSlpRaw(unittest.TestCase):
    def test_header(self):
        d = synth.build(range(-123, 10))
        h, _ = slpraw.parse_header(d)
        self.assertEqual(h.version, (3, 15, 0))
        self.assertEqual(h.stage, 31)
        self.assertEqual(h.ext_chars[:2], [2, 2])
        self.assertEqual(h.player_types, [0, 0, 3, 3])
        self.assertEqual(h.random_seed, 12345)

    def test_index_and_last_copy(self):
        d = synth.build(range(-123, 10), rollback_at={5, 7})
        ev = slpraw.index_events(d)
        self.assertEqual(ev.game_end_method, 2)
        post = ev.offsets[slpraw.CMD_POST]
        f, p, _ = slpraw.frame_port_keys(d, post)
        sel = post[p == 0]
        u, last, counts = slpraw.last_copy_index(f[p == 0])
        self.assertTrue(np.array_equal(u, np.arange(-123, 10)))
        self.assertEqual(int(counts.sum()), 133 + 2)
        self.assertEqual(int((counts > 1).sum()), 2)
        x = slpraw.gather(d, sel[last], 0xA, "f4")
        # la copia LAST lleva x = f + 1000
        self.assertEqual(float(x[u == 5][0]), 1005.0)
        self.assertEqual(float(x[u == 4][0]), 4.0)

    def test_last_copy_index_order(self):
        u, last, c = slpraw.last_copy_index(np.array([1, 2, 3, 2, 3, 4]))
        self.assertEqual(u.tolist(), [1, 2, 3, 4])
        self.assertEqual(last.tolist(), [0, 3, 4, 5])
        self.assertEqual(c.tolist(), [1, 2, 2, 1])

    def test_classify(self):
        ok = stream_filter.classify(synth.build(range(-123, 1600)))
        self.assertIsNone(ok["reason"])
        self.assertEqual(stream_filter.classify(synth.build(range(-123, 1600), chars=(2, 9)))["reason"], "not_fox_ditto")
        self.assertEqual(stream_filter.classify(synth.build(range(-123, 100)))["reason"], "too_short")
        self.assertEqual(stream_filter.classify(synth.build(range(-123, 1600), end_method=None))["reason"], "no_game_end")
        self.assertEqual(stream_filter.classify(synth.build(range(-123, 1600), end_method=7))["reason"], "no_contest")
        gap = list(range(-123, 50)) + list(range(60, 1600))
        self.assertEqual(stream_filter.classify(synth.build(gap))["reason"], "non_contiguous_frames")
        self.assertTrue(stream_filter.classify(b"garbage" * 10)["reason"].startswith("parse_error"))


if __name__ == "__main__":
    unittest.main()
