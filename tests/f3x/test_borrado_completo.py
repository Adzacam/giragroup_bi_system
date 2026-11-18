"""X-1: Pruebas de borrado completo de documentos en una sola transacción."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from core.database import Base, get_db  # noqa: E402
from core.security import get_current_user  # noqa: E402
import models  # noqa: F401, E402
from models.bridge_modulo_docente import BridgeModuloDocente  # noqa: E402
from models.dim_docente import DimDocente  # noqa: E402
from models.dim_estudiante import DimEstudiante  # noqa: E402
from models.dim_modulo import DimModulo  # noqa: E402
from models.dim_origen import DimOrigenDocumental  # noqa: E402
from models.dim_tiempo import DimTiempo  # noqa: E402
from models.fact_costo_programa import FactCostoPrograma  # noqa: E402
from models.fact_evaluacion import FactEvaluacionDocente  # noqa: E402
from models.fact_financiero import FactSituacionFinanciera  # noqa: E402
from models.fact_rendimiento import FactRendimientoAcademico  # noqa: E402
from models.fact_rentabilidad import FactRentabilidad  # noqa: E402
from models.fact_techo_convenio import FactTechoConvenio  # noqa: E402
from models.log_inconsistencia import LogInconsistencia  # noqa: E402
from models.log_pipeline import LogPipelineIngesta  # noqa: E402
from models.staging_entidad import StagingEntidadNoResuelta  # noqa: E402
from models.staging_registro import StagingRegistroCrudo  # noqa: E402
from routers.dataops import router as dataops_router  # noqa: E402
from services.ingestion_service import IngestionService  # noqa: E402


def _make_sqlite_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _attach_public(dbapi_conn, _conn_record):
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS public")

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS carga_fila_origen ("
                "clave VARCHAR(64) PRIMARY KEY, id_documento INTEGER, tabla VARCHAR(40), creado_en TEXT)"
            )
        )
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _seed_doc_with_all_tables(db, doc_id: int, suffix: str):
    if not db.query(DimTiempo).filter_by(id_tiempo=1).first():
        db.add(DimTiempo(id_tiempo=1, gestion=2026, mes=5, trimestre=2, semestre=1))
    if not db.query(DimEstudiante).filter_by(id_estudiante=doc_id).first():
        db.add(DimEstudiante(id_estudiante=doc_id, ci=f"CI{doc_id}", codigo_estudiante=f"CI{doc_id}", nombre_completo=f"Ana {doc_id}", deprecado=False))
    if not db.query(DimDocente).filter_by(id_docente=doc_id).first():
        db.add(DimDocente(id_docente=doc_id, nombre_completo=f"Dr. Luis {doc_id}"))
    if not db.query(DimModulo).filter_by(id_modulo=doc_id).first():
        db.add(DimModulo(id_modulo=doc_id, pos_code=f"MOD-{doc_id}", nombre_modulo=f"Modulo {doc_id}", programa="Maestria X"))

    doc = DimOrigenDocumental(
        id_documento=doc_id,
        nombre_archivo=f"doc_{suffix}.xlsx",
        tipo_fuente="ACTA",
        hash_sha256=(f"sha_{suffix}" + "0" * 64)[:64],
        institucion="GiraGroup",
        periodo="2026-1",
    )
    db.add(doc)
    db.flush()

    db.add(FactRendimientoAcademico(id_estudiante=doc_id, id_modulo=doc_id, id_tiempo=1, id_docente=doc_id, id_documento=doc_id, nota_final=90))
    db.add(FactSituacionFinanciera(id_estudiante=doc_id, id_tiempo=1, id_documento=doc_id, monto_deuda=100, monto_pagado=100))
    db.add(FactEvaluacionDocente(id_docente=doc_id, id_modulo=doc_id, id_tiempo=1, id_documento=doc_id, pregunta_bloque="P1", puntuacion=5.0, clave_respuesta=f"cr_{doc_id}_{suffix}"))
    db.add(FactRentabilidad(id_modulo=doc_id, id_tiempo=1, id_documento=doc_id, monto_ejecutado=1000))
    db.add(FactCostoPrograma(id_modulo=doc_id, id_documento=doc_id, egreso_real=500))
    db.add(FactTechoConvenio(id_modulo=doc_id, id_tiempo=1, id_documento=doc_id, clave_convenio=f"cv_{doc_id}_{suffix}", institucion="U", monto_convenio=2000))
    db.add(BridgeModuloDocente(id_modulo=doc_id, id_docente=doc_id, id_documento=doc_id))
    db.add(StagingRegistroCrudo(id_documento=doc_id, texto_plano="fila 1", score_confianza=0.95))
    db.add(StagingEntidadNoResuelta(id_documento=doc_id, tipo_entidad="ESTUDIANTE", texto_original="Juan", fk_estado="C"))
    db.add(LogInconsistencia(id_documento=doc_id, campo_afectado="nota", tipo_regla="RANGO", severidad="ALTA"))
    db.add(LogPipelineIngesta(id_documento=doc_id, etapa="INGESTA", nivel="INFO", modulo="Test", mensaje="ok"))
    db.execute(
        text("INSERT INTO carga_fila_origen (clave, id_documento, tabla) VALUES (:c, :d, 'fact_rendimiento_academico')"),
        {"c": f"k_{suffix}", "d": doc_id},
    )
    db.commit()


def _count_for_doc(db, doc_id: int) -> dict:
    models_map = {
        "fact_rendimiento_academico": FactRendimientoAcademico,
        "fact_situacion_financiera": FactSituacionFinanciera,
        "fact_evaluacion_docente": FactEvaluacionDocente,
        "fact_rentabilidad": FactRentabilidad,
        "fact_costo_programa": FactCostoPrograma,
        "fact_techo_convenio": FactTechoConvenio,
        "bridge_modulo_docente": BridgeModuloDocente,
        "staging_registros_crudos": StagingRegistroCrudo,
        "stg_entidad_no_resuelta": StagingEntidadNoResuelta,
        "log_inconsistencias": LogInconsistencia,
        "log_pipeline_ingesta": LogPipelineIngesta,
        "dim_origen_documental": DimOrigenDocumental,
    }
    counts = {k: db.query(m).filter(m.id_documento == doc_id).count() for k, m in models_map.items()}
    counts["carga_fila_origen"] = db.execute(
        text("SELECT COUNT(*) FROM carga_fila_origen WHERE id_documento = :d"), {"d": doc_id}
    ).scalar()
    return counts


def test_delete_source_y_delete_batch_borran_todo_sin_tocar_dimensiones():
    Session = _make_sqlite_session()
    db = Session()
    _seed_doc_with_all_tables(db, 10, "a")
    _seed_doc_with_all_tables(db, 11, "b")

    app = FastAPI()
    app.include_router(dataops_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, username="admin", role="ADMIN")
    client = TestClient(app)

    dims_antes = (
        db.query(DimEstudiante).count(),
        db.query(DimDocente).count(),
        db.query(DimModulo).count(),
        db.query(DimTiempo).count(),
    )

    r1 = client.delete("/api/v1/dataops/sources/10")
    assert r1.status_code == 200
    assert all(v == 0 for v in _count_for_doc(db, 10).values())
    assert all(v == 1 for v in _count_for_doc(db, 11).values())

    r2 = client.post("/api/v1/dataops/sources/delete-batch", json={"ids": [11]})
    assert r2.status_code == 200
    assert all(v == 0 for v in _count_for_doc(db, 11).values())

    dims_despues = (
        db.query(DimEstudiante).count(),
        db.query(DimDocente).count(),
        db.query(DimModulo).count(),
        db.query(DimTiempo).count(),
    )
    assert dims_despues == dims_antes
    assert db.query(LogPipelineIngesta).filter(LogPipelineIngesta.etapa == "BORRADO").count() == 2
    db.close()


def test_cargar_borrar_recargar_mismos_conteos():
    Session = _make_sqlite_session()
    db = Session()
    _seed_doc_with_all_tables(db, 20, "x")
    conteo_inicial = _count_for_doc(db, 20)

    assert IngestionService.eliminar_fuente(db, 20) is True
    despues = _count_for_doc(db, 20)
    assert all(v == 0 for v in despues.values()), f"Quedaron filas: {despues}"

    _seed_doc_with_all_tables(db, 20, "x")
    assert _count_for_doc(db, 20) == conteo_inicial
    db.close()


def test_borrado_hace_rollback_si_falla_a_mitad():
    Session = _make_sqlite_session()
    db = Session()
    _seed_doc_with_all_tables(db, 30, "rb")
    antes = _count_for_doc(db, 30)

    with patch.object(db, "execute", side_effect=RuntimeError("fallo simulado")):
        with pytest.raises(RuntimeError):
            IngestionService.eliminar_fuente(db, 30)

    assert _count_for_doc(db, 30) == antes
    db.close()


def test_borrado_respeta_roles():
    Session = _make_sqlite_session()
    db = Session()
    app = FastAPI()
    app.include_router(dataops_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, username="est", role="ESTUDIANTE")
    client = TestClient(app)

    r = client.delete("/api/v1/dataops/sources/99")
    assert r.status_code == 403
    r_batch = client.post("/api/v1/dataops/sources/delete-batch", json={"ids": [99]})
    assert r_batch.status_code == 403
    db.close()
