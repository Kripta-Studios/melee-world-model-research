"""E0 latency-bench models for architecture A (DESIGN §3), RANDOM WEIGHTS: they measure cost, not quality. PROP.

Shapes follow `evidence/A4/model_contract.json` (inputs.*, models.W0-S.heads) and DESIGN §2.1/§3.2-3.7:
  per player and frame: 10 continuous + dx,dy; categorical action(512) character(26) facing(2) on_ground(2)
  jumps_left(7) stock(5) hurtbox(3) invulnerable(2); counters action_frame(256) hitlag(64) hitstun(128)
  invuln_left(64, size assumed); controller 16 dims; 4 projectile slots x 7; stage_id.
Encoder E: per-field embeddings -> entity transformer over 7 tokens (2 players + 4 projectiles + stage) per frame ->
  temporal core over H frames. Cores: mlp (flattened window), gru (2 layers), tx (causal transformer, growing context
  history + rollout steps; with or without KV-cache; both give the same output, see tests/test_kv_cache.py).
W0-S: E + control conditioning (u_self, u_opp of f+1) + fused per-field heads (one Linear split by field, an
  implementation choice: same maths as one Linear per field) + sampling/decoding back into frame tensors.
q:    E (own weights) + factorised controller head (8 buttons Bernoulli, 4 stick axes x 161, 2 triggers x 141).
pi0:  smaller E + the same controller head. Mixture over K hypotheses in action space (DESIGN §3.1).
Declared simplifications (cost-neutral or cheaper than the real thing): two-hot with NB=63 bins (DreamerV3 uses 255);
dist_to_nearest_ledge recomputed as |x|-70; projectiles regressed, not sampled; open-loop q = ONE q forward on the
real history, K commands sampled and held for the D+1 steps; controller code = 8 bits + 4 axes + 2 triggers + 2 pad.
"""
import math
import torch
import torch.nn.functional as F
from torch import nn

NCONT, NCAT, NCNT, NCTRL, NPROJ, NPF = 12, 8, 4, 16, 4, 6
CAT_SIZES = [512, 26, 2, 2, 7, 5, 3, 2]
CAT_DIMS = [32, 8, 4, 4, 4, 4, 4, 4]
CNT_SIZES = [256, 64, 128, 64]
CNT_DIMS = [16, 8, 8, 8]
NSTAGE, NPTYPE = 32, 64
NB = 63  # two-hot bins (symlog)
TWOHOT_FIELDS = 8  # dpos_x, dpos_y, 5 speeds, shield
CTRL_HEAD = [("buttons", 8)] + [(f"axis{i}", 161) for i in range(4)] + [(f"trig{i}", 141) for i in range(2)]
CTRL_OUT = sum(n for _, n in CTRL_HEAD)


def nparams(m):
    return sum(p.numel() for p in m.parameters())


# ------------------------------------------------------------------------------------------- frame tensors
class Frames:
    """Batch of frame tensors; leading dims (B,) or (B, T)."""
    __slots__ = ("cont", "cat", "cnt", "ctrl", "proj", "ptype", "stage")

    def __init__(self, cont, cat, cnt, ctrl, proj, ptype, stage):
        self.cont, self.cat, self.cnt, self.ctrl = cont, cat, cnt, ctrl
        self.proj, self.ptype, self.stage = proj, ptype, stage

    def map(self, fn):
        return Frames(*(fn(getattr(self, k)) for k in self.__slots__))

    def at(self, t):
        return self.map(lambda x: x[:, t])


def random_frames(B, T, g=None):
    cat = torch.stack([torch.randint(0, n, (B, T, 2), generator=g) for n in CAT_SIZES], -1)
    cnt = torch.stack([torch.randint(0, n, (B, T, 2), generator=g) for n in CNT_SIZES], -1)
    return Frames(torch.randn(B, T, 2, NCONT, generator=g), cat, cnt, torch.randn(B, T, 2, NCTRL, generator=g),
                  torch.randn(B, T, NPROJ, NPF, generator=g), torch.randint(0, NPTYPE, (B, T, NPROJ), generator=g),
                  torch.randint(0, NSTAGE, (B, T), generator=g))


