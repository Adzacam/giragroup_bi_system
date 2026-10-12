"""
tests/test_forecasting.py
-------------------------
GIRA-58: Suite de pruebas unitarias y de integración para el módulo de forecasting.
Cubre:
1. Motor Holt-Winters (GIRA-54)
2. Estimador OLS para metas anuales (GIRA-55)
3. Extractor de series temporales (GIRA-53)
4. Resolución temporal y persistencia (GIRA-56)
5. Endpoints API REST FastAPI (GIRA-57)
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

# Configurar path raíz
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configurar backend en sys.path para imports de app
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from pipeline.analytics.forecasting_holtwinters import entrenar_y_proyectar_hw
from pipeline.analytics.forecasting_ols import estimar_tendencia_anual_ols
from pipeline.analytics.time_series_extractor import extraer_serie_temporal
from pipeline.analytics.forecast_loader import _resolver_id_tiempo
from backend.main import app


# ─────────────────────────────────────────────────────────────────────────────
# 1. PRUEBAS DEL MOTOR HOLT-WINTERS (GIRA-54)
# ─────────────────────────────────────────────────────────────────────────────

def test_holtwinters_proyeccion_exitosa():
    """Valida ajuste y proyección con serie sintética de 36 periodos."""
    np.random.seed(42)
    # 36 meses con tendencia lineal y estacionalidad anual
    t = np.arange(36)
    estacionalidad = 50 * np.sin(2 * np.pi * t / 12)
    tendencia = 10 * t + 200
    ruido = np.random.normal(0, 10, 36)
    valores = tendencia + estacionalidad + ruido

    periodos = pd.period_range("2023-01", periods=36, freq="M")
    serie = pd.Series(valores, index=periodos, name="TEST_SERIE")

    resultado = entrenar_y_proyectar_hw(serie, caso_uso="TEST_SERIE", horizonte=6)

    assert resultado["caso_uso"] == "TEST_SERIE"
    assert resultado["metodo"] == "HoltWinters"
    assert resultado["horizonte_meses"] == 6
    assert len(resultado["forecast"]) == 6
    assert len(resultado["ic_lower"]) == 6
    assert len(resultado["ic_upper"]) == 6
    assert resultado["periodos"] == ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]

    # Monotonía de bandas de confianza y no negatividad
    for f, l, u in zip(resultado["forecast"], resultado["ic_lower"], resultado["ic_upper"]):
        assert f >= 0, "El pronóstico no puede ser negativo"
        assert l >= 0, "La cota inferior no puede ser negativa"
        assert l <= f <= u, "La cota inferior debe ser menor o igual al forecast y este menor a la superior"

    assert resultado["rmse"] > 0
    assert "alpha" in resultado["parametros"]


def test_holtwinters_limite_horizonte():
    """Valida que un horizonte mayor a 6 meses dispare ValueError."""
    periodos = pd.period_range("2023-01", periods=30, freq="M")
    serie = pd.Series(np.ones(30) * 100, index=periodos)

    with pytest.raises(ValueError, match="comprendido entre 1 y 6"):
        entrenar_y_proyectar_hw(serie, caso_uso="TEST_HORIZONTE", horizonte=7)

    with pytest.raises(ValueError, match="comprendido entre 1 y 6"):
        entrenar_y_proyectar_hw(serie, caso_uso="TEST_HORIZONTE", horizonte=0)


def test_holtwinters_muestra_insuficiente():
    """Valida que una serie con N < 24 dispare ValueError."""
    periodos = pd.period_range("2023-01", periods=18, freq="M")
    serie = pd.Series(np.ones(18) * 100, index=periodos)

    with pytest.raises(ValueError, match="Se requieren al menos 24 periodos"):
        entrenar_y_proyectar_hw(serie, caso_uso="TEST_CORTO", horizonte=3)


# ─────────────────────────────────────────────────────────────────────────────
# 2. PRUEBAS DEL MOTOR OLS METAS ANUALES (GIRA-55)
# ─────────────────────────────────────────────────────────────────────────────

def test_ols_anual_proyeccion_exitosa():
    """Valida estimación OLS de tendencia indicativa para N=3."""
    serie_anual = pd.Series([8000000.0, 9500000.0, 11200000.0], index=[2023, 2024, 2025])
    resultado = estimar_tendencia_anual_ols(serie_anual, horizonte_anios=2)

    assert resultado["metodo"] == "OLS"
    assert resultado["horizonte_anios"] == 2
    assert resultado["periodos"] == ["2026", "2027"]
    assert len(resultado["forecast"]) == 2
    assert resultado["forecast"][0] > serie_anual.iloc[-1], "La tendencia creciente debe proyectar mayor ingreso"
    assert resultado["pendiente_anual_bs"] > 0
    assert resultado["cagr_historico_pct"] > 0

    # Rigor estadístico: no reportar IC formal con N=3
    assert resultado["ic_lower"] is None
    assert resultado["ic_upper"] is None
    assert "nota_metodologica" in resultado


def test_ols_anual_muestra_insuficiente():
    """Valida que N < 3 dispare ValueError en OLS."""
    serie_corta = pd.Series([10000.0, 20000.0], index=[2023, 2024])
    with pytest.raises(ValueError, match="al menos 3 años"):
        estimar_tendencia_anual_ols(serie_corta)


# ─────────────────────────────────────────────────────────────────────────────
# 3. PRUEBAS DE RESOLUCIÓN TEMPORAL Y EXTRACTOR (GIRA-53, GIRA-56)
# ─────────────────────────────────────────────────────────────────────────────

def test_resolver_id_tiempo():
    """Valida mapeo de periodos a claves YYYYMMDD de dim_tiempo."""
    assert _resolver_id_tiempo("2026-06") == 20260601
    assert _resolver_id_tiempo("2024-12") == 20241201
    assert _resolver_id_tiempo("2026") == 20260101
    with pytest.raises(ValueError):
        _resolver_id_tiempo("invalido")


def test_extractor_series_reales():
    """Valida que el extractor obtenga series consistentes desde las fuentes de datos."""
    serie_global = extraer_serie_temporal("ALUMNOS_GLOBAL")
    assert len(serie_global) >= 24, "La serie global de inscritos debe tener al menos 24 meses"
    assert serie_global.sum() > 5000, "El volumen acumulado de inscritos debe ser sustancial"

    serie_diplomado = extraer_serie_temporal("ALUMNOS_DIPLOMADO")
    assert len(serie_diplomado) >= 24

    serie_metas = extraer_serie_temporal("META_MENSUAL_PROGRAMAS")
    assert len(serie_metas) >= 24

    serie_anual = extraer_serie_temporal("META_ANUAL")
    assert len(serie_anual) == 3
    assert list(serie_anual.index) == [2023, 2024, 2025]


# ─────────────────────────────────────────────────────────────────────────────
# 4. PRUEBAS DE INTEGRACIÓN API REST (GIRA-57)
# ─────────────────────────────────────────────────────────────────────────────

client = TestClient(app)


def test_api_forecast_alumnos():
    """Valida endpoint GET /api/v1/forecast/alumnos."""
    response = client.get("/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=4")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    data = json_data["data"]
    assert data["caso_uso"] == "ALUMNOS_GLOBAL"
    assert data["metodo"] == "HoltWinters"
    assert len(data["proyecciones"]) == 4
    for p in data["proyecciones"]:
        assert "periodo" in p
        assert "valor_forecast" in p
        assert p["valor_forecast"] >= 0


def test_api_forecast_metas_mensual():
    """Valida endpoint GET /api/v1/forecast/metas para granularidad mensual."""
    response = client.get("/api/v1/forecast/metas?granularidad=MENSUAL&horizonte=3")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    data = json_data["data"]
    assert data["granularidad"] == "MENSUAL"
    assert data["metodo"] == "HoltWinters"
    assert len(data["proyecciones"]) == 3


def test_api_forecast_metas_anual():
    """Valida endpoint GET /api/v1/forecast/metas para granularidad anual (OLS N=3)."""
    response = client.get("/api/v1/forecast/metas?granularidad=ANUAL&horizonte=2")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    data = json_data["data"]
    assert data["granularidad"] == "ANUAL"
    assert data["metodo"] == "OLS"
    assert len(data["proyecciones"]) == 2
    assert "pendiente_anual_bs" in data
    assert "nota_metodologica" in data
