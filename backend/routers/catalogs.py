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


def _avisar_cambio_modulo(db, usuario, accion, id_modulo):
    from models.log_pipeline import LogPipelineIngesta
    from services.notification_service import NotificationService
    from services import cache_consultas
    cache_consultas.invalidar()
    try:
        db.add(LogPipelineIngesta(etapa='CATALOGO_MODULO', nivel='INFO', modulo='Catálogo de referencia',
            mensaje=f'{accion} de módulo {id_modulo}.',
            metadata_json={'accion': accion, 'id_modulo': id_modulo, 'usuario': getattr(usuario, 'id', None)}))
        db.commit()
        for rol in ('ADMIN', 'AUDITOR_CALIDAD'):
            NotificationService.create_notification(db=db, title='Catálogo de referencia actualizado',
                message='Se guardó un cambio de módulos. Abre el catálogo para consultarlo.',
                category='DataOps', severity='SUCCESS', role_target=rol, link='/dataops/datos-maestros')
    except Exception:
        db.rollback()
        import logging
        logging.getLogger(__name__).exception('No se pudo registrar el aviso del catálogo')


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
    q: Optional[str] = Query(None, description="Búsqueda por nombre, código POS o programa", max_length=100),
    gestion: Optional[int] = Query(None, ge=2000, le=2100, description="Solo módulos con actividad en esa gestión"),
    pagina: Optional[int] = Query(None, ge=1),
    por_pagina: Optional[int] = Query(None, ge=1, le=100, description="Activa la paginación en el servidor"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO", "ADMIN", "ANALISTA_MARKETING"]))
):
    service = CatalogService(db)
    return service.listar_modulos(busqueda=q, gestion=gestion, pagina=pagina, por_pagina=por_pagina)


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
    _avisar_cambio_modulo(db, current_user, 'Alta', mod.id_modulo)
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
    _avisar_cambio_modulo(db, current_user, 'Baja', id_modulo)
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


@router.get(
    "/catalogs/institutional-summary",
    summary="Resumen del Catálogo Maestro Institucional (giragroup_catalog_db, Cero PII)"
)
def get_institutional_summary(
    catalog_db: Session = Depends(get_catalog_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO", "ADMIN", "COORDINADOR_ACADEMICO", "ANALISTA_DATOS_MARKETING", "ANALISTA_MARKETING"]))
):
    """
    Resumen del Catálogo Maestro leído de giragroup_catalog_db (programas, inversión base, convenios,
    módulos, punto de equilibrio y metas de la última gestión registrada).
    Sin datos en el catálogo devuelve listas vacías; no contiene datos de estudiantes.
    """
    from sqlalchemy import text as _sql

    programas_rows = catalog_db.execute(_sql("""
        SELECT p.id_programa, p.pos_code, p.nombre_programa, p.version, p.inversion_base,
               p.punto_equilibrio, p.estado_programa, e.nombre_escuela, m.nombre_modalidad, t.nombre_tipo,
               COUNT(mo.id_modulo) AS modulos_count,
               (ARRAY_AGG(mo.nombre_modulo ORDER BY mo.nro_modulo)
                  FILTER (WHERE mo.id_modulo IS NOT NULL))[1:3] AS modulos_clave
        FROM cat_programa p
        LEFT JOIN cat_escuela e ON e.id_escuela = p.id_escuela
        LEFT JOIN cat_modalidad m ON m.id_modalidad = p.id_modalidad
        LEFT JOIN cat_tipo_programa t ON t.id_tipo_programa = p.id_tipo_programa
        LEFT JOIN cat_modulo mo ON mo.id_programa = p.id_programa
        GROUP BY p.id_programa, e.nombre_escuela, m.nombre_modalidad, t.nombre_tipo
        ORDER BY p.nombre_programa
    """)).mappings().all()

    programas = [{
        "pos_code": r["pos_code"],
        "nombre": r["nombre_programa"],
        "version": r["version"],
        "tipo": r["nombre_tipo"],
        "arancel_base_bs": float(r["inversion_base"]) if r["inversion_base"] else None,
        "escuela": r["nombre_escuela"],
        "modalidad": r["nombre_modalidad"],
        "modulos_count": int(r["modulos_count"]),
        "punto_equilibrio": r["punto_equilibrio"] or None,
        "estado_programa": r["estado_programa"],
        "modulos_clave": list(r["modulos_clave"] or []),
    } for r in programas_rows]

    meta = catalog_db.execute(_sql("""
        SELECT gestion, SUM(monto_meta_ingreso)::float AS meta_anual_bs
        FROM ref_metas_gestion
        WHERE gestion = (SELECT MAX(gestion) FROM ref_metas_gestion)
        GROUP BY gestion
    """)).mappings().first()

    equilibrios = [p["punto_equilibrio"] for p in programas if p["punto_equilibrio"]]
    return {
        "status": "success",
        "origen": "giragroup_catalog_db",
        "total_programas": len(programas),
        "total_programas_activos": sum(1 for p in programas if "BAJA" not in (p["estado_programa"] or "").upper()),
        "sin_pii": True,
        "contiene_pii": False,
        "programas": programas,
        "modulos_activos_total": sum(p["modulos_count"] for p in programas),
        "convenios_activos_total": catalog_db.execute(_sql("SELECT count(*) FROM cat_institucion_convenio")).scalar(),
        "metas_presupuestarias": {
            "gestion": meta["gestion"] if meta else None,
            "meta_anual_bs": meta["meta_anual_bs"] if meta else None,
            "punto_equilibrio_promedio_alumnos": round(sum(equilibrios) / len(equilibrios)) if equilibrios else None,
        },
    }


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



# ── Combinaciones válidas de estados de acta (hoja CRITERIOS) ─────────────────
from pydantic import BaseModel, Field  # noqa: E402


class CombinacionEstadoIn(BaseModel):
    estado_academico: str = Field(..., max_length=100)
    estado_reprobado: str = Field(..., max_length=100, description="Estado reprobado / tutoría")
    estado_arca: str = Field(..., max_length=100)


def _combinaciones(catalog_db: Session):
    from models.catalogos import CatCombinacionEstado, CatEstadoAcademico, CatEstadoArca, CatEstadoReprobado
    return (
        catalog_db.query(CatCombinacionEstado, CatEstadoAcademico.nombre_estado, CatEstadoReprobado.nombre_detalle,
                         CatEstadoArca.nombre_arca)
        .join(CatEstadoAcademico, CatEstadoAcademico.id_estado_academico == CatCombinacionEstado.id_estado_academico)
        .join(CatEstadoReprobado, CatEstadoReprobado.id_estado_reprobado == CatCombinacionEstado.id_estado_reprobado)
        .join(CatEstadoArca, CatEstadoArca.id_estado_arca == CatCombinacionEstado.id_estado_arca)
    )


@router.get("/catalogs/estados/combinaciones", summary="Combinaciones válidas (académico, reprobado, ARCA)")
def listar_combinaciones_estado(
    catalog_db: Session = Depends(get_catalog_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "DIRECTOR_ACADEMICO", "ADMIN"])),
):
    filas = _combinaciones(catalog_db).order_by("nombre_estado", "nombre_detalle", "nombre_arca").all()
    return {"status": "success", "total": len(filas), "data": [
        {"id_combinacion": c.id_combinacion, "estado_academico": a, "estado_reprobado": r, "estado_arca": e,
         "activo": c.activo}
        for c, a, r, e in filas
    ]}


