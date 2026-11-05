"""
backend/services/extraccion_por_encabezado.py
---------------------------------------------
Extracción de campos desde líneas serializadas 'ENCABEZADO: valor | ...' (formato del ingestor).
La lee /pipeline/process y /dataops/confirm-dw-insert, para que ambos flujos produzcan los mismos
hechos con la nota, la fecha y el estudiante reales de cada fila, en lugar de heurísticas por posición.
"""

import os
import re
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Optional

MESES = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6, "JULIO": 7,
    "AGOSTO": 8, "SEPTIEMBRE": 9, "SETIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12,
}

_CLAVES_CI = ("CEDULA DE IDENTIDAD", "CI", "C.I.", "DOC_IDENTIDAD/CI", "CI_ESTUDIANTE", "IDNUMBER", "ID NUMBER")
_CLAVES_NOMBRE_COMPLETO = ("NOMBRE COMPLETO", "NOMBRES Y APELLIDOS", "APELLIDOS Y NOMBRES", "ESTUDIANTE", "ALUMNO")
_CLAVES_NOTA = ("GRADE/100.00", "GRADE/100", "NOTA FINAL", "NOTA_FINAL", "CALIFICACION FINAL", "CALIF_FINAL", "FINALGRADE", "FINAL_GRADE",
                "PROMEDIO FINAL", "PROMEDIO", "NOTA", "CALIFICACION", "PUNTAJE")
# Cobranzas: la fecha de pago más reciente; si no, la primera factura o el inicio del programa
_CLAVES_FECHA_FINANCIERA = ("FECHA ULTIMA FACTURA", "FECHA DE PAGO", "FECHA PAGO", "FECHA DE VENCIMIENTO",
                            "FECHA VENCIMIENTO", "FECHA DE LA PRIMERA FACTURA", "FECHA INICIO DIPLOMADO")
_CLAVES_FECHA_ACADEMICA = ("FECHA", "FECHA EVALUACION", "FECHA DE EVALUACION", "FECHA ASENTAMIENTO",
                           "FECHA DE CIERRE", "FECHA FIN", "MARCA TEMPORAL", "FECHA DE ENVIO", "FINALIZADO",
                           "COMPLETADO", "COMENZADO EL")
_CLAVES_MES = ("MES INICIO", "MES INICO", "MES")
_CLAVES_ANIO = ("ANO INICIO", "ANO INCIO", "ANO", "GESTION")
# Moodle no trae la fecha del curso: la única es la de exportación del reporte, que se toma como fecha de corte
_CLAVE_DESCARGA_MOODLE = "LAST DOWNLOADED FROM THIS COURSE"
_RE_MODULO_N = re.compile(r"^MODULO (\d{1,2})$")
_RE_FECHA_LARGA = re.compile(r"(\d{1,2}) DE ([A-Z]+) DE (\d{4})")
# Google Forms escribe la cédula como 'CI-4892019' / 'ci 4892019' / 'C.I. 4892019': el prefijo no es parte del número
_RE_PREFIJO_CI = re.compile(r"^\s*c\.?\s*i\.?\s*[-:]?\s*(?=\d)", re.IGNORECASE)
# EJECUTADO VS META: una fila por categoría y mes, con columnas EJECUTADO <año> y META POR CATEGORIA <año>
_RE_EJECUTADO_ANIO = re.compile(r"^EJECUTADO (\d{4})$")
_RE_META_ANIO = re.compile(r"^META POR CATEGORIA (\d{4})$")
_RE_META_GENERICA_ANIO = re.compile(r"^META (\d{4})$")
# Columna que dice a qué serie pertenece la fila: CATEGORIA en EJECUTADO VS META, TIPO DE INGRESO en BD Egresos
_CLAVES_CATEGORIA_FIN = ("CATEGORIA", "TIPO DE INGRESO", "TIPO INGRESO", "CATEGORIA FINANCIERA", "SERIE")


