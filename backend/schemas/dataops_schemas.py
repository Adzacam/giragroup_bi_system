from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class PipelineStageLog(BaseModel):
    id: Optional[int] = None
    etapa: str
    nivel: str # INFO, WARN, ERROR, SUCCESS
    modulo: Optional[str] = None
    mensaje: str
    tiempo_ms: Optional[int] = None
    time: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class NormalizationEntry(BaseModel):
    cabecera_original: str
    cabecera_normalizada: str
    tipo_dato: str
    regla: str
    estado: str = "Completado"

class PipelineStageInfo(BaseModel):
    id: int
    name: str
    time: str
    desc: str
    status: str = "completed"

class PipelineResult(BaseModel):
    status: str
    id_documento: int
    nombre_archivo: str
    tipo_fuente: str
    stages: List[PipelineStageInfo]
    kpis: Dict[str, Any]
    normalization_matrix: List[NormalizationEntry]
    logs: List[PipelineStageLog]
    auditoria: Optional[Dict[str, Any]] = None

class SourceListItem(BaseModel):
    id: int
    name: str
    type: str
    records: int
    date: str
    status: str # completed, warning, error
    sha256: Optional[str] = None

class SourceKpis(BaseModel):
    total_fuentes: int
    registros_detectados: int
    archivos_advertencias: int
    ultima_sincronizacion: str

class SourceListResponse(BaseModel):
    status: str
    kpis: SourceKpis
    data: List[SourceListItem]

class FileUploadResponse(BaseModel):
    status: str
    message: str
    id_documento: int
    nombre_archivo: str
    tipo_fuente: str
    registros_detectados: int
    pipeline_result: Optional[PipelineResult] = None
