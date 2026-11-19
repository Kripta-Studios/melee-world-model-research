"""A7 SIGReg cost on CPU: forward+backward of the le-wm SIGReg class (extracted with ast from
sources/lucas-maes_le-wm/module.py @8edfeb3, L10-36; not reimplemented) on z of shape (T, N, D).
Also cross-checks the value against galilai-group/lejepa EppsPulley with the same directions.
Usage: python3 -I bench_sigreg.py --threads N --out FILE.jsonl
"""
import argparse, ast, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a7common import pin_threads, env_info, timeit, peak_rss_mb, Out

ap = argparse.ArgumentParser()
ap.add_argument("--threads", type=int, required=True)
ap.add_argument("--out", required=True)
args = ap.parse_args()
torch = pin_threads(args.threads)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LEWM = os.path.join(ROOT, "sources", "lucas-maes_le-wm", "module.py")
src = open(LEWM).read()
node = [n for n in ast.parse(src).body if isinstance(n, ast.ClassDef) and n.name == "SIGReg"][0]
ns = {"torch": torch}
exec(compile(ast.Module(body=[node], type_ignores=[]), LEWM, "exec"), ns)
SIGReg = ns["SIGReg"]
out = Out(args.out)
out.w({"kind": "env", "threads": args.threads, **env_info(args.threads), "sigreg_src": LEWM})

# value cross-check against lejepa (same directions)
try:
    sys.path.insert(0, os.path.join(ROOT, "sources", "galilai-group_lejepa"))
    import lejepa
    torch.manual_seed(0)
    x = torch.randn(1, 256, 192)
    s = SIGReg()
    torch.manual_seed(1); v1 = s(x).item()
    torch.manual_seed(1); Am = torch.randn(192, 1024); Am = Am / Am.norm(p=2, dim=0)
    v2 = lejepa.univariate.EppsPulley(n_points=17)(x @ Am).mean().item()
    out.w({"kind": "crosscheck", "lewm": v1, "lejepa": v2, "abs_diff": abs(v1 - v2)})
except Exception as e:  # noqa
    out.w({"kind": "crosscheck", "error": repr(e)})

# Configs kept small: x_t has T*N*M*17 floats (T=5,N=256,M=1024 -> ~1.1 GB peak RSS in the smoke run, above the
# 1 GB cap), so N*T is capped at 640 here.
for T, N, D, M in ((5, 64, 192, 1024), (5, 128, 192, 1024), (1, 128, 192, 1024), (1, 512, 192, 1024),
                   (5, 128, 192, 256), (5, 128, 192, 512), (5, 128, 64, 1024)):
    s = SIGReg(knots=17, num_proj=M)
    z = torch.randn(T, N, D, requires_grad=True)

    def fb():
        z.grad = None
        s(z).backward()

    st = timeit(fb, min_time=0.5)
    out.w({"kind": "sigreg_fb", "T": T, "N": N, "D": D, "M": M, "knots": 17, **st, "peak_rss_mb": peak_rss_mb()})
out.w({"kind": "end", "peak_rss_mb": peak_rss_mb(), "loadavg_end": open("/proc/loadavg").read().strip()})
