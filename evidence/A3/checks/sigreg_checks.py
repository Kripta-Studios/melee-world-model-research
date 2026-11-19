"""A3 local checks on SIGReg (CPU, small). Run:
  python3 -I evidence/A3/checks/sigreg_checks.py <repo_root>
Writes evidence/A3/checks/sigreg_checks_result.json.
Checks:
 C1 API: README of galilai-group/lejepa uses EppsPulley(num_points=17); class signature uses n_points.
 C2 Equivalence: le-wm module.SIGReg formula == lejepa SlicingUnivariateTest(EppsPulley) for the same directions.
 C3 Cost: forward+backward wall time on CPU for typical N, D, M, K=17.
 C4 What SIGReg measures: values for Gaussian, information-free noise, collapsed, low-rank, binary-feature embeddings.
 C5 Toy invariance: LeJEPA-style training on synthetic 'Melee-like' tabular state with two view families;
    linear probes for 'facing' and 'phase' on frozen embeddings.
"""
import json, sys, time, os, math
import torch

root = sys.argv[1]
sys.path.insert(0, os.path.join(root, "sources/galilai-group_lejepa"))
import lejepa  # noqa: E402

torch.manual_seed(0)
torch.set_num_threads(2)
out = {}

# ---------- verbatim copy of le-wm module.SIGReg (lucas-maes/le-wm@8edfeb3, module.py:10-36), device-agnostic
class SIGReg(torch.nn.Module):
    def __init__(self, knots=17, num_proj=1024):
        super().__init__()
        self.num_proj = num_proj
        t = torch.linspace(0, 3, knots, dtype=torch.float32)
        dt = 3 / (knots - 1)
        weights = torch.full((knots,), 2 * dt, dtype=torch.float32)
        weights[[0, -1]] = dt
        window = torch.exp(-t.square() / 2.0)
        self.register_buffer("t", t)
        self.register_buffer("phi", window)
        self.register_buffer("weights", weights * window)

    def forward(self, proj, A=None):
        if A is None:
            A = torch.randn(proj.size(-1), self.num_proj, device=proj.device)
            A = A.div_(A.norm(p=2, dim=0))
        x_t = (proj @ A).unsqueeze(-1) * self.t
        err = (x_t.cos().mean(-3) - self.phi).square() + x_t.sin().mean(-3).square()
        statistic = (err @ self.weights) * proj.size(-2)
        return statistic.mean()

# ---------- C1
c1 = {}
try:
    lejepa.univariate.EppsPulley(num_points=17)
    c1["readme_call_num_points"] = "ok"
except TypeError as e:
    c1["readme_call_num_points"] = f"TypeError: {e}"
ep = lejepa.univariate.EppsPulley(n_points=17)
c1["n_points_call"] = "ok"
c1["defaults"] = {"t_max": float(ep.t[-1]), "n_points": ep.n_points}
out["C1_api"] = c1

# ---------- C2
x = torch.randn(1, 256, 192)  # (T=1, N, D)
A = torch.randn(192, 1024); A = A / A.norm(dim=0)
v_lewm = SIGReg()(x, A).item()
v_lejepa = ep(x @ A).mean().item()
out["C2_equivalence"] = {"lewm": v_lewm, "lejepa_EppsPulley_mean": v_lejepa,
                         "abs_diff": abs(v_lewm - v_lejepa)}

# ---------- C3 cost
def bench(N, D, M, reps=5):
    s = SIGReg(num_proj=M)
    z = torch.randn(1, N, D, requires_grad=True)
    s(z).backward()  # warmup
    t0 = time.perf_counter()
    for _ in range(reps):
        z.grad = None
        s(z).backward()
    return (time.perf_counter() - t0) / reps * 1000
c3 = []
for N, D, M in [(128, 192, 1024), (256, 192, 1024), (256, 192, 256), (1024, 192, 1024), (256, 64, 1024)]:
    c3.append({"N": N, "D": D, "M": M, "K": 17, "fwd_bwd_ms_cpu_2threads": round(bench(N, D, M), 2),
               "largest_intermediate_MB": round(N * M * 17 * 4 / 2**20, 1)})
out["C3_cost"] = c3

# ---------- C4 what SIGReg sees (average over 20 draws of directions, N=256, D=192)
def avg_sig(z, n=20):
    s = SIGReg(num_proj=1024)
    return sum(s(z[None]).item() for _ in range(n)) / n
N, D = 256, 192
g = torch.randn(N, D)
c4 = {
    "gaussian_iid": avg_sig(g),
    "noise_independent_of_input (identical distribution to gaussian_iid; carries zero information)": avg_sig(torch.randn(N, D)),
    "collapsed_constant": avg_sig(torch.zeros(N, D) + 0.3),
    "rank8_scaled_unit_total_var": avg_sig((torch.randn(N, 8) @ torch.randn(8, D)) / math.sqrt(8) / math.sqrt(1.0)),
    "rank8_isotropic_in_8dims_zero_elsewhere": avg_sig(torch.cat([torch.randn(N, 8), torch.zeros(N, D - 8)], 1)),
    "one_binary_pm1_coordinate_rest_gaussian": avg_sig(torch.cat([torch.randint(0, 2, (N, 1)).float() * 2 - 1, torch.randn(N, D - 1)], 1)),
    "16_binary_pm1_coordinates_rest_gaussian": avg_sig(torch.cat([torch.randint(0, 2, (N, 16)).float() * 2 - 1, torch.randn(N, D - 16)], 1)),
    "all_192_binary_pm1": avg_sig(torch.randint(0, 2, (N, D)).float() * 2 - 1),
    "gaussian_times_3_(wrong_scale)": avg_sig(3 * g),
}
out["C4_sigreg_values_N256_D192_M1024"] = c4

