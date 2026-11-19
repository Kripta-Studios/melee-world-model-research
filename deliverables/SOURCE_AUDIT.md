# SOURCE_AUDIT · Mapa de fuentes consultadas por el swarm

Integrador · consulta 2026-11-19 · Consolida `evidence/A1`…`A8`, `ops/clone_inventory.txt` y el catálogo del paquete
(`handoff/melee_swarm/03_SOURCE_CATALOG.md`, `04_SOURCES.json`, `13_REFERENCE_REVISIONS.json`). La versión que lee una
máquina está en `sources.lock.json`, con los mismos IDs. Nada de esta auditoría se ejecutó: no hay ISO, Dolphin, GPU,
pesos ni datasets descargados.

**Alcance de verificación**, en orden de fuerza:
- **CÓD**: se leyó el código en el clon local, con su SHA.
- **DOC**: se leyó la documentación, la ficha o el paper.
- **META**: solo metadatos (API de HF, árbol, `ls-remote`, cabeceras).
- **NO**: no se accedió.

**Re-verificaciones propias** (2026-11-19, contra `sources/`), marcadas ✔:
- `git diff --stat 2bf8b0eb 7e179081` en melee-llm.
- Recuento de `--played-on/--no-ucf` en las tres revisiones de melee-brute.
- Versión de libmelee en `bce21f09` y en `2d63e7ee`.
- Ficheros LICENSE de los 21 clones.
- `fetch --depth 1` del pin de MIMIC `bdfb6293`.
- Longitudes de fichero de todos los `source_refs` con SHA local: 211 rangos válidos y 1 inválido (A1-016, véase §4).

> Nota de rutas: el brief dice `sources/<owner>__<repo>`, pero en disco es `sources/<owner>_<repo>` (A8 §5).

## 1. Repositorios clonados (21; HEAD = `ops/clone_inventory.txt`)

