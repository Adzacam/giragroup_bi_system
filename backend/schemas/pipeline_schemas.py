"""
backend/schemas/pipeline_schemas.py
------------------------------------
Esquemas Pydantic v2 para el endpoint orquestador del pipeline completo de datos
(Ingesta -> PLN/BETO -> Normalización/Calidad -> Carga DW).
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class PipelineExecutionResponse(BaseModel):
    status: str
    id_documento: Optional[int] = None
    nombre_archivo: str
    total_bloques_detectados: int
    total_filas_procesadas: int
    total_entidades_extraidas: int
    hechos_cargados_dw: int
    entidades_derivadas_staging: int
    nivel_confianza_promedio: float
    requiere_revision_humana: bool
    tiempo_total_ms: float
    detalles_carga: List[Dict[str, Any]] = []
