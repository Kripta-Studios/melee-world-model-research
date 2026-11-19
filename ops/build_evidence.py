"""Concatena evidence/A*/claims.jsonl en deliverables/EVIDENCE.jsonl y valida contra el esquema."""
import json, pathlib, sys, collections
root = pathlib.Path(__file__).resolve().parent.parent
schema = json.loads((root / "handoff/melee_swarm/08_EVIDENCE_SCHEMA.json").read_text())
try:
    import jsonschema
    validator = jsonschema.Draft202012Validator(schema)
except Exception as e:  # sin jsonschema: solo se comprueban campos requeridos
    validator = None
    print("jsonschema no disponible:", e)
out, seen, bad, per = [], set(), 0, collections.Counter()
for f in sorted(root.glob("evidence/A*/claims.jsonl")):
    for n, line in enumerate(f.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        errs = [e.message for e in validator.iter_errors(row)] if validator else [k for k in schema.get("required", []) if k not in row]
        key = row.get("claim_id") or row.get("id")
        if key in seen:
            errs.append("id duplicado")
        seen.add(key)
        if errs:
            bad += 1
            print(f"{f.relative_to(root)}:{n} {key}: {errs[:2]}")
        per[f.parent.name] += 1
        out.append(json.dumps(row, ensure_ascii=False))
(root / "deliverables/EVIDENCE.jsonl").write_text("\n".join(out) + "\n")
print(dict(per), "total", len(out), "invalidas", bad)
sys.exit(1 if bad else 0)
