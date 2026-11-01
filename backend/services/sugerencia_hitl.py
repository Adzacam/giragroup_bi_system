"""
backend/services/sugerencia_hitl.py
-----------------------------------
Regla de la bandeja HITL para ofrecer un candidato "con un clic": el candidato debe coincidir con el texto
como nombre completo (token_sort_ratio >= 85). WRatio no basta: puntúa alto coincidencias parciales como
'Maestría en Finanzas' -> 'INDICA QUE SE RETIRO DEL DIPLOMADO…' o 'Diplomado TIC' -> 'DIPLOMADO'.
"""

import re
import unicodedata
from typing import Optional

from rapidfuzz import fuzz

UMBRAL_UN_CLIC = 85.0


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.lower().split())


def similitud_nombre_completo(texto: Optional[str], candidato: Optional[str]) -> float:
    """token_sort_ratio (0-100) entre texto y candidato, sin tildes ni mayúsculas."""
    if not texto or not candidato:
        return 0.0
    return float(fuzz.token_sort_ratio(_normalizar(texto), _normalizar(candidato)))


def es_sugerencia_un_clic(texto: Optional[str], candidato: Optional[str], umbral: float = UMBRAL_UN_CLIC) -> bool:
    """True si el candidato puede aceptarse con un clic (coincidencia de nombre completo >= umbral)."""
    umbral_pct = umbral * 100.0 if umbral <= 1.0 else umbral
    return similitud_nombre_completo(texto, candidato) >= umbral_pct


_RE_NOMBRE_DISCORDANTE = re.compile(r"Nombre:\s*(.+?)\s*(?:\(|$)")


def nombre_extraido(texto_original: Optional[str], linea_origen: Optional[str] = None) -> str:
    """
    Nombre que la plataforma leyó para el caso, para compararlo con el candidato (no la línea completa del acta):
    - línea 'ENCABEZADO: valor | ...' (staging): NOMBRES + APELLIDOS por encabezado;
    - 'CI: … | Nombre: X (Discordante con: Y)' (CI ≠ nombre): X;
    - 'X (Programa entrante: …)' (homonimia): X.
    """
    from services.extraccion_por_encabezado import campos_por_encabezado, estudiante_de_fila

    for texto in (linea_origen, texto_original):
        if texto and "|" in texto and "Nombre:" not in texto:
            est = estudiante_de_fila(campos_por_encabezado([c.strip() for c in texto.split("|")]))
            if est and est.get("valor_extraido"):
                return est["valor_extraido"]
    texto = texto_original or ""
    m = _RE_NOMBRE_DISCORDANTE.search(texto)
    if m:
        return m.group(1).strip()
    return texto.split("(")[0].strip()
