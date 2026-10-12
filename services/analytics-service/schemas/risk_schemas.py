"""
backend/schemas/risk_schemas.py
-------------------------------
Esquemas Pydantic v2 para endpoint de riesgos cruzados (Sprint 4).
"""

from typing import List
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
