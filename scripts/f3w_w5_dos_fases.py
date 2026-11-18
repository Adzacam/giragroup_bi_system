"""W-5: Verificación de consolidación en dos fases (Fase A solo_revision + Fase B carga)
sobre clones limpios de f3w_vacio en beto_pg_f3w (127.0.0.1:55634). Nunca toca giragroup_db.

Genera docs/mediciones/f3w_dos_fases.json.
"""
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
MED_DIR = ROOT / "docs" / "mediciones"
SLICES_DIR = ROOT / "output" / "backups" / "f0_lote" / "corridas" / "f0_a0_llena_r1_interrumpida" / "landing" / "1"
ENV = dict(os.environ, MSYS_NO_PATHCONV="1")

ARCHIVOS_PRUEBA = [
    ("TBL_INSCRITOS.xlsx", "ADMISION"),
    ("BD Cobranzas.xlsx", "COBRANZA"),
    ("_BBDD_ ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx", "EVALUACION_DOCENTE"),
    ("Base centralizada Académica ARCA (1).xlsx", "ACTA"),
]

FACT_TABLES = [
    "fact_rendimiento_academico",
    "fact_situacion_financiera",
    "fact_evaluacion_docente",
    "fact_marketing",
    "fact_rentabilidad",
    "fact_forecast",
    "fact_cobranzas_proyectadas",
    "fact_costo_programa",
    "fact_techo_convenio",
]

OTHER_TABLES = [
    "staging_registros_crudos",
    "stg_entidad_no_resuelta",
    "log_inconsistencias",
    "log_pipeline_ingesta",
    "dim_estudiante",
    "dim_modulo",
    "dim_docente",
    "dim_origen_documental",
]


def sh(cmd, check=True):
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    if check and r.returncode != 0:
        raise RuntimeError(f"Comando falló ({' '.join(cmd)}): {r.stderr or r.stdout}")
    return r.stdout


