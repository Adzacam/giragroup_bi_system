# PLAN F11_REVISION_GRUPOS_UX — 2026-11-25

Objetivo de la fase (1 línea): Facilitar la revisión HITL en el Paso 3 sobre lotes grandes (Lote #1: 1.573 casos) reemplazando hashes opacos por etiquetas legibles, consolidando los 589+ grupos unitarios de `CI_NOMBRE_DISCORDANTE` en 3 bandas clicables y habilitando aprobación controlada por selección múltiple / banda segura (bloqueando aprobación masiva en `< 30`).

Entrada: CIERRE previo leído = `docs/cierres/CIERRE_F11_PREDEFENSA_SEMILLA.md`; rama base = `main` (`59176e8`); evidencia visual = capturas de Paso 3 (`Por grupos`: `839` grupos / `168` páginas, `609` parcial `30–59`, `121` muy distinto `< 30`, `12` casi igual `>= 60`).

## Tabla de tareas

| ID | Frente | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en `docs/mediciones/` |
|---|---|---|---|---|---|---|---|
| RG-1 | Backend: etiquetas legibles + agrupación por banda | En `backend/services/bandeja_grupos.py`, `backend/services/revision_consulta.py` y `backend/routers/dataops/revision.py`: (1) Reemplazar los hashes visibles (`#1f00c2`, `#e3eae8`, etc.) en el subtítulo de cada grupo por una etiqueta legible (`Archivo · Programa / Módulo o Hoja · Banda de confianza`), moviendo el hash corto a un campo secundario (`clave_corta` / tooltip); (2) Consolidar `CI_NOMBRE_DISCORDANTE` en `GET /review-tray/grupos` en las **3 bandas de similitud** (`>= 60` casi igual, `30–59` parcialmente distinto, `< 30` muy distinto) en lugar de emitir 1 grupo por cada CI individual (reduciendo drásticamente de `839` grupos / `168` páginas a grupos compactos); (3) Soportar filtro por `banda_discordancia` (`casi_igual`, `parcial`, `muy_distinto`) en `GET /review-tray` | `dev-media` | — | — | (a) `GET /review-tray/grupos` sobre Lote #1 baja de `839` grupos a `< 120` grupos sin perder ninguno de los `1.573` casos pendientes; (b) Ningún título/subtítulo principal de grupo muestra `#xxxxxx` sin descripción legible; (c) `GET /review-tray?banda_discordancia=...` filtra exactamente los `12` / `609` / `121` casos correspondientes | `rg_grupos_antes_despues.json` |
| RG-2 | Backend: gobernanza de aprobación controlada | En `backend/routers/dataops/revision.py` (`POST /review-tray/batch-resolve` y `POST /review-tray/approve-group`): (1) Permitir aprobar en bloque la sección completa únicamente para **`Nombre casi igual (>= 60)`** (con justificación obligatoria registrada en `log_auditoria_nlp`); (2) Permitir `batch-resolve` solo sobre IDs seleccionados explícitamente por el auditor para **`Nombre parcialmente distinto (30–59)`** y **`Lectura con baja confianza`**; (3) **Rechazar con HTTP `400`/`403` cualquier intento de aprobación masiva** si la selección incluye casos de **`Nombre muy distinto (< 30)`** (forzando revisión individual por riesgo de CI mal digitado o personas distintas); (4) Mantener idempotencia estricta (0 duplicados) y pruebas unitarias | `dev-media` | RG-1 | — | Tests `pytest` confirman: (a) aprobación en bloque permitida en `>= 60`; (b) selección explícita permitida en `30–59` y `BAJA_CONFIANZA_IA`; (c) rechazo explícito (`400`/`403`) al intentar aprobar en lote casos `< 30`; (d) trazabilidad completa en auditoría | `rg_gobernanza_test.txt` |
| RG-3 | Frontend: chips clicables, etiquetas limpias y selección múltiple | En `frontend/src/modules/dataops/components/GruposBandeja.jsx`, `frontend/src/modules/dataops/HumanReviewFlowView.jsx` y `frontend/src/api/dataopsApi.js`: (1) Mostrar la etiqueta legible de cada grupo (y el hash solo en `title`/tooltip secundario); (2) Convertir los 3 chips superiores (`Nombre casi igual >= 60`, `Nombre parcialmente distinto 30–59`, `Nombre muy distinto < 30`) en **filtros clicables directos** que abren la lista de casos de esa banda; (3) En la vista de casos pendientes filtrados por banda/grupo, añadir casillas de selección múltiple + **"Seleccionar página"** + barra de acción **"Confirmar seleccionados"** (con campo de justificación) para `>= 60` (más botón **"Aprobar sección (>= 60)"**), `30–59` y `Lectura con baja confianza`; (4) Ocultar/deshabilitar toda acción masiva en **`Nombre muy distinto (< 30)`** con aviso claro *"Revisión individual obligatoria (posible CI mal digitado)"*; (5) Respetar paleta/tokens en modo claro y oscuro (`/modern-web-guidance`) | `dev-media` | RG-1, RG-2 | — | (a) Chips filtran casos en 1 clic sin recargar; (b) Selección múltiple y aprobación controlada actualizan contadores en vivo sin duplicar ni perder casos; (c) En `< 30` no existe botón de aprobación masiva; (d) Modo claro y oscuro sin defectos de contraste | `rg_front_check.md` |
| RG-4 | Pruebas, rebuild y verificación visual | (1) Ejecutar `pytest` (backend) y `npx vitest run && npm run build` (frontend), rebuild de `api` y `web` (`dev-baja`); (2) Verificar visualmente en `/browser` a `1280×800` en **modo claro y oscuro** sobre Lote #1 (sin re-ingestar archivos): etiquetas legibles sin `#hash` dominante, chips clicables, selección múltiple en `>= 60`/`30–59`/`BAJA_CONFIANZA_IA`, bloqueo masivo en `< 30`, contadores consistentes y `0` errores de consola; (3) Commit limpio y `docs/cierres/CIERRE_F11_REVISION_GRUPOS_UX.md` | `dev-baja` (tests/build/rebuild) + `dev-media` (`/browser` + cierre) | RG-3 | — | `pytest` `0 failed`; `vitest` `0 failed`; `vite build` verde; `9/9` servicios Up/healthy; `0` errores de consola en `1280×800` claro/oscuro; `CIERRE_F11_REVISION_GRUPOS_UX.md` escrito | `rg_pruebas_back.txt`, `rg_pruebas_front.txt`, `docs/cierres/CIERRE_F11_REVISION_GRUPOS_UX.md` |

## Comandos exactos por tarea
- Pruebas backend (`RG-4`): `pytest tests/sprint5/test_ba_l3_ruteo.py tests/sprint5/test_beto_sugerencia_hitl.py tests/sprint5/test_w4_formularios.py -q` (más el nuevo test de gobernanza `RG-2`).
- Pruebas y build front (`RG-4`): `cd frontend && npx vitest run && npm run build`.
- Rebuild (`RG-4`): `docker compose up -d --build --no-deps api web && docker compose ps`.

## Riesgos y control
- **Gobernanza HITL:** Prohibido crear un botón "Insertar todo a ciegas". La validación de bloqueo para `< 30` se exige **tanto en frontend como en backend** (`RG-2` + `RG-3`).
- **Pérdida de datos (`accidental-data-loss-prevention`):** No re-ingestar archivos, no tocar `snapshot_dw_20261110_1201` ni `backups/snapshot_pre_defensa.*`. Si se prueba una aprobación en vivo durante `RG-4`, restaurar `backups/snapshot_pre_defensa.dump` al terminar si se desea mantener intacto el lote de demo.
- **Invariantes intactos:** Umbrales (`0,92 / 90 % / 85 % / 80 % / 0,85 / 0,60`), cascada y esquema (`51 / 10 / 23`) sin cambios.

## DECISIONES PENDIENTES PARA LEAN
- Ninguna (reglas de gobernanza y bandas ya especificadas explícitamente por el usuario).

Al cerrar: pytest (`0 failed`) · vitest (`0 failed`) · vite build · verificación visual `/browser` `1280×800` (claro/oscuro) · rebuild `api` y `web` · commit · `CIERRE_F11_REVISION_GRUPOS_UX.md`

## PROMPT PARA CHAT 2
```text
/gira-desarrollar
Ejecuta `docs/cierres/PLAN_F11_REVISION_GRUPOS_UX.md` en orden (RG-1 → RG-2 → RG-3 → RG-4).
No re-ingestes archivos ni toques `snapshot_dw_20261110_1201` ni ningún umbral invariante de `AGENTS.md`.
Asegúrate de que: (1) los grupos muestren etiquetas legibles (hash solo en tooltip); (2) los 3 chips de `CI_NOMBRE_DISCORDANTE` filtren directamente los casos sin crear cientos de grupos de 1 caso; (3) la aprobación masiva esté permitida solo para `>= 60` y selección explícita en `30–59` / `BAJA_CONFIANZA_IA`, y bloqueada tanto en backend como en frontend para `< 30`.
Usa `dev-baja` únicamente para comandos de consola, pruebas y rebuild (`RG-4`); ejecuta la lógica y la verificación visual `/browser` en `1280×800` (claro y oscuro) en `dev-media`.
Al terminar, escribe `docs/cierres/CIERRE_F11_REVISION_GRUPOS_UX.md`.
```
