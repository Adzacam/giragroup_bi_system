"""
pipeline/analytics/forecasting_ols.py
-------------------------------------
GIRA-55: Estimador OLS de tendencia indicativa para metas anuales (N=3).
Proyecta la recaudación anual para 2026-2027 basada en el ritmo de crecimiento 2023-2025.

Nota metodológica (Tribunal / Cap. 4):
Con N=3 observaciones anuales, los grados de libertad son mínimos (dof=1), por lo que
el ajuste lineal es puramente indicativo de tendencia y NO se calcula intervalo de
confianza al 95% para evitar supuestos estadísticos no respaldados por la muestra.
"""

import logging
from typing import Dict, Any, List
import numpy as np
import pandas as pd

logger = logging.getLogger("forecasting_ols")


def estimar_tendencia_anual_ols(
    serie_anual: pd.Series,
    horizonte_anios: int = 2
) -> Dict[str, Any]:
    """
    Estima la recta de tendencia indicativa mediante Mínimos Cuadrados Ordinarios (OLS grado 1).
    
    Parámetros:
    -----------
    serie_anual: pd.Series indexada por año (int: 2023, 2024, 2025) con valores en Bs.
    horizonte_anios: Años futuros a proyectar (por defecto 2: 2026 y 2027).
    
    Retorna:
    --------
    dict estructurado con la proyección puntual y la tasa anual de variación.
    """
    serie_clean = serie_anual.dropna().astype(float)
    anios_obs = np.array(serie_clean.index, dtype=float)
    valores_obs = serie_clean.values

    n_obs = len(anios_obs)
    if n_obs < 3:
        raise ValueError(f"Se requieren al menos 3 años históricos. Recibidos: {n_obs}")

    # Ajuste polinómico grado 1 (recta: y = m*x + b)
    coef = np.polyfit(anios_obs, valores_obs, deg=1)
    pendiente, intercepto = float(coef[0]), float(coef[1])
    poly = np.poly1d(coef)

    ultimo_anio = int(anios_obs[-1])
    anios_futuros = [ultimo_anio + i for i in range(1, horizonte_anios + 1)]
    proyecciones = [max(0.0, float(round(poly(a), 2))) for a in anios_futuros]

    # Variación porcentual interanual promedio histórica
    variaciones_pct = []
    for i in range(1, len(valores_obs)):
        prev = valores_obs[i - 1]
        act = valores_obs[i]
        if prev > 0:
            variaciones_pct.append(((act - prev) / prev) * 100.0)
    cagr_historico = float(np.mean(variaciones_pct)) if variaciones_pct else 0.0

    resultado = {
        "caso_uso": "META_ANUAL",
        "metodo": "OLS",
        "tipo_estimacion": "Proyección indicativa de tendencia lineal anual",
        "horizonte_anios": horizonte_anios,
        "n_observaciones": n_obs,
        "anios_historicos": [int(a) for a in anios_obs],
        "valores_historicos": [float(v) for v in valores_obs],
        "periodos": [str(a) for a in anios_futuros],
        "forecast": proyecciones,
        "ic_lower": None,  # No se reporta IC formal para N=3 por rigor estadístico
        "ic_upper": None,
        "pendiente_anual_bs": round(pendiente, 2),
        "cagr_historico_pct": round(cagr_historico, 2),
        "nota_metodologica": (
            "Estimación de tendencia lineal indicativa sobre N=3 puntos. "
            "No se calculan intervalos de confianza al 95% debido a la reducida "
            "muestra longitudinal histórica (dof=1). Ver Cap. 4 del informe técnico."
        )
    }

    logger.info(
        f"OLS anual calculado: pendiente={resultado['pendiente_anual_bs']} Bs/año, "
        f"Proyección: {dict(zip(anios_futuros, proyecciones))}"
    )
    return resultado
