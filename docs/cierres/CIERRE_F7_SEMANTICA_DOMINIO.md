# CIERRE F7_SEMANTICA_DOMINIO — 2026-11-24
Rama / commit: `main` `6f9beb3`
Hecho:
- F7-0: Verificado `beto_pg_tmpfs` (sin tocar `snapshot_dw_20261110_1201`) y registrada línea base en `docs/mediciones/f7_linea_base.json` (`scripts/f6_regresion_tmpfs.py`).
- F7-1a: Corregida agregación de `tasa_acuerdo` (`agregar_beto_totales`: `round(acuerdos / comparadas_acuerdo, 4)` sobre totales acumulados); verificada en `[0.0, 1.0]` (`0.9857` en test F6, `0.9952` en corrida F7 completa).
- F7-1b: Acotado `BETO_RESCATE_ACADEMICO` a hojas sin columna estructurada de `PROGRAMA`/`MÓDULO` (`hoja_tiene_columnas_academicas` en `backend/services/beto_integracion.py` + `backend/routers/dataops/consolidacion.py`); `residuales_academicas_enviadas` cayó de `11.812` a `1.186` (`-90,0 %`), `textos_inferidos` de `10.757` a `3.123` (`-71,0 %`) y `tiempo_beto_s` de `141,11 s` a `82,80 s` (`-41,3 %`).
- F7-2a: Añadido `POST /embed` en `pipeline/semantic/inference_server.py` (mean pooling respetando `attention_mask`, `768` dim, normalización L2, reutilizando `beto_local` en memoria, límite `128` tokens); benchmark en CPU: `47,48 ms` interno para 20 encabezados (`< 50 ms`).
- F7-2b (D-F7-1): Implementado `backend/services/mapeo_semantico_encabezados.py` + respaldo `resolver_encabezados_beto_esquema` en `backend/routers/dataops/extraccion.py` con triple compuerta (`coseno >= 0.78`, margen `top1 - top2 >= 0.05`, perfil de columna obligatorio sobre 20 valores), origen `BETO_ESQUEMA` y `0` sobrescrituras sobre RapidFuzz `>= 85.0`.
- F7-3 (D-F7-2): Implementada compuerta de dominio CMI `evaluar_compuerta_dominio_cmi` en `pipeline/ingesta.py` + aislamiento `FUERA_DE_ALCANCE_CMI` (`es_ruido=True`, `log_inconsistencias` `REGISTRADO`) en `backend/services/ingestion_service.py` + campo aditivo `fuera_de_alcance_cmi` en `backend/schemas/dataops_schemas.py` y `backend/routers/dataops/ingesta.py`. `0` hojas útiles descartadas en los 10 libros reales.
- F7-4a/4b/4c: Suite `pytest` en verde (`82 passed, 1 skipped, 0 failed`), invariantes `51 / 10 / 23` confirmados, regresión A/B y completa en `beto_pg_tmpfs`, rebuild de `api` y `pipeline` (`9/9` Up/healthy).
No hecho y por qué:
- La corrida histórica completa de los 10 libros con caché fría (~500k filas) registró `1.617,7 s` (`26,9 min` de reloj en host con carga concurrente, aunque `tiempo_beto_s` bajó a `82,8 s` [-41,3 %]); el cuello de botella remanente no es BETO sino el bucle SQL/fuzzy de `TBL_INSCRITOS` (`562 s`) y `BD Cobranzas` (`341 s`). En el lote de 10 archivos (`f7_aporte_10archivos.json`), Modo B completó en `174,23 s` (`2,90 min < 15 min`, RNF-03 cumplido).
Invariantes cambiados: no (`{"tablas_public_bi": 51, "vistas_bi": 10, "kpis_ref": 23}` en `docs/mediciones/f7_invariantes.json`; umbrales `0,92 / 90 % / 85 % / 80 %`, bandas `0,85 / 0,60`, cascada `CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO` y `128` tokens intactos).
Pruebas: 82 passed / 0 failed / 1 skipped (`docs/mediciones/f7_pruebas.txt`, `f7_tasa_acuerdo_test.txt`, `f7_mapeo_semantico_test.txt`, `f7_compuerta_dominio_test.txt`).
Servicios reconstruidos + estado de docker compose ps: `api` y `pipeline` reconstruidos; 9 servicios Up/healthy (`api`, `pipeline`, `web`, `gateway`, `db`, `catalog_db`, `auth-service`, `audit-service`, `notifications-service`); `GET http://localhost:8000/health` → `200 {"status":"healthy","database":"connected"}`.
Cambios de esquema o API:
- Esquema DW: sin cambios (51 tablas, 10 vistas `bi`, 23 KPIs en `bi.ref_kpi`).
- API interna (`pipeline:8006`): nuevo endpoint aditivo `POST /embed` (`textos`, `max_length <= 128` → embeddings `768` dim L2-normalizados).
- API ingesta (`/api/v1/dataops/upload`): campo aditivo `fuera_de_alcance_cmi: int = 0` en `FileUploadResponse` / `BatchUploadItem` y en `kpis`.
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- `POST /embed (20 encabezados, CPU)` | `47,48 ms` interno · `768` dim · norma L2 `1.0` | `docs/mediciones/f7_embed_bench.json`
- `residuales_academicas_enviadas (F6 → F7)` | `11.812 → 1.186` (`-90,0 %`) | `docs/mediciones/f7_rescate_acotado_diff.json`
- `textos_inferidos BETO (F6 → F7)` | `10.757 → 3.123` (`-71,0 %`) · `tiempo_beto_s`: `141,11 s → 82,80 s` (`-41,3 %`) | `docs/mediciones/f7_rescate_acotado_diff.json`
- `tasa_acuerdo corregida (F7 completo)` | `0.9952` (antes bug `1.657`) | `docs/mediciones/f7_completo.json`
- `Bandeja HITL 10 archivos Modo B (F6 → F7)` | `141 → 141` (`0` regresiones) · `174,23 s` (`2,90 min < 15 min`) | `docs/mediciones/f7_aporte_10archivos.json`
- `Bandeja HITL corrida completa (F6 → F7)` | `1.902 → 1.901` (`0` regresiones) | `docs/mediciones/f7_completo.json`
- `fuera_de_alcance_cmi en 10 libros reales` | `0` (`100 %` cobertura útil) | `docs/mediciones/f7_completo.json`
Impacto en el documento (sección o tabla): Cap. 3/4 (arquitectura de mapeo semántico de encabezados `BETO_ESQUEMA`, compuerta de dominio CMI en ingesta y optimización de inferencia BETO `-41,3 %`; solo vía Chat 3 tras congelar en `docs/fuente_verdad_tesis.md`).
Riesgos abiertos:
- El tiempo de reloj de la carga histórica completa de ~500k filas (`26,9 min` con caché fría) está dominado por el bucle de escritura/fuzzy de `TBL_INSCRITOS` y `BD Cobranzas` en PostgreSQL, no por BETO (`82,8 s` totales); optimizar inserción masiva en `TBL_INSCRITOS`/`COBRANZA` bajaría también la carga histórica bajo `15 min`.
Pendiente para el chat 4:
- Generar comparativa F6 vs F7 (`residuales_academicas_enviadas`, `tiempo_beto_s`, `POST /embed`, compuerta CMI) a partir de `docs/mediciones/f7_*.json`.
