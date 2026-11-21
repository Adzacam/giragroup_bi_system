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
from functools import lru_cache
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
_RE_FECHA_LARGA = re.compile(r"(\d{1,2}) DE ([A-Z]+) DE (\d{4})")
# Google Forms escribe la cédula como 'CI-4892019' / 'ci 4892019' / 'C.I. 4892019': el prefijo no es parte del número
_RE_PREFIJO_CI = re.compile(r"^\s*c\.?\s*i\.?\s*[-:]?\s*(?=\d)", re.IGNORECASE)
# EJECUTADO VS META: una fila por categoría y mes, con columnas EJECUTADO <año> y META POR CATEGORIA <año>
_RE_EJECUTADO_ANIO = re.compile(r"^EJECUTADO (\d{4})$")
_RE_META_ANIO = re.compile(r"^META POR CATEGORIA (\d{4})$")
_RE_META_GENERICA_ANIO = re.compile(r"^META (\d{4})$")
# Columna que dice a qué serie pertenece la fila: CATEGORIA en EJECUTADO VS META, TIPO DE INGRESO en BD Egresos
_CLAVES_CATEGORIA_FIN = ("CATEGORIA", "TIPO DE INGRESO", "TIPO INGRESO", "CATEGORIA FINANCIERA", "SERIE")


@lru_cache(maxsize=4096)
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


def metricas_captacion(campos: Dict[str, str]) -> Dict[str, int]:
    """Contadores explícitos; no deduce interesados a partir de personas o inscripciones.
    FU-L3: las cabeceras salen de los sinónimos del catálogo (services.captacion_canonica), no de una lista fija."""
    from services.captacion_canonica import metricas_enteras
    return metricas_enteras(campos)


ANIO_MIN, ANIO_MAX = 2000, 2100  # rango de gestiones de negocio


def parsear_fecha(valor: Optional[Any]) -> Optional[date]:
    """
    Fecha de negocio de la celda, o None. Fuera de ANIO_MIN..ANIO_MAX se descarta: en las planillas
    aparecen números de factura tecleados en columnas con formato fecha (10554 -> 1928-11-22) o
    años mal escritos (205), que antes creaban gestiones falsas en el CMI.
    """
    f = _parsear_fecha_cruda(valor)
    return f if f and ANIO_MIN <= f.year <= ANIO_MAX else None


def _parsear_fecha_cruda(valor: Optional[Any]) -> Optional[date]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    # FU-L3: «2025-01-10 09:17:19.521000» (milisegundos de una marca temporal) también es una fecha válida
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
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
    if anio and ANIO_MIN <= anio <= ANIO_MAX and mes:
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
    from services import acta_canonica   # FU-L4: CI por sinónimos del catálogo y complemento separado del número
    ci_raw = _primero(campos, _CLAVES_CI) or acta_canonica.valor_de_campo(campos, "ci")
    ci_num, ci_comp = acta_canonica.separar_ci(ci_raw)
    # Con número al inicio ('4892019-1C', '4892019 CBBA', '4892019.0') se separan número y complemento: antes el cargador
    # tomaba los dígitos de '48920191C' como número y el CI resolvía a otro estudiante. Sin número al inicio (CI extranjera,
    # relleno) se conserva la lectura anterior.
    ci = (ci_num + (ci_comp or "")) if ci_num else ("".join(ch for ch in _RE_PREFIJO_CI.sub("", ci_raw) if ch.isalnum()) if ci_raw else None)
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
    if nombre:
        nombre = " ".join(nombre.split())   # espacios dobles de la planilla
    if not ci and not nombre:
        return None
    fk = {"ci": ci, "fk_estado": "A" if ci else "B", "nombre_resuelto": nombre or f"Estudiante CI {ci}"}
    if ci_num:   # número y complemento explícitos: la identidad se resuelve por el número (el CI escrito conserva su extensión)
        fk["ci_numero"] = ci_num
        fk["ci_complemento"] = ci_comp
    return {"valor_extraido": nombre or ci, "fk_resolucion": fk}


def _pos(campos: Dict[str, str]) -> Optional[str]:
    curso = campos.get("COURSE") or campos.get("CURSO") or ""
    m = re.match(r"^POS-?(\d+)", curso.strip().upper())  # Moodle: 'POS-5376 - Maestría en Ciberseguridad'
    if m:
        return f"POS-{m.group(1)}"
    for k, v in campos.items():
        if k.startswith("POS") and k not in ("POS-CI", "POS + IBP"):
            digitos = re.sub(r"\.0+$", "", re.sub(r"^POS-?", "", v.strip().upper()))  # '4244.0' de Excel
            return f"POS-{digitos}" if digitos else None
    return None


