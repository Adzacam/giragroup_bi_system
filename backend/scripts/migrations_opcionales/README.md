# Migraciones opcionales (fuera de la inicialización automática del DW)

Este directorio contiene scripts SQL operativos que **no** forman parte del esquema base de 50 tablas del Data Warehouse (`48 public.BASE TABLE + 2 bi.BASE TABLE + 9 bi.VIEW`) y **no** deben ejecutarse automáticamente en `run_migrations.py` ni en el arranque de la API.

- `015_cache_beto_entidades.sql`: crea `public.cache_beto_entidades`, una caché operativa auxiliar para las opciones `BETO_CASCADA_FINAL` (opción 1) y `BETO_ACUERDO_QC` (opción 2). Si alguna de esas opciones se enciende en tiempo de ejecución, `backend/services/beto_integracion.py` (`CacheEntidades._asegurar` / `DDL_CACHE`) crea la tabla al vuelo.
