"""Métricas y suelos triviales (numpy puro). Unidades del juego en continuos; acierto/NLL en discretos.

Todo lo que entra aquí son arrays ya alineados: `pred` para x_{f+h} hecho con información <= f, `true` = x_{f+h}.
"""
from __future__ import annotations

import csv
from collections import defaultdict

import numpy as np

COLS = ["model", "family", "field", "h", "subset", "seed", "n", "mae", "rmse", "within1", "within5", "acc", "nll"]
POS_FIELDS = ("pos_x", "pos_y")
X_SIGNED = ("pos_x", "vel_air_x_self", "vel_x_attack", "vel_ground_x_self")  # se canonicalizan por facing


# ---------- suelos de dinámica (funciones puras, testeadas) ----------
def persistence(x: np.ndarray, f: np.ndarray, h: int) -> np.ndarray:
    """x̂_{f+h} = x_f (h = 0 devuelve el propio valor: error 0)."""
    return x[f]


def const_velocity(pos: np.ndarray, vel: np.ndarray, f: np.ndarray, h: int) -> np.ndarray:
    """pos_{f+h} ≈ pos_f + h·v_f. En Slippi pos_{f+1} - pos_f = v_{f+1} (v de post-frame f+1), así que con
    información <= f se usa v_f (velocidad del último frame observado)."""
    return pos[f] + h * vel[f]


def const_velocity_fd(pos: np.ndarray, f: np.ndarray, h: int) -> np.ndarray:
    """pos_f + h·(pos_f - pos_{f-1}) (diferencia finita; requiere f >= 1)."""
    return pos[f] + h * (pos[f] - pos[f - 1])


def counter_clock(x: np.ndarray, f: np.ndarray, h: int, direction: int) -> np.ndarray:
    """Contador que avanza a ritmo constante: action_frame + h (direction=+1); hitlag/hitstun max(0, x-h)."""
    if direction > 0:
        return x[f] + h
    return np.maximum(0.0, x[f] - h)


def slp_velocity(g: dict, p: int) -> tuple[np.ndarray, np.ndarray]:
    air = np.asarray(g["airborne"][:, p]) == 1
    vx = np.where(air, g["vel_air_x_self"][:, p], g["vel_ground_x_self"][:, p]) + np.asarray(g["vel_x_attack"][:, p])
    vy = np.asarray(g["vel_y_self"][:, p], "f8") + np.asarray(g["vel_y_attack"][:, p])
    return vx.astype("f8"), vy


# ---------- acumulador ----------
class Acc:
    """Suma errores por clave (model, family, field, h, subset, seed[, game]) y emite filas COLS."""

    def __init__(self):
        self.d = defaultdict(lambda: np.zeros(7))  # n, sum|e|, sum e², n<=1, n<=5, correct, nll

    def cont(self, key, pred, true, mask):
        e = np.abs(np.asarray(pred, "f8")[mask] - np.asarray(true, "f8")[mask])
        a = self.d[key]
        a[0] += e.size
        a[1] += e.sum()
        a[2] += (e * e).sum()
        a[3] += (e <= 1).sum()
        a[4] += (e <= 5).sum()

    def disc(self, key, pred, true, mask, nll=None):
        a = self.d[key]
        m = mask
        a[0] += m.sum()
        a[5] += (np.asarray(pred)[m] == np.asarray(true)[m]).sum()
        if nll is not None:
            a[6] += np.asarray(nll, "f8")[m].sum()
        else:
            a[6] = np.nan

    def rows(self, kind_of):
        out = []
        for key, a in sorted(self.d.items(), key=lambda kv: tuple(map(str, kv[0]))):
            model, family, field, h, subset, seed = key[:6]
            n = int(a[0])
            r = dict(model=model, family=family, field=field, h=h, subset=subset, seed=seed, n=n)
            if n == 0:
                out.append(r)
                continue
            if kind_of(field) == "cont":
                r.update(mae=a[1] / n, rmse=np.sqrt(a[2] / n))
                if field in POS_FIELDS:
                    r.update(within1=a[3] / n, within5=a[4] / n)
            else:
                r.update(acc=a[5] / n)
                if np.isfinite(a[6]) and a[6] != 0:
                    r.update(nll=a[6] / n)
            out.append(r)
        return out


def write_rows(path: str, rows: list[dict], append: bool = False):
    mode = "a" if append else "w"
    with open(path, mode, newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        if not append:
            w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items() if k in COLS})


# ---------- NLL de distribuciones categóricas suavizadas ----------
def smoothed_marginal(counts: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    c = counts.astype("f8") + alpha
    return c / c.sum()


def bernoulli_nll(p1: np.ndarray, y: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    p1 = np.clip(p1, eps, 1 - eps)
    return -np.where(y, np.log(p1), np.log1p(-p1))


class SparseCounts:
    """Conteos (clave, objetivo) dispersos; code = key * n_target + target."""

    def __init__(self, n_target: int):
        self.nt = int(n_target)
        self.parts: list[tuple[np.ndarray, np.ndarray]] = []
        self.codes = self.counts = None

    def add(self, key: np.ndarray, target: np.ndarray):
        u, c = np.unique(key.astype(np.int64) * self.nt + target.astype(np.int64), return_counts=True)
        self.parts.append((u, c))
        if len(self.parts) >= 40:
            self._reduce()

    def _reduce(self):
        if not self.parts:
            return
        u = np.concatenate([p[0] for p in self.parts])
        c = np.concatenate([p[1] for p in self.parts])
        uu, inv = np.unique(u, return_inverse=True)
        self.parts = [(uu, np.bincount(inv, weights=c).astype(np.int64))]

    def finalize(self):
        self._reduce()
        self.codes, self.counts = self.parts[0] if self.parts else (np.zeros(0, np.int64), np.zeros(0, np.int64))
        keys = self.codes // self.nt
        self.ukeys, kstart = np.unique(keys, return_index=True)
        self.kcount = np.add.reduceat(self.counts, kstart) if len(keys) else np.zeros(0, np.int64)
        # mayoritaria por clave: el código con más cuenta dentro de cada clave (empate -> objetivo menor)
        order = np.lexsort((-(self.codes % self.nt), self.counts, keys))
        last = np.r_[np.flatnonzero(np.diff(keys[order])), len(order) - 1] if len(keys) else np.zeros(0, int)
        self.kmode = (self.codes[order][last] % self.nt)
        return self

    def lookup(self, key: np.ndarray, target: np.ndarray):
        """-> (c(key,target), c(key), mode(key) o -1, key_seen)."""
        key = key.astype(np.int64)
        code = key * self.nt + target.astype(np.int64)
        i = np.searchsorted(self.codes, code)
        i = np.minimum(i, max(len(self.codes) - 1, 0))
        ckt = np.where((len(self.codes) > 0) & (self.codes[i] == code), self.counts[i], 0) if len(self.codes) else 0
        j = np.minimum(np.searchsorted(self.ukeys, key), max(len(self.ukeys) - 1, 0))
        seen = (self.ukeys[j] == key) if len(self.ukeys) else np.zeros(len(key), bool)
        ck = np.where(seen, self.kcount[j], 0)
        mode = np.where(seen, self.kmode[j], -1)
        return ckt, ck, mode, seen


def cond_nll(ckt, ck, p_marg_t, alpha: float = 1.0) -> np.ndarray:
    """-log((c(k,t) + α·P_marg(t)) / (c(k) + α))."""
    return -np.log((ckt + alpha * p_marg_t) / (ck + alpha))
