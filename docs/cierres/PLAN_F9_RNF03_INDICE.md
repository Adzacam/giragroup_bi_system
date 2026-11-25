# PLAN F9_RNF03_INDICE — 2026-11-24

Objetivo de la fase (1 línea): Cerrar la brecha de RNF-03 (`< 15 min`) en carga histórica fría omitiendo llamadas redundantes a `POST /indice` en filas estructuradas de `MARKETING` (`TBL_INSCRITOS`) y `COBRANZA` (`BD Cobranzas`) resueltas por regla, verificando `KPI-10` y alineando los 2 asserts pendientes de `test_beto_sugerencia_hitl.py`.

Entrada: CIERRE previo leído = `docs/cierres/CIERRE_F8_PULIDO_RENDIMIENTO.md`; mediciones base = `docs/mediciones/f8_completo.json`, `docs/mediciones/f8_perfil_sql.json`, `docs/mediciones/f8_pruebas.txt`; rama base = `main` (`281feb7`).

## Tabla de tareas

| ID | Frente | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en `docs/mediciones/` |
|---|---|---|---|---|---|---|---|
| F9-0 | Pre-vuelo | Verificar `beto_pg_tmpfs` aislado (sin tocar `snapshot_dw_20261110_1201`) y confirmar las ramas actuales de `fila_resuelta_por_regla` en `backend/services/extraccion_por_encabezado.py:985-1003` y su invocación en `backend/routers/dataops/consolidacion.py` | `dev-baja` | — | — | Rama limpia (`281feb7`), `tmpfs` disponible y línea base F8 (`1459.49 s`, `1901` bandeja) registrada | `f9_linea_base.json` |
| F9-1a | Recorte `/indice` (`MARKETING` / `COBRANZA`) | Implementar regla estricta en `fila_resuelta_por_regla` (`backend/services/extraccion_por_encabezado.py`) para `marketing`/`admision` y `financiero` + prueba unitaria explícita de casos `True`/`False` | `dev-media` | F9-0 | F9-1b | (a) Test unitario en verde (`True` completas / `False` residuales); (b) `TBL_INSCRITOS` baja de `541,51 s` a `< 100 s` y `BD Cobranzas` de `353,70 s` a `< 80 s`; (c) `0` pérdida de hechos en `fact_marketing` (`9.208`) y `fact_situacion_financiera` (`27.190`); (d) `CI_NOMBRE_DISCORDANTE` (`dw_loader.py`) y `RELACION_INCOHERENTE` (`validar_registro`) intactos | `f9_indice_recorte_diff.json`, `f9_fila_regla_test.txt` |
| F9-1b | Pruebas unitarias | Alinear los 2 asserts preexistentes de F6-3b en `tests/sprint5/test_beto_sugerencia_hitl.py` (`test_candidatos_por_similitud_enmascara_la_cedula` al corte `80.0` y `test_la_api_agrega_el_campo_solo_cuando_hay_sugerencias_y_no_cambia_el_resto` al contrato actual que expone `candidatos` junto a `sugerencias_beto`) | `dev-baja` | F9-0 | F9-1a | `pytest tests/sprint5/test_beto_sugerencia_hitl.py` en `0 failed` sin relajar ninguna validación de seguridad ni enmascaramiento | `f9_sugerencia_test.txt` |
| F9-2 | Pruebas, regresión, `KPI-10` y RNF-03 | Ejecutar suite `pytest` completa, validar invariantes (`51 / 10 / 23`), correr regresión completa de 10 libros (~500k filas, **caché fría**) y lote de 10 archivos en `beto_pg_tmpfs`, y verificar `KPI-10` / `fact_situacion_financiera.nivel_confianza_ia` en el scorecard | `dev-media` | F9-1a, F9-1b | — | (a) `pytest` `0 failed`; (b) Carga histórica completa fría `< 15 min` (`< 900 s`, `rnf03_cumplido_15m: true`); (c) Lote 10 archivos Modo B `< 5 min` con `141` casos en bandeja; (d) `KPI-10` en el scorecard no es `NULL` ni se degrada (`nivel_confianza_ia` poblado desde `extract_entities_from_line`); (e) Invariantes `51 / 10 / 23` intactos | `f9_completo.json`, `f9_aporte_10archivos.json`, `f9_pruebas.txt`, `f9_invariantes.json`, `f9_kpi10_check.json` |
| F9-3 | Cierre | Rebuild de `api`, verificar `docker compose ps` (`9/9` Up/healthy) y `GET /health` 200, commit limpio y escribir `docs/cierres/CIERRE_F9_RNF03_INDICE.md` | `dev-baja` | F9-2 | — | `9/9` servicios Up/healthy; `GET /health` 200; commit realizado; `CIERRE_F9_RNF03_INDICE.md` escrito | `docs/cierres/CIERRE_F9_RNF03_INDICE.md` |

