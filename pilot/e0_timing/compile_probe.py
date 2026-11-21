"""Probe: does torch.compile (inductor, CPU) cut the per-step eager overhead of the W0-S + q rollout step?
Exploratory (E0); noise is passed in as tensors so the compiled region has no generator objects."""
import os, sys, time, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import portable as _P  # noqa: E402  (Linux/Windows)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import torch
th = int(sys.argv[1]) if len(sys.argv) > 1 else 1
core = sys.argv[2] if len(sys.argv) > 2 else "gru"
torch.set_num_threads(th)
import wm_models as M

torch.manual_seed(0)
m = M.PresentPredictor(core, fast=True).eval()
K = 4
T = M.W0S_FAST


def step(wh, wst, qh, qst, cont, cat, cnt, proj, ptype, stage, u_self, nw, nq, nb):
    # q (closed loop): controller sample
    ql = m.q.head(qh)
    btn = (torch.sigmoid(ql[:, :8]) > nq[:, :8]).float()
    pq = ql - torch.log(-torch.log(nq))
    ax = torch.cat([pq, M.NEG.expand(K, 1)], 1)[:, M.CTRL_FAST].argmax(-1).float()
    u_opp = torch.cat([btn, (ax - M.CTRL_SCALE[0]) / M.CTRL_SCALE[1], torch.zeros(K, 2)], 1)
    lg = m.w.logits(wh, u_self, u_opp)
    pert = lg - torch.log(-torch.log(nw))
    c = torch.cat([pert, M.NEG.expand(K, 1)], 1)[:, T["cat_idx"]].argmax(-1).view(K, 2, 13)
    bern = (torch.sigmoid(lg[:, T["bern"]]) > nb).long()
    cat2 = torch.stack([c[..., 0], cat[..., 1], bern[..., 0], bern[..., 1], c[..., 2], c[..., 3], c[..., 1], bern[..., 2]], -1)
    mode, reset = c[..., 4:8], c[..., 8:12]
    cnt2 = torch.where(mode == 0, torch.minimum(cnt + 1, T["cnt_max"]), torch.where(mode == 1, reset, torch.zeros_like(reset)))
    vals = (torch.softmax(lg[:, T["twohot"]].view(K, 2, M.TWOHOT_FIELDS, M.NB), -1) * M.BINS_X).sum(-1)
    pos = cont[..., 0:2] + vals[..., 0:2]
    pos = torch.where((torch.sigmoid(lg[:, T["respawn"]]) > 0.5).view(K, 1, 1), lg[:, T["abspos"]], pos)
    pct = cont[..., 7:8] + c[..., 12:13].float()
    rel = torch.stack([pos[:, 1] - pos[:, 0], pos[:, 0] - pos[:, 1]], 1)
    cont2 = torch.cat([pos, vals[..., 2:7], pct, vals[..., 7:8], pos[..., 0:1].abs() - 70.0, rel], -1)
    a, b = T["proj"]
    fr = M.Frames(cont2, cat2, cnt2, torch.stack([u_self, u_opp], 1), lg[:, a:b].reshape(K, M.NPROJ, M.NPF), ptype, stage)
    wst, wh = m.w.E.core.step(wst, m.w.E.emb(fr))
    qst, qh = m.q.E.core.step(qst, m.q.E.emb(fr))
    return wh, wst, qh, qst, cont2, cat2, cnt2, fr.proj


class _Wrap(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.m = m

    def forward(self, *a):
        return step(*a)


g = torch.Generator().manual_seed(0)
hist = M.random_frames(1, 16, g)
with torch.inference_mode():
    wst, wh = m.w.E.core.prefix(m.w.E.emb.seq(hist)); wst = m.w.E.core.expand(wst, K); wh = wh.expand(K, -1).contiguous()
    qst, qh = m.q.E.core.prefix(m.q.E.emb.seq(hist)); qst = m.q.E.core.expand(qst, K); qh = qh.expand(K, -1).contiguous()
    fr = hist.at(-1).map(lambda x: x.expand(K, *x.shape[1:]).contiguous())
    args = lambda: (wh, wst, qh, qst, fr.cont, fr.cat, fr.cnt, fr.proj, fr.ptype, fr.stage, torch.randn(K, 16),
                    torch.rand(K, M.W0S_OUT).clamp(1e-9, 1 - 1e-9), torch.rand(K, M.CTRL_OUT).clamp(1e-9, 1 - 1e-9),
                    torch.rand(K, 2, 3))

    def bench(fn, n=300):
        A = args()
        for _ in range(10):
            fn(*A)
        ts = []
        for _ in range(n):
            t = time.perf_counter_ns(); fn(*A); ts.append((time.perf_counter_ns() - t) / 1e3)
        ts.sort()
        return {"p50_us": ts[n // 2], "p99_us": ts[int(.99 * n)]}

    res = {"core": core, "threads": th, "eager": bench(step)}
    backend = sys.argv[3] if len(sys.argv) > 3 else "jit"
    t0 = time.perf_counter()
    if backend == "inductor":
        cstep = torch.compile(step, dynamic=False)
        cstep(*args())
    else:  # TorchScript trace + freeze (low RAM)
        A = args()
        flat = lambda *a: tuple(x for x in step(*a))
        cstep = torch.jit.freeze(torch.jit.trace(torch.jit.script(lambda *a: a) if False else _Wrap(), A, check_trace=False).eval())
        cstep(*A); cstep(*A)
    res["backend"] = backend
    res["compile_s"] = time.perf_counter() - t0
    res["compiled"] = bench(cstep)
res["peak_rss_mb"] = _P.peak_rss_mb()
res["loadavg"] = _P.loadavg()
print(json.dumps(res))
