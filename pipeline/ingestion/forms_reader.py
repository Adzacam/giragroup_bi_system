"""
forms_reader.py — GIRA-7 + GIRA-39
Lector de CSV exportado desde Google Forms (Respuestas > Descargar CSV).
Detecta columna de timestamp y devuelve el contrato estándar.
"""

import pandas as pd
import os
from datetime import datetime


def leer_forms_csv(file_path: str) -> dict:
    """
    Lee el CSV exportado desde Google Forms (Respuestas > Descargar CSV).
    La primera columna suele ser la marca de tiempo.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Archivo Forms no encontrado: {file_path}")

    if not file_path.lower().endswith(".csv"):
        raise ValueError("Google Forms solo exporta CSV. Verificar el archivo.")

    df = pd.read_csv(file_path, encoding="utf-8-sig", on_bad_lines="skip")

    # Limpieza estructural
    df.dropna(how="all", inplace=True)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df = df.fillna("")

    # Renombrar columna de timestamp si existe
    timestamp_cols = [c for c in df.columns if "marca" in c or "timestamp" in c or "hora" in c]
    if timestamp_cols:
        df.rename(columns={timestamp_cols[0]: "fecha_respuesta"}, inplace=True)

    filas = df.to_dict(orient="records")
    texto_plano = _forms_a_texto(df)

    return {
        "texto_plano": texto_plano,
        "fuente_tipo": "FORM",
        "nombre_archivo": os.path.basename(file_path),
        "filas_raw": filas,
        "procesado_en": datetime.utcnow().isoformat(),
    }


def _forms_a_texto(df: pd.DataFrame) -> str:
    """Convierte respuestas del formulario a texto plano para BETO."""
    lineas = []
    for _, row in df.iterrows():
        partes = [f"{col.replace('_', ' ')}: {val}"
                  for col, val in row.items() if str(val).strip()]
        if partes:
            lineas.append(" | ".join(partes))
    return "\n".join(lineas)
