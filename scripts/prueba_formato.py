"""Ronda 10, tarea 5b: procesa UN archivo de prueba de formato (CSV de Google Forms o Moodle) con el pipeline final (/api/v1/pipeline/process)
y cuenta directo / HITL / staging. Uso (en giragroup_api, DATABASE_URL = clon): python scripts/prueba_formato.py <archivo> <salida.json>"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from fastapi.testclient import TestClient
from main import app
from core.security import get_current_user
from models.user import User
from sqlalchemy import text
from core.database import engine

app.dependency_overrides[get_current_user] = lambda: User(id=2, username="auditor", email="a@giragroup.bo", role="AUDITOR_CALIDAD", is_active=True)
cli = TestClient(app)
ruta = Path(sys.argv[1])
t0 = time.perf_counter()
with open(ruta, "rb") as fh:
    r = cli.post("/api/v1/pipeline/process", files={"file": (ruta.name, fh)})
seg = round(time.perf_counter() - t0, 2)
out = {"archivo": ruta.name, "http": r.status_code, "segundos": seg}
if r.status_code == 200:
    j = r.json()
    cargados, rev, stg = j["hechos_cargados_dw"], j["hechos_en_revision"], j["entidades_derivadas_staging"]
    doc = j["id_documento"]
    g = cli.get("/api/v1/dataops/review-tray/grupos", params={"doc_id": doc, "limite": 1000}).json()
    with engine.connect() as c:
        filas_dw = {t: c.execute(text(f"SELECT count(*) FROM {t} WHERE id_documento=:d"), {"d": doc}).scalar()
                    for t in ("fact_rendimiento_academico", "fact_situacion_financiera", "fact_evaluacion_docente")}
        stg_n = c.execute(text("SELECT count(*) FROM stg_entidad_no_resuelta WHERE id_documento=:d"), {"d": doc}).scalar()
    out.update({"id_documento": doc, "filas_procesadas": j["total_filas_procesadas"], "bloques": j["total_bloques_detectados"], "entidades_extraidas": j["total_entidades_extraidas"],
                "lineas_beto": j["lineas_beto"], "lineas_resueltas_por_reglas": j["lineas_resueltas_por_reglas"], "lineas_no_aplicables": j["lineas_no_aplicables"],
                "hechos_cargados_dw": cargados, "directo": cargados - rev, "hitl_hechos_en_revision": rev, "staging_entidades": stg, "staging_filas_en_tabla": stg_n,
                "bandeja_casos": g.get("total_casos"), "bandeja_grupos": g.get("total_grupos"), "filas_en_dw_por_tabla": filas_dw,
                "nivel_confianza_promedio": j["nivel_confianza_promedio"], "detalles_carga": j["detalles_carga"][:5]})
else:
    out["error"] = r.text[:500]
Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "detalles_carga"}, ensure_ascii=False, indent=1, default=str))
