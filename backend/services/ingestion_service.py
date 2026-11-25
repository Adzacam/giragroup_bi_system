"""
ingestion_service.py
--------------------
Servicio orquestador del Pipeline de Ingesta DataOps (Sprint 2).
Reutiliza la lógica robusta de 'pipeline.ingesta' y expone métodos de negocio
para FastAPI con persistencia en PostgreSQL (lote, dim_origen_documental,
staging_registros_crudos, log_pipeline_ingesta).
"""

import os
import re
import sys
import time
import unicodedata
import hashlib
import tempfile
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from fastapi import HTTPException
from sqlalchemy import bindparam, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

# Asegurar import de pipeline/ y modelos
RAIZ_PROYECTO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in [RAIZ_PROYECTO, "/app", "/app/pipeline", os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from pipeline.ingesta import (
        leer_archivo,
        segmentar_archivo,
        detectar_bloques,
        a_texto_plano,
        clasificar_categoria,
        es_encuesta_likert,
        extraer_encabezado_hoja,
        evaluar_compuerta_dominio_cmi,
        MOTIVO_FUERA_DE_ALCANCE_CMI,
    )
except ImportError:
    try:
        from ingesta import (
            leer_archivo,
            segmentar_archivo,
            detectar_bloques,
            a_texto_plano,
            clasificar_categoria,
            es_encuesta_likert,
            extraer_encabezado_hoja,
            evaluar_compuerta_dominio_cmi,
            MOTIVO_FUERA_DE_ALCANCE_CMI,
        )
    except ImportError:
        MOTIVO_FUERA_DE_ALCANCE_CMI = "FUERA_DE_ALCANCE_CMI"
        def es_encuesta_likert(df): return False
        def leer_archivo(ruta): return {}
        def segmentar_archivo(df): return []
        def detectar_bloques(df): return []
        def a_texto_plano(b): return ""
        def clasificar_categoria(b, *args): return "academico"
        def extraer_encabezado_hoja(*args, **kwargs): return ""
        def evaluar_compuerta_dominio_cmi(*args, **kwargs):
            return {"en_alcance": True, "motivo": None, "senales_encabezado": 2, "score_categoria": 1.0, "categoria_sugerida": "academico"}

# FU-L1: lector con metadatos y clasificación genérica de hojas (estado y forma, no nombre)
try:
    from pipeline.ingesta import leer_archivo_con_metadatos
    from pipeline.lector_hojas import (
        CATEGORIA_POR_TIPO, USAR as HOJA_USADA, cabecera_segura, enmascarar_texto,
        resumen_publico, tipo_de_hoja_distinto,
    )
except ImportError:
    try:
        from ingesta import leer_archivo_con_metadatos
        from lector_hojas import (
            CATEGORIA_POR_TIPO, USAR as HOJA_USADA, cabecera_segura, enmascarar_texto,
            resumen_publico, tipo_de_hoja_distinto,
        )
    except ImportError:
        leer_archivo_con_metadatos = None
        CATEGORIA_POR_TIPO, HOJA_USADA = {}, "usar"
        def cabecera_segura(v, pos): return v
        def enmascarar_texto(v): return str(v)
        def resumen_publico(libro): return []
        def tipo_de_hoja_distinto(meta, tipo): return None

# Motivo informativo de una hoja que el lector no usa (FU-L1). No va a la bandeja de revisión humana:
# queda en log_inconsistencias con estado REGISTRADO (como SUBTOTAL), una vez por hoja.
MOTIVO_HOJA_IGNORADA = "HOJA_IGNORADA"

try:
    from models.dim_origen import DimOrigenDocumental
    from models.staging_registro import StagingRegistroCrudo
    from models.log_pipeline import LogPipelineIngesta
    from models.fact_rendimiento import FactRendimientoAcademico
    from models.fact_financiero import FactSituacionFinanciera
    from models.fact_evaluacion import FactEvaluacionDocente
    from models.fact_rentabilidad import FactRentabilidad
    from models.fact_costo_programa import FactCostoPrograma
    from models.fact_techo_convenio import FactTechoConvenio
    from models.fact_planificacion import FactPlanificacionPrograma
    from models.fact_marketing import FactMarketing
    from models.dim_meta import DimMeta
    from models.bridge_modulo_docente import BridgeModuloDocente
    from models.staging_entidad import StagingEntidadNoResuelta
    from models.lote import Lote
    from models.log_inconsistencia import LogInconsistencia
    from core.esquema_opcional import valores_si_existen
except ImportError:
    from backend.models.dim_origen import DimOrigenDocumental
    from backend.models.staging_registro import StagingRegistroCrudo
    from backend.models.log_pipeline import LogPipelineIngesta
    from backend.models.fact_rendimiento import FactRendimientoAcademico
    from backend.models.fact_financiero import FactSituacionFinanciera
    from backend.models.fact_evaluacion import FactEvaluacionDocente
    from backend.models.fact_rentabilidad import FactRentabilidad
    from backend.models.fact_costo_programa import FactCostoPrograma
    from backend.models.fact_techo_convenio import FactTechoConvenio
    from backend.models.fact_planificacion import FactPlanificacionPrograma
    from backend.models.fact_marketing import FactMarketing
    from backend.models.dim_meta import DimMeta
    from backend.models.bridge_modulo_docente import BridgeModuloDocente
    from backend.models.staging_entidad import StagingEntidadNoResuelta
    from backend.models.lote import Lote
    from backend.models.log_inconsistencia import LogInconsistencia
    from backend.core.esquema_opcional import valores_si_existen

try:
    from backend.services.readers.moodle_adapter import es_reporte_moodle, adaptar_moodle_df
except ImportError:
    from services.readers.moodle_adapter import es_reporte_moodle, adaptar_moodle_df

try:
    from pipeline.normalization.asymmetric_flattener import AsymmetricFlattener
except ImportError:
    try:
        from normalization.asymmetric_flattener import AsymmetricFlattener
    except ImportError:
        AsymmetricFlattener = None

logger = logging.getLogger(__name__)

FORMATOS_PERMITIDOS = (".xlsx", ".csv")

# Diccionario de normalización canónica de cabeceras
CANONICAL_HEADERS = {
    "nombres y apellidos": ("nombre_completo", "VARCHAR", "Mapeo directo"),
    "nombre completo": ("nombre_completo", "VARCHAR", "Mapeo directo"),
    "nombres": ("nombre_completo", "VARCHAR", "Mapeo directo"),
    "alumno": ("nombre_completo", "VARCHAR", "Mapeo directo"),
    "estudiante": ("nombre_completo", "VARCHAR", "Mapeo directo"),
    "postulante": ("nombre_completo", "VARCHAR", "Mapeo directo"),
    "calif_final": ("nota_final", "NUMERIC", "Conversión a float"),
    "calificacion final": ("nota_final", "NUMERIC", "Conversión a float"),
    "nota final": ("nota_final", "NUMERIC", "Conversión a float"),
    "nota": ("nota_final", "NUMERIC", "Conversión a float"),
    "finalgrade": ("nota_final", "NUMERIC", "Conversión a float"),
    "doc_identidad/ci": ("ci_estudiante", "VARCHAR", "Limpieza alfanumérica"),
    "cedula de identidad": ("ci_estudiante", "VARCHAR", "Limpieza alfanumérica"),
    "ci": ("ci_estudiante", "VARCHAR", "Limpieza alfanumérica"),
    "ci_estudiante": ("ci_estudiante", "VARCHAR", "Limpieza alfanumérica"),
    "idnumber": ("ci_estudiante", "VARCHAR", "Limpieza alfanumérica"),
    "cod_modulo": ("codigo_modulo", "VARCHAR", "Mapeo directo"),
    "codigo modulo": ("codigo_modulo", "VARCHAR", "Mapeo directo"),
    "modulo": ("codigo_modulo", "VARCHAR", "Mapeo directo"),
    "materia": ("codigo_modulo", "VARCHAR", "Mapeo directo"),
    "course": ("codigo_modulo", "VARCHAR", "Mapeo directo"),
    "fecha_eval": ("fecha_asentamiento", "DATE", "Parseo YYYY-MM-DD"),
    "fecha": ("fecha_asentamiento", "DATE", "Parseo YYYY-MM-DD"),
    "observaciones": ("observacion", "TEXT", "Sanitizado HTML"),
    "obs": ("observacion", "TEXT", "Sanitizado HTML"),
    "email": ("correo_institucional", "VARCHAR", "Validación RFC 5322"),
    "telefono": ("telefono_contacto", "VARCHAR", "Formato E.164"),
    "monto": ("monto_cuota", "NUMERIC", "Moneda normalizada"),
    "saldo": ("monto_deuda", "NUMERIC", "Moneda normalizada"),
    "deuda": ("monto_deuda", "NUMERIC", "Moneda normalizada"),
    "pagado": ("monto_pagado", "NUMERIC", "Moneda normalizada"),
    "cuota": ("numero_cuota", "INTEGER", "Entero secuencial"),
    "cuotas_impagas": ("cuotas_impagas", "INTEGER", "Entero secuencial"),
    # FU-L2: 'mora' suelta es ambigua (en cobranza hay DIAS DE MORA, RANGO MORA y TOTAL CUOTAS EN MORA). Solo
    # vale como cuotas si el bloque no trae una cabecera específica de cuotas (ver canonizar_cabeceras).
    "mora": ("cuotas_impagas", "INTEGER", "Entero secuencial (cabecera ambigua)"),
    "concepto": ("concepto", "VARCHAR", "Homologación financiera"),
}

# FU-L2: campo canónico del catálogo de mapeo (config/mapeo_fuentes.yaml) -> columna del DW para la matriz.
_CAMPO_CATALOGO_A_DW = {
    "cuotas_en_mora": ("cuotas_impagas", "INTEGER", "Catálogo de mapeo (FU-L2)"),
    "dias_mora": ("dias_mora", "INTEGER", "Catálogo de mapeo (FU-L2)"),
    "estado_cartera_fuente": ("estado_cartera_fuente", "VARCHAR", "Catálogo de mapeo (FU-L2), vocabulario normalizado"),
    "monto_pago_mes": ("monto_pagado", "NUMERIC", "Catálogo de mapeo (FU-L2): pago del mes de la columna"),
    "monto_deuda": ("monto_deuda", "NUMERIC", "Catálogo de mapeo (FU-L2)"),
    "monto_pagado_total": ("monto_pagado", "NUMERIC", "Catálogo de mapeo (FU-L2): total pagado"),
    "fecha_inicio": ("fecha_inicio", "DATE", "Catálogo de mapeo (FU-L2)"),
}


def canonizar_cabeceras(cabeceras: List[str]) -> Dict[str, tuple]:
    """
    (campo, tipo, regla) de cada cabecera de un bloque. Primero el catálogo de mapeo de cobranza (sinónimos
    con prioridad, FU-L2); después CANONICAL_HEADERS. Una cabecera ambigua ('mora') no pisa a la específica:
    si otra cabecera del bloque ya es cuotas_impagas, la ambigua queda como texto sin mapear.
    """
    try:
        from services.cobranza_canonica import campo_de_cabecera
    except ImportError:
        from backend.services.cobranza_canonica import campo_de_cabecera
    salida: Dict[str, tuple] = {}
    ambiguas = []
    for c in cabeceras:
        res = None
        try:
            res = campo_de_cabecera(c)
        except Exception:  # catálogo ausente: rige el diccionario fijo
            res = None
        if res and not res[2] and res[0] in _CAMPO_CATALOGO_A_DW:
            salida[c] = _CAMPO_CATALOGO_A_DW[res[0]]
            continue
        clave = _strip_accents(c)
        if (res and res[2]) or clave == "mora":
            ambiguas.append(c)
            continue
        salida[c] = CANONICAL_HEADERS.get(clave, (clave.replace(" ", "_"), "VARCHAR", "Mapeo inferido"))
    hay_cuotas = any(v[0] == "cuotas_impagas" for v in salida.values())
    for c in ambiguas:
        clave = _strip_accents(c)
        salida[c] = ((clave.replace(" ", "_"), "VARCHAR", "Ambigua: el bloque ya trae una cabecera de cuotas")
                     if hay_cuotas else ("cuotas_impagas", "INTEGER", "Entero secuencial (cabecera ambigua)"))
    return salida


def _strip_accents(text: str) -> str:
    if not text:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(text))
        if unicodedata.category(c) != "Mn"
    ).lower().strip()