def normalizar_encabezado(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.upper().split())


def campos_por_encabezado(celdas: List[str]) -> Dict[str, str]:
    """{ENCABEZADO normalizado: valor} de las celdas 'ENCABEZADO: valor' (la primera aparición gana)."""
    campos: Dict[str, str] = {}
    for c in celdas:
        hdr, sep, val = c.partition(": ")
        val = val.strip()
        if sep and val and val.lower() != "nan":
            campos.setdefault(normalizar_encabezado(hdr), val)
    return campos


def es_encabezado_metadato_pos(encabezado: str) -> bool:
    """'POS - ACTAS', 'POS - MODULO', 'POS-CI', 'N° POS'…: identifican programa, nunca al estudiante."""
    h = normalizar_encabezado(encabezado)
    return h.startswith("POS") or h.endswith(" POS") or h == "POS"


def _primero(campos: Dict[str, str], claves) -> Optional[str]:
    return next((campos[k] for k in claves if campos.get(k)), None)


def _a_float(valor: Optional[str]) -> Optional[float]:
    """Monto o número de la celda ('Bs1.171.260' -> 1171260.0); ver pipeline.normalization.montos."""
    from pipeline.normalization.montos import parsear_monto
    return parsear_monto(valor)


def parsear_fecha(valor: Optional[Any]) -> Optional[date]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    # Moodle/Forms en español: 'miércoles, 20 de noviembre de 2024, 5:38' (se ignoran el día y la hora)
    m = _RE_FECHA_LARGA.search(normalizar_encabezado(texto))
    if m and m.group(2) in MESES:
        try:
            return date(int(m.group(3)), MESES[m.group(2)], int(m.group(1)))
        except ValueError:
            return None
    return None


def _mes(valor: Optional[str]) -> Optional[int]:
    if not valor:
        return None
    v = normalizar_encabezado(valor)
    if v in MESES:
        return MESES[v]
    n = _a_float(v)
    return int(n) if n is not None and 1 <= n <= 12 else None


def fecha_de_fila(campos: Dict[str, str], categoria: str) -> Optional[date]:
    """
    Fecha del hecho. Cobranzas: fecha de pago/vencimiento. Actas: fecha del acta o, si solo hay
    mes y gestión (MES INICIO / AÑO INICIO), el primer día de ese mes. None si la fila no trae fecha.
    """
    claves = _CLAVES_FECHA_FINANCIERA if categoria == "financiero" else _CLAVES_FECHA_ACADEMICA
    for k in claves:
        f = parsear_fecha(campos.get(k))
        if f:
            return f
    anio = _a_float(_primero(campos, _CLAVES_ANIO))
    mes = _mes(_primero(campos, _CLAVES_MES))
    if anio and 2000 <= anio <= 2100 and mes:
        return date(int(anio), mes, 1)
    return fecha_corte_moodle(campos) if categoria != "financiero" else None


def fecha_corte_moodle(campos: Dict[str, str]) -> Optional[date]:
    """
    Fecha de corte de un reporte de Moodle: MOODLE_FECHA_CORTE (AAAA-MM-DD) si está configurada; si no, la fecha
    de descarga de la fila ('Last downloaded from this course'). None si la fila no es de Moodle.
    """
    if _CLAVE_DESCARGA_MOODLE not in campos and not (campos.get("FIRST NAME") and campos.get("COURSE")):
        return None
    return parsear_fecha(os.getenv("MOODLE_FECHA_CORTE", "").strip() or None) or parsear_fecha(campos.get(_CLAVE_DESCARGA_MOODLE))


