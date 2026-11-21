"""
FU-L5: la fila de una encuesta (pares texto + número, columnas derivadas, identidad, tipo de pregunta) con datos ficticios.
"""

from services import encuesta_canonica as ec
from services.extraccion_por_encabezado import campos_por_encabezado, registros_evaluacion


def campos(linea):
    return campos_por_encabezado([c.strip() for c in linea.split(" | ")])


A1T = "A 1. ¿La/El docente explica los conceptos de manera clara?"
A1N = "A 1. N°¿La/El docente explica los conceptos de manera clara?"


def test_dos_columnas_por_pregunta_cuentan_una_sola_respuesta():
    fila = campos(f"{A1T}: 5/Totalmente de acuerdo | {A1N}: 5")
    r = ec.leer_fila(fila)
    assert len(r) == 1
    assert (r[0].puntuacion, r[0].escala_max, r[0].par_evitado) == (5.0, 5, True)
    assert "N°" not in r[0].cabecera                                       # la pregunta no lleva el marcador de la columna numérica


def test_en_un_par_manda_la_columna_numerica():
    fila = campos(f"{A1T}: 4/De acuerdo | {A1N}: 3")
    assert ec.leer_fila(fila)[0].puntuacion == 3.0


def test_par_con_cero_es_una_sola_respuesta_sin_valor():
    fila = campos(f"{A1T}: 0/Sin Información | {A1N}: 0")
    r = ec.leer_fila(fila)
    assert len(r) == 1 and r[0].clase == ec.SIN_INFORMACION and r[0].puntuacion is None


def test_si_solo_hay_la_columna_de_texto_se_usa_el_diccionario():
    r = ec.leer_fila(campos(f"{A1T}: Totalmente de acuerdo"))
    assert [(x.clase, x.puntuacion) for x in r] == [(ec.PUNTUADA, 5.0)]


def test_columna_calculada_de_promedio_no_es_una_respuesta():
    fila = campos(f"{A1T}: 5/Totalmente de acuerdo | Experiencia cualitativa promedio docente: De Acuerdo | Experiencia promedio docente: 4")
    assert len(ec.leer_fila(fila)) == 1


def test_la_pregunta_es_la_misma_aunque_la_columna_de_texto_este_antes_o_despues():
    a = ec.leer_fila(campos(f"{A1T}: 5/Totalmente de acuerdo | {A1N}: 5"))
    b = ec.leer_fila(campos(f"{A1N}: 5 | {A1T}: 5/Totalmente de acuerdo"))
    assert [x.cabecera for x in a] == [x.cabecera for x in b]


def test_tipo_de_pregunta_docente_institucional_y_nps():
    assert ec.tipo_pregunta("¿LA/EL DOCENTE EXPLICA?") == "DOCENTE"
    assert ec.tipo_pregunta("¿EL PERSONAL ADMINISTRATIVO FUE RECEPTIVO?") == "INSTITUCIONAL"
    assert ec.tipo_pregunta("¿QUE TAN PROBABLE ES QUE RECOMIENDE EL MODULO?") == "NPS"
    assert ec.tipo_pregunta("¿QUE TAN FACIL LE RESULTO RESOLVER SUS DUDAS?") == "DOCENTE"
    assert ec.tipo_pregunta("¿QUE TAN FACIL LE RESULTO RESOLVER SUS DUDAS?", "INSTITUCIONAL") == "INSTITUCIONAL"


def test_hoja_sin_preguntas_sobre_el_docente_toma_el_tipo_institucional_por_defecto():
    filas = [{"¿QUE TAN FACIL LE RESULTO RESOLVER SUS DUDAS?": v, "¿EL SOPORTE TECNICO FUE OPORTUNO?": w}
             for v, w in [("4/Facil", "4/De acuerdo"), ("5/Muy facil", "5/Totalmente de acuerdo"), ("3/Neutral", "3/Neutral"),
                          ("4/Facil", "4/De acuerdo")]]
    assert ec.perfilar(filas).defecto_tipo == "INSTITUCIONAL"
    filas_doc = [{**f, "¿EL DOCENTE EXPLICA CON CLARIDAD?": "5/Totalmente de acuerdo"} for f in filas]
    assert ec.perfilar(filas_doc).defecto_tipo == "DOCENTE"


def test_registros_evaluacion_lleva_los_avisos_y_no_crea_hecho_para_la_celda_sin_respuesta():
    fila = campos("NOMBRE COMPLETO: Ana Ficticia Ruiz | FECHA: 2027-03-10 | PROGRAMA POS: POS-9801 | MODULO: 1 | "
                  f"{A1T}: 0/Sin Información | {A1N}: 0 | A 2. ¿La/El docente mostró dominio de los temas?: 5/Totalmente de acuerdo")
    regs = registros_evaluacion(fila)
    con_valor = [r for r in regs if r["puntuacion"] is not None]
    sin_valor = [r for r in regs if r["puntuacion"] is None and not r["comentario"]]
    assert len(con_valor) == 1 and len(sin_valor) == 1
    assert sin_valor[0]["avisos_encuesta"][0][0] == "SIN_INFORMACION"
    assert sin_valor[0]["clave_respuesta"] != con_valor[0]["clave_respuesta"]


def test_una_respuesta_escrita_en_la_columna_del_modulo_no_es_un_numero_de_modulo():
    fila = campos("NOMBRE COMPLETO: Ana Ficticia Ruiz | FECHA: 2027-03-10 | PROGRAMA POS: POS-9801 | MODULO: 4/De acuerdo | "
                  "¿La/El docente explica con claridad los conceptos?: 5/Totalmente de acuerdo")
    regs = registros_evaluacion(fila)
    assert regs[0]["programa"]["metadata"]["pos_canonico"] == "POS-9801"          # sin «-M04» pegado
    motivos = [a[0] for r in regs for a in r["avisos_encuesta"]]
    assert motivos == ["RESPUESTA_EN_COLUMNA_EQUIVOCADA"]


def test_la_pista_de_escala_de_la_cabecera_sin_perfil():
    fila = campos("NOMBRE COMPLETO: Ana Ficticia Ruiz | FECHA: 2027-03-10 | PROGRAMA POS: POS-9801 | "
                  "1 - Docente explica claramente (1-5): 5 | 2 - Docente domina temas del curso (1-5): 9")
    regs = registros_evaluacion(fila)
    por_valor = {r["puntuacion"]: r["escala_max"] for r in regs if r["puntuacion"] is not None}
    assert por_valor == {5.0: 5}                                                  # el 9 de una pregunta 1-5 no se reescala a 1-10
    assert any(a[0] == "PUNTUACION_FUERA_DE_ESCALA" for r in regs for a in r["avisos_encuesta"])


def test_el_contenido_clasifica_una_hoja_de_encuesta_y_no_un_acta():
    filas = [["N°", "Nombre", "P1", "P2", "P3", "P4"]] + [
        [i, "ANA", "5/Totalmente de acuerdo", "Satisfecho", "4/De acuerdo", "Neutral"] for i in range(8)]
    assert ec.hoja_es_encuesta(filas) is True
    acta = [["N°", "Nombre", "M1", "M2", "M3", "M4"]] + [[i, "ANA", 85, 70, "Aprobó", 55] for i in range(8)]
    assert ec.hoja_es_encuesta(acta) is False
