"""A4 local_check: latencia en CPU de predictores candidatos (forward, sin entrenar, pesos aleatorios).

No mide calidad. Solo orden de magnitud del coste de un paso de predicción para un lote de candidatos,
para compararlo con el coste por frame del simulador DOCUMENTADO por su autor (melee-brute BRUTE.md:
12-15 us/frame dentro de la búsqueda, 17 us/frame desde Python). Re-implementa la estructura del
ARPredictor de le-wm (module.py: bloques AdaLN-zero, atención causal) sin einops.

Uso: python3 -I predictor_latency.py OUT.json
"""
import json
import sys
import time

import torch
from torch import nn
import torch.nn.functional as F

torch.set_num_threads(2)
torch.manual_seed(0)


class CondBlock(nn.Module):
    def __init__(self, dim, heads, dim_head, mlp_dim):
        super().__init__()
        self.h, self.dh = heads, dim_head
        self.n1 = nn.LayerNorm(dim, elementwise_affine=False)
        self.n2 = nn.LayerNorm(dim, elementwise_affine=False)
        self.qkv = nn.Linear(dim, 3 * heads * dim_head, bias=False)
        self.out = nn.Linear(heads * dim_head, dim)
        self.mlp = nn.Sequential(nn.LayerNorm(dim), nn.Linear(dim, mlp_dim), nn.GELU(), nn.Linear(mlp_dim, dim))
        self.ada = nn.Sequential(nn.SiLU(), nn.Linear(dim, 6 * dim))

    def forward(self, x, c):
        s1, g1, a1, s2, g2, a2 = self.ada(c).chunk(6, -1)
        y = self.n1(x) * (1 + g1) + s1
        B, T, _ = y.shape
        q, k, v = self.qkv(y).view(B, T, 3, self.h, self.dh).permute(2, 0, 3, 1, 4)
        o = F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(B, T, -1)
        x = x + a1 * self.out(o)
        y = self.n2(x) * (1 + g2) + s2
        return x + a2 * self.mlp(y)


class ARPred(nn.Module):
    def __init__(self, dim, depth, heads, dim_head, mlp_dim):
        super().__init__()
        self.blocks = nn.ModuleList([CondBlock(dim, heads, dim_head, mlp_dim) for _ in range(depth)])

    def forward(self, x, c):
        for b in self.blocks:
            x = b(x, c)
        return x


def mlp_pred(in_dim, hidden, out_dim, layers):
    mods, d = [], in_dim
    for _ in range(layers):
        mods += [nn.Linear(d, hidden), nn.GELU()]
        d = hidden
    mods.append(nn.Linear(d, out_dim))
    return nn.Sequential(*mods)


def bench(fn, reps=20):
    with torch.no_grad():
        for _ in range(3):
            fn()
        t = time.perf_counter()
        for _ in range(reps):
            fn()
    return (time.perf_counter() - t) / reps * 1e3


def main(out):
    res = []
    B = 512  # candidatos (p. ej. 64 acciones propias x 8 hipótesis del rival)
    # (a) predictor estructurado MLP: entrada = estado de 2 jugadores (~2x40 feats tras embeddings) + historia 8 frames
    #     + mandos de ambos (2x8 frames x 8 feats); salida = parámetros de cabezas (~2x700 logits/params)
    for hidden, layers in [(256, 3), (512, 4)]:
        m = mlp_pred(2 * 40 * 8 + 2 * 8 * 8, hidden, 2 * 700, layers).eval()
        x = torch.randn(B, 2 * 40 * 8 + 2 * 8 * 8)
        ms = bench(lambda: m(x))
        res.append(dict(model=f"MLP h{hidden} L{layers}", params=sum(p.numel() for p in m.parameters()),
                        batch=B, ms_per_step=round(ms, 3), us_per_candidate_step=round(ms * 1e3 / B, 3)))
    # (b) ARPredictor estilo le-wm, recalculando toda la ventana (sin caché KV), como hace JEPA.rollout
    for dim, depth, heads, dh, mlp, T in [(128, 4, 8, 16, 512, 16), (192, 6, 16, 64, 2048, 3), (192, 6, 16, 64, 2048, 16)]:
        m = ARPred(dim, depth, heads, dh, mlp).eval()
        x = torch.randn(B, T, dim)
        c = torch.randn(B, T, dim)
        ms = bench(lambda: m(x, c), reps=5)
        res.append(dict(model=f"ARPred d{dim} L{depth} H{heads}x{dh} mlp{mlp} T{T}",
                        params=sum(p.numel() for p in m.parameters()), batch=B, ms_per_step=round(ms, 3),
                        us_per_candidate_step=round(ms * 1e3 / B, 3)))
    meta = dict(torch=torch.__version__, threads=torch.get_num_threads(), note="servidor compartido, 4 vCPU; forward sin grad; float32")
    json.dump(dict(meta=meta, results=res), open(out, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
