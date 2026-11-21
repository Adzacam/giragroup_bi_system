"""
backend/services/captacion_dw.py
--------------------------------
FU-L3 (DA6) · Captación de planificación en `fact_marketing`: una cifra por programa y mes.

`fact_planificacion_programa` guarda cada fila de cada hoja (con su documento, su hoja y la prioridad de la hoja en
`payload_fuente`). Aquí se decide, entre ellas, la fuente de `fact_marketing.leads_captacion` / `inscritos_captacion`
(la lee el KPI-06): ver `captacion_canonica.elegir_fuente`. Es un RECÁLCULO desde las filas de planificación vigentes, no
una suma: el resultado no depende del orden de carga, no se duplica al recargar y se corrige al borrar un documento.

La fila de captación de `fact_marketing` tiene `id_documento` NULL (una sola cifra entre varios documentos);
las inscripciones individuales (columna `inscritos`) son filas con el documento que las trajo (migración 023).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from models.fact_marketing import FactMarketing
from models.fact_planificacion import FactPlanificacionPrograma
from services import captacion_canonica as capt


def id_tiempo_de(mes: date) -> int:
    """id_tiempo de dim_tiempo = AAAAMMDD (el primer día del mes es la unidad de la captación)."""
    return mes.year * 10000 + mes.month * 100 + mes.day


def candidatos(db: Session, id_modulo: int, mes: date) -> List[Dict[str, Any]]:
    """Filas válidas de planificación del programa y mes: ambos datos, enteros, 0 <= inscritos <= leads."""
    mes_iso = mes.isoformat()
    salida = []
    for f in db.query(FactPlanificacionPrograma).filter(FactPlanificacionPrograma.id_modulo == id_modulo).all():
        payload = f.payload_fuente if isinstance(f.payload_fuente, dict) else {}
        if payload.get("mes_captacion") != mes_iso:
            continue
        leads, inscritos = f.leads_fuente, f.inscritos_fuente
        if not (capt.es_entero(leads) and capt.es_entero(inscritos) and 0 <= float(inscritos) <= float(leads)):
            continue
        salida.append({"hoja": f.hoja, "prioridad": payload.get("prioridad_captacion"), "documento": f.id_documento,
                       "leads": int(leads), "inscritos": int(inscritos)})
    return salida


def recalcular(db: Session, id_modulo: int, mes: date, limpiar_si_no_hay: bool = False) -> Optional[Dict[str, Any]]:
    """
    Deja en la fila de captación de fact_marketing (id_documento NULL) la cifra de la hoja ganadora del programa y mes.
    Sin filas válidas: no toca nada, salvo `limpiar_si_no_hay` (se borró un documento): vacía la captación y retira la
    fila si no tiene otro dato. La fila de dim_tiempo del mes debe existir para crear la fila nueva.
    """
    ganadora = capt.elegir_fuente(candidatos(db, id_modulo, mes))
    id_tiempo = id_tiempo_de(mes)
    fila = db.query(FactMarketing).filter(FactMarketing.id_modulo == id_modulo, FactMarketing.id_tiempo == id_tiempo,
                                          FactMarketing.id_documento.is_(None)).first()
    if ganadora is None:
        if limpiar_si_no_hay and fila is not None:
            fila.leads_captacion = fila.inscritos_captacion = None
            if not (fila.inscritos or fila.leads or fila.reservas):
                db.delete(fila)
            db.flush()
        return None
    if fila is not None:
        fila.leads_captacion, fila.inscritos_captacion = ganadora["leads"], ganadora["inscritos"]
    else:
        db.add(FactMarketing(id_modulo=id_modulo, id_tiempo=id_tiempo, leads=0, reservas=0, inscritos=0,
                             leads_captacion=ganadora["leads"], inscritos_captacion=ganadora["inscritos"],
                             costo_programa=0.0, id_documento=None))
    db.flush()
    return ganadora


def afectados_por_documentos(db: Session, doc_ids: List[int]) -> Set[Tuple[int, date]]:
    """(programa, mes) con captación que traen las filas de planificación de estos documentos (antes de borrarlos)."""
    pares: Set[Tuple[int, date]] = set()
    for f in db.query(FactPlanificacionPrograma).filter(FactPlanificacionPrograma.id_documento.in_(doc_ids)).all():
        payload = f.payload_fuente if isinstance(f.payload_fuente, dict) else {}
        if f.id_modulo and payload.get("mes_captacion"):
            pares.add((f.id_modulo, date.fromisoformat(payload["mes_captacion"])))
    return pares


def recalcular_pares(db: Session, pares: Set[Tuple[int, date]]) -> int:
    """Recalcula cada (programa, mes) tras borrar documentos; sin fuentes vigentes se vacía su captación."""
    for id_modulo, mes in sorted(pares):
        recalcular(db, id_modulo, mes, limpiar_si_no_hay=True)
    return len(pares)