def estados_de_fila(campos: Dict[str, str]) -> Dict[str, Any]:
    """
    Estados del acta tal como vienen en la fuente, llevados a su nombre de catálogo y validados contra las combinaciones
    de CRITERIOS. Las columnas se reconocen por sinónimos del catálogo de fuentes (campos canónicos estado_academico,
    estado_tutoria y estado_arca; FU-L4), no por nombre de columna. Mayúsculas, acentos y espacios no cambian el estado.
    'estado_revision' es True si algún estado no está en catálogo o la combinación no es válida; un estado desconocido
    no se descarta: se guarda como vino y 'avisos_estado' lo registra como VALOR_FUERA_DE_CATALOGO.
    """
    from services import acta_canonica
    from services.catalogo_estados import reglas_estado
    from pipeline.normalization.quality_rules import canonizar_estado, validar_combinacion_estados

    reglas = reglas_estado()  # cat_estado_* y cat_combinacion_estado; config solo si el catálogo no responde
    aca, ok_aca = canonizar_estado(acta_canonica.valor_de_campo(campos, "estado_academico"), reglas.academicos)
    tut, ok_tut = canonizar_estado(acta_canonica.valor_de_campo(campos, "estado_tutoria"), reglas.tutoria)
    arca, ok_arca = canonizar_estado(acta_canonica.valor_de_campo(campos, "estado_arca"), reglas.arca)
    motivos = [f"ESTADO_FUERA_DE_CATALOGO: '{v}'" for v, ok in ((aca, ok_aca), (tut, ok_tut), (arca, ok_arca)) if not ok]
    avisos = [(acta_canonica.motivo("valor_fuera_de_catalogo", "VALOR_FUERA_DE_CATALOGO"), campo, str(v)[:40])
              for campo, v, ok in (("estado_academico", aca, ok_aca), ("estado_tutoria", tut, ok_tut), ("estado_arca", arca, ok_arca))
              if not ok]
    if not motivos:
        valida, motivo = validar_combinacion_estados(aca, tut, arca, reglas.combinaciones)
        if not valida:
            motivos.append(motivo)
    return {
        "estado_academico": aca,
        "estado_tutoria": tut,
        "estado_arca": arca,
        "estado_motivo": "; ".join(motivos) or None,
        "estado_revision": bool(motivos),
        "avisos_estado": avisos,
    }


NOTA_MINIMA_MODULO = 51.0  # por debajo, un módulo está reprobado sin discusión (base 100)
_FACTOR_ESCALA_EXPLICITA = {"DECIMAL_10": 10.0, "VIGESIMAL_20": 5.0}
MIN_FILAS_ESCALA = 3  # estudiantes con nota necesarios para deducir la escala de un programa


def factor_escala_fila(notas: List[float]) -> float:
    """
    Factor para llevar notas a base 100 según su máximo: <= 10 escala 10 (x10), <= 20 escala 20 (x5, hay
    programas del ARCA calificados sobre 20), si no base 100. Todo en 0 queda en base 100.
    Se aplica al máximo de un programa en el archivo (factores_escala_por_programa); una fila suelta sólo
    cuando no hay archivo de contexto (resolución individual en la bandeja).
    """
    tope = max(notas) if notas else 0.0
    if 0.0 < tope <= 10.0:
        return 10.0
    if 10.0 < tope <= 20.0:
        return 5.0
    return 1.0


def _notas_modulo_validas(campos: Dict[str, str]) -> List[float]:
    from services import acta_canonica
    return acta_canonica.notas_numericas(campos)   # columnas de nota por sinónimos del catálogo (FU-L4), valores de 0 a 100


def factores_escala_por_programa(filas: List[Dict[str, str]], tipo_escala: Optional[str] = None) -> Dict[Optional[str], float]:
    """
    Escala de cada programa (POS) del archivo: un mismo acta mezcla programas sobre 20 y sobre 100. Si el
    archivo declara DECIMAL_10 o VIGESIMAL_20, manda para todos; con CENTESIMAL_100 (el valor por defecto del
    selector) o sin escala, se deduce por programa con la nota más alta de todas sus filas. Así un estudiante
    con notas bajas en un programa sobre 100 no se confunde con uno sobre 20, como pasaba al decidir por fila.
    """
    explicito = _FACTOR_ESCALA_EXPLICITA.get((tipo_escala or "").upper().strip())
    maximos: Dict[Optional[str], float] = {}
    con_nota: Dict[Optional[str], int] = {}
    for campos in filas:
        notas = _notas_modulo_validas(campos)
        if notas:
            pos = _pos(campos)
            maximos[pos] = max(maximos.get(pos, 0.0), max(notas))
            con_nota[pos] = con_nota.get(pos, 0) + (max(notas) > 0)
    # Con menos de MIN_FILAS_ESCALA estudiantes con nota no hay evidencia para deducir otra escala (en el ARCA:
    # un 'Reprobado' con 9 y el resto deserción en 0): queda en base 100
    return {pos: explicito or (factor_escala_fila([m]) if con_nota[pos] >= MIN_FILAS_ESCALA else 1.0)
            for pos, m in maximos.items()}


