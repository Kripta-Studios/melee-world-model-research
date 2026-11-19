"""A3 C5b: longer toy LeJEPA training (N=128, V=2, 2000 steps, seed 0) with direct invariance ratios.
Run: python3 -I evidence/A3/checks/toy_invariance_long.py <repo_root>"""
import sys, os, json, math, time, importlib.util
import torch
root = sys.argv[1]
spec = importlib.util.spec_from_file_location("chk", os.path.join(root, "evidence/A3/checks/sigreg_checks.py"))
# re-use definitions without re-running the checks: copy needed functions textually
src = open(os.path.join(root, "evidence/A3/checks/sigreg_checks.py")).read()
ns = {}
start = src.index("class SIGReg"); end = src.index("# ---------- C1")
exec("import torch, math\n" + src[start:end], ns)
start = src.index("def make_state"); end = src.index("def train_and_probe")
exec("import torch, math\n" + src[start:end], ns)
SIGReg, make_state, view = ns["SIGReg"], ns["make_state"], ns["view"]
torch.set_num_threads(2)

def mirror_exact(s):
    v = s.clone(); v[:, [0, 2, 3]] *= -1; return v
def phase_shift(s, d):
    ph = torch.atan2(s[:, 4], s[:, 5]) + d; v = s.clone(); v[:, 4] = torch.sin(ph); v[:, 5] = torch.cos(ph); return v

def run(kind, seed=0, steps=2000, N=128, V=2, lam=0.05, dim=32):
    gen = torch.Generator().manual_seed(seed); torch.manual_seed(seed)
    enc = torch.nn.Sequential(torch.nn.Linear(9, 128), torch.nn.GELU(), torch.nn.Linear(128, 128), torch.nn.GELU(), torch.nn.Linear(128, dim))
    opt = torch.optim.AdamW(enc.parameters(), lr=1e-3, weight_decay=1e-4); sig = SIGReg(num_proj=256)
    for _ in range(steps):
        s, _, _ = make_state(N, gen)
        z = torch.stack([enc(view(s, kind, gen)) for _ in range(V)])
        inv = (z.mean(0) - z).square().mean()
        loss = lam * sig(z) + (1 - lam) * inv
        opt.zero_grad(); loss.backward(); opt.step()
    s, f, p = make_state(2000, gen); s2, _, _ = make_state(2000, gen)
    with torch.no_grad():
        z = enc(s); base = (z - enc(s2)).norm(dim=1).mean()
        r_mirror = ((z - enc(mirror_exact(s))).norm(dim=1).mean() / base).item()
        r_phase = ((z - enc(phase_shift(s, math.pi / 4))).norm(dim=1).mean() / base).item()
        # linear probe facing (train/test halves)
        Z = (z - z.mean(0)) / (z.std(0) + 1e-6); Z1 = torch.cat([Z, torch.ones(len(Z), 1)], 1)
        W = torch.linalg.lstsq(Z1[:1000], f[:1000]).solution
        acc = ((Z1[1000:] @ W).sign() == f[1000:]).float().mean().item()
        tgt = torch.cat([torch.sin(2*math.pi*p), torch.cos(2*math.pi*p)], 1)
        Wp = torch.linalg.lstsq(Z1[:1000], tgt[:1000]).solution; pr = Z1[1000:] @ Wp
        r2 = (1 - (pr - tgt[1000:]).square().sum() / (tgt[1000:] - tgt[1000:].mean(0)).square().sum()).item()
    return {"ratio_dist_mirror_over_random_pair": round(r_mirror, 4), "ratio_dist_phase+1/8cycle_over_random_pair": round(r_phase, 4),
            "facing_linear_acc": round(acc, 3), "phase_linear_R2": round(r2, 3), "final_inv": round(inv.item(), 5)}
out = {}
for k in ["jitter_only", "mirror", "phase_jitter"]:
    t = time.perf_counter(); out[k] = run(k); out[k]["wall_s"] = round(time.perf_counter() - t, 1); print(k, out[k], flush=True)
json.dump(out, open(os.path.join(root, "evidence/A3/checks/toy_invariance_long_result.json"), "w"), indent=1)
