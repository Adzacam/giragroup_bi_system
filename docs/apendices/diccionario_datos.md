# Diccionario de datos

Apéndice F: 27 tablas, 251 columnas. Apéndice G: 16 tablas, 77 columnas.

Convenciones: Nulo = SÍ si la columna admite NULL. FK → tabla(columna) con su acción ON DELETE. Los tipos se escriben como en PostgreSQL; SERIAL indica INTEGER con secuencia propia.

## Apéndice F: Almacén de datos (giragroup_db, esquema constelación)

Fuente: DDL de `db/schema.sql`, que incluye los índices de las migraciones `db/migrations/001` y `V005`–`V010`. La base `giragroup_db` en ejecución se alineó con ese DDL mediante `backend/scripts/migrations/005_alinear_esquema_con_ddl.sql` y se contrastó objeto por objeto (columnas, tipos, nulos, DEFAULT, PK, UNIQUE, FK con ON DELETE, CHECK, índices, RLS y políticas): 0 diferencias en las 27 tablas. Filas: conteo en `giragroup_db` en ejecución al 01-11-2026.

**Tabla F.1 Catálogo de tablas**

| N.º | Tabla | Tipo | Granularidad o propósito | N.º de columnas | Filas |
|---|---|---|---|---|---|
| 1 | fact_rendimiento_academico | Hecho | Un registro por estudiante y módulo cursado (nota, asistencia y alerta académica) | 16 | 4567 |
| 2 | fact_situacion_financiera | Hecho | Un registro por estudiante, módulo y fecha de corte de cartera (deuda, pagos y alerta de mora) | 16 | 234 |
| 3 | fact_cobranzas_proyectadas | Hecho | Un registro por estudiante y fecha de cobro proyectado | 6 | 0 |
| 4 | fact_evaluacion_docente | Hecho | Un registro por respuesta de evaluación de un docente en un módulo | 8 | 0 |
| 5 | fact_marketing | Hecho | Un registro por programa/módulo y mes (embudo leads → reservas → inscritos) | 7 | 0 |
| 6 | fact_rentabilidad | Hecho | Un registro por categoría financiera y mes (monto ejecutado frente a meta) | 6 | 95 |
| 7 | fact_forecast | Hecho | Un registro por serie pronosticada (caso de uso) y mes proyectado | 9 | 0 |
| 8 | dim_tiempo | Dimensión | Calendario con grano diario (clave AAAAMMDD) | 13 | 2230 |
| 9 | dim_estudiante | Dimensión | Un registro por estudiante identificado (con CI o identificador temporal) | 18 | 1364 |
| 10 | dim_docente | Dimensión | Un registro por docente que dicta módulos | 4 | 0 |
| 11 | dim_modulo | Dimensión | Un registro por módulo de programa e institución | 7 | 572 |
| 12 | dim_origen_documental | Dimensión | Un registro por archivo fuente ingerido (trazabilidad del dato) | 10 | 7 |
| 13 | dim_categoria_financiera | Dimensión | Categorías de ingreso/egreso usadas por los hechos financieros | 4 | 3 |
| 14 | dim_meta | Dimensión | Metas presupuestarias mensuales por categoría | 5 | 45 |
| 15 | cat_institucion | Dimensión | Instituciones del grupo a las que pertenecen estudiantes y módulos | 5 | 4 |
| 16 | cat_categoria_financiera | Dimensión | Catálogo estándar de categorías financieras (códigos de ingreso y egreso) | 5 | 5 |
| 17 | staging_registros_crudos | Staging | Bloques y filas extraídos de cada documento antes de cargarse al almacén | 20 | 15 |
| 18 | stg_entidad_no_resuelta | Staging | Entidades que no se pudieron enlazar a una dimensión y esperan revisión humana (HITL) | 21 | 150 |
| 19 | log_pipeline_ingesta | Log | Bitácora de cada etapa del pipeline de ingesta por documento | 9 | 51 |
| 20 | log_inconsistencias | Log | Registro de reglas de calidad incumplidas por documento y fila | 13 | 0 |
| 21 | log_auditoria_nlp | Log | Correcciones humanas a predicciones del modelo BETO | 7 | 0 |
| 22 | schema_migrations | Log | Migraciones SQL versionadas ya aplicadas a la base | 2 | 4 |
| 23 | users | Transaccional | Usuarios del sistema con su rol RBAC y estado de autenticación | 14 | 7 |
| 24 | notifications | Transaccional | Notificaciones y alertas enviadas a usuarios o roles | 10 | 10 |
| 25 | lote | Transaccional | Lotes de carga multi-archivo por institución y periodo | 6 | 1 |
| 26 | cat_docente | Dimensión | Catálogo canónico de docentes al que se enlaza dim_docente | 5 | 0 |
| 27 | cat_modulo | Dimensión | Catálogo canónico de módulos al que se enlaza dim_modulo | 5 | 0 |

**Tabla F.2 Diccionario de datos - fact_rendimiento_academico**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_hecho_aca | SERIAL | NO | PK | Identificador del registro de rendimiento académico |
| id_estudiante | INTEGER | SÍ | FK → dim_estudiante(id_estudiante) ON DELETE CASCADE; UNIQUE (id_estudiante, id_modulo) | Estudiante que cursó el módulo |
| id_docente | INTEGER | SÍ | FK → dim_docente(id_docente) ON DELETE SET NULL | Docente que dictó el módulo |
| id_modulo | INTEGER | SÍ | FK → dim_modulo(id_modulo) ON DELETE CASCADE; UNIQUE (id_estudiante, id_modulo) | Módulo cursado |
| id_tiempo | INTEGER | SÍ | FK → dim_tiempo(id_tiempo) ON DELETE CASCADE | Fecha a la que se imputa la calificación |
| id_documento | INTEGER | SÍ | FK → dim_origen_documental(id_documento) ON DELETE SET NULL | Documento fuente del que se extrajo la calificación |
| id_usuario_carga | INTEGER | SÍ | FK → users(id) ON DELETE SET NULL | Usuario que ejecutó la carga del registro |
| nota_final | NUMERIC(5,2) | SÍ | — | Promedio final del módulo en escala 0–100 (las escalas 0–10 y 0–20 se convierten al cargar) |
| asistencia_pct | NUMERIC(5,2) | SÍ | — | Porcentaje de asistencia del estudiante al módulo (0–100) |
| incumplimiento_actividades_pct | NUMERIC(5,2) | SÍ | DEFAULT 0.00 | Porcentaje de actividades no cumplidas en el módulo (0–100) |
| nivel_confianza_ia | NUMERIC(5,4) | SÍ | — | Confianza del modelo BETO en la extracción del registro (0–1) |
| requiere_revision | BOOLEAN | SÍ | DEFAULT false | Indica que el registro debe pasar por la bandeja de revisión humana (HITL) |
| fk_estado | VARCHAR(1) | SÍ | DEFAULT 'A' | Calidad del enlace al estudiante: A (CI válido, enlace directo), B (rescatado por coincidencia de nombre), C (no resuelto, a revisión humana) |
| estado_academico | VARCHAR(50) | SÍ | — | Resultado del módulo: Aprobado (nota ≥ 70), Reprobado o En Curso (sin nota) |
| tipo_alerta | VARCHAR(30) | SÍ | — | Alerta temprana académica: NORMAL, RIESGO_ACADEMICO (nota ≤ 70), RIESGO_CRITICO (nota < 51) |
| created_at | TIMESTAMP | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora de carga del registro |

Índices: fact_rendimiento_academico_pkey (id_hecho_aca) [PK]; idx_fact_rend_docente (id_docente); idx_fact_rend_documento (id_documento); idx_fact_rend_estudiante (id_estudiante); idx_fact_rend_modulo (id_modulo); idx_fact_rend_tiempo (id_tiempo); idx_fact_rendimiento_fk_estado (fk_estado); uq_fact_rendimiento_estudiante_modulo (id_estudiante, id_modulo) [único]

