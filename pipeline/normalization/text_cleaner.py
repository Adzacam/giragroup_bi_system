"""
text_cleaner.py — GIRA-40
Limpieza final del texto plano antes de pasarlo a BETO.
Preserva caracteres del español (acentos, ñ).
"""

import re
import unicodedata


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


def preparar_payload_beto(df, fuente_tipo: str, nombre_archivo: str, columnas_texto: list = None) -> list:
    """
    Normaliza y limpia comentarios de texto libre en un DataFrame,
    generando una lista de payloads estructurados para la inferencia con BETO.
    """
    import pandas as pd
    
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
                # Invocar la función de limpieza base
                texto_procesado = limpiar_texto(str(valor))
                if texto_procesado:
                    payload.append({
                        "texto_limpio": texto_procesado,
                        "fuente_tipo": fuente_tipo,
                        "nombre_archivo": nombre_archivo,
                        "id_fila": idx,
                        "columna_origen": col
                    })
    return payload

