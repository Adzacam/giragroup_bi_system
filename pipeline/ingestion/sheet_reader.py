"""
sheet_reader.py — GIRA-6
Lector de archivos XLSX/CSV locales y Google Sheets remotos.
Devuelve el contrato de salida estándar del pipeline.
"""

import pandas as pd
import os
from datetime import datetime
from typing import Union


def leer_xlsx(file_path: str) -> dict:
    """Lee archivos .xlsx o .csv locales."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
    else:
        # Leer solo la primera hoja con datos
        df = pd.read_excel(file_path, sheet_name=0)

    # Limpieza estructural
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df = df.fillna("")

    filas = df.to_dict(orient="records")
    texto_plano = _dataframe_a_texto(df)

    return {
        "texto_plano": texto_plano,
        "fuente_tipo": "SHEET",
        "nombre_archivo": os.path.basename(file_path),
        "filas_raw": filas,
        "procesado_en": datetime.utcnow().isoformat(),
    }


def leer_google_sheet(sheet_id: str, rango: str = "Sheet1") -> dict:
    """
    Lee un Google Sheet usando gspread + service account.
    Requiere: GOOGLE_CREDENTIALS_PATH en .env apuntando al JSON de la cuenta de servicio.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        raise ImportError("Instalar: pip install gspread google-auth")

    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    if not creds_path:
        raise EnvironmentError("Variable GOOGLE_CREDENTIALS_PATH no definida en .env")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(sheet_id).worksheet(rango)
    data = sheet.get_all_records()  # lista de dicts con cabeceras

    df = pd.DataFrame(data)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df = df.fillna("")
    texto_plano = _dataframe_a_texto(df)

    return {
        "texto_plano": texto_plano,
        "fuente_tipo": "SHEET",
        "nombre_archivo": f"gsheet_{sheet_id}",
        "filas_raw": df.to_dict(orient="records"),
        "procesado_en": datetime.utcnow().isoformat(),
    }


def _dataframe_a_texto(df: pd.DataFrame) -> str:
    """Convierte un DataFrame a texto plano fila por fila para BETO."""
    lineas = []
    for _, row in df.iterrows():
        partes = [f"{col}: {val}" for col, val in row.items() if str(val).strip()]
        lineas.append(" | ".join(partes))
    return "\n".join(lineas)