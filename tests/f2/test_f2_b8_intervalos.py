"""Pruebas F2 B-8: intervalos formales 80% y 95% de Holt-Winters sin alterar el punto."""

import numpy as np
import pandas as pd
import pytest

from backend.schemas.forecast_schemas import ForecastAlumnosData, ForecastMetasData
from pipeline.analytics.forecasting_holtwinters import (
    calcular_mape_holdout,
    entrenar_y_proyectar_hw,
    evaluar_cobertura_holdout,
)


def _serie_sintetica(n: int = 36, seed: int = 7) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.period_range("2023-01", periods=n, freq="M")
    t = np.arange(n, dtype=float)
    estacional = 15.0 * np.sin(2 * np.pi * t / 12.0)
    valores = np.maximum(10.0, 100.0 + 1.5 * t + estacional + rng.normal(0.0, 5.0, size=n))
    return pd.Series(valores, index=idx)


def test_b8_intervalos_crecen_y_son_ordenados():
    serie = _serie_sintetica(36)
    res = entrenar_y_proyectar_hw(serie, caso_uso="ALUMNOS_GLOBAL", horizonte=6)
    assert res["metodo_intervalo"] == "simulacion_param_aditivo_n1000"
    assert len(res["ic80_lower"]) == 6
    assert len(res["ic95_lower"]) == 6

    for i in range(6):
        assert res["ic95_lower"][i] <= res["ic80_lower"][i] <= res["forecast"][i]
        assert res["forecast"][i] <= res["ic80_upper"][i] <= res["ic95_upper"][i]

    anchos_95 = [u - l for l, u in zip(res["ic95_lower"], res["ic95_upper"])]
    assert anchos_95[-1] > anchos_95[0]


def test_b8_delta_cero_punto_y_legacy_ic():
    serie = _serie_sintetica(36)
    res = entrenar_y_proyectar_hw(serie, caso_uso="ALUMNOS_GLOBAL", horizonte=6)
    for f, lo, hi in zip(res["forecast"], res["ic_lower"], res["ic_upper"]):
        assert lo == pytest.approx(max(0.0, round(f - 1.96 * res["rmse"], 2)), abs=0.02)
        assert hi == pytest.approx(round(f + 1.96 * res["rmse"], 2), abs=0.02)
    mape = calcular_mape_holdout(serie, h=6)
    assert mape is not None and mape >= 0.0


def test_b8_cobertura_holdout_y_schemas():
    serie = _serie_sintetica(42)
    cov = evaluar_cobertura_holdout(serie, h=6, caso_uso="TEST_COV")
    assert cov is not None
    assert 0.0 <= cov["cobertura_80"] <= 1.0
    assert 0.0 <= cov["cobertura_95"] <= 1.0

    res = entrenar_y_proyectar_hw(serie, caso_uso="ALUMNOS_GLOBAL", horizonte=6)
    alumnos = ForecastAlumnosData(
        caso_uso="ALUMNOS_GLOBAL",
        tipo_solicitado="GLOBAL",
        metodo=res["metodo"],
        metodo_intervalo=res["metodo_intervalo"],
        origen="on_demand_computation",
        horizonte_meses=6,
        rmse=res["rmse"],
        aic=res["aic"],
        proyecciones=[
            {
                "periodo": p,
                "valor_forecast": f,
                "ic_lower": l,
                "ic_upper": u,
                "ic80_lower": l80,
                "ic80_upper": u80,
                "ic95_lower": l95,
                "ic95_upper": u95,
            }
            for p, f, l, u, l80, u80, l95, u95 in zip(
                res["periodos"], res["forecast"], res["ic_lower"], res["ic_upper"],
                res["ic80_lower"], res["ic80_upper"], res["ic95_lower"], res["ic95_upper"],
            )
        ],
    )
    assert len(alumnos.proyecciones) == 6

    metas = ForecastMetasData(
        caso_uso="META_MENSUAL_PROGRAMAS",
        granularidad="MENSUAL",
        metodo=res["metodo"],
        metodo_intervalo=res["metodo_intervalo"],
        horizonte_meses=6,
        rmse=res["rmse"],
        aic=res["aic"],
        proyecciones=[
            {
                "periodo": p,
                "monto_proyectado_bs": f,
                "ic_lower": l,
                "ic_upper": u,
                "ic80_lower": l80,
                "ic80_upper": u80,
                "ic95_lower": l95,
                "ic95_upper": u95,
            }
            for p, f, l, u, l80, u80, l95, u95 in zip(
                res["periodos"], res["forecast"], res["ic_lower"], res["ic_upper"],
                res["ic80_lower"], res["ic80_upper"], res["ic95_lower"], res["ic95_upper"],
            )
        ],
    )
    assert metas.metodo_intervalo == res["metodo_intervalo"]
