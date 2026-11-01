"""
backend/services/confianza_service.py
-------------------------------------
Cliente del índice de confianza final (BETO local) que sirve el contenedor giragroup_pipeline
en POST /indice. Lo usan /pipeline/process y /dataops/confirm-dw-insert para decidir la banda
de cada registro (ver pipeline/semantic/indice_confianza.py).
"""

import json
import logging
import os
import urllib.request
from typing import List, Optional

from pipeline.semantic.indice_confianza import (
    BANDA_REVISION,
    clasificar_banda,
    texto_para_indice,
)

logger = logging.getLogger("confianza_service")

BETO_INDICE_URL = os.getenv("BETO_INDICE_URL", "http://pipeline:8006/indice")
LINEAS_POR_PETICION = 256
TIMEOUT_SEG = 300


def obtener_indices(lineas: List[str]) -> List[Optional[float]]:
    """
    Índice final por línea. Si el servicio BETO no responde, devuelve None para esas líneas:
    el llamador las carga con requiere_revision (nunca se inventa un índice).
    """
    indices: List[Optional[float]] = []
    for i in range(0, len(lineas), LINEAS_POR_PETICION):
        lote = [texto_para_indice(l) for l in lineas[i:i + LINEAS_POR_PETICION]]
        try:
            req = urllib.request.Request(
                BETO_INDICE_URL,
                data=json.dumps({"textos": lote}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEG) as resp:
                indices.extend(json.loads(resp.read().decode("utf-8"))["indices"])
        except Exception as e:
            logger.warning(f"Servicio de índice BETO no disponible ({e}); {len(lote)} líneas quedan sin índice.")
            indices.extend([None] * len(lote))
    return indices


def banda_de(indice: Optional[float]) -> str:
    """Banda del registro; sin índice (servicio caído) se trata como revisión, no como consolidado."""
    return clasificar_banda(indice) if indice is not None else BANDA_REVISION
