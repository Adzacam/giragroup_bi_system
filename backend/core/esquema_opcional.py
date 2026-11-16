"""Columnas de la migración 016 (B-9) que pueden faltar en una DW sin migrar.

Se consulta information_schema una sola vez por base (cacheado). Si faltan, la carga omite esos valores y avisa
en el log, en vez de fallar con UndefinedColumn. Los modelos las declaran `deferred`, así los SELECT tampoco las piden.
"""
import logging
from functools import lru_cache

from sqlalchemy import text

logger = logging.getLogger("esquema_opcional")

COLUMNAS_B9 = {
    "stg_entidad_no_resuelta": ("id_homonimo",),
    "log_inconsistencias": ("regla_origen",),
}


@lru_cache(maxsize=None)
def _presentes(engine) -> frozenset:
    """Pares (tabla, columna) de COLUMNAS_B9 que existen en la base del `engine` (una consulta por engine)."""
    esperadas = {(t, c) for t, cs in COLUMNAS_B9.items() for c in cs}
    dialect = getattr(getattr(engine, "dialect", None), "name", "")
    if dialect == "sqlite":
        return frozenset()
    try:
        with engine.connect() as con:
            filas = con.execute(
                text("SELECT table_name, column_name FROM information_schema.columns "
                     "WHERE table_schema = current_schema() AND table_name = ANY(:t)"),
                {"t": list(COLUMNAS_B9)},
            ).fetchall()
    except Exception as ex:
        logger.warning("No se pudo inspeccionar columnas opcionales B-9 (%s); se omiten", ex)
        return frozenset()
    presentes = frozenset(esperadas & {(t, c) for t, c in filas})
    faltan = sorted(f"{t}.{c}" for t, c in esperadas - presentes)
    if faltan:
        logger.warning("DW sin migración 016 (B-9): faltan %s; se carga sin esas columnas", ", ".join(faltan))
    return presentes


def valores_si_existen(db, tabla: str, **valores) -> dict:
    """Devuelve `valores` sin las columnas de `tabla` que la base no tiene (para pasar como **kwargs al modelo)."""
    presentes = _presentes(db.get_bind())
    return {c: v for c, v in valores.items() if (tabla, c) in presentes}
