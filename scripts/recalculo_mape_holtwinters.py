"""Recalcula el hold-out del Holt-Winters amortiguado de inscritos mensuales sobre una base indicada.

Uso (desde la raíz del repositorio, con las variables DB_USER y DB_PASSWORD definidas):
    python -m scripts.recalculo_mape_holtwinters snapshot_dw_20261110_1201 [puerto] [salida.json]

Ventana: entrenamiento hasta el mes anterior a los últimos 6 meses de la serie, hold-out de 6 meses.
Guarda MAPE, RMSE, AIC, parámetros, los pares real/pronóstico, las comparaciones con dos pronósticos ingenuos y las
versiones de las bibliotecas, porque el optimizador puede variar unas centésimas entre entornos.
"""
import json
import os
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import statsmodels
from sqlalchemy import create_engine
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# `services` del backend debe resolverse antes que la carpeta de microservicios de la raíz
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))

from pipeline.analytics.time_series_extractor import extraer_serie_temporal
from services.forecast_service import _recortar_serie_alumnos

HOLDOUT = 6


def _mape(real, pron):
    return float(np.mean(np.abs((real - pron) / np.maximum(real, 1.0))) * 100.0)


def recalcular(base: str, puerto: str = "5434", host: str = "localhost") -> dict:
    url = f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{host}:{puerto}/{base}"
    serie = _recortar_serie_alumnos(extraer_serie_temporal("ALUMNOS_GLOBAL", engine=create_engine(url)))
    entrenamiento, prueba = serie.iloc[:-HOLDOUT], serie.iloc[-HOLDOUT:]
    idx = entrenamiento.index.to_timestamp(how="start")
    tr = pd.Series(entrenamiento.values.astype(float), index=idx).asfreq("MS").fillna(0.0)
    modelo = ExponentialSmoothing(tr, trend="add", damped_trend=True, seasonal="add", seasonal_periods=12,
                                  initialization_method="estimated").fit(optimized=True)
    pron = modelo.forecast(HOLDOUT).values
    real = prueba.values.astype(float)
    ingenuo_ultimo = np.full(HOLDOUT, tr.values[-1])
    ingenuo_estacional = tr.values[-12:][:HOLDOUT]
    return {
        "base": base,
        "serie": {"meses": len(serie), "desde": str(serie.index[0]), "hasta": str(serie.index[-1]), "suma": int(serie.sum())},
        "entrenamiento": {"meses": len(entrenamiento), "desde": str(entrenamiento.index[0]), "hasta": str(entrenamiento.index[-1])},
        "holdout": {"desde": str(prueba.index[0]), "hasta": str(prueba.index[-1])},
        "mape_pct": round(_mape(real, pron), 2),
        "rmse": round(float(np.sqrt(np.mean((real - pron) ** 2))), 2),
        "aic": round(float(modelo.aic), 2),
        "parametros": {k: round(float(v), 4) for k, v in modelo.params.items()
                       if k in ("smoothing_level", "smoothing_trend", "smoothing_seasonal", "damping_trend")},
        "pares_real_pronostico": [[int(r), round(float(p), 1)] for r, p in zip(real, pron)],
        "ingenuo_ultimo_valor_mape_pct": round(_mape(real, ingenuo_ultimo), 2),
        "ingenuo_estacional_mape_pct": round(_mape(real, ingenuo_estacional), 2),
        "entorno": {"python": platform.python_version(), "statsmodels": statsmodels.__version__, "scipy": scipy.__version__,
                    "numpy": np.__version__, "pandas": pd.__version__},
    }


if __name__ == "__main__":
    resultado = recalcular(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "5434")
    texto = json.dumps(resultado, ensure_ascii=False, indent=2)
    if len(sys.argv) > 3:
        with open(sys.argv[3], "w", encoding="utf-8") as f:
            f.write(texto + "\n")
    print(texto)