def crear_clon(db_name: str):
    sh(["docker", "exec", "beto_pg_f3w", "psql", "-U", "giragroup_user", "-d", "postgres", "-c",
        f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE);"])
    sh(["docker", "exec", "beto_pg_f3w", "psql", "-U", "giragroup_user", "-d", "postgres", "-c",
        f"CREATE DATABASE {db_name} TEMPLATE f3w_vacio;"])


def conteos_db(db_name: str) -> dict:
    tablas = FACT_TABLES + OTHER_TABLES
    sql = " UNION ALL ".join(f"SELECT '{t}', count(*) FROM {t}" for t in tablas)
    out = sh(["docker", "exec", "beto_pg_f3w", "psql", "-U", "giragroup_user", "-d", db_name, "-Atc", sql])
    res = {}
    for line in out.strip().splitlines():
        if "|" in line:
            k, v = line.split("|", 1)
            res[k.strip()] = int(v.strip())
    return res


def casos_pendientes_db(db_name: str) -> list:
    sql = (
        "SELECT id_documento, COALESCE(motivo,''), COALESCE(texto_original,''), COALESCE(tipo_entidad,'') "
        "FROM stg_entidad_no_resuelta WHERE COALESCE(resuelto, false) = false "
        "ORDER BY id_documento, motivo, texto_original;"
    )
    out = sh(["docker", "exec", "beto_pg_f3w", "psql", "-U", "giragroup_user", "-d", db_name, "-Atc", sql])
    return [tuple(line.split("|", 3)) for line in out.strip().splitlines() if line]


def ejecutar_escenario(db_name: str, modo: str):
    """Ejecuta en subproceso Python aislado con DATABASE_URL apuntando a db_name en beto_pg_f3w."""
    script = f"""
import os, sys, json, time
os.environ["DATABASE_URL"] = "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55634/{db_name}"
os.environ["BETO_CASCADA_FINAL"] = "0"
os.environ["BETO_ACUERDO_QC"] = "0"
os.environ["BETO_SUGERENCIA_HITL"] = "0"
sys.path.insert(0, {repr(str(BACKEND_DIR))})
sys.path.insert(0, {repr(str(ROOT / 'pipeline'))})

from pathlib import Path
from sqlalchemy import text
from core.database import SessionLocal
from models.lote import Lote
from models.user import User
from services.ingestion_service import IngestionService
from routers.dataops._comun import ConfirmDwInsertRequest
from routers.dataops import consolidacion

db = SessionLocal()
try:
    user = db.query(User).first()
    lote = Lote(institucion="GiraGroup Posgrado", periodo="2025-Q1", estado="EN_PROCESO", total_archivos=2)
    db.add(lote)
    db.commit()
    db.refresh(lote)
    id_lote = lote.id_lote

    archivos = {json.dumps(ARCHIVOS_PRUEBA)}
    slices_dir = Path({repr(str(SLICES_DIR))})
    for fname, tfuente in archivos:
        fpath = slices_dir / fname
        content = fpath.read_bytes()
        IngestionService.procesar_archivo_ingesta(
            db,
            file_bytes=content,
            filename=fname,
            id_lote=id_lote,
            tipo_fuente=tfuente,
            tipo_escala="CENTESIMAL_100",
        )
    db.commit()

    out = {{"id_lote": id_lote}}
    if {repr(modo)} == "actual":
        t0 = time.perf_counter()
        res = consolidacion.confirm_dw_insert(
            ConfirmDwInsertRequest(id_lote=id_lote, solo_revision=False, en_segundo_plano=False),
            db=db,
            current_user=user,
        )
        out["tiempo_s"] = round(time.perf_counter() - t0, 2)
        out["res"] = res
    elif {repr(modo)} == "fase_a":
        from services import tareas_dataops
        t0 = time.perf_counter()
        res = consolidacion.preparar_revision(
            ConfirmDwInsertRequest(id_lote=id_lote, en_segundo_plano=True),
            db=db,
            current_user=user,
        )
        assert res.get("status") == "accepted", f"Esperado accepted, recibido: {{res}}"
        tarea_id = res["tarea_id"]
        for _ in range(600):
            t_info = tareas_dataops.obtener(tarea_id)
            if t_info and t_info["estado"] != "EN_CURSO":
                break
            time.sleep(0.5)
        assert t_info and t_info["estado"] == "COMPLETADA", f"Tarea Fase A no completó: {{t_info}}"
        out["tiempo_s"] = round(time.perf_counter() - t0, 2)
        out["res"] = t_info.get("resultado") or res
        out["tarea_fase_a"] = {{"id": tarea_id, "tipo": t_info["tipo"], "estado": t_info["estado"]}}
    elif {repr(modo)} == "fase_b":
        id_lote = db.query(Lote).order_by(Lote.id_lote.desc()).first().id_lote
        # note: reuse existing lote if already ingested
        t0 = time.perf_counter()
        res = consolidacion.confirm_dw_insert(
            ConfirmDwInsertRequest(id_lote=1, solo_revision=False, en_segundo_plano=False),
            db=db,
            current_user=user,
        )
        out["tiempo_s"] = round(time.perf_counter() - t0, 2)
        out["res"] = res
    print("RESULTADO_JSON:" + json.dumps(out, default=str))
finally:
    db.close()
"""
    r = subprocess.run(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-c", script],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV,
    )
    if r.returncode != 0:
        raise RuntimeError(f"Subproceso ({modo}) falló:\nSTDOUT:\n{r.stdout[-1500:]}\nSTDERR:\n{r.stderr[-1500:]}")
    for line in r.stdout.splitlines():
        if line.startswith("RESULTADO_JSON:"):
            return json.loads(line[len("RESULTADO_JSON:"):])
    raise RuntimeError(f"No se encontró RESULTADO_JSON en salida ({modo}): {r.stdout[-1000:]}")


def ejecutar_fase_b(db_name: str, id_lote: int):
    script = f"""
import os, sys, json, time
os.environ["DATABASE_URL"] = "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55634/{db_name}"
os.environ["BETO_CASCADA_FINAL"] = "0"
os.environ["BETO_ACUERDO_QC"] = "0"
os.environ["BETO_SUGERENCIA_HITL"] = "0"
sys.path.insert(0, {repr(str(BACKEND_DIR))})
sys.path.insert(0, {repr(str(ROOT / 'pipeline'))})

from core.database import SessionLocal
from models.user import User
from routers.dataops._comun import ConfirmDwInsertRequest
from routers.dataops import consolidacion

db = SessionLocal()
try:
    user = db.query(User).first()
    t0 = time.perf_counter()
    res = consolidacion.confirm_dw_insert(
        ConfirmDwInsertRequest(id_lote={id_lote}, solo_revision=False, en_segundo_plano=False),
        db=db,
        current_user=user,
    )
    out = {{"tiempo_s": round(time.perf_counter() - t0, 2), "res": res}}
    print("RESULTADO_JSON:" + json.dumps(out, default=str))
finally:
    db.close()
"""
    r = subprocess.run(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-c", script],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV,
    )
    if r.returncode != 0:
        raise RuntimeError(f"Subproceso (fase_b) falló:\nSTDOUT:\n{r.stdout[-1500:]}\nSTDERR:\n{r.stderr[-1500:]}")
    for line in r.stdout.splitlines():
        if line.startswith("RESULTADO_JSON:"):
            return json.loads(line[len("RESULTADO_JSON:"):])
    raise RuntimeError(f"No se encontró RESULTADO_JSON en fase_b: {r.stdout[-1000:]}")


def main():
    print("1. Creando clones limpios en beto_pg_f3w...", flush=True)
    crear_clon("f3w_w5_actual")
    crear_clon("f3w_w5_dosfases")

    print("2. Ejecutando consolidación actual (1 fase) en f3w_w5_actual...", flush=True)
    res_actual = ejecutar_escenario("f3w_w5_actual", "actual")
    conteos_actual = conteos_db("f3w_w5_actual")
    casos_actual = casos_pendientes_db("f3w_w5_actual")

    print("3. Ejecutando Fase A (solo_revision=True) en f3w_w5_dosfases...", flush=True)
    res_fase_a = ejecutar_escenario("f3w_w5_dosfases", "fase_a")
    conteos_tras_a = conteos_db("f3w_w5_dosfases")
    casos_tras_a = casos_pendientes_db("f3w_w5_dosfases")

    print("4. Ejecutando Fase B (carga DW) en f3w_w5_dosfases...", flush=True)
    res_fase_b = ejecutar_fase_b("f3w_w5_dosfases", res_fase_a["id_lote"])
    conteos_tras_b = conteos_db("f3w_w5_dosfases")
    casos_tras_b = casos_pendientes_db("f3w_w5_dosfases")

    hechos_tras_a = {t: conteos_tras_a[t] for t in FACT_TABLES}
    hechos_actual = {t: conteos_actual[t] for t in FACT_TABLES}
    hechos_tras_b = {t: conteos_tras_b[t] for t in FACT_TABLES}

    diff_casos_a_vs_actual = len(list((Counter(casos_tras_a) - Counter(casos_actual)).elements())) + len(
        list((Counter(casos_actual) - Counter(casos_tras_a)).elements())
    )
    diff_hechos_b_vs_actual = {t: hechos_tras_b[t] - hechos_actual[t] for t in FACT_TABLES}

    medicion = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "contenedor": "beto_pg_f3w",
        "puerto": 55634,
        "subconjunto": [a[0] for a in ARCHIVOS_PRUEBA],
        "consolidacion_actual": {
            "tiempo_s": res_actual["tiempo_s"],
            "hechos": hechos_actual,
            "stg_entidad_no_resuelta_total": conteos_actual["stg_entidad_no_resuelta"],
            "casos_pendientes_total": len(casos_actual),
            "log_inconsistencias": conteos_actual["log_inconsistencias"],
            "dim_estudiante": conteos_actual["dim_estudiante"],
        },
        "fase_a_solo_revision": {
            "tiempo_s": res_fase_a["tiempo_s"],
            "hechos": hechos_tras_a,
            "total_hechos_tras_a": sum(hechos_tras_a.values()),
            "casos_pendientes_total": len(casos_tras_a),
            "diferencia_casos_vs_actual": diff_casos_a_vs_actual,
        },
        "fase_b_carga_dw": {
            "tiempo_s": res_fase_b["tiempo_s"],
            "hechos": hechos_tras_b,
            "diferencia_hechos_vs_actual": diff_hechos_b_vs_actual,
            "stg_entidad_no_resuelta_total": conteos_tras_b["stg_entidad_no_resuelta"],
            "casos_pendientes_total": len(casos_tras_b),
            "log_inconsistencias": conteos_tras_b["log_inconsistencias"],
            "dim_estudiante": conteos_tras_b["dim_estudiante"],
        },
        "criterios_w5": {
            "hechos_tras_a_igual_0": sum(hechos_tras_a.values()) == 0,
            "casos_a_igual_actual": diff_casos_a_vs_actual == 0,
            "hechos_b_igual_actual": all(v == 0 for v in diff_hechos_b_vs_actual.values()),
            "stg_total_igual_actual": conteos_tras_b["stg_entidad_no_resuelta"] == conteos_actual["stg_entidad_no_resuelta"],
            "logs_igual_actual": conteos_tras_b["log_inconsistencias"] == conteos_actual["log_inconsistencias"],
        },
    }

    out_path = MED_DIR / "f3w_dos_fases.json"
    out_path.write_text(json.dumps(medicion, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Escrito {out_path}", flush=True)
    print(json.dumps(medicion["criterios_w5"], indent=2, ensure_ascii=False), flush=True)
    if not all(medicion["criterios_w5"].values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
