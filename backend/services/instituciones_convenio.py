"""
Nombre canónico de una institución cliente de convenio ('OACHING CONSULTING GROUP S.R.L', ' ECOGUZ').

Orden: (1) coincidencia exacta normalizada con el nombre o una variante de cat_institucion_convenio
(giragroup_catalog_db); (2) RapidFuzz >= 90 % contra esos nombres; (3) RapidFuzz >= 90 % contra las
instituciones ya cargadas en el DW; (4) si hay duda (75 <= score < 90), marca DUDOSA para bandeja;
(5) si es una institución válida nueva, la registra en cat_institucion_convenio (tabla única de verdad).
"""

import os
import re
import time
import unicodedata
from typing import Dict, Iterable, Optional, Tuple

UMBRAL_FUZZY = 90.0
UMBRAL_DUDA = 75.0
_TTL_SEGUNDOS = 300
_RE_SOCIETARIA = re.compile(r"\b(S ?R ?L|LTDA|S ?A|S ?A ?S|SOCIEDAD ANONIMA|SRL)\b")
_cache: Optional[Tuple[float, Dict[str, Tuple[str, int]]]] = None


def invalidar_cache_convenios() -> None:
    global _cache
    _cache = None


def clave_institucion(nombre: Optional[str]) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", nombre or "") if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^A-Z0-9 ]", " ", sin_tildes.upper())
    t = _RE_SOCIETARIA.sub(" ", t)
    return " ".join(t.split())


def _catalogo(db_catalog=None) -> Dict[str, Tuple[str, int]]:
    """clave normalizada (nombre o variante) -> (nombre canónico, id_convenio)."""
    global _cache
    ahora = time.monotonic()
    if db_catalog is None and _cache and ahora - _cache[0] < _TTL_SEGUNDOS:
        return _cache[1]
    mapa: Dict[str, Tuple[str, int]] = {}
    session = db_catalog
    cerrar = False
    if session is None and os.getenv("TESTING") != "true" and os.getenv("APP_ENV") != "test":
        try:
            from core.database import CatalogSessionLocal
            session = CatalogSessionLocal()
            cerrar = True
        except Exception:
            session = None
    if session is not None:
        try:
            from models.catalogos import CatInstitucionConvenio
            for c in session.query(CatInstitucionConvenio).all():
                for forma in [c.nombre_institucion] + (c.variantes_origen or "").split("|"):
                    cl = clave_institucion(forma)
                    if cl:
                        mapa[cl] = (c.nombre_institucion, c.id_convenio)
        except Exception:
            mapa = {}
        finally:
            if cerrar:
                session.close()
    if db_catalog is None:
        _cache = (ahora, mapa)
    return mapa


def _registrar_nueva_o_variante(
    limpio: str,
    id_conv_existente: Optional[int] = None,
    fuente: str = "TECHOS",
    db_catalog=None,
) -> Optional[int]:
    session = db_catalog
    cerrar = False
    if session is None and os.getenv("TESTING") != "true" and os.getenv("APP_ENV") != "test":
        try:
            from core.database import CatalogSessionLocal
            session = CatalogSessionLocal()
            cerrar = True
        except Exception:
            session = None
    if session is None:
        return id_conv_existente
    try:
        from models.catalogos import CatInstitucionConvenio
        if id_conv_existente is not None:
            conv = session.query(CatInstitucionConvenio).filter_by(id_convenio=id_conv_existente).first()
            if conv:
                vars_actuales = [v.strip() for v in (conv.variantes_origen or "").split("|") if v.strip()]
                if limpio not in vars_actuales and limpio.upper() != conv.nombre_institucion.upper():
                    vars_actuales.append(limpio)
                    conv.variantes_origen = " | ".join(vars_actuales)
                    session.commit()
                    invalidar_cache_convenios()
            return id_conv_existente

        # Evitar colisión por nombre exacto (case-insensitive)
        clave = clave_institucion(limpio)
        for c in session.query(CatInstitucionConvenio).all():
            if clave_institucion(c.nombre_institucion) == clave:
                return c.id_convenio
        nuevo = CatInstitucionConvenio(
            nombre_institucion=limpio[:200],
            variantes_origen=limpio[:200],
            fuente_referencia=fuente[:150],
        )
        session.add(nuevo)
        session.commit()
        session.refresh(nuevo)
        invalidar_cache_convenios()
        return nuevo.id_convenio
    except Exception:
        session.rollback()
        return id_conv_existente
    finally:
        if cerrar:
            session.close()


def canonizar_o_registrar_institucion(
    nombre: str,
    existentes: Iterable[str] = (),
    db_catalog=None,
    fuente: str = "TECHOS",
) -> Tuple[str, Optional[int], float, str]:
    """
    Retorna `(nombre_canonico, id_convenio, score, estado)`.
    estado: 'EXACTA' | 'FUZZY_OK' | 'NUEVA_REGISTRADA' | 'DUDOSA' | 'VACIA'
    """
    from rapidfuzz import fuzz, process

    limpio = " ".join((nombre or "").split())
    clave = clave_institucion(limpio)
    if not limpio or not clave or len(clave) <= 2:
        return limpio, None, 0.0, "VACIA"

    catalogo = _catalogo(db_catalog=db_catalog)
    if clave in catalogo:
        canon, id_conv = catalogo[clave]
        return canon, id_conv, 100.0, "EXACTA"

    if catalogo:
        mejor = process.extractOne(clave, list(catalogo.keys()), scorer=fuzz.ratio)
        if mejor:
            score = float(mejor[1])
            canon, id_conv = catalogo[mejor[0]]
            if score >= UMBRAL_FUZZY:
                _registrar_nueva_o_variante(limpio, id_conv_existente=id_conv, fuente=fuente, db_catalog=db_catalog)
                return canon, id_conv, score, "FUZZY_OK"
            if score >= UMBRAL_DUDA:
                return limpio, None, score, "DUDOSA"

    por_clave = {clave_institucion(e): e for e in existentes if e}
    if clave in por_clave:
        id_conv = _registrar_nueva_o_variante(por_clave[clave], fuente=fuente, db_catalog=db_catalog)
        return por_clave[clave], id_conv, 100.0, "NUEVA_REGISTRADA" if id_conv else "EXACTA"
    if por_clave:
        mejor = process.extractOne(clave, list(por_clave.keys()), scorer=fuzz.ratio)
        if mejor:
            score = float(mejor[1])
            if score >= UMBRAL_FUZZY:
                canon = por_clave[mejor[0]]
                id_conv = _registrar_nueva_o_variante(canon, fuente=fuente, db_catalog=db_catalog)
                return canon, id_conv, score, "FUZZY_OK"
            if score >= UMBRAL_DUDA:
                return limpio, None, score, "DUDOSA"

    id_conv = _registrar_nueva_o_variante(limpio, fuente=fuente, db_catalog=db_catalog)
    return limpio, id_conv, 100.0, "NUEVA_REGISTRADA" if id_conv else "EXACTA"


def canonizar_institucion(nombre: str, existentes: Iterable[str] = ()) -> Tuple[str, Optional[int], float]:
    """(nombre canónico, id_convenio del catálogo o None, score 0-100 de la coincidencia)."""
    canon, id_conv, score, _ = canonizar_o_registrar_institucion(nombre, existentes=existentes)
    return canon, id_conv, score
