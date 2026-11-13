# Resumen de tareas — rama `ablacion-beto-personas` (cifras de ejecuciones reales)

| # | Tarea | Estado | Resultado |
|---|-------|--------|-----------|
| 0 | Rama + commit del estado previo | Hecho | commit `4634d36` en `ablacion-beto-personas` (antes de cualquier cambio) |
| 1 | Hechos vacíos | Hecho | `fact_rendimiento_academico` 0 -> 22.475; `bridge_modulo_docente` 0 -> 1.922; `fact_marketing` 0 -> 8.872 filas (15.055 inscritos). Causas abajo |
| 2 | Regla de personas | Hecho | bloqueo escalonado módulo -> programa -> dimensión, umbral 0,92. Directo 41,38 % -> 42,32 %; HITL 58,62 % -> 57,68 %; staging 0 % -> 0 % |
| 3 | Forecast | Hecho | 5/5 tests pasan sin skip |
| 4 | test_gira41 | Hecho | adaptado a `resolver_persona_detalle`; mantiene "Ing. Carlos Rojas" y verifica que no se vincula a otro docente (también contra los 638 docentes reales: `None`, `sin_candidatos`) |
| 5 | Tiempos ciclo mensual | Hecho (con límites) | 554,4 s en total; desglose abajo |
| 6 | BETO en rescatados A -> B | Hecho; no reproduce "19" | ejecución real: 7 rescatados, 2 con entidades BETO, 0 en dim_* |
| 7 | pytest sin DATABASE_URL ni PYTHONIOENCODING | Hecho | **440 passed, 0 failed, 11 skipped, 7 xfailed** (211 s) |

## 1. Hechos vacíos: causa, función, filas
- **fact_rendimiento_academico** (origen: hoja ACTAS DE NOTAS de *Base centralizada Académica ARCA*; inserta `DWLoaderService.cargar_registro` -> `FactRendimientoAcademico`). Las 8.660 filas de ACTAS llegaban a `registros_academicos` (8.660 con registros; verificado). Se perdían porque la hoja MODULOS dispara `_cargar_asignacion_docente`, y `resolver_o_crear_docente` devuelve `None` si el nombre no es persona (p. ej. "Por definir") -> `BridgeModuloDocente(id_docente=None)` -> `IntegrityError` (NOT NULL) -> HTTP 500 y **rollback de todo el documento** (el commit es único al final). Fix: `backend/services/dw_loader.py::_cargar_asignacion_docente`, 2 líneas (`if id_mod is None or id_doc is None: return {... "status": "staged"}`). Reproceso del doc 14 (ARCA): HTTP 200 en 569,7 s; 22.475 filas de rendimiento y 1.922 asignaciones.
- **fact_marketing** (origen esperado: TBL_INSCRITOS; inserta `cargar_registro`, rama `marketing`). No era un descarte: ningún código escribía en `fact_marketing` desde TBL_INSCRITOS (tipo ADMISION solo creaba `dim_estudiante`; la rama `marketing` solo corre con tipo_fuente MARKETING, que quedó asignado a *BD Techos*). Fix: `dw_loader.py` (rama `admision`: suma 1 inscrito por programa y mes, aunque la persona no se resuelva) y `backend/routers/pipeline.py` (fila de TBL_INSCRITOS: fecha = MARCA TEMPORAL, programa = NUMEROPROYECTO; la categoría de staging es `marketing`, por eso la rama `admision` no se alcanzaba). Resultado: 43 meses (2022-11 a 2026-05), 15.055 inscritos vs 15.196 filas del xlsx. **141 inscritos sin cargar** (POS-4527: 52, POS-4772: 41, POS-4907: 26, POS-4629: 16, POS-4921: 3, POS-5361: 1, POS-4153: 1, POS-6254: 1); causa no determinada (esos `pos_code` no existen en `dim_modulo`). 13 de 43 meses difieren del CSV.
- Aviso: reprocesar TBL_INSCRITOS vuelve a sumar inscritos (no hay clave de idempotencia por fila).

## 2. Personas: desglose y antes/después (DW actual: dim_estudiante 14.076, dim_docente 638)
| | Regla previa (0,85, contexto duro) | Escalonada (0,92) |
|---|---|---|
| Directo | 574 (41,38 %) | 587 (42,32 %) |
| HITL | 813 (58,62 %) | 800 (57,68 %) |
| Staging | 0 | 0 |
| Personas HITL | 1.347 (estudiantes 426 + docentes 921; todas "sin candidatos") | 1.221 (estudiantes 297 sin candidatos + 3 empate; docentes 921 sin candidatos) |