def estudiante_de_fila(campos: Dict[str, str]) -> Optional[Dict[str, Any]]:
    ci_raw = _primero(campos, _CLAVES_CI)
    ci = "".join(ch for ch in _RE_PREFIJO_CI.sub("", ci_raw) if ch.isalnum()) if ci_raw else None
    nombre = _primero(campos, _CLAVES_NOMBRE_COMPLETO)
    if not nombre and campos.get("FIRST NAME"):  # Moodle
        nombre = " ".join(p for p in (campos.get("FIRST NAME"), campos.get("SURNAME")) if p)
    if not nombre and campos.get("NOMBRES"):
        partes = [
            campos.get("NOMBRES"),
            campos.get("PATERNO") or campos.get("APELLIDO PATERNO"),
            campos.get("MATERNO") or campos.get("APELLIDO MATERNO"),
        ]
        nombre = " ".join(p for p in partes if p)
    if not ci and not nombre:
        return None
    return {
        "valor_extraido": nombre or ci,
        "fk_resolucion": {"ci": ci, "fk_estado": "A" if ci else "B", "nombre_resuelto": nombre or f"Estudiante CI {ci}"},
    }


def _pos(campos: Dict[str, str]) -> Optional[str]:
    curso = campos.get("COURSE") or campos.get("CURSO") or ""
    m = re.match(r"^POS-?(\d+)", curso.strip().upper())  # Moodle: 'POS-5376 - Maestría en Ciberseguridad'
    if m:
        return f"POS-{m.group(1)}"
    for k, v in campos.items():
        if k.startswith("POS") and k not in ("POS-CI", "POS + IBP"):
            digitos = re.sub(r"^POS-?", "", v.strip().upper())
            return f"POS-{digitos}" if digitos else None
    return None


def estados_de_fila(campos: Dict[str, str]) -> Dict[str, Any]:
    """
    Estados del acta tal como vienen en la fuente (ESTADO ACADEMICO / ESTADO TUTORIA / ESTADO ARCA),
    llevados a su nombre de catálogo y validados contra las combinaciones de CRITERIOS.
    'estado_revision' es True si algún estado no está en catálogo o la combinación no es válida.
    """
    from pipeline.config import ESTADOS_ACADEMICOS_VALIDOS, ESTADOS_TUTORIA_VALIDOS, ESTADOS_ARCA_VALIDOS
    from pipeline.normalization.quality_rules import canonizar_estado, validar_combinacion_estados

    aca, ok_aca = canonizar_estado(campos.get("ESTADO ACADEMICO"), ESTADOS_ACADEMICOS_VALIDOS)
    tut, ok_tut = canonizar_estado(
        campos.get("ESTADO TUTORIA") or campos.get("ESTADO REPROBADO"), ESTADOS_TUTORIA_VALIDOS
    )
    arca, ok_arca = canonizar_estado(campos.get("ESTADO ARCA"), ESTADOS_ARCA_VALIDOS)
    motivos = [f"ESTADO_FUERA_DE_CATALOGO: '{v}'" for v, ok in ((aca, ok_aca), (tut, ok_tut), (arca, ok_arca)) if not ok]
    if not motivos:
        valida, motivo = validar_combinacion_estados(aca, tut, arca)
        if not valida:
            motivos.append(motivo)
    return {
        "estado_academico": aca,
        "estado_tutoria": tut,
        "estado_arca": arca,
        "estado_motivo": "; ".join(motivos) or None,
        "estado_revision": bool(motivos),
    }


