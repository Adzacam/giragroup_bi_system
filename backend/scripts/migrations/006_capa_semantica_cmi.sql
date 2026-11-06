-- =============================================================================
-- 006 · Capa semántica del Cuadro de Mando Integral (esquema bi)
--
-- Fuente única de verdad del CMI: la SPA (GET /api/v1/cmi/*) y Power BI leen las mismas
-- vistas, así que valores, metas y semáforos coinciden en ambos. La configuración
-- (perspectivas, objetivos, metas y umbrales) vive en bi.ref_perspectiva y bi.ref_kpi y se
-- edita desde Ajustes > Configuración del CMI. Idempotente: el arranque la aplica si falta
-- y re-ejecutarla no pisa la configuración editada (ON CONFLICT DO NOTHING).
-- =============================================================================
BEGIN;

CREATE SCHEMA IF NOT EXISTS bi;

-- -----------------------------------------------------------------------------
-- 1. Perspectivas del CMI (Kaplan & Norton) con objetivo estratégico y peso
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bi.ref_perspectiva (
    codigo        VARCHAR(30)  PRIMARY KEY,
    nombre        VARCHAR(80)  NOT NULL,
    objetivo      VARCHAR(300) NOT NULL,
    pregunta      VARCHAR(200) NOT NULL,
    peso          NUMERIC(5,2) NOT NULL DEFAULT 25 CHECK (peso >= 0 AND peso <= 100),
    orden         SMALLINT     NOT NULL,
    activa        BOOLEAN      NOT NULL DEFAULT TRUE,
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_por VARCHAR(120)
);

INSERT INTO bi.ref_perspectiva (codigo, nombre, objetivo, pregunta, peso, orden) VALUES
 ('FINANCIERA', 'Financiera',
  'Asegurar la sostenibilidad financiera cumpliendo las metas de recaudación y controlando la cartera.',
  '¿Cómo debemos aparecer ante quienes financian la institución?', 30, 1),
 ('CLIENTES', 'Estudiantes y mercado',
  'Atraer, satisfacer y retener a los estudiantes y a las instituciones en convenio.',
  '¿Cómo nos perciben los estudiantes y las instituciones?', 25, 2),
 ('PROCESOS_INTERNOS', 'Procesos internos',
  'Procesar la información institucional con calidad, trazabilidad y mínima intervención manual.',
  '¿En qué procesos debemos ser excelentes?', 20, 3),
 ('APRENDIZAJE', 'Aprendizaje y crecimiento',
  'Elevar el rendimiento académico y la calidad docente como base del crecimiento.',
  '¿Cómo sostenemos la capacidad de mejorar y crecer?', 25, 4)
ON CONFLICT (codigo) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 2. Indicadores con meta y umbrales de semáforo
--    sentido = 'MAX' (más es mejor) | 'MIN' (menos es mejor)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bi.ref_kpi (
    codigo        VARCHAR(10)  PRIMARY KEY,
    perspectiva   VARCHAR(30)  NOT NULL REFERENCES bi.ref_perspectiva(codigo),
    nombre        VARCHAR(120) NOT NULL,
    descripcion   VARCHAR(300),
    unidad        VARCHAR(6)   NOT NULL CHECK (unidad IN ('PCT','BS','CANT','PTS')),
    sentido       VARCHAR(3)   NOT NULL CHECK (sentido IN ('MAX','MIN')),
    meta          NUMERIC(14,2),
    umbral_verde  NUMERIC(14,2),
    umbral_ambar  NUMERIC(14,2),
    peso          NUMERIC(5,2) NOT NULL DEFAULT 1 CHECK (peso >= 0),
    orden         SMALLINT     NOT NULL,
    activo        BOOLEAN      NOT NULL DEFAULT TRUE,
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_por VARCHAR(120)
);

INSERT INTO bi.ref_kpi (codigo, perspectiva, nombre, descripcion, unidad, sentido, meta, umbral_verde, umbral_ambar, orden) VALUES
 ('KPI-01','FINANCIERA','Ticket promedio por estudiante','Recaudación de la gestión dividida entre la matrícula efectiva.','BS','MAX',NULL,NULL,NULL,1),
 ('KPI-02','FINANCIERA','Cumplimiento de meta del último mes','Ingreso ejecutado frente a la meta del último mes con ejecución.','PCT','MAX',100,100,85,2),
 ('KPI-03','FINANCIERA','Cumplimiento de meta a la fecha','Ingreso ejecutado frente a la meta de los meses ya ejecutados.','PCT','MAX',100,100,85,3),
 ('KPI-13','FINANCIERA','Avance sobre la meta anual','Ingreso ejecutado frente a la meta de los doce meses de la gestión (informativo durante la gestión).','PCT','MAX',100,NULL,NULL,4),
 ('KPI-14','FINANCIERA','Brecha a la meta anual','Monto que falta recaudar para alcanzar la meta anual.','BS','MIN',0,NULL,NULL,5),
 ('KPI-12','FINANCIERA','Variación interanual de ingresos','Ingreso de la gestión frente a los mismos meses de la gestión anterior.','PCT','MAX',10,10,0,6),
 ('KPI-05','FINANCIERA','Estudiantes en mora','Estudiantes en mora o previsionables sobre el total con cartera.','PCT','MIN',10,10,20,7),
 ('KPI-15','FINANCIERA','Cartera vencida','Deuda en mora o previsionable sobre la deuda total.','PCT','MIN',10,10,20,8),
 ('KPI-04','FINANCIERA','Estudiantes con riesgo financiero','Estudiantes con dos o más cuotas impagas o cartera previsionable.','CANT','MIN',NULL,NULL,NULL,9),
 ('KPI-21','CLIENTES','Matrícula efectiva','Estudiantes distintos con calificaciones en la gestión.','CANT','MAX',NULL,NULL,NULL,10),
 ('KPI-22','CLIENTES','Inscritos por convenio','Estudiantes inscritos mediante convenios institucionales.','CANT','MAX',NULL,NULL,NULL,11),
 ('KPI-06','CLIENTES','Conversión de admisiones','Inscritos sobre leads de marketing.','PCT','MAX',10,10,7,12),
 ('KPI-20','CLIENTES','Satisfacción institucional','Puntaje medio de las preguntas institucionales de la evaluación.','PCT','MAX',85,85,75,13),
 ('KPI-16','CLIENTES','Tasa de deserción','Estudiantes con incumplimiento o inasistencia mayor al 30 %.','PCT','MIN',5,5,10,14),
 ('KPI-10','PROCESOS_INTERNOS','Confianza media del modelo BETO','Confianza promedio de la extracción automática de calificaciones.','PCT','MAX',85,85,75,15),
 ('KPI-11','PROCESOS_INTERNOS','Automatización directa','Registros consolidados sin revisión humana (confianza ≥ 85 %).','PCT','MAX',85,85,70,16),
 ('KPI-18','PROCESOS_INTERNOS','Pendientes de revisión humana','Entidades no resueltas que esperan revisión.','CANT','MIN',0,10,50,17),
 ('KPI-07','APRENDIZAJE','Promedio de calificaciones','Nota final promedio sobre 100.','PTS','MAX',75,75,70,18),
 ('KPI-08','APRENDIZAJE','Tasa de aprobación','Calificaciones con nota final ≥ 70.','PCT','MAX',85,85,75,19),
 ('KPI-19','APRENDIZAJE','Satisfacción con los docentes','Puntaje medio de las preguntas sobre el docente en la evaluación.','PCT','MAX',85,85,75,20),
 ('KPI-09','APRENDIZAJE','Estudiantes en riesgo académico','Estudiantes con promedio ≤ 70.','CANT','MIN',NULL,NULL,NULL,21),
 ('KPI-17','APRENDIZAJE','Estudiantes en prioridad crítica','Estudiantes que cumplen dos o más reglas de riesgo (académico, deserción, financiero).','CANT','MIN',NULL,NULL,NULL,22)
ON CONFLICT (codigo) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 3. Regla única de semáforo y su puntaje (la medida DAX [Semaforo] replica esta lógica)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION bi.fn_semaforo(valor NUMERIC, verde NUMERIC, ambar NUMERIC, sentido TEXT)
RETURNS TEXT LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE
        WHEN valor IS NULL OR verde IS NULL                          THEN 'SIN_UMBRAL'
        WHEN sentido = 'MAX' AND valor >= verde                      THEN 'VERDE'
        WHEN sentido = 'MAX' AND ambar IS NOT NULL AND valor >= ambar THEN 'AMBAR'
        WHEN sentido = 'MIN' AND valor <= verde                      THEN 'VERDE'
        WHEN sentido = 'MIN' AND ambar IS NOT NULL AND valor <= ambar THEN 'AMBAR'
        ELSE 'ROJO'
    END
$$;

-- VERDE 100 · AMBAR 60 · ROJO 20 · sin umbral no puntúa (NULL)
CREATE OR REPLACE FUNCTION bi.fn_puntaje(semaforo TEXT)
RETURNS NUMERIC LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE semaforo WHEN 'VERDE' THEN 100 WHEN 'AMBAR' THEN 60 WHEN 'ROJO' THEN 20 END::numeric
$$;

-- -----------------------------------------------------------------------------
-- 4. Ingresos vs meta por mes (página Financiera)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW bi.vw_metas_mensual AS
WITH base AS (
    SELECT dt.gestion, dt.mes, MIN(dt.nombre_mes) AS nombre_mes,
           dc.nombre_categoria AS categoria,
           SUM(fr.monto_ejecutado) AS ejecutado,
           SUM(fr.monto_meta)      AS meta
    FROM public.fact_rentabilidad fr
    JOIN public.dim_tiempo dt               ON dt.id_tiempo = fr.id_tiempo
    JOIN public.dim_categoria_financiera dc ON dc.id_categoria = fr.id_categoria
    WHERE dc.tipo = 'INGRESO'
    GROUP BY dt.gestion, dt.mes, dc.nombre_categoria
)
SELECT b.*,
       make_date(b.gestion, b.mes, 1)                                   AS fecha_mes,
       ROUND(100 * b.ejecutado / NULLIF(b.meta, 0), 2)                  AS avance_pct,
       LAG(b.ejecutado) OVER w                                          AS ejecutado_anio_ant
FROM base b
WINDOW w AS (PARTITION BY b.categoria, b.mes ORDER BY b.gestion);

-- -----------------------------------------------------------------------------
-- 5. Cartera por estado (página Financiera)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW bi.vw_cartera_estado AS
SELECT dt.gestion,
       COALESCE(sf.estado_cartera, 'Sin estado')   AS estado_cartera,
       COUNT(DISTINCT sf.id_estudiante)            AS n_estudiantes,
       SUM(sf.monto_deuda)                         AS deuda_bs,
       SUM(sf.monto_pagado)                        AS pagado_bs,
       SUM(sf.cuotas_impagas)                      AS cuotas_impagas
FROM public.fact_situacion_financiera sf
JOIN public.dim_tiempo dt ON dt.id_tiempo = sf.id_tiempo
GROUP BY dt.gestion, COALESCE(sf.estado_cartera, 'Sin estado');

-- -----------------------------------------------------------------------------
-- 6. Matriz de riesgo por estudiante y gestión (reglas A, D, F y prioridad K)
--    Cada hecho se agrega por separado (sin producto cartesiano). Sin PII.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW bi.vw_riesgo_estudiante AS
WITH aca AS (
    SELECT dt.gestion, ra.id_estudiante,
           AVG(ra.nota_final) AS prom_notas,
           MAX(GREATEST(COALESCE(ra.incumplimiento_actividades_pct, 0),
                        GREATEST(0, 100 - COALESCE(ra.asistencia_pct, 100)))) AS max_incumplimiento_pct
    FROM public.fact_rendimiento_academico ra
    JOIN public.dim_tiempo dt ON dt.id_tiempo = ra.id_tiempo
    GROUP BY dt.gestion, ra.id_estudiante
), fin AS (
    SELECT dt.gestion, sf.id_estudiante,
           SUM(sf.cuotas_impagas) AS total_cuotas_impagas,
           SUM(sf.monto_deuda)    AS deuda_total_bs
    FROM public.fact_situacion_financiera sf
    JOIN public.dim_tiempo dt ON dt.id_tiempo = sf.id_tiempo
    GROUP BY dt.gestion, sf.id_estudiante
), reglas AS (
    SELECT a.gestion, e.id_estudiante,
           COALESCE(NULLIF(e.programa_origen, ''), 'Programa general') AS programa,
           a.prom_notas, a.max_incumplimiento_pct,
           COALESCE(f.total_cuotas_impagas, 0) AS total_cuotas_impagas,
           COALESCE(f.deuda_total_bs, 0)       AS deuda_total_bs,
           (a.prom_notas <= 70.0)::int                        AS regla_a_academico,
           (a.max_incumplimiento_pct > 30.0)::int             AS regla_d_desercion,
           (COALESCE(f.total_cuotas_impagas, 0) >= 2)::int    AS regla_f_financiero
    FROM aca a
    JOIN public.dim_estudiante e ON e.id_estudiante = a.id_estudiante AND e.deprecado = FALSE
    LEFT JOIN fin f ON f.id_estudiante = a.id_estudiante AND f.gestion = a.gestion
)
SELECT r.*,
       COALESCE(r.regla_a_academico,0) + COALESCE(r.regla_d_desercion,0) + COALESCE(r.regla_f_financiero,0) AS k_reglas,
       CASE COALESCE(r.regla_a_academico,0) + COALESCE(r.regla_d_desercion,0) + COALESCE(r.regla_f_financiero,0)
            WHEN 0 THEN 'SIN_ALERTA' WHEN 1 THEN 'MODERADA' ELSE 'CRITICA' END AS nivel_prioridad
FROM reglas r;

-- -----------------------------------------------------------------------------
-- 7. Telemetría DataOps por documento (página Procesos internos)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW bi.vw_dataops_documento AS
SELECT d.id_documento, d.nombre_archivo, d.tipo_fuente, d.periodo,
       d.fecha_procesamiento::date                                        AS fecha,
       COUNT(ra.id_hecho_aca)                                             AS registros,
       ROUND(AVG(ra.nivel_confianza_ia) * 100, 2)                         AS confianza_media_pct,
       COUNT(*) FILTER (WHERE ra.nivel_confianza_ia >= 0.85)              AS consolidado_directo,
       COUNT(*) FILTER (WHERE ra.nivel_confianza_ia >= 0.60
                          AND ra.nivel_confianza_ia <  0.85)              AS revision_hitl,
       (SELECT COUNT(*) FROM public.stg_entidad_no_resuelta s
         WHERE s.id_documento = d.id_documento AND s.resuelto = FALSE)    AS pendientes_revision
FROM public.dim_origen_documental d
LEFT JOIN public.fact_rendimiento_academico ra ON ra.id_documento = d.id_documento
GROUP BY d.id_documento, d.nombre_archivo, d.tipo_fuente, d.periodo, d.fecha_procesamiento;

-- -----------------------------------------------------------------------------
-- 8. Valor de cada indicador por gestión
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW bi.vw_cmi_valores AS
WITH aca AS (
    SELECT dt.gestion, ra.id_estudiante, ra.nota_final, ra.nivel_confianza_ia,
           GREATEST(COALESCE(ra.incumplimiento_actividades_pct,0),
                    GREATEST(0, 100 - COALESCE(ra.asistencia_pct,100))) AS incumplimiento_ef
    FROM public.fact_rendimiento_academico ra
    JOIN public.dim_tiempo dt ON dt.id_tiempo = ra.id_tiempo
), fin AS (
    SELECT dt.gestion, sf.id_estudiante, sf.monto_pagado, sf.monto_deuda,
           sf.cuotas_impagas, sf.estado_cartera
    FROM public.fact_situacion_financiera sf
    JOIN public.dim_tiempo dt ON dt.id_tiempo = sf.id_tiempo
), rent AS (   -- ingresos por mes; un mes cuenta como ejecutado si tiene ingreso > 0
    SELECT dt.gestion, dt.mes,
           COALESCE(SUM(fr.monto_ejecutado), 0) AS ejecutado,
           COALESCE(SUM(fr.monto_meta), 0)      AS meta
    FROM public.fact_rentabilidad fr
    JOIN public.dim_tiempo dt               ON dt.id_tiempo = fr.id_tiempo
    JOIN public.dim_categoria_financiera dc ON dc.id_categoria = fr.id_categoria
    WHERE dc.tipo = 'INGRESO'
    GROUP BY dt.gestion, dt.mes
), rent_g AS (
    SELECT gestion,
           SUM(ejecutado)                               AS ejecutado,
           SUM(meta)                                    AS meta_anual,
           SUM(meta) FILTER (WHERE ejecutado > 0)       AS meta_a_la_fecha,
           MAX(mes)  FILTER (WHERE ejecutado > 0)       AS ultimo_mes
    FROM rent GROUP BY gestion
), ult_mes AS (
    SELECT r.gestion, 100.0 * r.ejecutado / NULLIF(r.meta, 0) AS cumpl_mes
    FROM rent r JOIN rent_g g ON g.gestion = r.gestion AND g.ultimo_mes = r.mes
), yoy AS (    -- solo meses ejecutados en la gestión actual: compara periodos equivalentes
    SELECT c.gestion, 100.0 * (SUM(c.ejecutado) / NULLIF(SUM(p.ejecutado), 0) - 1) AS var_pct
    FROM rent c
    JOIN rent p ON p.gestion = c.gestion - 1 AND p.mes = c.mes
    WHERE c.ejecutado > 0
    GROUP BY c.gestion
), aca_g AS (
    SELECT gestion,
           COUNT(DISTINCT id_estudiante)                                      AS matricula,
           AVG(nota_final)                                                    AS promedio,
           100.0 * COUNT(*) FILTER (WHERE nota_final >= 70) / NULLIF(COUNT(nota_final),0) AS aprobacion,
           AVG(nivel_confianza_ia) * 100                                      AS confianza,
           100.0 * COUNT(*) FILTER (WHERE nivel_confianza_ia >= 0.85)
                 / NULLIF(COUNT(nivel_confianza_ia),0)                        AS automatizacion,
           100.0 * COUNT(DISTINCT id_estudiante) FILTER (WHERE incumplimiento_ef > 30)
                 / NULLIF(COUNT(DISTINCT id_estudiante),0)                    AS desercion
    FROM aca GROUP BY gestion
), riesgo_g AS (
    SELECT gestion,
           COUNT(*) FILTER (WHERE regla_a_academico = 1) AS riesgo_aca,
           COUNT(*) FILTER (WHERE k_reglas >= 2)         AS criticos
    FROM bi.vw_riesgo_estudiante GROUP BY gestion
), fin_g AS (
    SELECT gestion,
           SUM(monto_pagado)                                                  AS recaudacion,
           COUNT(DISTINCT id_estudiante)                                      AS pagantes,
           COUNT(DISTINCT id_estudiante) FILTER (WHERE cuotas_impagas >= 2
                                   OR estado_cartera = 'Previsionable')       AS riesgo_fin,
           COUNT(DISTINCT id_estudiante) FILTER (WHERE estado_cartera = 'Vigente')               AS n_v,
           COUNT(DISTINCT id_estudiante) FILTER (WHERE estado_cartera IN ('Mora','En Mora'))     AS n_m,
           COUNT(DISTINCT id_estudiante) FILTER (WHERE estado_cartera = 'Previsionable')         AS n_p,
           100.0 * SUM(monto_deuda) FILTER (WHERE estado_cartera IN ('Mora','En Mora','Previsionable'))
                 / NULLIF(SUM(monto_deuda),0)                                 AS cartera_vencida
    FROM fin GROUP BY gestion
), mkt AS (
    SELECT dt.gestion, 100.0 * SUM(fm.inscritos) / NULLIF(SUM(fm.leads),0) AS conversion
    FROM public.fact_marketing fm JOIN public.dim_tiempo dt ON dt.id_tiempo = fm.id_tiempo
    WHERE fm.leads > 0 GROUP BY dt.gestion
), eval AS (
    SELECT dt.gestion,
           AVG(100.0 * ev.puntuacion / NULLIF(ev.escala_max,0)) FILTER (WHERE ev.tipo_pregunta = 'DOCENTE')       AS sat_docente,
           AVG(100.0 * ev.puntuacion / NULLIF(ev.escala_max,0)) FILTER (WHERE ev.tipo_pregunta = 'INSTITUCIONAL') AS sat_institucional
    FROM public.fact_evaluacion_docente ev JOIN public.dim_tiempo dt ON dt.id_tiempo = ev.id_tiempo
    GROUP BY dt.gestion
), convenio AS (
    SELECT gestion, SUM(n_inscritos) AS inscritos
    FROM public.fact_techo_convenio WHERE gestion IS NOT NULL GROUP BY gestion
), backlog AS (
    SELECT EXTRACT(YEAR FROM created_at)::int AS gestion, COUNT(*) AS n
    FROM public.stg_entidad_no_resuelta WHERE resuelto = FALSE
    GROUP BY 1
)
SELECT f.gestion, 'KPI-01'::varchar(10) AS codigo,
       f.recaudacion / NULLIF(COALESCE(NULLIF(a.matricula,0), f.pagantes),0) AS valor
  FROM fin_g f LEFT JOIN aca_g a USING (gestion)
UNION ALL SELECT gestion, 'KPI-02', cumpl_mes FROM ult_mes
UNION ALL SELECT gestion, 'KPI-03', 100.0 * ejecutado / NULLIF(meta_a_la_fecha,0) FROM rent_g
UNION ALL SELECT gestion, 'KPI-04', riesgo_fin FROM fin_g
UNION ALL SELECT gestion, 'KPI-05', 100.0 * (n_m + n_p) / NULLIF(n_v + n_m + n_p,0) FROM fin_g
UNION ALL SELECT gestion, 'KPI-06', conversion FROM mkt
UNION ALL SELECT gestion, 'KPI-07', promedio FROM aca_g
UNION ALL SELECT gestion, 'KPI-08', aprobacion FROM aca_g
UNION ALL SELECT gestion, 'KPI-09', riesgo_aca FROM riesgo_g
UNION ALL SELECT gestion, 'KPI-10', confianza FROM aca_g
UNION ALL SELECT gestion, 'KPI-11', automatizacion FROM aca_g
UNION ALL SELECT gestion, 'KPI-12', var_pct FROM yoy
UNION ALL SELECT gestion, 'KPI-13', 100.0 * ejecutado / NULLIF(meta_anual,0) FROM rent_g
UNION ALL SELECT gestion, 'KPI-14', GREATEST(meta_anual - ejecutado, 0) FROM rent_g WHERE meta_anual > 0
UNION ALL SELECT gestion, 'KPI-15', cartera_vencida FROM fin_g
UNION ALL SELECT gestion, 'KPI-16', desercion FROM aca_g
UNION ALL SELECT gestion, 'KPI-17', criticos FROM riesgo_g
UNION ALL SELECT gestion, 'KPI-18', n FROM backlog
UNION ALL SELECT gestion, 'KPI-19', sat_docente FROM eval
UNION ALL SELECT gestion, 'KPI-20', sat_institucional FROM eval
UNION ALL SELECT gestion, 'KPI-21', matricula FROM aca_g
UNION ALL SELECT gestion, 'KPI-22', inscritos FROM convenio;

-- Gestiones con al menos un indicador evaluable: con dato y con umbral (filtro de gestión en web y Power BI)
CREATE OR REPLACE VIEW bi.vw_cmi_gestiones AS
SELECT v.gestion, COUNT(*) AS indicadores_con_dato
FROM bi.vw_cmi_valores v
JOIN bi.ref_kpi k ON k.codigo = v.codigo AND k.activo
WHERE v.valor IS NOT NULL
GROUP BY v.gestion
HAVING COUNT(*) FILTER (WHERE k.umbral_verde IS NOT NULL) > 0;

-- -----------------------------------------------------------------------------
-- 9. Scorecard: una fila por gestión e indicador activo, con semáforo y tendencia
--    (cross join para que un indicador sin dato aparezca como «Sin dato», no desaparezca)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW bi.vw_cmi_scorecard AS
WITH grid AS (
    SELECT g.gestion, k.*
    FROM bi.vw_cmi_gestiones g
    CROSS JOIN bi.ref_kpi k
    JOIN bi.ref_perspectiva p ON p.codigo = k.perspectiva AND p.activa
    WHERE k.activo
), v AS (
    SELECT gr.*, ROUND(val.valor::numeric, 2) AS valor,
           ROUND(LAG(val.valor) OVER (PARTITION BY gr.codigo ORDER BY gr.gestion)::numeric, 2) AS valor_anterior
    FROM grid gr
    LEFT JOIN bi.vw_cmi_valores val ON val.gestion = gr.gestion AND val.codigo = gr.codigo
)
SELECT v.gestion, v.perspectiva, v.codigo, v.nombre, v.descripcion, v.unidad, v.sentido,
       v.valor, v.valor_anterior, v.valor - v.valor_anterior AS delta,
       v.meta, v.umbral_verde, v.umbral_ambar, v.peso, v.orden,
       bi.fn_semaforo(v.valor, v.umbral_verde, v.umbral_ambar, v.sentido)                    AS semaforo,
       bi.fn_puntaje(bi.fn_semaforo(v.valor, v.umbral_verde, v.umbral_ambar, v.sentido))     AS puntaje,
       CASE WHEN v.valor IS NULL OR v.valor_anterior IS NULL OR v.valor = v.valor_anterior THEN 'ESTABLE'
            WHEN (v.valor > v.valor_anterior) = (v.sentido = 'MAX') THEN 'MEJORA'
            ELSE 'EMPEORA' END                                                               AS tendencia
FROM v;

-- -----------------------------------------------------------------------------
-- 10. Índice por perspectiva (promedio ponderado del puntaje de sus indicadores con umbral)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW bi.vw_cmi_perspectiva AS
SELECT s.gestion, p.codigo AS perspectiva, p.nombre, p.objetivo, p.pregunta, p.peso, p.orden,
       COUNT(*)                                                     AS indicadores,
       COUNT(*) FILTER (WHERE s.semaforo = 'VERDE')                 AS verdes,
       COUNT(*) FILTER (WHERE s.semaforo = 'AMBAR')                 AS ambar,
       COUNT(*) FILTER (WHERE s.semaforo = 'ROJO')                  AS rojos,
       COUNT(*) FILTER (WHERE s.semaforo = 'SIN_UMBRAL')            AS sin_evaluar,
       ROUND(SUM(s.puntaje * s.peso) / NULLIF(SUM(s.peso) FILTER (WHERE s.puntaje IS NOT NULL), 0), 1) AS indice
FROM bi.vw_cmi_scorecard s
JOIN bi.ref_perspectiva p ON p.codigo = s.perspectiva
GROUP BY s.gestion, p.codigo, p.nombre, p.objetivo, p.pregunta, p.peso, p.orden;

-- Índice global ponderado por el peso de cada perspectiva
CREATE OR REPLACE VIEW bi.vw_cmi_global AS
SELECT gestion,
       ROUND(SUM(indice * peso) / NULLIF(SUM(peso) FILTER (WHERE indice IS NOT NULL), 0), 1) AS indice,
       SUM(verdes) AS verdes, SUM(ambar) AS ambar, SUM(rojos) AS rojos, SUM(sin_evaluar) AS sin_evaluar
FROM bi.vw_cmi_perspectiva
GROUP BY gestion;

-- -----------------------------------------------------------------------------
-- 11. Rol de solo lectura para Power BI (PoLP). La contraseña se asigna fuera del repo:
--     ALTER ROLE powerbi_reader PASSWORD '<secreto>';
--     Sin acceso a dim_estudiante (nombre, CI): la PII queda fuera del modelo Power BI.
-- -----------------------------------------------------------------------------
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'powerbi_reader') THEN
        CREATE ROLE powerbi_reader LOGIN;
    END IF;
    GRANT USAGE ON SCHEMA bi TO powerbi_reader;
    GRANT SELECT ON ALL TABLES IN SCHEMA bi TO powerbi_reader;
    ALTER DEFAULT PRIVILEGES IN SCHEMA bi GRANT SELECT ON TABLES TO powerbi_reader;
EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'Sin privilegio para crear powerbi_reader; crearlo con un superusuario.';
END $$;

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('006_capa_semantica_cmi.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
