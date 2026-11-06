"""
pipeline/normalization/person_resolver.py
------------------------------------------
Resolución de personas (estudiantes y docentes) SIN catálogo canónico (cat_docente).

Cascada:
  (a) CI exacta                      -> dim_estudiante / dim_docente   (fuente CI_EXACTA)
  (b) sin CI: RapidFuzz contra la propia dimensión, con
        - candidatos filtrados al mismo programa/módulo del registro,
        - coincidencia de apellido tras quitar títulos (Lic., Ing., Dr., MSc., Mgr., Ph.D.),
        - al menos 2 tokens de nombre en común y score >= UMBRAL_CONFIANZA_ALTO  (fuente FUZZY)
  (c) sin coincidencia               -> None  => el llamador deriva a HITL.

El catálogo canónico (cat_*) sigue siendo la fuente solo de programa, módulo, institución,
escuela, tipo de programa, modalidad y categoría financiera.
"""

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional

from rapidfuzz import fuzz

from pipeline.config import UMBRAL_CONFIANZA_ALTO

_TITULOS = re.compile(
    r"\b(?:lic|licda|ing|dr|dra|msc|mgr|mag|mba|ph\.?\s?d|phd|arq|abg|cpa|m\.?sc)\b\.?",
    re.IGNORECASE,
)
_STOP = {"de", "del", "la", "las", "los", "y", "san"}


def _sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def quitar_titulos(nombre: str) -> str:
    """Quita títulos académicos y normaliza (minúsculas, sin acentos ni puntuación)."""
    s = _sin_acentos(nombre or "").lower()
    s = _TITULOS.sub(" ", s)
    s = re.sub(r"[^a-z0-9ñ\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _tokens(nombre_limpio: str) -> List[str]:
    return [t for t in nombre_limpio.split() if len(t) >= 3 and t not in _STOP]


def _norm_ci(ci: Optional[str]) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", str(ci or "")).upper()


def _coincide_contexto(persona_ctx: Iterable[str], registro_ctx: Iterable[str]) -> bool:
    """Un contexto coincide si algún texto de programa/módulo contiene al otro."""
    pc = [quitar_titulos(c) for c in persona_ctx if c]
    rc = [quitar_titulos(c) for c in registro_ctx if c]
    return any(a and b and (a in b or b in a) for a in pc for b in rc)


def resolver_persona(
    nombre: Optional[str],
    ci: Optional[str],
    personas: List[Dict[str, Any]],
    contexto: Optional[Iterable[str]] = None,
    umbral: float = UMBRAL_CONFIANZA_ALTO,
) -> Optional[Dict[str, Any]]:
    """
    personas: [{"id", "nombre", "ci"(opcional), "contextos"(opcional: programas/módulos)}]
    contexto: programas/módulos del registro. Si se entrega, SOLO compiten personas con contexto coincidente.
    Retorna {"id","nombre","score"(0-1),"fuente"} o None (=> HITL).
    """
    # (a) CI exacta
    ci_n = _norm_ci(ci)
    if len(ci_n) >= 5:
        for p in personas:
            if _norm_ci(p.get("ci")) == ci_n:
                return {"id": p["id"], "nombre": p["nombre"], "score": 1.0, "fuente": "CI_EXACTA"}

    # (b) sin CI: fuzzy en la propia dimensión
    cand = quitar_titulos(nombre or "")
    toks_c = _tokens(cand)
    if len(toks_c) < 2:
        return None  # un solo token no identifica a una persona
    apellido = toks_c[-1]

    contexto = [c for c in (contexto or []) if c]
    mejor, mejor_score, mejor_ts = None, 0.0, 0.0
    for p in personas:
        if contexto and not _coincide_contexto(p.get("contextos") or [], contexto):
            continue
        canon = quitar_titulos(p["nombre"])
        toks_p = _tokens(canon)
        if len(toks_p) < 2:
            continue
        # apellido: el último token del candidato debe estar entre los apellidos (todos menos el primer token) del canónico
        if apellido not in toks_p[1:] and toks_c[0] not in toks_p[1:]:
            continue
        if len(set(toks_c) & set(toks_p)) < 2:
            continue
        ts = fuzz.token_sort_ratio(cand, canon)
        score = max(ts, fuzz.token_set_ratio(cand, canon)) / 100.0
        if (score, ts) > (mejor_score, mejor_ts):  # desempate: mayor token_sort (nombre más completo)
            mejor, mejor_score, mejor_ts = p, score, ts
    if mejor is not None and mejor_score >= umbral:
        return {"id": mejor["id"], "nombre": mejor["nombre"], "score": round(mejor_score, 4), "fuente": "FUZZY"}

    # (c) sin coincidencia
    return None


def cargar_personas_dw(tabla: str, database_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Carga dim_docente / dim_estudiante del DW como lista para resolver_persona.
    Docentes: contextos = módulos y programas asignados (bridge_modulo_docente -> dim_modulo).
    Estudiantes: contextos = programa_origen. Sin conexión devuelve [] (=> todo a HITL, nunca a un catálogo).
    """
    import os
    from sqlalchemy import create_engine, text
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        return []
    try:
        eng = create_engine(url)
        with eng.connect() as c:
            if tabla == "dim_docente":
                rows = c.execute(text(
                    "SELECT d.id_docente, d.nombre_completo, "
                    "COALESCE(array_remove(array_agg(DISTINCT m.nombre_modulo) || array_agg(DISTINCT m.programa), NULL), '{}') "
                    "FROM dim_docente d LEFT JOIN bridge_modulo_docente b ON b.id_docente=d.id_docente "
                    "LEFT JOIN dim_modulo m ON m.id_modulo=b.id_modulo GROUP BY d.id_docente, d.nombre_completo"
                )).fetchall()
                return [{"id": r[0], "nombre": r[1], "ci": None, "contextos": [x for x in (r[2] or []) if x]} for r in rows]
            rows = c.execute(text(
                "SELECT id_estudiante, nombre_completo, ci_numero, programa_origen FROM dim_estudiante WHERE deprecado = FALSE"
            )).fetchall()
            return [{"id": r[0], "nombre": r[1], "ci": r[2], "contextos": [r[3]] if r[3] else []} for r in rows]
    except Exception:
        return []
