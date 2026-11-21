# Preregistro de E1 (SELLADO 2026-11-21)

2026-11-21. Fuente de verdad: `preregistration.json` y `eval_schedule.csv` (42 evaluaciones). Este texto los
resume. Origen de cada umbral: **DEC** (DECISION §3), **E0** (medido en E0), **SOTA** (research/sota_2611),
**PROP** (propuesta nueva de este borrador). Ninguna cifra sale de un entrenamiento de E1.

## Regla de efecto (para todas las puertas)

Una comparación cuenta si: (1) |Δ̄| > 2·max(sd entre semillas en E1, sd de referencia de E0) **[DEC + E0]**;
(2) el IC bootstrap por partida (10.000 réplicas) excluye 0 **[DEC]**; (3) supera la mejora relativa mínima de la
puerta. En acierto, la mejora relativa es la reducción del error (1 − acierto), como en FLOORS_REPORT.
sd de referencia de E0: acción en eventos 0,0060 (h=4) y 0,0068 (h=8); NLL total de q 0,0062 (h=7) y 0,0068 (h=13);
0,005 donde E0 no midió nada **[PROP]**. Deciden las puertas los resultados en `I_full`. `I_human` (sin ningún
mando del rival en la historia) se evalúa con los mismos umbrales y se publica como veredicto aparte.

## Puertas

| Puerta | Métrica decisora (test) | Pasa si | Mín. relativo | Semillas |
|---|---|---|---|---|
| **G1-dyn** | acierto de `action` en eventos; u^yo reales, u^riv de q (K=8) | cuenta a h=4 **y** h=8 frente al mejor suelo y al control barajado | 10 % **[DEC]** | 5 |
| **G1-q** | (i) NLL total del mando del rival frente a la marginal; (ii) acierto de la acción del rival en cambios de acción, W0-S + q | cuentan las 4: (i) y (ii) a h = 7 y 13 (D = 6, 12) | 5 % **[PROP]** | 5 |
| **G1-jepa** | cabeza idéntica sobre E1 (W1-L congelado) frente a E1-S (W0-S): NLL de BC, NLL de q, MSE de V̂ | E1 gana en ≥ 2 de 3 tareas, IC 98,33 % | 2 % **[PROP]** | 5 |
| **G1-rep** | NLL de BC: E1 o E1-S frente a E0b (igual cómputo) al 10 y al 100 % | cuenta al menos 1 de 4, IC 98,75 % | 2 % **[PROP]** | 3 |
| **E1b** | transiciones/s de π0 + W0-S en GPU (mediana de ≥ 5 repeticiones) | ≥ 63.370 (10 × 6.337) **[DEC]** | — | — |

- **Variante de G1-dyn** **[SOTA + PROP]**: el predictor directo multihorizonte (W0-S-anc, Fast-JEPA) compite con el
  AR solo en val (3 semillas). Decide anc solo si supera al AR en más de 2σ; si gana, se le entrenan 2 semillas más
  antes de abrir test. La otra variante es exploratoria.
- **Sonda de colapso y SADL** **[SOTA]**: f_H, erank, coseno medio y clase N/O/D/C sobre 4.096 frames fijos de val.
  En la calibración E1-P, si alguna de 3 semillas de W1-L acaba con f_H < 0,5, todo W1-L lleva SADL. Si en E1 algún
  W1-L final tiene f_H < 0,5, G1-jepa es "inválida para esta receta", no negativa.
- **Diagnóstico de residuo** **[SOTA]**: en val, tras congelar, con un margen del 1 %. Solo distingue "falta de
  ajuste" de "límite de información"; no cambia ningún veredicto.

## Datos y split

- Fox ditto de `melee-ranked-replays@ef54ddc2`: diamond a1–a4, master a1–a2 y platinum a1; seis escenarios con
  `stage_id`, BF/FD como subconjunto aparte. Vocabularios de E0 congelados.
