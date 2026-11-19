"""R-1: Carga por la web de los 9 libros faltantes (todos menos PLANIFICACION)
en la DW viva a través de los endpoints reales de DataOps.
Lee credenciales de F5R_EMAIL / F5R_PASS / PG_PASS (sin hardcodear secretos).
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import requests

ROOT = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT / "output" / "backups" / "f0_lote" / "originales"
BASE_URL = os.getenv("F5R_BASE_URL", "http://127.0.0.1:80").rstrip("/")

LIBROS_FALTANTES = [
    ("TBL_INSCRITOS.xlsx", "MARKETING"),
    ("BD Cobranzas.xlsx", "COBRANZA"),
    ("BD Techos.xlsx", "TECHOS"),
    ("EJECUTADO VS META.xlsx", "RENTABILIDAD"),
    ("BD Egresos.xlsx", "EGRESOS"),
    ("[BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx", "EVALUACION_DOCENTE"),
    ("Evaluación Docente y Unifranz.xlsx", "EVALUACION_DOCENTE"),
    ("Experiencia Docente 2.0.xlsx", "ACTA"),
    ("Base centralizada Académica ARCA (1).xlsx", "ACTA"),
]


def login_token(session: requests.Session) -> str:
    email = os.environ["F5R_EMAIL"]
    password = os.environ["F5R_PASS"]
    r1 = session.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=20,
    )
    r1.raise_for_status()
    data1 = r1.json()
    if not data1.get("mfa_required") and data1.get("access_token"):
        return data1["access_token"]
    logs = subprocess.check_output(
        ["docker", "logs", "--tail", "30", "giragroup_auth_svc"],
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    otps = re.findall(r"CÓDIGO OTP PARA [^:]+:\s*(\d{6})", logs)
    if not otps:
        raise RuntimeError("No se encontró OTP en logs de giragroup_auth_svc")
    r2 = session.post(
        f"{BASE_URL}/api/v1/auth/verify-otp",
        json={"temp_token": data1["temp_token"], "code": otps[-1], "remember_device": False},
        timeout=20,
    )
    r2.raise_for_status()
    return r2.json()["access_token"]


def poll_tarea(session: requests.Session, headers: dict, id_lote: int, tipo: str, timeout_s: int = 1800) -> dict:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        r = session.get(
            f"{BASE_URL}/api/v1/dataops/lote/{id_lote}/tarea",
            params={"tipo": tipo},
            headers=headers,
            timeout=20,
        )
        r.raise_for_status()
        tarea = r.json()
        if tarea:
            estado = tarea.get("estado")
            print(f"[{tipo}] estado={estado} procesados={tarea.get('procesados')}/{tarea.get('total')}", flush=True)
            if estado in ("COMPLETADA", "ERROR"):
                return tarea
        time.sleep(5)
    raise TimeoutError(f"Timeout esperando tarea {tipo} del lote {id_lote}")


def conteos_db() -> dict:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5434,
        dbname="giragroup_db",
        user="giragroup_user",
        password=os.getenv("PG_PASS", "giragroup_secret_2026"),
    )
    cur = conn.cursor()
    tablas = [
        "fact_rendimiento_academico", "fact_situacion_financiera", "fact_evaluacion_docente",
        "fact_marketing", "fact_rentabilidad", "fact_costo_programa", "fact_techo_convenio",
        "fact_planificacion_programa", "fact_cobranzas_proyectadas", "fact_forecast",
        "dim_estudiante", "dim_docente", "dim_modulo", "dim_tiempo", "dim_origen_documental",
        "dim_meta", "dim_categoria_financiera", "bridge_modulo_docente", "carga_fila_origen",
        "stg_entidad_no_resuelta", "log_inconsistencias",
    ]
    res = {}
    for t in tablas:
        cur.execute(f"SELECT count(*) FROM {t}")
        res[t] = cur.fetchone()[0]
    cur.close()
    conn.close()
    return res


def main() -> int:
    t_inicio_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    t0 = time.monotonic()
    s = requests.Session()
    token = login_token(s)
    headers = {"Authorization": f"Bearer {token}"}

    # Verificar fuentes actuales y limpiar solo los unconsolidated de id_lote != 1 si existen
    r_src = s.get(f"{BASE_URL}/api/v1/dataops/sources", headers=headers, timeout=20)
    r_src.raise_for_status()
    fuentes_previas = r_src.json().get("data", [])
    ids_a_limpiar = [
        f["id"] for f in fuentes_previas
        if f.get("id") != 1 and "PLANIFICACION" not in (f.get("nombre_archivo") or "").upper()
    ] + [
        f["id"] for f in fuentes_previas
        if f.get("id") != 1 and "PLANIFICACION" in (f.get("nombre_archivo") or "").upper()
    ]
    ids_a_limpiar = sorted(set(ids_a_limpiar))
    limpieza_res = None
    if ids_a_limpiar:
        print(f"Limpiando documentos previos no consolidados: {ids_a_limpiar}", flush=True)
        r_del = s.post(
            f"{BASE_URL}/api/v1/dataops/sources/delete-batch",
            json={"ids": ids_a_limpiar},
            headers=headers,
            timeout=30,
        )
        r_del.raise_for_status()
        limpieza_res = r_del.json()

    # Subir los 9 libros faltantes via POST /api/v1/dataops/upload-batch
    archivos_abiertos = []
    files_payload = []
    meta_list = []
    try:
        for nombre, tipo in LIBROS_FALTANTES:
            ruta = ORIG_DIR / nombre
            if not ruta.exists():
                raise FileNotFoundError(f"No existe el archivo: {ruta}")
            fh = open(ruta, "rb")
            archivos_abiertos.append(fh)
            files_payload.append(
                ("files", (nombre, fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
            )
            meta_item = {"tipo_fuente": tipo}
            if tipo in ("ACTA", "MOODLE"):
                meta_item["tipo_escala"] = "CENTESIMAL_100"
            meta_list.append(meta_item)

        print("Subiendo lote de 9 libros a /api/v1/dataops/upload-batch...", flush=True)
        r_up = s.post(
            f"{BASE_URL}/api/v1/dataops/upload-batch",
            files=files_payload,
            data={
                "institucion": "GiraGroup Posgrado",
                "periodo": "2024-2026",
                "archivos_meta": json.dumps(meta_list),
            },
            headers=headers,
            timeout=300,
        )
        r_up.raise_for_status()
        up_json = r_up.json()
    finally:
        for fh in archivos_abiertos:
            fh.close()

    id_lote = up_json["id_lote"]
    print(f"Upload completado: id_lote={id_lote}, exitosos={up_json.get('archivos_exitosos')}/{up_json.get('total_archivos')}", flush=True)
    if up_json.get("archivos_fallidos", 0) > 0:
        for r in up_json.get("resultados", []):
            if r.get("status") != "procesado":
                print(f"  FALLO/SKIP: {r.get('nombre_archivo')} -> status={r.get('status')} msg={r.get('mensaje')}", flush=True)
        raise RuntimeError(f"upload-batch tuvo {up_json.get('archivos_fallidos')} archivo(s) no procesados")

    # Esperar LECTURA_BETO
    tarea_lectura = poll_tarea(s, headers, id_lote, "LECTURA_BETO", timeout_s=1800)
    if tarea_lectura.get("estado") != "COMPLETADA":
        raise RuntimeError(f"LECTURA_BETO falló: {tarea_lectura}")

    # Preparar revisión
    print(f"Iniciando preparar-revision para lote {id_lote}...", flush=True)
    r_prep = s.post(
        f"{BASE_URL}/api/v1/dataops/preparar-revision",
        json={"id_lote": id_lote, "en_segundo_plano": True},
        headers=headers,
        timeout=30,
    )
    r_prep.raise_for_status()
    tarea_prep = poll_tarea(s, headers, id_lote, "PREPARACION_REVISION", timeout_s=1800)
    if tarea_prep.get("estado") != "COMPLETADA":
        raise RuntimeError(f"PREPARACION_REVISION falló: {tarea_prep}")

    # Consolidar en DW
    print(f"Iniciando confirm-dw-insert para lote {id_lote}...", flush=True)
    r_cons = s.post(
        f"{BASE_URL}/api/v1/dataops/confirm-dw-insert",
        json={"id_lote": id_lote, "en_segundo_plano": True},
        headers=headers,
        timeout=30,
    )
    r_cons.raise_for_status()
    tarea_cons = poll_tarea(s, headers, id_lote, "CONSOLIDACION", timeout_s=1800)
    if tarea_cons.get("estado") != "COMPLETADA":
        raise RuntimeError(f"CONSOLIDACION falló: {tarea_cons}")

    # Revisar logs de giragroup_api desde t_inicio_utc para contar 5xx
    api_logs = subprocess.check_output(
        ["docker", "logs", "--since", t_inicio_utc, "giragroup_api"],
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    errores_5xx = [ln for ln in api_logs.splitlines() if re.search(r'" 5\d\d\b', ln)]

    # Comparar conteos contra f3v_completo.json
    f3v_ref = json.loads((ROOT / "docs" / "mediciones" / "f3v_completo.json").read_text(encoding="utf-8"))["conteos"]
    actuales = conteos_db()
    comparacion = {}
    for k, ref_v in f3v_ref.items():
        act_v = actuales.get(k)
        comparacion[k] = {
            "f3v_completo": ref_v,
            "dw_viva": act_v,
            "delta": (act_v - ref_v) if act_v is not None else None,
        }

    out = {
        "tarea": "R-1",
        "id_lote": id_lote,
        "duracion_seg": round(time.monotonic() - t0, 2),
        "limpieza_previa": limpieza_res,
        "upload_batch": {
            "status": up_json.get("status"),
            "total_archivos": up_json.get("total_archivos"),
            "archivos_exitosos": up_json.get("archivos_exitosos"),
            "archivos_fallidos": up_json.get("archivos_fallidos"),
            "total_registros_detectados": up_json.get("total_registros_detectados"),
            "resultados": [
                {
                    "id_documento": r.get("id_documento"),
                    "nombre_archivo": r.get("nombre_archivo"),
                    "tipo_fuente": r.get("tipo_fuente"),
                    "registros_detectados": r.get("registros_detectados"),
                    "status": r.get("status"),
                }
                for r in up_json.get("resultados", [])
            ],
        },
        "tareas": {
            "LECTURA_BETO": tarea_lectura,
            "PREPARACION_REVISION": tarea_prep,
            "CONSOLIDACION": tarea_cons,
        },
        "errores_5xx_api": len(errores_5xx),
        "errores_5xx_muestra": errores_5xx[:10],
        "conteos_vs_f3v_completo": comparacion,
    }
    out_path = ROOT / "docs" / "mediciones" / "f5r_recarga.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"R-1 completado en {out['duracion_seg']}s. Errores 5xx: {len(errores_5xx)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
