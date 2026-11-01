"""
pipeline/normalization/asymmetric_flattener.py
----------------------------------------------
Motor de detección y aplanamiento de tablas asimétricas y heterogéneas.
Especializado en archivos institucionales reales (Moodle, Google Sheets de Actas
de Notas y Asistencia, Google Forms de Admisiones y Pagos):
- Descombinación y mapeo de celdas combinadas (openpyxl merged_cells, ej. A1:F2).
- Detección heurística de cabeceras desplazadas (fila real N).
- Fusión y aplanamiento de encabezados multinivel (jerárquicos).
- Descarte preventivo de filas de subtotales, promedios y pies de firma.
- Inferencia automática de rangos de fechas (multi-gestión 2024-2026+) sin requerir selector manual.
- Extracción de mini-grid para inspección visual y advertencias estructurales.
- Pre-etiquetado con chips canónicos del Catálogo Institucional (Cero PII).
"""

import io
import re
import csv
import logging
import unicodedata
from typing import Dict, Any, List, Optional, Tuple, Union
import pandas as pd

try:
    import openpyxl
    from openpyxl.utils import get_column_letter, range_boundaries
except ImportError:
    openpyxl = None

from pipeline.normalization.catalog_repository import obtener_catalogo_repositorio

logger = logging.getLogger(__name__)

# Palabras clave para detectar la fila de encabezado
CABECERA_KEYWORDS = [
    "nro", "n°", "#", "ci", "c.i.", "cedula", "identidad", "estudiante", "alumno",
    "nombre", "apellidos", "nombres", "modulo", "materia", "curso", "nota", "calificacion",
    "calif", "final", "asistencia", "fecha", "monto", "pago", "cuota", "saldo", "deuda",
    "email", "correo", "first name", "surname", "grade", "id number"
]

# Palabras clave para detectar filas de subtotal/resumen/firmas que deben descartarse
SUBTOTAL_KEYWORDS = [
    "promedio", "promedio general", "media del curso", "overall average", "total",
    "subtotal", "suma", "firma", "docente:", "director", "coordinador", "rector",
    "observaciones generales:", "v°b°", "aprobado por:"
]

# Patrones para reconocimiento de fechas y años
REGEX_YEARS = re.compile(r"\b(202[0-9])\b")
REGEX_DATE_DMY = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](202[0-9])\b")
REGEX_DATE_YMD = re.compile(r"\b(202[0-9])[/-](\d{1,2})[/-](\d{1,2})\b")
REGEX_GESTION_RANGE = re.compile(r"\b(202[0-9])\s*[-–/]\s*(202[0-9])\b")


