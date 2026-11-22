"""
conftest.py
-----------
Configuración global de Pytest para asegurar que el directorio raíz
esté en sys.path durante la recolección y ejecución de pruebas.
"""

import sys
import os
import socket
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Asegurar que en ejecución local sobre host Windows (sin resolver giragroup_db)
# las pruebas que consumen DW_TEST_URL o DATABASE_URL apunten automáticamente al puerto publicado (5434).
def _can_resolve_host(h: str) -> bool:
    try:
        socket.gethostbyname(h)
        return True
    except Exception:
        return False

db_url = os.getenv("DATABASE_URL", "")
if "@giragroup_db:" in db_url and not _can_resolve_host("giragroup_db"):
    resolved_dw = db_url.replace("@giragroup_db:5432", "@localhost:5434").replace("@giragroup_db:", "@localhost:5434:")
    if not os.getenv("DW_TEST_URL"):
        os.environ["DW_TEST_URL"] = resolved_dw
    os.environ["DATABASE_URL"] = resolved_dw


import pytest


@pytest.fixture
def dw_sqlite():
    """Data Warehouse SQLite en memoria (con el esquema `public` adjunto) para probar servicios sin Postgres."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from core.database import Base
    import models  # noqa: F401  registra las tablas en Base.metadata

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def adjuntar_public(conn, _):
        cur = conn.cursor()
        cur.execute("ATTACH DATABASE ':memory:' AS public")
        cur.close()

    Base.metadata.create_all(bind=engine)
    sesion = sessionmaker(bind=engine)()
    yield sesion
    sesion.close()

