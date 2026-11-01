"""
backend/schemas/risk_schemas.py
-------------------------------
Esquemas Pydantic v2 para endpoint de riesgos cruzados y Vista 3:
Monitoreo de Reglas de Umbral y Alertas Tempranas (IF/THEN determinístico).
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class RendimientoInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nota_actual: float = Field(..., ge=0.0, le=100.0)
    estado_academico: str


class FinanzasInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cuotas_mora: int = Field(..., ge=0)
    deuda_total: float = Field(..., ge=0.0)
    estado_cartera: str


class AlertaCruzadaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estudiante: str
    codigo: str
    rendimiento: RendimientoInfo
    finanzas: FinanzasInfo
    nivel_riesgo_global: str


class RiesgoCruzadoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = "success"
    total_casos_criticos: int = Field(..., ge=0)
    data: List[AlertaCruzadaItem]


# ─── Esquemas Vista 3: Monitoreo de Reglas de Umbral y Alertas Tempranas ───


class TarjetaReglaKpi(BaseModel):
    codigo: str
    titulo: str
    regla_texto: str
    severidad: str  # "ROJO" | "AMBAR" | "CRITICO"
    total_alumnos: int = 0
    porcentaje_matricula: float = 0.0
    monto_mora_bs: Optional[float] = None
    subtitulo_secundario: str


class MatrizInterseccionItem(BaseModel):
    codigo: str  # "A+D", "D+F", "A+F", "A+D+F"
    etiqueta: str
    total_alumnos: int = 0


class TopProgramaAfectadoItem(BaseModel):
    programa: str
    codigo_programa: str
    total_afectados: int = 0


class EstudianteAlertaNominalItem(BaseModel):
    id_estudiante: int
    ci: str
    codigo_estudiante: Optional[str] = None
    nombre_completo: str
    programa: str
    modulo: str
    docente: str
    periodo: str
    promedio_notas: Optional[float] = None
    incumplimiento_pct: float = 0.0
    asistencia_pct: Optional[float] = None
    cuotas_mora: int = 0
    deuda_mora_bs: float = 0.0
    regla_academico: bool = False
    regla_desercion: bool = False
    regla_financiero: bool = False
    tag: str  # "A", "D", "F", "A+D", "A+F", "D+F", "A+D+F"
    cantidad_reglas: int = 1
    prioridad: str  # "CRITICA" | "ALTA" | "MEDIA"


class FiltrosDisponiblesAlertas(BaseModel):
    periodos: List[str] = []
    programas: List[str] = []
    modulos: List[str] = []
    docentes: List[str] = []


class AlertasTempranasResponse(BaseModel):
    status: str = "success"
    motor_reglas: str = "DETERMINISTICO_IF_THEN_ESTRICTO"
    total_matricula_activa: int = 0
    tarjetas: Dict[str, TarjetaReglaKpi]
    matriz_interseccion: List[MatrizInterseccionItem]
    top_programas: List[TopProgramaAfectadoItem]
    filtros_disponibles: FiltrosDisponiblesAlertas
    total_estudiantes_filtrados: int = 0
    estudiantes: List[EstudianteAlertaNominalItem]


class HistorialAcademicoItem(BaseModel):
    id_hecho_aca: int
    modulo: str
    programa: str
    docente: str
    periodo: str
    nota_final: float
    asistencia_pct: Optional[float] = None
    incumplimiento_pct: float = 0.0
    estado_academico: str
    regla_disparada: Optional[str] = None
    origen_archivo: Optional[str] = None
    hash_sha256: Optional[str] = None


class HistorialFinancieroItem(BaseModel):
    id_hecho_fin: int
    concepto: str
    modulo: Optional[str] = None
    periodo: str
    monto_pagado: float
    monto_deuda: float
    cuotas_impagas: int
    estado_cartera: str
    fecha_registro: Optional[str] = None
    origen_archivo: Optional[str] = None
    hash_sha256: Optional[str] = None


class FichaCruzadaEstudianteResponse(BaseModel):
    status: str = "success"
    id_estudiante: int
    nombre_completo: str
    ci: str
    codigo_estudiante: Optional[str] = None
    programa_origen: Optional[str] = None
    ciudad: Optional[str] = None
    resumen_reglas: Dict[str, Any]
    historial_academico: List[HistorialAcademicoItem]
    historial_financiero: List[HistorialFinancieroItem]

