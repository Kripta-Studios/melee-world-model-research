# Contrato propuesto de integración

Este contrato es una propuesta para acordar entre agentes. Los nombres siguientes no afirman que exista ya una API equivalente. A1 debe mapearlos a símbolos reales de las revisiones fijadas y documentar conversiones.

## Observaciones y privilegios

Separar tres niveles:

1. observation: información permitida al agente que decide, con historia suficiente y sello temporal.
2. training_metadata: mandos registrados de ambos jugadores, resultado, objetivos supervisados y metadatos de procedencia.
3. simulator_snapshot: memoria completa y RNG del motor para restaurar o diagnosticar; no entregarla inadvertidamente a una política de observación limitada.

Un campo presente en el log no es automáticamente observable durante inferencia. Los botones futuros del rival y estados futuros se excluyen de observation.

## Esquemas mínimos

ObservationSpec incluye schema_version, episode_id, frame_id, observation_timestamp, controlled_port, stage_id, player_observations, own_committed_action_queue, visibility_mask y history_length. Cada campo debe tener tipo, unidad, rango, disponibilidad y transformación desde la fuente.

ActionSpec incluye botones, sticks, gatillos, duración en frames, decision_frame, intended_application_frame, actual_application_frame y fallback. Separar pressed, held y released cuando el adaptador lo requiera. No normalizar rangos sin guardar la conversión exacta y su redondeo.

TransitionSpec incluye o_t, acciones aplicadas, r_t, o_next, terminated, truncated, frame_delta, delay, source_game_id y source_revision. El cronómetro interno forma parte de las reglas: su agotamiento puede adjudicar un resultado por stocks y porcentaje y terminar la partida. Un límite externo de tiempo o de horizonte puede truncar la observación sin producir un resultado del juego. Un crash o una cancelación conserva su motivo y queda inválido para puntuación, sin inventar victoria, derrota o empate. Si se estudian derrotas operativas por fallos del agente, preregistrar esa métrica por separado.

## Interfaces lógicas

- env.reset(seed, matchup, initial_state) devuelve observación y metadatos.
- env.step(joint_action) ejecuta entradas para ambos jugadores según el contrato del motor.
- agent.act(observation, memory, budget) devuelve acción, memoria y diagnóstico de tiempo.
- encoder.encode(history) devuelve representación.
- dynamics.predict(latent, own_actions, opponent_hypotheses, elapsed_frames) devuelve futuras representaciones y, si existe, incertidumbre.
- evaluator.score(prediction, goal_or_reward_model) devuelve utilidad bajo un objetivo explícito.
- planner.propose(observation, model, prior, budget) devuelve una acción y un registro del presupuesto gastado.

Son interfaces de diseño. Si se adopta Gymnasium, tratar terminated y truncated según su documentación; si se expone un entorno de dos agentes, decidir wrapper y coordinación sin perder simultaneidad.

## Semántica temporal

Fijar antes de comparar:

- En qué momento del frame se toma una observación.
- Si la acción calculada se aplica en el frame actual o en uno posterior.
- Dónde se introduce la demora de red o reacción.
- Cuándo se mantiene una acción previa y cómo se registra el fallback.
- Si frame skip repite botones o agrupa decisiones.
- Si la latencia de un planner consume frames o pausa el entorno.

Medir dos intervalos desde la disponibilidad de la observación: hasta aceptación del mando y hasta aplicación efectiva. El plazo de actuación se evalúa con el segundo. Si la aplicación solo puede inferirse, conservar el método y su incertidumbre; no presentarla como timestamp observado. Reportar también costes de captura, codificación, predicción, búsqueda, copia, cola y envío.

## Verificaciones mínimas del adaptador

Las verificaciones propuestas buscan errores concretos, no una batería ilimitada de tests.

- Si hay soporte de snapshots, reproducir la trayectoria esperada de ese motor con mismo snapshot, RNG e inputs. Es un requisito de S0; para los otros brazos registrar si está disponible.
- Pares de inputs que diferencien pulsación de mantenimiento, giro, salto, escudo y aterrizaje.
- Equivalencia de conversiones entre APIs en valores neutros, extremos y umbrales relevantes.
- Fin por reglas del juego, truncamiento externo y fallos de ejecución diferenciados, con resultado y motivo explícitos.
- Ausencia de datos futuros en observation.
- Latencia y presupuesto registrados cuando hay respuesta tardía.
- Reproducibilidad de acciones y semilla del agente por separado de la del entorno.

Si una correspondencia falla, resolverla antes de atribuir al modelo un cambio de rendimiento.

## Entrega del acuerdo

A1 mantiene evidence/A1/CONTRACT.md con tipos y tiempos e incorpora evidence/A6/timing_contract.json. A3, A4 y A5 entregan en sus propias rutas las dimensiones latentes, acciones por paso, predictor, puntuación y presupuesto; A1 integra sus acuerdos. A8 revisa la comparación de información. El coordinador congela la versión consolidada junto a sources.lock.json.

Fuentes de interfaces generales:

- https://gymnasium.farama.org/api/env/
- https://pettingzoo.farama.org/api/parallel/

La adopción de estas librerías es opcional; su API no demuestra que el simulador de Melee ya la implemente.

