# Brainstorm — postura PRAGMÁTICA con restricciones reales

Fecha: 2026-11-19. Autor: agente de brainstorming (postura asignada: pragmático). Idioma: español.

Convención de etiquetas en este documento:
- **[CITA]**: lo afirma un informe del swarm; se da archivo y sección. No lo he reverificado contra la fuente primaria.
- **PROPUESTA**: diseño, umbral o gate mío. Ningún umbral numérico de este documento está medido ni validado; A8 debe revisarlos antes de congelarlos.
- **HIPÓTESIS**: suposición mía (costes, horas, precios, viabilidad) pendiente de comprobar.

No he ejecutado nada: ni descargas, ni entrenamientos, ni partidas. No hay resultados nuevos aquí.

---

## 1. Resumen en una pantalla

Pregunta: ¿cuál es la secuencia de menor coste que más reduce la incertidumbre sobre «¿aporta un modelo del mundo aprendido / JEPA algo en Melee?» y deja algo útil si la respuesta es no?

Respuesta corta: **cuatro etapas, las tres primeras sin ISO y por menos de ~35 € de GPU en total** (HIPÓTESIS de coste, §6). El orden está elegido para que cada etapa produzca un componente que la siguiente necesita de todos modos (datos → q y V̂ → búsqueda con simulador), de modo que una parada en cualquier gate no desperdicia lo anterior.

| Etapa | Qué responde | Requiere ISO | Coste € (HIPÓTESIS) | Si el gate falla |
|---|---|---|---|---|
| 0. Tubería de datos + suelos triviales + humo local | ¿Se puede medir algo? ¿Cuánto margen dejan las líneas base triviales? | No | 0 | Se arregla la tubería; no se alquila GPU |
| 1. E1-S frente a JEPA latente, offline | ¿Aporta la parte «latente/JEPA» sobre predecir el estado explícito? ¿Aporta algún preentrenamiento predictivo sobre BC a igual cómputo? | No | 10–25 | Se cierran los brazos JEPA; se conserva W0-S/E1-S como único representante «modelo del mundo» |
| 2. Descomposición rival / valor / dinámica, offline | ¿Cuánto del valor de «mirar T frames adelante» sobrevive cuando el rival es q y no el log? ¿Es el cuello q, V̂ o la dinámica? | No | 3–8 | Se invierte en q y V̂ (útiles para cualquier bot) y no en dinámica |
| 3. «S0-ceiling» con el simulador exacto | ¿Sirve de algo planificar, incluso con dinámica perfecta? | **Sí** | 0–10 | Queda falsada la planificación con modelo aprendido en ese régimen; se redirige a S-teach |
| 4. (Opcional) W frente a S0/P0 en partida y entrante de bench | ¿Mejora la fuerza de juego bajo reloj? | Sí | 30–80 + muchas horas | — |

Primer paso concreto: ver §8.

---

## 2. Qué dicen los informes que condiciona el orden

