"""W-0 (Línea base + beto_pg_f3w) y W-0b (Purga del lote #18 en la DW viva con dump previo).
Uso:
  $env:ADMIN_EMAIL='...'; $env:ADMIN_PASS='...'; .venv\Scripts\python scripts/f3w_w0_y_w0b.py
"""
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_W = ROOT / "output" / "f3w"
OUT_W.mkdir(parents=True, exist_ok=True)
MED = ROOT / "docs" / "mediciones"
ENV = dict(os.environ, MSYS_NO_PATHCONV="1")

TABLAS_CONTEO = [
    "fact_rendimiento_academico",
    "fact_situacion_financiera",
    "fact_evaluacion_docente",
    "fact_marketing",
    "fact_rentabilidad",
    "fact_forecast",
    "fact_cobranzas_proyectadas",
    "fact_costo_programa",
    "fact_techo_convenio",
    "staging_registros_crudos",
    "stg_entidad_no_resuelta",
    "log_inconsistencias",
    "log_pipeline_ingesta",
    "carga_fila_origen",
    "lote",
    "dim_origen_documental",
    "dataops_tarea",
    "dim_modulo",
    "dim_estudiante",
    "dim_docente",
    "users",
]


def sh(cmd, check=True):
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    if check and r.returncode != 0:
        raise RuntimeError(f"Comando fallo ({' '.join(cmd)}): {r.stderr or r.stdout}")
    return r.stdout


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def conteos_db(container: str, db: str) -> dict:
    sql = " UNION ALL ".join(f"SELECT '{t}', count(*) FROM {t}" for t in TABLAS_CONTEO)
    out = sh(["docker", "exec", container, "psql", "-U", "giragroup_user", "-d", db, "-Atc", sql])
    res = {}
    for line in out.strip().splitlines():
        if "|" in line:
            k, v = line.split("|", 1)
            res[k.strip()] = int(v.strip())
    return res


