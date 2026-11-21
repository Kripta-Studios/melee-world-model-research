"""Exporta train+val (split A6-split-v1) de los .npz a memmaps .npy compactos para suelos y humo.

Solo frames con frame_id >= 0 (la cuenta atrás no es accionable). test NUNCA se lee (assert).
Uso (venv E0): nice -n 19 $P -I pilot/e0/models/export_cache.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
import portable as _P  # noqa: E402  (Linux/Windows)
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import common as C  # noqa: E402


def convert(z) -> dict:
    keep = z["frame_id"] >= 0
    out = {}
    for k in C.CONT:
        out[k] = z[k][keep].astype("f4")
    out["action"] = z["action"][keep].astype("u2")
    out["facing"] = np.sign(z["facing"][keep]).astype("i1")
    for k in ("airborne", "jumps_left", "stocks"):
        out[k] = z[k][keep].astype("u1")
    out["hurtbox"] = z["hurtbox"][keep].astype("u1")
    out["hitstun_flag"] = ((z["flags4"][keep] & 0x02) != 0).astype("u1")
    out["buttons_phys"] = z["buttons_phys"][keep].astype("u2")
    for src, dst, scale in (("joy_x", "joy_x", 80), ("joy_y", "joy_y", 80), ("cstick_x", "cstick_x", 80),
                            ("cstick_y", "cstick_y", 80), ("trig_l_phys", "trig_l", 140),
                            ("trig_r_phys", "trig_r", 140)):
        v = z[src][keep].astype("f8") * scale
        r = np.round(v)
        assert np.max(np.abs(v - r)) < 1e-3, f"{src} fuera de la rejilla 1/{scale}"
        out[dst] = r.astype(C.DTYPES[dst])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", default=os.path.join(C.DATA, "parsed"))
    ap.add_argument("--out", default=C.CACHE)
    a = ap.parse_args()
    t0 = time.time()
    rows = [r for r in C.read_splits() if not r["excluded"]]
    sel = [r for r in rows if r[C.SPLIT_KEY] in C.ALLOWED_SPLITS]
    n_test = sum(r[C.SPLIT_KEY] == "test" for r in rows)
    games = []
    for r in sel:
        with np.load(os.path.join(a.parsed_dir, r["sha1"] + ".npz")) as z:
            n = int((z["frame_id"] >= 0).sum())
        games.append(dict(sha1=r["sha1"], split=r[C.SPLIT_KEY], stage=int(r["stage"]), n=n))
    C.assert_no_test(games)
    N = sum(g["n"] for g in games)
    os.makedirs(a.out, exist_ok=True)
    mm = {k: np.lib.format.open_memmap(os.path.join(a.out, k + ".npy"), mode="w+", dtype=C.DTYPES[k],
                                        shape=(N, 2)) for k in C.ALL_FIELDS}
    s = 0
    for i, g in enumerate(games):
        with np.load(os.path.join(a.parsed_dir, g["sha1"] + ".npz")) as z:
            assert json.loads(str(z["meta_json"]))["sha1"] == g["sha1"]
            o = convert(z)
        assert len(o["pos_x"]) == g["n"]
        for k in C.ALL_FIELDS:
            mm[k][s:s + g["n"]] = o[k]
        g["start"] = s
        s += g["n"]
        if (i + 1) % 50 == 0:
            print(f"[{time.time()-t0:5.0f}s] {i+1}/{len(games)}", flush=True)
    for v in mm.values():
        v.flush()
    info = dict(games=games, n_rows=N, split_key=C.SPLIT_KEY, n_test_games_skipped=n_test,
                fields={k: C.DTYPES[k] for k in C.ALL_FIELDS},
                note="frame_id>=0; sticks/gatillos como enteros de la rejilla 1/80 y 1/140; facing=sign")
    json.dump(info, open(os.path.join(a.out, "index.json"), "w"))
    rss = _P.peak_rss_mb()
    print(json.dumps(dict(n_games=len(games), n_train=sum(g['split'] == 'train' for g in games),
                          n_val=sum(g['split'] == 'val' for g in games), n_rows=N, test_skipped=n_test,
                          seconds=round(time.time() - t0, 1), max_rss_mb=round(rss, 1))))


if __name__ == "__main__":
    main()