- **D-3 resuelta** **[EXPERIMENT_PLAN §5.3 + PROP]**: split `A6-split-v1-E1` (bucket por sha1; train < 0,606,
  val < 0,697, test el resto; ya está en `splits.py`). Mínimos **[DEC]**: 2.000 / 300 / 1.000 partidas. Las 12
  partidas de val de E0 caen en test de E1 y se inspeccionaron, así que se excluyen del análisis confirmatorio.
  Las 66 de E0 que caen en test (12 + 54 de train) se quitan en un análisis de sensibilidad.
- **Si faltan partidas** **[PROP]**: los umbrales no se tocan. Se añaden tarballs en un orden fijado, hasta 150 GB
  leídos. Si aun así faltan, E1 se ejecuta con la etiqueta "corpus reducido" siempre que haya ≥ 1.500 / 200 / 600
  partidas. Por debajo, no se abre test.

## Configuración fijada

- H = 16. Encoder de 1,0–1,5 M de parámetros. W0-S y W1-L dentro de ±10 % de parámetros.
- Batch 1024. FP32 con TF32 apagado. Atención SDPA **MATH** fijada (Flash solo como diagnóstico).
- AdamW con OneCycle, pico de lr 1e-3. 50 M de muestras por modelo de puerta y 10 M por cabeza. Checkpoint por pérdida
  de entrenamiento en val. **[PROP; precisión y atención por SOTA]**
- **Cómputo** **[PROP]**: 0 €. Tope duro de **80 h-GPU** para E1 + E1b (estimación sin medir: 45–55 h), revisión
  a las 60 h. E1-P mide el rendimiento y, si el plan no cabe en 70 h, aplica recortes en un orden fijado: primero el
  30 %, después anc, después 30 M de muestras y por último BF16 en todos los brazos por igual. Nunca baja las
  semillas de las puertas.
- **Parada**: falla una puerta de fuga o adaptador; se llega a 80 h-GPU (solo se analizan las puertas completas);
  más de 2 semillas divergidas (brazo inválido); test abierto (no se ajusta nada más).

## D-7 resuelta [PROP]

En E3, **a** y **b0** se juegan con **5 tripletas independientes** (π0_i, W0-S_i, q_i) salidas de E1, 200 partidas
cada una, igual que **c** con 5 semillas × 200. Así HP-2 compara receta con receta a nivel de semilla, y HP-1 se
empareja dentro de cada tripleta. En E1 cuesta solo subir π0 (BC E0 al 100 %) de 3 a 5 semillas. El cómputo de c_i
se iguala a los FLOPs de la tripleta i (`flops.json`). Se descarta "HP-2 solo para el checkpoint de b": dejaría un
contraste asimétrico con un 26 % de falsos positivos por pseudorreplicación.

## Decisiones del usuario (resueltas el 2026-11-21: se aceptan los valores por defecto de las seis)

1. **Mínimos relativos nuevos** (5 % en G1-q; 2 % en G1-jepa y G1-rep). DECISION no los fija.
2. **G1-q (ii)**: ¿se mide la *acción* del rival predicha con W0-S + q (lectura de FLOORS_REPORT, la que se
   adopta) o el *mando* del rival (queda como secundaria)?
3. **G1-rep**: ¿basta con que gane 1 de las 4 comparaciones, con el preentrenamiento sobre la misma fracción?
4. **Seis escenarios frente a solo BF/FD**, como dice DECISION §2.
5. **Tope de 80 h-GPU** y la política de corpus corto (mínimos de 1.500 / 200 / 600).
6. **D-7** sube a y b0 de E3 a 1.000 partidas por brazo (5 × 200).

Sellado (hecho el 2026-11-21, con la aprobación del usuario): `sha256sum deliverables/EXPERIMENT_PLAN.md evidence/E1/preregistration.json
evidence/E1/eval_schedule.csv > evidence/E1/preregistration.sha256`.
