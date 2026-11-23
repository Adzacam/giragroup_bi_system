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


def test_ba_l3_relacion_invalida_no_inserta_y_va_a_bandeja(entorno, monkeypatch, tmp_path):
    monkeypatch.setenv("BETO_CASCADA_FINAL", "0")
    monkeypatch.setenv("BETO_ACUERDO_QC", "0")
    monkeypatch.setenv("BETO_SUGERENCIA_HITL", "0")
    _servicio(monkeypatch, [])
    from services.validacion_relaciones import ContextoRelaciones, ReglaRelacion

    ctx_bad = ContextoRelaciones(
        reglas={
            "FECHA_GESTION_VALIDA": ReglaRelacion(
                "FECHA_GESTION_VALIDA", "Fecha ↔ Gestión", "", True, "ALTA",
                {"anio_min": 2015, "anio_max": 2030, "anios_invalidos": [205, 2580, 3035]},
                ["CORREGIR_FECHA", "MARCAR_SIN_DATO"],
            ),
        }
    )
    monkeypatch.setattr(consolidacion, "cargar_contexto_relaciones", lambda dw_db=None: ctx_bad)
    acta_bad_fecha = [{**ACTA[0], "AÑO INICIO": 2580}]
    lote, _ = _ingestar(entorno, tmp_path, acta_bad_fecha)
    monkeypatch.setattr(consolidacion, "obtener_indices", lambda textos, **kw: [0.95] * len(textos))
    res = consolidacion._consolidar(consolidacion.ConfirmDwInsertRequest(id_lote=lote.id_lote), entorno, None)
    assert res["desglose"]["inserted_academico"] == 0
    assert entorno.query(FactRendimientoAcademico).count() == 0
    casos = entorno.query(StagingEntidadNoResuelta).filter_by(motivo="RELACION_INCOHERENTE").all()
    assert len(casos) >= 1
    assert (casos[0].payload_json or {}).get("regla_relacion") == "FECHA_GESTION_VALIDA"


def test_ba_l3_acciones_bandeja_relacion_y_desacuerdo(entorno):
    from models.dim_estudiante import DimEstudiante
    from models.dim_modulo import DimModulo
    from services.revision_acciones_ejecutor import ejecutar_accion_contextual

    est = DimEstudiante(nombre_completo="MARIA TEST", ci="9988776", ci_numero="9988776", fk_estado="A")
    mod = DimModulo(pos_code="POS-5252", nombre_modulo="Módulo 1", programa="POS-5252")
    entorno.add_all([est, mod])
    entorno.flush()

    caso_rel = StagingEntidadNoResuelta(
        tipo_entidad="ESTUDIANTE", texto_original="fila test", fk_estado="C",
        resuelto=False, motivo="RELACION_INCOHERENTE", payload_json={"regla_relacion": "MODULO_EN_PROGRAMA"},
    )
    caso_fecha = StagingEntidadNoResuelta(
        tipo_entidad="ESTUDIANTE", texto_original="fila fecha", fk_estado="C",
        resuelto=False, motivo="RELACION_INCOHERENTE", payload_json={"regla_relacion": "FECHA_GESTION_VALIDA"},
    )
    caso_des = StagingEntidadNoResuelta(
        tipo_entidad="ESTUDIANTE", texto_original="fila des", fk_estado="C",
        resuelto=False, motivo="DESACUERDO_REGLA_BETO", payload_json={},
    )
    entorno.add_all([caso_rel, caso_fecha, caso_des])
    entorno.flush()

    ejecutar_accion_contextual(entorno, caso_rel, {"accion": "VINCULAR_RELACION", "id_modulo_destino": mod.id_modulo}, "admin", "ADMIN")
    assert caso_rel.resuelto is True and caso_rel.payload_json.get("id_modulo_vinculado") == mod.id_modulo

    ejecutar_accion_contextual(entorno, caso_fecha, {"accion": "CORREGIR_FECHA", "mes": 5, "gestion": 2025}, "admin", "ADMIN")
    assert caso_fecha.resuelto is True and caso_fecha.payload_json.get("gestion") == 2025

    ejecutar_accion_contextual(entorno, caso_des, {"accion": "VINCULAR_ESTUDIANTE", "id_estudiante_destino": est.id_estudiante}, "admin", "ADMIN")
    assert caso_des.resuelto is True and caso_des.payload_json.get("id_estudiante_vinculado") == est.id_estudiante
