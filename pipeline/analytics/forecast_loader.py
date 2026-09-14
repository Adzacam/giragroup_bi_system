"""
pipeline/analytics/forecast_loader.py
-------------------------------------
GIRA-56: Cargador y persistencia de pronósticos en fact_forecast.
Inserta o actualiza (UPSERT ON CONFLICT) los resultados generados por
los motores Holt-Winters (GIRA-54) y OLS (GIRA-55) en PostgreSQL.
"""

import sys
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from sqlalchemy import text, Engine

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipeline.analytics.time_series_extractor import extraer_serie_temporal
from pipeline.analytics.forecasting_holtwinters import entrenar_y_proyectar_hw
from pipeline.analytics.forecasting_ols import estimar_tendencia_anual_ols

logger = logging.getLogger("forecast_loader")


def _resolver_id_tiempo(periodo_str: str) -> int:
    """
    Convierte 'YYYY-MM' en YYYYMM01 o 'YYYY' en YYYY0101 para coincidir con dim_tiempo.
    """
    clean = str(periodo_str).strip()
    if "-" in clean:
        partes = clean.split("-")
        anio = int(partes[0])
        mes = int(partes[1])
        return anio * 10000 + mes * 100 + 1
    elif len(clean) == 4 and clean.isdigit():
        return int(clean) * 10000 + 101
    raise ValueError(f"Formato de periodo no reconocido para id_tiempo: {periodo_str}")


def persistir_resultado_forecast(resultado: Dict[str, Any], engine: Engine) -> int:
    """
    Persiste un resultado de pronóstico (Holt-Winters u OLS) en public.fact_forecast.
    Retorna la cantidad de registros insertados o actualizados.
    """
    caso_uso = resultado["caso_uso"]
    metodo = resultado["metodo"]
    periodos = resultado["periodos"]
    forecast = resultado["forecast"]
    ic_lower = resultado.get("ic_lower") or [None] * len(forecast)
    ic_upper = resultado.get("ic_upper") or [None] * len(forecast)
    horizonte = resultado.get("horizonte_meses", resultado.get("horizonte_anios", len(forecast)))

    insertados = 0
    query = text("""
        INSERT INTO public.fact_forecast (
            caso_uso, id_tiempo, valor_forecast, ic_lower, ic_upper, metodo, horizonte_meses, generado_en
        ) VALUES (
            :caso, :id_t, :valor, :lower, :upper, :metodo, :horizonte, CURRENT_TIMESTAMP
        )
        ON CONFLICT (caso_uso, id_tiempo)
        DO UPDATE SET
            valor_forecast = EXCLUDED.valor_forecast,
            ic_lower = EXCLUDED.ic_lower,
            ic_upper = EXCLUDED.ic_upper,
            metodo = EXCLUDED.metodo,
            horizonte_meses = EXCLUDED.horizonte_meses,
            generado_en = CURRENT_TIMESTAMP;
    """)

    with engine.begin() as conn:
        for p, f_val, l_val, u_val in zip(periodos, forecast, ic_lower, ic_upper):
            id_t = _resolver_id_tiempo(p)
            conn.execute(
                query,
                {
                    "caso": caso_uso,
                    "id_t": id_t,
                    "valor": float(f_val),
                    "lower": float(l_val) if l_val is not None else None,
                    "upper": float(u_val) if u_val is not None else None,
                    "metodo": metodo,
                    "horizonte": int(horizonte)
                }
            )
            insertados += 1

    logger.info(f"Persistidos {insertados} registros en fact_forecast para caso '{caso_uso}'.")
    return insertados


def ejecutar_pipeline_forecasting_completo(engine: Optional[Engine] = None) -> Dict[str, Any]:
    """
    Orquesta la ejecución integral de los 4 casos de uso viables:
    1. Alumnos global (HW)
    2. Alumnos por tipo: Diplomado, Curso, Experto (HW x3)
    3. Metas mensuales por categoría (HW)
    4. Metas financieras anuales (OLS N=3)
    Persiste en PostgreSQL si se provee engine.
    """
    logger.info("Iniciando ejecución completa del módulo de forecasting...")
    resultados = {}

    # 1. Casos mensuales con Holt-Winters
    casos_hw = [
        "ALUMNOS_GLOBAL",
        "ALUMNOS_DIPLOMADO",
        "ALUMNOS_CURSO",
        "ALUMNOS_EXPERTO",
        "META_MENSUAL_PROGRAMAS"
    ]

    for c in casos_hw:
        try:
            serie = extraer_serie_temporal(c, engine=engine)
            res = entrenar_y_proyectar_hw(serie, caso_uso=c, horizonte=6)
            resultados[c] = res
            if engine is not None:
                persistir_resultado_forecast(res, engine)
        except Exception as e:
            logger.error(f"Error procesando caso HW '{c}': {e}")
            resultados[c] = {"error": str(e)}

    # 2. Caso anual con OLS
    try:
        serie_anual = extraer_serie_temporal("META_ANUAL", engine=engine)
        res_ols = estimar_tendencia_anual_ols(serie_anual, horizonte_anios=2)
        resultados["META_ANUAL"] = res_ols
        if engine is not None:
            persistir_resultado_forecast(res_ols, engine)
    except Exception as e:
        logger.error(f"Error procesando caso OLS 'META_ANUAL': {e}")
        resultados["META_ANUAL"] = {"error": str(e)}

    logger.info("Pipeline de forecasting completado exitosamente.")
    return resultados


if __name__ == "__main__":
    from backend.core.database import engine
    ejecutar_pipeline_forecasting_completo(engine=engine)
