# CIERRE FU-L3 — 2026-11-21
Rama / commit: beto-integracion (ver `git log`, commit `fu(L3)`)

Hecho (máx. 10 líneas):
- Causa raíz del ×2 (corrige al plan, que sospechaba un doble paso por `FactMarketing`): `IngestionService._eliminar_documentos_transaccion` borraba los hechos de 13 tablas por `id_documento`, pero `fact_marketing` no tenía esa columna. Borrar el documento dejaba sus inscripciones y volver a subir el libro las sumaba otra vez. Una recarga limpia con el código anterior da 1 por inscripción (3.551 / 4.562 / 4.736 / 2.288). La «doble clave» de `carga_fila_origen` (30.392 = 2 × 15.196) es por diseño, una clave por archivo y otra por contenido.
- Migración 023: `fact_marketing.id_documento` (FK `ON DELETE CASCADE`, índice) e índice único (módulo, día, COALESCE(documento, 0)). Idempotente, no destructiva; `db/schema.sql` actualizado.
- El loader marca cada inscripción con su documento; borrar un documento retira sus inscripciones y recalcula la captación afectada.
- KPI-06 (DA6): `captacion_canonica.py` lee leads e inscritos por sinónimos del catálogo (YAML + espejo JSON) desde cualquier hoja programa × mes; `captacion_dw.py` deja una cifra por POS y mes (prioridad: detalle mensual visible > oculta rescatada > tabla por programa visible > oculta). La hoja de planificación por POS (2026) ahora trae POS y período (748 filas).
- `routers/cmi.py`: motivo «sin dato» dinámico y `cobertura` (meses con dato de 12) en el KPI-06; el drill-down de CLIENTES agrega `captacion_mensual` y `captacion_cobertura` (claves nuevas).
- Defectos hallados al recargar y corregidos: la lectura BETO borraba el payload de staging (período, hoja, 58 metas); fechas con milisegundos rechazadas; 5 inscripciones con CI incompleta contaban 0; inscripciones asignadas a un módulo leído de otra columna; `db.rollback()` borraba datos no confirmados en SQLite (ahora SAVEPOINT; arregla las 2 fallas de KPI-06 que HEAD ya tenía).

No hecho y por qué:
- La migración 023 NO está aplicada en la DW viva ni figura en `backend/core/migraciones.py` (decisión de Lean). `api` y `pipeline` NO se reconstruyeron: el modelo ya trae `id_documento` y, sin la 023, las cargas de marketing en la DW viva fallarían.
- La DW viva sigue duplicada: la 023 no corrige lo ya cargado; requiere vaciar `fact_marketing` y re-subir (FU-L9).
- El front no dibuja la cobertura mensual ni las series nuevas de CLIENTES (FU-L8).
- Las reservas quedan solo en `fact_planificacion_programa.reservas_fuente`, sin pasar a `fact_marketing.reservas`.

Invariantes cambiados: no (regla de la migración 014, 0 ≤ inscritos ≤ leads, intacta; 51 tablas y 10 vistas bi sin cambio)

Pruebas: 1.149 colectadas / 1.123 passed / 6 failed / 13 skipped / 7 xfailed · cobertura 75 % (sentencias; backend + pipeline). `tests/fu_l3`: 61 pruebas, incluida la migración 023 en PostgreSQL tmpfs.
- Las 6 fallas son de entorno (4 BETO por falta de `seqeval`; `test_f2_b8_intervalos` y Holt-Winters por `statsmodels`). Las 2 de KPI-06 en SQLite quedaron resueltas.

Servicios reconstruidos + estado de docker compose ps: ninguno reconstruido (ver «No hecho»). Los contenedores siguen arriba con el código de FU-L2; `fu_l3_pg_tmpfs` (127.0.0.1:55438) queda levantada con las migraciones 014 y 016–023.

Cambios de esquema o API: migración 023 (solo tmpfs); claves nuevas `cobertura`, `captacion_mensual`, `captacion_cobertura` en el CMI y el drill-down de CLIENTES.

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Inscritos por año fuente = DW tmpfs (diferencia 0) | 2022: 53 · 2023: 3.551 · 2024: 4.563 · 2025: 4.737 · 2026: 2.292 (DW viva antes: 106 / 7.102 / 9.124 / 9.472 / 4.576) | fu_l3_inscritos_conversion.csv
- Captación mensual (leads / inscritos) | Jul-2025 5.104 / 288 · Ene-2026 9.958 / 278 · May-2026 8.090 / 209 · Jun-2026 690 / 17 (12 meses en el CSV; tmpfs = cálculo independiente de la fuente) | fu_l3_inscritos_conversion.csv
- KPI-06 | 2025: 3,85 % (1.351 / 35.085, 6 de 12 meses) · 2026: 2,94 % (1.322 / 44.891, 6 de 12 meses) · 2022–2024: sin dato · la DW viva no tenía valor | fu_l3_kpi_antes_despues.csv
- KPI-21 | no cambia por FU-L3 (no lee `fact_marketing`); la diferencia viva/tmpfs (3.773/3.571 → 3.146/3.455) viene de que la tmpfs parte del snapshot | fu_l3_kpi_antes_despues.csv
- KPI-23 | sin cambios (100,00 / 99,77 / 46,62) | fu_l3_kpi_antes_despues.csv

Diferencias con las referencias del plan (la tmpfs coincide con el cálculo independiente; la referencia del plan no estaba validada): Jul-2025 da 288 inscritos y no 356 (2 filas con inscritos > leads quedan fuera por la regla 014); Mar-2026 da 7.073 leads y no 7.011 (la tabla por programa aporta un POS que el detalle no trae); Jun-2026 da 690 leads y no 3.398 (27 filas con leads sin inscritos, y el KPI exige ambos).

Impacto en el documento (sección o tabla): serie de inscritos por año de Clientes (se reduce a la mitad), KPI-06 por gestión (2025 y 2026 con valor; antes sin dato) y su cobertura. No se tocan hasta el recongelado de FU-L9.

Riesgos abiertos:
- Orden de despliegue: aplicar la 023 en la DW viva ANTES de reconstruir `api` y `pipeline`.
- `dim_modulo` crece de 3.585 a 3.649 (+64) por los POS de planificación e IBP que no existían.
- La recarga de la tabla de inscripciones tarda ~15 min la primera vez (BETO sobre 15.196 líneas); el caché `beto-v2` ya está en la tmpfs.
- Para la hoja de planificación por POS se usó una copia recortada del libro de actas (29 filas) en `/tmp` de `giragroup_api`; no está versionada.
- Deuda del principio rector: `routers/dataops/extraccion.py` (rama MARCA TEMPORAL) y `routers/pipeline.py` siguen con nombres de columna fijos (FU-L9).
- Árbol con cambios de otra sesión sin commitear (`database.py`, `conftest.py`, tests f3v/sprint4/sprint6, scripts de figuras, `scripts/auditoria_dw/_parche_da8.py`, `backend/uploads/`): no se incluyen.

Pendiente para el chat 4: ninguno.
