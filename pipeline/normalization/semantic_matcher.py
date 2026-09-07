"""
pipeline/normalization/semantic_matcher.py
-------------------------------------------
Módulo de matching semántico (GIRA-41) contra catálogos maestros institucionales.
Enlaza entidades extraídas (programas, módulos, docentes) contra la base canónica
utilizando coincidencia exacta O(1) y fallback probabilístico con RapidFuzz.

Refactorizado: Delega en CatalogRepository como single source of truth.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List

from pipeline.config import UMBRAL_CONFIANZA_ALTO
from pipeline.normalization.catalog_repository import obtener_catalogo_repositorio, CatalogRepository


class SemanticMatcher:
    """
    Motor de grounding y resolución contra catálogos maestros de GiraGroup.
    Delega en CatalogRepository (singleton) para evitar duplicación de parsing.
    """

    def __init__(self, ruta_seed_sql: Optional[Path] = None):
        self.repo: CatalogRepository = obtener_catalogo_repositorio(ruta_seed_sql)
        self.programas_por_pos = self.repo.programas_meta
        self.programas_por_nombre = self.repo._programas_por_nombre
        self.docentes_canonicos = [d["nombre_canonico"] for d in self.repo.docentes.values()]
        self.modulos_canonicos = [m["nombre_canonico"] for m in self.repo.modulos.values()]

    def enlazar_programa(
        self,
        texto_o_pos: str,
        umbral_minimo: float = UMBRAL_CONFIANZA_ALTO
    ) -> Optional[Dict[str, Any]]:
        """Enlaza un texto de programa o código numérico contra el catálogo oficial."""
        return self.repo.enlazar_programa(texto_o_pos, umbral_minimo)

    def enlazar_docente(
        self,
        nombre_extraido: str,
        umbral_minimo: float = UMBRAL_CONFIANZA_ALTO
    ) -> Optional[Dict[str, Any]]:
        """Enlaza un nombre de docente extraído contra el catálogo oficial."""
        return self.repo.enlazar_docente(nombre_extraido, umbral_minimo)

    def enlazar_modulo(
        self,
        nombre_modulo: str,
        umbral_minimo: float = UMBRAL_CONFIANZA_ALTO
    ) -> Optional[Dict[str, Any]]:
        """Enlaza el nombre de un módulo extraído contra el catálogo oficial."""
        return self.repo.enlazar_modulo(nombre_modulo, umbral_minimo)
