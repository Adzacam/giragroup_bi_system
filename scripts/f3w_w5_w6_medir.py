"""Medición y perfilado para W-5 (dos fases) y W-6 (rapidez de consolidación) en beto_pg_f3w.
Se ejecuta dentro de giragroup_api o en entorno con acceso a beto_pg_f3w:5432.
"""
import argparse
import cProfile
import hashlib
import io
import json
import os
import pstats
import sys
import time
from pathlib import Path

import psycopg2

ROOT = Path("/app") if Path("/app/services").exists() else Path(__file__).resolve().parent.parent / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PIPELINE = ROOT / "pipeline" if (ROOT / "pipeline").exists() else ROOT.parent / "pipeline"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

PG_HOST = os.getenv("F3W_PG_HOST", "beto_pg_f3w")
PG_PORT = int(os.getenv("F3W_PG_PORT", "5432"))
PG_USER = os.getenv("F3W_PG_USER", "giragroup_user")
PG_PASS = os.getenv("F3W_PG_PASS", "tmpfs_local")

ARCHIVO_ANTIGUO = "[BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx"
UPLOADS_DIR = Path("/app/uploads/data") if Path("/app/uploads/data").exists() else Path(__file__).resolve().parent.parent / "uploads" / "data"

FACT_TABLES = [
    "fact_rendimiento_academico",
    "fact_situacion_financiera",
    "fact_evaluacion_docente",
    "fact_marketing",
    "fact_rentabilidad",
    "fact_costo_programa",
    "fact_techo_convenio",
]
SURROGATE_COLS = {
    "id_hecho_aca", "id_hecho_fin", "id_hecho_eval", "id_hecho_mkt",
    "id_hecho_rent", "id_hecho_costo", "id_hecho_techo", "id_forecast",
    "created_at", "actualizado_en", "fecha_registro", "generado_en",
}


def db_url(dbname: str) -> str:
    return f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{dbname}"


def clonar_db(template: str, target: str) -> None:
    conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname="postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
        (target,),
    )
    cur.execute(f'DROP DATABASE IF EXISTS "{target}"')
    cur.execute(f'CREATE DATABASE "{target}" TEMPLATE "{template}"')
    cur.close()
    conn.close()


def set_db_env(dbname: str) -> None:
    url = db_url(dbname)
    os.environ["DATABASE_URL"] = url
    os.environ.setdefault("CATALOG_DATABASE_URL", "postgresql://giragroup_user:giragroup_pass@catalog_db:5432/giragroup_catalog")
    # Desactivar flags BETO si no se piden explícitamente (misma línea base que F3U-B)
    os.environ["BETO_CASCADA_FINAL"] = "0"
    os.environ["BETO_ACUERDO_QC"] = "0"
    os.environ["BETO_SUGERENCIA_HITL"] = "0"
    os.environ["BETO_VENTANA"] = "0"


def huella_hechos(dbname: str) -> dict:
    conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=dbname)
    cur = conn.cursor()
    res = {"conteos": {}, "md5_negocio": {}}
    for tbl in FACT_TABLES:
        cur.execute(f"SELECT count(*) FROM {tbl}")
        cnt = int(cur.fetchone()[0])
        res["conteos"][tbl] = cnt
        if cnt == 0:
            res["md5_negocio"][tbl] = None
            continue
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
            (tbl,),
        )
        cols = [r[0] for r in cur.fetchall() if r[0] not in SURROGATE_COLS]
        cols_expr = ", ".join(f"COALESCE({c}::text, '')" for c in cols)
        order_expr = ", ".join(cols)
        cur.execute(
            f"SELECT md5(string_agg(row_txt, E'\\n' ORDER BY row_txt)) "
            f"FROM (SELECT concat_ws('|', {cols_expr}) AS row_txt FROM {tbl} ORDER BY {order_expr}) sub"
        )
        res["md5_negocio"][tbl] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM stg_entidad_no_resuelta WHERE tipo_entidad != 'RUIDO'")
    res["conteos"]["stg_entidad_no_resuelta_no_ruido"] = int(cur.fetchone()[0])
    cur.execute("SELECT count(*) FROM stg_entidad_no_resuelta WHERE tipo_entidad = 'RUIDO'")
    res["conteos"]["stg_entidad_no_resuelta_ruido"] = int(cur.fetchone()[0])
    cur.execute("SELECT count(*) FROM log_inconsistencias")
    res["conteos"]["log_inconsistencias"] = int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return res


