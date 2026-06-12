"""
sheet_reader.py — GIRA-6
Lector de archivos XLSX/CSV locales y Google Sheets remotos.
Devuelve el contrato de salida estándar del pipeline.
Incluye extracción dinámica de tablas (saltando títulos).
"""

import pandas as pd
import os
import unicodedata
import logging
from datetime import datetime
from typing import Union

logger = logging.getLogger(__name__)

# Términos clave esperados en una fila de encabezados BI
_TERMINOS_CLAVE = [
    "id", "cod", "alumno", "estudiante", "email", "correo", 
    "monto", "nota", "gestion", "fecha", "ci", "nombre", "apellido",
    "deuda", "estado", "modulo", "docente"
]


def _normalizar_texto(texto: str) -> str:
    """Normaliza un texto eliminando acentos y espacios extra."""
    t = str(texto).strip().lower()
    return "".join(ch for ch in unicodedata.normalize("NFD", t) if unicodedata.category(ch) != "Mn")


def _encontrar_fila_encabezados(df: pd.DataFrame, n_filas: int = 20) -> int:
    """
    Escanea las primeras N filas buscando la fila que tenga más coincidencias
    con los términos clave de BI. Devuelve el índice de esa fila.
    """
    max_coincidencias = 0
    fila_seleccionada = 0

    limite = min(n_filas, len(df))
    for i in range(limite):
        fila_valores = df.iloc[i].dropna().astype(str).tolist()
        coincidencias = 0
        
        for val in fila_valores:
            val_norm = _normalizar_texto(val)
            # Otorgar punto si el valor normalizado contiene algún término clave
            if any(tk in val_norm for tk in _TERMINOS_CLAVE):
                coincidencias += 1
                
        if coincidencias > max_coincidencias:
            max_coincidencias = coincidencias
            fila_seleccionada = i

    # Si no se encontró ninguna coincidencia razonable (al menos 1), 
    # se asume que es la fila 0 por defecto.
    if max_coincidencias < 1:
        logger.warning("No se detectaron cabeceras claras en las primeras %d filas. Usando fila 0 por defecto.", n_filas)
        return 0
        
    logger.info("Cabeceras detectadas en la fila %d con %d coincidencias clave.", fila_seleccionada, max_coincidencias)
    return fila_seleccionada


def _validar_columnas_identificadoras(columnas: list) -> None:
    """Valida que la lista de columnas contenga al menos una identificadora primaria."""
    encontrado = False
    for col in columnas:
        if any(tk in col for tk in ["id", "cod", "alumno", "estudiante", "email", "correo", "ci"]):
            encontrado = True
            break
            
    if not encontrado:
        raise ValueError(
            "Fallo de validacion estructural: No se encontro ninguna columna identificadora primaria "
            f"(ej. que contenga 'id', 'cod', 'alumno', 'estudiante', 'email', 'correo'). "
            f"Columnas detectadas: {columnas}"
        )


def leer_xlsx(file_path: str) -> dict:
    """Lee archivos .xlsx o .csv locales con detección heurística de cabeceras."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    # Paso 1: Leer crudo sin encabezados
    if ext == ".csv":
        df_raw = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip", header=None)
    else:
        df_raw = pd.read_excel(file_path, sheet_name=0, header=None)

    # Si está completamente vacío
    if df_raw.empty:
        raise ValueError("El archivo está vacío.")

    # Paso 2: Escanear en busca de los verdaderos encabezados
    idx_header = _encontrar_fila_encabezados(df_raw)

    # Paso 3: Promover la fila seleccionada a cabecera y recortar el top
    nuevas_cabeceras = df_raw.iloc[idx_header]
    df = df_raw.iloc[idx_header + 1:].copy()
    df.columns = nuevas_cabeceras

    # Paso 4: Limpieza estructural (eliminar márgenes vacíos)
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)

    # Renombrar columnas vacías que hayan sobrevivido
    df.columns = [str(c).strip().lower().replace(" ", "_") if pd.notna(c) else f"unnamed_{i}" for i, c in enumerate(df.columns)]
    df = df.fillna("")

    # Paso 5: Validación
    _validar_columnas_identificadoras(df.columns.tolist())

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
    
    # Obtenemos los valores crudos para pasar por la heurística
    raw_values = sheet.get_all_values()
    if not raw_values:
        raise ValueError("El Google Sheet está vacío.")
        
    df_raw = pd.DataFrame(raw_values)
    idx_header = _encontrar_fila_encabezados(df_raw)
    
    nuevas_cabeceras = df_raw.iloc[idx_header]
    df = df_raw.iloc[idx_header + 1:].copy()
    df.columns = nuevas_cabeceras

    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)
    df.columns = [str(c).strip().lower().replace(" ", "_") if pd.notna(c) and str(c).strip() else f"unnamed_{i}" for i, c in enumerate(df.columns)]
    df = df.fillna("")

    _validar_columnas_identificadoras(df.columns.tolist())

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