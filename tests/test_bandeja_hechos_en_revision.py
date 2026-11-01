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


# ── Aprobación en bloque de los casos de un clic ──
def test_aprobacion_en_bloque_exige_confirmacion(dw):
    from fastapi import HTTPException
    from routers import dataops
    with pytest.raises(HTTPException) as exc:
        dataops.aprobar_casos_un_clic(dataops.AprobacionEnBloqueRequest(doc_id=1), db=dw, current_user=None)
    assert exc.value.status_code == 400


def test_aprobacion_en_bloque_aprueba_solo_los_de_un_clic_y_registra_cada_caso(dw):
    from models.fact_financiero import FactSituacionFinanciera
    from models.fact_rendimiento import FactRendimientoAcademico
    from models.log_pipeline import LogPipelineIngesta
    from routers import dataops

    assert _bandeja(dw)["un_clic_total"] == 2  # ACA-1 y FIN-1 completos; ACA-2 sin nota es manual
    res = dataops.aprobar_casos_un_clic(dataops.AprobacionEnBloqueRequest(doc_id=1, confirmar=True), db=dw, current_user=None)

    assert (res["aprobados"], res["fallidos"], res["manuales_pendientes"]) == (2, [], 1)
    assert dw.query(FactRendimientoAcademico).get(1).requiere_revision is False
    assert dw.query(FactSituacionFinanciera).get(1).requiere_revision is False
    assert {i["id"] for i in _bandeja(dw)["items"]} == {"HECHO-ACA-2"}  # el manual sigue en la bandeja
    eventos = dw.query(LogPipelineIngesta).filter(LogPipelineIngesta.etapa == "HITL_APROBACION_EN_BLOQUE").all()
    assert sorted(e.metadata_json["item_id"] for e in eventos) == ["HECHO-ACA-1", "HECHO-FIN-1"]
    assert all(e.metadata_json["accion"] == "APROBACION_EN_BLOQUE" and e.metadata_json["usuario"] for e in eventos)


# ── Corrección de fecha (mes y gestión) en el formulario ──
def test_hecho_sin_fecha_se_aprueba_con_la_fecha_corregida(dw):
    from models.fact_rendimiento import FactRendimientoAcademico
    from routers import dataops

    dw.add(FactRendimientoAcademico(id_hecho_aca=4, id_estudiante=1, id_modulo=1, id_documento=1, nota_final=88.5,
                                    nivel_confianza_ia=0.90, requiere_revision=True))
    dw.commit()
    caso = {i["id"]: i for i in _bandeja(dw)["items"]}["HECHO-ACA-4"]
    assert caso["campos_faltantes"] == ["fecha"] and caso["un_clic"] is False and caso["mes"] is None

    res = dataops.resolve_review_item("HECHO-ACA-4", {"accion": "APROBAR", "mes": 5, "gestion": 2025}, db=dw, current_user=None)

    h = dw.query(FactRendimientoAcademico).get(4)
    assert res["status"] == "success"
    assert (h.id_tiempo, h.requiere_revision) == (20250501, False)


def test_fecha_invalida_se_rechaza(dw):
    from models.fact_rendimiento import FactRendimientoAcademico
    from routers import dataops

    dw.add(FactRendimientoAcademico(id_hecho_aca=5, id_estudiante=1, id_modulo=1, id_documento=1, nota_final=70,
                                    requiere_revision=True))
    dw.commit()
    with pytest.raises(ValueError):
        dataops.resolve_review_item("HECHO-ACA-5", {"accion": "APROBAR", "mes": 13, "gestion": 2025}, db=dw, current_user=None)


def test_aprobar_entidad_de_acta_carga_las_notas_reales_y_no_inventa_75(dw):
    """Antes se cargaba un único hecho 'Módulo Académico' con nota 75 cuando el caso no traía nota."""
    from models.fact_rendimiento import FactRendimientoAcademico
    from models.staging_entidad import StagingEntidadNoResuelta
    from routers import dataops

    linea = ("N°: 2 | POS - ACTAS: 5314 | CÉDULA DE IDENTIDAD: 9008158 | MES INICO: 11 | AÑO INCIO: 2024 | "
             "APELLIDO MATERNO: CAYO | NOMBRES: EDGAR | MÓDULO 1: 83 | MÓDULO 2: 70")
    dw.add(StagingEntidadNoResuelta(id_staging=50, id_documento=1, tipo_entidad="ESTUDIANTE", texto_original=linea[:250],
                                    ci_temporal="9008158", mejor_candidato="EDGAR CAYO", motivo="BAJA_CONFIANZA_IA",
                                    resuelto=False, payload_json={"raw_line": linea}))
    dw.commit()
    antes = {h.id_hecho_aca for h in dw.query(FactRendimientoAcademico).all()}

    dataops.resolve_review_item("50", {"accion": "APROBAR", "estudiante_resuelto": "EDGAR CAYO"}, db=dw, current_user=None)

    nuevos = [h for h in dw.query(FactRendimientoAcademico).all() if h.id_hecho_aca not in antes]
    assert sorted(float(h.nota_final) for h in nuevos) == [70.0, 83.0]
    assert 75.0 not in [float(h.nota_final) for h in nuevos if h.nota_final is not None]
