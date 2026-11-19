# Investigación de JEPA y modelos del mundo para Melee

Fecha de corte: 19 de noviembre de 2026.

## Objetivo de aplicación

La pregunta de ingeniería es si aprender representaciones y consecuencias de acciones ayuda a jugar mejor, aprender con menos interacciones o decidir con menor coste. El resultado se compara con agentes por imitación, RL sin modelo de dinámica explícito y planificación mediante reglas del juego ya disponibles. El aprendizaje de un world model es una hipótesis de trabajo.

El destino principal es Super Smash Bros. Melee y el entorno de https://melee.m19182.dev. Las arquitecturas de robótica o control visual aportan ideas y código reutilizable; su rendimiento original no demuestra eficacia en este juego.

La primera decisión propuesta es separar dos estudios: control desde estado estructurado y control desde píxeles. El primero permite aislar dinámica y decisión. El segundo añade percepción, aliasing visual y coste de encoder. No deben mezclarse en una comparación que atribuya toda la diferencia a JEPA.

## Sistema existente

El proyecto de la web es https://github.com/mateo19182/melee-llm. Su README relaciona el sitio con su interfaz web; docs/bench.md y el registro de participantes describen los agentes y relojes. El sitio se utiliza como referencia de integración y evaluación, no como una arquitectura de IA única.

Documentos prioritarios:

- https://github.com/mateo19182/melee-llm/blob/main/README.md
- https://github.com/mateo19182/melee-llm/blob/main/docs/bench.md
- https://github.com/mateo19182/melee-llm/blob/main/docs/bots.md
- https://github.com/mateo19182/melee-llm/blob/main/docs/delay.md
- https://github.com/mateo19182/melee-llm/blob/main/docs/simulator.md
- https://github.com/mateo19182/melee-llm/blob/main/docs/architecture.md
- https://github.com/mateo19182/melee-llm/blob/main/melee_llm/bench/entrants.py

### Familias de participantes

| Familia | Función en la investigación |
|---|---|
| CPU del juego y bots programados | Controles y referencias de comportamiento. |
| MIMIC y clonación de comportamiento | Base para aprender de acciones humanas. |
| HAL | Imitación de datos humanos con condicionamiento por retorno y bloques de acciones. Investigar la frontera entre BC condicionada y offline RL. |
| Phillip II y Faynt Arena | Políticas con preentrenamiento y posterior RL; baselines relevantes. |
| Reyn | Política rápida que acepta orientación táctica; candidata a control jerárquico. |
| LLM live o paused | Macroacciones elegidas por un modelo general, con distintos relojes. |
| Coach | Un modelo lento orienta a una política rápida. |
| Bot-writer | El modelo genera el programa antes de su evaluación. |
| Jev | Selección entre opciones estructuradas; no es sinónimo de JEPA. |

Para las variantes exactas, consultar el registro y el adaptador, no inferir capacidades a partir del nombre de la familia. HAL predice mandos, lo cual no equivale a predecir estados. En la revisión inspeccionada, las integraciones no presentan un participante JEPA ni un world model aprendido que haga rollouts para planificar; los interiores de modelos externos requieren su propia auditoría.

### Versiones y procedencia

Conservar cuatro revisiones diferentes cuando existan: HEAD del repositorio, dependencia bloqueada, versión instalada descrita por el autor y revisión concreta de un experimento. No actualizar silenciosamente una dependencia y citar un resultado obtenido con otra.

En el corte consultado, melee-llm declara melee-brute en `090e54b048b7d51e82f9f6b551046c2ca8b130c7`, mientras el HEAD observado de ese repositorio es `9662ec973b9e077ff7b0ff89d6db950f53c11653`. El informe E31 cita a su vez la revisión abreviada `d3832724`; no se debe sustituir por ninguna de las anteriores al reproducirlo. Los registros completos y permalinks se encuentran en 04_SOURCES.json. El swarm debe regenerar su propio sources.lock.json si trabaja después de esta fecha.

### Relojes

docs/bench.md describe una escala con participantes real-time, untimed y agentes que actúan por fotograma. Un Elo relativo a los rivales del benchmark no es una medida universal de capacidad y su ancla no es un ranking humano. La puntuación mezcla evidencia bajo condiciones declaradas, no vuelve equivalentes los relojes.

