"""Tarea 3: tiempo de MÁQUINA de la bandeja HITL (GET /dataops/review-tray + POST /review-tray/{id}/resolve) sobre 20 casos reales,
contra un CLON del DW (no altera el DW real). No mide tiempo humano de lectura/decisión.
Uso: DATABASE_URL=<clon> python scripts/medir_hitl.py"""
import json, statistics, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from fastapi.testclient import TestClient
from backend.main import app
from core.security import get_current_user
from models.user import User
app.dependency_overrides[get_current_user] = lambda: User(id=2, username="auditor", email="a@giragroup.bo", role="AUDITOR_CALIDAD", is_active=True)
c = TestClient(app)
t = time.perf_counter(); r = c.get("/api/v1/dataops/review-tray", params={"page_size": 20, "estado": "PENDIENTE"}); t_lista = time.perf_counter() - t
print("lista", r.status_code, round(t_lista, 3), "s")
j = r.json(); items = j.get("items") or j.get("data") or j.get("casos") or []
print("claves", list(j)[:8], "n", len(items))
res = []
for it in items[:20]:
    iid = it.get("id") or it.get("id_staging") or it.get("item_id")
    t = time.perf_counter(); rr = c.post(f"/api/v1/dataops/review-tray/{iid}/resolve", json={"accion": "APROBAR"}); dt = time.perf_counter() - t
    res.append({"id": iid, "tipo": it.get("tipo_entidad") or it.get("tipo"), "motivo": it.get("motivo"), "http": rr.status_code, "segundos": round(dt, 3)})
ok = [x["segundos"] for x in res if x["http"] == 200]
out = {"lista_20_s": round(t_lista, 3), "resueltos_ok": len(ok), "intentados": len(res), "media_s": round(statistics.mean(ok), 3) if ok else None,
       "mediana_s": round(statistics.median(ok), 3) if ok else None, "max_s": max(ok) if ok else None, "detalle": res}
(ROOT / "docs/evidencias/tiempo_hitl_maquina.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "detalle"}, indent=1)); print(res[:3])
