# Brainstorm · postura ESCÉPTICA: "simulador y RL convencional primero"

Fecha: 2026-11-19 · Rol: abogado del "no construir ahora un modelo de dinámica aprendido".
Base: informes `evidence/A1`…`A7` (leídos enteros salvo A3/A4, de los que leí resumen, §5.4-5.5 y §6-8) y
`handoff/melee_swarm/01_MASTER_PROMPT.txt`, `06_EXPERIMENT_PROTOCOL.md`. No he ejecutado nada: aquí no hay ISO ni GPU.

Etiquetas: **DOC** documentado por su autor (no reproducido), **CÓD** inspeccionado en código por el agente citado,
**REP** medido localmente por el agente citado, **INF** inferencia, **PROP** propuesta, **DESC** desconocido,
**HIP** hipótesis mía sin respaldo en los informes. Lo marcado "(leído por mí)" lo comprobé directamente en
`sources/mateo19182_melee-llm` @ `7e179081c6cbab139d860c998b1452ad3dee047c` porque los informes solo lo citan de pasada.

---

## 0. Tesis

1. **El brazo S0 (búsqueda con el simulador exacto) está en el camino crítico de cualquier plan con modelo del
   mundo**, porque es su cota superior a igualdad de candidatos, modelo del rival y valor terminal
   (`A5/PLANNING.md` §0.7, §6.1, §6.3; `A4/DYNAMICS.md` §6.2 conclusión). Mi MVP es un prefijo estricto del plan
   del defensor: se construye primero en cualquier caso.
2. **Nadie ha planificado nunca con el simulador durante una partida** (`A5` §0.1, CÓD). No se sabe si la búsqueda
   *exacta* mejora a la política sola. Entrenar un modelo aproximado para hacer algo cuyo valor con el modelo
   perfecto es desconocido es invertir el orden de las incógnitas.
3. **Las tres ventajas habituales de un modelo aprendido no existen en esta plataforma**: velocidad (`A7` §0.3,
   `A4` §6.1), generación de experiencia (`A4` §6.2 fila Dreamer) y diferenciabilidad (`A4` §6.2). Queda un nicho
   estrecho (Dolphin tras la divergencia de RNG, máquinas sin ISO, abstracción temporal sin evidencia).
4. **Lo que sí es irreemplazable es aprendido pero no es dinámica**: el modelo del rival q y el valor terminal V̂
   (`A4` §6.2, `A5` §0.6, `A2` D3). Ambos se combinan igual con el simulador.
5. Mi propuesta no es "solo PPO". Es: **medir el techo de la búsqueda exacta y, si existe, destilarlo en una
   política rápida**; PPO con correa KL es el control y el plan B.

---

## 1. El caso contra construir ahora un modelo de dinámica aprendido

