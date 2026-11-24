# CIERRE F6_HITL_BETO — 2026-11-24
Rama / commit: `main` `c0a5f67`
Hecho:
- F6-0: Levantada copia `tmpfs` aislada (`beto_pg_tmpfs`, sin tocar `snapshot_dw_20261110_1201`) y registrada línea base en `docs/mediciones/f6_linea_base.json`.
- F6-1: Implementado Extractor de Contexto de Hoja (Nivel 1) en `pipeline/ingesta.py`, `backend/services/beto_integracion.py`, `backend/services/ingestion_service.py` y `backend/routers/dataops/consolidacion.py` (`<= 1` inferencia BETO/hoja, solo diccionario mínimo `contexto_hoja` sin repetir `contexto_hoja_texto` en `payload_json`, herencia con `heredado_de_hoja=True` sin pisar valores explícitos).
- F6-2a: Encuestas Likert validadas por `encuesta_canonica.perfilar` marcadas en `fila_resuelta_por_regla` y excluidas de `refinar_lineas` (`BAJA_CONFIANZA_IA` en `Evaluación Docente y Unifranz.xlsx`: `573` / `4.240` → `0`).
- F6-2b: Auto-hidratación de placeholders `Estudiante <CI>` / `Estudiante CI ...` en `backend/services/dw_loader.py` antes de `CI_NOMBRE_DISCORDANTE` con log informativo `PLACEHOLDER_HIDRATADO` (`0` casos `CI_NOMBRE_DISCORDANTE` con placeholder).
- F6-2c: Colisión real `>= 2` `id_estudiante` distintos en `HOMONIMIA` manteniendo umbrales `90 %` y `0,92`; candidato único `>= 92 %` (o `100 %`) resuelve directo en estado `B`.
- F6-3a (D-F6-1): Cruce en memoria `MODULOS → ACTAS DE NOTAS` (`indexar_modulos_arca` + `registros_academicos`) con fecha de respaldo trazable (`FECHA_RESPALDO_ARCA`) solo en estados cerrados válidos (`Titulado` / `Aprobado` / `Reprobado`); `HECHO_EN_REVISION` en ARCA bajó de `14.265` a `1.009` (`-92,93 %`), manteniendo `100 %` de notas anómalas y estados abiertos/inválidos en revisión.
- F6-3b (D-F6-2, D-F6-3): `BETO_ACUERDO_QC` acotado solo a `FUZZY` (`0` `DESACUERDO_REGLA_BETO` sobre `ENCABEZADO`), `BETO_RESCATE_ACADEMICO=True`, `BETO_SUGERENCIA_CORTE_SIMILITUD=80.0`, sugerencias HITL restringidas a `ENTIDAD_NUEVA`, `HOMONIMIA`, `POS_NO_EN_DIM_MODULO`, `BAJA_CONFIANZA_IA` (`0` en errores de nota/monto).
- F6-3c: Selección inteligente de hasta 8 celdas textuales relevantes en `pipeline/semantic/indice_confianza.py` (`MAX_LENGTH_TOKENS=128` intacto) y `MODELO=beto-v2-f6` con SHA-256 sobre texto filtrado en `backend/services/confianza_service.py`.
- F6-4a/4b/4c: Suite `pytest` en verde (`77 passed, 1 skipped, 0 failed`), invariantes `51 / 10 / 23` confirmados, regresión A/B y corrida completa de 10 libros en `beto_pg_tmpfs`, rebuild de `api` y `pipeline` (`9/9` Up/healthy), verificación visual en `http://localhost:5173` (HTTP 200, login institucional sin errores).
No hecho y por qué:
- Verificación visual autenticada de vistas internas DataOps/CMI en navegador: no se ingresaron credenciales ni se evadió 2FA (solo se verificó la carga limpia de `http://localhost:5173/v2/login`).
Invariantes cambiados: no (`{"tablas_public_bi": 51, "vistas_bi": 10, "kpis_ref": 23}` en `docs/mediciones/f6_invariantes.json`; umbrales `0,92 / 90 % / 85 % / 80 %`, bandas `0,85 / 0,60`, cascada `CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO` y `128` tokens intactos).
Pruebas: 77 passed / 0 failed / 1 skipped (`tests/beto_activo/`, `tests/adw/test_l7_pipeline.py`, `tests/sprint3/test_beto_*`, `tests/sprint5/test_beto_*`, `tests/sprint5/test_ba_l3_ruteo.py`) · unitarias F6-1 (`4 passed`) y F6-3 (`4 passed`).
Servicios reconstruidos + estado de docker compose ps: `api` y `pipeline` reconstruidos; 9 servicios Up/healthy (`api`, `pipeline`, `web`, `gateway`, `db`, `catalog_db`, `auth-service`, `audit-service`, `notifications-service`); `GET http://localhost:8000/health` → `200 {"status":"healthy","database":"connected"}`.
Cambios de esquema o API: ninguno (51 tablas, 10 vistas `bi`, 23 KPIs en `bi.ref_kpi` intactos; sin nuevas migraciones ni cambios de contrato REST).
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- `ARCA hechos en revisión` | `1.009` (antes `14.265`, `-92,93 %`) | `docs/mediciones/f6_arca_cruce_diff.json`
- `Evaluación Docente y Unifranz BAJA_CONFIANZA_IA` | `0` (antes `573` f5r / `4.240` f5v) | `docs/mediciones/f6_encuestas_diff.json`
- `CI_NOMBRE_DISCORDANTE con placeholder` | `0` | `docs/mediciones/f6_placeholders_diff.json`
- `Placeholders en fact_rendimiento_academico / fact_situacion_financiera` | `0` / `1` | `docs/mediciones/f6_auditoria_dw.json`
- `Bandeja HITL 10 archivos Modo B (vs 676 previos)` | `141` (`-79,1 %`) · tiempo `120,7 s` (`2,01 min`, RNF-03 `< 15 min` cumplido) | `docs/mediciones/f6_aporte_10archivos.json`
- `Bandeja HITL corrida completa 10 libros (vs 10.781 f5v)` | `1.902` (`-82,4 %`) · tiempo `1.309,05 s` (`21,8 min` vs `3.987,41 s` f5v, `-67,2 %`) | `docs/mediciones/f6_completo.json`, `docs/mediciones/f6_auditoria_dw.json`
- `DESACUERDO_REGLA_BETO sobre ENCABEZADO / sugerencias en motivos no-identidad` | `0` / `0` (`3` desacuerdos sobre `FUZZY`, `35` personas residuales rescatadas por BETO) | `docs/mediciones/f6_beto_rol_diff.json`
- `Bloques con contexto_hoja / con texto crudo repetido` | `11` (completo), `13` (10 archivos) / `0` | `docs/mediciones/f6_auditoria_dw.json`
Impacto en el documento (sección o tabla): Cap. 3/4 (sección de cascada BETO + contexto de hoja Nivel 1, tabla comparativa A/B de bandeja HITL, tabla de auditoría ARCA y tiempos RNF-03; solo vía Chat 3 tras congelar en `docs/fuente_verdad_tesis.md`).
Riesgos abiertos:
- En la corrida completa histórica de 10 libros con caché fría (`~500k` filas), el tiempo total fue `21,8 min` (frente a `66,5 min` en `f5v`), impulsado por la carga inicial sin caché de `TBL_INSCRITOS` (`382 s`) y `ARCA` (`304 s`); en el ciclo mensual/10 archivos (`f6_aporte_10archivos.json`) cumple holgadamente RNF-03 (`2,01 min < 15 min`).
- Queda `1` registro en `fact_situacion_financiera` asociado a un placeholder preexistente en `dw_vacio` cuyo CI no apareció con nombre real en ninguno de los 10 libros.
Pendiente para el chat 4:
- Generar figuras/tablas comparativas F5 vs F6 (bandeja HITL, ARCA en revisión `-92,93 %`, tiempos RNF-03) a partir de `docs/mediciones/f6_*.json`.
