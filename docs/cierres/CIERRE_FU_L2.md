# CIERRE FU-L2 — 2026-11-21
Rama / commit: beto-integracion (ver `git log`, commit `fu(L2)`)

Hecho (máx. 10 líneas):
- Lector canónico de cobranza (`cobranza_canonica.py`, `regla_mora.py`): campos por sinónimos del catálogo; `TIPO DE CARTERA` → `estado_cartera_fuente`; `TOTAL CUOTAS EN MORA` → `cuotas_impagas`; `DIAS DE MORA` → `dias_mora`. La cabecera ambigua `mora` ya no pisa a la específica. Sin «contiene MORA» en el código.
- DA3: mora = `cuotas_impagas ≥ 2`, una sola regla en `bi.vw_cmi_valores`, `bi.vw_cartera_estado`, `bi.vw_riesgo_estudiante`, `KPIService` y `risk_service` (por hecho, no por suma entre programas).
- Pagos por mes: cada columna `MONTO <MES> <AÑO>` va al mes del pago como hecho `PAGO_MES`; las 7 columnas PRELIMINAR se excluyen; idempotente por `carga_fila_origen`.
- Avisos agregados: 428 `CUOTAS_NEGATIVAS`, 629 `SOBREPAGO`, 1 `CUOTAS_CON_TEXTO`; valor de cartera desconocido → revisión.
- Migración 022 (dos columnas nuevas y las tres vistas con DA3), idempotente, sin DROP. Validada en la tmpfs (aplicada dos veces).
- Recarga real del libro de cobranza en la tmpfs (renombrado a otro nombre de archivo; el tipo se detectó por contenido como COBRANZA).
- Corregido en la revisión: el test de vistas sembraba `dim_tiempo` con 4 de 13 columnas obligatorias; ahora pasa en Postgres.

No hecho y por qué:
- La migración 022 NO está aplicada en la DW viva ni en el snapshot, ni figura en la lista de arranque de `backend/core/migraciones.py`; la DW viva sigue con la lectura anterior hasta FU-L9 (decisión de aplicarla = Lean/FU-L9).
- Alias de cabecera legacy en `routers/pipeline.py::_ENCABEZADOS_FINANCIEROS` y en el NER de `routers/dataops/extraccion.py`: ya no deciden los hechos de cobranza, pero van contra el principio rector. Deuda para FU-L9.

Invariantes cambiados: no (DA3 es decisión escrita de Lean; 51 tablas + 10 vistas bi sin cambio; cascada y umbrales intactos)

Pruebas: 1.088 colectadas / 1.060 passed / 8 failed / 13 skipped / 7 xfailed · cobertura 74 % (sentencias; backend + pipeline). `tests/fu_l2`: 54 de 54, con los 4 de vistas en Postgres tmpfs.
- 6 fallas de entorno de siempre (4 BETO por falta de `seqeval`; `test_f2_b8_intervalos` y Holt-Winters por `statsmodels`).
- 2 fallas de KPI-06 en SQLite (`tests/sprint5/test_dataops_integridad.py`: `admisiones_conservan_inscritos…` y `cero_inscritos…`): `KPIService` devuelve None. No son de FU-L2: fallan igual en una copia limpia de HEAD (09408aa) con solo `regla_mora.py` añadido. Origen probable: ADW-L5 (df45b59), otra sesión.

Servicios reconstruidos + estado de docker compose ps: `api` y `pipeline` reconstruidos; ambos Up, `db` y `catalog_db` healthy; `/health` 200; sin tracebacks en los logs. Docker Desktop estaba apagado y se arrancó para este cierre.

Cambios de esquema o API: `fact_situacion_financiera` + `estado_cartera_fuente`, `dias_mora` (migración 022, solo tmpfs); tres vistas bi redefinidas con DA3. Sin cambios de endpoint.

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Pagos 2024 / 2025 / 2026 (Bs) fuente = DW tmpfs | 8.071.737,03 / 12.422.501,39 / 4.841.944,46 (diferencia 0) | fu_l2_cobranza_fuente_vs_dw.csv
- Filas con ≥ 2 cuotas por año de inicio, fuente → DW | 369→369 / 809→816 / 643→645 (+7 y +2: 9 de las 10 filas sin fecha de inicio legible, que el hecho ubica por otra fecha) | fu_l2_cobranza_fuente_vs_dw.csv
- Estudiantes distintos con ≥ 2 cuotas | 362→362 / 801→808 / 639→641 | fu_l2_cobranza_fuente_vs_dw.csv
- Cartera CERRADA / VIGENTE / EN MORA / PREVISIONABLE / INCOBRABLE | 9.268→9.265 / 441 / 36 / 69 / 165 (−3 CERRADA; 38 sin estado→4) | fu_l2_cobranza_fuente_vs_dw.csv
- Filas fuente → hechos de situación | 10.017 → 9.980 (−37) | fu_l2_cobranza_fuente_vs_dw.csv
- KPI-05 mora (DW viva → tmpfs) | 2024: 94,28 → 10,60 · 2025: 53,11 → 18,46 · 2026: 75,33 → 37,75 | fu_l2_kpi_antes_despues.csv
- KPI-15 | 2024: 85,56 → 69,61 · 2025: 87,38 → 78,06 · 2026: 99,22 → 23,07 | fu_l2_kpi_antes_despues.csv
- KPI-04 | 2024: 276 → 362 · 2025: 617 → 808 · 2026: 864 → 641 | fu_l2_kpi_antes_despues.csv
- KPI-01 | 2024: 1.927,57 → 2.564,90 · 2025: 3.654,51 → 3.595,51 · 2026: 2.955,67 → 2.325,62 | fu_l2_kpi_antes_despues.csv

Impacto en el documento (sección o tabla): KPI-01, 04, 05 y 15 por gestión; cartera por estado; pagos por año. No se tocan hasta el recongelado de FU-L9 (el documento solo recibe cifras CONGELADAS). La diferencia de KPI-05 (94 % → 10,6 %) es el efecto de DA3 sobre la lectura corregida.

Riesgos abiertos:
- Las diferencias de 37 filas (10.017 → 9.980) y de 34 filas «sin estado» → 4 se explican en el CSV como filas que comparten hecho (mismo estudiante, programa y fecha de inicio) o sin campo de cobranza; no verifiqué fila por fila cuáles son. Revisar en FU-L9.
- 1.518 filas CERRADA con ≥ 2 cuotas (1.517 en la DW) cuentan como mora por DA3: contradicción interna de la fuente, documentada, no corregida.
- Las gestiones 2023 de los KPI de cobranza quedan vacías en la tmpfs porque la cobranza no trae 2023; el valor «antes» de 2023 viene de otras fuentes de la DW viva.
- HEAD estaba roto antes de este commit: `kpi_service.py` (df45b59) importa `regla_mora.py`, que no estaba versionado. Este commit lo incluye.
- Árbol con cambios de otras sesiones sin commitear (puerto 5434 en `database.py`, `conftest.py` y tests `f3v`, `sprint4`, `sprint6`, scripts de figuras): no se incluyen.

Pendiente para el chat 4: ninguno.
