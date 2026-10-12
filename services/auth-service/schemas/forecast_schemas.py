"""
backend/schemas/forecast_schemas.py
-----------------------------------
Esquemas Pydantic v2 para validación estricta de contratos de API en Forecasting (Sprint 4).
Garantiza Clean Code, tipado estricto y prevención de fugas de datos (OWASP A04/A08).
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ProyeccionItem(BaseModel):
    """Contrato de cada punto temporal proyectado."""
    model_config = ConfigDict(extra="forbid")

    periodo: str = Field(..., description="Periodo en formato YYYY-MM o YYYY", pattern=r"^\d{4}(-\d{2})?$")
    valor_forecast: float = Field(..., ge=0.0, description="Monto proyectado (>= 0)")
    ic_lower: Optional[float] = Field(None, ge=0.0, description="Límite inferior IC 95% (>= 0)")
    ic_upper: Optional[float] = Field(None, ge=0.0, description="Límite superior IC 95% (>= 0)")


class ForecastAlumnosData(BaseModel):
    """Cuerpo de datos para la proyección de alumnos."""
    model_config = ConfigDict(extra="forbid")

    caso_uso: str = Field(..., description="Identificador canónico del caso de uso")
    tipo_solicitado: str = Field(..., description="Tipo de programa solicitado")
    metodo: str = Field(..., description="Algoritmo predictivo (HoltWinters u OLS)")
    origen: Optional[str] = Field(None, description="Origen del dato (database_fact_forecast o on_demand)")
    horizonte_meses: int = Field(..., ge=1, le=6, description="Meses proyectados (máximo 6)")
    rmse: Optional[float] = Field(None, ge=0.0, description="Error cuadrático medio")
    aic: Optional[float] = Field(None, description="Criterio de Información de Akaike")
    proyecciones: List[ProyeccionItem] = Field(..., min_length=1, max_length=6)


class ForecastAlumnosResponse(BaseModel):
    """Respuesta estándar para endpoint de proyección de alumnos."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field("success", description="Estado de la respuesta")
    data: ForecastAlumnosData


class ProyeccionMetaItem(BaseModel):
    """Punto de proyección para metas financieras."""
    model_config = ConfigDict(extra="forbid")

    periodo: str = Field(..., description="Periodo proyectado (YYYY-MM o YYYY)")
    monto_proyectado_bs: float = Field(..., ge=0.0, description="Recaudación proyectada en Bs.")
    ic_lower: Optional[float] = Field(None, ge=0.0)
    ic_upper: Optional[float] = Field(None, ge=0.0)


class ForecastMetasData(BaseModel):
    """Cuerpo de datos para proyección de metas financieras."""
    model_config = ConfigDict(extra="forbid")

    caso_uso: str
    granularidad: str = Field(..., description="'MENSUAL' o 'ANUAL'")
    metodo: str = Field(..., description="'HoltWinters' o 'OLS'")
    tipo_estimacion: Optional[str] = None
    horizonte_meses: Optional[int] = Field(None, ge=1, le=6)
    pendiente_anual_bs: Optional[float] = None
    cagr_historico_pct: Optional[float] = None
    nota_metodologica: Optional[str] = None
    rmse: Optional[float] = None
    aic: Optional[float] = None
    proyecciones: List[ProyeccionMetaItem] = Field(..., min_length=1, max_length=6)


class ForecastMetasResponse(BaseModel):
    """Respuesta estándar para endpoint de metas."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field("success")
    data: ForecastMetasData
