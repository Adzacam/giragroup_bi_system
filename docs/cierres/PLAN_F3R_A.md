# PLAN F3R-A — 2026-11-16
Objetivo de la fase: revisar archivo por archivo cuántas filas de los 10 archivos del corpus llegan a la DW de f3_base y explicar cada diferencia antes de reescribir la SFV.
Entrada: PLAN_F3R.md en ejecución (R3-12 queda **bloqueada** hasta cerrar este plan); evidencia: `f3_base.json`, `f3r_extraccion_f3base.json`, `f3r_inventario_corpus.json`, `f3r_matricula_lote.json`; rama base = `beto-integracion` 2f68d0c.
Base de trabajo: copia tmpfs `f3r_base`, reconstruida en R3-1 (huella v2 `b5f1d7b1…af24f`). **Solo lectura**: no se toca código, ni la DW viva, ni el snapshot.

## CORRECCIÓN tras A-0 (16-nov, `f3r_diag_inscritos.json`) — manda sobre la sección siguiente
- **f3_base no se cargó con los libros completos.** Se cargó con los **recortes del ciclo mensual 2026-03** que están en `output/backups/f0_lote/slices/` (los 10 archivos; `medir_flujo_dataops.py` con `CICLO_REUSAR_SLICES=1`). Es el ciclo mensual que mide RNF-03. Por eso un solo mes de inscritos es lo esperado (391 filas → 299 hechos por módulo y día, que suman 391), y **no es un defecto**.
- Consecuencia: la tabla de abajo, que compara contra el inventario de los libros completos (90.538 filas), **no sirve como referencia**. El origen de cada cuadre pasa a ser:
  - (a) **el recorte** para f3_base;
  - (b) **el libro completo** para el `snapshot_dw_20261110_1201`, que es la fuente de las series de negocio (HW de matrícula, n = 43).
- **Hallazgo nuevo (A-9):** `dw_vacio`, la plantilla de la que se clonan las bases de medición, ya trae **15.196 filas en `carga_fila_origen`** (`id_documento = 12`, `tabla = fact_marketing`, `nombre_archivo` nulo). Esas filas ya estaban antes de cada medición. Como la idempotencia depende de `carga_fila_origen`, una carga del libro completo de inscritos sobre esa plantilla podría marcar esas filas como «ya cargadas» y no insertarlas.
- Las tareas se reorientan así:
  - A-0: **cerrada**.
  - A-1 a A-5 y A-7: se cuadran contra **los recortes** (y también los libros completos contra el snapshot, en solo lectura de la copia del dump `14D45F5A…`).
  - A-8 (metas): se cuadra el recorte de EJECUTADO VS META contra `fact_rentabilidad` de f3_base (91), y el libro completo (95 registros esperados contándolos a mano) contra el snapshot.
  - A-9: nueva tarea.

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| A-9 | `dw_vacio` no está vacía: listar todas las tablas con filas y cuántas tiene cada una; averiguar de dónde salen las 15.196 filas de `carga_fila_origen` (qué script o migración y cuándo); probar en una copia tmpfs desechable si cargar el libro completo de inscritos sobre `dw_vacio` deja filas sin insertar marcadas como «ya cargada», y cuántas; decir si alguna medición congelada (f3_base, lote 1.387, B-7) heredó esas filas y si eso afecta su huella | dev-media | — | A-1 | 1) inventario de las tablas no vacías de `dw_vacio` (N tablas, M filas); 2) origen de las 15.196 con commit o script; 3) número de filas bloqueadas por la idempotencia = N (0 si no pasa); 4) veredicto `regla_correcta` o `defecto` | `f3r_dw_vacio.json` |

## Por qué hace falta este plan (versión anterior; ver la corrección de arriba)
`f3_base` lee 11.956 registros y deja 15.978 filas en `carga_fila_origen`, mientras el inventario cuenta **90.538 filas procesables** en los mismos archivos. Con inscritos ya se vio que falta casi todo. En el resto del corpus hay más diferencias que nadie ha explicado:

| Archivo (uploads/data) | Hoja principal (inventario) | Filas origen | Destino esperado | Filas en f3_base | Señal |
|---|---|---|---|---|---|
| TBL_INSCRITOS.xlsx | TBL_INSCRITOS | 15.196 (2022–2026) | fact_marketing | 299 filas / 391 inscritos, solo 2026-03 | se diagnostica en A-0 |
| BD Cobranzas.xlsx | COBRANZAS 2024 2025 | 10.017 (+ copia 5.455, Hoja 4 467) | fact_situacion_financiera | 725 | 5.455 descartadas como ruido, igual a la «Copia»; `fact_cobranzas_proyectadas` = 0 |
| Base centralizada Académica ARCA (1).xlsx | ACTAS DE NOTAS | 8.660 | fact_rendimiento_academico | 1.392 | 1.901 `FILA_ACADEMICA_SIN_ESTUDIANTE` |
| BD Techos.xlsx | BD Techos | 207 | fact_techo_convenio | 1 | casi todo perdido |
| BD Egresos.xlsx | egresos | 1.373 | fact_costo_programa (?) | 1.371 | confirmar el destino |
| EJECUTADO VS META.xlsx | EJECUTADO / GESTIONES | 24 / 12 | fact_rentabilidad, dim_meta | 91 / dim_meta 0 | confirmar el despliegue por mes; dim_meta vacía |
| PLANIFICACION Y EJECUCION ACADÉMICA (…).xlsx | 40+ hojas mensuales, Programas Notificados 1.041, Detalle Presupuestado 299 | dim_modulo, fact_marketing (?) | — | 2.063 `FILA_AGREGADA_SIN_CATEGORIA_MES`; posible origen de las 299 filas de fact_marketing |
| Evaluación Docente y Unifranz.xlsx | DIP. EXP DOC. X MODULO 3.251 (+286, 276) | fact_evaluacion_docente | 75.073 entre los tres archivos de evaluación | 1.076 `FILA_EVALUACION_SIN_RESPUESTAS` |
| Experiencia Docente 2.0.xlsx | DIPLOMADOS DOCENTE 14.397 (+733, 828, 671) | fact_evaluacion_docente | (incluido arriba) | |
| [BBDD] ANTIGUO RESPUESTAS … .xlsx | TBL EVALUACION DOCENTE 16.451 (+2.539) | fact_evaluacion_docente | (incluido arriba) | |

### Hallazgos ya verificados en el código y en los Excel (lectura, 16-nov)
1. **Una sola categoría por libro.** `ingestion_service.py:826-838` clasifica el archivo completo con `detectar_tipo_fuente_por_cabeceras` y aplica esa categoría a todas sus hojas; la única excepción son las encuestas Likert, que pasan a evaluación. En los libros con varias hojas, cada hoja hereda la categoría del libro aunque su contenido sea otro:
   - BD Cobranzas: 5 hojas, entre ellas «Hoja 4» (467 filas) y la «Copia» (5.455).
   - ARCA: 5 hojas (MODULOS, IBP, CRITERIOS, PROGRMAS DE BAJA).
   - PLANIFICACION: más de 40 hojas, entre ellas «Julio-2025 borrador» y «Septiembre-2025boor», borradores que duplican «Julio-2025» y «Septiembre-2025»; «Julio» a «Diciembre» sin año; «Detalle Presupuestado»; dashboards.
   - BD Egresos: 3 hojas (egresos, Gestiones, acumulados).
   - Los 3 archivos de evaluación: incluyen la hoja «Análisis de Evaluación».
2. **Metas (EJECUTADO VS META).** La regla `registros_rentabilidad` (`extraccion_por_encabezado.py:396`) toma la hoja EJECUTADO en formato ancho: `EJECUTADO AAAA` y `META POR CATEGORIA AAAA`, y `META AAAA` solo si la otra está vacía. Ignora a propósito la hoja GESTIONES (totales) y la columna `EJEC. 2025`, que es PROGRAMAS + TECHOS (1.045.178,9 + 78.117 = 1.123.295,9, igual que GESTIONES). Esto es correcto. Quedan tres puntos abiertos:
   - a) Contando a mano salen **95** registros (2023: 24 · 2024: 24 · 2025: 24 · 2026: 12 PROGRAMAS + 11 TECHOS), pero `fact_rentabilidad` tiene **91**. Faltan 4.
   - b) La columna `META POR CATEGORIA 2024` está vacía salvo una celda, TECHOS/CERRADOS-diciembre = **10.719.694**. Parece un total anual escrito en una celda mensual, y entraría como meta de diciembre de 2024.
   - c) Ninguna fila de EBITDA (META/EJECUTADO 2024-2025), «PROYECCIÓN MAESTRIAS» ni «META 2025 2DO SEMESTRE» entra a la DW. Hay que confirmar si ningún KPI las necesita.
   - Además, `dim_meta` = 0.