def coherencia_estado_notas(estado_academico: Optional[str], notas: Dict[int, float]) -> Optional[str]:
    """
    Un acta 'Aprobado' con algún módulo claramente reprobado (< NOTA_MINIMA_MODULO, en base 100) es una
    inconsistencia de la fuente: un 0 o un 30 cargado a un estudiante aprobado. Devuelve el motivo, o None.
    Medido sobre el ARCA real: ~210 de 8.660 filas; entre 51 y 69 hay otras ~115 que se dejan pasar porque
    pueden venir de recuperación por tutoría. 'Reprobado' con todas las notas altas no se marca: suele ser
    reprobado por abandono (módulos del programa sin nota), y eso depende de cuántos módulos tiene cada
    programa, que no se ve en una sola fila.
    """
    if not notas or not estado_academico or normalizar_encabezado(estado_academico) != "APROBADO":
        return None
    bajos = {n: x for n, x in sorted(notas.items()) if x < NOTA_MINIMA_MODULO}
    if not bajos:
        return None
    detalle = ", ".join(f"módulo {n} = {x:g}" for n, x in bajos.items())
    return f"APROBADO_CON_MODULO_REPROBADO: {detalle} (< {NOTA_MINIMA_MODULO:g})"


def registros_academicos(campos: Dict[str, str],
                         factores_escala: Optional[Dict[Optional[str], float]] = None) -> List[Dict[str, Any]]:
    """
    Resoluciones académicas de una fila. Acta (una columna de nota por módulo, reconocida por sinónimos del catálogo): un
    registro por módulo con valor, del programa POS de la fila. Otras fuentes: un registro con la columna de nota final.
    Escala: la del programa en el archivo (factores_escala, ver factores_escala_por_programa); sin ella, la de la fila.
    FU-L4 (DA-FU2): cada registro trae `nota_final` (numérica o None) y `resultado` canónico (APROBADO, REPROBADO,
    INASISTENCIA, EXIMIDO, SIN_NOTA o None). Una celda con texto del vocabulario aporta su resultado sin nota; un 0 con estado
    Deserción o Abandono es INASISTENCIA; un número fuera de 0-100 o un texto fuera del catálogo dejan la nota en None y la fila
    a revisión (`avisos_acta` lleva el aviso sin publicar el valor). Cada registro trae 'requiere_revision' si falta nota o fecha.
    """
    from services import acta_canonica as ac

    estudiante = estudiante_de_fila(campos)
    if estudiante is None:
        return []  # hoja sin estudiante (MODULOS, IBP, catálogos): no es un hecho académico
    fecha = fecha_de_fila(campos, "academico")
    pos = _pos(campos)
    estados = estados_de_fila(campos)
    revision_estado = estados.pop("estado_revision")
    avisos_estado = estados.pop("avisos_estado")
    desercion = ac.es_desercion(estados.get("estado_academico"), estados.get("estado_tutoria"))

    celdas = {n: ac.leer_celda(v) for n, v in ac.columnas_modulo(campos).items()}
    celdas = {n: c for n, c in celdas.items() if c.clase != "VACIA"}
    # Un número fuera de 0-100 (en el acta real, un CI pegado) o un texto fuera del vocabulario no es una nota: no genera hecho
    # del módulo (queda NULL), deja la fila en revisión y se avisa agregado y sin el valor
    avisos_anomalas = []
    for n in sorted(celdas):
        if celdas[n].clase == "FUERA_DE_RANGO":
            avisos_anomalas.append((ac.motivo("nota_fuera_de_rango", "NOTA_FUERA_DE_RANGO"), "nota_modulo", "número fuera de 0-100"))
        elif celdas[n].clase == "FUERA_DE_CATALOGO":
            avisos_anomalas.append((ac.motivo("valor_fuera_de_catalogo", "VALOR_FUERA_DE_CATALOGO"), "nota_modulo", "texto fuera del vocabulario"))
    anomalas = list(avisos_anomalas)
    celdas = {n: c for n, c in celdas.items() if c.clase in ("NUMERO", "TEXTO")}
    numericas = {n: c.numero for n, c in celdas.items() if c.clase == "NUMERO"}

    if celdas:
        # Cada programa tiene su propio número de módulos (uno llega al 5, otro al 11): las columnas vacías
        # no son notas faltantes, sólo módulos que ese programa no tiene.
        if factores_escala is not None and pos in factores_escala:
            factor = factores_escala[pos]  # escala del programa en todo el archivo
        else:
            factor = factor_escala_fila(list(numericas.values()))
        motivo_notas = coherencia_estado_notas(
            estados.get("estado_academico"),
            {n: x * factor for n, x in numericas.items() if not (x == 0 and desercion)},
        )
        if motivo_notas:
            estados["estado_motivo"] = "; ".join(m for m in (estados.get("estado_motivo"), motivo_notas) if m)
            revision_estado = True
        registros = []
        for n in sorted(celdas):
            celda = celdas[n]
            avisos: List[Any] = []
            if celda.clase == "NUMERO":
                nota, resultado = ac.resolver_numero(round(celda.numero * factor, 2), desercion)
                if resultado == ac.INASISTENCIA:
                    avisos.append((ac.motivo("cero_inasistencia", "CERO_COMO_INASISTENCIA"), "nota_modulo", "0"))
            else:
                nota, resultado = None, celda.resultado
            codigo = f"{pos}-M{n:02d}" if pos else None
            registros.append({
                "estudiante": estudiante,
                "modulo": {"valor_extraido": f"{pos or 'POS-SIN-CODIGO'} · Módulo {n}"},
                "programa": {"valor_extraido": pos, "metadata": {"pos_canonico": codigo}} if pos else None,
                "nota_final": nota,
                "resultado": resultado,
                "nota_ya_normalizada": True,
                "sin_nota_por_acta": nota is None and resultado is not None,   # nota nula esperada: el acta trae un resultado sin número
                "fecha": fecha,
                **estados,
                "avisos_acta": avisos,
                "requiere_revision": fecha is None or bool(anomalas) or revision_estado,
            })
        registros[0]["avisos_acta"] = registros[0]["avisos_acta"] + avisos_anomalas + avisos_estado
        return registros

    nota_raw = _a_float(_primero(campos, _CLAVES_NOTA))
    nota, resultado = None, None
    if nota_raw is not None:
        nota_100 = round(nota_raw * 10.0, 2) if 0.0 <= nota_raw <= 10.0 else round(nota_raw, 2)
        if 0.0 <= nota_100 <= 100.0:
            nota, resultado = ac.resolver_numero(nota_100, desercion)
        else:
            nota = nota_100   # fuera de 0-100: el cargador la deja en NULL y la fila queda en revisión
    modulo = campos.get("MODULO") or campos.get("CURSO") or campos.get("MATERIA") or campos.get("COURSE")
    return [{
        "estudiante": estudiante,
        "modulo": {"valor_extraido": modulo} if modulo else None,
        "programa": {"valor_extraido": pos} if pos else None,
        "nota_final": nota,
        "resultado": resultado,
        "nota_ya_normalizada": True,
        # acta con estado de origen (Aprobado/Titulado...) pero sin nota: límite de la fuente, no un error de lectura
        "sin_nota_por_acta": nota is None and bool(estados.get("estado_academico") or estados.get("estado_arca")),
        "fecha": fecha,
        **estados,
        "avisos_acta": list(avisos_anomalas) + list(avisos_estado),
        "requiere_revision": (nota is None and not (estados.get("estado_academico") or estados.get("estado_arca"))) or fecha is None
                             or revision_estado or bool(anomalas),
    }]


