#!/bin/sh
# F1 de BETO (modos B y C) en gold_510 y layouts_5, con y sin cuantización dinámica int8. Salida: docs/evidencias/f1_beto_{fp32,int8}_{dataset}.json
cd "$(dirname "$0")/.."
for q in 0 1; do
  nombre=$([ "$q" = 1 ] && echo int8 || echo fp32)
  for ds in gold_510 layouts_5; do
    BETO_INT8=$q .venv/Scripts/python.exe -W ignore scripts/ablacion_beto.py --modo ALL --dataset $ds \
      --output_json docs/evidencias/f1_beto_${nombre}_${ds}.json --output_csv docs/evidencias/f1_beto_${nombre}_${ds}.csv > /dev/null 2>&1
  done
done
echo listo
