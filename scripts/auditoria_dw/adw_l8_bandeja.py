"""ADW L8: conteos de la bandeja (staging pendiente) y de log_auditoria_nlp en la copia tmpfs. Sin PII: solo agregados.
Uso: ADW_DB_URL=postgresql://giragroup_user:tmpfs_local@127.0.0.1:55433/giragroup_db python -I scripts/auditoria_dw/adw_l8_bandeja.py <salida.json>"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
url = os.environ.get("ADW_DB_URL", "")
if "55433" not in url:
    sys.exit("ADW_DB_URL debe apuntar a la copia tmpfs (puerto 55433).")
os.environ["DATABASE_URL"] = url

from sqlalchemy import text  # noqa: E402

from core.database import SessionLocal  # noqa: E402
from services.auditoria_hitl import es_correccion_humana  # noqa: E402
from services.bandeja_grupos import grupos_pendientes  # noqa: E402

with SessionLocal() as db:
    g = grupos_pendientes(db, None, limite=10**9)
    log = db.execute(text("SELECT correccion_humana, count(*) FROM public.log_auditoria_nlp GROUP BY 1")).all()
    pend = db.execute(text("SELECT motivo, count(*) FROM public.stg_entidad_no_resuelta WHERE NOT resuelto GROUP BY 1 ORDER BY 2 DESC")).all()
salida = {
    "bandeja": {"total_casos": g["total_casos"], "total_grupos": g["total_grupos"], "patrones": g["patrones"]},
    "pendientes_por_motivo": {m: n for m, n in pend},
    "log_auditoria_nlp": {
        "total": sum(n for _, n in log),
        "valores": {v[:40]: n for v, n in log},
        "cuentan_como_correccion_humana": sum(n for v, n in log if es_correccion_humana(v)),
    },
}
Path(sys.argv[1]).write_text(json.dumps(salida, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(salida, ensure_ascii=False)[:900])
