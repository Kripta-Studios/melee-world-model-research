# Sondas de latencia en el PC (2026-11-21): exploratorias, no sustituyen al banco completo

Máquina: `evidence/E1/hardware.json`. Pesos aleatorios, `--impl fast`, K = 4, H = 16, 60 decisiones por
configuración, 1 repetición. Comandos:

```bash
PY=<python con torch 2.10>
cd pilot/e0_timing
$PY -X utf8 -I bench_present.py --core gru --threads 1 --impl fast --mode direct  --n 60 --Ds 6,12,18 --out direct_gru_fast_cpu1.jsonl
$PY -X utf8 -I bench_present.py --core gru --threads 1 --impl fast --mode rollout --n 60 --Ds 6,12,18 --out rollout_gru_fast_cpu1.jsonl
$PY -X utf8 -I bench_present.py --core {gru,tx_kv} --threads 1 --impl fast --device cuda --n 60 --Ds 6,12,18 --out rollout_cuda_gru_txkv.jsonl
```

## Aviso: los valores absolutos de CPU no son válidos

Durante la sesión, la CPU rindió muy por debajo de su capacidad. Un bucle de Python puro de 5 M iteraciones tardaba
1,3–2,6 s, cuando en un Zen 5 se esperan unos 0,3 s (INF). WMI informa de 2.500 MHz con el plan "Equilibrado"; la
causa probable es el perfil de energía del fabricante (INF, sin verificar). El mismo `gru fast` con D=6 en lazo abierto
dio **157 ms** aquí y **13 ms** en el servidor (`../TIMING_REPORT.md`). Solo valen las **razones entre variantes**
medidas en la misma sesión.

## Resultado 1 (REP): predictor directo (P1 de Fast-JEPA) frente a rollout, CPU, 1 hilo

| D | rollout, q abierto, p50 / p99 ms | rollout, q cerrado, p50 / p99 ms | directo, p50 / p99 ms | razón frente a abierto / cerrado |
|---|---|---|---|---|
| 6 | 156,8 / 180,1 | 213,2 / 236,7 | 68,7 / 85,0 | 2,3× / 3,1× |
| 12 | 240,1 / 274,3 | 347,0 / 423,6 | 66,0 / 73,5 | 3,6× / 5,3× |
| 18 | 329,0 / 358,9 | 476,4 / 510,8 | 67,4 / 75,0 | 4,9× / 7,1× |

- El coste del directo **no depende de D**: es una sola pasada (REP).
- Aplicando la misma razón a la mediana del servidor (13 ms con D=6, en lazo abierto), el directo quedaría en unos
  5–6 ms (INF). Por debajo de 10 ms p99 en CPU, solo si la cola no se dispara; hay que medirlo con la CPU a pleno
  rendimiento.
- Es **solo coste**. Que el directo prediga tan bien como el rollout es la pregunta del brazo P2 de G1-dyn (ver
  `research/sota_2611/SYNTHESIS.md`). Además, la ventana de pi0 en el directo no incluye los frames imaginados
  intermedios.

## Resultado 2 (REP): ruta GPU, K = 4

Con batch 4, la GPU es **más lenta que la CPU** en la misma sesión: `gru` con D=6 en lazo abierto da 211 ms de
mediana. El rollout son cientos de kernels diminutos, y lo limita el coste de lanzarlos desde una CPU lenta (INF).
**PROPUESTA:** en GPU, capturar un paso con CUDA Graphs o usar `torch.compile(mode="reduce-overhead")` antes de
concluir nada. Para el predictor del presente con K pequeño, lo razonable es la CPU o el directo.
