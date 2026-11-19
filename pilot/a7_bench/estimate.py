"""A7 estimates from measured CPU numbers + explicit assumptions -> evidence/A7/budget.json (section 'derived').
All outputs here are ESTIMACIONES (INFERENCIA), except the copied measured inputs.
Usage: python3 -I estimate.py
Formulas (recompute by editing ASSUMPTIONS):
  decision_ms(K,T,H)   = enc_ms(H) + T * pstep_ms(K) + overhead_ms              [CPU, p99 of each term summed]
  pstep_ms(B)          = log-log interpolation of measured pstep p99 over B
  gpu_step_ms(B)       = max(kernels * launch_us/1000, flops_step(B) / (eff_tflops*1e9))
  flops_step(B)        = 2 * pred_params * B * (W if tx else 1)
  train_flops/sample   = 6 * (enc_params * L_enc_tokens + pred_params * P * W_pred) + sigreg_flops
  cpu_train_hours      = frames * epochs / samples_per_s / 3600   (1 window per frame, stride 1)
  gpu_train_hours      = frames * epochs * train_flops/sample / (eff_tflops*1e12) / 3600
"""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.join(HERE, "..", "..", "evidence", "A7")
summ = json.load(open(os.path.join(EV, "measurements", "summary.json")))

ASSUMPTIONS = {
    "frames_per_game": 10620,      # A6 DATA_AND_TIME.md §9 (HAL ranked mean, countdown incl.)
    "games": [1000, 10000],
    "epochs": [1, 10],             # LeWM paper: 10 epochs/env (DOC, A3 §6); config says 100
    "agent_budget_ms": {"sim_or_fast_strict": 16.0, "dolphin_realtime_conservative": 10.0, "half_frame": 8.0},
    "decision_overhead_ms": 0.5,   # python glue, state->tensor, controller write (SUPUESTO; measure in E2)
    "gpu": {   # SUPUESTO A VERIFICAR: VRAM nominal; eff_tflops = sustained on small models (<<peak); price = marketplace order of magnitude, 2026
        "L4_24GB": {"vram_gb": 24, "eff_tflops_train": 12, "eff_tflops_infer": 8, "usd_h": [0.4, 0.8]},
        "RTX4090_24GB": {"vram_gb": 24, "eff_tflops_train": 35, "eff_tflops_infer": 20, "usd_h": [0.3, 0.7]},
        "A100_80GB": {"vram_gb": 80, "eff_tflops_train": 60, "eff_tflops_infer": 30, "usd_h": [1.2, 2.0]},
    },
    "gpu_launch_us": {"eager": 10.0, "cuda_graph": 2.0},   # SUPUESTO per kernel incl. host dispatch
    "kernels_per_pred_step": {"mlp": 10, "gru": 14, "tx": None},  # tx: 15 per layer + 6
    "tx_kernels_per_layer": 15,
    "train_P": 4, "train_W_pred": 8,
    "bytes_per_param_ckpt": 12,    # fp32 weights + Adam m,v
}


def interp(xs, ys, x):
    pts = sorted(zip(xs, ys))
    if x <= pts[0][0]:
        return pts[0][1] * (x / pts[0][0]) if x < pts[0][0] else pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            t = (math.log(x) - math.log(x0)) / (math.log(x1) - math.log(x0))
            return math.exp(math.log(y0) + t * (math.log(y1) - math.log(y0)))
    (x0, y0), (x1, y1) = pts[-2], pts[-1]  # linear extrapolation in B beyond measured
    return y1 * x / x1


def cfg_iter():
    for k, v in summ["params"].items():
        a, t = k.split("/")
        yield a, t, v


