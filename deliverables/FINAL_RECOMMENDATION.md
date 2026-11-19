# FINAL_RECOMMENDATION

Integrador · 2026-11-19 · Fuente de verdad: `decision/DECISION.md`. Detalle: `DESIGN.md`, `EXPERIMENT_PLAN.md`,
`CRITICAL_REVIEW.md` (en esta carpeta).

## Respuesta a la pregunta central

**¿Aporta valor medible a Melee un modelo del mundo aprendido (JEPA / LeWorldModel)? Hoy no se sabe.** Nadie ha
medido fuerza de juego, y la evidencia previa en Melee es débil en ambos sentidos.

- **No se construye ahora un MPC con dinámica aprendida**, pero tampoco se descarta.
- **MVP: un predictor del presente bajo demora.**
  - Modelo conjunto dinámica + rival: W0-S estructurado y q con K = 4 hipótesis; un gemelo latente LeWM-like
    (W1-L) como ablación.
  - El presente predicho alimenta una política BC a 0 frames.
  - Se compara con el control que lo puede matar: la misma política entrenada con la demora, a igual cómputo.
- **Las dos primeras etapas (E0, E1) cuestan ≤ 35 €** y no necesitan ISO. La búsqueda exacta con el simulador
  (S0-ceiling, E4) es una segunda línea, posterior, con ≥ 400 partidas por brazo.
- **Solo es "JEPA" W1-L.** Si no bate a W0-S, lo que sobreviva se llamará "modelo predictivo aprendido".

## Reutilizar · construir · descartar

**Reutilizar** (revisiones en DECISION §4):
- melee-llm: `Agent`, `ConsoleTap`, el patrón `budget_ms` y el runner (sin LICENSE).
- melee-brute: `checkpoint/rollback`, `bench` y `validate_replay.py` (sin LICENSE; fijar una sola revisión).
- le-wm (MIT): `SIGReg`, `ARPredictor` y la pérdida.
- slippi-ai (MIT): la receta de demora y la recompensa.
- MIMIC (MIT): el bucle BC.
- `melee-ranked-replays@ef54ddc2`, carpeta FOX.
- Faynt, solo como referencia externa.
- `power.py`, `split_plan.json` y `timing_contract.json`.

**Construir:**
- un parser `.slp` → esquema A6, con test de fuga;
- W0-S, W1-L, q y V̂;
- π0 (BC a 0 frames) y π_delay;
- `PresentPredictorAgent`;
- el envoltorio `RT-strict` con trazas;
- un bootstrap jerárquico.

Más adelante: el paso del `World` (E4) y la API de semilla por frame (E5).

**Descartar:**
- píxeles y pesos JEPA publicados;
- JEPA no temporal con aumentos;
- `lejepa`, `ijepa` y `jepa-wms` (CC BY-NC);
- HAL MDS para dinámica;
- entrenar aquí más que humo;
- MPC aprendido antes de E4, y W2 antes de E1b;
- PPO propio ahora;
- una sombra alimentada desde `GameState`;
- CPU-9 como ancla.

## Próximos pasos (ordenados)

1. **El usuario responde a la decisión n.º 1** (venv + ≤ 1 GB de replays). Mientras tanto, sin permiso:
2. **Envoltorio de plazo con un agente sintético**, en un bucle falso que imite `runner.play` L279-300.
   → `timing.jsonl` con los campos de 06, p50/p95/p99 y plazos perdidos.
3. **Banco de latencia extendido** (`bash pilot/a7_bench/run_all.sh infer`): W0-S real con pesos aleatorios,
   transformer con KV-cache y A con K = 4, D ∈ {6, 12, 18}, con q en lazo abierto y cerrado.
   → `summary.json` que confirma o refuta "cabe en 10 ms p99" (CRITICAL_REVIEW D-2).
4. **Con permiso**: `python3 -m venv <2º disco>/venv-e0 && <venv>/bin/pip install peppi-py zstandard`. Después,
   descargar tarballs sueltas de `FOX/` de `erickfm/melee-ranked-replays` (revisión `ef54ddc2`, ≤ 1 GB).
   → ≥ 150 Fox dittos con sha1.
5. **Parser al esquema A6.** → `dataset_card.json` con la cobertura de campos por versión. Gate: ≥ 95 % de partidas
   con velocidades, hitstun y `action_state_frame`.
6. **Split y deduplicación por sha1**, más el test de fuga de alineación (objetivo = mando de f+1).
   → `splits.jsonl` y `adapter_checks.jsonl`.
7. **Suelos triviales por campo y h, humo ≤ 1M y 3 corridas** para estimar la varianza.
   → `model_diagnostics.csv`.
8. **Sellar el preregistro** (`sha256sum EXPERIMENT_PLAN.md preregistration.json eval_schedule.csv`), con los umbrales
   de bucket de E1 y la decisión D-7.
9. **E1 + E1b en GPU alquilada**, con parada dura a 35 €. → tabla G1-dyn / G1-q / G1-jepa / G1-rep y transiciones/s
   frente a 6.337.
10. **Si G1-q pasa: pedir la ISO.** Correr E2 (`python -m melee_brute bench`, panel de regret, `validate_replay.py`
    frente a `parity.py`) y E3 (≥ 400 partidas por brazo; c con 5 × 200).
11. **E4** con el cambio en `sim/runner.py` L47-53. E5 y E6 solo si sus disparadores se cumplen.

