# Guía de la literatura científica

El catálogo completo, con URLs, revisiones y disponibilidad, está en 03_SOURCE_CATALOG.md y 04_SOURCES.json. Esta guía organiza las decisiones que esas lecturas deben permitir.

| Pregunta | Lecturas prioritarias | Salida del agente |
|---|---|---|
| ¿Qué aprende una JEPA? | B01, B02, B04, B06, B07 | Variables preservadas, objetivo, colapso e invariancias. |
| ¿Cómo convertir representación en dinámica? | B03, B05, B11, B13 | Acción, historia, paso temporal, predictor y rival. |
| ¿Cómo usar un mundo aprendido para actuar? | B03, B08, B09, B12 | MPC, búsqueda o política entrenada con imaginación. |
| ¿Qué aporta tener reglas disponibles? | A14, A36, B10, B22, R11 | Referencia con motor conocido y alcance de la búsqueda. |
| ¿Qué tiene de especial Melee? | B16, B17, B18, B19, B20, A25 | Acciones simultáneas, retraso, rival y corpus de juego. |
| ¿Cómo demostrar valor? | R01, R02, B13, B20 | Contrastes, incertidumbre y generalización. |

## Distinciones que deben quedar explícitas

Una representación útil y un predictor sensible a las acciones son componentes distintos. LeJEPA aporta una receta de aprendizaje de representaciones; LeWorldModel incluye dinámica y planificación por meta visual. El objetivo de ganar una partida debe definirse y verificarse por separado.

DreamerV3 aprende con imaginación y despliega un actor; su entrenamiento incluye reconstrucción de observaciones. MuZero aprende una dinámica para recompensa, política y valor y usa búsqueda. Los modelos base de vídeo, sus variantes condicionadas a acciones y sus checkpoints de control no son intercambiables.

La correspondencia entre una publicación y un repositorio debe probarse. Un README puede describir una reimplementación, una receta puede no incluir pesos y un enlace a un dataset puede no publicar todo el corpus utilizado. Registrar estas diferencias en SOURCE_AUDIT.md.

## Decisión recomendada para la investigación

Comenzar con estado estructurado, políticas existentes y una dinámica pequeña permite separar el problema de control del de percepción. La línea de píxeles se justifica cuando la pregunta requiera esa modalidad. Esta recomendación es una propuesta metodológica; el paquete no demuestra que un método supere a otro en Melee.
