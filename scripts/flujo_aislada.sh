#!/bin/sh
# Ejecuta el flujo DataOps de 10 archivos (pasos ①–③ y consolidación) sobre un clon de la PostgreSQL tmpfs aislada.
#   sh scripts/flujo_aislada.sh <arbol_codigo> <db> <salida.json>   [VARIABLES_DE_ENTORNO...]
# <arbol_codigo>: /app (árbol de trabajo montado) o /tmp/base (copia de un commit); las variables BETO_* se pasan por entorno.
# Requiere: scripts/aislada_tmpfs.sh up + vacio, y /tmp/flujo/scripts y /tmp/slices_flujo en giragroup_api (ver docs/auditoria).
set -e
export MSYS_NO_PATHCONV=1
ARBOL="$1"; DB="$2"; SALIDA="$3"; shift 3
sh scripts/aislada_tmpfs.sh clon "$DB"
for f in medir_flujo_dataops.py huella_dw.py simular_revision.py medir_ciclo_mensual.py; do docker cp scripts/$f giragroup_api:/tmp/flujo/scripts/$f; done
docker exec giragroup_api env "$@" DATABASE_URL="postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/$DB" \
  FLUJO_SIN_REVISION=1 CICLO_REUSAR_SLICES=1 CICLO_FILAS_SIN_FECHA=0 CICLO_SLICES=/tmp/slices_flujo \
  PYTHONPATH="$ARBOL:$ARBOL/backend:/tmp/flujo/scripts" sh -c "cd $ARBOL && python /tmp/flujo/scripts/medir_flujo_dataops.py /tmp/$SALIDA" 2>&1 | grep -v -i "warn\|testclient" | tail -2 | cut -c1-400
docker cp "giragroup_api:/tmp/$SALIDA" "docs/mediciones/$SALIDA" 2>/dev/null || true
docker cp "giragroup_api:/tmp/$SALIDA.huella.json" "docs/mediciones/$SALIDA.huella.json"
