"""ADW L1: el desglose de perspectivas del CMI no responde 500 y las tablas que cita el SQL existen.

- Con PostgreSQL (DATABASE_URL / DW_TEST_URL, solo SELECT): las 4 perspectivas responden 200 en todas las gestiones
  y toda tabla o vista citada en `routers/` y en el servicio de personalización existe.
- Sin PostgreSQL: una serie que falla no tumba el desglose; se registra y llega en `avisos`.
"""
import logging
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from core.database import get_db  # noqa: E402
from core.security import get_current_user  # noqa: E402
from main import app  # noqa: E402
from services import cache_consultas  # noqa: E402

PERSPECTIVAS = ("FINANCIERA", "CLIENTES", "PROCESOS_INTERNOS", "APRENDIZAJE")
ADMIN = SimpleNamespace(id=1, username="admin", role="ADMIN", is_active=True)


def _pg_url():
    url = os.environ.get("ADW_DB_URL") or os.environ.get("DW_TEST_URL") or os.environ.get("DATABASE_URL", "")
    if "@giragroup_db:" in url:
        url = url.replace("@giragroup_db:5432", "@localhost:5434").replace("@giragroup_db:", "@localhost:5434:")
    return url if url.startswith("postgresql") else None


def _pg_disponible() -> bool:
    url = _pg_url()
    if not url:
        return False
    try:
        with create_engine(url).connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


requiere_pg = pytest.mark.skipif(not _pg_disponible(), reason="Requiere PostgreSQL con las migraciones del CMI")


class _DbQueFalla:
    """Devuelve las gestiones y falla en cualquier otra consulta, como si faltara una tabla."""

    def __init__(self):
        self.rollbacks = 0

    def execute(self, stmt, params=None):
        if "vw_cmi_gestiones" in str(stmt):
            return SimpleNamespace(mappings=lambda: [{"gestion": 2025}])
        raise ProgrammingError(str(stmt), params, Exception('relation "no_existe" does not exist'))

    def rollback(self):
        self.rollbacks += 1


def test_serie_que_falla_no_da_500_y_se_registra(caplog):
    cache_consultas.invalidar()
    db = _DbQueFalla()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: ADMIN
    try:
        with caplog.at_level(logging.ERROR, logger="cmi_router"):
            r = TestClient(app).get("/api/v1/cmi/perspectivas/CLIENTES/detalle?gestion=2025")
    finally:
        app.dependency_overrides.clear()
        cache_consultas.invalidar()
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["series"]["inscritos_programa"] == []
    assert any("inscritos_programa" in a for a in cuerpo["avisos"])
    assert any("personalizados" in a for a in cuerpo["avisos"])
    assert any("falló la serie" in rec.getMessage() for rec in caplog.records), "el error no quedó en el log"
    assert db.rollbacks >= 1


def test_clientes_ya_no_cita_tablas_inexistentes():
    """Las tablas de la versión anterior (fact_inscripcion, dim_programa, fact_captacion_marketing, dim_fuente_captacion)."""
    src = (ROOT / "backend" / "routers" / "cmi.py").read_text(encoding="utf-8")
    for tabla in ("fact_inscripcion", "dim_programa", "fact_captacion_marketing", "dim_fuente_captacion", "t.anio"):
        assert tabla not in src, f"cmi.py aún cita {tabla}"


def _tablas_citadas():
    patron = re.compile(r"\b(?:FROM|JOIN)\s+(public|bi|app)\.([a-z_][a-z_0-9]*)", re.IGNORECASE)
    archivos = list((ROOT / "backend" / "routers").glob("*.py")) + [ROOT / "backend" / "services" / "cmi_personalizacion_service.py"]
    citadas = {}
    for f in archivos:
        for esquema, tabla in patron.findall(f.read_text(encoding="utf-8")):
            citadas.setdefault((esquema.lower(), tabla.lower()), set()).add(f.name)
    return citadas


@requiere_pg
def test_todas_las_tablas_citadas_en_routers_existen():
    citadas = _tablas_citadas()
    assert citadas, "el recorrido no encontró ninguna tabla: revisar el patrón"
    with create_engine(_pg_url()).connect() as c:
        existentes = {
            (r[0], r[1]) for r in c.execute(text(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema IN ('public','bi','app')"))
        }
    faltan = {f"{e}.{t}": sorted(a) for (e, t), a in citadas.items() if (e, t) not in existentes}
    assert not faltan, f"Tablas o vistas citadas en el SQL que no existen: {faltan}"


@requiere_pg
@pytest.mark.parametrize("codigo", PERSPECTIVAS)
def test_detalle_responde_200_en_todas_las_gestiones(codigo):
    cache_consultas.invalidar()
    Session = sessionmaker(bind=create_engine(_pg_url()))
    db = Session()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: ADMIN
    try:
        client = TestClient(app)
        gestiones = [r[0] for r in db.execute(text("SELECT gestion FROM bi.vw_cmi_gestiones ORDER BY gestion"))]
        assert gestiones
        for g in gestiones:
            r = client.get(f"/api/v1/cmi/perspectivas/{codigo}/detalle", params={"gestion": g})
            assert r.status_code == 200, f"{codigo} {g}: {r.status_code} {r.text[:200]}"
            cuerpo = r.json()
            assert cuerpo["codigo"] == codigo and isinstance(cuerpo["avisos"], list)
            # sin errores internos: los únicos avisos admitidos son los informativos de CLIENTES
            assert not [a for a in cuerpo["avisos"] if "error interno" in a], cuerpo["avisos"]
    finally:
        app.dependency_overrides.clear()
        db.close()
        cache_consultas.invalidar()