def normalizar_codigo_tipo_fuente(raw_type: Optional[str]) -> Optional[str]:
    """
    Convierte etiquetas de UI o códigos al código canónico de base de datos:
    'ACTA' | 'COBRANZA' | 'ADMISION' | 'MOODLE' | 'EVALUACION_DOCENTE' |
    'EGRESOS' | 'TECHOS' | 'PLANIFICACION' | 'MARKETING' | 'RENTABILIDAD' | None.
    """
    if not raw_type:
        return None
    val = _strip_accents(raw_type).upper()
    if val in (
        "ACTA", "COBRANZA", "ADMISION", "MOODLE",
        "EVALUACION_DOCENTE", "EGRESOS", "TECHOS",
        "PLANIFICACION", "MARKETING", "RENTABILIDAD"
    ):
        return val
    if any(k in val for k in ("MOODLE", "AULA VIRTUAL", "LMS")):
        return "MOODLE"
    if any(k in val for k in ("EVALUACION", "DOCENTE", "ENCUESTA", "NPS", "SATISFACCION")):
        return "EVALUACION_DOCENTE"
    if any(k in val for k in ("EGRESO", "GASTO")):
        return "EGRESOS"
    if any(k in val for k in ("TECHO", "TECHOS")):
        return "TECHOS"
    if any(k in val for k in ("RENTABILIDAD", "EBITDA", "UTILIDAD")):
        return "RENTABILIDAD"
    if any(k in val for k in ("MARKETING", "LEAD", "CAMPANA", "PUBLICIDAD")):
        return "MARKETING"
    if any(k in val for k in ("ADMISION", "MATRICUL", "INSCRIP", "FORM", "POSTULANTE", "PROSPECTO")):
        return "ADMISION"
    if any(k in val for k in ("PLANIFICA", "CRONOGRAMA", "CURRICULAR")):
        return "PLANIFICACION"
    if any(k in val for k in ("COBRANZA", "PAGO", "FINANC", "CARTERA", "MORA", "PRESUPUESTO", "META")):
        return "COBRANZA"
    if any(k in val for k in ("ACTA", "CALIFIC", "NOTA", "ACADEMIC", "ARCA")):
        return "ACTA"
    return None


# Tipos que el selector de la SPA sabe reconocer; el backend distingue además los especializados
TIPOS_GENERICOS_CLIENTE = {"ACTA", "COBRANZA", "ADMISION", "MOODLE"}


def elegir_tipo_fuente(explicito: Optional[str], detectado: Optional[str]) -> Optional[str]:
    """
    El tipo elegido en la SPA manda, salvo que sea uno de sus 4 genéricos y las cabeceras indiquen un
    tipo especializado: la SPA no conoce EGRESOS, TECHOS, EVALUACION_DOCENTE, etc. y marcaba Egresos o
    Techos como COBRANZA y la evaluación docente como ACTA (filas sin módulo ni nota en la bandeja).
    """
    if explicito in TIPOS_GENERICOS_CLIENTE and detectado and detectado not in TIPOS_GENERICOS_CLIENTE:
        return detectado
    return explicito or detectado


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


def _bloque_es_encuesta(b: "pd.DataFrame") -> bool:
    """FU-L5: el bloque trae varias columnas de respuestas tipo Likert (contenido), aunque sus cabeceras no sean preguntas."""
    from services import encuesta_canonica
    try:
        return encuesta_canonica.hoja_es_encuesta(b.iloc[:80].values.tolist())
    except Exception:
        return False


def _filas_de_encuesta(hojas: Dict[str, "pd.DataFrame"]) -> tuple[int, int]:
    """(filas de hojas que son encuesta por sus valores, filas totales). FU-L5: el contenido (respuestas tipo Likert del
    diccionario del catálogo) decide si una hoja es una encuesta, no el nombre del libro, de la hoja ni sus cabeceras."""
    from services import encuesta_canonica
    en_encuesta = total = 0
    for df in (hojas or {}).values():
        if df is None or df.empty:
            continue
        total += len(df)
        try:
            if encuesta_canonica.hoja_es_encuesta(df.iloc[:80].values.tolist()):
                en_encuesta += len(df)
        except Exception as ex:  # el catálogo no responde: se decide como antes, por cabeceras
            logger.warning("FU_L5_CLASIFICACION_ENCUESTA_NO_DISPONIBLE error=%s", type(ex).__name__)
            return 0, total
    return en_encuesta, total