def categoria_rentabilidad(valor: Optional[str]) -> Optional[str]:
    """CATEGORIA de EJECUTADO VS META -> categoría financiera (mismos nombres que seed_historical_facts)."""
    v = normalizar_encabezado(valor or "")
    if "PROGRAMA" in v:
        return "PROGRAMAS"
    if "TECHO" in v or "CERRADO" in v:
        return "TECHOS_CERRADOS"
    # Cualquier otra categoría de ingreso de la fuente ('Inscripciones', 'Diplomados', 'Cursos cortos') se conserva
    # con su propio nombre: el cargador la crea en dim_categoria_financiera. Totales y celdas numéricas no son categoría.
    if not v or v.startswith(("TOTAL", "SUBTOTAL", "ACUMULADO", "GRAN TOTAL")) or _a_float(v) is not None or len(v) > 60:
        return None
    return re.sub(r"[^A-Z0-9]+", "_", v).strip("_")[:50] or None


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
    es_metas_categoria = any(_RE_META_ANIO.match(k) for k in campos) or (
        "CATEGORIA" in campos and any(_RE_EJECUTADO_ANIO.match(k) or _RE_META_GENERICA_ANIO.match(k) for k in campos)
    )
    return [
        {"categoria_financiera": categoria, "fecha": date(anio, mes, 1), "es_fuente_metas_categoria": es_metas_categoria, **montos}
        for anio, montos in sorted(por_anio.items())
        if montos["monto_ejecutado"] is not None or montos["monto_meta"] is not None
    ]


