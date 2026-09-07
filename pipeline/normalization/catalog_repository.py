"""
pipeline/normalization/catalog_repository.py
--------------------------------------------
Repositorio centralizado y unificado de catálogos canónicos de GiraGroup BI.
Consolida la lectura y resolución contra 'seed_catalogos.sql' en una sola fuente
de verdad con caché singleton, eliminando la triplicación de parsers regex y
garantizando compatibilidad total con el pipeline semántico y de inferencia NER.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union

from pipeline.config import (
    SEED_CATALOGOS_SQL_PATH,
    DATA_DIR,
    UMBRAL_CONFIANZA_ALTO,
    UMBRAL_CONFIANZA_MEDIO,
    PATRON_POS_GENERAL,
    PREFIJOS_TITULOS
)
from pipeline.normalization.fuzzy_normalizer import FuzzyNormalizer


class CatalogRepository:
    """
    Repositorio singleton unificado de catálogos maestros institucionales.
    Carga programas, docentes, módulos, escuelas, modalidades, estados y carteras
    desde 'db/seeds/seed_catalogos.sql' una única vez.
    """
    _instance: Optional["CatalogRepository"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CatalogRepository, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, ruta_seed_sql: Optional[Union[str, Path]] = None):
        if getattr(self, "_initialized", False):
            return
        self.ruta_seed = Path(ruta_seed_sql) if ruta_seed_sql else SEED_CATALOGOS_SQL_PATH
        
        # Estructuras maestras en memoria
        self.programas: Dict[str, str] = {}  # pos -> nombre_canonico
        self.programas_meta: Dict[str, Dict[str, Any]] = {}  # pos -> {id, pos, nombre, version}
        self.docentes: Dict[str, Dict[str, Any]] = {}  # nombre_limpio -> {id, nombre_original, etc}
        self.docentes_set: set = set()  # Nombres en mayúscula para búsqueda O(1)
        self.modulos: Dict[str, Dict[str, Any]] = {}  # nombre_limpio -> {id, nombre_original}
        
        self.escuelas: List[str] = []
        self.tipos_programa: List[str] = []
        self.modalidades: List[str] = []
        self.estados_academicos: List[str] = []
        self.estados_reprobados: List[str] = []
        self.estados_arca: List[str] = []
        self.carteras: List[Dict[str, Any]] = []

        self._cargar_desde_seed()
        self._inicializar_mapeos_rapidos()
        self._initialized = True

    def _cargar_desde_seed(self) -> None:
        """Parsea seed_catalogos.sql una sola vez para poblar todas las dimensiones."""
        if not self.ruta_seed.exists():
            return

        with open(self.ruta_seed, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("--"):
                    continue

                if "INSERT INTO public.cat_programa" in line:
                    m = re.search(
                        r"VALUES\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*(\d+)",
                        line,
                        re.IGNORECASE
                    )
                    if m:
                        pos = m.group(1).strip()
                        nombre = m.group(2).strip()
                        version = int(m.group(3))
                        self.programas[pos] = nombre
                        self.programas_meta[pos] = {
                            "pos": pos,
                            "nombre": nombre,
                            "version": version
                        }

                elif "INSERT INTO public.cat_docente" in line:
                    m = re.search(r"VALUES\s*\(\s*'([^']+)'", line, re.IGNORECASE)
                    if m:
                        nom_orig = m.group(1).strip()
                        self.docentes_set.add(nom_orig.upper())
                        nom_limpio = FuzzyNormalizer.limpiar_nombre(nom_orig)
                        self.docentes[nom_limpio] = {
                            "nombre_original": nom_orig,
                            "nombre_canonico": nom_orig
                        }

                elif "INSERT INTO public.cat_modulo" in line:
                    m = re.search(
                        r"(?:SELECT\s+id_programa\s*,\s*\d+\s*,\s*|VALUES\s*\(\s*)'([^']+)'",
                        line,
                        re.IGNORECASE
                    )
                    if m:
                        mod_orig = m.group(1).strip()
                        mod_limpio = FuzzyNormalizer.limpiar_nombre(mod_orig)
                        self.modulos[mod_limpio] = {
                            "nombre_original": mod_orig,
                            "nombre_canonico": mod_orig
                        }

                elif "INSERT INTO public.cat_escuela" in line:
                    m = re.search(r"VALUES\s*\(\s*'([^']+)'", line, re.IGNORECASE)
                    if m:
                        self.escuelas.append(m.group(1).strip())

                elif "INSERT INTO public.cat_modalidad" in line:
                    m = re.search(r"VALUES\s*\(\s*'([^']+)'", line, re.IGNORECASE)
                    if m:
                        self.modalidades.append(m.group(1).strip())

                elif "INSERT INTO public.cat_estado_academico" in line:
                    m = re.search(r"VALUES\s*\(\s*'([^']+)'", line, re.IGNORECASE)
                    if m:
                        self.estados_academicos.append(m.group(1).strip())

        # Fallbacks institucionales si no estaban en el seed
        if not self.escuelas:
            self.escuelas = ["Salud", "Negocios", "Leyes", "Ciencias Sociales", "Tecnología/Ingeniería"]
        if not self.modalidades:
            self.modalidades = ["VIRTUAL SINCRÓNICO", "SEMIPRESENCIAL", "PRESENCIAL SINCRÓNICO"]
        if not self.estados_academicos:
            self.estados_academicos = ["Aprobado", "Reprobado", "Deserción", "En curso", "Participó"]
        if not self.carteras:
            self.carteras = [
                {"nombre": "Cartera Vigente", "min": 0, "max": 90},
                {"nombre": "Cartera en Mora", "min": 91, "max": 180},
                {"nombre": "Cartera Previsionable", "min": 181, "max": 360},
                {"nombre": "Cartera Incobrable", "min": 361, "max": 99999},
                {"nombre": "Cartera Cerrada", "min": -1, "max": -1},
            ]

    def _inicializar_mapeos_rapidos(self) -> None:
        """Precomputa diccionarios en minúsculas para matching léxico veloz."""
        self._escuelas_map = {e.lower(): e for e in self.escuelas}
        self._modalidades_map = {m.lower(): m for m in self.modalidades}
        self._estados_aca_map = {ea.lower(): ea for ea in self.estados_academicos}
        self._programas_por_nombre = {
            FuzzyNormalizer.limpiar_nombre(nom): pos
            for pos, nom in self.programas.items()
        }

    # ── MÉTODOS DE PROGRAMA Y POS ───────────────────────────────────────

    def normalizar_pos(self, val: Any) -> Optional[str]:
        """
        Normaliza cualquier variante de código POS a formato canónico 'POS-XXXX'.
        Maneja enteros, floats en string ('5308.0'), '5308', 'POS-5308'.
        Excluye años calendarios (2020-2030) fuera del rango POS GiraGroup (4000-7000).
        """
        if val is None:
            return None
        val_str = str(val).strip()
        if not val_str:
            return None

        # Si viene como float en string ("5308.0")
        if "." in val_str:
            parte_entera = val_str.split(".")[0]
            if parte_entera.isdigit():
                val_str = parte_entera

        m = PATRON_POS_GENERAL.search(val_str)
        if m:
            num = int(m.group(1))
            # Rango válido de códigos POS en GiraGroup (4000 a 7000)
            if 4000 <= num <= 7000:
                return f"POS-{num}"
            # Si no está en rango pero existe exactamente en el catálogo
            candidato = f"POS-{num}"
            if candidato in self.programas:
                return candidato

        # Intentar match directo en catálogo
        val_upper = val_str.upper()
        if val_upper in self.programas:
            return val_upper

        return None

    def resolver_programa(self, pos_code: Optional[str]) -> Tuple[str, str]:
        """
        Resuelve un código POS a tupla (pos_canónico, nombre_oficial).
        Compatible con CatalogoGazetteer.
        """
        pos_norm = self.normalizar_pos(pos_code)
        if pos_norm and pos_norm in self.programas:
            return pos_norm, self.programas[pos_norm]
        if pos_norm:
            return pos_norm, f"PROGRAMA {pos_norm}"
        return "POS-0000", "PROGRAMA NO IDENTIFICADO"

    def buscar_por_pos(self, pos_code: Optional[str]) -> Optional[Dict[str, Any]]:
        """Busca metadata de un programa por código POS."""
        pos_norm = self.normalizar_pos(pos_code)
        if pos_norm and pos_norm in self.programas_meta:
            return self.programas_meta[pos_norm]
        return None

    def buscar_por_alias(self, texto: Optional[str]) -> Optional[Dict[str, Any]]:
        """Búsqueda de programa por subcadena o coincidencia léxica."""
        if not texto:
            return None
        t_norm = texto.upper()
        for pos, nom in self.programas.items():
            if nom.upper() in t_norm:
                return self.programas_meta.get(pos)
        return None

    def enlazar_programa(
        self,
        texto_o_pos: str,
        umbral_minimo: float = UMBRAL_CONFIANZA_ALTO
    ) -> Optional[Dict[str, Any]]:
        """
        Enlace semántico de programa con fallback fuzzy.
        Retorna diccionario canónico {pos, nombre_canonico, score, tipo_match}.
        """
        if not texto_o_pos or not str(texto_o_pos).strip():
            return None

        texto_limpio = str(texto_o_pos).strip()

        # 1. Búsqueda O(1) directa por POS
        pos_canonico = self.normalizar_pos(texto_limpio)
        if pos_canonico and pos_canonico in self.programas:
            return {
                "pos": pos_canonico,
                "nombre_canonico": self.programas[pos_canonico],
                "score": 1.0,
                "tipo_match": "EXACTO_POS"
            }

        # 2. Búsqueda difusa por nombre de programa
        candidato_norm = FuzzyNormalizer.limpiar_nombre(texto_limpio)
        if len(candidato_norm) < 4:
            return None

        resultado_fuzzy = FuzzyNormalizer.buscar_mejor_coincidencia(
            candidato=candidato_norm,
            opciones=list(self._programas_por_nombre.keys()),
            umbral_minimo=umbral_minimo,
            metodo="token_sort"
        )

        if resultado_fuzzy:
            nombre_match, score = resultado_fuzzy
            pos_asociado = self._programas_por_nombre[nombre_match]
            return {
                "pos": pos_asociado,
                "nombre_canonico": self.programas[pos_asociado],
                "score": round(score, 4),
                "tipo_match": "FUZZY_NOMBRE_PROGRAMA"
            }

        return None

    # ── MÉTODOS DE DOCENTES ─────────────────────────────────────────────

    def es_docente_conocido(self, nombre: Optional[str]) -> bool:
        """Verifica si un nombre corresponde a un docente registrado."""
        if not nombre:
            return False
        nom_upper = nombre.strip().upper()
        if nom_upper in self.docentes_set:
            return True
        nom_limpio = FuzzyNormalizer.limpiar_nombre(nombre)
        return nom_limpio in self.docentes

    def enlazar_docente(
        self,
        nombre_extraido: str,
        umbral_minimo: float = UMBRAL_CONFIANZA_ALTO
    ) -> Optional[Dict[str, Any]]:
        """Grounding de docentes extraídos contra la nómina oficial."""
        if not nombre_extraido or not str(nombre_extraido).strip():
            return None

        candidato_norm = FuzzyNormalizer.limpiar_nombre(nombre_extraido)
        if len(candidato_norm) < 4:
            return None

        # 1. Coincidencia exacta
        if candidato_norm in self.docentes:
            return {
                "nombre_canonico": self.docentes[candidato_norm]["nombre_canonico"],
                "score": 1.0,
                "tipo_match": "EXACTO_DOCENTE"
            }

        # 2. Búsqueda difusa
        resultado_fuzzy = FuzzyNormalizer.buscar_mejor_coincidencia(
            candidato=candidato_norm,
            opciones=list(self.docentes.keys()),
            umbral_minimo=umbral_minimo,
            metodo="wratio"
        )

        if resultado_fuzzy:
            nom_match, score = resultado_fuzzy
            return {
                "nombre_canonico": self.docentes[nom_match]["nombre_canonico"],
                "score": round(score, 4),
                "tipo_match": "FUZZY_DOCENTE"
            }

        return None

    # ── MÉTODOS DE MÓDULOS ──────────────────────────────────────────────

    def enlazar_modulo(
        self,
        nombre_modulo: str,
        umbral_minimo: float = UMBRAL_CONFIANZA_ALTO
    ) -> Optional[Dict[str, Any]]:
        """Enlace semántico de módulos académicos."""
        if not nombre_modulo or not str(nombre_modulo).strip():
            return None

        candidato_norm = FuzzyNormalizer.limpiar_nombre(nombre_modulo)
        if len(candidato_norm) < 3:
            return None

        if candidato_norm in self.modulos:
            return {
                "nombre_canonico": self.modulos[candidato_norm]["nombre_canonico"],
                "score": 1.0,
                "tipo_match": "EXACTO_MODULO"
            }

        resultado_fuzzy = FuzzyNormalizer.buscar_mejor_coincidencia(
            candidato=candidato_norm,
            opciones=list(self.modulos.keys()),
            umbral_minimo=umbral_minimo,
            metodo="token_sort"
        )

        if resultado_fuzzy:
            mod_match, score = resultado_fuzzy
            return {
                "nombre_canonico": self.modulos[mod_match]["nombre_canonico"],
                "score": round(score, 4),
                "tipo_match": "FUZZY_MODULO"
            }

        return None

    # ── MÉTODOS DE ESCUELAS, MODALIDADES Y CARTERAS ────────────────────

    def resolver_escuela(
        self,
        texto_raw: str,
        umbral_minimo: float = UMBRAL_CONFIANZA_MEDIO
    ) -> Optional[Dict[str, Any]]:
        """Resuelve una escuela institucional mediante similitud difusa."""
        if not texto_raw or not str(texto_raw).strip():
            return None
        candidato = str(texto_raw).strip().lower()
        res = FuzzyNormalizer.buscar_mejor_coincidencia(
            candidato=candidato,
            opciones=list(self._escuelas_map.keys()),
            umbral_minimo=umbral_minimo,
            metodo="token_set"
        )
        if res:
            match_key, score = res
            return {
                "valor_canonico": self._escuelas_map[match_key],
                "score": round(score, 4),
                "tipo_match": "FUZZY_ESCUELA"
            }
        return None

    def resolver_modalidad(
        self,
        texto_raw: str,
        umbral_minimo: float = UMBRAL_CONFIANZA_MEDIO
    ) -> Optional[Dict[str, Any]]:
        """Resuelve modalidad académica."""
        if not texto_raw or not str(texto_raw).strip():
            return None
        candidato = str(texto_raw).strip().lower()
        res = FuzzyNormalizer.buscar_mejor_coincidencia(
            candidato=candidato,
            opciones=list(self._modalidades_map.keys()),
            umbral_minimo=umbral_minimo,
            metodo="token_set"
        )
        if res:
            match_key, score = res
            return {
                "valor_canonico": self._modalidades_map[match_key],
                "score": round(score, 4),
                "tipo_match": "FUZZY_MODALIDAD"
            }
        return None

    def resolver_estado_academico(
        self,
        texto_raw: str,
        umbral_minimo: float = UMBRAL_CONFIANZA_MEDIO
    ) -> Optional[Dict[str, Any]]:
        """Resuelve estado académico."""
        if not texto_raw or not str(texto_raw).strip():
            return None
        candidato = str(texto_raw).strip().lower()
        res = FuzzyNormalizer.buscar_mejor_coincidencia(
            candidato=candidato,
            opciones=list(self._estados_aca_map.keys()),
            umbral_minimo=umbral_minimo,
            metodo="token_set"
        )
        if res:
            match_key, score = res
            return {
                "valor_canonico": self._estados_aca_map[match_key],
                "score": round(score, 4),
                "tipo_match": "FUZZY_ESTADO_ACADEMICO"
            }
        return None

    def clasificar_cartera(self, dias_mora: Any) -> str:
        """Clasifica los días de mora en la categoría financiera correspondiente."""
        if dias_mora is None:
            return "Cartera No Clasificada"
        try:
            dias = int(float(str(dias_mora).replace(",", ".").strip()))
        except (ValueError, TypeError):
            return "Cartera No Clasificada"

        if dias < 0:
            return "Cartera Cerrada"
        for c in self.carteras:
            if c["min"] <= dias <= c["max"]:
                return c["nombre"]
        return "Cartera No Clasificada"


_repositorio_singleton: Optional[CatalogRepository] = None


def obtener_catalogo_repositorio(
    ruta_seed_sql: Optional[Union[str, Path]] = None
) -> CatalogRepository:
    """Función helper para obtener la instancia singleton del repositorio."""
    global _repositorio_singleton
    if _repositorio_singleton is None:
        _repositorio_singleton = CatalogRepository(ruta_seed_sql)
    return _repositorio_singleton