**Tabla F.3 Diccionario de datos - fact_situacion_financiera**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_hecho_fin | SERIAL | NO | PK | Identificador del registro de situación financiera |
| id_estudiante | INTEGER | SÍ | FK → dim_estudiante(id_estudiante) ON DELETE CASCADE; UNIQUE (índice uq_fact_fin_est_mod_tiempo) | Estudiante titular de la deuda |
| id_modulo | INTEGER | SÍ | FK → dim_modulo(id_modulo) ON DELETE SET NULL; UNIQUE (índice uq_fact_fin_est_mod_tiempo) | Módulo o programa al que corresponde el cobro |
| id_categoria_fin | INTEGER | SÍ | FK → dim_categoria_financiera(id_categoria) ON DELETE SET NULL | Categoría financiera del movimiento |
| id_tiempo | INTEGER | SÍ | FK → dim_tiempo(id_tiempo) ON DELETE CASCADE; UNIQUE (índice uq_fact_fin_est_mod_tiempo) | Fecha de corte de la cartera |
| id_documento | INTEGER | SÍ | FK → dim_origen_documental(id_documento) ON DELETE SET NULL | Documento fuente del que se extrajo el registro |
| concepto | VARCHAR(150) | SÍ | — | Concepto de cobro informado en el documento fuente |
| monto_deuda | NUMERIC(12,2) | SÍ | DEFAULT 0.00 | Saldo pendiente de pago del estudiante |
| monto_pagado | NUMERIC(12,2) | SÍ | DEFAULT 0.00 | Monto pagado por el estudiante a la fecha de corte |
| cuotas_impagas | INTEGER | SÍ | DEFAULT 0 | Número de cuotas vencidas sin pagar (≥ 2 dispara la alerta de riesgo financiero) |
| estado_cartera | VARCHAR(20) | SÍ | — | Clasificación de la cartera: Vigente, En Mora, Previsionable |
| tipo_alerta | VARCHAR(30) | SÍ | DEFAULT 'NORMAL' | Alerta de mora: NORMAL (0 cuotas impagas), MORA_TEMPRANA (1), RIESGO_CARTERA (≥ 2) |
| nivel_confianza_ia | NUMERIC(5,4) | SÍ | DEFAULT 1.0000 | Confianza del modelo BETO en la extracción del registro (0–1) |
| requiere_revision | BOOLEAN | SÍ | DEFAULT false | Indica que el registro debe pasar por la bandeja de revisión humana (HITL) |
| fk_estado | VARCHAR(1) | SÍ | DEFAULT 'A' | Calidad del enlace al estudiante: A (CI válido, enlace directo), B (rescatado por coincidencia de nombre), C (no resuelto, a revisión humana) |
| fecha_registro | TIMESTAMP | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora de carga del registro |

Índices: fact_situacion_financiera_pkey (id_hecho_fin) [PK]; idx_fact_fin_documento (id_documento); idx_fact_fin_estado_cartera (estado_cartera); idx_fact_fin_estudiante (id_estudiante); idx_fact_fin_modulo (id_modulo); idx_fact_fin_mora_estudiante (id_estudiante) [parcial: WHERE (cuotas_impagas >= 2)]; idx_fact_fin_tiempo (id_tiempo); idx_fact_financiera_fk_estado (fk_estado); idx_fact_financiera_revision (requiere_revision); uq_fact_fin_est_mod_tiempo (id_estudiante, COALESCE(id_modulo, 0), id_tiempo) [único]

**Tabla F.4 Diccionario de datos - fact_cobranzas_proyectadas**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_hecho_cobro | SERIAL | NO | PK | Identificador de la cobranza proyectada |
| id_estudiante | INTEGER | SÍ | FK → dim_estudiante(id_estudiante) ON DELETE CASCADE; UNIQUE (id_estudiante, id_tiempo) | Estudiante al que corresponde el cobro proyectado |
| id_tiempo | INTEGER | SÍ | FK → dim_tiempo(id_tiempo) ON DELETE CASCADE; UNIQUE (id_estudiante, id_tiempo) | Fecha del cobro proyectado |
| monto_esperado | NUMERIC(10,2) | SÍ | — | Por documentar |
| estado_pago | VARCHAR(50) | SÍ | — | Por documentar |
| created_at | TIMESTAMP | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora de creación del registro |

Índices: fact_cobranzas_proyectadas_pkey (id_hecho_cobro) [PK]; idx_fact_cobproy_tiempo (id_tiempo); uq_fact_cobranzas_proyectadas_estudiante_tiempo (id_estudiante, id_tiempo) [único]

**Tabla F.5 Diccionario de datos - fact_evaluacion_docente**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_hecho_eval | SERIAL | NO | PK | Identificador de la respuesta de evaluación |
| id_docente | INTEGER | SÍ | FK → dim_docente(id_docente) ON DELETE CASCADE | Docente evaluado |
| id_modulo | INTEGER | SÍ | FK → dim_modulo(id_modulo) ON DELETE CASCADE | Módulo en el que se evaluó al docente |
| id_estudiante | INTEGER | SÍ | FK → dim_estudiante(id_estudiante) ON DELETE SET NULL | Estudiante que respondió la evaluación (opcional) |
| id_tiempo | INTEGER | SÍ | FK → dim_tiempo(id_tiempo) ON DELETE CASCADE | Fecha de la evaluación |
| pregunta_bloque | VARCHAR(500) | SÍ | — | Pregunta o criterio evaluado de la encuesta docente |
| puntuacion | NUMERIC(4,2) | SÍ | — | Puntuación otorgada al docente en el criterio |
| comentario | VARCHAR(1000) | SÍ | — | Comentario libre del estudiante sobre el docente |

Índices: fact_evaluacion_docente_pkey (id_hecho_eval) [PK]; idx_fact_eval_docente (id_docente); idx_fact_eval_estudiante (id_estudiante); idx_fact_eval_modulo (id_modulo); idx_fact_eval_tiempo (id_tiempo)

**Tabla F.6 Diccionario de datos - fact_marketing**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_hecho_mkt | SERIAL | NO | PK | Identificador del registro de marketing |
| id_modulo | INTEGER | SÍ | FK → dim_modulo(id_modulo) ON DELETE CASCADE; UNIQUE (id_modulo, id_tiempo) | Programa o módulo promocionado |
| id_tiempo | INTEGER | SÍ | FK → dim_tiempo(id_tiempo) ON DELETE CASCADE; UNIQUE (id_modulo, id_tiempo) | Mes de la campaña |
| leads | INTEGER | SÍ | DEFAULT 0 | Número de interesados (leads) captados |
| reservas | INTEGER | SÍ | DEFAULT 0 | Número de reservas de cupo |
| inscritos | INTEGER | SÍ | DEFAULT 0 | Número de inscritos efectivos |
| costo_programa | NUMERIC(12,2) | SÍ | — | Costo del programa ofertado |

Índices: fact_marketing_pkey (id_hecho_mkt) [PK]; idx_fact_mkt_tiempo (id_tiempo); uq_fact_marketing_modulo_tiempo (id_modulo, id_tiempo) [único]

**Tabla F.7 Diccionario de datos - fact_rentabilidad**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_hecho_rent | SERIAL | NO | PK | Identificador del registro de rentabilidad |
| id_modulo | INTEGER | SÍ | FK → dim_modulo(id_modulo) ON DELETE CASCADE | Programa o centro de costo (ADM-GEN cuando el monto es general) |
| id_tiempo | INTEGER | SÍ | FK → dim_tiempo(id_tiempo) ON DELETE CASCADE; UNIQUE (id_categoria, id_tiempo) | Mes del registro |
| id_categoria | INTEGER | SÍ | FK → dim_categoria_financiera(id_categoria) ON DELETE CASCADE; UNIQUE (id_categoria, id_tiempo) | Categoría financiera del monto (PROGRAMAS, TECHOS_CERRADOS, FINANCIERO_ANUAL…) |
| monto_ejecutado | NUMERIC(14,2) | SÍ | — | Ingreso o gasto ejecutado en el mes |
| monto_meta | NUMERIC(14,2) | SÍ | — | Meta presupuestaria del mes |

Índices: fact_rentabilidad_pkey (id_hecho_rent) [PK]; idx_fact_rent_tiempo (id_tiempo); uq_fact_rentabilidad_categoria_tiempo (id_categoria, id_tiempo) [único]

**Tabla F.8 Diccionario de datos - fact_forecast**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_forecast | SERIAL | NO | PK | Identificador del valor pronosticado |
| caso_uso | VARCHAR(50) | NO | UNIQUE (caso_uso, id_tiempo) | Serie pronosticada: ALUMNOS_GLOBAL, ALUMNOS_DIPLOMADO, ALUMNOS_CURSO, ALUMNOS_EXPERTO, META_ANUAL, META_MENSUAL_PROGRAMAS |
| id_tiempo | INTEGER | SÍ | FK → dim_tiempo(id_tiempo) ON DELETE CASCADE; UNIQUE (caso_uso, id_tiempo) | Mes proyectado |
| valor_forecast | NUMERIC(14,2) | NO | — | Valor pronosticado para el mes |
| ic_lower | NUMERIC(14,2) | SÍ | — | Límite inferior del intervalo de confianza del pronóstico |
| ic_upper | NUMERIC(14,2) | SÍ | — | Límite superior del intervalo de confianza del pronóstico |
| metodo | VARCHAR(30) | NO | DEFAULT 'HoltWinters' | Modelo de pronóstico usado: HoltWinters u OLS |
| horizonte_meses | INTEGER | NO | — | Cantidad de meses proyectados (1 a 6) |
| generado_en | TIMESTAMP | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora en que se generó el pronóstico |

