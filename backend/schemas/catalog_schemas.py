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


class InstitucionItem(BaseModel):
    id_institucion: int
    nombre: str
    sigla: Optional[str] = None
    tipo: Optional[str] = "Universidad / Instituto"
    estado: Optional[str] = "Activo"

    model_config = ConfigDict(from_attributes=True)


class InstitucionesListResponse(BaseModel):
    status: str = "success"
    total: int
    data: List[InstitucionItem]


class EstudianteCreate(BaseModel):
    nombre_completo: str
    codigo_estudiante: Optional[str] = None
    ci_documento: Optional[str] = None
    ciudad: Optional[str] = "La Paz"
    nivel_academico: Optional[str] = "Pregrado"


class DocenteCreate(BaseModel):
    nombre_completo: str
    area_especialidad: Optional[str] = "General"


class ModuloCreate(BaseModel):
    nombre_modulo: str
    nombre_institucion: str = "GiraGroup"
    programa: Optional[str] = None
    pos_code: Optional[str] = None


class InstitucionCreate(BaseModel):
    nombre: str
    sigla: Optional[str] = None
    tipo: Optional[str] = "Universidad / Instituto"


class FinancialConceptMatchRequest(BaseModel):
    termino: str
    umbral: Optional[float] = 90.0


class FinancialConceptMatchResponse(BaseModel):
    homologado: bool
    codigo_canonico: Optional[str] = None
    nombre_canonico: Optional[str] = None
    tipo_movimiento: Optional[str] = None
    categoria_contable: Optional[str] = None
    confianza: float
    termino_evaluado: str
    termino_coincidencia: Optional[str] = None
    es_equivalencia_historica: bool
    requiere_revision: bool
    motivo: Optional[str] = None


class FinancialTransactionValidateRequest(BaseModel):
    cuota: Any
    pagado: Any
    saldo: Any
    moneda: Optional[str] = "BOB"
    tolerancia: Optional[float] = 0.05


class FinancialTransactionValidateResponse(BaseModel):
    valido: bool
    cuota: Optional[float] = None
    pagado: Optional[float] = None
    saldo_registrado: Optional[float] = None
    saldo_calculado: Optional[float] = None
    diferencia: Optional[float] = None
    moneda: str = "BOB"
    cuadre_contable: bool
    requiere_revision: bool
    errores: List[str] = []
    advertencias: List[str] = []
    motivo: str


class FinancialGoalValidateRequest(BaseModel):
    meta: Any
    ejecutado: Any
    periodo: Optional[str] = None
    categoria: Optional[str] = None


class FinancialGoalValidateResponse(BaseModel):
    valido: bool
    meta: Optional[float] = None
    ejecutado: Optional[float] = None
    cumplimiento_pct: float = 0.0
    brecha: Optional[float] = None
    periodo: Optional[str] = None
    categoria: Optional[str] = None
    anomalia_detectada: bool = False
    requiere_revision: bool = False
    errores: List[str] = []
    advertencias: List[str] = []
    motivo: str


class StudentIdentityResolveRequest(BaseModel):
    ci: Optional[str] = None
    id_estudiante_codigo: Optional[str] = None
    correo: Optional[str] = None
    nombre: Optional[str] = None
    programa: Optional[str] = None
    periodo: Optional[str] = None


class StudentIdentityResolveResponse(BaseModel):
    resuelto: bool
    id_estudiante: Optional[int] = None
    codigo_estudiante: Optional[str] = None
    nombre_completo: Optional[str] = None
    nivel_resolucion: str
    confianza: float
    fk_estado: str
    requiere_revision: bool
    motivo: str


class CrossSourceCheckResponse(BaseModel):
    id_estudiante: int
    codigo_estudiante: Optional[str] = None
    nombre_completo: str
    tiene_academico: bool
    total_registros_academicos: int
    tiene_financiero: bool
    total_registros_financieros: int
    reconciliado: bool
    estado: str
    alerta: Optional[str] = None
    fragmentacion_detectada: bool


class FinancialRiskEvaluateRequest(BaseModel):
    cuotas_impagas: Optional[int] = 0
    dias_mora: Optional[int] = 0
    saldo: Optional[float] = 0.0
    total_cuotas: Optional[int] = 1
    nota_academica: Optional[float] = None


class FinancialRiskEvaluateResponse(BaseModel):
    estado_cartera: str
    nivel_riesgo: str
    requiere_gestion: bool
    es_riesgo_critico: bool
    es_riesgo_dual: bool
    reglas_activadas: List[str]
    diagnostico: str


class FinancialAnomalyDetectRequest(BaseModel):
    datos: Dict[str, Any]


class FinancialAnomalyDetectResponse(BaseModel):
    total_anomalias: int
    anomalias: List[Dict[str, Any]]
    requiere_revision: bool

