"""
backend/services/forecast_service.py
------------------------------------
GIRA-57: Servicio de consulta de pronósticos de demanda académica y metas.
Recupera los datos precalculados de fact_forecast o ejecuta el motor on-demand
si aún no se ha ejecutado el batch de persistencia.
"""

import sys
import logging
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

# Asegurar que el directorio raíz del proyecto esté en sys.path
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logger = logging.getLogger("forecast_service")

try:
    from pipeline.analytics.time_series_extractor import extraer_serie_temporal
    from pipeline.analytics.forecasting_holtwinters import entrenar_y_proyectar_hw
    from pipeline.analytics.forecasting_ols import estimar_tendencia_anual_ols
except ImportError:
    extraer_serie_temporal = None
    entrenar_y_proyectar_hw = None
    estimar_tendencia_anual_ols = None

try:
    from models.log_pipeline import LogPipelineIngesta
    from models.notification import Notification
    from services.notification_service import NotificationService
except ImportError:
    LogPipelineIngesta = None
    Notification = None
    NotificationService = None


def obtener_pronostico_alumnos(
    db: Optional[Session] = None,
    tipo: str = "GLOBAL",
    horizonte: int = 6
) -> Dict[str, Any]:
    """
    Retorna la proyección de alumnos inscritos para el horizonte especificado (1 a 6 meses).
    Casos soportados: GLOBAL, DIPLOMADO, CURSO, EXPERTO.
    """
    tipo_upper = _normalizar_texto(tipo)
    mapping = {
        "GLOBAL": "ALUMNOS_GLOBAL",
        "DIPLOMADO": "ALUMNOS_DIPLOMADO",
        "CURSO": "ALUMNOS_CURSO",
        "EXPERTO": "ALUMNOS_EXPERTO",
        "PROGRAMA EXPERTO": "ALUMNOS_EXPERTO",
        "MAESTRIA": "ALUMNOS_GLOBAL",
        "MAESTRÍA": "ALUMNOS_GLOBAL",
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

    # 2. On-demand: solo con datos reales del DW y observaciones suficientes
    engine = db.get_bind() if db is not None else None
    serie = extraer_serie_temporal(caso_uso, engine=engine)
    res, motivo = _proyectar_hw_seguro(serie, caso_uso, horizonte)
    if res is None:
        return _respuesta_sin_datos(caso_uso, motivo, tipo_solicitado=tipo_upper, n_observaciones=len(serie))

    proyecciones = [
        {"periodo": p, "valor_forecast": f, "ic_lower": l, "ic_upper": u}
        for p, f, l, u in zip(res["periodos"], res["forecast"], res["ic_lower"], res["ic_upper"])
    ]

    # Persistir en fact_forecast para acelerar subsecuentes lecturas
    if db is not None:
        _persistir_en_fact_forecast(db, caso_uso, proyecciones, res["metodo"], res["horizonte_meses"])

    return {
        "caso_uso": caso_uso,
        "tipo_solicitado": tipo_upper,
        "metodo": res["metodo"],
        "origen": "on_demand_computation",
        "horizonte_meses": res["horizonte_meses"],
        "n_observaciones": len(serie),
        "rmse": res["rmse"],
        "aic": res["aic"],
        "proyecciones": proyecciones
    }


MIN_OBS_HW = 24   # dos ciclos estacionales completos (m=12)
MIN_OBS_OLS = 3   # tres gestiones cerradas


def _respuesta_sin_datos(caso_uso: str, motivo: str, **extra) -> Dict[str, Any]:
    """Respuesta vacía explícita: el frontend muestra 'sin datos', nunca cifras de relleno."""
    return {"caso_uso": caso_uso, "origen": "sin_datos", "sin_datos": True,
            "mensaje": motivo, "proyecciones": [], **extra}


def _proyectar_hw_seguro(serie: pd.Series, caso_uso: str, horizonte: int):
    if entrenar_y_proyectar_hw is None:
        return None, "Motor de pronóstico no disponible."
    if len(serie) < MIN_OBS_HW:
        return None, (f"Se requieren al menos {MIN_OBS_HW} meses ingestados en el Data Warehouse "
                      f"para Holt-Winters (disponibles: {len(serie)}).")
    try:
        return entrenar_y_proyectar_hw(serie, caso_uso=caso_uso, horizonte=max(1, min(6, horizonte))), None
    except ValueError as e:
        return None, str(e)


def _proyectar_ols_seguro(serie: pd.Series, horizonte_anios: int):
    if estimar_tendencia_anual_ols is None:
        return None, "Motor OLS no disponible."
    if len(serie) < MIN_OBS_OLS:
        return None, (f"Se requieren al menos {MIN_OBS_OLS} gestiones cerradas en el Data Warehouse "
                      f"para la tendencia OLS (disponibles: {len(serie)}).")
    try:
        return estimar_tendencia_anual_ols(serie, horizonte_anios=horizonte_anios), None
    except ValueError as e:
        return None, str(e)


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
    Pronóstico de metas financieras:
    - MENSUAL: ingresos mensuales de Programas (Holt-Winters).
    - ANUAL: tendencia anual indicativa (OLS sobre gestiones cerradas).
    Sin historia suficiente en el DW devuelve sin_datos=True y proyecciones vacías.
    """
    gran_upper = granularity.strip().upper()
    engine = db.get_bind() if db is not None else None

    if gran_upper == "ANUAL":
        serie_anual = extraer_serie_temporal("META_ANUAL", engine=engine)
        res_ols, motivo = _proyectar_ols_seguro(serie_anual, min(horizonte, 3))
        if res_ols is None:
            return _respuesta_sin_datos("META_ANUAL", motivo, granularidad="ANUAL", n_observaciones=len(serie_anual))
        proyecciones = [
            {"periodo": p, "monto_proyectado_bs": f, "ic_lower": round(f * 0.95, 2), "ic_upper": round(f * 1.05, 2)}
            for p, f in zip(res_ols["periodos"], res_ols["forecast"])
        ]
        return {
            "caso_uso": "META_ANUAL",
            "granularidad": "ANUAL",
            "metodo": res_ols["metodo"],
            "tipo_estimacion": res_ols["tipo_estimacion"],
            "pendiente_anual_bs": res_ols["pendiente_anual_bs"],
            "cagr_historico_pct": res_ols["cagr_historico_pct"],
            "banda_operativa_pct": 5.0,
            "banda_min_bs": round(res_ols["forecast"][0] * 0.95, 2) if res_ols["forecast"] else None,
            "banda_max_bs": round(res_ols["forecast"][0] * 1.05, 2) if res_ols["forecast"] else None,
            "nota_metodologica": res_ols["nota_metodologica"],
            "proyecciones": proyecciones
        }

    serie_mensual = extraer_serie_temporal("META_MENSUAL_PROGRAMAS", engine=engine)
    res_hw, motivo = _proyectar_hw_seguro(serie_mensual, "META_MENSUAL_PROGRAMAS", min(horizonte, 6))
    if res_hw is None:
        return _respuesta_sin_datos("META_MENSUAL_PROGRAMAS", motivo, granularidad="MENSUAL",
                                    n_observaciones=len(serie_mensual))
    proyecciones = [
        {"periodo": p, "monto_proyectado_bs": f, "ic_lower": l, "ic_upper": u}
        for p, f, l, u in zip(res_hw["periodos"], res_hw["forecast"], res_hw["ic_lower"], res_hw["ic_upper"])
    ]
    return {
        "caso_uso": "META_MENSUAL_PROGRAMAS",
        "granularidad": "MENSUAL",
        "metodo": res_hw["metodo"],
        "horizonte_meses": res_hw["horizonte_meses"],
        "rmse": res_hw["rmse"],
        "aic": res_hw["aic"],
        "proyecciones": proyecciones
    }


def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


def _limpiar_nombre_programa(nombre: str) -> str:
    s = str(nombre).strip()
    s = re.sub(r'\s+v\.?\s*[\dIXVLCDM\.\-\w\s]+$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*-\s*NAL$', '', s, flags=re.IGNORECASE)
    return s.strip()


def _determinar_tipo_programa(nombre: str) -> str:
    u = _normalizar_texto(str(nombre))
    if "DIPLOMADO" in u:
        return "DIPLOMADO"
    if "CURSO" in u:
        return "CURSO"
    if "EXPERTO" in u:
        return "EXPERTO"
    if "MAESTR" in u:
        return "MAESTRÍA"
    return "PROGRAMA"


_SQL_INSCRITOS_PROGRAMA_GESTION = text("""
    SELECT dm.programa, dt.gestion, SUM(fm.inscritos)::int AS inscritos
    FROM public.fact_marketing fm
    JOIN public.dim_modulo dm ON fm.id_modulo = dm.id_modulo
    JOIN public.dim_tiempo dt ON fm.id_tiempo = dt.id_tiempo
    WHERE dm.programa IS NOT NULL AND fm.inscritos > 0
    GROUP BY dm.programa, dt.gestion
""")


def _inscritos_por_programa(db: Optional[Session]) -> pd.DataFrame:
    """Inscritos por programa y gestión, exclusivamente desde fact_marketing (DW)."""
    if db is None:
        return pd.DataFrame(columns=["programa", "gestion", "inscritos"])
    try:
        rows = db.execute(_SQL_INSCRITOS_PROGRAMA_GESTION).fetchall()
    except Exception as e:
        logger.warning(f"No se pudo leer fact_marketing: {e}")
        db.rollback()
        rows = []
    return pd.DataFrame(rows, columns=["programa", "gestion", "inscritos"])


def obtener_matriz_viabilidad_programas(
    db: Optional[Session] = None,
    tipo_filtro: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Matriz de Viabilidad Estratégica de Programas (Foco Marketing) calculada sobre
    fact_marketing. Sin inscripciones ingestadas retorna lista vacía.
    Decisión: 'ABRIR NUEVA VERSIÓN' | 'CONTINUAR' | 'DESCARTAR / REESTRUCTURAR'.
    """
    df = _inscritos_por_programa(db)
    if df.empty:
        return []

    anio_actual = pd.Timestamp.now().year
    a1, a2, a3 = anio_actual - 1, anio_actual - 2, anio_actual - 3
    df["base_prog"] = df["programa"].apply(_limpiar_nombre_programa)
    agg = df.groupby(["base_prog", "gestion"])["inscritos"].sum().unstack(fill_value=0)
    totales = agg.sum(axis=1).sort_values(ascending=False).head(25)

    datos = []
    for p in totales.index:
        fila = agg.loc[p]

        def c(anio: int) -> int:
            return int(fila.get(anio, 0))

        total, c_a3, c_a2, c_a1, c_act = int(totales[p]), c(a3), c(a2), c(a1), c(anio_actual)

        if c_a3 > 0 and c_a1 > 0:
            cagr = round(((c_a1 / c_a3) ** 0.5 - 1.0) * 100.0, 1)
        elif c_a2 > 0 and c_a1 > 0:
            cagr = round(((c_a1 - c_a2) / c_a2) * 100.0, 1)
        else:
            cagr = 0.0

        ajuste_cagr = max(-0.4, min(0.6, cagr / 100.0))
        proy_6m = int(round(c_a1 * 0.5 * (1.0 + ajuste_cagr)))
        pendiente_mensual = round((c_a1 - c_a2) / 12.0, 1)
        signo = "+" if pendiente_mensual >= 0 else ""

        if c_a1 >= 35 and cagr >= 5.0:
            decision, color = "ABRIR NUEVA VERSIÓN", "emerald"
            justificacion = f"Demanda alta y sostenida ({total} inscritos históricos, CAGR {cagr}%). Alta absorción proyectada."
        elif c_a1 >= 18 or cagr >= -10.0:
            decision, color = "CONTINUAR", "amber"
            justificacion = f"Desempeño estable ({c_a1} inscritos en {a1}). Mantener rotación de módulos y monitoreo de equilibrio."
        else:
            decision, color = "DESCARTAR / REESTRUCTURAR", "rose"
            justificacion = f"Volumen contractivo o inferior al punto de equilibrio ({c_a1} inscritos en {a1}). Requiere rediseño curricular."

        datos.append({
            "programa": p,
            "tipo": _determinar_tipo_programa(p),
            "total_historico": total,
            "anio_anterior": a1,
            "anio_actual": anio_actual,
            "inscritos_anio_anterior": c_a1,
            "inscritos_anio_actual": c_act,
            "cagr_pct": float(cagr),
            "proyeccion_6m": proy_6m,
            "tendencia_ols": f"{signo}{pendiente_mensual} al/mes",
            "decision_sugerida": decision,
            "badge_color": color,
            "justificacion": justificacion
        })

    if tipo_filtro and _normalizar_texto(tipo_filtro) != "GLOBAL":
        tf = _normalizar_texto(tipo_filtro)
        return [d for d in datos if tf in _normalizar_texto(d["tipo"])]
    return datos


def _resumen_cartera(df: pd.DataFrame) -> Dict[str, Any]:
    """Participación de inscritos por tipo de programa, calculada desde el DW."""
    if df.empty:
        return {}
    tipos = df["programa"].apply(_determinar_tipo_programa)
    por_tipo = df.groupby(tipos)["inscritos"].sum().sort_values(ascending=False)
    total = float(por_tipo.sum()) or 1.0
    return {
        _normalizar_texto(t): {"total_inscritos": int(v), "pct_participacion": round(v / total * 100.0, 1)}
        for t, v in por_tipo.items()
    }


_SQL_META_VS_EJECUTADO = text("""
    SELECT dt.gestion, dt.mes,
           SUM(fr.monto_meta)::float AS meta,
           SUM(fr.monto_ejecutado)::float AS ejecutado
    FROM public.fact_rentabilidad fr
    JOIN public.dim_categoria_financiera dcf ON fr.id_categoria = dcf.id_categoria
    JOIN public.dim_tiempo dt ON fr.id_tiempo = dt.id_tiempo
    WHERE dcf.nombre_categoria = 'PROGRAMAS'
    GROUP BY dt.gestion, dt.mes
    ORDER BY dt.gestion, dt.mes
""")

_MESES_CORTOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
_MESES_LARGOS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
                 "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _meta_vs_ejecutado(db: Optional[Session]) -> pd.DataFrame:
    if db is None:
        return pd.DataFrame(columns=["gestion", "mes", "meta", "ejecutado"])
    try:
        rows = db.execute(_SQL_META_VS_EJECUTADO).fetchall()
    except Exception as e:
        logger.warning(f"No se pudo leer fact_rentabilidad: {e}")
        db.rollback()
        rows = []
    return pd.DataFrame(rows, columns=["gestion", "mes", "meta", "ejecutado"])


def _num(v) -> Optional[float]:
    return None if v is None or pd.isna(v) else round(float(v), 2)


def obtener_analitica_macro_completa(
    db: Optional[Session] = None,
    horizonte: int = 6
) -> Dict[str, Any]:
    """
    Suite de Analítica Predictiva Macro (4 casos) calculada solo con datos del DW:
    - Caso 1: Demanda Global de Alumnos (Holt-Winters, OLS, CAGR, MAPE, RMSE)
    - Caso 2: Demanda por Programa y Matriz de Viabilidad (Marketing)
    - Caso 3: Meta vs Ejecutado mensual (fact_rentabilidad) + cierre HW
    - Caso 4: Recaudación anual OLS vs meta anual registrada
    Un caso sin historia suficiente se devuelve como None y su motivo en `sin_datos`.
    """
    engine = db.get_bind() if db is not None else None
    h_safe = max(1, min(6, 6 if horizonte is None else int(horizonte)))
    sin_datos: Dict[str, str] = {}

    # ── CASO 1: Demanda Global de Alumnos ──────────────────────────────
    serie_global = extraer_serie_temporal("ALUMNOS_GLOBAL", engine=engine)
    hw_alumnos, motivo = _proyectar_hw_seguro(serie_global, "ALUMNOS_GLOBAL", h_safe)
    caso1 = None
    if hw_alumnos is None:
        sin_datos["caso1"] = motivo
    else:
        n_meses = len(serie_global)
        y_arr = np.array([float(v) for v in serie_global.values], dtype=float)
        x_arr = np.arange(n_meses)
        poly = np.polyfit(x_arr, y_arr, deg=1)
        x_full = np.arange(n_meses + len(hw_alumnos["periodos"]))
        residuos = y_arr - (poly[0] * x_arr + poly[1])
        caso1 = {
            "nombre": "Caso 1: Demanda Global de Alumnos",
            "n_observaciones": n_meses,
            "periodos_historicos": [str(p) for p in serie_global.index],
            "valores_historicos": y_arr.tolist(),
            "periodos_proyectados": hw_alumnos["periodos"],
            "forecast_hw": hw_alumnos["forecast"],
            "ic_lower_95": hw_alumnos["ic_lower"],
            "ic_upper_95": hw_alumnos["ic_upper"],
            "recta_ols_full": [max(0.0, float(round(poly[0] * i + poly[1], 1))) for i in x_full],
            "pendiente_ols_mes": float(round(poly[0], 2)),
            "intercepto_ols": float(round(poly[1], 2)),
            "cagr_historico_pct": float(round(((y_arr[-1] / max(1.0, y_arr[0])) ** (12.0 / n_meses) - 1.0) * 100.0, 2)),
            "mape_pct": float(round(np.mean(np.abs(residuos / np.maximum(y_arr, 1.0))) * 100.0, 2)),
            "rmse": hw_alumnos["rmse"],
            "modelo": "Holt-Winters Aditivo (m=12) con cota no negativa y Banda 95%"
        }

    # ── CASO 2: Demanda por Programa y Matriz de Viabilidad ─────────────
    matriz = obtener_matriz_viabilidad_programas(db=db)
    caso2 = None
    if not matriz:
        sin_datos["caso2"] = "No hay inscripciones ingestadas en fact_marketing."
    else:
        caso2 = {
            "nombre": "Caso 2: Demanda por Programa y Matriz de Viabilidad",
            "resumen_cartera": _resumen_cartera(_inscritos_por_programa(db)),
            "matriz_viabilidad": matriz,
            "segmentos": {
                t: obtener_pronostico_alumnos(db=db, tipo=t, horizonte=h_safe)["proyecciones"]
                for t in ("DIPLOMADO", "CURSO", "EXPERTO")
            }
        }

    # ── CASO 3: Meta vs Ejecutado mensual ───────────────────────────────
    mve = _meta_vs_ejecutado(db)
    caso3 = None
    if mve.empty:
        sin_datos["caso3"] = "No hay metas ni ejecución financiera ingestadas en fact_rentabilidad."
    else:
        hw_metas = obtener_pronostico_metas(db=db, granularity="MENSUAL", horizonte=h_safe)
        ult = mve.tail(18)
        ultimo = ult.iloc[-1]
        proy = hw_metas.get("proyecciones") or []
        cierre = proy[0]["monto_proyectado_bs"] if proy else None
        meta_mes = _num(ultimo["meta"])
        caso3 = {
            "nombre": "Caso 3: Cumplimiento de Metas / Ingresos Mensuales",
            "meses_etiquetas": [f"{_MESES_CORTOS[int(m) - 1]} {str(int(g))[-2:]}" for g, m in zip(ult["gestion"], ult["mes"])],
            "meta_catalogo_bs": [_num(v) for v in ult["meta"]],
            "ejecutado_real_bs": [_num(v) for v in ult["ejecutado"]],
            "proyecciones_hw": proy,
            "mes_actual": {
                "periodo": f"{_MESES_LARGOS[int(ultimo['mes']) - 1]} {int(ultimo['gestion'])}",
                "meta_mes_bs": meta_mes,
                "ejecutado_actual_bs": _num(ultimo["ejecutado"]),
                "cierre_proyectado_hw_bs": cierre,
                "ic_lower_95": proy[0]["ic_lower"] if proy else None,
                "ic_upper_95": proy[0]["ic_upper"] if proy else None,
                "cumplimiento_proyectado_pct": round(cierre / meta_mes * 100.0, 1) if cierre and meta_mes else None
            },
            "rmse": hw_metas.get("rmse"),
            "mensaje_pronostico": hw_metas.get("mensaje")
        }

    # ── CASO 4: Recaudación anual vs meta anual ─────────────────────────
    serie_anual = extraer_serie_temporal("META_ANUAL", engine=engine)
    anio_actual = pd.Timestamp.now().year
    del_anio = mve[mve["gestion"] == anio_actual] if not mve.empty else mve
    meta_anual = _num(del_anio["meta"].sum(min_count=1)) if not del_anio.empty else None
    recaudado = _num(del_anio["ejecutado"].sum(min_count=1)) if not del_anio.empty else None
    caso4 = None
    if serie_anual.empty and meta_anual is None and recaudado is None:
        sin_datos["caso4"] = "No hay recaudación anual ni metas de la gestión ingestadas en fact_rentabilidad."
    else:
        ols_anual = obtener_pronostico_metas(db=db, granularity="ANUAL", horizonte=2)
        proy_ols = ols_anual.get("proyecciones") or []
        cierre_ols = float(proy_ols[0]["monto_proyectado_bs"]) if proy_ols else None
        caso4 = {
            "nombre": "Caso 4: Cumplimiento de Metas / Ingresos Anuales",
            "anios_historicos": [int(a) for a in serie_anual.index],
            "valores_historicos_bs": [float(v) for v in serie_anual.values],
            "proyecciones_ols": proy_ols,
            "pendiente_anual_bs": ols_anual.get("pendiente_anual_bs"),
            "cagr_historico_pct": ols_anual.get("cagr_historico_pct"),
            "gestion_actual": anio_actual,
            "meta_anual_institucional_bs": meta_anual,
            "recaudado_acumulado_bs": recaudado,
            "cierre_anual_proyectado_ols_bs": cierre_ols,
            "porcentaje_avance_meta": round(recaudado / meta_anual * 100.0, 1) if recaudado and meta_anual else None,
            "banda_ols_indicativa": {
                "porcentaje_tolerancia": 5.0,
                "min_bs": round(cierre_ols * 0.95, 2),
                "max_bs": round(cierre_ols * 1.05, 2)
            } if cierre_ols else None,
            "nota_metodologica": ols_anual.get("nota_metodologica") or ols_anual.get("mensaje")
        }

    return {
        "status": "success",
        "fecha_calculo_iso": pd.Timestamp.now().isoformat(),
        "horizonte_meses": h_safe,
        "sin_datos": sin_datos,
        "caso1_demanda_global": caso1,
        "caso2_demanda_programa": caso2,
        "caso3_metas_mensuales": caso3,
        "caso4_metas_anuales": caso4
    }