| ID | Repo · URL canónica | Revisión(es) exacta(s) | Alcance | Licencia (ruta) | Usado por |
|---|---|---|---|---|---|
| A02–A13, A25, A33–A37, A40–A47, R07–R10 | github.com/mateo19182/melee-llm | HEAD `7e179081c6cbab139d860c998b1452ad3dee047c` · catálogo `2bf8b0ebbb7c4a188c06782cd6f250f111c3418b` (ancestro) | CÓD (runtime, bench, sim, bots, train/farm, docs) | **Sin LICENSE** ✔ | A1, A2, A4–A8 |
| A14, R11 | github.com/mateo19182/melee-brute | HEAD `9662ec973b9e077ff7b0ff89d6db950f53c11653` · **pin de melee-llm `090e54b048b7d51e82f9f6b551046c2ca8b130c7`** · E31 `d3832724ef67f67db4bb4672ff46ae6c134dbad7` · farm `MELEE_SIM`: DESC | CÓD (API C/Python, BRUTE.md, validación) | **Sin LICENSE** ✔ | A1, A4, A5, A7, A8 |
| A15 | github.com/kyhavlov/melee-sim-light | `eea7b5fbcd0243baf4c1956d52f3e1d0f536edc4` (ancestro de las 3 de melee-brute) | CÓD + DOC (`agent_docs/VALIDATION.md`) | **Sin LICENSE** ✔ (melee-llm `docs/simulator.md` L7 lo dice) | A1, A4, A6–A8 |
| A16 | github.com/vladfi1/libmelee | HEAD master `bce21f09984b286e6d36bfd2939e4cd4691f94c2` (0.47.3 ✔) · **instalado en melee-llm: 0.47.6 = tag `v0.47.6` = `2d63e7ee948d77ab4e73165ed4c73abbe3ba121b`** (rama dev, ✔ `version.py`) | CÓD en ambas | **LGPL-3.0** (`LICENSE.txt`) ✔ | A1, A6, A8 |
| A20 / B19 | github.com/ericyuegu/hal | `37045d974116405dd690efea6109a1d83a2da868` | CÓD | **Sin LICENSE** ✔ (todos los derechos reservados) | A2, A4, A6, A8 |
| A23 | github.com/vladfi1/slippi-ai | `5ada33e90c6c87fe83a1fb2d1a8105a96fd7b05b` (coincide con la que cita melee-llm) | CÓD | MIT ✔ | A2, A3, A6, A8 |
| A26 | github.com/erickfm/MIMIC | HEAD `3691f534194f9c2ec52f131c8ab96e3d8674c3fa` · pin de integración `bdfb6293c6709462b77647714b65952d190c116f` (melee-llm `docs/bots.md` L45) | CÓD en HEAD; pin traído ✔ pero no auditado | MIT ✔; la build nativa del simulador es GPL-3 | A2, A6 |
| A29 | github.com/Na00s/Faynt-Tournament | `d20961761814caf01f5db19c945d00ab757730ea` | CÓD (`sources/faynt/268031e7…/model.py`) | MIT ✔, más un parche de Dolphin GPL-2.0+ | A2 |
| A31 | github.com/frisson-labs/Reyn | `93fa52742e43a3115a990211b3aebb31671d8fdc` | CÓD superficial | MIT ✔ | A2 |
| A38 | github.com/Na00s/Faynt-Benchmarks | `39bc007537501c16d6e2dac6f2bcaafe3b84a8c9` | CÓD + DOC (README, `evaluation/melee_rl`, TOML) | MIT ✔ | A2, A8 |
| X01 (código de B17/B18) | github.com/vladfi1/phillip | `114aea4c446b31359c5637b271db52b200440caa` | CÓD | **Ambigua**: `LICENSE` GPLv3 frente a `setup.py` L39 `license='MIT'` ✔ | A2, A4, A8 |
| B03-code | github.com/lucas-maes/le-wm | `8edfeb336732b5f3ce7b8b210d0ba370a09e2cac` | CÓD (`module.py`, `jepa.py`, `train.py`, configs) | MIT ✔ | A3, A4, A7, A8 |
| B02-code | github.com/galilai-group/lejepa | `c293d291ca87cd4fddee9d3fffe4e914c7272052` | CÓD | **CC BY-NC 4.0** ✔ | A3, A7 |
| B07-code | github.com/MLO-lab/LeVJEPA | `a748e0fbaa0ec548cad283978b818779708a3bd7` | CÓD (`loss.py`, `train.py`) | MIT ✔ | A3 |
| B13-code | github.com/facebookresearch/jepa-wms | `13cf1d9c7e476f53c17714d2e0f1dc239a883ce0` | CÓD | **CC BY-NC 4.0** ✔ | A3, A4 |
| B04/B05/B06-code | github.com/facebookresearch/vjepa2 | `204698b45b3712590f06245fbfba32d3be539812` | CÓD | MIT ✔ (3 archivos Apache-2.0, A3); licencia de pesos no consta | A3, A4 |
| B01-code | github.com/facebookresearch/ijepa | `52c1ae95d05f743e000e8f10a1f3a79b10cff048` | CÓD | **CC BY-NC 4.0** ✔ | A3 |
| B11-code | github.com/gaoyuezhou/dino_wm | `0a9492fa12044b852ae9e001cc74604b79c8bb0c` | CÓD puntual | MIT ✔ | A4 |
| B08-code | github.com/danijar/dreamerv3 | `e01491fad6434b2245a3b8ca201dd7faedcc458c` | CÓD puntual (`rssm.py`, `agent.py`) | MIT ✔ | A4 |
| B12-code | github.com/nicklashansen/tdmpc2 | `332f19e4aba4bffe2dc736f45ea7f7bdc585903a` | CÓD (configs MPPI) | MIT ✔ | A4, A7 |
| R02 | github.com/google-research/rliable | `3ccd9f4dea577a04d3d2b557f259aac08badbd81` | CÓD (`library.py`, `metrics.py`) | Apache-2.0 ✔; repo archivado (catálogo); depende de `arch` no instalado | A8 |

## 2. Fuentes remotas no clonadas

