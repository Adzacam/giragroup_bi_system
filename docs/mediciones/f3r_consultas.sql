-- Consultas de solo lectura sobre f3r_base (R3-1)
-- 1. Inventario completo de tablas base y vistas
SELECT table_schema, table_type, table_name
FROM information_schema.tables
WHERE table_schema IN ('public', 'bi')
ORDER BY table_schema, table_type, table_name;

-- 2. fk_estado (A/B/C) en tablas de hechos y dimensiones principales
SELECT 'fact_rendimiento_academico' AS tabla, fk_estado, count(*) AS filas FROM public.fact_rendimiento_academico GROUP BY fk_estado
UNION ALL
SELECT 'fact_situacion_financiera', fk_estado, count(*) FROM public.fact_situacion_financiera GROUP BY fk_estado
UNION ALL
SELECT 'dim_estudiante', fk_estado, count(*) FROM public.dim_estudiante GROUP BY fk_estado
UNION ALL
SELECT 'dim_docente', fk_estado, count(*) FROM public.dim_docente GROUP BY fk_estado
ORDER BY tabla, fk_estado;

-- 3. Staging de entidades no resueltas por motivo y estado resuelto
SELECT motivo, resuelto, count(*) AS filas
FROM public.stg_entidad_no_resuelta
GROUP BY motivo, resuelto
ORDER BY motivo, resuelto;

-- 4. Log de inconsistencias por regla_origen y tipo_regla
SELECT regla_origen, tipo_regla, count(*) AS filas
FROM public.log_inconsistencias
GROUP BY regla_origen, tipo_regla
ORDER BY filas DESC, regla_origen, tipo_regla;

-- 5. Rango y conteo de dim_tiempo
SELECT count(*) AS total_filas, min(fecha) AS fecha_min, max(fecha) AS fecha_max, min(gestion) AS gestion_min, max(gestion) AS gestion_max
FROM public.dim_tiempo;

-- 6. KPIs en bi.vw_cmi_valores
SELECT gestion, codigo, valor
FROM bi.vw_cmi_valores
WHERE codigo IN ('KPI-10', 'KPI-11', 'KPI-15', 'KPI-18')
ORDER BY gestion, codigo;
