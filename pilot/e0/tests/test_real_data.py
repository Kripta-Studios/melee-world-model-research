"""Tests sobre datos reales (se saltan si no existen). E0_DATA=/srv/mail/melee-research-data"""
import glob
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import numpy as np  # noqa: E402

DATA = os.environ.get("E0_DATA", "/srv/mail/melee-research-data")
NPZ = sorted(glob.glob(os.path.join(DATA, "parsed", "*.npz")))


@unittest.skipUnless(NPZ, "no hay datos parseados")
class TestRealData(unittest.TestCase):
    def test_reparse_reproducible(self):
        import a6io
        import parse_a6
        f = NPZ[0]
        arrs, meta = a6io.load(f)
        slp = os.path.join(DATA, "slp", meta["sha1"] + ".slp")
        if not os.path.exists(slp):
            self.skipTest("slp ausente")
        new, meta2 = parse_a6.parse_game(slp)
        self.assertEqual(sorted(new), sorted(arrs))
        for k in arrs:
            self.assertTrue(np.array_equal(new[k], arrs[k]), k)
        self.assertTrue(all(meta2["crosscheck"].values()))

    def test_shapes_and_contiguity(self):
        import a6io
        for f in NPZ[:5]:
            a, m = a6io.load(f)
            T = len(a["frame_id"])
            self.assertTrue(np.array_equal(a["frame_id"], np.arange(-123, -123 + T)))
            self.assertGreaterEqual(int(a["n_copies"].min()), 1)
            for k in ("pos_x", "action", "joy_x", "buttons_phys", "action_frame"):
                self.assertEqual(a[k].shape, (T, 2), k)
            self.assertTrue(np.all(np.abs(a["joy_x"]) <= 1))


if __name__ == "__main__":
    unittest.main()
