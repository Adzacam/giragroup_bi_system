"""
backend/services/planificacion_extractor.py
-------------------------------------------
Extracción estructural de libros PLANIFICACION (Diseño B, V-3).
Reconoce hojas por sus encabezados y contenido (fórmulas vs constantes), no por
el nombre de la hoja (salvo la marca de borrador).
"""

import re
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.utils import get_column_letter

from services.extraccion_por_encabezado import MESES, _a_float, normalizar_encabezado, parsear_fecha

try:
    from pipeline.lector_hojas import dato_sensible
except ImportError:  # contenedor con pipeline/ en sys.path
    from lector_hojas import dato_sensible

_RE_MES_ANIO_HOJA = re.compile(
    r"^\s*([A-Z]+)\s*[-_\s]\s*(20\d{2})\s*$",
    re.IGNORECASE,
)
_VALORES_VACIOS_PLANTILLA = {"", "NONE", "NAN", "NULL", "FALSE", "TRUE", "0", "0.0"}


def _norm(texto: Any) -> str:
    if texto is None:
        return ""
    s = "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn")
    return " ".join(s.upper().split())


def es_hoja_borrador(nombre_hoja: str) -> bool:
    n = _norm(nombre_hoja)
    return "BORRADOR" in n or "BOOR" in n


def anio_mes_de_hoja(nombre_hoja: str) -> Tuple[Optional[int], Optional[int]]:
    n = _norm(nombre_hoja)
    m = _RE_MES_ANIO_HOJA.match(n)
    if not m:
        return None, None
    mes = MESES.get(m.group(1))
    anio = int(m.group(2))
    return (anio, mes) if mes else (None, None)


def _es_hoja_informe_gestion(rows_vals: List[Tuple[Any, ...]]) -> bool:
    for row in rows_vals[:15]:
        joined = " | ".join(_norm(c) for c in row if c is not None)
        if "META (PROGRAMAS REGULARES Y TECHOS" in joined or "INGRESO PROYECTADO TECHOS" in joined:
            return True
    return False


def _extraer_informe_gestion(rows_vals: List[Tuple[Any, ...]], nombre_hoja: str) -> List[Dict[str, Any]]:
    metas: List[Dict[str, Any]] = []
    col_mes = None
    col_techos = None
    col_meta_total = None
    col_okr_total_meta = None
    gestion_actual: Optional[int] = None

    for r_idx, row in enumerate(rows_vals, start=1):
        # Detectar cambio de bloque anual ('GESTIÓN 2025', 'GESTIÓN 2026', etc.)
        for c_val in row:
            n = _norm(c_val)
            m_g = re.search(r"GESTION\s+(20\d{2})", n)
            if m_g:
                gestion_actual = int(m_g.group(1))

        # Detectar fila de encabezados de tabla
        row_norm = [_norm(c) for c in row]
        if "MES" in row_norm and any("META (PROGRAMAS REGULARES" in x for x in row_norm):
            col_mes = row_norm.index("MES")
            col_techos = next((i for i, x in enumerate(row_norm) if "INGRESO PROYECTADO TECHOS" in x), None)
            col_meta_total = next((i for i, x in enumerate(row_norm) if "META (PROGRAMAS REGULARES" in x), None)
            # La última columna 'META' de la derecha corresponde a TOTAL PROGRAMAS (OKR)
            metas_cols = [i for i, x in enumerate(row_norm) if x == "META"]
            col_okr_total_meta = metas_cols[-1] if metas_cols else None
            continue

        if col_mes is None or gestion_actual is None:
            continue

        mes_raw = _norm(row[col_mes] if col_mes < len(row) else None)
        mes_num = MESES.get(mes_raw)
        if not mes_num:
            continue

        if col_meta_total is not None and col_meta_total < len(row):
            val_g = _a_float(str(row[col_meta_total])) if row[col_meta_total] is not None else None
            if val_g is not None:
                metas.append({
                    "categoria": "PLAN_INGRESO_TOTAL",
                    "gestion": gestion_actual,
                    "mes": mes_num,
                    "monto_meta": round(val_g, 2),
                    "tipo_programa": None,
                    "celda_origen": f"{nombre_hoja}!{get_column_letter(col_meta_total + 1)}{r_idx}",
                })

        if col_techos is not None and col_techos < len(row):
            val_e = _a_float(str(row[col_techos])) if row[col_techos] is not None else None
            if val_e is not None and val_e > 0:
                metas.append({
                    "categoria": "PLAN_INGRESO_TECHOS_PROYECTADO",
                    "gestion": gestion_actual,
                    "mes": mes_num,
                    "monto_meta": round(val_e, 2),
                    "tipo_programa": None,
                    "celda_origen": f"{nombre_hoja}!{get_column_letter(col_techos + 1)}{r_idx}",
                })

        if col_okr_total_meta is not None and col_okr_total_meta < len(row):
            val_x = _a_float(str(row[col_okr_total_meta])) if row[col_okr_total_meta] is not None else None
            if val_x is not None and val_x > 0:
                metas.append({
                    "categoria": "OKR_APERTURAS",
                    "gestion": gestion_actual,
                    "mes": mes_num,
                    "monto_meta": round(val_x, 2),
                    "tipo_programa": "TOTAL",
                    "celda_origen": f"{nombre_hoja}!{get_column_letter(col_okr_total_meta + 1)}{r_idx}",
                })

    return metas


