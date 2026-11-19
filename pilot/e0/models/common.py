"""Utilidades comunes del paso "suelos + humo" de E0 (solo numpy; válido en el venv y en el python del sistema).

Caché: `$E0_DATA/cache/e0_floors_v1/` con un `.npy` por campo, forma [N, 2] (columna = puerto), filas de todas las
partidas train+val concatenadas, SOLO frames con `frame_id >= 0`. `index.json` da (sha1, split, stage, start, n).

Convención temporal (DESIGN §2-3, verificada en adapter_checks): la fila f = estado post-frame f + mando de f.
El mando de f ya actuó sobre el estado de f. Objetivo de mando sin fuga dado x_{<=f}: mando de f+1.
"""
from __future__ import annotations

import json
import os

import numpy as np

DATA = os.environ.get("E0_DATA", "/srv/mail/melee-research-data")
CACHE = os.path.join(DATA, "cache", "e0_floors_v1")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SPLITS = os.path.join(REPO, "evidence", "E0", "splits.jsonl")
SPLIT_KEY = "split_v1"            # split A6-split-v1 (90/5/5)
ALLOWED_SPLITS = ("train", "val")  # test queda reservado para E1: nunca se lee aquí

CONT = ["pos_x", "pos_y", "vel_air_x_self", "vel_y_self", "vel_x_attack", "vel_y_attack", "vel_ground_x_self",
        "percent", "shield", "action_frame", "hitlag_left", "hitstun_left"]
DISC = ["action", "facing", "airborne", "jumps_left", "stocks", "hurtbox"]
EXTRA = ["hitstun_flag"]
CTRL = ["buttons_phys", "joy_x", "joy_y", "cstick_x", "cstick_y", "trig_l", "trig_r"]
DTYPES = {**{k: "f4" for k in CONT}, "action": "u2", "facing": "i1", "airborne": "u1", "jumps_left": "u1",
          "stocks": "u1", "hurtbox": "u1", "hitstun_flag": "u1", "buttons_phys": "u2", "joy_x": "i1",
          "joy_y": "i1", "cstick_x": "i1", "cstick_y": "i1", "trig_l": "u1", "trig_r": "u1"}
ALL_FIELDS = CONT + DISC + EXTRA + CTRL

# Bits físicos (SPEC Physical Buttons; mismos valores que adapter_checks.py)
BUTTONS = {"A": 0x0100, "B": 0x0200, "X": 0x0400, "Y": 0x0800, "Z": 0x0010, "L": 0x0040, "R": 0x0020,
           "D_UP": 0x0008}
BUTTON_NAMES = list(BUTTONS)

AF_BINS = 256  # action_frame -> int(clip(floor(af), 0, 255))
H_DYN = [1, 4, 7, 8, 13, 16, 32]   # 7 y 13 = D+1 para D ∈ {6, 12} (criterio de acción del rival en G1-q)
H_Q = [1, 7, 13]                   # mando del rival en f+1 y f+D+1
HIST = 8                           # historia del modelo de humo (A4 history_frames_H)
H_MAX = 32


def read_splits(path: str = SPLITS) -> list[dict]:
    rows = [json.loads(line) for line in open(path)]
    return rows


def assert_no_test(games: list[dict]) -> None:
    bad = [g["sha1"] for g in games if g["split"] not in ALLOWED_SPLITS]
    assert not bad, f"partidas fuera de train/val (test reservado para E1): {bad[:3]}"


def load_cache(cache: str = CACHE, fields=None) -> tuple[dict, list[dict]]:
    idx = json.load(open(os.path.join(cache, "index.json")))
    games = idx["games"]
    assert_no_test(games)
    # verificación cruzada contra splits.jsonl: el split de cada partida debe coincidir
    ref = {r["sha1"]: r[SPLIT_KEY] for r in read_splits()}
    for g in games:
        assert ref[g["sha1"]] == g["split"], g["sha1"]
        assert g["split"] != "test"
    arrs = {f: np.load(os.path.join(cache, f + ".npy"), mmap_mode="r") for f in (fields or ALL_FIELDS)}
    return arrs, games


def anchors(n: int, hist: int = HIST, h_max: int = H_MAX) -> np.ndarray:
    """Índices locales f de una partida de n frames con historia completa y f+h_max dentro."""
    return np.arange(hist - 1, n - h_max, dtype=np.int64)


def af_bin(af: np.ndarray) -> np.ndarray:
    return np.clip(np.floor(np.asarray(af, dtype=np.float64)), 0, AF_BINS - 1).astype(np.int64)


def stick_code(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Celda conjunta de la rejilla 1/80 (x, y ∈ -80..80) -> entero 0..161²-1."""
    return (x.astype(np.int64) + 80) * 161 + (y.astype(np.int64) + 80)


def button_bits(bp: np.ndarray) -> np.ndarray:
    """[..] u2 -> [.., 8] bool en el orden BUTTON_NAMES."""
    bp = np.asarray(bp).astype(np.int64)
    return np.stack([(bp & m) != 0 for m in BUTTONS.values()], axis=-1)


def window_any_change(x: np.ndarray, f: np.ndarray, h: int) -> np.ndarray:
    """¿Hay algún x[k] != x[k-1] con k ∈ (f, f+h]? x es 1-D de una partida."""
    ch = np.zeros(len(x), np.int64)
    ch[1:] = (x[1:] != x[:-1])
    c = np.cumsum(ch)
    return (c[f + h] - c[f]) > 0


def window_any_rise(flag: np.ndarray, f: np.ndarray, h: int) -> np.ndarray:
    """¿Hay un flanco de subida de flag en (f, f+h]?"""
    r = np.zeros(len(flag), np.int64)
    r[1:] = (flag[1:].astype(bool) & ~flag[:-1].astype(bool))
    c = np.cumsum(r)
    return (c[f + h] - c[f]) > 0


def event_masks(g: dict, p: int, f: np.ndarray, h: int) -> dict:
    """Subconjuntos de evaluación del jugador p para anclas f y horizonte h (todos con datos reales)."""
    act = np.asarray(g["action"][:, p])
    hs = np.asarray(g["hitstun_flag"][:, p])
    st = np.asarray(g["stocks"][:, p])
    m_act = window_any_change(act, f, h)
    m_hs = window_any_rise(hs, f, h)
    m_st = st[f + h] < st[f]
    ev = m_act | m_hs | m_st
    return {"all": np.ones(len(f), bool), "event": ev, "non_event": ~ev, "ev_action_change": m_act,
            "ev_hitstun_start": m_hs, "ev_stock_loss": m_st}
