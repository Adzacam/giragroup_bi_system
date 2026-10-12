from pydantic import BaseModel, Field, AliasChoices
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
    id_lote: Optional[int] = None
    nombre_archivo: str
    tipo_fuente: Optional[str] = None
    tipo_escala: Optional[str] = None
    stages: List[PipelineStageInfo]
    kpis: Dict[str, Any]
    normalization_matrix: List[NormalizationEntry]
    logs: List[PipelineStageLog]
    auditoria: Optional[Dict[str, Any]] = None

class SourceListItem(BaseModel):
    id: int
    id_lote: Optional[int] = None
    name: str
    type: str
    tipo_fuente: Optional[str] = None
    tipo_escala: Optional[str] = None
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
    id_lote: Optional[int] = None
    nombre_archivo: str
    tipo_fuente: Optional[str] = None
    tipo_escala: Optional[str] = None
    registros_detectados: int
    pipeline_result: Optional[PipelineResult] = None

class BatchUploadItem(BaseModel):
    id_documento: Optional[int] = None
    doc_id: Optional[int] = None
    nombre_archivo: str
    tipo_fuente: Optional[str] = None
    tipo_escala: Optional[str] = None
    registros_detectados: int = 0
    status: str
    mensaje: Optional[str] = None
    pipeline_result: Optional[PipelineResult] = None

class BatchUploadResponse(BaseModel):
    status: str
    message: str
    id_lote: Optional[int] = None
    total_archivos: int
    archivos_exitosos: int
    files_processed: int = 0
    archivos_fallidos: int
    total_registros_detectados: int
    resultados: List[BatchUploadItem]
    archivos_procesados: List[Dict[str, Any]] = []
    errores: List[Dict[str, Any]] = []


class RapidFuzzCompareRequest(BaseModel):
    string_a: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("string_a", "str_a"),
    )
    string_b: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("string_b", "str_b"),
    )
    input_text: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("input_text", "query", "texto"),
    )
    catalog_type: Optional[str] = Field(
        default="MODULO",
        validation_alias=AliasChoices("catalog_type", "catalogo", "tipo_catalogo"),
    )
    umbral: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        validation_alias=AliasChoices("umbral", "threshold"),
    )