Distinguir: frecuencia del motor, frecuencia de observación, frecuencia de decisión, duración de una acción, demora de red, cola deliberada de acciones y velocidad de la simulación. Medir el instante real en el que un mando cambia el juego.

## Conceptos que no deben confundirse

| Concepto | Objetivo o salida |
|---|---|
| BC | Predecir acciones de demostraciones. |
| RL | Mejorar una política según retorno. Puede ser online u offline y usar o no un modelo. |
| Política | Seleccionar acciones; puede contener memoria. |
| Valor o crítico | Estimar retorno o utilidad futura. |
| Modelo de dinámica | Predecir una distribución o representación de estados futuros dados acciones e historia. |
| Planificador | Comparar secuencias usando un modelo, un objetivo y un presupuesto. |
| JEPA | Aprendizaje predictivo entre representaciones; no siempre temporal. |
| LeJEPA | Objetivo autosupervisado con regularización SIGReg. |
| LeWorldModel | Dinámica latente condicionada a acciones con predicción y SIGReg, más planificación por objetivos. |
| Simulador conocido | Reglas programadas disponibles para ejecutar transiciones. |

El nombre model-free se refiere al uso de dinámica explícita en el algoritmo. No significa ausencia de red, memoria o conocimiento implícito. Un encoder JEPA seguido de PPO permite estudiar representaciones, pero no demuestra aprendizaje de un simulador. Una política entrenada con rollouts imaginados puede actuar sin búsqueda online.

## Bibliografía central y preguntas de transferencia

### JEPA y LeJEPA

I-JEPA aprende relaciones entre partes de imágenes; ofrece un ejemplo de JEPA no temporal. LeJEPA combina su objetivo predictivo con SIGReg para evitar representaciones degeneradas. Investigar qué invariancias introducen las vistas y cómo comprobar que no borran orientación, contacto, fases de animación o información necesaria para el mando.

- https://arxiv.org/abs/2301.08243
- https://arxiv.org/abs/2511.08544
- https://github.com/galilai-group/lejepa

La regularización de la distribución no garantiza conservar todos los detalles relevantes para control ni identifica automáticamente coordenadas físicas interpretables. Congelar, ajustar y entrenar conjuntamente el encoder son alternativas que requieren controles.

### LeWorldModel y V-JEPA

LeWorldModel es una referencia directa para la combinación de dinámica latente condicionada a acciones y SIGReg. Su planificación usa objetivos visuales. Melee requiere adaptar acciones, interacción entre dos jugadores, temporalidad y valoración de resultados. No basta con pedir que un embedding se aproxime a una captura de victoria.

V-JEPA 2 base aprende representaciones de vídeo sin acciones. V-JEPA 2-AC añade un predictor condicionado por acciones y propiocepción sobre un encoder congelado. Ese postentrenamiento robótico no viene adaptado a mandos de GameCube ni al ritmo de un combate. V-JEPA 2.1 permite investigar características densas y consistencia temporal; sus experimentos robóticos con postentrenamiento/control deben distinguirse de los checkpoints base del encoder.

- https://le-wm.github.io/
- https://arxiv.org/abs/2603.19312
- https://github.com/facebookresearch/vjepa2

El catálogo recoge enlaces oficiales de código y datos resueltos desde estas fuentes.

### Dreamer y MuZero

DreamerV3 entrena una política con trayectorias latentes imaginadas y actúa con su actor sin búsqueda online. Su entrenamiento del modelo sí incluye un decodificador de observaciones, que pueden ser píxeles. MuZero combina dinámica aprendida con búsqueda y objetivos de recompensa, valor y política sin necesitar reconstruir las observaciones. Son alternativas metodológicas; sus objetivos y usos de la dinámica deben distinguirse de los de JEPA.

- https://www.nature.com/articles/s41586-025-08744-2
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12003158/
- https://github.com/danijar/dreamerv3
- https://arxiv.org/abs/1911.08265

Estudiar pérdidas, reconstrucción o ausencia de ella, memoria, recompensa, rollout multietapa y forma de usar el modelo durante entrenamiento e inferencia. No trasladar de manera automática presupuestos de Atari, ajedrez o robótica a Melee.

### Predicción bajo retraso

At Human Speed estudia RL con un predictor para compensar demora en Melee. El proyecto actual distingue esa propuesta histórica del Phillip II integrado. Investigar la implementación exacta de cada checkpoint y cómo se alinean observación, decisión y ejecución.

