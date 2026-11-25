"""
backend/services/mapeo_semantico_encabezados.py
-----------------------------------------------
F7-2b: Fallback semántico de encabezados desconocidos con BETO (POST /embed) + triple compuerta (D-F7-1):
  1) Similitud coseno >= UMBRAL_COSENO (0.78 por defecto, calibrable en 0.74-0.77).
  2) Margen top1 - top2 >= MARGEN_MINIMO (0.05) frente al segundo mejor rol candidato.
  3) Filtro obligatorio de perfil de columna sobre muestra de hasta 20 valores no vacíos
     (numérico para nota/monto, patrón CI para cédula, texto para nombre/docente/programa/módulo, fecha para fecha).

Solo se invoca cuando un encabezado obtuvo < 85.0 por RapidFuzz contra el catálogo canónico.
Asigna como respaldo con origen `BETO_ESQUEMA` sin pisar jamás matches RapidFuzz >= 85.0.
Cacheado en memoria por encabezado normalizado (1 consulta por encabezado desconocido).
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import unicodedata
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("mapeo_semantico_encabezados")

URL_EMBED = os.getenv("BETO_EMBED_URL", "http://pipeline:8006/embed")
ORIGEN_BETO_ESQUEMA = "BETO_ESQUEMA"
UMBRAL_RAPIDFUZZ_EXACTO = 85.0
UMBRAL_COSENO_DEFECTO = float(os.getenv("BETO_ESQUEMA_UMBRAL_COSENO", "0.78"))
MARGEN_TOP1_TOP2_MIN = float(os.getenv("BETO_ESQUEMA_MARGEN_MIN", "0.05"))
MUESTRA_PERFIL_MAX = 20

# Prototipos de roles canónicos (frases descriptivas en español para reducir anisotropía BERT)
PROTOTIPOS_ROLES: Dict[str, Tuple[str, ...]] = {
    "nota_final": (
        "calificacion final",
        "nota final del modulo",
        "calificacion ponderada",
        "promedio final evaluacion",
        "puntaje obtenido",
    ),
    "monto": (
        "importe neto facturado",
        "monto a pagar en bolivianos",
        "saldo deuda pendiente",
        "pago cuota arancel",
        "valor monetario factura",
    ),
    "ci_estudiante": (
        "carnet de identidad",
        "cedula de identidad",
        "documento de identidad ci",
        "numero de carnet estudiante",
    ),
    "docente": (
        "docente titular del modulo",
        "profesor facilitador catedratico",
        "nombre del docente instructor",
    ),
    "estudiante": (
        "nombre completo del estudiante",
        "nombres y apellidos alumno",
        "participante postulante inscrito",
    ),
    "programa": (
        "nombre del programa posgrado",
        "diplomado maestria especialidad",
        "codigo programa pos",
    ),
    "modulo": (
        "nombre del modulo asignatura",
        "materia curso academico",
        "codigo de modulo",
    ),
    "fecha": (
        "fecha de registro o pago",
        "fecha inicio del programa",
        "fecha de evaluacion acta",
    ),
}

_RE_CI = re.compile(r"^\s*(?:c\.?\s*i\.?\s*[-:]?\s*)?\d{5,9}(?:\s*[-]?\s*[0-9A-Za-z]{1,3})?\s*$", re.IGNORECASE)
_RE_MONTO = re.compile(
    r"^\s*(?:bs\.?|\$|usd|us\$)?\s*-?\s*(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d+)?\s*(?:bs\.?|\$|usd)?\s*$",
    re.IGNORECASE,
)
_RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
_RE_FECHA = re.compile(
    r"^\s*(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?\s*$"
)


def _norm(texto: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(texto or "")) if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().split())


def _parse_float_simple(v: str) -> Optional[float]:
    t = re.sub(r"(?:bs\.?|usd|us\$|\$|\s)", "", str(v or ""), flags=re.IGNORECASE).strip()
    if not t:
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        partes = t.split(",")
        t = t.replace(",", "") if (len(partes[-1]) == 3 and len(partes) >= 2) else t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def perfil_columna_compatible(rol: str, valores: Sequence[Any]) -> bool:
    """
    Compuerta 3 (obligatoria): verifica que la muestra (hasta 20 valores no vacíos) de la columna
    sea compatible con el tipo de dato del rol candidato. Si no hay muestra útil, rechaza (fail-closed).
    """
    muestra = [str(v).strip() for v in (valores or ()) if v is not None and str(v).strip() and str(v).strip().lower() != "nan"][:MUESTRA_PERFIL_MAX]
    if not muestra:
        return False
    n = len(muestra)

    if rol == "nota_final":
        validas = 0
        for v in muestra:
            if _RE_CI.match(v) and len(re.sub(r"\D", "", v)) >= 5:
                continue
            num = _parse_float_simple(v)
            if num is not None and 0.0 <= num <= 100.0:
                validas += 1
        return (validas / n) >= 0.70

    if rol == "monto":
        validos = 0
        for v in muestra:
            if _RE_MONTO.match(v):
                num = _parse_float_simple(v)
                if num is not None:
                    validos += 1
        return (validos / n) >= 0.70

    if rol == "ci_estudiante":
        validos = sum(1 for v in muestra if _RE_CI.match(v))
        return (validos / n) >= 0.60

    if rol in ("estudiante", "docente"):
        validos = 0
        for v in muestra:
            if _RE_CORREO.match(v) or re.search(r"\d", v):
                continue
            palabras = [p for p in re.split(r"\s+", v) if re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", p)]
            if 2 <= len(palabras) <= 6:
                validos += 1
        return (validos / n) >= 0.60

    if rol in ("programa", "modulo"):
        validos = 0
        for v in muestra:
            if _RE_CORREO.match(v):
                continue
            if re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{2,}", v) and _parse_float_simple(v) is None:
                validos += 1
        return (validos / n) >= 0.60

    if rol == "fecha":
        validos = sum(1 for v in muestra if _RE_FECHA.match(v))
        return (validos / n) >= 0.60

    return False


def _coseno(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (na * nb)


def _normalizar_l2(vec: Sequence[float]) -> List[float]:
    nrm = math.sqrt(sum(x * x for x in vec))
    if nrm <= 0.0:
        return list(vec)
    return [x / nrm for x in vec]


def _post_embed(textos: List[str], timeout: float = 15.0) -> Optional[List[List[float]]]:
    if not textos:
        return []
    try:
        req = urllib.request.Request(
            URL_EMBED,
            data=json.dumps({"textos": textos, "max_length": 128}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            datos = json.loads(resp.read().decode("utf-8"))
        if datos.get("status") != "success":
            return None
        return datos.get("embeddings")
    except Exception as e:
        logger.debug("POST /embed no disponible (%s); fallback semántico omitido.", e)
        return None


class MapeadorSemanticoEncabezados:
    """
    Resuelve encabezados desconocidos (RapidFuzz < 85.0) mediante similitud coseno contra
    prototipos canónicos + margen top1-top2 >= 0.05 + filtro obligatorio de perfil de columna.
    """

    def __init__(
        self,
        embed_fn: Optional[Callable[[List[str]], Optional[List[List[float]]]]] = None,
        umbral_coseno: float = UMBRAL_COSENO_DEFECTO,
        margen_minimo: float = MARGEN_TOP1_TOP2_MIN,
    ):
        self._embed_fn = embed_fn or _post_embed
        self.umbral_coseno = float(umbral_coseno)
        self.margen_minimo = float(margen_minimo)
        self._prototipos_vec: Optional[Dict[str, List[float]]] = None
        self._cache_encabezados: Dict[str, List[float]] = {}

    def _asegurar_prototipos(self) -> Optional[Dict[str, List[float]]]:
        if self._prototipos_vec is not None:
            return self._prototipos_vec
        frases: List[str] = []
        slices: Dict[str, Tuple[int, int]] = {}
        for rol, anchors in PROTOTIPOS_ROLES.items():
            ini = len(frases)
            frases.extend(anchors)
            slices[rol] = (ini, len(frases))
        vecs = self._embed_fn(frases)
        if not vecs or len(vecs) != len(frases):
            return None
        prototipos: Dict[str, List[float]] = {}
        for rol, (ini, fin) in slices.items():
            sub = vecs[ini:fin]
            dim = len(sub[0])
            medio = [sum(v[d] for v in sub) / len(sub) for d in range(dim)]
            prototipos[rol] = _normalizar_l2(medio)
        self._prototipos_vec = prototipos
        return prototipos

    def resolver_lote(
        self,
        encabezados_con_muestra: Dict[str, Sequence[Any]],
        scores_rapidfuzz: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Recibe `{encabezado_original: muestra_valores}` y opcionalmente `{encabezado: score_rapidfuzz}`.
        Solo evalúa encabezados con `score_rapidfuzz < 85.0`.
        Devuelve `{encabezado_original: {"rol": ..., "coseno": ..., "margen": ..., "origen": "BETO_ESQUEMA"}}`.
        """
        rf = scores_rapidfuzz or {}
        candidatos = [
            h for h in encabezados_con_muestra.keys()
            if float(rf.get(h, 0.0)) < UMBRAL_RAPIDFUZZ_EXACTO and str(h or "").strip()
        ]
        if not candidatos:
            return {}

        prototipos = self._asegurar_prototipos()
        if not prototipos:
            return {}

        # Solo pedir embeddings para encabezados aún no cacheados
        por_pedir = []
        norm_map = {}
        for h in candidatos:
            nh = _norm(h)
            norm_map[h] = nh
            if nh not in self._cache_encabezados and nh not in por_pedir:
                por_pedir.append(nh)
        if por_pedir:
            vecs = self._embed_fn(por_pedir)
            if vecs and len(vecs) == len(por_pedir):
                for nh, v in zip(por_pedir, vecs):
                    self._cache_encabezados[nh] = _normalizar_l2(v)

        resueltos: Dict[str, Dict[str, Any]] = {}
        for h in candidatos:
            vec = self._cache_encabezados.get(norm_map[h])
            if vec is None:
                continue
            puntajes = sorted(
                ((rol, _coseno(vec, p_vec)) for rol, p_vec in prototipos.items()),
                key=lambda x: -x[1],
            )
            if len(puntajes) < 2:
                continue
            top1_rol, top1_sim = puntajes[0]
            _, top2_sim = puntajes[1]
            margen = top1_sim - top2_sim

            # Triple compuerta obligatoria (D-F7-1):
            # (1) coseno >= umbral, (2) margen top1 - top2 >= 0.05, (3) perfil de columna compatible
            if top1_sim < self.umbral_coseno:
                continue
            if margen < self.margen_minimo:
                continue
            if not perfil_columna_compatible(top1_rol, encabezados_con_muestra[h]):
                continue

            resueltos[h] = {
                "rol": top1_rol,
                "coseno": round(top1_sim, 4),
                "margen": round(margen, 4),
                "origen": ORIGEN_BETO_ESQUEMA,
            }
        return resueltos


_MAPEADOR_GLOBAL: Optional[MapeadorSemanticoEncabezados] = None


def obtener_mapeador_semantico() -> MapeadorSemanticoEncabezados:
    global _MAPEADOR_GLOBAL
    if _MAPEADOR_GLOBAL is None:
        _MAPEADOR_GLOBAL = MapeadorSemanticoEncabezados()
    return _MAPEADOR_GLOBAL
