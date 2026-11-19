"""A7 CPU training throughput with synthetic data (LeWM-like objective, end to end, no stop-grad).

Usage: python3 -I bench_train.py --arch {mlp,gru,tx} --tier {1M,5M,15M} --threads N --H 8 --B 128 --out FILE.jsonl
One training sample = a window of L = H + P frames (P = 4 open-loop prediction steps).
loss = MSE(pred_{1..P}, z_{1..P}) + 0.09 * SIGReg(z_{0..P})   (lambda, M=1024, knots=17 as le-wm config)
SIGReg is the le-wm class (lucas-maes/le-wm@8edfeb3 module.py:10-36) extracted with ast (einops not installed).
Optimizer AdamW lr 5e-5 wd 1e-3 (le-wm config/train/lewm.yaml). fp32, eager.
"""
import argparse, ast, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a7common import pin_threads, env_info, peak_rss_mb, pct, Out

ap = argparse.ArgumentParser()
ap.add_argument("--arch", required=True)
ap.add_argument("--tier", required=True)
ap.add_argument("--threads", type=int, required=True)
ap.add_argument("--H", type=int, default=8)
ap.add_argument("--B", type=int, default=64)
ap.add_argument("--P", type=int, default=4)
ap.add_argument("--out", required=True)
ap.add_argument("--budget_s", type=float, default=60.0)
ap.add_argument("--max_steps", type=int, default=40)
ap.add_argument("--no_sigreg", action="store_true")
args = ap.parse_args()

torch = pin_threads(args.threads)
from a7models import build  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LEWM = os.path.join(ROOT, "sources", "lucas-maes_le-wm", "module.py")


def load_lewm_sigreg():
    src = open(LEWM).read()
    tree = ast.parse(src)
    node = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SIGReg"][0]
    ns = {"torch": torch}
    exec(compile(ast.Module(body=[node], type_ignores=[]), LEWM, "exec"), ns)
    return ns["SIGReg"]


SIGReg = load_lewm_sigreg()
torch.manual_seed(0)
out = Out(args.out)
base = {"arch": args.arch, "tier": args.tier, "threads": args.threads, "H": args.H, "B": args.B, "P": args.P,
        "sigreg": not args.no_sigreg}
out.w({"kind": "env", **base, **env_info(args.threads), "sigreg_src": LEWM})

enc, pred, meta = build(args.arch, args.tier, H=args.H)
S, A, D = meta["S"], meta["A"], meta["D"]
sig = SIGReg(knots=17, num_proj=1024)
params = list(enc.parameters()) + list(pred.parameters())
opt = torch.optim.AdamW(params, lr=5e-5, weight_decay=1e-3)
L = args.H + args.P


def step():
    x = torch.randn(args.B, L, S + A)
    a = x[..., S:]
    zs = enc.forward_seq(x)
    z = zs if args.arch == "mlp" else zs[:, args.H - 1:]   # (B, P+1, D)
    s = pred.init_state(z[:, 0])
    preds = []
    for t in range(args.P):
        s, zp = pred.step(s, a[:, args.H - 1 + t])
        preds.append(zp)
    preds = torch.stack(preds, 1)
    loss = (preds - z[:, 1:]).pow(2).mean()
    if not args.no_sigreg:
        loss = loss + 0.09 * sig(z.transpose(0, 1))
    opt.zero_grad(set_to_none=True)
    loss.backward()
    opt.step()
    return loss.item()


T0 = time.perf_counter()
for _ in range(2):
    step()
ts = []
while len(ts) < args.max_steps and time.perf_counter() - T0 < args.budget_s:
    t0 = time.perf_counter(); step(); ts.append(time.perf_counter() - t0)
    if peak_rss_mb() > 950:
        out.w({"kind": "abort", **base, "reason": "rss>950MB"}); break
p50 = pct(ts, .5)
out.w({"kind": "train", **base, "meta": meta, "steps": len(ts), "step_p50_ms": p50 * 1e3,
       "step_p95_ms": pct(ts, .95) * 1e3, "step_mean_ms": sum(ts) / len(ts) * 1e3,
       "samples_per_s": args.B / p50, "transitions_per_s": args.B * args.P / p50,
       "frames_in_window_per_s": args.B * L / p50, "peak_rss_mb": peak_rss_mb(),
       "elapsed_s": time.perf_counter() - T0, "loadavg_end": open("/proc/loadavg").read().strip()})