1. **En esta plataforma la dinámica aprendida no gana por velocidad ni por exactitud.** Coste amortizado MLP-1M 8,3 µs/transición y GRU-1M 9,6 µs frente a 12–17 µs/frame documentados del simulador exacto (otra CPU) [CITA `evidence/A7/FEASIBILITY.md` §0.3 y §3.2]. S0 es la cota superior de cualquier W a igual conteo de candidatos, q y V̂ [CITA `evidence/A5/PLANNING.md` §0.7 y §6.1].
2. **Lo irreemplazable es el modelo del rival q, que es una política y no una dinámica**, y se combina igual con el simulador que con un modelo aprendido [CITA `evidence/A4/DYNAMICS.md` §0.6 y §6.2, fila «Modelo del rival»]. Con demora, «lo necesario es q, no p_dyn» [CITA A4 §6.2; A5 §6.1].
3. **Con horizontes de 8–32 frames, J ≈ V̂(x_T)**: γ^32 = 0,955, así que el MPC es «V̂ compuesto con la dinámica» y es muy sensible a V̂ [CITA A5 §0.6]. No hay ningún valor terminal publicado reutilizable; hay que entrenarlo y debería evaluarse antes de cualquier MPC [CITA `evidence/A2/BASELINES.md` D3; A5 §7].
4. **El control E1-S es el que puede refutar «JEPA» en estado estructurado**: misma arquitectura preentrenada prediciendo el siguiente estado explícito; si E1-S ≥ E1 la parte latente no aporta [CITA `evidence/A3/REPRESENTATIONS.md` resumen §4, §3.1, §4]. W0-S es ese mismo control llevado a dinámica [CITA A4 §0.2].
5. **Sin ISO no hay nada falsable en juego**: ni simulador, ni Dolphin, ni PPO [CITA A5 §6.3 último punto; A2 §1.6; A7 §5 punto 4]. Sí son posibles las métricas offline sobre replays [CITA A4 §5.2–5.3].
6. **Entrenar en esta máquina solo sirve de humo**, pero el humo sin SIGReg es rápido: MLP-1M 4.721 muestras/s y GRU-1M 2.042 sin SIGReg, 800 y 573 con SIGReg M=1024 (datos sintéticos, 3 hilos, sin dataloader) [CITA A7 §3.4]. Hoy no se pueden leer datos reales porque faltan `peppi_py`, `zstandard` y `mosaicml-streaming` [CITA A7 §0.5, §1].
7. **Un piloto de 1k partidas, 3 épocas, 1–5M parámetros cuesta ≈ 0,1–1 h de RTX 4090 por réplica** (estimación, no medida; precio/hora supuesto 0,3–0,7 USD) [CITA A7 §4.2].
8. **Una pérdida predictiva baja no demuestra ventaja al jugar** [CITA `handoff/melee_swarm/01_MASTER_PROMPT.txt`, distinción 10]; las métricas a 1 frame con acciones del log no validan un planificador [CITA A4 §5.2; A6 §7].

Consecuencia para el orden (PROPUESTA): las etapas 1 y 2 no pueden demostrar que un modelo del mundo ayuda a jugar, pero sí pueden **retirar condiciones necesarias** a bajo coste. La etapa 3 es la primera que falsifica algo en juego, y por eso es la primera que justifica pedir la ISO.

---

## 3. Etapa 0 — Tubería de datos, suelos triviales y humo local

**Objetivo.** Tener un corpus pequeño, congelado y bien alineado, las líneas base triviales por campo y horizonte, y el código de las etapas 1–2 funcionando de extremo a extremo en CPU antes de pagar una hora de GPU.

**Trabajo.**
1. Venv propio (no paquetes de sistema) con `peppi_py` y `zstandard`. Requiere permiso del usuario [CITA A7 §5 punto 3 y §7].
2. Muestra de `.slp` crudo de `erickfm/melee-ranked-replays@ef54ddc2` filtrada a **Fox ditto** (es lo que fuerza el bench [CITA A4 §4.3, O4, que remite a A1 §3]). Se usa `.slp` crudo y no HAL MDS porque HAL MDS carece de velocidades, `action_state_frame`, hitstun y mandos crudos, y una dinámica entrenada solo con él tiene un suelo de error irreducible [CITA `evidence/A6/DATA_AND_TIME.md` §1.4 y §5; A4 §2.1 «Advertencia de corpus»].
   - HIPÓTESIS: los tarballs de FOX pesan de media ≈ 8 GB (301 GB / 36 tarballs, cálculo mío sobre cifras de A6 §2.1; el tamaño de cada tarball no lo he comprobado). Para el humo local basta leer en streaming el principio de un tarball y cortar al llegar a ~200 partidas; el corpus de 1k–2k partidas se parsea en la máquina alquilada de la etapa 1 y a local solo vuelve el resultado comprimido. Verificar que el corte de un `tar.gz` en streaming funciona con ese repositorio.
