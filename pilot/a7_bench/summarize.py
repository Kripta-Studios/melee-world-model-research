"""Summarise A7 raw measurements into tables (stdout, markdown) and measurements/summary.json.
Usage: python3 -I summarize.py
"""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
M = os.path.join(HERE, "..", "..", "evidence", "A7", "measurements")


def load(name):
    p = os.path.join(M, name)
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


inf, sig, tr = load("infer.jsonl"), load("sigreg.jsonl"), load("train.jsonl")
summ = {"files": {}}
for n in ("infer.jsonl", "sigreg.jsonl", "train.jsonl", "commands.log"):
    p = os.path.join(M, n)
    if os.path.exists(p):
        summ["files"][n] = hashlib.sha256(open(p, "rb").read()).hexdigest()

params = {}
for r in inf:
    if r["kind"] == "encode" and r["H"] == 32:
        params[(r["arch"], r["tier"])] = (r["meta"]["enc_params"], r["meta"]["pred_params"], r["meta"])

print("## Parámetros\n\n| arch | tier | enc | pred | total | config |\n|---|---|---|---|---|---|")
for (a, t), (e, p, m) in sorted(params.items()):
    cfg = {k: v for k, v in m.items() if k not in ("arch", "tier", "S", "A", "D", "H", "enc_params", "pred_params", "total_params")}
    print(f"| {a} | {t} | {e/1e6:.2f}M | {p/1e6:.2f}M | {(e+p)/1e6:.2f}M | {cfg} |")
summ["params"] = {f"{a}/{t}": {"enc": e, "pred": p} for (a, t), (e, p, _) in params.items()}

def tab(kind, keys, title):
    rows = [r for r in inf if r["kind"] == kind]
    print(f"\n## {title}\n\n| arch | tier | thr | " + " | ".join(keys) + " | p50 ms | p95 ms | p99 ms | n |")
    print("|---|---|---|" + "---|" * (len(keys) + 4))
    out = []
    for r in sorted(rows, key=lambda r: (r["arch"], ["1M", "5M", "15M"].index(r["tier"]), r["threads"], *[r[k] for k in keys])):
        print(f"| {r['arch']} | {r['tier']} | {r['threads']} | " + " | ".join(str(r[k]) for k in keys) +
              f" | {r['p50_ms']:.3f} | {r['p95_ms']:.3f} | {r['p99_ms']:.3f} | {r['n']} |")
        out.append({k: r[k] for k in ("arch", "tier", "threads", *keys, "p50_ms", "p95_ms", "p99_ms", "n")})
    summ[kind] = out

tab("encode", ["H"], "Encoder batch 1")
tab("pstep", ["B"], "Un paso de predictor a batch B")
tab("rollout", ["K", "T"], "Rollout secuencial real (K candidatos × T pasos)")
tab("decision", ["K", "T"], "Decisión MPC completa (encode H=32 + rollout + score + argmax)")
skips = [r for r in inf if r["kind"] == "skip"]
summ["skips"] = skips
ends = [r for r in inf if r["kind"] == "end"]
summ["infer_peak_rss_mb_max"] = max((r["peak_rss_mb"] for r in ends), default=None)
print("\nskips:", [(r["arch"], r["tier"], r["threads"], r["what"], r["reason"]) for r in skips])
print("infer peak RSS max MB:", summ["infer_peak_rss_mb_max"])
print("load at env:", sorted({r["loadavg"].split()[0] for r in inf if r["kind"] == "env"}))

print("\n## SIGReg fwd+bwd\n\n| thr | T | N | D | M | p50 ms | p95 ms | n | peak RSS MB |\n|---|---|---|---|---|---|---|---|---|")
thr = None
summ["sigreg"] = []
for r in sig:
    if r["kind"] == "env":
        thr = r["threads"]
    if r["kind"] == "crosscheck":
        print("crosscheck:", r); summ["sigreg_crosscheck"] = r
    if r["kind"] == "sigreg_fb":
        print(f"| {thr} | {r['T']} | {r['N']} | {r['D']} | {r['M']} | {r['p50_ms']:.1f} | {r['p95_ms']:.1f} | {r['n']} | {r['peak_rss_mb']:.0f} |")
        summ["sigreg"].append({"threads": thr, **{k: r[k] for k in ("T", "N", "D", "M", "p50_ms", "p95_ms", "n", "peak_rss_mb")}})

print("\n## Entrenamiento CPU (B=64, P=4)\n\n| arch | tier | thr | H | sigreg | step p50 ms | muestras/s | transiciones/s | peak RSS MB | steps |\n|---|---|---|---|---|---|---|---|---|---|")
summ["train"] = []
for r in sorted([r for r in tr if r["kind"] == "train"], key=lambda r: (r["arch"], ["1M", "5M", "15M"].index(r["tier"]), r["threads"], r["H"], not r["sigreg"])):
    print(f"| {r['arch']} | {r['tier']} | {r['threads']} | {r['H']} | {r['sigreg']} | {r['step_p50_ms']:.0f} | {r['samples_per_s']:.1f} | {r['transitions_per_s']:.0f} | {r['peak_rss_mb']:.0f} | {r['steps']} |")
    summ["train"].append({k: r[k] for k in ("arch", "tier", "threads", "H", "B", "P", "sigreg", "step_p50_ms", "samples_per_s", "transitions_per_s", "peak_rss_mb", "steps")})
print("aborts:", [r for r in tr if r["kind"] == "abort"])
json.dump(summ, open(os.path.join(M, "summary.json"), "w"), indent=1)
