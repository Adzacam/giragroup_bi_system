"""ADW L8: aplica el clasificador nuevo (`motivo_fila_sin_entidad`) a las 1.308 filas sin estudiante de la copia tmpfs.
Solo cuenta: no imprime ni guarda líneas ni payloads (sin PII).
Uso: ADW_DB_URL=postgresql://giragroup_user:tmpfs_local@127.0.0.1:55433/giragroup_db python -I scripts/auditoria_dw/adw_l8_clasificar.py <salida.csv>"""
import collections
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
url = os.environ.get("ADW_DB_URL", "")
if "55433" not in url:
    sys.exit("ADW_DB_URL debe apuntar a la copia tmpfs (puerto 55433).")

from sqlalchemy import create_engine, text  # noqa: E402

from services.extraccion_por_encabezado import campos_por_encabezado, motivo_fila_sin_entidad  # noqa: E402

CATEGORIA = {"FILA_FINANCIERA_SIN_ESTUDIANTE": "financiero", "FILA_ACADEMICA_SIN_ESTUDIANTE": "academico"}
cuentas = collections.Counter()
with create_engine(url).connect() as c:
    filas = c.execute(text("SELECT motivo, id_documento, payload_json->>'raw_line' FROM public.stg_entidad_no_resuelta "
                           "WHERE motivo IN ('FILA_FINANCIERA_SIN_ESTUDIANTE','FILA_ACADEMICA_SIN_ESTUDIANTE')")).all()
for motivo, doc, linea in filas:
    campos = campos_por_encabezado([x.strip() for x in (linea or "").split("|")])
    nuevo = motivo_fila_sin_entidad(campos, CATEGORIA[motivo]) or "(ya no es ruido: seguiría a extracción)"
    cuentas[(motivo, doc, nuevo)] += 1

with open(sys.argv[1], "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["motivo_anterior", "id_documento", "motivo_nuevo", "filas"])
    for (m, d, n), k in sorted(cuentas.items()):
        w.writerow([m, d, n, k])
        print(m, d, n, k)
print("total", sum(cuentas.values()))
