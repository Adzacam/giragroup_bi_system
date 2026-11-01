"""
backend/schemas/kpi_schemas.py
-------------------------------
Esquemas Pydantic v2 para exposición de métricas clave (KPIs) y Alertas
al Cuadro de Mando Integral (CMI) y herramientas de Business Intelligence (Power BI).
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class KpisAcademicos(BaseModel):
    promedio_general_notas: float
    tasa_aprobacion_pct: float
    tasa_reprobacion_pct: float
    estudiantes_en_riesgo_academico: int
    estudiantes_en_riesgo_desercion: int
    total_evaluaciones_registradas: int

    model_config = ConfigDict(from_attributes=True)


class KpisFinancieros(BaseModel):
    monto_total_deuda_bs: float
    estudiantes_con_cuotas_impagas: int
    total_cuotas_impagas: int
    estudiantes_cartera_previsionable: int
    estudiantes_cartera_mora: int
    estudiantes_cartera_vigente: int

    model_config = ConfigDict(from_attributes=True)


class KpisPipelineCalidad(BaseModel):
    total_documentos_procesados: int
    promedio_confianza_ia: float
    registros_requieren_revision: int
    entidades_no_resueltas_staging: int
    tasa_calidad_nlp_pct: float

    model_config = ConfigDict(from_attributes=True)


class KpiGeneralResponse(BaseModel):
    status: str = "success"
    fecha_calculo_iso: str
    academicos: KpisAcademicos
    financieros: KpisFinancieros
    pipeline_calidad: KpisPipelineCalidad


class AlertaItemSchema(BaseModel):
    regla: str
    tipo: str
    severidad: str
    estudiante: str
    codigo_estudiante: Optional[str] = None
    modulo: Optional[str] = None
    metrica_valor: Any
    umbral_disparador: str
    mensaje: str
    role_target: str


class AlertasListResponse(BaseModel):
    status: str = "success"
    total_alertas: int
    criticas: int
    advertencias: int
    data: List[AlertaItemSchema]
