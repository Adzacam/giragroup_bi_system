"""
backend/services/cache_lectura.py
---------------------------------
Resultado de la lectura de BETO de un lote, guardado en disco y compartido por los workers de la API.

La caché en memoria (cache_consultas) es por proceso: con 4 workers, la lectura que el servidor calculaba
tras la ingesta no servía a la página, y cada worker la recalculaba (~8 min con 100 mil registros). La clave
incluye la huella del lote, así que un cambio en staging o en los casos resueltos genera otra entrada.
"""

import gzip
import hashlib
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Any, Hashable, Optional

logger = logging.getLogger("cache_lectura")

DIR = Path(os.environ.get("LECTURA_CACHE_DIR", Path(__file__).resolve().parents[1] / "uploads" / ".cache_lectura"))
TTL_SEG = 24 * 3600


def _ruta(clave: Hashable) -> Path:
    return DIR / f"{hashlib.sha256(repr(clave).encode('utf-8')).hexdigest()}.pkl.gz"


def leer(clave: Hashable) -> Optional[Any]:
    ruta = _ruta(clave)
    try:
        if not ruta.is_file() or time.time() - ruta.stat().st_mtime > TTL_SEG:
            return None
        with gzip.open(ruta, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        logger.warning("No se pudo leer la caché de lectura %s: %s", ruta.name, e)
        return None


def guardar(clave: Hashable, valor: Any) -> None:
    """Escritura atómica (tmp + rename) para que otro worker nunca lea un archivo a medias."""
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        ruta = _ruta(clave)
        tmp = ruta.with_suffix(f".{os.getpid()}.tmp")
        with gzip.open(tmp, "wb", compresslevel=1) as f:
            pickle.dump(valor, f, protocol=pickle.HIGHEST_PROTOCOL)
        tmp.replace(ruta)
        _purgar_viejos()
    except Exception as e:
        logger.warning("No se pudo guardar la caché de lectura: %s", e)


def _purgar_viejos() -> None:
    limite = time.time() - TTL_SEG
    for p in DIR.glob("*.pkl.gz"):
        try:
            if p.stat().st_mtime < limite:
                p.unlink()
        except OSError:
            pass
