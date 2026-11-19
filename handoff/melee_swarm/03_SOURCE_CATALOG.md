# Catálogo de fuentes para el swarm

Corte de consulta: 2026-11-19. 82 fichas, agrupadas por propósito. Abrir primero los permalinks cuando existan. Un enlace a pesos no significa que el binario haya sido descargado o que funcione en Melee.

## Cómo leer el catálogo

- `source_read`: Se leyó contenido primario relevante, documentación, código o abstract. No implica auditoría integral ni ejecución.
- `metadata`: Se verificó la publicación o identidad del recurso, pero no su contenido completo o binario.
- `unverified`: El contenido activo o la versión exacta no pudo comprobarse; queda señalado para el swarm.

Las comprobaciones de disponibilidad se hicieron por distintas rutas de acceso. Si dos fichas difieren en disponibilidad del mismo enlace, conservar el alcance de cada comprobación y verificarlo de nuevo al usarlo. Ninguna de estas etiquetas equivale a `REPRODUCIDO`.

## Orden de lectura

1. A02–A10, A13–A15 y A25: sistema, reglas, observaciones, acciones y reloj.
2. A20–A34 y R07–R09: políticas e interfaces ya integradas.
3. B01–B05, B08–B09 y B17: representación, dinámica, planificación y demora.
4. B11–B13, B16 y B22: alternativas y límites multiagente.
5. A18, A28, A43–A46 y R01–R06: datos, entrenamiento, evaluación e instrumentación.

## Plataforma Melee y políticas

### A01 · Melee × LLM, sitio público

Punto de entrada. Asociación repositorio y dominio probada por A02/A05; la web activa no pudo verificarse directamente.

