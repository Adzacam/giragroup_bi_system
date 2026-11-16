"""S-7 (F3S): Locust con el mismo escenario y parámetros que R3-8 (scripts/f3r_ejecutar_r3_8.py): 50 usuarios, rampa 5/s, 30 s,
uvicorn local (127.0.0.1:8099) apuntando a la copia tmpfs (nunca a la DW viva). Sin Newman (S-5 ya lo midió).
Uso: python scripts/f3s_locust.py <dsn_base> <dsn_catalogo> <nombre_base>
Salidas: docs/mediciones/f3s_locust.json + f3s_locust_*.csv; log de uvicorn en output/f3s/s7/uvicorn_locust.log
"""
import csv
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

PORT = 8099
HOST = f"http://127.0.0.1:{PORT}"
MED = ROOT / "docs" / "mediciones"


def wait_health(timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(f"{HOST}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("uvicorn no respondio /health a tiempo")


def main(dsn, dsn_cat, base):
    env = os.environ.copy()
    env["DATABASE_URL"] = dsn
    env["CATALOG_DATABASE_URL"] = dsn_cat
    env["PYTHONPATH"] = f"{ROOT / 'backend'}{os.pathsep}{ROOT / 'pipeline'}{os.pathsep}{ROOT}"
    os.environ.update({"DATABASE_URL": dsn, "CATALOG_DATABASE_URL": dsn_cat})
    from core.security import create_access_token

    (ROOT / "output/f3s/s7").mkdir(parents=True, exist_ok=True)
    log_out = open(ROOT / "output/f3s/s7/uvicorn_locust.log", "w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                            cwd=str(ROOT / "backend"), env=env, stdout=log_out, stderr=subprocess.STDOUT)
    try:
        wait_health()
        env["LOCUST_TOKEN"] = create_access_token({"sub": "admin_general", "role": "ADMIN"})
        r = subprocess.run([sys.executable, "-m", "locust", "-f", str(ROOT / "tests/carga/locustfile.py"), "--headless",
                            "-u", "50", "-r", "5", "-t", "30s", "--host", HOST, "--csv", str(MED / "f3s_locust")],
                           cwd=str(ROOT), env=env, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (ROOT / "output/f3s/s7/locust_stdout.txt").write_text((r.stdout or "") + "\n--- stderr ---\n" + (r.stderr or ""), encoding="utf-8")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_out.close()

    por_endpoint, agg = {}, None
    with (MED / "f3s_locust_stats.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            e = {"method": row.get("Type", ""), "requests": int(row.get("Request Count", 0)), "failures": int(row.get("Failure Count", 0)),
                 "median_ms": float(row.get("Median Response Time", 0)), "avg_ms": float(row.get("Average Response Time", 0)),
                 "min_ms": float(row.get("Min Response Time", 0)), "max_ms": float(row.get("Max Response Time", 0)),
                 "rps": float(row.get("Requests/s", 0)), "p50_ms": float(row.get("50%", 0)), "p95_ms": float(row.get("95%", 0)),
                 "p99_ms": float(row.get("99%", 0))}
            if row.get("Name") == "Aggregated":
                agg = e
            else:
                por_endpoint[row.get("Name")] = e
    out = {"etiqueta": "F3S, escenario reescrito (Tabla 3.32)", "tarea": "S-7 (Locust)",
           "parametros": {"usuarios": 50, "rampa_por_s": 5, "duracion": "30s", "base_datos": base,
                          "pila": "uvicorn local 127.0.0.1:8099 (backend del árbol de trabajo) sobre la copia tmpfs beto_pg_s7",
                          "locustfile": "tests/carga/locustfile.py"},
           "agregado": agg, "por_endpoint": por_endpoint}
    (MED / "f3s_locust.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Locust requests={agg['requests'] if agg else None} fallos={agg['failures'] if agg else None} rps={agg['rps'] if agg else None}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
