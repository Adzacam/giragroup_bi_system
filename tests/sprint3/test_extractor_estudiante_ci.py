"""
tests/test_extractor_estudiante_ci.py
-------------------------------------
Regresión de extract_entities_from_line (routers/dataops.py) con filas reales:
1. Cobranzas: el nombre es NOMBRES + PATERNO + MATERNO, no el ASESOR.
2. Actas ARCA: el nombre usa APELLIDO PATERNO/MATERNO y el CI viene en CÉDULA DE IDENTIDAD.
3. Hoja MODULOS: ni el DOCENTE ni la RESIDENCIA DOCENTE son estudiantes, y el CELULAR no es CI.
4. Cobranzas 'Resumen por Programa': un estado de cartera ('EN PROCESO DE COBRO') no es un estudiante.
"""

from routers.dataops import extract_entities_from_line


def _estudiante_y_ci(linea: str):
    ents, _, _ = extract_entities_from_line(linea, [], [], [], tipo_fuente="COBRANZA")
    est = next((e["token"] for e in ents if e.get("label") == "ESTUDIANTE"), None)
    ci = next((e["token"] for e in ents if e.get("label") == "DOCUMENTO / CI"), None)
    return est, ci


def test_cobranzas_no_toma_asesor_como_estudiante():
    linea = (
        "TIPO DE PROGRAMA: CURSO | POS: POS-5059 | NOMBRE DEL PROGRAMA: CURSO TABLAS DINÁMICAS 12ª Versión | "
        "ASESOR: RODRIGO MEDINA | CI: 2560728 | NOMBRES: PEDRO PABLO | PATERNO: CONDORI | MATERNO: PEREZ | "
        "CELULAR: 61473048 | DEUDA TOTAL: 750"
    )
    assert _estudiante_y_ci(linea) == ("PEDRO PABLO CONDORI PEREZ", "2560728")


def test_acta_arca_compone_nombre_y_lee_cedula():
    linea = (
        "N°: 1 | POS - ACTAS: POS-011 | CÉDULA DE IDENTIDAD: 13727801 | MES INICIO: Febrero | AÑO INICIO: 2024 | "
        "APELLIDO PATERNO: Torrez | APELLIDO MATERNO: Salinas | NOMBRES: Ana Lucía | MÓDULO 1: 78"
    )
    assert _estudiante_y_ci(linea) == ("Ana Lucía Torrez Salinas", "13727801")


def test_hoja_modulos_no_genera_estudiante_ni_ci():
    linea = (
        "N°: 1 | POS - MODULO: POS-006 | TIPO DE PROGRAMA: ESPECIALIDAD | DOCENTE: Dr. María Huanca | "
        "TIPO DE DOCENTE: INVITADO | NOMBRE DEL PROGRAMA: Especialidad en Proyectos | PAGO DOCENTE: 2468 | "
        "CELULAR: 78351320 | E-MAIL: docente1@email.com | RESIDENCIA DOCENTE: Santa Cruz"
    )
    est, ci = _estudiante_y_ci(linea)
    assert est is None
    assert ci == "No provisto"


def test_estado_de_cartera_no_es_estudiante():
    linea = (
        "POS: POS-5439 | NOMBRE DEL PROGRAMA: CURSO EN EDICIÓN DE VIDEO PARA REDES SOCIALES 6ª Versión | "
        "FECHA INICIO: 2023-03-02 00:00:00 | INSCRITOS: 31 | ESTADO PROGRAMA: PROGRAMA CERRADO | "
        "TIPO CARTERA: CARTERA EN MORA | OBSERVACIÓN CARTERA: EN PROCESO DE COBRO"
    )
    est, _ = _estudiante_y_ci(linea)
    assert est is None
    # Sin encabezado tampoco: 'cobro' no forma parte de un nombre de persona
    est, _ = _estudiante_y_ci("POS-5439 | EN PROCESO DE COBRO | 31")
    assert est is None
