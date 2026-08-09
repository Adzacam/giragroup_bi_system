"""
error_logger.py — GIRA-43
Componente in-memory simplificado para acumular advertencias por archivo.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ErrorLogger:
    """
    Acumulador de errores/advertencias en memoria durante el procesamiento
    de un archivo de ingesta. Diseñado para ser instanciado por archivo.
    """

    def __init__(self, nombre_archivo: str = ""):
        self._nombre_archivo = nombre_archivo
        self._errores: list[dict] = []

    @property
    def nombre_archivo(self) -> str:
        return self._nombre_archivo

    @property
    def total_errores(self) -> int:
        return len(self._errores)

    def registrar_error(self, fila_id: int, mensaje: str) -> None:
        """
        Registra un error/advertencia para una fila específica.

        Args:
            fila_id: Índice o identificador de la fila con el error.
            mensaje: Descripción del error detectado.
        """
        self._errores.append({
            "fila_id": fila_id,
            "mensaje": mensaje,
            "archivo": self._nombre_archivo,
        })
        logger.warning("[%s] Fila %d: %s", self._nombre_archivo, fila_id, mensaje)

    def exportar_reporte(self) -> list[dict]:
        """
        Exporta la lista completa de errores acumulados.

        Returns:
            Lista de diccionarios con fila_id, mensaje y archivo.
        """
        return list(self._errores)

    def limpiar(self) -> None:
        """Resetea el acumulador de errores."""
        self._errores.clear()
