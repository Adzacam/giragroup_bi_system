"""V-7(f): Carga completa de los 10 libros en clon limpio f3v_completo (beto_pg_tmpfs),
con conteos por tabla, cifras de planificación, KPI-23 por mes y los 23 KPI del scorecard.
"""
import json
import os
import sys
import time
from decimal import Decimal
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

ROOT_HOST = Path(__file__).resolve().parent.parent
APP_ROOT = Path("/app") if Path("/app/services").exists() else ROOT_HOST / "backend"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
PIPELINE = APP_ROOT / "pipeline" if (APP_ROOT / "pipeline").exists() else APP_ROOT.parent / "pipeline"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

PG_HOST = os.getenv("F3V_PG_HOST", "beto_pg_tmpfs")
PG_PORT = int(os.getenv("F3V_PG_PORT", "5432"))
PG_USER = os.getenv("F3V_PG_USER", "giragroup_user")
PG_PASS = os.getenv("F3V_PG_PASS", "tmpfs_local")
DB_TARGET = "f3v_completo"
UPLOADS_DIR = Path("/app/uploads/data") if Path("/app/uploads/data").exists() else ROOT_HOST / "uploads" / "data"

LIBROS = [
    ("TBL_INSCRITOS.xlsx", "MARKETING"),
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


def _num(v):
    return float(v) if isinstance(v, Decimal) else v


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


def main():
    clonar_db("dw_vacio", DB_TARGET)
    os.environ["DATABASE_URL"] = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{DB_TARGET}"
    os.environ.setdefault("CATALOG_DATABASE_URL", "postgresql://giragroup_user:giragroup_pass@catalog_db:5432/giragroup_catalog_db")
    os.environ["BETO_CASCADA_FINAL"] = "0"
    os.environ["BETO_ACUERDO_QC"] = "0"
    os.environ["BETO_SUGERENCIA_HITL"] = "0"
    os.environ["BETO_VENTANA"] = "0"

    # Reutilizar cache_indice_beto de giragroup_dw (snapshot) para no re-inferir BETO CPU en ~700k filas
    conn_src = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname="giragroup_dw")
    conn_dst = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=DB_TARGET)
    with conn_src.cursor() as cs, conn_dst.cursor() as cd:
        cs.execute("SELECT hash_texto, modelo, indice FROM cache_indice_beto")
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
    por_libro = []
    try:
        user = db.query(User).first()
        for idx, (nombre, tf) in enumerate(LIBROS, 1):
            lote = Lote(estado="EN_PROCESO", total_archivos=1, institucion="GiraGroup Posgrado", periodo="2026-1")
            db.add(lote)
            db.flush()
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
            res_cons = _consolidar(ConfirmDwInsertRequest(id_lote=lote.id_lote, solo_revision=False, en_segundo_plano=False), db, user)
            por_libro.append({
                "archivo": nombre,
                "tipo_fuente": tf,
                "id_documento": doc_id,
                "inserted_dw": res_cons.get("inserted_dw"),
                "descartados_ruido": res_cons.get("descartados_ruido"),
                "sent_hitl": res_cons.get("sent_hitl"),
            })
            print(f"[{idx}/10] {nombre} (doc={doc_id}): inserted_dw={res_cons.get('inserted_dw')}", flush=True)
    finally:
        db.close()

    dt = round(time.perf_counter() - t0, 2)
    conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=DB_TARGET)
    cur = conn.cursor()
    tablas = [
        "fact_rendimiento_academico", "fact_situacion_financiera", "fact_evaluacion_docente",
        "fact_marketing", "fact_rentabilidad", "fact_costo_programa", "fact_techo_convenio",
        "fact_planificacion_programa", "fact_cobranzas_proyectadas", "fact_forecast",
        "dim_estudiante", "dim_docente", "dim_modulo", "dim_tiempo", "dim_origen_documental",
        "dim_meta", "dim_categoria_financiera", "bridge_modulo_docente",
        "carga_fila_origen", "stg_entidad_no_resuelta", "log_inconsistencias",
    ]
    conteos = {}
    for t in tablas:
        cur.execute(f"SELECT count(*) FROM public.{t}")
        conteos[t] = int(cur.fetchone()[0])

    cur.execute("""
        SELECT gestion, mes, id_tiempo, programas_planificados, programas_iniciados,
               programas_finalizados, programas_baja, programas_reprogramados,
               kpi_23, cobertura_estado, programas_con_pos,
               meta_ingreso_total, ingreso_proyectado_techos, meta_aperturas_okr,
               meta_financiera, ejecutado_financiero, costo_programa,
               pauta_asignada, pauta_ejecutada
        FROM bi.vw_planificacion_ejecucion_mensual
        ORDER BY gestion, mes
    """)
    cols = [d[0] for d in cur.description]
    serie_plan = [{c: _num(v) for c, v in zip(cols, row)} for row in cur.fetchall()]

    cur.execute("""
        SELECT gestion, codigo, nombre, perspectiva, unidad, valor, meta, semaforo
        FROM bi.vw_cmi_scorecard
        ORDER BY gestion, orden
    """)
    cols_k = [d[0] for d in cur.description]
    scorecard = [{c: _num(v) for c, v in zip(cols_k, row)} for row in cur.fetchall()]
    cur.close()
    conn.close()

    completo = {
        "tarea": "V-7(f)",
        "base_datos": f"beto_pg_tmpfs/{DB_TARGET}",
        "tiempo_total_seg": dt,
        "por_libro": por_libro,
        "conteos": conteos,
        "scorecard_por_gestion": scorecard,
    }
    serie_out = {
        "tarea": "V-7(f)",
        "base_datos": f"beto_pg_tmpfs/{DB_TARGET}",
        "kpi23_por_gestion": [k for k in scorecard if k["codigo"] == "KPI-23"],
        "serie_mensual": serie_plan,
    }
    Path("/tmp/f3v_completo.json").write_text(json.dumps(completo, indent=2, ensure_ascii=False), encoding="utf-8")
    Path("/tmp/f3v_kpi23_serie.json").write_text(json.dumps(serie_out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("OK f3v_completo dt=", dt)


if __name__ == "__main__":
    main()
