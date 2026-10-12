"""
backend/routers/catalogs.py
----------------------------
Router FastAPI para consulta y exploración de dimensiones del Data Warehouse:
Estudiantes, Docentes y Módulos curriculares.
Aplica el Principio de Mínimo Privilegio (PoLP).
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db, get_catalog_db
from core.security import require_roles
from models.user import User
from services.catalog_service import CatalogService
from services.financial_catalog_service import FinancialCatalogService
from services.financial_validator_service import FinancialTransactionValidator
from services.cross_source_reconciler import IdentityResolutionCascade, CrossSourceReconciler
from services.financial_rules_engine import FinancialRulesEngine
from schemas.catalog_schemas import (
    EstudiantesListResponse,
    EstudianteDetalleResponse,
    DocentesListResponse,
    ModulosListResponse,
    InstitucionesListResponse,
    EstudianteCreate,
    DocenteCreate,
    ModuloCreate,
    InstitucionCreate,
    FinancialConceptMatchRequest,
    FinancialConceptMatchResponse,
    FinancialTransactionValidateRequest,
    FinancialTransactionValidateResponse,
    FinancialGoalValidateRequest,
    FinancialGoalValidateResponse,
    StudentIdentityResolveRequest,
    StudentIdentityResolveResponse,
    CrossSourceCheckResponse,
    FinancialRiskEvaluateRequest,
    FinancialRiskEvaluateResponse,
    FinancialAnomalyDetectRequest,
    FinancialAnomalyDetectResponse
)

router = APIRouter(prefix="/api/v1", tags=["Catálogos Dimensionales"])


@router.get(
    "/estudiantes",
    response_model=EstudiantesListResponse,
    summary="Listar estudiantes registrados en el Data Warehouse"
)
def get_estudiantes(
    q: Optional[str] = Query(None, description="Búsqueda por nombre o CI", max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO", "ADMIN"]))
):
    service = CatalogService(db)
    return service.listar_estudiantes(busqueda=q, limit=limit, offset=offset)


@router.post(
    "/estudiantes",
    summary="Registrar nuevo estudiante en el catálogo maestro"
)
def create_estudiante(
    payload: EstudianteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"]))
):
    service = CatalogService(db)
    est = service.crear_estudiante(payload.model_dump())
    return {"status": "success", "message": "Estudiante creado exitosamente", "data": {"id_estudiante": est.id_estudiante, "nombre_completo": est.nombre_completo}}


@router.delete(
    "/estudiantes/{id_estudiante}",
    summary="Eliminar estudiante del catálogo maestro"
)
def delete_estudiante(
    id_estudiante: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"]))
):
    service = CatalogService(db)
    ok = service.eliminar_registro("estudiante", id_estudiante)
    if not ok:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado.")
    return {"status": "success", "message": "Estudiante eliminado exitosamente"}


@router.get(
    "/estudiantes/{id_estudiante}",
    response_model=EstudianteDetalleResponse,
    summary="Detalle de estudiante con filtrado de campos por Mínimo Privilegio (PoLP)"
)
def get_estudiante_detalle(
    id_estudiante: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO", "ADMIN"]))
):
    service = CatalogService(db)
    detalle = service.detalle_estudiante(id_estudiante, rol_usuario=current_user.role)
    if not detalle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estudiante con ID {id_estudiante} no encontrado."
        )
    return detalle


@router.get(
    "/docentes",
    response_model=DocentesListResponse,
    summary="Listar claustro docente registrado en la dimensión"
)
def get_docentes(
    q: Optional[str] = Query(None, description="Búsqueda por nombre", max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO", "ADMIN"]))
):
    service = CatalogService(db)
    return service.listar_docentes(busqueda=q)


@router.post(
    "/docentes",
    summary="Registrar nuevo docente en el catálogo maestro"
)
def create_docente(
    payload: DocenteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"]))
):
    service = CatalogService(db)
    doc = service.crear_docente(payload.model_dump())
    return {"status": "success", "message": "Docente creado exitosamente", "data": {"id_docente": doc.id_docente, "nombre_completo": doc.nombre_completo}}


@router.delete(
    "/docentes/{id_docente}",
    summary="Eliminar docente del catálogo maestro"
)
def delete_docente(
    id_docente: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"]))
):
    service = CatalogService(db)
    ok = service.eliminar_registro("docente", id_docente)
    if not ok:
        raise HTTPException(status_code=404, detail="Docente no encontrado.")
    return {"status": "success", "message": "Docente eliminado exitosamente"}


@router.get(
    "/modulos",
    response_model=ModulosListResponse,
    summary="Listar módulos curriculares y programas"
)
def get_modulos(
    q: Optional[str] = Query(None, description="Búsqueda por nombre o código POS", max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO", "ADMIN"]))
):
    service = CatalogService(db)
    return service.listar_modulos(busqueda=q)


@router.post(
    "/modulos",
    summary="Registrar nuevo módulo curricular"
)
def create_modulo(
    payload: ModuloCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"]))
):
    service = CatalogService(db)
    mod = service.crear_modulo(payload.model_dump())
    return {"status": "success", "message": "Módulo curricular creado exitosamente", "data": {"id_modulo": mod.id_modulo, "nombre_modulo": mod.nombre_modulo}}


@router.delete(
    "/modulos/{id_modulo}",
    summary="Eliminar módulo curricular"
)
def delete_modulo(
    id_modulo: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"]))
):
    service = CatalogService(db)
    ok = service.eliminar_registro("modulo", id_modulo)
    if not ok:
        raise HTTPException(status_code=404, detail="Módulo no encontrado.")
    return {"status": "success", "message": "Módulo eliminado exitosamente"}


@router.get(
    "/instituciones",
    response_model=InstitucionesListResponse,
    summary="Listar instituciones y sedes aliadas"
)
def get_instituciones(
    q: Optional[str] = Query(None, description="Búsqueda por nombre", max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO", "ADMIN"]))
):
    service = CatalogService(db)
    return service.listar_instituciones(busqueda=q)


# ── Catálogos Maestros Financieros con Soporte Histórico ──────────────

@router.get(
    "/catalogs/financial/concepts",
    summary="Listar catálogo maestro de conceptos financieros y equivalencias históricas"
)
def get_financial_concepts(
    tipo_movimiento: Optional[str] = Query(None, description="Filtrar por INGRESO, EGRESO, AJUSTE, SALDO"),
    catalog_db: Session = Depends(get_catalog_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ANALISTA_FINANCIERO", "ADMIN"]))
):
    """Retorna los conceptos canónicos y sus equivalencias históricas registradas en giragroup_catalog_db."""
    return FinancialCatalogService.listar_conceptos(catalog_db, tipo_movimiento=tipo_movimiento)


@router.post(
    "/catalogs/financial/match",
    response_model=FinancialConceptMatchResponse,
    summary="Homologar término financiero crudo contra catálogo e histórico con política de seguridad"
)
def match_financial_concept(
    payload: FinancialConceptMatchRequest,
    catalog_db: Session = Depends(get_catalog_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ANALISTA_FINANCIERO", "ADMIN"]))
):
    """
    Homologa un término crudo (ej: 'Mensualidad', 'Recargo por Mora', 'Cobro extraordinario convenio X').
    Si el score >= umbral (defecto 90%), homologa automáticamente.
    Si el score < umbral, retorna requiere_revision=True sin contaminar el Data Warehouse.
    """
    resultado = FinancialCatalogService.homologar_concepto(
        termino_crudo=payload.termino,
        db_catalog=catalog_db,
        umbral_confianza=payload.umbral or 90.0
    )
    return resultado


@router.post(
    "/catalogs/financial/validate-transaction",
    response_model=FinancialTransactionValidateResponse,
    summary="Validar consistencia contable: Saldo = Cuota - Pagado con sanitizado de importes"
)
def validate_financial_transaction(
    payload: FinancialTransactionValidateRequest,
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ANALISTA_FINANCIERO", "ADMIN"]))
):
    """
    Valida importes heterogéneos ('1.500 Bs', '500 BOB', '1000') y comprueba el cuadre contable.
    Si hay descuadre, retorna los detalles de la inconsistencia y deriva a revisión.
    """
    return FinancialTransactionValidator.validar_transaccion(
        cuota=payload.cuota,
        pagado=payload.pagado,
        saldo=payload.saldo,
        moneda_raw=payload.moneda or "BOB",
        tolerancia=payload.tolerancia or 0.05
    )


@router.post(
    "/catalogs/financial/validate-goal",
    response_model=FinancialGoalValidateResponse,
    summary="Validar relación Meta vs. Ejecutado y porcentaje de cumplimiento"
)
def validate_financial_goal(
    payload: FinancialGoalValidateRequest,
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ANALISTA_FINANCIERO", "ADMIN"]))
):
    """
    Calcula Cumplimiento = (Ejecutado / Meta) * 100, detecta sobre-ejecución anómala (>250%) o valores inválidos.
    """
    return FinancialTransactionValidator.validar_meta_ejecutado(
        meta=payload.meta,
        ejecutado=payload.ejecutado,
        periodo=payload.periodo,
        categoria=payload.categoria
    )


@router.post(
    "/catalogs/financial/resolve-student",
    response_model=StudentIdentityResolveResponse,
    summary="Resolver identidad del estudiante mediante cascada jerárquica: CI -> ID -> Correo -> Nombre+Prog"
)
def resolve_student_identity(
    payload: StudentIdentityResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ANALISTA_FINANCIERO", "ADMIN"]))
):
    """
    Ejecuta la cascada estricta:
    1. CI exacto
    2. ID o Código estudiante
    3. Correo electrónico
    4. Nombre completo + Programa (Fuzzy RapidFuzz)
    Si no resuelve, retorna fk_estado='C' y requiere_revision=True.
    """
    return IdentityResolutionCascade.resolver_estudiante_cascada(
        db=db,
        ci=payload.ci,
        id_estudiante_codigo=payload.id_estudiante_codigo,
        correo=payload.correo,
        nombre=payload.nombre,
        programa=payload.programa,
        periodo=payload.periodo
    )


@router.get(
    "/catalogs/financial/cross-source-check/{id_estudiante}",
    response_model=CrossSourceCheckResponse,
    summary="Cotejar presencia cruzada de un estudiante: actividad en Moodle/Actas vs. registro en Cobranzas"
)
def check_cross_source_student(
    id_estudiante: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ANALISTA_FINANCIERO", "DIRECTOR_ACADEMICO", "ADMIN"]))
):
    """
    Detecta si un estudiante está en aula virtual Moodle pero no en Cobranzas, o viceversa (fragmentación informacional).
    """
    return CrossSourceReconciler.verificar_presencia_cruzada(db=db, id_estudiante=id_estudiante)


@router.get(
    "/catalogs/financial/cross-source-audit",
    summary="Auditoría consolidada de discrepancias cross-source en el lote de estudiantes"
)
def audit_cross_source_batch(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ANALISTA_FINANCIERO", "DIRECTOR_ACADEMICO", "ADMIN"]))
):
    """
    Retorna métricas ejecutivas de fragmentación y lista de expedientes con discrepancia cross-source.
    """
    return CrossSourceReconciler.auditar_discrepancias_lote(db=db, limite=limit)


@router.post(
    "/catalogs/financial/evaluate-risk",
    response_model=FinancialRiskEvaluateResponse,
    summary="Evaluar reglas determinísticas de riesgo de cartera y alerta dual académico-financiera"
)
def evaluate_financial_risk(
    payload: FinancialRiskEvaluateRequest,
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ANALISTA_FINANCIERO", "DIRECTOR_ACADEMICO", "ADMIN"]))
):
    """
    Aplica reglas determinísticas:
    - >= 2 cuotas impagas o >= 90 días -> Mora Crítica (Riesgo Financiero).
    - 1 cuota impaga y > 15 días -> Mora Preventiva.
    - Cuotas impagas >= 2 y nota <= 70 -> Riesgo Dual (Académico + Financiero).
    """
    return FinancialRulesEngine.evaluar_riesgo_cartera(
        cuotas_impagas=payload.cuotas_impagas or 0,
        dias_mora=payload.dias_mora or 0,
        saldo=payload.saldo or 0.0,
        total_cuotas=payload.total_cuotas or 1,
        nota_academica=payload.nota_academica
    )


@router.post(
    "/catalogs/financial/detect-anomalies",
    response_model=FinancialAnomalyDetectResponse,
    summary="Detección de anomalías transversales (desproporción de escala, sobrepagos atípicos, inconsistencias)"
)
def detect_financial_anomalies(
    payload: FinancialAnomalyDetectRequest,
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ANALISTA_FINANCIERO", "ADMIN"]))
):
    """
    Detecta comportamientos inconsistentes o atípicos:
    - Meta vs Ejecutado > 200% o valores negativos.
    - Sobrepago > cuota * 3 sin cancelación documentada.
    - Descuento superior al costo del programa.
    """
    anomalias = FinancialRulesEngine.detectar_anomalias_financieras(payload.datos)
    return {
        "total_anomalias": len(anomalias),
        "anomalias": anomalias,
        "requiere_revision": len(anomalias) > 0
    }