Además: `dim_tiempo` va de 2005-02-05 a 2034-01-12, fuera de lo que traen los archivos (2022–2027), y en el inventario hay dos archivos con otro nombre («…Posgrado…» frente a «…Unifranz…»; los tamaños coinciden).

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| A-0 | Diagnóstico de inscritos (ya pedido): categoría del documento, de qué documento salen las 299 filas de fact_marketing, filas de TBL_INSCRITOS en carga_fila_origen, staging y log por motivo, y 5 ejemplos MARCA TEMPORAL → fecha asignada | dev-media | — | A-1 | 1) las 15.196 filas tienen destino o motivo (diferencia sin explicar = 0, o cuantificada con su causa); 2) causa raíz señalada con archivo:línea | `f3r_diag_inscritos.json` |
| A-1 | Script de solo lectura `scripts/f3r_cobertura_por_archivo.py`. Por cada `dim_origen_documental`: filas origen por hoja y gestión (leídas con pandas desde `uploads/data/`, sin escribir), staging_registros_crudos, carga_fila_origen agrupado por `tabla`, filas por hecho (via id_documento cuando la tabla lo tiene), stg_entidad_no_resuelta y log_inconsistencias por motivo, descartados_ruido, min/max de fecha por hecho. También confirma con sha256 que los archivos del inventario son los de `uploads/data/` | dev-baja | — | A-0 | 1) 10 archivos × todas sus hojas en el JSON; 2) por archivo, `origen = cargadas + staging + log + ruido + sin_explicar`, con `sin_explicar` calculado; 3) se corre dos veces y da el mismo resultado (md5) | `f3r_cobertura_por_archivo.json`, `.csv` |
| A-2 | Causas en los archivos financieros (Cobranzas, Techos, Egresos, EJECUTADO VS META): por qué 10.017 → 725, 207 → 1, dim_meta = 0, fact_cobranzas_proyectadas = 0; si la «Copia de COBRANZAS» debe descartarse; muestra de 10 filas perdidas por hoja con la regla que las saca (archivo:línea) | dev-media | A-1 | A-3, A-4 | 1) cada `sin_explicar` > 0 de estos 4 archivos queda con una causa y ejemplos; 2) cada causa se clasifica como `regla_correcta` (deliberada y documentada) o `defecto` | `f3r_cobertura_financiero.json` |
| A-3 | Causas en los académicos (ARCA, PLANIFICACION): 8.660 → 1.392 actas; las 1.901 sin estudiante; qué hojas de PLANIFICACION se leen y cuáles no; si las 299 filas de fact_marketing salen de «Detalle Presupuestado» | dev-media | A-1 | A-2, A-4 | igual que A-2 | `f3r_cobertura_academico.json` |
| A-4 | Causas en los tres de evaluación: filas origen frente a hechos (75.073 hechos = filas × preguntas), qué hojas entran, 1.076 sin respuestas | dev-media | A-1 | A-2, A-3 | igual que A-2; además, el factor hechos/fila por hoja | `f3r_cobertura_evaluacion.json` |
| A-5 | dim_tiempo 2005–2034: qué documentos, filas y columnas generan las fechas fuera de 2022–2027 | dev-baja | A-1 | A-2..A-4 | 1) cada fecha fuera de rango con documento, hoja y celda de origen; 2) número de hechos afectados por tabla | `f3r_dim_tiempo_fuera_rango.json` |
| A-7 | **Revisión por hoja**: para cada una de las ~75 hojas del inventario, registrar la categoría que recibió (staging), las filas de origen, las filas cargadas por tabla y el motivo de las no cargadas; decir si la categoría corresponde al contenido; detectar hojas duplicadas o borradores (PLANIFICACION «…borrador»/«…boor», «Copia de COBRANZAS») y si se cuentan dos veces | dev-media | A-1 | A-2..A-5 | 1) 100 % de las hojas del inventario en la tabla; 2) cada hoja marcada como `categoria_ok` sí/no y `duplicada` sí/no, con evidencia; 3) filas cargadas dos veces por borradores = N, con ejemplos | `f3r_cobertura_por_hoja.json` |
| A-8 | **Metas**: cuadrar celda por celda la hoja EJECUTADO contra `fact_rentabilidad` (categoría × mes × año, ejecutado y meta). Explicar los 4 registros que faltan (95 esperados frente a 91), la celda de 10.719.694 en META 2024 TECHOS-dic, por qué `dim_meta` = 0 y qué KPI y pronóstico (META_MENSUAL_PROGRAMAS) consumen esos montos | dev-media | A-1 | A-2..A-5, A-7 | 1) 0 celdas con monto distinto (tolerancia 1 Bs) o cada diferencia listada; 2) los 4 faltantes identificados con la regla que los saca; 3) la celda de 10,7 M marcada como `regla_correcta` o `defecto`, con el KPI afectado | `f3r_cobertura_metas.json` |
| A-6 | Consolidar: tabla única con el estado de los 10 archivos y lista de defectos, cada uno con impacto (qué KPI, sección de la SFV y figura afecta) | dev-baja | A-0..A-5, A-7, A-8 | — | 1) 10 filas, ninguna con `sin_explicar` sin clasificar; 2) cada defecto enlaza a su evidencia; 3) **0 cambios de código** (`git diff --stat backend/ pipeline/ frontend/` igual que antes de empezar) | `f3r_cobertura_resumen.md` |

