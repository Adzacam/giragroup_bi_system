"""BA-L3: Verifica que < 0,85 y DESACUERDO_REGLA_BETO van a bandeja sin insertarse y con prioridad MEDIA/ALTA."""
from types import SimpleNamespace
import pytest
from models.dim_origen import DimOrigenDocumental
from models.fact_rendimiento import FactRendimientoAcademico
from models.lote import Lote
from models.staging_entidad import StagingEntidadNoResuelta
from models.staging_registro import StagingRegistroCrudo
from routers.dataops import consolidacion
from tests.sprint5.test_beto_integracion_flujo import ACTA, _ingestar, _servicio, entorno  # noqa: F401


def test_ba_l3_banda_media_no_inserta_y_marca_prioridad_media(entorno, monkeypatch, tmp_path):
    monkeypatch.setenv("BETO_CASCADA_FINAL", "0")
    monkeypatch.setenv("BETO_ACUERDO_QC", "0")
    monkeypatch.setenv("BETO_SUGERENCIA_HITL", "0")
    _servicio(monkeypatch, [])
    lote, _ = _ingestar(entorno, tmp_path, ACTA)
    monkeypatch.setattr(consolidacion, "obtener_indices", lambda textos, **kw: [0.72] * len(textos))
    res = consolidacion._consolidar(consolidacion.ConfirmDwInsertRequest(id_lote=lote.id_lote), entorno, None)
    assert res["desglose"]["inserted_academico"] == 0
    assert entorno.query(FactRendimientoAcademico).count() == 0
    casos = entorno.query(StagingEntidadNoResuelta).all()
    assert len(casos) >= 1
    assert any((c.payload_json or {}).get("prioridad") == "MEDIA" for c in casos)


def test_ba_l3_banda_baja_no_inserta_y_marca_prioridad_alta(entorno, monkeypatch, tmp_path):
    monkeypatch.setenv("BETO_CASCADA_FINAL", "0")
    monkeypatch.setenv("BETO_ACUERDO_QC", "0")
    monkeypatch.setenv("BETO_SUGERENCIA_HITL", "0")
    _servicio(monkeypatch, [])
    lote, _ = _ingestar(entorno, tmp_path, ACTA)
    monkeypatch.setattr(consolidacion, "obtener_indices", lambda textos, **kw: [0.45] * len(textos))
    res = consolidacion._consolidar(consolidacion.ConfirmDwInsertRequest(id_lote=lote.id_lote), entorno, None)
    assert res["desglose"]["inserted_academico"] == 0
    assert entorno.query(FactRendimientoAcademico).count() == 0
    casos = entorno.query(StagingEntidadNoResuelta).all()
    assert len(casos) >= 1
    assert any((c.payload_json or {}).get("prioridad") == "ALTA" for c in casos)


def test_ba_l3_desacuerdo_no_inserta_y_va_a_bandeja(entorno, monkeypatch, tmp_path):
    monkeypatch.setenv("BETO_CASCADA_FINAL", "0")
    monkeypatch.setenv("BETO_ACUERDO_QC", "1")
    monkeypatch.setenv("BETO_SUGERENCIA_HITL", "0")
    _servicio(monkeypatch, [])  # BETO devuelve vacío -> desacuerdo
    lote, _ = _ingestar(entorno, tmp_path, ACTA)
    monkeypatch.setattr(consolidacion, "obtener_indices", lambda textos, **kw: [0.95] * len(textos))
    res = consolidacion._consolidar(consolidacion.ConfirmDwInsertRequest(id_lote=lote.id_lote), entorno, None)
    assert res["desglose"]["inserted_academico"] == 0
    assert entorno.query(FactRendimientoAcademico).count() == 0
    casos = entorno.query(StagingEntidadNoResuelta).filter_by(motivo="DESACUERDO_REGLA_BETO").all()
    assert len(casos) >= 1
