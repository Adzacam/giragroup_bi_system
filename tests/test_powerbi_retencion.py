"""Retención de versiones del informe .pbix: se conservan las últimas N y siempre la vigente."""
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from routers.powerbi import MAX_VERSIONES, _aplicar_retencion


@pytest.fixture
def db(tmp_path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def adjuntar_public(conn, _):
        cur = conn.cursor()
        cur.execute("ATTACH DATABASE ':memory:' AS public")
        cur.close()

    sesion = sessionmaker(bind=engine)()
    sesion.execute(text("CREATE TABLE public.powerbi_informe_version (version INTEGER PRIMARY KEY, ruta TEXT, vigente BOOLEAN)"))
    sesion.tmp = tmp_path
    yield sesion
    sesion.close()


def _crear(db, n, vigente=None):
    for v in range(1, n + 1):
        ruta = db.tmp / f"v{v}.pbix"
        ruta.write_bytes(b"x")
        db.execute(text("INSERT INTO public.powerbi_informe_version VALUES (:v, :r, :g)"),
                   {"v": v, "r": str(ruta), "g": v == (vigente or n)})
    db.commit()


def _versiones(db):
    return [r[0] for r in db.execute(text("SELECT version FROM public.powerbi_informe_version ORDER BY version"))]


def test_conserva_solo_las_ultimas_versiones_y_borra_los_archivos(db):
    _crear(db, 6)
    eliminadas = _aplicar_retencion(db, max_versiones=3)
    assert eliminadas == 3
    assert _versiones(db) == [4, 5, 6]
    assert not (db.tmp / "v1.pbix").exists() and (db.tmp / "v6.pbix").exists()


def test_nunca_elimina_la_version_vigente_aunque_sea_antigua(db):
    _crear(db, 6, vigente=2)
    _aplicar_retencion(db, max_versiones=3)
    assert 2 in _versiones(db)
    assert (db.tmp / "v2.pbix").exists()


def test_sin_exceso_no_borra_nada(db):
    _crear(db, 2)
    assert _aplicar_retencion(db, max_versiones=3) == 0
    assert _versiones(db) == [1, 2]


def test_retencion_por_defecto_es_positiva():
    assert MAX_VERSIONES >= 1