3. Esquema de transición de A6: fila `f` = `PostFrame(f)` + `PreFrame(f)` de ambos puertos, copia LAST en rollback, mandos crudos de ambos, `frame_id`, semilla, `n_rollback_copies`, `terminated/truncated/invalid` [CITA A6 §5; A4 §1.1 y §1.4].
4. Identidad de partida por sha1, deduplicación entre carpetas, **split por partida antes de ventanear** [CITA A6 §6]. Test contrafactual no existe en esta etapa.
5. Líneas base triviales por campo y horizonte h ∈ {1, 4, 8, 16, 32}: persistencia, velocidad constante, mayoritaria condicionada a (acción, action_frame) [CITA A4 §2.3]. Métricas y desgloses de A4 §5.2 (acción solo en frames de cambio, eventos con ventana ±1/±3, contadores, IC bootstrap por partida).
6. Test de fuga de alineación: un modelo que recibe el mando de la misma fila no debe «leer la respuesta» (el fallo que sufrió MIMIC) [CITA A6 §1.1 y §3.2 «Off-by-one conocidos»].
7. Humo local de W0-S/E1-S y de la variante latente a ≤ 1M parámetros sobre ≤ 200 partidas, con SIGReg M=256 declarado como cambio de configuración, porque en CPU SIGReg M=1024 es el 72–83 % del paso [CITA A7 §0.4 y §7]. Solo valida código; no se interpreta.

**Entregable.** `dataset card` con hashes, cobertura de campos por versión de `.slp`, tabla de suelos triviales, y scripts reproducibles. Útil con independencia del resto: es el esquema de datos que cualquier brazo (BC, q, V̂, dinámica) necesita.

**Gate G0 (PROPUESTA).** Se pasa a la etapa 1 solo si se cumplen todos:
- ≥ 150 partidas Fox ditto válidas en local y recuento estimado de dittos por tarball suficiente para llegar a ≥ 1.000 en la etapa 1;
- ≥ 95 % de esas partidas tienen velocidades, `action_state_frame` y hitstun (versión de `.slp` suficiente [CITA A6 §5]); si no, se redefine el esquema y se declara;
- el test de fuga pasa (la exactitud con el mando de la misma fila no es anómalamente superior a la del mando de `f+1`);
- en el humo, W0-S supera a la mejor línea base trivial en exactitud de `action` en frames de cambio a h=1 (si no, hay un bug, no un resultado);
- el ciclo completo (carga → entrenamiento → métricas → tabla) corre sin intervención en < 1 h de CPU.

**Coste (HIPÓTESIS).** 12–20 horas-persona; 3–8 horas-CPU locales con ≤ 2 hilos y prioridad baja (servidor compartido con apps en producción); 0 €; < 1 GB en el segundo disco, nada en `/` (95 % usado [CITA A7 §1 y §4.3]).

**Decisión que desbloquea.** Alquilar o no la GPU. Decisión del usuario implicada: permiso de venv y de descarga de la muestra.

---

## 4. Etapa 1 — E1-S frente a JEPA latente, todo offline

**Objetivo.** Responder con el mínimo de brazos a dos preguntas separadas:
- (a) ¿aporta la parte latente/JEPA sobre predecir el estado estructurado explícito? (E1 frente a E1-S);
- (b) ¿aporta algún preentrenamiento predictivo sobre gastar el mismo cómputo en BC? (E1 y E1-S frente a E0b).

**Brazos (subconjunto mínimo de `evidence/A3/ablations.json` según A3 §4).** Mismo encoder de estado E, misma entrada, misma canonicalización, mismo split:
- **E0**: E aleatorio entrenado con BC. **E0b**: E0 con pasos extra de BC equivalentes al cómputo de preentrenamiento.
- **E1-S** = tronco de W0-S: predicción del siguiente estado explícito con cabezas por campo y multihorizonte [CITA A4 §2.2–2.3].
- **E1** = tronco de W1-L: predicción del siguiente embedding condicionada a los mandos de ambos + SIGReg, sin stop-grad, con decodificador de campos sobre `sg(ẑ)` solo para medir [CITA A4 §3.2].
- **E-rand-frozen** como suelo [CITA A3 §4].
- Predictor de W1-L: núcleo GRU o MLP, no el transformer de ventana, que no cabe en tiempo real en CPU y es 10–50× más caro por paso [CITA A7 §0.2 y §7; A5 §7 propone `W1-L-GRU`]. Esto cambia la capacidad respecto a LeWM y debe declararse.
- Barrido reducido (PROPUESTA): λ ∈ {0,03; 0,09} × D ∈ {128; 192} con una semilla, y después 3 semillas en la mejor configuración elegida con sondas en validación [CITA A3 §4 «Barridos» para el rango completo]. El protocolo pide ≥ 5 semillas por brazo aprendido [CITA A7 §4.2 «Por réplica», que remite a `06_EXPERIMENT_PROTOCOL.md` L67]; 3 es un recorte de piloto y se sube a 5 solo para confirmar un resultado que cambie la decisión.

