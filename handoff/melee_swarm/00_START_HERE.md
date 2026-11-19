# Investigación de JEPA y modelos del mundo para Melee

Fecha de corte: 19 de noviembre de 2026. Destinatario: coordinador de un swarm de agentes de investigación e ingeniería.

## Objetivo

Determinar si un modelo del mundo aprendido, particularmente una variante inspirada en JEPA, LeJEPA o LeWorldModel, aporta valor medible a un agente de Super Smash Bros. Melee frente a imitación, RL sin modelo explícito de dinámica y planificación con el simulador existente. La entrega inicial del swarm es una investigación técnica con decisiones justificadas y un plan reproducible de aplicación. El paquete no contiene resultados de entrenamiento nuevos.

## Cómo utilizar el paquete

1. Entrega todos los archivos al coordinador.
2. Pega el contenido completo de 01_MASTER_PROMPT.txt.
3. Pide que lea 02_RESEARCH_DOSSIER.md y 03_SOURCE_CATALOG.md.
4. Usa 04_SOURCES.json para distribuir fuentes y registrar revisiones exactas.
5. Reparte el trabajo con 05_AGENT_TASKS.json. Los ocho roles son lógicos; ejecútalos por tandas si hay menos procesos disponibles.
6. Aplica el protocolo de 06_EXPERIMENT_PROTOCOL.md y la matriz de 07_EXPERIMENT_MATRIX.json antes de proponer conclusiones sobre rendimiento.
7. Registra evidencia con 08_EVIDENCE_SCHEMA.json y resuelve las interfaces con 09_INTEGRATION_CONTRACT.md.
8. Revisa 10_COMPLETION_CHECKLIST.md antes de cerrar la investigación.

## Qué incluye

- Fuentes primarias del benchmark, simuladores, políticas, datos, artículos y métodos de evaluación.
- URLs canónicas y revisiones Git cuando se pudieron verificar.
- Diferencia entre versión actual, dependencia configurada, revisión instalada descrita y experimento histórico.
- Prompt maestro, responsabilidades sin solapamientos, entregables y dependencias.
- Comparaciones para separar el efecto de la representación, la dinámica, la búsqueda y el RL.
- Plantilla de evidencia que distingue una afirmación del autor de una medición propia.

## Punto de partida

El sitio https://melee.m19182.dev corresponde al proyecto https://github.com/mateo19182/melee-llm. Integra bots con diferentes métodos de entrenamiento, LLM directos y entrenadores; contiene además experimentos de búsqueda con un simulador. La ausencia de un participante publicado como JEPA en la revisión inspeccionada no prueba que ninguna red externa contenga representaciones implícitas de dinámica.

La hipótesis JEPA se debe investigar; no es el resultado que el swarm deba confirmar. Un resultado útil puede recomendar RL convencional, planificación con reglas conocidas o posponer el modelo aprendido si no aporta ventajas.

## Alcance de las evidencias

source_read significa que se leyó una fuente; no significa que se reprodujera su resultado. metadata significa que se comprobó identidad, enlace o revisión, sin auditar necesariamente toda la implementación. Los números publicados permanecen atribuidos a sus autores. El registro conserva las etiquetas originales y una normalización para consumo por agentes.

Las fuentes externas se enlazan; el paquete contiene síntesis e instrucciones originales. Para reproducir, el swarm debe resolver los archivos y versiones de las fuentes y comprobar disponibilidad de datos, pesos y activos del juego. Las interfaces y umbrales del protocolo son propuestas que deben fijarse antes de medir.

## Orden mínimo de lectura

- Melee Bench: docs/bench.md, docs/bots.md, docs/delay.md y melee_llm/bench/entrants.py.
- Simulación: docs/simulator.md de melee-llm y README, API.md y BRUTE.md de melee-brute.
- Representaciones: LeJEPA y su implementación oficial.
- Dinámica: LeWorldModel; después DreamerV3 y MuZero para comparar cómo utilizan modelos.
- Evaluación: protocolo de este paquete, At Human Speed y Statistical Precipice.

Lee el documento completo en 02_RESEARCH_DOSSIER.md para evitar confundir una herramienta de evaluación, un agente, un simulador, un encoder y un planificador.


## Anexos y formatos portables

- 11_PLATFORM_MAP.md: mapa del runtime, dependencias y límites.
- 12_SCIENCE_READING_GUIDE.md: itinerario de lectura por decisión.
- 13_REFERENCE_REVISIONS.json: revisiones bibliográficas y dependencias documentadas; no es un entorno instalado.
- 14_URLS.txt: URLs únicas, una por línea, para ingestión automática.
- EVIDENCE_EXAMPLE.jsonl: ejemplo válido de una propuesta, sin mediciones ficticias.
- MANIFEST_SHA256.json: integridad de los archivos del paquete.

El catálogo contiene 82 fichas y el listado plano contiene 201 URLs únicas. Se incluyen referencias fijadas y enlaces generales. La cifra no significa que todos los destinos se hayan descargado: cada ficha conserva su alcance de verificación.