_CLAVES_PAYLOAD_PLAN = (
    "REPROGRAMACIONES", "COMENTARIOS", "COMENTARIO DAF", "COMENTARIO ADMISIONES",
    "COMENTARIO DIGITAL / VIDEO SOLICITADO", "FECHA DE INICIO - ADS", "FECHA DE FIN - ADS",
    "DIAS ACTIVOS", "DIAS TOTALES", "VERSION", "EDICION", "COORDINADOR ACADEMICO", "ASISTENTE", "MEC",
)


def registro_planificacion(
    campos: Dict[str, str],
    hoja: str = "",
    anio_hoja: Optional[int] = None,
    mes_hoja: Optional[int] = None,
) -> Dict[str, Any]:
    """Mapea una fila de PLANIFICACION (hoja mensual o Programas Notificados) a fact_planificacion_programa."""
    # FU-L3: POS, período y datos de captación por campos canónicos del catálogo (sinónimos), no por nombre de columna
    from services import captacion_canonica
    pos_norm, _prog_canon, periodo_fila, _periodo_de_hoja = captacion_canonica.leer_identidad(campos, anio_hoja, mes_hoja)
    fila_capt = captacion_canonica.leer_fila(campos, anio_hoja, mes_hoja)

    nombre_prog = _primero(campos, ("PROGRAMA", "NOMBRE DEL PROGRAMA", "NOMBRE PROGRAMA"))
    if not nombre_prog:
        nombre_prog = next((v for k, v in campos.items() if k.startswith("PROGRAMA ") and v), None)

    tipo_prog = _primero(campos, ("TIPO DE PROGRAMA", "TIPO PROGRAMA"))
    escuela = campos.get("ESCUELA")
    origen_prog = _primero(campos, ("ORIGEN DEL PROGRAMA", "CATEGORIA DE ORIGEN DEL PROGRAMA"))
    diseno = _primero(campos, ("DISENO CURRICULAR",))

    fecha_notif = parsear_fecha(_primero(campos, ("FECHA DE NOTIFICACION", "FECHA DE NOFITICACION")))
    fecha_ini = parsear_fecha(_primero(campos, ("FECHA INICIO",)))
    fecha_fin = parsear_fecha(_primero(campos, ("FECHA FIN", "FECHA DE FINALIZACION")))

    # Periodo del hecho: FECHA / AÑO+MES (campos de período del catálogo) / FECHA INICIO / FECHA DE NOTIFICACION;
    # fallback a la hoja mensual si falta. El período de captación (KPI-06) nunca usa fecha de inicio ni de notificación.
    fecha_plan = periodo_fila if (periodo_fila and not _periodo_de_hoja) else None
    if not fecha_plan:
        fecha_plan = fecha_ini or fecha_notif
    if not fecha_plan and anio_hoja and mes_hoja:
        fecha_plan = date(int(anio_hoja), int(mes_hoja), 1)

    notif_raw = normalizar_encabezado(campos.get("NOTIFICADO") or "")
    if notif_raw in ("SI", "SÍ", "TRUE", "1", "NOTIFICADO"):
        notificado = True
    elif notif_raw in ("NO", "FALSE", "0"):
        notificado = False
    elif fecha_notif is not None:
        notificado = True
    else:
        notificado = None

    estado_fuente = _primero(campos, ("ESTADO", "ESTADO DEL PROGRAMA"))
    if estado_fuente and normalizar_encabezado(estado_fuente) in ("FALSE", "TRUE", "0", "NONE", "NAN"):
        estado_fuente = None

    payload = {k: campos[k] for k in _CLAVES_PAYLOAD_PLAN if campos.get(k) is not None}

    return {
        "pos_code_fuente": pos_norm,
        "nombre_programa": nombre_prog,
        "tipo_programa": tipo_prog[:100] if tipo_prog else None,
        "escuela": escuela[:120] if escuela else None,
        "origen_programa": origen_prog[:120] if origen_prog else None,
        "diseno_curricular": diseno[:160] if diseno else None,
        "fecha_notificacion": fecha_notif,
        "fecha_inicio_plan": fecha_ini,
        "fecha_fin_plan": fecha_fin,
        "duracion_meses": _a_float(_primero(campos, ("DURACION DEL PROGRAMA (MESES)", "DURACION (MESES)", "DURACION"))),
        "estado_fuente": estado_fuente[:120] if estado_fuente else None,
        "notificado": notificado,
        "costo_programa": _a_float(campos.get("COSTO PROGRAMA")),
        "costo_descuento_20": _a_float(campos.get("CP CON DESCUENTO 20%")),
        "tarifa_contado_100": _a_float(campos.get("TP AL CONTADO 100%")),
        "tarifa_contado_80": _a_float(campos.get("TP AL CONTADO 80%")),
        "punto_equilibrio": _a_float(_primero(campos, ("PUNTO DE EQUILIBRIO", "PE", "PE A"))),
        "leads_fuente": fila_capt.leads if fila_capt else None,
        "reservas_fuente": fila_capt.reservas if fila_capt else None,
        "inscritos_fuente": fila_capt.inscritos if fila_capt else None,
        # Período de captación: el de la fila o, sin él, el de la hoja mensual (nunca la fecha de inicio del programa)
        "fecha_captacion": captacion_canonica.mes_de(periodo_fila),
        "pauta_ejecutada": _a_float(campos.get("P/EJECUTADO")),
        "pauta_asignada": _a_float(campos.get("P/ASIGNADO")),
        "fecha_plan": fecha_plan,
        "hoja": hoja[:200],
        "payload_fuente": payload or None,
    }


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
        valor = str(campos.get(k) or "").strip()
        numero = _a_float(valor)  # Excel entrega '4244.0': sacar solo dígitos daría '42440'
        digitos = str(int(numero)) if numero is not None and numero == int(numero) else re.sub(r"\D", "", valor)
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