# ------------------------------------------------------------------------------------------------ encoder E
class Block(nn.Module):
    """Pre-norm transformer block with explicit q/k/v so that a KV-cache is possible."""

    def __init__(self, d, heads, ff):
        super().__init__()
        self.h, self.hd = heads, d // heads
        self.n1, self.n2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.o = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.ff = nn.Sequential(nn.Linear(d, ff), nn.GELU(), nn.Linear(ff, d))

    def _split(self, x):  # (B, L, d) -> 3 x (B, h, L, hd)
        B, L, _ = x.shape
        q, k, v = self.qkv(self.n1(x)).view(B, L, 3, self.h, self.hd).permute(2, 0, 3, 1, 4)
        return q, k, v

    def _out(self, x, a):
        B, h, L, hd = a.shape
        x = x + self.o(a.transpose(1, 2).reshape(B, L, h * hd))
        return x + self.ff(self.n2(x))

    def forward(self, x, causal=False):
        q, k, v = self._split(x)
        return self._out(x, F.scaled_dot_product_attention(q, k, v, is_causal=causal))

    def forward_cached(self, x, cache, t):
        """x (B, 1, d) at position t; cache = (Kc, Vc) preallocated (B, h, Lmax, hd), written in place."""
        q, k, v = self._split(x)
        Kc, Vc = cache
        Kc[:, :, t:t + 1] = k
        Vc[:, :, t:t + 1] = v
        return self._out(x, F.scaled_dot_product_attention(q, Kc[:, :, :t + 1], Vc[:, :, :t + 1]))

    def prefill(self, x, cache):
        q, k, v = self._split(x)
        L = x.shape[1]
        cache[0][:, :, :L] = k
        cache[1][:, :, :L] = v
        return self._out(x, F.scaled_dot_product_attention(q, k, v, is_causal=True))


class FrameEmbed(nn.Module):
    def __init__(self, d_e=96, d=192, layers=1, heads=4):
        super().__init__()
        self.cat = nn.ModuleList(nn.Embedding(n, k) for n, k in zip(CAT_SIZES, CAT_DIMS))
        self.cnt = nn.ModuleList(nn.Embedding(n, k) for n, k in zip(CNT_SIZES, CNT_DIMS))
        pin = NCONT + sum(CAT_DIMS) + sum(CNT_DIMS) + NCNT + NCTRL
        self.player = nn.Linear(pin, d_e)
        self.projl = nn.Linear(NPF, d_e)
        self.ptype = nn.Embedding(NPTYPE, d_e)
        self.stage = nn.Embedding(NSTAGE, d_e)
        self.role = nn.Parameter(torch.zeros(7, d_e))
        self.blocks = nn.ModuleList(Block(d_e, heads, 2 * d_e) for _ in range(layers))
        self.out = nn.Linear(4 * d_e, d)
        self.cnt_scale = torch.tensor([1 / 255, 1 / 63, 1 / 127, 1 / 63])

    def forward(self, fr):  # fr leading dims (N,) -> (N, d)
        cat = torch.cat([e(fr.cat[..., i]) for i, e in enumerate(self.cat)], -1)
        cnt = torch.cat([e(fr.cnt[..., i]) for i, e in enumerate(self.cnt)], -1)
        pl = self.player(torch.cat([fr.cont, cat, cnt, fr.cnt.float() * self.cnt_scale, fr.ctrl], -1))  # (N,2,d_e)
        pr = self.projl(fr.proj) + self.ptype(fr.ptype)  # (N,4,d_e)
        st = self.stage(fr.stage).unsqueeze(-2)  # (N,1,d_e)
        x = torch.cat([pl, pr, st], -2) + self.role
        for b in self.blocks:
            x = b(x)
        return self.out(torch.cat([x[:, 0], x[:, 1], x[:, 2:6].mean(1), x[:, 6]], -1))

    def seq(self, fr):  # leading (B, T) -> (B, T, d)
        B, T = fr.stage.shape
        return self(fr.map(lambda x: x.reshape(B * T, *x.shape[2:]))).view(B, T, -1)


# ------------------------------------------------------------------------------------------------- cores
class MLPCore(nn.Module):
    def __init__(self, d, H, w=512, fe=48):
        super().__init__()
        self.H = H
        self.fin = nn.Linear(d, fe)
        self.net = nn.Sequential(nn.GELU(), nn.Linear(H * fe, w), nn.GELU(), nn.Linear(w, w), nn.GELU(), nn.Linear(w, d))

    def prefix(self, e):  # e (B, H, d) -> state, h
        f = self.fin(e)
        return f, self.net(f.flatten(1))

    def step(self, f, e):  # e (B, d)
        f = torch.cat([f[:, 1:], self.fin(e).unsqueeze(1)], 1)
        return f, self.net(f.flatten(1))

    def expand(self, st, K):
        return st.expand(K, -1, -1)


