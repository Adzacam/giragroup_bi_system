"""
Validación de nombres de módulo antes de resolver o crear en dim_modulo (CAT-L1).

Las listas de centinelas, prefijos de título y profesiones/ocupaciones se leen desde
`cat_etiqueta_clasificacion` (`categoria = 'MODULO_RECHAZO'`) en `giragroup_catalog_db`,
no en el código.
"""

from __future__ import annotations

import os
import re
import time
import unicodedata
from typing import Dict, Iterable, Optional, Set, Tuple

_TTL_SEGUNDOS = 300
_cache_reglas: Optional[Tuple[float, Dict[str, Set[str]]]] = None

_RE_NUMERO = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")
_RE_FECHA = re.compile(
    r"^(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?)$"
)


def _normalizar(texto: Optional[str]) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin_tildes.upper().split())


def invalidar_cache_modulo_validador() -> None:
    global _cache_reglas
    _cache_reglas = None


def _cargar_reglas_catalogo(db_catalog=None) -> Dict[str, Set[str]]:
    global _cache_reglas
    ahora = time.monotonic()
    if db_catalog is None and _cache_reglas and ahora - _cache_reglas[0] < _TTL_SEGUNDOS:
        return _cache_reglas[1]

    reglas: Dict[str, Set[str]] = {
        "CENTINELA": set(),
        "PREFIJO_TITULO": set(),
        "PROFESION_OCUPACION": set(),
    }

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
            from models.catalogos import CatEtiquetaClasificacion
            rows = (
                session.query(CatEtiquetaClasificacion)
                .filter(CatEtiquetaClasificacion.categoria == "MODULO_RECHAZO")
                .all()
            )
            for r in rows:
                sub = (r.subtipo or "PROFESION_OCUPACION").upper()
                norm = _normalizar(r.palabra_clave)
                if not norm:
                    continue
                # Preservar el espacio final en prefijos como 'LIC ' o 'ING '
                if sub == "PREFIJO_TITULO" and (r.palabra_clave or "").endswith(" "):
                    norm = norm + " "
                reglas.setdefault(sub, set()).add(norm)
        except Exception:
            pass
        finally:
            if cerrar:
                session.close()

    if db_catalog is None:
        _cache_reglas = (ahora, reglas)
    return reglas


def validar_nombre_modulo(
    nombre: Optional[str],
    reglas_override: Optional[Dict[str, Iterable[str]]] = None,
    db_catalog=None,
) -> Tuple[bool, Optional[str]]:
    """
    Evalúa si un texto puede representar un módulo académico/institucional.
    Retorna `(True, None)` si es válido, o `(False, motivo)` si debe rechazarse.
    """
    limpio = " ".join((nombre or "").split())
    if not limpio:
        return False, "VACIO"
    if len(limpio) <= 3:
        return False, "MUY_CORTO"
    if not any(c.isalnum() for c in limpio):
        return False, "SIN_ALFANUMERICOS"
    if "@" in limpio:
        return False, "CORREO"
    if _RE_NUMERO.match(limpio):
        return False, "NUMERO"
    if _RE_FECHA.match(limpio):
        return False, "FECHA"

    if reglas_override is not None:
        reglas = {
            k: {
                (_normalizar(v) + " " if k == "PREFIJO_TITULO" and str(v).endswith(" ") else _normalizar(v))
                for v in vals
                if _normalizar(v)
            }
            for k, vals in reglas_override.items()
        }
    else:
        reglas = _cargar_reglas_catalogo(db_catalog=db_catalog)

    norm = _normalizar(limpio)
    if norm in reglas.get("CENTINELA", set()):
        return False, "CENTINELA"
    if norm in reglas.get("PROFESION_OCUPACION", set()):
        return False, "PROFESION_OCUPACION"
    for pref in reglas.get("PREFIJO_TITULO", set()):
        if norm == pref.strip() or norm.startswith(pref):
            return False, "PREFIJO_TITULO"

    return True, None


def es_nombre_modulo_valido(
    nombre: Optional[str],
    reglas_override: Optional[Dict[str, Iterable[str]]] = None,
    db_catalog=None,
) -> bool:
    ok, _ = validar_nombre_modulo(nombre, reglas_override=reglas_override, db_catalog=db_catalog)
    return ok
