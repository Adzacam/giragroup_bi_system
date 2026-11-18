"""X-4: Verifica que el completado de docente en respuestas diferidas aplica antes de escribir el bloque."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from core.database import Base  # noqa: E402
import models  # noqa: F401, E402
from models.bridge_modulo_docente import BridgeModuloDocente  # noqa: E402
from models.dim_docente import DimDocente  # noqa: E402
from models.dim_modulo import DimModulo  # noqa: E402
from models.dim_origen import DimOrigenDocumental  # noqa: E402
from models.dim_tiempo import DimTiempo  # noqa: E402
from models.fact_evaluacion import FactEvaluacionDocente  # noqa: E402
from services.dw_loader import DWLoaderService  # noqa: E402


def _make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": {"public": None}},
    )

    @event.listens_for(engine, "connect")
    def _attach(dbapi_conn, _rec):
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS public")

    for tbl in Base.metadata.tables.values():
        tbl.schema = None
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_insertar_eval_completa_docente_unico_antes_de_escribir(monkeypatch):
    db = _make_session()
    db.add(DimTiempo(id_tiempo=1, gestion=2026, mes=5))
    db.add(DimDocente(id_docente=42, nombre_completo="Dra. Maria Perez"))
    db.add(DimModulo(id_modulo=10, pos_code="POS-2026-M01", nombre_modulo="Modulo 1", programa="POS-2026"))
    db.add(DimOrigenDocumental(id_documento=1, nombre_archivo="eval.xlsx", tipo_fuente="EVALUACION_DOCENTE"))
    db.add(BridgeModuloDocente(id_modulo=10, id_docente=42, id_documento=1))
    db.commit()

    loader = DWLoaderService(db)
    loader.diferir_eval = True
    loader._eval_pendientes["k1"] = {
        "id_docente": None,
        "id_modulo": 10,
        "id_estudiante": None,
        "id_tiempo": 1,
        "pregunta_bloque": "P1",
        "tipo_pregunta": "DOCENTE",
        "puntuacion": 95.0,
        "escala_max": 100.0,
        "comentario": "Excelente",
        "id_documento": 1,
        "requiere_revision": False,
        "motivo_revision": None,
    }
    loader._eval_pendientes["k2"] = {
        "id_docente": None,
        "id_modulo": 10,
        "id_estudiante": None,
        "id_tiempo": 1,
        "pregunta_bloque": "P2",
        "tipo_pregunta": "PLATAFORMA",
        "puntuacion": 80.0,
        "escala_max": 100.0,
        "comentario": None,
        "id_documento": 1,
        "requiere_revision": False,
        "motivo_revision": None,
    }

    capturadas = []

    def _fake_execute_values(cur, sql, argslist, page_size=2000):
        capturadas.extend(argslist)

    import psycopg2.extras
    monkeypatch.setattr(psycopg2.extras, "execute_values", _fake_execute_values)

    class _DummyCur:
        pass

    enviadas = loader._insertar_eval(_DummyCur(), pagina=2000, durante_carga=True)
    assert enviadas == 2
    por_clave = {row[0]: row for row in capturadas}
    # cols = [clave_respuesta, id_docente, id_modulo, ...]
    assert por_clave["k1"][1] == 42
    assert por_clave["k2"][1] is None
    db.close()


def test_asignacion_docente_completa_eval_ya_volcadas_por_tramos():
    db = _make_session()
    db.add(DimTiempo(id_tiempo=1, gestion=2026, mes=5))
    db.add(DimDocente(id_docente=7, nombre_completo="Dr. Carlos Rojas"))
    db.add(DimModulo(id_modulo=20, pos_code="POS-2026-M02", nombre_modulo="Modulo 2", programa="POS-2026"))
    db.add(DimOrigenDocumental(id_documento=2, nombre_archivo="eval2.xlsx", tipo_fuente="EVALUACION_DOCENTE"))
    db.add(
        FactEvaluacionDocente(
            id_docente=None,
            id_modulo=20,
            id_tiempo=1,
            pregunta_bloque="P1",
            tipo_pregunta="DOCENTE",
            puntuacion=90.0,
            escala_max=100.0,
            clave_respuesta="cr_tramo_1",
            id_documento=2,
            requiere_revision=False,
        )
    )
    db.commit()

    loader = DWLoaderService(db)
    loader.diferir_eval = True
    res = loader._cargar_asignacion_docente(
        resoluciones={"nombre_modulo_real": "Modulo 2"},
        nombre_docente="Dr. Carlos Rojas",
        pos_code="POS-2026-M02",
        doc_id=2,
        institucion="GiraGroup",
    )
    assert res["status"] == "loaded"
    assert res["evaluaciones_completadas"] == 1
    fila = db.query(FactEvaluacionDocente).filter_by(clave_respuesta="cr_tramo_1").first()
    assert fila.id_docente == 7
    db.close()
