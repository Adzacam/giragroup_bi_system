"""
header_detector.py — Sprint 2
Detección heurística de encabezados compuestos en hojas de Excel.

Resuelve los siguientes problemas reales:
1. Encabezados de 2 niveles fusionados ("Bloque 1..." + "Unnamed: N")
   → los concatena en un solo encabezado descriptivo.
2. Encabezados desplazados/corruptos (correos electrónicos, fragmentos
   aleatorios como "farma", "contabili" usados como nombres de columna)
   → los detecta y descarta/corrige.
3. Filas de encabezado que no están en la fila 0
   → escanea las primeras N filas para encontrar la real.
"""

import re
import logging
import unicodedata
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Patrones que indican contenido de datos, NO encabezados
_PATRON_EMAIL = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$")
_PATRON_FECHA = re.compile(
    r"^\d{1,4}[-/]\d{1,2}[-/]\d{1,4}$"
    r"|^\d{1,2}\s+de\s+\w+\s+de\s+\d{4}$",
    re.IGNORECASE,
)
_PATRON_CI_MONTO = re.compile(r"^\d{5,}\.?\d*$")

# Términos clave ampliados que indican fila de encabezado real
_TERMINOS_CLAVE = [
    "id", "cod", "alumno", "estudiante", "email", "correo",
    "monto", "nota", "gestion", "gestión", "fecha", "ci", "nombre",
    "apellido", "deuda", "estado", "modulo", "módulo", "docente",
    "programa", "pos", "grupo", "grupos", "calificación", "calificacion",
    "bloque", "marca temporal", "timestamp", "pregunta", "comentario",
    "sugerencia", "aspectos", "contenido", "valoración", "valoracion",
    "carrera", "materia", "periodo", "semestre", "inscritos",
]


def _normalizar_texto(texto: str) -> str:
    """Normaliza texto: minúsculas, sin tildes, sin espacios extra."""
    t = str(texto).strip().lower()
    return "".join(
        ch for ch in unicodedata.normalize("NFD", t)
        if unicodedata.category(ch) != "Mn"
    )


def _es_valor_corrupto_como_header(valor: str) -> bool:
    """Detecta si un valor es inaceptable como nombre de columna."""
    v = str(valor).strip()
    if not v or v.lower() in ("nan", "none", ""):
        return True
    # Correos electrónicos no son encabezados
    if _PATRON_EMAIL.match(v):
        return True
    # CIs, montos u otros números largos no son encabezados
    if _PATRON_CI_MONTO.match(v):
        return True
    # Fechas no son encabezados
    if _PATRON_FECHA.match(v):
        return True
    # Fragmentos de 1-2 caracteres no alfabéticos
    if len(v) <= 2 and not v.isalpha():
        return True
    return False


def _score_fila_como_encabezado(fila: pd.Series) -> tuple[int, int]:
    """
    Evalúa qué tan probable es que una fila sea la fila de encabezados.

    Returns:
        (coincidencias_terminos_clave, total_celdas_texto_valido)
    """
    valores = fila.dropna().astype(str).tolist()
    coincidencias = 0
    celdas_validas = 0

    for val in valores:
        val_strip = val.strip()
        if not val_strip or val_strip.lower() in ("nan", "none"):
            continue

        # No contar valores que parecen datos, no encabezados
        if _es_valor_corrupto_como_header(val_strip):
            continue

        celdas_validas += 1
        val_norm = _normalizar_texto(val_strip)
        if any(tk in val_norm for tk in _TERMINOS_CLAVE):
            coincidencias += 1

    return coincidencias, celdas_validas


def _detectar_unnamed(columnas: list) -> bool:
    """Verifica si hay columnas 'Unnamed: N' indicando encabezados fusionados."""
    return any(
        str(c).startswith("Unnamed:") or str(c).startswith("unnamed_")
        for c in columnas
    )


