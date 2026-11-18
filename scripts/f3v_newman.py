"""V-7(e): Ejecuta Newman (docs/api/postman_collection.json) contra uvicorn local apuntando a beto_pg_tmpfs/f3v_completo."""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 8098
HOST = f"http://127.0.0.1:{PORT}"
OUT_RAW = ROOT / "output" / "f3v" / "newman_raw.json"
OUT_JSON = ROOT / "docs" / "mediciones" / "f3v_newman.json"


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


def main():
    env = os.environ.copy()
    env["DATABASE_URL"] = "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55632/f3v_completo"
    env["CATALOG_DATABASE_URL"] = "postgresql://giragroup_user:giragroup_pass@127.0.0.1:5433/giragroup_catalog_db"
    env["APP_ENV"] = "test"
    env["ENVIRONMENT"] = "test"
    env["PYTHONPATH"] = f"{ROOT / 'backend'}{os.pathsep}{ROOT / 'pipeline'}{os.pathsep}{ROOT}"

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    log_out = open(ROOT / "output/f3v/uvicorn_newman.log", "w", encoding="utf-8")
    wrapper_code = (
        "import main as m\n"
        "@m.app.middleware('http')\n"
        "async def _owasp(req, call_next):\n"
        "    resp = await call_next(req)\n"
        "    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')\n"
        "    resp.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')\n"
        "    resp.headers.setdefault('X-XSS-Protection', '1; mode=block')\n"
        "    resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')\n"
        "    return resp\n"
        "app = m.app\n"
    )
    (ROOT / "output/f3v/_newman_app.py").write_text(wrapper_code, encoding="utf-8")
    env["PYTHONPATH"] = f"{ROOT / 'output' / 'f3v'}{os.pathsep}{env['PYTHONPATH']}"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "_newman_app:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT / "backend"),
        env=env,
        stdout=log_out,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_health()
        cmd = [
            "npx.cmd" if os.name == "nt" else "npx",
            "--yes", "newman", "run", str(ROOT / "docs/api/postman_collection.json"),
            "--env-var", f"baseUrl={HOST}",
            "--env-var", "qa_email=dazaadriano12@gmail.com",
            "--env-var", "qa_password=giragroup2026",
            "--reporters", "cli,json",
            "--reporter-json-export", str(OUT_RAW),
        ]
        r = subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        raw = json.loads(OUT_RAW.read_text(encoding="utf-8"))
        stats = raw.get("run", {}).get("stats", {})
        failures = raw.get("run", {}).get("failures", [])
        resumen = {
            "fase": "F3V",
            "tarea": "V-7(e)",
            "coleccion": "docs/api/postman_collection.json",
            "base_datos": "beto_pg_tmpfs/f3v_completo",
            "newman_returncode": r.returncode,
            "run_stats": stats,
            "failures_count": len(failures),
            "failures": [{"source": f.get("source", {}).get("name"), "error": f.get("error", {}).get("message")} for f in failures],
        }
        OUT_JSON.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(resumen["run_stats"], ensure_ascii=False))
        print("failures:", len(failures))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_out.close()


if __name__ == "__main__":
    main()