- Fuente: [Melee × LLM, sitio público](https://melee.m19182.dev/) · `unverified`.

### A02 · Melee × LLM, README

Objetivo, modos de ejecución, dependencias generales y vínculo con el sitio.

- Fuente: [Melee × LLM, README](https://github.com/mateo19182/melee-llm/blob/main/README.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/README.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A03 · Melee Bench, protocolo y reloj

Una tabla, dos relojes, reglas Fox contra Fox, ancla CPU9, admisión de partidas, estimación Elo e intervalos.

- Fuente: [Melee Bench, protocolo y reloj](https://github.com/mateo19182/melee-llm/blob/main/docs/bench.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/bench.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A04 · Melee Bench, registro de participantes

Tipos, relojes, configuración, controles y scripts retirados. Registro público, no volcado del marcador desplegado.

- Fuente: [Melee Bench, registro de participantes](https://github.com/mateo19182/melee-llm/blob/main/melee_llm/bench/entrants.py) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/melee_llm/bench/entrants.py
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A05 · Documentación de la interfaz web

Asocia el dominio con la implementación y distingue la tabla, las partidas, los replays y /brute.

- Fuente: [Documentación de la interfaz web](https://github.com/mateo19182/melee-llm/blob/main/docs/web-ui.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/web-ui.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A06 · Arquitectura y ciclo de partida

Mapa hacia runner, bots, replays, componentes de observación, evaluación y procesos.

- Fuente: [Arquitectura y ciclo de partida](https://github.com/mateo19182/melee-llm/blob/main/docs/architecture.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/architecture.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A07 · Simulador y pruebas de paridad

Modo sim y adaptadores. Los resultados de paridad son del autor, con condiciones sobre entradas y RNG.

- Fuente: [Simulador y pruebas de paridad](https://github.com/mateo19182/melee-llm/blob/main/docs/simulator.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/simulator.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A08 · Contrato de acciones de alto nivel

Macros, pad y ejecutor determinista por fotograma.

- Fuente: [Contrato de acciones de alto nivel](https://github.com/mateo19182/melee-llm/blob/main/melee_llm/actions.py) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/melee_llm/actions.py
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A09 · Contrato de observaciones

Transforma GameState en observación y texto; separa campos del juego y contexto calculado.

- Fuente: [Contrato de observaciones](https://github.com/mateo19182/melee-llm/blob/main/melee_llm/state.py) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/melee_llm/state.py
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A10 · Adaptador simulado de eventos Slippi

Genera eventos para reutilizar los parsers que esperan los bots; incluirlo en pruebas de paridad.

- Fuente: [Adaptador simulado de eventos Slippi](https://github.com/mateo19182/melee-llm/blob/main/melee_llm/sim/slippi.py) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/melee_llm/sim/slippi.py
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A11 · Vectorización en el entrenamiento

Lotes de partidas, observaciones y adaptación a GameState o a eventos Slippi.

- Fuente: [Vectorización en el entrenamiento](https://github.com/mateo19182/melee-llm/blob/main/train/farm/common.py) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/train/farm/common.py
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A12 · Experimentos de entrenamiento del proyecto

Punto de entrada a clonación, sensibilidad al retraso, afinado RL y comprobaciones del simulador.

- Fuente: [Experimentos de entrenamiento del proyecto](https://github.com/mateo19182/melee-llm/blob/main/docs/experiments/README.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/experiments/README.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A13 · Dependencias del proyecto

Manifiesto del runtime y revisión configurada del simulador; no reemplaza a un lockfile.

- Fuente: [Dependencias del proyecto](https://github.com/mateo19182/melee-llm/blob/main/pyproject.toml) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/pyproject.toml
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A14 · Melee Brute, contratos de búsqueda

Take-back, menús de acciones, horizontes acotados, prueba de primer golpe y defensa, límites del simulador.

- Fuente: [Melee Brute, contratos de búsqueda](https://github.com/mateo19182/melee-brute/blob/main/BRUTE.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-brute/blob/9662ec973b9e077ff7b0ff89d6db950f53c11653/BRUTE.md
- Revisión observada: `9662ec973b9e077ff7b0ff89d6db950f53c11653`.

### A15 · Melee Sim Light, upstream

Motor C derivado de la descompilación. API Python/NumPy y datos de una ISO aportada por el usuario.

- Fuente: [Melee Sim Light, upstream](https://github.com/kyhavlov/melee-sim-light) · `source_read`.
- Referencia fijada: https://github.com/kyhavlov/melee-sim-light/tree/eea7b5fbcd0243baf4c1956d52f3e1d0f536edc4
- Revisión observada: `eea7b5fbcd0243baf4c1956d52f3e1d0f536edc4`.
- Licencia indicada por metadatos: GitHub no declara licencia; verificar derechos. Comprobar alcance en la fuente.

### A16 · libmelee, fork usado por el proyecto

Frontera entre el runner, Slippi y el mando. Este SHA es HEAD de master, no la identidad de todos los parsers o de la versión instalada.

- Fuente: [libmelee, fork usado por el proyecto](https://github.com/vladfi1/libmelee) · `source_read`.
- Referencia fijada: https://github.com/vladfi1/libmelee/tree/bce21f09984b286e6d36bfd2939e4cd4691f94c2
- Revisión observada: `bce21f09984b286e6d36bfd2939e4cd4691f94c2`.
- Licencia indicada por metadatos: LGPL-3.0 (API). Comprobar alcance en la fuente.

### A17 · Slippi Dolphin

Repositorio actual del emulador. La rama slippi y su HEAD difieren de la AppImage fijada declarada en A47.

- Fuente: [Slippi Dolphin](https://github.com/project-slippi/dolphin) · `metadata`.
- Referencia fijada: https://github.com/project-slippi/dolphin/tree/accd20faa0017338654783e5e3421969e8ddf056
- Revisión observada: `accd20faa0017338654783e5e3421969e8ddf056`.
- Licencia indicada por metadatos: NOASSERTION (GitHub API; consultar COPYING). Comprobar alcance en la fuente.

### A18 · Formato de Slippi

Esquema binario para contrastar los eventos de .slp con el adaptador simulado y el parser.

- Fuente: [Formato de Slippi](https://github.com/project-slippi/slippi-wiki/blob/master/SPEC.md) · `source_read`.
- Referencia fijada: https://github.com/project-slippi/slippi-wiki/blob/3a85ce8b1f2dae1b487b2529a43c80f5de5885a3/SPEC.md
- Revisión observada: `3a85ce8b1f2dae1b487b2529a43c80f5de5885a3`.

### A19 · Descompilación de Melee

Origen del motor de juego. La disponibilidad pública no concede derechos sobre ISO, datos o activos.

- Fuente: [Descompilación de Melee](https://github.com/doldecomp/melee) · `metadata`.
- Referencia fijada: https://github.com/doldecomp/melee/tree/2f8eab8ebd7a2d25541e125abfa246defe1bacec
- Revisión observada: `2f8eab8ebd7a2d25541e125abfa246defe1bacec`.

### A20 · HAL

Código de HAL, imitación de partidas humanas y predicción de mandos. El proyecto usa este prefijo.

- Fuente: [HAL](https://github.com/ericyuegu/hal) · `source_read`.
- Referencia fijada: https://github.com/ericyuegu/hal/tree/37045d974116405dd690efea6109a1d83a2da868
- Revisión observada: `37045d974116405dd690efea6109a1d83a2da868`.
- Licencia indicada por metadatos: Sin licencia detectada por GitHub. Comprobar alcance en la fuente.

### A21 · HAL, checkpoint público

Pesos HAL publicados. El identificador del Hub fija revisión, no licencia del código o datos de origen.

- Fuente: [HAL, checkpoint público](https://huggingface.co/ericyuegu/hal-base-250m-rc) · `source_read`.
- Referencia fijada: https://huggingface.co/ericyuegu/hal-base-250m-rc/tree/e7fb8378ae15011cb0a414c16a8e5ac8b951fa63
- Revisión observada: `e7fb8378ae15011cb0a414c16a8e5ac8b951fa63`.
- Licencia indicada por metadatos: MIT (ficha). Comprobar alcance en la fuente.

### A22 · HAL, informe de entrenamiento

Describe enfoque y tamaño del corpus, arquitectura, agrupación de acciones y sensibilidad al retraso. Ver A46 para datos procesados; revisar condiciones del material de origen.

- Fuente: [HAL, informe de entrenamiento](https://ericyuegu.com/hillclimbing-melee/) · `source_read`.

### A23 · Phillip II / Slippi-AI

Proyecto moderno de imitación y revisión con RL. El retraso se modela con cola de acciones.

- Fuente: [Phillip II / Slippi-AI](https://github.com/vladfi1/slippi-ai) · `source_read`.
- Referencia fijada: https://github.com/vladfi1/slippi-ai/tree/5ada33e90c6c87fe83a1fb2d1a8105a96fd7b05b
- Revisión observada: `5ada33e90c6c87fe83a1fb2d1a8105a96fd7b05b`.
- Licencia indicada por metadatos: MIT (API). Comprobar alcance en la fuente.

### A24 · Phillip II, checkpoints ONNX

Modelo por nivel y personaje. index-v1.json indica hashes, tamaño y retraso de cada peso.

- Fuente: [Phillip II, checkpoints ONNX](https://huggingface.co/vladfi/phillip-models) · `source_read`.
- Referencia fijada: https://huggingface.co/vladfi/phillip-models/tree/a5045c5347ec6788a0d6f0801cb8483b3e8d47ce
- Revisión observada: `a5045c5347ec6788a0d6f0801cb8483b3e8d47ce`.
- Licencia indicada por metadatos: MIT (ficha). Comprobar alcance en la fuente.

### A25 · Tratamiento del retraso, ramas históricas y actuales

Distingue la predicción de estado de Firoiu 2018 del método recurrente sin predictor separado en Phillip II.

- Fuente: [Tratamiento del retraso, ramas históricas y actuales](https://github.com/mateo19182/melee-llm/blob/main/docs/delay.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/delay.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A26 · MIMIC, repositorio

HEAD encontrado. Integración declara bdfb6293c6709462b77647714b65952d190c116f. El proyecto explora RL; el checkpoint fox de la tabla se cataloga como clonación.

- Fuente: [MIMIC, repositorio](https://github.com/erickfm/MIMIC) · `source_read`.
- Referencia fijada: https://github.com/erickfm/MIMIC/tree/3691f534194f9c2ec52f131c8ab96e3d8674c3fa
- Revisión observada: `3691f534194f9c2ec52f131c8ab96e3d8674c3fa`.
- Licencia indicada por metadatos: MIT (API). Comprobar alcance en la fuente.

### A27 · MIMIC, checkpoints

Ficha y checkpoints por personaje; la variante fox está catalogada como fox-20260420-baseline.

- Fuente: [MIMIC, checkpoints](https://huggingface.co/erickfm/MIMIC) · `source_read`.
- Referencia fijada: https://huggingface.co/erickfm/MIMIC/tree/f49879b67abb64cd7fa76ea033f846fee45571e5
- Revisión observada: `f49879b67abb64cd7fa76ea033f846fee45571e5`.
- Licencia indicada por metadatos: MIT (ficha). Comprobar alcance en la fuente.

### A28 · Melee Ranked Replays

Corpus Slippi enlazado por MIMIC y Faynt. Verificar splits, duplicados entre perspectivas, opt-outs y derechos antes de ingesta.

- Fuente: [Melee Ranked Replays](https://huggingface.co/datasets/erickfm/melee-ranked-replays) · `source_read`.
- Referencia fijada: https://huggingface.co/datasets/erickfm/melee-ranked-replays/tree/ef54ddc230e01373ff2a179b49a7e559af788081
- Revisión observada: `ef54ddc230e01373ff2a179b49a7e559af788081`.
- Licencia indicada por metadatos: MIT (ficha). Comprobar alcance en la fuente.

### A29 · Faynt Tournament

Runtime de la política y evaluación con cruces de espejo. Coincide con el prefijo documentado.

- Fuente: [Faynt Tournament](https://github.com/Na00s/Faynt-Tournament) · `metadata`.
- Referencia fijada: https://github.com/Na00s/Faynt-Tournament/tree/d20961761814caf01f5db19c945d00ab757730ea
- Revisión observada: `d20961761814caf01f5db19c945d00ab757730ea`.
- Licencia indicada por metadatos: MIT (API). Comprobar alcance en la fuente.

### A30 · Faynt 10M-Arena

Checkpoint del benchmark. Preentrenamiento humano, currículo y PPO en encuentros Fox espejo; comparar con sus controles sin PPO.

- Fuente: [Faynt 10M-Arena](https://huggingface.co/frisson-labs/Faynt-10M-Arena) · `source_read`.
- Referencia fijada: https://huggingface.co/frisson-labs/Faynt-10M-Arena/tree/96929127f522c3fe3fc4721bb6fd6f0236e06888
- Revisión observada: `96929127f522c3fe3fc4721bb6fd6f0236e06888`.
- Licencia indicada por metadatos: MIT (ficha). Comprobar alcance en la fuente.

### A31 · Reyn

Inferencia de política y traducción de frases a órdenes de un catálogo, separado del entrenador LLM.

- Fuente: [Reyn](https://github.com/frisson-labs/Reyn) · `metadata`.
- Referencia fijada: https://github.com/frisson-labs/Reyn/tree/93fa52742e43a3115a990211b3aebb31671d8fdc
- Revisión observada: `93fa52742e43a3115a990211b3aebb31671d8fdc`.
- Licencia indicada por metadatos: MIT (API). Comprobar alcance en la fuente.

### A32 · Reyn-26C, pesos

Política condicionada por instrucciones y ficha de órdenes. No equivale a un predictor de transiciones.

- Fuente: [Reyn-26C, pesos](https://huggingface.co/frisson-labs/Reyn-26C) · `source_read`.
- Referencia fijada: https://huggingface.co/frisson-labs/Reyn-26C/tree/6a46ac79f33f80e00c262e8e91abd6cb9c38f4cf
- Revisión observada: `6a46ac79f33f80e00c262e8e91abd6cb9c38f4cf`.
- Licencia indicada por metadatos: MIT (ficha). Comprobar alcance en la fuente.

### A33 · Jev en el proyecto

Modelo TypeSafe que elige macros o comandos tácticos. Jev y JEPA designan tecnologías distintas.

- Fuente: [Jev en el proyecto](https://github.com/mateo19182/melee-llm/blob/main/docs/jev.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/jev.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A34 · Integración de entrenador y política

El entrenador cambia la estrategia; Reyn ejecuta cada fotograma. Control aleatorio y órdenes fijas.

- Fuente: [Integración de entrenador y política](https://github.com/mateo19182/melee-llm/blob/main/docs/coach.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/coach.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A35 · Hallazgos del proyecto y nombres de modos

Explica reproducción de acciones, familias de bots y experimentos de uso de LLM.

- Fuente: [Hallazgos del proyecto y nombres de modos](https://github.com/mateo19182/melee-llm/blob/main/writeup/melee-bench.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/writeup/melee-bench.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A36 · Análisis de juego óptimo

Define sondas y búsqueda adversarial sobre el simulador, con menús y horizontes explícitos.

- Fuente: [Análisis de juego óptimo](https://github.com/mateo19182/melee-llm/blob/main/docs/optimal-play.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/optimal-play.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A37 · Modo y dependencias de entrenamiento

Paquetes del entorno de entrenamiento de la política de referencia.

- Fuente: [Modo y dependencias de entrenamiento](https://github.com/mateo19182/melee-llm/blob/main/train/pyproject.toml) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/train/pyproject.toml
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A38 · Faynt Benchmarks

Suite externa para contrastar protocolo y resultados de los autores de Faynt.

- Fuente: [Faynt Benchmarks](https://github.com/Na00s/Faynt-Benchmarks) · `metadata`.
- Referencia fijada: https://github.com/Na00s/Faynt-Benchmarks/tree/39bc007537501c16d6e2dac6f2bcaafe3b84a8c9
- Revisión observada: `39bc007537501c16d6e2dac6f2bcaafe3b84a8c9`.
- Licencia indicada por metadatos: MIT (API). Comprobar alcance en la fuente.

### A39 · Anuncios y protocolo Slippi

Sitio oficial de herramientas de la comunidad. Contrastar versiones con el código y las AppImage del repositorio.

- Fuente: [Anuncios y protocolo Slippi](https://slippi.gg/) · `metadata`.

### A40 · Compatibilidad de políticas propias

Carga el ONNX y adapta el controlador. Distingue retardo de política y retardo de consola.

- Fuente: [Compatibilidad de políticas propias](https://github.com/mateo19182/melee-llm/blob/main/melee_llm/bots/bot_phillip.py) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/melee_llm/bots/bot_phillip.py
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A41 · Ajuste PPO de HAL, ensayo E21

Ensayo explícitamente planificado en este pin. No reporta un resultado ni una nueva política pública.

- Fuente: [Ajuste PPO de HAL, ensayo E21](https://github.com/mateo19182/melee-llm/blob/main/docs/experiments/E21-hal-ppo.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/experiments/E21-hal-ppo.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A42 · Validación de paridad, ensayo E31

Ensayo del autor que separa paridad con replays y control de RNG; registrar exclusiones del dominio.

- Fuente: [Validación de paridad, ensayo E31](https://github.com/mateo19182/melee-llm/blob/main/docs/experiments/E31-sim-faithful.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/experiments/E31-sim-faithful.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A43 · Entorno de self-play y recompensa del bot propio

Calcula ventaja de stocks más diferencia de daño ponderada por fotograma y dispone de semillas y control de matchup.

- Fuente: [Entorno de self-play y recompensa del bot propio](https://github.com/mateo19182/melee-llm/blob/main/train/meleebot/rl/env.py) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/train/meleebot/rl/env.py
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A44 · Implementación PPO del bot propio

PPO con ventaja GAE, refuerzo de condición de stock/daño, KL hacia la política docente y bonificación de entropía condicionada.

- Fuente: [Implementación PPO del bot propio](https://github.com/mateo19182/melee-llm/blob/main/train/meleebot/rl/ppo.py) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/train/meleebot/rl/ppo.py
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A45 · Ingesta de replays y transporte de datos

Selecciona y parsea replays con peppi, separa validación por nombre de partida y empaqueta muestras. Asegurar agrupación y deduplicación externa si cambia la procedencia.

- Fuente: [Ingesta de replays y transporte de datos](https://github.com/mateo19182/melee-llm/blob/main/train/meleebot/build_dataset.py) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/train/meleebot/build_dataset.py
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A46 · Corpus público HAL en MosaicML Streaming

README de HAL lo enlaza como el corpus que entrenó HAL 250M. Revisar licencia individual de datos, filtros y splits.

- Fuente: [Corpus público HAL en MosaicML Streaming](https://huggingface.co/datasets/ericyuegu/hal-mds-dataset) · `metadata`.
- Referencia fijada: https://huggingface.co/datasets/ericyuegu/hal-mds-dataset/tree/46ca723efd1de791c06300ed62c9278ecdb2f34a
- Revisión observada: `46ca723efd1de791c06300ed62c9278ecdb2f34a`.
- Licencia indicada por metadatos: other (ficha API). Comprobar alcance en la fuente.

### A47 · Setup reproducible de versiones Dolphin

Fija AppImage oficial v4.0.0-mainline-beta.19 para render y 4.0.0-mainline-beta.14.1-ExiAI para headless.

- Fuente: [Setup reproducible de versiones Dolphin](https://github.com/mateo19182/melee-llm/blob/main/scripts/setup.sh) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/scripts/setup.sh
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### A48 · Dolphin, release renderizado

Release fijada por scripts/setup.sh; guardar huella del binario al reproducir.

- Fuente: [Dolphin, release renderizado](https://github.com/project-slippi/dolphin/releases/tag/v4.0.0-mainline-beta.19) · `metadata`.

### A49 · Dolphin ExiAI, release headless

Release fijada por scripts/setup.sh para headless. Esta versión y sus parches de entrada importan para medir fidelidad.

- Fuente: [Dolphin ExiAI, release headless](https://github.com/vladfi1/dolphin/releases/tag/4.0.0-mainline-beta.14.1-ExiAI) · `metadata`.

## Métodos y trabajos científicos

### B01 · I-JEPA · Assran et al. (2023)

Aprende a predecir embeddings de regiones ocultas de una imagen a partir del contexto visible. Evalúa clasificación, conteo y profundidad. Es una referencia para percepción desde píxeles. Para planificar en Melee hacen falta transiciones temporales y acciones.

- Fuente: [I-JEPA · Assran et al. (2023)](https://arxiv.org/abs/2301.08243) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2301.08243v3
- Proyecto: https://ai.meta.com/blog/yann-lecun-ai-model-i-jepa/ · `source_read`.
- Código y pesos: https://github.com/facebookresearch/ijepa · `source_read`.
- Peso ViT-H/14: https://dl.fbaipublicfiles.com/ijepa/IN1K-vit.h.14-300e.pth.tar · `metadata`.
- Datos de referencia: https://www.image-net.org/ · `unverified`.
- HEAD observado de `main`: `52c1ae95d05f743e000e8f10a1f3a79b10cff048` en https://github.com/facebookresearch/ijepa.

El sitio directo de ImageNet no respondió en esta revisión. El paper y la documentación del proyecto identifican el conjunto y las variantes usadas.

### B02 · LeJEPA y SIGReg · Balestriero y LeCun (2025)

Combina pérdida predictiva y regularización gaussiana isotrópica para limitar el colapso. Evalúa representaciones en ImageNet y otros conjuntos. Permite una ablación en un latente de juego. Hace falta aprender e inspeccionar dinámica condicionada a acciones para controlar la partida.

- Fuente: [LeJEPA y SIGReg · Balestriero y LeCun (2025)](https://arxiv.org/abs/2511.08544) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2511.08544v3
- Texto completo: https://arxiv.org/html/2511.08544v3 · `source_read`.
- Código canónico, documentación y recetas: https://github.com/galilai-group/lejepa · `source_read`.
- Datos de evaluación de referencia: https://www.image-net.org/ · `unverified`.
- HEAD observado de `main`: `c293d291ca87cd4fddee9d3fffe4e914c7272052` en https://github.com/galilai-group/lejepa.

El repositorio antiguo rbalestr-lab/lejepa redirige a galilai-group/lejepa. No se identificó un catálogo independiente de pesos oficiales para este trabajo.

### B03 · LeWorldModel · Maes et al. (2026)

Aprende dinámica latente desde píxeles y acciones continuas con MSE de próximo embedding y SIGReg. CEM busca una meta visual. Evalúa Push-T, Cube, Two-Room y Reacher. Para Melee falta adaptar acciones, objetivo y rival y demostrar latencia de extremo a extremo.

- Fuente: [LeWorldModel · Maes et al. (2026)](https://arxiv.org/abs/2603.19312) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2603.19312v3
- Método, control y límites, versión 3: https://arxiv.org/html/2603.19312v3 · `source_read`.
- Proyecto: https://le-wm.github.io/ · `source_read`.
- Código: https://github.com/lucas-maes/le-wm · `source_read`.
- Pesos y datos de los cuatro entornos: https://huggingface.co/collections/quentinll/lewm · `source_read`.
- Pesos Push-T: https://huggingface.co/quentinll/lewm-pusht · `source_read`.
- HEAD observado de `main`: `8edfeb336732b5f3ce7b8b210d0ba370a09e2cac` en https://github.com/lucas-maes/le-wm.

### B04 · V-JEPA 2 · Assran et al. (2025)

Preentrena un predictor de representaciones espacio-temporales enmascaradas con VideoMix22M, sin mandos. Evalúa reconocimiento y anticipación en conjuntos como Something-Something V2 y EPIC-KITCHENS. Comparar encoders congelados tiene sentido cuando el punto de partida del agente son píxeles.

- Fuente: [V-JEPA 2 · Assran et al. (2025)](https://arxiv.org/abs/2506.09985) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2506.09985v1
- Método y composición del preentrenamiento: https://arxiv.org/html/2506.09985v1 · `source_read`.
- Proyecto: https://ai.meta.com/research/vjepa/ · `source_read`.
- Código y recetas: https://github.com/facebookresearch/vjepa2 · `source_read`.
- Pesos y sondas: https://huggingface.co/collections/facebook/v-jepa-2 · `source_read`.
- HEAD observado de `main`: `204698b45b3712590f06245fbfba32d3be539812` en https://github.com/facebookresearch/vjepa2.

El paper describe la mezcla VideoMix22M y el README facilita recetas y pesos. No se verificó una descarga unificada de la mezcla de preentrenamiento.

### B05 · V-JEPA 2-AC · Assran et al. (2025)

Congela V-JEPA 2 y entrena predicción autorregresiva latente con historia visual, acciones y estado del efector. DROID aporta trayectorias. MPC por meta visual ejecuta alcance, agarre y recogida/colocación con Franka. Transferible como diseño, con acciones y métrica propias del juego.

- Fuente: [V-JEPA 2-AC · Assran et al. (2025)](https://arxiv.org/abs/2506.09985) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2506.09985v1
- Método, secciones 3–4: https://arxiv.org/html/2506.09985v1 · `source_read`.
- Proyecto: https://ai.meta.com/research/vjepa/ · `source_read`.
- Código, checkpoint y configuración AC: https://github.com/facebookresearch/vjepa2 · `source_read`.
- URL del peso AC publicada en el README: https://dl.fbaipublicfiles.com/vjepa2/vjepa2-ac-vitg.pt · `metadata`.
- Datos DROID: https://droid-dataset.github.io/ · `source_read`.
- HEAD observado de `main`: `204698b45b3712590f06245fbfba32d3be539812` en https://github.com/facebookresearch/vjepa2.

El URL del checkpoint está publicado por Meta. No se descargó ni validó el archivo binario.

### B06 · V-JEPA 2.1 · Mur-Labadia et al. (2026)

Combina pérdidas densas y supervisión intermedia para representaciones de imagen y vídeo. Para planificar requiere dinámica condicionada; una política directa puede usar su encoder. Los experimentos robóticos postentrenados y los pesos base son recursos distintos.

- Fuente: [V-JEPA 2.1 · Mur-Labadia et al. (2026)](https://arxiv.org/abs/2603.14482) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2603.14482v3
- Código y tabla de pesos 2.1: https://github.com/facebookresearch/vjepa2/blob/main/README.md · `source_read`.
- Proyecto de la familia: https://ai.meta.com/research/vjepa/ · `source_read`.
- Método y composición, versión 3: https://arxiv.org/html/2603.14482v3 · `source_read`.
- HEAD observado de `main`: `204698b45b3712590f06245fbfba32d3be539812` en https://github.com/facebookresearch/vjepa2.

El README común distingue la tabla 2.1 de los pesos 2 y 2-AC. No se verificó una descarga unificada de VisionMix163M.

### B07 · LeVJEPA · video pretraining (2026)

Estudia una receta de predicción autosupervisada en vídeo con SIGReg y evalúa representaciones en benchmarks visuales. Compara coste de preentrenamiento con V-JEPA 2. Orienta un encoder de vídeo si hiciera falta, con una cabeza de dinámica jugable por entrenar.

- Fuente: [LeVJEPA · video pretraining (2026)](https://arxiv.org/abs/2608.27395) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2608.27395v1
- Proyecto y evaluación: https://levjepa.github.io/ · `source_read`.
- Código canónico: https://github.com/MLO-lab/LeVJEPA · `source_read`.
- Pesos y preentrenamiento VideoMix: https://huggingface.co/galilai-group/LeVJEPA-VideoMix-Large · `source_read`.

### B08 · DreamerV3 · Hafner et al. (2025)

Aprende dinámica recurrente latente, observación, recompensa y continuación, y entrena actor-crítico con trayectorias imaginadas. Al interactuar selecciona con el actor sin búsqueda. Evalúa Atari, control, Crafter y Minecraft. En Melee habría que adaptar acciones, recompensas y generalización a rivales.

- Fuente: [DreamerV3 · Hafner et al. (2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12003158/) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2301.04104v2
- Publicación Nature: https://doi.org/10.1038/s41586-025-08744-2 · `source_read`.
- Proyecto: https://danijar.com/project/dreamerv3/ · `source_read`.
- Código enlazado por el artículo, descrito como reimplementación en su README: https://github.com/danijar/dreamerv3 · `source_read`.
- Preprint: https://arxiv.org/abs/2301.04104 · `source_read`.
- HEAD observado de `main`: `e01491fad6434b2245a3b8ca201dd7faedcc458c` en https://github.com/danijar/dreamerv3.

El trabajo genera experiencia en entornos simulados y no usa un conjunto de entrenamiento externo. No se identificaron pesos oficiales del paper en el proyecto o README.

### B09 · MuZero · Schrittwieser et al. (2020)

Aprende una dinámica sobre latentes condicionada a acciones para predecir recompensa, política y valor. Usa búsqueda en árbol al jugar. Evalúa Atari, Go, ajedrez y shogi. La búsqueda para mandos simultáneos requiere explicitar las respuestas rivales y limitar la ramificación.

- Fuente: [MuZero · Schrittwieser et al. (2020)](https://www.nature.com/articles/s41586-020-03051-4) · `source_read`.
- Versión del paper: https://arxiv.org/abs/1911.08265v2
- Preprint: https://arxiv.org/abs/1911.08265 · `source_read`.
- Proyecto: https://deepmind.google/research/alphazero-and-muzero/ · `source_read`.
- Entorno de evaluación Atari: https://ale.farama.org/ · `source_read`.
- Entornos de tablero: https://github.com/google-deepmind/open_spiel · `source_read`.

Nature remite al pseudocódigo y a los datos de figuras en Supplementary Information. No se localizó una implementación completa ni pesos originales de los experimentos en los enlaces de los autores.

### B10 · AlphaZero · Silver et al. (2018)

Usa reglas conocidas para la búsqueda y autojuego para entrenar política y valor con el resultado final. Evalúa ajedrez, shogi y Go. Inspira una comparación con el motor de Melee. Los turnos de tablero y los mandos simultáneos requieren búsquedas distintas.

- Fuente: [AlphaZero · Silver et al. (2018)](https://doi.org/10.1126/science.aar6404) · `source_read`.
- Copia institucional: https://discovery.ucl.ac.uk/id/eprint/10069050/ · `source_read`.
- Preprint preliminar: https://arxiv.org/abs/1712.01815 · `source_read`.
- Proyecto: https://deepmind.google/blog/alphazero-shedding-new-light-on-chess-shogi-and-go/ · `source_read`.

La copia institucional permite leer la publicación definitiva. No se localizaron pesos ni una implementación integral original en los enlaces de los autores.

### B11 · DINO-WM · Zhou et al. (2025)

Predice futuros parches de un encoder DINOv2 congelado con trayectorias y acciones. Optimiza secuencias hacia una meta visual sin modelar una recompensa. Evalúa laberintos, empuje y materiales deformables. Sirve como comparación visual si se necesita estimar dinámica desde vídeo.

- Fuente: [DINO-WM · Zhou et al. (2025)](https://proceedings.mlr.press/v267/zhou25t.html) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2411.04983v2
- Preprint: https://arxiv.org/abs/2411.04983 · `source_read`.
- Proyecto: https://dino-wm.github.io/ · `source_read`.
- Código: https://github.com/gaoyuezhou/dino_wm · `source_read`.
- Datos y pesos en el espejo del autor: https://huggingface.co/datasets/gaoyuezhou/dino_wm · `source_read`.
- HEAD observado de `main`: `0a9492fa12044b852ae9e001cc74604b79c8bb0c` en https://github.com/gaoyuezhou/dino_wm.

### B12 · TD-MPC2 · Hansen et al. (2024)

Optimiza trayectorias continuas en un latente sin decodificador. Aprende consistencia latente, recompensa y valor y usa una política como propuesta. Evalúa DMControl, Meta-World, ManiSkill2 y MyoSuite. Transferir MPC a Melee exige decidir cómo representar y proponer entradas híbridas.

- Fuente: [TD-MPC2 · Hansen et al. (2024)](https://arxiv.org/abs/2310.16828) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2310.16828v2
- Método: https://arxiv.org/html/2310.16828v2 · `source_read`.
- Proyecto: https://www.tdmpc2.com/ · `source_read`.
- Código: https://github.com/nicklashansen/tdmpc2 · `source_read`.
- Pesos: https://www.tdmpc2.com/models · `source_read`.
- Datos: https://www.tdmpc2.com/dataset · `source_read`.
- HEAD observado de `main`: `332f19e4aba4bffe2dc736f45ea7f7bdc585903a` en https://github.com/nicklashansen/tdmpc2.

### B13 · JEPA-WMs · Terver et al. (2025/2026)

Compara encoders, predictores, objetivos y planificación latente en navegación y manipulación simuladas y robóticas. Incluye comparaciones con DINO-WM y V-JEPA 2-AC. Ayuda a diseñar ablaciones separadas y prevenir que un buen error predictivo se confunda con buen control.

- Fuente: [JEPA-WMs · Terver et al. (2025/2026)](https://arxiv.org/abs/2512.24497) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2512.24497v4
- Código y datos: https://github.com/facebookresearch/jepa-wms · `source_read`.
- Pesos comparables y referencia de tareas: https://huggingface.co/facebook/jepa-wms · `source_read`.
- HEAD observado de `main`: `13cf1d9c7e476f53c17714d2e0f1dc239a883ce0` en https://github.com/facebookresearch/jepa-wms.

### B14 · Reinforcement Learning: An Introduction · Sutton y Barto (2018)

El capítulo 8 distingue experiencia del entorno, experiencia generada por un modelo y planificación. Sirve para clasificar entrenamiento directo con el motor, búsqueda sobre el motor y aprendizaje con trayectorias imaginadas. No es un benchmark de Melee.

- Fuente: [Reinforcement Learning: An Introduction · Sutton y Barto (2018)](https://www.andrew.cmu.edu/course/10-703/textbook/BartoSutton.pdf) · `source_read`.
- Página del libro de los autores, disponibilidad no confirmada: https://incompleteideas.net/book/the-book-2nd.html · `unverified`.

El espejo universitario abrió. El sitio del libro de los autores no respondió en esta revisión.

### B15 · PPO · Schulman et al. (2017)

Optimiza una política a partir de trayectorias mediante un objetivo sustituto con recorte de la razón de probabilidades. Evalúa Atari y locomoción simulada. Referencia model-free si el agente extrae experiencia del motor y aprende sin consultar predicciones de transición.

- Fuente: [PPO · Schulman et al. (2017)](https://arxiv.org/abs/1707.06347) · `source_read`.
- Versión del paper: https://arxiv.org/abs/1707.06347v2
- Proyecto: https://openai.com/index/openai-baselines-ppo/ · `source_read`.
- Código OpenAI Baselines: https://github.com/openai/baselines · `source_read`.
- HEAD observado de `master`: `ea25b9e8b234e6ee1bca43083f8f3cf974143998` en https://github.com/openai/baselines.

### B16 · Markov Games · Littman (1994)

Modela la transición con una acción de cada jugador. Presenta minimax-Q en un fútbol simplificado de suma cero. El marco ayuda a distinguir dinámica conjunta y política rival. La observación contemporánea del mando rival debe respetar la información disponible al decidir.

- Fuente: [Markov Games · Littman (1994)](https://aima.eecs.berkeley.edu/~russell/classes/cs294/f21/papers/Littman_ICML94_Markov_Games.pdf) · `source_read`.
- Ficha ICML: https://mlanthology.org/icml/1994/littman1994icml-markov/ · `source_read`.

### B17 · At Human Speed · Firoiu, Ju y Tenenbaum (2018)

Combina RL y predicción neuronal de estado para compensar acciones ya en cola. Evalúa directamente Melee con retardos y contra un profesional. Deja la planificación contrafactual y ambas acciones como trabajo futuro. Antecedente de predicción en Melee, sin evidencia de una JEPA.

- Fuente: [At Human Speed · Firoiu, Ju y Tenenbaum (2018)](https://arxiv.org/abs/1810.07286) · `source_read`.
- Versión del paper: https://arxiv.org/abs/1810.07286v1
- Paper, secciones 4–5: https://arxiv.org/pdf/1810.07286 · `source_read`.
- Código histórico del autor, correspondencia de versión sin verificar: https://github.com/vladfi1/phillip · `source_read`.

Phillip es un repositorio histórico del autor. La revisión exacta de los experimentos de 2018 y sus pesos quedan sin verificar.

### B18 · Beating the World's Best at Super Smash Bros. with DRL · Firoiu et al. (2017)

Entrena agentes de RL con estado de Melee y prueba contra profesionales. Referencia histórica de políticas directas, autojuego y velocidad de reacción. Al comparar resultados hay que controlar retardo, alcance de observación y conjunto de rivales.

- Fuente: [Beating the World's Best at Super Smash Bros. with DRL · Firoiu et al. (2017)](https://arxiv.org/abs/1702.06230) · `source_read`.
- Versión del paper: https://arxiv.org/abs/1702.06230v3
- Tesis MIT: https://dspace.mit.edu/entities/publication/bb6fbc26-f70d-4004-862a-3aac3fc7e9ed · `source_read`.
- Código Phillip: https://github.com/vladfi1/phillip · `source_read`.

### B19 · HAL MDS y HAL · Gu (2026)

Trae partidas humanas 1v1 derivadas de Slippi con estado, mandos e información de objetos. HAL ofrece una política entrenada con datos humanos. Útil para preentrenamiento y validación por partida. Separar juegos completos y comprobar cobertura antes de evaluar contrafactuales.

- Fuente: [HAL MDS y HAL · Gu (2026)](https://huggingface.co/datasets/ericyuegu/hal-mds-dataset) · `source_read`.
- Proyecto y resultados: https://ericyuegu.com/hillclimbing-melee/ · `source_read`.
- Código y esquemas: https://github.com/ericyuegu/hal · `source_read`.
- Pesos: https://huggingface.co/ericyuegu/hal-base-250m-rc · `metadata`.
- Formato primario Slippi: https://github.com/project-slippi/slippi-wiki/blob/master/SPEC.md · `source_read`.
- HEAD observado de `main`: `37045d974116405dd690efea6109a1d83a2da868` en https://github.com/ericyuegu/hal.

El README publica el identificador de pesos. La tarjeta directa de Hugging Face no abrió en esta revisión. La tarjeta del conjunto estuvo disponible, aunque su visor informa un error de generación.

### B20 · Faynt · Janati et al. (2026)

Transformers con estado estructurado, imitación y RL ajustado en duelos Fox. Publica pesos y comparativas de bots. Los rivales de la tabla principal conservan retardos y la comparación sin retardo usa un único checkpoint rival. Buena referencia de control y medición.

- Fuente: [Faynt · Janati et al. (2026)](https://arxiv.org/abs/2610.02144) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2610.02144v1
- Proyecto, evaluación y publicación: https://www.frisson-labs.com/faynt · `source_read`.
- Pesos: https://huggingface.co/collections/frisson-labs/faynt · `source_read`.
- Benchmarks y ejecución: https://github.com/Na00s/Faynt-Benchmarks · `source_read`.
- Torneos: https://github.com/Na00s/Faynt-Tournament · `source_read`.

El proyecto publica pesos, benchmark y runtime de torneos. No se confirmó acceso al conjunto íntegro de ~840 mil replays usado para entrenar.

### B21 · DROID · Khazatsky et al. (2024)

Conjunto de demostraciones robóticas con cámaras, acciones y estado del efector. Referencia de cómo empaquetar trayectorias sincronizadas de observación y mando para entrenar dinámica. Sus transiciones corresponden a manipulación, mientras que Melee necesita su propio conjunto con dos mandos.

- Fuente: [DROID · Khazatsky et al. (2024)](https://arxiv.org/abs/2403.12945) · `source_read`.
- Versión del paper: https://arxiv.org/abs/2403.12945v2
- Proyecto y descarga: https://droid-dataset.github.io/ · `source_read`.
- Captura de datos: https://github.com/droid-dataset/droid · `source_read`.

### B22 · OpenSpiel · Lanctot et al. (2019)

Marco y entornos para RL y planificación en juegos, incluidos juegos simultáneos y de información imperfecta. Sirve para verificar semántica de acciones conjuntas y diseñar pruebas pequeñas de búsqueda adversarial. El ejemplo MCTS estándar excluye nodos simultáneos.

- Fuente: [OpenSpiel · Lanctot et al. (2019)](https://arxiv.org/abs/1908.09453) · `source_read`.
- Versión del paper: https://arxiv.org/abs/1908.09453v6
- Código y documentación: https://github.com/google-deepmind/open_spiel · `source_read`.
- Ejemplo MCTS y su comprobación de simultaneidad: https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/examples/mcts_example.cc · `source_read`.

## Evaluación y documentación complementaria

### R01 · Deep RL at the Edge of the Statistical Precipice

Evaluación de RL con pocas réplicas, incertidumbre y agregación robusta. Fundamenta el análisis; sus cifras no son resultados de Melee.

- Fuente: [Deep RL at the Edge of the Statistical Precipice](https://arxiv.org/abs/2108.13264) · `source_read`.

### R02 · rliable

Implementación de métricas e intervalos del trabajo de evaluación. Repositorio archivado el 15 de octubre de 2025: comprobar compatibilidad antes de usarlo.

- Fuente: [rliable](https://github.com/google-research/rliable) · `source_read`.

### R03 · Gymnasium Env API

Contrato general de reset, step, terminated y truncated. Referencia de diseño; no prueba que el adaptador de Melee implemente Gymnasium.

- Fuente: [Gymnasium Env API](https://gymnasium.farama.org/api/env/) · `source_read`.

### R04 · PettingZoo Parallel API

Interfaz para observaciones y acciones simultáneas de varios agentes. Útil para definir un wrapper sin introducir turnos artificiales.

- Fuente: [PettingZoo Parallel API](https://pettingzoo.farama.org/api/parallel/) · `source_read`.

### R05 · PyTorch CUDA semantics, documentación 2.15

Ejecución asíncrona, streams y sincronización. Consultar para medir tiempos correctamente; esta referencia no fija la versión que deba instalarse.

- Fuente: [PyTorch CUDA semantics, documentación 2.15](https://docs.pytorch.org/docs/2.15/notes/cuda.html) · `source_read`.

### R06 · libmelee GameState

Esquema público de estado y convenciones. Contrastar con el fork y revisión realmente cargados: documentación latest no identifica un parser instalado.

- Fuente: [libmelee GameState](https://libmelee.readthedocs.io/en/latest/gamestate.html) · `source_read`.

### R07 · Integraciones de bots aprendidos

Instalación, adaptadores y restricciones por política; distinguir checkpoint, versión de Python y parser.

- Fuente: [Integraciones de bots aprendidos](https://github.com/mateo19182/melee-llm/blob/main/docs/bots.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/bots.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### R08 · LLM player

Observación textual, macros, ejecución y registro del agente LLM directo.

- Fuente: [LLM player](https://github.com/mateo19182/melee-llm/blob/main/docs/llm-player.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/llm-player.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### R09 · Bot-writer

API del bot escrito y herramientas de práctica; distinguir generación del programa e inferencia durante la partida.

- Fuente: [Bot-writer](https://github.com/mateo19182/melee-llm/blob/main/docs/bot-writer.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/bot-writer.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### R10 · Notas de investigación del autor

Índice contextual e histórico de Melee AI. Verificar sus afirmaciones externas en la fuente original antes de convertirlas en conclusiones.

- Fuente: [Notas de investigación del autor](https://github.com/mateo19182/melee-llm/blob/main/docs/research.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-llm/blob/2bf8b0ebbb7c4a188c06782cd6f250f111c3418b/docs/research.md
- Revisión observada: `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b`.

### R11 · Melee Brute Runtime API

API nativa y Python, configuración, inputs, estados, terminales, checkpoint y rollback; comprobar límites de concurrencia por batch.

- Fuente: [Melee Brute Runtime API](https://github.com/mateo19182/melee-brute/blob/main/API.md) · `source_read`.
- Referencia fijada: https://github.com/mateo19182/melee-brute/blob/9662ec973b9e077ff7b0ff89d6db950f53c11653/API.md
- Revisión observada: `9662ec973b9e077ff7b0ff89d6db950f53c11653`.
