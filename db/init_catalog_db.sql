-- Crear la base de datos de catálogos si no existe
SELECT 'CREATE DATABASE giragroup_catalog_db OWNER giragroup_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'giragroup_catalog_db')\gexec
