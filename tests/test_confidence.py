"""
test_confidence.py — Tests unitarios para el motor de confianza (GIRA-42, GIRA-27)
"""

import pytest
from pipeline.analytics.confidence_engine import ConfidenceEngine


class TestCalcularConfianzaRegistro:
    """Tests para la fórmula lineal: (NER * 0.60) + (fuzzy * 0.40)"""

    def test_confianza_perfecta(self):
        """Ambas certezas al máximo → 1.0, sin revisión."""
        resultado = ConfidenceEngine.calcular_confianza_registro(1.0, 1.0)
        assert resultado["nivel_confianza_ia"] == 1.0
        assert resultado["requiere_revision"] is False

    def test_confianza_cero(self):
        """Ambas certezas en cero → 0.0, requiere revisión."""
        resultado = ConfidenceEngine.calcular_confianza_registro(0.0, 0.0)
        assert resultado["nivel_confianza_ia"] == 0.0
        assert resultado["requiere_revision"] is True

    def test_formula_correcta(self):
        """Verificar la ponderación 60/40."""
        # (0.80 * 0.60) + (0.70 * 0.40) = 0.48 + 0.28 = 0.76
        resultado = ConfidenceEngine.calcular_confianza_registro(0.80, 0.70)
        assert resultado["nivel_confianza_ia"] == 0.76
        assert resultado["requiere_revision"] is False

    def test_umbral_exacto_no_requiere_revision(self):
        """Score exacto de 0.60 no requiere revisión (solo < 0.60)."""
        # (1.0 * 0.60) + (0.0 * 0.40) = 0.60
        resultado = ConfidenceEngine.calcular_confianza_registro(1.0, 0.0)
        assert resultado["nivel_confianza_ia"] == 0.6
        assert resultado["requiere_revision"] is False

    def test_debajo_umbral_requiere_revision(self):
        """Score por debajo de 0.60 → requiere revisión."""
        # (0.50 * 0.60) + (0.50 * 0.40) = 0.30 + 0.20 = 0.50
        resultado = ConfidenceEngine.calcular_confianza_registro(0.50, 0.50)
        assert resultado["nivel_confianza_ia"] == 0.50
        assert resultado["requiere_revision"] is True

    def test_clamp_valores_fuera_de_rango(self):
        """Valores > 1.0 o < 0.0 se clampen a [0, 1]."""
        resultado = ConfidenceEngine.calcular_confianza_registro(1.5, -0.3)
        # (1.0 * 0.60) + (0.0 * 0.40) = 0.60
        assert resultado["nivel_confianza_ia"] == 0.6
        assert resultado["requiere_revision"] is False

    def test_caso_limite_bajo_umbral(self):
        """Caso justo por debajo del umbral 0.60."""
        # (0.98 * 0.60) + (0.01 * 0.40) = 0.588 + 0.004 = 0.592
        resultado = ConfidenceEngine.calcular_confianza_registro(0.98, 0.01)
        assert resultado["nivel_confianza_ia"] == 0.592
        assert resultado["requiere_revision"] is True


class TestCalcularEstadoDashboard:
    """Tests para el semáforo VERDE/AMARILLO/ROJO."""

    def test_estado_verde(self):
        """Promedio ≥ 0.85 → VERDE."""
        resultado = ConfidenceEngine.calcular_estado_dashboard([0.90, 0.95, 0.88])
        assert resultado["estado_dashboard"] == "VERDE"
        assert resultado["indice_confianza_global"] >= 0.85

    def test_estado_amarillo(self):
        """Promedio ≥ 0.60 y < 0.85 → AMARILLO."""
        resultado = ConfidenceEngine.calcular_estado_dashboard([0.70, 0.65, 0.75])
        assert resultado["estado_dashboard"] == "AMARILLO"

    def test_estado_rojo(self):
        """Promedio < 0.60 → ROJO."""
        resultado = ConfidenceEngine.calcular_estado_dashboard([0.30, 0.40, 0.50])
        assert resultado["estado_dashboard"] == "ROJO"

    def test_lista_vacia(self):
        """Lista vacía → confianza 0.0, ROJO."""
        resultado = ConfidenceEngine.calcular_estado_dashboard([])
        assert resultado["indice_confianza_global"] == 0.0
        assert resultado["estado_dashboard"] == "ROJO"

    def test_un_solo_registro(self):
        """Un solo registro con alta confianza → VERDE."""
        resultado = ConfidenceEngine.calcular_estado_dashboard([0.92])
        assert resultado["estado_dashboard"] == "VERDE"
        assert resultado["indice_confianza_global"] == 0.92

    def test_umbral_exacto_verde(self):
        """Promedio exacto 0.85 → VERDE."""
        resultado = ConfidenceEngine.calcular_estado_dashboard([0.85])
        assert resultado["estado_dashboard"] == "VERDE"

    def test_umbral_exacto_amarillo(self):
        """Promedio exacto 0.60 → AMARILLO."""
        resultado = ConfidenceEngine.calcular_estado_dashboard([0.60])
        assert resultado["estado_dashboard"] == "AMARILLO"

    def test_mezcla_registros(self):
        """Mezcla de registros altos y bajos → AMARILLO."""
        # Promedio: (0.90 + 0.40 + 0.80 + 0.55) / 4 = 2.65 / 4 = 0.6625
        resultado = ConfidenceEngine.calcular_estado_dashboard([0.90, 0.40, 0.80, 0.55])
        assert resultado["estado_dashboard"] == "AMARILLO"
        assert resultado["indice_confianza_global"] == 0.6625
