"""
backend/routers/forecast.py
---------------------------
GIRA-57: Router FastAPI para consultas de pronósticos de demanda académica y metas financieras.
Implementa validaciones OWASP (A03, A04, A05), contratos Pydantic v2 y sanitización de errores.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import require_roles
from models.user import User
from services import cache_consultas
from services.forecast_service import (
    obtener_pronostico_alumnos,
    obtener_pronostico_metas,
    obtener_analitica_macro_completa,
    obtener_matriz_viabilidad_programas
)
from schemas.forecast_schemas import (
    ForecastAlumnosResponse,
    ForecastMetasResponse,
    AnaliticaMacroResponse,
    MatrizViabilidadResponse
)

logger = logging.getLogger("forecast_router")

router = APIRouter(
    prefix="/api/v1/forecast",
    tags=["Pronósticos y Metas (Forecasting)"]
)

# Lecturas cacheadas (RNF-03); se invalidan al consolidar cargas en el DW
TTL_FORECAST_SEG = 600

TIPOS_PERMITIDOS = {"GLOBAL", "DIPLOMADO", "CURSO", "EXPERTO", "PROGRAMA EXPERTO", "MAESTRIA", "MAESTRÍA"}
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
        description="Segmento académico: 'GLOBAL', 'DIPLOMADO', 'CURSO', 'EXPERTO', 'MAESTRÍA'",
        max_length=50
    ),
    horizonte: int = Query(
        6, 
        ge=1, 
        le=6, 
        description="Horizonte de predicción en meses (acotado formalmente a máximo 6 meses)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["DIRECTOR_ACADEMICO", "ADMIN", "ANALISTA_MARKETING"]))
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ANALISTA_FINANCIERO", "ADMIN"]))
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
        # Holt-Winters / OLS se entrenan una vez por TTL, no en cada petición
        resultado = cache_consultas.obtener(
            ("forecast_metas", gran_sanitizada, horizonte), TTL_FORECAST_SEG,
            lambda: obtener_pronostico_metas(db=db, granularity=gran_sanitizada, horizonte=horizonte),
        )
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


@router.get(
    "/analitica-macro",
    response_model=AnaliticaMacroResponse,
    summary="Obtener suite unificada de Analítica Predictiva Macro (4 Casos de Negocio)"
)
@router.get(
    "/laboratorio-macro",
    response_model=AnaliticaMacroResponse,
    include_in_schema=False
)
def get_analitica_macro(
    horizonte: int = Query(
        6,
        ge=1,
        le=6,
        description="Horizonte mensual de proyección (1 a 6 meses)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO", "ANALISTA_MARKETING"]))
):
    """
    Retorna la suite completa de Analítica Predictiva Macro integrando:
    - Caso 1: Demanda Global de Alumnos (serie N=43, Holt-Winters, OLS, CAGR, MAPE, RMSE)
    - Caso 2: Demanda por Programa y Matriz de Viabilidad (Marketing)
    - Caso 3: Cumplimiento de Metas / Ingresos Mensuales
    - Caso 4: Cumplimiento de Metas / Ingresos Anuales (3.8M Bs)
    """
    try:
        resultado = obtener_analitica_macro_completa(db=db, horizonte=horizonte)
        return resultado
    except Exception as e:
        logger.error(f"Error en analítica predictiva macro: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar los modelos de analítica predictiva macro."
        )


@router.get(
    "/viabilidad-programas",
    response_model=MatrizViabilidadResponse,
    summary="Matriz de Viabilidad Estratégica de Programas y Cursos (Marketing)"
)
def get_viabilidad_programas(
    tipo: Optional[str] = Query(
        None,
        description="Filtro opcional: 'GLOBAL', 'DIPLOMADO', 'CURSO', 'EXPERTO', 'MAESTRÍA'",
        max_length=50
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO", "ANALISTA_MARKETING"]))
):
    """
    Retorna la Matriz de Viabilidad de Programas Académicos con recomendaciones estratégicas:
    - 'ABRIR NUEVA VERSIÓN' (emerald)
    - 'CONTINUAR' (amber)
    - 'DESCARTAR / REESTRUCTURAR' (rose)
    """
    try:
        datos = obtener_matriz_viabilidad_programas(db=db, tipo_filtro=tipo)
        return {
            "status": "success",
            "total_programas": len(datos),
            "data": datos
        }
    except Exception as e:
        logger.error(f"Error en matriz de viabilidad: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar la matriz de viabilidad de cursos."
        )

