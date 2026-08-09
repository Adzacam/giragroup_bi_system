"""
sheet_reader.py — GIRA-6 (Sprint 2 — refactorizado)
Lector multi-hoja de archivos XLSX/XLS/CSV con:
- Detección heurística de encabezados (1 o 2 niveles)
- Perfilado automático de columnas por contenido
- Clasificación de hojas en familias
- Mapeo canónico de columnas
- Descarte trazable de hojas no ingestables

Devuelve un contrato enriquecido por hoja, no un bloque monolítico.
"""

import pandas as pd
import os
import logging
from datetime import datetime, timezone
from typing import Optional

from pipeline.ingestion.header_detector import detectar_encabezado, aplicar_encabezado
from pipeline.ingestion.profiler import perfilar_hoja
from pipeline.ingestion.canonical_mapper import CanonicalMapper

logger = logging.getLogger(__name__)


def _crear_mapper() -> CanonicalMapper:
    """Crea una instancia del mapper canónico, tolerante a fallos."""
    try:
        return CanonicalMapper()
    except FileNotFoundError:
        logger.warning(
            "Diccionario canónico no encontrado. "
            "Operando sin mapeo de columnas."
        )
        return None


def leer_xlsx_multihoja(file_path: str, mapper: Optional[CanonicalMapper] = None) -> dict:
    """
    Lee TODAS las hojas de un archivo XLSX/XLS, aplicando detección de
    encabezados, perfilado y clasificación por hoja.

    Args:
        file_path: Ruta al archivo Excel.
        mapper: Instancia de CanonicalMapper (opcional, se crea si no se pasa).

    Returns:
        {
            "nombre_archivo": str,
            "procesado_en": str (ISO),
            "hojas": [
                {
                    "nombre_hoja": str,
                    "familia": str,
                    "razon_clasificacion": str,
                    "data": pd.DataFrame,
                    "mapeo_columnas": dict,
                    "columnas_no_mapeadas": list,
                    "columnas_texto_libre": list[str],
                    "n_filas": int,
                    "encabezado_info": dict,
                }
            ],
            "hojas_descartadas": [
                {"nombre_hoja": str, "razon": str}
            ],
            "estadisticas": {
                "total_hojas": int,
                "hojas_procesadas": int,
                "hojas_descartadas": int,
            }
        }
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    if mapper is None:
        mapper = _crear_mapper()

    nombre_archivo = os.path.basename(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    # Obtener config del profiler desde el mapper
    config_profiler = mapper.config if mapper else {}

    # ── Lectura de hojas ──────────────────────────────────────────────
    if ext == ".csv":
        # CSV: una sola "hoja"
        hojas_raw = {"Hoja1": pd.read_csv(
            file_path, encoding="utf-8", on_bad_lines="skip", header=None
        )}
    else:
        # XLSX/XLS: todas las hojas
        try:
            hojas_raw = pd.read_excel(
                file_path, sheet_name=None, header=None, engine="openpyxl"
            )
        except Exception:
            # Fallback para .xls
            hojas_raw = pd.read_excel(
                file_path, sheet_name=None, header=None
            )

    hojas_procesadas = []
    hojas_descartadas = []

    for nombre_hoja, df_raw in hojas_raw.items():
        nombre_hoja_str = str(nombre_hoja)

        # ── Paso 1: Verificar si la hoja es descartable por nombre ────
        if mapper:
            es_descartable, razon = mapper.es_hoja_descartable(nombre_hoja_str)
            if es_descartable:
                hojas_descartadas.append({
                    "nombre_hoja": nombre_hoja_str,
                    "razon": razon,
                })
                logger.info(
                    "Hoja '%s' descartada por nombre: %s",
                    nombre_hoja_str, razon,
                )
                continue

        # ── Paso 2: Verificar si está completamente vacía ─────────────
        if df_raw.dropna(how="all").empty:
            hojas_descartadas.append({
                "nombre_hoja": nombre_hoja_str,
                "razon": "HOJA_VACIA",
            })
            logger.info("Hoja '%s' descartada: vacía.", nombre_hoja_str)
            continue

        # ── Paso 3: Detectar encabezados ──────────────────────────────
        resultado_header = detectar_encabezado(df_raw)

        if resultado_header["encabezado_corrupto"]:
            hojas_descartadas.append({
                "nombre_hoja": nombre_hoja_str,
                "razon": "ENCABEZADO_CORRUPTO",
            })
            logger.warning(
                "Hoja '%s' descartada: encabezado mayoritariamente corrupto.",
                nombre_hoja_str,
            )
            continue

        # ── Paso 4: Aplicar encabezados y obtener DataFrame limpio ────
        df_limpio = aplicar_encabezado(df_raw, resultado_header)

        if df_limpio.empty:
            hojas_descartadas.append({
                "nombre_hoja": nombre_hoja_str,
                "razon": "HOJA_VACIA",
            })
            continue

        # Llenar NaN con cadena vacía para coherencia
        df_limpio = df_limpio.fillna("")

        # ── Paso 5: Perfilar columnas y clasificar hoja ───────────────
        perfil_hoja = perfilar_hoja(
            df_limpio, nombre_hoja_str, config=config_profiler
        )

        # ── Paso 6: Mapeo canónico de columnas con validación por perfil ────
        mapeo_resultado = None
        columnas_no_mapeadas = []
        if mapper:
            perfiles_map = {
                p["nombre"]: p for p in perfil_hoja.get("perfiles_columnas", [])
            }
            es_encuesta = (perfil_hoja.get("familia") == "texto_libre")
            mapeo_resultado = mapper.resolver_columnas_df(
                df_limpio.columns.tolist(),
                perfiles_map=perfiles_map,
                es_encuesta=es_encuesta,
                df=df_limpio,
            )
            columnas_no_mapeadas = mapeo_resultado.get("no_mapeadas", [])

            # Regla de especificidad de coincidencia canónica:
            # Si la hoja tiene al menos 1 campo mapeado a una pregunta abierta de encuesta específica (especifica: true),
            # prevalece como texto_libre (salvo que sea de la familia financiero o descartable).
            has_pregunta_especifica = False
            for col_orig, campo_can in mapeo_resultado.get("mapeo", {}).items():
                if campo_can and mapper.es_campo_pregunta_especifica(campo_can):
                    has_pregunta_especifica = True
                    break

            if has_pregunta_especifica and perfil_hoja["familia"] not in ("financiero", "descartable"):
                perfil_hoja["familia"] = "texto_libre"
                perfil_hoja["razon_clasificacion"] = (
                    "Coincidencia de alta confianza con pregunta abierta de encuesta específica"
                )

        # ── Paso 7: Determinar columnas de texto libre ────────────────────────
        # Combinar columnas de texto libre por profiler con las preguntas abiertas del diccionario canónico
        _CAMPOS_ESTRUCTURALES_RECHAZO = {
            "pos", "identificador_persona", "correo_persona", "nombre_persona",
            "nombre_programa", "fecha_evento", "grupo", "modulo", "docente"
        }
        _PREGUNTAS_ABIERTAS_TAGS = {
            "sugerencia_estilo_docente", "comentario_general", "contenido_a_explorar",
            "valoracion_positiva_docente", "valoracion_contenido"
        }

        cols_abiertas_mapeadas = []
        if mapeo_resultado:
            for col_orig, campo_can in mapeo_resultado.get("mapeo", {}).items():
                if campo_can in _PREGUNTAS_ABIERTAS_TAGS:
                    cols_abiertas_mapeadas.append(col_orig)

        cols_texto_final = list(set(perfil_hoja["columnas_texto_libre"] + cols_abiertas_mapeadas))
        cols_texto_final = [
            c for c in cols_texto_final
            if mapeo_resultado.get("mapeo", {}).get(c) not in _CAMPOS_ESTRUCTURALES_RECHAZO
        ]

        # Verificar si es descartable por contenido
        if perfil_hoja["familia"] == "descartable":
            hojas_descartadas.append({
                "nombre_hoja": nombre_hoja_str,
                "razon": perfil_hoja["razon_clasificacion"],
            })
            logger.info(
                "Hoja '%s' descartada por contenido: %s",
                nombre_hoja_str, perfil_hoja["razon_clasificacion"],
            )
            continue

        hojas_procesadas.append({
            "nombre_hoja": nombre_hoja_str,
            "familia": perfil_hoja["familia"],
            "razon_clasificacion": perfil_hoja["razon_clasificacion"],
            "data": df_limpio,
            "mapeo_columnas": mapeo_resultado.get("mapeo", {}) if mapeo_resultado else {},
            "columnas_no_mapeadas": columnas_no_mapeadas,
            "columnas_texto_libre": cols_texto_final,
            "columnas_identificadoras": perfil_hoja.get("columnas_identificadoras", []),
            "n_filas": len(df_limpio),
            "encabezado_info": {
                "fila_encabezado": resultado_header["fila_encabezado"],
                "es_doble_nivel": resultado_header["es_doble_nivel"],
                "columnas_corruptas": resultado_header["columnas_corruptas"],
            },
        })

    return {
        "nombre_archivo": nombre_archivo,
        "procesado_en": datetime.now(timezone.utc).isoformat(),
        "hojas": hojas_procesadas,
        "hojas_descartadas": hojas_descartadas,
        "estadisticas": {
            "total_hojas": len(hojas_raw),
            "hojas_procesadas": len(hojas_procesadas),
            "hojas_descartadas": len(hojas_descartadas),
        },
    }


# ── Función legacy para retrocompatibilidad ──────────────────────────────


def leer_xlsx(file_path: str) -> dict:
    """
    Función legacy que mantiene el contrato de salida original del Sprint 1.
    Internamente usa el nuevo lector multi-hoja y aplana el resultado
    a la primera hoja procesable.
    """
    resultado = leer_xlsx_multihoja(file_path)
    hojas = resultado["hojas"]

    if not hojas:
        raise ValueError(
            f"No se encontraron hojas procesables en '{file_path}'. "
            f"Hojas descartadas: {resultado['hojas_descartadas']}"
        )

    # Tomar la primera hoja procesable
    primera = hojas[0]
    df = primera["data"]

    filas = df.to_dict(orient="records")
    texto_plano = _dataframe_a_texto(df)

    return {
        "texto_plano": texto_plano,
        "fuente_tipo": "SHEET",
        "nombre_archivo": resultado["nombre_archivo"],
        "filas_raw": filas,
        "procesado_en": resultado["procesado_en"],
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
    resultado_header = detectar_encabezado(df_raw)
    df = aplicar_encabezado(df_raw, resultado_header)

    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)
    df = df.fillna("")

    texto_plano = _dataframe_a_texto(df)

    return {
        "texto_plano": texto_plano,
        "fuente_tipo": "SHEET",
        "nombre_archivo": f"gsheet_{sheet_id}",
        "filas_raw": df.to_dict(orient="records"),
        "procesado_en": datetime.now(timezone.utc).isoformat(),
    }


def _dataframe_a_texto(df: pd.DataFrame) -> str:
    """Convierte un DataFrame a texto plano fila por fila para BETO."""
    lineas = []
    for _, row in df.iterrows():
        partes = [f"{col}: {val}" for col, val in row.items() if str(val).strip()]
        lineas.append(" | ".join(partes))
    return "\n".join(lineas)