"""
backend/services/dataops_evaluation_service.py
----------------------------------------------
Servicio de evaluación semántica, normalización, cálculo de bonos acumulativos
y partición de registros para DataOps (Sprint 2, 3 & 4).
"""

import math
import re
import unicodedata
from functools import lru_cache

try:
    from rapidfuzz import fuzz as _rf_fuzz
except ImportError:  # pragma: no cover
    _rf_fuzz = None
from difflib import SequenceMatcher
from typing import Optional, Tuple, Dict, Any, List

try:
    from pipeline.config import (
        COMPUERTA_LECTURA_MODELO,
        COMPUERTA_LECTURA_MODELO_PCT,
        UMBRAL_INDICE_REGISTRO,
        UMBRAL_INDICE_REGISTRO_DEC,
        TOPE_INDICE_BONIFICADO,
        TOPE_INDICE_BONIFICADO_DEC,
    )
except ImportError:
    COMPUERTA_LECTURA_MODELO = 0.70
    COMPUERTA_LECTURA_MODELO_PCT = 70
    UMBRAL_INDICE_REGISTRO = 85
    UMBRAL_INDICE_REGISTRO_DEC = 0.85
    TOPE_INDICE_BONIFICADO = 99
    TOPE_INDICE_BONIFICADO_DEC = 0.99


MOTIVOS_REGLA_DURA = {
    "CI_DUDOSA",
    "CI_ILEGIBLE",
    "NOTA_FUERA_ESCALA",
    "NOTA_INVALIDA",
    "ESCALA_AMBIGUA",
    "MONTO_INVALIDO",
}

NON_PERSON_WORDS = {
    "escuela", "tecnologia", "alianza", "estrategica", "revision", "diplomado",
    "maestria", "especialidad", "ejemplos", "practicos", "grupo", "proyectos", "proyecto",
    "negocios", "inteligencia", "evaluacion", "satisfaccion", "observacion",
    "baja", "media", "alta", "modulo", "programa", "modalidad", "virtual",
    "presencial", "semipresencial", "docente", "profesor", "tutor", "curso",
    "acta", "calificacion", "final", "nota", "agosto", "septiembre", "octubre",
    "noviembre", "diciembre", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "informe", "gestion", "big data", "ingenieria", "estetica", "ciencias", "usuario", "correo",
    "pos", "mba", "ejecutivo", "marketing", "digital", "comercial", "finanzas", "contabilidad",
    "egreso", "egresos", "techo", "techos", "cuota", "cuotas", "pago", "pagos", "cartera",
    "cobranza", "cobranzas", "meta", "metas", "ejecutado", "presupuesto", "saldo", "mora",
    "inicio", "inicios", "okr", "okrs", "planificacion", "ejecucion", "fecha", "estado",
    "ciberseguridad", "desarrollo", "software", "redes", "sociales", "admision", "inscripcion",
}


@lru_cache(maxsize=262_144)
def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def strip_accents(s: str) -> str:
    # Cacheado: la evaluación compara cada línea contra todo el catálogo (miles de nombres repetidos por línea)
    if not s:
        return ""
    return _sin_tildes(str(s))


def fuzzy_score(s1: str, s2: str) -> Tuple[float, str]:
    s1_clean = strip_accents(s1).lower().strip()
    s2_clean = strip_accents(s2).lower().strip()
    if not s1_clean or not s2_clean:
        return 0.0, "Empty"
    if s1_clean == s2_clean:
        return 100.0, "Levenshtein Exact Match"
    if _rf_fuzz is not None:
        ts_ratio = round(float(_rf_fuzz.token_sort_ratio(s1_clean, s2_clean)), 1)
        w_ratio = round(float(_rf_fuzz.WRatio(s1_clean, s2_clean)), 1)
        best = max(ts_ratio, w_ratio)
        if best >= 80.0:
            return best, "RapidFuzz Token Sort / WRatio"
    w1, w2 = set(s1_clean.split()), set(s2_clean.split())
    if w1 and w1.issubset(w2):
        return 95.0, "Token Subset Match"
    if w2 and w2.issubset(w1):
        return 92.0, "Token Subset Match"
    inter = w1.intersection(w2)
    if inter:
        overlap = len(inter) / max(len(w1), len(w2))
        return round(overlap * 90.0 + 10.0, 1), "Token Overlap Match"
    t1 = " ".join(sorted(w1))
    t2 = " ".join(sorted(w2))
    if _rf_fuzz is not None:
        # Misma razón 2·M/T que difflib, en C: difflib era ~85 % del tiempo de evaluar un lote
        return round(float(_rf_fuzz.ratio(t1, t2)), 1), "SequenceMatcher Ratio"
    ratio = SequenceMatcher(None, t1, t2).ratio()
    return round(ratio * 100, 1), "SequenceMatcher Ratio"