Índices: fact_forecast_pkey (id_forecast) [PK]; idx_fact_forecast_caso (caso_uso); uq_forecast_caso_tiempo (caso_uso, id_tiempo) [único]

**Tabla F.9 Diccionario de datos - dim_tiempo**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_tiempo | INTEGER | NO | PK | Clave de la fecha en formato AAAAMMDD |
| fecha | DATE | NO | UNIQUE | Fecha calendario |
| gestion | INTEGER | NO | — | Año (gestión) |
| semestre | INTEGER | NO | — | Semestre del año (1, 2) |
| trimestre | INTEGER | NO | — | Trimestre del año (1 a 4) |
| mes | INTEGER | NO | — | Mes del año (1 a 12) |
| nombre_mes | VARCHAR(20) | NO | — | Nombre del mes en español (Enero … Diciembre) |
| semana_iso | INTEGER | NO | — | Semana ISO del año (1 a 53) |
| dia_mes | INTEGER | NO | — | Día del mes (1 a 31) |
| dia_semana | INTEGER | NO | — | Día de la semana (1 = Lunes … 7 = Domingo) |
| nombre_dia | VARCHAR(20) | NO | — | Nombre del día en español (Lunes … Domingo) |
| es_fin_semana | BOOLEAN | NO | — | Indica si la fecha cae sábado o domingo |
| periodo_mes | VARCHAR(7) | NO | — | Año y mes en formato AAAA-MM |

Índices: dim_tiempo_fecha_key (fecha) [único]; dim_tiempo_pkey (id_tiempo) [PK]; idx_dim_tiempo_gestion (gestion); idx_dim_tiempo_periodo (periodo_mes)

**Tabla F.10 Diccionario de datos - dim_estudiante**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_estudiante | SERIAL | NO | PK | Identificador del estudiante en el almacén |
| nombre_completo | VARCHAR(200) | NO | — | Nombre completo del estudiante |
| codigo_estudiante | VARCHAR(50) | SÍ | — | Código del estudiante (número de CI o identificador temporal) |
| ci | VARCHAR(50) | SÍ | — | Cédula de identidad tal como llegó en la fuente |
| ci_numero | VARCHAR(30) | SÍ | UNIQUE parcial (índice uq_dim_estudiante_ci_numero) | Parte numérica normalizada del CI (única entre estudiantes vigentes) |
| ci_complemento | VARCHAR(10) | SÍ | — | Complemento o extensión del CI |
| id_temporal | VARCHAR(100) | SÍ | — | Identificador temporal (TEMP-…) asignado al estudiante que llega sin CI |
| identidad_verificada | BOOLEAN | SÍ | DEFAULT false | Indica que la identidad se confirmó con un CI válido |
| id_institucion | INTEGER | SÍ | FK → cat_institucion(id_institucion) ON DELETE SET NULL | Institución a la que pertenece el estudiante |
| programa_origen | VARCHAR(200) | SÍ | — | Programa con el que se registró por primera vez al estudiante |
| deprecado | BOOLEAN | SÍ | DEFAULT false | Marca un registro duplicado que se fusionó en otro estudiante |
| fusionado_en | INTEGER | SÍ | FK → dim_estudiante(id_estudiante) ON DELETE SET NULL | Estudiante que absorbió a este registro al fusionar duplicados |
| genero | VARCHAR(20) | SÍ | — | Por documentar |
| ciudad | VARCHAR(100) | SÍ | — | Ciudad del estudiante |
| nivel_academico | VARCHAR(100) | SÍ | — | Nivel académico del estudiante |
| edad | INTEGER | SÍ | — | Por documentar |
| ocupacion | VARCHAR(100) | SÍ | — | Por documentar |
| estado_civil | VARCHAR(50) | SÍ | — | Por documentar |

Índices: dim_estudiante_pkey (id_estudiante) [PK]; uq_dim_estudiante_ci_numero (ci_numero) [único; parcial: WHERE ((deprecado = false) AND (ci_numero IS NOT NULL) AND (length((ci_numero)::text) >= 5))]

**Tabla F.11 Diccionario de datos - dim_docente**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_docente | SERIAL | NO | PK | Identificador del docente en el almacén |
| nombre_completo | VARCHAR(200) | NO | DEFAULT 'Docente Generico' | Nombre completo del docente (Docente Generico si la fuente no lo trae) |
| area_especialidad | VARCHAR(200) | SÍ | DEFAULT 'Generico' | Área de especialidad del docente |
| id_cat_docente | INTEGER | SÍ | FK → cat_docente(id_docente) ON DELETE SET NULL | Docente equivalente en el catálogo institucional (cat_docente) |

Índices: dim_docente_pkey (id_docente) [PK]

**Tabla F.12 Diccionario de datos - dim_modulo**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_modulo | SERIAL | NO | PK | Identificador del módulo en el almacén |
| nombre_modulo | VARCHAR(200) | NO | DEFAULT 'Modulo Generico' | Nombre del módulo |
| nombre_institucion | VARCHAR(200) | NO | DEFAULT 'GiraGroup Posgrado' | Nombre de la institución que dicta el módulo |
| id_institucion | INTEGER | SÍ | FK → cat_institucion(id_institucion) ON DELETE SET NULL | Institución que dicta el módulo |
| programa | VARCHAR(200) | SÍ | DEFAULT 'General' | Programa al que pertenece el módulo |
| pos_code | VARCHAR(50) | SÍ | — | Código del programa (POS-…; ADM-GEN para administración general) |
| id_cat_modulo | INTEGER | SÍ | FK → cat_modulo(id_modulo) ON DELETE SET NULL | Módulo equivalente en el catálogo institucional (cat_modulo) |

Índices: dim_modulo_pkey (id_modulo) [PK]

**Tabla F.13 Diccionario de datos - dim_origen_documental**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_documento | SERIAL | NO | PK | Identificador del documento fuente |
| id_lote | INTEGER | SÍ | FK → lote(id_lote) ON DELETE SET NULL | Lote de carga al que pertenece el documento |
| tipo_documento | VARCHAR(50) | SÍ | DEFAULT 'SHEET' | Formato del archivo (SHEET, CSV) |
| tipo_fuente | VARCHAR(30) | SÍ | CHECK IN (ACTA, COBRANZA, ADMISION, MOODLE, EVALUACION_DOCENTE, EGRESOS, TECHOS, PLANIFICACION, MARKETING, RENTABILIDAD, ERROR, RECHAZADO, DUPLICADO, SIN_RECONOCER) o NULL | Tipo de fuente: ACTA, COBRANZA, ADMISION, MOODLE, EVALUACION_DOCENTE, EGRESOS, TECHOS, PLANIFICACION, MARKETING, RENTABILIDAD, ERROR, RECHAZADO, DUPLICADO, SIN_RECONOCER |
| tipo_escala | VARCHAR(20) | SÍ | CHECK IN (CENTESIMAL_100, DECIMAL_10, VIGESIMAL_20) o NULL | Escala de calificación del documento: CENTESIMAL_100, DECIMAL_10, VIGESIMAL_20 |
| nombre_archivo | VARCHAR(500) | SÍ | DEFAULT 'archivo_generico' | Nombre del archivo cargado |
| institucion | VARCHAR(100) | SÍ | — | Institución a la que pertenece el documento |
| periodo | VARCHAR(30) | SÍ | — | Periodo que cubre el documento |
| hash_sha256 | VARCHAR(64) | SÍ | — | Huella SHA-256 del archivo, para detectar cargas duplicadas |
| fecha_procesamiento | TIMESTAMP | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora en que se procesó el documento |

Índices: dim_origen_documental_pkey (id_documento) [PK]; idx_dim_origen_hash_sha256 (hash_sha256); idx_dim_origen_id_lote (id_lote)

**Tabla F.14 Diccionario de datos - dim_categoria_financiera**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_categoria | SERIAL | NO | PK | Identificador de la categoría financiera |
| nombre_categoria | VARCHAR(200) | NO | UNIQUE | Nombre de la categoría (PROGRAMAS, TECHOS_CERRADOS, FINANCIERO_ANUAL…) |
| tipo | VARCHAR(50) | SÍ | — | Tipo de flujo: INGRESO, EGRESO, RENTABILIDAD, EBITDA |
| id_cat_categoria_fin | INTEGER | SÍ | FK → cat_categoria_financiera(id_categoria_fin) ON DELETE SET NULL | Categoría equivalente del catálogo estándar (cat_categoria_financiera) |

