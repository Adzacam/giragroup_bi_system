"""
backend/services/confianza_service.py
-------------------------------------
Cliente del índice de confianza final (BETO local) que sirve el contenedor giragroup_pipeline
en POST /indice. Lo usan /pipeline/process y /dataops/confirm-dw-insert para decidir la banda
de cada registro (ver pipeline/semantic/indice_confianza.py).
"""

import hashlib
import json
import logging
import os
import urllib.request
from typing import Dict, List, Optional

from pipeline.semantic.indice_confianza import (
    BANDA_REVISION,
    clasificar_banda,
    texto_para_indice,
)

logger = logging.getLogger("confianza_service")

BETO_INDICE_URL = os.getenv("BETO_INDICE_URL", "http://pipeline:8006/indice")
LINEAS_POR_PETICION = 256
TIMEOUT_SEG = 300


MODELO = os.getenv("BETO_MODELO_VERSION", "beto-v1")  # cambiarlo invalida la caché de índices
LOTE_CACHE_SQL = 5000


def _inferir(textos: List[str], al_avanzar=None) -> List[Optional[float]]:
    """Índices del servicio BETO; None para las líneas de una petición que falla (nunca se inventa uno)."""
    indices: List[Optional[float]] = []
    for i in range(0, len(textos), LINEAS_POR_PETICION):
        lote = textos[i:i + LINEAS_POR_PETICION]
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
        if al_avanzar:
            al_avanzar(len(lote))
    return indices


def _leer_cache(hashes: List[str]) -> Dict[str, float]:
    from sqlalchemy import text
    from core.database import SessionLocal

    encontrados: Dict[str, float] = {}
    db = SessionLocal()
    try:
        for i in range(0, len(hashes), LOTE_CACHE_SQL):
            filas = db.execute(text("""
                SELECT hash_texto, indice FROM public.cache_indice_beto
                 WHERE modelo = :m AND hash_texto = ANY(:h)"""), {"m": MODELO, "h": hashes[i:i + LOTE_CACHE_SQL]})
            encontrados.update({h: float(v) for h, v in filas})
    finally:
        db.close()
    return encontrados


def _guardar_cache(nuevos: Dict[str, float]) -> None:
    from sqlalchemy import text
    from core.database import SessionLocal

    if not nuevos:
        return
    db = SessionLocal()
    try:
        pares = list(nuevos.items())
        for i in range(0, len(pares), LOTE_CACHE_SQL):
            parte = pares[i:i + LOTE_CACHE_SQL]
            db.execute(text("""
                INSERT INTO public.cache_indice_beto (hash_texto, modelo, indice)
                SELECT h, :m, v FROM unnest(CAST(:h AS char(64)[]), CAST(:v AS numeric[])) AS t(h, v)
                ON CONFLICT DO NOTHING"""), {"m": MODELO, "h": [h for h, _ in parte], "v": [v for _, v in parte]})
        db.commit()
    finally:
        db.close()


def obtener_indices(lineas: List[str], al_avanzar=None) -> List[Optional[float]]:
    """
    Índice final por línea. Las líneas ya vistas salen de cache_indice_beto (migración 009) y sólo las nuevas
    van al servicio BETO, una vez por texto distinto aunque se repita en el lote. Si el servicio no responde,
    esas líneas quedan en None y el llamador las carga con requiere_revision (nunca se inventa un índice).
    Si la caché no está disponible se infiere todo, como antes.
    """
    textos = [texto_para_indice(l) for l in lineas]
    hashes = [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in textos]
    try:
        en_cache = _leer_cache(sorted(set(hashes)))
    except Exception as e:
        logger.warning(f"Caché de índices BETO no disponible ({e}); se infiere todo.")
        en_cache = None

    if en_cache is None:
        return _inferir(textos, al_avanzar)

    pendientes: Dict[str, str] = {}
    for h, t in zip(hashes, textos):
        if h not in en_cache and h not in pendientes:
            pendientes[h] = t
    if pendientes:
        inferidos = dict(zip(pendientes.keys(), _inferir(list(pendientes.values()), al_avanzar)))
        nuevos = {h: v for h, v in inferidos.items() if v is not None}
        try:
            _guardar_cache(nuevos)
        except Exception as e:
            logger.warning(f"No se pudo guardar la caché de índices BETO ({e}).")
        en_cache.update(nuevos)
    if al_avanzar:
        al_avanzar(len(lineas) - len(pendientes))  # las que salieron de la caché cuentan como hechas
    return [en_cache.get(h) for h in hashes]


def banda_de(indice: Optional[float]) -> str:
    """Banda del registro; sin índice (servicio caído) se trata como revisión, no como consolidado."""
    return clasificar_banda(indice) if indice is not None else BANDA_REVISION