- https://arxiv.org/abs/1810.07286
- https://github.com/mateo19182/melee-llm/blob/main/docs/delay.md

Mantener separado el futuro previsto por un predictor del futuro que ya puede calcularse avanzando el motor con acciones conocidas. Ambos siguen enfrentándose a incertidumbre sobre decisiones del rival.

## Simulación y planificación con reglas conocidas

Fuentes:

- https://github.com/kyhavlov/melee-sim-light
- https://github.com/mateo19182/melee-brute
- https://github.com/mateo19182/melee-brute/blob/main/API.md
- https://github.com/mateo19182/melee-brute/blob/main/BRUTE.md

El fork de búsqueda permite guardar estados, probar secuencias y deshacerlas. Sus búsquedas enumeran opciones, mejoran secuencias y examinan garantías bajo menús y horizontes definidos. Un rollback exacto del simulador no prueba que cualquier trayectoria coincida con Dolphin ni que se haya resuelto el juego completo.

El runtime `--mode sim` documentado no ofrece contrincantes CPU ni exporta replays `.slp`. Usar Dolphin para la referencia CPU 9 y las comprobaciones que necesiten un `.slp` producido por la partida. El motor necesita datos extraídos localmente de una ISO NTSC 1.02 aportada por el usuario; la ruta de rollback rápido del fork requiere Linux. Ver docs/simulator.md y BRUTE.md en las revisiones fijadas.

Auditar la dependencia efectivamente usada, RNG, botones mantenidos, cuantización, redondeo, hitlag, aterrizajes, agarres, muertes, transición entre partidas y truncamientos. Las pruebas de autor y sus excepciones deben permanecer atribuidas. Reproducir un conjunto mínimo de casos relevantes antes de generar grandes cantidades de experiencias.

El baseline con motor conocido es valioso, pero puede tener información privilegiada: memoria completa, RNG o estado interno no disponible en la observación. Declarar esa diferencia y diseñar un control con información equivalente. El adversario no debe convertirse en un oráculo gratuito de acciones futuras.

## Arquitecturas que merece la pena investigar

Estas son propuestas de estudio; no resultados observados.

### Política directa y control de representación

Reutilizar una política por imitación y un baseline PPO reproducible. Comparar encoder convencional y encoder preentrenado con objetivo JEPA igualando corpus offline, capacidad, receta de BC/PPO y presupuesto de interacción. Para aislar representación, excluir rollouts aprendidos de las actualizaciones de la política y de la decisión en inferencia; declarar y contrastar aparte cualquier pérdida auxiliar temporal o aprendizaje conjunto. Las trayectorias online pueden cambiar al cambiar la política: no exigir datos idénticos a costa de violar el entrenamiento on-policy de PPO.

Preguntas: ¿mejora generalización a rivales o retrasos?, ¿solo acelera el entrenamiento?, ¿depende de datos adicionales?, ¿preserva estados raros decisivos?

### Dinámica estructurada y MPC

Predecir campos de estado observable desde historia, acciones propias y una representación del rival. Optimizar secuencias cortas y ejecutar solo el primer segmento antes de volver a observar.

Es un control importante frente a una dinámica latente: permite comprobar si la complejidad del encoder y SIGReg aportan algo frente a un predictor más directo.

### Dinámica latente inspirada en LeWorldModel

Encoder de historia, predictor condicionado a acciones, objetivo predictivo y prevención de colapso. La representación debe conservar información de control. Añadir incertidumbre o varias hipótesis del rival cuando sea necesario; no promediar futuros incompatibles y tratarlos como uno físicamente válido.

No asumir que todos los métodos comparten mecanismo de anti-colapso, EMA o teacher. Reproducir el método que se dice evaluar y etiquetar las modificaciones.

### Imaginación y política rápida

Usar el modelo para producir trayectorias que entrenen una política, conservando una decisión rápida durante el juego. Auditar sesgo del modelo, explotación de fallos, longitud del rollout, mezcla con datos reales y actualización de la distribución.

No confundir una política entrenada así con un planificador que consulta múltiples futuros en cada frame.

### Híbrido con simulador o jerarquía