Índices: dim_categoria_financiera_nombre_categoria_key (nombre_categoria) [único]; dim_categoria_financiera_pkey (id_categoria) [PK]

**Tabla F.15 Diccionario de datos - dim_meta**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_meta | SERIAL | NO | PK | Identificador de la meta |
| categoria | VARCHAR(50) | NO | — | Categoría de la meta (PROGRAMAS, TECHOS_CERRADOS) |
| id_tiempo | INTEGER | SÍ | FK → dim_tiempo(id_tiempo) ON DELETE CASCADE | Mes al que corresponde la meta |
| monto_meta | NUMERIC(14,2) | SÍ | — | Monto presupuestado como meta |
| tipo_programa | VARCHAR(50) | SÍ | — | Tipo de programa de la meta (PROGRAMAS, TECHOS_CERRADOS) |

Índices: dim_meta_pkey (id_meta) [PK]; idx_dim_meta_cat (categoria); idx_dim_meta_tiempo (id_tiempo)

**Tabla F.16 Diccionario de datos - cat_institucion**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_institucion | SERIAL | NO | PK | Identificador de la institución |
| nombre_institucion | VARCHAR(100) | NO | UNIQUE | Nombre de la institución |
| sigla | VARCHAR(30) | SÍ | — | Sigla de la institución (GG, ENP, FCS) |
| tipo_escala_default | VARCHAR(20) | SÍ | DEFAULT 'CENTESIMAL_100' | Por documentar |
| created_at | TIMESTAMP | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora de registro de la institución |

Índices: cat_institucion_nombre_institucion_key (nombre_institucion) [único]; cat_institucion_pkey (id_institucion) [PK]

**Tabla F.17 Diccionario de datos - cat_categoria_financiera**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_categoria_fin | SERIAL | NO | PK | Identificador de la categoría estándar |
| codigo | VARCHAR(50) | NO | UNIQUE | Código de la categoría (ING-MAT-01, ING-COB-01, ING-CER-01, EGR-DOC-01, EGR-OPE-01) |
| nombre_categoria | VARCHAR(100) | NO | — | Nombre de la categoría |
| tipo_flujo | VARCHAR(30) | NO | DEFAULT 'INGRESO' | Tipo de flujo: INGRESO o EGRESO |
| created_at | TIMESTAMP | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora de registro de la categoría |

Índices: cat_categoria_financiera_codigo_key (codigo) [único]; cat_categoria_financiera_pkey (id_categoria_fin) [PK]

**Tabla F.18 Diccionario de datos - staging_registros_crudos**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id | SERIAL | NO | PK | Identificador del registro crudo |
| id_documento | INTEGER | SÍ | FK → dim_origen_documental(id_documento) ON DELETE CASCADE | Documento del que se extrajo el registro |
| hoja | VARCHAR(200) | SÍ | — | Hoja de cálculo de origen |
| bloque_id | INTEGER | SÍ | — | Número del bloque tabular dentro de la hoja |
| categoria | VARCHAR(50) | SÍ | — | Categoría del bloque: academico, financiero, marketing, rentabilidad, evaluacion_docente |
| texto_plano | TEXT | SÍ | — | Contenido del bloque serializado a texto para el modelo BETO |
| n_filas | INTEGER | SÍ | — | Número de filas del bloque |
| fila_inicio | INTEGER | SÍ | — | Primera fila del bloque en la hoja |
| fila_fin | INTEGER | SÍ | — | Última fila del bloque en la hoja |
| es_ruido | BOOLEAN | SÍ | DEFAULT false | Marca el bloque como ruido; no se carga al almacén |
| requiere_revision | BOOLEAN | SÍ | DEFAULT false | Indica que el registro debe pasar por la bandeja de revisión humana (HITL) |
| score_confianza | NUMERIC(5,4) | SÍ | DEFAULT 1.0 | Confianza de la extracción del registro (0–1) |
| motivo | VARCHAR(100) | SÍ | — | Motivo del estado del registro (por ejemplo, APROBADO_AUTOMATICO) |
| payload_json | JSONB | SÍ | — | Datos estructurados extraídos del registro, en JSON |
| registro_origen_id | INTEGER | SÍ | FK → staging_registros_crudos(id) ON DELETE CASCADE | Registro crudo del que deriva este registro |
| estado_resolucion | VARCHAR(30) | SÍ | DEFAULT 'PENDIENTE' | Estado del registro: PENDIENTE, APROBADO_AUTOMATICO, RESUELTO_HUMANO, DESCARTADO |
| resuelto | BOOLEAN | SÍ | DEFAULT false | Indica que el registro ya fue resuelto |
| resuelto_por | INTEGER | SÍ | FK → users(id) ON DELETE SET NULL | Usuario que resolvió el registro |
| resuelto_en | TIMESTAMP | SÍ | — | Fecha y hora de la resolución |
| created_at | TIMESTAMPTZ | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora de extracción del registro |

Índices: idx_staging_doc_id (id_documento); staging_registros_crudos_pkey (id) [PK]

**Tabla F.19 Diccionario de datos - stg_entidad_no_resuelta**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_staging | SERIAL | NO | PK | Identificador de la entidad pendiente |
| id_documento | INTEGER | SÍ | FK → dim_origen_documental(id_documento) ON DELETE CASCADE | Documento en el que se detectó la entidad |
| tipo_entidad | VARCHAR(50) | NO | — | Tipo de entidad no resuelta (ESTUDIANTE, RUIDO) |
| texto_original | TEXT | NO | — | Texto de la entidad tal como se extrajo |
| ci_temporal | VARCHAR(150) | SÍ | — | CI leído en la fuente o CI temporal asignado a la entidad |
| mejor_candidato | TEXT | SÍ | — | Mejor coincidencia encontrada en la dimensión |
| score_fuzzy | NUMERIC(5,2) | SÍ | — | Similitud difusa (RapidFuzz) con el mejor candidato, de 0 a 100 |
| fk_estado | VARCHAR(1) | SÍ | DEFAULT 'C' | Estado de la FK; las entidades ingresan con C (no resuelto) |
| nivel_confianza | NUMERIC(5,4) | SÍ | — | Confianza del modelo BETO en la extracción del registro (0–1) |
| resuelto | BOOLEAN | SÍ | DEFAULT false | Indica que la entidad ya fue resuelta |
| resuelto_por | INTEGER | SÍ | FK → users(id) ON DELETE SET NULL | Auditor que resolvió la entidad |
| resuelto_en | TIMESTAMP | SÍ | — | Fecha y hora de la resolución |
| id_dimension_resuelta | INTEGER | SÍ | — | Estudiante (id_estudiante) asignado al resolver la entidad |
| motivo | VARCHAR(100) | SÍ | — | Motivo del envío a revisión: BAJA_CONFIANZA_IA, CI_NOMBRE_DISCORDANTE, FILA_ACADEMICA_SIN_ESTUDIANTE, FILA_SIN_ENTIDAD |
| payload_json | JSONB | SÍ | — | Fila original en JSON, para recargarla al resolver |
| registro_origen_id | INTEGER | SÍ | FK → staging_registros_crudos(id) ON DELETE CASCADE | Registro crudo del que proviene la entidad |
| estado_resolucion | VARCHAR(30) | SÍ | DEFAULT 'PENDIENTE' | Estado de la revisión: PENDIENTE, RESUELTO_HUMANO, DESCARTADO |
| lock_usuario_id | INTEGER | SÍ | FK → users(id) ON DELETE SET NULL | Auditor que tiene tomada la entidad mientras la revisa |
| lock_expira | TIMESTAMP | SÍ | — | Vencimiento del bloqueo de revisión (5 minutos desde que se toma) |
| version | INTEGER | SÍ | DEFAULT 1 | Por documentar |
| created_at | TIMESTAMP | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora de detección de la entidad |

Índices: idx_stg_entidad_doc (id_documento); idx_stg_entidad_registro (registro_origen_id); idx_stg_entidad_resuelto (resuelto, estado_resolucion); idx_stg_no_resuelta_doc (id_documento); idx_stg_no_resuelta_estado (resuelto); idx_stg_no_resuelta_estado_res (estado_resolucion); idx_stg_no_resuelta_lock (lock_usuario_id, lock_expira); idx_stg_no_resuelta_motivo (motivo); idx_stg_no_resuelta_tipo (tipo_entidad); stg_entidad_no_resuelta_pkey (id_staging) [PK]