## Comandos exactos por tarea
- Base: `TMPFS_PORT=55632 scripts/aislada_tmpfs.sh up` y restaurar `f3r_base` como en R3-1. Antes y después, comprobar la huella v2 (`b5f1d7b1…af24f`); si cambia, se detiene todo.
- Consultas: solo `SELECT`, con `PYTHONIOENCODING=utf-8` y el mismo cliente psql_tmpfs de R3-1. Ningún `INSERT/UPDATE/DELETE`.
- Origen: `pandas.read_excel(..., sheet_name=None)` sobre `uploads/data/`, en lectura. El sha256 del lote (`aafde8ad…db60`) se verifica antes y después.
- Al terminar: `TMPFS_PORT=55632 scripts/aislada_tmpfs.sh down`.

## Riesgos y control
- **Corregir sobre la marcha**: está prohibido en este plan. Cualquier corrección cambia la huella, f3_base, el lote 1.387, B-7 y la SFV. Solo se registra como defecto.
- **Contar mal las filas de origen**: los encabezados, subtotales y filas vacías no son filas procesables. A-1 usa el mismo criterio que `f3r_inventario_corpus.json` y lo deja escrito en el JSON.
- **Hechos agregados** (marketing suma inscritos por módulo y mes; evaluación despliega preguntas): el cuadre se hace por fila de origen (`carga_fila_origen`), no por cantidad de hechos.
- **Tiempo de RNF-03**: si se corrigen defectos, el proceso carga más filas y el tiempo de 856 s puede subir. Hay que volver a medir B-7.

## DECISIONES PENDIENTES PARA LEAN (no se ejecutan hasta que responda)
1. **Por cada defecto de A-6**: ¿se corrige? Si sí, se abre `PLAN_F3S`: corrección con pruebas, nueva f3_base, nueva huella, se repiten el lote 1.387, B-7 y el KLM, y después R3-12. Si no, la SFV lo declara como limitación, con cifras.
2. **R3-12** (reescritura de la SFV) sigue bloqueada hasta que respondas la decisión 1. La Opción 1 del pronóstico de matrícula (snapshot, n = 43) sigue siendo válida como base mixta declarada, pero su nota debe dar la causa real que salga de A-0.

## Al cerrar
pytest sin cambios (no se tocó código) · sin rebuild · commit solo de `scripts/f3r_cobertura_por_archivo.py` y de los archivos `docs/mediciones/f3r_*` de este plan (`git add` con rutas explícitas), mensaje `docs(f3r-a): cobertura por archivo de f3_base` · `docs/cierres/CIERRE_F3R_A.md` con la tabla de A-6 y las decisiones abiertas.

## PROMPT PARA CHAT 2
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F3R_A.md antes de seguir con R3-12 de PLAN_F3R.md (R3-12 queda en pausa).
Todo es de solo lectura sobre la copia tmpfs `f3r_base` (huella v2 b5f1d7b1… antes y después) y sobre `uploads/data/` (sha del lote aafde8ad… antes y después). No modifiques backend/, pipeline/ ni frontend/: los defectos se registran, no se corrigen.
A-0 está cerrada (f3r_diag_inscritos.json): f3_base corresponde a los recortes del ciclo mensual 2026-03, así que lee primero la sección «CORRECCIÓN tras A-0». Los cuadres de f3_base se hacen contra `output/backups/f0_lote/slices/`, y los de los libros completos contra la copia del snapshot. A-9 (dw_vacio con 15.196 filas en carga_fila_origen) y A-1 en paralelo; luego A-2, A-3, A-4, A-5, A-7 (revisión por hoja: categoría heredada del libro, borradores duplicados) y A-8 (metas celda por celda: 95 frente a 91, la celda 10.719.694 de META 2024, dim_meta = 0) en paralelo (dev-media / dev-baja según la tabla); al final A-6.
Criterio central: por cada uno de los 10 archivos, origen = cargadas + staging + log + ruido + sin_explicar, y todo lo que sea sin_explicar queda clasificado como regla_correcta o defecto, con archivo:línea y 10 filas de ejemplo.
Commit solo de los archivos de este plan y CIERRE_F3R_A.md. Después espera mi decisión sobre cada defecto.
