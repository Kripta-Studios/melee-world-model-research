# Criterios de cierre de la investigación

## Fuentes y revisiones

- [ ] Cada fuente clave tiene URL canónica y fecha de consulta.
- [ ] Cada repositorio reutilizado tiene revisión completa y ruta de licencia o incertidumbre explícita.
- [ ] HEAD, dependencia configurada, revisión instalada descrita y revisión medida están separados.
- [ ] Pesos y datos tienen identidad, versión o hash y condiciones de uso comprobables.
- [ ] Las cifras publicadas conservan atribución; ninguna figura se presenta como reproducción propia sin logs.

## Sistema y diseño

- [ ] Existe un mapa de observación, política, mandos, motor, tiempos y resultados.
- [ ] Se identificaron símbolos reales para integrar un agente y, si procede, un predictor.
- [ ] Encoder, dinámica, valor, política y búsqueda están definidos por separado.
- [ ] Se comparan alternativas concretas, incluyendo no usar un modelo aprendido.
- [ ] Los modelos de robótica o vídeo no se presentan como ya adaptados a Melee.
- [ ] Se explica cómo se trata al rival durante entrenamiento y durante inferencia.

## Protocolo

- [ ] El split se hace por partidas antes de ventanas y se comprueban duplicados.
- [ ] La prueba reservada no interviene en seleccionar checkpoints ni ajustes.
- [ ] La información disponible y los retrasos son comparables o se reportan por separado.
- [ ] El control de representación no incluye inadvertidamente dinámica en inferencia.
- [ ] Hay un control sin rollouts con propuestas y puntuación comparables.
- [ ] Existe una referencia de dinámica estructurada y se justifica cualquier omisión.
- [ ] El error de predicción se acompaña de rendimiento en bucle cerrado.
- [ ] Se distinguen semillas de entrenamiento de partidas de evaluación.
- [ ] Se fijaron métricas, tamaño de muestra y diferencia mínima relevante antes del test.
- [ ] Se mide el coste completo hasta aplicar el mando, con percentiles y fallos.

## Viabilidad y entrega

- [ ] El presupuesto refleja hardware comprobado o supuestos etiquetados.
- [ ] El MVP reutiliza componentes existentes donde tiene sentido.
- [ ] Las tareas tienen propietarios, dependencias y salidas concretas.
- [ ] La revisión crítica intenta refutar las conclusiones principales.
- [ ] La recomendación final identifica el siguiente paso que más reduce incertidumbre.
- [ ] Lo pendiente se distingue de lo demostrado y de lo propuesto.

