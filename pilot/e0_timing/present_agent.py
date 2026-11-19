"""PresentPredictorAgent stand-in for the RT-strict loop: featurize + W0-S/q rollout + pi0 (random weights). PROP.
Spec string: present:<core>:<D>:<open|closed>[:threads[:impl]]  e.g. present:gru:12:closed:1:fast"""
import os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class PresentAgent:
    def __init__(self, core, D, q, threads=1, K=4, H=16, seed=0, impl="ref"):
        import torch
        torch.set_num_threads(threads)
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass
        import wm_models as M
        self.torch, self.M = torch, M
        torch.manual_seed(seed)
        self.g = torch.Generator().manual_seed(seed)
        self.model = M.PresentPredictor(core, H=H, fast=impl == "fast").eval()
        self.D, self.closed, self.K = D, q == "closed", K
        self.hist = M.random_frames(1, H, self.g)
        self.own = torch.randn(D + 1, M.NCTRL, generator=self.g)
        self.rng = random.Random(seed)
        self.threads, self._pinned = threads, False

    def _featurize(self):
        M, torch, r = self.M, self.torch, self.rng
        pl = lambda: ([r.random() for _ in range(M.NCONT)], [r.randrange(n) for n in M.CAT_SIZES],
                      [r.randrange(n) for n in M.CNT_SIZES], [r.random() for _ in range(M.NCTRL)])
        p = [pl(), pl()]
        new = M.Frames(torch.tensor([[x[0] for x in p]]), torch.tensor([[x[1] for x in p]]),
                       torch.tensor([[x[2] for x in p]]), torch.tensor([[x[3] for x in p]]),
                       torch.rand(1, M.NPROJ, M.NPF), torch.randint(0, M.NPTYPE, (1, M.NPROJ)), torch.tensor([3]))
        self.hist = M.Frames(*(torch.cat([getattr(self.hist, k)[:, 1:], getattr(new, k).unsqueeze(1)], 1)
                               for k in M.Frames.__slots__))

    def decide(self, obs, ctx):
        if not self._pinned:  # intra-op thread count is per calling thread: pin inside the worker thread too
            self.torch.set_num_threads(self.threads); self._pinned = True
            self.worker_threads_seen = self.torch.get_num_threads()
        with self.torch.inference_mode():
            self._featurize()
            cmd, _ = self.model.predict(self.hist, self.own, self.D, K=self.K, closed_loop=self.closed, g=self.g)
            return {"code": cmd.tolist()}


def from_spec(spec, seed=0):
    parts = spec.split(":")
    _, core, D, q = parts[:4]
    th = int(parts[4]) if len(parts) > 4 else 1
    impl = parts[5] if len(parts) > 5 else "ref"
    return PresentAgent(core, int(D), q, threads=th, seed=seed, impl=impl)