# ── Asignación docente-módulo (hoja MODULOS y equivalentes) ───────────────────
_CLAVES_DOCENTE = ("DOCENTE", "DOCENTE TITULAR", "NOMBRE DOCENTE", "NOMBRE DEL DOCENTE", "PROFESOR", "FACILITADOR", "TUTOR")
_CLAVES_NRO_MODULO = ("MODULO", "N° MODULO", "Nº MODULO", "NRO MODULO", "NUMERO MODULO", "NRO. MODULO")
_CLAVES_NOMBRE_MODULO = ("NOMBRE DEL MODULO", "NOMBRE MODULO", "MODULO NOMBRE", "MATERIA", "ASIGNATURA")
_CLAVES_TIPO_DOCENTE = ("TIPO DE DOCENTE", "TIPO DOCENTE", "ROL DOCENTE")
_CLAVES_HORAS = ("HRS MODULO", "HORAS MODULO", "HORAS", "HRS", "CARGA HORARIA")
_CLAVES_PAGO_DOCENTE = ("PAGO DOCENTE", "HONORARIO DOCENTE", "HONORARIO", "HONORARIOS")
_CLAVES_FECHA_INICIO = ("FECHA INICIO", "FECHA DE INICIO", "INICIO")
_CLAVES_FECHA_FIN = ("FECHA FIN", "FECHA DE FIN", "FECHA FINALIZACION", "FIN")
_RE_ENTERO_MODULO = re.compile(r"^\s*(?:M(?:OD(?:ULO)?)?\.?\s*)?(\d{1,2})\s*$", re.IGNORECASE)


