"""Deduplicación y split por PARTIDA (split_plan.json de A6, umbrales E1 de EXPERIMENT_PLAN §5.3).

- Duplicado exacto: mismo sha1 del .slp (ya colapsado en stream_filter; se vuelve a comprobar aquí).
- Casi-duplicado: misma semilla inicial (GameStart 0x13D) + mismo hash de las primeras N filas post-cuenta
  atrás (frame_id 0..N-1) de ambos puertos (pos, acción, sticks, botones).
- bucket = int(sha256('A6-split-v1|' + sha1)[:8], 16) / 2^32. Se escriben dos asignaciones:
    split_v1    : train < 0.90, val < 0.95, test resto   (A6-split-v1)
    split_v1_E1 : train < 0.606, val < 0.697, test resto (A6-split-v1-E1, PROP-int del plan)
  En cada grupo de casi-duplicados se conserva el sha1 menor; el resto se marca excluded.

Uso: python -I splits.py --parsed-dir DIR --out evidence/E0/splits.jsonl [--n-rows 600]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import a6io  # noqa: E402

HASH_FIELDS = ("pos_x", "pos_y", "action", "joy_x", "joy_y", "buttons_phys")


def bucket(sha1: str) -> float:
    return int(hashlib.sha256(("A6-split-v1|" + sha1).encode()).hexdigest()[:8], 16) / 2**32


def assign(b: float, train: float, val: float) -> str:
    return "train" if b < train else ("val" if b < val else "test")


def prefix_hash(arrs: dict, n_rows: int) -> str | None:
    sel = (arrs["frame_id"] >= 0) & (arrs["frame_id"] < n_rows)
    if sel.sum() < n_rows:
        return None
    h = hashlib.sha256()
    for k in HASH_FIELDS:
        h.update(np.ascontiguousarray(arrs[k][sel]).tobytes())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-rows", type=int, default=600)
    a = ap.parse_args()
    recs = []
    for _f, arrs, meta in a6io.iter_games(a.parsed_dir):
        recs.append(dict(sha1=meta["sha1"], start_seed=meta["start_seed"], n_frames=meta["n_frames"],
                         slippi_version=meta["slippi_version"], stage=meta["stage"],
                         prefix_hash=prefix_hash(arrs, a.n_rows)))
    sha_count = Counter(r["sha1"] for r in recs)
    groups = defaultdict(list)
    for r in recs:
        groups[(r["start_seed"], r["prefix_hash"])].append(r["sha1"])
    out_counts = Counter()
    with open(a.out, "w") as f:
        for r in sorted(recs, key=lambda r: r["sha1"]):
            g = sorted(groups[(r["start_seed"], r["prefix_hash"])])
            dup_exact = sha_count[r["sha1"]] > 1
            near = len(g) > 1
            excluded = (near and r["sha1"] != g[0]) or r["prefix_hash"] is None
            b = bucket(r["sha1"])
            row = dict(sha1=r["sha1"], bucket=round(b, 8), split_v1=assign(b, 0.90, 0.95),
                       split_v1_E1=assign(b, 0.606, 0.697), exact_dup=dup_exact, near_dup_group=g if near else None,
                       excluded=excluded, exclude_reason=("near_dup" if near and r["sha1"] != g[0] else
                                                          ("short_prefix" if r["prefix_hash"] is None else None)),
                       start_seed=r["start_seed"], prefix_hash_n_rows=a.n_rows, prefix_hash=r["prefix_hash"],
                       n_frames=r["n_frames"], slippi_version=r["slippi_version"], stage=r["stage"])
            f.write(json.dumps(row) + "\n")
            if not excluded:
                out_counts["v1:" + row["split_v1"]] += 1
                out_counts["E1:" + row["split_v1_E1"]] += 1
            out_counts["excluded"] += int(excluded)
    seeds = Counter(r["start_seed"] for r in recs)
    print(json.dumps(dict(n_games=len(recs), exact_dup_sha1=sum(v > 1 for v in sha_count.values()),
                          near_dup_groups=sum(len(v) > 1 for v in groups.values()),
                          games_sharing_start_seed=sum(v for v in seeds.values() if v > 1),
                          counts=dict(out_counts))))


if __name__ == "__main__":
    main()
