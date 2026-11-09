BEGIN;

-- 011: elimina de giragroup_db las tablas con 0 filas y sin consulta en el código (copias vacías de catálogos que
-- se sirven desde giragroup_catalog_db): cat_alias, cat_alias_{docente,financiero,modulo,programa}, cat_docente, cat_tipo_cartera.
-- Inventario y criterio: scripts/inventario_tablas.py -> docs/evidencias/inventario_tablas.json
ALTER TABLE IF EXISTS public.dim_docente DROP COLUMN IF EXISTS id_cat_docente;
DROP TABLE IF EXISTS public.cat_alias_docente;
DROP TABLE IF EXISTS public.cat_alias_financiero;
DROP TABLE IF EXISTS public.cat_alias_modulo;
DROP TABLE IF EXISTS public.cat_alias_programa;
DROP TABLE IF EXISTS public.cat_alias;
DROP TABLE IF EXISTS public.cat_docente;
DROP TABLE IF EXISTS public.cat_tipo_cartera;

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('011_eliminar_tablas_sin_uso.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