3.726 personas = 2.378 CI exacta + 127 fuzzy (126 en nivel DIMENSION, 1 en PROGRAMA) + 1.221 HITL. El nivel MÓDULO no resuelve ninguna (los estudiantes no tienen módulo y el registro casi nunca trae MODULO).
Desglose del HITL (script sin contexto de registro, `desglose_hitl_personas_por_token_y_motivo.txt`): docentes 240 de 1 token + 681 de 2+ tokens (p. ej. "KAREN ULLOA", "EVELYN PATTY": no están en dim_docente); estudiantes 122 de 1 token, 175 correos tomados como nombre, 4 empates. KPI-10 sin cambio: 0,9618 (todas), 0,9209 (solo BETO).

## 3. Forecast
- 3a: `test_extractor_series_reales` ahora pasa el engine del DW.
- 3b: causa de `sin_datos` con 48 meses: el fixture inyectaba `mock_db` cuyo `execute` lanzaba "DB offline", más el circuit breaker de 30 s y `cache_consultas`, que memorizaban `sin_datos`. El fixture usa ahora una sesión al DW y reinicia breaker y caché. Al activarlo apareció un defecto real: `forecast_service` reutilizaba un pronóstico guardado de menor horizonte (`len(rows) > 0`); corregido a `>= horizonte`.
- Efecto lateral: con el DW real, otros tests de `test_sprint4_verification_loops.py` fallaron por `deuda_total` negativa (-2, -3, -50) en la respuesta; por eso el override real se aplica solo dentro de `test_loop4_validacion_estricta_contratos`.
- 3c: la serie N=33 sale de `inscritos.csv` (raíz del repo) leído por `scripts/hw.py` (`iloc[-33:]`, 2023-09 a 2026-05). Ese CSV coincide **43/43 meses** con el conteo mensual de `MARCA TEMPORAL` de `TBL_INSCRITOS.xlsx` (15.196 filas). Sí: `fact_marketing` debe poblarse desde TBL_INSCRITOS (ahora ocurre).
- Resultado real de los 5 tests: pasan.

## 5. Tiempos (CPU, BETO en contenedor sin GPU; clon del DW; `tiempos_ciclo_mensual.json`)
Total 554,4 s: lectura/ingesta 2,4 s; reglas y resto 30,1 s (incluye ~3,6 s fijos por archivo); BETO 7,6 s; carga DW 514,1 s. El archivo PLANIFICACION (2.004 filas procesadas, 1.821 hechos) tarda 476,9 s (86 %); los demás suman ~77 s.
Límites: el recorte por mes es heurístico (hojas sin fecha de ≤100 filas completas; ARCA usó 2025-07 por no haber 2026-03; BD Techos quedó en 2034-01); *Evaluación Docente y Unifranz* no generó recorte; *[BBDD] ANTIGUO RESPUESTAS…* se excluyó (cuelga más de 30 min).

## 6. Rescatados A -> B
Con la definición del código (`ablacion_beto.py`, modo B: registros que el parser A no resuelve y pasan a BETO) el lote da **7** rescatados, no 19; A resuelve 1.380. 2 registros tienen entidades BETO; 0 de ellas está en dim_estudiante/dim_docente/dim_modulo. No hay en el repo ninguna cifra "19" (`beto_rescatados_a_b.json`). Las 50 entidades BETO (semilla 42): 1 de 50 en dim_*.

## 7. pytest
`pytest tests` con `DATABASE_URL` y `PYTHONIOENCODING` fuera del entorno: 440 passed, 11 skipped, 7 xfailed. Skips: READINESS_TOKEN (2), READINESS_TOKEN+TOKEN_2 (1), READINESS_BETO_URL (3), READINESS_DB_URL (5). Xfails: HW-IC, HW-GAP, OLS-CAGR, FK-CI-EXT, FK-HASH, FK-BANDA x2.
Los tests de forecast usan `DW_TEST_URL` (por defecto `localhost:5434`) en lugar de `DATABASE_URL`; necesitan el DW del compose arriba.
Cambios en tests: `test_person_resolver.py` (test de contexto reescrito a la regla escalonada + 3 nuevos), `test_gira41` (tarea 4), fixtures de `test_forecasting.py` y `test_sprint4_verification_loops.py`; ninguna aserción de forecast modificada.

## Qué capturar para la tesis
- `lote_1387_uploads_data_arquitectura_b.json`: `personas`, `personas_hitl_desglose_*`, `distribucion_bandas_*`, `kpis`.
- `tiempos_ciclo_mensual.json`: `suma_etapas_ms`, `archivos[]`.
- `pytest_completo_sin_env.txt`: línea final y "short test summary info".
- `beto_rescatados_a_b.json`, `muestra_50_entidades_beto_semilla42.json`, `desglose_hitl_personas_por_token_y_motivo.txt`.
- Comparativos: `..._regla_previa_dw_parcial.json`, `..._dw_casi_vacio.json`, `..._previo_tarea1.json`.