**Tabla F.20 Diccionario de datos - log_pipeline_ingesta**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id | SERIAL | NO | PK | Identificador del evento |
| id_documento | INTEGER | SÍ | FK → dim_origen_documental(id_documento) ON DELETE CASCADE | Documento procesado |
| etapa | VARCHAR(50) | NO | — | Etapa del pipeline: UPLOAD, INGESTA, CLEAN, NORMALIZE, VALIDATE, STAGE, DISPATCH, DW_CONSOLIDACION, SUMMARY |
| nivel | VARCHAR(10) | NO | — | Nivel del evento: INFO, WARN, ERROR, SUCCESS |
| modulo | VARCHAR(100) | SÍ | — | Componente que emitió el evento |
| mensaje | TEXT | NO | — | Descripción del evento |
| tiempo_ms | INTEGER | SÍ | — | Duración de la etapa en milisegundos |
| metadata | JSONB | SÍ | — | Datos adicionales del evento, en JSON |
| created_at | TIMESTAMPTZ | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora del evento |

Índices: idx_log_pipeline_doc (id_documento); log_pipeline_ingesta_pkey (id) [PK]

**Tabla F.21 Diccionario de datos - log_inconsistencias**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_inconsistencia | SERIAL | NO | PK | Identificador de la inconsistencia |
| id_documento | INTEGER | SÍ | FK → dim_origen_documental(id_documento) ON DELETE CASCADE | Documento en el que se detectó la inconsistencia |
| fila_origen | INTEGER | SÍ | — | Fila del documento con la inconsistencia |
| campo_afectado | VARCHAR(100) | NO | — | Campo que no cumple la regla |
| valor_recibido | TEXT | SÍ | — | Valor encontrado en la fuente |
| valor_esperado | TEXT | SÍ | — | Valor o formato esperado |
| tipo_regla | VARCHAR(50) | NO | — | Por documentar |
| severidad | VARCHAR(20) | NO | DEFAULT 'ALTA' | Por documentar (por defecto ALTA) |
| estado_resolucion | VARCHAR(30) | NO | DEFAULT 'BLOQUEADO' | Por documentar (por defecto BLOQUEADO) |
| descripcion | TEXT | SÍ | — | Detalle de la inconsistencia |
| detectado_en | TIMESTAMP | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora de detección |
| resuelto_en | TIMESTAMP | SÍ | — | Fecha y hora de la resolución |
| resuelto_por | INTEGER | SÍ | FK → users(id) ON DELETE SET NULL | Usuario que resolvió la inconsistencia |

Índices: idx_log_inconsistencias_doc (id_documento); idx_log_inconsistencias_estado (estado_resolucion); log_inconsistencias_pkey (id_inconsistencia) [PK]

**Tabla F.22 Diccionario de datos - log_auditoria_nlp**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_log | SERIAL | NO | PK | Identificador de la corrección |
| texto_original | VARCHAR(500) | NO | — | Texto revisado por el auditor |
| prediccion_beto | VARCHAR(200) | SÍ | — | Entidad que propuso el modelo BETO |
| confianza_ia | NUMERIC(5,4) | SÍ | — | Confianza del modelo BETO en su predicción (0–1) |
| correccion_humana | VARCHAR(200) | NO | — | Valor corregido por el auditor |
| usuario_auditor | INTEGER | SÍ | FK → users(id) ON DELETE SET NULL | Auditor que hizo la corrección |
| created_at | TIMESTAMP | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora de la corrección |

Índices: log_auditoria_nlp_pkey (id_log) [PK]

**Tabla F.23 Diccionario de datos - schema_migrations**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| version | VARCHAR(255) | NO | PK | Nombre del archivo de migración aplicado |
| applied_at | TIMESTAMPTZ | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora en que se aplicó la migración |

Índices: schema_migrations_pkey (version) [PK]

**Tabla F.24 Diccionario de datos - users**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id | SERIAL | NO | PK | Identificador del usuario |
| username | VARCHAR(100) | NO | UNIQUE | Nombre de usuario para iniciar sesión |
| hashed_password | VARCHAR(255) | NO | — | Contraseña almacenada como hash |
| role | VARCHAR(50) | NO | CHECK IN (ADMIN, AUDITOR_CALIDAD, DIRECTOR_ACADEMICO, ANALISTA_FINANCIERO, ANALISTA_MARKETING) | Rol RBAC: ADMIN, AUDITOR_CALIDAD, DIRECTOR_ACADEMICO, ANALISTA_FINANCIERO, ANALISTA_MARKETING |
| email | VARCHAR(150) | NO | UNIQUE | Correo del usuario, al que se envía el código OTP |
| phone | VARCHAR(30) | SÍ | — | Teléfono de contacto del usuario |
| is_active | BOOLEAN | SÍ | DEFAULT true | Indica si la cuenta está habilitada |
| is_mfa_enabled | BOOLEAN | SÍ | DEFAULT true | Indica si se exige el segundo factor (código OTP) |
| otp_code_hash | VARCHAR(255) | SÍ | — | Hash del código OTP vigente |
| otp_expires_at | TIMESTAMPTZ | SÍ | — | Vencimiento del código OTP vigente |
| failed_login_attempts | INTEGER | SÍ | DEFAULT 0 | Intentos fallidos consecutivos de inicio de sesión |
| locked_until | TIMESTAMPTZ | SÍ | — | Fecha y hora hasta la que la cuenta queda bloqueada |
| created_by_id | INTEGER | SÍ | FK → users(id) ON DELETE NO ACTION | Usuario administrador que creó la cuenta |
| created_at | TIMESTAMPTZ | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora de creación de la cuenta |

Índices: users_email_key (email) [único]; users_pkey (id) [PK]; users_username_key (username) [único]

**Tabla F.25 Diccionario de datos - notifications**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id | SERIAL | NO | PK | Identificador de la notificación |
| user_id | INTEGER | SÍ | FK → users(id) ON DELETE NO ACTION | Usuario destinatario (vacío si se dirige a un rol) |
| role_target | VARCHAR(50) | SÍ | — | Rol destinatario: ADMIN, AUDITOR_CALIDAD, DIRECTOR_ACADEMICO, ANALISTA_FINANCIERO |
| title | VARCHAR(200) | NO | — | Título de la notificación |
| message | TEXT | NO | — | Texto de la notificación |
| category | VARCHAR(50) | NO | — | Origen: DataOps, Predictivo o tipo de alerta (ACADEMICO, DESERCION, FINANCIERO, RIESGO_CRUZADO, DATAOPS_CALIDAD) |
| severity | VARCHAR(20) | NO | — | Severidad: INFO, SUCCESS, WARNING, CRITICAL |
| is_read | BOOLEAN | SÍ | DEFAULT false | Indica si el destinatario ya la leyó |
| link | VARCHAR(255) | SÍ | — | Ruta de la pantalla relacionada con la notificación |
| created_at | TIMESTAMPTZ | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora de emisión |

Índices: idx_notifications_user_unread (user_id, is_read); notifications_pkey (id) [PK]

**Tabla F.26 Diccionario de datos - lote**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_lote | SERIAL | NO | PK | Identificador del lote de carga |
| institucion | VARCHAR(100) | NO | — | Institución a la que pertenece el lote |
| periodo | VARCHAR(30) | NO | — | Periodo que cubre el lote |
| estado | VARCHAR(30) | SÍ | DEFAULT 'PROCESADO' | Estado del lote (PROCESADO por defecto) |
| total_archivos | INTEGER | SÍ | DEFAULT 0 | Cantidad de archivos del lote |
| creado_en | TIMESTAMP | SÍ | DEFAULT CURRENT_TIMESTAMP | Fecha y hora de creación del lote |

Índices: idx_lote_institucion_periodo (institucion, periodo); lote_pkey (id_lote) [PK]

**Tabla F.27 Diccionario de datos - cat_docente**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_docente | SERIAL | NO | PK | Identificador del docente en el catálogo canónico |
| codigo_docente | VARCHAR(50) | SÍ | — | Código del docente en el sistema académico de origen |
| nombre_canonico | VARCHAR(200) | NO | — | Nombre normalizado del docente, contra el que se emparejan los nombres extraídos |
| area | VARCHAR(100) | SÍ | DEFAULT 'Académico' | Área a la que pertenece el docente |
| nombre_completo | VARCHAR(200) | SÍ | — | Nombre completo del docente (la migración 002 lo inicializa con nombre_canonico) |

Índices: cat_docente_pkey (id_docente) [PK]

