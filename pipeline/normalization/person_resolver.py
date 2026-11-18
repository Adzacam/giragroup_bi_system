"""
pipeline/normalization/person_resolver.py
------------------------------------------
Resolución de personas (estudiantes y docentes) SIN catálogo canónico (cat_docente).

Cascada:
  (a) CI exacta                      -> dim_estudiante / dim_docente   (fuente CI_EXACTA)
  (b) sin CI: RapidFuzz contra la propia dimensión con bloqueo escalonado módulo -> programa -> dimensión completa,
        apellido obligatorio (tras quitar títulos), >=2 tokens en común y score >= 0,92  (fuente FUZZY)
  (c) 0 candidatos o >=2 empatados   -> None  => el llamador deriva a HITL.

El catálogo canónico (cat_*) sigue siendo la fuente solo de programa, módulo, institución,
escuela, tipo de programa, modalidad y categoría financiera.
"""

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional

from rapidfuzz import fuzz

_TITULOS = re.compile(
    r"\b(?:lic|licda|ing|dr|dra|msc|mgr|mag|mba|ph\.?\s?d|phd|arq|abg|cpa|m\.?sc)\b\.?",
    re.IGNORECASE,
)
_RE_CORREO = re.compile(r"^\s*[^@\s]+@[^@\s]+\.[A-Za-z]{2,}\s*$")
_STOP = {"de", "del", "la", "las", "los", "y", "san"}


def _sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def es_correo(valor: Optional[str]) -> bool:
    """Un correo electrónico no es el nombre de una persona."""
    return bool(valor) and bool(_RE_CORREO.match(valor))


def parece_nombre_propio(valor: Optional[str]) -> bool:
    """Forma de nombre de persona: 2 a 5 palabras sin dígitos y cada palabra (salvo partículas) empieza en mayúscula.
    Evita crear miembros nuevos (estado C) a partir de comentarios libres ('todo bien', 'mas tiempo') etiquetados como persona."""
    if not valor or es_correo(valor) or re.search(r"\d", valor):
        return False
    pal = [t for t in re.split(r"\s+", valor.strip()) if t]
    nucleo = [t for t in pal if t.lower() not in _STOP and t.lower().rstrip(".") not in ("lic", "ing", "dr", "dra", "msc", "mgr", "ph.d")]
    return 2 <= len(nucleo) <= 5 and all(t[0].isupper() for t in nucleo)


_RE_LIKERT = re.compile(r"^\s*\d+\s*/")
_RE_HDR_PATERNO = re.compile(r"^(apellido\s+)?paterno|^primer\s+apellido", re.I)
_RE_HDR_MATERNO = re.compile(r"^(apellido\s+)?materno|^segundo\s+apellido", re.I)
_RE_HDR_NOMBRES = re.compile(r"^(nombres?|nombre\(s\)|primer\s+nombre)\s*$", re.I)
_RE_HDR_APELLIDOS = re.compile(r"^apellidos?(\(s\))?\s*$", re.I)


def es_etiqueta_likert(valor: Optional[str]) -> bool:
    """'5/Totalmente de acuerdo', '3 / Adecuada': etiqueta de escala, no una persona."""
    return bool(valor) and bool(_RE_LIKERT.match(valor))


def componer_nombre_partido(celdas: Iterable[str]) -> Optional[Dict[str, Any]]:
    """
    Nombre completo de una fila cuyas columnas lo parten ('APELLIDO PATERNO: X | APELLIDO MATERNO: Y | NOMBRES: Z').
    celdas: textos 'ENCABEZADO: valor'. Devuelve {"nombre": "Z X Y", "partes": [valores usados]} si hay NOMBRES y al
    menos un apellido; None si no (la fila ya trae el nombre entero o no trae nombre).
    """
    nombres, paterno, materno, apellidos = None, None, None, None
    for c in celdas:
        hdr, sep, val = c.partition(": ")
        val = val.strip()
        if not sep or not val or val.lower() == "nan":
            continue
        h = hdr.strip()
        if _RE_HDR_PATERNO.match(h):
            paterno = paterno or val
        elif _RE_HDR_MATERNO.match(h):
            materno = materno or val
        elif _RE_HDR_NOMBRES.match(h):
            nombres = nombres or val
        elif _RE_HDR_APELLIDOS.match(h):
            apellidos = apellidos or val
    ap = [x for x in (paterno, materno) if x] or ([apellidos] if apellidos else [])
    if not nombres or not ap:
        return None
    return {"nombre": " ".join([nombres] + ap), "partes": [nombres] + ap}


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


