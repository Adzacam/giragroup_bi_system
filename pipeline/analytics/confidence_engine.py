"""
confidence_engine.py — GIRA-42, GIRA-27
Motor de confianza simplificado: combinación lineal directa
de las certezas NER + similitud fuzzy. Sin matriz ponderada 4D.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Pesos de la combinación lineal
_PESO_NER = 0.60
_PESO_FUZZY = 0.40

# Umbral de corte para revisión humana
_UMBRAL_REVISION = 0.60

# Umbrales para el semáforo del dashboard
_UMBRAL_VERDE = 0.85
_UMBRAL_AMARILLO = 0.60


class ConfidenceEngine:
    """
    Motor de confianza de entrada única.
    Calcula nivel_confianza_ia por registro usando la fórmula:
        nivel_confianza_ia = (confianza_ner * 0.60) + (score_fuzzy_matching * 0.40)
    """

    @staticmethod
    def calcular_confianza_registro(
        confianza_ner: float,
        score_fuzzy_matching: float,
    ) -> dict:
        """
        Calcula el índice de confianza para un registro individual.

        Args:
            confianza_ner: Score promedio del motor NER BETO (0.0 - 1.0).
            score_fuzzy_matching: Distancia fuzzy mínima resuelta (0.0 - 1.0).

        Returns:
            dict con:
                - nivel_confianza_ia: float
                - requiere_revision: bool
        """
        confianza_ner = max(0.0, min(1.0, confianza_ner))
        score_fuzzy_matching = max(0.0, min(1.0, score_fuzzy_matching))

        nivel_confianza_ia = (_PESO_NER * confianza_ner) + (_PESO_FUZZY * score_fuzzy_matching)
        nivel_confianza_ia = round(nivel_confianza_ia, 4)

        requiere_revision = nivel_confianza_ia < _UMBRAL_REVISION

        if requiere_revision:
            logger.info(
                "Registro requiere revisión: confianza=%.4f (NER=%.4f, fuzzy=%.4f)",
                nivel_confianza_ia, confianza_ner, score_fuzzy_matching,
            )

        return {
            "nivel_confianza_ia": nivel_confianza_ia,
            "requiere_revision": requiere_revision,
        }

    @staticmethod
    def calcular_estado_dashboard(registros_confianza: list[float]) -> dict:
        """
        Calcula el índice de confianza global y el estado del dashboard
        para un archivo completo.

        Args:
            registros_confianza: Lista de nivel_confianza_ia individuales.

        Returns:
            dict con:
                - indice_confianza_global: float
                - estado_dashboard: str ("VERDE" | "AMARILLO" | "ROJO")
        """
        if not registros_confianza:
            return {
                "indice_confianza_global": 0.0,
                "estado_dashboard": "ROJO",
            }

        indice_global = round(
            sum(registros_confianza) / len(registros_confianza), 4
        )

        if indice_global >= _UMBRAL_VERDE:
            estado = "VERDE"
        elif indice_global >= _UMBRAL_AMARILLO:
            estado = "AMARILLO"
        else:
            estado = "ROJO"

        return {
            "indice_confianza_global": indice_global,
            "estado_dashboard": estado,
        }