def preparar_antiguo():
    clonar_db("f3w_vacio", "f3w_antiguo_pre")
    set_db_env("f3w_antiguo_pre")
    from core.database import SessionLocal
    from models.lote import Lote
    from services.ingestion_service import IngestionService

    ruta = UPLOADS_DIR / ARCHIVO_ANTIGUO
    file_bytes = ruta.read_bytes()
    db = SessionLocal()
    try:
        lote = Lote(estado="EN_PROCESO", total_archivos=1, institucion="GiraGroup Posgrado", periodo="2026-1")
        db.add(lote)
        db.flush()
        res = IngestionService.procesar_archivo_ingesta(
            db=db,
            file_bytes=file_bytes,
            filename=ARCHIVO_ANTIGUO,
            id_lote=lote.id_lote,
            tipo_fuente="EVALUACION_DOCENTE",
        )
        db.commit()
        print(f"Preparado f3w_antiguo_pre: lote={lote.id_lote}, doc={res.get('id_documento')}")
    finally:
        db.close()


def correr_consolidacion(dbname: str, solo_revision: bool = False, profile: bool = False):
    set_db_env(dbname)
    # Reimportar / reconfigurar engine si cambió DATABASE_URL
    import importlib
    import core.database as cdb
    if str(cdb.engine.url).rsplit("/", 1)[-1] != dbname:
        importlib.reload(cdb)
    from core.database import SessionLocal
    from routers.dataops._comun import ConfirmDwInsertRequest
    from routers.dataops.consolidacion import _consolidar
    from models.user import User
    from services import tareas_dataops

    db = SessionLocal()
    try:
        user = db.query(User).first()
        tid = tareas_dataops.crear("CONSOLIDACION" if not solo_revision else "PREPARACION_REVISION", 1, 0, "bench")
        payload = ConfirmDwInsertRequest(id_lote=1, solo_revision=solo_revision, en_segundo_plano=False)
        pr = cProfile.Profile() if profile else None
        t0 = time.perf_counter()
        if pr:
            pr.enable()
        res = _consolidar(payload, db, user, tarea_id=tid)
        if pr:
            pr.disable()
        dt = round(time.perf_counter() - t0, 3)
        tareas_dataops.terminar(tid, res)
        prof_top = None
        if pr:
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats("cumtime")
            ps.print_stats(25)
            prof_top = s.getvalue()
        return dt, res, prof_top
    finally:
        db.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", required=True, choices=["preparar", "antes", "despues", "w5"])
    args = ap.parse_args()

    if args.modo == "preparar":
        preparar_antiguo()
    elif args.modo in ("antes", "despues"):
        tiempos = []
        prof_text = None
        huella = None
        last_res = None
        for i in range(1, 4):
            dbn = f"f3w_w6_{args.modo}_{i}"
            clonar_db("f3w_antiguo_pre", dbn)
            dt, res, prof = correr_consolidacion(dbn, solo_revision=False, profile=(i == 1))
            tiempos.append(dt)
            last_res = res
            if prof:
                prof_text = prof
            h = huella_hechos(dbn)
            if huella is None:
                huella = h
            else:
                assert h == huella, f"Huella inconsistente en corrida {i}: {h} != {huella}"
            print(f"[{args.modo}] corrida {i}: {dt}s, eval={h['conteos']['fact_evaluacion_docente']}")
        out = {
            "modo": args.modo,
            "archivo": ARCHIVO_ANTIGUO,
            "tiempos_seg": tiempos,
            "promedio_seg": round(sum(tiempos) / len(tiempos), 3),
            "min_seg": min(tiempos),
            "huella": huella,
            "resultado": last_res,
            "cprofile_top25": prof_text,
        }
        print(json.dumps({k: v for k, v in out.items() if k != "cprofile_top25"}, ensure_ascii=False, indent=2))
        if prof_text:
            print("=== CPROFILE TOP 25 ===")
            print(prof_text)
    elif args.modo == "w5":
        clonar_db("f3w_antiguo_pre", "f3w_w5_test")
        dt_a, res_a, _ = correr_consolidacion("f3w_w5_test", solo_revision=True)
        h_a = huella_hechos("f3w_w5_test")
        dt_b, res_b, _ = correr_consolidacion("f3w_w5_test", solo_revision=False)
        h_b = huella_hechos("f3w_w5_test")
        print(json.dumps({
            "fase_a": {"tiempo_seg": dt_a, "resultado": res_a, "huella": h_a},
            "fase_b": {"tiempo_seg": dt_b, "resultado": res_b, "huella": h_b},
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
