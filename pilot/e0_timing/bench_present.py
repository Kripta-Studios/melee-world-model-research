"""E0 extended latency bench: 'predict the present' for architecture A with random weights (cost, not quality).

One process = one (core, threads, rep). Inside: for D in {6,12,18} x q in {open, closed}: N decisions, each one
  featurize(new frame from a Python dict, ~110 values) -> encode(W0-S, q; B=1, H=16) -> K x (D+1) rollout ->
  pi0 on K hypotheses -> mixture -> command
timed per stage with perf_counter_ns. Plus pi0 alone on the aged observation (arm (a) / cheap fallback).

Usage: python3 -I bench_present.py --core {mlp,gru,tx,tx_kv} --threads {1,2} --rep R --out FILE.jsonl
"""
import argparse, json, os, random, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import portable as _P  # noqa: E402  (Linux/Windows)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "a7_bench"))
from a7common import pin_threads, env_info, pct, peak_rss_mb  # noqa: E402  (reused from A7)

ap = argparse.ArgumentParser()
ap.add_argument("--core", required=True, choices=("mlp", "gru", "tx", "tx_kv"))
ap.add_argument("--threads", type=int, required=True, choices=(1, 2))
ap.add_argument("--rep", type=int, default=0)
ap.add_argument("--n", type=int, default=200)
ap.add_argument("--warmup", type=int, default=15)
ap.add_argument("--K", type=int, default=4)
ap.add_argument("--H", type=int, default=16)
ap.add_argument("--Ds", default="6,12,18")
ap.add_argument("--budget_s", type=float, default=160.0)
ap.add_argument("--rss_cap_mb", type=float, default=1050.0)
ap.add_argument("--impl", default="ref", choices=("ref", "fast"), help="ref: per-field sampling; fast: vectorised")
ap.add_argument("--out", required=True)
ap.add_argument("--device", default="cpu", choices=("cpu", "cuda"),
                help="cuda: modelo y estado en GPU; featurize crea tensores en CPU->GPU y cmd.tolist() sincroniza (transferencias incluidas)")
a = ap.parse_args()

torch = pin_threads(a.threads)
if a.device == "cuda" and a.rss_cap_mb == 1050.0:
    a.rss_cap_mb = 6000.0  # el contexto CUDA ya supera 1 GB de RSS; el tope de 1050 MB era del servidor
if a.device == "cuda":
    torch.set_default_device("cuda")  # antes de importar wm_models: sus constantes de módulo nacen en GPU
import wm_models as M  # noqa: E402


def sync():
    if a.device == "cuda":
        torch.cuda.synchronize()

T0 = time.perf_counter()
torch.manual_seed(1000 + a.rep)
g = torch.Generator(device=a.device).manual_seed(a.rep)
model = M.PresentPredictor(a.core, H=a.H, fast=a.impl == "fast").eval()
out = open(a.out, "a")
base = {"core": a.core, "impl": a.impl, "device": a.device, "threads": a.threads, "rep": a.rep, "K": a.K, "H": a.H}
out.write(json.dumps({"kind": "env", **base, "params": model.param_counts(), **env_info(a.threads),
                      "gpu": torch.cuda.get_device_name(0) if a.device == "cuda" else None}) + "\n")
out.flush()

rng = random.Random(a.rep)


def fake_gs():  # Python-side GameState stand-in with the schema's field count
    pl = lambda: {"cont": [rng.random() for _ in range(M.NCONT)], "cat": [rng.randrange(n) for n in M.CAT_SIZES],
                  "cnt": [rng.randrange(n) for n in M.CNT_SIZES], "ctrl": [rng.random() for _ in range(M.NCTRL)]}
    return {"p": [pl(), pl()], "proj": [[rng.random() for _ in range(M.NPF)] for _ in range(M.NPROJ)],
            "ptype": [rng.randrange(M.NPTYPE) for _ in range(M.NPROJ)], "stage": 3}


def featurize(gs, hist):
    """Python dict -> tensors, shift the (1, H) history ring and append. This is the featurisation cost."""
    new = M.Frames(torch.tensor([[p["cont"] for p in gs["p"]]]), torch.tensor([[p["cat"] for p in gs["p"]]]),
                   torch.tensor([[p["cnt"] for p in gs["p"]]]), torch.tensor([[p["ctrl"] for p in gs["p"]]]),
                   torch.tensor([gs["proj"]]), torch.tensor([gs["ptype"]]), torch.tensor([gs["stage"]]))
    return M.Frames(*(torch.cat([getattr(hist, k)[:, 1:], getattr(new, k).unsqueeze(1)], 1) for k in M.Frames.__slots__))


