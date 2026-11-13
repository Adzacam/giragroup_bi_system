-- PROPUESTA: NO EJECUTAR sin aprobación. Corrige las inscripciones triplicadas de giragroup_db usando el snapshot como referencia.
-- Ver docs/propuestas/propuesta-correccion-inscripciones.md. Se ejecuta con psql sobre giragroup_db, con la API detenida.
--
-- Paso previo (fuera de este script): exportar la referencia desde el snapshot.
--   psql -d snapshot_dw_20261110_1201 -c "\copy (SELECT * FROM fact_marketing) TO 'mkt_base.tsv'"
--   psql -d snapshot_dw_20261110_1201 -c "\copy (SELECT id_modulo FROM dim_modulo) TO 'mod_base.tsv'"
--   psql -d snapshot_dw_20261110_1201 -c "\copy (SELECT id_estudiante FROM dim_estudiante) TO 'est_base.tsv'"

BEGIN;

CREATE SCHEMA respaldo_correccion_20261112;
-- El snapshot es anterior a la migración 014: no tiene las columnas de captación
CREATE TABLE respaldo_correccion_20261112.mkt_base (
  id_hecho_mkt integer, id_modulo integer, id_tiempo integer, leads integer, reservas integer, inscritos integer, costo_programa numeric);
CREATE TABLE respaldo_correccion_20261112.mod_base (id_modulo integer);
CREATE TABLE respaldo_correccion_20261112.est_base (id_estudiante integer);
\copy respaldo_correccion_20261112.mkt_base FROM 'mkt_base.tsv'
\copy respaldo_correccion_20261112.mod_base FROM 'mod_base.tsv'
\copy respaldo_correccion_20261112.est_base FROM 'est_base.tsv'

-- Guardas: la base debe tener exactamente el estado medido
DO $$
BEGIN
  IF (SELECT count(*) FROM public.fact_marketing) <> 15257
     OR (SELECT sum(inscritos) FROM public.fact_marketing) <> 45568
     OR (SELECT count(*) FROM public.dim_modulo) <> 4211
     OR (SELECT count(*) FROM respaldo_correccion_20261112.mkt_base) <> 8946
     OR (SELECT sum(inscritos) FROM respaldo_correccion_20261112.mkt_base) <> 15196 THEN
    RAISE EXCEPTION 'La base no coincide con el estado medido; no se aplica ningún cambio';
  END IF;
END $$;

-- 1. Respaldo de lo que se va a tocar
CREATE TABLE respaldo_correccion_20261112.fact_marketing AS SELECT * FROM public.fact_marketing;
CREATE TABLE respaldo_correccion_20261112.dim_modulo AS
  SELECT * FROM public.dim_modulo WHERE id_modulo NOT IN (SELECT id_modulo FROM respaldo_correccion_20261112.mod_base);
CREATE TABLE respaldo_correccion_20261112.dim_estudiante AS
  SELECT * FROM public.dim_estudiante WHERE id_estudiante NOT IN (SELECT id_estudiante FROM respaldo_correccion_20261112.est_base);
CREATE TABLE respaldo_correccion_20261112.fact_rentabilidad AS SELECT * FROM public.fact_rentabilidad WHERE id_documento = 18;

-- 2. Restaurar los contadores de las filas que cambiaron
UPDATE public.fact_marketing f
   SET leads = b.leads, reservas = b.reservas, inscritos = b.inscritos, costo_programa = b.costo_programa,
       leads_captacion = NULL, inscritos_captacion = NULL
  FROM respaldo_correccion_20261112.mkt_base b
 WHERE b.id_hecho_mkt = f.id_hecho_mkt
   AND (f.leads, f.reservas, f.inscritos) IS DISTINCT FROM (b.leads, b.reservas, b.inscritos);

-- 3. Eliminar las filas de marketing que no existían en la referencia
DELETE FROM public.fact_marketing
 WHERE id_hecho_mkt NOT IN (SELECT id_hecho_mkt FROM respaldo_correccion_20261112.mkt_base);

-- 4. Eliminar los módulos nuevos que ya no referencia ninguna tabla
DELETE FROM public.dim_modulo m
 WHERE m.id_modulo NOT IN (SELECT id_modulo FROM respaldo_correccion_20261112.mod_base)
   AND NOT EXISTS (SELECT 1 FROM public.fact_marketing x WHERE x.id_modulo = m.id_modulo)
   AND NOT EXISTS (SELECT 1 FROM public.fact_rendimiento_academico x WHERE x.id_modulo = m.id_modulo)
   AND NOT EXISTS (SELECT 1 FROM public.fact_situacion_financiera x WHERE x.id_modulo = m.id_modulo)
   AND NOT EXISTS (SELECT 1 FROM public.fact_evaluacion_docente x WHERE x.id_modulo = m.id_modulo)
   AND NOT EXISTS (SELECT 1 FROM public.fact_rentabilidad x WHERE x.id_modulo = m.id_modulo)
   AND NOT EXISTS (SELECT 1 FROM public.fact_costo_programa x WHERE x.id_modulo = m.id_modulo)
   AND NOT EXISTS (SELECT 1 FROM public.fact_techo_convenio x WHERE x.id_modulo = m.id_modulo)
   AND NOT EXISTS (SELECT 1 FROM public.bridge_modulo_docente x WHERE x.id_modulo = m.id_modulo);

-- 5. Eliminar el estudiante nuevo si no tiene hechos
DELETE FROM public.dim_estudiante e
 WHERE e.id_estudiante NOT IN (SELECT id_estudiante FROM respaldo_correccion_20261112.est_base)
   AND NOT EXISTS (SELECT 1 FROM public.fact_rendimiento_academico x WHERE x.id_estudiante = e.id_estudiante)
   AND NOT EXISTS (SELECT 1 FROM public.fact_situacion_financiera x WHERE x.id_estudiante = e.id_estudiante)
   AND NOT EXISTS (SELECT 1 FROM public.fact_evaluacion_docente x WHERE x.id_estudiante = e.id_estudiante);

-- 6. Reapuntar rentabilidad al documento original (mismo contenido, mismo archivo)
UPDATE public.fact_rentabilidad SET id_documento = 15 WHERE id_documento = 18;

-- Comprobaciones finales: si alguna falla, la transacción se revierte
DO $$
BEGIN
  IF (SELECT count(*) FROM public.fact_marketing) <> 8946
     OR (SELECT sum(inscritos) FROM public.fact_marketing) <> 15196
     OR (SELECT count(*) FROM public.dim_modulo) <> 3585
     OR (SELECT count(*) FROM public.dim_estudiante) <> 14078
     OR (SELECT count(*) FROM public.fact_rentabilidad) <> 108
     OR (SELECT count(*) FROM public.fact_rentabilidad WHERE id_documento IN (17, 18, 19)) <> 0 THEN
    RAISE EXCEPTION 'Las comprobaciones finales no coinciden; se revierte la transacción';
  END IF;
END $$;

COMMIT;
-- Reversión: restaurar desde el esquema respaldo_correccion_20261112 (tablas fact_marketing, dim_modulo, dim_estudiante, fact_rentabilidad).
