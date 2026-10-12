"""
tests/sprint3/test_financial_validator.py
-----------------------------------------
Suite de pruebas unitarias para el Loop 2 del pipeline financiero:
1. Sanitización de importes heterogéneos y monedas ('1.500 Bs', '1,500.00 BOB', etc.).
2. Detección de moneda institucional (BOB vs USD).
3. Verificación de consistencia contable: Saldo = Cuota - Pagado.
4. Detección de descuadres y generación de alertas contables.
5. Validación de duplas Meta vs. Ejecutado y cálculo de cumplimiento porcentual.
6. Detección de anomalías de escala presupuestaria (>250%).
"""

import pytest
from services.financial_validator_service import FinancialTransactionValidator


class TestSanitizarImporte:
    def test_formato_punto_miles_boliviano(self):
        assert FinancialTransactionValidator.sanitizar_importe("1.500 Bs") == 1500.0
        assert FinancialTransactionValidator.sanitizar_importe("Bs. 1.500") == 1500.0
        assert FinancialTransactionValidator.sanitizar_importe("2.800 Bs.") == 2800.0

    def test_formato_coma_decimal(self):
        assert FinancialTransactionValidator.sanitizar_importe("Bs. 1.500,50") == 1500.50
        assert FinancialTransactionValidator.sanitizar_importe("800,00 Bs") == 800.0

    def test_formato_anglosajon(self):
        assert FinancialTransactionValidator.sanitizar_importe("1,500.00 BOB") == 1500.0
        assert FinancialTransactionValidator.sanitizar_importe("1,250.75") == 1250.75

    def test_valores_numericos_nativos(self):
        assert FinancialTransactionValidator.sanitizar_importe(1500) == 1500.0
        assert FinancialTransactionValidator.sanitizar_importe(1500.55) == 1500.55

    def test_valores_negativos(self):
        assert FinancialTransactionValidator.sanitizar_importe("-250.00 Bs") == -250.0
        assert FinancialTransactionValidator.sanitizar_importe("(500)") == -500.0

    def test_valores_nulos_o_invalidos(self):
        assert FinancialTransactionValidator.sanitizar_importe(None) is None
        assert FinancialTransactionValidator.sanitizar_importe("") is None
        assert FinancialTransactionValidator.sanitizar_importe("N/A") is None
        assert FinancialTransactionValidator.sanitizar_importe("-") is None

    def test_cifras_grandes_multiples_puntos(self):
        assert FinancialTransactionValidator.sanitizar_importe("1.500.000 Bs") == 1500000.0


class TestExtraerMoneda:
    def test_detectar_moneda_boliviana(self):
        moneda, es_bob = FinancialTransactionValidator.extraer_moneda("1.500 Bs")
        assert moneda == "BOB"
        assert es_bob is True

        moneda, es_bob = FinancialTransactionValidator.extraer_moneda("Bs. 800,00")
        assert moneda == "BOB"
        assert es_bob is True

        moneda, es_bob = FinancialTransactionValidator.extraer_moneda("1200 BOB")
        assert moneda == "BOB"
        assert es_bob is True

    def test_detectar_moneda_extranjera(self):
        moneda, es_bob = FinancialTransactionValidator.extraer_moneda("$ 500")
        assert moneda == "USD"
        assert es_bob is False

        moneda, es_bob = FinancialTransactionValidator.extraer_moneda("350 USD")
        assert moneda == "USD"
        assert es_bob is False


class TestValidarTransaccionContable:
    def test_transaccion_consistente_numerica(self):
        res = FinancialTransactionValidator.validar_transaccion(cuota=1500.0, pagado=500.0, saldo=1000.0)
        assert res["valido"] is True
        assert res["cuadre_contable"] is True
        assert res["diferencia"] == 0.0
        assert res["requiere_revision"] is False
        assert len(res["errores"]) == 0

    def test_transaccion_consistente_con_cadenas_heterogeneas(self):
        res = FinancialTransactionValidator.validar_transaccion(
            cuota="1.500 Bs",
            pagado="Bs. 500",
            saldo="1,000.00 BOB",
            moneda_raw="BOB"
        )
        assert res["valido"] is True
        assert res["cuota"] == 1500.0
        assert res["pagado"] == 500.0
        assert res["saldo_registrado"] == 1000.0
        assert res["cuadre_contable"] is True

    def test_transaccion_con_descuadre_inconsistente(self):
        # Cuota 1500, Pagado 500 -> Saldo esperado = 1000, pero saldo registrado es 800 (diferencia 200)
        res = FinancialTransactionValidator.validar_transaccion(
            cuota=1500.0,
            pagado=500.0,
            saldo=800.0
        )
        assert res["valido"] is False
        assert res["cuadre_contable"] is False
        assert res["diferencia"] == 200.0
        assert res["saldo_calculado"] == 1000.0
        assert res["saldo_registrado"] == 800.0
        assert res["requiere_revision"] is True
        assert any("Inconsistencia contable" in err for err in res["errores"])

    def test_valores_nulos_o_ausentes(self):
        res = FinancialTransactionValidator.validar_transaccion(cuota=None, pagado=500, saldo=1000)
        assert res["valido"] is False
        assert res["requiere_revision"] is True
        assert any("Monto de Cuota no válido" in err for err in res["errores"])

    def test_montos_negativos_error(self):
        res = FinancialTransactionValidator.validar_transaccion(cuota=-1500, pagado=500, saldo=-2000)
        assert res["valido"] is False
        assert any("no pueden ser valores negativos" in err for err in res["errores"])


class TestValidarMetaEjecutado:
    def test_cumplimiento_normal_92_porciento(self):
        # Meta 150.000 Bs, Ejecutado 138.000 Bs -> Cumplimiento 92.0%
        res = FinancialTransactionValidator.validar_meta_ejecutado(
            meta="150.000 Bs",
            ejecutado="138.000 Bs",
            periodo="2026-01",
            categoria="PROGRAMAS"
        )
        assert res["valido"] is True
        assert res["meta"] == 150000.0
        assert res["ejecutado"] == 138000.0
        assert res["cumplimiento_pct"] == 92.0
        assert res["brecha"] == 12000.0
        assert res["anomalia_detectada"] is False
        assert res["requiere_revision"] is False

    def test_anomalia_de_escala_supera_250_porciento(self):
        res = FinancialTransactionValidator.validar_meta_ejecutado(
            meta=10000.0,
            ejecutado=30000.0
        )
        assert res["valido"] is True
        assert res["cumplimiento_pct"] == 300.0
        assert res["anomalia_detectada"] is True
        assert res["requiere_revision"] is True
        assert any("supera el 250%" in adv for adv in res["advertencias"])

    def test_meta_invalida_o_cero(self):
        res = FinancialTransactionValidator.validar_meta_ejecutado(meta=0, ejecutado=5000)
        assert res["valido"] is False
        assert res["requiere_revision"] is True
        assert any("mayor a cero" in err for err in res["errores"])
