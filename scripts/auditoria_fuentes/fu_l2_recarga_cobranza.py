"""
FU-L2 · Recarga de un libro de cobranza por el flujo DataOps real (carga en lote -> lectura BETO -> consolidación),
sobre una base AISLADA (copia tmpfs). Nunca contra giragroup_db ni contra el snapshot.

Uso (dentro de giragroup_api, con el árbol copiado por scripts/copiar_arbol.sh):
    DATABASE_URL=postgresql://...@fu_l2_pg_tmpfs:5432/giragroup_db \
    CATALOG_DATABASE_URL=postgresql://...@fu_l2_pg_tmpfs:5432/catalogo_copia \
    python scripts/auditoria_fuentes/fu_l2_recarga_cobranza.py <libro.xlsx> <salida.json>

El libro se pasa por argumento; el tipo de fuente lo detecta el sistema (se envía COBRANZA como sugerencia de la
SPA, que el sistema puede corregir por contenido). La salida no lleva datos personales: solo conteos y tiempos.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

BASE = "/api/v1/dataops"


def _verificar_aislada() -> None:
    url = os.environ.get("DATABASE_URL", "")
    host = url.split("@")[-1].split("/")[0]
    if not host.startswith("fu_l2_pg_tmpfs") and "55437" not in host:
        raise SystemExit(f"Base no aislada ({host}): esta recarga solo corre contra la copia tmpfs fu_l2_pg_tmpfs")


def cliente():
    from fastapi.testclient import TestClient
    from main import app
    from core.security import get_current_user
    from models.user import User
    app.dependency_overrides[get_current_user] = lambda: User(id=2, username="auditor", email="auditor@ejemplo.test",
                                                              role="AUDITOR_CALIDAD", is_active=True)
    return TestClient(app)


def main(libro: str, salida: str) -> int:
    _verificar_aislada()
    from sqlalchemy import text
    from core.database import SessionLocal

    cli = cliente()
    t = {}
    contenido = Path(libro).read_bytes()
    t0 = time.perf_counter()
    r = cli.post(f"{BASE}/upload-batch",
                 files=[("files", ("libro_cobranza.xlsx", contenido,
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
                 data={"tipos_fuente": ["COBRANZA"], "tipos_escala": [""], "institucion": "GiraGroup Posgrado"})
    t["carga_s"] = round(time.perf_counter() - t0, 2)
    j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    id_lote = j.get("id_lote")
    if not id_lote:
        Path(salida).write_text(json.dumps({"http": r.status_code, "error": str(j)[:500]}, ensure_ascii=False), encoding="utf-8")
        return 1
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 3600:
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
        hojas = s.execute(text("SELECT tipo_regla, count(*) FROM log_inconsistencias WHERE id_documento = ANY(:d) "
                               "GROUP BY 1 ORDER BY 1"), {"d": docs}).fetchall()
        tipo = s.execute(text("SELECT tipo_fuente FROM dim_origen_documental WHERE id_documento = ANY(:d)"), {"d": docs}).fetchall()
    out = {
        "id_lote": id_lote, "documentos": docs, "tipo_fuente_detectado": [x[0] for x in tipo],
        "carga_http": r.status_code, "carga": {k: v for k, v in j.items() if k != "resultados"},
        "consolidacion_http": rc.status_code, "etapas_s": t,
        "consolidacion": {k: v for k, v in rj.items() if not isinstance(v, (list, dict))},
        "descartes_por_regla": rj.get("descartes_por_regla"),
        "log_inconsistencias_por_regla": {k: v for k, v in hojas},
    }
    Path(salida).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, default=str)[:1500])
    return 0 if rc.status_code == 200 else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