## Detalle técnico de implementación

### F9-1a — Regla estricta en `fila_resuelta_por_regla` (`backend/services/extraccion_por_encabezado.py`)
1. **Validación de CI sobre `campos`:** usar `estudiante_de_fila(campos)` y comprobar que el CI extraído no sea `None`, no contenga `?`, no empiece con `TEMP-` y pase `PATRON_CI_BOLIVIA` (`pipeline/config.py:132`, `^\d{5,9}(?:-[0-9A-Za-z]{1,3})?$`, tras limpiar puntos/espacios) + que exista nombre no vacío en la fila.
2. **Rama `categoria in ("marketing", "admision")` (`TBL_INSCRITOS`):**
   - Mantener `registros_techo_convenio(campos)` como condición válida existente.
   - Retornar `True` también cuando la fila tenga **CI válida + nombre presente + programa/POS presente** (`NUMEROPROYECTO`, código `POS-*` o `NOMBRE DEL PROGRAMA` no vacío).
   - Cualquier fila sin CI, con CI dudosa (`?` o `< 5` dígitos), sin nombre o sin programa retorna `False` y continúa hacia BETO (`POST /indice`).
3. **Rama `categoria == "financiero"` (`BD Cobranzas`):**
   - Retornar `True` solo cuando la fila tenga **CI válida + nombre presente** y al menos un campo financiero numérico válido (`registros_cobranza(campos, ...)` no vacío, o valor numérico válido en `monto_deuda`, `monto_pagado` o `cuotas_impagas` usando `parsear_monto`).
   - Toda fila incompleta, sin CI, con CI dudosa o texto libre retorna `False` y sigue pasando a BETO (`POST /indice`).
4. **Garantía de integridad:** omitir `POST /indice` en `indices_cascada` **no** desactiva ni `CI_NOMBRE_DISCORDANTE` (evaluado en `dw_loader.py` contra `dim_estudiante`) ni `validar_registro` (`RELACION_INCOHERENTE` en `consolidacion.py`).
5. **Prueba unitaria explícita:** agregar test unitario (p. ej. `tests/sprint5/test_f9_fila_resuelta_regla.py`) verificando:
   - `marketing`/`admision`: fila completa con CI boliviana válida + nombre + programa → `True`; sin CI, con `CI` `"123?"` (`CI_DUDOSA`) o sin programa → `False`.
   - `financiero`: fila completa con CI válida + nombre + monto/cuotas válidos → `True`; sin CI, con `CI` `"123?"` o sin campo financiero numérico → `False`.

### F9-1b — Alinear 2 asserts en `tests/sprint5/test_beto_sugerencia_hitl.py`
1. `test_candidatos_por_similitud_enmascara_la_cedula`: ajustar la similitud del dato de prueba o el corte esperado al nuevo default `BETO_SUGERENCIA_CORTE_SIMILITUD = 80.0` (aprobado en `D-F6-3`), manteniendo intacta la verificación de enmascaramiento de CI.
2. `test_la_api_agrega_el_campo_solo_cuando_hay_sugerencias_y_no_cambia_el_resto`: alinear el assert de claves esperadas al contrato actual que expone `candidatos` junto a `sugerencias_beto`.

### F9-2 — Verificación de `KPI-10` y RNF-03
- Confirmar en `docs/mediciones/f9_kpi10_check.json` que `fact_situacion_financiera.nivel_confianza_ia` queda poblado (desde el `score` de `extract_entities_from_line` cuando `indice is None`) y que `KPI-10` en `/api/v1/cmi/scorecard` (o consulta directa a la vista `bi`) no devuelve `NULL` ni se degrada respecto a F8.
- Confirmar en `docs/mediciones/f9_completo.json` que la carga histórica completa con caché fría baja de `1459.49 s` (`24,32 min`) a **`< 900 s` (`< 15 min`)** (`rnf03_cumplido_15m: true`).