def registros_asignacion_docente(campos: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Fila que dice qué docente dictó qué módulo de qué programa (sin estudiante): POS + número de módulo + docente.
    El nombre del módulo se toma de su columna; si la planilla lo puso bajo 'NOMBRE DEL PROGRAMA' (pasa en MODULOS
    de ARCA), una fila con número de módulo usa ese texto como nombre del módulo. Lista vacía si falta algo.
    """
    if estudiante_de_fila(campos) is not None:
        return []  # fila de un estudiante: es un acta, no una asignación
    docente = _primero(campos, _CLAVES_DOCENTE)
    pos = _pos_de_valores(campos) or _pos(campos)
    nro = None
    for k in _CLAVES_NRO_MODULO:
        m = _RE_ENTERO_MODULO.match(str(campos.get(k) or ""))
        if m and 1 <= int(m.group(1)) <= 30:
            nro = int(m.group(1))
            break
    if not (docente and pos and nro):
        return []
    nombre_mod = _primero(campos, _CLAVES_NOMBRE_MODULO)
    if not nombre_mod:
        candidato = _primero(campos, ("NOMBRE DEL PROGRAMA", "NOMBRE PROGRAMA", "PROGRAMA"))
        if candidato and not _RE_POS_VALOR.search(candidato.upper()):
            nombre_mod = candidato
    codigo = f"{pos}-M{nro:02d}"
    return [{
        "asignacion_docente": True,
        "estudiante": {},
        "docente": {"valor_extraido": docente},
        "programa": {"valor_extraido": pos, "metadata": {"pos_canonico": codigo}},
        "modulo": {"valor_extraido": nombre_mod or f"{pos} · Módulo {nro}"},
        "nombre_modulo_real": nombre_mod,
        "nro_modulo": nro,
        "tipo_docente": (_primero(campos, _CLAVES_TIPO_DOCENTE) or "").strip().upper() or None,
        "horas_modulo": _a_float(_primero(campos, _CLAVES_HORAS)),
        "pago_docente": _a_float(_primero(campos, _CLAVES_PAGO_DOCENTE)),
        "fecha_inicio": parsear_fecha(_primero(campos, _CLAVES_FECHA_INICIO)),
        "fecha_fin": parsear_fecha(_primero(campos, _CLAVES_FECHA_FIN)),
        "fecha": parsear_fecha(_primero(campos, _CLAVES_FECHA_INICIO)),
        "requiere_revision": False,
    }]


# ── Convenios corporativos / techos (POS + institución cliente + monto) ───────
_CABECERAS_INSTITUCION = ("INSTITUCION", "EMPRESA", "CONVENIO", "CLIENTE", "ENTIDAD", "INSTITUCION CONVENIO")
_PALABRAS_MONTO_CONVENIO = (("PAGO", "MONTO", "IMPORTE", "VALOR"), ("TECHO",))  # por prioridad
_EXCLUIR_MONTO = ("GESTION", "ANO", "FECHA", "ESCUELA", "N°", "Nº", "NRO", "INSCR", "ID")
_CLAVES_FECHA_FIN_CONVENIO = ("FECHA CONCLUSION", "FECHA DE CONCLUSION") + _CLAVES_FECHA_FIN


def _cabecera_institucion(campos: Dict[str, str]) -> Optional[str]:
    """Columna de la institución cliente, tolerando erratas ('INSITUCION'); nunca una llave derivada ('ID_INSTITUCION')."""
    from rapidfuzz import fuzz

    for k in campos:
        if k.startswith("ID") or not campos.get(k):
            continue
        if any(k == c or fuzz.ratio(k, c) >= 85 for c in _CABECERAS_INSTITUCION):
            return k
    return None


def registros_techo_convenio(campos: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Fila de un convenio con una institución (techo/cerrado): POS + institución cliente, y si hay, monto,
    inscritos y fechas. El monto se reconoce por el valor (numérico) bajo una cabecera de pago/monto/techo, aunque
    la cabecera diga 'Estado de Pago'. Lista vacía si falta POS o institución.
    """
    if estudiante_de_fila(campos) is not None:
        return []
    k_inst = _cabecera_institucion(campos)
    pos = _pos_de_valores(campos) or _pos(campos)
    if not (k_inst and pos):
        return []

    monto = None
    for palabras in _PALABRAS_MONTO_CONVENIO:
        for k, v in campos.items():
            if any(p in k for p in palabras) and not any(x in k.split() or k.startswith(x) for x in _EXCLUIR_MONTO):
                monto = _a_float(v)
                if monto is not None:
                    break
        if monto is not None:
            break
    inscritos = next((_a_float(v) for k, v in campos.items() if "INSCR" in k and _a_float(v) is not None), None)
    gestion = next((_a_float(v) for k, v in campos.items() if k.startswith("GESTION") and _a_float(v)), None)
    fecha_ini = parsear_fecha(_primero(campos, _CLAVES_FECHA_INICIO))
    fecha_fin = parsear_fecha(_primero(campos, _CLAVES_FECHA_FIN_CONVENIO))

    nombre_prog = _primero(campos, ("NOMBRE DEL PROGRAMA", "NOMBRE PROGRAMA", "PROGRAMA"))
    if nombre_prog:
        nombre_prog = re.sub(r"^\s*POS[\s-]?\d{3,5}\s*", "", nombre_prog).strip() or None

    motivos = []
    if fecha_ini and fecha_fin and fecha_fin < fecha_ini:
        motivos.append(f"FECHAS_INVERTIDAS: fin {fecha_fin} anterior al inicio {fecha_ini}")
    if gestion and fecha_ini and int(gestion) != fecha_ini.year:
        motivos.append(f"GESTION_DISTINTA_A_INICIO: gestión {int(gestion)} vs inicio {fecha_ini}")
    return [{
        "techo_convenio": True,
        "estudiante": {},
        "programa": {"valor_extraido": nombre_prog or pos, "metadata": {"pos_canonico": pos}},
        "modulo": {"valor_extraido": nombre_prog or pos},
        "institucion_cliente": campos[k_inst].strip(),
        "monto_convenio": monto,
        "n_inscritos": int(inscritos) if inscritos is not None else None,
        "gestion": int(gestion) if gestion else None,
        "fecha_inicio": fecha_ini,
        "fecha_fin": fecha_fin,
        "fecha": fecha_ini,
        "motivo_techo": "; ".join(motivos) or None,
        "requiere_revision": bool(motivos),
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
    # Cabeceras cortas que nombran el programa ('PROGRAMA', 'PROGRAMA - POS', 'PROGRAMA POS', 'CURSO'); las
    # preguntas largas que mencionan 'el programa' no cuentan.
    texto_programa = " ".join(v for k, v in campos.items()
                              if v and len(k) <= 40 and re.search(r"\b(PROGRAMA|CURSO|COURSE|POS)\b", k))
    m_pos = _RE_POS_VALOR.search(texto_programa.upper())
    pos = f"POS-{m_pos.group(1)}" if m_pos else _pos(campos)
    # Número de módulo bajo cualquier cabecera corta con 'MODULO' ('MODULO', 'N° MODULO', 'NUMERO DEL MODULO');
    # el valor debe ser corto ('1', 'M02', 'Módulo 3'), no el nombre del módulo ni una respuesta.
    valor_mod = next((v for k, v in campos.items()
                      if v and len(k) <= 30 and "MODULO" in k and len(v.strip()) <= 12), "")
    m_mod = _RE_NRO_MODULO.search(valor_mod)
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


def fila_resuelta_por_regla(campos: Dict[str, str], categoria: str) -> bool:
    """D-A8a / D-T1: una fila que una regla estructural (categoría + mes, costos por programa o convenio)
    ya convierte en hecho en cualquier categoría donde el pipeline aplica esa regla.
    No necesita persona ni índice BETO: BETO solo ve lo que las reglas no resolvieron (cascada)."""
    if not campos:
        return False
    if categoria == "rentabilidad":
        return bool(
            registros_rentabilidad(campos)
            or registros_costo_programa(campos)
            or registros_techo_convenio(campos)
        )
    if categoria in ("marketing", "admision"):
        return bool(registros_techo_convenio(campos))
    return False


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
        if registros_rentabilidad(campos) or registros_costo_programa(campos) or registros_techo_convenio(campos):
            return None
        return "FILA_AGREGADA_SIN_CATEGORIA_MES"
    if categoria == "evaluacion_docente":
        return None if registros_evaluacion(campos) else "FILA_EVALUACION_SIN_RESPUESTAS"
    if estudiante_de_fila(campos) is not None:
        return None
    if categoria == "academico":
        if registros_asignacion_docente(campos):
            return None
        return _detalle_academica_sin_estudiante(campos)
    if categoria == "financiero" and _es_pago_sin_estudiante(campos):
        return MOTIVO_SIN_IDENTIDAD
    if _pos(campos) or any(campos.get(k) for k in _CLAVES_ENTIDAD_PROGRAMA):
        return MOTIVO_CATALOGO_NO_PAGO if categoria == "financiero" else None
    return "FILA_SIN_ENTIDAD"


# ADW-L8 (DA7): lo que antes era un único «FILA_*_SIN_ESTUDIANTE» ahora dice qué es la fila.
MOTIVO_CATALOGO_NO_ALUMNO = "CATALOGO_PROGRAMA_NO_ALUMNO"   # se descarta con motivo
MOTIVO_CATALOGO_NO_PAGO = "CATALOGO_PROGRAMA_NO_PAGO"       # se descarta con motivo
MOTIVO_DOCENTE_NO_ESTUDIANTE = "DOCENTE_NO_ESTUDIANTE"      # se descarta con motivo
MOTIVO_SIN_IDENTIDAD = "FILA_SIN_IDENTIDAD"                  # NO se descarta: va a la bandeja de revisión
MOTIVOS_A_BANDEJA = frozenset({MOTIVO_SIN_IDENTIDAD})

_ENCABEZADOS_DOCENTE = ("POS - MODULO", "PAGO DOCENTE", "HRS MODULO", "TIPO DE DOCENTE")
_ENCABEZADOS_CATALOGO = ("POS - IBP", "MES IBP", "ANO IBP", "PUNTO EQUILIBRIO", "INVERSION DEL PROGRAMA", "ESTADO PROGRAMA")


def _tiene_encabezado(campos: Dict[str, str], candidatos) -> bool:
    return any(k in campos or any(c.startswith(k) for c in campos) for k in candidatos)


def _detalle_academica_sin_estudiante(campos: Dict[str, str]) -> str:
    """Fila académica sin estudiante: docente (hoja POS - MODULO), catálogo de programas (hoja IBP) o sin identidad."""
    if _tiene_encabezado(campos, _ENCABEZADOS_DOCENTE):
        return MOTIVO_DOCENTE_NO_ESTUDIANTE
    if _tiene_encabezado(campos, _ENCABEZADOS_CATALOGO):
        return MOTIVO_CATALOGO_NO_ALUMNO
    return MOTIVO_SIN_IDENTIDAD


def _es_pago_sin_estudiante(campos: Dict[str, str]) -> bool:
    """Una factura o pago (monto, NIT, razón social) sin código de estudiante: hay dinero, así que alguien debe verlo."""
    return any(k.startswith("MONTO") or k.startswith("N DE FACTURA") or "FACTURA" in k or k in ("NIT", "RAZON SOCIAL") for k in campos)
