"""
profiler.py — Sprint 2
Perfilado automático de columnas y clasificación de hojas por contenido.

Determina el rol de cada columna (identificador, fecha, categorico_likert,
texto_libre, financiero) sin depender de su nombre, usando estadísticas
del contenido (nulos, cardinalidad, longitud, patrones regex).

Clasifica hojas en familias (texto_libre, estructurado_relacional,
financiero, descartable) según el perfil combinado de sus columnas.

Usa muestreo eficiente (primeras N filas) para hojas grandes.
"""

import re
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Configuración por defecto (puede sobrescribirse desde canonical_dictionary.json)
_DEFAULT_SAMPLE_SIZE = 300
_DEFAULT_TEXT_WORD_THRESHOLD = 3
_DEFAULT_TEXT_CHAR_THRESHOLD = 30
_DEFAULT_TEXT_CELL_PCT = 0.40

# Patrones regex para inferencia de rol
_PATRON_EMAIL = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$")
_PATRON_FECHA = re.compile(
    r"^\d{1,4}[-/]\d{1,2}[-/]\d{1,4}$"
    r"|^\d{1,2}\s+de\s+\w+\s+de\s+\d{4}$"
    r"|^\d{4}-\d{2}-\d{2}T",
    re.IGNORECASE,
)
_PATRON_CI = re.compile(r"^\d{6,9}$")
_PATRON_MONTO = re.compile(r"^\$?\s*[\d,]{3,}[\d,]*\.?\d{0,2}$|^[\d.]{3,}[\d.]*,\d{2}$")


class ColumnProfile:
    """Perfil estadístico de una columna individual."""

    def __init__(
        self,
        nombre: str,
        pct_nulos: float,
        cardinalidad: int,
        n_filas: int,
        longitud_promedio: float,
        pct_texto_largo: float,
        palabras_promedio: float,
        pct_numerico: float,
        pct_email: float,
        pct_fecha: float,
        pct_ci: float,
        pct_monto: float,
        rol_inferido: str,
    ):
        self.nombre = nombre
        self.pct_nulos = pct_nulos
        self.cardinalidad = cardinalidad
        self.n_filas = n_filas
        self.longitud_promedio = longitud_promedio
        self.pct_texto_largo = pct_texto_largo
        self.palabras_promedio = palabras_promedio
        self.pct_numerico = pct_numerico
        self.pct_email = pct_email
        self.pct_fecha = pct_fecha
        self.pct_ci = pct_ci
        self.pct_monto = pct_monto
        self.rol_inferido = rol_inferido

    def to_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "pct_nulos": round(self.pct_nulos, 4),
            "cardinalidad": self.cardinalidad,
            "n_filas": self.n_filas,
            "longitud_promedio": round(self.longitud_promedio, 2),
            "pct_texto_largo": round(self.pct_texto_largo, 4),
            "palabras_promedio": round(self.palabras_promedio, 2),
            "pct_numerico": round(self.pct_numerico, 4),
            "rol_inferido": self.rol_inferido,
        }


