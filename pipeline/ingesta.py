"""
ingesta.py — Sprint 2, Loop 1
Lector universal de archivos heterogéneos.

Arquitectura: registro dinámico de funciones lectoras por extensión.
Para agregar soporte a un nuevo tipo de archivo (ej. .json, .parquet),
basta con definir una función con la firma:

    def leer_mi_formato(ruta: str) -> dict[str, pd.DataFrame]:
        ...

y registrarla:

    LECTORES[".json"] = leer_mi_formato

No se necesita herencia, subclases ni modificar código existente.

Restricción: toda validación se hace contra uploads/data (corpus real).
Queda prohibido usar uploads/test o datos sintéticos preexistentes.
"""

import csv
import logging
import os
from pathlib import Path
from typing import Callable

import pandas as pd

logger = logging.getLogger(__name__)

# ── Tipo de la función lectora ──────────────────────────────────────
# Recibe una ruta, devuelve {nombre_hoja: DataFrame_crudo}.
# Para formatos sin concepto de "hoja" (como CSV), la clave es el
# nombre del archivo sin extensión.
LectorFn = Callable[[str], dict[str, pd.DataFrame]]


# ── Lectores concretos ──────────────────────────────────────────────

def _leer_xlsx(ruta: str) -> dict[str, pd.DataFrame]:
    """
    Lee todas las hojas de un archivo .xlsx/.xls sin procesar nada:
    sin header, sin dropna, sin fillna. Devuelve los DataFrames tal
    cual los entrega pandas/openpyxl.
    """
    try:
        hojas = pd.read_excel(
            ruta,
            sheet_name=None,   # todas las hojas
            header=None,       # no asumir fila de encabezado
            dtype=str,         # todo como texto para no perder datos
        )
    except Exception:
        # Fallback para .xls (xlrd engine)
        try:
            hojas = pd.read_excel(
                ruta,
                sheet_name=None,
                header=None,
                dtype=str,
                engine="xlrd",
            )
        except Exception as e:
            logger.error("No se pudo leer '%s': %s", ruta, e)
            return {}

    logger.info(
        "Archivo '%s': %d hoja(s) leída(s).",
        os.path.basename(ruta), len(hojas),
    )
    return hojas


def _leer_csv(ruta: str) -> dict[str, pd.DataFrame]:
    """
    Lee un archivo CSV completo como una sola "hoja".
    La clave del dict es el nombre del archivo sin extensión.
    """
    nombre = Path(ruta).stem
    try:
        # Detectar delimitador
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            muestra = f.read(4096)
        try:
            dialecto = csv.Sniffer().sniff(muestra)
            sep = dialecto.delimiter
        except csv.Error:
            sep = ","

        df = pd.read_csv(ruta, header=None, dtype=str, sep=sep)
        logger.info(
            "Archivo CSV '%s': 1 hoja, %d filas × %d columnas.",
            os.path.basename(ruta), len(df), len(df.columns),
        )
        return {nombre: df}
    except Exception as e:
        logger.error("No se pudo leer CSV '%s': %s", ruta, e)
        return {}


# ── Registro de lectores por extensión ──────────────────────────────
# Para agregar un nuevo formato:
#   from pipeline.ingesta import LECTORES
#   LECTORES[".json"] = mi_funcion_lectora_json
LECTORES: dict[str, LectorFn] = {
    ".xlsx": _leer_xlsx,
    ".xls":  _leer_xlsx,
    ".csv":  _leer_csv,
}


# ── Función pública principal ───────────────────────────────────────

def leer_archivo(ruta: str) -> dict[str, pd.DataFrame]:
    """
    Lee un archivo y devuelve un dict {nombre_hoja: DataFrame_crudo}.

    - Si la extensión no está soportada, loguea un warning y devuelve {}.
    - Si el archivo no existe, loguea un error y devuelve {}.
    - Nunca lanza excepciones: loguea y continúa.
    """
    if not os.path.exists(ruta):
        logger.error("Archivo no encontrado: '%s'", ruta)
        return {}

    ext = Path(ruta).suffix.lower()
    lector = LECTORES.get(ext)

    if lector is None:
        logger.warning(
            "Extensión '%s' no soportada para '%s'. "
            "Extensiones válidas: %s",
            ext, ruta, list(LECTORES.keys()),
        )
        return {}

    return lector(ruta)


def leer_corpus(directorio: str) -> dict[str, dict[str, pd.DataFrame]]:
    """
    Lee todos los archivos soportados dentro de un directorio.
    Devuelve {nombre_archivo: {nombre_hoja: DataFrame}}.

    Nunca se detiene por un archivo corrupto: loguea el error y
    continúa con el siguiente.
    """
    resultados = {}
    ruta_dir = Path(directorio)

    if not ruta_dir.is_dir():
        logger.error("Directorio no encontrado: '%s'", directorio)
        return resultados

    archivos = sorted(
        f for f in ruta_dir.iterdir()
        if f.is_file() and f.suffix.lower() in LECTORES
    )

    logger.info(
        "Corpus '%s': %d archivo(s) soportado(s) encontrado(s).",
        directorio, len(archivos),
    )

    for archivo in archivos:
        hojas = leer_archivo(str(archivo))
        resultados[archivo.name] = hojas

    return resultados