class GRUCore(nn.Module):
    def __init__(self, d, H, layers=2):
        super().__init__()
        self.gru = nn.GRU(d, d, num_layers=layers, batch_first=True)

    def prefix(self, e):
        y, h = self.gru(e)
        return h, y[:, -1]

    def step(self, h, e):
        y, h = self.gru(e.unsqueeze(1), h)
        return h, y[:, 0]

    def expand(self, st, K):
        return st.expand(-1, K, -1).contiguous()


class TXCore(nn.Module):
    """Causal transformer over the growing context [history H | rollout steps]. kv=False recomputes everything."""

    def __init__(self, d, H, layers=2, heads=4, ff=None, Lmax=64, kv=True):
        super().__init__()
        self.kv, self.Lmax, self.heads = kv, Lmax, heads
        self.pos = nn.Parameter(torch.randn(1, Lmax, d) * 0.02)
        self.blocks = nn.ModuleList(Block(d, heads, ff or 2 * d) for _ in range(layers))
        self.norm = nn.LayerNorm(d)

    def full(self, e):
        x = e + self.pos[:, : e.shape[1]]
        for b in self.blocks:
            x = b(x, causal=True)
        return self.norm(x[:, -1])

    def prefix(self, e):
        if not self.kv:
            return e, self.full(e)
        B, L, d = e.shape
        hd = d // self.heads
        caches = [(torch.empty(B, self.heads, self.Lmax, hd), torch.empty(B, self.heads, self.Lmax, hd))
                  for _ in self.blocks]
        x = e + self.pos[:, :L]
        for b, c in zip(self.blocks, caches):
            x = b.prefill(x, c)
        return (caches, L), self.norm(x[:, -1])

    def step(self, st, e):
        if not self.kv:
            seq = torch.cat([st, e.unsqueeze(1)], 1)
            return seq, self.full(seq)
        caches, t = st
        x = (e + self.pos[:, t]).unsqueeze(1)
        for b, c in zip(self.blocks, caches):
            x = b.forward_cached(x, c, t)
        return (caches, t + 1), self.norm(x[:, 0])

    def expand(self, st, K):
        if not self.kv:
            return st.expand(K, -1, -1)
        caches, t = st
        return [(a.expand(K, -1, -1, -1).clone(), b.expand(K, -1, -1, -1).clone()) for a, b in caches], t


def make_core(kind, d, H):
    if kind == "mlp":
        return MLPCore(d, H)
    if kind == "gru":
        return GRUCore(d, H)
    if kind in ("tx", "tx_kv"):
        return TXCore(d, H, kv=kind == "tx_kv")
    raise ValueError(kind)


class Encoder(nn.Module):
    def __init__(self, core, d=192, d_e=96, H=16):
        super().__init__()
        self.emb = FrameEmbed(d_e, d)
        self.core = make_core(core, d, H)


# ------------------------------------------------------------------------------------------------- heads
def _w0s_layout():
    per = [("action", 512), ("change", 1), ("bern", 3), ("hurtbox", 3), ("jumps", 7), ("stock", 5),
           ("cmode", 12), ("creset0", 256), ("creset1", 64), ("creset2", 128), ("creset3", 64),
           ("twohot", TWOHOT_FIELDS * NB), ("abspos", 4), ("dpct", 61)]
    lay, o = {}, 0
    for p in (0, 1):
        for name, n in per:
            lay[(p, name)] = (o, o + n); o += n
    lay[("g", "events")] = (o, o + 12); o += 12
    lay[("g", "proj")] = (o, o + NPROJ * NPF); o += NPROJ * NPF
    return lay, o


W0S_LAYOUT, W0S_OUT = _w0s_layout()
BINS = torch.linspace(-6, 6, NB)
BINS_X = torch.sign(BINS) * (torch.exp(BINS.abs()) - 1)  # symexp


def gumbel_argmax(logits, u):
    return (logits - torch.log(-torch.log(u.clamp_(1e-9, 1 - 1e-9)))).argmax(-1)


