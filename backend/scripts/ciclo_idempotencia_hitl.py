"""
Tareas 1-2 (ronda 4): un ciclo mensual dos veces sobre el mismo juego de archivos (mismos bytes -> mismo hash).
Mide, antes y después de cada pasada: cola de staging (única por clave_origen) por tipo/motivo, hechos en revisión
(académicos + financieros, que son los que muestra la bandeja), hechos de evaluación docente sin docente o sin módulo
(no tienen marca de revisión, no aparecen en la bandeja) y el total que devuelve GET /dataops/review-tray.
Uso (dentro de giragroup_api, DATABASE_URL = clon): python scripts/ciclo_idempotencia_hitl.py [AAAA-MM]
"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
sys.argv = [sys.argv[0]] + sys.argv[1:2]
import medir_ciclo_mensual as m
from sqlalchemy import text


def main():
    info = m.construir_slices()
    from fastapi.testclient import TestClient
    from main import app
    from core.database import engine
    from core.security import get_current_user
    from models.user import User
    app.dependency_overrides[get_current_user] = lambda: User(id=2, username="auditor", email="a@giragroup.bo", role="AUDITOR_CALIDAD", is_active=True)
    cli = TestClient(app)

    def estado():
        with engine.connect() as c:
            q = lambda s: c.execute(text(s)).scalar()
            e = {
                "stg_total": q("SELECT count(*) FROM stg_entidad_no_resuelta"),
                "stg_pendientes": q("SELECT count(*) FROM stg_entidad_no_resuelta WHERE NOT resuelto AND estado_resolucion='PENDIENTE'"),
                "stg_por_tipo_motivo": {f"{r[0]}/{r[1]}": r[2] for r in c.execute(text(
                    "SELECT tipo_entidad, motivo, count(*) FROM stg_entidad_no_resuelta WHERE NOT resuelto AND estado_resolucion='PENDIENTE' GROUP BY 1,2 ORDER BY 3 DESC"))},
                "hechos_revision_aca": q("SELECT count(*) FROM fact_rendimiento_academico WHERE requiere_revision"),
                "hechos_revision_fin": q("SELECT count(*) FROM fact_situacion_financiera WHERE requiere_revision"),
                "eval_revision_filas": q("SELECT count(*) FROM fact_evaluacion_docente WHERE requiere_revision"),
                "eval_revision_casos": q("SELECT count(*) FROM (SELECT 1 FROM fact_evaluacion_docente WHERE requiere_revision GROUP BY id_documento, id_modulo) g"),
                "eval_docente_con_docente": q("SELECT count(*) FROM fact_evaluacion_docente WHERE id_docente IS NOT NULL"),
                "eval_docente_filas": q("SELECT count(*) FROM fact_evaluacion_docente"),
                "eval_docente_sin_docente_o_modulo": q("SELECT count(*) FROM fact_evaluacion_docente WHERE id_docente IS NULL OR id_modulo IS NULL"),
                "hechos_aca": q("SELECT count(*) FROM fact_rendimiento_academico"),
                "hechos_fin": q("SELECT count(*) FROM fact_situacion_financiera"),
                "dim_estudiante": q("SELECT count(*) FROM dim_estudiante"),
                "dim_docente": q("SELECT count(*) FROM dim_docente"),
            }
        r = cli.get("/api/v1/dataops/review-tray", params={"page": 1, "page_size": 1})
        j = r.json()
        e["bandeja_total_items"] = j.get("total_items", j.get("total"))
        e["bandeja_claves"] = list(j)[:10]
        return e

    res = {"mes_objetivo": m.MES, "estados": {"inicial": estado()}, "pasadas": []}
    for n in (1, 2):
        t0 = time.perf_counter()
        det = []
        for it in info:
            if "slice" not in it:
                continue
            with open(it["slice"], "rb") as fh:
                r = cli.post("/api/v1/pipeline/process", files={"file": (Path(it["slice"]).name, fh)})
            j = r.json() if r.status_code == 200 else {}
            det.append({"archivo": it["archivo"], "http": r.status_code, "filas": j.get("total_filas_procesadas"), "hechos": j.get("hechos_cargados_dw")})
        res["pasadas"].append({"n": n, "segundos": round(time.perf_counter() - t0, 1), "archivos": det})
        res["estados"][f"tras_pasada_{n}"] = estado()
        print("pasada", n, res["pasadas"][-1]["segundos"], "s", flush=True)
    e0, e1, e2 = (res["estados"][k] for k in ("inicial", "tras_pasada_1", "tras_pasada_2"))
    res["delta_pasada_1"] = {k: e1[k] - e0[k] for k in e0 if isinstance(e0[k], int) and isinstance(e1.get(k), int)}
    res["delta_pasada_2"] = {k: e2[k] - e1[k] for k in e1 if isinstance(e1[k], int) and isinstance(e2.get(k), int)}
    res["delta_pasada_1"]["stg_por_tipo_motivo"] = {k: e1["stg_por_tipo_motivo"].get(k, 0) - e0["stg_por_tipo_motivo"].get(k, 0) for k in e1["stg_por_tipo_motivo"]}
    res["delta_pasada_2"]["stg_por_tipo_motivo"] = {k: e2["stg_por_tipo_motivo"].get(k, 0) - e1["stg_por_tipo_motivo"].get(k, 0) for k in e2["stg_por_tipo_motivo"]}
    Path("/tmp/ciclo_idempotencia_hitl.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"delta_pasada_1": res["delta_pasada_1"], "delta_pasada_2": res["delta_pasada_2"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
