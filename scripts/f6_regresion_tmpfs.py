"""
scripts/f6_regresion_tmpfs.py
-----------------------------
Regresión F6-4b sobre clones aislados en `beto_pg_tmpfs` (NUNCA toca `snapshot_dw_20261110_1201` ni la DW viva).

Ejecuta dentro de `giragroup_api`:
  1. Corrida A vs B sobre lote de 10 archivos -> `/tmp/f6_aporte_10archivos.json`
  2. Corrida completa de los 10 libros reales -> `/tmp/f6_completo.json`, `/tmp/f6_auditoria_dw.json`
     y diffs específicos: `f6_encuestas_diff.json`, `f6_placeholders_diff.json`,
     `f6_homonimia_diff.json`, `f6_arca_cruce_diff.json`, `f6_beto_rol_diff.json`.
"""
import io
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import openpyxl
import psycopg2

ROOT_HOST = Path(__file__).resolve().parent.parent
APP_ROOT = Path("/app") if Path("/app/services").exists() else ROOT_HOST / "backend"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
PIPELINE = APP_ROOT / "pipeline" if (APP_ROOT / "pipeline").exists() else APP_ROOT.parent / "pipeline"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

PG_HOST = os.getenv("F6_PG_HOST", "beto_pg_tmpfs")
PG_PORT = int(os.getenv("F6_PG_PORT", "5432"))
PG_USER = os.getenv("F6_PG_USER", "giragroup_user")
PG_PASS = os.getenv("F6_PG_PASS", "tmpfs_local")
UPLOADS_DIR = Path("/app/uploads/data") if Path("/app/uploads/data").exists() else ROOT_HOST / "uploads" / "data"
OUT_DIR = Path(os.getenv("F6_OUT_DIR", "/tmp/f6_out"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

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


def _sql_all(db_name: str, sql: str):
    conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=db_name)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()


def _sql_one(db_name: str, sql: str):
    rows = _sql_all(db_name, sql)
    return rows[0][0] if rows else None


def _recortar_xlsx(ruta: Path, max_filas: int = 350) -> bytes:
    """Crea una copia en memoria con a lo sumo `max_filas` filas por hoja para la comparación rápida A vs B."""
    wb_src = openpyxl.load_workbook(str(ruta), read_only=True, data_only=True)
    wb_dst = openpyxl.Workbook(write_only=True)
    for name in wb_src.sheetnames:
        ws_src = wb_src[name]
        ws_dst = wb_dst.create_sheet(title=name)
        for i, row in enumerate(ws_src.iter_rows(values_only=True)):
            if i >= max_filas:
                break
            ws_dst.append(list(row))
    wb_src.close()
    buf = io.BytesIO()
    wb_dst.save(buf)
    return buf.getvalue()


def correr_lote(db_name: str, modo: str, recortar_filas: int | None = None) -> dict:
    clonar_db("dw_vacio", db_name)
    os.environ["DATABASE_URL"] = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{db_name}"
    os.environ["CATALOG_DATABASE_URL"] = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/catalogo_copia"
    os.environ["PYTHONHASHSEED"] = "0"

    if modo == "A":
        os.environ["BETO_CASCADA_FINAL"] = "0"
        os.environ["BETO_ACUERDO_QC"] = "0"
        os.environ["BETO_SUGERENCIA_HITL"] = "0"
        os.environ["BETO_RESCATE_ACADEMICO"] = "0"
        os.environ["BETO_VENTANA"] = "0"
    else:
        os.environ["BETO_CASCADA_FINAL"] = "1"
        os.environ["BETO_ACUERDO_QC"] = "1"
        os.environ["BETO_SUGERENCIA_HITL"] = "1"
        os.environ["BETO_RESCATE_ACADEMICO"] = "1"
        os.environ["BETO_ACUERDO_SOLO_FUZZY"] = "1"
        os.environ["BETO_VENTANA"] = "0"

    # Re-inicializar engine de SQLAlchemy apuntando al nuevo db_name
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import core.database as db_mod
    import services.confianza_service as cs_mod
    import routers.dataops.consolidacion as cons_mod

    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_mod.engine = engine
    db_mod.SessionLocal = Session
    cons_mod.SessionLocal = Session

    cat_engine = create_engine(os.environ["CATALOG_DATABASE_URL"], pool_pre_ping=True)
    db_mod.catalog_engine = cat_engine
    db_mod.CatalogSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cat_engine)

    # En Modo A no llamar a /indice
    orig_obtener = cs_mod.obtener_indices
    orig_cascada = cs_mod.indices_cascada
    if modo == "A":
        def _sin_beto(lineas, al_avanzar=None):
            if al_avanzar:
                al_avanzar(len(lineas))
            return [None] * len(lineas)
        cs_mod.obtener_indices = _sin_beto
        cons_mod.obtener_indices = _sin_beto
        cons_mod.indices_cascada = lambda lineas, resueltas, obtener=None, al_avanzar=None: _sin_beto(lineas, al_avanzar)
    else:
        cs_mod.obtener_indices = orig_obtener
        cons_mod.obtener_indices = orig_obtener
        cons_mod.indices_cascada = orig_cascada

    from models.lote import Lote
    from models.user import User
    from services.ingestion_service import IngestionService
    from routers.dataops._comun import ConfirmDwInsertRequest
    from routers.dataops.consolidacion import _consolidar

    db = Session()
    t0 = time.perf_counter()
    por_libro = []
    beto_totales = Counter()
    try:
        user = db.query(User).first()
        for idx, (nombre, tf) in enumerate(LIBROS, 1):
            ruta = UPLOADS_DIR / nombre
            if not ruta.exists():
                print(f"[SKIP] No encontrado: {ruta}", flush=True)
                continue
            t_lib = time.perf_counter()
            file_bytes = _recortar_xlsx(ruta, recortar_filas) if recortar_filas else ruta.read_bytes()
            lote = Lote(estado="EN_PROCESO", total_archivos=1, institucion="GiraGroup Posgrado", periodo="2026-1")
            db.add(lote)
            db.flush()
            res_ing = IngestionService.procesar_archivo_ingesta(
                db=db,
                file_bytes=file_bytes,
                filename=nombre,
                id_lote=lote.id_lote,
                tipo_fuente=tf,
                tipo_escala="CENTESIMAL_100" if tf in ("ACTA", "MOODLE") else None,
            )
            db.commit()
            doc_id = res_ing.get("id_documento")
            res_cons = _consolidar(
                ConfirmDwInsertRequest(id_lote=lote.id_lote, solo_revision=False, en_segundo_plano=False),
                db,
                user,
            )
            dt_lib = round(time.perf_counter() - t_lib, 2)
            beto_info = res_cons.get("beto") or {}
            for k_b, v_b in beto_info.items():
                if isinstance(v_b, (int, float)):
                    beto_totales[k_b] += v_b
            por_libro.append({
                "archivo": nombre,
                "tipo_fuente": tf,
                "id_documento": doc_id,
                "tiempo_s": dt_lib,
                "inserted_dw": res_cons.get("inserted_dw"),
                "inserted_revision": res_cons.get("inserted_revision"),
                "descartados_ruido": res_cons.get("descartados_ruido"),
                "sent_hitl": res_cons.get("sent_hitl"),
                "beto": beto_info,
            })
            print(
                f"[{modo}][{idx}/10] {nombre}: ins={res_cons.get('inserted_dw')} "
                f"rev={res_cons.get('inserted_revision')} hitl={res_cons.get('sent_hitl')} ({dt_lib}s)",
                flush=True,
            )
    finally:
        db.close()
        engine.dispose()
        cat_engine.dispose()
        cs_mod.obtener_indices = orig_obtener
        cons_mod.obtener_indices = orig_obtener
        cons_mod.indices_cascada = orig_cascada

    tiempo_total = round(time.perf_counter() - t0, 2)

    # Consultas de auditoría sobre db_name
    tablas = [
        "fact_rendimiento_academico", "fact_situacion_financiera", "fact_evaluacion_docente",
        "fact_marketing", "fact_rentabilidad", "fact_costo_programa", "fact_techo_convenio",
        "fact_planificacion_programa", "dim_estudiante", "dim_docente", "dim_modulo",
        "dim_tiempo", "dim_origen_documental", "bridge_modulo_docente",
        "stg_entidad_no_resuelta", "log_inconsistencias",
    ]
    conteos = {t: int(_sql_one(db_name, f"SELECT count(*) FROM public.{t}") or 0) for t in tablas}

    stg_motivos = [
        {"motivo": r[0], "archivo": r[1], "estado_resolucion": r[2], "total": int(r[3])}
        for r in _sql_all(db_name, """
            SELECT s.motivo, COALESCE(d.nombre_archivo, '<sin_doc>'), s.estado_resolucion, count(*)
            FROM public.stg_entidad_no_resuelta s
            LEFT JOIN public.dim_origen_documental d ON d.id_documento = s.id_documento
            WHERE s.tipo_entidad <> 'RUIDO'
            GROUP BY 1, 2, 3
            ORDER BY 4 DESC
        """)
    ]

    pendientes_tot = int(_sql_one(db_name, """
        SELECT count(*) FROM public.stg_entidad_no_resuelta
        WHERE resuelto = FALSE AND tipo_entidad <> 'RUIDO'
    """) or 0)

    arca_rev = int(_sql_one(db_name, """
        SELECT count(*) FROM public.fact_rendimiento_academico f
        JOIN public.dim_origen_documental d ON d.id_documento = f.id_documento
        WHERE d.nombre_archivo ILIKE '%ARCA%' AND f.requiere_revision IS TRUE
    """) or 0)
    arca_tot = int(_sql_one(db_name, """
        SELECT count(*) FROM public.fact_rendimiento_academico f
        JOIN public.dim_origen_documental d ON d.id_documento = f.id_documento
        WHERE d.nombre_archivo ILIKE '%ARCA%'
    """) or 0)

    placeholders_dim = int(_sql_one(db_name, """
        SELECT count(*) FROM public.dim_estudiante
        WHERE nombre_completo ~* '^Estudiante\\s+(CI\\s*[:#-]?\\s*)?[0-9]'
    """) or 0)

    placeholders_fact_aca = int(_sql_one(db_name, """
        SELECT count(*) FROM public.fact_rendimiento_academico f
        JOIN public.dim_estudiante e ON e.id_estudiante = f.id_estudiante
        WHERE e.nombre_completo ~* '^Estudiante\\s+(CI\\s*[:#-]?\\s*)?[0-9]'
    """) or 0)

    placeholders_fact_fin = int(_sql_one(db_name, """
        SELECT count(*) FROM public.fact_situacion_financiera f
        JOIN public.dim_estudiante e ON e.id_estudiante = f.id_estudiante
        WHERE e.nombre_completo ~* '^Estudiante\\s+(CI\\s*[:#-]?\\s*)?[0-9]'
    """) or 0)

    ci_discord_ph = int(_sql_one(db_name, """
        SELECT count(*) FROM public.stg_entidad_no_resuelta
        WHERE motivo = 'CI_NOMBRE_DISCORDANTE'
          AND mejor_candidato ~* '^Estudiante\\s+(CI\\s*[:#-]?\\s*)?[0-9]'
    """) or 0)

    homonimia_100 = int(_sql_one(db_name, """
        SELECT count(*) FROM public.stg_entidad_no_resuelta
        WHERE motivo = 'HOMONIMIA' AND score_fuzzy = 100.0
    """) or 0)

    eval_baja_conf = int(_sql_one(db_name, """
        SELECT count(*) FROM public.stg_entidad_no_resuelta s
        JOIN public.dim_origen_documental d ON d.id_documento = s.id_documento
        WHERE d.nombre_archivo ILIKE '%Evaluaci%Docente%Unifranz%'
          AND s.motivo = 'BAJA_CONFIANZA_IA'
    """) or 0)

    desacuerdos_log = int(_sql_one(db_name, """
        SELECT count(*) FROM public.log_inconsistencias
        WHERE tipo_regla = 'DESACUERDO_REGLA_BETO'
    """) or 0)

    placeholders_hidratados = int(_sql_one(db_name, """
        SELECT count(*) FROM public.log_inconsistencias
        WHERE tipo_regla = 'PLACEHOLDER_HIDRATADO'
    """) or 0)

    sug_motivos_invalidos = int(_sql_one(db_name, """
        SELECT count(*) FROM public.stg_entidad_no_resuelta
        WHERE payload_json ? 'sugerencias'
          AND motivo NOT IN ('ENTIDAD_NUEVA', 'HOMONIMIA', 'POS_NO_EN_DIM_MODULO', 'BAJA_CONFIANZA_IA')
    """) or 0)

    bloques_con_ctx = int(_sql_one(db_name, """
        SELECT count(*) FROM public.staging_registros_crudos
        WHERE payload_json ? 'contexto_hoja'
    """) or 0)

    bloques_con_texto_crudo = int(_sql_one(db_name, """
        SELECT count(*) FROM public.staging_registros_crudos
        WHERE payload_json ? 'contexto_hoja_texto'
    """) or 0)

    return {
        "modo": modo,
        "db_name": db_name,
        "recortar_filas": recortar_filas,
        "timestamp": datetime.now().isoformat(),
        "tiempo_total_seg": tiempo_total,
        "rnf03_cumplido_15m": tiempo_total < 900.0,
        "rnf03_aceptable_20m": tiempo_total < 1200.0,
        "por_libro": por_libro,
        "conteos": conteos,
        "bandeja_pendientes_no_ruido": pendientes_tot,
        "stg_por_motivo_archivo": stg_motivos,
        "beto_totales": dict(beto_totales),
        "auditoria": {
            "arca_total_hechos": arca_tot,
            "arca_hechos_en_revision": arca_rev,
            "eval_unifranz_baja_confianza_ia": eval_baja_conf,
            "ci_nombre_discordante_con_placeholder": ci_discord_ph,
            "placeholders_hidratados_log": placeholders_hidratados,
            "placeholders_dim_estudiante": placeholders_dim,
            "placeholders_en_fact_aca": placeholders_fact_aca,
            "placeholders_en_fact_fin": placeholders_fact_fin,
            "homonimia_score_100": homonimia_100,
            "desacuerdos_regla_beto_log": desacuerdos_log,
            "sugerencias_en_motivos_no_identidad": sug_motivos_invalidos,
            "bloques_con_contexto_hoja": bloques_con_ctx,
            "bloques_con_contexto_hoja_texto_crudo": bloques_con_texto_crudo,
        },
    }