# ---------- C5 toy invariance on synthetic tabular state
def make_state(n, gen):
    x = torch.rand(n, 1, generator=gen) * 2 - 1           # stage x in [-1,1]
    y = torch.rand(n, 1, generator=gen)
    facing = (torch.rand(n, 1, generator=gen) < 0.5).float() * 2 - 1
    vx = torch.randn(n, 1, generator=gen) * 0.3
    phase = torch.rand(n, 1, generator=gen)               # normalized action_frame
    nuis = torch.randn(n, 3, generator=gen)
    return torch.cat([x, y, facing, vx, torch.sin(2 * math.pi * phase), torch.cos(2 * math.pi * phase), nuis], 1), facing, phase

def view(s, kind, gen):
    v = s + 0.05 * torch.randn(s.shape, generator=gen)    # small jitter for all
    if kind == "mirror":   # left/right mirror augmentation: flip x, facing, vx with p=.5
        m = (torch.rand(s.size(0), 1, generator=gen) < 0.5).float() * -2 + 1
        v = v.clone(); v[:, [0]] *= m; v[:, [2]] *= m; v[:, [3]] *= m
    if kind == "phase_jitter":  # treat nearby animation frames as same: random phase shift up to +-0.25 cycle
        ph = torch.atan2(v[:, 4], v[:, 5]) + (torch.rand(s.size(0), generator=gen) - 0.5) * math.pi
        v = v.clone(); v[:, 4] = torch.sin(ph); v[:, 5] = torch.cos(ph)
    return v

def train_and_probe(kind, seed, steps=800, N=256, V=4, lam=0.05, dim=32):
    gen = torch.Generator().manual_seed(seed)
    torch.manual_seed(seed)
    enc = torch.nn.Sequential(torch.nn.Linear(9, 128), torch.nn.GELU(), torch.nn.Linear(128, 128), torch.nn.GELU(), torch.nn.Linear(128, dim))
    opt = torch.optim.AdamW(enc.parameters(), lr=1e-3, weight_decay=1e-4)
    sig = SIGReg(num_proj=256)
    for _ in range(steps):
        s, _, _ = make_state(N, gen)
        z = torch.stack([enc(view(s, kind, gen)) for _ in range(V)])  # (V,N,dim)
        inv = (z.mean(0) - z).square().mean()                        # LeJEPA MINIMAL.md:172
        loss = lam * sig(z) + (1 - lam) * inv                         # MINIMAL.md:174
        opt.zero_grad(); loss.backward(); opt.step()
    # linear probes on frozen embedding of clean states
    s_tr, f_tr, p_tr = make_state(4000, gen); s_te, f_te, p_te = make_state(2000, gen)
    with torch.no_grad():
        z_tr, z_te = enc(s_tr), enc(s_te)
    mu, sd = z_tr.mean(0), z_tr.std(0) + 1e-6
    z_tr, z_te = (z_tr - mu) / sd, (z_te - mu) / sd
    def lin_fit(Z, Y):
        Z1 = torch.cat([Z, torch.ones(Z.size(0), 1)], 1)
        return torch.linalg.lstsq(Z1, Y).solution
    def lin_pred(W, Z):
        return torch.cat([Z, torch.ones(Z.size(0), 1)], 1) @ W
    Wf = lin_fit(z_tr, f_tr); acc_f = ((lin_pred(Wf, z_te).sign() == f_te).float().mean()).item()
    tgt_tr = torch.cat([torch.sin(2*math.pi*p_tr), torch.cos(2*math.pi*p_tr)], 1)
    tgt_te = torch.cat([torch.sin(2*math.pi*p_te), torch.cos(2*math.pi*p_te)], 1)
    Wp = lin_fit(z_tr, tgt_tr); pr = lin_pred(Wp, z_te)
    r2_p = (1 - (pr - tgt_te).square().sum() / (tgt_te - tgt_te.mean(0)).square().sum()).item()
    xs_tr = s_tr[:, [0]]; xs_te = s_te[:, [0]]
    Wx = lin_fit(z_tr, xs_tr); r2_x = (1 - (lin_pred(Wx, z_te) - xs_te).square().sum() / (xs_te - xs_te.mean()).square().sum()).item()
    return {"facing_linear_acc": round(acc_f, 3), "phase_linear_R2": round(r2_p, 3), "x_linear_R2": round(r2_x, 3),
            "final_inv": round(inv.item(), 4)}

c5 = {}
for kind in ["jitter_only", "mirror", "phase_jitter"]:
    c5[kind] = [train_and_probe(kind, seed) for seed in (0, 1, 2)]
out["C5_toy_invariance_probe"] = c5
out["torch"] = torch.__version__
out_path = os.path.join(root, "evidence/A3/checks/sigreg_checks_result.json")
json.dump(out, open(out_path, "w"), indent=1)
print(json.dumps(out, indent=1))
