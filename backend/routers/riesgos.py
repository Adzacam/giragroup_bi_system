"""
backend/routers/riesgos.py
--------------------------
Router FastAPI para consultas de alertas y riesgo cruzado académico-financiero
y Vista 3: Monitoreo de Reglas de Umbral y Alertas Tempranas (IF/THEN determinístico).
Implementa validaciones de rango numérico (OWASP A04) y respuesta tipada Pydantic.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import require_roles
from models.user import User
from services import cache_consultas
from services.risk_service import (
    get_riesgo_cruzado,
    evaluar_alertas_tempranas_deterministicas,
    obtener_ficha_cruzada_estudiante,
)
from schemas.risk_schemas import (
    RiesgoCruzadoResponse,
    AlertasTempranasResponse,
    FichaCruzadaEstudianteResponse,
)

logger = logging.getLogger("riesgos_router")

router = APIRouter(
    prefix="/api/v1/riesgos",
    tags=["Alertas de Riesgo"]
)

# Lecturas cacheadas (RNF-03); se invalidan al consolidar cargas en el DW
TTL_ALERTAS_SEG = 60

ROLES_ALERTAS = ["ADMIN", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO", "AUDITOR_CALIDAD"]


@router.get(
    "/estudiante/{id_estudiante}/revelar",
    summary="Revelar nombre o CI de un estudiante con auditoría (DD3)",
)
def revelar_campo_estudiante(
    id_estudiante: int = Path(..., ge=1),
    campo: str = Query("nombre", pattern="^(nombre|ci)$"),
    motivo: str = Query("Consulta operativa autorizada", max_length=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "ANALISTA_FINANCIERO", "DIRECTOR_ACADEMICO"])),
):
    from models.dim_estudiante import DimEstudiante
    from models.log_pipeline import LogPipelineIngesta

    est = db.query(DimEstudiante).filter(DimEstudiante.id_estudiante == id_estudiante).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado.")

    valor = (
        (est.nombre_completo or "").strip()
        if campo == "nombre"
        else (est.ci or est.ci_numero or est.codigo_estudiante or "S/C").strip()
    )
    user_name = getattr(current_user, "username", None) or "Usuario"
    user_role = getattr(current_user, "role", None) or "SIN_ROL"
    try:
        db.add(
            LogPipelineIngesta(
                id_documento=None,
                etapa="REVELACION_PII",
                nivel="INFO",
                modulo="Riesgos y Cartera",
                mensaje=f"{user_name} ({user_role}) reveló {campo} de estudiante #{id_estudiante}.",
                metadata_json={
                    "id_estudiante": id_estudiante,
                    "campo": campo,
                    "usuario": user_name,
                    "rol": user_role,
                    "motivo": motivo,
                },
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("No se pudo auditar revelación de estudiante %s: %s", id_estudiante, exc)

    return {"status": "success", "id_estudiante": id_estudiante, "campo": campo, "valor": valor}


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
    current_user: User = Depends(require_roles(ROLES_ALERTAS))
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


@router.get(
    "/alertas-tempranas",
    response_model=AlertasTempranasResponse,
    summary="Evaluar Motor Determinístico de Reglas Fijas (IF/THEN) de Alertas Tempranas",
)
def obtener_alertas_tempranas(
    periodo: Optional[str] = Query(None, description="Periodo académico o TODOS"),
    programa: Optional[str] = Query(None, description="Programa curricular o TODOS"),
    modulo: Optional[str] = Query(None, description="Módulo curricular o TODOS"),
    docente: Optional[str] = Query(None, description="Docente o TODOS"),
    regla_filtro: Optional[str] = Query(
        None,
        description="Filtro de regla o intersección: TODOS, ACADEMICO, DESERCION, FINANCIERO, CRITICA, A+D, D+F, A+F, A+D+F",
    ),
    busqueda: Optional[str] = Query(None, description="Búsqueda nominal por CI o nombre de estudiante"),
    umbral_nota: float = Query(70.0, ge=0.0, le=100.0),
    umbral_incumplimiento: float = Query(30.0, ge=0.0, le=100.0),
    umbral_cuotas_mora: int = Query(2, ge=1, le=60),
    limit: int = Query(50, ge=1, le=5000, description="Máximo de estudiantes retornados por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación de estudiantes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ROLES_ALERTAS)),
):
    """
    Audita el estado de la matrícula activa mediante la evaluación determinística estricta (IF/THEN)
    sobre las tablas de hechos consolidadas (fact_rendimiento_academico y fact_situacion_financiera),
    aislando cualquier incertidumbre estadística en la toma de decisiones sobre alumnos individuales.
    """
    try:
        clave = ("alertas", periodo, programa, modulo, docente, regla_filtro, busqueda,
                 umbral_nota, umbral_incumplimiento, umbral_cuotas_mora, limit, offset)
        return cache_consultas.obtener(clave, TTL_ALERTAS_SEG, lambda: evaluar_alertas_tempranas_deterministicas(
            db=db,
            periodo=periodo,
            programa=programa,
            modulo=modulo,
            docente=docente,
            regla_filtro=regla_filtro,
            busqueda=busqueda,
            umbral_nota=umbral_nota,
            umbral_incumplimiento=umbral_incumplimiento,
            umbral_cuotas_mora=umbral_cuotas_mora,
            limit=limit,
            offset=offset,
        ))
    except Exception as e:
        logger.error(f"Falla al evaluar alertas tempranas determinísticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al evaluar el motor determinístico de alertas tempranas.",
        )


@router.get(
    "/ficha-estudiante/{id_estudiante}",
    response_model=FichaCruzadaEstudianteResponse,
    summary="Obtener Ficha Cruzada Académico-Financiera del Estudiante",
)
def obtener_ficha_cruzada(
    id_estudiante: int = Path(..., ge=1, description="ID del estudiante en dim_estudiante"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ROLES_ALERTAS)),
):
    """
    Retorna el expediente consolidado académico-financiero y la trazabilidad documental (SHA-256)
    de un estudiante específico para auditoría e intervención oportuna.
    """
    try:
        ficha = obtener_ficha_cruzada_estudiante(db=db, id_estudiante=id_estudiante)
        if not ficha:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró el estudiante con ID {id_estudiante} en el Data Warehouse.",
            )
        return ficha
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Falla al obtener ficha cruzada del estudiante {id_estudiante}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al consultar la ficha cruzada del estudiante.",
        )


@router.get(
    "/resumen-vista",
    summary="Resumen de riesgo estudiantil por gestión desde bi.vw_riesgo_estudiante",
)
def obtener_resumen_riesgo_vista(
    gestion: Optional[int] = Query(None, ge=2000, le=2100, description="Gestión opcional"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ROLES_ALERTAS)),
):
    """Consulta agregada sobre `bi.vw_riesgo_estudiante` (unión académico + financiero por gestión)."""
    try:
        where = "WHERE gestion = :g" if gestion is not None else ""
        params = {"g": gestion} if gestion is not None else {}
        filas = db.execute(
            text(f"""
                SELECT gestion,
                       COUNT(*) AS total_estudiantes,
                       COUNT(*) FILTER (WHERE regla_a_academico = 1) AS regla_academico,
                       COUNT(*) FILTER (WHERE regla_d_desercion = 1) AS regla_desercion,
                       COUNT(*) FILTER (WHERE regla_f_financiero = 1) AS regla_financiero,
                       COUNT(*) FILTER (WHERE k_reglas >= 2) AS criticos,
                       COUNT(*) FILTER (WHERE nivel_prioridad = 'MODERADA') AS moderados,
                       COUNT(*) FILTER (WHERE nivel_prioridad = 'SIN_ALERTA') AS sin_alerta
                FROM bi.vw_riesgo_estudiante
                {where}
                GROUP BY gestion
                ORDER BY gestion DESC
            """),
            params,
        ).mappings().all()
        return {
            "status": "success",
            "fuente": "bi.vw_riesgo_estudiante",
            "gestiones": [dict(f) for f in filas],
        }
    except Exception as e:
        logger.error(f"Falla al consultar bi.vw_riesgo_estudiante: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al consultar el resumen de riesgo por gestión.",
        )
