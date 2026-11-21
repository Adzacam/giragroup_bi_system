"""
backend/services/auditoria_hitl.py
----------------------------------
Qué guarda `log_auditoria_nlp.correccion_humana` y qué cuenta como corrección humana (ADW-L8, D2).

Una aprobación en bloque «sin cambios» (miles de hechos a la vez) o la revelación autorizada de un dato personal no son
correcciones: no dicen que el modelo se equivocó. Se registran con un marcador propio para que ninguna métrica de
retroalimentación las cuente.
"""
from typing import Optional

APROBACION_BLOQUE = "APROBACION_BLOQUE"
_APROBACION_BLOQUE_ANTIGUA = "Aprobación en bloque sin cambios"   # texto que escribía la versión anterior
_PREFIJO_REVELACION = "REVELAR_"


def es_aprobacion_en_bloque(valor: Optional[str]) -> bool:
    v = (valor or "").strip()
    return v == APROBACION_BLOQUE or v == _APROBACION_BLOQUE_ANTIGUA


def es_revelacion(valor: Optional[str]) -> bool:
    return (valor or "").strip().startswith(_PREFIJO_REVELACION)


def es_correccion_humana(valor: Optional[str]) -> bool:
    """True solo si una persona corrigió o decidió algo sobre el caso (no aprobación en bloque ni revelación de dato)."""
    return not (es_aprobacion_en_bloque(valor) or es_revelacion(valor))


def accion_de_auditoria(valor: Optional[str]) -> str:
    """Texto de la columna «Acción» de la pantalla de Auditoría."""
    if es_aprobacion_en_bloque(valor):
        return "Aprobación en bloque (sin cambios)"
    if es_revelacion(valor):
        return "Revelación autorizada de dato personal"
    return "Resolución HITL: Validación de Entidad"
