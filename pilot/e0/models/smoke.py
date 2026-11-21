"""Prueba de humo de E0: W0-S pequeño (MLP, H=8) y q pequeño (MLP, H=8), ≤ 1M parámetros, CPU, 2 hilos.

NO es un resultado de E1: solo verifica que el ciclo datos -> entrenamiento -> rollout -> métricas funciona y mide
throughput, RAM y dispersión entre semillas. Mismas anclas, subconjuntos y métricas que floors.py.

W0-S: paso de 1 frame  [x_{f-7..f} (estado + mandos de ambos), u_{f+1} de ambos]  ->  x_{f+1} de ambos.
      Rollout AR a h ∈ {4, 8} realimentando argmax de los discretos y la media de los Δ continuos.
      Variantes de mandos futuros en evaluación: oracle_u (reales, ORACLE: cota), persist_u (u_{f+k} = u_f;
      misma información que los suelos) y shuffled_u (secuencia real de otra ancla del lote: control de "acciones
      barajadas").
q:    [x_{f-7..f} con el rival en la ranura 0, I_full]  ->  mando del rival en f+1, f+7, f+13 (cabezas directas).
      8 botones (Bernoulli), stick y C-stick (celdas top-K de train + OTHER, mismo vocabulario que floors.py).

Uso (python del sistema con torch):
  nice -n 19 python3 pilot/e0/models/smoke.py --model w0s --seed 0 --games 40 --epochs 2
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
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
import torch.nn.functional as Fn  # noqa: E402

import common as C  # noqa: E402
import floors as FL  # noqa: E402
import metrics as M  # noqa: E402

torch.set_num_threads(2)


def _watchdog(cap_mb=880):
    """Aborta el proceso si VmRSS supera el tope (encargo: 900 MB por proceso)."""
    import threading

    def run():
        while True:
            mb = _P.rss_mb()
            if mb > cap_mb:
                print(f"WATCHDOG: VmRSS {mb:.0f} MB > {cap_mb} MB, abortando", flush=True)
                os._exit(3)
            time.sleep(1.0)
    threading.Thread(target=run, daemon=True).start()
OUTDIR = os.path.join(C.REPO, "evidence", "E0", "floors")
NCOL = 32          # columnas de la fila cruda por puerto
I_ACT, I_FAC, I_AIR, I_JMP, I_STK, I_HRT = 12, 13, 14, 15, 16, 17
CTRL0 = 18         # 8 bits, 4 sticks (-80..80), 2 gatillos (0..140)
STAGES = [2, 3, 8, 28, 31, 32]
DISC_HEADS = [("facing", I_FAC, 3, 1), ("airborne", I_AIR, 2, 0), ("jumps_left", I_JMP, 7, 0),
              ("stocks", I_STK, 5, 0), ("hurtbox", I_HRT, 3, 0)]   # (campo, col, clases, offset de codificación)


def rss_mb():
    return _P.peak_rss_mb()


def raw_rows(v: dict) -> np.ndarray:
    n = len(v["pos_x"])
    R = np.zeros((n, 2, NCOL), np.float32)
    for i, c in enumerate(C.CONT):
        R[:, :, i] = v[c]
    R[:, :, I_ACT] = v["action"]
    R[:, :, I_FAC] = v["facing"]
    R[:, :, I_AIR] = v["airborne"]
    R[:, :, I_JMP] = v["jumps_left"]
    R[:, :, I_STK] = v["stocks"]
    R[:, :, I_HRT] = v["hurtbox"]
    R[:, :, CTRL0:CTRL0 + 8] = C.button_bits(v["buttons_phys"])
    for j, c in enumerate(["joy_x", "joy_y", "cstick_x", "cstick_y", "trig_l", "trig_r"]):
        R[:, :, CTRL0 + 8 + j] = v[c]
    return R


class Block:
    """Partidas copiadas a RAM como un tensor [N, 2, 32] contiguo (no se toca el memmap en el bucle)."""

    def __init__(self, arrs, games, keep_view=False):
        """keep_view=False (train): no se guardan vistas del memmap; R se rellena en sitio (sin copia doble)."""
        N = sum(g["n"] for g in games)
        R = np.empty((N, 2, NCOL), np.float32)
        self.games = []
        s = 0
        for g in games:
            v = FL.game_view(arrs, g)
            R[s:s + g["n"]] = raw_rows(v)
            # val: copia en RAM de los campos (pequeña) para no retener páginas del memmap
            self.games.append(dict(g, lstart=s, view={k: np.array(x) for k, x in v.items()} if keep_view else None))
            del v
            s += g["n"]
        self.R = torch.from_numpy(R)
        self.stage = torch.zeros(len(self.R), dtype=torch.long)
        for g in self.games:
            self.stage[g["lstart"]:g["lstart"] + g["n"]] = STAGES.index(g["stage"]) if g["stage"] in STAGES else 0

    def anchors(self, h_after: int):
        return np.concatenate([g["lstart"] + np.arange(C.HIST - 1, g["n"] - h_after) for g in self.games])


class Feat(nn.Module):
    def __init__(self, act_vocab, mu, sd, emb=16):
        super().__init__()
        lut = torch.full((65536,), len(act_vocab), dtype=torch.long)
        lut[torch.tensor(act_vocab)] = torch.arange(len(act_vocab))
        self.register_buffer("lut", lut)
        self.register_buffer("mu", torch.tensor(mu, dtype=torch.float32))
        self.register_buffer("sd", torch.tensor(sd, dtype=torch.float32))
        self.emb = nn.Embedding(len(act_vocab) + 1, emb)
        self.dim = 12 + emb + 2 + 7 + 5 + 3 + 14

    def ctrl(self, r):  # r [..., 32] o [..., 14]
        c = r[..., CTRL0:] if r.shape[-1] == NCOL else r
        return torch.cat([c[..., :8], c[..., 8:12] / 80.0, c[..., 12:14] / 140.0], -1)

    def forward(self, r):
        cont = (r[..., :12] - self.mu) / self.sd
        a = self.emb(self.lut[r[..., I_ACT].long()])
        oh = lambda col, k: Fn.one_hot(r[..., col].long().clamp(0, k - 1), k).float()  # noqa: E731
        return torch.cat([cont, a, r[..., I_FAC:I_FAC + 1], r[..., I_AIR:I_AIR + 1], oh(I_JMP, 7), oh(I_STK, 5),
                          oh(I_HRT, 3), self.ctrl(r)], -1)


def mlp(din, hid, dout):
    return nn.Sequential(nn.Linear(din, hid), nn.LayerNorm(hid), nn.GELU(), nn.Linear(hid, hid), nn.LayerNorm(hid),
                         nn.GELU(), nn.Linear(hid, dout))


class W0S(nn.Module):
    def __init__(self, feat, n_act, dsd, hid=384):
        super().__init__()
        self.feat, self.n_act = feat, n_act
        self.register_buffer("dsd", torch.tensor(dsd, dtype=torch.float32))
        self.sizes = [n_act] + [k for _, _, k, _ in DISC_HEADS] + [12]
        self.per = sum(self.sizes)
        self.net = mlp(C.HIST * 2 * feat.dim + 2 * 14 + len(STAGES), hid, 2 * self.per)

    def forward(self, win, u_next, stage):
        B = win.shape[0]
        x = torch.cat([self.feat(win).reshape(B, -1), self.feat.ctrl(u_next).reshape(B, -1),
                       Fn.one_hot(stage, len(STAGES)).float()], -1)
        out = self.net(x).reshape(B, 2, self.per)
        return torch.split(out, self.sizes, -1)   # action, 5 discretos, Δ continuos normalizados

    def next_raw(self, last, outs, u_next, act_vocab_t):
        """Fila cruda predicha f+1 a partir de la última fila f, salidas de la red y mandos u_{f+1}."""
        new = last.clone()
        new[..., :12] = last[..., :12] + outs[-1] * self.dsd
        ai = outs[0].argmax(-1)
        new[..., I_ACT] = torch.where(ai < len(act_vocab_t), act_vocab_t[ai.clamp(max=len(act_vocab_t) - 1)],
                                      last[..., I_ACT])
        for (name, col, k, off), o in zip(DISC_HEADS, outs[1:-1]):
            new[..., col] = (o.argmax(-1) - off).float()
        new[..., CTRL0:] = u_next
        return new


class Q(nn.Module):
    def __init__(self, feat, n_st, n_cs, hid=256):
        super().__init__()
        self.feat = feat
        self.sizes = [8, n_st, n_cs]
        self.per = sum(self.sizes)
        self.net = mlp(C.HIST * 2 * feat.dim + len(STAGES), hid, len(C.H_Q) * self.per)

    def forward(self, win, stage):
        B = win.shape[0]
        x = torch.cat([self.feat(win).reshape(B, -1), Fn.one_hot(stage, len(STAGES)).float()], -1)
        out = self.net(x).reshape(B, len(C.H_Q), self.per)
        return torch.split(out, self.sizes, -1)


def n_params(m):
    return sum(p.numel() for p in m.parameters())


def gather(R, idx, lo, hi):
    """R[idx + k] para k ∈ [lo, hi) -> [B, hi-lo, 2, 32]."""
    off = torch.arange(lo, hi)
    return R[idx[:, None] + off[None, :]]


# ------------------------------------------------------------------ objetivos (q)
def q_targets(V, R, idx, h, rival):
    """Clases del mando del rival en f+h (rival = 0/1, tensor [B])."""
    r = R[idx + h, rival].numpy()                      # [B, 32]
    bits = r[:, CTRL0:CTRL0 + 8].astype(np.int64)
    st = V.stick(r[:, CTRL0 + 8], r[:, CTRL0 + 9])
    cs = V.cstick(r[:, CTRL0 + 10], r[:, CTRL0 + 11])
    return bits, st, cs


def swap_ports(win, rival):
    """Pone al rival en la ranura 0. win [B, L, 2, 32], rival [B]."""
    sw = rival.bool()
    out = win.clone()
    out[sw] = win[sw].flip(2)
    return out


# ------------------------------------------------------------------ entrenamiento
def train(args, model, blk, V, act_vocab_t, seed):
    g = torch.Generator().manual_seed(seed)
    rng = np.random.default_rng(seed)
    h_after = 1 if args.model == "w0s" else max(C.H_Q)
    anc = blk.anchors(h_after)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    steps_per_epoch = len(anc) // args.batch
    total = steps_per_epoch * args.epochs
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=total, pct_start=0.05)
    R = blk.R
    log = []
    t_start = time.time()
    for ep in range(args.epochs):
        perm = rng.permutation(anc)
        t0 = time.time()
        tot = 0.0
        for s in range(steps_per_epoch):
            idx = torch.from_numpy(perm[s * args.batch:(s + 1) * args.batch])
            win = gather(R, idx, -(C.HIST - 1), 1)
            stage = blk.stage[idx]
            if args.model == "w0s":
                nxt = R[idx + 1]                                       # [B, 2, 32]
                outs = model(win, nxt[..., CTRL0:], stage)
                last = win[:, -1]
                loss = 0.0
                ya = model.feat.lut[nxt[..., I_ACT].long()].clamp(max=model.n_act - 1)
                chg = (nxt[..., I_ACT] != last[..., I_ACT]).float()
                ce = Fn.cross_entropy(outs[0].reshape(-1, model.n_act), ya.reshape(-1), reduction="none")
                loss = loss + (ce * (1 + args.w_change * chg.reshape(-1))).mean()
                for (name, col, k, off), o in zip(DISC_HEADS, outs[1:-1]):
                    y = (nxt[..., col].long() + off).clamp(0, k - 1)
                    loss = loss + Fn.cross_entropy(o.reshape(-1, k), y.reshape(-1))
                dt = (nxt[..., :12] - last[..., :12]) / model.dsd
                loss = loss + Fn.huber_loss(outs[-1], dt)
            else:
                rival = torch.from_numpy(rng.integers(0, 2, len(idx)))
                outs = model(swap_ports(win, rival), stage)
                loss = 0.0
                for hi, h in enumerate(C.H_Q):
                    bits, st, cs = q_targets(V, R, idx, h, rival)
                    loss = loss + Fn.binary_cross_entropy_with_logits(outs[0][:, hi], torch.from_numpy(bits).float(),
                                                                      reduction="sum") / len(idx)
                    loss = loss + Fn.cross_entropy(outs[1][:, hi], torch.from_numpy(st))
                    loss = loss + Fn.cross_entropy(outs[2][:, hi], torch.from_numpy(cs))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            tot += float(loss)
            if (s + 1) % 200 == 0:
                print(f"  ep{ep} step {s+1}/{steps_per_epoch} loss {tot/(s+1):.4f} "
                      f"{(s+1)*args.batch/(time.time()-t0):.0f} muestras/s rss {rss_mb():.0f}MB", flush=True)
        dt_ep = time.time() - t0
        log.append(dict(epoch=ep, loss=tot / steps_per_epoch, seconds=dt_ep, samples=steps_per_epoch * args.batch,
                        samples_per_s=steps_per_epoch * args.batch / dt_ep, rss_mb=rss_mb()))
        print(json.dumps(log[-1]), flush=True)
    return log, time.time() - t_start


# ------------------------------------------------------------------ evaluación
@torch.no_grad()
def eval_w0s(model, blk, V, act_vocab_t, acc, pg, seed, args):
    model.eval()
    R = blk.R
    gshuf = np.random.default_rng(1000 + seed)
    hs = [1, 4, 8]
    t0, n_fwd = time.time(), 0
    for g in blk.games:
        v = g["view"]
        f = C.anchors(g["n"])
        gid = g["sha1"][:10]
        idx_all = torch.from_numpy(g["lstart"] + f)
        preds = {var: {h: [] for h in hs} for var in ("oracle_u", "persist_u", "shuffled_u")}
        nll1 = {var: [] for var in preds}
        for c0 in range(0, len(f), args.eval_batch):
            idx = idx_all[c0:c0 + args.eval_batch]
            win0 = gather(R, idx, -(C.HIST - 1), 1)
            fut = gather(R, idx, 1, max(hs) + 1)[..., CTRL0:]          # [B, 8, 2, 14] mandos reales
            perm = torch.from_numpy(gshuf.permutation(len(idx)))
            futs = {"oracle_u": fut, "persist_u": win0[:, -1:, :, CTRL0:].expand_as(fut).clone(),
                    "shuffled_u": fut[perm]}
            for var, fu in futs.items():
                win = win0.clone()
                for k in range(1, max(hs) + 1):
                    outs = model(win, fu[:, k - 1], blk.stage[idx])
                    n_fwd += len(idx)
                    if k == 1:
                        ya = model.feat.lut[R[idx + 1][..., I_ACT].long()].clamp(max=model.n_act - 1)
                        nll1[var].append(Fn.cross_entropy(outs[0].permute(0, 2, 1), ya, reduction="none"))
                    new = model.next_raw(win[:, -1], outs, fu[:, k - 1], act_vocab_t)
                    if k in hs:
                        preds[var][k].append(new.clone())
                    win = torch.cat([win[:, 1:], new[:, None]], 1)
        for var in preds:
            nl = torch.cat(nll1[var]).numpy()
            for h in hs:
                P = torch.cat(preds[var][h]).numpy()                  # [n, 2, 32]
                for p in range(2):
                    masks = C.event_masks(v, p, f, h)
                    Tt = blk.R[torch.from_numpy(g["lstart"] + f + h), p].numpy()

                    def put(field, pred, true, nll=None, kind="disc"):
                        for sname, m in masks.items():
                            key = (f"w0s_{var}", "dyn", field, h, sname, seed)
                            if kind == "cont":
                                acc.cont(key, pred, true, m)
                                if field in FL.PER_GAME_FIELDS and sname in FL.PER_GAME_SUBSETS:
                                    pg.cont(key + (gid,), pred, true, m)
                            else:
                                acc.disc(key, pred, true, m, nll)
                                if field in FL.PER_GAME_FIELDS and sname in FL.PER_GAME_SUBSETS:
                                    pg.disc(key + (gid,), pred, true, m, nll)

                    for i, c in enumerate(C.CONT):
                        put(c, P[:, p, i], Tt[:, i], kind="cont")
                    put("action", V.act(P[:, p, I_ACT].astype(np.int64)), V.act(Tt[:, I_ACT].astype(np.int64)),
                        nl[:, p] if h == 1 else None)
                    for name, col, k, off in DISC_HEADS:
                        put(name, P[:, p, col].astype(np.int64) + off, Tt[:, col].astype(np.int64) + off)
    model.train()
    return dict(eval_seconds=time.time() - t0, eval_forward_samples=n_fwd)


@torch.no_grad()
def eval_q(model, blk, V, acc, pg, seed, args):
    model.eval()
    R = blk.R
    t0, n_fwd = time.time(), 0
    for g in blk.games:
        f = C.anchors(g["n"])
        gid = g["sha1"][:10]
        idx_all = torch.from_numpy(g["lstart"] + f)
        for p in range(2):
            res = {h: {"bits_p": [], "bits_l": [], "st": [], "cs": []} for h in C.H_Q}
            for c0 in range(0, len(f), args.eval_batch):
                idx = idx_all[c0:c0 + args.eval_batch]
                rival = torch.full((len(idx),), p, dtype=torch.long)
                outs = model(swap_ports(gather(R, idx, -(C.HIST - 1), 1), rival), blk.stage[idx])
                n_fwd += len(idx)
                for hi, h in enumerate(C.H_Q):
                    _b, st_c, cs_c = q_targets(V, R, idx, h, rival)
                    res[h]["bits_l"].append(outs[0][:, hi])
                    for name, o, y in (("st", outs[1][:, hi], st_c), ("cs", outs[2][:, hi], cs_c)):
                        L = Fn.log_softmax(o, -1)   # solo se guardan NLL del objetivo y argmax (RAM)
                        res[h][name].append((-L[torch.arange(len(y)), torch.from_numpy(y)], L.argmax(-1)))
            idx_np = g["lstart"] + f
            for h in C.H_Q:
                bt, st_t, cs_t = q_targets(V, R, torch.from_numpy(idx_np), h, torch.full((len(f),), p))
                b0, st0, cs0 = q_targets(V, R, torch.from_numpy(idx_np), 0, torch.full((len(f),), p))
                logit = torch.cat(res[h]["bits_l"]).numpy()
                p1 = 1 / (1 + np.exp(-logit))
                bit_nll = M.bernoulli_nll(p1, bt.astype(bool))
                key0 = ("q_mlp", "q")
                for i, b in enumerate(C.BUTTON_NAMES):
                    pred = (p1[:, i] > 0.5).astype(np.int64)
                    for sname, m in {"all": np.ones(len(f), bool), "change": bt[:, i] != b0[:, i]}.items():
                        k = key0 + (f"btn_{b}", h, sname, seed)
                        acc.disc(k, pred, bt[:, i], m, bit_nll[:, i])
                        if f"btn_{b}" in FL.PER_GAME_FIELDS:
                            pg.disc(k + (gid,), pred, bt[:, i], m, bit_nll[:, i])
                code_t = (bt * (1 << np.arange(8))).sum(1)
                code_p = ((p1 > 0.5) * (1 << np.arange(8))).sum(1)
                for sname, m in {"all": np.ones(len(f), bool), "change": (bt != b0).any(1)}.items():
                    k = key0 + ("buttons", h, sname, seed)
                    acc.disc(k, code_p, code_t, m, bit_nll.sum(1))
                    pg.disc(k + (gid,), code_p, code_t, m, bit_nll.sum(1))
                for comp, lp, yt, y0 in (("stick", res[h]["st"], st_t, st0), ("cstick", res[h]["cs"], cs_t, cs0)):
                    nll = torch.cat([x[0] for x in lp]).numpy()
                    pred = torch.cat([x[1] for x in lp]).numpy()
                    for sname, m in {"all": np.ones(len(f), bool), "change": yt != y0}.items():
                        k = key0 + (comp, h, sname, seed)
                        acc.disc(k, pred, yt, m, nll)
                        pg.disc(k + (gid,), pred, yt, m, nll)
    model.train()
    return dict(eval_seconds=time.time() - t0, eval_forward_samples=n_fwd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["w0s", "q"], required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--games", type=int, default=40, help="nº de partidas de train (las primeras por sha1)")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--eval-batch", type=int, default=2048)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--w-change", type=float, default=3.0)
    ap.add_argument("--max-steps-bench", type=int, default=0, help=">0: solo mide throughput y sale")
    ap.add_argument("--tag", default="")
    ap.add_argument("--val-games", type=int, default=0, help="solo depuración: limita val")
    args = ap.parse_args()
    _watchdog()
    torch.manual_seed(args.seed)
    t_all = time.time()
    arrs, games = C.load_cache()
    voc = json.load(open(os.path.join(OUTDIR, "vocab.json")))
    V = FL.Vocab(voc)
    tr = sorted([g for g in games if g["split"] == "train"], key=lambda g: g["sha1"])[:args.games]
    va = [g for g in games if g["split"] == "val"]
    if args.val_games:
        va = va[:args.val_games]
    C.assert_no_test(tr + va)
    blk_tr, blk_va = Block(arrs, tr), Block(arrs, va, keep_view=True)
    del arrs   # se cierran los memmaps: ya no se tocan
    t_load = time.time() - t_all
    Rt = blk_tr.R
    mu = np.array([Rt[:, :, i].mean().item() for i in range(12)], np.float32)   # por campo: sin copias grandes
    sd = np.array([max(Rt[:, :, i].std().item(), 1e-3) for i in range(12)], np.float32)
    act_vocab = voc["actions"]
    act_vocab_t = torch.tensor(act_vocab, dtype=torch.float32)
    feat = Feat(act_vocab, mu, sd)
    if args.model == "w0s":
        # incluye 39 saltos entre partidas: despreciable; por campo para no materializar [N, 2, 12]
        dsd = np.array([max((Rt[1:, :, i] - Rt[:-1, :, i]).std().item(), 1e-3) for i in range(12)], np.float32)
        model = W0S(feat, len(act_vocab) + 1, dsd)
    else:
        model = Q(feat, V.n_st, V.n_cs)
    npar = n_params(model)
    assert npar <= 1_000_000, npar
    print(f"modelo {args.model}: {npar} parámetros; train {len(tr)} partidas ({len(Rt)} frames), "
          f"val {len(va)}; carga {t_load:.1f}s rss {rss_mb():.0f}MB", flush=True)
    if args.max_steps_bench:
        args.epochs = 1
        anc = blk_tr.anchors(1 if args.model == "w0s" else 13)
        blk_tr_anchors = anc[:args.max_steps_bench * args.batch]
        blk_tr.anchors = lambda h, a=blk_tr_anchors: a
    log, t_train = train(args, model, blk_tr, V, act_vocab_t, args.seed)
    if args.max_steps_bench:
        print(json.dumps(dict(bench=True, params=npar, log=log)))
        return
    acc, pg = M.Acc(), M.Acc()
    ev = (eval_w0s(model, blk_va, V, act_vocab_t, acc, pg, args.seed, args) if args.model == "w0s"
          else eval_q(model, blk_va, V, acc, pg, args.seed, args))
    tag = f"{args.model}_s{args.seed}{args.tag}"
    os.makedirs(os.path.join(OUTDIR, "runs"), exist_ok=True)
    M.write_rows(os.path.join(OUTDIR, "runs", f"smoke_{tag}.csv"), acc.rows(FL.kind_of))
    pgr = []
    for k, r in zip(sorted(pg.d, key=lambda k: tuple(map(str, k))), pg.rows(FL.kind_of)):
        r["subset"] = f"{r['subset']}@{k[6]}"
        pgr.append(r)
    M.write_rows(os.path.join(OUTDIR, "runs", f"smoke_{tag}_per_game.csv"), pgr)
    info = dict(model=args.model, seed=args.seed, params=npar, train_games=len(tr), train_frames=int(len(Rt)),
                train_anchors=int(len(blk_tr.anchors(1 if args.model == "w0s" else 13))), epochs=args.epochs,
                batch=args.batch, lr=args.lr, w_change=args.w_change, hist=C.HIST, threads=torch.get_num_threads(),
                load_seconds=t_load, train_seconds=t_train, epochs_log=log, **ev,
                eval_forward_samples_per_s=ev["eval_forward_samples"] / ev["eval_seconds"],
                total_seconds=time.time() - t_all, max_rss_mb=rss_mb(), torch=torch.__version__,
                train_games_sha1=[g["sha1"] for g in tr])
    json.dump(info, open(os.path.join(OUTDIR, "runs", f"smoke_{tag}.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in info.items() if k not in ("train_games_sha1",)})[:1500])


if __name__ == "__main__":
    main()
