"""
pipeline/semantic/indice_confianza.py
-------------------------------------
Índice de confianza final por registro (BETO local, pipeline/semantic/beto_local).

Es el cálculo de scripts/reprocesar_lote_1387.py, compartido por ese script y por el
servidor de inferencia (POST /indice), que lo sirve a /pipeline/process y a
/dataops/confirm-dw-insert:

    indice = media de las probabilidades softmax de los tokens que BETO etiqueta distinto de 'O'
    sin entidades detectadas: 0.55 si el texto tiene < 20 caracteres, 0.72 en otro caso

Bandas (umbrales formales del sistema):
    >= 0.85          -> hecho consolidado
    [0.60, 0.85)     -> hecho con requiere_revision = True
    <  0.60          -> stg_entidad_no_resuelta
"""

import re
from typing import List, Optional

UMBRAL_CONSOLIDADO = 0.85
UMBRAL_REVISION = 0.60
MAX_CELDAS_TEXTO = 8
MAX_LENGTH_TOKENS = 128
BATCH_SIZE = 32

BANDA_CONSOLIDADO = "CONSOLIDADO"
BANDA_REVISION = "REVISION"
BANDA_STAGING = "STAGING"

_MODELO = None
_TOKENIZER = None

_RE_SOLO_NUM_O_FECHA = re.compile(
    r"^[\s$€Bs.,:%/\-+0-9]+$",
    re.IGNORECASE,
)
_RE_TIENE_PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{2,}")
_RE_ENC_PRIORITARIO = re.compile(
    r"\b(ESTUDIANTE|ALUMNO|NOMBRE|APELLIDO|PATERNO|MATERNO|DOCENTE|PROFESOR|FACILITADOR|TUTOR|"
    r"PROGRAMA|DIPLOMADO|MAESTR|MODULO|MÓDULO|MATERIA|CURSO|CONCEPTO|OBSERVACI|INSTITUC|CATEGORIA|POS)\b",
    re.IGNORECASE,
)
_RE_ENC_ID_O_NUM = re.compile(
    r"^(N°|Nº|NRO|NO\.?|ID|ITEM|FILA|CORRELATIVO|COD(?:IGO)?|CUOTA|MES|ANO|AÑO|GESTION|GESTIÓN|"
    r"NOTA|CALIF|MONTO|SALDO|DEUDA|PAGADO|IMPORTE|TOTAL|SUBTOTAL|HORAS|HRS|TELEFONO|CELULAR|WHATSAPP|EDAD)$",
    re.IGNORECASE,
)


def _es_celda_textual_relevante(celda: str) -> bool:
    """True si la celda aporta texto semántico (no es puramente numérica, fecha ni ID corto)."""
    hdr, sep, val = celda.partition(":")
    cuerpo = val.strip() if sep else celda.strip()
    if not cuerpo or _RE_SOLO_NUM_O_FECHA.match(cuerpo):
        return False
    if not _RE_TIENE_PALABRA.search(cuerpo):
        return False
    if sep and _RE_ENC_ID_O_NUM.match(hdr.strip()) and len(cuerpo.split()) <= 1:
        return False
    return True


def texto_para_indice(linea: str) -> str:
    """
    F6-3c: Selecciona hasta MAX_CELDAS_TEXTO (8) celdas textuales relevantes filtrando columnas
    puramente numéricas/IDs/fechas antes de truncar a MAX_LENGTH_TOKENS (128). Prioriza celdas
    con encabezados de identidad/entidad y luego otras celdas textuales; solo recurre a celdas
    numéricas si no hay suficientes textuales.
    """
    celdas = [c.strip() for c in (linea or "").split("|") if c.strip()]
    if len(celdas) <= MAX_CELDAS_TEXTO:
        textuales = [c for c in celdas if _es_celda_textual_relevante(c)]
        return " | ".join(textuales if textuales else celdas)

    prioritarias: List[str] = []
    otras_textuales: List[str] = []
    respaldo: List[str] = []
    for c in celdas:
        if _es_celda_textual_relevante(c):
            hdr = c.split(":", 1)[0].strip() if ":" in c else ""
            if hdr and _RE_ENC_PRIORITARIO.search(hdr):
                prioritarias.append(c)
            else:
                otras_textuales.append(c)
        else:
            respaldo.append(c)

    seleccionadas = (prioritarias + otras_textuales)[:MAX_CELDAS_TEXTO]
    if not seleccionadas:
        seleccionadas = respaldo[:MAX_CELDAS_TEXTO]
    return " | ".join(seleccionadas)


