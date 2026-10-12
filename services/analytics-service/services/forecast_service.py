"""
backend/services/forecast_service.py
------------------------------------
GIRA-57: Servicio de consulta de pronósticos de demanda académica y metas.
Recupera los datos precalculados de fact_forecast o ejecuta el motor on-demand
si aún no se ha ejecutado el batch de persistencia.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en sys.path
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from pipeline.analytics.time_series_extractor import extraer_serie_temporal
    from pipeline.analytics.forecasting_holtwinters import entrenar_y_proyectar_hw
    from pipeline.analytics.forecasting_ols import estimar_tendencia_anual_ols
except ImportError:
    extraer_serie_temporal = None
    entrenar_y_proyectar_hw = None
    estimar_tendencia_anual_ols = None


def obtener_pronostico_alumnos(
    db: Optional[Session] = None,
    tipo: str = "GLOBAL",
    horizonte: int = 6
) -> Dict[str, Any]:
    """
    Retorna la proyección de alumnos inscritos para el horizonte especificado (1 a 6 meses).
    Casos soportados: GLOBAL, DIPLOMADO, CURSO, EXPERTO.
    """
    tipo_upper = tipo.strip().upper()
    mapping = {
        "GLOBAL": "ALUMNOS_GLOBAL",
        "DIPLOMADO": "ALUMNOS_DIPLOMADO",
        "CURSO": "ALUMNOS_CURSO",
        "EXPERTO": "ALUMNOS_EXPERTO",
        "PROGRAMA EXPERTO": "ALUMNOS_EXPERTO",
    }
    caso_uso = mapping.get(tipo_upper, "ALUMNOS_GLOBAL")

    # 1. Intentar consultar fact_forecast en la base de datos
    if db is not None:
        try:
            query = text("""
                SELECT 
                    dt.periodo_mes,
                    ff.valor_forecast,
                    ff.ic_lower,
                    ff.ic_upper,
                    ff.metodo,
                    ff.generado_en
                FROM public.fact_forecast ff
                JOIN public.dim_tiempo dt ON ff.id_tiempo = dt.id_tiempo
                WHERE ff.caso_uso = :caso
                ORDER BY dt.periodo_mes
                LIMIT :limite;
            """)
            rows = db.execute(query, {"caso": caso_uso, "limite": horizonte}).fetchall()
            if rows and len(rows) > 0:
                proyecciones = []
                for r in rows:
                    proyecciones.append({
                        "periodo": r.periodo_mes,
                        "valor_forecast": float(r.valor_forecast),
                        "ic_lower": float(r.ic_lower) if r.ic_lower is not None else None,
                        "ic_upper": float(r.ic_upper) if r.ic_upper is not None else None,
                    })
                return {
                    "caso_uso": caso_uso,
                    "tipo_solicitado": tipo_upper,
                    "metodo": rows[0].metodo,
                    "origen": "database_fact_forecast",
                    "horizonte_meses": len(proyecciones),
                    "proyecciones": proyecciones
                }
        except Exception:
            # Si falla la consulta o tabla vacía, fallback on-demand
            pass

    # 2. On-demand compute si no está en fact_forecast
    engine = db.get_bind() if db is not None else None
    serie = extraer_serie_temporal(caso_uso, engine=engine)
    res = entrenar_y_proyectar_hw(serie, caso_uso=caso_uso, horizonte=horizonte)

    proyecciones = []
    for p, f, l, u in zip(res["periodos"], res["forecast"], res["ic_lower"], res["ic_upper"]):
        proyecciones.append({
            "periodo": p,
            "valor_forecast": f,
            "ic_lower": l,
            "ic_upper": u
        })

    # Persistir en fact_forecast para acelerar subsecuentes lecturas
    if db is not None:
        _persistir_en_fact_forecast(db, caso_uso, proyecciones, res["metodo"], res["horizonte_meses"])

    return {
        "caso_uso": caso_uso,
        "tipo_solicitado": tipo_upper,
        "metodo": res["metodo"],
        "origen": "on_demand_computation",
        "horizonte_meses": res["horizonte_meses"],
        "rmse": res["rmse"],
        "aic": res["aic"],
        "proyecciones": proyecciones
    }


def _persistir_en_fact_forecast(db: Session, caso_uso: str, proyecciones: list, metodo: str, horizonte: int):
    try:
        from models.fact_forecast import FactForecast
        from models.dim_tiempo import DimTiempo
        for item in proyecciones:
            periodo = item.get("periodo")
            if not periodo:
                continue
            # Buscar id_tiempo
            t = db.query(DimTiempo).filter(DimTiempo.periodo_mes == periodo).first()
            id_t = t.id_tiempo if t else int(f"{periodo.replace('-', '')[:6]}01")

            val = item.get("valor_forecast") or item.get("monto_proyectado_bs")
            if val is None:
                continue

            existente = db.query(FactForecast).filter(
                FactForecast.caso_uso == caso_uso,
                FactForecast.id_tiempo == id_t
            ).first()

            if existente:
                existente.valor_forecast = val
                existente.ic_lower = item.get("ic_lower")
                existente.ic_upper = item.get("ic_upper")
                existente.metodo = metodo
                existente.horizonte_meses = horizonte
            else:
                nuevo = FactForecast(
                    caso_uso=caso_uso,
                    id_tiempo=id_t,
                    valor_forecast=val,
                    ic_lower=item.get("ic_lower"),
                    ic_upper=item.get("ic_upper"),
                    metodo=metodo,
                    horizonte_meses=horizonte
                )
                db.add(nuevo)
        db.commit()
    except Exception:
        db.rollback()


def obtener_pronostico_metas(
    db: Optional[Session] = None,
    granularity: str = "MENSUAL",
    horizonte: int = 6
) -> Dict[str, Any]:
    """
    Retorna el pronóstico de metas financieras:
    - granularity='MENSUAL': Proyección mensual de ingresos para Programas (Holt-Winters).
    - granularity='ANUAL': Proyección indicativa de tendencia anual 2026-2027 (OLS N=3).
    """
    gran_upper = granularity.strip().upper()
    engine = db.get_bind() if db is not None else None

    if gran_upper == "ANUAL":
        serie_anual = extraer_serie_temporal("META_ANUAL", engine=engine)
        res_ols = estimar_tendencia_anual_ols(serie_anual, horizonte_anios=min(horizonte, 3))
        proyecciones = []
        for p, f in zip(res_ols["periodos"], res_ols["forecast"]):
            proyecciones.append({
                "periodo": p,
                "monto_proyectado_bs": f,
                "ic_lower": None,
                "ic_upper": None
            })
        return {
            "caso_uso": "META_ANUAL",
            "granularidad": "ANUAL",
            "metodo": res_ols["metodo"],
            "tipo_estimacion": res_ols["tipo_estimacion"],
            "pendiente_anual_bs": res_ols["pendiente_anual_bs"],
            "cagr_historico_pct": res_ols["cagr_historico_pct"],
            "nota_metodologica": res_ols["nota_metodologica"],
            "proyecciones": proyecciones
        }
    else:
        # Mensual con Holt-Winters
        serie_mensual = extraer_serie_temporal("META_MENSUAL_PROGRAMAS", engine=engine)
        res_hw = entrenar_y_proyectar_hw(serie_mensual, caso_uso="META_MENSUAL_PROGRAMAS", horizonte=min(horizonte, 6))
        proyecciones = []
        for p, f, l, u in zip(res_hw["periodos"], res_hw["forecast"], res_hw["ic_lower"], res_hw["ic_upper"]):
            proyecciones.append({
                "periodo": p,
                "monto_proyectado_bs": f,
                "ic_lower": l,
                "ic_upper": u
            })
        return {
            "caso_uso": "META_MENSUAL_PROGRAMAS",
            "granularidad": "MENSUAL",
            "metodo": res_hw["metodo"],
            "horizonte_meses": res_hw["horizonte_meses"],
            "rmse": res_hw["rmse"],
            "aic": res_hw["aic"],
            "proyecciones": proyecciones
        }
