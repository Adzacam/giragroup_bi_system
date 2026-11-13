"""Cobertura de forecasting_holtwinters: motor nativo NumPy, respaldo ante fallo de statsmodels, ausencia de statsmodels, tipos de indice y validaciones."""
import numpy as np
import pandas as pd
import pytest

from pipeline.analytics import forecasting_holtwinters as hw


def _serie(n=36, periodo=False):
    t = np.arange(n)
    y = 100 + 2.0 * t + 10 * np.sin(2 * np.pi * t / 12)
    idx = pd.period_range("2023-01", periods=n, freq="M") if periodo else pd.date_range("2023-01-01", periods=n, freq="MS")
    return pd.Series(y, index=idx)


def test_motor_nativo_devuelve_pronostico_ajuste_y_rmse():
    y = _serie(36).values
    fc, fitted, rmse, params = hw._holt_winters_nativo(y, m=12, h=6)
    assert len(fc) == 6 and len(fitted) == 36 - 12
    assert rmse >= 0 and set(params) == {"alpha", "beta", "gamma", "phi"}
    # serie con tendencia positiva: el pronostico queda cerca del nivel final
    assert fc.mean() > y[:12].mean()


def test_motor_nativo_horizonte_mayor_que_el_periodo_reutiliza_estacionalidad():
    fc, *_ = hw._holt_winters_nativo(_serie(36).values, m=12, h=14)
    assert len(fc) == 14


def test_proyeccion_con_indice_de_periodos_y_formato_yyyy_mm():
    r = hw.entrenar_y_proyectar_hw(_serie(30, periodo=True), "alumnos_global", horizonte=3)
    assert r["caso_uso"] == "ALUMNOS_GLOBAL" and r["metodo"] == "HoltWinters"
    assert r["periodos"] == ["2025-07", "2025-08", "2025-09"]
    assert len(r["forecast"]) == len(r["ic_lower"]) == len(r["ic_upper"]) == 3
    assert all(lo <= f <= up for lo, f, up in zip(r["ic_lower"], r["forecast"], r["ic_upper"]))


def test_proyeccion_con_indice_datetime_y_huecos_rellenados_con_cero():
    s = _serie(30)
    s = s.drop(s.index[10])  # un mes ausente: asfreq("MS") lo rellena
    r = hw.entrenar_y_proyectar_hw(s, "x", horizonte=2)
    assert r["periodos"] == ["2025-07", "2025-08"]
    assert r["n_observaciones"] == 29


def test_valores_negativos_del_pronostico_se_acotan_a_cero():
    n = 30
    y = np.linspace(60, 0, n)
    r = hw.entrenar_y_proyectar_hw(pd.Series(y, index=pd.date_range("2023-01-01", periods=n, freq="MS")), "baja", horizonte=6)
    assert min(r["forecast"]) >= 0 and min(r["ic_lower"]) >= 0


def test_sin_statsmodels_usa_el_motor_nativo(monkeypatch):
    monkeypatch.setattr(hw, "HAS_STATSMODELS", False)
    r = hw.entrenar_y_proyectar_hw(_serie(30), "sin_sm", horizonte=4)
    assert r["aic"] is None
    assert {k: r["parametros"][k] for k in ("alpha", "beta", "gamma")} == {"alpha": 0.2, "beta": 0.1, "gamma": 0.2}
    assert r["parametros"]["phi"] in hw.PHI_CANDIDATOS
    assert len(r["forecast"]) == 4


def test_si_statsmodels_falla_se_recurre_al_motor_nativo(monkeypatch):
    class Roto:
        def __init__(self, *a, **k):
            raise RuntimeError("fallo simulado de statsmodels")

    monkeypatch.setattr(hw, "HAS_STATSMODELS", True)
    monkeypatch.setattr(hw, "ExponentialSmoothing", Roto, raising=False)
    r = hw.entrenar_y_proyectar_hw(_serie(30), "respaldo", horizonte=2)
    assert r["aic"] is None and len(r["forecast"]) == 2


@pytest.mark.parametrize("h", [0, 7, -1])
def test_horizonte_fuera_de_rango(h):
    with pytest.raises(ValueError, match="horizonte"):
        hw.entrenar_y_proyectar_hw(_serie(30), "x", horizonte=h)


def test_serie_corta_se_rechaza_y_los_nulos_no_cuentan():
    s = _serie(30)
    s.iloc[:10] = np.nan  # quedan 20 observaciones validas
    with pytest.raises(ValueError, match="al menos 24"):
        hw.entrenar_y_proyectar_hw(s, "corta")


def test_motor_nativo_amortigua_la_tendencia():
    """Con tendencia creciente, phi < 1 proyecta menos que la tendencia sin amortiguar (phi = 1)."""
    t = np.arange(36)
    y = 100 + 5.0 * t + 6 * np.sin(2 * np.pi * t / 12)
    amortiguado, _, _ = hw._hw_amortiguado_fijo(y, 12, 6, 0.2, 0.1, 0.2, phi=0.8)
    sin_amortiguar, _, _ = hw._hw_amortiguado_fijo(y, 12, 6, 0.2, 0.1, 0.2, phi=1.0)
    assert amortiguado[-1] < sin_amortiguar[-1]
    assert (sin_amortiguar - amortiguado)[-1] > (sin_amortiguar - amortiguado)[0]


def test_phi_se_elige_entre_los_candidatos():
    fc, _, _, params = hw._holt_winters_nativo(_serie(36).values, m=12, h=3)
    assert params["phi"] in hw.PHI_CANDIDATOS


def test_mape_holdout_se_calcula_sin_statsmodels(monkeypatch):
    monkeypatch.setattr(hw, "HAS_STATSMODELS", False)
    mape = hw.calcular_mape_holdout(_serie(36, periodo=True), h=6)
    assert mape is not None and mape >= 0.0