def main():
    # 1. W-0: Linea base
    git_stat = sh(["git", "diff", "--stat"]).strip()
    dump_f3ub = ROOT / "output/f3ub/f3u_completo.dump"
    dump_sha = sha256_file(dump_f3ub)
    f3ub_json = json.loads((MED / "f3ub_completo.json").read_text(encoding="utf-8"))
    if dump_sha != f3ub_json["dump_sha256"]:
        raise RuntimeError(f"SHA mismatch f3u_completo.dump: {dump_sha} != {f3ub_json['dump_sha256']}")

    viva_lotes = sh(["docker", "exec", "giragroup_db", "psql", "-U", "giragroup_user", "-d", "giragroup_db", "-Atc",
                     "SELECT id_lote, estado, total_archivos FROM lote ORDER BY id_lote;"]).strip().splitlines()
    viva_docs = sh(["docker", "exec", "giragroup_db", "psql", "-U", "giragroup_user", "-d", "giragroup_db", "-Atc",
                    "SELECT id_documento, nombre_archivo, tipo_fuente, id_lote FROM dim_origen_documental ORDER BY id_documento;"]).strip().splitlines()
    viva_casos_motivo = sh(["docker", "exec", "giragroup_db", "psql", "-U", "giragroup_user", "-d", "giragroup_db", "-Atc",
                            "SELECT COALESCE(motivo,'NULL'), count(*) FROM stg_entidad_no_resuelta WHERE COALESCE(resuelto,false)=false GROUP BY motivo ORDER BY 2 DESC;"]).strip().splitlines()
    viva_antes = conteos_db("giragroup_db", "giragroup_db")

    # 2. Crear beto_pg_f3w (127.0.0.1:55634, tmpfs 6g)
    existing = sh(["docker", "ps", "-a", "--filter", "name=^/beto_pg_f3w$", "--format", "{{.Names}}"]).strip()
    if existing:
        sh(["docker", "rm", "-f", "beto_pg_f3w"])
    sh([
        "docker", "run", "-d", "--name", "beto_pg_f3w",
        "--network", "giragroup_bi_system_default",
        "-p", "127.0.0.1:55634:5432",
        "--tmpfs", "/var/lib/postgresql/data:size=6g",
        "-e", "POSTGRES_USER=giragroup_user",
        "-e", "POSTGRES_PASSWORD=tmpfs_local",
        "-e", "POSTGRES_DB=postgres",
        "postgres:16-alpine",
    ])
    # Esperar a que postgres este listo
    import time
    for _ in range(30):
        r = subprocess.run(["docker", "exec", "beto_pg_f3w", "pg_isready", "-U", "giragroup_user"],
                           capture_output=True, text=True, env=ENV)
        if r.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError("beto_pg_f3w no arranco a tiempo")

    # Restaurar f3w_completo
    sh(["docker", "exec", "beto_pg_f3w", "psql", "-U", "giragroup_user", "-d", "postgres", "-c", "CREATE DATABASE f3w_completo;"])
    sh(["docker", "cp", str(dump_f3ub), "beto_pg_f3w:/tmp/f3u_completo.dump"])
    subprocess.run(
        ["docker", "exec", "beto_pg_f3w", "pg_restore", "-U", "giragroup_user", "-d", "f3w_completo",
         "--no-owner", "--no-privileges", "/tmp/f3u_completo.dump"],
        capture_output=True, text=True, env=ENV,
    )
    f3w_comp_conteos = conteos_db("beto_pg_f3w", "f3w_completo")

    # Crear f3w_vacio clonando f3w_completo y truncando hechos/staging/logs/lotes (aplicando 014 y 016)
    sh(["docker", "exec", "beto_pg_f3w", "psql", "-U", "giragroup_user", "-d", "postgres",
        "-c", "CREATE DATABASE f3w_vacio TEMPLATE f3w_completo;"])
    sh(["docker", "cp", str(ROOT / "backend/scripts/migrations/014_conversion_captacion_comprobable.sql"), "beto_pg_f3w:/tmp/014.sql"])
    sh(["docker", "cp", str(ROOT / "backend/scripts/migrations/016_b9_descartes_y_homonimos.sql"), "beto_pg_f3w:/tmp/016.sql"])
    sh(["docker", "exec", "beto_pg_f3w", "psql", "-U", "giragroup_user", "-d", "f3w_vacio", "-f", "/tmp/014.sql"])
    sh(["docker", "exec", "beto_pg_f3w", "psql", "-U", "giragroup_user", "-d", "f3w_vacio", "-f", "/tmp/016.sql"])
    sh(["docker", "exec", "beto_pg_f3w", "psql", "-U", "giragroup_user", "-d", "f3w_vacio", "-c",
        "TRUNCATE TABLE fact_rendimiento_academico, fact_situacion_financiera, fact_evaluacion_docente, "
        "fact_marketing, fact_rentabilidad, fact_forecast, fact_cobranzas_proyectadas, fact_costo_programa, "
        "fact_techo_convenio, staging_registros_crudos, stg_entidad_no_resuelta, log_inconsistencias, "
        "log_pipeline_ingesta, carga_fila_origen, dataops_tarea, dim_origen_documental, lote, "
        "cache_indice_beto RESTART IDENTITY CASCADE;"])
    f3w_vacio_conteos = conteos_db("beto_pg_f3w", "f3w_vacio")

    w0 = {
        "tarea": "W-0 (Linea base F3W)",
        "git_diff_stat": git_stat,
        "lote_sha256": f3ub_json["lote_sha256"],
        "dump_f3ub_sha256": dump_sha,
        "dump_sha_coincide_f3ub": dump_sha == f3ub_json["dump_sha256"],
        "dw_viva_antes": {
            "lotes": viva_lotes,
            "documentos": viva_docs,
            "casos_abiertos_por_motivo": viva_casos_motivo,
            "conteos": viva_antes,
        },
        "beto_pg_f3w_puerto": 55634,
        "f3w_completo_conteos": f3w_comp_conteos,
        "f3w_vacio_conteos": f3w_vacio_conteos,
    }
    (MED / "f3w_linea_base.json").write_text(json.dumps(w0, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[W-0 OK]", flush=True)

    # 3. W-0b: Dump previo de giragroup_db y DELETE /api/v1/dataops/sources/28
    dump_pre = OUT_W / "giragroup_db_pre_w0b.dump"
    sh(["docker", "exec", "giragroup_db", "pg_dump", "-U", "giragroup_user", "-d", "giragroup_db", "-Fc", "-f", "/tmp/giragroup_db_pre_w0b.dump"])
    sh(["docker", "cp", "giragroup_db:/tmp/giragroup_db_pre_w0b.dump", str(dump_pre)])
    dump_pre_sha = sha256_file(dump_pre)

    # Autenticar y llamar DELETE /api/v1/dataops/sources/{doc_id}
    email = os.environ["ADMIN_EMAIL"]
    pwd = os.environ["ADMIN_PASS"]
    req_login = urllib.request.Request(
        "http://localhost:8000/api/v1/auth/login",
        data=json.dumps({"email": email, "password": pwd}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req_login, timeout=20) as resp:
        token = json.loads(resp.read().decode("utf-8"))["access_token"]

    deleted_docs = []
    for line in viva_docs:
        doc_id = int(line.split("|")[0])
        req_del = urllib.request.Request(
            f"http://localhost:8000/api/v1/dataops/sources/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
            method="DELETE",
        )
        with urllib.request.urlopen(req_del, timeout=60) as resp:
            deleted_docs.append({"id_documento": doc_id, "http": resp.status, "body": json.loads(resp.read().decode("utf-8"))})

    viva_despues = conteos_db("giragroup_db", "giragroup_db")
    w0b = {
        "tarea": "W-0b (Purga lote #18 en DW viva)",
        "dump_previo_path": "output/f3w/giragroup_db_pre_w0b.dump",
        "dump_previo_sha256": dump_pre_sha,
        "endpoints_delete": deleted_docs,
        "dw_viva_antes": viva_antes,
        "dw_viva_despues": viva_despues,
        "catalogo_y_usuarios_sin_cambio": {
            "dim_modulo_antes": viva_antes["dim_modulo"],
            "dim_modulo_despues": viva_despues["dim_modulo"],
            "users_antes": viva_antes["users"],
            "users_despues": viva_despues["users"],
        },
    }
    (MED / "f3w_purga_lote18.json").write_text(json.dumps(w0b, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[W-0b OK] DW viva lotes despues:", viva_despues["lote"], "docs:", viva_despues["dim_origen_documental"], flush=True)


if __name__ == "__main__":
    main()