**Tareas posteriores sobre el encoder congelado (las tres producen artefactos reutilizables).**
1. **BC propio**: NLL en test del mando propio de `f+1`.
2. **q, modelo del rival**: NLL en test del mando del rival, sobre historia visible [CITA A4 §4.1].
3. **V̂(x)**: valor offline con recompensa de stocks + daño y semivida de 8 s, definido sobre el estado estructurado para que sea el mismo evaluador en todos los brazos [CITA A2 D3; A5 §2.4]. Métricas: calibración y capacidad de ordenar.
4. Sondas por campo con techo (entrada cruda) y suelo (encoder aleatorio), más el test de pares mínimos, porque un probe lineal puede seguir aprobando con la invariancia a medio formar [CITA A3 §3.2 y §7 C5b].
5. Predicción multihorizonte por campo y evento a h ∈ {1, 4, 8, 16, 32} con rival oracle, frente a los suelos triviales de la etapa 0 [CITA A4 §5.2–5.3].
6. **Eficiencia de datos** (parte de la pregunta central del `01_MASTER_PROMPT.txt`): repetir 1–3 con el 10 %, 30 % y 100 % de las partidas etiquetadas para la cabeza, con el encoder preentrenado sobre el 100 %.

**Entregable.** Tabla E0 / E0b / E1 / E1-S / E-rand × {BC, q, V̂, sondas, multihorizonte} con IC bootstrap por partida; checkpoints de un BC pequeño, de q y de V̂; curvas de eficiencia de datos.

**Gate G1 (PROPUESTA; métrica primaria fijada antes de mirar test).**
- **G1-a, JEPA frente a explícito.** Los brazos latentes (E1, W1-L, B2 con J-T) continúan solo si E1 mejora a E1-S en ≥ 2 % relativo de NLL en al menos 2 de las 3 tareas (BC, q, V̂), con IC 95 % por partida que excluye 0, en ≥ 2 de 3 semillas, y sin violar los umbrales de rechazo de sondas de A3 §3.2. En caso contrario se cierran y W0-S/E1-S queda como único representante.
- **G1-b, preentrenamiento frente a cómputo.** Si ni E1 ni E1-S mejoran a E0b en ≥ 1 % relativo de NLL de BC (IC que excluye 0) con el 100 % de los datos **ni** con el 10 %, se concluye «el preentrenamiento predictivo no aporta a la representación offline en este corpus» y la única vía restante para un modelo del mundo es la planificación (etapas 2–3).
- Lectura obligada: un resultado negativo aquí es evidencia en contra, no una falsación en juego; uno positivo es condición necesaria, no suficiente [CITA `01_MASTER_PROMPT.txt`, distinción 10; A3 §4 «Interpretación»].

**Coste (HIPÓTESIS).** 20–35 horas-persona. Cómputo: ~25–30 entrenamientos cortos × 0,1–1 h de 4090 [CITA A7 §4.2 para la cifra por réplica] ⇒ 3–30 h de GPU; techo propuesto 30 h. A 0,3–0,7 USD/h supuestos ⇒ 1–21 USD, más 2–4 h de la misma instancia para descargar y parsear. Presupuesto: **10–25 €**, con parada dura a 30 €. Riesgo conocido: con modelos de 1–5M la GPU no se satura y manda el dataloader [CITA A7 §4.2]; mitigación: 1k partidas decodificadas (1,3–2,2 GB [CITA A7 §4.3]) precargadas en RAM/VRAM.

**Decisión que desbloquea.** Si «JEPA» sigue en el proyecto o se sustituye por predicción explícita; si merece la pena un B2 con PPO más adelante.

---

## 5. Etapa 2 — Descomposición rival / valor / dinámica, offline

**Objetivo.** Medir, sin simulador, cuánto podría aportar un rollout corto al evaluador y dónde se pierde ese aporte. Aprovecha los modelos de la etapa 1; casi no hay entrenamiento nuevo.

