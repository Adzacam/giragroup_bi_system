# CIERRE ADW-L7 — 2026-11-20
Rama / commit: beto-integracion · commit `adw(L7): …` (ver `git log`)
Hecho (máx. 10 líneas):
- **C1 (tareas BETO del lote 1 en ERROR):** no era un fallo del pipeline. Las tareas 44–55 las **crea pytest**: `test_upload_batch_no_evalua_antes_de_responder` usa una base SQLite, pero `tareas_dataops` abre su propia sesión contra la DW. Cada corrida dejaba una INGESTA «COMPLETADA» (1 registro, 0,03 s) y una LECTURA_BETO «EN_CURSO» que sin latido pasa a ERROR a los 180 s. Reproducido en tmpfs (+2 filas por corrida) y corregido parcheando `tareas_dataops` en esa prueba. Tras el arreglo, la suite completa contra la DW viva no añade filas (22 → 22, max id 55). Evidencia: `adw_l7_c1_contaminacion.json`, `adw_l7_c1_repro_lote1.json` (iniciar-lectura sobre el lote 1 real responde 409: está consolidado, no se cuelga).
- **B5 (caché BETO):** premisa incorrecta. `cache_beto_entidades` se crea sola en el primer uso (`DDL_CACHE`) y solo con algún flag encendido (todos apagados por defecto); si falla, ya registra un `warning`. No hay «migración 015» y no conviene crearla: añadiría una tabla a las 51 del invariante. Se corrigió el texto del módulo. En la ruta por defecto la caché que sí se usa es `cache_indice_beto` (180.585 filas).
- **C3 (`carga_fila_origen`):** es el diseño: cada fila de origen registra **2 claves** (posición y contenido), por eso `claves / 2` = filas reclamadas. Con esa lectura 6 de 9 fuentes cuadran exacto con los hechos (razón 2,00). Excepciones reales en `adw_l7_c3_claves.csv`: doc 41 (32.949 filas reclamadas sin hecho), doc 36 cobranzas (4.741), doc 40 (8.853), marketing doc 44 (15.196 reclamadas frente a 13.860 hechos agregados) y rentabilidad/costo del doc 39 (sin hechos). No se purgó nada.
- 5 pruebas nuevas en `tests/adw/test_l7_pipeline.py`: guardia estática (toda prueba que llame a `upload_batch` o la lectura aísla `tareas_dataops`), prueba dinámica en tmpfs (0 tareas nuevas), flags y caché de BETO, segunda lectura desde caché y las dos claves por fila.
No hecho y por qué:
- **C4** (hojas descartadas) y **C5** (10 `CONFLICTO_FUENTES`): el plan FU los reemplaza (FU-L1 y FU-L6); L4-0 ya documentó los conflictos.
- **Purga de claves «huérfanas»:** no hay forma de identificar cuáles claves concretas no tienen hecho (el hecho no guarda la clave), y borrar por conteo sería inseguro. Las filas reclamadas sin hecho se corrigen en la fuente (FU-L1/L2/L5) y con la recarga por documento, que ya borra las claves del documento (`ingestion_service`).
- **Limpieza de las tareas basura de la DW viva:** hecha con autorización escrita de Lean (2026-11-20). `DELETE FROM public.dataops_tarea WHERE id BETWEEN 44 AND 55 AND id_lote = 1 AND tipo IN ('INGESTA','LECTURA_BETO')` borró 12 filas (6 INGESTA y 6 LECTURA_BETO, todas con `total_registros = 1` o ERROR sin procesados). `dataops_tarea` pasó de 22 a 10 filas; quedan las tareas legítimas 1 y 2 del lote 1. Es la única escritura en la DW viva de este loop.
- No se midió el acierto de la caché de entidades: con los flags apagados no se usa.
- Tarea hecha en línea por el chat de desarrollo, no delegada a `dev-alta`.
Invariantes cambiados: no (cascada, umbrales y 51 tablas / 10 vistas / 23 KPI intactos).
Pruebas: 6 failed / 940 passed / 12 skipped / 7 xfailed (965 colectadas) · cobertura 72 %. Los 6 fallos son los mismos de L0 (4 por `torch`/`seqeval` ausentes en el host y 2 de Holt-Winters).
Servicios reconstruidos + estado de docker compose ps: `api` reconstruida; los 9 servicios `Up` (`giragroup_catalog_db` se reinicia al levantar la API).
Cambios de esquema o API: ninguno.
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Filas que dejaba cada corrida de pytest en `dataops_tarea` | 2 (antes) / 0 (después) | adw_l7_c1_contaminacion.json
- Filas reclamadas sin hecho, evaluación doc 41 | 32.949 | adw_l7_c3_claves.csv
- Filas reclamadas sin hecho, cobranzas doc 36 | 4.741 | adw_l7_c3_claves.csv
- Fuentes con razón claves/hechos = 2,00 | 5 de 9 (docs 1, 37, 38, 42, 43) | adw_l7_c3_claves.csv
Impacto en el documento (sección o tabla): ninguno. La corrección de B5/C1 desmiente dos hallazgos de la auditoría: avisar al chat 1 para que los retire del plan.
Riesgos abiertos:
- **Efecto secundario que causé:** mis corridas de pytest en L0 y L1 dejaron 6 filas en `dataops_tarea` de la DW viva (ids 50–55). Ya no se generan más y las 12 filas basura se borraron (ver arriba).
- Filas reclamadas sin hecho = datos que una recarga normal se saltaría (la clave existe, el hecho no): puede haber pérdida silenciosa en doc 41 y doc 36. Lo cubren FU-L1, FU-L2 y FU-L5; verificar antes de la recarga FU-L9.
- `fact_marketing` no guarda `id_documento`, así que su trazabilidad por documento no es verificable.
- RV2 y L1 ya están commiteados; el resto del árbol sigue sin commit.
Pendiente para el chat 4: nada.
