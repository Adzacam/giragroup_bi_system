"""
text_cleaner.py — GIRA-40 (Sprint 2 — ampliado)
Limpieza final del texto plano antes de pasarlo a BETO.
Preserva caracteres del español (acentos, ñ).

Sprint 2 añade:
- Filtrado estricto de celdas basura (N/A, N/A.1, 1 caracter, solo números)
- Corrección de codificación mojibake (tildes/eñes)
- Deduplicación por llaves compuestas
- Detección de respuestas vacías para flag es_respuesta_vacia
"""

import re
import hashlib
import logging
import unicodedata
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Valores que representan "vacío" en los datos reales
_VALORES_VACIOS = {
    "", "n/a", "n/a.1", "n/a.2", "n/a.3", "nan", "none", "null",
    "na", "n.a.", "n.a", "sin respuesta", "sin comentario",
    "no aplica", "no responde", "-", "--", "---", ".",
}

# Pares comunes de mojibake español (Windows-1252 → UTF-8 mal interpretado)
# Usamos unicode escapes para evitar problemas de encoding en el propio source.
_MOJIBAKE_FIXES = [
    ("\u00c3\u00a1", "\u00e1"),  # Ã¡ → á
    ("\u00c3\u00a9", "\u00e9"),  # Ã© → é
    ("\u00c3\u00ad", "\u00ed"),  # Ã­ → í
    ("\u00c3\u00b3", "\u00f3"),  # Ã³ → ó
    ("\u00c3\u00ba", "\u00fa"),  # Ãº → ú
    ("\u00c3\u00b1", "\u00f1"),  # Ã± → ñ
    ("\u00c3\u0091", "\u00d1"),  # Ã' → Ñ
    ("\u00c3\u00bc", "\u00fc"),  # Ã¼ → ü
    ("\u00c2\u00b0", "\u00b0"),  # Â° → °
    ("\u00c2\u00bf", "\u00bf"),  # Â¿ → ¿
    ("\u00c2\u00a1", "\u00a1"),  # Â¡ → ¡
    ("\u00e2\u0080\u0099", "'"),  # â€™ → '
    ("\u00e2\u0080\u009c", '"'),  # â€œ → "
    ("\u00e2\u0080\u009d", '"'),  # â€ → "
    ("\u00e2\u0080\u0094", "\u2014"),  # â€" → —
    ("\u00e2\u0080\u0093", "\u2013"),  # â€" → –
]


def limpiar_texto(texto: str) -> str:
    """
    Limpieza final del texto plano antes de pasarlo a BETO.
    No elimina caracteres en español (acentos, ñ) — BETO los necesita.
    """
    if not texto or not texto.strip():
        return ""

    # 1. Normalizar unicode: preserva tildes y ñ
    texto = unicodedata.normalize("NFC", texto)

    # 2. Eliminar caracteres de control (excepto newline y tab)
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", texto)

    # 3. Colapsar espacios múltiples en uno solo
    texto = re.sub(r"[ \t]+", " ", texto)

    # 4. Colapsar líneas vacías múltiples en una sola
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    # 5. Eliminar líneas que solo tienen guiones, igual o puntos (separadores visuales)
    texto = re.sub(r"^[-=_.]{3,}\s*$", "", texto, flags=re.MULTILINE)

    return texto.strip()


def corregir_mojibake(texto: str) -> str:
    """
    Corrige secuencias mojibake comunes en exportaciones Moodle/Forms
    que codifican UTF-8 como si fuera Windows-1252.
    """
    if not texto:
        return texto
    for corrupto, correcto in _MOJIBAKE_FIXES:
        texto = texto.replace(corrupto, correcto)
    return texto


def es_respuesta_vacia(texto: str) -> bool:
    """
    Determina si un texto es efectivamente una respuesta vacía/basura
    que NO debe procesarse por BETO.

    Criterios:
    - String vacío o solo whitespace
    - Valores conocidos de "vacío" (N/A, NaN, etc.)
    - String de 1 solo carácter
    - String puramente numérico (respuesta numérica colada en columna de texto)
    """
    if not texto or not texto.strip():
        return True

    limpio = texto.strip().lower()

    # Valor conocido de vacío
    if limpio in _VALORES_VACIOS:
        return True

    # Un solo carácter
    if len(limpio) <= 1:
        return True

    # Puramente numérico (con o sin decimales/signo)
    if re.match(r"^-?\d+\.?\d*$", limpio):
        return True

    return False


