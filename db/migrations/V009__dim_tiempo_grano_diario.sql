-- ==============================================================================
-- Migración V009: dim_tiempo con grano diario completo
--
-- Estado previo: 2 335 filas. 216 eran antiguas sin fecha:
--   * 108 de grano mensual con id AAAAMM (2020-2028).
--   * 108 con id AAAAMM01 (primer día del mes). 72 de ellas (2022-2027) bloqueaban la semilla
--     seed_dim_tiempo.sql por ON CONFLICT (id_tiempo) DO NOTHING, que dejaba esos días sin fecha.
--
-- 1. Completa fecha y atributos de calendario en toda fila con id AAAAMMDD válido.
-- 2. Re-apunta las FK que usen un id AAAAMM al primer día del mes (AAAAMM01), creándolo si falta,
--    y recién entonces elimina las filas AAAAMM. Las FK son ON DELETE CASCADE: borrarlas antes
--    eliminaría hechos.
-- Idempotente.
-- ==============================================================================

BEGIN;

-- 1. Atributos de calendario derivados del propio id (AAAAMMDD)
UPDATE public.dim_tiempo t SET
    fecha        = d.f,
    gestion      = EXTRACT(YEAR FROM d.f)::int,
    semestre     = CASE WHEN EXTRACT(MONTH FROM d.f) <= 6 THEN 1 ELSE 2 END,
    trimestre    = EXTRACT(QUARTER FROM d.f)::int,
    mes          = EXTRACT(MONTH FROM d.f)::int,
    nombre_mes   = (ARRAY['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto',
                          'Septiembre','Octubre','Noviembre','Diciembre'])[EXTRACT(MONTH FROM d.f)::int],
    semana_iso   = EXTRACT(WEEK FROM d.f)::int,
    dia_mes      = EXTRACT(DAY FROM d.f)::int,
    dia_semana   = EXTRACT(ISODOW FROM d.f)::int,
    nombre_dia   = (ARRAY['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'])[EXTRACT(ISODOW FROM d.f)::int],
    es_fin_semana = EXTRACT(ISODOW FROM d.f) >= 6,
    periodo_mes  = to_char(d.f, 'YYYY-MM')
FROM (
    SELECT id_tiempo, to_date(id_tiempo::text, 'YYYYMMDD') AS f
    FROM public.dim_tiempo
    WHERE id_tiempo >= 10000000 AND fecha IS NULL
) d
WHERE t.id_tiempo = d.id_tiempo;

-- 2a. Primer día del mes para cada id mensual que aún no lo tenga
INSERT INTO public.dim_tiempo (id_tiempo, gestion)
SELECT id_tiempo * 100 + 1, gestion
FROM public.dim_tiempo m
WHERE m.id_tiempo < 1000000
  AND NOT EXISTS (SELECT 1 FROM public.dim_tiempo x WHERE x.id_tiempo = m.id_tiempo * 100 + 1);

UPDATE public.dim_tiempo t SET
    fecha = to_date(t.id_tiempo::text, 'YYYYMMDD'),
    semestre = CASE WHEN EXTRACT(MONTH FROM to_date(t.id_tiempo::text, 'YYYYMMDD')) <= 6 THEN 1 ELSE 2 END,
    trimestre = EXTRACT(QUARTER FROM to_date(t.id_tiempo::text, 'YYYYMMDD'))::int,
    mes = EXTRACT(MONTH FROM to_date(t.id_tiempo::text, 'YYYYMMDD'))::int,
    dia_mes = 1,
    periodo_mes = to_char(to_date(t.id_tiempo::text, 'YYYYMMDD'), 'YYYY-MM')
WHERE t.id_tiempo >= 10000000 AND t.fecha IS NULL;

-- 2b. Re-apuntar todas las FK que referencian dim_tiempo y usan un id mensual
DO $$
DECLARE
    r RECORD;
    n BIGINT;
BEGIN
    FOR r IN
        SELECT tc.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu USING (constraint_name, table_schema)
        JOIN information_schema.constraint_column_usage ccu USING (constraint_name, table_schema)
        WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = 'dim_tiempo' AND tc.table_schema = 'public'
    LOOP
        EXECUTE format('UPDATE public.%I SET %I = %I * 100 + 1 WHERE %I < 1000000',
                       r.table_name, r.column_name, r.column_name, r.column_name);
        GET DIAGNOSTICS n = ROW_COUNT;
        IF n > 0 THEN
            RAISE NOTICE 'Re-apuntadas % filas de %.%', n, r.table_name, r.column_name;
        END IF;
    END LOOP;
END $$;

-- 2c. Sin referencias restantes, eliminar el grano mensual
DELETE FROM public.dim_tiempo WHERE id_tiempo < 1000000;

DO $$
DECLARE sin_fecha INT;
BEGIN
    SELECT count(*) INTO sin_fecha FROM public.dim_tiempo WHERE fecha IS NULL;
    IF sin_fecha > 0 THEN
        RAISE EXCEPTION 'dim_tiempo conserva % filas sin fecha', sin_fecha;
    END IF;
END $$;

COMMIT;