**Tabla F.28 Diccionario de datos - cat_modulo**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_modulo | SERIAL | NO | PK | Identificador del módulo en el catálogo canónico |
| codigo_modulo | VARCHAR(50) | SÍ | — | Código del módulo en el sistema académico de origen |
| nombre_canonico | VARCHAR(200) | NO | — | Nombre normalizado del módulo, contra el que se emparejan los nombres extraídos |
| area | VARCHAR(100) | SÍ | DEFAULT 'General' | Área temática del módulo |
| nombre_modulo | VARCHAR(255) | SÍ | — | Nombre del módulo (la migración 002 lo inicializa con nombre_canonico) |

Índices: cat_modulo_pkey (id_modulo) [PK]

**Tabla F.29 Relaciones**

| Tabla origen | Columna FK | Tabla destino | Columna | ON DELETE |
|---|---|---|---|---|
| dim_categoria_financiera | id_cat_categoria_fin | cat_categoria_financiera | id_categoria_fin | SET NULL |
| dim_docente | id_cat_docente | cat_docente | id_docente | SET NULL |
| dim_estudiante | fusionado_en | dim_estudiante | id_estudiante | SET NULL |
| dim_estudiante | id_institucion | cat_institucion | id_institucion | SET NULL |
| dim_meta | id_tiempo | dim_tiempo | id_tiempo | CASCADE |
| dim_modulo | id_cat_modulo | cat_modulo | id_modulo | SET NULL |
| dim_modulo | id_institucion | cat_institucion | id_institucion | SET NULL |
| dim_origen_documental | id_lote | lote | id_lote | SET NULL |
| fact_cobranzas_proyectadas | id_estudiante | dim_estudiante | id_estudiante | CASCADE |
| fact_cobranzas_proyectadas | id_tiempo | dim_tiempo | id_tiempo | CASCADE |
| fact_evaluacion_docente | id_docente | dim_docente | id_docente | CASCADE |
| fact_evaluacion_docente | id_estudiante | dim_estudiante | id_estudiante | SET NULL |
| fact_evaluacion_docente | id_modulo | dim_modulo | id_modulo | CASCADE |
| fact_evaluacion_docente | id_tiempo | dim_tiempo | id_tiempo | CASCADE |
| fact_forecast | id_tiempo | dim_tiempo | id_tiempo | CASCADE |
| fact_marketing | id_modulo | dim_modulo | id_modulo | CASCADE |
| fact_marketing | id_tiempo | dim_tiempo | id_tiempo | CASCADE |
| fact_rendimiento_academico | id_docente | dim_docente | id_docente | SET NULL |
| fact_rendimiento_academico | id_documento | dim_origen_documental | id_documento | SET NULL |
| fact_rendimiento_academico | id_estudiante | dim_estudiante | id_estudiante | CASCADE |
| fact_rendimiento_academico | id_modulo | dim_modulo | id_modulo | CASCADE |
| fact_rendimiento_academico | id_tiempo | dim_tiempo | id_tiempo | CASCADE |
| fact_rendimiento_academico | id_usuario_carga | users | id | SET NULL |
| fact_rentabilidad | id_categoria | dim_categoria_financiera | id_categoria | CASCADE |
| fact_rentabilidad | id_modulo | dim_modulo | id_modulo | CASCADE |
| fact_rentabilidad | id_tiempo | dim_tiempo | id_tiempo | CASCADE |
| fact_situacion_financiera | id_categoria_fin | dim_categoria_financiera | id_categoria | SET NULL |
| fact_situacion_financiera | id_documento | dim_origen_documental | id_documento | SET NULL |
| fact_situacion_financiera | id_estudiante | dim_estudiante | id_estudiante | CASCADE |
| fact_situacion_financiera | id_modulo | dim_modulo | id_modulo | SET NULL |
| fact_situacion_financiera | id_tiempo | dim_tiempo | id_tiempo | CASCADE |
| log_auditoria_nlp | usuario_auditor | users | id | SET NULL |
| log_inconsistencias | id_documento | dim_origen_documental | id_documento | CASCADE |
| log_inconsistencias | resuelto_por | users | id | SET NULL |
| log_pipeline_ingesta | id_documento | dim_origen_documental | id_documento | CASCADE |
| notifications | user_id | users | id | NO ACTION |
| staging_registros_crudos | id_documento | dim_origen_documental | id_documento | CASCADE |
| staging_registros_crudos | registro_origen_id | staging_registros_crudos | id | CASCADE |
| staging_registros_crudos | resuelto_por | users | id | SET NULL |
| stg_entidad_no_resuelta | id_documento | dim_origen_documental | id_documento | CASCADE |
| stg_entidad_no_resuelta | lock_usuario_id | users | id | SET NULL |
| stg_entidad_no_resuelta | registro_origen_id | staging_registros_crudos | id | CASCADE |
| stg_entidad_no_resuelta | resuelto_por | users | id | SET NULL |
| users | created_by_id | users | id | NO ACTION |

## Apéndice G: Base de catálogo (catalog_db, 3NF)

Fuente: esquema de la base `giragroup_catalog_db` en ejecución (PostgreSQL 16), en tercera forma normal. Filas: conteo actual al 01-11-2026.

**Tabla G.1 Catálogo de tablas**

| N.º | Tabla | Tipo | Granularidad o propósito | N.º de columnas | Filas |
|---|---|---|---|---|---|
| 1 | cat_programa | Catálogo | Un registro por programa académico canónico (código POS) | 11 | 15 |
| 2 | cat_modulo | Catálogo | Un registro por módulo de un programa (número de orden único por programa) | 6 | 43 |
| 3 | cat_docente | Catálogo | Un registro por docente institucional | 6 | 7 |
| 4 | cat_escuela | Catálogo | Escuelas académicas de la institución | 3 | 9 |
| 5 | cat_tipo_programa | Catálogo | Tipos de programa ofertados | 2 | 8 |
| 6 | cat_modalidad | Catálogo | Modalidades de dictado | 2 | 6 |
| 7 | cat_estado_academico | Catálogo | Estados académicos posibles del estudiante | 2 | 6 |
| 8 | cat_estado_reprobado | Catálogo | Motivos de reprobación o baja | 2 | 4 |
| 9 | cat_estado_arca | Catálogo | Estados de registro del título (ARCA) | 2 | 4 |
| 10 | cat_tipo_cartera | Catálogo | Tramos de cartera según días de mora | 5 | 5 |
| 11 | cat_concepto_financiero | Catálogo | Conceptos financieros canónicos | 6 | 14 |
| 12 | cat_historico_equivalencia | Catálogo | Sinónimos históricos de cada concepto financiero en las planillas | 6 | 55 |
| 13 | cat_etiqueta_clasificacion | Catálogo | Palabras clave para clasificar documentos y hojas | 6 | 0 |
| 14 | cat_mapeo_columna | Catálogo | Encabezados de columna alternativos y su campo canónico | 4 | 0 |
| 15 | cat_guia_texto_plano | Catálogo | Plantillas para serializar filas a texto plano por subtipo | 6 | 0 |
| 16 | ref_metas_gestion | Referencia | Metas mensuales de ingreso y EBITDA por gestión y categoría | 8 | 6 |

**Tabla G.2 Diccionario de datos - cat_programa**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_programa | SERIAL | NO | PK | Identificador del programa |
| pos_code | VARCHAR(50) | NO | UNIQUE | Código único del programa (POS-…) |
| nombre_programa | VARCHAR(255) | NO | — | Nombre canónico del programa, sin sufijo de versión |
| version | INTEGER | SÍ | DEFAULT 1 | Versión del programa, tomada del nombre (v. N) o de la columna VERSIÓN |
| nombre_completo_raw | VARCHAR(300) | SÍ | — | Nombre del programa tal como figura en la fuente, con la versión |
| id_escuela | INTEGER | SÍ | FK → cat_escuela(id_escuela) ON DELETE RESTRICT | Escuela a la que pertenece el programa |
| id_tipo_programa | INTEGER | SÍ | FK → cat_tipo_programa(id_tipo_programa) ON DELETE RESTRICT | Tipo de programa |
| id_modalidad | INTEGER | SÍ | FK → cat_modalidad(id_modalidad) ON DELETE RESTRICT | Modalidad de dictado del programa |
| inversion_base | NUMERIC(12,2) | SÍ | DEFAULT 0.00 | Inversión base del programa según la planilla de programas |
| punto_equilibrio | INTEGER | SÍ | DEFAULT 0 | Número de inscritos necesario para cubrir los costos del programa |
| horas_totales | INTEGER | SÍ | DEFAULT 0 | Carga horaria total del programa |

