"""
backend/services/bandeja_grupos.py
----------------------------------
Agrupa los casos pendientes de la bandeja HITL por (motivo, valor normalizado) para aprobarlos de una vez.
- CI_NOMBRE_DISCORDANTE: el CI del caso.  - HOMONIMIA: el nombre sin títulos ni acentos.
- BAJA_CONFIANZA_IA y otros: la forma de la línea (encabezados sin valores, dígitos como '#'); sin encabezados, el texto normalizado.
"""
import re
import unicodedata
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models.staging_entidad import StagingEntidadNoResuelta


def _sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")


def valor_normalizado(motivo: Optional[str], texto: Optional[str]) -> str:
    t = (texto or "").strip()
    m = (motivo or "").upper()
    if m == "CI_NOMBRE_DISCORDANTE":
        ci = re.search(r"CI:\s*([0-9A-Za-z\-]+)", t)
        return ci.group(1).upper() if ci else _sin_acentos(t).lower()[:80]
    if m == "HOMONIMIA":
        from pipeline.normalization.person_resolver import quitar_titulos
        return quitar_titulos(t)[:80]
    celdas = [c.strip() for c in t.split("|") if c.strip()]
    hdrs = [c.partition(": ")[0] for c in celdas if ": " in c]
    base = " | ".join(hdrs) if hdrs else " | ".join(celdas)
    return re.sub(r"\d+", "#", _sin_acentos(base).lower())[:120]


def clave_grupo(motivo: Optional[str], texto: Optional[str]) -> str:
    return f"{(motivo or '').upper()}::{valor_normalizado(motivo, texto)}"


def grupos_pendientes(db: Session, doc_ids: Optional[List[int]] = None, limite: int = 500) -> Dict[str, Any]:
    """Grupos de casos de staging pendientes: [{clave, motivo, valor, n, ejemplo, ids}] por tamaño; total de casos y de grupos."""
    q = db.query(StagingEntidadNoResuelta.id_staging, StagingEntidadNoResuelta.motivo, StagingEntidadNoResuelta.texto_original).filter(
        StagingEntidadNoResuelta.resuelto == False)  # noqa: E712
    if doc_ids is not None:
        q = q.filter(StagingEntidadNoResuelta.id_documento.in_(list(doc_ids)))
    grupos: Dict[str, Dict[str, Any]] = {}
    n_casos = 0
    for id_stg, motivo, texto in q.order_by(StagingEntidadNoResuelta.id_staging).all():
        n_casos += 1
        k = clave_grupo(motivo, texto)
        g = grupos.setdefault(k, {"clave": k, "motivo": motivo, "valor": valor_normalizado(motivo, texto), "n": 0, "ejemplo": (texto or "")[:160], "ids": []})
        g["n"] += 1
        if len(g["ids"]) < 50:
            g["ids"].append(id_stg)
    ordenados = sorted(grupos.values(), key=lambda g: -g["n"])
    return {"total_casos": n_casos, "total_grupos": len(ordenados), "grupos": ordenados[:limite]}


def ids_del_grupo(db: Session, clave: str, doc_ids: Optional[List[int]] = None) -> List[int]:
    motivo = clave.split("::", 1)[0]
    q = db.query(StagingEntidadNoResuelta.id_staging, StagingEntidadNoResuelta.motivo, StagingEntidadNoResuelta.texto_original).filter(
        StagingEntidadNoResuelta.resuelto == False, StagingEntidadNoResuelta.motivo == motivo)  # noqa: E712
    if doc_ids is not None:
        q = q.filter(StagingEntidadNoResuelta.id_documento.in_(list(doc_ids)))
    return [i for i, m, t in q.order_by(StagingEntidadNoResuelta.id_staging).all() if clave_grupo(m, t) == clave]
