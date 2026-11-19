# Brainstorm — postura DEFENSOR del world model aprendido

Ronda de brainstorming · 2026-11-19 · Postura asignada: defender el modelo del mundo aprendido (JEPA temporal / LeWorldModel adaptado) con el caso más fuerte y honesto posible.

Base: solo los informes `evidence/A1`…`A7` (los .md), el brief y el master prompt. No he ejecutado nada ni he leído fuentes primarias. Todo lo que no sale de un informe va marcado **[HIP]** (hipótesis mía). Las cifras son las que citan los informes, con su etiqueta original (DOC = del autor de la fuente, MED/REP = medido por el especialista en esta máquina).

---

## 1. Tesis

Los informes refutan bien una versión concreta del proyecto: **"MPC con dinámica aprendida en `--mode sim`, en CPU, compitiendo con el simulador exacto"**. Esa versión la concedo (§5).

La versión que defiendo es otra:

> Un modelo predictivo **conjunto de dinámica + rival humano**, entrenado con replays, usado **donde el simulador no llega**: partidas en Dolphin (todo el bench), régimen sin mando del rival, y decisiones con retraso. Su primer uso no es buscar, sino **predecir el presente** que la política no ve todavía.

Tres hechos de los informes sostienen que ese nicho existe y no es marginal:

1. **Todas las partidas puntuadas del bench son en Dolphin y ahí el simulador no existe como modelo.** `bench` nunca usa `sim` (A1 §2.2), no hay hook de planificación ni acceso al motor, y no hay API `GameState → estado del simulador` (A1 §5.2). El "simulador sombra" es una propuesta sin construir (A4 §6.2).
2. **El simulador no predice lo que hará el rival.** A4 §6.2 lo llama "irreemplazable"; con retraso, "lo necesario es q, no p_dyn". Lo que falta es justo la parte aprendida.
3. **El único resultado de juego en Melee con un predictor aprendido es favorable bajo retraso.** Firoiu 2018 contra un profesional: (d=6,p=0) 0–6, (6,6) 3–5, (7,7) 2–5; en población "best results are achieved with p = d" (A2 §2 Phillip histórico; A6 §4). Es DOC de los autores, pocas partidas, sin IC, y el modelo ignoraba al rival.

---

## 2. Ideas, una a una

Formato: mecanismo → por qué podría funcionar → evidencia a favor / en contra → coste → experimento que la falsaría.

### I1. Predictor del presente bajo retraso (mi apuesta principal)

