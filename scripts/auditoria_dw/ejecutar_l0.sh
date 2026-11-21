#!/bin/sh
# Ejecuta adw_*.sql sobre la copia tmpfs (adw_pg_tmpfs) y deja 1 CSV por bloque en docs/mediciones/adw_l0_*.csv
# La copia se crea con pg_dump (solo lectura) de la DW viva; ver docs/mediciones/adw_l0_entorno.md
set -e
export MSYS_NO_PATHCONV=1
CT="${CT:-adw_pg_tmpfs}"
OUT="docs/mediciones"
for f in scripts/auditoria_dw/adw_*.sql; do
  b=$(basename "$f" .sql); b=${b#adw_}
  docker exec -i "$CT" psql -U giragroup_user -d giragroup_db -q -v ON_ERROR_STOP=1 --csv < "$f" > "$OUT/adw_l0_$b.csv"
  echo "$b: $(($(wc -l < "$OUT/adw_l0_$b.csv") - 1)) filas"
done
