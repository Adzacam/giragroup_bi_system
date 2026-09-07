"""
pipeline/normalization/fk_resolver.py
--------------------------------------
Resolución y validación inteligente de llaves foráneas (CI / Nombre) (GIRA-50).
Implementa la máquina de estados A/B/C:
- Estado A: CI presente y sintácticamente válido -> Enlace directo.
- Estado B: CI ausente/corrupto -> Búsqueda difusa por Nombre Completo en TBL_INSCRITOS.
- Estado C: No resuelto -> Asignación de CI sintético temporal 'TEMP-CI-XXXX' y auditoría.
"""

import hashlib
import re
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
from pipeline.config import DATA_DIR, UMBRAL_CONFIANZA_ALTO, UMBRAL_CONFIANZA_BAJO, PATRON_CI_BOLIVIA
from pipeline.normalization.fuzzy_normalizer import FuzzyNormalizer


class FKResolver:
    """
    Resolvedor de llaves foráneas de estudiantes y participantes.
    Mantiene en memoria el padrón canónico de TBL_INSCRITOS para rescate de CI por nombre.
    """

    def __init__(self, ruta_inscritos: Optional[Path] = None):
        self.ruta_inscritos = ruta_inscritos or (DATA_DIR / "TBL_INSCRITOS.xlsx")
        self.padron_nombres: Dict[str, str] = {}  # nombre_limpio -> ci
        self.nombres_originales: Dict[str, str] = {}  # nombre_limpio -> nombre_original
        self._cargar_padron()

    def _cargar_padron(self):
        """Carga el padrón de TBL_INSCRITOS en memoria mapeando nombre a CI."""
        if not self.ruta_inscritos.exists():
            return

        try:
            # Leer el archivo con pandas
            df = pd.read_excel(self.ruta_inscritos, dtype=str)
            # Buscar columnas de CI y Nombre
            col_ci = None
            col_nom = None

            for col in df.columns:
                c_upper = str(col).strip().upper()
                if c_upper in ("CI", "CARNET", "CEDULA", "NRO_DOCUMENTO", "DOCUMENTO"):
                    col_ci = col
                elif "NOMBRE" in c_upper or "ESTUDIANTE" in c_upper or "POSTULANTE" in c_upper:
                    if col_nom is None or "COMPLETO" in c_upper:
                        col_nom = col

            if col_ci and col_nom:
                for _, row in df[[col_ci, col_nom]].dropna().iterrows():
                    ci_val = self.limpiar_ci(row[col_ci])
                    nom_val = str(row[col_nom]).strip()
                    if ci_val and nom_val:
                        nom_limpio = FuzzyNormalizer.limpiar_nombre(nom_val)
                        if nom_limpio and nom_limpio not in self.padron_nombres:
                            self.padron_nombres[nom_limpio] = ci_val
                            self.nombres_originales[nom_limpio] = nom_val
        except Exception as e:
            # Fallback tolerante si no se puede abrir el Excel en el entorno
            pass

    @staticmethod
    def limpiar_ci(ci_raw: Any) -> Optional[str]:
        """
        Normaliza el formato del CI: elimina puntos, espacios y convierte a mayúsculas.
        Verifica que cumpla con el estándar de longitud y caracteres de CI boliviano.
        """
        if ci_raw is None:
            return None
        txt = str(ci_raw).strip()
        if not txt or txt.lower() in ("nan", "none", "null", "0", "-", "."):
            return None

        # Si termina en .0 por conversión de float
        if txt.endswith(".0"):
            txt = txt[:-2]

        # Eliminar puntos de miles comunes (ej. 4.859.201 -> 4859201)
        txt = txt.replace(".", "").replace(" ", "").upper()

        if PATRON_CI_BOLIVIA.match(txt):
            return txt

        # Si contiene dígitos válidos entre 5 y 9 dígitos
        m = re.search(r'\b(\d{5,9}(?:-[0-9A-Z]{1,3})?)\b', txt)
        if m:
            return m.group(1)

        return None

    @staticmethod
    def generar_ci_sintetico(nombre: str) -> str:
        """
        Genera un identificador sintético determinista para registros sin CI:
        TEMP-CI-<HASH-8-CHARS>.
        """
        semilla = FuzzyNormalizer.limpiar_nombre(nombre or "DESCONOCIDO")
        hash_digest = hashlib.md5(semilla.encode("utf-8")).hexdigest()[:8].upper()
        return f"TEMP-CI-{hash_digest}"

    def resolver_estudiante(
        self,
        nombre: Optional[str] = None,
        ci_candidato: Optional[str] = None,
        umbral_minimo: float = UMBRAL_CONFIANZA_ALTO
    ) -> Dict[str, Any]:
        """
        Máquina de estados para resolver la llave del estudiante:
        - Estado A: CI válido directo.
        - Estado B: CI ausente -> rescate por nombre en padrón de inscritos.
        - Estado C: No resuelto -> generación de CI temporal y auditoría.
        """
        nombre_str = (nombre or "").strip()

        # ─── ESTADO A: CI Presente y Válido ──────────────────────────────────
        ci_limpio = self.limpiar_ci(ci_candidato)
        if ci_limpio:
            return {
                "ci": ci_limpio,
                "estado_resolucion": "ESTADO_A_CI_VALIDO",
                "score": 1.0,
                "es_sintetico": False,
                "requiere_auditoria": False,
                "nombre_resuelto": nombre_str
            }

        # ─── ESTADO B: CI Ausente / Inválido -> Búsqueda por Nombre en Padrón ─
        if nombre_str and self.padron_nombres:
            n_limpio = FuzzyNormalizer.limpiar_nombre(nombre_str)

            # 1. Búsqueda exacta en padrón
            if n_limpio in self.padron_nombres:
                return {
                    "ci": self.padron_nombres[n_limpio],
                    "estado_resolucion": "ESTADO_B_CI_HEREDADO_EXACTO",
                    "score": 1.0,
                    "es_sintetico": False,
                    "requiere_auditoria": False,
                    "nombre_resuelto": self.nombres_originales.get(n_limpio, nombre_str)
                }

            # 2. Búsqueda difusa en padrón con RapidFuzz
            mejor = FuzzyNormalizer.buscar_mejor_coincidencia(
                nombre_str,
                list(self.padron_nombres.keys()),
                umbral_minimo=umbral_minimo,
                metodo="token_sort"
            )
            if mejor:
                nom_padron_match, score = mejor
                return {
                    "ci": self.padron_nombres[nom_padron_match],
                    "estado_resolucion": "ESTADO_B_CI_HEREDADO_FUZZY",
                    "score": score,
                    "es_sintetico": False,
                    "requiere_auditoria": False,
                    "nombre_resuelto": self.nombres_originales.get(nom_padron_match, nombre_str)
                }

        # ─── ESTADO C: No Resuelto -> Generación Sintética y Flag Auditoría ──
        ci_sintetico = self.generar_ci_sintetico(nombre_str)
        return {
            "ci": ci_sintetico,
            "estado_resolucion": "ESTADO_C_NO_RESUELTO_SINTETICO",
            "score": UMBRAL_CONFIANZA_BAJO,
            "es_sintetico": True,
            "requiere_auditoria": True,
            "nombre_resuelto": nombre_str
        }
