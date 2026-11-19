"""A8: power and pseudo-replication calculation (analytic + Monte Carlo). No game data; synthetic model only.
Model: arm a, training seed s, game g: win ~ Bernoulli(clip(p_a + u_s, 0, 1)), u_s ~ N(0, sigma_s^2).
Usage: python3 -I power.py OUT.json
"""
import json, math, sys
import numpy as np

Z = 1.959964 + 0.841621  # alpha=0.05 two-sided, power 0.80

def seeds_needed(delta, sigma_s, games_per_seed, p=0.5):
    var_seed_mean = sigma_s**2 + p * (1 - p) / games_per_seed
    return math.ceil(2 * Z**2 * var_seed_mean / delta**2)

def mde(seeds, sigma_s, games_per_seed, p=0.5):
    return Z * math.sqrt(2 * (sigma_s**2 + p * (1 - p) / games_per_seed) / seeds)

def games_needed_single_checkpoint(delta, p=0.5):
    # same frozen checkpoint, two deployment-time variants (e.g. P0 vs S0), independent games
    return math.ceil(2 * Z**2 * p * (1 - p) / delta**2)

def pseudo_rep_fpr(sigma_s, seeds, games, reps=4000, rng=np.random.default_rng(0)):
    """False-positive rate of a naive game-level z-test when both arms have equal true p=0.5."""
    fp_naive = fp_seed = 0
    for _ in range(reps):
        res = []
        for _arm in range(2):
            u = rng.normal(0, sigma_s, seeds)
            pr = np.clip(0.5 + u, 0, 1)
            wins = rng.binomial(games, pr)
            res.append(wins / games)
        a, b = res
        # naive: pool all games as independent
        pa, pb = a.mean(), b.mean(); n = seeds * games
        se = math.sqrt(pa * (1 - pa) / n + pb * (1 - pb) / n)
        fp_naive += abs(pa - pb) / se > 1.96 if se > 0 else 0
        if seeds > 1:
            se2 = math.sqrt(a.var(ddof=1) / seeds + b.var(ddof=1) / seeds)
            from scipy import stats
            t = (pa - pb) / se2 if se2 > 0 else 0
            df = 2 * seeds - 2
            fp_seed += abs(t) > stats.t.ppf(0.975, df)
    return fp_naive / reps, (fp_seed / reps if seeds > 1 else None)

out = {"z_alpha_plus_z_beta": Z, "assumptions": "p=0.5 base win rate; independent training seeds per arm; no pairing gain; sigma_s = between-seed sd of true win rate (unknown for Melee, to be estimated in E2)"}
out["seeds_needed"] = {f"delta={d}_sigma_s={s}_G={g}": seeds_needed(d, s, g)
                       for d in (0.05, 0.10) for s in (0.0, 0.03, 0.05, 0.08) for g in (40, 200, 1000)}
out["mde_pp"] = {f"S={S}_sigma_s={s}_G={g}": round(100 * mde(S, s, g), 1)
                 for S in (1, 3, 5, 10) for s in (0.03, 0.05, 0.08) for g in (40, 200)}
out["games_single_checkpoint"] = {f"delta={d}": games_needed_single_checkpoint(d) for d in (0.05, 0.10, 0.20, 0.30)}
out["mde_pp_single_checkpoint_40_games"] = round(100 * Z * math.sqrt(2 * 0.25 / 40), 1)
out["pseudo_replication_fpr"] = {f"sigma_s={s}_S={S}_G={g}": pseudo_rep_fpr(s, S, g, reps=1500)
                                 for s in (0.05,) for S, g in ((1, 200), (5, 40), (5, 200))}
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(json.dumps(out, indent=1))
