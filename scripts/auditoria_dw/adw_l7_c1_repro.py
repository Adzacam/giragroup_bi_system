"""ADW L7-C1: reproduce en la copia tmpfs la lectura BETO del lote 1 (tareas 45, 47 y 49 terminaron en ERROR con 0 procesados).
Uso (solo contra la copia tmpfs, nunca la DW viva):
  ADW_DB_URL=postgresql://giragroup_user:tmpfs_local@127.0.0.1:55433/giragroup_db python scripts/auditoria_dw/adw_l7_c1_repro.py <id_lote> <salida.json>
Ejecuta la API en proceso, llama a iniciar-lectura y vigila la tarea LECTURA_BETO con un temporizador."""
import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
url = os.environ.get("ADW_DB_URL", "")
if "55433" not in url:
    sys.exit("ADW_DB_URL debe apuntar a la copia tmpfs (puerto 55433).")
os.environ["DATABASE_URL"] = url

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from core.database import SessionLocal  # noqa: E402
from core.security import get_current_user  # noqa: E402
from main import app  # noqa: E402
from models.user import User  # noqa: E402

id_lote = int(sys.argv[1])
salida = sys.argv[2]
app.dependency_overrides[get_current_user] = lambda: User(id=1, username="admin", email="a@giragroup.bo", role="ADMIN", is_active=True)
cli = TestClient(app)


def ultima_tarea():
    with SessionLocal() as db:
        r = db.execute(text("SELECT id, estado, total, procesados, error, "
                            "EXTRACT(EPOCH FROM (now() - actualizado_en)) AS sin_latido FROM public.dataops_tarea "
                            "WHERE id_lote=:l AND tipo='LECTURA_BETO' ORDER BY id DESC LIMIT 1"), {"l": id_lote}).mappings().first()
        return dict(r) if r else None


resultado = {"id_lote": id_lote, "antes": ultima_tarea(), "muestras": []}
fin = threading.Event()


def vigilar():
    t0 = time.monotonic()
    while not fin.is_set():
        time.sleep(5)
        resultado["muestras"].append({"t": round(time.monotonic() - t0), **(ultima_tarea() or {})})


hilo = threading.Thread(target=vigilar, daemon=True)
hilo.start()
t0 = time.monotonic()
try:
    r = cli.post(f"/api/v1/dataops/lote/{id_lote}/iniciar-lectura")
    resultado["http"] = r.status_code
    resultado["respuesta"] = r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:300]
except Exception as e:  # noqa: BLE001
    resultado["excepcion"] = repr(e)[:300]
resultado["segundos_llamada"] = round(time.monotonic() - t0, 1)
fin.set()
resultado["despues"] = ultima_tarea()
Path(salida).write_text(json.dumps(resultado, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: resultado.get(k) for k in ("http", "segundos_llamada", "antes", "despues")}, default=str, ensure_ascii=False))
