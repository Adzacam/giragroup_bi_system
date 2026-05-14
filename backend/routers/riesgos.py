from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from services.risk_service import get_riesgo_cruzado

router = APIRouter(
    prefix="/api/v1/riesgos",
    tags=["Alertas de Riesgo"]
)

@router.get("/cruzado")
def obtener_riesgo_academico_financiero(
    limite_nota: float = 70.0, 
    min_cuotas: int = 2, 
    db: Session = Depends(get_db)
):
    """
    Retorna el cruce de estudiantes con bajo rendimiento académico y alta morosidad.
    """
    datos = get_riesgo_cruzado(db=db, limite_nota=limite_nota, min_cuotas_mora=min_cuotas)
    
    return {
        "status": "success",
        "total_casos_criticos": len(datos),
        "data": datos
    }