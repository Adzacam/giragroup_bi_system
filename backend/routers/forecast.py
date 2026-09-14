"""
backend/routers/forecast.py
---------------------------
GIRA-57: Router FastAPI para consultas de pronósticos de demanda académica y metas financieras.
Implementa validaciones OWASP (A03, A04, A05), contratos Pydantic v2 y sanitización de errores.
"""

import logging
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from services.forecast_service import obtener_pronostico_alumnos, obtener_pronostico_metas
from schemas.forecast_schemas import ForecastAlumnosResponse, ForecastMetasResponse

logger = logging.getLogger("forecast_router")

router = APIRouter(
    prefix="/api/v1/forecast",
    tags=["Pronósticos y Metas (Forecasting)"]
)

TIPOS_PERMITIDOS = {"GLOBAL", "DIPLOMADO", "CURSO", "EXPERTO", "PROGRAMA EXPERTO"}
GRANULARIDADES_PERMITIDAS = {"MENSUAL", "ANUAL"}


@router.get(
    "/alumnos",
    response_model=ForecastAlumnosResponse,
    summary="Obtener proyección de alumnos inscritos",
    responses={
        400: {"description": "Parámetros de consulta no válidos"},
        500: {"description": "Error interno del servidor (sanitizado)"}
    }
)
def get_forecast_alumnos(
    tipo: str = Query(
        "GLOBAL", 
        description="Segmento académico: 'GLOBAL', 'DIPLOMADO', 'CURSO', 'EXPERTO'",
        max_length=50
    ),
    horizonte: int = Query(
        6, 
        ge=1, 
        le=6, 
        description="Horizonte de predicción en meses (acotado formalmente a máximo 6 meses)"
    ),
    db: Session = Depends(get_db)
):
    """
    Retorna la proyección mensual de alumnos inscritos para el segmento solicitado
    utilizando el modelo Holt-Winters aditivo con estacionalidad anual de 12 meses.
    """
    tipo_sanitizado = tipo.strip().upper()
    if tipo_sanitizado not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo '{tipo}' no válido. Opciones permitidas: {sorted(list(TIPOS_PERMITIDOS))}"
        )

    try:
        resultado = obtener_pronostico_alumnos(db=db, tipo=tipo_sanitizado, horizonte=horizonte)
        return {
            "status": "success",
            "data": resultado
        }
    except ValueError as ve:
        logger.warning(f"Error de validación de negocio en forecast alumnos: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # OWASP A05: No filtrar trazas ni rutas internas al cliente
        logger.error(f"Falla no controlada en forecast alumnos: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al procesar el pronóstico de demanda. Consulte al administrador."
        )


@router.get(
    "/metas",
    response_model=ForecastMetasResponse,
    summary="Obtener proyección de metas financieras",
    responses={
        400: {"description": "Parámetros de consulta no válidos"},
        500: {"description": "Error interno del servidor (sanitizado)"}
    }
)
def get_forecast_metas(
    granularidad: str = Query(
        "MENSUAL", 
        description="Granularidad de pronóstico: 'MENSUAL' (Holt-Winters) o 'ANUAL' (OLS N=3)",
        max_length=20
    ),
    horizonte: int = Query(
        6, 
        ge=1, 
        le=6, 
        description="Horizonte a proyectar (meses para MENSUAL, años para ANUAL)"
    ),
    db: Session = Depends(get_db)
):
    """
    Retorna la proyección de recaudación y metas financieras:
    - MENSUAL: Holt-Winters aditivo para ingresos mensuales en Programas.
    - ANUAL: Proyección indicativa de tendencia lineal (OLS) 2026-2027 sin IC espurio.
    """
    gran_sanitizada = granularidad.strip().upper()
    if gran_sanitizada not in GRANULARIDADES_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Granularidad '{granularidad}' no válida. Opciones: {sorted(list(GRANULARIDADES_PERMITIDAS))}"
        )

    try:
        resultado = obtener_pronostico_metas(db=db, granularity=gran_sanitizada, horizonte=horizonte)
        return {
            "status": "success",
            "data": resultado
        }
    except ValueError as ve:
        logger.warning(f"Error de validación de negocio en forecast metas: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # OWASP A05: Enmascaramiento de excepciones internas
        logger.error(f"Falla no controlada en forecast metas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al procesar la proyección de metas financieras."
        )
