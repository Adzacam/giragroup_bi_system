"""
pipeline/analytics/forecasting_holtwinters.py
---------------------------------------------
GIRA-54: Motor predictivo Holt-Winters amortiguado (tendencia damped + estacionalidad anual aditiva).
Diseñado para series mensuales (N >= 24) con horizonte acotado a h <= 6 meses.
Aplica a:
- ALUMNOS_GLOBAL
- ALUMNOS_DIPLOMADO
- ALUMNOS_CURSO
- ALUMNOS_EXPERTO
- META_MENSUAL_PROGRAMAS
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger("forecasting_holtwinters")

# Intento de importar statsmodels; si no está disponible, se utiliza el motor nativo NumPy
try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    logger.warning("statsmodels no está disponible. Se utilizará el motor nativo de Holt-Winters (NumPy).")


PHI_CANDIDATOS = (0.80, 0.85, 0.90, 0.95, 0.98, 0.99)


def _hw_amortiguado_fijo(y: np.ndarray, m: int, h: int, alpha: float, beta: float, gamma: float, phi: float):
    """Holt-Winters con tendencia aditiva amortiguada (phi) y estacionalidad aditiva, parámetros fijos."""
    n = len(y)
    l = np.zeros(n)
    b = np.zeros(n)
    s = np.zeros(n + m)
    fitted = np.zeros(n)

    l[m - 1] = np.mean(y[:m])
    b[m - 1] = np.mean((y[m:2 * m] - y[:m]) / m)
    s_init = y[:m] - l[m - 1]
    s_init -= np.mean(s_init)
    s[:m] = s_init

    for t in range(m, n):
        s_idx = t - m
        fitted[t] = l[t - 1] + phi * b[t - 1] + s[s_idx]
        l[t] = alpha * (y[t] - s[s_idx]) + (1.0 - alpha) * (l[t - 1] + phi * b[t - 1])
        b[t] = beta * (l[t] - l[t - 1]) + (1.0 - beta) * phi * b[t - 1]
        s[t] = gamma * (y[t] - l[t]) + (1.0 - gamma) * s[s_idx]

    forecast = np.zeros(h)
    for i in range(1, h + 1):
        # Tendencia acumulada amortiguada: phi + phi^2 + ... + phi^i (se aplana, no crece sin límite)
        tendencia = b[-1] * sum(phi ** k for k in range(1, i + 1))
        forecast[i - 1] = l[-1] + tendencia + s[n - m + ((i - 1) % m)]

    residuos = y[m:] - fitted[m:]
    rmse = float(np.sqrt(np.mean(residuos ** 2)))
    return forecast, fitted[m:], rmse


def _holt_winters_nativo(
    y: np.ndarray,
    m: int = 12,
    h: int = 6,
    alpha: float = 0.2,
    beta: float = 0.1,
    gamma: float = 0.2
) -> tuple[np.ndarray, np.ndarray, float, dict]:
    """
    Motor Holt-Winters amortiguado en NumPy (respaldo cuando statsmodels no está instalado).
    El factor de amortiguación phi se elige entre PHI_CANDIDATOS por menor RMSE en la muestra.
    Retorna: (forecast, fitted_values, rmse, params)
    """
    mejor = None
    for phi in PHI_CANDIDATOS:
        forecast, fitted, rmse = _hw_amortiguado_fijo(y, m, h, alpha, beta, gamma, phi)
        if mejor is None or rmse < mejor[2]:
            mejor = (forecast, fitted, rmse, phi)
    forecast, fitted, rmse, phi = mejor
    return forecast, fitted, rmse, {"alpha": alpha, "beta": beta, "gamma": gamma, "phi": phi}


def entrenar_y_proyectar_hw(
    serie: pd.Series,
    caso_uso: str,
    horizonte: int = 6,
    seasonal_periods: int = 12
) -> Dict[str, Any]:
    """
    Ajusta un modelo Holt-Winters con tendencia amortiguada (damped) y estacionalidad aditiva de 12 meses
    y proyecta hasta `horizonte` meses futuros (máximo 6 meses).
    """
    if horizonte < 1 or horizonte > 6:
        raise ValueError(f"El horizonte ({horizonte}) debe estar comprendido entre 1 y 6 meses.")

    n_obs = len(serie.dropna())
    if n_obs < 24:
        raise ValueError(
            f"La serie '{caso_uso}' tiene {n_obs} observaciones. "
            f"Se requieren al menos 24 periodos (2 ciclos estacionales completos) para Holt-Winters."
        )

    # Asegurar índice datetime regular
    serie_clean = serie.dropna().astype(float)
    if isinstance(serie_clean.index, pd.PeriodIndex):
        ts_index = serie_clean.index.to_timestamp(how="start")
    else:
        ts_index = pd.to_datetime(serie_clean.index)

    serie_ts = pd.Series(serie_clean.values, index=ts_index).asfreq("MS").fillna(0.0)

    aic_val = None
    if HAS_STATSMODELS:
        try:
            modelo = ExponentialSmoothing(
                serie_ts,
                trend="add",
                damped_trend=True,  # amortiguado: menor MAPE en origen movil (docs/evidencias/holtwinters_origen_movil.json)
                seasonal="add",
                seasonal_periods=seasonal_periods,
                initialization_method="estimated"
            ).fit(optimized=True)

            raw_forecast = modelo.forecast(horizonte).values
            residuos = serie_ts.values - modelo.fittedvalues.values
            rmse = float(np.sqrt(np.mean(residuos ** 2)))
            aic_val = float(round(modelo.aic, 2)) if hasattr(modelo, "aic") and not np.isnan(modelo.aic) else None
            parametros = {
                "alpha": float(round(modelo.params.get("smoothing_level", 0.0), 4)),
                "beta": float(round(modelo.params.get("smoothing_trend", 0.0), 4)),
                "gamma": float(round(modelo.params.get("smoothing_seasonal", 0.0), 4)),
                "phi": float(round(modelo.params.get("damping_trend", 1.0), 4)),
            }
        except Exception as ex:
            logger.warning(f"Falla en statsmodels ExponentialSmoothing ({ex}). Usando motor nativo...")
            raw_forecast, _, rmse, parametros = _holt_winters_nativo(serie_ts.values, m=seasonal_periods, h=horizonte)
    else:
        raw_forecast, _, rmse, parametros = _holt_winters_nativo(serie_ts.values, m=seasonal_periods, h=horizonte)

    # Banda de confianza empírica 95% (+- 1.96 * RMSE), acotada a >= 0
    forecast_vals = [max(0.0, float(round(v, 2))) for v in raw_forecast]
    ic_lower_vals = [max(0.0, float(round(v - 1.96 * rmse, 2))) for v in raw_forecast]
    ic_upper_vals = [float(round(v + 1.96 * rmse, 2)) for v in raw_forecast]

    # Periodos proyectados en formato 'YYYY-MM'
    last_period = serie_clean.index[-1]
    if isinstance(last_period, pd.Period):
        futuros = [str(last_period + i) for i in range(1, horizonte + 1)]
    else:
        last_dt = pd.to_datetime(last_period)
        futuros = [(last_dt + pd.DateOffset(months=i)).strftime("%Y-%m") for i in range(1, horizonte + 1)]

    resultado = {
        "caso_uso": caso_uso.upper(),
        "metodo": "HoltWinters",
        "horizonte_meses": horizonte,
        "n_observaciones": n_obs,
        "periodos": futuros,
        "forecast": forecast_vals,
        "ic_lower": ic_lower_vals,
        "ic_upper": ic_upper_vals,
        "rmse": round(rmse, 2),
        "aic": aic_val,
        "parametros": parametros
    }
    
    logger.info(
        f"Ajuste HW exitoso para '{caso_uso}': h={horizonte}, RMSE={resultado['rmse']}, "
        f"Proyección={forecast_vals[:3]}..."
    )
    return resultado


def calcular_mape_holdout(serie: pd.Series, h: int = 6, seasonal_periods: int = 12) -> Optional[float]:
    """MAPE (%) de validación hold-out: entrena con serie[:-h], proyecta h meses y compara
    contra los h últimos reales. Calculado, no fijo. None si no hay observaciones suficientes
    (se exigen 2 ciclos estacionales completos en el tramo de entrenamiento)."""
    s = serie.dropna().astype(float)
    if len(s) - h < 2 * seasonal_periods:
        return None
    train, test = s.iloc[:-h], s.iloc[-h:]
    idx = train.index.to_timestamp(how="start") if isinstance(train.index, pd.PeriodIndex) else pd.to_datetime(train.index)
    tr = pd.Series(train.values, index=idx).asfreq("MS").fillna(0.0)
    try:
        if HAS_STATSMODELS:
            m = ExponentialSmoothing(tr, trend="add", damped_trend=True, seasonal="add",
                                     seasonal_periods=seasonal_periods,
                                     initialization_method="estimated").fit(optimized=True)
            pred = m.forecast(h).values
        else:
            pred = _holt_winters_nativo(tr.values, m=seasonal_periods, h=h)[0]
    except Exception:
        return None
    y = test.values
    return float(round(np.mean(np.abs((y - pred) / np.maximum(y, 1.0))) * 100.0, 2))
