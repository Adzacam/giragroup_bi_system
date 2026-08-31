#!/bin/bash
set -e

echo "Inicializando esquema de catálogos en giragroup_catalog_db..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "giragroup_catalog_db" <<-EOSQL
    \i /docker-entrypoint-initdb.d/schema_catalogos.sql
EOSQL