def main():
    modo_run = sys.argv[1] if len(sys.argv) > 1 else "all"
    if modo_run in ("all", "ab"):
        print("=== F6-4b Parte 1: Lote 10 archivos (A vs B) ===", flush=True)
        res_a = correr_lote("f6_ap_a", "A", recortar_filas=350)
        res_b = correr_lote("f6_ap_b", "B", recortar_filas=350)
        aporte = {
            "etiqueta": "F6-4b regresión A vs B (10 archivos, tmpfs)",
            "modelo_indice": os.getenv("BETO_MODELO_VERSION", "beto-v2-f6"),
            "timestamp": datetime.now().isoformat(),
            "referencia_f3_modo_b_bandeja": 676,
            "modos": {"A": res_a, "B": res_b},
        }
        (OUT_DIR / "f6_aporte_10archivos.json").write_text(
            json.dumps(aporte, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print("Guardado f6_aporte_10archivos.json", flush=True)

    if modo_run in ("all", "completo"):
        print("=== F6-4b Parte 2: Corrida completa 10 libros (tmpfs) ===", flush=True)
        res_full = correr_lote("f6_completo", "B", recortar_filas=None)
        (OUT_DIR / "f6_completo.json").write_text(
            json.dumps(res_full, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        aud = res_full["auditoria"]
        (OUT_DIR / "f6_auditoria_dw.json").write_text(
            json.dumps({
                "fase": "F6-4b",
                "timestamp": res_full["timestamp"],
                "tiempo_total_seg": res_full["tiempo_total_seg"],
                "rnf03_cumplido_15m": res_full["rnf03_cumplido_15m"],
                "rnf03_aceptable_20m": res_full["rnf03_aceptable_20m"],
                "conteos": res_full["conteos"],
                "bandeja_pendientes_no_ruido": res_full["bandeja_pendientes_no_ruido"],
                "auditoria": aud,
                "beto_totales": res_full["beto_totales"],
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # Diffs específicos requeridos por el plan
        (OUT_DIR / "f6_encuestas_diff.json").write_text(json.dumps({
            "tarea": "F6-2a",
            "antes_f5r_baja_confianza_ia": 573,
            "antes_f5v_baja_confianza_ia": 4240,
            "despues_f6_baja_confianza_ia": aud["eval_unifranz_baja_confianza_ia"],
            "fact_evaluacion_docente_total": res_full["conteos"]["fact_evaluacion_docente"],
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        (OUT_DIR / "f6_placeholders_diff.json").write_text(json.dumps({
            "tarea": "F6-2b",
            "despues_ci_nombre_discordante_placeholder": aud["ci_nombre_discordante_con_placeholder"],
            "placeholders_hidratados_log": aud["placeholders_hidratados_log"],
            "placeholders_restantes_dim_estudiante": aud["placeholders_dim_estudiante"],
            "placeholders_en_fact_aca": aud["placeholders_en_fact_aca"],
            "placeholders_en_fact_fin": aud["placeholders_en_fact_fin"],
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        (OUT_DIR / "f6_homonimia_diff.json").write_text(json.dumps({
            "tarea": "F6-2c",
            "despues_homonimia_score_100": aud["homonimia_score_100"],
            "umbrales_invariantes": {"homonimia_pct": 90.0, "persona_directa": 0.92},
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        (OUT_DIR / "f6_arca_cruce_diff.json").write_text(json.dumps({
            "tarea": "F6-3a",
            "antes_f5v_arca_en_revision": 14265,
            "despues_f6_arca_en_revision": aud["arca_hechos_en_revision"],
            "arca_total_hechos": aud["arca_total_hechos"],
            "reduccion_absoluta": 14265 - aud["arca_hechos_en_revision"],
            "reduccion_pct": round((14265 - aud["arca_hechos_en_revision"]) / 14265 * 100.0, 2),
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        (OUT_DIR / "f6_beto_rol_diff.json").write_text(json.dumps({
            "tarea": "F6-3b",
            "beto_acuerdo_qc_solo_fuzzy": True,
            "beto_rescate_academico": True,
            "beto_sugerencia_corte_similitud": 80.0,
            "desacuerdos_regla_beto_log": aud["desacuerdos_regla_beto_log"],
            "sugerencias_en_motivos_no_identidad": aud["sugerencias_en_motivos_no_identidad"],
            "beto_totales": res_full["beto_totales"],
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Guardados f6_completo.json, f6_auditoria_dw.json y diffs F6.", flush=True)


if __name__ == "__main__":
    main()
