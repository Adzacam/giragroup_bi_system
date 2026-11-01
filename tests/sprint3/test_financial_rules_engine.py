"""
tests/sprint3/test_financial_rules_engine.py
--------------------------------------------
Suite de pruebas unitarias para el Loop 4:
1. Reglas determinísticas de riesgo de cartera (Mora crítica, preventiva, al día).
2. Detección de alerta compuesta dual (Riesgo Académico <= 70 pts + Deuda Financiera >= 2 cuotas).
3. Detección de anomalías de escala (Meta vs. Ejecutado > 200%).
4. Detección de anomalías operativas (Sobrepago atípico > 3x, descuento excesivo, cuotas inconsistentes).
5. Preparación desacoplada de series temporales para modelos Holt-Winters.
"""

import pytest
from services.financial_rules_engine import FinancialRulesEngine


class TestFinancialRiskRules:
    def test_saldo_cero_al_dia(self):
        res = FinancialRulesEngine.evaluar_riesgo_cartera(
            cuotas_impagas=0,
            dias_mora=0,
            saldo=0.0
        )
        assert res["estado_cartera"] == "AL_DIA"
        assert res["nivel_riesgo"] == "NINGUNO"
        assert res["requiere_gestion"] is False
        assert res["es_riesgo_critico"] is False
        assert res["es_riesgo_dual"] is False

    def test_mora_critica_dos_cuotas(self):
        res = FinancialRulesEngine.evaluar_riesgo_cartera(
            cuotas_impagas=2,
            dias_mora=45,
            saldo=3000.0
        )
        assert res["estado_cartera"] == "MORA_CRITICA"
        assert res["nivel_riesgo"] == "CRITICO"
        assert res["requiere_gestion"] is True
        assert res["es_riesgo_critico"] is True
        assert any("Mora crítica detectada" in r for r in res["reglas_activadas"])

    def test_mora_critica_por_dias_mora_90(self):
        res = FinancialRulesEngine.evaluar_riesgo_cartera(
            cuotas_impagas=1,
            dias_mora=95,
            saldo=1500.0
        )
        assert res["estado_cartera"] == "MORA_CRITICA"
        assert res["nivel_riesgo"] == "CRITICO"
        assert res["requiere_gestion"] is True

    def test_mora_preventiva_una_cuota_15_dias(self):
        res = FinancialRulesEngine.evaluar_riesgo_cartera(
            cuotas_impagas=1,
            dias_mora=20,
            saldo=1500.0
        )
        assert res["estado_cartera"] == "MORA_PREVENTIVA"
        assert res["nivel_riesgo"] == "MEDIO"
        assert res["requiere_gestion"] is True
        assert res["es_riesgo_critico"] is False

    def test_periodo_de_gracia_tolerancia(self):
        res = FinancialRulesEngine.evaluar_riesgo_cartera(
            cuotas_impagas=1,
            dias_mora=7,
            saldo=1500.0
        )
        assert res["estado_cartera"] == "PERIODO_GRACIA"
        assert res["nivel_riesgo"] == "BAJO"
        assert res["requiere_gestion"] is False

    def test_alerta_dual_academico_financiera(self):
        # Alumno con 2 cuotas en mora Y nota 64 pts (reprobación en riesgo)
        res = FinancialRulesEngine.evaluar_riesgo_cartera(
            cuotas_impagas=2,
            dias_mora=60,
            saldo=3000.0,
            nota_academica=64.0
        )
        assert res["nivel_riesgo"] == "EXTREMO_DUAL"
        assert res["es_riesgo_critico"] is True
        assert res["es_riesgo_dual"] is True
        assert any("Alerta combinada de retención" in r for r in res["reglas_activadas"])


class TestFinancialAnomalyDetection:
    def test_anomalia_desproporcion_meta_ejecutado(self):
        # Meta 150.000 Bs y Ejecutado 350.000 Bs (> 200%)
        anomalias = FinancialRulesEngine.detectar_anomalias_financieras({
            "meta": "150.000 Bs",
            "ejecutado": "350.000 Bs"
        })
        assert len(anomalias) >= 1
        anom = next(a for a in anomalias if a["tipo"] == "DESPROPORCION_META_EJECUTADO")
        assert anom["severidad"] == "WARNING"
        assert "supera en más del 200%" in anom["mensaje"]

    def test_anomalia_ejecutado_negativo(self):
        anomalias = FinancialRulesEngine.detectar_anomalias_financieras({
            "meta": 100000,
            "ejecutado": -5000
        })
        assert len(anomalias) >= 1
        anom = next(a for a in anomalias if a["tipo"] == "EJECUTADO_NEGATIVO")
        assert anom["severidad"] == "CRITICAL"

    def test_anomalia_sobrepago_atipico(self):
        # Cuota 1.500 Bs pero pago registrado 8.500 Bs (sin contado)
        anomalias = FinancialRulesEngine.detectar_anomalias_financieras({
            "cuota": "1.500 Bs",
            "pago": "8.500 Bs",
            "tipo_inscripcion": "CUOTAS"
        })
        assert len(anomalias) >= 1
        anom = next(a for a in anomalias if a["tipo"] == "SOBREPAGO_ATIPICO")
        assert anom["severidad"] == "WARNING"
        assert "Sobrepago atípico" in anom["mensaje"]

    def test_anomalia_descuento_excesivo(self):
        anomalias = FinancialRulesEngine.detectar_anomalias_financieras({
            "costo_programa": "5.000 Bs",
            "descuento": "6.000 Bs"
        })
        assert len(anomalias) >= 1
        anom = next(a for a in anomalias if a["tipo"] == "DESCUENTO_EXCESIVO")
        assert anom["severidad"] == "CRITICAL"

    def test_anomalia_cuotas_en_mora_inconsistentes(self):
        anomalias = FinancialRulesEngine.detectar_anomalias_financieras({
            "cuotas_en_mora": 14,
            "total_cuotas": 10
        })
        assert len(anomalias) >= 1
        anom = next(a for a in anomalias if a["tipo"] == "CUOTAS_MORA_SUPERIOR_TOTAL")
        assert anom["severidad"] == "CRITICAL"

    def test_registro_limpio_sin_anomalias(self):
        anomalias = FinancialRulesEngine.detectar_anomalias_financieras({
            "meta": 150000,
            "ejecutado": 138000,
            "cuota": 1500,
            "pago": 1500,
            "costo_programa": 9000,
            "descuento": 1000,
            "cuotas_en_mora": 1,
            "total_cuotas": 6
        })
        assert len(anomalias) == 0


class TestHoltWintersDecoupledPreparation:
    def test_preparar_serie_temporal(self):
        historico = [
            {"periodo": "2025-01", "valor": "120.000 Bs"},
            {"periodo": "2025-02", "valor": "125.000 Bs"},
            {"periodo": "2025-03", "valor": "132.000 Bs"},
            {"periodo": "2025-04", "valor": "138.000 Bs"},
        ]
        res = FinancialRulesEngine.preparar_serie_temporal_holtwinters(historico)
        assert res["n_puntos"] == 4
        assert res["es_apta_holtwinters"] is True
        assert res["valores"] == [120000.0, 125000.0, 132000.0, 138000.0]
        assert "ExponentialSmoothing" in res["sugerencia_modelo"]
