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

from core.database import get_db
from core.security import require_roles
from models.user import User
from services.catalog_service import CatalogService
from schemas.catalog_schemas import (
    EstudiantesListResponse,
    EstudianteDetalleResponse,
    DocentesListResponse,
    ModulosListResponse
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
    current_user: User = Depends(require_roles(["DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO", "ADMIN"]))
):
    service = CatalogService(db)
    return service.listar_estudiantes(busqueda=q, limit=limit, offset=offset)


@router.get(
    "/estudiantes/{id_estudiante}",
    response_model=EstudianteDetalleResponse,
    summary="Detalle de estudiante con filtrado de campos por Mínimo Privilegio (PoLP)"
)
def get_estudiante_detalle(
    id_estudiante: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO", "ADMIN"]))
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
    current_user: User = Depends(require_roles(["DIRECTOR_ACADEMICO", "ADMIN"]))
):
    service = CatalogService(db)
    return service.listar_docentes(busqueda=q)


@router.get(
    "/modulos",
    response_model=ModulosListResponse,
    summary="Listar módulos curriculares y programas"
)
def get_modulos(
    q: Optional[str] = Query(None, description="Búsqueda por nombre o código POS", max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["DIRECTOR_ACADEMICO", "ADMIN"]))
):
    service = CatalogService(db)
    return service.listar_modulos(busqueda=q)
