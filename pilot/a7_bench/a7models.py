"""A7 benchmark models: small encoder + one-step predictor over structured Melee-like state.

Not a proposed architecture: a cost proxy. Shapes (parametrised, A7 assumptions):
  S = per-frame structured state floats for 2 players (default 192, range 100-300)
  A = per-frame joint action floats (2 players x (8 buttons + 4 stick + 2 trigger) = 28 -> 32)
  D = latent size (192, as LeWM; arXiv 2603.19312v3)
Encoder: history of H frames of [state, action] -> z (D).
Predictor: one step z_t (+ window / recurrent state) and action a_t -> z_{t+1}.
Three families: mlp, gru, tx (pre-norm transformer; predictor = AR over a sliding window
of W latents, LeWM-like, action added to tokens instead of AdaLN-zero).
"""
import math
import torch
from torch import nn

S_DEFAULT, A_DEFAULT, D_DEFAULT = 192, 32, 192


def nparams(m):
    return sum(p.numel() for p in m.parameters())


class MLPEnc(nn.Module):
    def __init__(self, S, A, D, H, w, fe=64):
        super().__init__()
        self.H = H
        self.frame = nn.Linear(S + A, fe)
        self.net = nn.Sequential(nn.GELU(), nn.Linear(H * fe, w), nn.GELU(), nn.Linear(w, w), nn.GELU(), nn.Linear(w, D))

    def forward(self, x):  # x (B, H, S+A) -> (B, D)
        return self.net(self.frame(x).flatten(1))

    def forward_seq(self, x):  # x (B, L, S+A) -> (B, L-H+1, D), sliding windows
        f = self.frame(x)  # (B, L, fe)
        win = f.unfold(1, self.H, 1)  # (B, L-H+1, fe, H)
        win = win.transpose(-1, -2).flatten(2)
        return self.net(win)


class MLPPred(nn.Module):
    def __init__(self, A, D, w, depth=4):
        super().__init__()
        layers = [nn.Linear(D + A, w), nn.GELU()]
        for _ in range(depth - 2):
            layers += [nn.Linear(w, w), nn.GELU()]
        layers += [nn.Linear(w, D)]
        self.net = nn.Sequential(*layers)

    def init_state(self, z):
        return z

    def step(self, st, a):  # st = z (B, D)
        z = st + self.net(torch.cat([st, a], -1))
        return z, z


class GRUEnc(nn.Module):
    def __init__(self, S, A, D, w, layers=2):
        super().__init__()
        self.inp = nn.Linear(S + A, w)
        self.gru = nn.GRU(w, w, num_layers=layers, batch_first=True)
        self.out = nn.Linear(w, D)

    def forward(self, x):
        y, _ = self.gru(self.inp(x))
        return self.out(y[:, -1])

    def forward_seq(self, x):
        y, _ = self.gru(self.inp(x))
        return self.out(y)


class GRUPred(nn.Module):
    def __init__(self, A, D, w):
        super().__init__()
        self.zin = nn.Linear(D, w)
        self.cell = nn.GRUCell(A, w)
        self.cell2 = nn.GRUCell(w, w)
        self.out = nn.Linear(w, D)

    def init_state(self, z):
        h = torch.tanh(self.zin(z))
        return (h, h)

    def step(self, st, a):
        h1, h2 = st
        h1 = self.cell(a, h1)
        h2 = self.cell2(h1, h2)
        return (h1, h2), self.out(h2)


def _tx(d, layers, heads):
    lay = nn.TransformerEncoderLayer(d, heads, 4 * d, dropout=0.0, activation="gelu", batch_first=True, norm_first=True)
    return nn.TransformerEncoder(lay, layers, enable_nested_tensor=False)


