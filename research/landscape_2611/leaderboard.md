# Leaderboard de Melee Bench (melee.m19182.dev): estado a 2026-11-21

Instantánea tomada el **2026-11-21 13:51 UTC**. Etiquetas: **[SOP]** = dato leído de la fuente citada;
**[INF]** = inferencia nuestra.

## 0. Fuentes

| Id | Fuente | Fecha del dato |
|---|---|---|
| S1 | `https://melee.m19182.dev/api/bench` (JSON que carga la página `/bench`; endpoint localizado en `/static/v1795098887/pages/bench.js`, `api("/api/bench")`). Copia íntegra en `leaderboard_snapshot.json` (`payload`) y tabla plana en `leaderboard_snapshot.csv` | `standings.generated` = 2026-11-17 11:20:45 UTC; `status.updated` (fin del último relleno) = 2026-11-15 22:41 UTC |
| S2 | `https://melee.m19182.dev/api/docs/bench` (= `docs/bench.md` del repo) | `updated` 2026-11-15 09:15 UTC |
| S3 | `https://melee.m19182.dev/api/docs/bots` | 2026-11-21 11:50 UTC |
| S4 | `https://melee.m19182.dev/api/docs/delay` | 2026-11-18 20:35 UTC |
| S5 | `https://melee.m19182.dev/api/docs/status` | dice «As of 2026-11-15» |
| S6 | `https://melee.m19182.dev/api/bench/entrant/faynt` | igual que S1 |
| S7 | repo `mateo19182/melee-llm`, `main` @ `f274f930` (2026-11-21 11:50 UTC). `data/bench/*.json` está en `.gitignore` [SOP, S2 «File (data/bench/, gitignored)»], así que **el repo no contiene resultados**; la API es la única fuente de datos | 2026-11-21 |