def _campo_canonico(cabecera: str) -> Optional[str]:
    """FU-L3: campo canónico de una cabecera según los sinónimos del catálogo (pos, programa, leads…), o None."""
    from services.captacion_canonica import campo_de_cabecera
    res = campo_de_cabecera(cabecera) if cabecera and cabecera.strip() else None
    return res[0] if res else None


def _es_col_programa(h_norm: str) -> bool:
    return (h_norm in ("PROGRAMA", "NOMBRE DEL PROGRAMA", "NOMBRE PROGRAMA") or h_norm.startswith("PROGRAMA ")
            or _campo_canonico(h_norm) == "programa")


def _es_col_pos(h_norm: str) -> bool:
    return h_norm == "POS" or _campo_canonico(h_norm) == "pos"


def _detectar_cabecera_planificacion(rows_vals: List[Tuple[Any, ...]]) -> Optional[Tuple[int, List[str]]]:
    for r_idx, row in enumerate(rows_vals[:15], start=1):
        norm_cells = [_norm(c) for c in row]
        tiene_prog = any(_es_col_programa(c) for c in norm_cells)
        tiene_ctrl = any(
            c in ("POS", "TIPO DE PROGRAMA", "ESTADO", "ESTADO DEL PROGRAMA", "COSTO PROGRAMA", "FECHA INICIO")
            or _campo_canonico(c) in ("pos", "leads_captacion", "inscritos_captacion")
            for c in norm_cells
        )
        if tiene_prog and tiene_ctrl:
            headers = []
            for idx, c in enumerate(row, start=1):
                txt = " ".join(str(c).splitlines()).strip() if c is not None else ""
                # FU-L1: una cabecera con PII (p. ej. un correo personal en A1) no se copia a cada línea
                headers.append(txt if txt and not dato_sensible(txt) else f"col_{idx}")
            return r_idx, headers
    return None


def _es_hoja_derivada_por_formulas(ws_form, header_row_idx: int, headers: List[str]) -> bool:
    norm_headers = [_norm(h) for h in headers]
    cols_clave = [
        i for i, h in enumerate(norm_headers)
        if _es_col_programa(h) or _es_col_pos(h) or h in ("ESTADO", "ESTADO DEL PROGRAMA")
    ]
    if not cols_clave:
        return True
    no_vacios = 0
    formulas = 0
    for row in ws_form.iter_rows(min_row=header_row_idx + 1, max_row=header_row_idx + 35, values_only=True):
        for idx in cols_clave:
            if idx < len(row) and row[idx] is not None:
                s = str(row[idx]).strip()
                if s:
                    no_vacios += 1
                    if s.startswith("="):
                        formulas += 1
    return no_vacios > 0 and (formulas / no_vacios) >= 0.60