**Diseño (PROPUESTA mía, construida sobre A4 §5.3 y A5 §2.4/§6.3; no está en los informes con esta forma).** Para estados de test y T ∈ {8, 16, 32}, se predice el retorno descontado realizado con seis evaluadores:
1. `V̂(h_t)`: sin mirar adelante.
2. `Q̂(h_t, u^yo_{t+1..t+T})`: con la secuencia propia y sin rollout, el análogo offline de P0-Q [CITA A5 §1].
3. **Oráculo de futuro**: recompensa realizada en `[t, t+T)` + `γ^T V̂(x_{t+T} real)`. Es el análogo offline, en distribución, de la dinámica exacta con rival conocido.
4. `W + rival oracle`: lo mismo con `x̂_{t+T}` del modelo y los mandos reales del rival → pérdida por error de dinámica.
5. `W + q` con K ∈ {4, 8} hipótesis en lazo cerrado, agregando en utilidad y nunca en estado [CITA A4 §4.2–4.3, O2] → pérdida por incertidumbre del rival.
6. `W + rival UNK` (O1 marginal), solo diagnóstico [CITA A4 §4.3].

A la vez, las curvas error-vs-h de A4 §5.3 con rival oracle, O2 y O1, y la diferencia `I_full − I_human` a h=1.

**Límites que hay que escribir junto al resultado.** Solo cubre acciones que los humanos eligieron; no dice nada sobre candidatos contrafactuales de un planificador, que exigen verdad del simulador [CITA A6 §7; A4 §5.4]. El oráculo de futuro incluye el mando real del rival, por lo que es una cota optimista con etiqueta oracle [CITA `01_MASTER_PROMPT.txt`, «Restricciones de la comparación»].

**Entregable.** Una tabla «ganancia del oráculo sobre Q̂, y fracción retenida por cada sustitución» por T y por fase de juego (neutral, hitstun, fuera del escenario, borde, escudo [CITA A4 §5.2 desgloses]); q y V̂ evaluados por separado.

**Gate G2 (PROPUESTA).** Sea G la mejora relativa del oráculo de futuro (3) sobre Q̂ (2) en la métrica de retorno.
- Si G < 1 % o su IC 95 % incluye 0 para todo T ≤ 32: mirar adelante no informa al evaluador ni con futuro perfecto; se baja la prioridad de todo MPC y la etapa 3 solo se hace si el usuario quiere el simulador por otros motivos.
- Si G es apreciable pero `W + q` retiene < 25 % de G: el cuello es el rival. Se invierte en q (y en V̂), no en dinámica.
- Si `W + rival oracle` retiene < 50 % de G: el cuello es la dinámica aprendida; la etapa 3 se hace solo con S0 (simulador), sin brazos W.
- Si `W + q` retiene ≥ 50 % de G en algún T o en alguna fase (candidato natural: recuperación/borde, casi monoagente [CITA A5 §6.2 punto 2]): hay caso para pedir la ISO y pasar a la etapa 3 con W incluido.

**Coste (HIPÓTESIS).** 10–15 horas-persona; 3–10 h de GPU o inferencia en CPU alquilada; **3–8 €**.

**Decisión que desbloquea.** Si se le pide al usuario la ISO, y con qué brazos se entra en la etapa 3.

---

## 6. Etapa 3 — «S0-ceiling» con el simulador exacto (primera etapa con ISO)

**Objetivo.** El experimento más barato que falsifica en juego, tal como lo define A5: si la búsqueda con dinámica exacta no supera al control sin rollouts, ningún modelo aprendido con los mismos candidatos, q y V̂ puede hacerlo [CITA A5 §6.3 y §0.7].

**Requisitos nuevos.** ISO NTSC 1.02 propia para extraer los datos del motor [CITA `evidence/A1/SYSTEM_MAP.md` §8; A6 §8]; compilar el simulador en Linux; el cambio para pasar el `World` al agente, que hoy no existe [CITA A5 §7 primer punto; A4 §8]. Todo ello es CPU: no hace falta GPU.