class TxEnc(nn.Module):
    def __init__(self, S, A, D, d, layers, heads, Hmax=64):
        super().__init__()
        self.inp = nn.Linear(S + A, d)
        self.pos = nn.Parameter(torch.zeros(1, Hmax + 8, d))
        self.tx = _tx(d, layers, heads)
        self.out = nn.Linear(d, D)

    def forward(self, x):
        h = self.inp(x) + self.pos[:, : x.size(1)]
        return self.out(self.tx(h)[:, -1])

    def forward_seq(self, x):  # causal over the whole sequence
        L = x.size(1)
        h = self.inp(x) + self.pos[:, :L]
        mask = nn.Transformer.generate_square_subsequent_mask(L)
        return self.out(self.tx(h, mask=mask, is_causal=True))


class TxPred(nn.Module):
    """AR predictor over a sliding window of W latents; action embedding added to tokens."""

    def __init__(self, A, D, d, layers, heads, W=8):
        super().__init__()
        self.W = W
        self.zin = nn.Linear(D, d)
        self.ain = nn.Linear(A, d)
        self.pos = nn.Parameter(torch.zeros(1, W, d))
        self.tx = _tx(d, layers, heads)
        self.out = nn.Linear(d, D)

    def init_state(self, z):  # window filled with the current latent (cost proxy)
        return z.unsqueeze(1).expand(-1, self.W, -1).contiguous()

    def step(self, win, a):  # win (B, W, D), a (B, A) applied at last token
        h = self.zin(win) + self.pos
        h = h.clone()
        h[:, -1] = h[:, -1] + self.ain(a)
        znew = self.out(self.tx(h)[:, -1])
        win = torch.cat([win[:, 1:], znew.unsqueeze(1)], 1)
        return win, znew

    def forward_seq(self, z, a):  # teacher-forced training over (B, L, D), causal
        L = z.size(1)
        h = self.zin(z) + self.ain(a)
        h = h + self.pos[:, :L] if L <= self.W else h
        mask = nn.Transformer.generate_square_subsequent_mask(L)
        return self.out(self.tx(h, mask=mask, is_causal=True))


# Tier tables chosen so that total params (H=32, S=192) land near 1M / 5M / 15M.
TX_TIERS = {  # d, enc_layers, pred_layers, heads
    "1M": (128, 2, 3, 4),
    "5M": (256, 2, 4, 8),
    "15M": (384, 3, 5, 8),
}


def _search_width(build, target, lo=32, hi=4096):
    best = None
    for w in range(lo, hi + 1, 32):
        n = build(w)
        if best is None or abs(n - target) < abs(best[1] - target):
            best = (w, n)
        if n > 1.3 * target:
            break
    return best[0]


TARGET = {"1M": 1e6, "5M": 5e6, "15M": 15e6}


def build(arch, tier, S=S_DEFAULT, A=A_DEFAULT, D=D_DEFAULT, H=32, W=8, width_ref_H=32):
    """Return (encoder, predictor, meta). Width is chosen at H=width_ref_H and kept for other H."""
    if arch == "tx":
        d, le, lp, heads = TX_TIERS[tier]
        enc = TxEnc(S, A, D, d, le, heads)
        pred = TxPred(A, D, d, lp, heads, W=W)
        meta = {"d": d, "enc_layers": le, "pred_layers": lp, "heads": heads, "W": W}
    elif arch == "mlp":
        f = lambda w: nparams(MLPEnc(S, A, D, width_ref_H, w)) + nparams(MLPPred(A, D, 2 * w))
        w = _search_width(f, TARGET[tier])
        enc = MLPEnc(S, A, D, H, w)
        pred = MLPPred(A, D, 2 * w)
        meta = {"enc_w": w, "pred_w": 2 * w, "pred_depth": 4}
    elif arch == "gru":
        f = lambda w: nparams(GRUEnc(S, A, D, w)) + nparams(GRUPred(A, D, w))
        w = _search_width(f, TARGET[tier])
        enc = GRUEnc(S, A, D, w)
        pred = GRUPred(A, D, w)
        meta = {"w": w, "enc_layers": 2, "pred_cells": 2}
    else:
        raise ValueError(arch)
    meta.update({"arch": arch, "tier": tier, "S": S, "A": A, "D": D, "H": H,
                 "enc_params": nparams(enc), "pred_params": nparams(pred)})
    meta["total_params"] = meta["enc_params"] + meta["pred_params"]
    return enc, pred, meta
