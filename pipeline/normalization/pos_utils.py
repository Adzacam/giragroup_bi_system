"""
pos_utils.py — Ingestion Pipeline POS Utilities
Centralizes POS code extraction and normalization to ensure consistency
across document_builder, entity_enricher, and fk_checker.
"""

import re
import unicodedata
from typing import Union

# Regex standard: matches 'POS-' followed by 2 to 6 alphanumeric characters.
# Includes word boundary/start anchor to prevent matching large numbers.
POS_STANDARD_REGEX = re.compile(r"\b(POS-[a-zA-Z0-9]{2,6})\b", re.IGNORECASE)

# Suffix matching for raw digits (2 to 6 digits) optionally followed by a hyphen/CI
POS_NUMERIC_PREFIX_REGEX = re.compile(r"^(\d{2,6})(?:\b|-)")

def extraer_codigo_pos(valor: Union[str, int, float]) -> str:
    """
    Extracts and standardizes the POS code from a string or number.
    
    Examples:
        'Maestría en Finanzas / POS-028' -> 'POS-028'
        'POS-033-5160091' -> 'POS-033'
        '5381' -> 'POS-5381'
        5381 -> 'POS-5381'
        '4403-1114709' -> 'POS-4403'
    """
    if valor is None:
        return ""
    
    # Fast path for empty values
    v_str = str(valor).strip()
    if not v_str or v_str.lower() in ("nan", "none"):
        return ""
        
    # Attempt standard POS-XXXX matching
    match = POS_STANDARD_REGEX.search(v_str)
    if match:
        return match.group(1).upper()
        
    # Attempt pure numeric prefix/digits matching (e.g. 5381 or 4403-1114709)
    match_num = POS_NUMERIC_PREFIX_REGEX.match(v_str)
    if match_num:
        return f"POS-{match_num.group(1)}"
        
    return ""

def normalizar_pos(valor: Union[str, int, float]) -> str:
    """
    Normalizes a POS value to a standardized lowercase representation
    for robust mapping/comparison (e.g., 'pos-5381').
    """
    pos_code = extraer_codigo_pos(valor)
    if not pos_code:
        return ""
        
    t = pos_code.strip().lower()
    # Remove any accent/markings
    t = "".join(
        ch for ch in unicodedata.normalize("NFD", t)
        if unicodedata.category(ch) != "Mn"
    )
    return t
