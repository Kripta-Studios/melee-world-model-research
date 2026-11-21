"""E0c: mapa de predecibilidad. ¿Qué del futuro de cada jugador está fijado por la mecánica, qué depende de sus
propios mandos y qué no se puede predecir ni con ellos? Solo numpy; train/val de A6-split-v1 (test nunca se lee).

Para cada jugador p, frame f y horizonte k, objetivo y = acción de p en f+k. Predictores (tablas de mayoría
ajustadas en TRAIN, evaluadas en VAL, con back-off al nivel anterior si el contexto tiene < MIN_N muestras):
  S      : contexto mecánico de p en f   c = (acción, bin de action_frame, airborne, hitlag>0, hitstun>0)
  S+Up   : c + resumen de los mandos de p en f+1..f+k  (u = flancos de botón OR en la ventana [5 bits]
           × zona del stick en f+1 [9])
  S+Up+Uo: lo anterior + el mismo resumen de los mandos del otro jugador
"Comprometido a k": en train, P(acción mayoritaria en f+k | c) ≥ COMMIT y n ≥ MIN_N. El horizonte de compromiso de un
frame es el mayor k de la rejilla tal que está comprometido para todos los k' ≤ k.

Uso: python -X utf8 -I pilot/e0/predictability.py --out evidence/E0/predictability
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"))
import numpy as np  # noqa: E402

import common as C  # noqa: E402

KS = [1, 2, 4, 7, 8, 13, 16, 19]   # 7, 13, 19 = D+1 para D = 6, 12, 18
MIN_N = 20
COMMIT = 0.95
BTN5 = [C.BUTTONS["A"], C.BUTTONS["B"], C.BUTTONS["X"] | C.BUTTONS["Y"], C.BUTTONS["Z"],
        C.BUTTONS["L"] | C.BUTTONS["R"]]


def zone(x, y, dead=0.3 * 80):
    """Zona del stick: 0 neutro, 1..8 octantes."""
    x = x.astype(np.float32); y = y.astype(np.float32)
    r = np.hypot(x, y)
    ang = (np.degrees(np.arctan2(y, x)) + 360 + 22.5) % 360
    z = 1 + (ang // 45).astype(np.int64)
    return np.where(r < dead, 0, z)


def press_bits(btn):
    """[N] bits de 5 grupos de botones 'pulsados' en cada fila."""
    out = np.zeros(btn.shape, np.int64)
    for i, m in enumerate(BTN5):
        out |= ((btn & m) != 0).astype(np.int64) << i
    return out


def table_fit(key, y):
    """Mayoría y su frecuencia por clave. Devuelve (claves únicas ordenadas, mayoritaria, p_mayoritaria, n)."""
    order = np.lexsort((y, key))
    k, yy = key[order], y[order]
    pair_change = np.r_[True, (k[1:] != k[:-1]) | (yy[1:] != yy[:-1])]
    pk, py = k[pair_change], yy[pair_change]
    pc = np.diff(np.r_[np.flatnonzero(pair_change), len(k)])
    # para cada clave: el par con mayor cuenta
    key_change = np.r_[True, pk[1:] != pk[:-1]]
    starts = np.flatnonzero(key_change)
    uk = pk[starts]
    tot = np.add.reduceat(pc, starts)
    # argmax por grupo
    grp = np.cumsum(key_change) - 1
    best = np.full(len(uk), -1); bestc = np.zeros(len(uk), np.int64)
    o2 = np.lexsort((-pc, grp))
    first = np.r_[True, grp[o2][1:] != grp[o2][:-1]]
    sel = o2[first]
    best[grp[sel]] = py[sel]; bestc[grp[sel]] = pc[sel]
    return uk, best, bestc / tot, tot


def table_predict(tab, key):
    uk, best, p, n = tab
    i = np.searchsorted(uk, key)
    i = np.clip(i, 0, len(uk) - 1)
    hit = (uk[i] == key) & (n[i] >= MIN_N)
    return np.where(hit, best[i], -1), np.where(hit, p[i], np.nan)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    arr, games = C.load_cache(fields=["action", "action_frame", "airborne", "hitlag_left", "hitstun_left",
                                      "buttons_phys", "joy_x", "joy_y"])
    act = np.asarray(arr["action"]).astype(np.int64)
    ctx = (((act * C.AF_BINS + C.af_bin(arr["action_frame"])) * 2 + np.asarray(arr["airborne"]).astype(np.int64))
           * 4 + (np.asarray(arr["hitlag_left"]) > 0) * 2 + (np.asarray(arr["hitstun_left"]) > 0))
    btn = np.asarray(arr["buttons_phys"]).astype(np.int64)
    pb = press_bits(btn)
    edge = np.zeros_like(pb)
    z = zone(np.asarray(arr["joy_x"]), np.asarray(arr["joy_y"]))

    # índices de ancla por split (f con f+max(KS) dentro de la partida, sin cruzar partidas)
    idx = {"train": [], "val": []}
    for g in games:
        s, n = g["start"], g["n"]
        if n <= max(KS) + 1:
            continue
        idx[g["split"]].append(np.arange(s, s + n - max(KS) - 1))
        # flancos de pulsación dentro de la partida
        e = pb[s:s + n].copy()
        e[1:] = pb[s + 1:s + n] & ~pb[s:s + n - 1]
        edge[s:s + n] = e
    idx = {k: np.concatenate(v) for k, v in idx.items()}

    def window_or(f, k, p):
        out = np.zeros(len(f), np.int64)
        for j in range(1, k + 1):
            out |= edge[f + j, p]
        return out

    res = {"config": {"KS": KS, "MIN_N": MIN_N, "COMMIT": COMMIT, "n_anchor_train": int(len(idx["train"])),
                      "n_anchor_val": int(len(idx["val"])), "split": C.SPLIT_KEY}, "by_k": {}}
    commit_ok = {s: np.ones((len(idx[s]), 2), bool) for s in ("train", "val")}
    commit_h = {s: np.zeros((len(idx[s]), 2), np.int64) for s in ("train", "val")}
    for k in KS:
        rk = {}
        for p in (0, 1):
            o = 1 - p
            ft, fv = idx["train"], idx["val"]
            ytr, yva = act[ft + k, p], act[fv + k, p]
            ctr, cva = ctx[ft, p], ctx[fv, p]
            up_tr = window_or(ft, k, p) * 9 + z[ft + 1, p]
            up_va = window_or(fv, k, p) * 9 + z[fv + 1, p]
            uo_tr = window_or(ft, k, o) * 9 + z[ft + 1, o]
            uo_va = window_or(fv, k, o) * 9 + z[fv + 1, o]
            # niveles
            tS = table_fit(ctr, ytr)
            tA = table_fit(act[ft, p], ytr)  # back-off: solo la acción
            tSU = table_fit(ctr * 288 + up_tr, ytr)
            tSUU = table_fit((ctr * 288 + up_tr) * 288 + uo_tr, ytr)
            pers = act[fv, p]
            prA, _ = table_predict(tA, act[fv, p]); prA = np.where(prA < 0, pers, prA)
            prS, pS = table_predict(tS, cva); prS = np.where(prS < 0, prA, prS)
            prSU, _ = table_predict(tSU, cva * 288 + up_va); prSU = np.where(prSU < 0, prS, prSU)
            prSUU, _ = table_predict(tSUU, (cva * 288 + up_va) * 288 + uo_va); prSUU = np.where(prSUU < 0, prSU, prSUU)
            # compromiso (definido en train, aplicado en val y en train para la fracción de tiempo)
            _, pS_tr = table_predict(tS, ctr)
            for s, pp in (("train", pS_tr), ("val", pS)):
                c = np.nan_to_num(pp, nan=0.0) >= COMMIT
                commit_ok[s][:, p] &= c
                commit_h[s][:, p] = np.where(commit_ok[s][:, p], k, commit_h[s][:, p])
            ev = yva != act[fv, p]
            com = np.nan_to_num(pS, nan=0.0) >= COMMIT
            def acc(pr, m):
                return float((pr[m] == yva[m]).mean()) if m.any() else None
            for name, m in (("all", np.ones_like(ev)), ("event", ev), ("event_committed", ev & com),
                            ("event_choice", ev & ~com), ("committed", com), ("choice", ~com)):
                rk.setdefault(name, {"n": 0, "persist": [], "S": [], "S+Up": [], "S+Up+Uo": []})
                rk[name]["n"] += int(m.sum())
                for lab, pr in (("persist", pers), ("S", prS), ("S+Up", prSU), ("S+Up+Uo", prSUU)):
                    rk[name][lab].append(acc(pr, m))
            rk.setdefault("frac_committed_val", []).append(float(com.mean()))
        for name, d in rk.items():
            if isinstance(d, dict):
                for lab in ("persist", "S", "S+Up", "S+Up+Uo"):
                    v = [x for x in d[lab] if x is not None]
                    d[lab] = float(np.mean(v)) if v else None
        rk["frac_committed_val"] = float(np.mean(rk["frac_committed_val"]))
        res["by_k"][str(k)] = rk
        print(f"[{time.time() - t0:6.1f}s] k={k} committed={rk['frac_committed_val']:.3f} "
              f"event S={rk['event']['S']:.3f} S+Up={rk['event']['S+Up']:.3f} S+Up+Uo={rk['event']['S+Up+Uo']:.3f}",
              flush=True)
    # horizonte de compromiso: fracción del tiempo con compromiso >= D+1
    hz = {}
    for s in ("train", "val"):
        h = commit_h[s]
        hz[s] = {f">={k}": float((h >= k).mean()) for k in KS}
        hz[s]["both_players_>=7"] = float(((h >= 7).all(1)).mean())
        hz[s]["at_least_one_>=7"] = float(((h >= 7).any(1)).mean())
    res["commitment_horizon_fraction"] = hz
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(a.out, "predictability.json"), "w", encoding="utf-8"), indent=1)
    print(json.dumps(res["commitment_horizon_fraction"], indent=1))


if __name__ == "__main__":
    main()
