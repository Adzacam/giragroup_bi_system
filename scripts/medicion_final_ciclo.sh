#!/bin/sh
# 3 corridas del ciclo completo, cada una sobre un clon restaurado de giragroup_db; tras cada corrida mide grupos y 'aprobar grupo'.
# Salida en el contenedor: /tmp/final_<n>.json y /tmp/grupos_<n>.json (copiar a docs/evidencias/).
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."
for n in 1 2 3; do
  docker stop giragroup_api giragroup_pipeline >/dev/null
  docker exec giragroup_db psql -U giragroup_user -d postgres -c "drop database if exists clon_f$n" -c "create database clon_f$n template giragroup_db" >/dev/null
  docker start giragroup_pipeline giragroup_api >/dev/null
  sleep 40
  docker cp scripts/medir_ciclo_mensual.py giragroup_api:/app/scripts/; docker cp scripts/ciclo_completo.py giragroup_api:/app/scripts/; docker cp scripts/medir_grupos_hitl.py giragroup_api:/app/scripts/
  docker exec giragroup_api sh -c "cd /app && rm -f /tmp/final_$n.json && CICLO_FILAS_SIN_FECHA=0 CICLO_SLICES=/tmp/slices_completo DATABASE_URL=\$(echo \$DATABASE_URL | sed 's#/giragroup_db\$#/clon_f$n#') PYTHONPATH=/app:/app/scripts python scripts/ciclo_completo.py /tmp/final_$n.json 2026-03 > /tmp/final_$n.log 2>&1"
  docker exec giragroup_api sh -c "cd /app && DATABASE_URL=\$(echo \$DATABASE_URL | sed 's#/giragroup_db\$#/clon_f$n#') PYTHONPATH=/app:/app/scripts ID_MIN=16 python scripts/medir_grupos_hitl.py /tmp/grupos_$n.json > /tmp/grupos_$n.log 2>&1"
  docker cp giragroup_api:/tmp/final_$n.json docs/evidencias/ciclo_completo_final_$n.json
  docker cp giragroup_api:/tmp/grupos_$n.json docs/evidencias/grupos_hitl_final_$n.json
done
echo listo
