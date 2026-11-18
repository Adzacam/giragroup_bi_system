"""W-13: Carga de los 10 libros en copia limpia de f3w_vacio + verificación de carga_fila_origen e idempotencia."""
import json
import os
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
DB_TARGET = "f3w_w13_10libros"

UPLOADS_DIR = Path("/app/uploads/data") if Path("/app/uploads/data").exists() else Path(__file__).resolve().parent.parent / "uploads" / "data"

LIBROS = [
    ("TBL_INSCRITOS.xlsx", "ADMISION"),
    ("BD Cobranzas.xlsx", "COBRANZA"),
    ("BD Techos.xlsx", "TECHOS"),
    ("EJECUTADO VS META.xlsx", "RENTABILIDAD"),
    ("BD Egresos.xlsx", "EGRESOS"),
    ("PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx", "PLANIFICACION"),
    ("[BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx", "EVALUACION_DOCENTE"),
    ("Evaluación Docente y Unifranz.xlsx", "EVALUACION_DOCENTE"),
    ("Experiencia Docente 2.0.xlsx", "ACTA"),
    ("Base centralizada Académica ARCA (1).xlsx", "ACTA"),
]


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


def conteos_hechos_y_cfo(dbname: str) -> dict:
    conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=dbname)
    cur = conn.cursor()
    tablas = [
        "fact_rendimiento_academico",
        "fact_situacion_financiera",
        "fact_evaluacion_docente",
        "fact_marketing",
        "fact_rentabilidad",
        "fact_costo_programa",
        "fact_techo_convenio",
        "carga_fila_origen",
    ]
    conteos = {}
    for t in tablas:
        cur.execute(f"SELECT count(*) FROM {t}")
        conteos[t] = int(cur.fetchone()[0])
    cur.execute("SELECT tabla, count(*), count(distinct id_documento) FROM carga_fila_origen GROUP BY tabla ORDER BY tabla")
    cfo_por_tabla = {r[0]: {"filas": int(r[1]), "docs_distintos": int(r[2])} for r in cur.fetchall()}
    cur.execute("SELECT count(distinct id_documento) FROM carga_fila_origen")
    cfo_docs_distintos = int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return {"conteos": conteos, "cfo_por_tabla": cfo_por_tabla, "cfo_docs_distintos": cfo_docs_distintos}


def main():
    clonar_db("f3w_vacio", DB_TARGET)
    # Copiar cache_indice_beto desde f3w_completo para no re-inferir BETO CPU
    os.environ["DATABASE_URL"] = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{DB_TARGET}"
    os.environ.setdefault("CATALOG_DATABASE_URL", "postgresql://giragroup_user:giragroup_pass@catalog_db:5432/giragroup_catalog")
    os.environ["BETO_CASCADA_FINAL"] = "0"
    os.environ["BETO_ACUERDO_QC"] = "0"
    os.environ["BETO_SUGERENCIA_HITL"] = "0"
    os.environ["BETO_VENTANA"] = "0"

    conn_src = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname="f3w_completo")
    conn_dst = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=DB_TARGET)
    with conn_src.cursor() as cs, conn_dst.cursor() as cd:
        cs.execute("SELECT hash_texto, modelo, indice FROM cache_indice_beto")
        from psycopg2.extras import execute_values
        rows = cs.fetchall()
        for i in range(0, len(rows), 5000):
            execute_values(cd, "INSERT INTO cache_indice_beto (hash_texto, modelo, indice) VALUES %s ON CONFLICT DO NOTHING", rows[i:i+5000])
        conn_dst.commit()
    conn_src.close()
    conn_dst.close()

    from core.database import SessionLocal
    from models.lote import Lote
    from models.user import User
    from services.ingestion_service import IngestionService
    from routers.dataops._comun import ConfirmDwInsertRequest
    from routers.dataops.consolidacion import _consolidar

    db = SessionLocal()
    t0 = time.perf_counter()
    doc_ids = []
    lote_ids = []
    try:
        user = db.query(User).first()
        for idx, (nombre, tf) in enumerate(LIBROS, 1):
            lote = Lote(estado="EN_PROCESO", total_archivos=1, institucion="GiraGroup Posgrado", periodo="2026-1")
            db.add(lote)
            db.flush()
            lote_ids.append(lote.id_lote)
            ruta = UPLOADS_DIR / nombre
            res_ing = IngestionService.procesar_archivo_ingesta(
                db=db,
                file_bytes=ruta.read_bytes(),
                filename=nombre,
                id_lote=lote.id_lote,
                tipo_fuente=tf,
                tipo_escala="CENTESIMAL_100" if tf in ("ACTA", "MOODLE") else None,
            )
            db.commit()
            doc_id = res_ing.get("id_documento")
            doc_ids.append(doc_id)
            res_cons = _consolidar(ConfirmDwInsertRequest(id_lote=lote.id_lote, solo_revision=False, en_segundo_plano=False), db, user)
            print(f"[{idx}/10] {nombre} (doc={doc_id}): inserted_dw={res_cons.get('inserted_dw')}", flush=True)

        despues_10 = conteos_hechos_y_cfo(DB_TARGET)
        # Prueba de idempotencia: re-consolidar el primer documento y verificar +0 hechos
        res_re = _consolidar(ConfirmDwInsertRequest(id_lote=lote_ids[0], solo_revision=False, en_segundo_plano=False), db, user)
        despues_re = conteos_hechos_y_cfo(DB_TARGET)
        dt = round(time.perf_counter() - t0, 2)
        print(json.dumps({
            "tiempo_total_seg": dt,
            "despues_10_libros": despues_10,
            "re_consolidacion_lote_1": {
                "inserted_dw": res_re.get("inserted_dw"),
                "conteos": despues_re["conteos"],
                "delta_hechos": {
                    k: despues_re["conteos"][k] - despues_10["conteos"][k]
                    for k in despues_10["conteos"]
                },
            },
        }, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
