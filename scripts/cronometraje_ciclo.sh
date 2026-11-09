#!/bin/sh
# Modo cronometraje: restaura un clon de giragroup_db, ejecuta el ciclo mensual completo, deja la bandeja filtrada a los grupos de ese ciclo
# (documentos nuevos) y simula la revisión. Imprime el tiempo de máquina y el número de grupos; el JSON con inicio/fin de cada aprobación queda
# en docs/evidencias/cronometraje_aprobaciones.json (eventos simulados) y cronometraje_servidor.jsonl (lo que registró el servidor).
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."
docker stop giragroup_api giragroup_pipeline >/dev/null
docker exec giragroup_db psql -U giragroup_user -d postgres -c "drop database if exists clon_crono" -c "create database clon_crono template giragroup_db" >/dev/null
docker start giragroup_pipeline giragroup_api >/dev/null
sleep 40
docker cp scripts/medir_ciclo_mensual.py giragroup_api:/app/scripts/; docker cp scripts/ciclo_completo.py giragroup_api:/app/scripts/; docker cp scripts/simular_revision.py giragroup_api:/app/scripts/
ID_MIN=$(docker exec giragroup_db psql -U giragroup_user -d clon_crono -At -c "select coalesce(max(id_documento),0) from dim_origen_documental")
docker exec giragroup_api sh -c "cd /app && rm -f /tmp/crono.jsonl && CRONOMETRAJE_LOG=/tmp/crono.jsonl CICLO_FILAS_SIN_FECHA=0 CICLO_SLICES=/tmp/slices_completo DATABASE_URL=\$(echo \$DATABASE_URL | sed 's#/giragroup_db\$#/clon_crono#') PYTHONPATH=/app:/app/scripts python scripts/ciclo_completo.py /tmp/crono_ciclo.json 2026-03 > /tmp/crono_ciclo.log 2>&1"
docker exec giragroup_api sh -c "cd /app && CRONOMETRAJE_LOG=/tmp/crono.jsonl DATABASE_URL=\$(echo \$DATABASE_URL | sed 's#/giragroup_db\$#/clon_crono#') PYTHONPATH=/app:/app/scripts ID_MIN=$ID_MIN python scripts/simular_revision.py /tmp/crono_rev.json 2>&1 | grep '^{'"
docker cp giragroup_api:/tmp/crono_ciclo.json docs/evidencias/cronometraje_ciclo.json
docker cp giragroup_api:/tmp/crono_rev.json docs/evidencias/cronometraje_aprobaciones.json
docker cp giragroup_api:/tmp/crono.jsonl docs/evidencias/cronometraje_servidor.jsonl
python3 - <<'PY' 2>/dev/null || python - <<'PY2'
import json
c = json.load(open("docs/evidencias/cronometraje_ciclo.json", encoding="utf-8"))
print("TIEMPO DE MAQUINA DEL CICLO:", c["tiempo_total_s"], "s")
PY
import json
c = json.load(open("docs/evidencias/cronometraje_ciclo.json", encoding="utf-8"))
print("TIEMPO DE MAQUINA DEL CICLO:", c["tiempo_total_s"], "s")
PY2
