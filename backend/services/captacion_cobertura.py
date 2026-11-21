"""
backend/services/captacion_cobertura.py
---------------------------------------
FU-L3 (DA6) · Cobertura mensual de la captación (KPI-06) y motivo cuando una gestión queda «sin dato».

Lee `public.fact_marketing` (leads_captacion / inscritos_captacion, ya deduplicados por programa y mes al cargar)
con la MISMA regla de `bi.vw_cmi_valores`: leads > 0 e 0 <= inscritos <= leads. No crea vistas (el esquema bi
mantiene sus 10 vistas): son consultas de solo lectura sobre las tablas públicas.

- `por_mes`: leads, inscritos, programas y conversión de cada mes con dato.
- `cobertura`: por gestión, meses con dato de los 12 de la gestión y desde/hasta qué mes hay datos.
- `motivo_sin_dato`: texto para una gestión sin leads, que dice desde qué mes hay datos.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger("captacion_cobertura")

MESES_GESTION = 12
_NOMBRE_MES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
               "octubre", "noviembre", "diciembre"]

_SQL_POR_MES = text("""
    SELECT dt.gestion AS gestion, dt.mes AS mes, dt.periodo_mes AS periodo_mes,
           SUM(fm.leads_captacion) AS leads, SUM(fm.inscritos_captacion) AS inscritos,
           COUNT(DISTINCT fm.id_modulo) AS programas
    FROM public.fact_marketing fm
    JOIN public.dim_tiempo dt ON dt.id_tiempo = fm.id_tiempo
    WHERE fm.leads_captacion > 0 AND fm.inscritos_captacion >= 0
      AND fm.inscritos_captacion <= fm.leads_captacion
    GROUP BY dt.gestion, dt.mes, dt.periodo_mes
    ORDER BY dt.gestion, dt.mes
""")


def etiqueta_mes(gestion: int, mes: int) -> str:
    return f"{_NOMBRE_MES[mes - 1]} de {gestion}"


def por_mes(db: Session, gestion: Optional[int] = None) -> List[Dict[str, Any]]:
    """Meses con captación comprobable (todas las gestiones, o solo `gestion`)."""
    savepoint = getattr(db, "begin_nested", None)
    try:
        if savepoint is None:
            filas = db.execute(_SQL_POR_MES).mappings().all()
        else:
            with savepoint():   # SAVEPOINT: un fallo no descarta lo que la sesión aún no confirmó
                filas = db.execute(_SQL_POR_MES).mappings().all()
    except SQLAlchemyError:
        if savepoint is None:
            db.rollback()
        logger.warning("No se pudo leer la captación mensual de fact_marketing")
        return []
    salida = []
    for f in filas:
        if gestion is not None and int(f["gestion"]) != int(gestion):
            continue
        leads, ins = int(f["leads"]), int(f["inscritos"])
        salida.append({
            "gestion": int(f["gestion"]), "mes": int(f["mes"]), "periodo_mes": f["periodo_mes"],
            "leads": leads, "inscritos": ins, "programas": int(f["programas"]),
            "conversion_pct": round(100.0 * ins / leads, 2),
        })
    return salida


def cobertura(meses: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """{gestión: meses con dato / meses de la gestión, primer y último mes con dato} a partir de `por_mes`."""
    por_gestion: Dict[int, List[int]] = {}
    for m in meses:
        por_gestion.setdefault(m["gestion"], []).append(m["mes"])
    out = {}
    for g, lista in por_gestion.items():
        lista = sorted(set(lista))
        out[g] = {
            "gestion": g, "meses_con_dato": len(lista), "meses_gestion": MESES_GESTION,
            "primer_mes": lista[0], "ultimo_mes": lista[-1],
            "desde": etiqueta_mes(g, lista[0]), "hasta": etiqueta_mes(g, lista[-1]),
        }
    return out


def motivo_sin_dato(meses: List[Dict[str, Any]], gestion: int, plantillas: Optional[dict] = None) -> str:
    """
    Motivo de un KPI-06 «sin dato» en `gestion`: no hay interesados e inscritos de un mismo programa y mes, y dice
    desde qué mes hay datos en la DW (o que no hay en ninguna gestión).
    """
    plantillas = plantillas or {}
    cob = cobertura(meses)
    if not cob:
        return plantillas.get("sin_ninguna") or "No hay interesados e inscritos de un mismo programa y mes en ninguna fuente cargada."
    primera = min(cob.values(), key=lambda c: (c["gestion"], c["primer_mes"]))
    desde = primera["desde"]
    if gestion in cob:
        c = cob[gestion]
        return (f"La gestión tiene datos de captación en {c['meses_con_dato']} de {MESES_GESTION} meses "
                f"({c['desde']} a {c['hasta']}), pero ninguno con interesados e inscritos comprobables.")
    plantilla = plantillas.get("sin_leads") or ("Sin leads en esta gestión: la fuente de captación trae interesados e "
                                                 "inscritos de un mismo programa y mes desde {desde}.")
    return plantilla.format(desde=desde)
