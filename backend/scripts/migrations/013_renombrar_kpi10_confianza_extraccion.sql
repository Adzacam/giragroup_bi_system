BEGIN;
-- 013: KPI-10 mide la confianza media de la extracción (reglas y BETO), no solo la del modelo BETO.
UPDATE bi.ref_kpi
   SET nombre = 'Confianza media de extracción',
       descripcion = 'Confianza promedio de la extracción automática de calificaciones (reglas por encabezado y modelo BETO).'
 WHERE codigo = 'KPI-10' AND nombre <> 'Confianza media de extracción';
INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('013_renombrar_kpi10_confianza_extraccion.sql', now())
ON CONFLICT (version) DO NOTHING;
COMMIT;