hist = M.random_frames(1, a.H, g)
stop = False
with torch.inference_mode():
    for D in [int(x) for x in a.Ds.split(",")]:
        for closed in (False, True):
            if stop:
                break
            qname = "closed" if closed else "open"
            own = torch.randn(D + 1, M.NCTRL, generator=g)
            gss = [fake_gs() for _ in range(a.n + a.warmup)]
            tot, st = [], {"featurize_ms": [], "encode_ms": [], "rollout_ms": [], "pi0_ms": []}
            for i in range(a.n + a.warmup):
                tm = {}
                t0 = time.perf_counter_ns()
                hist = featurize(gss[i], hist)
                tm["featurize_ms"] = (time.perf_counter_ns() - t0) / 1e6
                cmd, _ = model.predict(hist, own, D, K=a.K, closed_loop=closed, g=g, timings=tm)
                cmd = cmd.tolist()
                dt = (time.perf_counter_ns() - t0) / 1e6
                if i >= a.warmup:
                    tot.append(dt)
                    for k in st:
                        st[k].append(tm[k])
                if time.perf_counter() - T0 > a.budget_s or peak_rss_mb() > a.rss_cap_mb:
                    stop = True
                    break
            rec = {"kind": "present", **base, "D": D, "q": qname, "steps": a.K * (D + 1), "n": len(tot),
                   "p50_ms": pct(tot, .5), "p95_ms": pct(tot, .95), "p99_ms": pct(tot, .99), "max_ms": max(tot) if tot else None,
                   "mean_ms": sum(tot) / len(tot) if tot else None,
                   "stages_p50": {k: pct(v, .5) for k, v in st.items()},
                   "stages_p99": {k: pct(v, .99) for k, v in st.items()},
                   "raw_total_ms": [round(x, 4) for x in tot],
                   "loadavg": _P.loadavg(), "peak_rss_mb": peak_rss_mb(),
                   "truncated": stop}
            out.write(json.dumps(rec) + "\n"); out.flush()
    # pi0 alone on the aged observation (arm (a) / cheap_policy fallback)
    ts = []
    for i in range(a.n + a.warmup):
        t0 = time.perf_counter_ns()
        model.pi0_aged(hist).tolist()
        if i >= a.warmup:
            ts.append((time.perf_counter_ns() - t0) / 1e6)
    out.write(json.dumps({"kind": "pi0_aged", **base, "n": len(ts), "p50_ms": pct(ts, .5), "p95_ms": pct(ts, .95),
                          "p99_ms": pct(ts, .99), "max_ms": max(ts)}) + "\n")
# per-component cost of ONE rollout step at batch K (where the time goes)
with torch.inference_mode():
    K = a.K
    def T(f, n=150):
        for _ in range(10):
            f()
        ts = []
        for _ in range(n):
            sync(); t0 = time.perf_counter_ns(); f(); sync(); ts.append((time.perf_counter_ns() - t0) / 1e3)
        return {"p50_us": pct(ts, .5), "p99_us": pct(ts, .99)}
    fr = hist.at(-1).map(lambda x: x.expand(K, *x.shape[1:]).contiguous())
    wst, wh = model.w.E.core.prefix(model.w.E.emb.seq(hist))
    wst, wh = model.w.E.core.expand(wst, K), wh.expand(K, -1).contiguous()
    e = model.w.E.emb(fr); u = torch.randn(K, M.NCTRL); lg = model.w.logits(wh, u, u); ql = model.q.head(wh)
    samp = M.w0s_sample_next_fast if a.impl == "fast" else model.w.sample_next
    qs = M.ctrl_sample_fast if a.impl == "fast" else M.CtrlPolicy.sample
    comp = {"encode_prefix_B1_H16": T(lambda: model.w.E.core.prefix(model.w.E.emb.seq(hist))),
            "frame_embed_K": T(lambda: model.w.E.emb(fr)),
            "core_step_K": T(lambda: model.w.E.core.step(wst, e)),
            "w0s_heads_K": T(lambda: model.w.logits(wh, u, u)),
            "w0s_sample_decode_K": T(lambda: samp(fr, lg, u, u, g)),
            "q_head_K": T(lambda: model.q.head(wh)),
            "q_sample_K": T(lambda: qs(ql, g))}
    if a.core == "tx":  # no-cache step cost grows with the context: report at the end of an 18-step rollout
        st18 = torch.cat([wst, e.unsqueeze(1).expand(K, 18, -1)], 1)
        comp["core_step_K_ctx35"] = T(lambda: model.w.E.core.step(st18, e))
out.write(json.dumps({"kind": "components", **base, **comp}) + "\n")
out.write(json.dumps({"kind": "end", **base, "elapsed_s": time.perf_counter() - T0, "peak_rss_mb": peak_rss_mb(),
                      "loadavg_end": _P.loadavg(), "truncated": stop}) + "\n")