@router.post("/catalogs/estados/combinaciones", status_code=status.HTTP_201_CREATED,
             summary="Agregar (o reactivar) una combinación válida de estados")
def crear_combinacion_estado(
    payload: CombinacionEstadoIn,
    catalog_db: Session = Depends(get_catalog_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"])),
):
    from models.catalogos import CatCombinacionEstado, CatEstadoAcademico, CatEstadoArca, CatEstadoReprobado
    from pipeline.normalization.quality_rules import canonizar_estado
    from services.catalogo_estados import invalidar_cache

    ids = []
    for valor, modelo, col_id, col_nombre in (
        (payload.estado_academico, CatEstadoAcademico, "id_estado_academico", "nombre_estado"),
        (payload.estado_reprobado, CatEstadoReprobado, "id_estado_reprobado", "nombre_detalle"),
        (payload.estado_arca, CatEstadoArca, "id_estado_arca", "nombre_arca"),
    ):
        registros = catalog_db.query(modelo).all()
        nombre, reconocido = canonizar_estado(valor, tuple(getattr(r, col_nombre) for r in registros))
        if not reconocido or nombre is None:
            raise HTTPException(status_code=422, detail=f"'{valor}' no existe en {modelo.__tablename__}")
        ids.append(next(getattr(r, col_id) for r in registros if getattr(r, col_nombre) == nombre))

    existente = catalog_db.query(CatCombinacionEstado).filter_by(
        id_estado_academico=ids[0], id_estado_reprobado=ids[1], id_estado_arca=ids[2]
    ).first()
    if existente:
        existente.activo = True
        comb = existente
    else:
        comb = CatCombinacionEstado(id_estado_academico=ids[0], id_estado_reprobado=ids[1], id_estado_arca=ids[2])
        catalog_db.add(comb)
    catalog_db.commit()
    invalidar_cache()
    return {"status": "success", "id_combinacion": comb.id_combinacion}


@router.delete("/catalogs/estados/combinaciones/{id_combinacion}",
               summary="Desactivar una combinación (deja de ser válida; no se borra)")
def desactivar_combinacion_estado(
    id_combinacion: int,
    catalog_db: Session = Depends(get_catalog_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"])),
):
    from models.catalogos import CatCombinacionEstado
    from services.catalogo_estados import invalidar_cache

    comb = catalog_db.query(CatCombinacionEstado).get(id_combinacion)
    if not comb:
        raise HTTPException(status_code=404, detail="Combinación no encontrada.")
    comb.activo = False
    catalog_db.commit()
    invalidar_cache()
    return {"status": "success", "id_combinacion": id_combinacion, "activo": False}