## Decisiones del usuario (valor por defecto si no responde)

| # | Decisión | Por defecto |
|---|---|---|
| 1 | venv con `peppi_py`/`zstandard` y ≤ 1 GB de replays aquí (≤ 2 hilos, prioridad baja) | se planifica con "sí", pero no se instala sin confirmación; si es "no", E0 va a la instancia alquilada (+2–4 €) |
| 2 | Techo de gasto en GPU | 35 € (E1 + E1b), parada dura |
| 3 | ISO NTSC 1.02 propia y dónde reside | no se pide hasta pasar G1; después, solo en máquina propia |
| 4 | ¿Importa el régimen con demora (6–18 frames)? | sí, como eje secundario; si es "no", tras G1 se pasa a E4 |
| 5 | ¿Responder la pregunta o publicar un entrante? | responder la pregunta |
| 6 | Cambios en melee-llm (`World`, semilla) y en melee-brute (API de semilla) | melee-llm sí al llegar a E4; melee-brute no hasta que E2 lo justifique |
| 7 | Datos: solo `melee-ranked-replays`, sin HAL MDS | sí |
| 8 (int.) | Para cerrar líneas con "sin efecto", ¿525 partidas por brazo en lugar de 400? | 400, aceptando que muchos "sin efecto" saldrán inconclusos |

## Recorrido de `10_COMPLETION_CHECKLIST.md`

**Fuentes y revisiones**
1. URL canónica y fecha: **cumplido**. `SOURCE_AUDIT.md` y `accessed_at` en las 240 claims.
2. Revisión y licencia de los repositorios reutilizados: **cumplido**. Tienen SHA completo; los que no tienen
   LICENSE están señalados.
3. HEAD / dependencia / instalada / medida: **parcial**. Están separadas para melee-llm, melee-brute y libmelee. La
   revisión "medida" no existe (no se ejecutó nada) y la de `MELEE_SIM` de la granja es desconocida.
4. Pesos y datos con identidad y condiciones: **parcial**. Faynt-10M-Expert, lewm y LeVJEPA no tienen SHA; los
   derechos del origen del corpus son DESC.
5. Cifras publicadas atribuidas: **cumplido**.

**Sistema y diseño**
6. Mapa de observación, política, mandos, motor, tiempos y resultados: **cumplido** (`evidence/A1/SYSTEM_MAP.md`,
   A6). El frame de aplicación en Dolphin es DESC.
7. Símbolos reales de integración: **cumplido** (`Agent.begin/step`, `KINDS`, `registry()`, `ConsoleTap`, `sim/runner.py`
   L47-53). Algunos localizadores de A1 eran falsos y se corrigieron.
8. Encoder, dinámica, valor, política y búsqueda definidos por separado: **cumplido** (DESIGN §3–5).
9. Alternativas, incluida la de no usar un modelo aprendido: **cumplido** (B, brazo c, P0-Q, B0/B1).
10. Robótica y vídeo no presentados como adaptados: **cumplido**.
11. Rival en entrenamiento e inferencia: **cumplido** (DESIGN §2.3).

**Protocolo**
12. Split por partida antes de ventanas, con duplicados: **cumplido en diseño**, sin ejecutar. Las proporciones
    están corregidas (D-3).
13. El test no interviene en la selección: **cumplido en diseño**.
14. Información y demoras comparables o reportadas por separado: **cumplido en diseño**.
15. El control de representación no usa dinámica en inferencia: **cumplido en diseño** (conteo de parámetros del
    forward).
16. Control sin rollouts comparable: **cumplido en diseño** (P0-Q; en A, brazos a y c).
17. Referencia de dinámica estructurada: **cumplido** (W0-S; S0 exacta).
18. Error de predicción acompañado de rendimiento en bucle cerrado: **cumplido en diseño** (E3, E4). Ningún
    resultado existe.
19. Semillas de entrenamiento frente a partidas: **cumplido**. Queda abierta la asimetría D-7.
20. Métricas, tamaño y diferencia mínima fijados antes del test: **parcial**. Están fijados 10 pp, ≥ 400 partidas y
    5 semillas. El tamaño del margen de stocks, σ_s y los umbrales de G1 dependen del piloto, y el preregistro no se
    ha sellado.
21. Coste completo hasta aplicar el mando, con percentiles y fallos: **parcial**. Solo hay proxies de torch sin
    Dolphin; el envoltorio no existe y el frame de aplicación no está medido.

**Viabilidad y entrega**
22. Presupuesto con hardware comprobado o supuestos etiquetados: **cumplido** (A7 `budget.json`; costes HIP/EST).
23. El MVP reutiliza componentes: **cumplido**.
24. Tareas con propietarios, dependencias y salidas: **parcial**. Hay etapas con dependencias y artefactos, pero
    ningún propietario asignado (no hay equipo definido).
25. Revisión crítica que intenta refutar: **cumplido** (CRITICAL_REVIEW).
26. Siguiente paso que más reduce la incertidumbre: **cumplido**. E0 es el prerrequisito gratuito; E1/E1b es el
    primer recorte real de incertidumbre (G-02, G-07).
27. Pendiente distinguido de demostrado y de propuesto: **cumplido** (etiquetas en todos los entregables).

**Entregas obligatorias:** las ocho están en `deliverables/`. SOURCE_AUDIT, `sources.lock.json`, SYSTEM_MAP,
BASELINES y EVIDENCE.jsonl son de otro integrador; este no los revisó.
