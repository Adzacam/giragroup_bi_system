"""
Reglas de estados de acta leídas de giragroup_catalog_db (cat_estado_* y cat_combinacion_estado).

Las combinaciones válidas viven en el catálogo, no en el código: agregar una (por ejemplo, de una hoja
CRITERIOS nueva) se hace en cat_combinacion_estado y la validación la toma en el siguiente refresco.
Si el catálogo no responde o está vacío, se usan las de pipeline.config como respaldo.
"""

import os
import time
from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple

_TTL_SEGUNDOS = 300


@dataclass(frozen=True)
class ReglasEstado:
    academicos: Tuple[str, ...]
    tutoria: Tuple[str, ...]
    arca: Tuple[str, ...]
    combinaciones: FrozenSet[Tuple[str, str, str]]
    origen: str  # "catalogo" | "config"


_cache: Optional[Tuple[float, ReglasEstado]] = None


def _desde_config() -> ReglasEstado:
    from pipeline.config import (
        COMBINACIONES_ESTADO_VALIDAS, ESTADOS_ACADEMICOS_VALIDOS, ESTADOS_ARCA_VALIDOS, ESTADOS_TUTORIA_VALIDOS,
    )
    return ReglasEstado(ESTADOS_ACADEMICOS_VALIDOS, ESTADOS_TUTORIA_VALIDOS, ESTADOS_ARCA_VALIDOS,
                        COMBINACIONES_ESTADO_VALIDAS, "config")


def _desde_catalogo() -> Optional[ReglasEstado]:
    if os.getenv("TESTING") == "true" or os.getenv("APP_ENV") == "test":
        return None
    try:
        from core.database import CatalogSessionLocal
        from models.catalogos import CatCombinacionEstado, CatEstadoAcademico, CatEstadoArca, CatEstadoReprobado
    except Exception:
        return None
    db = CatalogSessionLocal()
    try:
        filas = (
            db.query(CatEstadoAcademico.nombre_estado, CatEstadoReprobado.nombre_detalle, CatEstadoArca.nombre_arca)
            .select_from(CatCombinacionEstado)
            .join(CatEstadoAcademico, CatEstadoAcademico.id_estado_academico == CatCombinacionEstado.id_estado_academico)
            .join(CatEstadoReprobado, CatEstadoReprobado.id_estado_reprobado == CatCombinacionEstado.id_estado_reprobado)
            .join(CatEstadoArca, CatEstadoArca.id_estado_arca == CatCombinacionEstado.id_estado_arca)
            .filter(CatCombinacionEstado.activo.is_(True))
            .all()
        )
        if not filas:
            return None
        return ReglasEstado(
            tuple(n for (n,) in db.query(CatEstadoAcademico.nombre_estado).all()),
            tuple(n for (n,) in db.query(CatEstadoReprobado.nombre_detalle).all()),
            tuple(n for (n,) in db.query(CatEstadoArca.nombre_arca).all()),
            frozenset((a, r, c) for a, r, c in filas),
            "catalogo",
        )
    except Exception:
        return None
    finally:
        db.close()


def reglas_estado() -> ReglasEstado:
    """Reglas vigentes (catálogo, refrescadas cada 5 minutos; config si el catálogo no está disponible)."""
    global _cache
    ahora = time.monotonic()
    if _cache and ahora - _cache[0] < _TTL_SEGUNDOS:
        return _cache[1]
    reglas = _desde_catalogo() or _desde_config()
    _cache = (ahora, reglas)
    return reglas


def invalidar_cache() -> None:
    """Llamar tras modificar cat_combinacion_estado para que la validación lo vea de inmediato."""
    global _cache
    _cache = None