# ═══════════════════════════════════════════════════════════════════════
# Loop 2 — Detección aislada de bloques de datos (Islas Tabulares)
# ═══════════════════════════════════════════════════════════════════════
#
# Dentro de una sola hoja de Excel pueden coexistir varias tablas
# apiladas verticalmente, separadas por filas vacías. Este módulo
# detecta esos "bloques" (islas) de forma independiente a cualquier
# lógica de categorización o extracción semántica.
#
# Heurística:
#   - Una fila se considera vacía si TODAS sus celdas son NaN o cadena
#     vacía (después de strip).
#   - Un gap de ≥ GAP_THRESHOLD filas vacías consecutivas marca el
#     límite entre dos islas.
#   - Un bloque con < MIN_FILAS_ISLA filas de datos se marca como
#     ruido (no se descarta, se etiqueta — la decisión de qué hacer
#     con él es de la capa de extracción, Loop 3).

GAP_THRESHOLD = 2   # filas vacías consecutivas para cortar
MIN_FILAS_ISLA = 2  # mínimo de filas de datos para no ser ruido


def _fila_esta_vacia(fila: pd.Series) -> bool:
    """True si todos los valores de la fila son NaN o cadena vacía/whitespace."""
    for v in fila:
        if pd.notna(v) and str(v).strip() != "":
            return False
    return True


def detectar_islas(
    df: pd.DataFrame,
    gap_threshold: int = GAP_THRESHOLD,
    min_filas: int = MIN_FILAS_ISLA,
) -> list[dict]:
    """
    Detecta bloques de datos (islas) dentro de un DataFrame crudo.

    Retorna una lista de dicts, uno por isla encontrada:
        {
            "indice":      int,           # número secuencial de isla (0-based)
            "fila_inicio": int,           # fila original donde empieza
            "fila_fin":    int,           # fila original donde termina (inclusive)
            "n_filas":     int,           # cantidad de filas de datos
            "es_ruido":    bool,          # True si n_filas < min_filas
            "df":          pd.DataFrame,  # sub-DataFrame con los datos de la isla
        }

    Si el DataFrame está completamente vacío, retorna lista vacía.
    """
    if df.empty or len(df) == 0:
        return []

    # Marcar cada fila como vacía o no
    vacias = [_fila_esta_vacia(df.iloc[i]) for i in range(len(df))]

    # Encontrar los rangos de filas NO vacías agrupadas
    islas = []
    en_isla = False
    gap_count = 0
    inicio_isla = 0

    for i, es_vacia in enumerate(vacias):
        if not es_vacia:
            if not en_isla:
                # Empezamos una nueva isla
                inicio_isla = i
                en_isla = True
            gap_count = 0
        else:
            if en_isla:
                gap_count += 1
                if gap_count >= gap_threshold:
                    # Cerramos la isla anterior (el fin real es antes del gap)
                    fin_isla = i - gap_count
                    islas.append((inicio_isla, fin_isla))
                    en_isla = False
                    gap_count = 0

    # Si terminamos dentro de una isla, cerrarla
    if en_isla:
        # Encontrar la última fila no vacía
        fin_isla = len(vacias) - 1
        while fin_isla >= inicio_isla and vacias[fin_isla]:
            fin_isla -= 1
        if fin_isla >= inicio_isla:
            islas.append((inicio_isla, fin_isla))

    # Construir resultado
    resultado = []
    for idx, (inicio, fin) in enumerate(islas):
        sub_df = df.iloc[inicio:fin + 1].reset_index(drop=True)
        n_filas = len(sub_df)
        resultado.append({
            "indice": idx,
            "fila_inicio": inicio,
            "fila_fin": fin,
            "n_filas": n_filas,
            "es_ruido": n_filas < min_filas,
            "df": sub_df,
        })

    return resultado


def segmentar_archivo(
    hojas: dict[str, pd.DataFrame],
    gap_threshold: int = GAP_THRESHOLD,
    min_filas: int = MIN_FILAS_ISLA,
) -> dict[str, list[dict]]:
    """
    Aplica la detección de islas a todas las hojas de un archivo.

    Recibe el dict {nombre_hoja: DataFrame} que devuelve leer_archivo().
    Retorna {nombre_hoja: [lista_de_islas]}.

    Ejemplo de uso:
        hojas = leer_archivo("mi_archivo.xlsx")
        bloques = segmentar_archivo(hojas)
        for hoja, islas in bloques.items():
            print(f"{hoja}: {len(islas)} isla(s)")
            for isla in islas:
                print(f"  Isla {isla['indice']}: filas {isla['fila_inicio']}-{isla['fila_fin']}, ruido={isla['es_ruido']}")
    """
    resultado = {}
    for nombre_hoja, df in hojas.items():
        islas = detectar_islas(df, gap_threshold=gap_threshold, min_filas=min_filas)
        resultado[nombre_hoja] = islas

        n_ruido = sum(1 for i in islas if i["es_ruido"])
        n_validas = len(islas) - n_ruido
        logger.info(
            "Hoja '%s': %d isla(s) detectada(s) (%d válida(s), %d ruido).",
            nombre_hoja, len(islas), n_validas, n_ruido,
        )

    return resultado

