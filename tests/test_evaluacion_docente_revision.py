"""Evaluación docente en la bandeja HITL (un caso por documento y módulo) y precedencia de fuentes de la recaudación."""
from datetime import date

import pytest


@pytest.fixture
def dw():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from core.database import Base
    import models  # noqa: F401
    from models.dim_docente import DimDocente
    from models.dim_modulo import DimModulo
    from models.dim_origen import DimOrigenDocumental
    from models.fact_evaluacion import FactEvaluacionDocente

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _public(dbapi_connection, _):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS public")

    Base.metadata.create_all(bind=engine)
    s = sessionmaker(bind=engine)()
    s.add_all([
        DimOrigenDocumental(id_documento=1, nombre_archivo="Experiencia Docente 2.0.xlsx", tipo_fuente="EVALUACION_DOCENTE"),
        DimModulo(id_modulo=7, nombre_modulo="POS-5908 · Módulo 1"),
        DimDocente(id_docente=3, nombre_completo="Ana Rojas"),
        FactEvaluacionDocente(id_hecho_eval=1, id_modulo=7, id_documento=1, tipo_pregunta="DOCENTE", puntuacion=5, requiere_revision=True, motivo_revision="DOCENTE_SIN_VINCULAR"),
        FactEvaluacionDocente(id_hecho_eval=2, id_modulo=7, id_documento=1, tipo_pregunta="DOCENTE", puntuacion=4, requiere_revision=True, motivo_revision="DOCENTE_SIN_VINCULAR"),
        FactEvaluacionDocente(id_hecho_eval=3, id_modulo=7, id_documento=1, tipo_pregunta="INSTITUCIONAL", puntuacion=4, requiere_revision=False),
    ])
    s.commit()
    yield s
    s.close()


def test_respuestas_sin_docente_forman_un_caso_por_documento_y_modulo(dw):
    from services.revision_hechos import contar_hechos_en_revision, items_hechos_en_revision
    assert contar_hechos_en_revision(dw, [1]) == 1
    (it,) = items_hechos_en_revision(dw, [1], offset=0, limit=10)
    assert it["id"] == "HECHO-EVA-1-7" and it["respuestas"] == 2 and it["un_clic"] is False and it["campos_faltantes"] == ["docente"]


def test_aprobar_con_docente_vincula_las_respuestas_del_docente_y_las_saca_de_revision(dw):
    from models.fact_evaluacion import FactEvaluacionDocente
    from services.revision_hechos import contar_hechos_en_revision, resolver_caso_hecho
    r = resolver_caso_hecho(dw, "HECHO-EVA-1-7", {"accion": "APROBAR", "docente_resuelto": "ana rojas"}, user_id=None, user_name="auditor")
    assert r["status"] == "success"
    assert {f.id_hecho_eval: f.id_docente for f in dw.query(FactEvaluacionDocente).all()} == {1: 3, 2: 3, 3: None}
    assert contar_hechos_en_revision(dw, [1]) == 0


def test_fuente_de_referencia_tiene_precedencia_sobre_bd_egresos():
    from services.dw_loader import DWLoaderService
    p = DWLoaderService._prioridad_fuente
    assert p("EJECUTADO VS META.xlsx") > p("BD Egresos.xlsx") and p(None) == p("BD Egresos.xlsx")