**Trabajo.**
1. Medir primero, no suponer: `python -m melee_brute bench` en la máquina donde se vaya a correr [CITA A5 §4]. Ninguna latencia del simulador está medida aquí.
2. Brazos de A5 §6.3: política/prior (Faynt-10M-Expert si no hay B1 propio) frente a **P0-Q** frente a **S0**, con N=16, K=4 (q = copia del prior, ditto), T=16, el mismo V̂(x) de la etapa 1, en `--mode sim`, reloj en pausa, igual conteo. Calendario piloto: 40 partidas por brazo.
3. Panel offline de regret de decisión (~2.000 estados, mismas N, K, T): regret del argmax de W0-S (y de W1-L si pasó G1-a) frente al argmax de S0 [CITA A5 §6.3; A4 §5.4 C1].
4. Si hay `.slp` crudos compatibles, «replay-to-reach» (C2) para ramificar desde estados humanos [CITA A4 §5.4].

**Entregable.** Resultado S0 − P0-Q con IC por bloque emparejado; panel de regret; el parche de integración del `World`; la cifra medida de µs/frame del simulador en hardware propio.

**Gate G3.**
- [CITA A5 §6.3] Si S0 − P0 ≤ 0 (IC 95 % por bloque emparejado) o la mejora queda bajo el umbral preregistrado, se cierra W0/W1 para MPC y se redirige a S-teach (etiquetado por búsqueda) o W2.
- PROPUESTA de umbral: mejora mínima de +0,3 stocks de diferencial medio por partida. Aviso de potencia: con 40 partidas el semiancho del IC 95 % de una tasa de victoria ronda ±15 puntos (cálculo binomial mío), así que un resultado ambiguo se resuelve ampliando a 120 partidas por brazo antes de concluir.
- Si S0 > P0-Q: W continúa solo si su regret en el panel es menor que el de P0-Q [CITA A5 §6.3 segundo punto].

**Coste (HIPÓTESIS).** 30–50 horas-persona, casi todo integración. Cómputo ≈ 20 horas-núcleo para 120 partidas según la estimación de A5 §6.3 (basada en cifras documentadas en otra CPU, no medidas): en local con 2 núcleos a prioridad baja serían ~10 h de pared repartidas, o ~1–2 h en una instancia de 16 núcleos alquilada. **0–10 €**. Subir la ISO a una máquina alquilada es decisión del usuario; la alternativa de 0 € es correrlo todo en local.

**Decisión que desbloquea.** Si existe la etapa 4, y con qué familia (W, S-teach, o nada).

---

## 7. Etapa 4 (opcional) — Partida bajo reloj y entrante de bench

Solo si G3 fue positivo **y** el usuario quiere un entrante. Contenido: envoltorio de plazo tipo bot-writer con fallback y trazas, porque el bench no impone el plazo de 16,67 ms a un agente every-frame [CITA A7 §0.1 y §2.3]; W frente a S0 frente a P0 a igual tiempo; regímenes `RT-strict`, `RT-slow` y `untimed` reportados por separado; Dolphin.

Límites duros ya medidos en esta CPU: con plazo de 16 ms caben, a p99, GRU-1M con K=64×T=16 o MLP-1M con K=16×T=8; a 15M nada [CITA A7 §0.2 y §4.1]. Faynt-10M como prior más rollouts no cabe en 16 ms con 4 vCPU compartidas [CITA A7 §4.1; A5 §0.5].

Coste (HIPÓTESIS): 60–120 horas-persona; la evaluación domina: ≈ 9,8 h de Dolphin a 60 fps en serie por brazo y reloj [CITA A7 §0.6]; 30–80 € si se alquila CPU/GPU para paralelizar. Un B1 propio con PPO queda fuera de este presupuesto; como referencias externas de RL e imitación se usan Faynt-10M-Arena y Expert [CITA A2 D1].

---

## 8. Decisiones que son del usuario