def _pos_valido(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    if _norm(s) in _VALORES_VACIOS_PLANTILLA:
        return None
    m = re.match(r"^(?:POS[\s-]?)?(\d{3,5})(?:\.0+)?$", s, re.IGNORECASE)
    if m:
        return f"POS-{m.group(1)}"
    return s[:80] if "POS" in s.upper() else None


def _programa_valido(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    n = _norm(s)
    if n in _VALORES_VACIOS_PLANTILLA or n.startswith(("TOTAL", "SUBTOTAL")):
        return None
    return s


def _serializar_valor(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, date):
        return val.isoformat()
    s = " ".join(str(val).splitlines()).strip()
    if not s or s.lower() == "nan":
        return None
    return s


def extraer_libro_planificacion(ruta_xlsx: str, hojas_excluidas: Optional[set] = None) -> Dict[str, Any]:
    """
    Extrae de un libro PLANIFICACION:
    - `metas`: filas del informe de gestión (detectado por contenido) para `dim_meta`
    - `filas`: filas útiles de hojas fuente para `fact_planificacion_programa`
    - `hojas_resumen`: conteo y clasificación por hoja
    `hojas_excluidas` (FU-L1b): hojas que el clasificador genérico ignora (pipeline/lector_hojas.py). La ingesta
    las pasa para que clasificador y extractor tomen una sola decisión por hoja.
    """
    wb_vals = openpyxl.load_workbook(ruta_xlsx, read_only=True, data_only=True)
    wb_form = openpyxl.load_workbook(ruta_xlsx, read_only=True, data_only=False)
    try:
        metas: List[Dict[str, Any]] = []
        filas: List[Dict[str, Any]] = []
        hojas_resumen: List[Dict[str, Any]] = []

        for nombre_hoja in wb_vals.sheetnames:
            if hojas_excluidas and nombre_hoja in hojas_excluidas:
                hojas_resumen.append({"hoja": nombre_hoja, "tipo": "ignorada_por_clasificador", "filas": 0})
                continue
            if es_hoja_borrador(nombre_hoja):
                hojas_resumen.append({"hoja": nombre_hoja, "tipo": "borrador", "filas": 0})
                continue

            ws_v = wb_vals[nombre_hoja]
            ws_f = wb_form[nombre_hoja]
            primeras = list(ws_v.iter_rows(min_row=1, max_row=45, values_only=True))

            if _es_hoja_informe_gestion(primeras):
                metas_hoja = _extraer_informe_gestion(primeras, nombre_hoja)
                metas.extend(metas_hoja)
                hojas_resumen.append({"hoja": nombre_hoja, "tipo": "informe_gestion", "filas": len(metas_hoja)})
                continue

            cab = _detectar_cabecera_planificacion(primeras)
            if not cab:
                hojas_resumen.append({"hoja": nombre_hoja, "tipo": "derivada_sin_cabecera", "filas": 0})
                continue

            header_row_idx, headers = cab
            if _es_hoja_derivada_por_formulas(ws_f, header_row_idx, headers):
                hojas_resumen.append({"hoja": nombre_hoja, "tipo": "derivada_formulas", "filas": 0})
                continue

            anio_hoja, mes_hoja = anio_mes_de_hoja(nombre_hoja)
            norm_headers = [_norm(h) for h in headers]
            idx_prog = next((i for i, h in enumerate(norm_headers) if _es_col_programa(h)), None)
            idx_pos = next((i for i, h in enumerate(norm_headers) if _es_col_pos(h)), None)

            count_hoja = 0
            for r_idx, row in enumerate(ws_v.iter_rows(min_row=header_row_idx + 1, values_only=True), start=header_row_idx + 1):
                prog_val = _programa_valido(row[idx_prog] if idx_prog is not None and idx_prog < len(row) else None)
                pos_val = _pos_valido(row[idx_pos] if idx_pos is not None and idx_pos < len(row) else None)
                if not prog_val and not pos_val:
                    continue

                pares = []
                campos_raw: Dict[str, str] = {}
                for col_i, h in enumerate(headers):
                    if col_i >= len(row):
                        continue
                    v_str = _serializar_valor(row[col_i])
                    if v_str is not None:
                        pares.append(f"{h}: {v_str}")
                        campos_raw.setdefault(normalizar_encabezado(h), v_str)

                if not pares:
                    continue

                filas.append({
                    "hoja": nombre_hoja,
                    "fila_excel": r_idx,
                    "anio_hoja": anio_hoja,
                    "mes_hoja": mes_hoja,
                    "texto_linea": " | ".join(pares),
                    "campos": campos_raw,
                })
                count_hoja += 1

            hojas_resumen.append({"hoja": nombre_hoja, "tipo": "dato_fuente", "filas": count_hoja})

        return {"metas": metas, "filas": filas, "hojas_resumen": hojas_resumen}
    finally:
        wb_vals.close()
        wb_form.close()