def calcular_porcentajes_mayor_residuo(
    auto_count: int,
    audit_count: int,
    inc_count: int
) -> Tuple[float, float, float]:
    """
    Método del Mayor Residuo (Largest Remainder Method) a 1 decimal (#2).
    Garantiza que auto_pct + audit_pct + inc_pct == 100.0% siempre que total > 0.
    Si total == 0, devuelve (0.0, 0.0, 0.0).
    """
    total = int(auto_count) + int(audit_count) + int(inc_count)
    if total <= 0:
        return 0.0, 0.0, 0.0

    counts = [int(auto_count), int(audit_count), int(inc_count)]
    quotas = [(c / total) * 1000.0 for c in counts]
    floors = [int(math.floor(q)) for q in quotas]
    remainders = [quotas[i] - floors[i] for i in range(3)]

    missing = 1000 - sum(floors)
    order = sorted(range(3), key=lambda i: remainders[i], reverse=True)
    for idx in range(max(0, missing)):
        floors[order[idx % 3]] += 1

    return round(floors[0] / 10.0, 1), round(floors[1] / 10.0, 1), round(floors[2] / 10.0, 1)


def calcular_indice_entidad_con_bonos(
    lectura_base: float,
    score_rapidfuzz: float = 0.0,
    apariciones_lote: int = 1,
    bono_catalogo_override: Optional[float] = None,
    bono_repetido_override: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Regla unificada de bonos acumulativos con compuerta 0.70 (70) y tope 0.99 (99) (#3, #6):
    - Si lectura_base < 0.70 (o < 70 en escala 0-100): no recibe bonos; índice = lectura_base.
    - Si lectura_base >= 0.70 (o >= 70):
      Índice = min(tope, lectura_base + bono_catalogo + bono_repetido).
    Soporta tanto escala decimal (0.0 - 1.0) como entera (0 - 100).
    """
    es_escala_100 = lectura_base > 1.0
    if es_escala_100:
        lectura_pct = min(TOPE_INDICE_BONIFICADO, max(0, int(round(lectura_base))))
        if lectura_pct < COMPUERTA_LECTURA_MODELO_PCT:
            return {
                "lectura_modelo": lectura_pct,
                "bono_catalogo": 0,
                "bono_repetido": 0,
                "bono_aplicado": False,
                "indice_final": lectura_pct,
            }
        if bono_catalogo_override is not None:
            bono_cat = int(round(bono_catalogo_override))
        else:
            if score_rapidfuzz >= 95.0:
                bono_cat = 12
            elif score_rapidfuzz >= 90.0:
                bono_cat = max(6, int(round(12 * ((score_rapidfuzz - 90.0) / 10.0))))
            elif score_rapidfuzz >= 85.0:
                bono_cat = 4
            else:
                bono_cat = 0

        if bono_repetido_override is not None:
            bono_rep = int(round(bono_repetido_override))
        else:
            bono_rep = 3 if apariciones_lote >= 3 else 0

        indice_final = min(TOPE_INDICE_BONIFICADO, lectura_pct + bono_cat + bono_rep)
        return {
            "lectura_modelo": lectura_pct,
            "bono_catalogo": bono_cat,
            "bono_repetido": bono_rep,
            "bono_aplicado": (bono_cat + bono_rep) > 0,
            "indice_final": indice_final,
        }
    else:
        lectura_dec = min(TOPE_INDICE_BONIFICADO_DEC, max(0.0, round(float(lectura_base), 4)))
        if lectura_dec < COMPUERTA_LECTURA_MODELO:
            return {
                "lectura_modelo": lectura_dec,
                "bono_catalogo": 0.0,
                "bono_repetido": 0.0,
                "bono_aplicado": False,
                "indice_final": lectura_dec,
            }
        if bono_catalogo_override is not None:
            bono_cat_d = round(float(bono_catalogo_override), 4)
        else:
            if score_rapidfuzz >= 95.0:
                bono_cat_d = 0.12
            elif score_rapidfuzz >= 90.0:
                bono_cat_d = round(max(0.06, 0.12 * ((score_rapidfuzz - 90.0) / 10.0)), 4)
            elif score_rapidfuzz >= 85.0:
                bono_cat_d = 0.04
            else:
                bono_cat_d = 0.0

        if bono_repetido_override is not None:
            bono_rep_d = round(float(bono_repetido_override), 4)
        else:
            bono_rep_d = 0.03 if apariciones_lote >= 3 else 0.0

        indice_final_d = min(TOPE_INDICE_BONIFICADO_DEC, round(lectura_dec + bono_cat_d + bono_rep_d, 4))
        return {
            "lectura_modelo": lectura_dec,
            "bono_catalogo": bono_cat_d,
            "bono_repetido": bono_rep_d,
            "bono_aplicado": (bono_cat_d + bono_rep_d) > 0,
            "indice_final": indice_final_d,
        }


def enmascarar_ci(ci_raw: Optional[str]) -> str:
    """
    Enmascara un número de Cédula de Identidad por defecto (#13).
    Ejemplo: '4892019 LP' -> '••••019 LP', '4892019' -> '••••019'.
    """
    if not ci_raw:
        return "No provisto"
    clean = str(ci_raw).strip()
    if not clean or clean.lower() in ("no provisto", "no especificado", "none", "null", "—"):
        return "No provisto"
    if clean.upper().startswith("TEMP-"):
        return clean

    parts = clean.split(None, 1)
    num_part = parts[0]
    suffix = f" {parts[1]}" if len(parts) > 1 else ""

    trailing_q = ""
    if num_part.endswith("?"):
        trailing_q = "?"
        num_part = num_part[:-1]

    if len(num_part) > 3:
        masked_num = f"••••{num_part[-3:]}{trailing_q}"
    else:
        masked_num = f"••••{num_part}{trailing_q}"

    return f"{masked_num}{suffix}"