Combinar propuestas de una política, valor terminal y búsqueda corta; o usar un predictor para decisiones tácticas más lentas y una política rápida para el mando. Compararlo con el mismo generador de propuestas sin rollout. El híbrido solo se justifica si los controles atribuyen la mejora y el coste cabe en el reloj.

## Datos y acciones

La unidad de datos debe describir observación disponible, acción decidida, acción realmente aplicada, tiempos, siguiente observación, recompensa, fin de episodio y procedencia. Si hay mandos del rival registrados, se pueden usar para aprender transiciones conjuntas. Durante evaluación, su futuro real permanece oculto.

Separar partidas completas antes de crear ventanas. Mantener perspectivas de la misma partida en el mismo split, deduplicar repeticiones y registrar identidad y fecha cuando existan. Informar qué tipos de generalización están realmente reservados.

El espacio de acción incluye botones, sticks, gatillos y duración. Mantener pulsado no equivale a pulsar de nuevo. Las conversiones entre APIs tienen que comprobarse, no inferirse por nombres parecidos. Una macro, un input por frame y un bloque de acciones son unidades diferentes.

Los datos de demostraciones pueden cubrir muy mal acciones extrañas que un planificador comenzará a proponer. Evaluar cobertura y fallos fuera de distribución. Un test con secuencias humanas acertadas no prueba exactitud en contrafactuales arbitrarios.

## Evaluación causal de la mejora

El protocolo completo está en 06_EXPERIMENT_PROTOCOL.md. La matriz debe permitir responder por separado:

- ¿Ayuda el preentrenamiento de representaciones?
- ¿Ayuda aprender dinámica?
- ¿Ayuda hacer rollouts frente a usar la misma política o valor sin ellos?
- ¿Ayuda el espacio latente frente al estado estructurado?
- ¿Ahorra interacciones, tiempo o coste total?
- ¿Se mantiene la mejora con la misma información y retraso?
- ¿Funciona frente a rivales y escenarios que no intervinieron en la selección?

Medir fuerza por emparejamiento, victorias y empates, daño/vidas cuando aporten contexto, latencia hasta actuación, throughput, memoria, fallos y número de decisiones útiles. Reportar distribución e incertidumbre. El error latente es un diagnóstico, no el criterio principal de victoria.

La unidad de aleatoriedad del entrenamiento y la de las partidas son distintas. Varias partidas de un único checkpoint no equivalen a varias semillas de entrenamiento. Utilizar pareado cuando sea apropiado y remuestreo jerárquico que respete dependencias. Elegir tamaño de muestra y mejora mínima relevante antes del test.

Referencias metodológicas:

- https://arxiv.org/abs/2108.13264
- https://github.com/google-research/rliable

El repositorio rliable está archivado en el corte consultado; sirve como referencia metodológica y requiere verificar compatibilidad si se reutiliza.

## Recursos y secuencia de trabajo

El hardware disponible para la aplicación es un dato por verificar. No asumir una GPU concreta a partir de conversaciones antiguas ni de los experimentos del autor. El swarm debe registrar GPU, VRAM, RAM, CPU, almacenamiento, sistema operativo y versiones de controladores.

Propuesta de secuencia:

1. Auditoría de fuentes y versiones, sin entrenamiento.
2. Contrato de datos, reloj, observación y acciones.
3. Pruebas pequeñas de correspondencia del adaptador y control reproducible.
4. Baseline de imitación y PPO viable.
5. Dinámica estructurada compacta y control de planificación.
6. Dinámica latente y ablación de encoder, solo si las etapas anteriores están bien medidas.
7. Ampliar rivales, retrasos, escenarios o píxeles según la pregunta y el presupuesto.

Evitar descargar todo un corpus o un backbone grande antes de estimar almacenamiento, cobertura, coste y necesidad. Primero medir una muestra y expresar los costes como estimaciones con supuestos, nunca como garantías de viabilidad.

## Entregas del swarm

El coordinador debe entregar mapa de sistema, auditoría de fuentes, baselines, diseño comparado, protocolo, revisión crítica, recomendación final y registros de evidencia. Cada conclusión debe indicar qué la sostiene y qué observación la refutaría.

Un buen cierre localiza qué reutilizar y qué falta construir; no termina en una lista genérica de papers. Si el modelo aprendido no mejora la alternativa disponible, explicará en qué condiciones podría justificarse y qué evidencia falta para cambiar la decisión.

