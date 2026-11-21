# CIERRE FU-L5 — 2026-11-21
Rama / commit: beto-integracion (ver `git log`, commit `fu(L5)`)

Hecho (máx. 10 líneas):
- `encuesta_canonica.py`: lector canónico de encuestas por contenido y por sinónimos del catálogo (`vocabularios.etiquetas` en el YAML, 7 familias: acuerdo, satisfacción, probabilidad, utilidad, facilidad, adecuación y «Neutral» como comodín). Una hoja es encuesta si ≥ 3 columnas traen etiquetas del diccionario en ≥ 50 % de sus celdas; un libro es EVALUACION_DOCENTE si esas hojas son ≥ 50 % de sus filas. El libro de Experiencia Docente 2.0 ya no sale como ACTA/CENTESIMAL_100.
- Pares texto + número: se lee solo la columna numérica (se evita la doble columna: 198.801 + 11.592 celdas en el libro C). «Promedio» no es respuesta.
- DA1: 0 y «Sin Información» → NULL; fuera de [1, escala_max] → NULL; escala 5 o 10 por pregunta (cabecera, luego números sueltos); el NPS (0–10) queda aparte y el 0 vale. Preguntas «recomiende/recomienda» pasan a NPS (antes contaban en KPI-19).
- Hoja por módulo del libro B (doc 41), antes descartada: se carga completa. Causa: el libro comparte cabeceras con Moodle y `adaptar_moodle_df` tomaba la fila de grupos como cabecera; una hoja que por contenido es encuesta ya no pasa por ese adaptador.
- Avisos agregados por documento, hoja y pregunta, sin PII: `SIN_INFORMACION` (informativo), `PUNTUACION_FUERA_DE_ESCALA`, `RESPUESTA_EN_COLUMNA_EQUIVOCADA`, `VALOR_FUERA_DE_CATALOGO`, `ESCALA_NO_INFERIBLE` (pendientes). Ejemplos solo del diccionario o «<texto de N caracteres>».
- Migración 025: redefine `bi.vw_cmi_valores` desde la 024; KPI-19 y KPI-20 solo cuentan `1 ≤ puntuacion ≤ escala_max` con `escala_max > 0`; NPS fuera. Sin cambios de esquema; idempotente.
- `catalog_service`: el promedio por docente solo cuenta [1, escala_max].
- Recarga completa de los 3 libros en tmpfs (`fu_l5_pg_tmpfs`) y comparación fuente–DW sin PII.

No hecho y por qué:
- La 025 NO está aplicada en la DW viva ni figura en `backend/core/migraciones.py`; `api` y `pipeline` no se reconstruyeron (decisión de Lean: esperar FU-L9). Orden al aplicar: 022, 023, 024, 025.
- La DW viva conserva los datos viejos (715.217 hechos con doble columna, ceros y duplicados). La vista 025 descarta los 0 pero no quita duplicados: requiere vaciar `fact_evaluacion_docente` y re-subir (FU-L9).
- La bandeja de revisión y el front no muestran aún los motivos nuevos legibles (FU-L7 y FU-L8).

Invariantes cambiados: no (cascada, umbrales, `fk_resolver` y `migraciones.py` intactos; 51 tablas y 10 vistas bi sin cambio)

Pruebas: 1.273 colectadas / 1.233 passed / 6 failed / 27 skipped / 7 xfailed · cobertura 76 % (sentencias; backend + pipeline). `tests/fu_l5`: 53 de 53 (4 de la migración 025 en PostgreSQL tmpfs, con transacción que siempre se revierte).
- Las 6 fallas son de entorno: 4 BETO (falta `seqeval`), `test_f2_b8_intervalos` y Holt-Winters (`statsmodels`).

Servicios reconstruidos + estado de docker compose ps: ninguno (ver «No hecho»). Los contenedores siguen con el código de FU-L2. `fu_l5_pg_tmpfs` (127.0.0.1:55440) queda levantada con `giragroup_db` (snapshot + migraciones 014, 016–025 + los 3 libros) y `catalogo_copia`.

