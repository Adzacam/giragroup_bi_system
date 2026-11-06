"""Puebla el DW (docker-compose) enviando cada archivo de uploads/data/ a /api/v1/pipeline/process."""
import sys, json, time, requests
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "backend"))
from core.security import create_access_token
H = {"Authorization": "Bearer " + create_access_token({"sub": "2", "role": "AUDITOR_CALIDAD"})}
out = []
for f in sorted((BASE / "uploads" / "data").glob("*.xlsx")):
    t = time.time(); print("->", f.name, flush=True)
    try:
        with open(f, "rb") as fh:
            r = requests.post("http://localhost:8000/api/v1/pipeline/process", headers=H,
                              files={"file": (f.name, fh)}, timeout=3000)
        res = {"archivo": f.name, "http": r.status_code, "seg": round(time.time() - t, 1),
               "cuerpo": (r.json() if r.status_code == 200 else r.text[:300])}
    except Exception as e:
        res = {"archivo": f.name, "error": str(e)}
    print(json.dumps(res, ensure_ascii=False, default=str)[:600], flush=True); out.append(res)
(BASE / "docs" / "evidencias" / "poblado_dw_uploads_data.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
