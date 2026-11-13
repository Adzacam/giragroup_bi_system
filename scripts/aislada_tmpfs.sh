#!/bin/sh
# PostgreSQL aislada en tmpfs para pruebas y mediciones. Nunca toca el snapshot ni la base viva: solo LEE el snapshot (pg_dump).
#   sh scripts/aislada_tmpfs.sh up          crea el contenedor beto_pg_tmpfs (127.0.0.1:55432) y restaura giragroup_db desde el snapshot
#   sh scripts/aislada_tmpfs.sh vacio       crea la plantilla dw_vacio (snapshot + DW vaciado + migraciones 014 y 015)
#   sh scripts/aislada_tmpfs.sh clon <db>   crea <db> desde dw_vacio (una por corrida)
#   sh scripts/aislada_tmpfs.sh down        borra el contenedor
# URL desde el host:      postgresql://giragroup_user:tmpfs_local@127.0.0.1:55432/<db>
# Catálogo:              postgresql://giragroup_user:tmpfs_local@127.0.0.1:55432/catalogo_copia
# URL desde contenedores: postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/<db>   (red giragroup_bi_system_default)
set -e
export MSYS_NO_PATHCONV=1
SNAPSHOT="${SNAPSHOT:-snapshot_dw_20261110_1201}"
RED="${RED:-giragroup_bi_system_default}"
PSQL="docker exec beto_pg_tmpfs psql -U giragroup_user -q -v ON_ERROR_STOP=1"
TRUNC="TRUNCATE TABLE public.fact_rendimiento_academico, public.fact_situacion_financiera, public.fact_evaluacion_docente, public.fact_marketing, public.fact_rentabilidad, public.fact_forecast, public.fact_cobranzas_proyectadas, public.stg_entidad_no_resuelta, public.staging_registros_crudos, public.log_pipeline_ingesta, public.log_inconsistencias, public.log_auditoria_nlp, public.dim_origen_documental, public.lote, public.dataops_tarea RESTART IDENTITY CASCADE"

case "$1" in
  up)
    docker rm -f beto_pg_tmpfs >/dev/null 2>&1 || true
    docker run -d --name beto_pg_tmpfs --tmpfs /var/lib/postgresql/data:rw,size=3g -e POSTGRES_USER=giragroup_user \
      -e POSTGRES_PASSWORD=tmpfs_local -e POSTGRES_DB=postgres -p 127.0.0.1:55432:5432 postgres:16-alpine >/dev/null
    docker network connect "$RED" beto_pg_tmpfs
    until docker exec beto_pg_tmpfs pg_isready -U giragroup_user >/dev/null 2>&1; do sleep 2; done
    $PSQL -d postgres -c "create database giragroup_db"
    U=$(docker exec giragroup_db printenv POSTGRES_USER)
    docker exec giragroup_db pg_dump -U "$U" -d "$SNAPSHOT" --no-owner --no-privileges | docker exec -i beto_pg_tmpfs psql -U giragroup_user -d giragroup_db -q >/dev/null 2>&1
    $PSQL -d giragroup_db -Atc "select 'fact_rendimiento_academico', count(*) from fact_rendimiento_academico"
    # copia del catálogo institucional (solo lectura del original), para que ninguna prueba toque catalog_db
    CU=$(docker exec giragroup_catalog_db printenv POSTGRES_USER); CD=$(docker exec giragroup_catalog_db printenv POSTGRES_DB)
    $PSQL -d postgres -c "create database catalogo_copia"
    docker exec giragroup_catalog_db pg_dump -U "$CU" -d "$CD" --no-owner --no-privileges | docker exec -i beto_pg_tmpfs psql -U giragroup_user -d catalogo_copia -q >/dev/null 2>&1
    ;;
  vacio)
    $PSQL -d postgres -c "drop database if exists dw_vacio" -c "create database dw_vacio template giragroup_db"
    $PSQL -d dw_vacio -c "$TRUNC"
    for m in 014_conversion_captacion_comprobable.sql 015_cache_beto_entidades.sql; do
      [ -f "backend/scripts/migrations/$m" ] || continue
      docker cp "backend/scripts/migrations/$m" beto_pg_tmpfs:/tmp/m.sql
      $PSQL -d dw_vacio -f /tmp/m.sql >/dev/null 2>&1 || true
    done
    ;;
  clon)
    $PSQL -d postgres -c "drop database if exists $2" -c "create database $2 template dw_vacio"
    ;;
  down)
    docker rm -f beto_pg_tmpfs
    ;;
  *) echo "uso: $0 up|vacio|clon <db>|down"; exit 2 ;;
esac
