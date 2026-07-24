"""
document_builder.py — GIRA-40 (Sprint 2)
Construye el contrato estandarizado de "Documento Mínimo" para cada
fila de texto libre extraída de encuestas.

Cada documento contiene:
- Texto plano limpio
- Metadatos de fuente (archivo, hoja, fila original)
- Pregunta canónica (del diccionario canónico)
- Llaves de relación resueltas (POS, CI, DOCENTE, etc.)
- Estado de validación (ok, sin_llave_valida, vacio_descartado)
- ID idempotente (SHA-256 de archivo+hoja+fila+pregunta+texto)
"""

import re
import hashlib
import logging
import unicodedata
from typing import Optional

import pandas as pd

from pipeline.normalization.text_cleaner import (
    limpiar_texto_para_ner,
    es_respuesta_vacia,
)
from pipeline.normalization.entity_enricher import EntityEnricher

logger = logging.getLogger(__name__)


def _normalizar_clave(valor) -> str:
    """Normaliza un valor para usarlo como clave."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return str(valor).strip()


def _generar_id_documento(
    archivo: str, hoja: str, fila: int, pregunta: str, texto: str
) -> str:
    """
    Genera un hash SHA-256 idempotente sobre la combinación determinista:
    archivo + hoja + fila_original + pregunta_canonica + texto_plano.
    
    Esto garantiza que re-ingestar el mismo archivo produce el mismo ID,
    permitiendo upserts en lugar de inserts duplicados.
    """
    contenido = f"{archivo}|{hoja}|{fila}|{pregunta}|{texto}"
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def construir_documentos_minimos(
    hoja_info: dict,
    enricher: Optional[EntityEnricher] = None,
) -> list[dict]:
    """
    Genera los Documentos Mínimos a partir de una hoja clasificada
    como texto_libre por el dispatcher.

    Args:
        hoja_info: Dict de una hoja del dispatcher con claves:
            - nombre_hoja: str
            - data: pd.DataFrame
            - columnas_texto_libre: list[str]
            - mapeo_columnas: dict {col_original: campo_canonico}
            - nombre_archivo (inyectado por el caller)
        enricher: Instancia de EntityEnricher para resolver DOCENTE.

    Returns:
        Lista de Documentos Mínimos:
        [
            {
                "id_documento": str (SHA-256),
                "texto_plano": str,
                "fuente": {"archivo": str, "hoja": str},
                "fila_original": int,
                "pregunta_canonica": str,
                "llaves_relacion": {
                    "POS": str|"",
                    "CI": str|"",
                    "NOMBRE_PROGRAMA": str|"",
                    "DOCENTE": str|"",
                    "MODULO": str|"",
                    "FECHA": str|"",
                },
                "es_respuesta_vacia": bool,
                "estado": "ok" | "sin_llave_valida" | "vacio_descartado",
            }
        ]
    """
    df = hoja_info.get("data")
    if df is None or df.empty:
        return []

    nombre_archivo = hoja_info.get("nombre_archivo", "desconocido")
    nombre_hoja = hoja_info.get("nombre_hoja", "Hoja1")
    columnas_texto = hoja_info.get("columnas_texto_libre", [])
    mapeo = hoja_info.get("mapeo_columnas", {})

    if not columnas_texto:
        logger.warning(
            "Hoja '%s' marcada como texto_libre pero sin columnas "
            "de texto libre detectadas.",
            nombre_hoja,
        )
        return []

    # Invertir mapeo: canónico → columna original
    inv_mapeo = {}
    for col_orig, campo_can in mapeo.items():
        if campo_can:
            inv_mapeo.setdefault(campo_can, col_orig)

    documentos = []

    for idx, row in df.iterrows():
        # Extraer llaves de relación disponibles
        llaves = _extraer_llaves_relacion(row, inv_mapeo, enricher, mapeo)

        # Procesar cada columna de texto libre
        for col_texto in columnas_texto:
            if col_texto not in df.columns:
                continue

            valor_raw = row.get(col_texto)
            if valor_raw is None:
                continue

            texto_str = str(valor_raw)

            # Limpieza NER completa
            texto_limpio = limpiar_texto_para_ner(texto_str)

            # Determinar pregunta canónica
            pregunta_canonica = mapeo.get(col_texto, col_texto)
            if pregunta_canonica is None:
                pregunta_canonica = col_texto

            # Verificar si es respuesta vacía
            vacia = es_respuesta_vacia(texto_limpio)

            # Determinar estado
            if vacia:
                estado = "vacio_descartado"
            elif not llaves["POS"]:
                estado = "sin_llave_valida"
            else:
                estado = "ok"

            # Generar ID idempotente
            id_doc = _generar_id_documento(
                nombre_archivo, nombre_hoja,
                int(idx) if not isinstance(idx, int) else idx,
                pregunta_canonica, texto_limpio,
            )

            doc = {
                "id_documento": id_doc,
                "texto_plano": texto_limpio,
                "fuente": {
                    "archivo": nombre_archivo,
                    "hoja": nombre_hoja,
                },
                "fila_original": int(idx) if not isinstance(idx, int) else idx,
                "pregunta_canonica": pregunta_canonica,
                "llaves_relacion": llaves,
                "es_respuesta_vacia": vacia,
                "estado": estado,
            }

            documentos.append(doc)

    # Estadísticas
    n_ok = sum(1 for d in documentos if d["estado"] == "ok")
    n_sin_llave = sum(1 for d in documentos if d["estado"] == "sin_llave_valida")
    n_vacios = sum(1 for d in documentos if d["estado"] == "vacio_descartado")

    logger.info(
        "DocumentBuilder: hoja '%s' → %d docs (%d ok, %d sin_llave, %d vacíos)",
        nombre_hoja, len(documentos), n_ok, n_sin_llave, n_vacios,
    )

    return documentos


# Etiquetas canónicas de metadatos/relación que NUNCA deben enviarse como texto libre a BETO
_CAMPOS_NO_TEXTO_LIBRE = {
    "grupo", "pos", "identificador_persona", "correo_persona",
    "nombre_persona", "nombre_programa", "fecha_evento", "nota_likert",
    "modulo", "modulo_acta_1", "modulo_acta_2", "modulo_acta_3",
    "modulo_acta_4", "modulo_acta_5", "modulo_acta_6", "modulo_acta_7",
    "modulo_acta_8", "modulo_acta_9", "docente"
}

_PATRON_CI_STRICT = re.compile(r"^\d{7,9}$")
_PATRON_EMAIL = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$")


def _validar_formato_ci(valor: str) -> str:
    """Valida que un valor tenga formato real de CI (7-9 dígitos) o Email."""
    if not valor:
        return ""
    v = str(valor).strip()
    if _PATRON_CI_STRICT.match(v) or _PATRON_EMAIL.match(v):
        return v
    return ""


def _validar_modulo(valor: str) -> str:
    """Valida que un valor de módulo sea un número de módulo plausible (1-20) o texto de materia."""
    if not valor:
        return ""
    v = str(valor).strip()
    if v.isdigit():
        num = int(v)
        if num > 20:  # Artefacto: probablemente un ID o código de estado (ej: 78)
            return ""
    return v


def extraer_codigo_pos(valor: str) -> str:
    """
    Extrae únicamente el código de programa POS-XXX (2-4 caracteres) de un string.
    Recorta sufijos compuestos como POS-033-5160091 -> POS-033.
    """
    if not valor:
        return ""
    v_str = str(valor).strip()
    match = re.search(r"\b(POS-[a-zA-Z0-9]{2,4})\b", v_str, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return ""


def construir_documentos_minimos(
    hoja_info: dict,
    enricher: Optional[EntityEnricher] = None,
) -> list[dict]:
    """
    Genera los Documentos Mínimos a partir de una hoja clasificada
    como texto_libre por el dispatcher.
    """
    df = hoja_info.get("data")
    if df is None or df.empty:
        return []

    nombre_archivo = hoja_info.get("nombre_archivo", "desconocido")
    nombre_hoja = hoja_info.get("nombre_hoja", "Hoja1")
    columnas_texto = hoja_info.get("columnas_texto_libre", [])
    mapeo = hoja_info.get("mapeo_columnas", {})

    if not columnas_texto:
        logger.warning(
            "Hoja '%s' marcada como texto_libre pero sin columnas "
            "de texto libre detectadas.",
            nombre_hoja,
        )
        return []

    # Invertir mapeo: canónico → columna original
    inv_mapeo = {}
    for col_orig, campo_can in mapeo.items():
        if campo_can:
            inv_mapeo.setdefault(campo_can, col_orig)

    documentos = []

    for idx, row in df.iterrows():
        # Extraer llaves de relación disponibles
        llaves = _extraer_llaves_relacion(row, inv_mapeo, enricher, mapeo)

        # Procesar cada columna de texto libre
        for col_texto in columnas_texto:
            if col_texto not in df.columns:
                continue

            pregunta_canonica = mapeo.get(col_texto, col_texto) or col_texto

            # REGLA: Si la pregunta canónica es una etiqueta administrativa/metadata, NO enviar a BETO
            if pregunta_canonica.lower() in _CAMPOS_NO_TEXTO_LIBRE:
                continue

            valor_raw = row.get(col_texto)
            if valor_raw is None:
                continue

            texto_str = str(valor_raw)

            # Limpieza NER completa
            texto_limpio = limpiar_texto_para_ner(texto_str)

            # Verificar si es respuesta vacía
            vacia = es_respuesta_vacia(texto_limpio)

            # Determinar estado
            if vacia:
                estado = "vacio_descartado"
            elif not llaves["POS"]:
                estado = "sin_llave_valida"
            else:
                estado = "ok"

            # Generar ID idempotente
            id_doc = _generar_id_documento(
                nombre_archivo, nombre_hoja,
                int(idx) if not isinstance(idx, int) else idx,
                pregunta_canonica, texto_limpio,
            )

            doc = {
                "id_documento": id_doc,
                "texto_plano": texto_limpio,
                "fuente": {
                    "archivo": nombre_archivo,
                    "hoja": nombre_hoja,
                },
                "fila_original": int(idx) if not isinstance(idx, int) else idx,
                "pregunta_canonica": pregunta_canonica,
                "llaves_relacion": llaves,
                "es_respuesta_vacia": vacia,
                "estado": estado,
            }

            documentos.append(doc)

    # Estadísticas
    n_ok = sum(1 for d in documentos if d["estado"] == "ok")
    n_sin_llave = sum(1 for d in documentos if d["estado"] == "sin_llave_valida")
    n_vacios = sum(1 for d in documentos if d["estado"] == "vacio_descartado")

    logger.info(
        "DocumentBuilder: hoja '%s' → %d docs (%d ok, %d sin_llave, %d vacíos)",
        nombre_hoja, len(documentos), n_ok, n_sin_llave, n_vacios,
    )

    return documentos


def _extraer_llaves_relacion(
    row: pd.Series,
    inv_mapeo: dict,
    enricher: Optional[EntityEnricher],
    mapeo: dict,
) -> dict:
    """
    Extrae las llaves de relación con guardián de asignación única por columna
    y validación estricta de formato CI / POS.
    """
    llaves = {
        "POS": "",
        "CI": "",
        "NOMBRE_PROGRAMA": "",
        "DOCENTE": "",
        "MODULO": "",
        "FECHA": "",
    }

    # Registro de columna original usada para cada campo relacional
    col_usada = {}

    # 1. POS
    pos_raw, col_pos_orig = _buscar_valor_con_columna(row, inv_mapeo, "pos")
    llaves["POS"] = extraer_codigo_pos(pos_raw)
    if llaves["POS"] and col_pos_orig:
        col_usada["POS"] = col_pos_orig

    # 2. CI (exige validación estricta de 7-9 dígitos o email)
    ci_raw, col_ci_orig = _buscar_valor_con_columna(row, inv_mapeo, "identificador_persona")
    llaves["CI"] = _validar_formato_ci(ci_raw)
    if llaves["CI"] and col_ci_orig:
        col_usada["CI"] = col_ci_orig

    # 3. NOMBRE_PROGRAMA
    prog_raw, col_prog_orig = _buscar_valor_con_columna(row, inv_mapeo, "nombre_programa")
    llaves["NOMBRE_PROGRAMA"] = prog_raw
    if llaves["NOMBRE_PROGRAMA"] and col_prog_orig:
        col_usada["NOMBRE_PROGRAMA"] = col_prog_orig

    # 4. MÓDULO
    mod_raw, col_mod_orig = _buscar_valor_con_columna(row, inv_mapeo, "modulo")
    llaves["MODULO"] = _validar_modulo(mod_raw)

    # 5. FECHA
    fecha_raw, _ = _buscar_valor_con_columna(row, inv_mapeo, "fecha_evento")
    llaves["FECHA"] = fecha_raw

    # 6. GUARDIÁN DE ASIGNACIÓN ÚNICA DE COLUMNA:
    # Si la misma columna original (ej: "N°") alimentó múltiples llaves (ej: CI, NOMBRE_PROGRAMA),
    # revertir la asignación colisionada para evitar datos corruptos.
    inverso_cols = {}
    for campo, col_orig in col_usada.items():
        if col_orig in inverso_cols:
            # Colisión detectada
            inverso_cols[col_orig].append(campo)
        else:
            inverso_cols[col_orig] = [campo]

    for col_orig, campos_colisionados in inverso_cols.items():
        if len(campos_colisionados) > 1:
            logger.warning(
                "Guardián de Asignación Única: columna '%s' colisionó en %s. Limpiando llaves.",
                col_orig, campos_colisionados,
            )
            for c in campos_colisionados:
                llaves[c] = ""

    # 7. DOCENTE: En encuestas NUNCA se mapea desde columna directa. Se puebla SOLO vía enricher.
    if enricher and enricher.cargado:
        docente_resuelto = enricher.buscar_docente(llaves["POS"], llaves["MODULO"])
        if docente_resuelto:
            llaves["DOCENTE"] = docente_resuelto

        # Enriquecer NOMBRE_PROGRAMA si falta
        if not llaves["NOMBRE_PROGRAMA"]:
            programa_resuelto = enricher.buscar_programa(llaves["POS"])
            if programa_resuelto:
                llaves["NOMBRE_PROGRAMA"] = programa_resuelto

    return llaves


def _buscar_valor_con_columna(
    row: pd.Series,
    inv_mapeo: dict,
    campo_canonico: str,
) -> tuple[str, str]:
    """
    Busca el valor de un campo canónico y retorna (valor_str, nombre_columna_original).
    """
    # Intento 1: por mapeo canónico
    col_real = inv_mapeo.get(campo_canonico)
    if col_real and col_real in row.index:
        val = row.get(col_real)
        if val is not None and str(val).strip() and str(val).strip().lower() not in ("nan", "none", ""):
            return str(val).strip(), col_real

    # Intento 2: búsqueda directa por nombre parcial
    campo_norm = campo_canonico.lower().replace("_", "")
    for col in row.index:
        col_norm = str(col).lower().replace("_", "").replace(" ", "")
        col_norm = "".join(
            ch for ch in unicodedata.normalize("NFD", col_norm)
            if unicodedata.category(ch) != "Mn"
        )
        if len(col_norm) >= 3 and (campo_norm in col_norm or col_norm in campo_norm):
            val = row.get(col)
            if val is not None and str(val).strip() and str(val).strip().lower() not in ("nan", "none", ""):
                return str(val).strip(), str(col)

    return "", ""


def _buscar_valor(
    row: pd.Series,
    inv_mapeo: dict,
    campo_canonico: str,
) -> str:
    val, _ = _buscar_valor_con_columna(row, inv_mapeo, campo_canonico)
    return val