def _pad_index(groups, total, width):
    """groups: list of (start, n) slices of a logits vector -> LongTensor (len(groups), width), pad -> `total`."""
    idx = torch.full((len(groups), width), total, dtype=torch.long)
    for i, (o, n) in enumerate(groups):
        idx[i, :n] = torch.arange(o, o + n)
    return idx


def _w0s_fast_tables():
    L = W0S_LAYOUT
    groups = []
    for p in (0, 1):
        o = L[(p, "action")][0]; groups.append((o, 512))
        for name in ("hurtbox", "jumps", "stock"):
            a, b = L[(p, name)]; groups.append((a, b - a))
        a = L[(p, "cmode")][0]
        groups += [(a + 3 * j, 3) for j in range(4)]
        for j in range(4):
            a, b = L[(p, f"creset{j}")]; groups.append((a, b - a))
        a, b = L[(p, "dpct")]; groups.append((a, b - a))
    tab = {"cat_idx": _pad_index(groups, W0S_OUT, 512)}
    tab["bern"] = torch.tensor([[L[(p, "bern")][0] + i for i in range(3)] for p in (0, 1)])
    tab["twohot"] = torch.tensor([list(range(*L[(p, "twohot")])) for p in (0, 1)])
    tab["abspos"] = torch.tensor([[L[(p, "abspos")][0], L[(p, "abspos")][0] + 1] for p in (0, 1)])
    tab["respawn"] = L[("g", "events")][0] + 8
    tab["proj"] = L[("g", "proj")]
    tab["cnt_max"] = torch.tensor(CNT_SIZES) - 1
    return tab


W0S_FAST = _w0s_fast_tables()
CTRL_FAST = _pad_index([(8 + 161 * i, 161) for i in range(4)] + [(8 + 644 + 141 * i, 141) for i in range(2)],
                       CTRL_OUT, 161)
CTRL_SCALE = torch.tensor([80.0, 80.0, 80.0, 80.0, 0.0, 0.0]), torch.tensor([80.0, 80.0, 80.0, 80.0, 140.0, 140.0])
NEG = torch.tensor([[-1e9]])


def padded_gumbel_argmax(lg, idx, g):
    """One gather + one argmax for all categorical fields (fields padded with -1e9)."""
    u = torch.rand(lg.shape, generator=g).clamp_(1e-9, 1 - 1e-9)  # noise only on real logits
    pert = lg - torch.log(-torch.log(u))
    return torch.cat([pert, NEG.expand(lg.shape[0], 1)], 1)[:, idx].argmax(-1)  # (K, nf)


def w0s_sample_next_fast(fr, lg, u_self, u_opp, g):
    """Vectorised equivalent of W0S.sample_next (same distributions, both players at once, ~25 ops)."""
    T = W0S_FAST
    K = lg.shape[0]
    c = padded_gumbel_argmax(lg, T["cat_idx"], g).view(K, 2, 13)
    bern = (torch.sigmoid(lg[:, T["bern"]]) > torch.rand(K, 2, 3, generator=g)).long()
    # cat order: action, character, facing, on_ground, jumps, stock, hurtbox, invulnerable
    cat = torch.stack([c[..., 0], fr.cat[..., 1], bern[..., 0], bern[..., 1], c[..., 2], c[..., 3], c[..., 1],
                       bern[..., 2]], -1)
    mode, reset = c[..., 4:8], c[..., 8:12]
    contv = torch.minimum(fr.cnt + 1, T["cnt_max"])
    cnt = torch.where(mode == 0, contv, torch.where(mode == 1, reset, torch.zeros_like(reset)))
    vals = (torch.softmax(lg[:, T["twohot"]].view(K, 2, TWOHOT_FIELDS, NB), -1) * BINS_X).sum(-1)  # (K,2,8)
    pos = fr.cont[..., 0:2] + vals[..., 0:2]
    respawn = (torch.sigmoid(lg[:, T["respawn"]]) > 0.5).view(K, 1, 1)
    pos = torch.where(respawn, lg[:, T["abspos"]], pos)
    pct = fr.cont[..., 7:8] + c[..., 12:13].float()
    ledge = pos[..., 0:1].abs() - 70.0
    rel = torch.stack([pos[:, 1] - pos[:, 0], pos[:, 0] - pos[:, 1]], 1)
    cont = torch.cat([pos, vals[..., 2:7], pct, vals[..., 7:8], ledge, rel], -1)
    a, b = T["proj"]
    return Frames(cont, cat, cnt, torch.stack([u_self, u_opp], 1), lg[:, a:b].view(K, NPROJ, NPF), fr.ptype, fr.stage)