def registros_academicos(campos: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Resoluciones académicas de una fila. Acta ARCA (columnas MÓDULO 1..12): un registro por módulo con
    nota, del programa POS de la fila. Otras fuentes: un registro con la columna de nota final.
    Escala: si todas las notas de la fila son <= 10 se trata como escala 10 y se lleva a base 100.
    Cada registro trae 'requiere_revision' si falta nota o fecha.
    """
    estudiante = estudiante_de_fila(campos)
    if estudiante is None:
        return []  # hoja sin estudiante (MODULOS, IBP, catálogos): no es un hecho académico
    fecha = fecha_de_fila(campos, "academico")
    pos = _pos(campos)
    estados = estados_de_fila(campos)
    revision_estado = estados.pop("estado_revision")

    notas_modulo = {}
    for k, v in campos.items():
        m = _RE_MODULO_N.match(k)
        if m:
            notas_modulo[int(m.group(1))] = _a_float(v)

    # Un valor fuera de 0-100 en MÓDULO N no es una nota (en ARCA hay CIs pegados en esas columnas):
    # se descarta y los hechos de la fila van a revisión
    fuera_de_rango = any(x is not None and not (0.0 <= x <= 100.0) for x in notas_modulo.values())
    notas_modulo = {n: (x if x is not None and 0.0 <= x <= 100.0 else None) for n, x in notas_modulo.items()}

    if notas_modulo and not any(x is not None for x in notas_modulo.values()):
        # Acta sin ninguna nota: un hecho del programa con nota null, a revisión
        return [{
            "estudiante": estudiante,
            "modulo": {"valor_extraido": f"{pos} · Sin módulo con nota"} if pos else None,
            "programa": {"valor_extraido": pos, "metadata": {"pos_canonico": f"{pos}-M00"}} if pos else None,
            "nota_final": None,
            "nota_ya_normalizada": True,
            "fecha": fecha,
            **estados,
            "requiere_revision": True,
        }]

    if notas_modulo:
        con_nota = {n: x for n, x in notas_modulo.items() if x is not None}
        escala_10 = bool(con_nota) and max(con_nota.values()) <= 10.0
        registros = []
        for n in sorted(con_nota):
            nota = round(con_nota[n] * 10.0, 2) if escala_10 else round(con_nota[n], 2)
            codigo = f"{pos}-M{n:02d}" if pos else None
            registros.append({
                "estudiante": estudiante,
                "modulo": {"valor_extraido": f"{pos or 'POS-SIN-CODIGO'} · Módulo {n}"},
                "programa": {"valor_extraido": pos, "metadata": {"pos_canonico": codigo}} if pos else None,
                "nota_final": nota,
                "nota_ya_normalizada": True,
                "fecha": fecha,
                **estados,
                "requiere_revision": fecha is None or fuera_de_rango or revision_estado,
            })
        return registros

    nota_raw = _a_float(_primero(campos, _CLAVES_NOTA))
    nota = None
    if nota_raw is not None:
        nota = round(nota_raw * 10.0, 2) if 0.0 <= nota_raw <= 10.0 else round(nota_raw, 2)
    modulo = campos.get("MODULO") or campos.get("CURSO") or campos.get("MATERIA") or campos.get("COURSE")
    return [{
        "estudiante": estudiante,
        "modulo": {"valor_extraido": modulo} if modulo else None,
        "programa": {"valor_extraido": pos} if pos else None,
        "nota_final": nota,
        "nota_ya_normalizada": True,
        "fecha": fecha,
        **estados,
        "requiere_revision": nota is None or fecha is None or revision_estado,
    }]


def categoria_rentabilidad(valor: Optional[str]) -> Optional[str]:
    """CATEGORIA de EJECUTADO VS META -> categoría financiera (mismos nombres que seed_historical_facts)."""
    v = normalizar_encabezado(valor or "")
    if "PROGRAMA" in v:
        return "PROGRAMAS"
    if "TECHO" in v or "CERRADO" in v:
        return "TECHOS_CERRADOS"
    return None


def registros_rentabilidad(campos: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Una fila mensual de EJECUTADO VS META trae varios años (EJECUTADO 2023..2026, META POR CATEGORIA 2024..2026).
    Devuelve un registro por año con dato, con la fecha del primer día de ese mes: así cada fila conserva su
    categoría y su mes en fact_rentabilidad (clave id_categoria + id_tiempo) en vez de colapsar en una sola.
    """
    categoria = next(
        (c for c in (categoria_rentabilidad(campos.get(k)) for k in _CLAVES_CATEGORIA_FIN) if c), None
    )
    mes = _mes(campos.get("MES NUMERICO")) or _mes(campos.get("MES"))
    if not categoria or not mes:
        return []  # sin categoría: hoja de totales (GESTIONES, acumulados), derivada de las categorías
    por_anio: Dict[int, Dict[str, Optional[float]]] = {}
    metas_genericas: Dict[int, Optional[float]] = {}
    for k, v in campos.items():
        m_ejec, m_meta = _RE_EJECUTADO_ANIO.match(k), _RE_META_ANIO.match(k)
        if m_ejec or m_meta:
            anio = int((m_ejec or m_meta).group(1))
            por_anio.setdefault(anio, {"monto_ejecutado": None, "monto_meta": None})
            por_anio[anio]["monto_ejecutado" if m_ejec else "monto_meta"] = _a_float(v)
            continue
        m_gen = _RE_META_GENERICA_ANIO.match(k)
        if m_gen:
            metas_genericas[int(m_gen.group(1))] = _a_float(v)
    # 'META 2025' solo cuenta si la fila no trae 'META POR CATEGORIA 2025' (en EJECUTADO VS META son la misma
    # serie; 'META 2026' allí es otra cifra y no debe pisarla)
    for anio, meta in metas_genericas.items():
        montos = por_anio.setdefault(anio, {"monto_ejecutado": None, "monto_meta": None})
        if montos["monto_meta"] is None:
            montos["monto_meta"] = meta
    return [
        {"categoria_financiera": categoria, "fecha": date(anio, mes, 1), **montos}
        for anio, montos in sorted(por_anio.items())
        if montos["monto_ejecutado"] is not None or montos["monto_meta"] is not None
    ]


_RE_POS_EXACTO = re.compile(r"^\s*POS[\s-]?(\d{3,5})\s*$", re.IGNORECASE)
_CLAVES_NRO_POS = ("NRO POS", "N° POS", "Nº POS", "NUMERO POS", "POS", "COD POS", "CODIGO POS")
_CLAVES_NOMBRE_PROGRAMA = ("NOMBRE DEL PROGRAMA", "NOMBRE PROGRAMA", "PROGRAMA")
_TOLERANCIA_RENTABILIDAD_BS = 1.0


def _pos_de_valores(campos: Dict[str, str]) -> Optional[str]:
    """POS de la fila: una celda que es exactamente 'POS-NNNN', o una columna de número de POS ('NRO POS: 4403')."""
    for v in campos.values():
        m = _RE_POS_EXACTO.match(str(v or ""))
        if m:
            return f"POS-{m.group(1)}"
    for k in _CLAVES_NRO_POS:
        digitos = re.sub(r"\D", "", str(campos.get(k) or ""))
        if 3 <= len(digitos) <= 5:
            return f"POS-{digitos}"
    return None


def registros_costo_programa(campos: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Fila de costos de un programa (egreso, ingreso, rentabilidad por POS). Las columnas se reconocen por su
    concepto (services.conceptos_financieros: reglas + sinónimos de cat_historico_equivalencia), no por su nombre
    exacto; las de moneda secundaria (DOLARES) son derivadas y se ignoran.
    Valida rentabilidad = ingreso - egreso real; si no viene, la calcula. Lista vacía si no hay POS o montos.
    """
    from services.conceptos_financieros import concepto_de_cabecera

    pos = _pos_de_valores(campos)
    if not pos:
        return []
    montos: Dict[str, Optional[float]] = {}
    for k, v in campos.items():
        concepto = concepto_de_cabecera(k)
        if concepto and concepto not in montos:
            montos[concepto] = _a_float(v)
    if not any(x is not None for x in montos.values()):
        return []

    ingreso, egreso = montos.get("INGRESO"), montos.get("EGRESO_REAL")
    rentabilidad = montos.get("RENTABILIDAD")
    motivo = None
    if ingreso is not None and egreso is not None:
        calculada = round(ingreso - egreso, 2)
        if rentabilidad is None:
            rentabilidad = calculada
        elif abs(rentabilidad - calculada) > _TOLERANCIA_RENTABILIDAD_BS:
            motivo = f"RENTABILIDAD_INCOHERENTE: {rentabilidad} != ingreso {ingreso} - egreso {egreso} = {calculada}"

    nombre = next(
        (campos[k] for k in _CLAVES_NOMBRE_PROGRAMA if campos.get(k) and not _RE_POS_EXACTO.match(campos[k])), None
    )
    return [{
        "costo_programa": True,
        "programa": {"valor_extraido": nombre or pos, "metadata": {"pos_canonico": pos}},
        "modulo": {"valor_extraido": nombre or pos},
        "egreso_anterior": montos.get("EGRESO_ANTERIOR"),
        "egreso_real": egreso,
        "ingreso": ingreso,
        "rentabilidad": rentabilidad,
        "motivo_costo": motivo,
        "requiere_revision": motivo is not None,
    }]


_CLAVES_ENTIDAD_PROGRAMA = ("NOMBRE DEL PROGRAMA", "NOMBRE PROGRAMA", "PROGRAMA", "CURSO", "COURSE", "MODULO", "MATERIA")


# ── Evaluación docente / satisfacción ────────────────────────────────────────
# Columnas de identidad de una encuesta: nunca son preguntas
_CLAVES_IDENTIDAD_ENCUESTA = (
    "NOMBRE", "NOMBRES", "APELLIDO", "APELLIDOS", "APELLIDO(S)", "PATERNO", "MATERNO", "NOMBRE COMPLETO",
    "ESTUDIANTE", "ALUMNO", "PARTICIPANTE", "CORREO", "CORREO ELECTRONICO", "EMAIL", "E-MAIL",
    "USUARIO", "PROGRAMA", "NOMBRE DEL PROGRAMA", "CURSO", "COURSE", "MODULO", "N° MODULO", "NRO MODULO",
    "MATERIA", "DOCENTE", "PROFESOR", "FACILITADOR", "TUTOR", "GRUPO", "SEDE", "CIUDAD", "N°", "Nº", "NRO",
    "ID", "RESPUESTA", "INSTITUCION",
) + _CLAVES_CI + _CLAVES_FECHA_ACADEMICA
# '5/Totalmente de acuerdo', '3 - Adecuada', '8', '4,5'
_RE_LIKERT = re.compile(r"^\s*(\d{1,2}(?:[.,]\d+)?)\s*(?:[/\-–:.)]\s*\D.*)?$")
_RE_ANONIMO = re.compile(r"ANONIM|SIN NOMBRE|^PERSONA \d+$")
_RE_POS_VALOR = re.compile(r"POS[\s-]?(\d{3,5})")
_RE_NRO_MODULO = re.compile(r"(\d{1,2})")
# Comentarios sin contenido: no se guardan. 'Todo conforme' sí es una opinión y se conserva.
_COMENTARIOS_VACIOS = {"", ".", "-", "_", "NINGUNO", "NINGUNA", "NADA", "NO", "N/A", "NA", "SIN COMENTARIOS",
                       "NINGUN COMENTARIO", "NO HAY", "NO HAY DATOS", "S/C", "X"}
_PALABRAS_INSTITUCIONAL = ("PLATAFORMA", "MOODLE", "ZOOM", "TEAMS", "AULA VIRTUAL", "ATENCION", "ADMINISTRATIV",
                           "COORDINACION", "COORDINADOR", "INSTITUCION", "UNIFRANZ", "SOPORTE", "SERVICIO",
                           "INSCRIPCION", "PAGO", "CERTIFICA", "INFRAESTRUCTURA", "ORGANIZACION", "ASESOR")
_PALABRAS_NPS = ("RECOMENDAR", "RECOMENDARIA", "RECOMENDACION", "DEL 0 AL 10", "DEL 1 AL 10", "0 A 10", "1 A 10")


def _es_columna_identidad(encabezado: str) -> bool:
    return encabezado in _CLAVES_IDENTIDAD_ENCUESTA or encabezado.startswith(("CORREO", "DIRECCION DE CORREO", "POS"))


def _parece_pregunta(encabezado: str) -> bool:
    return "?" in encabezado or "¿" in encabezado or len(encabezado) >= 30


def tipo_pregunta(encabezado: str) -> str:
    """NPS (recomendación 0-10), INSTITUCIONAL (plataforma, atención, gestión) o DOCENTE."""
    if any(p in encabezado for p in _PALABRAS_NPS):
        return "NPS"
    if "DOCENTE" in encabezado or "PROFESOR" in encabezado or "FACILITADOR" in encabezado:
        return "DOCENTE"
    if any(p in encabezado for p in _PALABRAS_INSTITUCIONAL):
        return "INSTITUCIONAL"
    return "DOCENTE"


def _escala(encabezado: str, valor: float, tipo: str) -> int:
    """Escala de la pregunta: 10 si es NPS, si la cabecera la menciona o si el valor pasa de 5; si no, 5."""
    if tipo == "NPS" or "10" in encabezado or valor > 5:
        return 10
    return 5


def _estudiante_encuesta(campos: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Estudiante de la encuesta, o None si es anónima o no trae identidad."""
    est = estudiante_de_fila(campos)
    if est is None and campos.get("NOMBRE"):
        apellido = campos.get("APELLIDO(S)") or campos.get("APELLIDOS") or campos.get("APELLIDO") or ""
        nombre = " ".join(p for p in (campos.get("NOMBRE"), apellido) if p)
        est = {"valor_extraido": nombre, "fk_resolucion": {"ci": None, "fk_estado": "B", "nombre_resuelto": nombre}}
    if est and _RE_ANONIMO.search(normalizar_encabezado(est["valor_extraido"])):
        return None
    return est


def registros_evaluacion(campos: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Una fila de encuesta -> un registro por pregunta (fact_evaluacion_docente: una fila por respuesta).
    - Pregunta con puntaje ('5/Totalmente de acuerdo', '8'): puntuacion + escala_max (5 o 10).
    - Pregunta abierta (cabecera tipo pregunta, valor de texto): comentario, puntuacion NULL.
    - tipo_pregunta DOCENTE / INSTITUCIONAL / NPS: solo DOCENTE se atribuye al docente.
    - Anónima ('ENTRADA ANONIMA - PERSONA 5'): sin estudiante, nunca se crea uno ficticio.
    - clave_respuesta: hash estable de la fila + pregunta, para que volver a subir el archivo no duplique.
    Lista vacía si la fila no tiene respuestas (listas de comentarios de una hoja de gráficos, totales).
    """
    import hashlib

    estudiante = _estudiante_encuesta(campos)
    texto_programa = " ".join(campos.get(k) or "" for k in ("PROGRAMA", "NOMBRE DEL PROGRAMA", "CURSO", "COURSE"))
    m_pos = _RE_POS_VALOR.search(texto_programa.upper())
    pos = f"POS-{m_pos.group(1)}" if m_pos else _pos(campos)
    m_mod = _RE_NRO_MODULO.search(campos.get("MODULO") or campos.get("N° MODULO") or campos.get("NRO MODULO") or "")
    nro_modulo = int(m_mod.group(1)) if m_mod else None
    docente = next((campos[k] for k in ("DOCENTE", "PROFESOR", "FACILITADOR", "TUTOR") if campos.get(k)), None)
    fecha = fecha_de_fila(campos, "academico")

    respuestas = []
    for enc, valor in campos.items():
        if _es_columna_identidad(enc) or valor is None:
            continue
        v = str(valor).strip()
        m = _RE_LIKERT.match(v)
        # Un número suelto solo es respuesta bajo una cabecera de pregunta (no 'EDAD', 'HORAS', 'GESTION')
        if m and (_parece_pregunta(enc) or not v.replace(",", ".").replace(".", "", 1).isdigit()):
            num = float(m.group(1).replace(",", "."))
            tipo = tipo_pregunta(enc)
            esc = _escala(enc, num, tipo)
            if 0.0 <= num <= esc:
                respuestas.append((enc, num, esc, tipo, None))
            continue
        if _parece_pregunta(enc) and normalizar_encabezado(v) not in _COMENTARIOS_VACIOS:
            respuestas.append((enc, None, None, tipo_pregunta(enc), v[:1000]))

    # Sin puntajes ni identidad: lista suelta de comentarios de una hoja de gráficos, o fila de resumen
    if not respuestas or (not any(r[1] is not None for r in respuestas) and not (pos or estudiante)):
        return []

    if pos and nro_modulo:
        programa = {"valor_extraido": pos, "metadata": {"pos_canonico": f"{pos}-M{nro_modulo:02d}"}}
        modulo = {"valor_extraido": f"{pos} · Módulo {nro_modulo}"}
    elif pos:
        programa = {"valor_extraido": pos, "metadata": {"pos_canonico": pos}}
        modulo = {"valor_extraido": campos.get("NOMBRE DEL PROGRAMA") or pos}
    else:
        programa = None
        nombre_mod = campos.get("MODULO") or campos.get("CURSO") or campos.get("PROGRAMA")
        modulo = {"valor_extraido": nombre_mod} if nombre_mod else None

    fila_canonica = "|".join(f"{k}={campos[k]}" for k in sorted(campos))
    return [{
        "estudiante": estudiante,
        "docente": {"valor_extraido": docente} if docente else None,
        "programa": programa,
        "modulo": modulo,
        "fecha": fecha,
        "pregunta_bloque": enc[:500],
        "tipo_pregunta": tipo,
        "puntuacion": num,
        "escala_max": esc,
        "comentario": coment,
        "clave_respuesta": hashlib.sha1(f"{fila_canonica}||{enc}".encode("utf-8")).hexdigest(),
        "requiere_revision": fecha is None,
    } for enc, num, esc, tipo, coment in respuestas]


def motivo_fila_sin_entidad(campos: Dict[str, str], categoria: str) -> Optional[str]:
    """
    Motivo por el que una línea no puede producir un hecho (se descarta como ruido, no va a revisión), o None.
    - academico: sin estudiante (hojas MODULOS, IBP, catálogos): registros_academicos no generaría hechos.
    - rentabilidad: fila sin categoría y mes reconocibles.
    - financiero: sin estudiante (hoja 'Resumen por Programa'): el hecho financiero es por estudiante, y sin él el
      extractor tomaba otra celda como nombre ('OBSERVACIÓN CARTERA: EN PROCESO DE COBRO').
    - admisión / marketing: sin estudiante ni programa (p. ej. la hoja de estados académicos
      'Estado académico: Aprobado | Estado ARCA: Titulado', que es un catálogo de combinaciones).
    """
    if not campos:
        return "FILA_SIN_CABECERAS"
    if categoria == "rentabilidad":
        if registros_rentabilidad(campos) or registros_costo_programa(campos):
            return None
        return "FILA_AGREGADA_SIN_CATEGORIA_MES"
    if categoria == "evaluacion_docente":
        return None if registros_evaluacion(campos) else "FILA_EVALUACION_SIN_RESPUESTAS"
    if estudiante_de_fila(campos) is not None:
        return None
    if categoria == "academico":
        return "FILA_ACADEMICA_SIN_ESTUDIANTE"
    if _pos(campos) or any(campos.get(k) for k in _CLAVES_ENTIDAD_PROGRAMA):
        return "FILA_FINANCIERA_SIN_ESTUDIANTE" if categoria == "financiero" else None
    return "FILA_SIN_ENTIDAD"
