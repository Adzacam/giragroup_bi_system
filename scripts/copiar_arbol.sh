#!/bin/sh
# Copia el árbol de trabajo (backend + pipeline, sin .venv ni cachés) a /tmp/<nombre> de giragroup_api y lo deja listo para el flujo aislado.
#   sh scripts/copiar_arbol.sh <nombre>        → después: sh scripts/flujo_aislada.sh /tmp/<nombre> <db> <salida.json>
set -e
export MSYS_NO_PATHCONV=1
N="$1"
docker exec giragroup_api sh -c "rm -rf /tmp/$N && mkdir -p /tmp/$N"
tar --exclude=.venv --exclude=__pycache__ --exclude='*.pyc' --exclude=uploads --exclude='C:' -cf - backend pipeline | docker exec -i giragroup_api tar -x -C "/tmp/$N"
docker exec giragroup_api sh -c "ln -sfn /app/uploads /tmp/$N/uploads; sed -i 's#\"/app\", \"/app/pipeline\"#\"/tmp/$N\", \"/tmp/$N/pipeline\"#' /tmp/$N/backend/services/ingestion_service.py; grep -c /tmp/$N /tmp/$N/backend/services/ingestion_service.py"