Índices: cat_programa_pkey (id_programa) [PK]; cat_programa_pos_code_key (pos_code) [único]; idx_cat_prg_nombre (nombre_programa); idx_cat_prg_pos (pos_code)

**Tabla G.3 Diccionario de datos - cat_modulo**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_modulo | SERIAL | NO | PK | Identificador del módulo |
| id_programa | INTEGER | NO | FK → cat_programa(id_programa) ON DELETE CASCADE; UNIQUE (id_programa, nro_modulo) | Programa al que pertenece el módulo |
| nro_modulo | INTEGER | NO | UNIQUE (id_programa, nro_modulo) | Número de orden del módulo dentro del programa |
| nombre_modulo | VARCHAR(255) | NO | — | Nombre del módulo |
| horas_modulo | NUMERIC(6,2) | SÍ | DEFAULT 0 | Carga horaria del módulo |
| pago_docente_base | NUMERIC(10,2) | SÍ | DEFAULT 0 | Pago base al docente por dictar el módulo |

Índices: cat_modulo_pkey (id_modulo) [PK]; uq_cat_modulo_programa_nro (id_programa, nro_modulo) [único]

**Tabla G.4 Diccionario de datos - cat_docente**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_docente | SERIAL | NO | PK | Identificador del docente |
| nombre_completo | VARCHAR(200) | NO | UNIQUE | Nombre completo del docente |
| email | VARCHAR(150) | SÍ | — | Correo de contacto del docente |
| celular | VARCHAR(50) | SÍ | — | Teléfono celular del docente |
| grado_academico | VARCHAR(100) | SÍ | — | Grado académico del docente |
| tipo_docente | VARCHAR(50) | SÍ | DEFAULT 'TITULAR' | Tipo de docente: TITULAR, ADJUNTO, INVITADO |

Índices: cat_docente_nombre_completo_key (nombre_completo) [único]; cat_docente_pkey (id_docente) [PK]; idx_cat_doc_nombre (nombre_completo)

**Tabla G.5 Diccionario de datos - cat_escuela**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_escuela | SERIAL | NO | PK | Identificador de la escuela |
| nombre_escuela | VARCHAR(100) | NO | UNIQUE | Nombre de la escuela académica |
| sigla | VARCHAR(20) | SÍ | — | Sigla de la escuela |

Índices: cat_escuela_nombre_escuela_key (nombre_escuela) [único]; cat_escuela_pkey (id_escuela) [PK]

**Tabla G.6 Diccionario de datos - cat_tipo_programa**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_tipo_programa | SERIAL | NO | PK | Identificador del tipo de programa |
| nombre_tipo | VARCHAR(100) | NO | UNIQUE | Tipo de programa (Diplomado, Maestría, Especialidad, Curso, Curso Experto / Certificación, Formación Continua…) |

Índices: cat_tipo_programa_nombre_tipo_key (nombre_tipo) [único]; cat_tipo_programa_pkey (id_tipo_programa) [PK]

**Tabla G.7 Diccionario de datos - cat_modalidad**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_modalidad | SERIAL | NO | PK | Identificador de la modalidad |
| nombre_modalidad | VARCHAR(100) | NO | UNIQUE | Modalidad de dictado (Presencial, Virtual Sincrónica, Virtual Asincrónica, Semipresencial / Híbrida) |

Índices: cat_modalidad_nombre_modalidad_key (nombre_modalidad) [único]; cat_modalidad_pkey (id_modalidad) [PK]

**Tabla G.8 Diccionario de datos - cat_estado_academico**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_estado_academico | SERIAL | NO | PK | Identificador del estado académico |
| nombre_estado | VARCHAR(100) | NO | UNIQUE | Estado académico: INSCRITO, REGULAR_ACTIVO, CONCLUIDO_PENDIENTE_MONOGRAFIA, GRADUADO_TITULADO, REPROBADO, RETIRADO_ABANDONO |

Índices: cat_estado_academico_nombre_estado_key (nombre_estado) [único]; cat_estado_academico_pkey (id_estado_academico) [PK]

**Tabla G.9 Diccionario de datos - cat_estado_reprobado**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_estado_reprobado | SERIAL | NO | PK | Identificador del motivo de reprobación |
| nombre_detalle | VARCHAR(100) | NO | UNIQUE | Motivo: REPROBADO_POR_NOTA, REPROBADO_POR_ASISTENCIA, BAJA_POR_INCUMPLIMIENTO_PAGOS, REPROBADO_POR_PLAGIO_ACADEMICO |

Índices: cat_estado_reprobado_nombre_detalle_key (nombre_detalle) [único]; cat_estado_reprobado_pkey (id_estado_reprobado) [PK]

**Tabla G.10 Diccionario de datos - cat_estado_arca**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_estado_arca | SERIAL | NO | PK | Identificador del estado ARCA |
| nombre_arca | VARCHAR(100) | NO | UNIQUE | Estado del título: HOMOLOGADO_SISTEMA_NACIONAL, EN_TRAMITE_MINISTERIAL, NO_APLICA_FORMACION_CONTINUA, REGISTRO_ARCHIVADO |

Índices: cat_estado_arca_nombre_arca_key (nombre_arca) [único]; cat_estado_arca_pkey (id_estado_arca) [PK]

**Tabla G.11 Diccionario de datos - cat_tipo_cartera**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_cartera | SERIAL | NO | PK | Identificador del tramo de cartera |
| nombre_cartera | VARCHAR(100) | NO | UNIQUE | Tramo: VIGENTE_AL_DIA, MORA_PREVENTIVA, MORA_ADMINISTRATIVA, MORA_PREJUDICIAL, CARTERA_CASTIGADA_JUDICIAL |
| dias_mora_min | INTEGER | NO | — | Días de mora desde los que aplica el tramo |
| dias_mora_max | INTEGER | NO | — | Días de mora hasta los que aplica el tramo |
| descripcion | VARCHAR(255) | SÍ | — | Descripción del tramo |

Índices: cat_tipo_cartera_nombre_cartera_key (nombre_cartera) [único]; cat_tipo_cartera_pkey (id_cartera) [PK]

**Tabla G.12 Diccionario de datos - cat_concepto_financiero**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_concepto | SERIAL | NO | PK | Identificador del concepto |
| codigo_canonico | VARCHAR(50) | NO | UNIQUE (índice ix_cat_concepto_financiero_codigo_canonico) | Código canónico del concepto (FIN-CUOTA-01, FIN-MAT-01…) |
| nombre_canonico | VARCHAR(100) | NO | UNIQUE | Nombre canónico: CUOTA, MATRICULA, CONTADO, REINCORPORACION, DESCUENTO, MORA, DEUDA_TOTAL, TOTAL_PAGADO, EGRESO_REAL, EGRESO_ANTERIOR, HONORARIO_DOCENTE, TECHO_CONVENIO, META_PROGRAMAS, META_TECHOS |
| tipo_movimiento | VARCHAR(30) | NO | — | Tipo de movimiento: INGRESO, EGRESO, SALDO, AJUSTE |
| categoria_contable | VARCHAR(50) | SÍ | — | Categoría contable: COBRANZA, OPERATIVO, DOCENTE, CONVENIO, METAS |
| descripcion | VARCHAR(255) | SÍ | — | Descripción del concepto |

Índices: cat_concepto_financiero_nombre_canonico_key (nombre_canonico) [único]; cat_concepto_financiero_pkey (id_concepto) [PK]; ix_cat_concepto_financiero_codigo_canonico (codigo_canonico) [único]; ix_cat_concepto_financiero_id_concepto (id_concepto)

**Tabla G.13 Diccionario de datos - cat_historico_equivalencia**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_equivalencia | SERIAL | NO | PK | Identificador de la equivalencia |
| id_concepto | INTEGER | NO | FK → cat_concepto_financiero(id_concepto) ON DELETE CASCADE | Concepto canónico equivalente |
| termino_origen | VARCHAR(150) | NO | — | Término usado en las planillas que equivale al concepto |
| periodo_historico | VARCHAR(50) | SÍ | — | Periodo en que se usó el término (HISTORICO, 2023-2025, 2024-2025) |
| confianza_mapeo | NUMERIC(5,4) | SÍ | — | Confianza de la equivalencia (0–1) |
| fuente_referencia | VARCHAR(100) | SÍ | — | Planilla de origen del término (BD Cobranzas.xlsx, BD Egresos.xlsx, BD Techos.xlsx, EJECUTADO VS META.xlsx) |

Índices: cat_historico_equivalencia_pkey (id_equivalencia) [PK]; ix_cat_historico_equivalencia_id_equivalencia (id_equivalencia); ix_cat_historico_equivalencia_termino_origen (termino_origen)

