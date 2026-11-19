"""The transformer core with KV-cache must give the same numbers as recomputing the whole causal context.
Run: nice -n 19 python3 -I -m unittest discover -s pilot/e0_timing/tests -v"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import torch  # noqa: E402

torch.set_num_threads(1)
import wm_models as M  # noqa: E402


class TestKV(unittest.TestCase):
    def test_core_equal(self):
        torch.manual_seed(0)
        a = M.TXCore(192, 16, kv=False).eval()
        b = M.TXCore(192, 16, kv=True).eval()
        b.load_state_dict(a.state_dict())
        e = torch.randn(1, 16, 192)
        steps = torch.randn(19, 4, 192)
        with torch.inference_mode():
            sa, ha = a.prefix(e); sb, hb = b.prefix(e)
            self.assertTrue(torch.allclose(ha, hb, atol=1e-5))
            sa, sb = a.expand(sa, 4), b.expand(sb, 4)
            md = 0.0
            for t in range(19):
                sa, ha = a.step(sa, steps[t]); sb, hb = b.step(sb, steps[t])
                md = max(md, (ha - hb).abs().max().item())
        self.assertLess(md, 1e-4, md)

    def test_full_predict_equal(self):
        """Whole predictor (W0-S + closed-loop q + pi0) with the same weights and the same random streams."""
        for closed in (False, True):
            torch.manual_seed(1)
            pa = M.PresentPredictor("tx").eval()
            pb = M.PresentPredictor("tx_kv").eval()
            pb.load_state_dict(pa.state_dict())
            g0 = torch.Generator().manual_seed(5)
            hist = M.random_frames(1, 16, g0)
            own = torch.randn(13, M.NCTRL, generator=g0)
            with torch.inference_mode():
                ca, da = pa.predict(hist, own, 12, K=4, closed_loop=closed, g=torch.Generator().manual_seed(9), return_debug=True)
                cb, db = pb.predict(hist, own, 12, K=4, closed_loop=closed, g=torch.Generator().manual_seed(9), return_debug=True)
            self.assertLess((da["h"] - db["h"]).abs().max().item(), 1e-3)
            self.assertTrue(torch.equal(da["final"].cat, db["final"].cat))  # same sampled discrete state
            self.assertTrue(torch.equal(da["final"].cnt, db["final"].cnt))
            self.assertTrue(torch.allclose(da["final"].cont, db["final"].cont, atol=1e-3))
            self.assertTrue(torch.equal(ca, cb))

    def test_shapes_and_params(self):
        for core in ("mlp", "gru", "tx_kv"):
            p = M.PresentPredictor(core).eval()
            n = p.param_counts()
            self.assertTrue(0.8e6 < n["W0S"] < 2.6e6, (core, n))
            with torch.inference_mode():
                c, _ = p.predict(M.random_frames(1, 16), torch.zeros(7, M.NCTRL), 6, K=4)
            self.assertEqual(c.shape, (M.NCTRL,))


    def test_fast_sampling_matches_reference_semantics(self):
        """Vectorised sampler: same shapes/dtypes/ranges; with near-deterministic logits, same discrete outcome."""
        torch.manual_seed(2)
        m = M.PresentPredictor("gru").eval()
        g = torch.Generator().manual_seed(0)
        fr = M.random_frames(4, 1, g).at(0)
        lg = torch.randn(4, M.W0S_OUT, generator=g) * 50  # sharp logits: sampling ~ argmax
        u = torch.randn(4, M.NCTRL)
        with torch.inference_mode():
            a = m.w.sample_next(fr, lg, u, u, torch.Generator().manual_seed(1))
            b = M.w0s_sample_next_fast(fr, lg, u, u, torch.Generator().manual_seed(1))
        for k in M.Frames.__slots__:
            self.assertEqual(getattr(a, k).shape, getattr(b, k).shape, k)
            self.assertEqual(getattr(a, k).dtype, getattr(b, k).dtype, k)
        same = (a.cat[..., [0, 4, 5, 6]] == b.cat[..., [0, 4, 5, 6]]).float().mean().item()
        self.assertGreater(same, 0.9)
        self.assertTrue(torch.allclose(a.cont[..., 2:7], b.cont[..., 2:7], atol=1e-4))  # two-hot means
        cl = torch.randn(4, M.CTRL_OUT) * 50
        ca = M.CtrlPolicy.sample(cl, torch.Generator().manual_seed(3))
        cb = M.ctrl_sample_fast(cl, torch.Generator().manual_seed(3))
        self.assertEqual(ca.shape, cb.shape)
        self.assertGreater((ca[:, 8:] == cb[:, 8:]).float().mean().item(), 0.9)


if __name__ == "__main__":
    unittest.main()
