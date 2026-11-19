"""A7 inference latency on CPU (forward only, torch.inference_mode, fp32, eager).

Usage: python3 -I bench_infer.py --arch {mlp,gru,tx} --tier {1M,5M,15M} --threads N --out FILE.jsonl
Records (one JSON line each):
  kind=encode   : encoder, batch 1, history H in {8,32,64}
  kind=pstep    : one predictor step at batch B (B = candidates, or candidates x horizon when flattened)
  kind=rollout  : real sequential rollout of T steps at batch K (checks T x pstep linearity)
  kind=decision : encode(H=32, B=1) + rollout(K,T) + linear score + argmax (whole MPC decision proxy)
"""
import argparse, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a7common import pin_threads, env_info, timeit, peak_rss_mb, Out

ap = argparse.ArgumentParser()
ap.add_argument("--arch", required=True)
ap.add_argument("--tier", required=True)
ap.add_argument("--threads", type=int, required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--S", type=int, default=192)
ap.add_argument("--budget_s", type=float, default=100.0)
args = ap.parse_args()

torch = pin_threads(args.threads)
from a7models import build  # noqa: E402

torch.manual_seed(0)
out = Out(args.out)
T0 = time.perf_counter()
base = {"arch": args.arch, "tier": args.tier, "threads": args.threads, "S": args.S}
out.w({"kind": "env", **base, **env_info(args.threads)})


def left():
    return args.budget_s - (time.perf_counter() - T0)


with torch.inference_mode():
    # ---- encoder, batch 1
    for H in (8, 32, 64):
        enc, pred, meta = build(args.arch, args.tier, S=args.S, H=H)
        enc.eval(); pred.eval()
        x = torch.randn(1, H, meta["S"] + meta["A"])
        st = timeit(lambda: enc(x))
        out.w({"kind": "encode", **base, "H": H, "B": 1, "meta": meta, **st})
    enc, pred, meta = build(args.arch, args.tier, S=args.S, H=32)
    enc.eval(); pred.eval()
    A, D = meta["A"], meta["D"]

    # ---- predictor single step at increasing batch
    for B in (1, 16, 64, 256, 512, 2048, 4096, 16384):
        if left() < 15:
            out.w({"kind": "skip", **base, "what": f"pstep B={B}", "reason": "time budget"}); break
        width = meta.get("d", 0) * 4 * meta.get("W", 1) if args.arch == "tx" else 2 * max(meta.get("pred_w", 0), meta.get("w", 0))
        est_mb = B * width * 4 / 2**20
        if est_mb > 80 or peak_rss_mb() > 900:
            out.w({"kind": "skip", **base, "what": f"pstep B={B}", "reason": f"RAM guard est_act_mb={est_mb:.0f} rss={peak_rss_mb():.0f}"}); break
        z = torch.randn(B, D); a = torch.randn(B, A)
        s0 = pred.init_state(z)
        st = timeit(lambda: pred.step(s0, a), min_time=0.3)
        out.w({"kind": "pstep", **base, "B": B, "pred_params": meta["pred_params"], **st})
        if st["p50_ms"] > 400:
            break

    # ---- real sequential rollouts
    def rollout(K, T):
        z = torch.randn(K, D)
        s = pred.init_state(z)
        acts = torch.randn(T, K, A)
        for t in range(T):
            s, z = pred.step(s, acts[t])
        return z

    for K, T in ((16, 8), (64, 8), (64, 32), (256, 8), (256, 16), (512, 8)):
        if left() < 12:
            out.w({"kind": "skip", **base, "what": f"rollout K={K} T={T}", "reason": "time budget"}); continue
        st = timeit(lambda: rollout(K, T), min_time=0.4, max_single=3.0)
        out.w({"kind": "rollout", **base, "K": K, "T": T, **st})

    # ---- whole decision proxy
    head = torch.nn.Linear(D, 1)
    xh = torch.randn(1, 32, meta["S"] + A)

    def decision(K, T):
        z0 = enc(xh)                     # encode history once
        s = pred.init_state(z0.expand(K, -1).contiguous())
        acts = torch.randn(T, K, A)      # candidate action sequences (proposal cost not included)
        score = torch.zeros(K)
        for t in range(T):
            s, z = pred.step(s, acts[t])
            score += head(z).squeeze(-1)  # reward proxy per step
        return int(score.argmax())

    for K, T in ((16, 4), (16, 8), (64, 8), (64, 16), (256, 8)):
        if left() < 10:
            out.w({"kind": "skip", **base, "what": f"decision K={K} T={T}", "reason": "time budget"}); continue
        st = timeit(lambda: decision(K, T), min_time=0.6, max_reps=300, max_single=3.0)
        out.w({"kind": "decision", **base, "K": K, "T": T, "H": 32, **st})

out.w({"kind": "end", **base, "elapsed_s": time.perf_counter() - T0, "peak_rss_mb": peak_rss_mb(),
       "loadavg_end": open("/proc/loadavg").read().strip()})
