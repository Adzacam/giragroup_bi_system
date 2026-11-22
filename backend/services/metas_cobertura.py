"""
backend/services/metas_cobertura.py
-----------------------------------
FU-L6 (DA4) · Qué metas trae la fuente por gestión, para explicar por qué el KPI-02 queda «sin dato».

El KPI-02 (cumplimiento del último mes cerrado) solo se calcula con meta MENSUAL (`bi.vw_cmi_valores`, migración 026). Cuando una gestión
no tiene meta mensual el valor es NULL y este módulo dice por qué, con los textos de `config/mapeo_fuentes.yaml` (sección `metas`,
`motivos_sin_dato`): la fuente solo trae meta anual, no trae ninguna meta o no hay un mes cerrado con ejecución.

Sin la columna `granularidad_meta` (DW sin la migración 026) toda meta se lee como mensual, igual que las vistas.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("metas_cobertura")

_SQL_CON_GRANULARIDAD = """
    SELECT dt.gestion, fr.granularidad_meta, MAX(CASE WHEN fr.monto_meta > 0 THEN 1 ELSE 0 END) AS con_meta
    FROM fact_rentabilidad fr
    JOIN dim_tiempo dt               ON dt.id_tiempo = fr.id_tiempo
    JOIN dim_categoria_financiera dc ON dc.id_categoria = fr.id_categoria
    WHERE dc.tipo = 'INGRESO'
    GROUP BY dt.gestion, fr.granularidad_meta"""

_SQL_SIN_GRANULARIDAD = """
    SELECT dt.gestion, NULL AS granularidad_meta, MAX(CASE WHEN fr.monto_meta > 0 THEN 1 ELSE 0 END) AS con_meta
    FROM fact_rentabilidad fr
    JOIN dim_tiempo dt               ON dt.id_tiempo = fr.id_tiempo
    JOIN dim_categoria_financiera dc ON dc.id_categoria = fr.id_categoria
    WHERE dc.tipo = 'INGRESO'
    GROUP BY dt.gestion"""


def _leer(db, sql: str) -> Dict[int, Dict[str, bool]]:
    savepoint = getattr(db, "begin_nested", None)
    if savepoint is None:
        filas = db.execute(text(sql)).all()
    else:
        with savepoint():   # un fallo (columna ausente, vistas sin migrar) solo deshace esta lectura
            filas = db.execute(text(sql)).all()
    res: Dict[int, Dict[str, bool]] = {}
    for gestion, gran, con_meta in filas:
        m = res.setdefault(int(gestion), {"mensual": False, "anual": False})
        if con_meta:
            m["anual" if gran == "ANUAL" else "mensual"] = True   # sin bandera (NULL) se lee como mensual, igual que las vistas
    return res


def metas_por_gestion(db) -> Dict[int, Dict[str, bool]]:
    """{gestión: {mensual, anual}}: si la fuente trae meta mensual y/o meta anual de ingresos en esa gestión."""
    try:
        return _leer(db, _SQL_CON_GRANULARIDAD)
    except SQLAlchemyError:
        try:
            return _leer(db, _SQL_SIN_GRANULARIDAD)
        except SQLAlchemyError:
            logger.warning("No se pudieron leer las metas por gestión; el KPI-02 sin dato queda sin motivo específico.")
            return {}


def motivo_sin_dato_kpi02(db, gestion: int, plantillas: Optional[dict] = None) -> Optional[str]:
    """Motivo por el que el KPI-02 de la gestión no tiene valor; None si no se puede determinar (sin lectura de metas)."""
    from services import metas_canonica
    metas = metas_por_gestion(db)
    if not metas:
        return None
    m = metas.get(int(gestion)) or {"mensual": False, "anual": False}
    if m["mensual"]:
        clave, defecto = "kpi_02_sin_mes_cerrado", "La gestión no tiene ningún mes cerrado con ejecución y meta mensual."
    elif m["anual"]:
        clave, defecto = "kpi_02_solo_anual", "La fuente solo trae meta anual."
    else:
        clave, defecto = "kpi_02_sin_meta", "No hay meta cargada para esta gestión."
    return (plantillas or {}).get(clave) or metas_canonica.motivo_sin_dato(clave, defecto)
