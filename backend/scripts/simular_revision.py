"""
Simula la revisión humana de la bandeja de un ciclo: lista los grupos de los documentos con id > ID_MIN y actúa como lo haría el usuario
(approve-group; 'mapear estado' en los grupos de estado; resolución caso por caso en los que no se pueden aprobar en bloque).
El tiempo humano es SIMULADO con un reloj virtual (no se espera): lectura LECTURA_S por grupo, acción ACCION_S, y CASO_MANUAL_S por caso en los
manuales. Las duraciones de máquina de cada llamada son reales. Con CRONOMETRAJE_LOG activo el servidor registra además inicio y fin de cada acción.
Uso (en giragroup_api, DATABASE_URL = clon tras el ciclo): ID_MIN=16 python scripts/simular_revision.py <salida.json>
"""
import json, os, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from fastapi.testclient import TestClient
from main import app
from core.security import get_current_user
from models.user import User
app.dependency_overrides[get_current_user] = lambda: User(id=2, username="auditor", email="a@giragroup.bo", role="AUDITOR_CALIDAD", is_active=True)
cli = TestClient(app)
LECTURA_S, ACCION_S, CASO_MANUAL_S = 6.0, 2.0, 20.0
id_min = int(os.environ.get("ID_MIN", "16"))
t_real0 = time.perf_counter()
r = cli.get("/api/v1/dataops/review-tray/grupos", params={"doc_desde": id_min + 1, "limite": 1000}).json()
grupos = r["grupos"]
docs_ids = None
virtual = datetime.now(timezone.utc)
inicio_humano = virtual
eventos, bloque, manuales = [], 0, 0
for g in grupos:
    accion = g.get("accion_grupo") or "APROBAR"
    v0 = virtual + timedelta(seconds=LECTURA_S)
    t0 = time.perf_counter()
    if accion == "MANUAL":
        manuales += 1
        n_ok = 0
        for i in g["ids"]:  # caso por caso: aprobar el hecho tal cual (el humano corregiría; aquí solo se mide el flujo)
            rr = cli.post(f"/api/v1/dataops/review-tray/{i}/resolve", json={"accion": "APROBAR"}).json()
            n_ok += rr.get("status") == "success"
        dur_h = CASO_MANUAL_S * g["n"]
        res = {"resueltos": n_ok}
    else:
        bloque += 1
        body = {"clave": g["clave"], "doc_ids": None, "accion": "MAPEAR_ESTADO" if accion == "MAPEAR_ESTADO" else None}
        rr = cli.post("/api/v1/dataops/review-tray/approve-group", json=body)
        res = {"resueltos": (rr.json() or {}).get("resolved_count"), "http": rr.status_code}
        dur_h = ACCION_S
    dt = time.perf_counter() - t0
    eventos.append({"clave": g["clave"][:100], "accion": accion, "casos": g["n"], "inicio_humano_simulado": v0.isoformat(), "fin_humano_simulado": (v0 + timedelta(seconds=dur_h)).isoformat(),
                    "segundos_humano_simulado": dur_h, "segundos_maquina_real": round(dt, 3), **res})
    virtual = v0 + timedelta(seconds=dur_h)
total_h = (virtual - inicio_humano).total_seconds()
resumen = {"casos": r["total_casos"], "grupos": r["total_grupos"], "grupos_aprobables_en_bloque": bloque, "grupos_manuales": manuales,
           "pct_grupos_aprobables_en_bloque": round(bloque / max(1, len(grupos)) * 100, 1),
           "tiempo_humano_simulado_s": total_h, "supuestos": {"lectura_por_grupo_s": LECTURA_S, "accion_por_grupo_s": ACCION_S, "por_caso_manual_s": CASO_MANUAL_S},
           "tiempo_maquina_real_aprobaciones_s": round(sum(e["segundos_maquina_real"] for e in eventos), 2)}
Path(sys.argv[1]).write_text(json.dumps({"resumen": resumen, "eventos": eventos}, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(resumen, ensure_ascii=False))
