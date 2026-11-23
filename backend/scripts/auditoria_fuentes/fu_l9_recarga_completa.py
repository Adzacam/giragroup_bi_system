"""
FU-L9 · Recarga controlada completa de los libros fuente por el flujo DataOps real
(upload-batch -> LECTURA_BETO -> confirm-dw-insert) sobre giragroup_db.

Uso (dentro de giragroup_api):
    python scripts/auditoria_fuentes/fu_l9_recarga_completa.py <salida.json> <libro1::TIPO[::ESCALA]> ...
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

BASE = "/api/v1/dataops"


def cliente():
    from fastapi.testclient import TestClient
    from main import app
    from core.security import get_current_user
    from models.user import User
    app.dependency_overrides[get_current_user] = lambda: User(
        id=2, username="auditor", email="auditor@ejemplo.test",
        role="AUDITOR_CALIDAD", is_active=True,
    )
    return TestClient(app)


def cargar_libro(cli, ruta: str, tipo: str, indice: int, escala: str = "") -> dict:
    from sqlalchemy import text
    from core.database import SessionLocal

    t = {}
    contenido = Path(ruta).read_bytes()
    nombre = f"libro_{indice}.xlsx"
    t0 = time.perf_counter()
    r = cli.post(
        f"{BASE}/upload-batch",
        files=[("files", (nombre, contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        data={"tipos_fuente": [tipo], "tipos_escala": [escala], "institucion": "GiraGroup Posgrado"},
    )
    t["carga_s"] = round(time.perf_counter() - t0, 2)
    j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    id_lote = j.get("id_lote")
    if not id_lote:
        return {"libro": indice, "archivo": Path(ruta).name, "http": r.status_code, "error": str(j)[:500]}

    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 7200:
        tarea = cli.get(f"{BASE}/lote/{id_lote}/tarea", params={"tipo": "LECTURA_BETO"}).json()
        if (tarea or {}).get("estado") != "EN_CURSO":
            break
        time.sleep(3)
    t["lectura_beto_s"] = round(time.perf_counter() - t0, 2)

    t0 = time.perf_counter()
    rc = cli.post(f"{BASE}/confirm-dw-insert", json={"id_lote": id_lote, "en_segundo_plano": False})
    t["consolidacion_s"] = round(time.perf_counter() - t0, 2)
    rj = rc.json() if rc.headers.get("content-type", "").startswith("application/json") else {}

    with SessionLocal() as s:
        docs = [d for (d,) in s.execute(text("SELECT id_documento FROM dim_origen_documental WHERE id_lote = :l"), {"l": id_lote})]
        reglas = s.execute(
            text("SELECT tipo_regla, count(*) FROM log_inconsistencias WHERE id_documento = ANY(:d) GROUP BY 1 ORDER BY 1"),
            {"d": docs},
        ).fetchall()
        tipos = s.execute(
            text("SELECT tipo_fuente FROM dim_origen_documental WHERE id_documento = ANY(:d)"),
            {"d": docs},
        ).fetchall()

    return {
        "libro": indice,
        "archivo": Path(ruta).name,
        "tipo_sugerido": tipo,
        "id_lote": id_lote,
        "documentos": docs,
        "tipo_fuente_detectado": [x[0] for x in tipos],
        "carga_http": r.status_code,
        "carga": {k: v for k, v in j.items() if isinstance(v, (int, float, str, bool)) or v is None},
        "consolidacion_http": rc.status_code,
        "etapas_s": t,
        "consolidacion": {k: v for k, v in rj.items() if not isinstance(v, (list, dict))},
        "descartes_por_regla": rj.get("descartes_por_regla"),
        "log_inconsistencias_por_regla": {k: v for k, v in reglas},
    }


def main(salida: str, libros: list[str]) -> int:
    cli = cliente()
    out = []
    codigo = 0
    for i, spec in enumerate(libros, 1):
        ruta, _, resto = spec.partition("::")
        if "*" in ruta:
            import glob
            ruta = sorted(glob.glob(ruta))[0]
        tipo, _, escala = resto.partition("::")
        res = cargar_libro(cli, ruta, tipo, i, escala)
        out.append(res)
        print(json.dumps(res, ensure_ascii=False, default=str)[:1200], flush=True)
        if res.get("consolidacion_http") != 200:
            codigo = 2
        Path(salida).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return codigo


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2:]))
