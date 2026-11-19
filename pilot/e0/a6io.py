"""Lectura de los .npz del esquema A6."""
from __future__ import annotations

import glob
import json
import os

import numpy as np


def load(path: str) -> tuple[dict, dict]:
    with np.load(path, allow_pickle=False) as z:
        arrs = {k: z[k] for k in z.files if k != "meta_json"}
        meta = json.loads(str(z["meta_json"]))
    return arrs, meta


def iter_games(parsed_dir: str, limit: int = 0):
    files = sorted(glob.glob(os.path.join(parsed_dir, "*.npz")))
    if limit:
        files = files[:limit]
    for f in files:
        yield f, *load(f)
