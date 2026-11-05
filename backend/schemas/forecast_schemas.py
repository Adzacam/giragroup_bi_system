"""
backend/schemas/forecast_schemas.py
-----------------------------------
Esquemas Pydantic v2 para validación estricta de contratos de API en Forecasting (Sprint 4).
Garantiza Clean Code, tipado estricto y prevención de fugas de datos (OWASP A04/A08).
"""

from typing import Dict, List, Optional
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
    metodo: Optional[str] = Field(None, description="Algoritmo predictivo (HoltWinters u OLS)")
    origen: Optional[str] = Field(None, description="Origen del dato (database_fact_forecast o on_demand)")
    horizonte_meses: Optional[int] = Field(None, ge=1, le=6, description="Meses proyectados (máximo 6)")
    rmse: Optional[float] = Field(None, ge=0.0, description="Error cuadrático medio")
    aic: Optional[float] = Field(None, description="Criterio de Información de Akaike")
    sin_datos: bool = Field(False, description="True cuando el DW no tiene historia suficiente")
    mensaje: Optional[str] = Field(None, description="Motivo del estado sin datos")
    n_observaciones: Optional[int] = Field(None, ge=0)
    proyecciones: List[ProyeccionItem] = Field(default_factory=list, max_length=6)


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
    model_config = ConfigDict(extra="ignore")

    caso_uso: str
    granularidad: str = Field(..., description="'MENSUAL' o 'ANUAL'")
    metodo: Optional[str] = Field(None, description="'HoltWinters' o 'OLS'")
    tipo_estimacion: Optional[str] = None
    horizonte_meses: Optional[int] = Field(None, ge=1, le=6)
    pendiente_anual_bs: Optional[float] = None
    cagr_historico_pct: Optional[float] = None
    banda_operativa_pct: Optional[float] = None
    banda_min_bs: Optional[float] = None
    banda_max_bs: Optional[float] = None
    nota_metodologica: Optional[str] = None
    rmse: Optional[float] = None
    aic: Optional[float] = None
    sin_datos: bool = Field(False, description="True cuando el DW no tiene historia suficiente")
    mensaje: Optional[str] = Field(None, description="Motivo del estado sin datos")
    n_observaciones: Optional[int] = Field(None, ge=0)
    proyecciones: List[ProyeccionMetaItem] = Field(default_factory=list, max_length=6)


class ForecastMetasResponse(BaseModel):
    """Respuesta estándar para endpoint de metas."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field("success")
    data: ForecastMetasData


class MatrizViabilidadItem(BaseModel):
    """Elemento individual de la Matriz de Viabilidad de Programas (Marketing)."""
    programa: str
    tipo: str
    total_historico: int
    anio_anterior: int
    anio_actual: int
    inscritos_anio_anterior: int
    inscritos_anio_actual: int
    cagr_pct: float
    proyeccion_6m: int
    tendencia_ols: str
    decision_sugerida: str
    badge_color: str
    justificacion: str


class MatrizViabilidadResponse(BaseModel):
    status: str = "success"
    total_programas: int
    data: List[MatrizViabilidadItem]


class AnaliticaMacroResponse(BaseModel):
    status: str = "success"
    fecha_calculo_iso: str
    horizonte_meses: int
    sin_datos: Dict[str, str] = Field(default_factory=dict, description="Motivo por caso sin datos suficientes")
    caso1_demanda_global: Optional[dict] = None
    caso2_demanda_programa: Optional[dict] = None
    caso3_metas_mensuales: Optional[dict] = None
    caso4_metas_anuales: Optional[dict] = None