def perfilar_columna(
    serie: pd.Series,
    nombre: str,
    text_char_threshold: int = _DEFAULT_TEXT_CHAR_THRESHOLD,
    text_word_threshold: int = _DEFAULT_TEXT_WORD_THRESHOLD,
    text_cell_pct: float = _DEFAULT_TEXT_CELL_PCT,
) -> ColumnProfile:
    """
    Calcula el perfil estadístico de una columna sin mirar su nombre.
    """
    n_total = len(serie)
    if n_total == 0:
        return ColumnProfile(
            nombre=nombre, pct_nulos=1.0, cardinalidad=0, n_filas=0,
            longitud_promedio=0, pct_texto_largo=0, palabras_promedio=0,
            pct_numerico=0, pct_email=0, pct_fecha=0, pct_ci=0, pct_monto=0,
            rol_inferido="desconocido",
        )

    # Tratar como strings para análisis
    serie_str = serie.dropna().astype(str)
    serie_str = serie_str[serie_str.str.strip() != ""]
    n_no_vacio = len(serie_str)

    pct_nulos = 1.0 - (n_no_vacio / n_total) if n_total > 0 else 1.0
    cardinalidad = serie_str.nunique() if n_no_vacio > 0 else 0

    # Longitud promedio de texto
    longitudes = serie_str.str.len()
    longitud_promedio = longitudes.mean() if n_no_vacio > 0 else 0.0

    # Palabras promedio
    palabras = serie_str.str.split().str.len()
    palabras_promedio = palabras.mean() if n_no_vacio > 0 else 0.0

    # Porcentaje de celdas con texto largo (>threshold chars o >threshold palabras)
    if n_no_vacio > 0:
        pct_texto_largo = (
            (longitudes > text_char_threshold) | (palabras > text_word_threshold)
        ).mean()
    else:
        pct_texto_largo = 0.0

    # Detección de patrones
    pct_numerico = 0.0
    pct_email = 0.0
    pct_fecha = 0.0
    pct_ci = 0.0
    pct_monto = 0.0

    if n_no_vacio > 0:
        pct_numerico = serie_str.apply(
            lambda x: bool(re.match(r"^-?\d+\.?\d*$", x.strip()))
        ).mean()
        pct_email = serie_str.apply(
            lambda x: bool(_PATRON_EMAIL.match(x.strip()))
        ).mean()
        pct_fecha = serie_str.apply(
            lambda x: bool(_PATRON_FECHA.match(x.strip()))
        ).mean()
        pct_ci = serie_str.apply(
            lambda x: bool(_PATRON_CI.match(x.strip()))
        ).mean()
        pct_monto = serie_str.apply(
            lambda x: bool(_PATRON_MONTO.match(x.strip()))
        ).mean()

    # ── Inferir rol ───────────────────────────────────────────────────
    rol = _inferir_rol(
        pct_email=pct_email,
        pct_fecha=pct_fecha,
        pct_ci=pct_ci,
        pct_numerico=pct_numerico,
        pct_monto=pct_monto,
        cardinalidad=cardinalidad,
        pct_texto_largo=pct_texto_largo,
        palabras_promedio=palabras_promedio,
        longitud_promedio=longitud_promedio,
        n_no_vacio=n_no_vacio,
        nombre_columna=nombre,
        text_cell_pct=text_cell_pct,
    )

    return ColumnProfile(
        nombre=nombre,
        pct_nulos=pct_nulos,
        cardinalidad=cardinalidad,
        n_filas=n_total,
        longitud_promedio=longitud_promedio,
        pct_texto_largo=pct_texto_largo,
        palabras_promedio=palabras_promedio,
        pct_numerico=pct_numerico,
        pct_email=pct_email,
        pct_fecha=pct_fecha,
        pct_ci=pct_ci,
        pct_monto=pct_monto,
        rol_inferido=rol,
    )


# Eliminada primera definición duplicada de _inferir_rol (código muerto)

_PATRON_PREGUNTA_ABIERTA = re.compile(
    r"\(abierta\)|sugerencia|aspectos|deseado|explorar|didáctica|didactica|enseñanza|profesor|docente.*mejorar|otro contenido",
    re.IGNORECASE
)
_PATRON_GRUPO_SEDE = re.compile(r"^\s*grupo\b|^\s*sede\b|^\s*grupos\b", re.IGNORECASE)


def _inferir_rol(
    pct_email: float,
    pct_fecha: float,
    pct_ci: float,
    pct_numerico: float,
    pct_monto: float,
    cardinalidad: int,
    pct_texto_largo: float,
    palabras_promedio: float,
    longitud_promedio: float,
    n_no_vacio: int,
    nombre_columna: str,
    text_cell_pct: float,
) -> str:
    """Infiere el rol semántico de una columna basándose en su perfil."""

    # Email
    if pct_email > 0.5:
        return "correo"

    # Fecha
    if pct_fecha > 0.5:
        return "fecha_evento"

    # CI/Identificador
    if pct_ci > 0.5:
        return "identificador"

    # Escala Likert / categórica: pocos valores únicos, mayormente numéricos
    # Verificar ANTES de financiero para que escalas 1-5 no se confundan con montos.
    if pct_numerico > 0.7 and cardinalidad <= 11:
        return "categorico_likert"

    # Montos financieros (requiere patrón de monto, no solo numéricos)
    if pct_monto > 0.5:
        return "financiero"

    # Numérico general (notas, porcentajes)
    if pct_numerico > 0.7:
        return "numerico"

    # Texto libre: si la cabecera coincide con patrón de pregunta abierta, O si cumple métricas de texto largo conciso sin ser grupo/sede
    es_pregunta_abierta_header = bool(_PATRON_PREGUNTA_ABIERTA.search(nombre_columna))
    es_grupo_sede_header = bool(_PATRON_GRUPO_SEDE.search(nombre_columna))

    if not es_grupo_sede_header:
        if es_pregunta_abierta_header:
            return "texto_libre"
        if pct_texto_largo >= text_cell_pct and palabras_promedio >= 2.2 and longitud_promedio >= 18.0:
            return "texto_libre"

    # Categórico texto (pocos valores únicos o texto corto tipo grupo/sede)
    if n_no_vacio > 0 and (cardinalidad / max(n_no_vacio, 1) < 0.1 or longitud_promedio < 30.0):
        return "categorico_texto"

    # Identificador texto (alta cardinalidad, texto corto)
    if longitud_promedio < 30 and cardinalidad > 10:
        return "identificador_texto"

    return "desconocido"