[SOP] La página es pública y la API no requiere autenticación. [SOP, S1] El relleno está `phase: done`,
`stop_reason: "max games played"`, 300 partidas en la última tanda, 124,7 M tokens contados (139,7 M recontados,
~196 USD en Claude). [INF] Los ratings no se han movido desde el 2026-11-17: el leaderboard está **congelado**; Mateo
ha dicho que los LLM ya no son el centro (S5, «What's next»).

## 1. Reglas del juego y del rating [SOP, S2 salvo indicación]

- **Partida estándar única:** Fox contra Fox, Battlefield o Final Destination (puertos y escenario alternan por
  emparejamiento), 4 stocks, 8 minutos. Un time-out gana quien tenga más stocks y luego menos porcentaje. Otros
  personajes/escenarios serían tableros aparte (no existen). **Todos los entrantes juegan Fox en BF/FD**; no hay
  columna de personaje porque no varía.
- **Método:** un único ajuste **Bradley-Terry MAP** sobre todas las partidas `ok` entre entrantes no retirados, en
  escala Elo (400 puntos ≈ 10:1), prior gaussiano sd 2,0 por log-fuerza, empate = media victoria. **Ancla: `cpu:9` =
  1500** fija. IC95 = el más ancho entre el bootstrap (percentiles 2,5/97,5 de 300 remuestreos de partidas, según S1;
  la doc dice 1000) y la aproximación de Laplace. Puerto y escenario **no** entran en el modelo.
- **Convergencia:** `target_half_width` = ±125. Entrante invicto o sin victorias → solo cota (`bound: lower/upper`).
- **Relojes (S2, tabla «One board, two clocks»):**
  - *Real time* (`llm_live:*`, `jev_live`, `coach:*`, `coach_jev`): Dolphin headless a 60 fps, el juego no espera.
    Partida con media < 50 fps = `slow`, no puntúa.
  - *Untimed* (`llm_paused:*`, `jev_paused`): el juego espera cada decisión; mide solo calidad de decisión.
  - *Every frame* (CPUs, bots aprendidos, bots escritos): actúan cada frame; se juegan en modo `fast` (sin plazo).
    Los bots escritos sí llevan presupuesto de 16 ms/frame (BotAgent).
  - Real-time y untimed **nunca se enfrentan**; se conectan solo a través de los every-frame. Hasta el 2026-11-15
    había dos tableros (uno por reloj); diferían ≤ 66 Elo. [SOP, S1] Las vistas `tracks.realtime` (3782 partidas) y
    `tracks.untimed` (3017) dan hoy exactamente el mismo Elo que `board` para los entrantes comunes (son filtros de un
    solo ajuste).
- **Partidas:** 4082 valoradas (3466 del bench + 1327 importadas de ladders/pilotos, menos exclusiones). Excluidas:
  711 de entrantes retirados (scripts que se atascaban y el bot piloto), 94 de arena que no eran Fox ditto en BF/FD,
  62 del LLM arena capadas a 3600 frames, ~40 de coach/Jev por < 50 fps, 8 de self-play [SOP, S1 `games.excluded`].
- **Scheduler:** elige la partida de máxima información esperada por coste (tokens + máquina); un emparejamiento que
  un lado ha ganado siempre en ≥ 8 partidas no se repite. Antes de esa regla Faynt jugó 349 veces contra Phillip gm.
- [SOP, SYSTEM_MAP §1-2] El bench **nunca usa `--mode sim`** ni impone plazo por frame a los every-frame; el agente
  recibe `GameState` con el mando del rival (`I_full`).

## 2. Tabla de entrantes (tablero principal + controles) [SOP, S1]

Elo = estimación puntual MAP; IC95 = `elo_lo`–`elo_hi`; ± = `half_width` (lo que la web muestra). n = partidas
valoradas (V-D-E). Familia y reloj: campos `category`, `track` y `about` del registro (S1 `standings.entrants`),
traducidos. Personaje/escenario: Fox ditto en BF/FD para todos (S2). Última columna: [SOP] para HAL (S3: «predicts
4-frame action chunks, replans every 2 frames») y Phillip (S4: «No predictive model any more»); para el resto
[INF] a partir de las descripciones (`about`, S3): ninguno declara predicción de estados, simulador ni búsqueda.

| # | Entrante | Familia | Reloj | Grupo | Elo [IC95] | ± | n (V-D-E) | Pred. estado / sim / búsqueda |
|---|---|---|---|---|---|---|---|---|
| 1 | `faynt` | Transformer + RL (Faynt 10M-Arena) | por frame | main | >3326 (cota inf.) | 230 (no conv.) | 370 (370-0-0) | no |
| 2 | `phillip:gm` | Imitación + RL (slippi-ai), demora 18-24 f | por frame | main | 2549 [2470–2654] | 116 | 524 (154-370-0) | no |
| 3 | `coach_jev` | Coach LLM/Jev → Reyn | real-time | main | 2403 [2292–2523] | 123 | 78 (48-30-0) | no |
| 4 | `coach:claude-haiku-4-5-20251001` | Coach LLM/Jev → Reyn | real-time | main | 2324 [2246–2413] | 107 | 168 (108-60-0) | no |
| 5 | `coach:gpt-6-luna` | Coach LLM/Jev → Reyn | real-time | main | 2305 [2224–2391] | 106 | 175 (106-69-0) | no |
| 6 | `coach:claude-sonnet-5-5` | Coach LLM/Jev → Reyn | real-time | main | 2303 [2231–2396] | 108 | 155 (94-61-0) | no |
| 7 | `hal:MASTER` | Imitación (HAL 250M), chunks de acción | por frame | main | 2300 [2215–2394] | 101 | 198 (114-84-0) | predice mandos (chunk 4 f), no estados |
| 8 | `coach:random` | Control: coach aleatorio → Reyn | real-time | control | 2141 [2071–2222] | 100 | 238 (112-126-0) | no |
| 9 | `coach:gpt-6.1-sol` | Coach LLM/Jev → Reyn | real-time | main | 2130 [2048–2220] | 103 | 179 (74-105-0) | no |
| 10 | `phillip:plat` | Imitación + RL (slippi-ai), demora 18-24 f | por frame | main | 2039 [1978–2113] | 93 | 201 (99-102-0) | no |
| 11 | `mimic` | Imitación (MIMIC 20M) | por frame | main | 2004 [1929–2097] | 93 | 196 (113-83-0) | no |
| 12 | `written:sonnet-5.5-high/run5` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1944 [1866–2034] | 99 | 78 (50-28-0) | no |
| 13 | `written:opus-5.5-high/run5` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1879 [1783–1968] | 99 | 76 (48-28-0) | no |
| 14 | `written:opus-5.5-medium/run1` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1858 [1780–1934] | 91 | 101 (65-36-0) | no |
| 15 | `reyn` | Política condicionada por lenguaje (Reyn 33M) | por frame | main | 1846 [1768–1930] | 93 | 131 (56-75-0) | no |
| 16 | `written:opus-5.5-high/run3` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1759 [1673–1849] | 98 | 67 (36-31-0) | no |
| 17 | `written:sonnet-5.5/run1` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1752 [1686–1824] | 74 | 263 (155-108-0) | no |
| 18 | `llm_paused:gpt-6.1-sol` | LLM paused (macros) | untimed | main | 1729 [1600–1885] | 142 (no conv.) | 33 (23-10-0) | no |
| 19 | `written:haiku-5.5-high/run4` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1728 [1632–1822] | 95 | 76 (44-32-0) | no |
| 20 | `written:haiku-5.5-high/run2` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1719 [1624–1805] | 92 | 79 (43-36-0) | no |
| 21 | `written:opus-5.5-high/run1` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1713 [1617–1796] | 98 | 65 (36-29-0) | no |
| 22 | `written:opus-5.5-medium/run3` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1713 [1632–1795] | 90 | 88 (52-36-0) | no |
| 23 | `written:sonnet-5.5-high/run2` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1686 [1592–1775] | 99 | 62 (28-28-6) | no |
| 24 | `written:haiku-5.5-high/run1` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1685 [1595–1760] | 99 | 61 (29-21-11) | no |
| 25 | `written:opus-5.5-medium/run2` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1684 [1607–1772] | 82 | 105 (61-44-0) | no |
| 26 | `written:haiku-5.5-high/run5` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1673 [1586–1757] | 98 | 62 (28-24-10) | no |
| 27 | `written:sonnet-5.5-high/run4` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1654 [1566–1735] | 98 | 60 (26-23-11) | no |
| 28 | `written:opus-5.5-high/run2` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1636 [1530–1719] | 94 | 83 (44-39-0) | no |
| 29 | `written:haiku-5.5-high/run3` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1627 [1529–1707] | 92 | 74 (35-39-0) | no |
| 30 | `written:sonnet-5.5-high/run1` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1621 [1534–1715] | 90 | 78 (37-39-2) | no |
| 31 | `written:haiku-4.5/run1` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1599 [1510–1701] | 96 | 167 (109-57-1) | no |
| 32 | `phillip:silver` | Imitación + RL (slippi-ai), demora 18-24 f | por frame | main | 1541 [1458–1621] | 91 | 79 (34-45-0) | no |
| 33 | `written:opus-5.5/run1` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1527 [1456–1615] | 88 | 142 (98-44-0) | no |
| 34 | `written:opus-5.5-high/run4` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1506 [1431–1588] | 83 | 87 (46-41-0) | no |
| 35 | `cpu:9` | CPU integrada (scripted del juego) | por frame | main | 1500 [1500–1500] | ancla | 760 (354-406-0) | no |
| 36 | `llm_paused:claude-sonnet-5-5` | LLM paused (macros) | untimed | main | 1474 [1304–1643] | 170 (no conv.) | 26 (16-10-0) | no |
| 37 | `cpu:8` | CPU integrada (scripted del juego) | por frame | main | 1447 [1359–1522] | 88 | 116 (55-60-1) | no |
| 38 | `written:haiku-5.5-medium/run3` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1444 [1363–1532] | 84 | 83 (41-42-0) | no |
| 39 | `llm_paused:gpt-6-luna` | LLM paused (macros) | untimed | main | 1417 [1285–1540] | 128 (no conv.) | 31 (12-19-0) | no |
| 40 | `written:sonnet-5.5-high/run3` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1395 [1295–1478] | 95 | 65 (22-43-0) | no |
| 41 | `cpu:7` | CPU integrada (scripted del juego) | por frame | main | 1278 [1201–1352] | 81 | 161 (66-95-0) | no |
| 42 | `llm_paused:claude-haiku-4-5-20251001` | LLM paused (macros) | untimed | main | 1254 [1046–1405] | 185 (no conv.) | 19 (5-14-0) | no |
| 43 | `written:sonnet-5.5-medium/run3` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1233 [1145–1309] | 82 | 129 (54-70-5) | no |
| 44 | `written:sonnet-5.5-medium/run1` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1231 [1143–1304] | 93 | 93 (41-52-0) | no |
| 45 | `cpu:5` | CPU integrada (scripted del juego) | por frame | main | 1194 [1112–1260] | 93 | 137 (67-70-0) | no |
| 46 | `written:haiku-5.5-medium/run1` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1194 [1102–1271] | 94 | 100 (46-53-1) | no |
| 47 | `cpu:6` | CPU integrada (scripted del juego) | por frame | main | 1183 [1100–1259] | 95 | 110 (43-67-0) | no |
| 48 | `cpu:4` | CPU integrada (scripted del juego) | por frame | main | 1104 [1017–1172] | 95 | 122 (49-73-0) | no |
| 49 | `jev_paused` | Jev jugador | untimed | main | 1082 [938–1204] | 133 (no conv.) | 43 (15-28-0) | no |
| 50 | `cpu:3` | CPU integrada (scripted del juego) | por frame | main | 1066 [983–1155] | 93 | 158 (77-81-0) | no |
| 51 | `written:haiku-5.5-medium/run2` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 1060 [968–1136] | 93 | 136 (71-65-0) | no |
| 52 | `cpu:2` | CPU integrada (scripted del juego) | por frame | main | 984 [890–1059] | 96 | 144 (55-89-0) | no |
| 53 | `cpu:1` | CPU integrada (scripted del juego) | por frame | main | 976 [886–1037] | 96 | 152 (61-91-0) | no |
| 54 | `written:sonnet-5.5-medium/run2` | Bot-writer (Python escrito por LLM, 16 ms/frame) | por frame | main | 936 [844–1021] | 89 | 203 (95-97-11) | no |
| 55 | `llm_live:gpt-6.1-sol` | LLM live (macros) | real-time | main | 878 [749–976] | 149 (no conv.) | 48 (13-33-2) | no |
| 56 | `jev_live` | Jev jugador | real-time | main | 863 [691–994] | 152 (no conv.) | 77 (18-59-0) | no |
| 57 | `llm_live:claude-sonnet-5-5` | LLM live (macros) | real-time | main | 842 [714–952] | 158 (no conv.) | 34 (8-22-4) | no |
| 58 | `llm_live:none` | LLM live (macros) | real-time | control | 824 [730–895] | 105 | 105 (22-76-7) | no |
| 59 | `llm_live:gpt-6-luna` | LLM live (macros) | real-time | main | 810 [657–928] | 161 (no conv.) | 34 (8-24-2) | no |
| 60 | `llm_live:claude-haiku-4-5-20251001` | LLM live (macros) | real-time | main | 762 [591–894] | 188 (no conv.) | 24 (4-18-2) | no |
| 61 | `llm_paused:random` | LLM paused (macros) | untimed | control | 732 [623–812] | 102 | 154 (24-130-0) | no |
| 62 | `llm_live:random` | LLM live (macros) | real-time | control | 700 [588–801] | 111 | 111 (18-93-0) | no |

**Experimentos** (variantes con pocas partidas, listadas aparte en la web) [SOP, S1]:

| # | Entrante | Familia | Reloj | Grupo | Elo [IC95] | ± | n (V-D-E) | Pred. estado / sim / búsqueda |
|---|---|---|---|---|---|---|---|---|
| 1 | `reyn:stock_protection` | Política condicionada por lenguaje (Reyn 33M) | por frame | experiment | 2452 [2323–2594] | 162 (no conv.) | 32 (21-11-0) | no |
| 2 | `coach_jev,interval=60` | Coach LLM/Jev → Reyn | real-time | experiment | 2327 [2178–2490] | 172 (no conv.) | 26 (17-9-0) | no |
| 3 | `coach_jev,features` | Coach LLM/Jev → Reyn | real-time | experiment | 2240 [2059–2381] | 175 (no conv.) | 25 (16-9-0) | no |
| 4 | `coach:claude-haiku-4-5-20251001,features` | Coach LLM/Jev → Reyn | real-time | experiment | 2228 [2012–2440] | 214 (no conv.) | 15 (8-7-0) | no |
| 5 | `coach:random,jev6` | Control: coach aleatorio → Reyn | real-time | experiment | 2220 [2077–2367] | 178 (no conv.) | 23 (14-9-0) | no |
| 6 | `coach_jev,interval=900` | Coach LLM/Jev → Reyn | real-time | experiment | 2206 [2075–2353] | 173 (no conv.) | 24 (14-10-0) | no |
| 7 | `coach:random,fixed` | Control: coach aleatorio → Reyn | real-time | experiment | 2075 [1911–2203] | 175 (no conv.) | 23 (10-13-0) | no |
| 8 | `coach:random,sticky` | Control: coach aleatorio → Reyn | real-time | experiment | 2061 [1863–2216] | 179 (no conv.) | 22 (9-13-0) | no |

Fuera del ajuste: `baseline:laser/rusher/shine` y `written:sonnet/pilot1` (retirados: se atascaban o pierden con
CPU 1) y `human:mateo` (plaza reservada, 0 partidas) [SOP, S1/S2].

## 3. Cuántas partidas hacen falta para separar a un entrante de su vecino

**Lo que dice el tablero [SOP, S1]:** con 150–250 partidas los entrantes every-frame y los coaches quedan en
±80–110 (p. ej. `cpu:7` ±81 con 161, `coach:claude-haiku` ±107 con 168, `written:sonnet-5.5/run1` ±74 con 263).
Los LLM live/paused, con 19–48 partidas, siguen en ±128–188 y no convergen. Phillip gm, con 524 partidas, solo
llega a ±116 porque 349 son contra Faynt (resultado siempre igual, informa poco).

**Conversión a nuestro cálculo de potencia [INF]:** los «10 puntos» de `HECHO.md` son puntos porcentuales de tasa de
victoria (40 partidas/brazo → 2,8·√(0,5/40) ≈ 31 pp; 400/brazo → ≈ 10 pp, α = 0,05 bilateral, potencia 80 %).
Cerca del 50 %, **10 pp ≈ 70 Elo**. Con un error por partida de ≈ 347/√n Elo en partidas equilibradas:

| Diferencia a detectar | Duelo directo (n total) | Contra rivales comunes (n por brazo) |
|---|---|---|
| 150 Elo | ~40 | ~85 |
| 70 Elo (≈ 10 pp) | ~190 | ~390 (nuestras ~400) |
| 35 Elo | ~770 | ~1500 |
| 20 Elo | ~2400 | ~4700 |

Son mínimos ideales: el tablero real es 1,4–2× más ancho de lo que da 347/√n (`half_width·√n` ≈ 950–1400 frente a
680 ideal) por la cadena hasta el ancla y los emparejamientos desequilibrados, así que en la práctica hay que
**multiplicar n por 2–4** si se mide a través del tablero y no en duelo directo [INF].

**Vecinos concretos [SOP para las diferencias, INF para n]:** la diferencia mediana entre vecinos del tablero
principal es ~21 Elo, inseparable con las partidas actuales. Huecos relevantes para nosotros:
`phillip:gm`–`coach_jev` 146 (≈ 45 partidas directas), `hal:MASTER`–`coach:random` 159 (≈ 40),
`coach:gpt-6.1-sol`–`phillip:plat` 91 (≈ 115), `phillip:plat`–`mimic` 35 (≈ 770), `hal:MASTER` y los tres coaches
LLM a 2300–2324 (diferencias de 2–24 Elo: empate estadístico). Conclusión: **para entrar al tablero con ±125 bastan
~30–80 partidas; para afirmar que superamos a un vecino concreto a ~70 Elo hacen falta ~200 partidas en duelo
directo o ~400 por brazo**, coherente con nuestra cifra.

**Mezcla de relojes [SOP S2, valoración INF]:** el Elo mezcla tres condiciones (real-time, untimed, every-frame sin
plazo). Los LLM real-time pagan la latencia (GPT-6.1 Sol live descarta ~95 % de sus respuestas, S2), mientras los
bots every-frame juegan en `fast` sin plazo ni demora. Las condiciones se conectan solo vía los every-frame, que se
suponen indiferentes al reloj. **Ningún entrante juega con demora impuesta por el bench**: la demora de Phillip
(18–24 f) es propia, de diseño. Un Elo de este tablero no mide robustez a la demora.

## 4. Quién domina, por qué, y dónde cabe un modelo del mundo

**Dominan los bots aprendidos que actúan cada frame [SOP, S1/S5]:**

1. **Faynt 10M-Arena**, 370-0, Elo > 3326 (solo cota inferior; ±230; diferencia media de 3,8 stocks). Transformer de
   10 M, RL sobre Fox, 0 frames de demora añadida, corre en CPU a ~8 ms p50 (S3). [INF] Domina porque está
   ajustado con RL exactamente al juego del bench (Fox ditto) y juega sin demora. [SOP, S3/S5] **Con 10 frames de
   demora pierde todas** (experimento E32 de Mateo).
2. **Phillip gm**, 2549 ±116: imitación + RL (slippi-ai) **con 18–24 frames de demora de diseño**, sin modelo
   predictivo (S4). [INF] Es el agente fuerte más robusto a la demora del tablero.
3. **Reyn guiado** (coaches 2130–2403; `reyn:stock_protection` 2452 sin LLM). [SOP, S5] La fuerza viene del cuerpo
   Reyn y de un comando («Don't die.»); un coach aleatorio ya da 2141; los coaches LLM añaden +160–180 y Jev +260.
4. **HAL master** 2300 ±101 (imitación 250 M, sin demora) y **MIMIC** 2004 ±93 (imitación 20 M).
5. Por debajo: bots escritos por LLM (936–1944, la mitad alrededor del bot inicial de ~1685, S5), LLM paused
   (1254–1729) y **LLM live por debajo de CPU 1** (762–878; el comportamiento de espera sin modelo ya da 824).

**Huecos [INF salvo indicación]:**

- **Ningún entrante predice estados, usa el simulador ni busca.** [SOP] HAL predice mandos, no estados (S3); Phillip
  abandonó el modelo predictivo (S4); el bench no usa `--mode sim` (SYSTEM_MAP). La página «Brute» (búsqueda
  exhaustiva) y el simulador existen en la web, pero no son entrantes. Un agente con modelo del mundo sería el
  primero de su familia en el tablero, valga lo que valga su Elo.
- **Hay un vacío de ~780 Elo entre Phillip gm (2549) y la cota de Faynt (3326).** No es un hueco fácil: para subir
  ahí habría que acercarse a Faynt, que tiene RL específico de Fox.
- **El hueco que encaja con nuestra hipótesis no está en las reglas actuales.** En el bench, sin demora y con
  `I_full`, un predictor del presente no tiene nada que predecir: el estado observado ya es el presente. Donde
  aporta es bajo demora, y ahí el líder sin demora (Faynt) se hunde (S3) mientras Phillip está diseñado para ella.
  Para que el bench mida nuestra hipótesis hace falta una **condición con demora impuesta** (p. ej. 10–18 f, con
  el envoltorio `rt_strict` de `pilot/e0_timing/`), que hoy no existe. Habría que proponerla o montarla en local.

**Rival de referencia para el MVP [INF]:** el MVP es una política de imitación sobre Fox-Fox con predictor del
presente (W0-S + q) bajo demora.

- **Principal: `phillip:plat`** (2039 [1978–2113], 201 partidas, convergido). Juega con 18–24 f de demora propia, la
  misma condición que queremos medir, y su nivel queda al alcance de una política de imitación. Que 35 Elo lo
  separen de MIMIC da un par de referencias próximas.
- **Control de imitación sin demora: `mimic`** (2004 ±93, BC de 20 M, Fox): indica cuánto vale la imitación sola.
- **Objetivo ambicioso: `phillip:gm`** (2549). Es el mejor agente con demora del tablero.
- **Cordura: `cpu:9`** (ancla 1500). [SOP, S5] Los BC Yoshi de Mateo contra él: bc-6m-v1 0/12, bc-20m-v2 1/12. Superarlo
  no es trivial para un BC pequeño.
- **No sirve como rival del MVP: Faynt.** Está fuera de alcance sin demora y pierde siempre con ella (S3), así que
  como referencia no discrimina. HAL (2300) es alternativa a MIMIC, pero exige los puertos 1 y 2 y su código no
  tiene licencia (S3).

Con ~200 partidas en duelo directo contra `phillip:plat` se detectan diferencias de ~70 Elo. Para un contraste
ablativo (con y sin predictor) frente a los mismos rivales hacen falta ~400 por brazo, como ya estimábamos.
