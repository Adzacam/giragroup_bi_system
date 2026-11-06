"""
Nombre canónico de una institución cliente de convenio ('OACHING CONSULTING GROUP S.R.L', ' ECOGUZ').

Orden: (1) coincidencia exacta normalizada con el nombre o una variante de cat_institucion_convenio
(giragroup_catalog_db); (2) RapidFuzz contra esos nombres; (3) RapidFuzz contra las instituciones ya
cargadas en el DW; (4) el nombre limpio tal cual. Normalizar quita tildes, puntuación, espacios sobrantes y
la forma societaria (S.R.L., LTDA, S.A.), que no distinguen a una institución de otra.
"""

import os
import re
import time
import unicodedata
from typing import Dict, Iterable, Optional, Tuple

UMBRAL_FUZZY = 90.0
_TTL_SEGUNDOS = 300
_RE_SOCIETARIA = re.compile(r"\b(S ?R ?L|LTDA|S ?A|S ?A ?S|SOCIEDAD ANONIMA|SRL)\b")
_cache: Optional[Tuple[float, Dict[str, Tuple[str, int]]]] = None


def clave_institucion(nombre: Optional[str]) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", nombre or "") if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^A-Z0-9 ]", " ", sin_tildes.upper())
    t = _RE_SOCIETARIA.sub(" ", t)
    return " ".join(t.split())


def _catalogo() -> Dict[str, Tuple[str, int]]:
    """clave normalizada (nombre o variante) -> (nombre canónico, id_convenio)."""
    global _cache
    ahora = time.monotonic()
    if _cache and ahora - _cache[0] < _TTL_SEGUNDOS:
        return _cache[1]
    mapa: Dict[str, Tuple[str, int]] = {}
    if os.getenv("TESTING") != "true" and os.getenv("APP_ENV") != "test":
        try:
            from core.database import CatalogSessionLocal
            from models.catalogos import CatInstitucionConvenio
            db = CatalogSessionLocal()
            try:
                for c in db.query(CatInstitucionConvenio).all():
                    for forma in [c.nombre_institucion] + (c.variantes_origen or "").split("|"):
                        if clave_institucion(forma):
                            mapa[clave_institucion(forma)] = (c.nombre_institucion, c.id_convenio)
            finally:
                db.close()
        except Exception:
            mapa = {}
    _cache = (ahora, mapa)
    return mapa


def canonizar_institucion(nombre: str, existentes: Iterable[str] = ()) -> Tuple[str, Optional[int], float]:
    """(nombre canónico, id_convenio del catálogo o None, score 0-100 de la coincidencia)."""
    from rapidfuzz import fuzz, process

    limpio = " ".join((nombre or "").split())
    clave = clave_institucion(limpio)
    catalogo = _catalogo()
    if clave in catalogo:
        canon, id_conv = catalogo[clave]
        return canon, id_conv, 100.0
    if catalogo:
        mejor = process.extractOne(clave, list(catalogo.keys()), scorer=fuzz.ratio)
        if mejor and mejor[1] >= UMBRAL_FUZZY:
            canon, id_conv = catalogo[mejor[0]]
            return canon, id_conv, float(mejor[1])
    por_clave = {clave_institucion(e): e for e in existentes if e}
    if clave in por_clave:
        return por_clave[clave], None, 100.0
    if por_clave:
        mejor = process.extractOne(clave, list(por_clave.keys()), scorer=fuzz.ratio)
        if mejor and mejor[1] >= UMBRAL_FUZZY:
            return por_clave[mejor[0]], None, float(mejor[1])
    return limpio, None, 100.0
