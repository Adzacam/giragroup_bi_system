-- Migración del catálogo (giragroup_catalog_db), ronda 8: se elimina cat_docente.
-- Motivo: las personas (docentes) se resuelven contra dim_docente (CI exacta -> RapidFuzz -> HITL), nunca contra este catálogo;
-- ninguna consulta del código la lee y contenía 735 nombres sin datos de contacto. En giragroup_db se eliminó con la migración 011.
DROP TABLE IF EXISTS public.cat_docente;
