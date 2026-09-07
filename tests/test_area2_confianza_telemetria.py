"""
tests/test_area2_confianza_telemetria.py
-----------------------------------------
Suite de pruebas para GIRA-42 (Nivel de confianza probabilístico)
y GIRA-12 (Persistencia de rendimiento y telemetría).
"""

import json
from pathlib import Path
import pytest

from pipeline.config import UMBRAL_CONFIANZA_ALTO, UMBRAL_CONFIANZA_MEDIO
from pipeline.semantic.ner_schema import (
    EntidadExtraida,
    ResultadoInferenciaNER,
    TipoEntidad,
    NivelConfianza
)
from pipeline.semantic.performance_logger import PerformanceLogger, MetricasTelemetria


def test_gira42_niveles_confianza_probabilistica():
    """Verifica la asignación rigurosa de los 3 niveles de confianza según score."""
    # Alta confianza (>= 0.85)
    e_alta = EntidadExtraida(
        tipo=TipoEntidad.DOCENTE,
        valor="CARLOS ROJAS",
        start_char=0,
        end_char=12,
        score=0.92
    )
    assert e_alta.nivel_confianza == NivelConfianza.ALTA
    assert e_alta.es_confiable() is True
    assert e_alta.requiere_revision() is False

    # Media confianza ([0.60, 0.85))
    e_media = EntidadExtraida(
        tipo=TipoEntidad.ESTUDIANTE,
        valor="JUAN P.",
        start_char=15,
        end_char=22,
        score=0.74
    )
    assert e_media.nivel_confianza == NivelConfianza.MEDIA
    assert e_media.es_confiable() is False
    assert e_media.requiere_revision() is True

    # Baja confianza (< 0.60)
    e_baja = EntidadExtraida(
        tipo=TipoEntidad.PROGRAMA,
        valor="CURSO",
        start_char=25,
        end_char=30,
        score=0.45
    )
    assert e_baja.nivel_confianza == NivelConfianza.BAJA
    assert e_baja.es_confiable() is False
    assert e_baja.requiere_revision() is False


def test_gira42_serializacion_contrato_con_nivel():
    """Verifica que to_dict incluya nivel_confianza y requiere_revision."""
    ent = EntidadExtraida(
        tipo=TipoEntidad.NOTA,
        valor="85",
        start_char=0,
        end_char=2,
        score=0.78
    )
    d = ent.to_dict()
    assert d["nivel_confianza"] == "MEDIA"
    assert d["requiere_revision"] is True
    assert d["score"] == 0.78
    assert d["tipo"] == "NOTA"
    assert d["entidad"] == "85"


def test_gira42_filtros_resultado_inferencia():
    """Verifica los métodos de filtrado por nivel y revisión en ResultadoInferenciaNER."""
    e1 = EntidadExtraida(TipoEntidad.DOCENTE, "DR. LOPEZ", 0, 9, 0.95)
    e2 = EntidadExtraida(TipoEntidad.ESTUDIANTE, "ANA PAZ", 15, 22, 0.70)
    e3 = EntidadExtraida(TipoEntidad.MODULO, "MODULO 1", 30, 38, 0.50)

    res = ResultadoInferenciaNER(
        texto="DR. LOPEZ evaluó a ANA PAZ en MODULO 1",
        entidades=[e1, e2, e3]
    )

    altas = res.entidades_por_nivel(NivelConfianza.ALTA)
    medias = res.entidades_por_nivel("MEDIA")
    bajas = res.entidades_por_nivel(NivelConfianza.BAJA)
    revision = res.entidades_que_requieren_revision()

    assert len(altas) == 1 and altas[0].valor == "DR. LOPEZ"
    assert len(medias) == 1 and medias[0].valor == "ANA PAZ"
    assert len(bajas) == 1 and bajas[0].valor == "MODULO 1"
    assert len(revision) == 1 and revision[0].valor == "ANA PAZ"


def test_gira12_performance_logger_registro_y_persistencia(tmp_path):
    """Verifica el cálculo de telemetría y la persistencia en disco JSONL."""
    ruta_log = tmp_path / "test_telemetria.jsonl"
    logger = PerformanceLogger(ruta_archivo=ruta_log)

    e1 = EntidadExtraida(TipoEntidad.DOCENTE, "CARLOS ROJAS", 0, 12, 0.95)
    e2 = EntidadExtraida(TipoEntidad.ESTUDIANTE, "JUAN PEREZ", 15, 25, 0.88)
    r1 = ResultadoInferenciaNER(
        texto="El docente CARLOS ROJAS evaluó al estudiante JUAN PEREZ.",
        entidades=[e1, e2],
        tiempo_inferencia_ms=25.0,
        modelo="beto_test",
        dispositivo="cpu"
    )

    metricas = logger.registrar_lote([r1], tiempo_total_ms=25.0)

    assert isinstance(metricas, MetricasTelemetria)
    assert metricas.total_oraciones == 1
    assert metricas.total_entidades == 2
    assert metricas.tiempo_total_ms == 25.0
    assert metricas.latencia_ms_por_oracion == 25.0
    assert metricas.tokens_por_segundo > 0
    assert metricas.entidades_por_nivel["ALTA"] == 2
    assert metricas.entidades_por_tipo["DOCENTE"] == 1
    assert metricas.entidades_por_tipo["ESTUDIANTE"] == 1

    # Verificar existencia y contenido del archivo JSONL
    assert ruta_log.exists()
    lineas = ruta_log.read_text(encoding="utf-8").strip().split("\n")
    assert len(lineas) == 1
    data_guardada = json.loads(lineas[0])
    assert data_guardada["total_oraciones"] == 1
    assert data_guardada["modelo"] == "beto_test"

    # Resumen acumulado
    resumen = logger.obtener_resumen()
    assert resumen["total_ejecuciones"] == 1
    assert resumen["total_oraciones_procesadas"] == 1
    assert resumen["total_entidades_extraidas"] == 2
