"""
backend/routers/kpis.py
-----------------------
Router FastAPI para exposición de KPIs consolidados del CMI y feed de alertas para Power BI.
Aplica RBAC estricto según la matriz de mínimo privilegio (PoLP).
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import require_roles
from models.user import User
from services.kpi_service import KPIService
from services.alert_engine import AlertEngine
from schemas.kpi_schemas import (
    KpiGeneralResponse,
    KpisAcademicos,
    KpisFinancieros,
    KpisPipelineCalidad,
    AlertasListResponse
)

router = APIRouter(prefix="/api/v1", tags=["KPIs y Alertas de Negocio"])


@router.get(
    "/kpis",
    response_model=KpiGeneralResponse,
    summary="Obtener consolidado general de KPIs para CMI y Power BI"
)
def get_kpis_general(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO"]))
):
    service = KPIService(db)
    return service.obtener_consolidado_general()


@router.get(
    "/kpis/academico",
    response_model=KpisAcademicos,
    summary="KPIs de la perspectiva académica"
)
def get_kpis_academico(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["DIRECTOR_ACADEMICO", "ADMIN"]))
):
    service = KPIService(db)
    return service.obtener_kpis_academicos()


@router.get(
    "/kpis/financiero",
    response_model=KpisFinancieros,
    summary="KPIs de la perspectiva financiera y recaudación"
)
def get_kpis_financiero(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ANALISTA_FINANCIERO", "ADMIN"]))
):
    service = KPIService(db)
    return service.obtener_kpis_financieros()


@router.get(
    "/kpis/pipeline",
    response_model=KpisPipelineCalidad,
    summary="KPIs de calidad del pipeline de ingesta y NLP"
)
def get_kpis_pipeline(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"]))
):
    service = KPIService(db)
    return service.obtener_kpis_pipeline()


@router.get(
    "/alertas",
    response_model=AlertasListResponse,
    summary="Feed unificado de alertas institucionales para Power BI y CMI"
)
def get_alertas(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO"]))
):
    engine = AlertEngine(db)
    todas = engine.evaluar_todas(persistir_notificaciones=False)

    # Filtrar según rol si no es ADMIN
    if current_user.role == "DIRECTOR_ACADEMICO":
        filtradas = [a for a in todas if a["tipo"] in ("ACADEMICO", "DESERCION")]
    elif current_user.role == "ANALISTA_FINANCIERO":
        filtradas = [a for a in todas if a["tipo"] == "FINANCIERO"]
    else:
        filtradas = todas

    criticas = sum(1 for a in filtradas if a["severidad"] == "CRITICAL")
    advertencias = sum(1 for a in filtradas if a["severidad"] == "WARNING")

    return {
        "status": "success",
        "total_alertas": len(filtradas),
        "criticas": criticas,
        "advertencias": advertencias,
        "data": filtradas
    }