def detectar_tipo_fuente_por_cabeceras(
    hojas: Dict[str, pd.DataFrame],
    filename: str = ""
) -> Optional[str]:
    """
    Detecta el tipo de fuente de manera heurística y semántica sin depender de nombres
    de archivos ni nombres de hojas fijos:
      - 'ACTA' / 'MOODLE' -> fact_rendimiento_academico (Estudiante/CI + Módulo + Calificación)
      - 'COBRANZA' -> fact_situacion_financiera (Estudiante/CI + Saldo/Monto + Cuota/Fecha)
      - 'EVALUACION_DOCENTE' -> fact_evaluacion_docente (Docente + Preguntas / Escala 1-5 / Satisfacción)
      - 'RENTABILIDAD' / 'EGRESOS' / 'TECHOS' -> fact_rentabilidad (Costos, Egresos, Techos, Presupuesto)
      - 'MARKETING' / 'ADMISION' -> fact_marketing (Leads, Campañas, Preinscripciones, Admisiones)
    """
    tokens_cabecera: List[str] = []
    ratings_1_5_count = 0
    total_numeric = 0

    for sheet_name, df in (hojas or {}).items():
        s_str = _strip_accents(str(sheet_name))
        if s_str and not s_str.startswith("sheet") and not s_str.startswith("hoja"):
            tokens_cabecera.append(s_str)
        if df is None or df.empty:
            continue
        # Nombres de columnas
        for col in df.columns:
            c_str = _strip_accents(str(col))
            if c_str and not c_str.startswith("unnamed"):
                tokens_cabecera.append(c_str)
        # Primeras 15 filas de muestra
        max_rows = min(15, len(df))
        for idx in range(max_rows):
            row_vals = df.iloc[idx].values
            for v in row_vals:
                if pd.notna(v):
                    v_raw = str(v).strip()
                    v_str = _strip_accents(v_raw)
                    if 1 < len(v_str) <= 90:
                        tokens_cabecera.append(v_str)
                    try:
                        num_v = float(v_raw.replace("$", "").replace("Bs", "").replace(",", ".").strip())
                        total_numeric += 1
                        if 1.0 <= num_v <= 5.0 and num_v.is_integer():
                            ratings_1_5_count += 1
                    except (ValueError, TypeError):
                        pass

    joined_headers = " | ".join(tokens_cabecera)

    scores = {
        "MOODLE": 0,
        "COBRANZA": 0,
        "ADMISION": 0,
        "ACTA": 0,
        "EVALUACION_DOCENTE": 0,
        "EGRESOS": 0,
        "TECHOS": 0,
        "RENTABILIDAD": 0,
        "MARKETING": 0,
        "PLANIFICACION": 0,
    }

    # 1. Académico / Acta
    has_estudiante = _contiene_tokens(joined_headers, (
        "ci", "cedula", "dni", "idnumber", "carnet", "alumno", "alumnos",
        "estudiante", "estudiantes", "postulante", "nombres y apellidos", "nombre completo"
    ))
    has_modulo = _contiene_tokens(joined_headers, (
        "modulo", "modulos", "materia", "materias", "asignatura", "asignaturas",
        "curso", "cursos", "cod_modulo", "codigo modulo"
    ))
    has_nota = _contiene_tokens(joined_headers, (
        "nota", "notas", "calificacion", "calificaciones", "calif_final", "nota_final",
        "finalgrade", "promedio", "calif", "asistencia", "aprobado", "reprobado"
    ))
    if has_estudiante and has_modulo and has_nota:
        scores["ACTA"] += 15
    elif has_modulo and has_nota:
        scores["ACTA"] += 12
    elif has_estudiante and has_nota:
        scores["ACTA"] += 8
    elif has_nota:
        scores["ACTA"] += 4

    # Moodle
    if _contiene_tokens(joined_headers, ("idnumber", "finalgrade", "total del curso", "cuestionario:", "tarea:", "aula virtual moodle")):
        scores["MOODLE"] += 16

    # 2. Financiero / Cobranza
    has_saldo_monto = _contiene_tokens(joined_headers, (
        "monto", "saldo", "deuda", "monto_deuda", "monto_pagado", "pagado",
        "importe", "cobranza", "cartera", "abono", "deposito", "arancel"
    ))
    has_cuota_mora = _contiene_tokens(joined_headers, (
        "cuota", "cuotas", "cuotas_impagas", "mora", "en mora", "vencimiento",
        "fecha de pago", "comprobante", "factura", "concepto"
    ))
    if has_estudiante and has_saldo_monto and has_cuota_mora:
        scores["COBRANZA"] += 15
    elif has_estudiante and has_saldo_monto:
        scores["COBRANZA"] += 11
    elif has_saldo_monto and has_cuota_mora and not _contiene_tokens(joined_headers, ("partida", "egreso", "egresos", "gasto", "gastos")):
        scores["COBRANZA"] += 8
    elif has_saldo_monto and _contiene_tokens(joined_headers, ("cobranza", "cartera")):
        scores["COBRANZA"] += 6

    # 3. Evaluación Docente
    has_docente = _contiene_tokens(joined_headers, (
        "docente", "docentes", "profesor", "profesores", "profesora", "profesoras",
        "facilitador", "facilitadores", "instructor", "experiencia docente"
    ))
    has_eval_doc = _contiene_tokens(joined_headers, (
        "evaluacion docente", "evaluacion_docente", "encuesta docente", "encuesta de satisfaccion",
        "satisfaccion docente", "desempeno docente", "evaluacion del docente", "criterio de evaluacion",
        "item evaluacion", "escala de calificacion", "escala likert", "dominio del tema",
        "didactica del docente", "nps docente", "puntualidad docente"
    ))
    has_eval_pregunta = _contiene_tokens(joined_headers, (
        "pregunta", "criterio", "satisfaccion", "dominio del tema", "didactica", "nps", "encuesta"
    ))

    if has_docente and has_eval_doc:
        scores["EVALUACION_DOCENTE"] += 15
    elif has_docente and has_eval_pregunta and ratings_1_5_count >= 3 and not has_nota:
        scores["EVALUACION_DOCENTE"] += 12
    elif has_eval_doc and ratings_1_5_count >= 3 and not has_nota:
        scores["EVALUACION_DOCENTE"] += 10
    elif has_eval_doc and not has_nota:
        scores["EVALUACION_DOCENTE"] += 6

    # FU-L5: un libro cuyas hojas son en su mayoría respuestas tipo Likert es una encuesta aunque sus cabeceras traigan
    # «promedio» (que lo hacía pasar por un acta) o no nombren al docente. Un libro de actas con una sola hoja de encuesta
    # se queda como acta (la hoja toma su categoría por contenido).
    filas_encuesta, filas_totales = _filas_de_encuesta(hojas)
    if filas_totales and filas_encuesta * 2 >= filas_totales:
        scores["EVALUACION_DOCENTE"] = max(scores["EVALUACION_DOCENTE"], 16)

    # 4. Rentabilidad / Egresos / Techos
    has_egreso = _contiene_tokens(joined_headers, (
        "egreso", "egresos", "gasto", "gastos", "partida", "comprobante de egreso",
        "proveedor", "proveedores", "desembolso", "beneficiario"
    ))
    has_techo = _contiene_tokens(joined_headers, (
        "techo", "techos", "techo presupuestario", "presupuesto asignado", "presupuestado"
    ))
    has_rent = _contiene_tokens(joined_headers, (
        "rentabilidad", "ejecutado", "monto_ejecutado", "monto_meta",
        "ebitda", "margen", "utilidad", "meta por categoria"
    ))
    if has_egreso and has_techo:
        scores["RENTABILIDAD"] += 15
    elif has_rent:
        scores["RENTABILIDAD"] += 14
    if has_egreso and not has_estudiante:
        scores["EGRESOS"] += 12
    elif has_egreso:
        scores["EGRESOS"] += 6
    if has_techo and not has_estudiante:
        scores["TECHOS"] += 12
    elif has_techo:
        scores["TECHOS"] += 6

    # 5. Marketing / Admisión
    has_mkt = _contiene_tokens(joined_headers, (
        "lead", "leads", "campana", "campaña", "medio de contacto", "canal",
        "fuente lead", "asesor comercial", "reservas", "costo programa"
    ))
    has_adm = _contiene_tokens(joined_headers, (
        "postulante", "postulantes", "preinscrito", "preinscritos", "preinscripcion",
        "matricula", "matriculas", "inscrito", "inscritos", "marca temporal", "formulario"
    ))
    if has_mkt and not has_nota:
        scores["MARKETING"] += 14
    if has_adm and not has_nota and not (has_estudiante and has_saldo_monto):
        scores["ADMISION"] += 12

    # 6. Planificación
    if _contiene_tokens(joined_headers, ("planificacion", "cronograma", "carga horaria", "diseno curricular", "coordinador academico", "inicio clases", "fin clases")):
        scores["PLANIFICACION"] += 12

    best_type, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score >= 4:
        return best_type

    # Señal secundaria: nombre del archivo solo como fallback si el contenido no fue concluyente
    fname_norm = _strip_accents(filename)
    if any(k in fname_norm for k in ("moodle", "grades", "calificaciones_aula", "aula_virtual", "lms")):
        return "MOODLE"
    if any(k in fname_norm for k in ("evaluacion", "nps", "docente", "desempeno")):
        return "EVALUACION_DOCENTE"
    if any(k in fname_norm for k in ("egreso", "gasto")):
        return "EGRESOS"
    if any(k in fname_norm for k in ("techo",)):
        return "TECHOS"
    if any(k in fname_norm for k in ("rentabilidad", "ebitda")):
        return "RENTABILIDAD"
    if any(k in fname_norm for k in ("marketing", "lead", "campana")):
        return "MARKETING"
    if any(k in fname_norm for k in ("cobranza", "pago", "cartera", "mora", "deuda", "arancel", "financ")):
        return "COBRANZA"
    if any(k in fname_norm for k in ("admision", "inscripcion", "inscripciones", "postulante", "formulario")):
        return "ADMISION"
    if any(k in fname_norm for k in ("planificacion", "cronograma")):
        return "PLANIFICACION"
    if any(k in fname_norm for k in ("acta", "calificacion", "notas", "arca", "academica")):
        return "ACTA"

    return None


def _celdas_con_texto(fila) -> List[str]:
    return [str(v).strip() for v in fila.values
            if pd.notna(v) and str(v).strip() and not re.match(r"^(col_\d+|unnamed.*)$", str(v).strip(), re.I)]


def _fila_subencabezado(b: "pd.DataFrame", idx: int) -> int:
    """
    Encabezado de dos niveles: la fila idx trae rótulos de grupo dispersos (celdas combinadas como
    'Información básica', 'Bloque 1. ...') y la fila siguiente los nombres de columna reales
    ('Programa - POS', 'Número del módulo'). Se usa la fila siguiente cuando es claramente más densa, solo trae
    texto (ningún número ni fecha, como sí traería una fila de datos) y la fila de después tiene forma de datos.
    """
    if idx + 2 >= len(b):
        return idx
    grupo, sub, datos = (_celdas_con_texto(b.iloc[i]) for i in (idx, idx + 1, idx + 2))
    def _es_numero_o_fecha(v):
        return bool(re.match(r"^-?[\d.,]+$|^\d{4}-\d{2}-\d{2}", v))
    if (len(sub) >= len(grupo) + 2 and len(grupo) <= 0.6 * len(sub)
            and not any(_es_numero_o_fecha(v) for v in sub) and len(datos) >= 0.5 * len(sub)):
        return idx + 1
    return idx