UMBRAL_PERSONA = 0.92  # umbral de candidato (score RapidFuzz/100) para el bloqueo escalonado


class _PersonaPreparada:
    """Lo que de una persona del catálogo se usa en cada resolución, calculado una sola vez (antes se recalculaba por cada nombre a resolver:
    con 14 mil personas y 8 mil nombres eran 200 millones de normalizaciones y el 90 % del tiempo de la lectura)."""

    __slots__ = ("p", "canon", "toks", "toks_set", "apellidos", "ctx", "modulos", "ci")

    def __init__(self, p: Dict[str, Any]):
        self.p = p
        self.canon = quitar_titulos(p["nombre"])
        self.toks = _tokens(self.canon)
        self.toks_set = set(self.toks)
        self.apellidos = set(self.toks[1:])
        self.ctx = [quitar_titulos(c) for c in (p.get("contextos") or []) if c]
        self.modulos = [quitar_titulos(c) for c in (p.get("modulos") or []) if c]
        self.ci = _norm_ci(p.get("ci"))


_PREPARADAS: Dict[int, tuple] = {}
_MAX_CATALOGOS_PREPARADOS = 8


class _CatalogoPersonas:
    """Índice en memoria del catálogo preparado para evitar recorridos O(N) por cada fila."""
    __slots__ = ("lista", "ci_map", "por_apellido")

    def __init__(self, personas: List[Dict[str, Any]]):
        self.lista = [_PersonaPreparada(p) for p in personas]
        self.ci_map: Dict[str, _PersonaPreparada] = {}
        self.por_apellido: Dict[str, List[Tuple[int, _PersonaPreparada]]] = {}
        for idx, pp in enumerate(self.lista):
            if pp.ci and pp.ci not in self.ci_map:
                self.ci_map[pp.ci] = pp
            if len(pp.toks) >= 2:
                for ap in pp.apellidos:
                    self.por_apellido.setdefault(ap, []).append((idx, pp))

    def __len__(self) -> int:
        return len(self.lista)


def _preparar(personas: List[Dict[str, Any]]) -> _CatalogoPersonas:
    """Catálogo preparado, memorizado por identidad y tamaño de la lista (la misma lista se reutiliza en toda una lectura o consolidación)."""
    clave = id(personas)
    hit = _PREPARADAS.get(clave)
    if hit is not None and hit[0] is personas and hit[1] == len(personas):
        return hit[2]
    cat = _CatalogoPersonas(personas)
    while len(_PREPARADAS) >= _MAX_CATALOGOS_PREPARADOS:
        _PREPARADAS.pop(next(iter(_PREPARADAS)))
    _PREPARADAS[clave] = (personas, len(personas), cat)
    return cat


def _coincide_ctx_preparado(ctx_persona: List[str], ctx_registro: List[str]) -> bool:
    return any(a and b and (a in b or b in a) for a in ctx_persona for b in ctx_registro)


def _candidatos(personas, cand, toks_c, umbral):
    """Personas compatibles: apellido (sin títulos) en los apellidos del canónico, >=2 tokens en común y score >= umbral.
    `personas` son _PersonaPreparada (o dicts, que se preparan al vuelo)."""
    apellido, primero, toks_c_set = toks_c[-1], toks_c[0], set(toks_c)
    out = []
    for pp in personas:
        if not isinstance(pp, _PersonaPreparada):
            pp = _PersonaPreparada(pp)
        if len(pp.toks) < 2:
            continue
        # apellido: el último token del candidato debe estar entre los apellidos (todos menos el primer token) del canónico
        if apellido not in pp.apellidos and primero not in pp.apellidos:
            continue
        if len(toks_c_set & pp.toks_set) < 2:
            continue
        ts = fuzz.token_sort_ratio(cand, pp.canon)
        score = max(ts, fuzz.token_set_ratio(cand, pp.canon)) / 100.0
        if score >= umbral:
            out.append((score, ts, pp.p))
    return out


