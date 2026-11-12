"""Configuración y modelos de solicitud compartidos por los pasos de DataOps."""
from pydantic import BaseModel, Field
from typing import List, Optional, Union
from sqlalchemy import text


try:
    from pipeline.config import (
        COMPUERTA_LECTURA_MODELO,
        COMPUERTA_LECTURA_MODELO_PCT,
        UMBRAL_INDICE_REGISTRO,
        UMBRAL_INDICE_REGISTRO_DEC,
        TOPE_INDICE_BONIFICADO,
        TOPE_INDICE_BONIFICADO_DEC,
        NOTA_APROBACION,
    )
except ImportError:
    COMPUERTA_LECTURA_MODELO = 0.70
    COMPUERTA_LECTURA_MODELO_PCT = 70
    UMBRAL_INDICE_REGISTRO = 85
    UMBRAL_INDICE_REGISTRO_DEC = 0.85
    NOTA_APROBACION = 70.0
    TOPE_INDICE_BONIFICADO = 99
    TOPE_INDICE_BONIFICADO_DEC = 0.99


class DeleteBatchRequest(BaseModel):
    ids: List[int]


class BetoInferRequest(BaseModel):
    text: str
    threshold: Optional[float] = UMBRAL_INDICE_REGISTRO_DEC


class ConfirmDwInsertRequest(BaseModel):
    record_ids: Optional[List[int]] = None
    id_lote: Optional[int] = None
    doc_id: Optional[int] = None
    id_documento: Optional[int] = None
    resolved_item_id: Optional[Union[int, str]] = None
    motivo: Optional[str] = None
    accion: Optional[str] = None
    texto_editado: Optional[str] = None
    threshold: Optional[float] = UMBRAL_INDICE_REGISTRO_DEC
    # Lotes grandes: la consolidación corre en segundo plano y la SPA sigue su avance (GET /tareas/{id})
    en_segundo_plano: bool = False


class BatchResolveRequest(BaseModel):
    item_ids: List[str]
    accion: Optional[str] = "CREAR_O_VINCULAR"
    ci_corregida: Optional[str] = None
    estudiante_resuelto: Optional[str] = None
    email: Optional[str] = None
    modulo_resuelto: Optional[str] = None
    nota_final: Optional[float] = None
    monto_deuda: Optional[float] = None
    monto_pagado: Optional[float] = None
    cuotas_impagas: Optional[int] = None
    concepto: Optional[str] = None


class AprobarGrupoRequest(BaseModel):
    clave: str
    doc_id: Optional[int] = None
    doc_ids: Optional[List[int]] = None  # alcance: solo los casos de estos documentos (p. ej. los del ciclo)
    estudiante_resuelto: Optional[str] = None
    accion: Optional[str] = None  # APROBAR (por defecto) o MAPEAR_ESTADO (grupos con estado fuera de catálogo / combinación no admitida)
    canonico: Optional[str] = None  # estado canónico al que se reescribe el valor fuera de catálogo (MAPEAR_ESTADO)
    mes: Optional[int] = Field(None, ge=1, le=12)
    gestion: Optional[int] = Field(None, ge=2000, le=2100)


class AprobacionEnBloqueRequest(BaseModel):
    id_lote: Optional[str] = None
    doc_id: Optional[int] = None
    confirmar: bool = False
