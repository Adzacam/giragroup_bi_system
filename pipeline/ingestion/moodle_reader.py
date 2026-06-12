"""
moodle_reader.py — GIRA-5
Lector de exportaciones CSV/XLSX de Moodle (Calificaciones > Exportar).
Normaliza columnas al esquema canónico y devuelve el contrato estándar.
"""

import pandas as pd
import os
import unicodedata
from datetime import datetime


# Columnas canónicas que Moodle suele exportar (normalizadas a minúsculas y sin acentos).
_MOODLE_COLUMN_MAP = {
    "nombre": "nombre",
    "apellido": "apellido",
    "nombre(s)": "nombre",
    "apellido(s)": "apellido",
    "nombre completo": "nombre_completo",
    "direccion de correo": "email",
    "correo institucional": "email",
    "calificacion": "nota_final",
    "calificacion/100,00": "nota_final",
    "total del curso": "nota_final",
    "calificacion final del curso": "nota_final",
    "numero de id": "codigo_estudiante",
    "estado": "estado_entrega",
    "ultima modificacion (entrega)": "fecha_entrega",
}


def normalizar_cabecera(cabecera: str) -> str:
    """Remueve tildes y caracteres especiales, convirtiendo a minúsculas y limpiando espacios."""
    if not cabecera:
        return ""
    # Convertir a minúsculas y strip
    c = str(cabecera).strip().lower()
    # Normalizar para separar caracteres combinados (tildes) y removerlos
    c = "".join(ch for ch in unicodedata.normalize("NFD", c) if unicodedata.category(ch) != "Mn")
    return c


def leer_moodle_export(file_path: str) -> dict:
    """
    Lee el export CSV o XLSX que genera Moodle en
    Calificaciones > Exportar > Archivo de texto plano o Excel.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Archivo Moodle no encontrado: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        # Moodle exporta a veces con BOM (utf-8-sig)
        df = pd.read_csv(file_path, encoding="utf-8-sig", on_bad_lines="skip")
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, sheet_name=0)
    else:
        raise ValueError(f"Formato Moodle no soportado: {ext}. Usar CSV o XLSX.")

    # Limpieza estructural
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)
    df.columns = [normalizar_cabecera(c) for c in df.columns]
    df = df.fillna("")

    # Normalización de columnas al esquema canónico
    df.rename(columns={k: v for k, v in _MOODLE_COLUMN_MAP.items()
                       if k in df.columns}, inplace=True)

    filas = df.to_dict(orient="records")
    texto_plano = _moodle_a_texto(df)

    return {
        "texto_plano": texto_plano,
        "fuente_tipo": "MOODLE",
        "nombre_archivo": os.path.basename(file_path),
        "filas_raw": filas,
        "procesado_en": datetime.utcnow().isoformat(),
    }


def _moodle_a_texto(df: pd.DataFrame) -> str:
    """
    Genera texto plano optimizado para NER:
    'Estudiante: Juan Perez | ID: 20002131 | Nota: 78.50 | Estado: Entregado'
    """
    lineas = []
    for _, row in df.iterrows():
        partes = []
        nombre_completo = ""
        if "nombre_completo" in row and str(row["nombre_completo"]).strip():
            nombre_completo = str(row["nombre_completo"]).strip()
        else:
            partes_nombre = []
            if "nombre" in row and str(row["nombre"]).strip():
                partes_nombre.append(str(row["nombre"]).strip())
            if "apellido" in row and str(row["apellido"]).strip():
                partes_nombre.append(str(row["apellido"]).strip())
            if partes_nombre:
                nombre_completo = " ".join(partes_nombre)

        if nombre_completo:
            partes.append(f"Estudiante: {nombre_completo}")
        if "codigo_estudiante" in row and str(row["codigo_estudiante"]).strip():
            partes.append(f"ID: {row['codigo_estudiante']}")
        if "nota_final" in row and str(row["nota_final"]).strip():
            partes.append(f"Nota: {row['nota_final']}")
        if "estado_entrega" in row and str(row["estado_entrega"]).strip():
            partes.append(f"Estado: {row['estado_entrega']}")
        if "fecha_entrega" in row and str(row["fecha_entrega"]).strip():
            partes.append(f"Fecha: {row['fecha_entrega']}")
        if partes:
            lineas.append(" | ".join(partes))
    return "\n".join(lineas)

