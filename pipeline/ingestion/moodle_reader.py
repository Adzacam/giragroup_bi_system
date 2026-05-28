"""
moodle_reader.py — GIRA-5
Lector de exportaciones CSV/XLSX de Moodle (Calificaciones > Exportar).
Normaliza columnas al esquema canónico y devuelve el contrato estándar.
"""

import pandas as pd
import os
from datetime import datetime


# Columnas canónicas que Moodle suele exportar.
# Si el export tiene nombres distintos, el mapper los normaliza.
_MOODLE_COLUMN_MAP = {
    "nombre": "nombre_completo",
    "apellido": "apellido",
    "dirección de correo": "email",
    "calificación": "nota_final",
    "calificación/100,00": "nota_final",
    "estado": "estado_entrega",
    "última modificación (entrega)": "fecha_entrega",
}


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
    df.columns = [str(c).strip().lower() for c in df.columns]
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
    'Estudiante: Juan Perez | Nota: 78.50 | Estado: Entregado'
    """
    lineas = []
    for _, row in df.iterrows():
        partes = []
        if "nombre_completo" in row:
            partes.append(f"Estudiante: {row.get('nombre_completo', '')} {row.get('apellido', '')}".strip())
        if "nota_final" in row and str(row["nota_final"]).strip():
            partes.append(f"Nota: {row['nota_final']}")
        if "estado_entrega" in row:
            partes.append(f"Estado: {row['estado_entrega']}")
        if "fecha_entrega" in row:
            partes.append(f"Fecha: {row['fecha_entrega']}")
        if partes:
            lineas.append(" | ".join(partes))
    return "\n".join(lineas)
