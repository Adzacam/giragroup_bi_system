# Ronda 5 — `main` (cifras de ejecuciones reales)

## Tabla única de cifras
| Cifra | Antes | Después | Evidencia |
|---|---|---|---|
| Entidades PER descartadas por forma (PER_SIN_FORMA_NOMBRE) | 494 (261 registros) | 48 (48 registros) | corrida_final_ronda4_antes.json, corrida_final_1/2.json |
| Registros sin ninguna persona (van a HITL) | 122 | 26 | idem |
| Lote 1.387 directo / HITL / staging (2 corridas idénticas) | 90,77 % / 9,23 % / 0 % | 97,62 % / 2,38 % / 0 % | idem |
| Entidades PER del lote | 3.006 | 1.658 (1.050 nombres compuestos, 283 etiquetas Likert excluidas) | idem |
| HOMONIMIA nuevas por ciclo mensual | 597 | 0 | ciclo_idempotencia_hitl.json, ciclo_idempotencia_hitl_ronda5.json |
| n (casos nuevos en la bandeja por ciclo) | 1.165 | 617 = 557 staging + 60 casos de evaluación docente + 0 hechos aca/fin + 0 empates | idem |
| Segunda pasada del ciclo | +0 | +0 (staging, hechos, evaluación, estudiantes) | idem |
| Duración del ciclo (pasada 1 / 2) | 159,0 s / 97,6 s | 166,5 s / 111,0 s (una sola corrida) | idem |
| Evaluación docente: filas con docente vinculado | 0 de 11.210 (0 %) | 0 de 11.210 (0,0 %) | evaluacion_docente_vinculacion.json |
| Evaluación docente: filas con id_tiempo | 12.264 de 14.234 (86,16 %) | 12.264 (86,16 %) | idem |
| Evaluación docente en la bandeja | 0 | 11.210 filas = 48 casos (documento, módulo) | idem |
| Recaudación PROGRAMAS 2023 / 2024 / 2025 (Bs) | 8.035.694,25 / 9.989.730,09 / 12.570.961,91 | 8.035.694,25 / 9.989.730,09 / 12.907.977,61 | ols_reajuste.json, ols_hw_proyecciones.json |
| OLS mensual N=40 (2023-01..2026-04) | N=36: pend. 13.911,94, R² 0,5861 | pend. 16.212,88 Bs/mes, R² 0,7128, RMSE 118.783,06 | ols_reajuste.json |
| OLS hold-out últimos 6 meses (2025-11..2026-04) | MAPE 11,51 % (2025-07..12) | MAPE 17,01 %, RMSE 191.568,93 | idem |
| OLS entrenado hasta 2025-12 vs ejecutado ene–abr 2026 | MAPE 16,0 % (con marzo 2025 en 660.209) | MAPE 15,23 % | idem |
| Tablas | 48 | 48 (cat_docente y 6 más ya eliminadas; 17 vacías con motivo) | inventario_tablas_48.csv |
| pytest | 444 passed | 448 passed, 0 failed, 11 skipped, 7 xfailed | pytest_completo_sin_env.txt |

## 1. Nombres partidos (ARCA) y Likert
`componer_nombre_partido` (pipeline/normalization/person_resolver.py) compone NOMBRES + APELLIDO PATERNO + MATERNO de la misma fila antes de resolver; `es_etiqueta_likert` (`^\d+\s*/`) excluye '5/Totalmente de acuerdo' (283 entidades). Resultado en la tabla. Las 48 que siguen descartadas son sobre todo 'PATRICIA'/'PATRICIA DEL' (BD Cobranzas, TBL_INSCRITOS) y respuestas de comentario ('Ninguno', '-'); el CI exacto bajó de 2.378 a 1.021 porque antes cada parte del nombre contaba como una persona.

## 2. Homonimias
Con empate (fk_estado C) el cargador no carga el hecho: `cargar_registro` devuelve `staged` y el hecho no se inserta (FK ni nula ni provisional ni primer candidato: no hay hecho). Se agregó el desempate (`_desempatar_homonimos`: CI parcial, programa, módulo y mes), pero las 597 HOMONIMIA del ciclo no eran homónimos: 595 de 597 eran celdas de planilla ('TOTAL GASTOS: Bs. 2170', 'PROYECTO (POS): 5510', 'Fecha Inicio - Mes: ago') tratadas como nombre de estudiante. Con el filtro `nombre con dígitos o 'clave: valor' no es persona` quedaron 0. El desempate no se ejerció en esta carga (0 casos con candidatos reales empatados); no hay cifra de desempates exitosos.

