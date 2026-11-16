"""R3-6: Script versionado para Holt-Winters de matrícula (ALUMNOS_GLOBAL, E-03..E-14) e intervalos 80/95% B-8 sobre el snapshot."""

import json
import os
from pathlib import Path

from sqlalchemy import create_engine

from pipeline.analytics.forecasting_holtwinters import (
    calcular_mape_holdout,
    entrenar_y_proyectar_hw,
    evaluar_cobertura_holdout,
)
from pipeline.analytics.time_series_extractor import extraer_serie_temporal

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "mediciones" / "f3r_hw_matricula.json"


def main() -> None:
    db_url = os.environ["DATABASE_URL"]
    engine = create_engine(db_url)
    serie = extraer_serie_temporal("ALUMNOS_GLOBAL", engine=engine)
    res = entrenar_y_proyectar_hw(serie, caso_uso="ALUMNOS_GLOBAL", horizonte=6, seasonal_periods=12)
    mape_holdout = calcular_mape_holdout(serie, h=6, seasonal_periods=12)
    cov_holdout = evaluar_cobertura_holdout(serie, h=6, seasonal_periods=12, caso_uso="ALUMNOS_GLOBAL")

    payload = {
        "etiqueta": "F3R, final (snapshot 10-nov)",
        "tarea": "R3-6 (HW Matrícula E-03..E-14 + B-8)",
        "caso_uso": "ALUMNOS_GLOBAL",
        "n_observaciones": res["n_observaciones"],
        "serie_observada": {str(k): float(v) for k, v in serie.items()},
        "parametros_hw": res["parametros"],
        "rmse": res["rmse"],
        "aic": res["aic"],
        "mape_holdout_6m_pct": mape_holdout,
        "metodo_intervalo": res["metodo_intervalo"],
        "periodos_proyectados": res["periodos"],
        "forecast": res["forecast"],
        "ic_legacy_95": {"lower": res["ic_lower"], "upper": res["ic_upper"]},
        "ic80_formal": {"lower": res["ic80_lower"], "upper": res["ic80_upper"]},
        "ic95_formal": {"lower": res["ic95_lower"], "upper": res["ic95_upper"]},
        "cobertura_empirica_holdout_6m": cov_holdout,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Escrito {OUT} (n_obs={len(serie)}, rmse={res['rmse']}, aic={res['aic']}, mape={mape_holdout})")


if __name__ == "__main__":
    main()
