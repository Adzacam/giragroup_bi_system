"""
normalizer.py — Normalizador Semántico Determinista y Grounding contra Catálogos 3NF

Utiliza rapidfuzz para resolver variaciones tipográficas, errores ortográficos,
abreviaciones y versiones numéricas en las planillas crudas de uploads/data/ contra
los catálogos canónicos de referencia institucional (sin sobreingeniería de LLMs).
"""

import json
import os
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from rapidfuzz import fuzz, process


@dataclass
class MatchResult:
    valor_canonico: str
    id_referencia: Optional[int]
    confianza: float
    extra: Dict[str, Any]


class CatalogMatcher:
    """
    Cargador y resolvedor de entidades canónicas usando similitud de cadenas.
    Puede inicializarse desde diccionarios en memoria, base de datos o archivo seed.
    """

    def __init__(self, catalogos: Optional[Dict[str, Any]] = None):
        if catalogos is None:
            self.catalogos = self._cargar_catalogos_defecto()
        else:
            self.catalogos = catalogos

        # Precomputar listas para búsqueda rápida con rapidfuzz
        self._escuelas_map = {e.lower(): e for e in self.catalogos.get("escuelas", [])}
        self._tipos_map = {t.lower(): t for t in self.catalogos.get("tipos_programa", [])}
        self._modalidades_map = {m.lower(): m for m in self.catalogos.get("modalidades", [])}
        self._estados_aca_map = {ea.lower(): ea for ea in self.catalogos.get("estados_academicos", [])}
        self._estados_rep_map = {er.lower(): er for er in self.catalogos.get("estados_reprobados", [])}
        self._estados_arca_map = {ar.lower(): ar for ar in self.catalogos.get("estados_arca", [])}
        self._programas = self.catalogos.get("programas", {})
        self._docentes = self.catalogos.get("docentes", {})

    def _cargar_catalogos_defecto(self) -> Dict[str, Any]:
        """Carga los catálogos canónicos directamente desde el extractor."""
        from db.seeds.populate_catalogos import extraer_datos_catalogos
        dir_datos = "uploads/data"
        if os.path.exists(dir_datos):
            try:
                return extraer_datos_catalogos(dir_datos)
            except Exception as e:
                print(f"Aviso: no se pudo cargar uploads/data dinámicamente ({e}). Usando estáticos.")

        # Fallback estático institucional base
        return {
            "escuelas": ["Salud", "Negocios", "Leyes", "Ciencias Sociales", "Tecnología/Ingeniería"],
            "tipos_programa": ["DIPLOMADO", "CURSO", "MAESTRÍA"],
            "modalidades": ["VIRTUAL SINCRÓNICO", "SEMIPRESENCIAL", "PRESENCIAL SINCRÓNICO"],
            "estados_academicos": ["Aprobado", "Reprobado", "Deserción", "En curso", "Participó"],
            "estados_reprobados": ["Insuficiencia académica", "Abandono", "Congelamiento", "Tutoría"],
            "estados_arca": ["Titulado", "No Titulado"],
            "programas": {},
            "docentes": {},
            "carteras": [
                {"nombre": "Cartera Vigente", "min": 0, "max": 90},
                {"nombre": "Cartera en Mora", "min": 91, "max": 180},
                {"nombre": "Cartera Previsionable", "min": 181, "max": 360},
                {"nombre": "Cartera Incobrable", "min": 361, "max": 99999},
                {"nombre": "Cartera Cerrada", "min": -1, "max": -1},
            ],
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Resolución de Escuelas
    # ──────────────────────────────────────────────────────────────────────────
    def resolver_escuela(self, texto_raw: str, umbral_minimo: float = 70.0) -> Optional[MatchResult]:
        if not texto_raw or not str(texto_raw).strip():
            return None
        candidato = str(texto_raw).strip()
        opciones = list(self._escuelas_map.keys())
        res = process.extractOne(candidato.lower(), opciones, scorer=fuzz.token_set_ratio)
        if res and res[1] >= umbral_minimo:
            nombre_canonico = self._escuelas_map[res[0]]
            return MatchResult(
                valor_canonico=nombre_canonico,
                id_referencia=None,
                confianza=round(res[1] / 100.0, 4),
                extra={"score_fuzz": res[1]}
            )
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Resolución de Modalidades
    # ──────────────────────────────────────────────────────────────────────────
    def resolver_modalidad(self, texto_raw: str, umbral_minimo: float = 75.0) -> Optional[MatchResult]:
        if not texto_raw or not str(texto_raw).strip():
            return None
        candidato = str(texto_raw).strip()
        opciones = list(self._modalidades_map.keys())
        res = process.extractOne(candidato.lower(), opciones, scorer=fuzz.token_set_ratio)
        if res and res[1] >= umbral_minimo:
            nombre_canonico = self._modalidades_map[res[0]]
            return MatchResult(
                valor_canonico=nombre_canonico,
                id_referencia=None,
                confianza=round(res[1] / 100.0, 4),
                extra={"score_fuzz": res[1]}
            )
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Resolución de Estados Académicos
    # ──────────────────────────────────────────────────────────────────────────
    def resolver_estado_academico(self, texto_raw: str, umbral_minimo: float = 75.0) -> Optional[MatchResult]:
        if not texto_raw or not str(texto_raw).strip():
            return None
        candidato = str(texto_raw).strip()
        opciones = list(self._estados_aca_map.keys())
        res = process.extractOne(candidato.lower(), opciones, scorer=fuzz.token_set_ratio)
        if res and res[1] >= umbral_minimo:
            nombre_canonico = self._estados_aca_map[res[0]]
            return MatchResult(
                valor_canonico=nombre_canonico,
                id_referencia=None,
                confianza=round(res[1] / 100.0, 4),
                extra={"score_fuzz": res[1]}
            )
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Resolución de Programas y Versiones
    # ──────────────────────────────────────────────────────────────────────────
    def resolver_programa(self, pos_o_texto: str, umbral_minimo: float = 70.0) -> Optional[MatchResult]:
        """
        Resuelve un programa buscando primero por POS directo O(1).
        Si no es POS, detecta la versión en el texto y busca por similitud
        contra los nombres canónicos de cat_programa.
        """
        if not pos_o_texto or not str(pos_o_texto).strip():
            return None
        txt = str(pos_o_texto).strip()

        # 1. Búsqueda directa por código POS
        match_pos = re.search(r'POS[-_ ]?(\d+)', txt, re.IGNORECASE)
        if match_pos:
            pos_key = f"POS-{match_pos.group(1)}"
            if pos_key in self._programas:
                prg = self._programas[pos_key]
                return MatchResult(
                    valor_canonico=prg["nombre_programa"],
                    id_referencia=None,
                    confianza=1.0,
                    extra={
                        "pos_code": pos_key,
                        "version": prg.get("version", 1),
                        "escuela": prg.get("escuela"),
                        "tipo_programa": prg.get("tipo_programa"),
                        "modalidad": prg.get("modalidad"),
                    }
                )

        # 2. Extracción de versión en texto (ej: "v. 28", "v27", "V14")
        match_ver = re.search(r'\bv\.?\s*(\d+)', txt, re.IGNORECASE)
        version_detectada = int(match_ver.group(1)) if match_ver else 1
        texto_limpio = re.sub(r'\bv\.?\s*\d+', '', txt, flags=re.IGNORECASE).strip()

        # 3. Fuzzy matching contra nombres canónicos
        candidatos = {p["pos_code"]: p["nombre_programa"] for p in self._programas.values()}
        if not candidatos:
            return None

        pos_codes = list(candidatos.keys())
        nombres = [candidatos[k] for k in pos_codes]

        res = process.extractOne(texto_limpio, nombres, scorer=fuzz.token_sort_ratio)
        if res and res[1] >= umbral_minimo:
            idx = res[2]
            pos_code_encontrado = pos_codes[idx]
            prg = self._programas[pos_code_encontrado]

            return MatchResult(
                valor_canonico=prg["nombre_programa"],
                id_referencia=None,
                confianza=round(res[1] / 100.0, 4),
                extra={
                    "pos_code": pos_code_encontrado,
                    "version": version_detectada if match_ver else prg.get("version", 1),
                    "escuela": prg.get("escuela"),
                    "tipo_programa": prg.get("tipo_programa"),
                    "score_fuzz": res[1],
                }
            )

        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Clasificación de Cartera por Días de Mora
    # ──────────────────────────────────────────────────────────────────────────
    def clasificar_cartera(self, dias_mora: Any) -> str:
        """Determina la cartera correspondiente según los días de retraso."""
        if dias_mora is None or str(dias_mora).strip() == "" or str(dias_mora).strip() == "-":
            return "Cartera Vigente"
        try:
            dias = int(float(dias_mora))
        except (ValueError, TypeError):
            return "Cartera Vigente"

        if dias < 0:
            return "Cartera Cerrada"
        elif 0 <= dias <= 90:
            return "Cartera Vigente"
        elif 91 <= dias <= 180:
            return "Cartera en Mora"
        elif 181 <= dias <= 360:
            return "Cartera Previsionable"
        else:
            return "Cartera Incobrable"
