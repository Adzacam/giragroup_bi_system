"""W-14: Recarga de la DW viva por el gateway HTTP con los 10 libros y verificación."""
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
UPLOADS_DIR = ROOT / "uploads" / "data"
MED_DIR = ROOT / "docs" / "mediciones"
DUMP_PRE = ROOT / "output" / "f3w" / "giragroup_db_pre_w14.dump"
BASE_URL = os.getenv("GIRA_GATEWAY_URL", "http://localhost/api/v1/dataops")
ENV = dict(os.environ, MSYS_NO_PATHCONV="1")

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

TABLAS = [
    "fact_rendimiento_academico",
    "fact_situacion_financiera",
    "fact_evaluacion_docente",
    "fact_marketing",
    "fact_rentabilidad",
    "fact_forecast",
    "fact_cobranzas_proyectadas",
    "fact_costo_programa",
    "fact_techo_convenio",
    "bridge_modulo_docente",
    "staging_registros_crudos",
    "stg_entidad_no_resuelta",
    "carga_fila_origen",
    "lote",
    "dim_origen_documental",
    "dim_modulo",
    "users",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def psql_conteos() -> dict:
    sql = " UNION ALL ".join(f"SELECT '{t}', count(*) FROM {t}" for t in TABLAS)
    out = subprocess.check_output(
        ["docker", "exec", "giragroup_db", "psql", "-U", "giragroup_user", "-d", "giragroup_db", "-Atc", sql],
        text=True,
        encoding="utf-8",
        env=ENV,
    )
    res = {}
    for line in out.strip().splitlines():
        if "|" in line:
            k, v = line.split("|", 1)
            res[k.strip()] = int(v.strip())
    return res


def poll_tarea(headers: dict, id_lote: int, tipo: str, timeout_s: int = 3600) -> dict:
    t0 = time.perf_counter()
    last_pct = -1
    while True:
        r = requests.get(
            f"{BASE_URL}/lote/{id_lote}/tarea",
            params={"tipo": tipo},
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if data is None:
            if time.perf_counter() - t0 > 60:
                raise RuntimeError(f"Tarea {tipo} para lote {id_lote} no aparecio en 60s")
            time.sleep(2)
            continue
        estado = data.get("estado")
        pct = data.get("progreso_pct") or data.get("porcentaje")
        if pct != last_pct:
            print(f"  [{tipo}] lote={id_lote} estado={estado} pct={pct} etapa={data.get('etapa_actual')}", flush=True)
            last_pct = pct
        if estado in ("COMPLETADA", "FALLIDA", "ERROR"):
            return data
        if time.perf_counter() - t0 > timeout_s:
            raise TimeoutError(f"Timeout esperando {tipo} en lote {id_lote}: {data}")
        time.sleep(3)


def main():
    token = os.environ["GIRA_TOKEN"].strip()
    headers = {"Authorization": f"Bearer {token}"}
    start_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conteos_antes = psql_conteos()
    dump_sha = sha256_file(DUMP_PRE)

    # 1. Subir los 10 libros en lote por el gateway HTTP
    files_payload = []
    data_payload = []
    opened = []
    try:
        for nombre, tf in LIBROS:
            p = UPLOADS_DIR / nombre
            f = p.open("rb")
            opened.append(f)
            files_payload.append(
                ("files", (nombre, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
            )
            data_payload.append(("source_types", tf))
            data_payload.append(("tipos_fuente", tf))
            data_payload.append(("tipos_escala", ""))
        data_payload.append(("institucion", "GiraGroup Posgrado"))
        data_payload.append(("periodo", "2026-1"))

        t0 = time.perf_counter()
        print("Subiendo 10 libros via POST /upload-batch ...", flush=True)
        resp_up = requests.post(
            f"{BASE_URL}/upload-batch",
            headers=headers,
            files=files_payload,
            data=data_payload,
            timeout=600,
        )
        resp_up.raise_for_status()
        up_json = resp_up.json()
        t_upload = round(time.perf_counter() - t0, 2)
        id_lote = up_json.get("id_lote") or up_json.get("lote_id")
        print(f"Upload OK en {t_upload}s -> id_lote={id_lote}", flush=True)
    finally:
        for f in opened:
            f.close()

    # 2. Esperar LECTURA_BETO
    t1 = time.perf_counter()
    tarea_beto = poll_tarea(headers, id_lote, "LECTURA_BETO", timeout_s=3600)
    t_beto = round(time.perf_counter() - t1, 2)
    if tarea_beto.get("estado") != "COMPLETADA":
        raise RuntimeError(f"LECTURA_BETO fallo: {tarea_beto}")

    # 3. Fase A: preparar-revision
    t2 = time.perf_counter()
    r_prep = requests.post(
        f"{BASE_URL}/preparar-revision",
        headers=headers,
        json={"id_lote": id_lote, "solo_revision": True, "en_segundo_plano": True},
        timeout=60,
    )
    r_prep.raise_for_status()
    prep_json = r_prep.json()
    if prep_json.get("status") != "already_prepared":
        tarea_prep = poll_tarea(headers, id_lote, "PREPARACION_REVISION", timeout_s=1800)
        if tarea_prep.get("estado") != "COMPLETADA":
            raise RuntimeError(f"PREPARACION_REVISION fallo: {tarea_prep}")
    else:
        tarea_prep = {"estado": "already_prepared"}
    t_prep = round(time.perf_counter() - t2, 2)

    # Consultar resumen de bandeja antes de consolidar
    r_sum = requests.get(f"{BASE_URL}/lote/{id_lote}/contexto", headers=headers, timeout=30)
    ctx_antes_consolidar = r_sum.json() if r_sum.ok else {}

    # 4. Fase B: confirm-dw-insert (consolidacion en segundo plano)
    t3 = time.perf_counter()
    r_cons = requests.post(
        f"{BASE_URL}/confirm-dw-insert",
        headers=headers,
        json={"id_lote": id_lote, "en_segundo_plano": True},
        timeout=60,
    )
    r_cons.raise_for_status()
    tarea_cons = poll_tarea(headers, id_lote, "CONSOLIDACION", timeout_s=3600)
    t_cons = round(time.perf_counter() - t3, 2)
    if tarea_cons.get("estado") != "COMPLETADA":
        raise RuntimeError(f"CONSOLIDACION fallo: {tarea_cons}")

    # 5. Verificacion en giragroup_db
    conteos_despues = psql_conteos()
    docs_sql = subprocess.check_output(
        [
            "docker", "exec", "giragroup_db", "psql", "-U", "giragroup_user", "-d", "giragroup_db", "-Atc",
            "SELECT id_documento, nombre_archivo, tipo_fuente, estado_procesamiento, id_lote FROM dim_origen_documental ORDER BY id_documento;",
        ],
        text=True,
        encoding="utf-8",
        env=ENV,
    ).strip().splitlines()
    docs_info = []
    for line in docs_sql:
        parts = line.split("|")
        if len(parts) >= 5:
            docs_info.append({
                "id_documento": int(parts[0]),
                "nombre_archivo": parts[1],
                "tipo_fuente": parts[2],
                "estado_procesamiento": parts[3],
                "id_lote": int(parts[4]),
            })

    cfo_sql = subprocess.check_output(
        [
            "docker", "exec", "giragroup_db", "psql", "-U", "giragroup_user", "-d", "giragroup_db", "-Atc",
            "SELECT tabla, count(*), count(distinct id_documento) FROM carga_fila_origen GROUP BY tabla ORDER BY tabla;",
        ],
        text=True,
        encoding="utf-8",
        env=ENV,
    ).strip().splitlines()
    cfo_por_tabla = {}
    for line in cfo_sql:
        parts = line.split("|")
        if len(parts) == 3:
            cfo_por_tabla[parts[0]] = {"filas": int(parts[1]), "docs_distintos": int(parts[2])}

    # Revisar logs de giragroup_api buscando errores 5xx desde start_iso
    logs = subprocess.check_output(
        ["docker", "logs", "--since", start_iso, "giragroup_api"],
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=ENV,
    )
    errores_5xx = [
        ln for ln in logs.splitlines()
        if any(code in ln for code in (" 500 ", " 502 ", " 503 ", " 504 ", "HTTP/1.1\" 5"))
    ]

    w13_json = json.loads((MED_DIR / "f3w_carga_fila_origen.json").read_text(encoding="utf-8"))
    w13_conteos = w13_json["conteos_hechos_10_libros"]
    comparacion_w13 = {}
    for tabla, w13_val in w13_conteos.items():
        viva_val = conteos_despues.get(tabla, 0)
        comparacion_w13[tabla] = {
            "w13_clon": w13_val,
            "w14_dw_viva": viva_val,
            "delta": viva_val - w13_val,
        }

    out = {
        "tarea": "W-14 (Recarga de la DW viva con los 10 libros por el gateway web)",
        "fecha": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dump_previo_path": "output/f3w/giragroup_db_pre_w14.dump",
        "dump_previo_sha256": dump_sha,
        "id_lote": id_lote,
        "tiempos_referencia_no_rnf03_seg": {
            "upload_batch": t_upload,
            "lectura_beto": t_beto,
            "preparacion_revision": t_prep,
            "consolidacion": t_cons,
            "total": round(t_upload + t_beto + t_prep + t_cons, 2),
        },
        "dw_viva_antes": conteos_antes,
        "dw_viva_despues": conteos_despues,
        "documentos": docs_info,
        "documentos_completados": sum(1 for d in docs_info if d["estado_procesamiento"] == "COMPLETADA"),
        "carga_fila_origen_por_tabla": cfo_por_tabla,
        "comparacion_vs_w13": comparacion_w13,
        "errores_5xx_api_count": len(errores_5xx),
        "errores_5xx_api": errores_5xx[:20],
        "pendientes_revision_antes_consolidar": ctx_antes_consolidar.get("pendientes_revision"),
    }
    (MED_DIR / "f3w_recarga_dw_viva.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[W-14 OK] docs_completados:", out["documentos_completados"], "5xx:", len(errores_5xx), flush=True)


if __name__ == "__main__":
    main()