| # | Argumento | Evidencia | Fuerza |
|---|---|---|---|
| 1 | S0 acota a W por arriba en `--mode sim` con mismos candidatos, q y V̂. Si S0 ≤ P0, ningún W gana en ese régimen | `A5` §6.1 tabla, §6.3 ("queda falsada"), INF de A5 | Alta: es lógica, no empírica. Excepción reconocida: abstracción temporal a igual *tiempo* |
| 2 | En CPU el modelo aprendido no es más barato que el motor: MLP-1M 8,3 µs/transición, GRU-1M 9,6, TX-1M 130 frente a 12–17 µs/frame del simulador. El predictor tipo LeWM es 50–300× más lento | `A7` §0.3 y §3.2 (REP propio vs DOC en otra CPU); `A4` §6.1 (REP) | Alta en CPU. En GPU no está medido (`A7` §4.1 es estimación) |
| 3 | El coste real de un rollout no es la dinámica sino las políticas dentro del rollout (q y continuación). En la granja "the models set the pace": simulador 0,3 ms de un frame de 4–6 ms | `simulator.md` "Learned bots in it" (DOC, leído por mí); `A5` §4 (q en lazo cerrado duplica el coste de W0) | Alta. Sustituir el motor por una red no toca el cuello de botella |
| 4 | Con horizonte de 8–32 frames y semivida de 8 s, J ≈ V̂(x_T): el MPC es "V̂ compuesto con la dinámica". El componente crítico es V̂, que no existe publicado | `A5` §0.6; `A2` D3 | Alta. Un W que falle no se podrá distinguir de un V̂ malo sin S0 |
| 5 | Los predictores de estado ya probados en Melee no dieron fuerza: Firoiu 2018 solo ayudó con p=d, ignoraba al rival y rindió algo peor contra CPU; cabezas de estado de HAL "within noise" (−0,05 NSM) y sin cualificación; slippi-ai lo abandonó; ningún peso moderno usa dinámica en inferencia | `A2` §1.4; `A5` §6.2; `delay.md` §5.4 "Skip the predictive model" (DOC, opinión del autor) | Media: es ausencia de evidencia más opiniones de autor, no una refutación |
| 6 | Lo único con historial de subir fuerza en Melee es BC → PPO con correa KL: Faynt Expert 23/68 → Arena 68/68 contra un slippi-ai privado a 0 frames; MIMIC RL 279–105 contra su BC; Phillip | `A2` §2 Faynt/MIMIC, D1 (DOC, sin IC, con asimetrías de retraso en el resto de cifras) | Media: cifras de autor, no reproducidas |
| 7 | Los datos humanos no cubren las acciones que un planificador consulta, y el estado público no es Markov (mando previo, temporizadores, RNG). El motor sí da verdad contrafactual a demanda | `A6` §3.2 (botones), §7, §8; `A4` §0.1, §5.4 | Alta |
| 8 | Reacción: planificar cada 2 frames cambia el valor del juego (0 → 0,382 a 12,59 u). Una búsqueda en vivo paga en la misma moneda que quiere ganar; una política destilada no | `A5` §0.3 (DOC de `optimal-play.md`, menús y horizonte concretos) | Media: resultado para un menú, Fox ditto FD, 0 % |
| 9 | La canalización de datos que exige una dinámica "completa" (reparsear `.slp` crudo con RNG, sticks raw y `n_copies`) no existe en ningún formato derivado; HAL MDS carece de velocidades, hitstun y `action_state_frame` | `A6` §1.3-1.4, §5, §11 | Media: es coste de ingeniería, no imposibilidad |
| 10 | Entrenar aquí es inviable y en GPU el piloto W0/W1 cuesta 10–50 h de GPU con 5 semillas, más ≈10 h de Dolphin por brazo y reloj | `A7` §0.5-0.6, §5 (INF) | Baja como argumento de coste (es barato); alta como argumento de **orden**: ese gasto no reduce la incógnita principal |

Lo que este caso **no** prueba: que un modelo aprendido no sirva en Dolphin en vivo, ni que la representación
predictiva (B2/E1 de `A3` §4) no ayude a la política. Son preguntas distintas y las trato en §5-6.

---

## 2. Alternativas

Requisitos comunes a todas: **ISO NTSC 1.02** para extraer `data/` (`A1` §8), Linux con GCC (take-back solo Linux),
y una máquina que no sea esta (`A7` §0.5, §5). El autor de melee-llm documenta una RTX 3090 local y la granja
funcionando (E10, E28, E32; DOC, leído por mí); si ese hardware está disponible para este proyecto es **DESC**.

### 2.1 Alt-A · BC + PPO con correa KL sobre la granja existente (B0 → B1)

- **Mecanismo.** Partir de una política de imitación, jugar en `melee_sim` por lotes y actualizar con PPO, KL hacia
  el punto de partida, valor separado que ve el estado presente. Reutiliza `train/farm/rl.py` + `learner.py`
  (porta la receta Faynt a melee-sim-light) y `Faynt-Benchmarks/evaluation/melee_rl/` (`A2` D2).
