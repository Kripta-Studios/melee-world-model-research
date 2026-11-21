# Síntesis: cuatro papers de noviembre de 2026 frente al plan de Melee

Fecha: 2026-11-21. Cuatro agentes, uno por paper. Cada uno leyó el PDF completo y los documentos del repo
(`DECISION.md`, `DESIGN.md`, `EXPERIMENT_PLAN.md`, los informes de E0). Los informes completos, con citas de sección
y tabla, están en esta carpeta. Las cifras de los papers son de sus autores y no se han reproducido. Los costes son
estimaciones sin medir.

## Veredicto

**Ninguno de los cuatro es clave.** Ninguno cambia la decisión de `decision/DECISION.md`. Dos son útiles y dos son
marginales.

| Paper | Qué es | Veredicto | Pieza del plan a la que afecta |
|---|---|---|---|
| [2611.25927](2611.25927.md) | Fast-JEPA: predice el resultado de una secuencia de acciones en una sola pasada, en vez de paso a paso | **Útil** | Latencia del predictor del presente; G1-dyn |
| [2611.21596](2611.21596.md) | SADL: término sin parámetros sobre la salida del encoder que evita el colapso de LeWorldModel/SIGReg | **Útil** | W1-L, validez de G1-jepa y G1-rep |
| [2611.24778](2611.24778.md) | Counterfactual World Models (Balestriero, LeCun y otros): corrección por residuo para el "qué pasaría si" | Marginal | Diagnóstico del 4,9 % de W0-S |
| [2611.19771](2611.19771.md) | JEPA4R: JEPA sobre nubes de puntos para manipulación robótica | Marginal | Nada central; ya trabajamos con estado exacto |

Por qué ninguno es clave (INFERIDO):

- **Lo que más falta es información, no método.** Con los mandos futuros reales, W0-S acierta la acción a 4
  frames en 0,639. Sin ellos, solo en 0,324, frente a 0,289 de la línea base: una reducción relativa del error del
  4,9 % (`evidence/E0/floors/FLOORS_REPORT.md` §4.1). Lo que falta es predecir al
  rival, y ninguno de los cuatro papers lo trata.
- **Dominio distinto.** Los cuatro trabajan sobre píxeles o robots con un solo agente. Ninguno incluye un rival
  adversario, eventos discretos de contacto ni tiempo real a 60 Hz.

## Qué incorporar al plan

Las cuatro propuestas son **PROPUESTA**: no están implementadas y deben entrar en el preregistro antes de entrenar
E1. Si se añaden después de ver resultados, no cuentan.

1. **Sonda de colapso en W1-L** (de SADL). Medir la varianza entre muestras, el rango efectivo y el coseno medio
   de los embeddings en la prueba de humo y en E1.
   - Si W1-L sale degradado, G1-jepa se declara inválida para esa receta, no negativa para el enfoque JEPA.
   - Solo entonces se activa SADL, y la decisión se toma antes de ver métricas de G1.
   - Hay que fijar el tipo de atención (MATH o Flash) y la precisión, porque el paper sitúa en Flash el
     disparador del colapso.
   - Coste: casi nulo; con SADL, unas 2–4 h de implementación más 0,5–1 h de GPU.
2. **Predictor del presente "directo"** (de Fast-JEPA). Una sola pasada a f+D, con la cola de mandos propia y
   K hipótesis del rival, en vez de K×(D+1) pasos.
   - Se añade al banco de latencia de E0 como núcleo nuevo.
   - Se refuta si con D=12 supera 10 ms p99 o no gana al menos 2× al GRU `fast`.
   - Como brazo de G1-dyn: W0-S entrenado a varios horizontes directos. Se refuta si no supera al W0-S actual a
     8 frames. Coste: 2–10 h de GPU.
3. **Diagnóstico de residuo** (de Counterfactual World Models, apéndice I), antes de aplicar G1-dyn y G1-q. Dice
   si la reducción del error del 4,9 % se queda corta porque el modelo está poco entrenado o porque falta información.
   Coste: menos de 4 h de GPU.
4. **Fijar en el preregistro** el tamaño de batch, el tipo de atención y la precisión. En JEPA4R, cambiar el batch
   mueve el resultado de 57,6 a 68,5.

Descartado o aplazado:

- **Nubes de puntos** (JEPA4R): no aportan nada sobre estado estructurado exacto.
- **Regla contrafactual por residuo como corrector en juego**: el paper muestra que empeora con contacto, que es
  justo el caso de los golpes de Melee. Medir esa interacción exige la ISO (E2, con melee-brute).

## Avisos

- 2611.19771: los metadatos del PDF apuntan a 2611.24778, pero el texto y la página abs son de JEPA4R. Se analizó
  JEPA4R.
- Fast-JEPA y SADL no publican código usable: el repo de Fast-JEPA solo trae un README sin licencia, y SADL no tiene
  repo. Counterfactual World Models sí publica código, con licencia MIT.