## Comandos exactos por tarea
- Pre-vuelo (`F9-0`): `git status` y comprobar contenedor `beto_pg_tmpfs` (prohibido mutar `snapshot_dw_20261110_1201`).
- Pruebas unitarias (`F9-1a`, `F9-1b`): `pytest tests/sprint5/test_f9_fila_resuelta_regla.py tests/sprint5/test_beto_sugerencia_hitl.py -v`.
- Suite completa (`F9-2`): `pytest tests/beto_activo/ tests/adw/test_l7_pipeline.py tests/sprint3/test_beto_* tests/sprint5/test_beto_* tests/sprint5/test_ba_l3_ruteo.py -q`.
- Regresión (`F9-2`): ejecutar corrida completa (caché fría) y lote de 10 archivos en `beto_pg_tmpfs` guardando `docs/mediciones/f9_completo.json`, `docs/mediciones/f9_aporte_10archivos.json`, `docs/mediciones/f9_kpi10_check.json` y `docs/mediciones/f9_invariantes.json`.
- Rebuild (`F9-3`): `docker compose up -d --build --no-deps api && docker compose ps`.

## Riesgos y control
- **Pérdida de datos (`accidental-data-loss-prevention`):** Prohibido mutar `snapshot_dw_20261110_1201`; toda regresión corre en clones aislados sobre `beto_pg_tmpfs`.
- **Falsos negativos en HITL:** `fila_resuelta_por_regla` exige `PATRON_CI_BOLIVIA` + `estudiante_de_fila(campos)` + programa/campo financiero válido; las filas residuales o dudosas siguen pasando a BETO y HITL, y `CI_NOMBRE_DISCORDANTE` + `validar_registro` permanecen activos.
- **Degradación de `KPI-10`:** Verificación obligatoria en `F9-2` (`f9_kpi10_check.json`).
- **Invariantes intactos:** Sin cambios en umbrales (`0,92 / 90 % / 85 % / 80 % / 0,85 / 0,60`), cascada (`CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO`), `128` tokens ni esquema (`51 / 10 / 23`).

## DECISIONES APROBADAS POR LEAN
- **D-F9-1 (Aprobada):** Aplicar recorte estricto en `fila_resuelta_por_regla` (`backend/services/extraccion_por_encabezado.py`) para `marketing`/`admision` y `financiero` (sin modificar umbrales ni requerir GPU) para cerrar RNF-03 (`< 15 min`) incluso en carga histórica fría.

Al cerrar: pytest (`0 failed`) · regresión fría `< 15 min` · `KPI-10` verificado · rebuild `api` · commit · `CIERRE_F9_RNF03_INDICE.md`

## PROMPT PARA CHAT 2
```text
/gira-desarrollar
Ejecuta `docs/cierres/PLAN_F9_RNF03_INDICE.md` en orden (F9-0 → F9-1a/F9-1b en paralelo → F9-2 → F9-3).
En `F9-1a`, edita `fila_resuelta_por_regla` en `backend/services/extraccion_por_encabezado.py` validando sobre `campos`: `PATRON_CI_BOLIVIA` (sin `?`, 5–9 dígitos) + `estudiante_de_fila(campos)` + programa/POS (en `marketing`/`admision`) o `registros_cobranza`/campo financiero numérico válido (en `financiero`), e incluye el test unitario explícito de casos `True`/`False`.
En `F9-2`, verifica explícitamente que `KPI-10` en el scorecard no quede `NULL` ni se degrade (`f9_kpi10_check.json`).
Usa `dev-baja` para pre-vuelo, `F9-1b` y rebuild/cierre; ejecuta `F9-1a` y la regresión `F9-2` en `dev-media`.
No modifiques `snapshot_dw_20261110_1201` ni ningún invariante de `AGENTS.md`. Al terminar, escribe `docs/cierres/CIERRE_F9_RNF03_INDICE.md`.
```
