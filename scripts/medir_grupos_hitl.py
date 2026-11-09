"""Casos y grupos HITL de los documentos del ciclo (ids > ID_MIN) y tiempo de máquina de 'aprobar grupo'.
Uso (en giragroup_api, DATABASE_URL = clon tras el ciclo): ID_MIN=16 python scripts/medir_grupos_hitl.py <salida.json>"""
import json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from fastapi.testclient import TestClient
from main import app
from core.database import SessionLocal
from core.security import get_current_user
from models.user import User
from services.bandeja_grupos import grupos_pendientes
app.dependency_overrides[get_current_user] = lambda: User(id=2, username="auditor", email="a@giragroup.bo", role="AUDITOR_CALIDAD", is_active=True)
cli = TestClient(app)
db = SessionLocal()
id_min = int(os.environ.get("ID_MIN", "16"))
from sqlalchemy import text
docs = [r[0] for r in db.execute(text("SELECT id_documento FROM dim_origen_documental WHERE id_documento > :m"), {"m": id_min})]
t0 = time.perf_counter(); g = grupos_pendientes(db, docs, limite=1000); t_listar = time.perf_counter() - t0
res = {"documentos": len(docs), "casos": g["total_casos"], "grupos": g["total_grupos"], "tiempo_listar_grupos_s": round(t_listar, 3),
       "grupos_detalle": [{k: v for k, v in x.items() if k != "ids"} for x in g["grupos"]], "aprobar_grupo": []}
for x in g["grupos"]:
    t1 = time.perf_counter()
    r = cli.post("/api/v1/dataops/review-tray/approve-group", json={"clave": x["clave"], "doc_ids": docs})
    dt = time.perf_counter() - t1
    j = r.json() if r.status_code == 200 else {"error": r.text[:150]}
    res["aprobar_grupo"].append({"clave": x["clave"][:90], "casos": x["n"], "http": r.status_code, "segundos": round(dt, 3), "resueltos": j.get("resolved_count"), "detalle": j.get("message") or j.get("error")})
ok = [a for a in res["aprobar_grupo"] if a["http"] == 200 and a["resueltos"]]
res["resumen_aprobar_grupo"] = {"grupos_intentados": len(res["aprobar_grupo"]), "con_casos_resueltos": len(ok), "casos_resueltos": sum(a["resueltos"] for a in ok),
                                "segundos_total": round(sum(a["segundos"] for a in res["aprobar_grupo"]), 2), "segundos_mediana": sorted(a["segundos"] for a in res["aprobar_grupo"])[len(res["aprobar_grupo"]) // 2] if res["aprobar_grupo"] else None}
Path(sys.argv[1]).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k not in ("grupos_detalle", "aprobar_grupo")}, ensure_ascii=False, indent=1))
