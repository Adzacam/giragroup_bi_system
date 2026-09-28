"""
backend/routers/riesgos.py
--------------------------
Router FastAPI para consultas de alertas y riesgo cruzado académico-financiero.
Implementa validaciones de rango numérico (OWASP A04) y respuesta tipada Pydantic.
"""

import logging
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import require_roles
from models.user import User
from services.risk_service import get_riesgo_cruzado
from schemas.risk_schemas import RiesgoCruzadoResponse

logger = logging.getLogger("riesgos_router")

router = APIRouter(
    prefix="/api/v1/riesgos",
    tags=["Alertas de Riesgo"]
)


@router.get(
    "/cruzado",
    response_model=RiesgoCruzadoResponse,
    summary="Obtener alertas de riesgo académico-financiero cruzado",
    responses={
        400: {"description": "Parámetros fuera de rango permitido"},
        500: {"description": "Error interno del servidor (sanitizado)"}
    }
)
def obtener_riesgo_academico_financiero(
    limite_nota: float = Query(
        70.0, 
        ge=0.0, 
        le=100.0, 
        description="Nota máxima de umbral de riesgo (entre 0.0 y 100.0)"
    ), 
    min_cuotas: int = Query(
        2, 
        ge=0, 
        le=100, 
        description="Cantidad mínima de cuotas en mora (>= 0)"
    ), 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO"]))
):
    """
    Retorna el cruce de estudiantes con bajo rendimiento académico y alta morosidad.
    """
    try:
        datos = get_riesgo_cruzado(db=db, limite_nota=limite_nota, min_cuotas_mora=min_cuotas)
        return {
            "status": "success",
            "total_casos_criticos": len(datos),
            "data": datos
        }
    except Exception as e:
        logger.error(f"Falla al obtener riesgo cruzado: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al evaluar alertas de riesgo académico-financiero."
        )