## 3. Evaluación docente
Las encuestas no nombran al docente: se vincula por bridge_modulo_docente (módulo único o único docente del programa 'POS-xxxx-M%') y el id_tiempo se completa con el último período con actas del programa (a confirmar). Lo no resuelto queda con `requiere_revision` y motivo (DOCENTE_SIN_VINCULAR 9.240; DOCENTE_SIN_VINCULAR + SIN_FECHA 1.970) y entra a la bandeja como un caso por (documento, módulo): 48 casos para 11.210 filas. Vinculadas: 0 %. La causa es de cobertura: bridge_modulo_docente solo tiene docentes de 381 programas de ARCA y solo 1 de los 48 programas evaluados coincide, con varios docentes (523 filas, ambiguo). Nuevas columnas en fact_evaluacion_docente: id_documento, requiere_revision, motivo_revision (migración 012).
KPI que usa fact_evaluacion_docente: el puntaje por docente de `catalog_service` (promedio de `puntuacion` agrupado por `id_docente`); con 0 docentes vinculados ese puntaje es None para todos. `total_evaluaciones_registradas` de kpi_service cuenta fact_rendimiento_academico, no esta tabla.

## 4. Marzo 2025
No es defecto de mapeo: la hoja 'Gestiones' de BD Egresos ('TIPO DE INGRESO: POR PROGRAMAS') es un corte parcial de la misma recaudación (marzo 660.209; abril a diciembre en 0; metas con +100.000 en varios meses). Se aplicó precedencia de fuentes (`_prioridad_fuente`: EJECUTADO VS META = 2, el resto = 1; fact_rentabilidad guarda `id_documento` de la cifra vigente) y una fuente menor ya no reemplaza a la mayor (queda CONFLICTO_FUENTES 'se conserva'). Se reprocesó EJECUTADO VS META en el DW real (marzo 2025 = 997.224,70) y luego BD Egresos para comprobarlo (no pisó). Recaudación anual final: 8.035.694,25 / 9.989.730,09 / 12.907.977,61 Bs; coincide con recaudacion.csv y con la tesis (8,03 / 9,98 / 12,90 M truncados).

## 5. OLS reajustado (`ols_reajuste.json`)
N=40 (2023-01..2026-04; mayo parcial excluido). Proyección 2026-06..11 con IC 95 % de predicción: 1.248.342 [988.215; 1.508.470]; 07 1.264.555 [1.003.463; 1.525.647]; 08 1.280.768 [1.018.672; 1.542.864]; 09 1.296.981 [1.033.842; 1.560.120]; 10 1.313.194 [1.048.972; 1.577.416]; 11 1.329.407 [1.064.063; 1.594.750].

## 6. Esquema
Bloque DROP movido a la migración 011 (`011_eliminar_tablas_sin_uso.sql`) y la 012 (`012_evaluacion_revision_y_fuente_rentabilidad.sql`); ambas en `MIGRACIONES_EN_ARRANQUE`. `db/schema.sql` ya no define cat_docente ni dim_docente.id_cat_docente y agrega las columnas nuevas. Tests con cambio de requisito por diseño: `test_migraciones_arranque` (lista de arranque con 011 y 012) y `test_esquema_alineado_ddl` (cat_docente ya no está en el DDL); sin otras aserciones tocadas.

## 7. Inventario (`inventario_tablas_48.csv`)
48 tablas: tabla, capa, filas, PK, descripción, archivo que la alimenta y motivo de las 17 vacías (copias de catálogos servidas desde giragroup_catalog_db, dim_meta y fact_cobranzas_proyectadas sin escritor). Metas del CMI: no salen de dim_meta ni de ref_metas_gestion sino de `bi.ref_kpi` (22 indicadores con meta y umbrales, esquema `bi`, migración 006), `bi.ref_perspectiva` y `fact_rentabilidad.monto_meta` (vista `bi.vw_metas_mensual`). El esquema `bi` tiene 2 tablas y 9 vistas fuera de las 48 de `public`.

## 8. n por ciclo y retención de hechos
Segunda pasada: +0 en todo. n = 617 (557 staging nuevo único: 300 BAJA_CONFIANZA_IA + 257 CI_NOMBRE_DISCORDANTE; 60 casos de evaluación docente por 7.322 respuestas; 0 empates; 0 hechos académicos/financieros en revisión). T = 2,6–2,8 min + 617 × (tiempo humano por caso).
Retención: los 557 casos de staging retienen su línea (no se carga hecho hasta resolverlos). Los hechos con `requiere_revision` (3.678 académicos + 16 financieros + 18.532 respuestas de evaluación en el clon) sí están cargados y los KPIs de `kpi_service` no filtran por esa marca, así que no quedan "no disponibles"; solo el puntaje por docente queda en None porque no hay docente vinculado.
