"""Une suelos + corridas de humo en model_diagnostics.csv y emite tablas markdown (stdout) para FLOORS_REPORT.md.

Filas añadidas: para cada modelo de humo, seed="mean" y seed="std" (desviación típica muestral entre las 3 semillas,
ddof=1). Comparaciones contra el MEJOR suelo por (campo, h, subconjunto), con IC95 bootstrap por partida (val).
Uso: python3 pilot/e0/models/summarize.py > evidence/E0/floors/logs/summarize.out
"""
from __future__ import annotations

import csv
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import common as C  # noqa: E402
import metrics as M  # noqa: E402

D = os.path.join(C.REPO, "evidence", "E0", "floors")
FLOOR_MODELS_DYN = ["persist", "constvel", "constvel_fd", "condmean", "majority", "marginal"]
FLOOR_MODELS_Q = ["marginal", "persist", "cond_act", "cond_act_prev"]


def read(path):
    return list(csv.DictReader(open(path)))


def f(x):
    return float(x) if x not in ("", None) else np.nan


def main():
    floors = read(os.path.join(D, "floors_diagnostics.csv"))
    runs = []
    for p in sorted(glob.glob(os.path.join(D, "runs", "smoke_*_s[0-9].csv"))):
        runs += read(p)
    # agregados entre semillas
    groups = {}
    for r in runs:
        groups.setdefault((r["model"], r["family"], r["field"], r["h"], r["subset"]), []).append(r)
    agg = []
    for k, rs in groups.items():
        for stat in ("mean", "std"):
            o = dict(model=k[0], family=k[1], field=k[2], h=k[3], subset=k[4], seed=stat, n=rs[0]["n"])
            for m in ("mae", "rmse", "within1", "within5", "acc", "nll"):
                v = np.array([f(r[m]) for r in rs])
                if np.all(np.isnan(v)):
                    continue
                o[m] = float(np.mean(v)) if stat == "mean" else (float(np.std(v, ddof=1)) if len(v) > 1 else np.nan)
            o["n_seeds"] = len(rs)
            agg.append(o)
    allrows = floors + runs + agg
    M.write_rows(os.path.join(D, "model_diagnostics.csv"), allrows)
    print(f"model_diagnostics.csv: {len(allrows)} filas ({len(floors)} suelos, {len(runs)} humo, {len(agg)} agregados)")

    idx = {}
    for r in allrows:
        idx[(r["model"], r["family"], r["field"], str(r["h"]), r["subset"], str(r["seed"]))] = r

    def get(model, fam, field, h, sub, seed, met):
        r = idx.get((model, fam, field, str(h), sub, str(seed)))
        return f(r[met]) if r and met in r else np.nan

    # per-game para bootstrap
    pg_rows = read(os.path.join(D, "floors_per_game.csv"))
    for p in sorted(glob.glob(os.path.join(D, "runs", "smoke_*_s[0-9]_per_game.csv"))):
        pg_rows += read(p)
    pg = {}
    for r in pg_rows:
        sub, gid = r["subset"].split("@")
        pg[(r["model"], r["field"], r["h"], sub, r["seed"], gid)] = r

    def per_game(model, field, h, sub, seed, met):
        out = {}
        for (m, fl, hh, s, sd, gid), r in pg.items():
            if m == model and fl == field and hh == str(h) and s == sub and sd == str(seed) and r.get(met):
                out[gid] = (f(r[met]), int(r["n"]))
        return out

    rng = np.random.default_rng(0)

    seeds_of = {}
    for r in runs:
        seeds_of.setdefault(r["model"], set()).add(str(r["seed"]))

    def boot_diff(model, floor, field, h, sub, met, B=4000):
        """IC95 bootstrap por partida de (modelo media de las semillas disponibles − suelo); media ponderada por n."""
        seeds = sorted(seeds_of.get(model, []))
        fl = per_game(floor, field, h, sub, "-", met)
        ms = [per_game(model, field, h, sub, s, met) for s in seeds]
        gids = sorted(set(fl).intersection(*[set(m) for m in ms]))
        if len(gids) < 3:
            return np.nan, np.nan, 0
        n = np.array([fl[g][1] for g in gids], float)
        d = np.array([np.mean([m[g][0] for m in ms]) - fl[g][0] for g in gids])
        bs = []
        for _ in range(B):
            i = rng.integers(0, len(gids), len(gids))
            bs.append(np.sum(d[i] * n[i]) / np.sum(n[i]))
        return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), len(gids)

    # ---------------- tablas de suelos ----------------
    def floor_table(field, met, subsets, hs, models, fam="dyn", better="low"):
        print(f"\n**{field} — {met} ({'menor' if better == 'low' else 'mayor'} es mejor)**\n")
        print("| subconjunto | suelo | " + " | ".join(f"h={h}" for h in hs) + " |")
        print("|---|---|" + "---|" * len(hs))
        for sub in subsets:
            for m in models:
                vals = [get(m, fam, field, h, sub, "-", met) for h in hs]
                if all(np.isnan(vals)):
                    continue
                print(f"| {sub} | {m} | " + " | ".join("—" if np.isnan(v) else f"{v:.4g}" for v in vals) + " |")
        ns = [idx.get((models[0], fam, field, str(h), s, "-"), {}).get("n", "") for s in subsets for h in hs[:1]]
        print(f"\n(n por subconjunto a h={hs[0]}: " + ", ".join(f"{s}={n}" for s, n in zip(subsets, ns)) + ")")

    print("\n## Suelos de dinámica (val, 12 partidas, ambos puertos)")
    H = C.H_DYN
    subs = ["all", "event", "non_event", "ev_action_change", "ev_hitstun_start", "ev_stock_loss"]
    floor_table("action", "acc", subs, H, ["persist", "majority", "marginal"], better="high")
    floor_table("action", "nll", ["all", "event"], H, ["persist", "majority", "marginal"])
    for fld in ("pos_x", "pos_y"):
        floor_table(fld, "mae", ["all", "event", "ev_hitstun_start"], H, ["persist", "constvel", "constvel_fd", "condmean"])
        floor_table(fld, "rmse", ["event"], H, ["persist", "constvel", "constvel_fd", "condmean"])
        floor_table(fld, "within5", ["event"], H, ["persist", "constvel", "constvel_fd", "condmean"], better="high")
    for fld in ("percent", "shield", "vel_air_x_self", "vel_y_self", "vel_x_attack", "vel_y_attack",
                "vel_ground_x_self", "action_frame", "hitlag_left", "hitstun_left"):
        floor_table(fld, "mae", ["all", "event"], [1, 4, 8, 16, 32], ["persist", "constvel", "constvel_fd", "condmean"])
    for fld in ("airborne", "facing", "jumps_left", "stocks", "hurtbox"):
        floor_table(fld, "acc", ["all", "event"], [1, 4, 8, 16, 32], ["persist", "majority"], better="high")

    print("\n## Suelos del rival q (val; mando del rival en f+h; h = 7, 13 = D+1 para D = 6, 12)")
    for comp in ["buttons", "stick", "cstick"] + [f"btn_{b}" for b in C.BUTTON_NAMES]:
        floor_table(comp, "nll", ["all", "change"], C.H_Q, FLOOR_MODELS_Q, fam="q")
        floor_table(comp, "acc", ["all", "change"], C.H_Q, FLOOR_MODELS_Q, fam="q", better="high")

    # ---------------- humo frente al mejor suelo ----------------
    def best_floor(fam, field, h, sub, met, better, models):
        cands = [(get(m, fam, field, h, sub, "-", met), m) for m in models]
        cands = [c for c in cands if not np.isnan(c[0])]
        if not cands:
            return np.nan, None
        return (min(cands) if better == "low" else max(cands))

    def cmp_table(fam, field, met, better, hs, subs, models_smoke, floor_models):
        print(f"\n**{field} — {met}**: humo (media ± desv. entre semillas: {len(seeds_of.get(models_smoke[0], []))}) frente al mejor suelo; "
              "Δ = modelo − suelo; IC95 bootstrap por partida (12 partidas de val)\n")
        print("| subconjunto | h | mejor suelo | valor suelo | modelo | media ± sd | Δ | Δ/sd | mejora relativa | IC95 Δ |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for sub in subs:
            for h in hs:
                bv, bm = best_floor(fam, field, h, sub, met, better, floor_models)
                for ms in models_smoke:
                    mu = get(ms, fam, field, h, sub, "mean", met)
                    sd = get(ms, fam, field, h, sub, "std", met)
                    if np.isnan(mu):
                        continue
                    d = mu - bv
                    if met == "acc":
                        rel = ((1 - bv) - (1 - mu)) / (1 - bv)     # reducción relativa del error (1 - acc)
                    else:
                        rel = (bv - mu) / bv
                    lo, hi, ng = boot_diff(ms, bm, field, h, sub, met)
                    ci = "—" if np.isnan(lo) else f"[{lo:+.4g}, {hi:+.4g}]"
                    print(f"| {sub} | {h} | {bm} | {bv:.4g} | {ms} | {mu:.4g} ± {sd:.2g} | {d:+.4g} | "
                          f"{d / sd if sd > 0 else np.nan:+.1f} | {rel * 100:+.1f} % | {ci} |")

    smoke_dyn = ["w0s_oracle_u", "w0s_persist_u", "w0s_shuffled_u"]
    if any(r["model"].startswith("w0s") for r in runs):
        print("\n## Humo W0-S frente a suelos (val)")
        cmp_table("dyn", "action", "acc", "high", [1, 4, 8], ["event", "ev_action_change", "all"], smoke_dyn,
                  ["persist", "majority", "marginal"])
        for fld in ("pos_x", "pos_y"):
            cmp_table("dyn", fld, "mae", "low", [1, 4, 8], ["event", "all"], smoke_dyn,
                      ["persist", "constvel", "constvel_fd", "condmean"])
        for fld in ("percent", "airborne"):
            cmp_table("dyn", fld, "mae" if fld == "percent" else "acc", "low" if fld == "percent" else "high",
                      [1, 4, 8], ["event"], smoke_dyn,
                      ["persist", "constvel", "constvel_fd", "condmean"] if fld == "percent" else ["persist", "majority"])
        print("\n**action — NLL a h=1** (media ± sd)\n")
        for sub in ("all", "event"):
            bv, bm = best_floor("dyn", "action", 1, sub, "nll", "low", ["persist", "majority", "marginal"])
            for ms in smoke_dyn:
                print(f"- {sub}: {ms} {get(ms, 'dyn', 'action', 1, sub, 'mean', 'nll'):.4g} ± "
                      f"{get(ms, 'dyn', 'action', 1, sub, 'std', 'nll'):.2g} (mejor suelo {bm} {bv:.4g})")
    if any(r["model"] == "q_mlp" for r in runs):
        print("\n## Humo q frente a suelos (val)")
        for comp in ("buttons", "stick", "cstick", "btn_A", "btn_X"):
            cmp_table("q", comp, "nll", "low", C.H_Q, ["all", "change"], ["q_mlp"], FLOOR_MODELS_Q)
            cmp_table("q", comp, "acc", "high", C.H_Q, ["all", "change"], ["q_mlp"], FLOOR_MODELS_Q)
        print("\n**q frente a la marginal (NLL, all)**\n")
        for comp in ("buttons", "stick", "cstick"):
            for h in C.H_Q:
                mg = get("marginal", "q", comp, h, "all", "-", "nll")
                mu = get("q_mlp", "q", comp, h, "all", "mean", "nll")
                sd = get("q_mlp", "q", comp, h, "all", "std", "nll")
                print(f"- {comp} h={h}: marginal {mg:.4g}, q {mu:.4g} ± {sd:.2g}")

    # ---------------- tiempos ----------------
    print("\n## Tiempos y memoria de las corridas de humo")
    print("| modelo | semilla | parámetros | frames train | épocas | muestras/s (por época) | s/época | "
          "eval muestras-fwd/s | RSS pico MB | total s |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for p in sorted(glob.glob(os.path.join(D, "runs", "smoke_*_s[0-9].json"))):
        j = json.load(open(p))
        sps = "/".join(f"{e['samples_per_s']:.0f}" for e in j["epochs_log"])
        spe = "/".join(f"{e['seconds']:.0f}" for e in j["epochs_log"])
        print(f"| {j['model']} | {j['seed']} | {j['params']} | {j['train_frames']} | {j['epochs']} | {sps} | {spe} | "
              f"{j['eval_forward_samples_per_s']:.0f} | {j['max_rss_mb']:.0f} | {j['total_seconds']:.0f} |")


if __name__ == "__main__":
    main()
