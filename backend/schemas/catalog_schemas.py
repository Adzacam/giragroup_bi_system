"""
backend/schemas/catalog_schemas.py
-----------------------------------
Esquemas Pydantic v2 para consulta y exploración de dimensiones maestras:
Estudiantes, Docentes y Módulos curriculares.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class EstudianteItem(BaseModel):
    id_estudiante: int
    nombre_completo: str
    codigo_estudiante: Optional[str] = None
    genero: Optional[str] = None
    ciudad: Optional[str] = None
    nivel_academico: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RendimientoResumen(BaseModel):
    modulo: str
    nota_final: Optional[float] = None
    asistencia_pct: Optional[float] = None
    estado_academico: Optional[str] = None


class SituacionFinancieraResumen(BaseModel):
    monto_deuda: Optional[float] = None
    cuotas_impagas: Optional[int] = None
    estado_cartera: Optional[str] = None
    tipo_alerta: Optional[str] = None


class EstudianteDetalleResponse(BaseModel):
    id_estudiante: int
    nombre_completo: str
    codigo_estudiante: Optional[str] = None
    ciudad: Optional[str] = None
    nivel_academico: Optional[str] = None
    historial_academico: List[RendimientoResumen] = []
    situacion_financiera: Optional[SituacionFinancieraResumen] = None  # None para DIRECTOR_ACADEMICO (PoLP)


class EstudiantesListResponse(BaseModel):
    status: str = "success"
    total: int
    limit: int
    offset: int
    data: List[EstudianteItem]


class DocenteItem(BaseModel):
    id_docente: int
    nombre_completo: str
    area_especialidad: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocentesListResponse(BaseModel):
    status: str = "success"
    total: int
    data: List[DocenteItem]


class ModuloItem(BaseModel):
    id_modulo: int
    nombre_modulo: str
    nombre_institucion: str
    programa: Optional[str] = None
    pos_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ModulosListResponse(BaseModel):
    status: str = "success"
    total: int
    data: List[ModuloItem]
