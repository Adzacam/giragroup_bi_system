"""
pipeline/semantic/ventana.py
----------------------------
Ventana deslizante para los textos de más de `max_length` tokens (flag BETO_VENTANA, apagado por defecto).

BETO se lee con max_length = 128 (el mismo recorte que el índice de confianza): un texto más largo solo se veía por el inicio (el 27 % de
las líneas de una carga mensual). Con la ventana el texto se parte en tramos de 128 − 2 tokens (CLS y SEP) que se solapan `stride` tokens,
cada tramo se lee con el pipeline NER normal y las entidades se fusionan por máxima probabilidad. Funciones puras, sin torch.
"""
from typing import Any, Dict, List, Tuple

TOKENS_ESPECIALES = 2   # [CLS] y [SEP]


def tramos_de_tokens(n_tokens: int, ventana: int, stride: int) -> List[Tuple[int, int]]:
    """Tramos [i0, i1) de a lo sumo `ventana` tokens que se solapan `stride` tokens. Un texto que cabe en una ventana da un solo tramo."""
    if ventana <= 0:
        raise ValueError("la ventana debe ser positiva")
    if n_tokens <= ventana:
        return [(0, n_tokens)]
    paso = max(1, ventana - max(0, stride))
    tramos, i = [], 0
    while True:
        j = min(i + ventana, n_tokens)
        tramos.append((i, j))
        if j >= n_tokens:
            return tramos
        i += paso


def _se_solapan(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def fusionar_entidades(predicciones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fusiona las entidades de ventanas que se solapan. Cada predicción: {entity_group, start, end, score, word?, borde?}.
    1) Una entidad cortada por el borde de una ventana (`borde` verdadero) se descarta si otra, que no está cortada, la cubre en parte:
       la ventana vecina la ve completa.
    2) De las entidades del mismo grupo que se solapan queda la de mayor probabilidad (a igualdad, la más larga y la primera).
    Las de grupos distintos se conservan: decide después _procesar_predicciones_beto.
    """
    completas = [p for p in predicciones if not p.get("borde")]
    candidatas = completas + [p for p in predicciones if p.get("borde") and not any(_se_solapan(p, c) for c in completas)]
    elegidas: List[Dict[str, Any]] = []
    for p in sorted(candidatas, key=lambda p: (-p["score"], -(p["end"] - p["start"]), p["start"])):
        if any(q["entity_group"] == p["entity_group"] and _se_solapan(p, q) for q in elegidas):
            continue
        elegidas.append(p)
    return sorted(elegidas, key=lambda p: (p["start"], p["end"]))
