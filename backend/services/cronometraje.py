"""
backend/services/cronometraje.py
--------------------------------
Registro de las aprobaciones de la bandeja HITL con hora de inicio y fin (para medir el tiempo humano de un ciclo).
Activo solo si CRONOMETRAJE_LOG apunta a un archivo: una línea JSON por acción (approve-group, batch-resolve, resolución individual).
Lo escriben los endpoints, así que registra igual lo que hace el usuario desde la UI que lo que hace un script.
"""
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def ahora() -> float:
    return time.time()


def registrar_aprobacion(accion: str, t_inicio: float, detalle: Optional[Dict[str, Any]] = None, usuario: Optional[str] = None) -> None:
    ruta = os.getenv("CRONOMETRAJE_LOG")
    if not ruta:
        return
    t_fin = time.time()
    fila = {"accion": accion, "inicio": datetime.fromtimestamp(t_inicio, timezone.utc).isoformat(), "fin": datetime.fromtimestamp(t_fin, timezone.utc).isoformat(),
            "segundos": round(t_fin - t_inicio, 3), "usuario": usuario, **(detalle or {})}
    try:
        with open(ruta, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(fila, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass  # el registro nunca debe romper una aprobación
