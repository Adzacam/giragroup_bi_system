"""ADW DA8: cifras del pronóstico financiero (analitica-macro) en la copia tmpfs, para comparar antes/después de usar todas las categorías.
Uso: ADW_DB_URL=postgresql://giragroup_user:tmpfs_local@127.0.0.1:55433/giragroup_db python -I scripts/auditoria_dw/adw_da8_forecast.py <salida.json>"""
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

from core.database import SessionLocal  # noqa: E402
from services.forecast_service import obtener_analitica_macro_completa  # noqa: E402

with SessionLocal() as db:
    macro = obtener_analitica_macro_completa(db)
c3, c4 = macro.get("caso3_metas_mensuales") or {}, macro.get("caso4_metas_anuales") or {}
salida = {
    "caso3": {k: v for k, v in c3.items() if not isinstance(v, (list, dict))},
    "caso3_meses": len(c3.get("meses_etiquetas") or []),
    "caso3_meta_catalogo_bs": c3.get("meta_catalogo_bs"),
    "caso3_ejecutado_real_bs": c3.get("ejecutado_real_bs"),
    "caso3_proyecciones_hw": [(p.get("periodo"), p.get("monto_proyectado_bs")) for p in (c3.get("proyecciones_hw") or [])],
    "caso4": {k: v for k, v in c4.items() if not isinstance(v, (list, dict))},
    "sin_datos": macro.get("sin_datos"),
}
Path(sys.argv[1]).write_text(json.dumps(salida, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps({"caso3": salida["caso3"], "caso4": salida["caso4"]}, ensure_ascii=False, default=str)[:1500])