- **A favor.** Único método con mejoras documentadas en Melee (`A2` D1, fila "RL propio"). La granja reproduce
  Dolphin en espejos (Arena vs Expert: 8/8 en Dolphin, 64/64 y 512/512 en granja) y corre a 6.337 frames/s con 8
  procesos (E28, DOC; `A2` D3). El motor reproduce 406/411 partidas de bots y 36/40 humanas con inputs y semillas
  grabados (E31, DOC; `A4` §5.4 C2').
- **En contra.** El PPO propio del usuario falló dos veces: 77 % contra el maestro en simulador que no se trasladó
  a Dolphin (E09) y caída a 31 % (E10); el autor detuvo ese pipeline (`A2` §2 "Bot propio"). E32 (receta Faynt
  sobre Yoshi) está "running", sin resultado (leído por mí). El bucle BC de Faynt no está publicado (`A2` §1.3). El
  dispositivo `cuda` está fijado en el código (`A2` D2). Faynt usó 96 Dolphins y dos runs (`A2` §2).
- **Requisitos.** ISO, GPU de 24 GB, ningún cambio en `sim/runner.play` (la granja no pasa por el runner).
- **Coste (INF).** Orden de E10: 101 M frames en 3,6 h en una 3090 con 20 M parámetros (`A2` D2, DOC). Decenas de
  horas de GPU por run; ×5 semillas si se quiere inferencia (06 §Separación).
- **Riesgo.** Explotar a un rival congelado en vez de mejorar (veredicto de E09); estrategias degeneradas (ExPhil,
  `delay.md` §3). Mitigación ya conocida: pool de rivales y correa KL (E21 planificado).
- **Lo falsa.** Con el mismo presupuesto de frames, B1 no supera a su B0 en ≥5 pp con IC95 > 0 contra rivales
  **no usados en el entrenamiento ni en la selección de checkpoint**, juzgado en Dolphin tras la corrección de
  gatillos de E30. Si falla también con la receta Faynt completa, el "RL convencional" tampoco está resuelto aquí.

### 2.2 Alt-B · S0: búsqueda en vivo con el simulador exacto + q + V̂ (`--mode sim`)

- **Mecanismo.** En cada decisión: `checkpoint` → N candidatos propios (top-1 y muestras del prior + menú de
  `fox.frame_rules()`) × K hipótesis del rival muestreadas de q → T frames de motor → `rollback` → puntuar con
  recompensa + V̂(x_T) → argmax. Especificación completa en `A5` §2 (la adopto tal cual).
- **A favor.** Primitivos existentes y exactos: `Match.checkpoint/rollback/branch/hash` a 4,4/4,5 µs,
  `EnvBatch.checkpoint/rollback` (`A1` §8, DOC/CÓD); 12–17 µs/frame (DOC). Presupuesto estimado RT-a (64 ramas ×
  8 frames) 8,3–9,3 ms en un núcleo (`A5` §1, INF sobre DOC).
- **En contra.** (i) Es un brazo **nuevo**, no una reproducción (`A5` §0.1). (ii) El agente no recibe el `World`
  (`A1` §5.2). (iii) Privilegiado: estado exacto, RNG y mando actual del rival (`A5` §5). (iv) Argmax sobre E_q
  es una estrategia pura, explotable (`A5` §3.4). (v) Depende de V̂, que hay que entrenar (`A5` §0.6). (vi) La
  búsqueda desde Python cuesta ~43 ms (`A5` §1): en tiempo real exige el camino en C o lotes.
- **Requisitos.** ISO; **cambio en `sim/runner.play` L47-53** (o `Agent.setup`) para pasar el `World`; reenviar y
  registrar la semilla (`runner.play` L202 no la reenvía, `A1` §11.6); q leyendo filas nativas por lote, no
  `GameState` de libmelee (0,23 ms/frame lo hace inviable, `A5` §4). GPU solo si q/V̂ son Faynt-10M.
- **Coste (INF de A5 §6.3).** 1.024 frames simulados por decisión ≈ 15–18 ms + inferencia; ~10 min por partida y
  núcleo; 120 partidas ≈ 20 h·núcleo. **Mi salvedad (HIP):** esa cifra no incluye la inferencia de q en lazo
  cerrado; con Faynt-10M dominará (argumento 3 de §1). Hay que medirlo antes de fijar N, K, T.
- **Lo falsa.** `A5` §6.3 "S0-ceiling": S0 − P0 ≤ 0 (o < umbral preregistrado) con IC95 por bloque emparejado, en
  paused y a igual conteo. Añado un control para no culpar a la búsqueda de un V̂ malo: brazo **S0-MC** sin V̂
  (rollouts largos de ambos priors hasta T=120–240 y retorno Monte Carlo). Si S0-MC > P0 pero S0+V̂ ≤ P0, el
  culpable es V̂ (PROP mía).

### 2.3 Alt-C · S-teach / expert iteration: destilar la búsqueda exacta en una política rápida

- **Mecanismo.** Estilo AlphaZero/ExIt/DAgger: (1) la política actual juega en la granja; (2) en estados
  visitados, S0 (Alt-B) devuelve una distribución mejorada sobre los N candidatos (softmax de J) y un objetivo de
  valor; (3) la política se entrena por entropía cruzada hacia esa distribución con correa KL al prior humano, y
  V̂ hacia el retorno de la búsqueda; (4) repetir. La política final es causal, de un solo forward y juega en el
  bench **sin ningún cambio de integración** (`A1` §5.1).
- **A favor.** Es el brazo que `A5` §1 propone como secundario ("S-teach") y la vía que el autor describe:
  "search at training time, not at play time, the thing a 16 ms budget rules out live" (`tas.md` §7, DOC, leído
  por mí). Sortea tres problemas de la búsqueda en vivo: plazo de 16 ms, coste de reacción (`A5` §0.3) y ausencia
  de simulador en Dolphin. El privilegio queda en entrenamiento, igual que el valor que ve el presente (`A2` D3).
  MuZero/Dreamer muestran que la política absorbe parte del beneficio de la búsqueda (`A5` §1 fila W2, DOC de
  MuZero en Atari; no es Melee).
- **En contra.** (i) **Sin evidencia en Melee**: nadie lo ha hecho (HIP que funcione). (ii) AlphaZero/MuZero
  asumen turnos alternos y dinámica determinista; Melee es simultáneo y requiere estrategias mixtas (`A5` §3.1).
  Destilar un argmax puede enseñar una estrategia pura explotable; por eso destilo el softmax y mantengo la
  correa. (iii) El maestro ve RNG y estado exacto: parte de sus etiquetas puede ser inimitable para un alumno
  causal (mismo reparo que la ruta DIDA de `delay.md` §5, DOC). (iv) El autor ya avisa: una secuencia hallada es
  óptima contra un rival fijo, "it teaches execution and option coverage, not strategy" (`tas.md` §7, DOC).
  (v) Coste de etiquetado dominado por la inferencia de q.
- **Requisitos.** Los de Alt-B menos el cambio en `sim/runner.play` (el etiquetado corre en la granja o sobre
  `melee_brute.Match` directamente); bucle de entrenamiento supervisado (el de MIMIC es reutilizable, `A2` D2).
- **Coste (HIP).** 1 M de estados etiquetados × ~17 ms de motor ≈ 5 h·núcleo, más inferencia de q/V̂ por lotes en
  GPU (no estimable sin medir). Orden de magnitud: uno o dos días de una 3090 por iteración.
- **Lo falsa.** A igual número total de frames simulados (los de la búsqueda cuentan), la política destilada no
  supera a B1 (PPO) ni a su punto de partida en ≥5 pp con IC95 > 0, en Dolphin, contra rivales reservados. Señal
  temprana y barata: si la ganancia del alumno es < 1/3 de (S0 − P0) tras dos iteraciones, la destilación no
  captura la búsqueda.

### 2.4 Alt-D · Simulador sombra en Dolphin

- **Mecanismo.** El agente mantiene un `World` paralelo alimentado con los mandos aplicados de ambos puertos y la
  semilla de la partida; mientras su observación coincida con el `GameState` de Dolphin, el estado del simulador
  **es** el de la partida y se puede ramificar (`A4` §6.2 fila Dolphin, PROP de A4; `A5` §5 fila S0-shadow).
- **A favor.** Es el mecanismo de `sim/parity.py`. Con inputs y RNG grabados el motor reproduce 406/411 y 36/40
  partidas hasta el final (E31). Una partida rusher vs laser se reprodujo input a input durante 28.923 frames
  dada la semilla de Dolphin (`simulator.md` "Closed loop", DOC, leído por mí). Los bots ya reciben el flujo
  Slippi crudo (`A1` §6.3) y `FrameStart` lleva la semilla por frame (`A6` §3.1).
- **En contra.** Sin RNG inyectado, 25 de 40 partidas divergen (`A4` §0.5, DOC). **No hay API localizada para
  escribir el RNG a mitad de partida** en el camino RL (`A4` §5.5, DESC); el validador que sí lo hace es otra
  herramienta (`A4` §5.4 C2'). Tras divergir no hay resincronización: no existe `GameState → estado del
  simulador` (`A1` §5.2). Hace falta el stick C crudo del rival y no consta que libmelee lo exponga (`A4` §8).
  Exige `I_full` (mando del rival), que un humano no ve (`A1` §6.1). Las reglas deben ser las soportadas (UCF,
  sin ítems). Hoy es enteramente PROP.
- **Requisitos.** ISO en la máquina de juego; agente nuevo vía `Agent.step` (sin tocar `sim/runner.play`, sí
  construir un `World` propio dentro del agente); idealmente una función para fijar el RNG por frame en
  melee-brute (cambio en C, DESC si es viable).
- **Coste y riesgo.** Días de ingeniería; riesgo alto de que la fracción de frames en sincronía sea baja.
- **Lo falsa.** Medir en ≥100 partidas de Dolphin entre bots la fracción de frames de decisión con sombra en
  sincronía. Si la mediana es < 50 % de la partida y no se puede inyectar el RNG, la sombra queda descartada y
  **concedo** ese régimen al modelo aprendido (ver §5).

### 2.5 Alt-E · Activos aprendidos que no son dinámica: q y V̂

- **Mecanismo.** q = BC del rival sobre historia visible a su demora de reacción; V̂(x) = valor sobre estado
  estructurado, entrenado offline con la recompensa de slippi-ai (semivida 8 s) o tomado del crítico de B1
  (`A2` D3; `A4` §4.1).
- **A favor.** `A4` §6.2 lo llama irreemplazable; sirve a S0, a S-teach, a PPO y a cualquier W futuro. Evaluable
  offline (calibración y ranking) antes de jugar (`A5` §7).
- **En contra.** Ningún valor publicado reutilizable (`A2` D3). La recompensa con términos de modelado sesga V̂.
  q entrenado en humanos puede no describir a bots a 0 frames.
- **Lo falsa.** V̂ no ordena candidatos mejor que log π: correlación de rango con el retorno Monte Carlo del
  simulador ≤ la de P0-logp en un panel de estados reservado.

### 2.6 Comparación rápida

| Alternativa | ISO | GPU | Cambio en `sim/runner.play` | Estado | Incógnita que reduce |
|---|---|---|---|---|---|
| A · BC+PPO | sí | sí | no | existe (granja, E32 en curso) | ¿sube el RL convencional con nuestro pipeline? |
| B · S0 en vivo | sí | opcional | **sí** (pasar `World`, semilla) | primitivos existen, agente no | ¿vale algo la búsqueda con dinámica perfecta? |
| C · S-teach | sí | sí | no | no existe | ¿se puede destilar ese valor en una política causal? |
| D · Sombra | sí | opcional | no (agente propio) | PROP | ¿hay simulador exacto en Dolphin en vivo? |
| E · q y V̂ | para validar | sí | no | no existen | calidad del evaluador común a todo |

---

## 3. Dónde falla el simulador (dureza con mi propia postura)

1. **RNG.** "The game's RNG is not Dolphin's": la misma semilla e inputs se repiten en el simulador pero se
   desarrollan distinto en Dolphin (`simulator.md` "Differences", DOC). Los resultados de fuerza obtenidos solo en
   simulador no son resultados de Dolphin. El autor: "the farm replaces Dolphin for generating games… Dolphin
   stays the judge" (E24, DOC, leído por mí). Todo criterio de éxito mío termina en Dolphin.
2. **Sin CPU.** No hay rival CPU en el simulador (`A1` §8); el ancla CPU-9 del bench solo existe en Dolphin. Mis
   brazos en simulador solo pueden jugar contra políticas aprendidas o escritas.
3. **Transferencia.** E09: 77 % en simulador sin mejora en Dolphin. El autor lo atribuye a explotar a un rival
   congelado, no a infidelidad del motor, pero es una atribución, no una prueba. Además, hasta E30 el Dolphin
   headless tenía los gatillos analógicos rotos: **todo resultado Dolphin anterior a E30 es dudoso** (DOC, leído
   por mí), incluida parte de la evidencia que cito a favor y en contra de PPO.
4. **Privilegio de información.** S0 conoce estado exacto, memoria de mandos, RNG futuro y mando actual del
   rival. Una victoria de S0 en `--mode sim` es una cota privilegiada, no una fuerza comparable con B1 (`A5` §5).
   Tampoco se puede cuantificar bien el privilegio de RNG: no hay API para escribirlo (`A4` §5.5).
5. **Cobertura.** Upstream declara plantilla completa y seis escenarios, pero melee-brute solo Versus, UCF, sin
   ítems, Stadium congelado (`A1` §8). El bench fuerza Fox (`A1` §3). Los menús de búsqueda existen solo para
   Fox (`A5` §2.1). Las "pruebas" publicadas valen para un menú, un horizonte, FD, 0 %, y parte es anterior a dos
   bugs de menú no reejecutados (`A5` §3.2). No hay ECB ni flag de powershield ni Sudden Death.
6. **Versiones.** Runtime de melee-llm fijado a melee-brute `090e54b0` (sin `hitlag_left`, ABI v1); la granja
   carga otro checkout de revisión no registrada (`A1` §11.2-11.3). S0 en `--mode sim` y el etiquetado en granja
   pueden correr motores distintos si no se fija.
7. **Licencia y portabilidad.** melee-sim-light y melee-brute no tienen LICENSE (`A6` §10); la ISO es de
   Nintendo. Nada de esto se puede redistribuir ni ejecutar en la máquina de un tercero sin su propia ISO.
8. **Simultaneidad.** El simulador no resuelve el juego: sin q, la búsqueda da cotas (∃∀ / ∀∃), no valores
   (`A5` §3.1-3.2). Mi S0 hereda todo el sesgo de q.
9. **Estados humanos.** No se puede arrancar el simulador desde un replay salvo por "replay-to-reach", válido
   hasta la primera divergencia de RNG y con sesgo de selección (`A4` §5.4 C2). El etiquetado por búsqueda vive
   en la distribución de estados de bots, no de humanos (`A6` §8).

Ninguno de estos fallos lo arregla un modelo de dinámica aprendido en la fase de entrenamiento y validación; los
puntos 1, 4 y 7 son los que le dan nicho en despliegue.

---

## 4. MVP recomendado (una página)

**Nombre.** "Techo de búsqueda exacta y su destilación". Fox ditto, 4 stocks, 8 min, FD y Battlefield, 0 frames de
demora en el piloto (demora como extensión).

**Hardware.** Una máquina Linux con ISO NTSC 1.02, 8–16 núcleos y una GPU de 24 GB (la 3090 documentada por el
autor si está disponible, DESC; si no, alquiler a 0,3–0,7 USD/h, precio SUPUESTO de `A7` §4.2). Esta máquina
queda fuera salvo para escribir código y pruebas con agente sintético.

**Componentes reutilizados.** `melee_brute.Match` (checkpoint/rollback/branch), `train/farm/` (lotes, CUDA graph),
`train/farm/rl.py` (PPO receta Faynt), pesos Faynt-10M-Expert (prior y q en ditto) y Arena (referencia), menús de
`fox.py`, runner y bench de melee-llm, especificación de planificador de `A5` §2, contrato de tiempos de `A6`.

**Datos.** Ningún corpus humano nuevo. V̂ se entrena con partidas de la granja (Expert y Arena, autojuego y
cruzadas) con la recompensa de slippi-ai sin términos de modelado. Panel congelado (sha256) de ~2.000 estados
alcanzados por el prior, con partidas y semillas reservadas para test.

**Etapas y puertas.**

| Etapa | Qué | Coste (INF/HIP) | Puerta |
|---|---|---|---|
| 0 | Fijar revisión de melee-brute; pasar `World` y semilla en `sim/runner.play`; q y V̂ sobre filas nativas por lote; `python -m melee_brute bench`; medir `t_dec` integral por brazo | 3–5 días de ingeniería, 0 € de GPU | rollback byte-idéntico; coste por decisión medido |
| 1a | Panel offline de mejora en la raíz: para cada estado, valor Monte Carlo (rollouts largos, ambos priors) de la acción elegida por S0 frente a top-1 del prior y frente a P0-Q | pocas horas de GPU | mejora media > 0 con IC95; si no, parar la búsqueda |
| 1b | "S0-ceiling" de `A5` §6.3 en `--mode sim`, paused, igual conteo (N=16, K=4, T=16), ≥200 partidas emparejadas por brazo con intercambio de puertos | horas de GPU por lotes | S0 − P0 ≥ 5 pp, IC95 > 0 |
| 2 | Destilación (Alt-C), 2 iteraciones, frente a PPO (Alt-A) con el mismo total de frames simulados, 3–5 semillas | 2–5 días de GPU | ver criterio |
| 3 | Juez: Dolphin `fast`, post-E30, rivales reservados (CPU-9, Faynt Arena, Phillip a su demora nativa, declarada) | ≈6–10 h por brazo en serie (`A7` §0.6) | ver criterio |

**Brazos.** π₀ = Faynt-10M-Expert directo · P0-logp y P0-Q · S0+V̂ · S0-MC (sin V̂) · B1 = PPO con correa ·
ST = alumno destilado. Referencia externa: Arena. Todos con la misma observación y códec (`A2` §1.7).

**Éxito.** (a) 1b pasa: existe valor de búsqueda con dinámica perfecta. (b) ST supera a π₀ y no es peor que B1 en
Dolphin (≥5 pp sobre π₀, IC95 > 0, macro-promedio por rival y escenario; autodestrucciones y time-outs dentro de
límites congelados).

**Fracaso y qué se aprende.** 1a o 1b fallan con S0-MC también ≤ P0 → la planificación de horizonte corto queda
falsada en este régimen para **cualquier** fuente de dinámica; el dinero va a PPO, liga de rivales y demora. 1b
pasa y ST falla → el valor está en la búsqueda en vivo y no se destila: es el escenario que abre la puerta al
modelo aprendido (§5). B1 tampoco sube → el problema es el pipeline de RL, anterior a toda la pregunta.

**Presupuesto total (HIP).** 2–3 semanas-persona y del orden de 50–150 h de GPU (≈20–100 € alquilada). El coste
dominante es ingeniería y pared de Dolphin, no cómputo.

---

## 5. Qué evidencia me haría cambiar a favor de un world model aprendido

Cambiaría de opinión con **cualquiera** de estas, todas medibles con la infraestructura del MVP:

1. **S0 gana, no se destila y no hay simulador en vivo.** 1b pasa con margen; ST recupera < 1/3 de (S0 − P0) tras
   dos iteraciones; y la sombra (Alt-D) mantiene sincronía en < 50 % de los frames sin posibilidad de inyectar
   RNG. Entonces la búsqueda en vivo vale, y en Dolphin solo un modelo aprendido puede darla.
2. **Regret de decisión bajo.** En el panel contrafactual (`A4` §5.4 C1/C2, `A5` §6.3), un W0-S pequeño obtiene
   regret de argmax frente a S0 claramente menor que P0 a 16–32 frames. Un W0-S de ~1 M cuesta horas de GPU:
   aceptaría añadirlo como diagnóstico lateral en la etapa 1a (≤10 % del presupuesto).
3. **Igual tiempo en tiempo real.** Con plazo impuesto (`RT-strict`, `A7` §2.1) y q en lazo cerrado, S0 no cabe en
   12 ms pero un W1-L-GRU de bloque 4 sí, y gana a P0 y a S0 a igual tiempo (el único hueco que `A5` §6.1 deja
   abierto en simulador).
4. **Varianza por RNG grande.** Los gemelos de RNG (`A4` §5.5) muestran que el privilegio de RNG explica buena
   parte de la ventaja de S0; un modelo que trate el RNG como ruido sería entonces el estimador honesto.
5. **Objetivo de despliegue sin ISO** (máquinas de terceros, web) declarado por el usuario como requisito.
6. **Representación.** E1/E1-S de `A3` §4 mejora la eficiencia de datos de BC con igual capacidad y cómputo. Eso
   justificaría una pérdida auxiliar predictiva, no un planificador; y si E1-S ≥ E1, tampoco justifica JEPA.

## 6. Qué concedo a un defensor

- **El simulador sombra es una propuesta, no un hecho.** Hoy, en Dolphin en vivo, S0 no existe (`A1` §5.2), y el
  bench se juega en Dolphin. Si el objetivo es buscar en vivo en el bench, el modelo aprendido es por defecto la
  única opción (`A5` §6.1, fila Dolphin sin simulador).
- **La cota "S0 ≥ W" es a igual conteo y mismo evaluador.** No cubre la abstracción temporal ni modelos de evento,
  que el motor no ofrece; ahí no tengo evidencia en contra, solo ausencia a favor.
- **Mi brazo estrella (destilación) tiene exactamente la misma evidencia en Melee que el suyo: ninguna.** Y
  AlphaZero no se traslada limpiamente a un juego simultáneo con azar.
- **PPO propio ha fallado aquí dos veces** y E32 no tiene resultado; "RL convencional" no es una apuesta segura.
- **El coste de GPU de un piloto W0/W1 es pequeño** (`A7` §5). Mi objeción es de orden e interpretabilidad, no de
  euros.
- **q es un modelo aprendido del mundo** en sentido amplio, y es la pieza que más defiendo.
- **Un modelo aprendido trata el RNG y la información oculta de forma natural**; S0 hace trampa con ambos.
- **Si la meta del usuario es científica** (responder a la pregunta JEPA) y no la fuerza de juego, una
  recomendación negativa creíble exige haber ejecutado al menos W0-S contra S0. Mi plan lo deja preparado y
  barato, pero no lo sustituye.
- **Sin ISO no se puede ejecutar nada de lo que propongo**; un estudio offline de predicción sobre HAL MDS sí
  (con las carencias de `A6` §1.4).

## 7. Hipótesis y desconocidos que sostienen esta propuesta

| Supuesto | Estado | Cómo se resuelve |
|---|---|---|
| Hay ISO y GPU disponibles para el proyecto | DESC | preguntar al usuario |
| El coste por decisión de S0 lo domina la inferencia de q, no el motor | HIP | etapa 0 |
| El softmax de J con correa KL evita destilar una estrategia pura explotable | HIP | sonda de mejor respuesta de `A5` §3.4 |
| El RNG pesa poco en Fox ditto en FD/BF | HIP | gemelos de RNG (`A4` §5.5), limitado por la falta de API |
| Se puede fijar el RNG por frame en el camino RL de melee-brute | DESC (`A4` §5.5) | leer `src/runtime` con ISO disponible |
| libmelee expone el stick C crudo del rival | DESC (`A4` §8) | comprobar en 0.47.6 |
| La granja y `--mode sim` usan el mismo motor | no, hoy difieren (`A1` §11.3) | fijar revisión en etapa 0 |
| Las cifras de Faynt/MIMIC/Phillip se sostienen a igual demora y con IC | no verificado (`A2` §1.5, §4) | etapa 3 con demora declarada |