def resolver_persona_detalle(
    nombre: Optional[str],
    ci: Optional[str],
    personas: List[Dict[str, Any]],
    contexto: Optional[Iterable[str]] = None,
    ctx_modulo: Optional[Iterable[str]] = None,
    umbral: float = UMBRAL_PERSONA,
) -> Dict[str, Any]:
    """
    Bloqueo escalonado: módulo -> programa -> dimensión completa (umbral 0,92 + apellido obligatorio).
    Un nivel resuelve si tiene exactamente un candidato (o uno con score estrictamente mayor); con >=2 empatados
    en el máximo => HITL por 'empate'; con 0 candidatos en todos los niveles => HITL por 'sin_candidatos'.
    personas: [{"id","nombre","ci","modulos"(opcional),"contextos"(programas, opcional)}]
    Retorna {"resultado": dict|None, "motivo": None|"sin_candidatos"|"empate", "nivel": "CI"|"MODULO"|"PROGRAMA"|"DIMENSION"|None}.
    """
    if es_correo(nombre):  # filtro previo: ni CI ni fuzzy sobre un correo
        return {"resultado": None, "motivo": "correo", "nivel": None}
    cat = _preparar(personas)
    ci_n = _norm_ci(ci)
    if len(ci_n) >= 5:
        pp = cat.ci_map.get(ci_n)
        if pp is not None:
            p = pp.p
            return {"resultado": {"id": p["id"], "nombre": p["nombre"], "score": 1.0, "fuente": "CI_EXACTA"},
                    "motivo": None, "nivel": "CI"}

    cand = quitar_titulos(nombre or "")
    toks_c = _tokens(cand)
    if len(toks_c) < 2:
        return {"resultado": None, "motivo": "sin_candidatos", "nivel": None}  # un solo token no identifica a una persona

    apellido, primero = toks_c[-1], toks_c[0]
    vistos: Dict[int, _PersonaPreparada] = {}
    for idx, pp in cat.por_apellido.get(apellido, ()):
        vistos[idx] = pp
    if primero != apellido:
        for idx, pp in cat.por_apellido.get(primero, ()):
            vistos[idx] = pp
    if not vistos:
        return {"resultado": None, "motivo": "sin_candidatos", "nivel": None}
    pre_cands = [vistos[i] for i in sorted(vistos)]

    ctx_mod = [quitar_titulos(c) for c in (ctx_modulo or []) if c]
    ctx_prog = [quitar_titulos(c) for c in (contexto or []) if c]
    niveles = []
    if ctx_mod:
        niveles.append(("MODULO", [pp for pp in pre_cands if _coincide_ctx_preparado(pp.modulos, ctx_mod)]))
    if ctx_prog:
        niveles.append(("PROGRAMA", [pp for pp in pre_cands if _coincide_ctx_preparado(pp.ctx, ctx_prog)]))
    niveles.append(("DIMENSION", pre_cands))

    empate = False
    for nivel, pool in niveles:
        cands = _candidatos(pool, cand, toks_c, umbral)
        if not cands:
            continue  # 0 candidatos: escala al siguiente nivel
        cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
        if len(cands) > 1 and (cands[0][0], cands[0][1]) == (cands[1][0], cands[1][1]) and cands[0][2]["id"] != cands[1][2]["id"]:
            empate = True  # >=2 empatados en el máximo: no se elige a ciegas
            break
        sc, _, p = cands[0]
        return {"resultado": {"id": p["id"], "nombre": p["nombre"], "score": round(sc, 4), "fuente": "FUZZY"},
                "motivo": None, "nivel": nivel}
    return {"resultado": None, "motivo": "empate" if empate else "sin_candidatos", "nivel": None}


def resolver_persona(
    nombre: Optional[str],
    ci: Optional[str],
    personas: List[Dict[str, Any]],
    contexto: Optional[Iterable[str]] = None,
    umbral: float = UMBRAL_PERSONA,
    ctx_modulo: Optional[Iterable[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Versión de compatibilidad: devuelve {"id","nombre","score","fuente"} o None (=> HITL)."""
    return resolver_persona_detalle(nombre, ci, personas, contexto=contexto, ctx_modulo=ctx_modulo, umbral=umbral)["resultado"]


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
                    "COALESCE(array_remove(array_agg(DISTINCT m.nombre_modulo), NULL), '{}'), "
                    "COALESCE(array_remove(array_agg(DISTINCT m.programa), NULL), '{}') "
                    "FROM dim_docente d LEFT JOIN bridge_modulo_docente b ON b.id_docente=d.id_docente "
                    "LEFT JOIN dim_modulo m ON m.id_modulo=b.id_modulo GROUP BY d.id_docente, d.nombre_completo"
                )).fetchall()
                return [{"id": r[0], "nombre": r[1], "ci": None, "modulos": [x for x in (r[2] or []) if x],
                         "contextos": [x for x in (r[3] or []) if x]} for r in rows]
            rows = c.execute(text(
                "SELECT id_estudiante, nombre_completo, ci_numero, programa_origen FROM dim_estudiante WHERE deprecado = FALSE"
            )).fetchall()
            return [{"id": r[0], "nombre": r[1], "ci": r[2], "contextos": [r[3]] if r[3] else []} for r in rows]
    except Exception:
        return []
