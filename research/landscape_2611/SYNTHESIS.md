# Panorama a 2026-11-21: repos de Mateo, leaderboard y competidores

Tres agentes, uno por tema. Informes completos en esta carpeta: `mateo_repos.md`, `leaderboard.md` (con instantánea en
`leaderboard_snapshot.{json,csv}`) y `competitors.md`. Todas las cifras de fuerza son de sus autores: no se ha
jugado ninguna partida ni se han descargado pesos.

## Hechos

- **Mateo casi no ha cambiado nada.**
  - melee-brute sigue en `9662ec97`.
  - melee-llm pasa de `7e179081` a `f274f930`: SEO de la web y resultados de E32. No cambian el protocolo, el
    simulador ni la interfaz del agente.
  - Sigue sin semilla RNG por frame y sin hook para un planificador. `docs/status.md` (14-11) da al proyecto «una o
    dos semanas más»: probablemente se congele.
- **El leaderboard está congelado desde el 2026-11-17.**
  - Fuente: API `https://melee.m19182.dev/api/bench`.
  - Ajuste Bradley-Terry en escala Elo, con CPU 9 = 1500. 4.082 partidas Fox ditto en Battlefield y Final
    Destination.
  - Mezcla tres relojes, y **ninguno impone demora**.
  - Domina Faynt (370-0). Le sigue Phillip gm (2549), que juega con 18–24 frames de demora propia.
- **Retraso (E32 de Mateo).**
  - Faynt gana 48/48 sin retraso y 0/48 con 1 frame.
  - Con su último mando propio (`own=1`) gana 42/48 a 1 frame y 0/48 a partir de 4.
- **Nadie busca jugadas ni usa un modelo del mundo aprendido para jugar.**
  - Lo más cercano es 4Stockfish: busca combos con el simulador suponiendo que el rival no reacciona.
  - Hay además un modelo del mundo en píxeles sin evaluar.
- **Trabajo afín que no conocíamos:**
  - La rama `student` de melee-llm (PR #99, E25): una política que recibe los mandos pendientes para jugar con
    retraso.
  - `nash_policy_delay.md` de slippi-ai: separa la cola de acciones propia, conocida, de la del rival, oculta.
  - HAL tiene PPO en liga con brazos de 16 frames de retraso.
  - MIMIC hace RL en el simulador nativo, con lo aprendido transferido a Dolphin.

## Qué implica para el plan (INF)

1. **El predictor del presente solo tiene sentido con demora.** En el benchmark actual, sin demora, no aporta. Para
   medirlo haría falta una condición con demora impuesta, que hoy no existe. E32 confirma que el retraso hunde al
   mejor bot y que basta un truco barato (`own=1`) para recuperar algo.
   - **Líneas base nuevas obligatorias en E3:** `own=1` y la política `student` con mandos pendientes. Son lo que el
     predictor tiene que batir, no solo la observación envejecida.
2. **Rival de referencia:** `phillip:plat` (Elo 2039) como objetivo realista, MIMIC (2004) como control de
   imitación y Phillip gm como objetivo ambicioso.
   - Con vecinos a ~20 Elo, distinguir 10 puntos (~70 Elo) pide unas 400 partidas por brazo, como ya preveía el plan.
3. **El hueco real coincide con E0c.** Nadie modela cuándo está comprometido el rival (~15 % del tiempo a 7 frames)
   ni una distribución calibrada de sus decisiones.
   - El diseño que sale de las dos líneas de evidencia es híbrido: simulador exacto (o un modelo aprendido barato)
     para lo comprometido y lo propio, y un modelo del rival calibrado para sus puntos de decisión.
4. **Congelar los pines.** Mateo no avanza, así que nuestros pines de revisión siguen valiendo.
