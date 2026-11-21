"""Aggregate E0 timing runs -> evidence/E0/timing/{timing.jsonl (sample), timing_summary.json,
latency_summary.json, latency_summary.md}.  Usage: python3 -I summarize_timing.py [RAW_DIR]"""
import json, os, statistics as stt, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.join(HERE, "..", "..", "evidence", "E0", "timing")
RAW = sys.argv[1] if len(sys.argv) > 1 else "/srv/mail/melee-research-data/e0_timing_raw"
BUDGET = 10.0


def pct(xs, q):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def r3(x):
    return None if x is None else round(x, 3)


def across(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None
    return {"median": r3(stt.median(v)), "min": r3(min(v)), "max": r3(max(v)), "n_reps": len(v)}


def read_runs(path):
    runs, cur = [], None
    if not os.path.exists(path):
        return runs
    for line in open(path):
        r = json.loads(line)
        if r["kind"] == "run":
            cur = {"hdr": r, "dec": []}; runs.append(cur)
        else:
            cur["dec"].append(r)
    return runs


def run_stats(run):
    d, h = run["dec"], run["hdr"]
    lat = [r["latency_ms"] for r in d]
    ontime = [r for r in d if r["fallback_used"] == "none"]
    fb = Counter(r["fallback_used"] for r in d)
    late = h["frame_lateness_ms"]
    def _f(v):  # Windows no tiene loadavg (portable.loadavg da "win ..."): se registra como NaN
        try:
            return float(v)
        except ValueError:
            return float("nan")
    loads = [_f(x[1]) for x in h["loadavg_samples"]] or [_f(h["loadavg_start"].split()[0])]
    return {
        "n": len(d),
        "latency_p50_ms": pct(lat, .5), "latency_p95_ms": pct(lat, .95), "latency_p99_ms": pct(lat, .99),
        "latency_max_ms": max(lat),
        "compute_p50_ms": pct([r["compute_ms"] for r in d], .5), "compute_p99_ms": pct([r["compute_ms"] for r in d], .99),
        "missed_pct": 100 * sum(r["deadline_missed"] for r in d) / len(d),
        "fallback_pct": {k: 100 * v / len(d) for k, v in fb.items()},
        "overrun_p99_ms": pct([max(0, r["overrun_ms"]) for r in d], .99), "overrun_max_ms": max(r["overrun_ms"] for r in d),
        "overrun_gt1ms_pct": 100 * sum(r["overrun_ms"] > 1.0 for r in d) / len(d),
        "wrapper_overhead_p50_ms": pct([r["wrapper_overhead_ms"] for r in ontime], .5),
        "wrapper_overhead_p99_ms": pct([r["wrapper_overhead_ms"] for r in ontime], .99),
        "begin_cost_p99_ms": pct([r.get("begin_cost_ns", 0) / 1e6 for r in d], .99),
        "agent_section_p99_ms": pct(h["agent_section_ms"], .99), "agent_section_max_ms": max(h["agent_section_ms"]),
        "frame_late_gt1ms_pct": 100 * sum(x > 1.0 for x in late) / len(late), "frame_late_max_ms": max(late),
        "load1_min": min(loads), "load1_max": max(loads),
    }


def summarize_runs(runs):
    groups = defaultdict(list)
    for run in runs:
        h = run["hdr"]
        groups[(h["agent"], h["mode"], h["switch_ms"])].append(run)
    out = {}
    for key, rs in sorted(groups.items(), key=lambda kv: str(kv[0])):
        per = [run_stats(r) for r in rs]
        agg = {}
        for k in per[0]:
            if k == "fallback_pct":
                ks = set().union(*[p[k] for p in per])
                agg[k] = {f: across([p[k].get(f, 0.0) for p in per]) for f in sorted(ks)}
            else:
                agg[k] = across([p[k] for p in per])
        out["|".join(str(x) for x in key)] = {"agent": key[0], "mode": key[1], "switch_ms": key[2],
                                              "budget_ms": rs[0]["hdr"]["budget_ms"], "frames_per_rep": rs[0]["hdr"]["frames"],
                                              **agg}
    return out


def sample(runs, f, per_cfg_first=60, per_cfg_missed=40):
    seen = set()
    for run in runs:
        h = run["hdr"]
        key = (h["agent"], h["mode"], h["switch_ms"])
        if key in seen:
            continue
        seen.add(key)
        hdr = {k: v for k, v in h.items() if k not in ("frame_lateness_ms", "agent_section_ms")}
        f.write(json.dumps(hdr) + "\n")
        d = run["dec"]
        pick = d[:per_cfg_first] + [r for r in d[per_cfg_first:] if r["deadline_missed"]][:per_cfg_missed]
        for r in pick:
            f.write(json.dumps(r) + "\n")


def main():
    os.makedirs(EV, exist_ok=True)
    wr = read_runs(os.path.join(RAW, "wrapper.jsonl"))
    e2e = read_runs(os.path.join(RAW, "e2e.jsonl"))
    with open(os.path.join(EV, "timing.jsonl"), "w") as f:
        sample(wr, f); sample(e2e, f)
    ws, es = summarize_runs(wr), summarize_runs(e2e)
    json.dump({"note": "RT-strict wrapper in a fake 60 Hz blocking loop; per-config stats are per-rep values "
                       "aggregated as median [min,max] across reps. Raw traces: " + RAW,
               "wrapper": ws, "e2e_present_in_wrapper": es},
              open(os.path.join(EV, "timing_summary.json"), "w"), indent=1)

    # ------------------------------------------------------------------ present-predictor bench
    pres = defaultdict(list); comps = defaultdict(list); pi0 = defaultdict(list); envs = []
    p = os.path.join(EV, "present_raw.jsonl")
    for line in open(p) if os.path.exists(p) else []:
        r = json.loads(line)
        if r["kind"] == "present":
            pres[(r["core"], r["impl"], r["threads"], r["D"], r["q"])].append(r)
        elif r["kind"] == "components":
            comps[(r["core"], r["impl"], r["threads"])].append(r)
        elif r["kind"] == "pi0_aged":
            pi0[(r["core"], r["impl"], r["threads"])].append(r)
        elif r["kind"] == "env":
            envs.append({k: r[k] for k in ("core", "impl", "threads", "rep", "uptime", "loadavg", "mem_available_mb", "params", "torch_threads")})
    zero_thr = ws.get("zero|thread|None", {})
    ovh = (zero_thr.get("wrapper_overhead_p99_ms") or {}).get("max")
    rows = []
    for (core, impl, th, D, q), rs in sorted(pres.items()):
        p99s = [r["p99_ms"] for r in rs]
        row = {"core": core, "impl": impl, "threads": th, "D": D, "q": q, "steps": rs[0]["steps"],
               "n_per_rep": rs[0]["n"], "p50_ms": across([r["p50_ms"] for r in rs]), "p95_ms": across([r["p95_ms"] for r in rs]),
               "p99_ms": across(p99s),
               "stages_p50_ms": {k: r3(stt.median([r["stages_p50"][k] for r in rs])) for k in rs[0]["stages_p50"]},
               "loadavg_at_end": [r["loadavg"].split()[0] for r in rs], "peak_rss_mb_max": r3(max(r["peak_rss_mb"] for r in rs)),
               "truncated": any(r["truncated"] for r in rs)}
        row["route_p99_ms_worst_rep"] = r3(max(p99s) + (ovh or 0))
        row["route_p99_ms_best_rep"] = r3(min(p99s) + (ovh or 0))
        row["fits_10ms_p99"] = ("SI" if row["route_p99_ms_worst_rep"] <= BUDGET else
                                "NO" if row["route_p99_ms_best_rep"] > BUDGET else "LIMITE")
        rows.append(row)
    comp_sum = {"|".join(map(str, k)): {c: {"p50_us": across([r[c]["p50_us"] for r in v]), "p99_us": across([r[c]["p99_us"] for r in v])}
                                        for c in v[0] if isinstance(v[0][c], dict)} for k, v in sorted(comps.items())}
    pi0_sum = {"|".join(map(str, k)): {"p50_ms": across([r["p50_ms"] for r in v]), "p99_ms": across([r["p99_ms"] for r in v])}
               for k, v in sorted(pi0.items())}
    jit = []
    jp = os.path.join(EV, "jit_probe.jsonl")
    for line in open(jp) if os.path.exists(jp) else []:
        jit.append(json.loads(line))
    jit_sum = defaultdict(list)
    for r in jit:
        jit_sum[f'{r["core"]}|{r["threads"]}'].append(r)
    jit_sum = {k: {"eager_step_p50_us": across([r["eager"]["p50_us"] for r in v]), "jit_step_p50_us": across([r["compiled"]["p50_us"] for r in v]),
                   "eager_step_p99_us": across([r["eager"]["p99_us"] for r in v]), "jit_step_p99_us": across([r["compiled"]["p99_us"] for r in v])}
               for k, v in sorted(jit_sum.items())}
    summary = {"budget_ms": BUDGET, "K": 4, "H": 16,
               "wrapper_overhead_p99_ms_added": ovh,
               "wrapper_overhead_source": "max over reps of p99 wrapper overhead, zero-latency agent, thread backend (timing_summary.json)",
               "verdict_rule": "route = predictor+pi0 p99 (in-process) + wrapper overhead p99; SI if worst rep <= 10 ms, NO if best rep > 10 ms, else LIMITE",
               "rows": rows, "components_one_step": comp_sum, "pi0_aged_obs": pi0_sum, "jit_probe_closed_loop_step": jit_sum,
               "e2e_in_wrapper": {k: {kk: v[kk] for kk in ("latency_p99_ms", "compute_p50_ms", "compute_p99_ms", "missed_pct", "fallback_pct", "overrun_max_ms", "load1_max")}
                                  for k, v in es.items()},
               "env_per_run": envs}
    json.dump(summary, open(os.path.join(EV, "latency_summary.json"), "w"), indent=1)

    f = lambda a: "—" if a is None else f'{a["median"]:.1f} [{a["min"]:.1f}–{a["max"]:.1f}]'
    L = ["# E0 · Latencia de \"predecir el presente\" (pesos aleatorios) — tabla generada por `summarize_timing.py`", "",
         f"K = 4, H = 16, presupuesto 10 ms p99. Celdas: mediana [mín–máx] entre las repeticiones DISPONIBLES (n_reps en latency_summary.json; en la corrida del 2026-11-19 solo hubo 1, a 1 hilo: la campaña se cortó por falta de memoria del host) del percentil de cada repetición; "
         f"ruta = p99 del predictor+π0 (en proceso) + overhead p99 del envoltorio ({"NO MEDIDO en campaña, no sumado" if ovh is None else str(round(ovh, 3)) + " ms"}). "
         "Veredicto: SI si la peor repetición cabe, NO si ni la mejor cabe, LIMITE en otro caso.", "",
         "| núcleo | impl | hilos | D | q | pasos | p50 ms | p95 ms | p99 ms | ruta p99 (peor rep) | ¿cabe 10 ms p99? |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f'| {r["core"]} | {r["impl"]} | {r["threads"]} | {r["D"]} | {r["q"]} | {r["steps"]} | {f(r["p50_ms"])} | '
                 f'{f(r["p95_ms"])} | {f(r["p99_ms"])} | {r["route_p99_ms_worst_rep"]:.1f} | {r["fits_10ms_p99"]} |')
    L += ["", "Etapas (p50 ms, mediana entre reps): featurize / encode / rollout / π0", ""]
    L += ["| núcleo | impl | hilos | D | q | featurize | encode | rollout | π0 |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        s = r["stages_p50_ms"]
        L.append(f'| {r["core"]} | {r["impl"]} | {r["threads"]} | {r["D"]} | {r["q"]} | {s["featurize_ms"]} | {s["encode_ms"]} | {s["rollout_ms"]} | {s["pi0_ms"]} |')
    open(os.path.join(EV, "latency_summary.md"), "w").write("\n".join(L) + "\n")
    print(f"wrapper cfgs={len(ws)} e2e cfgs={len(es)} present rows={len(rows)} jit={len(jit)}")


if __name__ == "__main__":
    main()
