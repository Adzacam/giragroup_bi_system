"""Tarea 5: ciclo COMPLETO (archivo entero, sin recorte de filas) de los dos libros de evaluación docente, midiendo tiempo real.
Corre dentro del contenedor giragroup_api contra un clon del DW: DATABASE_URL=<clon> python /app/scripts/medir_completo.py"""
import json, sys, time
from pathlib import Path
sys.path[:0] = ["/app"]
from fastapi.testclient import TestClient
from main import app
from core.security import get_current_user
from models.user import User
app.dependency_overrides[get_current_user] = lambda: User(id=2, username="auditor", email="a@giragroup.bo", role="AUDITOR_CALIDAD", is_active=True)
c = TestClient(app, raise_server_exceptions=False)
out = []
ARCHIVOS = sys.argv[1:] or ["Evaluación Docente y Unifranz.xlsx", "[BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx"]
for nombre in ARCHIVOS:
    f = Path("/app/uploads/data") / nombre
    t = time.perf_counter()
    with open(f, "rb") as fh:
        r = c.post("/api/v1/pipeline/process", files={"file": (f.name, fh)}, timeout=None)
    dt = time.perf_counter() - t
    j = r.json() if r.status_code == 200 else {"error": r.text[:300]}
    out.append({"archivo": nombre, "http": r.status_code, "segundos": round(dt, 1), **{k: j.get(k) for k in ("total_filas_procesadas", "hechos_cargados_dw", "hechos_en_revision", "entidades_derivadas_staging", "tiempos_etapa_ms", "error")}})
    print(json.dumps(out[-1], ensure_ascii=False), flush=True)
    Path("/tmp/ciclo_completo_" + str(abs(hash(tuple(ARCHIVOS))) % 10000) + ".json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