derived = {"cpu_realtime_mpc": [], "gpu_realtime_mpc": [], "train_hours": [], "notes": []}
Ks = [1, 16, 64, 256, 512]
Ts = [1, 4, 8, 16, 32]
for a, t, pv in cfg_iter():
    for thr in (1, 3):
        ps = [r for r in summ["pstep"] if r["arch"] == a and r["tier"] == t and r["threads"] == thr]
        en = {r["H"]: r["p99_ms"] for r in summ["encode"] if r["arch"] == a and r["tier"] == t and r["threads"] == thr}
        if not ps or 32 not in en:
            continue
        Bs = [r["B"] for r in ps]; ys = [r["p99_ms"] for r in ps]
        for name, bud in ASSUMPTIONS["agent_budget_ms"].items():
            avail = bud - ASSUMPTIONS["decision_overhead_ms"] - en[32]
            fit = {}
            for K in Ks:
                st = interp(Bs, ys, K)
                fit[f"K={K}"] = max(0, int(avail // st)) if avail > 0 else 0
            derived["cpu_realtime_mpc"].append({"arch": a, "tier": t, "threads": thr, "budget": name, "budget_ms": bud,
                                                "enc_H32_p99_ms": en[32], "max_T_for_K": fit})

for a, t, pv in cfg_iter():
    tx = a == "tx"
    from_meta = {"1M": (128, 3), "5M": (256, 4), "15M": (384, 5)}
    kern = (ASSUMPTIONS["tx_kernels_per_layer"] * from_meta[t][1] + 6) if tx else ASSUMPTIONS["kernels_per_pred_step"][a]
    for g, gv in ASSUMPTIONS["gpu"].items():
        for mode, lus in ASSUMPTIONS["gpu_launch_us"].items():
            row = {"arch": a, "tier": t, "gpu": g, "launch_mode": mode, "kernels_per_step": kern, "step_ms": {}}
            for K in Ks:
                fl = 2 * pv["pred"] * K * (8 if tx else 1)
                row["step_ms"][f"K={K}"] = round(max(kern * lus / 1000, fl / (gv["eff_tflops_infer"] * 1e9)), 4)
            row["max_T_K256_in_12ms"] = int((12 - 1.0) // row["step_ms"]["K=256"])  # 1 ms enc+transfer (SUPUESTO)
            derived["gpu_realtime_mpc"].append(row)

# training
for a, t, pv in cfg_iter():
    for H in (8, 32):
        rows = [r for r in summ["train"] if r["arch"] == a and r["tier"] == t and r["H"] == H and r["threads"] == 3 and r["sigreg"]]
        if not rows:
            continue
        rows.sort(key=lambda r: (r["steps"] >= 10, r["B"]), reverse=True)
        sel = rows[0]
        sps = sel["samples_per_s"]
        L = H + ASSUMPTIONS["train_P"]
        enc_tokens = L if a != "mlp" else (ASSUMPTIONS["train_P"] + 1)  # mlp: one pass per window
        flops = 6 * (pv["enc"] * enc_tokens + pv["pred"] * ASSUMPTIONS["train_P"] * (ASSUMPTIONS["train_W_pred"] if a == "tx" else 1))
        for G in ASSUMPTIONS["games"]:
            frames = G * ASSUMPTIONS["frames_per_game"]
            for E in ASSUMPTIONS["epochs"]:
                row = {"arch": a, "tier": t, "H": H, "games": G, "epochs": E, "samples": frames * E,
                       "cpu3_samples_per_s_measured": round(sps, 1), "measured_B": sel["B"], "measured_steps": sel["steps"],
                       "low_confidence": sel["steps"] < 10,
                       "cpu3_hours": round(frames * E / sps / 3600, 1), "train_flops_per_sample": flops, "gpu": {}}
                for g, gv in ASSUMPTIONS["gpu"].items():
                    h = frames * E * flops / (gv["eff_tflops_train"] * 1e12) / 3600
                    row["gpu"][g] = {"hours_compute_bound": round(h, 3), "usd": [round(h * p, 2) for p in gv["usd_h"]]}
                derived["train_hours"].append(row)

derived["notes"].append("GPU training hours are compute-bound lower bounds: small models on GPU are usually "
                        "input-pipeline or launch bound; multiply by 3-10x until E2 measures it (SUPUESTO).")
derived["checkpoint_mb"] = {f"{a}/{t}": round((pv['enc'] + pv['pred']) * ASSUMPTIONS["bytes_per_param_ckpt"] / 2**20, 1)
                            for a, t, pv in cfg_iter()}
json.dump({"assumptions": ASSUMPTIONS, "derived": derived}, open(os.path.join(EV, "measurements", "estimates.json"), "w"), indent=1)
print(json.dumps(derived["cpu_realtime_mpc"][:3], indent=1))
