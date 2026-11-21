"""
backend/services/cmi_valores.py
-------------------------------
Lector único de los valores del CMI por gestión (ADW-L5, hallazgo B3).

El CMI calcula sus 23 KPI en las vistas `bi.vw_cmi_valores` / `bi.vw_cmi_scorecard`. Las pantallas de módulo (académico,
financiero, metas) usaban `KPIService`, que recalculaba en Python sobre TODAS las gestiones y con definiciones propias,
así que una misma cifra podía contradecir al CMI. Ahora `KPIService` toma de aquí las cifras que el CMI también publica.

Sin las vistas `bi` (SQLite de pruebas o una base sin migrar) devuelve vacío y el servicio conserva su cálculo local; el
resultado lo declara en `fuente`.
"""
import logging
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger("cmi_valores")

FUENTE_CMI = "bi.vw_cmi_valores"
FUENTE_LOCAL = "calculo_local (sin vistas bi)"


def gestiones(db: Session) -> List[int]:
    try:
        return [int(r[0]) for r in db.execute(text("SELECT gestion FROM bi.vw_cmi_gestiones ORDER BY gestion"))]
    except SQLAlchemyError:
        db.rollback()
        return []


def gestion_vigente(db: Session, gestion: Optional[int] = None) -> Optional[int]:
    """La gestión pedida si el CMI la tiene; si no, la última del CMI (la misma que abre el scorecard). None sin vistas."""
    gs = gestiones(db)
    if not gs:
        return None
    return gestion if gestion in gs else gs[-1]


def valores(db: Session, gestion: Optional[int]) -> Dict[str, Optional[float]]:
    """{KPI-xx: valor} de la gestión; un KPI sin dato vale None. Vacío si no hay vistas bi o gestión."""
    if gestion is None:
        return {}
    try:
        filas = db.execute(text("SELECT codigo, valor FROM bi.vw_cmi_valores WHERE gestion = :g"), {"g": gestion}).all()
    except SQLAlchemyError:
        db.rollback()
        logger.warning("No se pudieron leer los valores del CMI para la gestión %s; se usa el cálculo local.", gestion)
        return {}
    return {str(c): (None if v is None else float(v)) for c, v in filas}


def redondear(v: Optional[float], n: int = 2) -> Optional[float]:
    return None if v is None else round(float(v), n)