def detectar_encabezado(
    df_raw: pd.DataFrame,
    n_filas_escaneo: int = 10,
) -> dict:
    """
    Analiza las primeras filas de un DataFrame crudo (sin header=)
    para detectar la estructura real de encabezados.

    Maneja:
    - Encabezados de un solo nivel (caso normal)
    - Encabezados de 2 niveles fusionados (Bloque + sub-pregunta)
    - Encabezados corruptos/desplazados

    Args:
        df_raw: DataFrame leído con header=None
        n_filas_escaneo: Número de filas a analizar

    Returns:
        {
            "fila_encabezado": int,        # índice de la fila de encabezado principal
            "es_doble_nivel": bool,         # True si hay 2 niveles fusionados
            "columnas_finales": list[str],  # Nombres de columna resueltos
            "columnas_corruptas": list[str],# Columnas detectadas como basura
            "encabezado_corrupto": bool,    # True si el encabezado es irrecuperable
        }
    """
    if df_raw.empty:
        return {
            "fila_encabezado": 0,
            "es_doble_nivel": False,
            "columnas_finales": [],
            "columnas_corruptas": [],
            "encabezado_corrupto": True,
        }

    limite = min(n_filas_escaneo, len(df_raw))

    # Evaluar cada fila candidata
    scores = []
    for i in range(limite):
        coincidencias, celdas_validas = _score_fila_como_encabezado(df_raw.iloc[i])
        scores.append({
            "fila": i,
            "coincidencias": coincidencias,
            "celdas_validas": celdas_validas,
        })

    # Elegir la fila con más coincidencias de términos clave
    mejor = max(scores, key=lambda x: (x["coincidencias"], x["celdas_validas"]))
    fila_header = mejor["fila"]

    # ── Detectar encabezado de 2 niveles ──────────────────────────────
    es_doble_nivel = False
    columnas_finales = []

    if fila_header > 0:
        # Verificar si la fila anterior parece un "bloque" de nivel superior
        fila_superior = df_raw.iloc[fila_header - 1]
        valores_sup = fila_superior.dropna().astype(str).tolist()
        valores_sup_no_vacios = [
            v for v in valores_sup
            if v.strip() and v.strip().lower() not in ("nan", "none")
        ]

        # Si la fila superior tiene pocos valores no vacíos
        # (porque las celdas fusionadas solo ponen valor en la primera celda del grupo),
        # es probable que sea el nivel superior de un encabezado de 2 niveles
        fila_inferior = df_raw.iloc[fila_header]
        n_cols = len(df_raw.columns)
        n_sup_no_vacios = len(valores_sup_no_vacios)

        if 0 < n_sup_no_vacios < n_cols * 0.6:
            # Probable encabezado de 2 niveles: fusionar
            es_doble_nivel = True
            ultimo_bloque = ""
            for col_idx in range(n_cols):
                val_sup = str(fila_superior.iloc[col_idx]).strip()
                val_inf = str(fila_inferior.iloc[col_idx]).strip()

                # Actualizar el bloque si la celda superior tiene valor
                if val_sup and val_sup.lower() not in ("nan", "none"):
                    ultimo_bloque = val_sup

                # Construir nombre fusionado
                if val_inf and val_inf.lower() not in ("nan", "none"):
                    if (
                        ultimo_bloque
                        and not val_inf.lower().startswith("unnamed")
                        and ultimo_bloque.lower() != val_inf.lower()
                    ):
                        nombre = f"{ultimo_bloque} — {val_inf}"
                    else:
                        nombre = val_inf
                elif ultimo_bloque:
                    nombre = ultimo_bloque
                else:
                    nombre = f"columna_{col_idx}"

                columnas_finales.append(nombre)

            logger.info(
                "Encabezado de 2 niveles detectado (filas %d-%d). "
                "Fusionado a %d columnas.",
                fila_header - 1, fila_header, len(columnas_finales),
            )

    # ── Encabezado de 1 solo nivel ────────────────────────────────────
    if not es_doble_nivel:
        fila_header_vals = df_raw.iloc[fila_header]
        for col_idx in range(len(df_raw.columns)):
            val = str(fila_header_vals.iloc[col_idx]).strip()
            if val and val.lower() not in ("nan", "none"):
                columnas_finales.append(val)
            else:
                columnas_finales.append(f"columna_{col_idx}")

    # ── Detección de corrupción residual ──────────────────────────────
    columnas_corruptas = []
    for col in columnas_finales:
        if _es_valor_corrupto_como_header(col) or col.startswith("columna_"):
            columnas_corruptas.append(col)

    encabezado_corrupto = len(columnas_corruptas) > len(columnas_finales) * 0.7

    if encabezado_corrupto:
        logger.warning(
            "Encabezado mayoritariamente corrupto: %d/%d columnas inválidas.",
            len(columnas_corruptas), len(columnas_finales),
        )

    # Normalizar nombres de columna: strip, lowercase, underscores
    columnas_limpias = []
    for c in columnas_finales:
        limpio = str(c).strip().lower().replace(" ", "_")
        # Eliminar caracteres no imprimibles
        limpio = re.sub(r"[^\w\s\-—áéíóúñü¿?¡!.,]", "", limpio, flags=re.UNICODE)
        limpio = re.sub(r"_+", "_", limpio).strip("_")
        if not limpio:
            limpio = f"columna_{len(columnas_limpias)}"
        columnas_limpias.append(limpio)

    return {
        "fila_encabezado": fila_header,
        "es_doble_nivel": es_doble_nivel,
        "columnas_finales": columnas_limpias,
        "columnas_corruptas": columnas_corruptas,
        "encabezado_corrupto": encabezado_corrupto,
    }


def aplicar_encabezado(
    df_raw: pd.DataFrame,
    resultado_deteccion: dict,
) -> pd.DataFrame:
    """
    Aplica los encabezados detectados al DataFrame crudo,
    recortando las filas superiores y renombrando las columnas.

    Returns:
        DataFrame con columnas limpias y datos a partir de la fila correcta.
    """
    fila_header = resultado_deteccion["fila_encabezado"]
    columnas = resultado_deteccion["columnas_finales"]
    es_doble = resultado_deteccion["es_doble_nivel"]

    # Determinar la primera fila de datos
    fila_datos = fila_header + 1
    if es_doble and fila_header > 0:
        # Los datos empiezan después de las 2 filas de encabezado
        fila_datos = fila_header + 1

    df = df_raw.iloc[fila_datos:].copy()

    # Ajustar columnas al tamaño del DataFrame
    if len(columnas) >= len(df.columns):
        df.columns = columnas[:len(df.columns)]
    else:
        # Más columnas en datos que en encabezados detectados
        extras = [f"columna_extra_{i}" for i in range(len(df.columns) - len(columnas))]
        df.columns = columnas + extras

    # Eliminar filas y columnas completamente vacías
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)

    df.reset_index(drop=True, inplace=True)
    return df