Cambios de esquema o API: migración 025 (solo tmpfs; vista); motivos nuevos de revisión de encuestas.

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Respuestas válidas fuente = DW tmpfs (diferencia 0 en 7 hojas / 3 libros) | 357.782 (A 160.359 · B 64.923 · C 132.500) | fu_l5_encuestas_fuente_vs_dw.csv
- Hechos de evaluación en la DW tmpfs; puntuaciones fuera de [1, escala_max] y puntuaciones = 0 | 409.859; 0 y 0 | fu_l5_encuestas_fuente_vs_dw.csv
- Hoja por módulo del libro B, válidas fuente = DW | 52.975 = 52.975 | fu_l5_encuestas_fuente_vs_dw.csv
- Avisos: SIN_INFORMACION / FUERA_DE_ESCALA / RESPUESTA_EN_COLUMNA_EQUIVOCADA / FUERA_DE_CATALOGO | 77.902 · 625 · 10.751 · 1.255 celdas | fu_l5_encuestas_fuente_vs_dw.csv
- KPI-19 (DW viva → tmpfs) | 2024: 58,61 → 82,26 · 2025: 66,77 → 82,06 · 2026: 82,35 → 84,01 | fu_l5_kpi_antes_despues.csv
- KPI-20 | 2024: 22,00 → 81,65 · 2025: 12,58 → 78,21 · 2026: 70,99 → 80,20 | fu_l5_kpi_antes_despues.csv
- Cálculo independiente sobre la fuente (KPI-19 / KPI-20) | 2024: 79,96 / 79,78 · 2025: 82,01 / 77,72 · 2026: 84,01 / 80,20 | fu_l5_kpi_antes_despues.csv

Impacto en el documento (sección o tabla): KPI-19 y KPI-20 por gestión; conteo de respuestas de evaluación docente; descripción de la escala y del tratamiento del 0 / «Sin Información» (DA1). No se tocan hasta el recongelado de FU-L9.

Riesgos abiertos:
- 2024 sale ~2,3 (KPI-19) y ~1,9 (KPI-20) puntos por encima del cálculo independiente: la DW asigna a las 11.171 respuestas sin fecha (sobre todo la hoja de cursos del libro C) el último período del programa; la fuente independiente las deja sin gestión. Decidir en FU-L9 si esas filas entran a un KPI por gestión. 77 hechos con `id_tiempo` NULL no entran a ningún KPI.
- 2026 no coincide con la estimación de DA1 (82,35 → 82,35) porque ahora entra la hoja por módulo del libro B (78.875 respuestas) que antes no estaba. 2025 queda a menos de 0,2 puntos de DA1; 2026 a 1,7 (KPI-19) y 0,9 (KPI-20); 2024 a 2,3 y 1,9 (82,26 / 81,65 contra 79,99 / 79,71).
- Las preguntas de recomendación salen de KPI-19 y KPI-20: n más bajo y no estrictamente comparable con DA1 en ese punto. Revisar con Lean si el NPS debe reportarse como KPI propio.
- 1.255 celdas de comentarios de una o dos palabras («excelente», «todo bien») en columnas puntuadas quedan como `VALOR_FUERA_DE_CATALOGO`; FU-L7 decide si se agrupan.
- Los 0 y «Sin Información» de las columnas de texto de los pares (94.578 celdas, libro C) son «sin comentario»; los avisos cuentan 77.893 preguntas puntuadas, una vez por par.
- El «antes» de la DW viva (n = 428.811 en 2025) incluye 0 que la vista anterior promediaba, doble columna y duplicados; no es una comparación de filas equivalentes.
- Deuda del principio rector: listas fijas de cabeceras en `extraccion_por_encabezado.py` y `routers/pipeline.py` (FU-L9).
- Árbol con cambios de otra sesión sin commitear (`database.py`, `conftest.py`, tests f3v/sprint4/sprint6, scripts de figuras, `docs/encuestas/`, `backend/uploads/`, PNG de evidencias): no se incluyen.

Pendiente para el chat 4: ninguno.