| # | Decisión | Por defecto que propongo | Qué cambia |
|---|---|---|---|
| 1 | Permiso para crear un venv con `peppi_py`/`zstandard` y descargar una muestra de replays en el segundo disco | Sí, ≤ 1 GB local | Sin esto no arranca la etapa 0 [CITA A7 §5 punto 3] |
| 2 | Techo de gasto de GPU | 35 € para las etapas 1–2, con parada dura | Con menos de ~10 € se recorta a 1 semilla y el resultado solo es orientativo |
| 3 | Aportar una ISO NTSC 1.02 propia, y si puede salir de la máquina local | Decidir tras G2 | Sin ISO el proyecto termina en la etapa 2 con una respuesta solo offline |
| 4 | Personaje y escenario | Fox ditto; escenario único (Final Destination) en el piloto | Otro matchup obliga a otro filtrado y no coincide con lo que fuerza el bench |
| 5 | Objetivo: responder la pregunta científica o publicar un entrante en Melee Bench | Pregunta científica | El entrante añade la etapa 4, el envoltorio de plazo y 5 semillas por brazo |
| 6 | Régimen de información primario: `I_full` (el agente ve el mando actual del rival, lo que hoy reciben los agentes del bench) o `I_human` | `I_full` primario, `I_human` como ablación a h=1 | [CITA A4 §4.4]; afecta a q y a la comparabilidad con slippi-ai |
| 7 | Tolerancia de licencias de datos | Solo `melee-ranked-replays` (MIT declarada, derechos de origen desconocidos); evitar HAL MDS (`license: other`, connect codes de jugadores reales) | [CITA A6 §2 y §10]. Importa si se publica algo |
| 8 | Código reutilizado | Copias MIT de `SIGReg` (le-wm o LeVJEPA); no la librería `lejepa` (CC BY-NC) | [CITA A3 §5] |

---

## 9. Qué queda aunque la respuesta sea «no»

- Etapa 0: tubería `.slp` → esquema de transición completo con split por partida y test de fuga; suelos triviales por campo y horizonte.
- Etapa 1: un BC pequeño, un modelo del rival q y un valor V̂ evaluados por separado. Son las piezas que A4 y A5 señalan como valiosas con independencia del resultado de la dinámica [CITA A4 §6.2 conclusión; A5 §7], y sirven igual para S0, para S-teach o como priors de otro bot.
- Etapa 2: una medida de cuánto pesa la incertidumbre del rival frente a la de la dinámica por horizonte y fase.
- Etapa 3: la integración del `World`, la velocidad medida del simulador en hardware propio y la cota superior S0, que es además el punto de partida de la vía «búsqueda como maestro» que el propio autor de melee-llm propone [CITA A5 §1, fila S-teach].

## 10. Qué no haría con este presupuesto

- Píxeles, encoders de vídeo o pesos JEPA publicados: no hay ninguno reutilizable para estado [CITA A3 resumen §5 y §5].
- El `ARPredictor` transformer de tamaño LeWM (10,8M) en CPU: 50–300× más lento por frame-candidato que el simulador [CITA A4 §6.1].
- Entrenar aquí más que humo: 1k partidas × 10 épocas son 37 h con MLP-1M [CITA A7 §0.5].
- Un B1 con PPO propio o un W2 tipo Dreamer antes de G3: exigen ISO y GPU, y mientras el simulador corra genera experiencia exacta más rápido [CITA A4 §6.2].
- Citar cifras cruzadas publicadas como fuerza esperada: casi todas llevan asimetría de retraso [CITA A2 §1.5].

## 11. Dudas abiertas y puntos débiles de esta propuesta

- Todos los umbrales de G0–G3 son míos y no están calibrados; el 1–2 % relativo de NLL puede ser menor que la varianza entre semillas. Hay que estimar esa varianza con E0 antes de congelarlos. A8 trabaja en paralelo y puede contradecirlos.
- La etapa 2 es un diseño nuevo; su validez como predictor del resultado de la etapa 3 es una HIPÓTESIS. Su valor es descartar barato, no confirmar.
- No sé cuántos Fox ditto hay por tarball, ni la velocidad de `peppi_py` en esta CPU, ni el tamaño real de cada tarball.
- 1k partidas pueden ser pocas para que el preentrenamiento muestre efecto; la curva de eficiencia de datos de la etapa 1 lo detecta parcialmente, y la ampliación a 3k–10k multiplicaría el coste de GPU por 3–10.
- Contradicción entre informes que afecta al humo: A3 §1.3 llama «despreciable» al coste de SIGReg y A7 §0.4 mide que domina el paso en CPU para modelos de 1M. Para este plan vale A7.
- Los precios de GPU son los supuestos de A7 §4.2, sin verificar; el cambio USD/EUR lo trato como ≈ 1.
