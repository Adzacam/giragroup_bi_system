# CIERRE FU-L1 — 2026-11-20
Rama / commit: beto-integracion (ver `git log`, commit `fu(L1)`)

Hecho (máx. 10 líneas):
- `pipeline/lector_hojas.py`: metadatos por hoja con openpyxl (estado, combinadas, fórmulas, fórmulas sin valor, forma) y clasificación genérica usada/ignorada con motivo, desde las reglas de `config/mapeo_fuentes.yaml` (espejo `pipeline/mapeo_fuentes.json` para el contenedor).
- `pipeline/ingesta.py`: API nueva `leer_archivo_con_metadatos`; `leer_archivo` queda igual.
- `ingestion_service`: cada hoja ignorada se registra una vez como `HOJA_IGNORADA` (severidad BAJA, estado REGISTRADO; no entra a la bandeja). Corta filas fantasma al final y cabeceras con PII se enmascaran.
- Las hojas válidas que antes caían como `LINEA_SIN_ENTIDAD` pasan por detección de contenido (evaluación por módulo; planificación por POS).
- Test del principio rector: ningún nombre de libro u hoja en `backend/` ni `pipeline/`, con lista blanca comentada.
- Fixtures sintéticas en `tests/fixtures/fuentes_sinteticas/` (otros nombres, columnas reordenadas, ocultas, borradores, subtotales, fantasma, fórmula sin valor).
- Corregido en la revisión: el contrato marcaba MODULOS «ignorar», pero alimenta `bridge_modulo_docente`; queda «usar».

No hecho y por qué:
- No se cambió la selección de hojas del extractor de planificación (lee 7 hojas ocultas que alimentan cifras congeladas). Solo emite un WARN. Ver decisión pendiente.
- `fk_resolver.py` sigue buscando el padrón por una ruta fija de libro; cambiarlo afecta la resolución de identidad. Queda en lista blanca como deuda.
- Sin recarga de la DW (fuera de este loop).

Invariantes cambiados: no

Pruebas: 992 colectadas / 968 passed / 6 failed / 13 skipped / 7 xfailed · cobertura 73 % (sentencias; backend + pipeline).
- Las 6 fallas son las mismas de FU-L0, por entorno: 4 de BETO (falta `seqeval`), 1 de `test_f2_b8_intervalos` y 1 de Holt-Winters (`statsmodels`). `tests/fu_l1`: 29 de 29.

Servicios reconstruidos + estado de docker compose ps: `api` y `pipeline` reconstruidos; ambos Up, `catalog_db` healthy. `/health` y `/docs` responden 200; el lector se importa dentro del contenedor.

Cambios de esquema o API: ninguno. Nuevo tipo de registro `HOJA_IGNORADA` en `log_inconsistencias`.

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Hojas usadas / ignoradas | 29 / 33 (de 62) | fu_l1_hojas_clasificadas.csv
- Filas leídas en hojas usadas | 77.833 | fu_l1_resumen_clasificacion.json
- Filas fantasma cortadas | 3.072 | fu_l1_resumen_clasificacion.json
- Líneas `LINEA_SIN_ENTIDAD` antes → después | 3.689 → 71 | fu_l1_descartes_antes_despues.csv
- Líneas que dejan de cargarse (hojas ocultas duplicadas) | 6.862 | fu_l1_descartes_antes_despues.csv
- Fórmulas sin valor en hojas usadas | 83.908 | fu_l1_hojas_clasificadas.csv

Impacto en el documento (sección o tabla): ninguno todavía. La recarga de FU-L9 cambiará pagos de cobranza y evaluación docente al quitar duplicados de hojas ocultas.

Riesgos abiertos:
- El extractor de planificación sigue leyendo 7 hojas ocultas (6 mensuales jul–dic 2025 con 140 de las 1.663 filas de `fact_planificacion`; `Informe Gestión` con las 58 metas de `dim_meta`, KPI-23). DA6 pide KPI-06 desde jul-2025 y esos datos están solo ahí. **Decisión pendiente de Lean: usarlas o no.**
- IBP entra a `fact_planificacion` como +748 filas sin periodo ni POS; no afecta el KPI-23 (la vista filtra sin periodo). Completar mes, año y POS queda para FU-L3.
- El lote congelado 1387 incluye 110 filas de la hoja oculta `CURSOS DOC 1`; su script la lee por nombre, así que la medición no cambia, pero queda incoherente con lo que el sistema carga.
- Para leer el YAML directo en el contenedor harían falta el volumen `./config` y PyYAML; mientras tanto rige el espejo JSON (un test falla si se desincroniza).

Pendiente para el chat 4: ninguno.
