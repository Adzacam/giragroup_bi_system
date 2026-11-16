"""R3-8: Locust (escenario reescrito Tabla 3.32), Newman y W medido para KLM."""
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

from core.security import create_access_token
import scripts.agregar_flujo_repetido as afr

DB_URL = "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55632/f3r_base"
CAT_URL = "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55632/catalogo_copia"
PORT = 8099
HOST = f"http://127.0.0.1:{PORT}"


def wait_health(timeout=45):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(f"{HOST}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("uvicorn no respondio /health a tiempo")


def main():
    env = os.environ.copy()
    env["DATABASE_URL"] = DB_URL
    env["CATALOG_DATABASE_URL"] = CAT_URL
    env["PYTHONPATH"] = f"{ROOT / 'backend'}{os.pathsep}{ROOT / 'pipeline'}{os.pathsep}{ROOT}"

    log_out = open(ROOT / "output/f3r/uvicorn_r3_8.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT / "backend"),
        env=env,
        stdout=log_out,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_health()
        token = create_access_token({"sub": "admin_general", "role": "ADMIN"})
        env["LOCUST_TOKEN"] = token

        # 1. Locust headless: 50 usuarios, ramp 5/s, 30s
        subprocess.run(
            [
                sys.executable,
                "-m",
                "locust",
                "-f",
                str(ROOT / "tests/carga/locustfile.py"),
                "--headless",
                "-u",
                "50",
                "-r",
                "5",
                "-t",
                "30s",
                "--host",
                HOST,
                "--csv",
                str(ROOT / "docs/mediciones/f3r_locust"),
            ],
            cwd=str(ROOT),
            env=env,
            check=False,
        )

        # 2. Newman contra postman_collection.json (sin editarla)
        subprocess.run(
            f'npx --yes newman run "{ROOT / "docs/api/postman_collection.json"}" '
            f'--env-var "baseUrl={HOST}" -r json --reporter-json-export "{ROOT / "docs/mediciones/f3r_newman.json"}"',
            shell=True,
            cwd=str(ROOT),
            env=env,
            check=False,
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_out.close()

    # Parsear f3r_locust_stats.csv -> f3r_locust.json
    stats_rows = []
    with (ROOT / "docs/mediciones/f3r_locust_stats.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            stats_rows.append(row)

    por_endpoint = {}
    agg = None
    for r in stats_rows:
        name = r.get("Name", "")
        entry = {
            "method": r.get("Type", ""),
            "requests": int(r.get("Request Count", 0)),
            "failures": int(r.get("Failure Count", 0)),
            "median_ms": float(r.get("Median Response Time", 0)),
            "avg_ms": float(r.get("Average Response Time", 0)),
            "min_ms": float(r.get("Min Response Time", 0)),
            "max_ms": float(r.get("Max Response Time", 0)),
            "rps": float(r.get("Requests/s", 0)),
            "p50_ms": float(r.get("50%", 0)),
            "p95_ms": float(r.get("95%", 0)),
            "p99_ms": float(r.get("99%", 0)),
        }
        if name == "Aggregated":
            agg = entry
        else:
            por_endpoint[name] = entry

    locust_json = {
        "etiqueta": "F3R, escenario reescrito (Tabla 3.32)",
        "tarea": "R3-8 (Locust)",
        "parametros": {"usuarios": 50, "rampa_por_s": 5, "duracion": "30s", "base_datos": "f3r_base"},
        "agregado": agg,
        "por_endpoint": por_endpoint,
    }
    (ROOT / "docs/mediciones/f3r_locust.json").write_text(
        json.dumps(locust_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 3. KLM con W medido (p95 de review-tray/grupos y approve-group)
    p95_grupos_ms = por_endpoint.get("GET /api/v1/dataops/review-tray/grupos", {}).get("p95_ms", 0.0)
    p95_approve_ms = por_endpoint.get("POST /api/v1/dataops/review-tray/approve-group", {}).get("p95_ms", 0.0)
    w_medido_s = round(max(p95_grupos_ms, p95_approve_ms) / 1000.0, 4)

    # Eventos de f3_base (19 grupos, 680 casos: 4 APROBAR, 1 CORREGIR_FECHA, 14 MANUAL con 47 casos)
    eventos = (
        [{"accion": "APROBAR"} for _ in range(4)]
        + [{"accion": "CORREGIR_FECHA"}]
        + [{"accion": "MANUAL", "casos": 47}]
        + [{"accion": "MANUAL", "casos": 0} for _ in range(13)]
    )

    def calc_klm(w_s):
        afr.W_DESHACER = w_s
        tot, desg = afr.klm(eventos, con_espera=True)
        return {"W_s": w_s, "klm_s": tot, "desglose_s": desg}

    klm_w0 = calc_klm(0.0)
    klm_w10 = calc_klm(10.0)
    klm_wmed = calc_klm(w_medido_s)

    rnf03 = json.loads((ROOT / "docs/mediciones/f3_b7_rnf03.json").read_text(encoding="utf-8"))
    maq_vacia = rnf03["solo_maquina"]["cache_vacia_media_s"]
    maq_llena = rnf03["solo_maquina"]["cache_llena_media_s"]

    klm_out = {
        "etiqueta": "F3R",
        "tarea": "R3-8 (W medido + KLM + RNF-03)",
        "fuente_w": "p95 de GET /api/v1/dataops/review-tray/grupos y POST /api/v1/dataops/review-tray/approve-group en f3r_locust.json",
        "p95_grupos_ms": p95_grupos_ms,
        "p95_approve_group_ms": p95_approve_ms,
        "W_medido_s": w_medido_s,
        "bandeja": {"casos": 680, "grupos": 19, "manuales": 14, "casos_manuales": 47, "acciones_con_W": 52},
        "klm": {
            "W_medido": klm_wmed,
            "sensibilidad_W_0": klm_w0,
            "sensibilidad_W_10": klm_w10,
        },
        "rnf03_totales_s": {
            "maquina_cache_vacia_s": maq_vacia,
            "maquina_cache_llena_s": maq_llena,
            "vacia_mas_klm_W_medido_s": round(maq_vacia + klm_wmed["klm_s"], 2),
            "llena_mas_klm_W_medido_s": round(maq_llena + klm_wmed["klm_s"], 2),
            "vacia_mas_klm_W_0_s": round(maq_vacia + klm_w0["klm_s"], 2),
            "llena_mas_klm_W_0_s": round(maq_llena + klm_w0["klm_s"], 2),
            "vacia_mas_klm_W_10_s": round(maq_vacia + klm_w10["klm_s"], 2),
            "llena_mas_klm_W_10_s": round(maq_llena + klm_w10["klm_s"], 2),
        },
    }
    (ROOT / "docs/mediciones/f3r_klm_w_medido.json").write_text(
        json.dumps(klm_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[OK] R3-8 Locust rps={agg['rps'] if agg else None} W_medido={w_medido_s}s KLM_Wmed={klm_wmed['klm_s']}s")


if __name__ == "__main__":
    main()
