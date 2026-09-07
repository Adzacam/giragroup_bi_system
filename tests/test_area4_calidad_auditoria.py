"""
tests/test_area4_calidad_auditoria.py
--------------------------------------
Suite de pruebas unitarias y de integración para el ÁREA 4:
- GIRA-27: Evaluador de reglas de calidad y flag `requiere_revision`.
- GIRA-43: Registro y trazabilidad de inconsistencias en JSONL y métricas.
"""

import json
import pytest
from pathlib import Path

from pipeline.config import (
    UMBRAL_REVISION_BETO,
    UMBRAL_REVISION_FUZZY,
    NOTA_MINIMA_VALIDA,
    NOTA_MAXIMA_VALIDA,
    NOTA_APROBACION_MINIMA
)
from pipeline.normalization.quality_rules import (
    QualityEvaluator,
    ResultadoCalidad,
    SeveridadRegla
)
from pipeline.analytics.audit_logger import (
    AuditLogger,
    EventoInconsistencia,
    SeveridadInconsistencia
)
from pipeline.semantic.ner_schema import (
    ResultadoInferenciaNER,
    EntidadExtraida,
    TipoEntidad
)
from pipeline.normalization.fk_resolver import FKResolver


@pytest.fixture
def evaluador():
    return QualityEvaluator()


@pytest.fixture
def audit_logger_temp(tmp_path):
    ruta_temp = tmp_path / "test_inconsistencias.jsonl"
    return AuditLogger(ruta_log=ruta_temp)


# ══════════════════════════════════════════════════════════════════════════════
# GIRA-27: Pruebas del Evaluador de Reglas de Calidad
# ══════════════════════════════════════════════════════════════════════════════

def test_evaluador_nota_valida_no_activa_revision(evaluador):
    registro = {
        "estudiante": "Juan Perez",
        "ci": "4859201",
        "nota": 85.5,
        "estado_academico": "Aprobado",
        "score_matching": 0.95
    }
    resultado = evaluador.evaluar_registro_academico(registro)
    assert not resultado.requiere_revision
    assert len(resultado.motivos) == 0
    assert resultado.severidad_maxima == SeveridadRegla.INFO


def test_evaluador_nota_fuera_de_rango(evaluador):
    # Caso 1: Nota negativa
    reg_neg = {"estudiante": "Ana Ramos", "ci": "5920194", "nota": -5}
    res_neg = evaluador.evaluar_registro_academico(reg_neg)
    assert res_neg.requiere_revision
    assert any("NOTA_FUERA_DE_RANGO" in m for m in res_neg.motivos)
    assert res_neg.severidad_maxima == SeveridadRegla.ERROR

    # Caso 2: Nota mayor a 100
    reg_sup = {"estudiante": "Carlos Lopez", "ci": "5920194", "nota": 105}
    res_sup = evaluador.evaluar_registro_academico(reg_sup)
    assert res_sup.requiere_revision
    assert any("NOTA_FUERA_DE_RANGO" in m for m in res_sup.motivos)
    assert res_sup.severidad_maxima == SeveridadRegla.ERROR

    # Caso 3: Nota no numérica
    reg_nan = {"estudiante": "Pedro Soto", "ci": "5920194", "nota": "CORRUPTO"}
    res_nan = evaluador.evaluar_registro_academico(reg_nan)
    assert res_nan.requiere_revision
    assert any("NOTA_NO_NUMERICA" in m for m in res_nan.motivos)


def test_evaluador_ci_sintetico_activa_flag(evaluador):
    # Registro con CI sintético generado por FKResolver (Estado C)
    registro = {
        "estudiante": "Persona Totalmente Desconocida",
        "ci": "TEMP-CI-9A8B7C6D",
        "nota": 70,
        "es_sintetico": True,
        "requiere_auditoria": True
    }
    resultado = evaluador.evaluar_registro_academico(registro)
    assert resultado.requiere_revision
    assert any("CI_NO_RESUELTO_SINTETICO" in m for m in resultado.motivos)
    assert resultado.severidad_maxima == SeveridadRegla.ERROR


def test_evaluador_score_beto_bajo(evaluador):
    # Entidad extraída por BETO con confianza < 0.65
    entidad_dudosa = EntidadExtraida(
        tipo=TipoEntidad.DOCENTE,
        valor="Dr. Posible Docente",
        start_char=0,
        end_char=18,
        score=0.62  # < 0.65
    )
    ner_res = ResultadoInferenciaNER(
        texto="Texto de prueba",
        entidades=[entidad_dudosa]
    )
    registro = {"nota": 80, "ci": "1234567"}
    resultado = evaluador.evaluar_registro_academico(registro, inferencia_ner=ner_res)
    assert resultado.requiere_revision
    assert any("BETO_CONF_BAJA" in m for m in resultado.motivos)


def test_evaluador_fuzzy_score_bajo(evaluador):
    # Similitud en catálogo < 80%
    registro = {
        "estudiante": "Juan Perez",
        "ci": "4859201",
        "nota": 85,
        "score_matching": 0.74  # < 0.80
    }
    resultado = evaluador.evaluar_registro_academico(registro)
    assert resultado.requiere_revision
    assert any("SCORE_FUZZY_BAJO" in m for m in resultado.motivos)


