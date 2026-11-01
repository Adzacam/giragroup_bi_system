"""
tests/test_bandeja_hechos_en_revision.py
----------------------------------------
HU-06 / RF-06: la pestaña "Pendientes" de la bandeja lista también los hechos con requiere_revision = True
(índice 0,60–0,85), y cada uno se acepta, o se corrige y aprueba, por separado. Al aprobar: requiere_revision
= False y registro en la bitácora. Antes la bandeja solo mostraba entidades no resueltas.
"""

from datetime import date

import pytest


@pytest.fixture
def dw(monkeypatch):
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from core.database import Base
    import models  # noqa: F401
    from models.dim_estudiante import DimEstudiante
    from models.dim_modulo import DimModulo
    from models.dim_origen import DimOrigenDocumental
    from models.dim_tiempo import DimTiempo
    from models.fact_financiero import FactSituacionFinanciera
    from models.fact_rendimiento import FactRendimientoAcademico
    from routers import dataops

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _public(dbapi_connection, _):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS public")

    Base.metadata.create_all(bind=engine)
    s = sessionmaker(bind=engine)()
    monkeypatch.setattr(dataops, "_evaluar_documentos_lote", lambda *a, **k: None)
    s.add_all([
        DimOrigenDocumental(id_documento=1, nombre_archivo="ARCA_lote1387_860_filas.xlsx", tipo_fuente="ACTA"),
        DimEstudiante(id_estudiante=1, nombre_completo="NATALY CAERO FORONDA", ci="9453509", codigo_estudiante="E1"),
        DimModulo(id_modulo=1, nombre_modulo="POS-5379 · Módulo 1"),
        DimTiempo(id_tiempo=20241201, gestion=2024, fecha=date(2024, 12, 1)),
        FactRendimientoAcademico(id_hecho_aca=1, id_estudiante=1, id_modulo=1, id_documento=1, id_tiempo=20241201, nota_final=90,
                                 nivel_confianza_ia=0.81, requiere_revision=True),
        FactRendimientoAcademico(id_hecho_aca=2, id_estudiante=1, id_modulo=1, id_documento=1, id_tiempo=20241201, nota_final=None,
                                 nivel_confianza_ia=0.70, requiere_revision=True),
        FactRendimientoAcademico(id_hecho_aca=3, id_estudiante=1, id_modulo=1, id_documento=1, nota_final=88,
                                 nivel_confianza_ia=0.95, requiere_revision=False),
        FactSituacionFinanciera(id_hecho_fin=1, id_estudiante=1, id_documento=1, id_tiempo=20241201, monto_deuda=500, cuotas_impagas=1,
                                nivel_confianza_ia=0.80, requiere_revision=True),
    ])
    s.commit()
    yield s
    s.close()


def _bandeja(dw):
    from routers import dataops
    return dataops.get_review_tray(doc_id=1, id_lote=None, motivo=None, estado=None, page=1, page_size=100, db=dw)


def test_pendientes_incluye_hechos_en_revision(dw):
    items = {i["id"]: i for i in _bandeja(dw)["items"]}
    assert set(items) == {"HECHO-ACA-1", "HECHO-ACA-2", "HECHO-FIN-1"}  # el hecho 3 no está en revisión
    assert items["HECHO-ACA-1"]["motivo"] == "HECHO_EN_REVISION"
    assert items["HECHO-ACA-1"]["un_clic"] is True        # completo: se acepta tal cual
    assert items["HECHO-ACA-2"]["un_clic"] is False       # sin nota: hay que corregir
    assert items["HECHO-ACA-2"]["campos_faltantes"] == ["nota"]
    assert items["HECHO-ACA-1"]["nota_final"] == 90.0


def test_aprobar_un_caso_lo_saca_de_revision_y_queda_en_bitacora(dw):
    from models.fact_rendimiento import FactRendimientoAcademico
    from models.log_auditoria_nlp import LogAuditoriaNlp
    from models.log_pipeline import LogPipelineIngesta
    from routers import dataops

    res = dataops.resolve_review_item("HECHO-ACA-2", {"accion": "APROBAR", "nota_final": 65}, db=dw, current_user=None)

    assert res["status"] == "success"
    h = dw.query(FactRendimientoAcademico).get(2)
    assert (h.requiere_revision, float(h.nota_final), h.estado_academico) == (False, 65.0, "Reprobado")
    assert dw.query(FactRendimientoAcademico).get(1).requiere_revision is True  # los demás casos siguen pendientes
    assert dw.query(LogAuditoriaNlp).filter(LogAuditoriaNlp.texto_original.like("HECHO-ACA-2%")).count() == 1
    log = dw.query(LogPipelineIngesta).filter(LogPipelineIngesta.etapa == "HITL_RESOLUCION_INDIVIDUAL").one()
    assert log.metadata_json["correcciones"] == {"nota_final": 65.0}
    assert {i["id"] for i in _bandeja(dw)["items"]} == {"HECHO-ACA-1", "HECHO-FIN-1"}


def test_rechazar_un_caso_elimina_el_hecho(dw):
    from models.fact_financiero import FactSituacionFinanciera
    from routers import dataops

    dataops.resolve_review_item("HECHO-FIN-1", {"accion": "DESCARTAR"}, db=dw, current_user=None)
    assert dw.query(FactSituacionFinanciera).get(1) is None
