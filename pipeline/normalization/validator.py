"""
validator.py — GIRA-50
Validación estructural simplificada: rangos cronológicos y nulos críticos.
Sin penalizaciones financieras/contables.
"""

import logging

logger = logging.getLogger(__name__)

# Rango estricto de gestiones permitidas
_GESTION_MIN = 2024
_GESTION_MAX = 2026

# Llaves naturales que no deben ser nulas
_LLAVES_NATURALES = ["ci", "codigo_estudiante", "codigo", "nombre_completo"]


def validar_rango_temporal(gestion: int) -> bool:
    """
    Verifica que la gestión se encuentre en el rango estricto 2024-2026.

    Args:
        gestion: Año de gestión del registro.

    Returns:
        True si el rango es válido, False en caso contrario.
    """
    try:
        gestion_int = int(gestion)
    except (TypeError, ValueError):
        return False

    return _GESTION_MIN <= gestion_int <= _GESTION_MAX


def detectar_nulos_criticos(registro: dict) -> list[str]:
    """
    Identifica ausencia de llaves naturales (CI, Código) en un registro.

    Args:
        registro: Diccionario con los campos del registro.

    Returns:
        Lista de nombres de campo que están ausentes o vacíos.
    """
    nulos = []
    for llave in _LLAVES_NATURALES:
        if llave in registro:
            valor = registro[llave]
            if valor is None or (isinstance(valor, str) and not valor.strip()):
                nulos.append(llave)
    return nulos