- **Mecanismo.** Con retraso D, la política ve post(f) y su mando se aplica en f+1+D (A6 §4). El modelo despliega D+1 frames con la cola propia ya comprometida (conocida) y entrega a la política una estimación del estado en el frame de aplicación. Es el esquema (d,p) de Firoiu, pero prediciendo también al rival (A4 §1.1).
- **Por qué podría funcionar.**
  - Cada frame de latencia efectiva cuesta valor de juego: con inputs de 2 frames el valor del duelo a 12,59 u pasa de 0 a 0,382 (A5 §0.3, DOC). Predecir recupera frames.
  - Dentro de la ventana de reacción del rival (`D_yo+1+R_riv`, R humano ≈ 12–15) sus acciones no pueden depender de mi decisión actual (A4 §4.3 O3'; A5 §2.3). Un modelo que predice el futuro del rival desde la historia es **causalmente correcto** en ese horizonte, sin lazo cerrado.
  - Es barato en inferencia: son K hipótesis × D pasos, no N×K×T. Un MLP-1M con K16·T4 mide 1,4 ms p99 y K16·T8 2,8 ms en esta CPU (A7 §3.1, MED). El argumento "no cabe en tiempo real" (A7 §0.2, A5 §0.4) afecta al MPC, no a este uso.
- **A favor.** Firoiu 2018 (arriba). HAL "pierde fuerza con 3–10 frames de delay" (A6 §4, DOC de melee-llm, E16/E22): las políticas a 0 frames se degradan y hay hueco que recuperar. Las mejores políticas publicadas a 0 frames (Faynt Arena, MIMIC fox) no están entrenadas con retraso (A2 §2).
- **En contra.** slippi-ai abandonó el predictor y entrena la política con el retraso en los objetivos; melee-llm recomienda "Skip the predictive model" (`delay.md` L70; A4 §6.2, A5 §6.2 — opiniones de autor, no pruebas). Frente a la CPU el agente predictivo de Firoiu rinde "algo peor" (A2). A5 §6.2 punto 4: improbable que supere a una política entrenada con la cola como entrada. Promediar futuros del rival produce estados imposibles (A4 §4.2): hay que muestrear hipótesis, no regresar la media.
- **Coste.** Un predictor de 1–2 M y una política BC pequeña. Entrenamiento: minutos a horas en una GPU de 24 GB para 1k–10k partidas (A7 §4.2, estimación). La parte offline no necesita ISO; la de juego sí.
- **Falsación.** Es el MVP (§3). Muere si la política con estado predicho no supera a la misma política con observación envejecida, o si una política entrenada con el retraso en los objetivos la iguala o supera con el mismo cómputo.

### I2. Modelo conjunto dinámica + rival humano (lo que el simulador no puede dar)

- **Mecanismo.** p(x_{f+1..f+T} | historia, mandos propios), con el rival dentro del modelo. A4 §4.1 lo factoriza en p_dyn × q y propone q como BC de los mandos del rival.
- **Por qué podría funcionar.** [HIP] Predecir el **estado futuro** del rival es un objetivo mejor planteado que predecir sus mandos en el régimen `I_human`, donde su mando actual no se observa (slippi-ai lo excluye, A2 §1.7; A4 §4.4). El estado sí se observa siempre. Además el corpus humano (≈1,3 M partidas en HAL MDS, ≈850k .slp en MRR; A6 §2) es la única fuente de comportamiento humano: el simulador no aporta nada ahí.
- **A favor.** A4 §6.2 ("Modelo del rival: Sí, irreemplazable"); Firoiu §5.2 propone esta extensión como trabajo futuro (A4 §4.1). En `I_human` S0 ni siquiera es ejecutable (A5 §5 punto 3): el contraste válido pasa a ser W vs P0 vs B1.
- **En contra.** A4 §6.2: q "se combina igual de bien con el simulador que con un modelo aprendido", y el control decisivo es W(p_dyn+q) vs S0(simulador+mismo q). Si se dispone de simulador y de `I_full`, la dinámica aprendida es redundante. Un modelo conjunto entrenado con L2 promedia futuros (A4 §4.2). LeWM es determinista y no trata multiagente (A4 §3.1).
- **Coste.** El de I1; es el mismo modelo.
- **Falsación.** Curvas de A4 §5.3 en replays: error por horizonte con rival oracle frente a rival predicho. Si el modelo conjunto no mejora la predicción del estado del rival a h ∈ {4, 8, 16} sobre persistencia y "mayoritaria condicionada" (A4 §2.3), no hay modelo de rival útil. Con ISO: si simulador + q-BC de mandos predice igual o mejor en `I_human`, la parte de dinámica aprendida sobra.

### I3. Dolphin sin snapshot: el simulador sombra es más frágil de lo que parece

- **Mecanismo.** En Dolphin el planificador o predictor solo tiene `gs`; el modelo aprendido se re-sincroniza con la observación en cada frame por construcción.
- **Por qué podría funcionar.** El simulador sombra reproduce mandos desde la semilla y es exacto "hasta la primera divergencia de RNG": sin RNG inyectado, 25 de 40 partidas divergen en algún momento (A4 §2.4, §6.2, DOC). [HIP] Como no existe `GameState → estado del simulador` (A1 §5.2), tras divergir no hay forma descrita de re-sincronizarlo, así que queda inservible para el resto de la partida. Requiere además sticks crudos de ambos jugadores (duda abierta, A4 §8), ISO, Linux, y pasar el `World` al agente (A1 §5.2).
- **A favor.** A5 §6.1: "Dolphin, I_human / sin simulador: Sí por defecto (S0 no existe)". A1 §5.2 opción 1: `Agent.step` con `gs` es "la única vía que funciona igual en Dolphin y sim".
- **En contra.** Con RNG grabado el validador reproduce 36/40 partidas hasta el final (A4 §5.4 C2'), y en netplay el RNG por frame podría ser predecible (A5 §5, nota INF sin verificar). Si el flujo Slippi en vivo expone `random_seed` de FrameStart (duda de A5 §7), la sombra podría aguantar mucho más. Y aun sin sombra, el modelo aprendido tiene que ganar a P0/B1, no solo existir.
- **Coste.** Para el escéptico: construir y validar la sombra es ingeniería no trivial. Para mí: ninguno adicional.
- **Falsación.** Medir en Dolphin la fracción de frames de partida con sombra sincronizada. Si supera ~95 % con el flujo en vivo, este argumento cae y el nicho se reduce a `I_human`.

### I4. Planificación en GPU por lotes: la relación de velocidad puede invertirse

- **Mecanismo.** Rollouts latentes en un solo forward por paso sobre miles de ramas.
- **A favor.** A7 §4.1 estima (sin medir) que una GPU modesta con CUDA graphs da 10⁴–10⁵ evaluaciones por decisión en 12 ms para MLP/GRU de 1–5 M. El simulador a 12–17 µs/frame (DOC) da ~800 frames-rama por núcleo en 12 ms. A4 §6.1 lo admite: "En GPU… la relación puede invertirse — no medido". La abstracción temporal (bloques de 4) añade 4× horizonte por paso (A5 §0.4, §6.1).
- **En contra.** Más búsqueda no implica más fuerza: MuZero en Atari satura (A5 §6.2); J ≈ V̂ a horizonte corto (A5 §0.6); el error del modelo crece con el horizonte y los golpes son discontinuos dentro del bloque (A4 §1.2). El simulador también escala con núcleos.
- **Coste.** GPU en inferencia durante la partida; medición con sincronización (A7 §2.3).
- **Falsación.** El "S0-ceiling" de A5 §6.3: si S0 − P0 ≤ 0 con dinámica exacta, ningún W gana por rollouts con ese evaluador. Lo acepto como veto para el MPC (no para I1, I5, I6).

### I5. Preentrenamiento predictivo para eficiencia de datos y transferencia entre personajes

- **Mecanismo.** Preentrenar el encoder prediciendo el futuro (J-T latente o S-T estructurado, A3 §4) y ajustar BC con pocos datos.
- **Por qué podría funcionar.** [HIP] La dinámica no depende de la habilidad del jugador: el objetivo predictivo puede usar todas las partidas de todos los rangos y personajes, mientras que BC necesita partidas buenas del personaje concreto. El desequilibrio es grande: FOX 301 GB frente a PICHU 0,9 GB y KIRBY 1,9 GB (A6 §2.1).
- **A favor.** A3 §3.1: J-T es "el único con sentido" y puede codificar variables no observadas por frame (inercia de decisiones del rival). El diseño de ablaciones ya existe (E0, E0b, E1, E2, E1-S; A3 §4).
- **En contra.** A3 §3.1: en estado estructurado el rival natural es predecir el estado explícito y no hay razón a priori para que el latente gane. Las cabezas de estado de HAL no dieron ganancia: 029 = −0,05 NSM "within noise", 060 sin cualificar (A2 §1.4). SIGReg no garantiza contenido y puede atenuar información del rival (A3 §1.5).
- **Matiz que hago valer.** [HIP] HAL probó la pérdida auxiliar con ~1,3 M partidas, el régimen donde menos se espera ganancia. La pregunta abierta es el régimen de pocos datos, que nadie ha medido.
- **Coste.** Bajo: mismo corpus y encoder que el MVP. La fuerza de juego exige ISO.
- **Falsación.** Curvas de BC con N ∈ {100, 1k, 10k} partidas del personaje objetivo: E0/E0b vs E1/E2 vs E1-S. Si E1/E2 no superan a E0b con N pequeño, no hay eficiencia de datos. Si E1-S ≥ E1, lo que ayuda es "predecir", no "JEPA" (ver §5).

### I6. El modelo como valor / crítico

- **Mecanismo.** Entrenar V̂ sobre el latente predictivo, o usar las cabezas de eventos (golpe, muerte en k frames) como valor de corto plazo.
- **A favor.** A5 §0.6 y §7: V̂ es "el componente crítico" y no hay ninguno publicado reutilizable (A2 D3). [HIP] La recompensa es escasa (stocks, semivida 8 s); los eventos predichos son supervisión densa para el mismo encoder.
- **En contra.** HAL 059 ya entrena V(s) sin modelo de dinámica (A2 §1.1). P0-Q, un Q̂ de la secuencia sin rollout, es el control directo (A5 §1) y puede absorber el beneficio.
- **Coste.** Mínimo y offline: ranking y calibración de V̂ en partidas reservadas.
- **Falsación.** V̂ sobre encoder predictivo vs V̂ sobre E0 con igual cómputo (E0b): si no mejora calibración ni ranking de candidatos en test por partida, la idea cae.

### I7. Entrenamiento de política en imaginación, masivamente paralelo

- **Mecanismo.** Actor-crítico sobre rollouts latentes en GPU (Dreamer, brazo W2).
- **A favor.** [HIP] El cuello de botella del RL real no parece el simulador: E10 hizo 101 M frames en 3,6 h en una 3090 (≈7,8k frames/s; A2 D2) y la granja Faynt 6.337 frames/s con 8 procesos (A2 D3), muy por debajo de los ~120k frames/s/núcleo del motor (A1 §8). Además el RL en simulador no se trasladó a Dolphin en E09/E10 (A2, bot propio; causa no establecida). Un modelo entrenado con replays de Dolphin y con rival humano dentro es un entorno distinto al autojuego en simulador. Excepción reconocida por A4 §6.2: arrancar imaginación desde estados humanos que el simulador no alcanza.
- **En contra.** A4 §6.2: "No, mientras el simulador corra". Si el cuello es el forward de la política (10–20 M), imaginar no lo quita. Los errores del modelo son explotables por la política (Firoiu §5.1, A6 §7). La causa de E09/E10 es desconocida.
- **Coste.** Alto: es el brazo más caro y exige GPU e ISO para evaluar.
- **Falsación.** Perfilar la granja: si el simulador + transferencias pesan < 30 % del paso, no hay ganancia de throughput posible. No lo recomiendo como MVP.

### I8. Píxeles

- **Mecanismo.** LeWM tal cual (ViT-Tiny + predictor), su caso de uso nativo.
- **A favor.** Es donde el latente JEPA tiene justificación real (A3 §3.1 por contraste) y donde no hay estado ni simulador.
- **En contra.** En Dolphin el estado estructurado llega siempre por Slippi; los pesos publicados no sirven (A3 §5); un ViT a 60 fps no cabe en esta CPU (A7 §0.2). El master prompt lo trata como línea aparte.
- **Veredicto.** No lo defiendo para el MVP. Solo tendría sentido como proyecto distinto (consola real, otros juegos).

### Orden de fuerza

I1 ≈ I2 > I3 > I5 ≈ I6 > I4 > I7 > I8.

---

## 3. MVP recomendado: "predictor del presente" (I1 + I2), con I5/I6 de polizón

**Pregunta única.** ¿Una política a 0 frames alimentada con el presente predicho por un modelo aprendido juega mejor bajo retraso D que la misma política con observación envejecida, y aguanta la comparación con una política entrenada con el retraso?

**Datos.** .slp crudos de la carpeta FOX de `erickfm/melee-ranked-replays@ef54ddc2` (A6 §2.1), reparseados con peppi al esquema de A6 §5 (velocidades, `action_state_frame`, hitstun, hitlag, mandos de ambos, copia LAST). Fox ditto, que es lo que fuerza el bench (A1 §3). 2.000 partidas de entrenamiento, 200 de validación, 200 de test; split por sha1 de partida antes de ventanear (A6 §6). HAL MDS no sirve: le faltan velocidades y contadores (A6 §1.4).

**Modelo.** Dos predictores con el mismo contrato (A4 §2–3), ~1–2 M parámetros, núcleo GRU/MLP (el transformer de LeWM no cabe en CPU, A7 §0.2):
- **W0-S**: estructurado, cabezas categóricas/two-hot por campo.
- **W1-L**: latente estilo LeWM (mismo encoder, SIGReg, D=128, bloques de 4) con decodificador de campos.

Entrada: historia de 16 frames + cola propia comprometida. Sin mandos futuros del rival; K=4 hipótesis muestreadas, nunca la media (A4 §4.2). Regímenes `I_full` e `I_human` reportados por separado.

**Política.** B0 propio: BC pequeño (~5 M), 0 frames, mismo encoder y datos.

**Brazos de juego**, D ∈ {4, 8, 12}, mismos rivales fijos, puertos y semillas:

| Brazo | Qué ve la política | Papel |
|---|---|---|
| a | observación envejecida D frames | suelo |
| b0 / b1 | presente predicho por W0-S / W1-L | la afirmación |
| c | B0-D: misma arquitectura entrenada con el retraso en los objetivos (receta slippi-ai, A6 §4), mismos datos y pasos | control decisivo del escéptico |
| d | presente real (D=0) | techo, privilegiado |
| e | simulador + rival "mantiene último mando", solo en `--mode sim` | control "¿hace falta aprender al rival?", privilegiado |

**Hardware.** Nada de esto corre en la máquina actual (A7 §5). Hace falta una GPU de 24 GB alquilada o del usuario, ISO NTSC 1.02 y Dolphin; permiso para un venv con `peppi_py`. Estimación de A7 §4.2 y §5 (supuestos sin verificar): entrenamiento en horas de GPU; la evaluación en Dolphin domina el tiempo.

**Etapa 0 — puerta offline (sin ISO, la más barata).** En test por partida, a h = D+1 ∈ {5, 9, 13}: acierto de la acción del rival en frames donde cambia, recall de eventos (golpe, escudo, agarre) y MAE de posición, contra persistencia, velocidad constante y mayoritaria condicionada (A4 §2.3, §5.2), con IC bootstrap por partida.
- **Pasa** si W supera a la mejor línea trivial con IC que excluye 0 en acción-en-cambio y en eventos, en los tres horizontes.
- **No pasa** → se para aquí. Coste hundido: unas horas de GPU y el parser.

**Etapa 1 — juego.** Calendario piloto que cita A5 §6.3 (2 escenarios × 2 rivales × 2 puertos × 5 repeticiones = 40 partidas por brazo y D), plazo impuesto con envoltorio (A7 §2.1).
- **Éxito mínimo:** b > a en diferencial de stocks/daño, IC 95 % por bloque emparejado que excluye 0, en al menos D = 8 y 12.
- **Éxito fuerte:** b ≥ c dentro de un margen preregistrado, o b > c.
- **Fracaso:** b ≤ a, o c > b con claridad a igual cómputo. Entonces la conclusión es "basta entrenar la política con retraso" y se cierra la línea de dinámica aprendida para control.
- **Lectura JEPA:** b1 vs b0. Si b1 ≤ b0, el latente no aporta en estado estructurado y se conserva solo W0-S.

**Polizones de coste casi nulo** (mismo encoder y datos, solo offline): curva de BC con pocos datos E0b/E1/E1-S (I5) y ranking de V̂ (I6).

---

## 4. Por qué este MVP y no el MPC

- Esquiva las tres objeciones más sólidas: no compite con S0 en `--mode sim` (A5 §6.1), no depende de V̂ (A5 §0.6) y cabe en tiempo real en CPU (A7 §3.1).
- Ataca la única pieza que los escépticos declaran irreemplazable (el rival, A4 §6.2) y el único régimen con evidencia previa favorable en Melee (retraso, Firoiu).
- Tiene una puerta offline barata y un control (brazo c) que puede matarlo limpiamente.
- Lo construido se reutiliza gane o pierda: parser con esquema completo, W0-S, q/modelo del rival, envoltorio de plazo; A4 §6.2 ya recomienda invertir en q "con independencia del resultado".

---

## 5. Lo que concedo al escéptico

1. **En `--mode sim`, con `I_full` e igual conteo, W no puede superar a S0** (A5 §6.1). No lo discuto.
2. **La velocidad en CPU no es argumento** (A4 §6.1, A7 §0.3). En GPU es una estimación sin medir.
3. **El LeWM literal no sirve aquí**: predictor transformer fuera de tiempo real en CPU, determinista, coste por imagen meta, un solo agente (A4 §3.1, A7 §0.2). Lo que defiendo es "inspirado en", con núcleo recurrente y muestreo de hipótesis.
4. **No hay razón a priori para que el latente JEPA gane al predictor estructurado** en estado estructurado (A3 §3.1). Si E1-S ≥ E1 y b0 ≥ b1, lo que sobrevive es "modelo predictivo aprendido", no "JEPA". Como defensor lo considero una victoria parcial del world model y una derrota de la etiqueta.
5. **JEPA no temporal, vistas por aumento y pesos preentrenados: descartados** (A3 §3.1, §5).
6. **Las pérdidas auxiliares de estado no han dado fuerza de juego en datos abundantes** (HAL, A2 §1.4).
7. **El control más peligroso para mi MVP es trivial y ya existe**: entrenar la política con el retraso (slippi-ai, Phillip). Mi prior honesto de que b supere a c es bajo-medio; de que b supere a a, medio-alto. Ambos son [HIP].
8. **Píxeles e imaginación a gran escala no son MVP.**
9. **Nada de lo anterior está medido en Melee por nosotros.** La evidencia a favor (Firoiu) es antigua, pequeña y de sus autores; una pérdida predictiva baja no demuestra ventaja al jugar.
10. **Si la Etapa 0 falla, o el brazo c gana y el "S0-ceiling" de A5 §6.3 da S0 ≤ P0**, la recomendación negativa es la correcta y la firmaría.
