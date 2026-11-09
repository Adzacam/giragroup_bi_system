#!/bin/sh
# Ronda 8, tarea 4: 3 corridas del ciclo completo con el código final, cada una sobre un clon restaurado de giragroup_db,
# seguidas de la revisión simulada de los grupos del ciclo. Salida: docs/evidencias/ciclo_r8_<n>.json y revision_r8_<n>.json
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."
for n in 1 2 3; do
  docker stop giragroup_api giragroup_pipeline >/dev/null
  docker exec giragroup_db psql -U giragroup_user -d postgres -c "drop database if exists clon_r8_$n" -c "create database clon_r8_$n template giragroup_db" >/dev/null
  docker start giragroup_pipeline giragroup_api >/dev/null
  sleep 40
  docker cp scripts/medir_ciclo_mensual.py giragroup_api:/app/scripts/; docker cp scripts/ciclo_completo.py giragroup_api:/app/scripts/; docker cp scripts/simular_revision.py giragroup_api:/app/scripts/
  ID_MIN=$(docker exec giragroup_db psql -U giragroup_user -d clon_r8_$n -At -c "select coalesce(max(id_documento),0) from dim_origen_documental")
  docker exec giragroup_api sh -c "cd /app && rm -f /tmp/r8_$n.json && CICLO_FILAS_SIN_FECHA=0 CICLO_SLICES=/tmp/slices_completo DATABASE_URL=\$(echo \$DATABASE_URL | sed 's#/giragroup_db\$#/clon_r8_$n#') PYTHONPATH=/app:/app/scripts python scripts/ciclo_completo.py /tmp/r8_$n.json 2026-03 > /tmp/r8_$n.log 2>&1"
  docker exec giragroup_api sh -c "cd /app && DATABASE_URL=\$(echo \$DATABASE_URL | sed 's#/giragroup_db\$#/clon_r8_$n#') PYTHONPATH=/app:/app/scripts ID_MIN=$ID_MIN python scripts/simular_revision.py /tmp/r8_rev_$n.json > /tmp/r8_rev_$n.log 2>&1"
  docker cp giragroup_api:/tmp/r8_$n.json docs/evidencias/ciclo_r8_$n.json
  docker cp giragroup_api:/tmp/r8_rev_$n.json docs/evidencias/revision_r8_$n.json
  docker exec giragroup_db psql -U giragroup_user -d postgres -c "drop database if exists clon_r8_$n" >/dev/null
done
echo listo
