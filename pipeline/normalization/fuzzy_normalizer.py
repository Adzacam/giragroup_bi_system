"""
pipeline/normalization/fuzzy_normalizer.py
-------------------------------------------
Módulo de normalización léxica y similitud difusa (GIRA-11) utilizando RapidFuzz.
Limpia títulos profesionales, acentos diacríticos, resuelve el orden 'APELLIDO, NOMBRE'
y calcula métricas de similitud optimizadas en C.
"""

import re
import unicodedata
from typing import List, Tuple, Optional, Dict, Any, Union

from rapidfuzz import fuzz, process
from pipeline.config import UMBRAL_CONFIANZA_ALTO, PREFIJOS_TITULOS


def remover_diacriticos(texto: str) -> str:
    """Elimina tildes y marcas diacríticas preservando letras base (ej. Pérez -> Perez)."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def limpiar_espacios_y_puntuacion(texto: str) -> str:
    """Colapsa espacios múltiples y elimina puntuación residual innecesaria."""
    if not texto:
        return ""
    txt = re.sub(r'[\t\r\n]+', ' ', texto)
    txt = re.sub(r'\s+', ' ', txt)
    return txt.strip()


def canonizar_orden_apellidos_nombre(texto: str) -> str:
    """
    Detecta si el texto está en formato 'APELLIDOS, NOMBRES' (con coma divisoria)
    y lo invierte a 'NOMBRES APELLIDOS'.
    Ejemplo: 'QUISPE MAMANI, JUAN CARLOS' -> 'JUAN CARLOS QUISPE MAMANI'.
    """
    if not texto or "," not in texto:
        return texto

    partes = [p.strip() for p in texto.split(",") if p.strip()]
    if len(partes) == 2:
        apellidos, nombres = partes[0], partes[1]
        return f"{nombres} {apellidos}".strip()

    return texto


class FuzzyNormalizer:
    """
    Normalizador léxico y comparador difuso con RapidFuzz para docentes,
    estudiantes y programas académicos de GiraGroup.
    """

    @staticmethod
    def limpiar_nombre(texto: str) -> str:
        """
        Aplica la cadena completa de limpieza:
        1. Inversión de 'APELLIDOS, NOMBRES'
        2. Remoción de títulos profesionales (Lic, Dr, Ing, etc.)
        3. Remoción de diacríticos
        4. Normalización a mayúsculas y colapso de espacios
        """
        if not texto:
            return ""

        # 1. Invertir formato con coma si existe
        txt = canonizar_orden_apellidos_nombre(texto)

        # 2. Remover títulos
        txt = PREFIJOS_TITULOS.sub(" ", txt)

        # 3. Remover caracteres no alfanuméricos excepto espacios
        txt = re.sub(r'[^\w\s]', ' ', txt)

        # 4. Remover diacríticos
        txt = remover_diacriticos(txt)

        # 5. Colapsar espacios y convertir a mayúsculas
        txt = limpiar_espacios_y_puntuacion(txt).upper()

        return txt

    @classmethod
    def calcular_similitud(
        cls,
        s1: str,
        s2: str,
        metodo: str = "token_sort"
    ) -> float:
        """
        Calcula la similitud normalizada en [0.0, 1.0] entre dos cadenas
        utilizando las funciones optimizadas en C de RapidFuzz.
        """
        n1 = cls.limpiar_nombre(s1)
        n2 = cls.limpiar_nombre(s2)

        if not n1 or not n2:
            return 0.0

        if n1 == n2:
            return 1.0

        if metodo == "wratio":
            score_raw = fuzz.WRatio(n1, n2)
        elif metodo == "token_set":
            score_raw = fuzz.token_set_ratio(n1, n2)
        else:
            # token_sort_ratio por defecto: insensible al orden de las palabras
            score_raw = fuzz.token_sort_ratio(n1, n2)

        return round(float(score_raw) / 100.0, 4)

    @classmethod
    def buscar_mejor_coincidencia(
        cls,
        candidato: str,
        opciones: Union[List[str], Dict[str, Any]],
        umbral_minimo: float = UMBRAL_CONFIANZA_ALTO,
        metodo: str = "token_sort"
    ) -> Optional[Tuple[str, float]]:
        """
        Busca la mejor coincidencia de 'candidato' en una lista o diccionario de opciones.
        Retorna (texto_mejor_coincidencia, score) si score >= umbral_minimo, sino None.
        """
        if not candidato:
            return None

        candidato_limpio = cls.limpiar_nombre(candidato)
        if not candidato_limpio:
            return None

        lista_opciones = list(opciones.keys()) if isinstance(opciones, dict) else list(opciones)
        if not lista_opciones:
            return None

        scorer_fn = fuzz.token_sort_ratio
        if metodo == "wratio":
            scorer_fn = fuzz.WRatio
        elif metodo == "token_set":
            scorer_fn = fuzz.token_set_ratio

        # processor de RapidFuzz para limpiar cada opción al vuelo
        resultado = process.extractOne(
            candidato_limpio,
            lista_opciones,
            scorer=scorer_fn,
            processor=cls.limpiar_nombre
        )

        if resultado is not None:
            mejor_match, score_pct, _ = resultado
            score_norm = round(float(score_pct) / 100.0, 4)
            if score_norm >= umbral_minimo:
                return (mejor_match, score_norm)

        return None