def ctrl_sample_fast(lg, g):
    K = lg.shape[0]
    btn = (torch.sigmoid(lg[:, :8]) > torch.rand(K, 8, generator=g)).float()
    ax = padded_gumbel_argmax(lg, CTRL_FAST, g).float()
    return torch.cat([btn, (ax - CTRL_SCALE[0]) / CTRL_SCALE[1], torch.zeros(K, 2)], 1)


class W0S(nn.Module):
    def __init__(self, core="gru", d=192, H=16, hid=256):
        super().__init__()
        self.E = Encoder(core, d, H=H)
        self.uin = nn.Linear(2 * NCTRL, d)
        self.head = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, hid), nn.GELU(), nn.Linear(hid, W0S_OUT))

    def logits(self, h, u_self, u_opp):
        return self.head(h + self.uin(torch.cat([u_self, u_opp], -1)))

    def sample_next(self, fr, lg, u_self, u_opp, g):
        """fr: Frames (K,) current; lg (K, W0S_OUT); returns Frames (K,) for f+1."""
        K = lg.shape[0]
        u = torch.rand(K, W0S_OUT, generator=g)
        L = W0S_LAYOUT
        sl = lambda p, n: (lg[:, L[(p, n)][0]:L[(p, n)][1]], u[:, L[(p, n)][0]:L[(p, n)][1]])
        cat = fr.cat.clone(); cnt = fr.cnt.clone(); cont = fr.cont.clone()
        for p in (0, 1):
            a_l, a_u = sl(p, "action")
            cat[:, p, 0] = gumbel_argmax(a_l, a_u)
            b_l, b_u = sl(p, "bern")
            cat[:, p, [2, 3, 7]] = (torch.sigmoid(b_l) > b_u).long()
            for j, name in ((6, "hurtbox"), (4, "jumps"), (5, "stock")):
                l_, u_ = sl(p, name)
                cat[:, p, j] = gumbel_argmax(l_, u_)
            m_l, m_u = sl(p, "cmode")
            mode = gumbel_argmax(m_l.view(K, 4, 3), m_u.view(K, 4, 3))  # 0 continue, 1 reset, 2 zero
            for j in range(4):
                r_l, r_u = sl(p, f"creset{j}")
                reset = gumbel_argmax(r_l, r_u)
                cont_v = (fr.cnt[:, p, j] + 1).clamp(max=CNT_SIZES[j] - 1)
                cnt[:, p, j] = torch.where(mode[:, j] == 0, cont_v, torch.where(mode[:, j] == 1, reset, 0))
            t_l, _ = sl(p, "twohot")
            vals = (torch.softmax(t_l.view(K, TWOHOT_FIELDS, NB), -1) * BINS_X).sum(-1)  # two-hot mean
            ap, _ = sl(p, "abspos")
            dp, dp_u = sl(p, "dpct")
            cont[:, p, 0:2] = fr.cont[:, p, 0:2] + vals[:, 0:2]
            cont[:, p, 2:7] = vals[:, 2:7]
            cont[:, p, 7] = fr.cont[:, p, 7] + gumbel_argmax(dp, dp_u).float()
            cont[:, p, 8] = vals[:, 7]
            cont[:, p, 9] = cont[:, p, 0].abs() - 70.0
            ev = lg[:, L[("g", "events")][0]:L[("g", "events")][1]]
            respawn = torch.sigmoid(ev[:, 8]) > 0.5
            cont[:, p, 0:2] = torch.where(respawn.unsqueeze(-1), ap[:, 0:2], cont[:, p, 0:2])
        cont[:, 0, 10:12] = cont[:, 1, 0:2] - cont[:, 0, 0:2]
        cont[:, 1, 10:12] = -cont[:, 0, 10:12]
        pr = lg[:, L[("g", "proj")][0]:L[("g", "proj")][1]].view(K, NPROJ, NPF)
        ctrl = torch.stack([u_self, u_opp], 1)
        return Frames(cont, cat, cnt, ctrl, pr, fr.ptype, fr.stage)


