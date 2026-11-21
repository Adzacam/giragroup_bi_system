# CIERRE FU-L0 — 2026-11-20
Rama / commit: beto-integracion c854da5

Hecho (máx. 10 líneas):
- `scripts/auditoria_fuentes/perfil_fuentes.py`: perfil genérico (`--entrada`, `--salida`), sin nombres de libro ni de hoja, sin PII. Salidas `docs/mediciones/fu_l0_perfil.json` y `fu_l0_hojas.csv`.
- `config/mapeo_fuentes.yaml`: catálogo editable de 8 tipos de fuente, 18 campos canónicos, sinónimos con prioridad, reglas de hoja por estado y forma, y prioridad de fuentes DA-FU3.
- `docs/fuentes/CONTRATO_FUENTES.md`: contrato por tipo de fuente y tabla con una decisión (usar o ignorar, con motivo) para las 62 hojas.
- `tests/transversales/test_fu_l0_perfil.py`: 8 pruebas con libros sintéticos.
- Corregido en la revisión: el perfil publicaba el contenido de la hoja oculta de una sola fila `BAJAS POR DUPLICADOS` (nombre, domicilio, fecha de nacimiento). Ahora solo publica el ancho; hay prueba de regresión.

No hecho y por qué:
- No se tocó backend ni pipeline (fuera de FU-L0). El catálogo YAML aún no lo lee ningún código; eso es FU-L1 a FU-L5.
- No se cargó `cat_mapeo_columna` en `catalog_db`; se eligió el YAML versionado.

Invariantes cambiados: no

Pruebas: 954 colectadas · 935 passed · 6 failed · 12 skipped · 7 xfailed · cobertura 73 % (sentencias; backend + pipeline).
- Las 6 fallas no vienen de FU-L0: falta `seqeval` (4 pruebas BETO) y `statsmodels` no resuelve el método de intervalos (2 pruebas de Holt-Winters).

Servicios reconstruidos + estado de docker compose ps: no aplica (solo scripts, config, docs y tests; no se tocó backend, pipeline ni frontend).

Cambios de esquema o API: ninguno.

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Libros | 10 | fu_l0_perfil.json
- Hojas | 62 (39 visibles, 23 ocultas, 0 muy ocultas) | fu_l0_hojas.csv
- Decisión del contrato | 28 usar, 34 ignorar | docs/fuentes/CONTRATO_FUENTES.md

Impacto en el documento (sección o tabla): ninguno todavía. Para el chat 3: el recuento de hojas de `uploads/data` es 62, no 61.

Diferencias con la PARTE 1 del plan (según el perfil):
- Hay 62 hojas; la nueva es «Análisis de Evaluación» (ANTIGUO, resumen de fórmulas, se ignora).
- Planificación: 19 hojas ocultas, no 13.
- TBL EVALUACION DOCENTE: 794 filas duplicadas, no 748.
- Hoja 12 de Cobranzas: 10 filas de datos, no 18.
- ACTAS: Deserción 488 + 1, no 489.
- Coinciden: cartera 9.268 / 441 / 36 / 69 / 165, fórmulas, filas de IBP, inscritos, DIPLOMADOS DOCENTE y meta 2024 en una celda.

Riesgos abiertos:
- La cabecera de «Enero-2026» (Planificación) contiene un correo personal; el perfil la enmascara, pero FU-L1 y FU-L8 deben tratarla.
- Se perfiló MODULOS (catálogo de docentes con contacto) como «ignorar»; hay que confirmarlo si algún KPI la necesita.
- Árbol de trabajo con unos 150 cambios ajenos sin commitear; este commit incluye solo los archivos de FU-L0.
- Fallas de entorno del suite (`seqeval`, `statsmodels`) por resolver antes del recongelado FU-L9.

Pendiente para el chat 4: ninguno.
