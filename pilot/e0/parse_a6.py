"""Parser .slp -> esquema A6 (un .npz comprimido por partida).

- peppi-py 0.8.6 (Arrow) es el parser principal. Esta versión NO deduplica rollback: devuelve todas las copias
  de cada frame en orden de llegada (comprobado: ids no monótonos). Aquí se aplica la regla de A6: ÚLTIMA copia.
- slpraw (lector propio) aporta el C-stick crudo (Pre 0x41/0x42, 3.17.0+) y una verificación cruzada byte a byte
  de varios campos tras la deduplicación.

Uso: python -I parse_a6.py --slp-dir DIR --out-dir DIR --index OUT.jsonl
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
from peppi_py._peppi import read_slippi  # noqa: E402

import schema_a6 as S  # noqa: E402
import slpraw  # noqa: E402

PARSER_ID = "peppi-py==0.8.6 + slpraw(E0); rollback=LAST"


def _get(arr, path):
    for p in path:
        try:
            arr = arr.field(p)
        except KeyError:
            return None
    return arr


def _np(arr, dtype):
    return np.asarray(arr.to_numpy(zero_copy_only=False)).astype(dtype, copy=False)


def parse_game(path: str) -> tuple[dict, dict]:
    data = open(path, "rb").read()
    g = read_slippi(path, False)
    fr = g.frames
    ids = _np(fr.field("id"), "i4")
    uniq, last, counts = slpraw.last_copy_index(ids)
    T = len(uniq)
    out: dict[str, np.ndarray] = {"frame_id": uniq.astype("i4"), "n_copies": counts.astype("u1")}
    present = {"frame_id": True, "n_copies": True}

    for name, (path_, dt, *_r) in S.FRAME_FIELDS.items():
        if path_ is None or name == "frame_id":
            continue
        a = _get(fr, path_)
        present[name] = a is not None
        if a is not None:
            out[name] = _np(a, dt)[last]

    ports_arrow = fr.field("ports")
    port_names = [f.name for f in ports_arrow.type]
    if len(port_names) != 2:
        raise ValueError(f"expected 2 ports, got {port_names}")
    leaders = [ports_arrow.field(p).field("leader") for p in port_names]
    for name, (path_, dt, *_r) in {**S.POST_FIELDS, **S.PRE_FIELDS}.items():
        if path_ is None:
            continue
        cols = [_get(ld, path_) for ld in leaders]
        present[name] = all(c is not None for c in cols)
        if present[name]:
            out[name] = np.stack([_np(c, dt)[last] for c in cols], axis=1)
    if present.get("misc_as") and present.get("flags4"):
        hs = (out["flags4"] & 0x02) != 0
        out["hitstun_left"] = np.where(hs, out["misc_as"], 0).astype("f4")
        present["hitstun_left"] = True
    else:
        present["hitstun_left"] = False

    # ---- slpraw: C-stick crudo + verificación cruzada ----
    ev = slpraw.index_events(data)
    h = ev.header
    pre_off, post_off = ev.offsets[slpraw.CMD_PRE], ev.offsets[slpraw.CMD_POST]
    port_idx = [int(p[1]) - 1 for p in port_names]  # 'P1' -> 0
    xcheck = {}

    def raw_last(offs, port):
        f, p, _ = slpraw.frame_port_keys(data, offs)
        sel = offs[p == port]
        u, l, _c = slpraw.last_copy_index(f[p == port])
        return u, sel[l]

    pre_last, post_last = [], []
    for k, p in enumerate(port_idx):
        u1, o1 = raw_last(pre_off, p)
        u2, o2 = raw_last(post_off, p)
        if not (np.array_equal(u1, uniq) and np.array_equal(u2, uniq)):
            raise ValueError("frame set mismatch peppi vs slpraw")
        pre_last.append(o1)
        post_last.append(o2)
    has_c = slpraw.field_present(h, slpraw.CMD_PRE, 0x42, 1)
    present["raw_cx"] = present["raw_cy"] = has_c
    if has_c:
        out["raw_cx"] = np.stack([slpraw.gather(data, o, 0x41, "i1") for o in pre_last], 1)
        out["raw_cy"] = np.stack([slpraw.gather(data, o, 0x42, "i1") for o in pre_last], 1)
    checks = [("action", post_last, 0x8, "u2"), ("pos_x", post_last, 0xA, "f4"),
              ("percent", post_last, 0x16, "f4"), ("joy_x", pre_last, 0x19, "f4"),
              ("buttons_phys", pre_last, 0x31, "u2"), ("trig_l_phys", pre_last, 0x33, "f4")]
    if present.get("hitlag_left"):
        checks.append(("hitlag_left", post_last, 0x49, "f4"))
    for name, offs, o, dt in checks:
        raw = np.stack([slpraw.gather(data, x, o, dt) for x in offs], 1)
        xcheck[name] = bool(np.array_equal(raw.view("u1"), np.ascontiguousarray(out[name]).view("u1")))
    # semilla por frame: FrameStart (LAST) debe coincidir con la de peppi
    if present.get("rng_seed"):
        fs = ev.offsets[slpraw.CMD_FRAME_START]
        u3, l3, _ = slpraw.last_copy_index(slpraw.gather(data, fs, 0x1, "i4"))
        xcheck["rng_seed"] = bool(np.array_equal(slpraw.gather(data, fs[l3], 0x5, "u4"), out["rng_seed"]))

    # ---- ítems (solo filas LAST) ----
    items = fr.field("item")
    present["items"] = items is not None
    if items is not None:
        offs = np.asarray(items.offsets)
        rows = np.repeat(np.arange(len(ids)), np.diff(offs))
        keep_row = np.full(len(ids), -1, dtype=np.int64)
        keep_row[last] = np.arange(T)
        mask = keep_row[rows] >= 0
        flat = items.values
        out["item_row"] = keep_row[rows][mask].astype("i4")
        for name, (path_, dt, *_r) in S.ITEM_FIELDS.items():
            if path_ is None:
                continue
            a = _get(flat, path_)
            present[name] = a is not None
            if a is not None:
                out[name] = _np(a, dt)[offs[0]:offs[-1]][mask]

    start = g.start
    end = g.end or {}
    meta = {
        "sha1": os.path.basename(path)[:-4], "slp_bytes": len(data), "slippi_version": ".".join(map(str, h.version)),
        "stage": h.stage, "ports": port_idx, "start_seed": h.random_seed, "major_scene": h.major_scene,
        "n_rows_raw": int(len(ids)), "n_frames": int(T), "n_frames_with_rollback": int((counts > 1).sum()),
        "max_copies": int(counts.max()), "first_frame": int(uniq[0]), "last_frame": int(uniq[-1]),
        "contiguous": bool(T == uniq[-1] - uniq[0] + 1),
        "end_method": end.get("method") if isinstance(end, dict) else None,
        "placements": end.get("players") if isinstance(end, dict) else None,
        "timer_s": start.get("timer"), "is_frozen_ps": start.get("is_frozen_ps"),
        "ucf": [p.get("ucf") for p in start.get("players", [])],
        "fields_present": present, "crosscheck": xcheck, "parser": PARSER_ID,
    }
    return out, meta


def _one(args):
    f, out_dir = args
    rec = {"sha1": os.path.basename(f)[:-4]}
    try:
        arrs, meta = parse_game(f)
        dst = os.path.join(out_dir, meta["sha1"] + ".npz")
        np.savez_compressed(dst + ".tmp.npz", meta_json=np.array(json.dumps(meta)), **arrs)
        os.replace(dst + ".tmp.npz", dst)
        meta["npz_bytes"] = os.path.getsize(dst)
        meta["raw_array_bytes"] = int(sum(v.nbytes for v in arrs.values()))
        rec.update(meta, ok=True)
    except Exception as e:  # noqa: BLE001
        rec.update(ok=False, error=f"{type(e).__name__}: {e}"[:300])
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slp-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1, help="procesos; el índice sale en el mismo orden (sha1) que con 1")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(a.slp_dir, "*.slp")))
    if a.limit:
        files = files[: a.limit]
    t0 = time.time()
    jobs = [(f, a.out_dir) for f in files]
    if a.workers > 1:
        import multiprocessing as mp
        pool = mp.get_context("spawn").Pool(a.workers)
        it = pool.imap(_one, jobs, chunksize=4)
    else:
        pool, it = None, map(_one, jobs)
    with open(a.index, "w") as idx:
        for i, rec in enumerate(it):
            idx.write(json.dumps(rec) + "\n")
            if (i + 1) % 25 == 0:
                idx.flush()
                print(f"[{time.time()-t0:6.0f}s] {i+1}/{len(files)}", flush=True)
    if pool:
        pool.close(); pool.join()
    print(f"done {len(files)} in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