**Tabla G.14 Diccionario de datos - cat_etiqueta_clasificacion**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_etiqueta | SERIAL | NO | PK | Identificador de la etiqueta |
| categoria | VARCHAR(50) | NO | — | Categoría del documento: academico, financiero, comercial |
| subtipo | VARCHAR(50) | SÍ | — | Subtipo de documento (ACTAS_NOTAS, COBRANZAS, EVALUACION_DOCENTE…) |
| palabra_clave | VARCHAR(100) | NO | UNIQUE | Palabra clave que identifica la categoría o subtipo |
| ambito | VARCHAR(30) | SÍ | — | Dónde se busca la palabra: ARCHIVO, HOJA, CONTENIDO, AMBOS |
| peso | INTEGER | SÍ | — | Peso de la palabra en el puntaje de clasificación |

Índices: cat_etiqueta_clasificacion_palabra_clave_key (palabra_clave) [único]; cat_etiqueta_clasificacion_pkey (id_etiqueta) [PK]; ix_cat_etiqueta_clasificacion_categoria (categoria); ix_cat_etiqueta_clasificacion_id_etiqueta (id_etiqueta); ix_cat_etiqueta_clasificacion_subtipo (subtipo)

**Tabla G.15 Diccionario de datos - cat_mapeo_columna**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_mapeo | SERIAL | NO | PK | Identificador del mapeo |
| campo_canonico | VARCHAR(50) | NO | — | Campo canónico (ESTUDIANTE, CI, MONTO, NOTA…) |
| alias_columna | VARCHAR(100) | NO | UNIQUE | Encabezado alternativo con el que el campo aparece en las planillas |
| tipo_entidad | VARCHAR(50) | NO | — | Tipo de entidad NER al que corresponde el campo |

Índices: cat_mapeo_columna_alias_columna_key (alias_columna) [único]; cat_mapeo_columna_pkey (id_mapeo) [PK]; ix_cat_mapeo_columna_campo_canonico (campo_canonico); ix_cat_mapeo_columna_id_mapeo (id_mapeo)

**Tabla G.16 Diccionario de datos - cat_guia_texto_plano**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_guia | SERIAL | NO | PK | Identificador de la guía |
| subtipo | VARCHAR(50) | NO | UNIQUE | Subtipo de documento al que aplica (ACTAS_NOTAS, COBRANZAS…) |
| descripcion | VARCHAR(255) | SÍ | — | Descripción de la guía |
| plantilla_texto | TEXT | NO | — | Plantilla para convertir una fila a texto plano |
| campos_requeridos | TEXT | SÍ | — | Campos obligatorios de la plantilla, separados por coma |
| prioridad | INTEGER | SÍ | — | Prioridad de la plantilla frente a otras del mismo subtipo |

Índices: cat_guia_texto_plano_pkey (id_guia) [PK]; cat_guia_texto_plano_subtipo_key (subtipo) [único]; ix_cat_guia_texto_plano_id_guia (id_guia)

**Tabla G.17 Diccionario de datos - ref_metas_gestion**

| Campo | Tipo | Nulo | Restricción / defecto | Descripción |
|---|---|---|---|---|
| id_meta | SERIAL | NO | PK | Identificador de la meta |
| gestion | INTEGER | NO | UNIQUE (gestion, mes, categoria) | Año de la meta |
| mes | INTEGER | NO | UNIQUE (gestion, mes, categoria) | Mes de la meta (1 a 12) |
| categoria | VARCHAR(100) | NO | UNIQUE (gestion, mes, categoria) | Línea de negocio de la meta (POSTGRADO_REGULAR, CONVENIOS_CORPORATIVOS) |
| monto_meta_ingreso | NUMERIC(14,2) | SÍ | DEFAULT 0 | Meta de ingreso del mes |
| monto_ejecutado | NUMERIC(14,2) | SÍ | DEFAULT 0 | Ingreso ejecutado en el mes |
| ebitda_meta_pct | NUMERIC(6,4) | SÍ | — | Meta de margen EBITDA como fracción (0,30 = 30 %) |
| ebitda_ejecutado_pct | NUMERIC(6,4) | SÍ | — | Margen EBITDA ejecutado como fracción |

Índices: ref_metas_gestion_pkey (id_meta) [PK]; uq_ref_metas_gestion_mes_cat (gestion, mes, categoria) [único]

**Tabla G.18 Relaciones**

| Tabla origen | Columna FK | Tabla destino | Columna | ON DELETE |
|---|---|---|---|---|
| cat_historico_equivalencia | id_concepto | cat_concepto_financiero | id_concepto | CASCADE |
| cat_modulo | id_programa | cat_programa | id_programa | CASCADE |
| cat_programa | id_escuela | cat_escuela | id_escuela | RESTRICT |
| cat_programa | id_modalidad | cat_modalidad | id_modalidad | RESTRICT |
| cat_programa | id_tipo_programa | cat_tipo_programa | id_tipo_programa | RESTRICT |

## Columnas por documentar

Columnas sin comentario en el DDL ni uso claro en el código:

| Apéndice | Tabla | Columna |
|---|---|---|
| F | fact_cobranzas_proyectadas | monto_esperado |
| F | fact_cobranzas_proyectadas | estado_pago |
| F | dim_estudiante | genero |
| F | dim_estudiante | edad |
| F | dim_estudiante | ocupacion |
| F | dim_estudiante | estado_civil |
| F | cat_institucion | tipo_escala_default |
| F | stg_entidad_no_resuelta | version |
| F | log_inconsistencias | tipo_regla |
| F | log_inconsistencias | severidad |
| F | log_inconsistencias | estado_resolucion |

## Notas de verificación

### Diferencias entre el DDL del repositorio y `giragroup_db` en ejecución

Ninguna en las 27 tablas del Apéndice F. La base en ejecución la habían levantado la migración `001_initial_constellation_baseline.sql` y `Base.metadata.create_all`, y difería del DDL en 95 puntos (entre otros: `dim_tiempo` admitía NULL y no tenía UNIQUE en `fecha`, faltaban DEFAULT y acciones ON DELETE, y el índice `uq_fact_aca_est_mod` duplicaba a `uq_fact_rendimiento_estudiante_modulo`). La migración `005_alinear_esquema_con_ddl.sql`, que la API aplica al arrancar (también al restaurar un respaldo anterior), la alinea; el DDL dejó de declarar `uq_fact_aca_est_mod` y los índices que repetían una PK o UNIQUE, y ahora incluye `cat_docente` y `cat_modulo` con las FK que las referencian.

La base en ejecución tiene además 19 tablas que no forman parte del almacén y que el Apéndice F no incluye: `cat_alias`, `cat_alias_docente`, `cat_alias_financiero`, `cat_alias_modulo`, `cat_alias_programa`, `cat_concepto_financiero`, `cat_escuela`, `cat_estado_academico`, `cat_estado_arca`, `cat_estado_reprobado`, `cat_etiqueta_clasificacion`, `cat_guia_texto_plano`, `cat_historico_equivalencia`, `cat_mapeo_columna`, `cat_modalidad`, `cat_programa`, `cat_tipo_cartera`, `cat_tipo_programa` y `ref_metas_gestion`. Las crean la migración `002_beto_ner_governance_schema.sql` y los modelos ORM de `backend/models/catalogos.py` al arrancar la API.

### Diferencias entre `db/schema_catalogos.sql` y `giragroup_catalog_db` en ejecución

El Apéndice G documenta la base en ejecución. El archivo define dos tablas que la base no tiene: `cat_categoria_financiera` y `stg_entidad_no_resuelta`. En las tablas comunes, la base en ejecución no tiene:

- `cat_concepto_financiero`: UNIQUE en `codigo_canonico` ni los índices `idx_cat_concepto_codigo` e `idx_cat_concepto_tipo`; tiene `ix_cat_concepto_financiero_codigo_canonico` (no único).
- `cat_etiqueta_clasificacion`: DEFAULT 'AMBOS' en `ambito`, DEFAULT 1 en `peso` ni los índices `idx_cat_etiq_cat` e `idx_cat_etiq_sub` (tiene sus equivalentes `ix_…`).
- `cat_guia_texto_plano`: DEFAULT 1 en `prioridad`.
- `cat_historico_equivalencia`: DEFAULT 'TODOS' en `periodo_historico`, DEFAULT 0.9500 en `confianza_mapeo` ni los índices `idx_cat_equiv_concepto` e `idx_cat_equiv_termino`; la FK `id_concepto` queda sin índice.
- `cat_mapeo_columna`: el índice `idx_cat_map_campo` (tiene `ix_cat_mapeo_columna_campo_canonico`).

