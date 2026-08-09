"""
fk_checker.py — GIRA-50 (Semilla, Sprint 2)
Verificación de llaves foráneas: cruza los códigos POS extraídos
en las encuestas contra los registros maestros académicos.

Los registros con POS no encontrado en la base académica se marcan
con estado 'sin_llave_valida' para alimentar GIRA-27 (requiere_revisión).
"""

import logging
import unicodedata
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


from pipeline.normalization.pos_utils import extraer_codigo_pos, normalizar_pos

# Usar alias local para mantener compatibilidad con cualquier otra parte que llame a _normalizar_pos
_normalizar_pos = normalizar_pos


class ForeignKeyChecker:
    """
    Valida que los POS (códigos de programa) extraídos de encuestas
    existan en los registros maestros académicos.
    """

    def __init__(self):
        self._pos_activos: set[str] = set()
        self._pos_validos = self._pos_activos
        self._pos_de_baja: set[str] = set()
        self._cargado = False

    @property
    def cargado(self) -> bool:
        return self._cargado

    @property
    def total_pos_registrados(self) -> int:
        return len(self._pos_activos) + len(self._pos_de_baja)

    def cargar_pos_maestros(self, hojas_estructuradas: list[dict]) -> None:
        """
        Carga todos los POS válidos desde las hojas estructuradas
        (PLANIFICACION_Y_EJECUCION_ACADÉMICA, Base_centralizada_Académica_ARCA,
        TBL_INSCRITOS, etc.)

        Args:
            hojas_estructuradas: Lista de dicts de hojas del dispatcher
                con 'data' (DataFrame) y 'mapeo_columnas'.
        """
        for hoja in hojas_estructuradas:
            df = hoja.get("data")
            if df is None or df.empty:
                continue

            mapeo = hoja.get("mapeo_columnas", {})
            nombre_hoja = hoja.get("nombre_hoja", "?")

            # Buscar la columna que mapea a 'pos'
            col_pos = None
            for col_orig, campo_can in mapeo.items():
                if campo_can == "pos":
                    col_pos = col_orig
                    break

            # Si no está en el mapeo, buscar por nombre directo
            if col_pos is None:
                for col in df.columns:
                    col_lower = str(col).lower().strip()
                    if col_lower in ("pos", "codigo_pos", "código_pos", "cod_pos"):
                        col_pos = col
                        break

            if col_pos is None:
                continue

            is_baja = "baja" in nombre_hoja.lower()
            n_antes = self.total_pos_registrados
            col_series = df[col_pos]
            if isinstance(col_series, pd.DataFrame):
                col_series = col_series.iloc[:, 0]
            for val in col_series.dropna().unique():
                pos_norm = _normalizar_pos(val)
                if pos_norm:
                    if is_baja:
                        self._pos_de_baja.add(pos_norm)
                    else:
                        self._pos_activos.add(pos_norm)

            n_nuevos = self.total_pos_registrados - n_antes
            if n_nuevos > 0:
                logger.info(
                    "FKChecker: %d POS cargados desde hoja '%s' (Baja: %s).",
                    n_nuevos, nombre_hoja, is_baja,
                )

        self._cargado = True
        logger.info(
            "FKChecker listo: %d POS válidos registrados (%d activos, %d de baja).",
            self.total_pos_registrados, len(self._pos_activos), len(self._pos_de_baja)
        )

    def verificar_pos(self, pos: str) -> bool:
        """
        Verifica si un POS existe en los registros maestros (activos o de baja).

        Returns:
            True si el POS es válido, False si no se encuentra.
        """
        if not pos or not pos.strip():
            return False
        pos_norm = _normalizar_pos(pos)
        return pos_norm in self._pos_activos or pos_norm in self._pos_de_baja or pos_norm in self._pos_validos

    def verificar_documentos(self, documentos: list[dict]) -> dict:
        """
        Verifica las llaves foráneas de una lista de Documentos Mínimos
        y actualiza su estado si el POS no es válido.

        Args:
            documentos: Lista de Documentos Mínimos del document_builder.

        Returns:
            {
                "documentos_actualizados": list[dict],
                "pos_validos": int,
                "pos_de_baja": int,
                "pos_invalidos": int,
                "pos_vacios": int,
                "pos_no_encontrados": list[str],  # POS únicos que no cruzaron
            }
        """
        if not self._cargado:
            logger.warning(
                "FKChecker no tiene POS maestros cargados. "
                "Saltando verificación de llaves foráneas."
            )
            return {
                "documentos_actualizados": documentos,
                "pos_validos": 0,
                "pos_de_baja": 0,
                "pos_invalidos": 0,
                "pos_vacios": 0,
                "pos_no_encontrados": [],
            }

        pos_invalidos_set = set()
        n_validos = 0
        n_baja = 0
        n_invalidos = 0
        n_vacios = 0

        for doc in documentos:
            # Solo verificar documentos que no estén ya descartados
            if doc.get("estado") == "vacio_descartado":
                continue

            pos = doc.get("llaves_relacion", {}).get("POS", "")

            if not pos:
                n_vacios += 1
                if doc.get("estado") != "sin_llave_valida":
                    doc["estado"] = "sin_llave_valida"
                continue

            pos_norm = _normalizar_pos(pos)

            if pos_norm in self._pos_activos or pos_norm in self._pos_validos:
                n_validos += 1
                doc["estado"] = "ok"
            elif pos_norm in self._pos_de_baja:
                n_baja += 1
                doc["estado"] = "pos_valido_dado_de_baja"
            else:
                n_invalidos += 1
                pos_invalidos_set.add(pos)
                doc["estado"] = "sin_llave_valida"

        if pos_invalidos_set:
            logger.warning(
                "FKChecker: %d POS no encontrados en maestros: %s",
                len(pos_invalidos_set),
                list(pos_invalidos_set)[:10],
            )

        return {
            "documentos_actualizados": documentos,
            "pos_validos": n_validos,
            "pos_de_baja": n_baja,
            "pos_invalidos": n_invalidos,
            "pos_vacios": n_vacios,
            "pos_no_encontrados": sorted(pos_invalidos_set),
        }