def test_evaluador_incoherencia_academica(evaluador):
    # Caso 1: Aprobado con nota insuficiente (< 51)
    reg_aprob_bajo = {
        "estudiante": "Maria Silva",
        "ci": "4859201",
        "nota": 45,
        "estado_academico": "Aprobado"
    }
    res1 = evaluador.evaluar_registro_academico(reg_aprob_bajo)
    assert res1.requiere_revision
    assert any("INCOHERENCIA_ESTADO_NOTA" in m for m in res1.motivos)

    # Caso 2: Reprobado con nota suficiente (>= 51)
    reg_rep_alto = {
        "estudiante": "Maria Silva",
        "ci": "4859201",
        "nota": 80,
        "estado_academico": "Reprobado"
    }
    res2 = evaluador.evaluar_registro_academico(reg_rep_alto)
    assert res2.requiere_revision
    assert any("INCOHERENCIA_ESTADO_NOTA" in m for m in res2.motivos)


def test_preservacion_datos_originales(evaluador):
    registro_original = {
        "archivo_origen": "ACTAS_2024.xlsx",
        "hoja": "Notas Módulo 1",
        "fila": 42,
        "estudiante_raw": "  perez mamani, Juan  ",
        "nota_raw": "-10",
        "custom_metadata": {"cod": 999}
    }
    res = evaluador.evaluar_registro_academico(registro_original)
    assert res.requiere_revision
    assert res.valores_auditados["archivo_origen"] == "ACTAS_2024.xlsx"
    assert res.valores_auditados["fila"] == 42
    assert res.valores_auditados["custom_metadata"] == {"cod": 999}


def test_evaluador_financiero(evaluador):
    # Monto negativo
    reg_fin = {
        "cliente": "Empresa XYZ",
        "ci": "1234567",
        "monto": -1500.00
    }
    res = evaluador.evaluar_registro_financiero(reg_fin)
    assert res.requiere_revision
    assert any("MONTO_NEGATIVO" in m for m in res.motivos)


# ══════════════════════════════════════════════════════════════════════════════
# GIRA-43: Pruebas de AuditLogger e Inconsistencias JSONL
# ══════════════════════════════════════════════════════════════════════════════

def test_audit_logger_registro_individual(audit_logger_temp):
    evento = audit_logger_temp.registrar_inconsistencia(
        tipo_inconsistencia="NOTA_FUERA_DE_RANGO",
        campo_afectado="nota",
        valor_recibido=-20,
        severidad=SeveridadInconsistencia.ERROR,
        archivo="ACTA_NOTAS_POS5252.xlsx",
        hoja="Notas",
        bloque_id=1,
        fila=15
    )

    assert evento.tipo_inconsistencia == "NOTA_FUERA_DE_RANGO"
    assert evento.severidad == "ERROR"
    assert evento.archivo == "ACTA_NOTAS_POS5252.xlsx"

    # Verificar que se escribió en el archivo JSONL
    lineas = audit_logger_temp.leer_inconsistencias()
    assert len(lineas) == 1
    assert lineas[0]["campo_afectado"] == "nota"
    assert lineas[0]["valor_recibido"] == -20
    assert "timestamp" in lineas[0]


def test_audit_logger_desde_resultado_calidad(audit_logger_temp, evaluador):
    registro_dudoso = {
        "estudiante": "Estudiante Prueba",
        "ci": "TEMP-CI-ABC12345",
        "nota": 115,
        "score_matching": 0.50
    }
    res_calidad = evaluador.evaluar_registro_academico(registro_dudoso)
    assert res_calidad.requiere_revision

    eventos = audit_logger_temp.registrar_desde_evaluacion_calidad(
        resultado_calidad=res_calidad,
        archivo="PRUEBA_INTEGRACION.xlsx",
        hoja="Hoja1",
        fila=10
    )

    # Debe haber registrado al menos eventos para la nota, el CI sintético y el fuzzy score
    assert len(eventos) >= 2

    # Verificar lectura de JSONL
    registros_guardados = audit_logger_temp.leer_inconsistencias()
    assert len(registros_guardados) == len(eventos)
    for r in registros_guardados:
        assert r["archivo"] == "PRUEBA_INTEGRACION.xlsx"
        assert r["fila"] == 10


def test_audit_logger_resumen_metricas(audit_logger_temp):
    audit_logger_temp.registrar_inconsistencia("ERR_1", "campo1", 1, SeveridadInconsistencia.ERROR, archivo="A.xlsx")
    audit_logger_temp.registrar_inconsistencia("ERR_2", "campo2", 2, SeveridadInconsistencia.WARNING, archivo="A.xlsx")
    audit_logger_temp.registrar_inconsistencia("ERR_1", "campo1", 3, SeveridadInconsistencia.CRITICAL, archivo="B.xlsx")

    resumen = audit_logger_temp.obtener_resumen_metricas()
    assert resumen["total_inconsistencias"] == 3
    assert resumen["por_severidad"]["ERROR"] == 1
    assert resumen["por_severidad"]["WARNING"] == 1
    assert resumen["por_severidad"]["CRITICAL"] == 1
    assert resumen["top_tipos"][0][0] == "ERR_1"
