# E0c: qué es predecible en Melee y qué no

2026-11-21. Lo motiva una observación del usuario: lo primero en un modelo del mundo es averiguar qué tiene sentido
predecir, no empeñarse en adivinar las decisiones del rival.

Etiquetas: **REP** (medido aquí), **INF** (inferido).
Código: `pilot/e0/predictability.py`, solo numpy y unos 2 min de CPU. Resultados: `predictability.json`.
Datos: 288 partidas Fox ditto de E0; tablas ajustadas en train (258 partidas) y evaluadas en val (12). El test no se lee.

## Método

Objetivo: la acción de cada jugador en f+k. Se usan predictores de mayoría por contexto, en tres niveles de
información:

| Nivel | Información que usa |
|---|---|
| **S** | Contexto mecánico en f: acción, frame dentro de la acción, en el aire, hitlag > 0, hitstun > 0 |
| **S+Up** | S más un resumen de los mandos **del propio jugador** en f+1…f+k: botones pulsados en la ventana y zona del stick |
| **S+Up+Uo** | Lo anterior más el mismo resumen de los mandos **del otro jugador** |

**Frame comprometido a k:** en train, la acción mayoritaria en f+k dado el contexto de f ocurre ≥ 95 % de las veces,
con n ≥ 20. Es una definición empírica: no usa tablas del juego.

## Resultados (REP, val, media de los dos puertos)

Las columnas "acierto" son en eventos (la acción cambia entre f y f+k) y miden el acierto de la acción en f+k.

| k (frames) | Frames comprometidos | Acierto con S | Con S+Up | Con S+Up+Uo | Acierto con S en comprometidos (todos los frames) | Acierto con S en decisión (todos los frames) |
|---|---|---|---|---|---|---|
| 1 | 53,5 % | 0,282 | 0,526 | 0,530 | 0,987 | 0,848 |
| 4 | 24,3 % | 0,251 | 0,479 | 0,483 | 0,986 | 0,672 |
| 7 (D=6) | 15,5 % | 0,249 | 0,455 | 0,456 | 0,987 | 0,570 |
| 13 (D=12) | 8,3 % | 0,201 | 0,394 | 0,395 | 0,990 | 0,426 |
| 19 (D=18) | 4,1 % | 0,183 | 0,345 | 0,345 | 0,993 | 0,340 |

Horizonte de compromiso en val, como fracción del tiempo de cada jugador: ≥ 1 frame el 53 %, ≥ 4 el 24 %, ≥ 7 el
16 %, ≥ 13 el 8 % y ≥ 19 el 4 %. Los dos jugadores están comprometidos ≥ 7 frames a la vez solo el 4,2 % del tiempo;
al menos uno de ellos, el 26,8 %.

## Lectura

1. **Hay dos regímenes muy distintos (REP).**
   - **Comprometido:** el estado basta para acertar ~99 % a cualquier horizonte, y ningún mando, propio o ajeno,
     añade nada (S = S+Up = S+Up+Uo). Es mecánica pura: hitstun, lag, animaciones.
   - **Decisión:** el acierto cae deprisa con el horizonte.
2. **El futuro de cada jugador depende de sus propios mandos, no de los del otro (REP).**
   - Con los mandos propios, el acierto en eventos casi se duplica (0,25 → 0,46 a k=7).
   - Los mandos del otro solo suman ≤ 0,004 a cualquier horizonte.
   - En este corpus, la interacción, es decir que te golpeen, apenas cambia qué acción haces en f+k una vez conocidos
     tus mandos. La salvedad es que el resumen de mandos es grueso y los golpes son eventos raros (INF).
3. **Del rival solo es predecible su ventana comprometida (INF a partir de 1 y 2).** Sus mandos no los conocemos.
   - Por mecánica, su futuro solo es predecible el 15 % del tiempo a 7 frames y el 8 % a 13.
   - El resto depende de sus decisiones. Cualquier modelo del rival solo puede dar una distribución, y la medida
     honesta es la calibración (NLL, ECE), no el acierto.
4. **Lo propio es casi determinista dados nuestros mandos (INF).**
   - Esa parte la cubre exactamente el simulador (melee-brute) cuando el estado es conocido.
   - El hueco de un modelo aprendido no está en "predecir qué pasa si pulso X", donde gana el simulador. Está en
     representar la incertidumbre del rival en sus puntos de decisión y en cuándo se abren y cierran sus ventanas
     comprometidas.
5. **Encaja con lo medido en E0 (REP, FLOORS_REPORT §8).** W0-S acierta 0,64 en eventos a 4 frames con los mandos
   reales de ambos jugadores, y 0,32 si mantiene los mandos actuales. Esa caída es justo la parte de decisión.

## Qué cambia en el plan (PROPUESTA; el preregistro está sellado y no se toca sin el usuario)

- **Desglose obligatorio** de todas las métricas de E1 en frames comprometidos y de decisión, como análisis
  secundario. Se ha pedido al código de E1 que lo emita. No cambia ninguna métrica decisora.
- **Para el rival en frames de decisión,** medir calibración (NLL, ECE), no acierto. G1-q ya decide con NLL frente a
  la marginal; la parte (ii) (acción del rival) debería leerse sobre todo en frames comprometidos.
- **Objetivo natural de un modelo tipo JEPA:** predecir en el latente lo predecible (estado comprometido, horizonte
  de compromiso, conjunto de acciones posibles) y no forzar el resto. Una sonda útil es si el latente de W1-L
  codifica el horizonte de compromiso del rival.
- **Si se quiere enmendar el preregistro con esto,** debe hacerse antes de entrenar E1 y con aprobación explícita.

## Límites

- 12 partidas de val (los conteos son de frames, no de partidas) y un solo bucket de habilidad (diamond-diamond).
- La definición de "comprometido" es empírica. Puede incluir hábitos casi universales además de mecánica, aunque el
  hecho de que los mandos no añadan nada en esos frames apunta a mecánica.
- Los predictores de mayoría con un resumen grueso de los mandos son una cota inferior de lo alcanzable con esa
  información. El modelo W0-S con los mandos reales llega más lejos (0,64 frente a 0,48 a k=4 en eventos).
