# melee-world-model-research

Investigación: ¿aporta valor medible un modelo del mundo aprendido (JEPA / LeJEPA / LeWorldModel) a un agente de
Super Smash Bros. Melee frente a imitación, RL sin dinámica explícita y búsqueda con el simulador existente?

Estado (2026-11-19): fase de investigación cerrada; etapa E0 (datos reales en CPU) hecha en parte. Nada se ha
ejecutado en el juego (sin ISO ni GPU).

**Para continuar el trabajo: lee [`HECHO.md`](HECHO.md) y después [`PENDIENTE.md`](PENDIENTE.md).**

Empieza por `deliverables/FINAL_RECOMMENDATION.md`; la decisión razonada está en `decision/DECISION.md` y sus correcciones en `deliverables/CRITICAL_REVIEW.md` §7.

| Ruta | Contenido |
|---|---|
| `handoff/melee_swarm/` | Paquete de encargo original (prompt maestro, dossier, catálogo de fuentes, protocolo). |
| `swarm/` | Brief común y organización del swarm de agentes. |
| `deliverables/` | Los ocho entregables consolidados (auditoría, mapa, baselines, diseño, plan, crítica, recomendación, evidencia). |
| `decision/` | Brainstorming (defensor, escéptico, pragmático) y decisión. |
| `evidence/A1…A8/` | Informes y evidencias por rol. |
| `ops/` | Inventario de clones/revisiones y script que construye `EVIDENCE.jsonl`. |
| `pilot/` | Código de la etapa E0: tubería de datos (`e0/`), latencia y envoltorio de plazo (`e0_timing/`), banco de A7 (`a7_bench/`). |

Las fuentes externas se clonan en `sources/` (no versionado); sus revisiones están en `ops/clone_inventory.txt`.