class AsymmetricFlattener:
    """
    Inspector y normalizador de tablas con estructuras no homogéneas,
    cabeceras flotantes, celdas fusionadas y metadatos integrados.
    """

    @classmethod
    def sanitizar_texto_institucion(cls, texto: str) -> str:
        """Sanitiza menciones de instituciones antiguas unificando a GiraGroup Posgrado."""
        if not texto:
            return ""
        pattern = re.compile(
            r"\b(universidad\s+franz\s+tamayo|unifranz|universidad\s+bolivariana|bolivariana|bm\s+group)\b",
            re.IGNORECASE
        )
        return pattern.sub("GiraGroup Posgrado", texto)

    @classmethod
    def extraer_fechas_texto(cls, texto: str) -> List[str]:
        """Extrae años y fechas encontradas en una cadena de texto."""
        if not texto:
            return []
        fechas = []
        for m in REGEX_GESTION_RANGE.finditer(texto):
            fechas.append(f"{m.group(1)}–{m.group(2)}")
        for m in REGEX_DATE_DMY.finditer(texto):
            fechas.append(f"{m.group(1)}/{m.group(2)}/{m.group(3)}")
        for m in REGEX_DATE_YMD.finditer(texto):
            fechas.append(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
        for m in REGEX_YEARS.finditer(texto):
            fechas.append(m.group(1))
        return list(dict.fromkeys(fechas))

    @classmethod
    def calcular_rango_fechas(cls, lista_fechas: List[str]) -> str:
        """Determina la representación compacta del rango temporal detectado."""
        anios = []
        for item in lista_fechas:
            for y in REGEX_YEARS.findall(item):
                anios.append(int(y))
        if anios:
            min_y = min(anios)
            max_y = max(anios)
            if min_y == max_y:
                return f"{min_y} (Auto)"
            return f"{min_y}–{max_y} (Auto)"
        return "Auto (Sin fecha explícita)"

    @classmethod
    def clasificar_origen_documental(
        cls,
        filename: str,
        hojas_data: Optional[Dict[str, Any]] = None,
        primera_linea: str = ""
    ) -> str:
        """
        Clasifica el origen en uno de los 4 tipos del wireframe oficial:
        - MOODLE_EXPORT
        - GSHEETS_ACTA_NOTAS
        - GSHEETS_ACTA_ASIST
        - GFORMS_ADM_PAGOS
        """
        f_lower = (filename or "").lower()
        texto_global = f_lower + " " + (primera_linea or "").lower()
        if hojas_data:
            for h_nom, h_val in hojas_data.items():
                texto_global += f" {h_nom.lower()} {str(h_val)[:400].lower()}"

        # 1. Moodle
        if any(k in texto_global for k in ["moodle", "first name", "surname", "last downloaded", "calificaciones del curso"]):
            return "MOODLE_EXPORT"

        # 2. Google Forms Admisiones / Pagos
        if any(k in texto_global for k in ["form", "formulario", "admision", "postulante", "marca temporal", "timestamp", "recibo", "pago", "cuota"]):
            return "GFORMS_ADM_PAGOS"

        # 3. Google Sheets Asistencia
        if any(k in texto_global for k in ["asist", "asistencia", "falta", "retraso", "asistencias", "presente"]):
            return "GSHEETS_ACTA_ASIST"

        # 4. Google Sheets Acta de Notas / Calificaciones
        if any(k in texto_global for k in ["acta", "nota", "calific", "evaluac", "parcial", "final", "ponderado"]):
            return "GSHEETS_ACTA_NOTAS"

        # Por defecto según extensión o contexto
        if f_lower.endswith(".csv"):
            return "GFORMS_ADM_PAGOS"
        return "GSHEETS_ACTA_NOTAS"

    @classmethod
    def procesar_archivo_asimetrico(
        cls,
        file_bytes: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Analiza un archivo completo (.xlsx o .csv) extrayendo:
        - Diagnóstico estructural completo (celdas combinadas, cabecera desplazada, warnings, mini-grid)
        - DataFrames limpios y aplanados
        - Fechas y rangos inferidos
        - Chips pre-etiquetados con el Catálogo Institucional
        """
        ext = filename.split(".")[-1].lower() if "." in filename else "xlsx"
        if ext in ("xlsx", "xls") and openpyxl:
            return cls._procesar_excel_asimetrico(file_bytes, filename)
        else:
            return cls._procesar_csv_asimetrico(file_bytes, filename)

    @classmethod
    def _procesar_excel_asimetrico(
        cls,
        file_bytes: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Procesa libro Excel inspeccionando celdas combinadas y cabeceras asimétricas."""
        celdas_combinadas = []
        metadatos_cabecera = []
        fechas_detectadas_set = set()
        advertencias = []
        mini_grid = []
        fila_cabecera_idx = 1
        multinivel_aplanados = 0
        subtotales_descartados = 0
        columnas_dinamicas = []

        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            sheet_names = wb.sheetnames
            ws = wb.active or wb[sheet_names[0]]

            # Si la hoja activa está vacía o es una carátula (<= 1 fila) y existen otras hojas, buscar la hoja con más datos
            if (not ws or (ws.max_row or 0) <= 1) and len(sheet_names) > 1:
                mejor_hoja = ws
                max_filas_detectadas = ws.max_row or 0
                for s_name in sheet_names:
                    cand_ws = wb[s_name]
                    c_rows = cand_ws.max_row or 0
                    if c_rows > max_filas_detectadas:
                        max_filas_detectadas = c_rows
                        mejor_hoja = cand_ws
                ws = mejor_hoja

            # 1. Extraer celdas combinadas (Merged Cells)
            for rng in list(ws.merged_cells.ranges):
                coord = str(rng)
                min_col, min_row, max_col, max_row = range_boundaries(coord)
                top_left_val = ws.cell(row=min_row, column=min_col).value
                val_str = str(top_left_val).strip() if top_left_val is not None else ""
                val_str = cls.sanitizar_texto_institucion(val_str)
                
                celda_info = {
                    "rango": coord,
                    "valor": val_str,
                    "fila_inicio": min_row,
                    "fila_fin": max_row,
                    "col_inicio": min_col,
                    "col_fin": max_col
                }
                celdas_combinadas.append(celda_info)
                if val_str:
                    metadatos_cabecera.append(val_str)
                    for f in cls.extraer_fechas_texto(val_str):
                        fechas_detectadas_set.add(f)

            # 2. Descombinar celdas en memoria rellenando valores (forward-fill visual)
            max_r = min(ws.max_row or 1, 500)
            max_c = min(ws.max_column or 1, 30)

            # Construir matriz cruda
            raw_matrix = []
            for r in range(1, max_r + 1):
                row_vals = []
                for c in range(1, max_c + 1):
                    val = ws.cell(row=r, column=c).value
                    row_vals.append("" if val is None else str(val).strip())
                raw_matrix.append(row_vals)

            # Rellenar valores de celdas combinadas en la matriz cruda de forma defensiva
            for m in celdas_combinadas:
                if m.get("valor"):
                    start_r = max(0, m["fila_inicio"] - 1)
                    end_r = min(m["fila_fin"], len(raw_matrix))
                    for r in range(start_r, end_r):
                        start_c = max(0, m["col_inicio"] - 1)
                        end_c = min(m["col_fin"], len(raw_matrix[r]))
                        for c in range(start_c, end_c):
                            if not raw_matrix[r][c]:
                                raw_matrix[r][c] = m["valor"]

            # 3. Detectar fila de cabecera desplazada (inspeccionar primeras 12 filas)
            mejor_score = 0
            for r_idx in range(min(12, len(raw_matrix))):
                fila_txt = [c.lower() for c in raw_matrix[r_idx] if c]
                score = sum(1 for c in fila_txt if any(kw in c for kw in CABECERA_KEYWORDS))
                if score > mejor_score:
                    mejor_score = score
                    fila_cabecera_idx = r_idx + 1

            if fila_cabecera_idx > 1:
                advertencias.append(f"Cabecera desplazada detectada en fila {fila_cabecera_idx}")

            # 4. Detectar encabezados multinivel (inspeccionar hasta 3 filas superiores)
            cabecera_final = []
            hdr_row = raw_matrix[fila_cabecera_idx - 1] if fila_cabecera_idx <= len(raw_matrix) else []
            preceding_rows = [raw_matrix[pr] for pr in range(max(0, fila_cabecera_idx - 4), fila_cabecera_idx - 1)]

            for c_idx, col_name in enumerate(hdr_row):
                nombre_limpio = cls.sanitizar_texto_institucion(col_name.strip())
                partes_multinivel = []
                if preceding_rows:
                    for p_row in preceding_rows:
                        if c_idx < len(p_row):
                            cat_sup = cls.sanitizar_texto_institucion(p_row[c_idx].strip())
                            if cat_sup and cat_sup not in partes_multinivel and cat_sup != nombre_limpio and not cat_sup.isdigit() and len(cat_sup) > 2:
                                if len(cat_sup) < 70 and not any(k in cat_sup.lower() for k in ["maestría", "diplomado", "universidad"]):
                                    partes_multinivel.append(cat_sup)

                if partes_multinivel:
                    multinivel_aplanados += 1
                    prefijo = " - ".join(partes_multinivel)
                    nombre_limpio = f"{prefijo} - {nombre_limpio}" if nombre_limpio else prefijo

                nombre_limpio = cls.sanitizar_texto_institucion(nombre_limpio)
                if not nombre_limpio:
                    nombre_limpio = f"Columna_{c_idx + 1}"
                cabecera_final.append(nombre_limpio)
                columnas_dinamicas.append(nombre_limpio)

                # Buscar fechas en los nombres de columna
                for f in cls.extraer_fechas_texto(nombre_limpio):
                    fechas_detectadas_set.add(f)

            if multinivel_aplanados > 0:
                advertencias.append(f"{multinivel_aplanados} encabezados multinivel fusionados y aplanados")

            # 5. Filtrar filas de datos y descartar subtotales/firmas
            filas_datos = []
            for r_idx in range(fila_cabecera_idx, len(raw_matrix)):
                fila = raw_matrix[r_idx]
                # Verificar si está completamente vacía
                if not any(c for c in fila):
                    continue
                # Verificar si es fila de subtotal o firma
                fila_str_lower = " ".join([c.lower() for c in fila if c])
                es_subtotal = any(skw in fila_str_lower for skw in SUBTOTAL_KEYWORDS)
                if es_subtotal:
                    subtotales_descartados += 1
                    continue

                filas_datos.append(fila[:len(cabecera_final)])
                # Buscar fechas en celdas de datos
                for val in fila:
                    if val:
                        for f in cls.extraer_fechas_texto(val):
                            fechas_detectadas_set.add(f)

            if subtotales_descartados > 0:
                advertencias.append(f"{subtotales_descartados} filas de subtotales/promedios/firmas descartadas preventivamente")

            if celdas_combinadas:
                advertencias.append(f"{len(celdas_combinadas)} celdas combinadas detectadas y rescatadas para metadatos")

            # 6. Construir Mini-Grid para el inspector visual de la Sección C (primeras 6 filas x 6 cols)
            for r in range(min(6, len(raw_matrix))):
                fila_grid = []
                for c in range(min(6, len(raw_matrix[r]))):
                    coord = f"{get_column_letter(c + 1)}{r + 1}"
                    # Identificar si pertenece a un rango combinado
                    rango_comb = next(
                        (m["rango"] for m in celdas_combinadas if m["fila_inicio"] <= r + 1 <= m["fila_fin"] and m["col_inicio"] <= c + 1 <= m["col_fin"]),
                        None
                    )
                    valor_celda = raw_matrix[r][c]
                    es_hdr = (r + 1 == fila_cabecera_idx)
                    fila_grid.append({
                        "coord": coord,
                        "valor": valor_celda[:35] + ("..." if len(valor_celda) > 35 else ""),
                        "es_combinada": bool(rango_comb),
                        "rango": rango_comb,
                        "es_cabecera": es_hdr
                    })
                mini_grid.append(fila_grid)

        except Exception as e_proc:
            logger.warning("Error procesando estructura Excel asimétrica: %s", e_proc)
            advertencias.append(f"Aviso estructural: Procesado con lector estándar ({e_proc})")

        # 7. Pre-etiquetar chips con Catálogo Institucional
        texto_para_catalogo = f"{filename} {' '.join(metadatos_cabecera)} {' '.join(columnas_dinamicas)}"
        chips = cls._resolver_chips_catalogo(texto_para_catalogo, fechas_detectadas_set)

        fechas_lista = sorted(list(fechas_detectadas_set))
        rango_fechas = cls.calcular_rango_fechas(fechas_lista)
        chips["fecha_detectada"] = rango_fechas

        origen_detectado = cls.clasificar_origen_documental(filename, None, " ".join(metadatos_cabecera))

        diagnostico = {
            "celdas_combinadas": celdas_combinadas,
            "fila_cabecera_desplazada": fila_cabecera_idx,
            "fila_cabecera": fila_cabecera_idx,
            "encabezados_multinivel_aplanados": multinivel_aplanados,
            "filas_subtotales_descartadas": subtotales_descartados,
            "advertencias_estructurales": advertencias,
            "columnas_dinamicas": columnas_dinamicas[:15],
            "fechas_reconocidas": fechas_lista,
            "rango_fechas": rango_fechas,
            "origen_detectado": origen_detectado,
            "mini_grid": mini_grid
        }

        return {
            "diagnostico_estructural": diagnostico,
            "chips_catalogo": chips,
            "origen_detectado": origen_detectado,
            "fechas_reconocidas": fechas_lista,
            "rango_fechas": rango_fechas
        }

    @classmethod
    def _procesar_csv_asimetrico(
        cls,
        file_bytes: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Procesa archivo CSV detectando encabezados desplazados y metadatos preliminares."""
        fechas_detectadas_set = set()
        advertencias = []
        mini_grid = []
        fila_cabecera_idx = 1
        subtotales_descartados = 0
        columnas_dinamicas = []

        try:
            texto = file_bytes.decode("utf-8", errors="replace")
        except Exception:
            texto = file_bytes.decode("latin-1", errors="replace")

        lineas_crudas = texto.splitlines()
        
        # Detectar delimitador buscando la frecuencia acumulada en las primeras 10 líneas
        sep = ","
        candidatos = [";", ",", "\t", "|"]
        conteos = {c: 0 for c in candidatos}
        for l in lineas_crudas[:10]:
            for c in candidatos:
                conteos[c] += l.count(c)
        mejor_sep = max(conteos.items(), key=lambda x: x[1])
        if mejor_sep[1] > 0:
            sep = mejor_sep[0]

        raw_matrix = []
        for l in lineas_crudas[:100]:
            if not l.strip():
                raw_matrix.append([])
                continue
            try:
                reader = csv.reader([l], delimiter=sep)
                row = next(reader)
                raw_matrix.append([str(c).strip() for c in row])
            except Exception:
                raw_matrix.append([str(c).strip() for c in l.split(sep)])

        # Detectar cabecera desplazada
        mejor_score = 0
        for r_idx in range(min(15, len(raw_matrix))):
            fila_txt = [c.lower() for c in raw_matrix[r_idx] if c]
            score = sum(1 for c in fila_txt if any(kw in c for kw in CABECERA_KEYWORDS))
            if score > mejor_score:
                mejor_score = score
                fila_cabecera_idx = r_idx + 1

        if fila_cabecera_idx > 1:
            advertencias.append(f"Cabecera desplazada detectada en fila {fila_cabecera_idx} (preámbulo omitido)")

        hdr_row = raw_matrix[fila_cabecera_idx - 1] if fila_cabecera_idx <= len(raw_matrix) else []
        columnas_dinamicas = [col if col else f"Col_{i+1}" for i, col in enumerate(hdr_row)]

        # Buscar fechas en todo el CSV
        for f in cls.extraer_fechas_texto(texto[:5000]):
            fechas_detectadas_set.add(f)

        # Construir mini grid (primeras 6 filas x 6 columnas)
        for r in range(min(6, len(raw_matrix))):
            fila_grid = []
            for c in range(min(6, len(raw_matrix[r]))):
                coord = f"C{c+1}:R{r+1}"
                val = raw_matrix[r][c]
                fila_grid.append({
                    "coord": coord,
                    "valor": val[:35] + ("..." if len(val) > 35 else ""),
                    "es_combinada": False,
                    "rango": None,
                    "es_cabecera": (r + 1 == fila_cabecera_idx)
                })
            mini_grid.append(fila_grid)

        texto_para_catalogo = f"{filename} {' '.join(columnas_dinamicas)} {texto[:1000]}"
        chips = cls._resolver_chips_catalogo(texto_para_catalogo, fechas_detectadas_set)

        fechas_lista = sorted(list(fechas_detectadas_set))
        rango_fechas = cls.calcular_rango_fechas(fechas_lista)
        chips["fecha_detectada"] = rango_fechas

        origen_detectado = cls.clasificar_origen_documental(filename, None, lineas_crudas[0] if lineas_crudas else "")

        diagnostico = {
            "celdas_combinadas": [],
            "fila_cabecera_desplazada": fila_cabecera_idx,
            "fila_cabecera": fila_cabecera_idx,
            "encabezados_multinivel_aplanados": 0,
            "filas_subtotales_descartadas": subtotales_descartados,
            "advertencias_estructurales": advertencias,
            "columnas_dinamicas": columnas_dinamicas[:15],
            "fechas_reconocidas": fechas_lista,
            "rango_fechas": rango_fechas,
            "origen_detectado": origen_detectado,
            "mini_grid": mini_grid
        }

        return {
            "diagnostico_estructural": diagnostico,
            "chips_catalogo": chips,
            "origen_detectado": origen_detectado,
            "fechas_reconocidas": fechas_lista,
            "rango_fechas": rango_fechas
        }

    @classmethod
    def _normalizar_texto_busqueda(cls, txt: str) -> str:
        """Remueve acentos y pasa a mayúsculas para matching tolerante."""
        if not txt:
            return ""
        norm = unicodedata.normalize("NFD", str(txt))
        return "".join(c for c in norm if unicodedata.category(c) != "Mn").upper()

    @classmethod
    def _resolver_chips_catalogo(
        cls,
        texto_busqueda: str,
        fechas_set: set
    ) -> Dict[str, str]:
        """
        Resuelve los 4 chips semánticos contra el Catálogo Institucional Estático Oficial:
        - PROGRAMA_CAT (ej. 'Maestría en BI (POS-5308)')
        - MODULO_CAT (ej. 'Minería de Datos (M-02)')
        - PRECIO_BASE_CAT (ej. '14,500 Bs')
        - FECHA_DETECTADA (ej. '2024–2026 (Auto)')
        """
        import unicodedata
        repo = obtener_catalogo_repositorio()
        resumen = repo.obtener_resumen_institucional()
        programas = resumen.get("programas", [])

        # Buscar mejor programa coincidente con tolerancia a acentos
        t_clean = cls._normalizar_texto_busqueda(texto_busqueda)
        prog_match = None
        for p in programas:
            if p["pos_code"].upper() in t_clean:
                prog_match = p
                break
            # Coincidencia por subcadena
            nom_clean = cls._normalizar_texto_busqueda(p["nombre"])
            palabras = [w for w in nom_clean.split() if len(w) > 4 and w not in ("DIPLOMADO", "MAESTRIA", "PROGRAMA", "EXPERTO", "CURSO")]
            if sum(1 for w in palabras if w in t_clean) >= 2:
                prog_match = p
                break

        # Fallback al primer programa activo si no hay match directo (ej. Maestría en BI)
        if not prog_match:
            prog_match = programas[0] if programas else {
                "pos_code": "POS-5308",
                "nombre": "Maestría en Business Intelligence y Big Data",
                "arancel_base_bs": 14500.0,
                "modulos_clave": ["Minería de Datos", "Arquitectura de Datos"]
            }

        pos_code = prog_match.get("pos_code", "POS-5308")
        nombre_corto = prog_match.get("nombre", "").split(" y ")[0]
        if len(nombre_corto) > 30:
            nombre_corto = nombre_corto[:28] + "..."
        prog_chip = f"{nombre_corto} ({pos_code})"

        # Módulo curricular
        mod_chip = "Módulo General (M-01)"
        modulos_cand = prog_match.get("modulos_clave", [])
        for m in modulos_cand:
            if cls._normalizar_texto_busqueda(m) in t_clean:
                mod_chip = f"{m} (M-02)"
                break
        if mod_chip == "Módulo General (M-01)" and modulos_cand:
            mod_chip = f"{modulos_cand[0]} (M-02)"

        # Precio base
        arancel = prog_match.get("arancel_base_bs", 14500.0)
        precio_chip = f"{arancel:,.0f} Bs".replace(",", ".")

        return {
            "programa_cat": prog_chip,
            "modulo_cat": mod_chip,
            "precio_base_cat": precio_chip,
            "fecha_detectada": cls.calcular_rango_fechas(sorted(list(fechas_set)))
        }
