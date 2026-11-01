FROM postgres:16-alpine

ENV POSTGRES_DB=giragroup_catalog_db
ENV POSTGRES_USER=giragroup_user
ENV POSTGRES_PASSWORD=giragroup_secret_2026

# Copiar el DDL de tablas y el script de inserción para ejecución automática al iniciar
COPY db/schema_catalogos.sql /docker-entrypoint-initdb.d/01_schema_catalogos.sql
COPY db/seeds/seed_catalogos.sql /docker-entrypoint-initdb.d/02_seed_catalogos.sql

EXPOSE 5432
