"""
entity_enricher.py — Sprint 2
Enriquecimiento relacional previo a la construcción del Documento Mínimo.

Resuelve el problema: las hojas de encuesta NO contienen la columna DOCENTE.
El nombre del docente solo existe en la hoja MODULOS de
Base_centralizada_Académica_ARCA, indexada por (POS, MÓDULO).

Este módulo construye un índice en memoria del cruce (POS, MÓDULO) → DOCENTE
y lo aplica a cada registro de encuesta ANTES de que document_builder.py
genere el contrato de salida.
"""

import logging
import unicodedata
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def extraer_codigo_pos(valor: str) -> str:
    """
    Extrae el patrón POS-XXXX de un string.
    Ej: 'Maestría en Finanzas / POS-028' -> 'POS-028'
    """
    if not valor:
        return ""
    import re
    match = re.search(r"\b(POS-[a-zA-Z0-9_-]+)\b", str(valor), re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return str(valor).strip()


def _normalizar_clave(valor) -> str:
    """Normaliza un valor para usarlo como clave de cruce."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    
    val_str = str(valor)
    # Extraer POS si corresponde
    if "pos" in val_str.lower():
        val_str = extraer_codigo_pos(val_str)
        
    t = val_str.strip().lower()
    # Remover tildes para comparación robusta
    t = "".join(
        ch for ch in unicodedata.normalize("NFD", t)
        if unicodedata.category(ch) != "Mn"
    )
    return t


class EntityEnricher:
    """
    Enriquece registros de encuesta con datos que solo existen
    en hojas maestras de datos académicos (ej: DOCENTE desde ARCA).
    """

    def __init__(self):
        # Índice de (pos_norm, modulo_norm) → nombre_docente
        self._indice_docente: dict[tuple[str, str], str] = {}
        # Índice de pos_norm → nombre_programa
        self._indice_programa: dict[str, str] = {}
        self._cargado = False

    @property
    def cargado(self) -> bool:
        return self._cargado

    @property
    def total_docentes(self) -> int:
        return len(self._indice_docente)

    @property
    def total_programas(self) -> int:
        return len(self._indice_programa)

    def cargar_desde_dataframes(
        self,
        hojas_estructuradas: list[dict],
        col_pos: str = "pos",
        col_modulo: str = "modulo",
        col_docente: str = "docente",
        col_programa: str = "nombre_programa",
    ) -> None:
        """
        Construye los índices de enriquecimiento a partir de las hojas
        clasificadas como estructurado_relacional por el dispatcher.

        Busca las columnas relevantes en los mapeos canónicos de cada hoja.
        Si no encuentra el campo canónico, busca por nombre directo.

        Args:
            hojas_estructuradas: Lista de dicts de hojas estructuradas
                del dispatcher. Cada dict tiene 'data' (DataFrame) y
                'mapeo_columnas' (dict original→canónico).
        """
        for hoja in hojas_estructuradas:
            df = hoja.get("data")
            if df is None or df.empty:
                continue

            mapeo = hoja.get("mapeo_columnas", {})
            nombre_hoja = hoja.get("nombre_hoja", "?")

            # Invertir mapeo: canónico → columna original
            inv_mapeo = {}
            for col_orig, campo_can in mapeo.items():
                if campo_can:
                    inv_mapeo.setdefault(campo_can, col_orig)

            # Resolver columnas reales
            col_pos_real = inv_mapeo.get(col_pos) or self._buscar_columna(df, col_pos)
            col_mod_real = inv_mapeo.get(col_modulo) or self._buscar_columna(df, col_modulo)
            if col_mod_real == col_pos_real:
                col_mod_real = None
            col_doc_real = inv_mapeo.get(col_docente) or self._buscar_columna(df, col_docente)
            col_prog_real = inv_mapeo.get(col_programa) or self._buscar_columna(df, col_programa)
            if col_prog_real == col_pos_real:
                col_prog_real = None

            # Construir índice POS+MÓDULO → DOCENTE
            if col_pos_real and col_mod_real and col_doc_real:
                n_antes = len(self._indice_docente)
                for _, row in df.iterrows():
                    pos_val = _normalizar_clave(row.get(col_pos_real))
                    mod_val = _normalizar_clave(row.get(col_mod_real))
                    doc_val = str(row.get(col_doc_real, "")).strip()

                    if pos_val and mod_val and doc_val:
                        self._indice_docente[(pos_val, mod_val)] = doc_val

                n_nuevos = len(self._indice_docente) - n_antes
                if n_nuevos > 0:
                    logger.info(
                        "EntityEnricher: %d registros POS+MÓDULO→DOCENTE cargados "
                        "desde hoja '%s'.",
                        n_nuevos, nombre_hoja,
                    )

            # Construir índice POS → NOMBRE_PROGRAMA
            if col_pos_real and col_prog_real:
                n_antes = len(self._indice_programa)
                for _, row in df.iterrows():
                    pos_val = _normalizar_clave(row.get(col_pos_real))
                    prog_val = str(row.get(col_prog_real, "")).strip()

                    if pos_val and prog_val:
                        self._indice_programa[pos_val] = prog_val

                n_nuevos = len(self._indice_programa) - n_antes
                if n_nuevos > 0:
                    logger.info(
                        "EntityEnricher: %d registros POS→PROGRAMA cargados "
                        "desde hoja '%s'.",
                        n_nuevos, nombre_hoja,
                    )

        self._cargado = True
        logger.info(
            "EntityEnricher listo: %d docentes, %d programas en índice.",
            self.total_docentes, self.total_programas,
        )

    @staticmethod
    def _buscar_columna(df: pd.DataFrame, nombre_canonico: str) -> Optional[str]:
        """Busca una columna por coincidencia de nombre si no estaba en el mapeo."""
        nombre_norm = nombre_canonico.lower().replace("_", "")
        for col in df.columns:
            col_norm = str(col).lower().replace("_", "").replace(" ", "")
            if len(col_norm) >= 4 and (nombre_norm in col_norm or col_norm in nombre_norm):
                return str(col)
        return None

    def buscar_docente(self, pos: str, modulo: str) -> Optional[str]:
        """
        Busca el nombre del docente por cruce (POS, MÓDULO).

        Returns:
            Nombre del docente o None si no se encuentra.
        """
        pos_norm = _normalizar_clave(pos)
        mod_norm = _normalizar_clave(modulo)

        if not pos_norm or not mod_norm:
            return None

        return self._indice_docente.get((pos_norm, mod_norm))

    def buscar_programa(self, pos: str) -> Optional[str]:
        """
        Busca el nombre del programa por POS.

        Returns:
            Nombre del programa o None.
        """
        pos_norm = _normalizar_clave(pos)
        if not pos_norm:
            return None

        return self._indice_programa.get(pos_norm)

    def enriquecer_registro(self, registro: dict, mapeo_columnas: dict) -> dict:
        """
        Enriquece un registro individual de encuesta con DOCENTE y
        NOMBRE_PROGRAMA si están disponibles en el índice.

        Args:
            registro: Dict con los datos de una fila de encuesta.
            mapeo_columnas: Mapeo de columna_original → campo_canónico.

        Returns:
            Dict del registro con campos enriquecidos agregados:
            _docente_enriquecido, _programa_enriquecido
        """
        # Invertir mapeo para encontrar las columnas originales
        inv = {}
        for col_orig, campo_can in mapeo_columnas.items():
            if campo_can:
                inv.setdefault(campo_can, col_orig)

        # Obtener POS y MÓDULO del registro
        col_pos = inv.get("pos")
        col_mod = inv.get("modulo")

        pos_val = ""
        mod_val = ""

        if col_pos and col_pos in registro:
            pos_val = str(registro[col_pos]).strip()
        else:
            # Buscar directamente
            for k, v in registro.items():
                if "pos" in _normalizar_clave(k):
                    pos_val = str(v).strip()
                    break

        if col_mod and col_mod in registro:
            mod_val = str(registro[col_mod]).strip()
        else:
            for k, v in registro.items():
                kn = _normalizar_clave(k)
                if "modulo" in kn or "materia" in kn:
                    mod_val = str(v).strip()
                    break

        # Enriquecer
        registro["_docente_enriquecido"] = self.buscar_docente(pos_val, mod_val)
        registro["_programa_enriquecido"] = self.buscar_programa(pos_val)

        return registro