class CtrlPolicy(nn.Module):
    """q (opponent BC) and pi0 share this shape: E + factorised controller head."""

    def __init__(self, core="gru", d=192, H=16, hid=256):
        super().__init__()
        self.E = Encoder(core, d, d_e=96 if d >= 192 else 64, H=H)
        self.head = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, hid), nn.GELU(), nn.Linear(hid, CTRL_OUT))

    @staticmethod
    def sample(lg, g):
        """lg (K, CTRL_OUT) -> controller code (K, 16)."""
        K = lg.shape[0]
        u = torch.rand(K, CTRL_OUT, generator=g)
        out = torch.zeros(K, NCTRL)
        out[:, :8] = (torch.sigmoid(lg[:, :8]) > u[:, :8]).float()
        o = 8
        for i in range(4):
            out[:, 8 + i] = (gumbel_argmax(lg[:, o:o + 161], u[:, o:o + 161]).float() - 80) / 80; o += 161
        for i in range(2):
            out[:, 12 + i] = gumbel_argmax(lg[:, o:o + 141], u[:, o:o + 141]).float() / 140; o += 141
        return out

    @staticmethod
    def mixture_act(lg):
        """Mixture over the K hypotheses in ACTION space: average per-factor probabilities, then argmax."""
        pb = torch.sigmoid(lg[:, :8]).mean(0)
        out = torch.zeros(NCTRL)
        out[:8] = (pb > 0.5).float()
        o = 8
        for i in range(4):
            out[8 + i] = (torch.softmax(lg[:, o:o + 161], -1).mean(0).argmax().float() - 80) / 80; o += 161
        for i in range(2):
            out[12 + i] = torch.softmax(lg[:, o:o + 141], -1).mean(0).argmax().float() / 140; o += 141
        return out


# ------------------------------------------------------------------------------------------ direct (Fast-JEPA P1)
DMAX = 18


class W0SDirect(nn.Module):
    """PROPUESTA P1 (research/sota_2611/2611.25927.md): una sola pasada h_f + cola propia f+1..f+D+1 + hipótesis de
    mando del rival + D  ->  logits del frame f+D+1 (mismo formato de salida que W0-S de un paso). Solo coste."""

    def __init__(self, d=192, hid=256):
        super().__init__()
        self.uin = nn.Linear((DMAX + 1) * NCTRL + NCTRL + 1, d)
        self.head = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, hid), nn.GELU(), nn.Linear(hid, W0S_OUT))

    def logits(self, h, own_queue, u_opp, D):
        K = h.shape[0]
        q = torch.zeros(DMAX + 1, NCTRL)
        q[:D + 1] = own_queue[:D + 1]
        x = torch.cat([q.reshape(1, -1).expand(K, -1), u_opp, torch.full((K, 1), D / DMAX)], -1)
        return self.head(h + self.uin(x))


