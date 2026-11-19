"""Suelos triviales de E0 (dinámica y rival q), estimados en train y medidos en val (split A6-split-v1).

Dinámica (por jugador, ambos puertos agregados), h ∈ H_DYN:
  persist      x̂_{f+h} = x_f (todos los campos)
  constvel     pos += h·v_f (velocidad Slippi: aire/suelo + knockback); counters: action_frame+h, hitlag/hitstun -h
  constvel_fd  pos += h·(pos_f - pos_{f-1})
  condmean     x̂ = x_f + E_train[Δ_h | acción_f, floor(action_frame_f)] (x-campos con signo de facing)
  majority     discretos: moda_train de campo_{f+h} | (acción_f, floor(action_frame_f), campo_f); clave no vista -> persist
Rival (mando del rival en f+h, h ∈ H_Q, régimen I_full: u_f del rival es observable):
  marginal, persist (p_stay(h) de train + marginal), cond_act (| acción del rival), cond_act_prev (| acción, u_f)
  componentes: 8 botones (Bernoulli), stick principal y C-stick como celda conjunta de la rejilla 1/80 sobre
  vocabulario top-K de train + OTHER.

Uso (cualquier python con numpy): nice -n 19 python3 pilot/e0/models/floors.py --out evidence/E0/floors
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import common as C  # noqa: E402
import metrics as M  # noqa: E402

DISC_DYN = ["facing", "airborne", "jumps_left", "stocks", "hurtbox"]
COUNTER_DIR = {"action_frame": +1, "hitlag_left": -1, "hitstun_left": -1}
K_STICK, K_CSTICK = 512, 64
ALPHA = 1.0
PER_GAME_FIELDS = {"action", "pos_x", "pos_y", "stick", "cstick", "buttons", "btn_A", "btn_X"}
PER_GAME_SUBSETS = {"all", "event", "change", "ev_action_change"}


def kind_of(field):
    return "cont" if field in C.CONT else "disc"


def game_view(arrs, g):
    s, n = g["start"], g["n"]
    return {k: np.asarray(v[s:s + n]) for k, v in arrs.items()}


def build_vocab(arrs, games):
    tr = [g for g in games if g["split"] == "train"]
    act_c, st_c, cs_c = {}, {}, {}
    for g in tr:
        v = game_view(arrs, g)
        for dct, vals in ((act_c, v["action"].ravel()),
                          (st_c, C.stick_code(v["joy_x"], v["joy_y"]).ravel()),
                          (cs_c, C.stick_code(v["cstick_x"], v["cstick_y"]).ravel())):
            u, c = np.unique(vals, return_counts=True)
            for a, b in zip(u.tolist(), c.tolist()):
                dct[a] = dct.get(a, 0) + b
    actions = sorted(act_c)
    sticks = [k for k, _ in sorted(st_c.items(), key=lambda kv: -kv[1])[:K_STICK]]
    csticks = [k for k, _ in sorted(cs_c.items(), key=lambda kv: -kv[1])[:K_CSTICK]]
    cover = lambda d, keep: sum(d[k] for k in keep) / sum(d.values())  # noqa: E731
    return dict(actions=actions, sticks=sticks, csticks=csticks, n_stick_cells_train=len(st_c),
                n_cstick_cells_train=len(cs_c), stick_topk_coverage_train=cover(st_c, sticks),
                cstick_topk_coverage_train=cover(cs_c, csticks))


class Vocab:
    def __init__(self, voc):
        self.voc = voc
        self.n_act = len(voc["actions"]) + 1      # + UNK
        self.n_st = len(voc["sticks"]) + 1        # + OTHER
        self.n_cs = len(voc["csticks"]) + 1
        self._a = np.full(65536, self.n_act - 1, np.int64)
        self._a[np.array(voc["actions"])] = np.arange(len(voc["actions"]))
        self._s = np.full(161 * 161, self.n_st - 1, np.int64)
        self._s[np.array(voc["sticks"])] = np.arange(len(voc["sticks"]))
        self._c = np.full(161 * 161, self.n_cs - 1, np.int64)
        self._c[np.array(voc["csticks"])] = np.arange(len(voc["csticks"]))

    def act(self, a):
        return self._a[np.asarray(a, np.int64)]

    def stick(self, x, y):
        return self._s[C.stick_code(x, y)]

    def cstick(self, x, y):
        return self._c[C.stick_code(x, y)]


def q_components(v, V, p):
    """dict componente -> array de clases por frame del jugador p (botones como 0/1)."""
    bits = C.button_bits(v["buttons_phys"][:, p])
    out = {f"btn_{b}": bits[:, i].astype(np.int64) for i, b in enumerate(C.BUTTON_NAMES)}
    out["stick"] = V.stick(v["joy_x"][:, p], v["joy_y"][:, p])
    out["cstick"] = V.cstick(v["cstick_x"][:, p], v["cstick_y"][:, p])
    return out


def dkey(V, v, p, f):
    return V.act(v["action"][f, p]) * C.AF_BINS + C.af_bin(v["action_frame"][f, p])


def dval(field, x):
    x = np.asarray(x, np.int64)
    return x + 1 if field == "facing" else x


# ---------------------------------------------------------------- train
def fit(arrs, games, V):
    tr = [g for g in games if g["split"] == "train"]
    nk = V.n_act * C.AF_BINS
    st = {"act_marg": np.zeros(V.n_act, np.int64), "act_stay": {h: [0, 0] for h in C.H_DYN}}
    st["act_cond"] = {h: M.SparseCounts(V.n_act) for h in C.H_DYN}
    st["disc_cond"] = {(d, h): M.SparseCounts(8) for d in DISC_DYN for h in C.H_DYN}
    st["cm_sum"] = {(c, h): np.zeros(nk) for c in C.CONT for h in C.H_DYN}
    st["cm_n"] = {h: np.zeros(nk) for h in C.H_DYN}
    comps = [f"btn_{b}" for b in C.BUTTON_NAMES] + ["stick", "cstick"]
    ncls = {c: 2 for c in comps}
    ncls.update(stick=V.n_st, cstick=V.n_cs)
    st["q_marg"] = {c: np.zeros(ncls[c], np.int64) for c in comps}
    st["q_stay"] = {(c, h): [0, 0] for c in comps for h in C.H_Q}
    st["q_cact"] = {(c, h): np.zeros((V.n_act, ncls[c]), np.int64) for c in comps for h in C.H_Q}
    st["q_cap"] = {(c, h): M.SparseCounts(ncls[c]) for c in comps for h in C.H_Q}
    for gi, g in enumerate(tr):
        v = game_view(arrs, g)
        n = g["n"]
        for p in range(2):
            a_idx = V.act(v["action"][:, p])
            st["act_marg"] += np.bincount(a_idx, minlength=V.n_act)
            fac = np.where(v["facing"][:, p] < 0, -1.0, 1.0)
            for h in C.H_DYN:
                f = np.arange(0, n - h)
                key = dkey(V, v, p, f)
                st["act_cond"][h].add(key, a_idx[f + h])
                st["act_stay"][h][0] += int((a_idx[f + h] == a_idx[f]).sum())
                st["act_stay"][h][1] += len(f)
                for d in DISC_DYN:
                    x = dval(d, v[d][:, p])
                    st["disc_cond"][(d, h)].add(key * 8 + x[f], x[f + h])
                st["cm_n"][h] += np.bincount(key, minlength=nk)
                for c in C.CONT:
                    x = v[c][:, p].astype("f8")
                    dlt = x[f + h] - x[f]
                    if c in M.X_SIGNED:
                        dlt = dlt * fac[f]
                    st["cm_sum"][(c, h)] += np.bincount(key, weights=dlt, minlength=nk)
            qc = q_components(v, V, p)
            for c, y in qc.items():
                st["q_marg"][c] += np.bincount(y, minlength=ncls[c])
                for h in C.H_Q:
                    f = np.arange(0, n - h)
                    st["q_stay"][(c, h)][0] += int((y[f + h] == y[f]).sum())
                    st["q_stay"][(c, h)][1] += len(f)
                    st["q_cact"][(c, h)] += np.bincount(a_idx[f] * ncls[c] + y[f + h],
                                                        minlength=V.n_act * ncls[c]).reshape(V.n_act, ncls[c])
                    st["q_cap"][(c, h)].add(a_idx[f] * ncls[c] + y[f], y[f + h])
        if (gi + 1) % 50 == 0:
            print(f"  fit {gi+1}/{len(tr)}", flush=True)
    for dct in (st["act_cond"], st["disc_cond"], st["q_cap"]):
        for sc in dct.values():
            sc.finalize()
    st["ncls"] = ncls
    st["comps"] = comps
    return st


# ---------------------------------------------------------------- val
def evaluate(arrs, games, V, st, acc, pg):
    va = [g for g in games if g["split"] == "val"]
    assert all(g["split"] == "val" for g in va)
    pm_act = M.smoothed_marginal(st["act_marg"])
    for g in va:
        v = game_view(arrs, g)
        f = C.anchors(g["n"])
        gid = g["sha1"][:10]
        for p in range(2):
            a_idx = V.act(v["action"][:, p])
            fac = np.where(v["facing"][:, p] < 0, -1.0, 1.0)
            vx, vy = M.slp_velocity(v, p)
            for h in C.H_DYN:
                masks = C.event_masks(v, p, f, h)
                key = dkey(V, v, p, f)
                cmn = st["cm_n"][h][key]

                def put(model, field, pred, true, nll=None):
                    for sname, m in masks.items():
                        k = (model, "dyn", field, h, sname, "-")
                        if kind_of(field) == "cont":
                            acc.cont(k, pred, true, m)
                            if field in PER_GAME_FIELDS and sname in PER_GAME_SUBSETS:
                                pg.cont(k + (gid,), pred, true, m)
                        else:
                            acc.disc(k, pred, true, m, nll)
                            if field in PER_GAME_FIELDS and sname in PER_GAME_SUBSETS:
                                pg.disc(k + (gid,), pred, true, m, nll)

                for c in C.CONT:
                    x = v[c][:, p].astype("f8")
                    true = x[f + h]
                    put("persist", c, M.persistence(x, f, h), true)
                    if c == "pos_x":
                        put("constvel", c, M.const_velocity(x, vx, f, h), true)
                        put("constvel_fd", c, M.const_velocity_fd(x, f, h), true)
                    elif c == "pos_y":
                        put("constvel", c, M.const_velocity(x, vy, f, h), true)
                        put("constvel_fd", c, M.const_velocity_fd(x, f, h), true)
                    elif c in COUNTER_DIR:
                        put("constvel", c, M.counter_clock(x, f, h, COUNTER_DIR[c]), true)
                    else:
                        put("constvel_fd", c, M.const_velocity_fd(x, f, h), true)
                    mean_d = np.where(cmn > 0, st["cm_sum"][(c, h)][key] / np.maximum(cmn, 1), 0.0)
                    if c in M.X_SIGNED:
                        mean_d = mean_d * fac[f]
                    put("condmean", c, x[f] + mean_d, true)
                # acción
                yt = a_idx[f + h]
                p_stay = st["act_stay"][h][0] / st["act_stay"][h][1]
                nll_p = -np.log(p_stay * (yt == a_idx[f]) + (1 - p_stay) * pm_act[yt])
                put("persist", "action", a_idx[f], yt, nll_p)
                put("marginal", "action", np.full(len(f), int(np.argmax(pm_act))), yt,
                    -np.log(pm_act[yt]))
                ckt, ck, mode, seen = st["act_cond"][h].lookup(key, yt)
                put("majority", "action", np.where(seen, mode, a_idx[f]), yt, M.cond_nll(ckt, ck, pm_act[yt], ALPHA))
                for d in DISC_DYN:
                    x = dval(d, v[d][:, p])
                    put("persist", d, x[f], x[f + h])
                    _c, _k, mode, seen = st["disc_cond"][(d, h)].lookup(key * 8 + x[f], x[f + h])
                    put("majority", d, np.where(seen, mode, x[f]), x[f + h])
            # ---- rival q: el jugador p es el rival ----
            qc = q_components(v, V, p)
            for h in C.H_Q:
                bits_true, bits_pred = {}, {}
                for c, y in qc.items():
                    yt, y0 = y[f + h], y[f]
                    nc = st["ncls"][c]
                    marg = M.smoothed_marginal(st["q_marg"][c])
                    ps = st["q_stay"][(c, h)][0] / st["q_stay"][(c, h)][1]
                    cact = st["q_cact"][(c, h)][a_idx[f]]                       # [n, nc]
                    ck = cact.sum(1)
                    p_cact = (cact + ALPHA * marg[None, :]) / (ck[:, None] + ALPHA)
                    ckt2, ck2, mode2, seen2 = st["q_cap"][(c, h)].lookup(a_idx[f] * nc + y0, yt)
                    preds = {
                        "marginal": (np.full(len(f), int(np.argmax(marg))), -np.log(marg[yt])),
                        "persist": (y0, -np.log(ps * (yt == y0) + (1 - ps) * marg[yt])),
                        "cond_act": (np.argmax(p_cact, 1), -np.log(p_cact[np.arange(len(f)), yt])),
                        "cond_act_prev": (np.where(seen2, mode2, y0), M.cond_nll(ckt2, ck2, marg[yt], ALPHA)),
                    }
                    subsets = {"all": np.ones(len(f), bool), "change": yt != y0}
                    for model, (pred, nll) in preds.items():
                        for sname, m in subsets.items():
                            k = (model, "q", c, h, sname, "-")
                            acc.disc(k, pred, yt, m, nll)
                            if c in PER_GAME_FIELDS:
                                pg.disc(k + (gid,), pred, yt, m, nll)
                        if c.startswith("btn_"):
                            bits_true[model] = bits_true.get(model, []) + [yt]
                            bits_pred[model] = bits_pred.get(model, []) + [(pred, nll)]
                # botones conjuntos: exact-match de los 8 bits y NLL = suma de NLL por bit
                for model in bits_true:
                    T = np.stack(bits_true[model], 1)
                    P = np.stack([x[0] for x in bits_pred[model]], 1)
                    nll = np.sum([x[1] for x in bits_pred[model]], 0)
                    code_t = (T * (1 << np.arange(8))).sum(1)
                    code_p = (P * (1 << np.arange(8))).sum(1)
                    T0 = np.stack([qc[f"btn_{b}"][f] for b in C.BUTTON_NAMES], 1)
                    subsets = {"all": np.ones(len(f), bool), "change": (T != T0).any(1)}
                    for sname, m in subsets.items():
                        k = (model, "q", "buttons", h, sname, "-")
                        acc.disc(k, code_p, code_t, m, nll)
                        pg.disc(k + (gid,), code_p, code_t, m, nll)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(C.REPO, "evidence", "E0", "floors"))
    a = ap.parse_args()
    t0 = time.time()
    arrs, games = C.load_cache()
    voc = build_vocab(arrs, games)
    os.makedirs(a.out, exist_ok=True)
    json.dump(voc, open(os.path.join(a.out, "vocab.json"), "w"))
    V = Vocab(voc)
    print(f"vocab: {V.n_act} acciones, {V.n_st} celdas stick, {V.n_cs} C-stick ({time.time()-t0:.0f}s)", flush=True)
    st = fit(arrs, games, V)
    print(f"fit done {time.time()-t0:.0f}s", flush=True)
    acc, pg = M.Acc(), M.Acc()
    evaluate(arrs, games, V, st, acc, pg)
    M.write_rows(os.path.join(a.out, "floors_diagnostics.csv"), acc.rows(kind_of))
    pgr = []
    for k, r in zip(sorted(pg.d, key=lambda k: tuple(map(str, k))), pg.rows(kind_of)):
        r["subset"] = f"{r['subset']}@{k[6]}"
        pgr.append(r)
    M.write_rows(os.path.join(a.out, "floors_per_game.csv"), pgr)
    # estadísticas para el modelo de humo (persistencia de q, para que el humo use el mismo códec)
    side = dict(act_stay={h: st["act_stay"][h][0] / st["act_stay"][h][1] for h in C.H_DYN},
                q_stay={f"{c}|{h}": st["q_stay"][(c, h)][0] / st["q_stay"][(c, h)][1]
                        for c in st["comps"] for h in C.H_Q},
                n_train_games=sum(g["split"] == "train" for g in games),
                n_val_games=sum(g["split"] == "val" for g in games),
                n_val_anchors_per_port=int(sum(len(C.anchors(g["n"])) for g in games if g["split"] == "val")),
                seconds=round(time.time() - t0, 1),
                max_rss_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1))
    json.dump(side, open(os.path.join(a.out, "floors_side.json"), "w"), indent=1)
    print(json.dumps(side)[:400])


if __name__ == "__main__":
    main()
