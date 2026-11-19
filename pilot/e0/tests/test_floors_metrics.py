"""Tests mínimos de métricas y suelos (pilot/e0/models). numpy puro; la parte de torch se salta si no hay torch."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "models"))
import numpy as np  # noqa: E402

import common as C  # noqa: E402
import metrics as M  # noqa: E402

try:
    import torch  # noqa: F401
    HAVE_TORCH = True
except Exception:  # noqa: BLE001
    HAVE_TORCH = False


class TestFloors(unittest.TestCase):
    def test_persistence_h0_zero_error(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=100)
        f = np.arange(5, 90)
        acc = M.Acc()
        acc.cont(("persist", "dyn", "pos_x", 0, "all", "-"), M.persistence(x, f, 0), x[f + 0], np.ones(len(f), bool))
        r = acc.rows(lambda _: "cont")[0]
        self.assertEqual(r["mae"], 0.0)
        self.assertEqual(r["rmse"], 0.0)
        self.assertEqual(r["within1"], 1.0)
        a = np.array([3, 3, 4, 4, 5])
        acc2 = M.Acc()
        acc2.disc(("persist", "dyn", "action", 0, "all", "-"), M.persistence(a, np.arange(5), 0), a, np.ones(5, bool))
        self.assertEqual(acc2.rows(lambda _: "disc")[0]["acc"], 1.0)

    def test_const_velocity_exact_on_linear_motion(self):
        # convención Slippi: pos_{f+1} - pos_f = v_{f+1}; con v constante el suelo es exacto
        v = np.full(50, 2.5)
        pos = np.cumsum(v)
        f = np.arange(1, 40)
        for h in (1, 4, 8):
            np.testing.assert_allclose(M.const_velocity(pos, v, f, h), pos[f + h])
            np.testing.assert_allclose(M.const_velocity_fd(pos, f, h), pos[f + h])

    def test_counter_clock(self):
        x = np.array([0.0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        np.testing.assert_array_equal(M.counter_clock(x, np.array([2]), 3, +1), [5.0])
        np.testing.assert_array_equal(M.counter_clock(x[::-1].copy(), np.array([7]), 5, -1), [0.0])

    def test_window_change_excludes_f_itself(self):
        a = np.array([1, 2, 2, 2, 3, 3])
        f = np.array([1, 1, 2])
        # cambio 1->2 ocurre en k=1 (=f): NO cuenta; cambio 2->3 en k=4
        np.testing.assert_array_equal(C.window_any_change(a, f, 2), [False, False, True])
        np.testing.assert_array_equal(C.window_any_change(a, f, 3), [True, True, True])
        np.testing.assert_array_equal(C.window_any_change(a, np.array([0]), 1), [True])   # k=1 > f=0
        np.testing.assert_array_equal(C.window_any_change(a, np.array([2]), 2), [True])

    def test_rise_and_masks(self):
        hs = np.array([0, 0, 1, 1, 0, 1])
        np.testing.assert_array_equal(C.window_any_rise(hs, np.array([0, 2, 3]), 2), [True, False, True])

    def test_sparse_counts_majority_and_nll(self):
        sc = M.SparseCounts(4)
        sc.add(np.array([0, 0, 0, 1, 1]), np.array([2, 2, 3, 1, 1]))
        sc.add(np.array([0]), np.array([3]))
        sc.finalize()
        ckt, ck, mode, seen = sc.lookup(np.array([0, 1, 7]), np.array([2, 1, 0]))
        np.testing.assert_array_equal(ck, [4, 2, 0])
        np.testing.assert_array_equal(ckt, [2, 2, 0])
        self.assertEqual(mode[0], 2)          # empate 2 vs 3 -> el menor
        self.assertEqual(mode[1], 1)
        self.assertEqual(mode[2], -1)
        self.assertFalse(seen[2])
        # la condicional suavizada suma 1 sobre los objetivos
        pm = np.array([0.1, 0.2, 0.3, 0.4])
        tot = 0
        for t in range(4):
            c1, c2, _m, _s = sc.lookup(np.array([0]), np.array([t]))
            tot += np.exp(-M.cond_nll(c1, c2, pm[t]))[0]
        self.assertAlmostEqual(tot, 1.0, places=12)

    def test_no_test_split(self):
        with self.assertRaises(AssertionError):
            C.assert_no_test([{"sha1": "x", "split": "test"}])
        C.assert_no_test([{"sha1": "x", "split": "train"}, {"sha1": "y", "split": "val"}])

    def test_anchors_room_for_history_and_horizon(self):
        f = C.anchors(100)
        self.assertEqual(f[0], C.HIST - 1)
        self.assertEqual(f[-1] + C.H_MAX, 99)


@unittest.skipUnless(HAVE_TORCH, "sin torch")
class TestSmokeTargets(unittest.TestCase):
    def test_q_target_is_f_plus_1_and_port_swap(self):
        import torch
        import floors as FL
        import smoke as S
        voc = dict(actions=[0, 14], sticks=[C.stick_code(np.array([0]), np.array([0]))[0],
                                             C.stick_code(np.array([80]), np.array([0]))[0]],
                   csticks=[C.stick_code(np.array([0]), np.array([0]))[0]])
        V = FL.Vocab(voc)
        R = torch.zeros((10, 2, S.NCOL))
        R[5, 1, S.CTRL0 + 8] = 80          # stick del puerto 1 a la derecha SOLO en la fila 5
        R[5, 1, S.CTRL0 + 0] = 1           # botón A del puerto 1 en la fila 5
        idx = torch.tensor([4])
        bits, st, _cs = S.q_targets(V, R, idx, 1, torch.tensor([1]))
        self.assertEqual(st[0], 1)         # mando de f+1 = fila 5
        self.assertEqual(bits[0, 0], 1)
        bits0, st0, _ = S.q_targets(V, R, idx, 0, torch.tensor([1]))
        self.assertEqual(st0[0], 0)        # el mando de f (fila 4) es neutro: el objetivo no es el de f
        win = S.gather(R, torch.tensor([5]), -1, 1)
        sw = S.swap_ports(win, torch.tensor([1]))
        self.assertTrue(torch.equal(sw[0, -1, 0], R[5, 1]))
        self.assertTrue(torch.equal(sw[0, -1, 1], R[5, 0]))

    def test_w0s_window_excludes_future(self):
        import torch
        import smoke as S
        R = torch.arange(20 * 2 * S.NCOL, dtype=torch.float32).reshape(20, 2, S.NCOL)
        win = S.gather(R, torch.tensor([10]), -(C.HIST - 1), 1)
        self.assertEqual(win.shape[1], C.HIST)
        self.assertTrue(torch.equal(win[0, -1], R[10]))   # la última fila de la historia es f, no f+1


if __name__ == "__main__":
    unittest.main()
