"""
sheet_reader.py — GIRA-6
Lector de archivos XLSX/CSV locales y Google Sheets remotos.
Devuelve el contrato de salida estándar del pipeline.
"""

import pandas as pd
import os
import unicodedata
from datetime import datetime
from typing import Union


def _validar_columnas_identificadoras(df: pd.DataFrame) -> None:
    """Valida que el DataFrame contenga al menos una columna identificadora primaria."""
    # Términos clave a buscar en las columnas normalizadas
    terminos_clave = ["id", "cod", "alumno", "estudiante", "email", "correo"]
    
    def normalizar(c):
        c_str = str(c).strip().lower()
        return "".join(ch for ch in unicodedata.normalize("NFD", c_str) if unicodedata.category(ch) != "Mn")
    
    columnas_norm = [normalizar(col) for col in df.columns]
    
    # Comprobar si al menos una columna contiene alguno de los términos clave (coincidencia parcial)
    encontrado = False
    for col in columnas_norm:
        if any(tk in col for tk in terminos_clave):
            encontrado = True
            break
            
    if not encontrado:
        raise ValueError(
            "Fallo de validacion estructural: No se encontro ninguna columna identificadora primaria "
            f"(ej. que contenga 'id', 'cod', 'alumno', 'estudiante', 'email', 'correo'). "
            f"Columnas encontradas: {list(df.columns)}"
        )


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

    # Validación estructural
    _validar_columnas_identificadoras(df)

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

    # Validación estructural
    _validar_columnas_identificadoras(df)

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