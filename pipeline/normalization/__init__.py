# normalization — limpieza, normalización de texto, validación y orquestación
from pipeline.normalization.text_cleaner import limpiar_texto, normalizar_nombre, preparar_payload_beto
from pipeline.normalization.normalizer import (
    asociar_entidad_fuzzy,
    resolver_dimension_estudiante,
    resolver_dimension_docente,
)
from pipeline.normalization.validator import validar_rango_temporal, detectar_nulos_criticos
from pipeline.normalization.error_logger import ErrorLogger
from pipeline.normalization.ner_engine import BetoNerEngine
from pipeline.normalization.pipeline_orchestrator import ejecutar_pipeline_completo