def normalizar_nombre(nombre: str) -> str:
    """
    Normaliza un nombre propio para comparación fuzzy en Sprint 3.
    'Ing. JUAN  pérez  ' → 'Juan Perez'
    """
    if not nombre:
        return ""

    # Eliminar títulos/prefijos académicos
    prefijos = r"\b(ing|lic|dr|dra|msc|mgr|prof|arq|abog)\.?\s*"
    nombre = re.sub(prefijos, "", nombre, flags=re.IGNORECASE)

    # Normalizar unicode manteniendo caracteres españoles
    nombre = unicodedata.normalize("NFC", nombre)

    # Title case y strip
    nombre = nombre.strip().title()

    # Colapsar espacios internos dobles
    nombre = re.sub(r"\s+", " ", nombre)

    return nombre


def limpiar_texto_para_ner(texto: str) -> str:
    """
    Pipeline completo de limpieza de un texto individual
    previo a ingreso en BETO/NER:
    1. Corrección de mojibake
    2. Limpieza base (unicode, control chars, espacios)
    3. Verificación de respuesta vacía
    """
    texto = corregir_mojibake(texto)
    texto = limpiar_texto(texto)
    return texto


def deduplicar_respuestas(
    registros: list[dict],
    llaves_dedup: Optional[list[str]] = None,
) -> tuple[list[dict], list[dict]]:
    """
    Deduplica respuestas usando una llave compuesta.

    Args:
        registros: Lista de dicts con datos de respuestas.
        llaves_dedup: Campos a usar como llave compuesta.
            Default: ["pos", "identificador_persona", "fecha_evento"]

    Returns:
        (registros_unicos, registros_duplicados)
    """
    if llaves_dedup is None:
        llaves_dedup = ["pos", "identificador_persona", "fecha_evento"]

    vistos = set()
    unicos = []
    duplicados = []

    for registro in registros:
        # Construir llave compuesta con lo disponible
        partes_llave = []
        for llave in llaves_dedup:
            valor = registro.get(llave, "")
            if valor is None:
                valor = ""
            partes_llave.append(str(valor).strip().lower())

        llave_str = "|".join(partes_llave)

        # Si la llave está completamente vacía, no deduplicar
        if all(p == "" for p in partes_llave):
            unicos.append(registro)
            continue

        if llave_str in vistos:
            duplicados.append(registro)
            logger.debug("Registro duplicado detectado: %s", llave_str)
        else:
            vistos.add(llave_str)
            unicos.append(registro)

    if duplicados:
        logger.info(
            "Deduplicación: %d únicos, %d duplicados eliminados.",
            len(unicos), len(duplicados),
        )

    return unicos, duplicados


def preparar_payload_beto(df, fuente_tipo: str, nombre_archivo: str, columnas_texto: list = None) -> list:
    """
    Normaliza y limpia comentarios de texto libre en un DataFrame,
    generando una lista de payloads estructurados para la inferencia con BETO.
    """
    payload = []
    
    # Aplicar la heurística si no hay columnas explícitas
    if not columnas_texto:
        columnas_texto = []
        for col in df.columns:
            # Exigir que sea de tipo object o string
            if df[col].dtype in ['object', 'string'] or str(df[col].dtype) in ['object', 'string']:
                non_null_series = df[col].dropna().astype(str)
                if not non_null_series.empty:
                    longitud_promedio = non_null_series.str.len().mean()
                    # Al menos el 70% de las celdas no nulas deben cumplir con el umbral > 15
                    porcentaje_cumple = (non_null_series.str.len() > 15).mean()
                    
                    if longitud_promedio > 15 and porcentaje_cumple >= 0.7:
                        columnas_texto.append(col)
                    
    # Recorrer las columnas identificadas para extraer y limpiar los strings
    for col in columnas_texto:
        if col not in df.columns:
            continue
        for idx, valor in df[col].items():
            if valor is not None and str(valor).strip():
                # Invocar la función de limpieza con corrección de mojibake
                texto_procesado = limpiar_texto_para_ner(str(valor))
                if texto_procesado and not es_respuesta_vacia(texto_procesado):
                    payload.append({
                        "texto_limpio": texto_procesado,
                        "fuente_tipo": fuente_tipo,
                        "nombre_archivo": nombre_archivo,
                        "id_fila": idx,
                        "columna_origen": col
                    })
    return payload
