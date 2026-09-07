"""
pipeline/normalization/semantic_matcher.py
-------------------------------------------
Módulo de matching semántico (GIRA-41) contra catálogos maestros institucionales.
Enlaza entidades extraídas (programas, módulos, docentes) contra la base canónica
utilizando coincidencia exacta O(1) y fallback probabilístico con RapidFuzz.
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from pipeline.config import SEED_CATALOGOS_SQL_PATH, UMBRAL_CONFIANZA_ALTO
from pipeline.normalization.fuzzy_normalizer import FuzzyNormalizer


class SemanticMatcher:
    """
    Motor de grounding y resolución contra catálogos maestros de GiraGroup.
    """

    def __init__(self, ruta_seed_sql: Optional[Path] = None):
        self.ruta_seed = ruta_seed_sql or SEED_CATALOGOS_SQL_PATH
        self.programas_por_pos: Dict[str, Dict[str, Any]] = {}
        self.programas_por_nombre: Dict[str, str] = {}  # nombre_limpio -> pos_code
        self.docentes_canonicos: List[str] = []
        self.modulos_canonicos: List[str] = []

        self._cargar_catalogos()

    def _cargar_catalogos(self):
        """Carga y estructura los catálogos en memoria desde el archivo seed de la BD."""
        if not self.ruta_seed.exists():
            return

        with open(self.ruta_seed, "r", encoding="utf-8") as f:
            for line in f:
                # 1. Programas: INSERT INTO public.cat_programa ... VALUES ('POS-XXXX', 'NOMBRE', ...)
                if "INSERT INTO public.cat_programa" in line:
                    m = re.search(
                        r"VALUES\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*(\d+)",
                        line,
                        re.IGNORECASE
                    )
                    if m:
                        pos = m.group(1).strip().upper()
                        nombre = m.group(2).strip()
                        version = int(m.group(3))
                        self.programas_por_pos[pos] = {
                            "pos": pos,
                            "nombre_canonico": nombre,
                            "version": version
                        }
                        nombre_limpio = FuzzyNormalizer.limpiar_nombre(nombre)
                        if nombre_limpio:
                            self.programas_por_nombre[nombre_limpio] = pos

                # 2. Docentes: INSERT INTO public.cat_docente (nombre_docente) VALUES ('NOMBRE')
                elif "INSERT INTO public.cat_docente" in line:
                    m = re.search(r"VALUES\s*\(\s*'([^']+)'", line, re.IGNORECASE)
                    if m:
                        self.docentes_canonicos.append(m.group(1).strip())

                # 3. Módulos: INSERT INTO public.cat_modulo (nombre_modulo) VALUES ('NOMBRE')
                elif "INSERT INTO public.cat_modulo" in line:
                    m = re.search(r"VALUES\s*\(\s*'([^']+)'", line, re.IGNORECASE)
                    if m:
                        self.modulos_canonicos.append(m.group(1).strip())

    # ──────────────────────────────────────────────────────────────────────────
    # Matching de Programas Académicos (POS)
    # ──────────────────────────────────────────────────────────────────────────
    def enlazar_programa(
        self,
        texto_o_pos: str,
        umbral_minimo: float = UMBRAL_CONFIANZA_ALTO
    ) -> Optional[Dict[str, Any]]:
        """
        Enlaza un texto de programa o código numérico contra el catálogo oficial.
        Prioridad 1: Coincidencia de código POS (ej. POS-5252 o 5252).
        Prioridad 2: Similitud difusa con RapidFuzz sobre nombres canónicos.
        """
        if not texto_o_pos:
            return None

        txt = str(texto_o_pos).strip()

        # 1. Búsqueda directa por código POS
        m_pos = re.search(r'\b(?:POS[-_ ]?)?(\d{4,5})\b', txt, re.IGNORECASE)
        if m_pos:
            pos_key = f"POS-{m_pos.group(1)}"
            if pos_key in self.programas_por_pos:
                prg = self.programas_por_pos[pos_key]
                return {
                    "pos": pos_key,
                    "nombre_canonico": prg["nombre_canonico"],
                    "version": prg.get("version", 1),
                    "score": 1.0,
                    "tipo_match": "EXACTO_POS"
                }

        # 2. Fallback fuzzy por nombre de programa
        nombres_lista = [p["nombre_canonico"] for p in self.programas_por_pos.values()]
        mejor = FuzzyNormalizer.buscar_mejor_coincidencia(
            txt,
            nombres_lista,
            umbral_minimo=umbral_minimo,
            metodo="token_sort"
        )
        if mejor:
            nombre_match, score = mejor
            # Encontrar el POS correspondiente
            pos_encontrado = None
            for p in self.programas_por_pos.values():
                if p["nombre_canonico"] == nombre_match:
                    pos_encontrado = p["pos"]
                    break

            return {
                "pos": pos_encontrado,
                "nombre_canonico": nombre_match,
                "score": score,
                "tipo_match": "FUZZY_NOMBRE_PROGRAMA"
            }

        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Matching de Docentes
    # ──────────────────────────────────────────────────────────────────────────
    def enlazar_docente(
        self,
        nombre_extraido: str,
        umbral_minimo: float = UMBRAL_CONFIANZA_ALTO
    ) -> Optional[Dict[str, Any]]:
        """
        Enlaza el nombre de un docente contra la nómina canónica de 768 docentes.
        Limpia títulos profesionales (Lic., Dr., etc.) antes de comparar.
        """
        if not nombre_extraido:
            return None

        # 1. Coincidencia exacta post-limpieza
        nombre_limpio = FuzzyNormalizer.limpiar_nombre(nombre_extraido)
        for doc in self.docentes_canonicos:
            if FuzzyNormalizer.limpiar_nombre(doc) == nombre_limpio:
                return {
                    "nombre_canonico": doc,
                    "score": 1.0,
                    "tipo_match": "EXACTO_NOMBRE"
                }

        # 2. Fallback fuzzy con RapidFuzz WRatio / token_sort
        mejor = FuzzyNormalizer.buscar_mejor_coincidencia(
            nombre_extraido,
            self.docentes_canonicos,
            umbral_minimo=umbral_minimo,
            metodo="wratio"
        )
        if mejor:
            doc_match, score = mejor
            return {
                "nombre_canonico": doc_match,
                "score": score,
                "tipo_match": "FUZZY_DOCENTE"
            }

        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Matching de Módulos
    # ──────────────────────────────────────────────────────────────────────────
    def enlazar_modulo(
        self,
        nombre_modulo: str,
        umbral_minimo: float = UMBRAL_CONFIANZA_ALTO
    ) -> Optional[Dict[str, Any]]:
        """
        Enlaza el nombre de un módulo contra el catálogo canónico de módulos.
        """
        if not nombre_modulo:
            return None

        mod_limpio = FuzzyNormalizer.limpiar_nombre(nombre_modulo)
        for m in self.modulos_canonicos:
            if FuzzyNormalizer.limpiar_nombre(m) == mod_limpio:
                return {
                    "modulo_canonico": m,
                    "score": 1.0,
                    "tipo_match": "EXACTO_MODULO"
                }

        mejor = FuzzyNormalizer.buscar_mejor_coincidencia(
            nombre_modulo,
            self.modulos_canonicos,
            umbral_minimo=umbral_minimo,
            metodo="token_sort"
        )
        if mejor:
            m_match, score = mejor
            return {
                "modulo_canonico": m_match,
                "score": score,
                "tipo_match": "FUZZY_MODULO"
            }

        return None
