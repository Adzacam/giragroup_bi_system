"""
backend/services/tareas_dataops.py
----------------------------------
Progreso de tareas largas de DataOps (migración 008). Cada escritura usa su propia sesión y confirma al
instante, independiente de la transacción de la tarea: así la consolidación (una sola transacción al final)
puede reportar avance mientras corre, y cualquier worker de la API puede leerlo.
"""

import time
from typing import Any, Dict, Optional

from sqlalchemy import text

from core.database import SessionLocal

INTERVALO_SEG = 1.0      # como mucho una escritura de avance por segundo y tarea
SIN_LATIDO_SEG = 180     # EN_CURSO sin avance en 3 min: la API se reinició y la tarea no terminará

_ultima_escritura: Dict[int, float] = {}


def _ejecutar(sql: str, params: Dict[str, Any]):
    db = SessionLocal()
    try:
        r = db.execute(text(sql), params)
        db.commit()
        return r
    finally:
        db.close()


def crear(tipo: str, id_lote: Optional[int], total: int = 0, usuario: Optional[str] = None) -> int:
    db = SessionLocal()
    try:
        tid = db.execute(text("""
            INSERT INTO public.dataops_tarea (tipo, id_lote, total, iniciado_por)
            VALUES (:t, :l, :n, :u) RETURNING id"""), {"t": tipo, "l": id_lote, "n": total, "u": usuario}).scalar()
        db.commit()
        return tid
    finally:
        db.close()


def avanzar(tid: Optional[int], procesados: int, total: Optional[int] = None, forzar: bool = False) -> None:
    if not tid:
        return
    ahora = time.monotonic()
    if not forzar and ahora - _ultima_escritura.get(tid, 0.0) < INTERVALO_SEG:
        return
    _ultima_escritura[tid] = ahora
    _ejecutar("""
        UPDATE public.dataops_tarea SET procesados = :p, total = COALESCE(:n, total),
               actualizado_en = CURRENT_TIMESTAMP WHERE id = :id""", {"p": procesados, "n": total, "id": tid})


def terminar(tid: Optional[int], resultado: Optional[Dict[str, Any]] = None) -> None:
    if not tid:
        return
    import json
    _ultima_escritura.pop(tid, None)
    _ejecutar("""
        UPDATE public.dataops_tarea SET estado = 'COMPLETADA', procesados = GREATEST(procesados, total),
               resultado = CAST(:r AS jsonb), actualizado_en = CURRENT_TIMESTAMP, terminado_en = CURRENT_TIMESTAMP
         WHERE id = :id""", {"r": json.dumps(resultado or {}, default=str), "id": tid})


def fallar(tid: Optional[int], error: str) -> None:
    if not tid:
        return
    _ultima_escritura.pop(tid, None)
    _ejecutar("""
        UPDATE public.dataops_tarea SET estado = 'ERROR', error = :e, actualizado_en = CURRENT_TIMESTAMP,
               terminado_en = CURRENT_TIMESTAMP WHERE id = :id""", {"e": str(error)[:2000], "id": tid})


_COLS = """id, tipo, id_lote, estado, total, procesados, resultado, error, iniciado_por,
           EXTRACT(EPOCH FROM (COALESCE(terminado_en, CURRENT_TIMESTAMP) - iniciado_en)) AS transcurrido,
           EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - actualizado_en)) AS sin_latido"""


def _serializar(r) -> Optional[Dict[str, Any]]:
    if r is None:
        return None
    d = dict(r._mapping)
    estado = d["estado"]
    if estado == "EN_CURSO" and float(d.pop("sin_latido")) > SIN_LATIDO_SEG:
        estado, d["error"] = "ERROR", "La tarea se interrumpió (la API se reinició). Vuelve a ejecutarla."
    d.pop("sin_latido", None)
    transcurrido = float(d["transcurrido"] or 0)
    total, hechos = d["total"] or 0, d["procesados"] or 0
    restante = None
    if estado == "EN_CURSO" and total and 0 < hechos < total:
        restante = round(transcurrido / hechos * (total - hechos))
    d.update({
        "estado": estado,
        "transcurrido_seg": round(transcurrido),
        "restante_seg": restante,
        "porcentaje": round(hechos * 100 / total, 1) if total else 0.0,
    })
    del d["transcurrido"]
    return d


def obtener(tid: int) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        return _serializar(db.execute(text(f"SELECT {_COLS} FROM public.dataops_tarea WHERE id = :id"),
                                      {"id": tid}).first())
    finally:
        db.close()


def ultima(id_lote: int, tipo: str) -> Optional[Dict[str, Any]]:
    """Tarea más reciente de ese tipo para el lote (en curso o la última terminada)."""
    db = SessionLocal()
    try:
        return _serializar(db.execute(text(f"""
            SELECT {_COLS} FROM public.dataops_tarea WHERE id_lote = :l AND tipo = :t
            ORDER BY id DESC LIMIT 1"""), {"l": id_lote, "t": tipo}).first())
    finally:
        db.close()
