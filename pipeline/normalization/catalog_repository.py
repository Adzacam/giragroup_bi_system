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
        self.modulos: Dict[str, Dict[str, Any]] = {}  # nombre_limpio -> {id, nombre_original}
        
        self.escuelas: List[str] = []
        self.tipos_programa: List[str] = []
        self.modalidades: List[str] = []
        self.estados_academicos: List[str] = []
        self.estados_reprobados: List[str] = []
        self.estados_arca: List[str] = []
        self.carteras: List[Dict[str, Any]] = []

        # Estructuras dinámicas para clasificación y guías de texto plano
        self.etiquetas_clasificacion: List[Dict[str, Any]] = []
        self.mapeos_columna: Dict[str, Dict[str, str]] = {}
        self.guias_texto_plano: Dict[str, Dict[str, Any]] = {}

        self._cargar_desde_seed()
        self._inicializar_mapeos_rapidos()
        self._initialized = True

    def _cargar_desde_seed(self) -> None:
        """Parsea seed_catalogos.sql una sola vez para poblar todas las dimensiones y guías."""
        if not self.ruta_seed.exists():
            return

        with open(self.ruta_seed, "r", encoding="utf-8") as f:
            contenido_sql = f.read()

        for line in contenido_sql.splitlines():
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

        # Parsear bloques relacionales de clasificación y plantillas
        m_etiq = re.search(r"INSERT INTO public\.cat_etiqueta_clasificacion.*?VALUES\s*(.*?)(?:ON CONFLICT|;)", contenido_sql, re.DOTALL | re.IGNORECASE)
        if m_etiq:
            for item in re.finditer(r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*(\d+)\s*\)", m_etiq.group(1)):
                self.etiquetas_clasificacion.append({
                    "categoria": item.group(1).strip().lower(),
                    "subtipo": item.group(2).strip(),
                    "palabra_clave": item.group(3).strip().lower(),
                    "ambito": item.group(4).strip().upper(),
                    "peso": int(item.group(5))
                })

        m_map = re.search(r"INSERT INTO public\.cat_mapeo_columna.*?VALUES\s*(.*?)(?:ON CONFLICT|;)", contenido_sql, re.DOTALL | re.IGNORECASE)
        if m_map:
            for item in re.finditer(r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", m_map.group(1)):
                self.mapeos_columna[item.group(2).strip().lower()] = {
                    "campo_canonico": item.group(1).strip().upper(),
                    "tipo_entidad": item.group(3).strip().upper()
                }

        m_guia = re.search(r"INSERT INTO public\.cat_guia_texto_plano.*?VALUES\s*(.*?)(?:ON CONFLICT|;)", contenido_sql, re.DOTALL | re.IGNORECASE)
        if m_guia:
            for item in re.finditer(r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']*)'\s*,\s*(\d+)\s*\)", m_guia.group(1)):
                subtipo = item.group(1).strip()
                self.guias_texto_plano[subtipo] = {
                    "subtipo": subtipo,
                    "descripcion": item.group(2).strip(),
                    "plantilla_texto": item.group(3).strip(),
                    "campos_requeridos": [c.strip() for c in item.group(4).split(",") if c.strip()],
                    "prioridad": int(item.group(5))
                }

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

        # Mapeos institucionales complementarios para rendimiento académico y situación financiera
        mapeos_adicionales = {
            "asistencia": {"campo_canonico": "ASISTENCIA_PCT", "tipo_entidad": "ASISTENCIA_PCT"},
            "asistencia_pct": {"campo_canonico": "ASISTENCIA_PCT", "tipo_entidad": "ASISTENCIA_PCT"},
            "% asistencia": {"campo_canonico": "ASISTENCIA_PCT", "tipo_entidad": "ASISTENCIA_PCT"},
            "incumplimiento": {"campo_canonico": "INCUMPLIMIENTO_ACTIVIDADES_PCT", "tipo_entidad": "INCUMPLIMIENTO_ACTIVIDADES_PCT"},
            "incumplimiento_actividades_pct": {"campo_canonico": "INCUMPLIMIENTO_ACTIVIDADES_PCT", "tipo_entidad": "INCUMPLIMIENTO_ACTIVIDADES_PCT"},
            "% incumplimiento": {"campo_canonico": "INCUMPLIMIENTO_ACTIVIDADES_PCT", "tipo_entidad": "INCUMPLIMIENTO_ACTIVIDADES_PCT"},
            "monto_deuda": {"campo_canonico": "MONTO_DEUDA", "tipo_entidad": "MONTO_DEUDA"},
            "deuda": {"campo_canonico": "MONTO_DEUDA", "tipo_entidad": "MONTO_DEUDA"},
            "cuotas_impagas": {"campo_canonico": "CUOTAS_IMPAGAS", "tipo_entidad": "CUOTAS_IMPAGAS"},
            "cuotas impagas": {"campo_canonico": "CUOTAS_IMPAGAS", "tipo_entidad": "CUOTAS_IMPAGAS"},
            "estado_cartera": {"campo_canonico": "ESTADO_CARTERA", "tipo_entidad": "ESTADO_CARTERA"},
            "cartera": {"campo_canonico": "ESTADO_CARTERA", "tipo_entidad": "ESTADO_CARTERA"},
            "nota_final": {"campo_canonico": "NOTA", "tipo_entidad": "NOTA"},
            "calificacion_final": {"campo_canonico": "NOTA", "tipo_entidad": "NOTA"},
        }
        for k, v in mapeos_adicionales.items():
            if k not in self.mapeos_columna:
                self.mapeos_columna[k] = v

    def _inicializar_mapeos_rapidos(self) -> None:
        """Precomputa diccionarios en minúsculas para matching léxico veloz."""
        self._escuelas_map = {e.lower(): e for e in self.escuelas}
        self._modalidades_map = {m.lower(): m for m in self.modalidades}
        self._estados_aca_map = {ea.lower(): ea for ea in self.estados_academicos}
        self._programas_por_nombre = {
            FuzzyNormalizer.limpiar_nombre(nom): pos
            for pos, nom in self.programas.items()
        }
        # Agrupación de etiquetas por categoría y subtipo
        self._palabras_por_categoria: Dict[str, List[Tuple[str, str, int]]] = {}
        for etiq in self.etiquetas_clasificacion:
            cat = etiq["categoria"]
            if cat not in self._palabras_por_categoria:
                self._palabras_por_categoria[cat] = []
            self._palabras_por_categoria[cat].append(
                (etiq["palabra_clave"], etiq["ambito"], etiq["peso"])
            )

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

    # ── MÉTODOS DINÁMICOS DE CLASIFICACIÓN Y GUÍAS DE TEXTO PLANO ─────

    def clasificar_bloque_con_catalogo(
        self,
        texto_archivo: str = "",
        texto_hoja: str = "",
        texto_contenido: str = "",
        es_ruido: bool = False
    ) -> Tuple[str, str]:
        """
        Clasifica dinámicamente un bloque tabular en (categoría, subtipo) usando
        las etiquetas y ponderaciones cargadas de la base de datos de catálogos.
        """
        if es_ruido:
            return "ruido", "descartable"

        t_arch = (texto_archivo or "").lower()
        t_hoja = (texto_hoja or "").lower()
        t_cont = (texto_contenido or "").lower()

        cat_scores: Dict[str, float] = {"academico": 0.0, "financiero": 0.0, "comercial": 0.0}
        sub_scores: Dict[str, float] = {}

        for etiq in self.etiquetas_clasificacion:
            kw = etiq["palabra_clave"]
            cat = etiq["categoria"]
            sub = etiq["subtipo"]
            amb = etiq["ambito"]
            peso = float(etiq["peso"])

            puntos = 0.0
            if amb in ("ARCHIVO", "AMBOS") and kw in t_arch:
                puntos += peso * 2.0
            if amb in ("HOJA", "AMBOS") and kw in t_hoja:
                puntos += peso * 1.5
            if amb in ("CONTENIDO", "AMBOS") and kw in t_cont:
                puntos += peso * 1.0

            if puntos > 0:
                cat_scores[cat] = cat_scores.get(cat, 0.0) + puntos
                if sub:
                    sub_scores[sub] = sub_scores.get(sub, 0.0) + puntos

        mejor_cat = max(cat_scores, key=cat_scores.get)
        if cat_scores[mejor_cat] > 0.0:
            mejor_sub = max(sub_scores, key=sub_scores.get) if sub_scores else f"{mejor_cat.upper()}_GENERICO"
            return mejor_cat, mejor_sub

        return "generico", "GENERICO"

    def detectar_subtipo_con_catalogo(self, header_cols: List[str], categoria: str = "generico") -> str:
        """
        Determina el subtipo semántico del bloque analizando los encabezados
        contra las etiquetas del catálogo institucional.
        """
        hdr_norm = " ".join([c.lower() for c in header_cols])
        sub_scores: Dict[str, int] = {}

        for etiq in self.etiquetas_clasificacion:
            kw = etiq["palabra_clave"]
            sub = etiq["subtipo"]
            if sub and kw in hdr_norm:
                sub_scores[sub] = sub_scores.get(sub, 0) + etiq["peso"]

        if sub_scores:
            return max(sub_scores, key=sub_scores.get)

        if categoria == "financiero":
            return "COBRANZAS"
        if categoria == "academico":
            return "ACTAS_NOTAS"
        if categoria == "comercial":
            return "INSCRIPCIONES"
        return "GENERICO"

    def identificar_columna(self, col_name: str) -> Optional[Dict[str, str]]:
        """
        Mapea el nombre de una columna a su campo canónico y tipo de entidad
        usando el diccionario de cat_mapeo_columna.
        """
        if not col_name:
            return None
        clean = col_name.strip().lower()

        # 1. Búsqueda exacta
        if clean in self.mapeos_columna:
            return self.mapeos_columna[clean]

        # 2. Búsqueda por subcadena / contención
        for alias, mapeo in self.mapeos_columna.items():
            if alias in clean or clean in alias:
                return mapeo

        return None

    def obtener_guia_texto_plano(self, subtipo: str) -> Dict[str, Any]:
        """
        Retorna la plantilla y metadatos de serialización para un subtipo dado.
        """
        if subtipo in self.guias_texto_plano:
            return self.guias_texto_plano[subtipo]
        return self.guias_texto_plano.get("GENERICO", {
            "subtipo": "GENERICO",
            "descripcion": "Plantilla genérica",
            "plantilla_texto": "Registro en hoja {HOJA}: {DETALLES}.",
            "campos_requeridos": ["HOJA", "DETALLES"],
            "prioridad": 99
        })

    def obtener_resumen_institucional(self) -> Dict[str, Any]:
        """
        Retorna el resumen del Catálogo Maestro Institucional Estático (18 Programas Activos).
        Garantiza por diseño que no contiene ni expone ningún dato personal (Zero-PII).
        """
        programas_resumen = []
        for p in PROGRAMAS_ACTIVOS_INSTITUCIONALES:
            pos = p["pos_code"]
            nom = self.programas.get(pos, p["nombre"])
            programas_resumen.append({
                "pos_code": pos,
                "nombre": nom,
                "version": p["version"],
                "arancel_base_bs": p["arancel_base_bs"],
                "escuela": p["escuela"],
                "modalidad": p["modalidad"],
                "modulos_count": p["modulos_count"],
                "punto_equilibrio": p["punto_equilibrio"],
                "modulos_clave": p["modulos_clave"]
            })

        return {
            "status": "success",
            "total_programas_activos": len(programas_resumen),
            "sin_pii": True,
            "contiene_pii": False,
            "programas": programas_resumen,
            "modulos_activos_total": sum(p["modulos_count"] for p in programas_resumen),
            "convenios_activos_total": 6,
            "metas_presupuestarias": {
                "meta_anual_bs": 2450000.0,
                "punto_equilibrio_promedio_alumnos": 15
            },
            "mensaje": "Catálogo Maestro Institucional Estático Oficial (Zero PII Compliance)"
        }


PROGRAMAS_ACTIVOS_INSTITUCIONALES: List[Dict[str, Any]] = [
    {
        "pos_code": "POS-5308",
        "nombre": "Maestría en Business Intelligence y Big Data",
        "version": 4,
        "arancel_base_bs": 14500.0,
        "escuela": "Tecnología/Ingeniería",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 8,
        "punto_equilibrio": 15,
        "modulos_clave": ["Minería de Datos", "Arquitectura de Datos", "Visualización de Datos"]
    },
    {
        "pos_code": "POS-5952",
        "nombre": "Diplomado en Endodoncia y Sistemas de Instrumentación Mecanizada",
        "version": 1,
        "arancel_base_bs": 8200.0,
        "escuela": "Salud",
        "modalidad": "SEMIPRESENCIAL",
        "modulos_count": 5,
        "punto_equilibrio": 11,
        "modulos_clave": ["Instrumentación Rotatoria", "Obturación Termoplastificada"]
    },
    {
        "pos_code": "POS-5940",
        "nombre": "Diplomado en Liderazgo Comercial y Estrategia de Ventas",
        "version": 7,
        "arancel_base_bs": 7500.0,
        "escuela": "Negocios",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 6,
        "punto_equilibrio": 14,
        "modulos_clave": ["Negociación Estratégica", "Gestión de Equipos Comerciales"]
    },
    {
        "pos_code": "POS-5910",
        "nombre": "Diplomado en Medicina Estética",
        "version": 29,
        "arancel_base_bs": 12000.0,
        "escuela": "Salud",
        "modalidad": "SEMIPRESENCIAL",
        "modulos_count": 6,
        "punto_equilibrio": 28,
        "modulos_clave": ["Toxina Botulínica", "Rellenos Dérmicos", "Bioestimuladores"]
    },
    {
        "pos_code": "POS-5948",
        "nombre": "Programa Experto en Bases de Datos y SQL",
        "version": 3,
        "arancel_base_bs": 6500.0,
        "escuela": "Tecnología/Ingeniería",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 4,
        "punto_equilibrio": 11,
        "modulos_clave": ["Modelado Relacional", "Optimización de Consultas SQL"]
    },
    {
        "pos_code": "POS-5905",
        "nombre": "Diplomado en Urgencias y Emergencias Clínicas Quirúrgicas",
        "version": 5,
        "arancel_base_bs": 8900.0,
        "escuela": "Salud",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 6,
        "punto_equilibrio": 19,
        "modulos_clave": ["Soporte Vital Avanzado", "Trauma Quirúrgico"]
    },
    {
        "pos_code": "POS-5922",
        "nombre": "Curso en Obstetricia Clínica Integral y Manejo de Emergencias",
        "version": 1,
        "arancel_base_bs": 4200.0,
        "escuela": "Salud",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 3,
        "punto_equilibrio": 15,
        "modulos_clave": ["Control Prenatal", "Parto de Alto Riesgo"]
    },
    {
        "pos_code": "POS-5919",
        "nombre": "Diplomado en Análisis Clínico y Microbiología Laboratorial",
        "version": 11,
        "arancel_base_bs": 7800.0,
        "escuela": "Salud",
        "modalidad": "SEMIPRESENCIAL",
        "modulos_count": 6,
        "punto_equilibrio": 16,
        "modulos_clave": ["Bacteriología Clínica", "Inmunodiagnóstico"]
    },
    {
        "pos_code": "POS-5951",
        "nombre": "Curso Tablas Dinámicas y Analítica en Microsoft Excel",
        "version": 14,
        "arancel_base_bs": 2500.0,
        "escuela": "Tecnología/Ingeniería",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 2,
        "punto_equilibrio": 14,
        "modulos_clave": ["Power Query", "Dashboards Ejecutivos"]
    },
    {
        "pos_code": "POS-5935",
        "nombre": "Maestría en Gestión y Dirección de Empresas (MBA)",
        "version": 3,
        "arancel_base_bs": 16000.0,
        "escuela": "Negocios",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 10,
        "punto_equilibrio": 18,
        "modulos_clave": ["Dirección Estratégica", "Finanzas Corporativas"]
    },
    {
        "pos_code": "POS-5915",
        "nombre": "Diplomado en Derecho Procesal Civil y Oralidad",
        "version": 4,
        "arancel_base_bs": 7000.0,
        "escuela": "Leyes",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 5,
        "punto_equilibrio": 16,
        "modulos_clave": ["Audiencias Preliminares", "Recursos Ordinarios"]
    },
    {
        "pos_code": "POS-5928",
        "nombre": "Diplomado en Inteligencia Artificial y Machine Learning",
        "version": 2,
        "arancel_base_bs": 11500.0,
        "escuela": "Tecnología/Ingeniería",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 6,
        "punto_equilibrio": 15,
        "modulos_clave": ["Deep Learning", "Procesamiento de Lenguaje Natural"]
    },
    {
        "pos_code": "POS-5931",
        "nombre": "Diplomado en Marketing Digital y Growth Hacking",
        "version": 5,
        "arancel_base_bs": 6800.0,
        "escuela": "Negocios",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 5,
        "punto_equilibrio": 14,
        "modulos_clave": ["Performance Marketing", "Automatización de Embudos"]
    },
    {
        "pos_code": "POS-5944",
        "nombre": "Programa Experto en Ciberseguridad Defensiva",
        "version": 2,
        "arancel_base_bs": 8500.0,
        "escuela": "Tecnología/Ingeniería",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 4,
        "punto_equilibrio": 12,
        "modulos_clave": ["SOC & SIEM", "Respuesta a Incidentes"]
    },
    {
        "pos_code": "POS-5912",
        "nombre": "Diplomado en Farmacología Clínica y Terapéutica",
        "version": 6,
        "arancel_base_bs": 7900.0,
        "escuela": "Salud",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 5,
        "punto_equilibrio": 17,
        "modulos_clave": ["Farmacovigilancia", "Interacciones Medicamentosas"]
    },
    {
        "pos_code": "POS-5925",
        "nombre": "Diplomado en Educación Superior y Docencia Universitaria",
        "version": 8,
        "arancel_base_bs": 6200.0,
        "escuela": "Ciencias Sociales",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 5,
        "punto_equilibrio": 20,
        "modulos_clave": ["Diseño Curricular por Competencias", "Evaluación de los Aprendizajes"]
    },
    {
        "pos_code": "POS-5938",
        "nombre": "Maestría en Finanzas Corporativas y Mercado de Valores",
        "version": 2,
        "arancel_base_bs": 15500.0,
        "escuela": "Negocios",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 9,
        "punto_equilibrio": 16,
        "modulos_clave": ["Valoración de Empresas", "Instrumentos Derivados"]
    },
    {
        "pos_code": "POS-5945",
        "nombre": "Diplomado en Gestión de Proyectos Tecnológicos",
        "version": 4,
        "arancel_base_bs": 8000.0,
        "escuela": "Tecnología/Ingeniería",
        "modalidad": "VIRTUAL SINCRÓNICO",
        "modulos_count": 5,
        "punto_equilibrio": 15,
        "modulos_clave": ["Metodologías Ágiles", "Gestión de Riesgos TI"]
    }
]


_repositorio_singleton: Optional[CatalogRepository] = None


def obtener_catalogo_repositorio(
    ruta_seed_sql: Optional[Union[str, Path]] = None
) -> CatalogRepository:
    """Función helper para obtener la instancia singleton del repositorio."""
    global _repositorio_singleton
    if _repositorio_singleton is None:
        _repositorio_singleton = CatalogRepository(ruta_seed_sql)
    return _repositorio_singleton


def obtener_resumen_institucional() -> Dict[str, Any]:
    """Helper para obtener el resumen institucional del catálogo singleton."""
    return obtener_catalogo_repositorio().obtener_resumen_institucional()