| ID | Fuente · URL | Revisión | Alcance | Licencia / incertidumbre |
|---|---|---|---|---|
| A18 | slippi-wiki `SPEC.md` · github.com/project-slippi/slippi-wiki/blob/…/SPEC.md | `3a85ce8b1f2dae1b487b2529a43c80f5de5885a3` (raw) | DOC (tablas de eventos, offsets) | No comprobada |
| A21 | HF `ericyuegu/hal-base-250m-rc` | `e7fb8378ae15011cb0a414c16a8e5ac8b951fa63` | DOC (ficha) | Pesos MIT según la ficha; el código no tiene licencia |
| A22 | Blog de HAL · ericyuegu.com/hillclimbing-melee/ | sin versión (página viva) | DOC | Desconocida. A2 la citó con `catalog_id` B19 por error |
| A24 | HF `vladfi/phillip-models` `index-v1.json` | `a5045c5347ec6788a0d6f0801cb8483b3e8d47ce` | DOC + META (índice leído en dos tramos, offsets 0 y 100000) | MIT (ficha) |
| A27 | HF `erickfm/MIMIC` | `f49879b67abb64cd7fa76ea033f846fee45571e5` | DOC (ficha y tabla de checkpoints) | MIT. El linaje de `fox-master` es contradictorio (A2-010) |
| A28 | HF dataset `erickfm/melee-ranked-replays` | `ef54ddc230e01373ff2a179b49a7e559af788081` | META (árbol paginado: 936 ficheros, 1,43 TB) + DOC (README) | «MIT» declarada por quien redistribuye; los derechos del origen son DESC |
| A46 | HF dataset `ericyuegu/hal-mds-dataset` | `46ca723efd1de791c06300ed62c9278ecdb2f34a` | META + 4 JSON pequeños (`projection`, `selection`, `stats`, `val/index`) + 3 KB del `manifest.jsonl` | `license: other` sin texto. `player_codes.jsonl.gz` contiene datos personales |
| A30 | HF `frisson-labs/Faynt-10M-Arena` | `96929127f522c3fe3fc4721bb6fd6f0236e06888` | DOC + lista de ficheros | MIT, «Offline use only. Do not use or adapt Faynt for Slippi Online» |
| X02 | HF `frisson-labs/Faynt-10M-Expert` (y la colección Faynt) | **no fijada** | DOC (ficha) | MIT (según A2); hay que fijar la revisión antes de usarla |
| A32 | HF `frisson-labs/Reyn-26C` | `6a46ac79f33f80e00c262e8e91abd6cb9c38f4cf` | DOC | MIT; el método de entrenamiento no está documentado |
| X03 | HF `quentinll/lewm-pusht` | no fijada | DOC (ficha) | MIT según la ficha |
| X04 | HF `galilai-group/LeVJEPA-1.5-Large` | no fijada | DOC (ficha) | CC BY-NC 4.0 |
| X05 | le-wm.github.io | página viva | DOC | — |
| R05 | docs.pytorch.org/docs/2.15/notes/cuda.html | doc 2.15 (aquí está instalado torch 2.10) | DOC | — |
| R06 | libmelee.readthedocs.io | — | **NO**: A6 citó el ID R06 pero leyó código de `bce21f09` | — |

**Papers** (todos DOC; las cifras siguen atribuidas a sus autores):

| ID | Versión leída | Notas |
|---|---|---|
| B17, At Human Speed | arXiv 1810.07286**v1**, PDF sha256 `d93cb1de64eb73d0d015bb2643643749f49cd4f0cb1756c621c02b3e2f5a19db`, texto extraído con pdftotext | A2, A4, A6, A8 |
| B03, LeWM | 2603.19312**v3** (html) | |
| B02, LeJEPA | 2511.08544**v3** | |
| B05 (y B04), V-JEPA 2 | 2506.09985**v1** | |
| B12, TD-MPC2 | 2310.16828**v2** | |
| B20, Faynt | 2610.02144**v1** | Solo el abstract |
| B09, MuZero | 1911.08265**v2** (arXiv) | **Distinto de la URL del catálogo** (Nature) |
| R01 | 2108.13264 | Sin versión registrada |
| B22, OpenSpiel | 1908.09453 | Solo la ficha del catálogo (A4-030) |

**No accedidos (NO)**:
- A01 (sitio; ya `unverified` en el catálogo).
- A05: no citado. A08 y A12 se leyeron sin citar su ID.
- A17, Dolphin `accd20fa…`.
- A19, decomp `2f8eab8e…`.
- A39, slippi.gg.
- A48/A49, las releases de Dolphin. Solo se leyó su pin en `scripts/setup.sh` L9-10 @ `7e179081`: `v4.0.0-mainline-beta.19` y `4.0.0-mainline-beta.14.1-ExiAI`.
- B01, B04, B06, B07, B08, B11 y B13 como papers: se leyó su código, no el PDF.
- B10, B14, B15, B16, B18 (paper), B21, R03 y R04.

## 3. Discrepancias frente al catálogo del paquete

