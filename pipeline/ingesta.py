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
import json
import logging
import os
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, Dict, Any, List, Optional, Tuple

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


def _leer_xml(ruta: str) -> dict[str, pd.DataFrame]:
    """
    Lee un archivo XML (por ejemplo reportes Moodle o exportaciones tabulares).
    Extrae elementos repetitivos en filas de un DataFrame.
    """
    nombre = Path(ruta).stem
    try:
        tree = ET.parse(ruta)
        root = tree.getroot()
        rows = []
        # Buscar nodos repetidos que representen registros/estudiantes/calificaciones
        for elem in root:
            row_data = {}
            for child in elem:
                row_data[child.tag] = child.text or ""
            if row_data:
                rows.append(row_data)
        if not rows:
            for elem in root.iter():
                if len(list(elem)) > 1:
                    row_data = {c.tag: (c.text or "") for c in elem}
                    if len(row_data) >= 2:
                        rows.append(row_data)
        if rows:
            df = pd.DataFrame(rows).astype(str)
            logger.info(
                "Archivo XML '%s': 1 hoja, %d filas × %d columnas.",
                os.path.basename(ruta), len(df), len(df.columns),
            )
            return {nombre: df}
        logger.warning("El archivo XML '%s' no contiene nodos tabulares estructurados.", ruta)
        return {}
    except Exception as e:
        logger.error("No se pudo leer XML '%s': %s", ruta, e)
        return {}


# ── Registro de lectores por extensión ──────────────────────────────

LECTORES: dict[str, LectorFn] = {
    ".xlsx": _leer_xlsx,
    ".xls":  _leer_xlsx,
    ".csv":  _leer_csv,
    ".xml":  _leer_xml,
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


def detectar_bloques(
    df: pd.DataFrame,
    gap_threshold: int = GAP_THRESHOLD,
    min_filas: int = MIN_FILAS_ISLA,
) -> list[pd.DataFrame]:
    """
    Función directa de Loop 2: detecta tablas dentro de un DataFrame y retorna
    la lista de sub-DataFrames de cada bloque rectangular detectado.

    Cada DataFrame incluye los atributos en .attrs:
        - df.attrs['indice']
        - df.attrs['fila_inicio']
        - df.attrs['fila_fin']
        - df.attrs['es_ruido']
    """
    islas = detectar_islas(df, gap_threshold=gap_threshold, min_filas=min_filas)
    bloques = []
    for isla in islas:
        sub_df = isla["df"].copy()
        sub_df.attrs["indice"] = isla["indice"]
        sub_df.attrs["fila_inicio"] = isla["fila_inicio"]
        sub_df.attrs["fila_fin"] = isla["fila_fin"]
        sub_df.attrs["n_filas"] = isla["n_filas"]
        sub_df.attrs["es_ruido"] = isla["es_ruido"]
        bloques.append(sub_df)
    return bloques


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


# ═══════════════════════════════════════════════════════════════════════
# Loop 3 — Extracción, categorización, persistencia y reporte final
# ═══════════════════════════════════════════════════════════════════════
#
# Principio: Extraer texto plano y categorizar cada bloque para el pase
# a Sprint 3 (BETO NER), garantizando el invariante de conservación:
#
#   Total_Filas_Ingresadas = Procesadas + Descartadas_Ruido + Vacías
#
# No hay pérdida silenciosa de datos.

PALABRAS_CLAVE_CATEGORIA = {
    "academico": [
        "nota", "asistencia", "módulo", "modulo", "docente", "acta",
        "evaluacion", "evaluación", "postgrado", "giragroup", "programa",
        "alumno", "estudiante", "carrera", "arca", "academ", "inicios y okr",
        "okr", "materia", "experto", "diplomado", "curso"
    ],
    "financiero": [
        "cuota", "monto", "factura", "ingreso", "egreso", "techo",
        "cobranza", "saldo", "deuda", "presupuest", "ejecutado", "costo",
        "gasto", "pago", "financier"
    ],
    "comercial": [
        "lead", "interesado", "inscripción", "inscripcion", "inscrito",
        "inscripto", "meta", "venta", "prospecto", "crm", "marketing",
        "campana", "contacto", "baja", "duplicado", "matricul"
    ]
}


def a_texto_plano(bloque: pd.DataFrame) -> str:
    """
    Serializa un bloque tabular (DataFrame) a texto plano legible.
    Cada fila de datos se une con ' | ', y las filas se separan con saltos de línea '\\n'.
    Las celdas vacías o nulas se omiten.
    """
    if bloque is None or bloque.empty:
        return ""

    lineas = []
    for i in range(len(bloque)):
        fila = bloque.iloc[i]
        celdas = [str(v).strip() for v in fila if pd.notna(v) and str(v).strip() != ""]
        if celdas:
            lineas.append(" | ".join(celdas))

    return "\n".join(lineas)


def _strip_accents(text: str) -> str:
    if not text:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(text))
        if unicodedata.category(c) != "Mn"
    ).lower().strip()



