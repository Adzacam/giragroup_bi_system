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


def texto_para_indice(linea: str) -> str:
    """Primeras 8 celdas 'COL: valor' de la línea, igual que el texto evaluado por el script del lote."""
    celdas = [c.strip() for c in (linea or "").split("|") if c.strip()]
    return " | ".join(celdas[:MAX_CELDAS_TEXTO])


def clasificar_banda(indice: Optional[float]) -> str:
    if indice is None or indice < UMBRAL_REVISION:
        return BANDA_STAGING
    if indice < UMBRAL_CONSOLIDADO:
        return BANDA_REVISION
    return BANDA_CONSOLIDADO


def _cargar_modelo():
    global _MODELO, _TOKENIZER
    if _MODELO is None:
        from transformers import BertForTokenClassification, BertTokenizerFast
        from pipeline.config import MODELO_BETO_CACHE_DIR

        _TOKENIZER = BertTokenizerFast.from_pretrained(str(MODELO_BETO_CACHE_DIR))
        _MODELO = BertForTokenClassification.from_pretrained(str(MODELO_BETO_CACHE_DIR))
        _MODELO.eval()
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
        with torch.no_grad():
            probs = torch.softmax(modelo(**inputs).logits, dim=-1)

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