| # | Fuente | Catálogo dice | Observado | Consecuencia |
|---|---|---|---|---|
| D1 | melee-llm | `2bf8b0eb` (A02–A13, R07–R10) | HEAD del clon `7e179081` (+17 min). ✔ Diff de 10 ficheros, solo `docs/experiments/E32*`, `docs/experiments/README.md`, `docs/simulator.md` (+2), `web/training*` y `train/farm/{faynt,learner,rl,rl_eval,run}.py`. **Runtime, bench, sim, bots, `pyproject.toml` y `uv.lock` idénticos** | Las citas del swarm usan `7e179081`. Son válidas para `2bf8b0eb` salvo `train/farm/*`: `rl.py`, `learner.py` y `rl_eval.py` **no existen** en `2bf8b0eb`. Corrige la nota de A8 §5: `2bf8b0eb` **sí** está en el clon (se trajo con fetch) |
| D2 | melee-brute | `9662ec97` (A14, R11) como referencia | Lo que instala melee-llm es **`090e54b0`** (`pyproject.toml` L38 `[tool.uv.sources]` y `uv.lock`). E31 cita `d3832724`. La farm carga `MELEE_SIM=/mnt/data/melee/native/melee-brute` (`train/farm/common.py` L24), de revisión no registrada | `090e54b0` no tiene `hitlag_left` ni ABI v2 (gamestate 1208 B frente a 1240 B). Los resultados de la farm y de `--mode sim` pueden venir de motores distintos (A1 §11.3, A8 §3.2-8) |
| D3 | E31 (A42) | «build d3832724» | ✔ `--played-on/--no-ucf` aparecen 0 veces en `090e54b0`, 0 en `d3832724` y 4 en `9662ec97` (`tools/validation/validate_replay.py`) | E31 tiene **dos revisiones efectivas**: build `d3832724` y validador con flags de PR #19 (≥ `9662ec97`). No es reproducible solo con `d3832724` |
| D4 | melee-sim-light (A15) | Motor de referencia | melee-llm **no** lo instala. `docs/simulator.md` L7 dice «pyproject.toml pins that commit [eea7b5fb]»: desactualizado; el mismo doc L28 lo reconoce | Ancestro de melee-brute: carece de `checkpoint/rollback` (solo save/restore/copy) |
| D5 | libmelee (A16) | `bce21f09` (HEAD master) | Instalado: `0.47.6` (PyPI, `uv.lock` L569-571) = tag `v0.47.6` `2d63e7ee`. Diff: `console.py` (background_input, interrupt, GCPad) y `slippstream.py`; `controller.py` y el cuerpo de `__pre_frame` son idénticos (md5, A8 G01 §2). Faynt fija 0.47.3; HAL necesita campos de su propio fork que 0.47.6 descarta (`docs/bots.md` L24, L82) | Que el wheel de PyPI salga del tag es INFERENCIA (no se descargó) |
| D6 | MIMIC (A26) | HEAD `3691f534`; la nota menciona `bdfb6293` | ✔ `bdfb6293` (2026-11-04) traído. Diff con HEAD (2026-11-16): 302 ficheros, sobre todo `runs/` y `train.py` (34 líneas). Ancestría indeterminable en el clon shallow | Las cifras de latencia de melee-llm corresponden a `bdfb6293`; las afirmaciones de código de A2 y A6, a `3691f534` |
| D7 | `erickfm/melee-ranked-replays` (A28) | README | README **desactualizado** respecto a `ef54ddc2`: habla de `ZELDA_SHEIK` y `metadata/`, pero hay `SHEIK` y `ZELDA` separadas y no existe `metadata/`. `usedStorage` (2,15 TB) incluye historial. Las revisiones anteriores en HF siguen mal etiquetadas (A6 §1.5, notas MIMIC 2026-06-15) | Fijar siempre `ef54ddc2`. El número de partidas (~850k) queda sin verificar en esta revisión |
| D8 | `hal-mds-dataset` (A46) | Ficha | README «at most one cheap death» frente a `selection.json` `max_cheap_deaths: 2`. El build tiene `git_dirty: true` (`git_sha 03c7a168…`). Sin velocidades, `action_state_frame`, hitstun, RNG ni stick crudo | Sirve para prototipar, no como corpus de dinámica (A8 K11) |
| D9 | A29, A31, A38 | `access_status: metadata` | Se leyó el código (CÓD) | El alcance real supera lo que dice el catálogo |
| D10 | B09 | Nature s41586-020-03051-4 | Se leyó arXiv 1911.08265v2 | Las citas de A5 tienen como locator líneas del texto extraído |
| D11 | A22 | ID A22 | A2 lo citó como B19 | Corregido en el lock |
| D12 | R06 | Docs de readthedocs | No se accedió; se usó el código | El esquema de la doc puede no coincidir con 0.47.6 |
| D13 | lejepa (B02) | — | La API del README es errónea (A3 C1) | Usar `module.py` de le-wm o `loss.py` de LeVJEPA (MIT) |
| D14 | HF sin revisión | — | Faynt-10M-Expert, lewm-pusht y LeVJEPA-1.5-Large sin SHA | Hay que fijarlas antes de reutilizarlas |