# ------------------------------------------------------------------------------------------ predict present
class PresentPredictor(nn.Module):
    def __init__(self, core="gru", H=16, d=192, d_pi=128, fast=False):
        super().__init__()
        self.H, self.fast = H, fast
        self.w = W0S(core, d, H)
        self.q = CtrlPolicy(core, d, H)
        self.pi = CtrlPolicy("tx" if core.startswith("tx") else core, d_pi, H)
        self.wd = W0SDirect(d)

    def param_counts(self):
        return {"W0S": nparams(self.w), "q": nparams(self.q), "pi0": nparams(self.pi)}

    def predict(self, hist, own_queue, D, K=4, closed_loop=True, g=None, timings=None, return_debug=False):
        """hist: Frames (1, H); own_queue (D+1, 16): committed own commands f+1..f+D (+ last repeated).
        K hypotheses x (D+1) W0-S steps. Returns (command (16,), debug)."""
        tm = timings if timings is not None else {}
        t0 = _t()
        we = self.w.E.emb.seq(hist)                    # (1, H, d)
        wst, wh = self.w.E.core.prefix(we)
        qe = self.q.E.emb.seq(hist)
        qst, qh = self.q.E.core.prefix(qe)
        wst, wh = self.w.E.core.expand(wst, K), wh.expand(K, -1)
        tm["encode_ms"] = _ms(t0)
        t1 = _t()
        qsample = ctrl_sample_fast if self.fast else CtrlPolicy.sample
        wsample = w0s_sample_next_fast if self.fast else self.w.sample_next
        if closed_loop:
            qst, qh = self.q.E.core.expand(qst, K), qh.expand(K, -1)
        else:  # open loop: ONE q forward on the real history, K commands held for all D+1 steps
            u_open = qsample(self.q.head(qh).expand(K, -1), g)
        fr = hist.at(-1).map(lambda x: x.expand(K, *x.shape[1:]))
        traj = []
        hs = []
        for t in range(D + 1):
            u_self = own_queue[t].expand(K, -1)
            u_opp = qsample(self.q.head(qh), g) if closed_loop else u_open
            lg = self.w.logits(wh, u_self, u_opp)
            fr = wsample(fr, lg, u_self, u_opp, g)
            traj.append(fr)
            e = self.w.E.emb(fr)
            wst, wh = self.w.E.core.step(wst, e)
            hs.append(wh)
            if closed_loop:
                qst, qh = self.q.E.core.step(qst, self.q.E.emb(fr))
        tm["rollout_ms"] = _ms(t1)
        t2 = _t()
        # pi0 on the last H frames of each hypothesis (real history + imagined)
        n_im = min(D + 1, self.H)
        im = traj[-n_im:]
        real = hist.map(lambda x: (lambda y: y.expand(K, *y.shape[1:]))(x[:, (D + 1):])) if n_im < self.H else None
        stack = lambda xs: torch.stack(xs, 1)
        imf = Frames(*(stack([getattr(f, k) for f in im]) for k in Frames.__slots__))
        win = imf if real is None else Frames(*(torch.cat([getattr(real, k), getattr(imf, k)], 1) for k in Frames.__slots__))
        pe = self.pi.E.emb.seq(win)
        core = self.pi.E.core
        ph = core.full(pe) if isinstance(core, TXCore) else core.prefix(pe)[1]
        plg = self.pi.head(ph)
        a = CtrlPolicy.mixture_act(plg)
        tm["pi0_ms"] = _ms(t2)
        if return_debug:
            return a, {"h": torch.stack(hs, 1), "final": traj[-1], "pi_logits": plg}
        return a, None

    def predict_direct(self, hist, own_queue, D, K=4, g=None, timings=None):
        """P1: encode W y q una vez, K hipótesis del rival con una pasada de q, UNA pasada directa a f+D+1,
        pi0 sobre la ventana real desplazada + el frame imaginado final."""
        tm = timings if timings is not None else {}
        t0 = _t()
        wst, wh = self.w.E.core.prefix(self.w.E.emb.seq(hist))
        qst, qh = self.q.E.core.prefix(self.q.E.emb.seq(hist))
        tm["encode_ms"] = _ms(t0)
        t1 = _t()
        qsample = ctrl_sample_fast if self.fast else CtrlPolicy.sample
        wsample = w0s_sample_next_fast if self.fast else self.w.sample_next
        u_opp = qsample(self.q.head(qh).expand(K, -1), g)
        lg = self.wd.logits(wh.expand(K, -1), own_queue, u_opp, D)
        fr = hist.at(-1).map(lambda x: x.expand(K, *x.shape[1:]))
        fr = wsample(fr, lg, own_queue[D].expand(K, -1), u_opp, g)
        tm["rollout_ms"] = _ms(t1)
        t2 = _t()
        real = hist.map(lambda x:
                        x[:, 1:].expand(K, x.shape[1] - 1, *x.shape[2:]))  # ventana real sin el frame más viejo
        last = fr.map(lambda x: x.unsqueeze(1))
        win = Frames(*(torch.cat([getattr(real, k), getattr(last, k)], 1) for k in Frames.__slots__))
        pe = self.pi.E.emb.seq(win)
        core = self.pi.E.core
        ph = core.full(pe) if isinstance(core, TXCore) else core.prefix(pe)[1]
        a = CtrlPolicy.mixture_act(self.pi.head(ph))
        tm["pi0_ms"] = _ms(t2)
        return a, None

    def pi0_aged(self, hist):
        """Arm (a) / cheap fallback: pi0 on the aged observation, batch 1."""
        pe = self.pi.E.emb.seq(hist)
        core = self.pi.E.core
        ph = core.full(pe) if isinstance(core, TXCore) else core.prefix(pe)[1]
        return CtrlPolicy.mixture_act(self.pi.head(ph))


import time as _time  # noqa: E402


def _t():
    return _time.perf_counter_ns()


def _ms(t0):
    return (_time.perf_counter_ns() - t0) / 1e6