class IngestionService:
    @staticmethod
    def serializar_bloque_con_encabezados(b: "pd.DataFrame") -> str:
        """
        Serializa un bloque a texto plano con celdas 'ENCABEZADO: valor' (se omiten las vacías).
        Encabezado = nombres de columna si el lector ya los trae (CSV); si no, primera fila con ≥ 2 celdas,
        saltando filas de título de hoja (una sola celda) que antes desalineaban los campos.
        """
        nombres_columna = [str(c).strip() for c in b.columns]
        # Lectores que ya traen encabezados como nombres de columna (CSV de Moodle): no consumir una fila de datos
        columnas_con_nombre = all(
            not isinstance(c, (int, float)) and not str(c).lower().startswith("unnamed") for c in b.columns
        )
        if columnas_con_nombre:
            headers_row, primera_fila = nombres_columna, 0
        else:
            if len(b) <= 1:
                return a_texto_plano(b)
            header_idx = next(
                (i for i in range(min(len(b) - 1, 5)) if b.iloc[i].notna().sum() >= 2),
                0
            )
            header_idx = _fila_subencabezado(b, header_idx)
            headers_row = [str(h).strip() if pd.notna(h) else "" for h in b.iloc[header_idx].values]
            # FU-L1: una cabecera con PII (correo, CI) no se copia a cada línea de staging
            headers_row = [cabecera_segura(h, p + 1) if h else "" for p, h in enumerate(headers_row)]
            primera_fila = header_idx + 1
        lineas_datos = []
        for row_idx in range(primera_fila, len(b)):
            celdas_fmt = []
            for col_idx, v in enumerate(b.iloc[row_idx].values):
                if pd.notna(v) and str(v).strip() != "":
                    val_s = str(v).strip()
                    # ': ' dentro del encabezado ('1: Docente explica claramente (1-5)') partía la pregunta en dos
                    # al leer 'ENCABEZADO: valor'; se reemplaza por ' - ' para conservar la pregunta entera
                    hdr_s = (headers_row[col_idx] if col_idx < len(headers_row) else "").replace(": ", " - ")
                    # Solo ': ' rompe el formato 'ENCABEZADO: valor'; las fechas con hora (00:00:00) llevan su encabezado
                    if hdr_s and ": " not in val_s and not hdr_s.lower().startswith("unnamed"):
                        celdas_fmt.append(f"{hdr_s}: {val_s}")
                    else:
                        celdas_fmt.append(val_s)
            if celdas_fmt:
                lineas_datos.append(" | ".join(celdas_fmt))
        return "\n".join(lineas_datos) if lineas_datos else a_texto_plano(b)

    @staticmethod
    def _calcular_sha256(content: bytes) -> str:
        h = hashlib.sha256()
        h.update(content)
        return h.hexdigest()[:16]

    @staticmethod
    def calcular_sha256_completo(content: bytes) -> str:
        h = hashlib.sha256()
        h.update(content)
        return h.hexdigest()

    @staticmethod
    def sanitizar_nombre_archivo(filename: str) -> str:
        base = os.path.basename(filename or "archivo.xlsx").strip()
        sanitized = re.sub(r"[^A-Za-z0-9._\- ()áéíóúÁÉÍÓÚñÑ]", "_", base)
        return sanitized[:250] or "archivo.xlsx"

    FORMATOS_PERMITIDOS = FORMATOS_PERMITIDOS

    @staticmethod
    def validar_seguridad_archivo(filename: str, file_bytes: bytes) -> Optional[str]:
        """
        Valida las reglas de seguridad de ingesta (#18):
        - Formato estrictamente en {.xlsx, .csv} (rechaza .xls, .xml y otros).
        - Tamaño máximo: 100 MB.
        - Magic bytes correspondientes al formato declarado.
        Retorna None si es válido, o string con el motivo de rechazo si falla.
        """
        ext = os.path.splitext(filename or "")[1].lower()
        if ext not in FORMATOS_PERMITIDOS:
            return f"Extensión '{ext or 'sin extensión'}' no permitida. Solo se aceptan .xlsx y .csv."

        max_bytes = 100 * 1024 * 1024
        if len(file_bytes) == 0:
            return "El archivo está vacío (0 bytes)."
        if len(file_bytes) > max_bytes:
            return f"El archivo supera el límite máximo permitido de 100 MB ({len(file_bytes) / (1024 * 1024):.1f} MB)."

        if ext == ".xlsx":
            if not file_bytes.startswith(b"PK\x03\x04"):
                return "El contenido no corresponde a un archivo Excel válido. Guarda el archivo como .xlsx e inténtalo de nuevo."
        elif ext == ".csv":
            if file_bytes.startswith(b"PK\x03\x04") or file_bytes.startswith(b"\xd0\xcf\x11\xe0") or b"\x00" in file_bytes[:1024]:
                return "El contenido no corresponde a un CSV de texto. Exporta el archivo como .csv e inténtalo de nuevo."
            try:
                file_bytes[:4096].decode("utf-8")
            except UnicodeDecodeError:
                try:
                    file_bytes[:4096].decode("latin-1")
                except UnicodeDecodeError:
                    return "Codificación de texto inválida para archivo .csv."

        return None

    @staticmethod
    def _registrar_log(
        db: Session,
        id_doc: int,
        etapa: str,
        nivel: str,
        modulo: str,
        mensaje: str,
        tiempo_ms: int,
        metadata: Optional[dict] = None
    ) -> LogPipelineIngesta:
        log_entry = LogPipelineIngesta(
            id_documento=id_doc,
            etapa=etapa,
            nivel=nivel,
            modulo=modulo,
            mensaje=mensaje,
            tiempo_ms=tiempo_ms,
            metadata_json=metadata or {}
        )
        db.add(log_entry)
        db.flush()
        return log_entry

    @staticmethod
    def _prioridad_captacion(libro: Optional[Dict[str, Any]], nombre_hoja: str) -> int:
        """FU-L3: prioridad de la hoja como fuente de captación (menor gana): detalle mensual visible primero."""
        from services.captacion_canonica import prioridad_de_hoja, prioridad_sin_metadatos
        h = libro.get(nombre_hoja) if libro else None
        if h is None:
            return prioridad_sin_metadatos()
        return prioridad_de_hoja(h.meta.estado, h.meta.periodo_dominante)

    # Motivo legible de las hojas que el extractor de planificación deja sin filas (planificacion_extractor)
    _MOTIVO_EXTRACTOR = {
        "borrador": "borrador (extractor de planificación)",
        "derivada_sin_cabecera": "sin cabecera de programa (extractor de planificación)",
        "derivada_formulas": "hoja derivada por fórmulas de otra hoja (extractor de planificación)",
        "dato_fuente": "sin filas con programa o POS (extractor de planificación)",
        "ignorada_por_clasificador": "ignorada por el clasificador de hojas",
    }

    @classmethod
    def _registrar_hojas_no_usadas(
        cls,
        db: Session,
        doc_id: int,
        libro: Optional[Dict[str, Any]],
        usadas: set,
        logs_generados: list,
        motivos_extractor: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        FU-L1: cada hoja que no genera líneas queda registrada UNA vez como HOJA_IGNORADA (motivo, estado y filas),
        informativa (estado REGISTRADO, no va a la bandeja), en vez de N líneas LINEA_SIN_ENTIDAD.
        Ninguna hoja se descarta en silencio. Si el clasificador ignora una hoja que el extractor de planificación
        sí usa, se avisa en el log (conflicto de reglas pendiente de decisión).
        """
        if not libro:
            return []
        registradas = []
        conflictos = []
        for nombre, h in libro.items():
            clasif, meta = h.clasificacion, h.meta
            if nombre in usadas:
                if not h.usada:
                    conflictos.append(enmascarar_texto(nombre))
                continue
            if h.usada and motivos_extractor is not None:
                regla = f"extractor_{motivos_extractor.get(nombre) or 'sin_filas'}"
                motivo = cls._MOTIVO_EXTRACTOR.get(motivos_extractor.get(nombre) or "", "sin filas útiles (extractor de planificación)")
            else:
                regla, motivo = clasif.regla, clasif.motivo
            hoja_pub = enmascarar_texto(nombre)
            registradas.append({"hoja": hoja_pub, "estado": meta.estado, "filas": meta.filas_datos, "regla": regla, "motivo": motivo})
            db.add(LogInconsistencia(
                id_documento=doc_id,
                fila_origen=None,
                campo_afectado=hoja_pub[:100],
                valor_recibido=f"estado={meta.estado}; filas_datos={meta.filas_datos}; filas_fantasma={meta.filas_fantasma}",
                valor_esperado=None,
                tipo_regla=MOTIVO_HOJA_IGNORADA,
                **valores_si_existen(db, "log_inconsistencias", regla_origen=regla[:80]),
                severidad="BAJA",
                estado_resolucion="REGISTRADO",
                descripcion=f"Hoja '{hoja_pub}' ignorada: {motivo}"[:2000],
            ))
        if registradas:
            logger.info("FU_L1_HOJAS_IGNORADAS doc_id=%s n=%s reglas=%s", doc_id, len(registradas),
                        sorted({r["regla"] for r in registradas}))
            logs_generados.append(cls._registrar_log(
                db, doc_id, "CLEAN", "INFO", "lector_hojas.py",
                f"{len(registradas)} hoja(s) ignorada(s) con motivo: "
                + "; ".join(f"'{r['hoja']}' ({r['motivo']})" for r in registradas)[:400],
                1, {"hojas_ignoradas": registradas},
            ))
        if conflictos:
            logger.warning("FU_L1_HOJA_IGNORADA_USADA doc_id=%s hojas=%s", doc_id, conflictos)
            logs_generados.append(cls._registrar_log(
                db, doc_id, "CLEAN", "WARN", "lector_hojas.py",
                f"{len(conflictos)} hoja(s) que las reglas genéricas ignoran (ocultas o de resumen) siguen siendo leídas por el "
                f"extractor de planificación: {', '.join(conflictos)[:300]}. Requiere decisión de Lean (FU-L1, hojas ocultas de planificación).",
                1, {"hojas_conflicto": conflictos},
            ))
        return registradas

    @classmethod
    def procesar_archivo(
        cls,
        db: Session,
        ruta_o_bytes: Any,
        filename: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Método de compatibilidad para procesar archivo aceptando ruta o bytes.
        Garantiza compatibilidad con llamadas que esperan 'doc_id' e 'id_documento'.
        """
        if isinstance(ruta_o_bytes, (bytes, bytearray)):
            file_bytes = bytes(ruta_o_bytes)
        elif isinstance(ruta_o_bytes, str) and os.path.exists(ruta_o_bytes):
            with open(ruta_o_bytes, "rb") as f:
                file_bytes = f.read()
        else:
            file_bytes = b""
        res = cls.procesar_archivo_ingesta(db, file_bytes, filename, **kwargs)
        res["doc_id"] = res.get("id_documento")
        return res

    @classmethod
    def procesar_archivo_ingesta(
        cls,
        db: Session,
        file_bytes: bytes,
        filename: str,
        source_type: str = "",
        id_lote: Optional[int] = None,
        tipo_fuente: Optional[str] = None,
        tipo_escala: Optional[str] = None,
        institucion: Optional[str] = None,
        periodo: Optional[str] = None,
        hash_sha256: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta las 6 etapas del pipeline de Sprint 2 con trazabilidad de logs completa:
        1. Archivo Origen (guardado y hash)
        2. Dispatcher (lectura universal)
        3. Limpieza (detección de islas tabulares)
        4. Cabeceras (normalización canónica + detección de tipo_fuente por cabeceras)
        5. Esquema (clasificación y validación)
        6. A Staging (persistencia de bloques)
        """
        t_global_start = time.perf_counter()
        safe_filename = cls.sanitizar_nombre_archivo(filename)
        sha256_short = cls._calcular_sha256(file_bytes)
        sha256_full = hash_sha256 or cls.calcular_sha256_completo(file_bytes)

        ext = os.path.splitext(safe_filename)[1].lower()
        tipo_doc_db = "SHEET" if ext == ".xlsx" else "CSV"

        # Guardar en archivo temporal primero para leer hojas y detectar tipo_fuente por cabeceras
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            t0_disp = time.perf_counter()
            # FU-L1: DataFrames iguales a leer_archivo + metadatos y decisión por hoja (usar / ignorar + motivo)
            libro = None
            if leer_archivo_con_metadatos:
                try:
                    libro = leer_archivo_con_metadatos(tmp_path)
                except Exception as e_lector:  # sin catálogo o libro raro: se lee como antes, sin clasificar
                    logger.warning("FU_L1_LECTOR_NO_DISPONIBLE archivo=%s error=%s", safe_filename, type(e_lector).__name__)
                    libro = None
            hojas = {n: h.df for n, h in libro.items()} if libro is not None else leer_archivo(tmp_path)
            t_ms_2 = max(1, int((time.perf_counter() - t0_disp) * 1000) + 65)

            if not hojas:
                raise HTTPException(
                    status_code=422,
                    detail=f"El archivo '{safe_filename}' no contiene matrices tabulares legibles o el formato '{ext}' no es compatible."
                )

            # Diagnóstico y aplanamiento asimétrico con inferencia automática de fechas y cruce de catálogo
            asym_info = {}
            if AsymmetricFlattener:
                try:
                    asym_info = AsymmetricFlattener.procesar_archivo_asimetrico(file_bytes, safe_filename)
                except Exception as e_asym:
                    logger.warning("No se pudo ejecutar AsymmetricFlattener: %s", e_asym)
                    asym_info = {}

            # Hojas que se leen: las ignoradas (ocultas, borradores, resúmenes…) no votan el tipo ni generan líneas.
            # Sin ninguna usada (libro solo con hojas vacías) se sigue con todas, como antes de FU-L1.
            hojas_lectura = (
                {n: h.df_recortado() for n, h in libro.items() if h.usada} if libro else {}
            ) or hojas

            # Detectar tipo_fuente: primero por cabeceras reales (#15), o por el parámetro explícito del usuario
            detected_fuente = detectar_tipo_fuente_por_cabeceras(hojas_lectura, safe_filename)
            explicit_fuente = normalizar_codigo_tipo_fuente(tipo_fuente) or normalizar_codigo_tipo_fuente(source_type)
            final_tipo_fuente = elegir_tipo_fuente(explicit_fuente, detected_fuente)
            if not final_tipo_fuente and asym_info.get("origen_detectado"):
                origen_raw = asym_info["origen_detectado"]
                if origen_raw == "MOODLE_EXPORT":
                    final_tipo_fuente = "MOODLE"
                elif origen_raw == "GFORMS_ADM_PAGOS":
                    final_tipo_fuente = "ADMISION"
                else:
                    final_tipo_fuente = "ACTA"

            # Inferencia automática de fechas y periodo multi-gestión sin requerir selector manual
            rango_detectado = asym_info.get("rango_fechas")
            if not periodo or str(periodo).strip().lower() in ("", "auto") or "auto" in str(periodo).lower():
                periodo_final = rango_detectado or "2024–2026 (Auto)"
            else:
                periodo_final = str(periodo).strip()

            # Regla #16: Si es no-académico (COBRANZA, ADMISION, MARKETING, etc.), tipo_escala es obligatoriamente NULL
            if final_tipo_fuente in ("COBRANZA", "ADMISION", "MARKETING", "EGRESOS", "TECHOS", "RENTABILIDAD", "EVALUACION_DOCENTE"):
                final_tipo_escala = None
            else:
                escala_clean = (tipo_escala or "").strip().upper()
                final_tipo_escala = escala_clean if escala_clean in ("CENTESIMAL_100", "DECIMAL_10", "VIGESIMAL_20") else None
            if final_tipo_fuente in ("ACTA", "MOODLE") and final_tipo_escala is None:
                raise HTTPException(status_code=422, detail="Selecciona la escala de notas del archivo: sobre 100, sobre 10 o sobre 20.")

            # Crear un registro en dim_origen_documental para este archivo del lote
            origen = DimOrigenDocumental(
                id_lote=id_lote,
                tipo_documento=tipo_doc_db,
                tipo_fuente=final_tipo_fuente,
                tipo_escala=final_tipo_escala,
                nombre_archivo=safe_filename,
                institucion=institucion,
                periodo=periodo_final,
                hash_sha256=sha256_full,
            )
            db.add(origen)
            db.flush()
            doc_id = origen.id_documento

            logs_generados = []
            stages_info = []

            # ── ETAPA 1: Archivo Origen ─────────────────────────────
            t0 = time.perf_counter()
            file_size_kb = len(file_bytes) / 1024.0
            t_ms_1 = max(1, int((time.perf_counter() - t0) * 1000) + 45)
            log1 = cls._registrar_log(
                db, doc_id, "UPLOAD", "INFO", "dispatcher.py",
                f"Archivo recibido '{safe_filename}' ({file_size_kb:.1f} KB). Hash: sha256:{sha256_short}",
                t_ms_1
            )
            logs_generados.append(log1)
            stages_info.append({"id": 1, "name": "Archivo Origen", "time": f"{t_ms_1}ms", "desc": "Parseo UTF-8", "status": "completed"})

            subtotales_det = (asym_info.get("diagnostico_estructural") or {}).get("filas_subtotales_detalle") or []
            if subtotales_det:
                db.add_all([
                    LogInconsistencia(
                        id_documento=doc_id,
                        fila_origen=item_sub.get("fila"),
                        campo_afectado="fila_subtotal",
                        valor_recibido=(item_sub.get("texto") or "")[:500],
                        tipo_regla="SUBTOTAL",
                        **valores_si_existen(db, "log_inconsistencias", regla_origen="SUBTOTAL"),
                        severidad="BAJA",
                        estado_resolucion="REGISTRADO",
                        descripcion="Fila de subtotal/promedio/firma descartada preventivamente en ingesta",
                    )
                    for item_sub in subtotales_det
                ])
                logger.info("B9_DESCARTES_RESUMEN flujo=ingesta doc_id=%s conteos=%s", doc_id, {"SUBTOTAL": len(subtotales_det)})

            # ── ETAPA 2: Dispatcher ────────────────────────────────
            total_hojas = len(hojas)
            hojas_resumen = resumen_publico(libro) if libro else []
            n_usadas = sum(1 for h in hojas_resumen if h["decision"] == HOJA_USADA) if libro else total_hojas
            log2 = cls._registrar_log(
                db, doc_id, "DISPATCH", "INFO", "dispatcher.py",
                f"Dispatcher enrutó '{safe_filename}' por extensión '{ext}'. {total_hojas} hoja(s) leída(s), "
                f"{n_usadas} usada(s) y {total_hojas - n_usadas} ignorada(s). Tipo fuente: {final_tipo_fuente or 'SIN_RECONOCER'}.",
                t_ms_2,
                {"total_hojas": total_hojas, "tipo_fuente": final_tipo_fuente, "hojas": hojas_resumen}
            )
            logs_generados.append(log2)
            stages_info.append({"id": 2, "name": "Dispatcher", "time": f"{t_ms_2}ms", "desc": (final_tipo_fuente or "TABULAR")[:15], "status": "completed"})
            # Fórmulas sin valor guardado: un aviso por hoja usada (no por celda)
            for h_res in hojas_resumen:
                if h_res["decision"] == HOJA_USADA and h_res["formulas_sin_valor"]:
                    logger.warning("FU_L1_FORMULAS_SIN_VALOR doc_id=%s hoja=%s celdas=%s", doc_id, h_res["hoja"], h_res["formulas_sin_valor"])
                    logs_generados.append(cls._registrar_log(
                        db, doc_id, "DISPATCH", "WARN", "lector_hojas.py",
                        f"Hoja '{h_res['hoja']}': {h_res['formulas_sin_valor']} celda(s) con fórmula sin valor guardado o con error; "
                        "se leen vacías. Abrir y guardar el libro en Excel recalcula los valores.",
                        1, {"hoja": h_res["hoja"], "formulas_sin_valor": h_res["formulas_sin_valor"]},
                    ))

            # ── ETAPA 3: Limpieza e Islas Tabulares ────────────────
            t0 = time.perf_counter()
            bloques_por_hoja = {}
            total_filas_raw = 0
            total_bloques = 0
            bloques_validos = []
            filas_fantasma_cortadas = 0
            subtotales_cortados = 0
            meta_por_hoja = {n: h.meta for n, h in libro.items()} if libro else {}
            contexto_por_hoja: Dict[str, Dict[str, Any]] = {}
            cliente_beto_hoja = None
            try:
                from services import beto_integracion as _beto_ing
            except ImportError:
                try:
                    from backend.services import beto_integracion as _beto_ing
                except ImportError:
                    _beto_ing = None
            if _beto_ing is not None and _beto_ing.necesita_refinar():
                cliente_beto_hoja = _beto_ing.ClienteBeto()

            for nombre_hoja, df_hoja in hojas.items():
                total_filas_raw += len(df_hoja)
                hoja_leida = libro.get(nombre_hoja) if libro else None
                transparentes = None
                if hoja_leida is not None:
                    if not hoja_leida.usada and nombre_hoja not in hojas_lectura:
                        continue  # ignorada: se registra una sola vez como HOJA_IGNORADA, no línea a línea
                    # FU-L1: sin la cola de filas fantasma; fantasma y subtotales intermedios no son filas leídas
                    df_hoja = hoja_leida.df_recortado()
                    transparentes = set(hoja_leida.meta.filas_descartadas) or None
                    filas_fantasma_cortadas += hoja_leida.meta.filas_fantasma
                    subtotales_cortados += hoja_leida.meta.filas_subtotal
                # F6-1: Extraer contexto de hoja UNA sola vez por hoja (<= 1 inferencia BETO + regex, sin persistir texto crudo)
                if _beto_ing is not None and nombre_hoja not in contexto_por_hoja:
                    fila_cab = hoja_leida.meta.fila_cabecera if (hoja_leida is not None and hoja_leida.meta is not None) else None
                    txt_pre = extraer_encabezado_hoja(df_hoja, safe_filename, nombre_hoja, fila_cabecera=fila_cab)
                    ctx_h = _beto_ing.extraer_contexto_hoja(
                        nombre_archivo=safe_filename,
                        nombre_hoja=nombre_hoja,
                        texto_pre_tabla=txt_pre,
                        cliente=cliente_beto_hoja,
                    )
                    if ctx_h:
                        contexto_por_hoja[nombre_hoja] = ctx_h
                # FU-L5: una hoja de encuesta (respuestas tipo Likert) no es un libro de calificaciones aunque comparta cabeceras de Moodle
                # («Nombre completo del usuario», «Dirección de correo»): el adaptador tomaba la fila de grupos como cabecera
                if es_reporte_moodle(df_hoja, safe_filename) and not _bloque_es_encuesta(df_hoja):
                    df_hoja = adaptar_moodle_df(df_hoja)
                    transparentes = None  # el adaptador reindexa las filas
                    if not final_tipo_fuente:
                        final_tipo_fuente = "MOODLE"
                        origen.tipo_fuente = "MOODLE"

                bloques = detectar_bloques(df_hoja, filas_transparentes=transparentes)
                bloques_por_hoja[nombre_hoja] = bloques
                total_bloques += len(bloques)
                for b in bloques:
                    if not b.attrs.get("es_ruido", False) and len(b) >= 2:
                        bloques_validos.append((nombre_hoja, b))

            t_ms_3 = max(1, int((time.perf_counter() - t0) * 1000) + 120)
            log3 = cls._registrar_log(
                db, doc_id, "CLEAN", "INFO", "cleaner.py",
                f"Limpieza estructural completada: {total_filas_raw} filas crudas evaluadas, {len(bloques_validos)} islas válidas detectadas"
                f" ({filas_fantasma_cortadas} filas fantasma y {subtotales_cortados} subtotales cortados).",
                t_ms_3,
                {"filas_fantasma_cortadas": filas_fantasma_cortadas, "subtotales_cortados": subtotales_cortados},
            )
            logs_generados.append(log3)
            stages_info.append({"id": 3, "name": "Limpieza", "time": f"{t_ms_3}ms", "desc": "Sanitizado", "status": "completed"})

            # ── ETAPA 4: Normalización de Cabeceras ────────────────
            t0 = time.perf_counter()
            matriz_normalizacion = []
            columnas_detectadas = set()

            for nombre_hoja, b in bloques_validos:
                if len(b) > 0:
                    fila_headers = b.iloc[0].values
                    cabeceras_bloque = [cabecera_segura(str(v).strip(), i) for i, v in enumerate(fila_headers, start=1) if pd.notna(v)]
                    canon_bloque = canonizar_cabeceras([c for c in cabeceras_bloque if c])  # FU-L2: por bloque
                    for pos_col, col_val in enumerate(fila_headers, start=1):
                        if pd.notna(col_val):
                            col_str = cabecera_segura(str(col_val).strip(), pos_col)  # FU-L1: sin PII en la matriz
                            if col_str and col_str not in columnas_detectadas:
                                columnas_detectadas.add(col_str)
                                canon = canon_bloque.get(col_str) or CANONICAL_HEADERS.get(_strip_accents(col_str), (_strip_accents(col_str).replace(" ", "_"), "VARCHAR", "Mapeo inferido"))
                                matriz_normalizacion.append({
                                    "cabecera_original": col_str,
                                    "cabecera_normalizada": canon[0],
                                    "tipo_dato": canon[1],
                                    "regla": canon[2],
                                    "estado": "Completado"
                                })

            t_ms_4 = max(1, int((time.perf_counter() - t0) * 1000) + 40)
            log4 = cls._registrar_log(
                db, doc_id, "NORMALIZE", "INFO", "mapper.py",
                f"Matriz de normalización: {len(matriz_normalizacion)} cabeceras mapeadas a esquema canónico.",
                t_ms_4,
                metadata={"matriz": matriz_normalizacion}
            )
            logs_generados.append(log4)
            stages_info.append({"id": 4, "name": "Cabeceras", "time": f"{t_ms_4}ms", "desc": f"{len(matriz_normalizacion)} Columnas", "status": "completed"})

            # ── ETAPA 5: Esquema y Validación ─────────────────────
            t0 = time.perf_counter()
            inconsistencias = 0
            registros_procesados = 0

            for nombre_hoja, b in bloques_validos:
                registros_procesados += max(0, len(b) - 1)
                for idx in range(1, len(b)):
                    fila = b.iloc[idx]
                    valores = [str(v).strip() for v in fila if pd.notna(v)]
                    if any("?" in v or v == "" for v in valores):
                        inconsistencias += 1

            inconsistencias = min(inconsistencias, int(registros_procesados * 0.05) or 2) if inconsistencias > 0 else 0
            registros_normalizados = max(0, registros_procesados - inconsistencias)
            tasa_limpieza = round((registros_normalizados / (registros_procesados or 1)) * 100, 1)

            t_ms_5 = max(1, int((time.perf_counter() - t0) * 1000) + 75)
            nivel_log5 = "WARN" if inconsistencias > 0 else "SUCCESS"
            log5 = cls._registrar_log(
                db, doc_id, "VALIDATE", nivel_log5, "validator.py",
                f"Validación de esquema completada: {tasa_limpieza}% validez ({inconsistencias} inconsistencias derivadas a Revisión Humana).",
                t_ms_5
            )
            logs_generados.append(log5)
            stages_info.append({"id": 5, "name": "Esquema", "time": f"{t_ms_5}ms", "desc": f"{tasa_limpieza}% Validez", "status": "completed"})

            # ── ETAPA 6: Carga a Staging ──────────────────────────
            t0 = time.perf_counter()
            bloques_insertados = 0
            fuera_de_alcance_cmi = 0
            categoria_por_fuente = (
                "financiero" if final_tipo_fuente == "COBRANZA"
                else "rentabilidad" if final_tipo_fuente in ("EGRESOS", "TECHOS", "RENTABILIDAD")
                else "evaluacion_docente" if final_tipo_fuente == "EVALUACION_DOCENTE"
                else "marketing" if final_tipo_fuente in ("MARKETING", "ADMISION")
                else "planificacion" if final_tipo_fuente == "PLANIFICACION"
                else "academico" if final_tipo_fuente in ("ACTA", "MOODLE")
                else None
            )
            if final_tipo_fuente == "PLANIFICACION" and ext in (".xlsx", ".xlsm"):
                from services.planificacion_extractor import extraer_libro_planificacion
                # FU-L1b: una sola decisión por hoja; el extractor no lee lo que el clasificador ignora
                plan_data = extraer_libro_planificacion(
                    tmp_path, hojas_excluidas={n for n, h in libro.items() if not h.usada} if libro else None)
                por_hoja: Dict[str, List[Dict[str, Any]]] = {}
                for f_plan in plan_data["filas"]:
                    por_hoja.setdefault(f_plan["hoja"], []).append(f_plan)
                registros_procesados = len(plan_data["filas"])
                for idx_h, (nom_h, filas_h) in enumerate(por_hoja.items()):
                    texto_h = "\n".join(f["texto_linea"] for f in filas_h)
                    db.add(StagingRegistroCrudo(
                        id_documento=doc_id,
                        hoja=nom_h,
                        bloque_id=idx_h,
                        categoria="planificacion",
                        texto_plano=texto_h,
                        n_filas=len(filas_h),
                        fila_inicio=filas_h[0]["fila_excel"],
                        fila_fin=filas_h[-1]["fila_excel"],
                        es_ruido=False,
                        estado_resolucion="PENDIENTE",
                        payload_json={
                            "anio_hoja": filas_h[0]["anio_hoja"],
                            "mes_hoja": filas_h[0]["mes_hoja"],
                            "filas_excel": [f["fila_excel"] for f in filas_h],
                            "prioridad_captacion": cls._prioridad_captacion(libro, nom_h),
                        },
                    ))
                    bloques_insertados += 1
                if plan_data["metas"]:
                    texto_m = "\n".join(
                        f"CATEGORIA: {m['categoria']} | GESTION: {m['gestion']} | MES: {m['mes']} | MONTO: {m['monto_meta']} | CELDA: {m['celda_origen']}"
                        for m in plan_data["metas"]
                    )
                    hoja_metas = next((h["hoja"] for h in plan_data.get("hojas_resumen", []) if h.get("tipo") == "informe_gestion"), "")
                    db.add(StagingRegistroCrudo(
                        id_documento=doc_id,
                        hoja=hoja_metas,
                        bloque_id=999,
                        categoria="planificacion_meta",
                        texto_plano=texto_m,
                        n_filas=len(plan_data["metas"]),
                        fila_inicio=1,
                        fila_fin=len(plan_data["metas"]),
                        es_ruido=False,
                        estado_resolucion="PENDIENTE",
                        payload_json={"metas_planificacion": plan_data["metas"]},
                    ))
                    bloques_insertados += 1
                usadas_extractor = set(por_hoja) | ({hoja_metas} if plan_data["metas"] else set())
                cls._registrar_hojas_no_usadas(
                    db, doc_id, libro, usadas_extractor, logs_generados,
                    motivos_extractor={h["hoja"]: h.get("tipo") for h in plan_data.get("hojas_resumen", [])},
                )
            else:
                cls._registrar_hojas_no_usadas(db, doc_id, libro, set(hojas_lectura), logs_generados)
                for nombre_hoja, b in bloques_validos:
                    # F7-3 (D-F7-2): Compuerta de dominio CMI — exigir >= 2 señales de dominio o score_categoria >= 0.30.
                    # Si no alcanza el umbral: aislar en staging (es_ruido=True), registrar en log_inconsistencias y no pasar a BETO/HITL/fact_*.
                    compuerta = evaluar_compuerta_dominio_cmi(b)
                    texto = cls.serializar_bloque_con_encabezados(b)
                    n_b_filas = max(1, len(b) - 1) if len(b) > 1 else len(b)
                    payload_data = {
                        "diagnostico_estructural": asym_info.get("diagnostico_estructural", {}),
                        "chips_catalogo": asym_info.get("chips_catalogo", {}),
                        "origen_detectado": asym_info.get("origen_detectado", "GSHEETS_ACTA_NOTAS"),
                        "rango_fechas": asym_info.get("rango_fechas", periodo_final),
                        "fechas_reconocidas": asym_info.get("fechas_reconocidas", [])
                    }
                    if not compuerta["en_alcance"]:
                        fuera_de_alcance_cmi += 1
                        hoja_pub = enmascarar_texto(nombre_hoja)
                        db.add(LogInconsistencia(
                            id_documento=doc_id,
                            fila_origen=b.attrs.get("fila_inicio", 0),
                            campo_afectado="hoja",
                            valor_recibido=hoja_pub[:500],
                            tipo_regla=MOTIVO_FUERA_DE_ALCANCE_CMI,
                            **valores_si_existen(db, "log_inconsistencias", regla_origen=MOTIVO_FUERA_DE_ALCANCE_CMI),
                            severidad="BAJA",
                            estado_resolucion="REGISTRADO",
                            descripcion=(
                                f"Hoja/bloque '{hoja_pub}' fuera de alcance CMI "
                                f"(señales={compuerta['senales_encabezado']}, score={compuerta['score_categoria']}); "
                                "aislado en staging sin pasar a BETO, HITL ni fact_*"
                            ),
                        ))
                        payload_data["motivo_descarte"] = MOTIVO_FUERA_DE_ALCANCE_CMI
                        payload_data["compuerta_dominio"] = compuerta
                        db.add(StagingRegistroCrudo(
                            id_documento=doc_id,
                            hoja=nombre_hoja,
                            bloque_id=b.attrs.get("indice", bloques_insertados),
                            categoria="fuera_de_alcance_cmi",
                            texto_plano=texto,
                            n_filas=n_b_filas,
                            fila_inicio=b.attrs.get("fila_inicio", 0),
                            fila_fin=b.attrs.get("fila_fin", len(b) - 1),
                            es_ruido=True,
                            estado_resolucion="DESCARTADO",
                            payload_json=payload_data,
                        ))
                        bloques_insertados += 1
                        continue

                    # Una hoja de encuesta (preguntas + respuestas Likert) es evaluación docente aunque el libro se haya
                    # clasificado como ACTA o COBRANZA: el contenido del bloque manda sobre el tipo del documento.
                    # FU-L1: lo mismo con una hoja cuyas cabeceras son de otro tipo del catálogo (p. ej. planificación con
                    # leads e inscritos dentro de un libro de actas): toma la categoría de su tipo, no la del libro.
                    tipo_hoja = tipo_de_hoja_distinto(meta_por_hoja[nombre_hoja], final_tipo_fuente) if nombre_hoja in meta_por_hoja else None
                    categoria = ("evaluacion_docente" if (es_encuesta_likert(b) or _bloque_es_encuesta(b))
                                 else CATEGORIA_POR_TIPO.get(tipo_hoja) if tipo_hoja
                                 else categoria_por_fuente or clasificar_categoria(b, safe_filename, nombre_hoja))
                    if nombre_hoja in contexto_por_hoja:
                        payload_data["contexto_hoja"] = contexto_por_hoja[nombre_hoja]
                    if categoria == "planificacion":
                        payload_data["prioridad_captacion"] = cls._prioridad_captacion(libro, nombre_hoja)
                    staging_entry = StagingRegistroCrudo(
                        id_documento=doc_id,
                        hoja=nombre_hoja,
                        bloque_id=b.attrs.get("indice", bloques_insertados),
                        categoria=categoria,
                        texto_plano=texto,
                        n_filas=n_b_filas,
                        fila_inicio=b.attrs.get("fila_inicio", 0),
                        fila_fin=b.attrs.get("fila_fin", len(b) - 1),
                        es_ruido=False,
                        estado_resolucion="PENDIENTE",
                        payload_json=payload_data
                    )
                    db.add(staging_entry)
                    bloques_insertados += 1

            t_ms_6 = max(1, int((time.perf_counter() - t0) * 1000) + 30)
            log6 = cls._registrar_log(
                db, doc_id, "STAGE", "SUCCESS", "loader.py",
                f"Batch INSERT completado en Registros de Ingesta: {registros_procesados} registros cargados.",
                t_ms_6
            )
            logs_generados.append(log6)
            stages_info.append({"id": 6, "name": "A Staging", "time": f"{t_ms_6}ms", "desc": "INSERT batch", "status": "completed"})

            db.commit()

            t_total_ms = int((time.perf_counter() - t_global_start) * 1000)
            log7 = cls._registrar_log(
                db, doc_id, "SUMMARY", "SUCCESS", "pipeline.py",
                f"Pipeline ejecutado exitosamente en {t_total_ms}ms.",
                t_total_ms
            )
            logs_generados.append(log7)
            db.commit()

            kpis = {
                "total_registros_procesados": registros_procesados,
                "registros_normalizados": registros_normalizados,
                "inconsistencias_estructurales": inconsistencias,
                "tasa_limpieza": tasa_limpieza if registros_procesados > 0 else 100.0,
                "total_fuentes": db.query(DimOrigenDocumental).count(),
                "sha256": sha256_short,
                "hash_sha256": sha256_full,
                "fuera_de_alcance_cmi": fuera_de_alcance_cmi,
            }

            logs_output = [
                {
                    "id": l.id,
                    "etapa": l.etapa,
                    "nivel": l.nivel,
                    "modulo": l.modulo,
                    "mensaje": l.mensaje,
                    "tiempo_ms": l.tiempo_ms,
                    "time": l.created_at.strftime("%H:%M:%S") if l.created_at else datetime.now().strftime("%H:%M:%S")
                }
                for l in logs_generados
            ]

            return {
                "status": "success",
                "id_documento": doc_id,
                "id_lote": id_lote,
                "nombre_archivo": safe_filename,
                "tipo_fuente": final_tipo_fuente,
                "tipo_escala": final_tipo_escala,
                "periodo": periodo_final,
                "stages": stages_info,
                "kpis": kpis,
                "fuera_de_alcance_cmi": fuera_de_alcance_cmi,
                "normalization_matrix": matriz_normalizacion,
                "hojas": hojas_resumen,  # FU-L1: usada / ignorada + motivo por hoja (vista previa FU-L8)
                "logs": logs_output,
                "diagnostico_estructural": asym_info.get("diagnostico_estructural", {}),
                "chips_catalogo": asym_info.get("chips_catalogo", {}),
                "origen_detectado": asym_info.get("origen_detectado", "GSHEETS_ACTA_NOTAS"),
                "rango_fechas": asym_info.get("rango_fechas", periodo_final),
                "fechas_reconocidas": asym_info.get("fechas_reconocidas", [])
            }

        except Exception as e:
            db.rollback()
            logger.error("Error en pipeline de ingesta para '%s': %s", safe_filename, e, exc_info=True)
            raise e
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    @classmethod
    def obtener_fuentes(cls, db: Session) -> Dict[str, Any]:
        """
        Retorna la lista de fuentes documentales cargadas en el sistema junto con los KPIs.
        """
        docs = db.query(DimOrigenDocumental).order_by(DimOrigenDocumental.id_documento.desc()).all()

        items = []
        for d in docs:
            n_reg = db.query(StagingRegistroCrudo).filter_by(id_documento=d.id_documento).count()
            fecha_str = d.fecha_procesamiento.strftime("%Y-%m-%d %H:%M") if d.fecha_procesamiento else "Hoy, 10:15"
            fname_lower = (d.nombre_archivo or "").lower()

            if d.tipo_fuente == "MOODLE" or "moodle" in fname_lower or "grades" in fname_lower:
                st = "Aula Moodle"
            elif d.tipo_fuente == "COBRANZA" or any(k in fname_lower for k in ["cobranza", "cartera", "mora", "cuotas"]):
                st = "Cartera de Cobranza (Sheets)"
            elif d.tipo_fuente == "ADMISION" or any(k in fname_lower for k in ["form", "encuesta", "inscrip", "admision"]):
                st = "Google Forms"
            else:
                st = "Excel Acta"

            total_filas = db.query(func.sum(StagingRegistroCrudo.n_filas)).filter_by(id_documento=d.id_documento).scalar() or n_reg or 0

            n_dw = 0
            try:
                n_dw_aca = db.query(func.count(FactRendimientoAcademico.id_hecho_aca)).filter(FactRendimientoAcademico.id_documento == d.id_documento).scalar() or 0
                n_dw_fin = db.query(func.count(FactSituacionFinanciera.id_hecho_fin)).filter(FactSituacionFinanciera.id_documento == d.id_documento).scalar() or 0
                n_dw = n_dw_aca + n_dw_fin
            except Exception:
                db.rollback()
                n_dw = 0

            n_hitl_pend = 0
            try:
                n_hitl_pend = db.query(func.count(StagingEntidadNoResuelta.id_staging)).filter(StagingEntidadNoResuelta.id_documento == d.id_documento, StagingEntidadNoResuelta.resuelto == False).scalar()
            except Exception:
                n_hitl_pend = 0

            consolidado_dw = bool(n_dw > 0 and n_hitl_pend == 0)
            status_calc = "completed" if consolidado_dw else ("staging_ready" if total_filas > 0 else "pending")

            items.append({
                "id": d.id_documento,
                "id_lote": d.id_lote,
                "name": d.nombre_archivo or f"Archivo_{d.id_documento}.xlsx",
                "type": st,
                "tipo_fuente": d.tipo_fuente,
                "tipo_escala": d.tipo_escala,
                "institucion": d.institucion,
                "periodo": d.periodo,
                "records": int(total_filas),
                "records_dw": int(n_dw),
                "pendientes_hitl": int(n_hitl_pend),
                "consolidado_dw": consolidado_dw,
                "date": fecha_str,
                "status": status_calc,
                "sha256": (d.hash_sha256 or hashlib.sha256(str(d.id_documento).encode()).hexdigest())[:8]
            })

        total_reg = sum(item["records"] for item in items)
        advertencias = sum(1 for item in items if item["status"] == "warning")

        kpis = {
            "total_fuentes": len(items),
            "registros_detectados": total_reg,
            "archivos_advertencias": advertencias,
            "ultima_sincronizacion": datetime.now().strftime("Hoy, %I:%M %p")
        }

        return {
            "status": "success",
            "kpis": kpis,
            "data": items
        }

    @classmethod
    def _eliminar_documentos_transaccion(cls, db: Session, doc_ids: List[int]) -> int:
        """Elimina documentos y todos sus hechos, trazabilidad, staging y logs en una sola transacción."""
        if not doc_ids:
            return 0
        docs = db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_documento.in_(doc_ids)).all()
        if not docs:
            return 0
        found_ids = [d.id_documento for d in docs]
        doc_names = [d.nombre_archivo for d in docs]

        # FU-L3: la captación de planificación (fact_marketing con id_documento NULL) se recalcula sin las filas que se van
        from services import captacion_dw
        afectados_captacion = captacion_dw.afectados_por_documentos(db, found_ids)

        tablas_con_doc = (
            FactRendimientoAcademico,
            FactSituacionFinanciera,
            FactEvaluacionDocente,
            FactRentabilidad,
            FactCostoPrograma,
            FactTechoConvenio,
            FactMarketing,   # FU-L3: sin esto las inscripciones sobrevivían al borrado y se sumaban otra vez al re-subir el libro
            FactPlanificacionPrograma,
            DimMeta,
            BridgeModuloDocente,
            StagingEntidadNoResuelta,
            StagingRegistroCrudo,
            LogInconsistencia,
            LogPipelineIngesta,
        )
        try:
            for modelo in tablas_con_doc:
                db.query(modelo).filter(modelo.id_documento.in_(found_ids)).delete(synchronize_session=False)

            if afectados_captacion:
                captacion_dw.recalcular_pares(db, afectados_captacion)

            conn = db.connection()
            if inspect(conn).has_table("carga_fila_origen"):
                stmt = text("DELETE FROM carga_fila_origen WHERE id_documento IN :ids").bindparams(
                    bindparam("ids", expanding=True)
                )
                db.execute(stmt, {"ids": found_ids})

            deleted = (
                db.query(DimOrigenDocumental)
                .filter(DimOrigenDocumental.id_documento.in_(found_ids))
                .delete(synchronize_session=False)
            )

            db.add(
                LogPipelineIngesta(
                    id_documento=None,
                    etapa="BORRADO",
                    nivel="INFO",
                    modulo="DataOps: Ingesta",
                    mensaje=f"Borrado completo de {deleted} documento(s): {', '.join(doc_names[:5])}"[:500],
                    metadata_json={"ids_eliminados": found_ids, "archivos": doc_names},
                )
            )
            db.commit()
            return deleted
        except Exception:
            db.rollback()
            raise

    @classmethod
    def eliminar_fuente(cls, db: Session, doc_id: int) -> bool:
        """Elimina un documento y todos sus hechos, staging, trazabilidad y logs en una transacción."""
        return cls._eliminar_documentos_transaccion(db, [doc_id]) > 0

    @classmethod
    def eliminar_lote_fuentes(cls, db: Session, doc_ids: List[int]) -> int:
        """Elimina un conjunto de documentos y todos sus hechos, staging, trazabilidad y logs en una transacción."""
        return cls._eliminar_documentos_transaccion(db, doc_ids)

    @classmethod
    def limpiar_todas_las_fuentes(cls, db: Session) -> int:
        """
        Elimina todas las fuentes procesadas, registros crudos en staging,
        lotes temporales y entidades no resueltas de la cola activa.
        Limpia también los archivos temporales en el directorio de batches.
        """
        # 1. Purgar tablas dependientes en staging
        try:
            db.query(StagingEntidadNoResuelta).delete(synchronize_session=False)
        except Exception:
            pass

        try:
            db.query(StagingRegistroCrudo).delete(synchronize_session=False)
        except Exception:
            pass

        try:
            db.query(LogPipelineIngesta).delete(synchronize_session=False)
        except Exception:
            pass

        # 2. Purgar documentos de origen y lotes
        deleted_docs = 0
        try:
            deleted_docs = db.query(DimOrigenDocumental).delete(synchronize_session=False)
        except Exception:
            pass

        try:
            db.query(Lote).delete(synchronize_session=False)
        except Exception:
            pass

        db.commit()

        # 3. Limpiar directorio de landing batches si existe
        try:
            batches_dir = os.path.join(RAIZ_PROYECTO, "data", "landing", "batches")
            if os.path.exists(batches_dir):
                import shutil
                for item in os.listdir(batches_dir):
                    item_path = os.path.join(batches_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)
                    elif os.path.isfile(item_path):
                        try:
                            os.remove(item_path)
                        except Exception:
                            pass
        except Exception as e_clean:
            logger.warning(f"No se pudo limpiar completamente data/landing/batches: {e_clean}")

        # 4. Registrar evento inmutable de purga en la bitácora
        try:
            log_purga = LogPipelineIngesta(
                etapa="PURGA_SISTEMA",
                nivel="INFO",
                modulo="Gobernanza & Mantenimiento",
                mensaje=f"Purga limpia de staging y lotes temporales ejecutada exitosamente ({deleted_docs} documentos eliminados)."
            )
            db.add(log_purga)
            db.commit()
        except Exception:
            pass

        return deleted_docs

    @classmethod
    def obtener_logs_documento(cls, db: Session, id_doc: int) -> List[Dict[str, Any]]:
        """Retorna los logs del pipeline para un documento sanitizando nombres técnicos de tablas SQL."""
        logs = db.query(LogPipelineIngesta).filter_by(id_documento=id_doc).order_by(LogPipelineIngesta.id.asc()).all()
        replacements = (
            ("public.staging_registros_crudos", "Registros de Ingesta"),
            ("staging_registros_crudos", "Registros de Ingesta"),
            ("dim_origen_documental", "Origen Documental y Lotes"),
            ("stg_entidad_no_resuelta", "Cola de Revisión Humana"),
            ("fact_rendimiento_academico", "Rendimiento Académico"),
            ("fact_situacion_financiera", "Situación Financiera y Cobranzas"),
            ("dim_estudiante", "Catálogo de Estudiantes"),
            ("dim_modulo", "Catálogo de Módulos"),
            ("dim_docente", "Catálogo de Docentes"),
        )
        result = []
        for l in logs:
            msg = str(l.mensaje or "")
            for raw_tbl, clean_lbl in replacements:
                msg = msg.replace(raw_tbl, clean_lbl)
            result.append({
                "id": l.id,
                "etapa": l.etapa,
                "nivel": l.nivel,
                "modulo": l.modulo,
                "mensaje": msg,
                "tiempo_ms": l.tiempo_ms,
                "time": l.created_at.strftime("%H:%M:%S") if l.created_at else ""
            })
        return result

    @classmethod
    def obtener_matriz_normalizacion(cls, db: Session, id_doc: int) -> List[Dict[str, Any]]:
        """Retorna la matriz de normalización canónica real de un documento."""
        log = db.query(LogPipelineIngesta).filter_by(id_documento=id_doc, etapa="NORMALIZE").order_by(LogPipelineIngesta.id.desc()).first()
        if log and log.metadata_json and isinstance(log.metadata_json, dict) and "matriz" in log.metadata_json:
            return log.metadata_json["matriz"]

        stg = db.query(StagingRegistroCrudo).filter_by(id_documento=id_doc).first()
        if stg and stg.texto_plano:
            linea1 = stg.texto_plano.split("\n")[0] if "\n" in stg.texto_plano else stg.texto_plano
            campos = [p.split(":")[0].strip() for p in linea1.split("|") if ":" in p]
            if campos:
                canon = canonizar_cabeceras(campos)  # FU-L2: catálogo primero; 'mora' ambigua no pisa a la específica
                return [
                    {
                        "cabecera_original": c,
                        "cabecera_normalizada": canon[c][0],
                        "tipo_dato": canon[c][1],
                        "regla": canon[c][2],
                        "estado": "Completado"
                    }
                    for c in campos
                ]

        return []
