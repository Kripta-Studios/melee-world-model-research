import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import numpy as np  # noqa: E402

import adapter_checks as AC  # noqa: E402
import splits  # noqa: E402


class TestChecks(unittest.TestCase):
    def test_edges(self):
        h = np.array([0, 1, 1, 0, 1], bool)
        self.assertEqual(AC.edges(h).tolist(), [False, True, False, False, True])

    def test_lag_k0_and_k1(self):
        act = np.array([14] * 10 + [24] * 5 + [14] * 10)
        prev = np.ones(len(act), bool)
        press = np.zeros(len(act), bool)
        press[10] = True                     # mismo frame que el cambio -> k=0
        self.assertEqual(dict(AC.lag_histogram(press, act, prev, 24)), {0: 1})
        press2 = np.zeros(len(act), bool)
        press2[9] = True                     # un frame antes -> k=1 (convención con desfase)
        self.assertEqual(dict(AC.lag_histogram(press2, act, prev, 24)), {1: 1})

    def test_static_obs(self):
        r = AC.static_observation_check()
        self.assertTrue(r["passed"])
        self.assertNotIn("rng_seed", r["observation_fields"])
        self.assertNotIn("joy_x", r["observation_fields"])


class TestSplits(unittest.TestCase):
    def test_bucket_deterministic(self):
        b = splits.bucket("c197dd644161c5036551c621bc0858e20c7b2d47")
        self.assertEqual(b, splits.bucket("c197dd644161c5036551c621bc0858e20c7b2d47"))
        self.assertTrue(0 <= b < 1)
        import hashlib
        ref = int(hashlib.sha256(b"A6-split-v1|c197dd644161c5036551c621bc0858e20c7b2d47").hexdigest()[:8], 16) / 2**32
        self.assertEqual(b, ref)

    def test_assign(self):
        self.assertEqual(splits.assign(0.5, 0.606, 0.697), "train")
        self.assertEqual(splits.assign(0.65, 0.606, 0.697), "val")
        self.assertEqual(splits.assign(0.9, 0.606, 0.697), "test")
        self.assertEqual(splits.assign(0.94, 0.90, 0.95), "val")


if __name__ == "__main__":
    unittest.main()