def clasificar_banda(indice: Optional[float]) -> str:
    if indice is None or indice < UMBRAL_REVISION:
        return BANDA_STAGING
    if indice < UMBRAL_CONSOLIDADO:
        return BANDA_REVISION
    return BANDA_CONSOLIDADO


def cuantizar_int8(modelo):
    """Cuantización dinámica int8 de las capas Linear (solo CPU). Se activa con BETO_INT8=1; sin la variable devuelve el modelo tal cual."""
    import os
    if os.getenv("BETO_INT8") != "1":
        return modelo
    import torch
    return torch.quantization.quantize_dynamic(modelo, {torch.nn.Linear}, dtype=torch.qint8)


def _cargar_modelo():
    global _MODELO, _TOKENIZER
    if _MODELO is None:
        try:
            from pipeline.semantic.inference_server import get_engine_and_tokenizer
            engine, tok = get_engine_and_tokenizer()
            if engine is not None and getattr(engine, "_nlp_pipeline", None) is not None:
                _MODELO = cuantizar_int8(engine._nlp_pipeline.model)
                _TOKENIZER = tok or engine._nlp_pipeline.tokenizer
                return _MODELO, _TOKENIZER
        except Exception:
            pass
        from transformers import BertForTokenClassification, BertTokenizerFast
        from pipeline.config import MODELO_BETO_CACHE_DIR
        from pipeline.semantic.ner_engine import configurar_hilos_torch

        configurar_hilos_torch()

        _TOKENIZER = BertTokenizerFast.from_pretrained(str(MODELO_BETO_CACHE_DIR))
        _MODELO = BertForTokenClassification.from_pretrained(str(MODELO_BETO_CACHE_DIR))
        _MODELO.eval()
        _MODELO = cuantizar_int8(_MODELO)
        import torch
        if torch.cuda.is_available():  # con docker-compose.gpu.yml: ~4x más rápido, mismo resultado
            _MODELO.to("cuda")
    return _MODELO, _TOKENIZER


def calcular_indices(textos: List[str]) -> List[float]:
    """Índice final por texto, en el mismo orden de entrada."""
    import numpy as np
    import torch

    modelo, tokenizer = _cargar_modelo()
    id2label = modelo.config.id2label
    especiales = (tokenizer.cls_token_id, tokenizer.sep_token_id, tokenizer.pad_token_id)
    indices: List[float] = []

    for i in range(0, len(textos), BATCH_SIZE):
        lote = textos[i:i + BATCH_SIZE]
        inputs = tokenizer(lote, return_tensors="pt", padding=True, truncation=True, max_length=MAX_LENGTH_TOKENS)
        with torch.inference_mode():
            en_dispositivo = {k: v.to(modelo.device) for k, v in inputs.items()}
            probs = torch.softmax(modelo(**en_dispositivo).logits, dim=-1).cpu()

        for b_idx, texto in enumerate(lote):
            p_matrix = probs[b_idx]
            pred_ids = torch.argmax(p_matrix, dim=-1)
            confianzas = [
                float(p_matrix[t_idx, pid].item())
                for t_idx, (tid, pid) in enumerate(zip(inputs["input_ids"][b_idx], pred_ids))
                if tid not in especiales and id2label.get(int(pid), "O") != "O"
            ]
            if confianzas:
                indices.append(round(float(np.mean(confianzas)), 4))
            else:
                indices.append(0.55 if len(texto) < 20 else 0.72)
    return indices
