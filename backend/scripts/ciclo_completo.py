"""Ciclo mensual COMPLETO (10 archivos, hojas sin fecha completas) por /api/v1/pipeline/process, una pasada.
Mide por archivo y etapa (lectura, reglas, BETO, carga), casos de la bandeja antes/después y la huella del DW (filas + hash por tabla).
Uso (dentro de giragroup_api, DATABASE_URL = clon): CICLO_FILAS_SIN_FECHA=0 CICLO_SLICES=/tmp/slices python scripts/ciclo_completo.py <salida.json> [AAAA-MM]"""
import json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
salida = sys.argv[1]
sys.argv = [sys.argv[0]] + sys.argv[2:3]
import medir_ciclo_mensual as m
from sqlalchemy import text

TABLAS_HUELLA = ["fact_cobranzas_proyectadas", "fact_costo_programa", "fact_evaluacion_docente", "fact_forecast", "fact_marketing",
                 "fact_rendimiento_academico", "fact_rentabilidad", "fact_situacion_financiera", "fact_techo_convenio",
                 "dim_categoria_financiera", "dim_docente", "dim_estudiante", "dim_meta", "dim_modulo", "dim_tiempo", "bridge_modulo_docente"]


def huella(engine):
    out = {}
    with engine.connect() as c:
        for t in TABLAS_HUELLA:
            n, h = c.execute(text(f"SELECT count(*), md5(coalesce(string_agg(x::text, '|' ORDER BY x::text), '')) FROM {t} x")).one()
            # sin columnas de id_documento/clave ni serial no se puede abstraer de forma genérica: se registra tal cual
            out[t] = {"filas": n, "hash": h}
    return out


def main():
    info = m.construir_slices()
    from fastapi.testclient import TestClient
    from main import app
    from core.database import engine
    from core.security import get_current_user
    from models.user import User
    app.dependency_overrides[get_current_user] = lambda: User(id=2, username="auditor", email="a@giragroup.bo", role="AUDITOR_CALIDAD", is_active=True)
    cli = TestClient(app)

    def bandeja():
        j = cli.get("/api/v1/dataops/review-tray", params={"page": 1, "page_size": 1}).json()
        return j.get("total_items", j.get("total"))

    b0 = bandeja(); t_global = time.perf_counter(); tot = {"lectura_e_ingesta": 0.0, "reglas_y_resto": 0.0, "beto": 0.0, "carga_dw": 0.0}
    for it in info:
        if "slice" not in it:
            continue
        t0 = time.perf_counter()
        with open(it["slice"], "rb") as fh:
            r = cli.post("/api/v1/pipeline/process", files={"file": (Path(it["slice"]).name, fh)})
        it["http"], it["segundos"] = r.status_code, round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            j = r.json()
            it["tiempos_etapa_ms"] = j.get("tiempos_etapa_ms"); it["filas_procesadas"] = j.get("total_filas_procesadas"); it["hechos_cargados_dw"] = j.get("hechos_cargados_dw")
            for k in tot:
                tot[k] += (j.get("tiempos_etapa_ms") or {}).get(k, 0.0)
        else:
            it["error"] = r.text[:300]
        print(it["archivo"][:40], it["http"], it["segundos"], flush=True)
    total = round(time.perf_counter() - t_global, 2)
    res = {"mes_objetivo": m.MES, "filas_sin_fecha": "completas" if not m.FILAS_SIN_FECHA else m.FILAS_SIN_FECHA, "tiempo_total_s": total,
           "suma_etapas_s": {k: round(v / 1000, 1) for k, v in tot.items()}, "bandeja_antes": b0, "bandeja_despues": bandeja(), "archivos": info, "huella_dw": huella(engine)}
    res["casos_hitl_nuevos"] = res["bandeja_despues"] - b0
    Path(salida).write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("archivos", "huella_dw")}, indent=1))


if __name__ == "__main__":
    main()
