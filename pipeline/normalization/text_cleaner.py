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