# Keywords que identifican hojas financieras o de ejecución económica
_KEYWORDS_FINANCIERAS = {
    "ibp", "inversion", "inversión", "gastos", "punto equilibrio", "punto de equilibrio",
    "leads", "costos", "presupuesto", "cobranzas", "egresos", "metas", "proyeccion", "proyección"
}

# Keywords que sirven de refuerzo para identificar encuestas cuando hay Likert
_KEYWORDS_ENCUESTA_HOJA = {"docente", "encuesta", "experiencia", "evaluacion", "evaluación"}


# ── Clasificación de hoja ──────────────────────────────────────────────────


def perfilar_hoja(
    df: pd.DataFrame,
    nombre_hoja: str = "",
    config: Optional[dict] = None,
) -> dict:
    """
    Perfila todas las columnas de una hoja y clasifica la hoja
    en una de las 4 familias.
    """
    cfg = config or {}
    sample_size = cfg.get("profiler_sample_size", _DEFAULT_SAMPLE_SIZE)
    text_word_thresh = cfg.get("text_libre_word_threshold", _DEFAULT_TEXT_WORD_THRESHOLD)
    text_char_thresh = cfg.get("text_libre_char_threshold", _DEFAULT_TEXT_CHAR_THRESHOLD)
    text_cell_pct = cfg.get("text_libre_cell_pct_threshold", _DEFAULT_TEXT_CELL_PCT)

    # Muestreo eficiente
    if len(df) > sample_size:
        df_sample = df.head(sample_size)
        logger.info(
            "Hoja '%s': muestreando %d/%d filas para perfilado.",
            nombre_hoja, sample_size, len(df),
        )
    else:
        df_sample = df

    # Hoja vacía
    if df_sample.empty or len(df_sample.columns) == 0:
        return {
            "nombre_hoja": nombre_hoja,
            "familia": "descartable",
            "razon_clasificacion": "HOJA_VACIA",
            "perfiles_columnas": [],
            "columnas_texto_libre": [],
            "columnas_identificadoras": [],
            "n_filas": 0,
            "n_columnas": 0,
        }

    # Perfilar cada columna (utilizar iloc para garantizar que se obtiene una Series, incluso si hay columnas duplicadas)
    perfiles = []
    for i, col in enumerate(df_sample.columns):
        perfil = perfilar_columna(
            df_sample.iloc[:, i], str(col),
            text_char_threshold=text_char_thresh,
            text_word_threshold=text_word_thresh,
            text_cell_pct=text_cell_pct,
        )
        perfiles.append(perfil)

    # Agrupar columnas por rol
    roles = {}
    for p in perfiles:
        roles.setdefault(p.rol_inferido, []).append(p.nombre)

    columnas_texto_libre = roles.get("texto_libre", [])
    columnas_id = (
        roles.get("identificador", [])
        + roles.get("identificador_texto", [])
        + roles.get("correo", [])
    )
    columnas_financieras = roles.get("financiero", [])
    columnas_likert = roles.get("categorico_likert", [])

    # Verificar si el nombre de la hoja o las columnas contienen keywords financieras explícitas
    nombre_hoja_norm = nombre_hoja.lower()
    cols_norm = [str(c).lower() for c in df_sample.columns]
    tiene_keywords_financieras = (
        any(kw in nombre_hoja_norm for kw in _KEYWORDS_FINANCIERAS)
        or any(any(kw in col for kw in _KEYWORDS_FINANCIERAS) for col in cols_norm)
    )

    es_nombre_hoja_encuesta = any(kw in nombre_hoja_norm for kw in _KEYWORDS_ENCUESTA_HOJA)

    _RELATIONAL_KEY_PATTERNS = {
        "pos": ["pos", "código pos", "codigo pos", "pos - actas", "pos - modulo", "n° pos"],
        "docente": ["docente", "nombre del docente", "instructor", "profesor"],
        "modulo": ["módulo", "modulo", "materia", "asignatura", "módulo 1", "modulo 1"],
    }
    cols_joined = " ".join(cols_norm)
    has_pos_key = any(p in cols_joined for p in _RELATIONAL_KEY_PATTERNS["pos"])
    has_docente_key = any(p in cols_joined for p in _RELATIONAL_KEY_PATTERNS["docente"])
    has_modulo_key = any(p in cols_joined for p in _RELATIONAL_KEY_PATTERNS["modulo"])

    es_hoja_maestra_relacional = (has_pos_key and has_docente_key) or (has_pos_key and has_modulo_key and len(columnas_id) >= 1)

    # ── Clasificación de la hoja ──────────────────────────────────────
    n_cols = len(perfiles)

    # Descartable: casi todas las columnas tienen >90% nulos
    cols_vacias = sum(1 for p in perfiles if p.pct_nulos > 0.9)
    if n_cols > 0 and cols_vacias / n_cols > 0.7:
        familia = "descartable"
        razon = "HOJA_VACIA"
    # Financiero: keywords financieras explícitas o mayoría de columnas de montos
    elif tiene_keywords_financieras or len(columnas_financieras) > n_cols * 0.3:
        familia = "financiero" if len(columnas_financieras) > n_cols * 0.3 else "estructurado_relacional"
        razon = (
            "Hoja de gestión económica/IBP detectada por keywords financieras"
            if tiene_keywords_financieras else f"{len(columnas_financieras)} columnas financieras detectadas"
        )
    # Encuesta/Texto libre:
    # 1. Tiene columnas de texto libre detectadas (por cabecera o métricas)
    # 2. O tiene Likert (>=2) y refuerzo por nombre de hoja
    # 3. O tiene Likert (>=4)
    elif columnas_texto_libre:
        familia = "texto_libre"
        razon = f"{len(columnas_texto_libre)} columnas de texto libre detectadas"
    # PRIORIDAD RELACIONAL MAESTRA: Si no hay texto libre y tiene llaves (POS + DOCENTE o POS + MÓDULO + ID), es estructurada relacional
    elif es_hoja_maestra_relacional:
        familia = "estructurado_relacional"
        razon = "Esquema relacional maestro detectado (POS + DOCENTE / MÓDULO)"
        columnas_texto_libre = []
    elif len(columnas_likert) >= 2 and es_nombre_hoja_encuesta:
        familia = "texto_libre"
        razon = (
            f"Encuesta detectada por {len(columnas_likert)} columnas Likert "
            f"y refuerzo por nombre de hoja '{nombre_hoja}'"
        )
    elif len(columnas_likert) >= 4:
        familia = "texto_libre"
        razon = f"Encuesta detectada: {len(columnas_likert)} columnas Likert"
    # Estructurado: tiene identificadores o datos tabulares normales
    elif columnas_id:
        familia = "estructurado_relacional"
        razon = f"{len(columnas_id)} columnas identificadoras detectadas"
    else:
        familia = "estructurado_relacional"
        razon = "Hoja de datos tabulares estructurada"
        razon = "Clasificación por defecto (sin texto libre ni montos)"

    logger.info(
        "Hoja '%s' clasificada como '%s': %s",
        nombre_hoja, familia, razon,
    )

    return {
        "nombre_hoja": nombre_hoja,
        "familia": familia,
        "razon_clasificacion": razon,
        "perfiles_columnas": [p.to_dict() for p in perfiles],
        "columnas_texto_libre": columnas_texto_libre,
        "columnas_identificadoras": columnas_id,
        "n_filas": len(df),
        "n_columnas": n_cols,
    }
