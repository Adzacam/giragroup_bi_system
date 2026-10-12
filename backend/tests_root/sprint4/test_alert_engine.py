"""
tests/sprint4/test_alert_engine.py
----------------------------------
Pruebas para el Motor de Alertas IF/THEN (AlertEngine):
- Riesgo académico (promedio / nota_final <= 70.0)
- Riesgo de deserción (incumplimiento > 30%)
- Riesgo financiero (cuotas_impagas >= 2 y estado_cartera Previsionable)
- Derivación y alertas de entidades no resueltas en staging (Estado C)
"""

import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from services.alert_engine import AlertEngine, AlertItem
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from models.dim_estudiante import DimEstudiante
from models.staging_entidad import StagingEntidadNoResuelta


class TestAlertEngineRules:
    def test_regla_riesgo_academico(self):
        db = MagicMock(spec=Session)
        # Mock de 2 casos: nota 65.0 y nota 45.0
        db.query().join().outerjoin().filter().all.return_value = [
            (65.0, "Carlos Gomez", "4892019", "Módulo 1"),
            (45.0, "Maria Lopez", "8932014", "Módulo 2")
        ]

        engine = AlertEngine(db)
        alertas = engine.evaluar_riesgo_academico(limite_nota=70.0)

        assert len(alertas) == 2
        assert alertas[0].tipo == "ACADEMICO"
        assert alertas[0].severidad == "WARNING"  # >= 51
        assert alertas[0].metrica_valor == 65.0
        assert alertas[1].severidad == "CRITICAL"  # < 51
        assert alertas[0].role_target == "DIRECTOR_ACADEMICO"

    def test_regla_riesgo_desercion(self):
        db = MagicMock(spec=Session)
        db.query().join().outerjoin().filter().all.return_value = [
            (45.0, "Pedro Alarcon", "7614226", "Diplomado Finanzas")
        ]

        engine = AlertEngine(db)
        alertas = engine.evaluar_riesgo_desercion(umbral_incumplimiento=30.0)

        assert len(alertas) == 1
        assert alertas[0].tipo == "DESERCION"
        assert alertas[0].severidad == "CRITICAL"
        assert alertas[0].metrica_valor == 45.0
        assert "> 30.0%" in alertas[0].umbral_disparador

    def test_regla_riesgo_financiero(self):
        db = MagicMock(spec=Session)
        db.query().join().filter().all.return_value = [
            (2, 3500.0, "Mora", "Juan Perez", "123456"),
            (0, 7200.0, "Previsionable", "Elena Rios", "654321")
        ]

        engine = AlertEngine(db)
        alertas = engine.evaluar_riesgo_financiero(min_cuotas=2)

        assert len(alertas) == 2
        assert alertas[0].tipo == "FINANCIERO"
        assert alertas[0].role_target == "ANALISTA_FINANCIERO"
        assert alertas[1].severidad == "CRITICAL"  # Previsionable

    def test_regla_entidades_no_resueltas(self):
        db = MagicMock(spec=Session)
        stg_mock = StagingEntidadNoResuelta(
            texto_original="Dr. Desconocido",
            ci_temporal=None,
            tipo_entidad="DOCENTE",
            score_fuzzy=60.0,
            mejor_candidato="Dr. David Quispe"
        )
        db.query().filter().all.return_value = [stg_mock]

        engine = AlertEngine(db)
        alertas = engine.evaluar_entidades_no_resueltas()

        assert len(alertas) == 1
        assert alertas[0].tipo == "DATAOPS_CALIDAD"
        assert alertas[0].role_target == "AUDITOR_CALIDAD"
