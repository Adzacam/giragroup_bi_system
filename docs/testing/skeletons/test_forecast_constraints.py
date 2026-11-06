"""
docs/testing/skeletons/test_forecast_constraints.py
---------------------------------------------------
Esqueleto de pruebas unitarias para restricciones de entrada en modelos predictivos:
- Holt-Winters: Requiere N >= 24 observaciones mensuales (2 ciclos estacionales) y horizonte h <= 6.
- OLS Anual: Requiere N >= 3 gestiones para trazar tendencia lineal de metas.
Marcador: unit
"""

import pytest
import numpy as np

@pytest.mark.unit
class TestForecastConstraints:

    def test_holt_winters_rechaza_n_menor_a_24(self):
        """Holt-Winters estacional aditivo no puede ejecutarse con menos de 24 meses."""
        def validar_serie_hw(y: np.ndarray):
            if len(y) < 24:
                raise ValueError(f"Serie insuficiente para Holt-Winters estacional: se requieren N >= 24, recibidos N={len(y)}")
            return True

        serie_incompleta = np.ones(23)
        serie_completa = np.ones(24)

        with pytest.raises(ValueError, match="Serie insuficiente"):
            validar_serie_hw(serie_incompleta)

        assert validar_serie_hw(serie_completa) is True

    def test_holt_winters_limite_horizonte_maximo_6(self):
        """El horizonte de proyección no debe superar los 6 meses para acotar la incertidumbre."""
        def validar_horizonte_hw(h: int):
            if h < 1 or h > 6:
                raise ValueError("El horizonte debe encontrarse entre 1 y 6 meses.")
            return True

        with pytest.raises(ValueError):
            validar_horizonte_hw(7)

        with pytest.raises(ValueError):
            validar_horizonte_hw(0)

        assert validar_horizonte_hw(6) is True
        assert validar_horizonte_hw(1) is True

    def test_ols_anual_requiere_minimo_3_gestiones(self):
        """La regresión lineal OLS para metas anuales exige al menos 3 puntos históricos."""
        def validar_serie_ols(anios: list):
            if len(anios) < 3:
                raise ValueError(f"OLS requiere al menos 3 gestiones históricas, recibidas {len(anios)}")
            return True

        with pytest.raises(ValueError, match="al menos 3 gestiones"):
            validar_serie_ols([2023, 2024])

        assert validar_serie_ols([2022, 2023, 2024]) is True