**Enlaces fallidos**: ninguna evidencia registra un fallo de red o un HTTP de error. Los huecos son de **no acceso
deliberado** (§2), de **contenido no descargado** (el wheel 0.47.6, `manifest.jsonl` completo, pesos) y de A01, que
ya estaba `unverified`.

## 4. Correcciones de A8 que afectan a la trazabilidad

| Claim | Veredicto A8 | Versión consolidada | Re-verificado |
|---|---|---|---|
| A1-016 y SYSTEM_MAP de A1 | IMPRECISA: localizador falso | `bench/game.py` tiene 113 líneas: `MIN_FPS` L14, `VOID_API_FAILED_FRAC` L13, `make_agent` L17-28, `play_one` L83-104, `status_of` L107-113. **No existen** L230, L233-244, L299-320, L323-329 ni L327-328 | ✔ |
| A1-003 | IMPRECISA | `docs/bench.md` L27 ya dice «The runner waits for a late bot… marked slow». No es una contradicción oculta | (A8) |
| A4-027 | **FALSA** tal como está escrita | Corrección (A8 G01 §4): el `GameState` **no** basta para una sombra. La sombra sí es posible **desde el flujo Slippi crudo** (`ConsoleTap`), con una ampliación de la API pública de melee-brute (semilla por frame + eventos de escenario) | (A8, código citado en G01) |
| A4-021 / A5 (15/40) | IMPRECISA en el uso | Son 40 replays **de bots del autor** (`docs/simulator.md` L53). El 36/40 humano es **con** RNG grabado (L55). La tasa en humanos sin RNG es DESC | (A8) |
| A6-029 / `timing_contract.controller_semantics` | IMPRECISA | La cita «before input edges/timers» (`VALIDATION.md` L152-158) está bajo «Recorded CPU inputs». La no-Markovianidad se sostiene por `BRUTE.md` L74-80 | (A8) |
| A2-019 / A6-026 | IMPRECISA por omisión | Firoiu, Tabla 1: (6,0) 3 días, (6,6) 10 días, (7,7) 7 días de entrenamiento; 6–8 partidas por agente | (A8, mismo PDF sha256) |
| A5-036 (semilla por frame en el flujo) | DESC → resuelta | Frame Start 0x5 desde Slippi 2.2.0 y Pre-Frame 0x7 desde 0.1.0 (SPEC `3a85ce8b` L305-313, L315-342). libmelee la descarta | (A8 G01) |
| A1 «2bf8b0eb ≡ runtime» | A8 no lo repitió | **Confirmada** | ✔ |

Las demás afirmaciones auditadas están en `evidence/A8/CRITICAL_REVIEW.md` §1 (30 en total: 20 confirmadas, 9
imprecisas y 1 falsa).

## 5. Qué falta para cerrar el checklist de fuentes

- Fijar SHA de HF para Faynt-10M-Expert y Base, lewm-pusht y LeVJEPA. Fijar el sha256 del `.onnx` de Phillip elegido
  (`index-v1.json` lo trae).
- Registrar la revisión del checkout `MELEE_SIM` de la farm y el hash de las AppImage de Dolphin (A48/A49).
- Licencias pendientes: SPEC de slippi-wiki, datos de origen de ranked (Fizzi), HAL MDS `other`. melee-llm,
  melee-brute, melee-sim-light y HAL **no tienen licencia**: uso local, sin redistribuir.
- La revisión medida no existe: ningún experimento del swarm corrió sobre estas fuentes. Las únicas mediciones son de
  torch en CPU (A3, A4, A7, A8), con artefactos en `evidence/*/checks|measurements`.
