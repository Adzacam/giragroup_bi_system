"""
backend/services/cache_consultas.py
-----------------------------------
Caché en proceso para lecturas analíticas costosas (alertas tempranas, CMI, forecast), RNF-03.
El DW solo cambia al consolidar cargas: los flujos de carga llaman a invalidar() al hacer commit,
y el TTL acota cuánto puede quedar desactualizado otro worker de uvicorn.
"""

import threading
import time
from typing import Any, Callable, Dict, Hashable, Tuple

_lock = threading.Lock()
_entradas: Dict[Hashable, Tuple[float, Any]] = {}


def obtener(clave: Hashable, ttl_seg: float, calcular: Callable[[], Any]) -> Any:
    ahora = time.monotonic()
    with _lock:
        entrada = _entradas.get(clave)
        if entrada and entrada[0] > ahora:
            return entrada[1]
    valor = calcular()
    with _lock:
        _entradas[clave] = (ahora + ttl_seg, valor)
    return valor


def invalidar() -> None:
    with _lock:
        _entradas.clear()


def consultar(clave: Hashable) -> Any:
    """Consulta sin calcular ni guardar ausencias: una tarea puede terminar en otro worker."""
    with _lock:
        entrada = _entradas.get(clave)
        return entrada[1] if entrada and entrada[0] > time.monotonic() else None
