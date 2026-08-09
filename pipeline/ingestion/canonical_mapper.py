"""
canonical_mapper.py — GIRA-11 (Sprint 2 — refactorizado)
Resuelve nombres de columna entrantes contra el diccionario canónico
usando:
1. Coincidencia exacta
2. Coincidencia difusa (RapidFuzz con threshold configurable)
3. Validación por Perfil de Contenido (Defensa Primaria)
4. Anti-Aliases / Reglas de Exclusión (Salvavidas secundario)
5. Bloqueo estructural de 'docente' en encuestas (solo written por enricher)
"""

import json
import logging
import unicodedata
import re
from pathlib import Path
from typing import Optional, Any

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# Ruta por defecto del diccionario canónico
_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_DICT_PATH = _CONFIG_DIR / "canonical_dictionary.json"


class CanonicalMapper:
    """
    Mapea nombres de columna heterogéneos a etiquetas canónicas
    con validación por perfil de contenido y reglas de exclusión.
    """

    def __init__(self, dict_path: Optional[str] = None):
        path = Path(dict_path) if dict_path else _DICT_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Diccionario canónico no encontrado: {path}. "
                "Crear pipeline/config/canonical_dictionary.json"
            )
        with open(path, "r", encoding="utf-8") as f:
            self._dict = json.load(f)

        self._config = self._dict.get("config", {})
        self._threshold = self._config.get("matching_threshold", 88.0)

        # Cargar anti_aliases: campo_canonico -> lista de alias prohibidos
        self._anti_aliases: dict[str, set[str]] = {}
        for campo, prohibidos in self._dict.get("anti_aliases", {}).items():
            self._anti_aliases[campo] = {self._normalizar(p) for p in prohibidos}

        # Construir índice invertido: alias_normalizado → campo_canónico
        self._indice_exacto: dict[str, str] = {}
        self._alias_pool: list[tuple[str, str]] = []

        for seccion in ("campos_estructurales", "preguntas_abiertas"):
            bloque = self._dict.get(seccion, {})
            for campo_canonico, meta in bloque.items():
                for alias in meta.get("aliases", []):
                    alias_norm = self._normalizar(alias)
                    self._indice_exacto[alias_norm] = campo_canonico
                    self._alias_pool.append((alias_norm, campo_canonico))

        # Cargar campos de preguntas abiertas específicas (especifica: true)
        self._campos_preguntas_especificas: set[str] = set()
        for campo, meta in self._dict.get("preguntas_abiertas", {}).items():
            if meta.get("especifica") is True:
                self._campos_preguntas_especificas.add(campo)

        # Patrones de hojas descartables
        self._patrones_descartables = (
            self._dict
            .get("hojas_descartables", {})
            .get("patrones_nombre", [])
        )
        self._razones_descarte = (
            self._dict
            .get("hojas_descartables", {})
            .get("razones_descarte", {})
        )

        logger.info(
            "CanonicalMapper inicializado: %d aliases exactos, threshold=%.1f%%",
            len(self._indice_exacto), self._threshold,
        )

    @staticmethod
    def _normalizar(texto: str) -> str:
        """Minúsculas, sin tildes, sin caracteres especiales, sin espacios extra."""
        t = str(texto).strip().lower()
        # Normalizar prefijos numéricos de preguntas (ej: '6. ', 'a 7. ', '10. n°', etc.)
        t = re.sub(r"^(?:[a-z]\s*)?\d+(?:[\.\)\-\:]|\s+)(?:\s*(?:n[°º]|nro)\.?)?\s*", "", t, flags=re.IGNORECASE)
        t = "".join(
            ch for ch in unicodedata.normalize("NFD", t)
            if unicodedata.category(ch) != "Mn"
        )
        t = re.sub(r"[_\s]+", " ", t).strip()
        return t

    @property
    def threshold(self) -> float:
        return self._threshold

    @property
    def config(self) -> dict:
        return dict(self._config)

    def _es_anti_alias(self, campo_canonico: str, norm_col: str) -> bool:
        """Verifica si la columna normalizada está explícitamente prohibida para este campo."""
        if campo_canonico in self._anti_aliases:
            if norm_col in self._anti_aliases[campo_canonico]:
                return True
        return False

    def resolver_columna(
        self,
        nombre_columna: str,
        perfil_columna: Optional[Any] = None,
        es_encuesta: bool = False,
        df: Optional[Any] = None,
    ) -> tuple[Optional[str], str, float]:
        """
        Resuelve un nombre de columna a su etiqueta canónica con
        validación por perfil de contenido y reglas de exclusión.

        Args:
            nombre_columna: Nombre de la columna fuente.
            perfil_columna: Objeto ColumnProfile opcional de profiler.py.
            es_encuesta: True si la hoja es de tipo encuesta / texto_libre.
            df: DataFrame de origen opcional para resolución dinámica por contenido.

        Returns:
            (campo_canonico | None, metodo_match, score)
        """
        norm = self._normalizar(nombre_columna)

        # Regla especial dinámica: si el nombre es exactamente 'programa'
        if norm == "programa":
            if df is not None and nombre_columna in df.columns:
                series = df[nombre_columna].dropna().astype(str)
                # Contar coincidencias con formato POS (ej: POS-XXXX o puro numérico de 4 dígitos)
                pos_matches = sum(1 for v in series if re.search(r"\b(POS-[a-zA-Z0-9]{2,4})\b", v, re.IGNORECASE))
                numeric_matches = sum(1 for v in series if v.isdigit() and len(v) == 4)
                total_non_empty = len(series)
                if total_non_empty > 0 and (pos_matches / total_non_empty > 0.5 or numeric_matches / total_non_empty > 0.5):
                    return "pos", "EXACTO", 100.0
                else:
                    return "nombre_programa", "EXACTO", 100.0

        # REGLA DURA 1: docente NUNCA se mapea desde columnas directas en encuestas
        if es_encuesta:
            # Si el target sugerido es docente, se bloquea (solo entity_enricher lo escribe)
            pass

        # Nivel 1: Coincidencia exacta
        if norm in self._indice_exacto:
            campo = self._indice_exacto[norm]
            if not self._es_anti_alias(campo, norm):
                if not (es_encuesta and campo == "docente"):
                    return campo, "EXACTO", 100.0

        # Nivel 2: Coincidencia difusa con validación de perfil
        mejor_score = 0.0
        mejor_campo = None

        for alias_norm, campo in self._alias_pool:
            # Regla dura: docente bloqueado en encuestas
            if es_encuesta and campo == "docente":
                continue

            # Regla de exclusión / anti-alias
            if self._es_anti_alias(campo, norm):
                continue

            score = fuzz.token_sort_ratio(norm, alias_norm)
            if score > mejor_score:
                mejor_score = score
                mejor_campo = campo

        if mejor_score >= self._threshold and mejor_campo is not None:
            # Defensa Primaria: Validación de Perfil de Contenido
            if perfil_columna is not None:
                valido = self._validar_perfil_contenido(mejor_campo, perfil_columna, norm)
                if not valido:
                    logger.warning(
                        "Match difuso rechazada por perfil de contenido: '%s' → '%s' (score=%.1f%%)",
                        nombre_columna, mejor_campo, mejor_score,
                    )
                    return None, "RECHAZADO_POR_PERFIL", mejor_score

            logger.info(
                "Fuzzy match: '%s' → '%s' (score=%.1f%%)",
                nombre_columna, mejor_campo, mejor_score,
            )
            return mejor_campo, "FUZZY", mejor_score

        return None, "NO_MATCH", mejor_score

    def _validar_perfil_contenido(self, campo_canonico: str, perfil: Any, norm_col: str) -> bool:
        """
        Valida que el contenido real de la columna coincida con
        el perfil semántico esperado para el campo canónico destino.
        """
        # identificador_persona (CI): exige CI regex o email. Rechaza secuencias o texto largo.
        if campo_canonico == "identificador_persona":
            # Si el contenido es puramente numérico corto tipo secuencia (nulos/cardinalidad baja)
            if getattr(perfil, "pct_numerico", 0) > 0.8:
                # Si la longitud promedio es muy corta (ej: 1-3 dígitos = fila_id), rechazar
                if getattr(perfil, "longitud_promedio", 0) < 5 and getattr(perfil, "pct_ci", 0) < 0.3:
                    return False
            # Si es texto largo de opinión, no es CI
            if getattr(perfil, "rol_inferido", "") == "texto_libre":
                return False

        # nombre_programa: no debe ser un nombre propio de persona, secuencia o estado
        if campo_canonico == "nombre_programa":
            if any(term in norm_col for term in ["nombre completo", "nombres", "apellido", "estado"]):
                return False

        # pos: no debe ser una columna de opinión/texto libre
        if campo_canonico == "pos":
            if getattr(perfil, "rol_inferido", "") == "texto_libre":
                return False

        return True

    def resolver_columnas_df(
        self,
        columnas: list[str],
        perfiles_map: Optional[dict[str, Any]] = None,
        es_encuesta: bool = False,
        df: Optional[Any] = None,
    ) -> dict:
        """
        Resuelve una lista de columnas usando perfil de contenido opcional.
        """
        mapeo = {}
        no_mapeadas = []
        stats = {"exactas": 0, "fuzzy": 0, "no_match": 0}

        perfiles_map = perfiles_map or {}

        for col in columnas:
            perfil = perfiles_map.get(col)
            campo, metodo, score = self.resolver_columna(
                col, perfil_columna=perfil, es_encuesta=es_encuesta, df=df
            )
            mapeo[col] = campo

            if metodo == "EXACTO":
                stats["exactas"] += 1
            elif metodo == "FUZZY":
                stats["fuzzy"] += 1
            else:
                stats["no_match"] += 1
                mejor_candidato = None
                if self._alias_pool:
                    norm = self._normalizar(col)
                    candidatos = [
                        x for x in self._alias_pool
                        if not self._es_anti_alias(x[1], norm)
                    ]
                    if candidatos:
                        mejor = max(
                            candidatos,
                            key=lambda x: fuzz.token_sort_ratio(norm, x[0]),
                        )
                        mejor_candidato = mejor[1]
                no_mapeadas.append({
                    "columna": col,
                    "mejor_score": score,
                    "mejor_candidato": mejor_candidato,
                })

        return {
            "mapeo": mapeo,
            "no_mapeadas": no_mapeadas,
            "estadisticas": stats,
        }

    def es_hoja_descartable(self, nombre_hoja: str) -> tuple[bool, Optional[str]]:
        """Determina si una hoja debe descartarse por su nombre."""
        nombre_norm = self._normalizar(nombre_hoja)

        for patron in self._patrones_descartables:
            patron_norm = self._normalizar(patron)
            if patron_norm in nombre_norm:
                if any(p in patron_norm for p in ["copia", "borrador", "boor"]):
                    return True, "HOJA_DUPLICADA_BORRADOR"
                if any(p in patron_norm for p in ["tabla dinamica", "pivot", "pivote"]):
                    return True, "TABLA_DINAMICA"
                if any(p in patron_norm for p in ["dashboard", "resumen"]):
                    return True, "DASHBOARD_SIN_DATOS"
                return True, "HOJA_DUPLICADA_BORRADOR"

        return False, None

    def es_campo_pregunta_especifica(self, campo_canonico: str) -> bool:
        """Retorna True si el campo canónico es una pregunta abierta de encuesta específica."""
        return campo_canonico in self._campos_preguntas_especificas
