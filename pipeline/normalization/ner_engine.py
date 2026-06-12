"""
ner_engine.py — GIRA-9, GIRA-10
Motor NER basado en BETO (bert-base-spanish-wwm-cased)
para extracción de entidades nombradas en textos académicos.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Ruta del modelo local (relativa al directorio pipeline/semantic/)
_BETO_LOCAL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "semantic", "beto_local"
)
_BETO_HUB_MODEL = "dccuchile/bert-base-spanish-wwm-cased"


class BetoNerEngine:
    """
    Motor de Reconocimiento de Entidades Nombradas (NER) basado en BETO.
    Carga diferida (lazy loading) del modelo para optimizar memoria en reposo.
    """

    def __init__(self, modelo_local: str = _BETO_LOCAL_DIR, batch_size: int = 16):
        self._modelo_local = modelo_local
        self._batch_size = batch_size
        self._pipeline = None

    def _cargar_modelo(self) -> None:
        """Carga diferida: inicializa el pipeline NER solo cuando se necesita."""
        if self._pipeline is not None:
            return

        from transformers import pipeline as hf_pipeline

        # Intentar carga local primero
        modelo_path = self._modelo_local
        if os.path.isdir(modelo_path) and os.listdir(modelo_path):
            logger.info("Cargando modelo BETO desde directorio local: %s", modelo_path)
        else:
            logger.info(
                "Modelo local no encontrado en %s. Descargando desde HuggingFace Hub: %s",
                modelo_path, _BETO_HUB_MODEL
            )
            modelo_path = _BETO_HUB_MODEL

        self._pipeline = hf_pipeline(
            "ner",
            model=modelo_path,
            tokenizer=modelo_path,
            aggregation_strategy="simple",
        )
        logger.info("Pipeline NER inicializado correctamente.")

    def extraer_entidades(self, texto: str) -> dict:
        """
        Extrae entidades nombradas de un texto individual.

        Returns:
            dict con claves:
                - entidades_per: list[str] — nombres de personas detectados
                - entidades_org: list[str] — nombres de organizaciones detectados
                - confianza_ner: float — promedio de certeza de todas las entidades
        """
        self._cargar_modelo()

        if not texto or not texto.strip():
            return {"entidades_per": [], "entidades_org": [], "confianza_ner": 0.0}

        # Truncar a 512 tokens (límite de BETO)
        texto_truncado = texto[:512]
        resultados = self._pipeline(texto_truncado)

        entidades_per = []
        entidades_org = []
        scores = []

        for entidad in resultados:
            grupo = entidad.get("entity_group", "")
            palabra = entidad.get("word", "").strip()
            score = entidad.get("score", 0.0)

            if not palabra:
                continue

            scores.append(score)

            if grupo == "PER":
                entidades_per.append(palabra)
            elif grupo == "ORG":
                entidades_org.append(palabra)

        confianza_ner = sum(scores) / len(scores) if scores else 0.0

        return {
            "entidades_per": entidades_per,
            "entidades_org": entidades_org,
            "confianza_ner": round(confianza_ner, 4),
        }

    def extraer_entidades_lote(self, textos: list[str]) -> list[dict]:
        """
        Procesa un lote de textos, devolviendo una lista de resultados NER
        con la misma estructura que extraer_entidades().
        """
        self._cargar_modelo()

        resultados = []
        for i in range(0, len(textos), self._batch_size):
            lote = textos[i : i + self._batch_size]
            for texto in lote:
                resultados.append(self.extraer_entidades(texto))

        return resultados