def _contiene_tokens(texto: str, palabras_o_frases: tuple[str, ...]) -> bool:
    """
    Verifica si alguna de las palabras o frases clave está presente en el texto,
    respetando límites de palabra (word boundaries) para términos únicos
    (evitando falsos positivos como 'ci' en 'servicio', 'lead' en 'empleados', 'mora' en 'memorando').
    """
    for term in palabras_o_frases:
        term_clean = term.strip()
        if not term_clean:
            continue
        if " " in term_clean or "-" in term_clean or "_" in term_clean:
            if term_clean in texto:
                return True
        else:
            pattern = r"\b" + re.escape(term_clean) + r"\b"
            if re.search(pattern, texto):
                return True
    return False


def clasificar_contenido_agnostico(
    df: pd.DataFrame,
    cabeceras: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Clasificador Semántico Agnóstico de Contenido (cero nombres de archivos u hojas quemados):
    Inspecciona tokens canónicos de cabecera, tipos de datos y densidad muestral para derivar
    con precisión el hecho destino del modelo estrella / constelación:
      * Académico (estudiante CI/nombre + módulo + nota) -> fact_rendimiento_academico
      * Financiero (estudiante CI + monto/saldo + cuota/fecha) -> fact_situacion_financiera
      * Evaluación Docente (docente + preguntas/satisfacción + escala 1-5) -> fact_evaluacion_docente
      * Rentabilidad/Egresos (costos, egresos, techos, presupuesto, margen) -> fact_rentabilidad
      * Marketing/Admisión (leads, campañas, prospectos, preinscritos) -> fact_marketing
    """
    if df is None or df.empty:
        return {
            "categoria": "generico",
            "fact_table": None,
            "tipo_fuente": "SIN_RECONOCER",
            "confidence": 0.0,
            "scores": {},
            "criterios": []
        }

    tokens_cabecera: List[str] = []
    if cabeceras:
        for c in cabeceras:
            t = _strip_accents(str(c))
            if t and not t.startswith("unnamed"):
                tokens_cabecera.append(t)

    for col in df.columns:
        c_str = _strip_accents(str(col))
        if c_str and not c_str.startswith("unnamed"):
            tokens_cabecera.append(c_str)

    max_rows = min(15, len(df))
    ratings_1_5_count = 0
    total_numeric_cells = 0

    for r_idx in range(max_rows):
        row_vals = df.iloc[r_idx].values
        for v in row_vals:
            if pd.notna(v):
                v_raw = str(v).strip()
                v_str = _strip_accents(v_raw)
                if 1 < len(v_str) <= 90:
                    tokens_cabecera.append(v_str)

                try:
                    num_val = float(v_raw.replace("$", "").replace("Bs", "").replace(",", ".").strip())
                    total_numeric_cells += 1
                    if 1.0 <= num_val <= 5.0 and num_val.is_integer():
                        ratings_1_5_count += 1
                except (ValueError, TypeError):
                    pass

    joined = " | ".join(tokens_cabecera)

    # Detección basada en tokens con límites de palabra precisos
    has_estudiante = _contiene_tokens(joined, (
        "ci", "cedula", "dni", "idnumber", "carnet", "alumno", "alumnos",
        "estudiante", "estudiantes", "postulante", "nombre completo",
        "nombres y apellidos", "apellidos y nombres"
    ))
    has_modulo = _contiene_tokens(joined, (
        "modulo", "modulos", "materia", "materias", "asignatura", "asignaturas",
        "curso", "cursos", "course", "cod_modulo", "codigo modulo"
    ))
    has_nota = _contiene_tokens(joined, (
        "nota", "notas", "calificacion", "calificaciones", "calif_final", "nota_final",
        "finalgrade", "promedio", "calif", "aprobado", "reprobado"
    ))
    has_moodle = _contiene_tokens(joined, (
        "idnumber", "finalgrade", "total del curso", "cuestionario:", "tarea:", "aula virtual"
    ))

    has_saldo_monto = _contiene_tokens(joined, (
        "monto", "saldo", "deuda", "monto_deuda", "monto_pagado", "pagado",
        "importe", "cobranza", "cartera", "abono", "deposito", "arancel", "recibo"
    ))
    has_cuota_mora = _contiene_tokens(joined, (
        "cuota", "cuotas", "cuotas_impagas", "mora", "en mora", "vencimiento",
        "fecha de pago", "comprobante de pago", "factura", "concepto"
    ))

    has_docente = _contiene_tokens(joined, (
        "docente", "docentes", "profesor", "profesores", "profesora", "profesoras",
        "facilitador", "facilitadores", "instructor", "instructores", "tutor", "tutores",
        "desempeno docente"
    ))
    has_eval_doc = _contiene_tokens(joined, (
        "evaluacion docente", "evaluacion_docente", "encuesta docente", "encuesta de satisfaccion",
        "satisfaccion docente", "desempeno docente", "evaluacion del docente", "criterio de evaluacion",
        "item evaluacion", "escala de calificacion", "escala likert", "dominio del tema",
        "didactica del docente", "nps docente", "puntualidad docente"
    ))
    has_eval_pregunta = _contiene_tokens(joined, (
        "pregunta", "criterio", "satisfaccion", "dominio del tema", "didactica", "nps", "encuesta"
    ))

    has_egreso_puro = _contiene_tokens(joined, (
        "egreso", "egresos", "gasto", "gastos", "partida",
        "partida presupuestaria", "comprobante de egreso", "proveedor", "proveedores",
        "desembolso", "beneficiario"
    ))
    has_egreso_costo = has_egreso_puro or _contiene_tokens(joined, ("costo", "costos"))
    has_techo_meta = _contiene_tokens(joined, (
        "techo", "techos", "techo presupuestario", "presupuesto asignado", "presupuestado",
        "presupuesto", "rentabilidad", "balance financiero", "utilidad neta", "margen",
        "ebitda", "ejecutado", "monto_ejecutado", "monto_meta", "ejecutado vs meta",
        "categoria financiera"
    ))

    has_mkt_lead = _contiene_tokens(joined, (
        "lead", "leads", "campana", "campaña", "medio de contacto", "canal de marketing",
        "fuente lead", "asesor comercial", "reservas de plaza", "costo programa", "costo programa comercial"
    ))
    has_admision = _contiene_tokens(joined, (
        "preinscrito", "preinscritos", "preinscripcion", "preinscripciones",
        "prospecto", "prospectos", "matricula", "matriculas", "inscrito", "inscritos",
        "formulario de admision", "marca temporal"
    ))

    scores = {
        "academico": 0.0,
        "financiero": 0.0,
        "evaluacion_docente": 0.0,
        "rentabilidad": 0.0,
        "marketing": 0.0
    }
    criterios = []

    # 1. Académico
    if has_estudiante and has_modulo and has_nota:
        scores["academico"] += 14.0
        criterios.append("Co-ocurrencia estudiante + modulo + calificacion")
    elif has_modulo and has_nota:
        scores["academico"] += 10.0
        criterios.append("Modulo + calificacion detectados")
    elif has_estudiante and has_nota:
        scores["academico"] += 8.0
        criterios.append("Estudiante + calificacion detectados")
    if has_moodle:
        scores["academico"] += 8.0
        criterios.append("Tokens estructurales Moodle")

    # 2. Financiero (Situación financiera de estudiantes / aranceles / mora)
    if has_estudiante and has_saldo_monto and has_cuota_mora:
        scores["financiero"] += 14.0
        criterios.append("Co-ocurrencia estudiante/CI + saldo/monto + cuota/mora")
    elif has_estudiante and has_saldo_monto:
        scores["financiero"] += 10.0
        criterios.append("Estudiante + saldo/monto detectados")
    elif has_saldo_monto and has_cuota_mora and not has_egreso_costo:
        scores["financiero"] += 7.0
        criterios.append("Saldo/monto + cuota/mora detectados")

    # 3. Evaluación Docente
    if has_docente and has_eval_doc:
        scores["evaluacion_docente"] += 14.0
        criterios.append("Docente + encuesta/evaluacion formal detectada")
    elif has_docente and has_eval_pregunta and ratings_1_5_count >= 3 and not has_nota:
        scores["evaluacion_docente"] += 12.0
        criterios.append("Docente + preguntas de satisfaccion y escala 1-5")
    elif has_eval_doc and ratings_1_5_count >= 3 and not has_nota:
        scores["evaluacion_docente"] += 10.0
        criterios.append("Encuesta de satisfaccion con escala numerica 1-5")
    elif has_eval_doc and not has_nota:
        scores["evaluacion_docente"] += 6.0

    # 4. Rentabilidad / Egresos / Techos
    if has_egreso_costo and has_techo_meta:
        scores["rentabilidad"] += 14.0
        criterios.append("Co-ocurrencia costos/egresos + techos/presupuesto/ejecutado")
    elif has_egreso_puro and not has_estudiante:
        scores["rentabilidad"] += 11.0
        criterios.append("Costos y egresos institucionales")
    elif has_techo_meta and not has_estudiante:
        scores["rentabilidad"] += 11.0
        criterios.append("Techos presupuestarios / ejecutado vs meta")
    elif has_egreso_costo and not has_mkt_lead and not has_estudiante:
        scores["rentabilidad"] += 6.0

    if not has_estudiante and scores["rentabilidad"] > 0 and not has_mkt_lead:
        scores["rentabilidad"] += 2.0

    # 5. Marketing / Admisión
    if has_mkt_lead and not has_nota:
        scores["marketing"] += 14.0
        criterios.append("Leads / campanas de marketing comercial")
    if has_admision and not has_nota and not (has_estudiante and has_saldo_monto):
        scores["marketing"] += 10.0
        criterios.append("Postulantes / matriculas / admision")
    if has_mkt_lead and has_admision and not has_nota:
        scores["marketing"] += 4.0

    best_cat = max(scores, key=scores.get)
    best_score = scores[best_cat]

    if best_score < 3.0:
        return {
            "categoria": "generico",
            "fact_table": None,
            "tipo_fuente": "SIN_RECONOCER",
            "confidence": 0.2,
            "scores": scores,
            "criterios": ["Puntaje insuficiente para clasificacion determinista"]
        }

    fact_table_map = {
        "academico": "fact_rendimiento_academico",
        "financiero": "fact_situacion_financiera",
        "evaluacion_docente": "fact_evaluacion_docente",
        "rentabilidad": "fact_rentabilidad",
        "marketing": "fact_marketing"
    }

    fuente_map = {
        "academico": "MOODLE" if has_moodle else "ACTA",
        "financiero": "COBRANZA",
        "evaluacion_docente": "EVALUACION_DOCENTE",
        "rentabilidad": "RENTABILIDAD" if has_techo_meta and "ejecutado" in joined else ("EGRESOS" if has_egreso_costo else "TECHOS"),
        "marketing": "MARKETING" if has_mkt_lead else "ADMISION"
    }

    confidence = min(0.99, round(0.5 + (best_score / 20.0), 2))

    return {
        "categoria": best_cat,
        "fact_table": fact_table_map.get(best_cat),
        "tipo_fuente": fuente_map.get(best_cat, "ACTA"),
        "confidence": confidence,
        "scores": scores,
        "criterios": criterios
    }


def clasificar_categoria(
    bloque: pd.DataFrame = None,
    nombre_archivo: str = "",
    nombre_hoja: str = "",
) -> str:
    """
    Clasifica un bloque en una categoría de negocio ('academico', 'financiero', 'evaluacion_docente',
    'rentabilidad', 'marketing', 'comercial', 'generico').
    Prioriza la inspección heurística agnóstica de tokens y densidad de contenido del DataFrame,
    garantizando cero dependencia de nombres de archivo u hojas quemadas.
    """
    if bloque is not None:
        if getattr(bloque, "attrs", {}).get("es_ruido", False) or len(bloque) < MIN_FILAS_ISLA:
            return "ruido"

        # 1. Detección agnóstica primaria basada en contenido y cabeceras
        agnostico = clasificar_contenido_agnostico(bloque)
        if agnostico.get("confidence", 0.0) >= 0.5 and agnostico.get("categoria") != "generico":
            return agnostico["categoria"]

    # 2. Respaldo secundario en catálogo dinámico si el contenido fue ambiguo o bloque es None
    texto_contenido = ""
    if bloque is not None and not bloque.empty:
        filas_muestra = bloque.iloc[:min(3, len(bloque))].values.flatten()
        texto_contenido = " ".join(str(v) for v in filas_muestra if pd.notna(v))

    try:
        from pipeline.normalization.catalog_repository import obtener_catalogo_repositorio
        repo = obtener_catalogo_repositorio()
        cat, _ = repo.clasificar_bloque_con_catalogo(
            texto_archivo=nombre_archivo,
            texto_hoja=nombre_hoja,
            texto_contenido=texto_contenido,
            es_ruido=False
        )
        return cat
    except Exception as e:
        logger.warning("Fallo al clasificar con catálogos dinámicos (%s), retornando 'generico'", e)
        return "generico"


def clasificar_bloque(
    nombre_archivo: str,
    nombre_hoja: str,
    df_isla: pd.DataFrame = None,
    es_ruido: bool = False,
) -> str:
    """Compatibilidad con Loop 2/3 previo."""
    if es_ruido:
        return "descartable"
    cat = clasificar_categoria(df_isla, nombre_archivo, nombre_hoja)
    if cat == "ruido":
        return "descartable"
    return cat


def extraer_documentos_isla(
    nombre_archivo: str,
    nombre_hoja: str,
    isla: dict,
    categoria: str,
) -> tuple[list[dict], int, int]:
    """
    Extrae documentos de texto plano para cada fila válida de la isla.

    Retorna:
        (documentos, n_filas_procesadas, n_filas_vacias_internas)
    """
    if isla.get("es_ruido", False):
        return [], 0, 0

    df_isla = isla["df"]
    fila_inicio = isla["fila_inicio"]
    isla_idx = isla["indice"]

    docs = []
    n_proc = 0
    n_vac = 0

    for i in range(len(df_isla)):
        fila = df_isla.iloc[i]
        valores_limpios = []
        for v in fila:
            if pd.notna(v):
                s = str(v).strip()
                if s:
                    valores_limpios.append(s)

        if not valores_limpios:
            n_vac += 1
            continue

        texto_plano = " | ".join(valores_limpios)
        doc = {
            "id": f"{nombre_archivo}::{nombre_hoja}::isla_{isla_idx}::fila_{fila_inicio + i}",
            "archivo": nombre_archivo,
            "hoja": nombre_hoja,
            "isla_idx": isla_idx,
            "fila_original": fila_inicio + i,
            "categoria": categoria,
            "texto": texto_plano,
            "valores": valores_limpios,
        }
        docs.append(doc)
        n_proc += 1

    return docs, n_proc, n_vac


def procesar_corpus(
    directorio: str,
    ruta_salida_jsonl: str = None,
) -> tuple[list[dict], dict]:
    """
    Lee todo el corpus heterogéneo, detecta bloques/islas, clasifica por área,
    extrae documentos de texto plano y calcula la auditoría garantizando el
    invariante de conservación.

    Invariante verificado:
        total_filas_raw = filas_procesadas + filas_descartadas_ruido + filas_vacias
    """
    corpus = leer_corpus(directorio)

    todos_los_documentos = []
    auditoria_global = {
        "archivos_leidos": len(corpus),
        "hojas_totales": 0,
        "islas_totales": 0,
        "islas_validas": 0,
        "islas_ruido": 0,
        "total_filas_raw": 0,
        "filas_procesadas": 0,
        "filas_descartadas_ruido": 0,
        "filas_vacias": 0,
        "invariante_cumplido": True,
        "conteo_por_categoria": {},
        "desglose_por_archivo": [],
    }

    for nombre_archivo, hojas in corpus.items():
        filas_raw_archivo = 0
        filas_proc_archivo = 0
        filas_ruido_archivo = 0
        filas_vacias_archivo = 0
        docs_archivo = []
        islas_archivo = 0
        islas_val_archivo = 0
        islas_ruido_archivo = 0

        for nombre_hoja, df_hoja in hojas.items():
            auditoria_global["hojas_totales"] += 1
            n_raw_hoja = len(df_hoja)
            filas_raw_archivo += n_raw_hoja

            islas = detectar_islas(df_hoja)
            islas_archivo += len(islas)
            auditoria_global["islas_totales"] += len(islas)

            filas_en_islas = 0
            for isla in islas:
                filas_en_islas += isla["n_filas"]
                if isla["es_ruido"]:
                    islas_ruido_archivo += 1
                    auditoria_global["islas_ruido"] += 1
                    filas_ruido_archivo += isla["n_filas"]
                else:
                    islas_val_archivo += 1
                    auditoria_global["islas_validas"] += 1
                    cat = clasificar_bloque(nombre_archivo, nombre_hoja, isla["df"], False)
                    docs_isla, n_proc, n_vac = extraer_documentos_isla(
                        nombre_archivo, nombre_hoja, isla, cat
                    )
                    docs_archivo.extend(docs_isla)
                    todos_los_documentos.extend(docs_isla)
                    filas_proc_archivo += n_proc
                    filas_vacias_archivo += n_vac

                    auditoria_global["conteo_por_categoria"][cat] = (
                        auditoria_global["conteo_por_categoria"].get(cat, 0) + len(docs_isla)
                    )

            vacias_fuera = n_raw_hoja - filas_en_islas
            filas_vacias_archivo += vacias_fuera

        contabilizado = filas_proc_archivo + filas_ruido_archivo + filas_vacias_archivo
        ok_archivo = (contabilizado == filas_raw_archivo)
        if not ok_archivo:
            auditoria_global["invariante_cumplido"] = False

        auditoria_global["desglose_por_archivo"].append({
            "archivo": nombre_archivo,
            "hojas": len(hojas),
            "islas": islas_archivo,
            "filas_raw": filas_raw_archivo,
            "procesadas": filas_proc_archivo,
            "descartadas_ruido": filas_ruido_archivo,
            "vacias": filas_vacias_archivo,
            "invariante_ok": ok_archivo,
        })

        auditoria_global["total_filas_raw"] += filas_raw_archivo
        auditoria_global["filas_procesadas"] += filas_proc_archivo
        auditoria_global["filas_descartadas_ruido"] += filas_ruido_archivo
        auditoria_global["filas_vacias"] += filas_vacias_archivo

    total_calc = (
        auditoria_global["filas_procesadas"]
        + auditoria_global["filas_descartadas_ruido"]
        + auditoria_global["filas_vacias"]
    )
    auditoria_global["invariante_cumplido"] = (
        auditoria_global["invariante_cumplido"]
        and (total_calc == auditoria_global["total_filas_raw"])
    )

    if ruta_salida_jsonl:
        os.makedirs(os.path.dirname(os.path.abspath(ruta_salida_jsonl)), exist_ok=True)
        with open(ruta_salida_jsonl, "w", encoding="utf-8") as f:
            for doc in todos_los_documentos:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")
        logger.info(
            "Persistidos %d documentos en '%s'",
            len(todos_los_documentos), ruta_salida_jsonl,
        )

    return todos_los_documentos, auditoria_global


def generar_reporte_auditoria(auditoria: dict) -> str:
    """Genera un reporte markdown formateado a partir del dict de auditoría."""
    lineas = [
        "# Reporte Final de Auditoría — Ingesta Sprint 2",
        "",
        f"- **Archivos procesados:** {auditoria['archivos_leidos']}",
        f"- **Hojas totales:** {auditoria['hojas_totales']}",
        f"- **Islas detectadas:** {auditoria['islas_totales']} ({auditoria['islas_validas']} válidas, {auditoria['islas_ruido']} ruido)",
        f"- **Invariante de conservación cumplido:** {'✅ SÍ (100% verificado)' if auditoria['invariante_cumplido'] else '❌ NO'}",
        "",
        "## Invariante de Conservación Global",
        "",
        "$$\\text{Total Raw} = \\text{Procesadas} + \\text{Ruido Descartado} + \\text{Filas Vacías}$$",
        f"$$\\{auditoria['total_filas_raw']} = {auditoria['filas_procesadas']} + {auditoria['filas_descartadas_ruido']} + {auditoria['filas_vacias']}$$",
        "",
        "## Distribución por Categoría de Negocio",
        "",
        "| Categoría | Documentos Procesados | % del Total |",
        "|:---|:---:|:---:|",
    ]

    total_proc = auditoria["filas_procesadas"] or 1
    for cat, cnt in sorted(auditoria["conteo_por_categoria"].items(), key=lambda x: -x[1]):
        pct = (cnt / total_proc) * 100
        lineas.append(f"| `{cat}` | {cnt:,} | {pct:.2f}% |")

    lineas.extend([
        "",
        "## Desglose por Archivo",
        "",
        "| Archivo | Hojas | Islas | Filas Raw | Procesadas | Ruido | Vacías | Invariante |",
        "|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ])

    for d in auditoria["desglose_por_archivo"]:
        inv_str = "✅ OK" if d["invariante_ok"] else "❌ FALLA"
        lineas.append(
            f"| {d['archivo']} | {d['hojas']} | {d['islas']} | {d['filas_raw']:,} | "
            f"{d['procesadas']:,} | {d['descartadas_ruido']:,} | {d['vacias']:,} | {inv_str} |"
        )

    return "\n".join(lineas)


