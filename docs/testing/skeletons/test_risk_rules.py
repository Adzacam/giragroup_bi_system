"""
docs/testing/skeletons/test_risk_rules.py
-----------------------------------------
Esqueleto de pruebas unitarias puras para las reglas de negocio críticas de riesgo.
Reglas:
- Riesgo Académico: nota final <= 70.0
- Riesgo Deserción: tasa inactividad / asistencia < 70% o > 30% riesgo
- Riesgo Financiero: cuotas en mora >= 2
- Riesgo Cruzado: intersección determinista de alertas académicas y financieras
Marcador: unit
"""

import pytest
from unittest.mock import MagicMock

@pytest.mark.unit
class TestRiskRulesUnit:

    def test_riesgo_academico_umbral_exacto_70(self):
        """Regla crítica: una nota de 70.0 debe ser clasificada en RIESGO ACADÉMICO (<= 70)."""
        nota_borde_reprobado = 70.0
        nota_borde_aprobado = 70.1

        def es_riesgo_academico(nota: float, umbral: float = 70.0) -> bool:
            return nota is not None and nota <= umbral

        assert es_riesgo_academico(nota_borde_reprobado) is True
        assert es_riesgo_academico(nota_borde_aprobado) is False
        assert es_riesgo_academico(45.0) is True
        assert es_riesgo_academico(100.0) is False

    def test_riesgo_desercion_umbral_30_porciento(self):
        """Regla crítica: probabilidad o factor de deserción acumulada > 30% o inactividad prolongada."""
        def clasificar_riesgo_desercion(asistencia_pct: float, inasistencias_consecutivas: int) -> dict:
            if asistencia_pct < 70.0 or inasistencias_consecutivas >= 3:
                return {"en_riesgo": True, "severidad": "CRITICAL" if asistencia_pct < 50.0 else "WARNING"}
            return {"en_riesgo": False, "severidad": "INFO"}

        res_riesgo = clasificar_riesgo_desercion(asistencia_pct=69.9, inasistencias_consecutivas=0)
        assert res_riesgo["en_riesgo"] is True
        assert res_riesgo["severidad"] == "WARNING"

        res_seguro = clasificar_riesgo_desercion(asistencia_pct=85.0, inasistencias_consecutivas=1)
        assert res_seguro["en_riesgo"] is False

    def test_riesgo_financiero_cuotas_mora_minimo_dos(self):
        """Regla crítica: 2 o más cuotas vencidas generan alerta financiera obligatoria."""
        def evaluar_alerta_mora(cuotas_vencidas: int, monto_deuda: float) -> bool:
            return cuotas_vencidas >= 2 and monto_deuda > 0.0

        assert evaluar_alerta_mora(cuotas_vencidas=1, monto_deuda=500.0) is False
        assert evaluar_alerta_mora(cuotas_vencidas=2, monto_deuda=1200.0) is True
        assert evaluar_alerta_mora(cuotas_vencidas=3, monto_deuda=2500.0) is True
        assert evaluar_alerta_mora(cuotas_vencidas=2, monto_deuda=0.0) is False

    def test_riesgo_cruzado_interseccion_dual(self):
        """Regla crítica: si confluyen riesgo académico y mora financiera, se eleva a RIESGO_CRUZADO."""
        def clasificar_riesgo_cruzado(es_academico: bool, es_financiero: bool) -> str:
            if es_academico and es_financiero:
                return "RIESGO_CRUZADO_ALTO"
            if es_academico:
                return "RIESGO_ACADEMICO"
            if es_financiero:
                return "RIESGO_FINANCIERO"
            return "REGULAR"

        assert clasificar_riesgo_cruzado(True, True) == "RIESGO_CRUZADO_ALTO"
        assert clasificar_riesgo_cruzado(True, False) == "RIESGO_ACADEMICO"
        assert clasificar_riesgo_cruzado(False, True) == "RIESGO_FINANCIERO"
        assert clasificar_riesgo_cruzado(False, False) == "REGULAR"
