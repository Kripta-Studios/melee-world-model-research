"""Tarjeta del dataset E0 + gate del 95 %.

Uso: python -I dataset_card.py --index parsed_index.jsonl --parsed-dir DIR --stream-summary S.json \
        --data-root /srv/mail/melee-research-data --out evidence/E0/dataset_card.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import zstandard  # noqa: E402

import a6io  # noqa: E402
import schema_a6 as S  # noqa: E402

GATE_GROUPS = {"velocities": ["vel_air_x_self", "vel_y_self", "vel_x_attack", "vel_y_attack", "vel_ground_x_self"],
               "hitstun": ["hitstun_left"], "action_state_frame": ["action_frame"]}


def stats(v):
    v = np.asarray(v, dtype=np.float64)
    return dict(n=int(v.size), min=float(v.min()), p10=float(np.percentile(v, 10)), median=float(np.median(v)),
                mean=float(v.mean()), p90=float(np.percentile(v, 90)), max=float(v.max()))


def du(path):
    try:
        return int(subprocess.check_output(["du", "-sb", path]).split()[0])
    except Exception:  # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--parsed-dir", required=True)
    ap.add_argument("--stream-summary", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    recs = [json.loads(l) for l in open(a.index)]
    ok = [r for r in recs if r.get("ok")]
    failed = [dict(sha1=r["sha1"], error=r.get("error")) for r in recs if not r.get("ok")]
    n = len(ok)
    frames = np.array([r["n_frames"] for r in ok])
    rows = np.array([r["n_rows_raw"] for r in ok])
    rb = np.array([r["n_frames_with_rollback"] for r in ok])
    playable = np.array([r["last_frame"] + 1 for r in ok])  # frames con frame_id >= 0

    # cobertura por versión
    by_ver = defaultdict(list)
    for r in ok:
        by_ver[r["slippi_version"]].append(r)
    all_fields = list(S.FRAME_FIELDS) + list(S.POST_FIELDS) + list(S.PRE_FIELDS) + ["items"]
    coverage = {}
    for ver, rs in sorted(by_ver.items()):
        coverage[ver] = dict(n_games=len(rs), fields={f: round(np.mean([bool(r["fields_present"].get(f)) for r in rs]), 4)
                                                     for f in all_fields})
    overall = {f: round(float(np.mean([bool(r["fields_present"].get(f)) for r in ok])), 4) for f in all_fields}
    gate = {}
    for gname, fl in GATE_GROUPS.items():
        gate[gname] = float(np.mean([all(r["fields_present"].get(f) for f in fl) for r in ok]))
    all3 = float(np.mean([all(r["fields_present"].get(f) for fl in GATE_GROUPS.values() for f in fl) for r in ok]))
    # verificación de que los campos "presentes" no son constantes vacías
    nonzero = Counter()
    zc = zstandard.ZstdCompressor(level=3)
    zstd_bytes = 0
    zstd19_sample = []
    for i, (_f, arrs, meta) in enumerate(a6io.iter_games(a.parsed_dir)):
        for k in ("vel_air_x_self", "vel_x_attack", "hitstun_left", "action_frame", "hitlag_left"):
            if k in arrs and np.any(arrs[k] != 0):
                nonzero[k] += 1
        blob = b"".join(np.ascontiguousarray(arrs[k]).tobytes() for k in sorted(arrs))
        zstd_bytes += len(zc.compress(blob))
        if i < 20:
            zstd19_sample.append((len(zstandard.ZstdCompressor(level=19).compress(blob)), meta["n_frames"]))
    npz_bytes = sum(r["npz_bytes"] for r in ok)
    raw_bytes = sum(r["raw_array_bytes"] for r in ok)
    slp_bytes = sum(r["slp_bytes"] for r in ok)
    tf = int(frames.sum())
    stream = json.load(open(a.stream_summary))
    card = {
        "schema": "A6 (E0)", "parser": ok[0]["parser"] if ok else None,
        "source": {"dataset": "erickfm/melee-ranked-replays", "revision": stream["revision"],
                   "tarballs": stream["tarballs"], "bytes_streamed_total": stream["bytes_streamed_total"],
                   "stop_reason": stream["stop_reason"], "stream_reason_counts": stream["reason_counts"]},
        "filter": "2 jugadores humanos, ambos Fox (ID externo 2), sin teams, sin Nana, GameEnd TIME!/GAME!, "
                  "last_frame >= 1500, frames contiguos desde -123, sha1 único",
        "n_games": n, "n_parse_failures": len(failed), "parse_failures": failed[:20],
        "frames": {"total_unique": tf, "total_playable_frame_id_ge_0": int(playable.sum()),
                   "total_raw_rows_with_rollback_copies": int(rows.sum()),
                   "per_game_unique": stats(frames)},
        "duration_seconds_playable": stats(playable / 60.0),
        "rollback": {"frames_with_duplicates_total": int(rb.sum()), "frac_frames_with_duplicates": float(rb.sum() / tf),
                     "per_game_frac": stats(rb / frames), "extra_rows_frac": float((rows.sum() - tf) / tf),
                     "max_copies_seen": int(max(r["max_copies"] for r in ok)),
                     "games_with_any_rollback": int((rb > 0).sum())},
        "slippi_versions": dict(Counter(r["slippi_version"] for r in ok)),
        "stages": dict(Counter(str(r["stage"]) for r in ok)),
        "end_methods": dict(Counter(str(r["end_method"]) for r in ok)),
        "major_scene": dict(Counter(str(r["major_scene"]) for r in ok)),
        "crosscheck_peppi_vs_slpraw_all_ok": all(all(r["crosscheck"].values()) for r in ok),
        "coverage_overall": overall, "coverage_by_version": coverage,
        "nonconstant_field_games": dict(nonzero),
        "bytes": {
            "slp_total": slp_bytes, "slp_per_frame": slp_bytes / tf,
            "npz_total": npz_bytes, "npz_per_frame_measured": npz_bytes / tf,
            "uncompressed_arrays_total": raw_bytes, "uncompressed_per_frame": raw_bytes / tf,
            "zstd3_total": zstd_bytes, "zstd3_per_frame": zstd_bytes / tf,
            "zstd19_per_frame_first20": sum(b for b, _ in zstd19_sample) / max(1, sum(f for _, f in zstd19_sample)),
            "note": "por frame = ambos puertos + cabecera de frame + ítems (ragged); el npz incluye meta_json",
        },
        "disk_usage_bytes": {k: du(os.path.join(a.data_root, k)) for k in ("slp", "parsed", "venv-e0")},
        "disk_usage_total_bytes": du(a.data_root),
        "gate_95": {"threshold": 0.95, "frac_games_with": gate, "frac_games_with_all_three": all3,
                    "passed": all3 >= 0.95},
        "fields": S.all_fields(),
    }
    with open(a.out, "w") as f:
        json.dump(card, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: card[k] for k in ("n_games", "frames", "rollback", "slippi_versions", "bytes", "gate_95",
                                           "disk_usage_total_bytes", "crosscheck_peppi_vs_slpraw_all_ok")}, indent=1))


if __name__ == "__main__":
    main()
