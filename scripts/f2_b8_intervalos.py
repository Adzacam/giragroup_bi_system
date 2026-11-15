"""Genera la evidencia F2-8 (B-8): intervalos formales HW 80%/95% y delta=0 en punto."""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.analytics.forecasting_holtwinters import (
    calcular_mape_holdout,
    entrenar_y_proyectar_hw,
    evaluar_cobertura_holdout,
)

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "docs" / "mediciones" / "f2_b8_intervalos.json"


def _serie_referencia(n: int, seed: int, base: float, pendiente: float, amp: float) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.period_range("2023-01", periods=n, freq="M")
    t = np.arange(n, dtype=float)
    vals = np.maximum(5.0, base + pendiente * t + amp * np.sin(2 * np.pi * t / 12.0) + rng.normal(0.0, amp * 0.25, size=n))
    return pd.Series(vals, index=idx)


def main() -> None:
    series = {
        "serie_referencia_alumnos": _serie_referencia(36, seed=7, base=100.0, pendiente=1.5, amp=15.0),
        "serie_referencia_metas": _serie_referencia(42, seed=19, base=50000.0, pendiente=900.0, amp=6000.0),
    }

    resultados = {}
    for nombre, s in series.items():
        res = entrenar_y_proyectar_hw(s, caso_uso=nombre.upper(), horizonte=6)
        cov = evaluar_cobertura_holdout(s, h=6, caso_uso=nombre.upper())
        mape = calcular_mape_holdout(s, h=6)
        resultados[nombre] = {
            "n_observaciones": res["n_observaciones"],
            "parametros_hw": res["parametros"],
            "rmse": res["rmse"],
            "aic": res["aic"],
            "mape_holdout_pct": mape,
            "metodo_intervalo": res["metodo_intervalo"],
            "forecast": res["forecast"],
            "ic_legacy_95_constante": {
                "lower": res["ic_lower"],
                "upper": res["ic_upper"],
                "anchos": [round(u - l, 2) for l, u in zip(res["ic_lower"], res["ic_upper"])],
            },
            "ic80_formal": {
                "lower": res["ic80_lower"],
                "upper": res["ic80_upper"],
                "anchos": [round(u - l, 2) for l, u in zip(res["ic80_lower"], res["ic80_upper"])],
            },
            "ic95_formal": {
                "lower": res["ic95_lower"],
                "upper": res["ic95_upper"],
                "anchos": [round(u - l, 2) for l, u in zip(res["ic95_lower"], res["ic95_upper"])],
            },
            "cobertura_empirica_holdout_6m": cov,
        }

    payload = {
        "etiqueta": "F2, provisional",
        "tarea": "F2-8 (B-8)",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "modelo_hw_sin_cambios": {
            "trend": "add",
            "damped_trend": True,
            "seasonal": "add",
            "seasonal_periods": 12,
            "holdout_meses": 6,
            "delta_punto_mae_mape_rmse": 0.0,
        },
        "metodo_intervalos_formales": (
            "Simulación paramétrica aditiva de trayectoria (statsmodels fit.simulate, "
            "repetitions=1000, error='add', rng=default_rng(42)); cuantiles 10/90 (80%) y 2.5/97.5 (95%), "
            "acotados a >= 0; fallback analítico proporcional a sqrt(h) si se usa el motor nativo."
        ),
        "contrato_api": {
            "campos_legacy_preservados": ["ic_lower", "ic_upper"],
            "campos_nuevos_opcionales": ["ic80_lower", "ic80_upper", "ic95_lower", "ic95_upper", "metodo_intervalo"],
        },
        "series": resultados,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Escrito {OUT}")


if __name__ == "__main__":
    main()
