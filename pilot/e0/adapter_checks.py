"""Comprobaciones empíricas del adaptador A6 sobre los .npz parseados.

1. Alineación: con qué desfase k el flanco de un botón en PreFrame(f) se refleja en el action_state de
   PostFrame(f+k). Convención A6 => k = 0 (el mando de la fila f ya actuó sobre el estado de la fila f).
2. Fuga: si el objetivo de imitación fuera el mando de la MISMA fila, el estado de esa fila lo delata.
   Se mide P(flanco en f | x_f muestra el inicio de la acción) frente a P(flanco en f+1 | mismo x_f).
3. Coherencia pre/post: pre_action(f) == action(f-1) y pre_pos(f) == pos(f-1) (el pre-frame es "antes").
4. Rangos y cuantización de sticks/gatillos, bits de botones definidos, pulsado vs mantenido.
5. Ningún campo del futuro / privilegiado en la lista de observación.

Uso: python -I adapter_checks.py --parsed-dir DIR --out evidence/E0/adapter_checks.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import a6io  # noqa: E402
import schema_a6 as S  # noqa: E402

# IDs de action state comunes (SPEC "Melee IDs" / tablas estándar de Melee)
KNEEBEND = 24          # jumpsquat
ATTACK11 = 44          # jab 1
GROUND_ACTIONABLE = {14, 15, 16, 17, 18, 20, 21, 39, 40, 41}  # Wait, Walk*, Turn, Dash, Run, Squat*
BTN_A, BTN_B, BTN_X, BTN_Y, BTN_Z = 0x0100, 0x0200, 0x0400, 0x0800, 0x0010
BTN_L, BTN_R = 0x0040, 0x0020
DEFINED_PHYS_BITS = 0x1F7F  # bits documentados en SPEC Physical Buttons


def edges(held: np.ndarray) -> np.ndarray:
    """Flanco de subida: e[f] = held[f] & ~held[f-1]; e[0] = held[0]."""
    e = held.copy()
    e[1:] = held[1:] & ~held[:-1]
    return e


def lag_histogram(press: np.ndarray, action: np.ndarray, prev_ok: np.ndarray, target: int,
                  kmin=-3, kmax=6) -> Counter:
    """Para cada f con flanco y estado previo accionable, k = primer desfase en [kmin,kmax] con
    action[f+k]==target y action[f+k-1]!=target. 'none' si no aparece."""
    T = len(action)
    start = np.zeros(T, bool)
    start[1:] = (action[1:] == target) & (action[:-1] != target)
    hist = Counter()
    for f in np.flatnonzero(press & prev_ok):
        if f + kmin < 1 or f + kmax >= T:
            continue
        ks = [k for k in range(kmin, kmax + 1) if start[f + k]]
        hist[ks[0] if ks else "none"] += 1
    return hist


def alignment_game(a: dict) -> dict:
    res = {"jump": Counter(), "jab": Counter(), "leak": Counter(), "prepost": Counter(),
           "jump_none_post_f": Counter(), "prepost_mismatch_pairs": Counter()}
    fid = a["frame_id"]
    act_ok = fid >= 0
    for p in range(2):
        act = a["action"][:, p].astype(np.int64)
        bp = a["buttons_phys"][:, p].astype(np.int64)
        prev = np.zeros(len(act), bool)
        prev[1:] = np.isin(act[:-1], list(GROUND_ACTIONABLE))
        jump_held = (bp & (BTN_X | BTN_Y)) != 0
        jpress = edges(jump_held) & act_ok
        res["jump"].update(lag_histogram(jpress, act, prev, KNEEBEND))
        # diagnóstico: qué acción aparece en post(f) cuando no hay KneeBend
        st = np.zeros(len(act), bool)
        st[1:] = (act[1:] == KNEEBEND) & (act[:-1] != KNEEBEND)
        for f in np.flatnonzero(jpress & prev):
            if 4 <= f < len(act) - 7 and not st[f - 3:f + 7].any():
                res["jump_none_post_f"][f"{act[f-1]}->{act[f]}"] += 1
        # jab: A desde Wait con stick casi neutro y sin otros botones
        a_press = edges((bp & BTN_A) != 0) & act_ok
        neutral = (np.abs(a["joy_x"][:, p]) < 0.2) & (np.abs(a["joy_y"][:, p]) < 0.2)
        prev_wait = np.zeros(len(act), bool)
        prev_wait[1:] = act[:-1] == 14
        res["jab"].update(lag_histogram(a_press & neutral, act, prev_wait, ATTACK11))
        # fuga: x_f muestra "acaba de empezar KneeBend desde estado accionable"
        start = np.zeros(len(act), bool)
        start[1:] = (act[1:] == KNEEBEND) & (act[:-1] != KNEEBEND)
        cond = start & prev & act_ok
        cond[-1] = False
        jp_any = edges(jump_held)
        res["leak"]["n_cond"] += int(cond.sum())
        res["leak"]["press_same_row"] += int((cond & jp_any).sum())
        nxt = np.zeros_like(cond)
        nxt[:-1] = jp_any[1:]
        res["leak"]["press_next_row"] += int((cond & nxt).sum())
        # base rates
        res["leak"]["n_rows"] += int(act_ok.sum())
        res["leak"]["press_rows"] += int((jp_any & act_ok).sum())
        # pre/post coherencia
        mm = np.flatnonzero(a["pre_action"][1:, p] != a["action"][:-1, p])
        res["prepost_mismatch_pairs"].update(f"post(f-1)={a['action'][i, p]}->pre(f)={a['pre_action'][i+1, p]}" for i in mm)
        res["prepost"]["n"] += len(act) - 1
        res["prepost"]["pre_action_eq_prev_post"] += int((a["pre_action"][1:, p] == a["action"][:-1, p]).sum())
        res["prepost"]["pre_pos_eq_prev_post"] += int(((a["pre_pos_x"][1:, p] == a["pos_x"][:-1, p]) &
                                                      (a["pre_pos_y"][1:, p] == a["pos_y"][:-1, p])).sum())
        res["prepost"]["pre_pos_eq_same_post"] += int(((a["pre_pos_x"][:, p] == a["pos_x"][:, p]) &
                                                      (a["pre_pos_y"][:, p] == a["pos_y"][:, p])).sum())
        res["prepost"]["pre_percent_eq_prev_post"] += int((a["pre_percent"][1:, p] == a["percent"][:-1, p]).sum())
    return res


def on_grid(x: np.ndarray, n: int) -> float:
    y = x.astype(np.float64) * n
    return float(np.mean(np.abs(y - np.round(y)) < 1e-4))


def ranges_game(a: dict) -> dict:
    out = {}
    for k in ("joy_x", "joy_y", "cstick_x", "cstick_y"):
        v = a[k]
        out[k] = dict(min=float(v.min()), max=float(v.max()), in_range=float(np.mean(np.abs(v) <= 1.0)),
                      grid80=on_grid(v, 80), n_distinct=int(len(np.unique(v))))
    for k in ("trigger", "trig_l_phys", "trig_r_phys"):
        v = a[k]
        out[k] = dict(min=float(v.min()), max=float(v.max()), in_range=float(np.mean((v >= 0) & (v <= 1))),
                      grid140=on_grid(v, 140), frac_zero=float(np.mean(v == 0)), n_distinct=int(len(np.unique(v))))
    for k in ("raw_x", "raw_y", "raw_cx", "raw_cy"):
        if k in a:
            v = a[k].astype(np.int64)
            out[k] = dict(min=int(v.min()), max=int(v.max()), n_distinct=int(len(np.unique(v))))
    # relación raw_x -> joy_x (cuantización UCF): ¿joy_x*80 == clamp(raw_x)?
    if "raw_x" in a:
        jx = np.round(a["joy_x"].astype(np.float64) * 80).astype(np.int64)
        rx = a["raw_x"].astype(np.int64)
        out["joy_x80_eq_raw_x"] = float(np.mean(jx == rx))
        out["joy_x80_eq_clip_raw_x"] = float(np.mean(jx == np.clip(rx, -80, 80)))
    bp = a["buttons_phys"].astype(np.int64)
    out["undefined_phys_bits_frac"] = float(np.mean((bp & ~DEFINED_PHYS_BITS) != 0))
    # botones procesados: la mitad baja coincide con los físicos?
    out["proc_low16_eq_phys"] = float(np.mean((a["buttons"].astype(np.int64) & 0xFFFF) == bp))
    hp = {}
    for name, m in (("A", BTN_A), ("B", BTN_B), ("X", BTN_X), ("Y", BTN_Y), ("Z", BTN_Z), ("L", BTN_L), ("R", BTN_R)):
        held = (bp & m) != 0
        e = np.zeros_like(held)
        e[1:] = held[1:] & ~held[:-1]
        hp[name] = dict(held_frames=int(held.sum()), press_edges=int(e.sum()))
    out["held_vs_pressed"] = hp
    return out


def static_observation_check() -> dict:
    fields = S.all_fields()
    obs = sorted(k for k, v in fields.items() if v["level"] == "observation")
    bad = sorted(set(obs) & S.NEVER_IN_OBSERVATION)
    pre_in_obs = sorted(k for k in obs if fields[k]["group"] == "pre")
    return dict(observation_fields=obs, forbidden_in_obs=bad, pre_frame_fields_in_obs=pre_in_obs,
                control_fields=sorted(k for k, v in fields.items() if v["level"] == "control"),
                passed=not bad and not pre_in_obs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    tot = {"jump": Counter(), "jab": Counter(), "leak": Counter(), "prepost": Counter(),
           "jump_none_post_f": Counter(), "prepost_mismatch_pairs": Counter()}
    rng_agg: dict = {}
    n_games = 0
    rollback_rows = Counter()
    for _f, arrs, meta in a6io.iter_games(a.parsed_dir, a.limit):
        n_games += 1
        r = alignment_game(arrs)
        for k in tot:
            tot[k].update(r[k])
        g = ranges_game(arrs)
        for k, v in g.items():
            rng_agg.setdefault(k, []).append(v)
        rollback_rows["frames"] += meta["n_frames"]
        rollback_rows["raw_rows"] += meta["n_rows_raw"]
        rollback_rows["frames_with_dup"] += meta["n_frames_with_rollback"]

    def summarize(lst):
        if isinstance(lst[0], dict):
            keys = lst[0].keys()
            out = {}
            for k in keys:
                vals = [x[k] for x in lst if k in x]
                if isinstance(vals[0], dict):
                    out[k] = summarize(vals)
                elif k == "min":
                    out[k] = min(vals)
                elif k == "max":
                    out[k] = max(vals)
                elif k in ("held_frames", "press_edges"):
                    out[k] = int(sum(vals))
                else:
                    out[k + "_mean_over_games"] = float(np.mean(vals))
                    out[k + "_min_over_games"] = float(np.min(vals))
            return out
        return dict(mean_over_games=float(np.mean(lst)), min_over_games=float(np.min(lst)))

    def kdist(c):
        n = sum(c.values())
        return dict(n=n, counts={str(k): v for k, v in sorted(c.items(), key=lambda kv: str(kv[0]))},
                    frac_k0=(c.get(0, 0) / n if n else None))

    lk = tot["leak"]
    pp = tot["prepost"]
    rows = [
        dict(check="alignment_jump_press_to_kneebend", n_games=n_games,
             description="flanco X|Y en PreFrame(f) desde estado de suelo accionable en post(f-1); k = desfase hasta el inicio de KneeBend(24) en post(f+k)",
             expected="k=0 (fila f = post(f) + mando de f, que ya actuó)", result=kdist(tot["jump"]),
             diag_none_top_transitions_post_fm1_to_f=dict(tot["jump_none_post_f"].most_common(10)),
             passed=kdist(tot["jump"])["frac_k0"] is not None and kdist(tot["jump"])["frac_k0"] > 0.95),
        dict(check="alignment_A_press_to_jab", n_games=n_games,
             description="flanco A con stick neutro desde Wait(14) en post(f-1); k hasta inicio de Attack11(44)",
             expected="k=0", result=kdist(tot["jab"]),
             passed=kdist(tot["jab"])["frac_k0"] is not None and kdist(tot["jab"])["frac_k0"] > 0.90),
        dict(check="leak_same_row_vs_next_row", n_games=n_games,
             description="condición: x_f muestra inicio de KneeBend desde estado accionable. P(flanco de salto en el mando de la misma fila f) vs P(flanco en f+1). Tasa base de flanco por fila incluida.",
             result=dict(n_cond=lk["n_cond"],
                         p_press_same_row=lk["press_same_row"] / max(lk["n_cond"], 1),
                         p_press_next_row=lk["press_next_row"] / max(lk["n_cond"], 1),
                         base_rate_press_per_row=lk["press_rows"] / max(lk["n_rows"], 1)),
             conclusion="si p_same_row >> base y p_next_row ~ base, usar el mando de f como objetivo dado x_f es fuga; el objetivo sin fuga es el mando de f+1",
             passed=lk["press_same_row"] / max(lk["n_cond"], 1) > 0.5),
        dict(check="pre_post_coherence", n_games=n_games,
             result={k: (v / pp["n"] if k != "n" else v) for k, v in pp.items()},
             diag_top_mismatch_pairs=dict(tot["prepost_mismatch_pairs"].most_common(12)),
             description="fracción de filas con pre_X(f) == post_X(f-1) (pre-frame = antes de procesar f) y pre_pos(f) == post_pos(f) (debería ser baja salvo estados quietos)"),
        dict(check="rollback_dedup_LAST", n_games=n_games, result=dict(rollback_rows),
             description="filas brutas del flujo de peppi vs frames únicos tras quedarse con la ÚLTIMA copia"),
        dict(check="ranges_quantization_buttons", n_games=n_games, result=summarize_ranges(rng_agg, summarize)),
        dict(check="no_future_or_privileged_fields_in_observation", **static_observation_check(),
             note="Además: parse_a6 verifica por partida que post/pre de la fila f son los eventos con frame_id=f (crosscheck byte a byte con slpraw)."),
    ]
    with open(a.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    for r in rows:
        print(json.dumps({k: r[k] for k in r if k in ("check", "passed", "result")}, ensure_ascii=False)[:600])


def summarize_ranges(agg, summarize):
    return {k: summarize(v) for k, v in agg.items()}


if __name__ == "__main__":
    main()
