"""
FU-L5 (DA1): lectura de una celda de encuesta con datos ficticios, sin libros.

- «n/Etiqueta», número suelto, etiqueta sin número (diccionario del catálogo), texto libre y celdas vacías;
- 0 y «Sin Información» → sin respuesta (NULL), nunca 0; fuera de escala → NULL; el NPS 0-10 admite el 0;
- escala 1-5 frente a 1-10 y NPS; etiqueta desconocida; respuesta cruzada.
"""

import pytest

from services import encuesta_canonica as ec

PREGUNTA = "EL CONTENIDO DEL MODULO FUE PERTINENTE PARA MI CAMPO PROFESIONAL."


def leer(cab, valor, perfil=None):
    return ec._interpretar(cab, valor, perfil)


def perfil_de(valores, cab=PREGUNTA):
    """Perfil de una hoja con una pregunta cuyas celdas son `valores`."""
    return ec.perfilar([{cab: v} for v in valores])


@pytest.mark.parametrize("texto,tipo,numero", [
    ("5/Totalmente de acuerdo", ec.N_ETIQUETA, 5.0),
    ("1/ Totalmente en desacuerdo", ec.N_ETIQUETA, 1.0),
    ("3 - Adecuada", ec.N_ETIQUETA, 3.0),
    ("4,5", ec.NUMERO, 4.5),
    ("8", ec.NUMERO, 8.0),
    ("Satisfecho", ec.ETIQUETA, 4.0),
    ("MUY PROBABLE", ec.ETIQUETA, 5.0),
    ("Neutral", ec.ETIQUETA, 3.0),
    ("De acuerdo", ec.ETIQUETA, 4.0),
])
def test_parseo_de_n_etiqueta_numero_y_etiqueta_sin_numero(texto, tipo, numero):
    v = ec.leer_valor(texto)
    assert (v.tipo, v.numero) == (tipo, numero)


def test_texto_libre_y_celdas_vacias():
    assert ec.leer_valor("Más casos prácticos").tipo == ec.TEXTO
    for vacio in (None, "", "  ", "nan", ".", "-", "n/a", "Ninguno"):
        assert ec.leer_valor(vacio).tipo == ec.VACIO
    assert ec.leer_valor("Excelente").tipo == ec.TEXTO          # sola, «Excelente» es una palabra de un comentario
    assert ec.leer_valor("4/Bueno").tipo == ec.N_ETIQUETA       # con número sí es respuesta de la familia de calidad


@pytest.mark.parametrize("texto", ["0/Sin Información", "0/sin informacion", "Sin Información", "3/Sin información"])
def test_sin_informacion_es_sin_respuesta(texto):
    assert ec.leer_valor(texto).tipo == ec.SIN_INFO
    r = leer(PREGUNTA, texto)
    assert (r.clase, r.puntuacion) == (ec.SIN_INFORMACION, None)
    assert r.aviso[0] == "SIN_INFORMACION"


def test_cero_numerico_es_sin_respuesta_no_cero():
    perfil = perfil_de(["5/Totalmente de acuerdo", "4/De acuerdo", "3/Neutral", "0"])
    r = leer(PREGUNTA, "0", perfil)
    assert (r.clase, r.puntuacion) == (ec.SIN_INFORMACION, None)


def test_fuera_de_escala_es_null():
    perfil = perfil_de(["5/Totalmente de acuerdo", "4/De acuerdo", "3/Neutral", "2/En desacuerdo", "8"])
    assert perfil.columnas[PREGUNTA].escala == 5
    r = leer(PREGUNTA, "8", perfil)
    assert (r.clase, r.puntuacion) == (ec.FUERA_DE_ESCALA, None)
    assert r.aviso[0] == "PUNTUACION_FUERA_DE_ESCALA"
    assert leer(PREGUNTA, "5", perfil).puntuacion == 5.0


def test_escala_1_5_frente_a_1_10_por_los_valores_de_la_columna():
    c5 = perfil_de(["5", "4", "3", "5", "2", "4"])
    c10 = perfil_de(["9", "8", "10", "7", "6", "8"])
    assert (c5.columnas[PREGUNTA].escala, c10.columnas[PREGUNTA].escala) == (5, 10)
    assert leer(PREGUNTA, "9", c10).escala_max == 10
    assert leer(PREGUNTA, "9", c5).clase == ec.FUERA_DE_ESCALA


def test_la_cabecera_manda_sobre_los_valores():
    cab = "EN UNA ESCALA DEL 1 AL 10, ¿QUE TAN SATISFECHO/A ESTA CON SU EXPERIENCIA?"
    perfil = perfil_de(["3", "4", "2", "5", "1"], cab=cab)   # todos ≤ 5, pero la pregunta dice 1-10
    assert perfil.columnas[cab].escala == 10
    assert leer(cab, "4", perfil).escala_max == 10


def test_escala_que_no_se_puede_inferir_deja_las_respuestas_sin_valor():
    cab = "¿QUE PUNTAJE LE DA A LA ATENCION DEL PERSONAL EN GENERAL?"
    perfil = perfil_de(["85", "90", "70", "95", "60", "88"], cab=cab)    # una escala de 100: ni 1-5 ni 1-10
    assert perfil.columnas[cab].escala is None
    r = leer(cab, "85", perfil)
    assert (r.clase, r.puntuacion) == (ec.ESCALA_NO_INFERIBLE, None)
    assert r.aviso[0] == "ESCALA_NO_INFERIBLE"


def test_el_nps_acepta_el_cero_y_la_satisfaccion_no():
    nps = "¿QUE TAN PROBABLE ES QUE RECOMIENDE ESTE MODULO A UN COLEGA O AMIGO/A?"
    sat = "¿QUE TAN SATISFECHO/A ESTA CON SU EXPERIENCIA GENERAL EN ESTE MODULO?"
    filas = [{nps: v, sat: w} for v, w in [("10", "9"), ("0", "0"), ("7", "8"), ("9", "10"), ("6", "7"), ("8", "9")]]
    perfil = ec.perfilar(filas)
    assert ec.tipo_pregunta(nps) == "NPS"
    r_nps = leer(nps, "0", perfil)
    assert (r_nps.clase, r_nps.puntuacion, r_nps.escala_max) == (ec.PUNTUADA, 0.0, 10)
    r_sat = leer(sat, "0", perfil)
    assert (r_sat.clase, r_sat.puntuacion) == (ec.SIN_INFORMACION, None)


def test_etiqueta_sin_numero_y_etiqueta_desconocida():
    perfil = perfil_de(["De acuerdo", "Totalmente de acuerdo", "Muy de acuerdo", "Neutral", "En desacuerdo", "Estupendo"])
    assert [leer(PREGUNTA, v, perfil).puntuacion for v in ("De acuerdo", "Totalmente de acuerdo", "Muy de acuerdo", "Neutral",
                                                           "En desacuerdo")] == [4.0, 5.0, 5.0, 3.0, 2.0]
    r = leer(PREGUNTA, "Estupendo", perfil)
    assert (r.clase, r.puntuacion) == (ec.FUERA_DE_CATALOGO, None)
    assert r.aviso[0] == "VALOR_FUERA_DE_CATALOGO"
    assert "Estupendo" not in r.aviso[2]                                   # el ejemplo no publica el texto


def test_etiqueta_de_otra_familia_es_respuesta_cruzada():
    perfil = perfil_de(["5/Totalmente de acuerdo", "4/De acuerdo", "3/Neutral", "4/De acuerdo", "5/Totalmente de acuerdo", "4/Fácil"])
    assert perfil.columnas[PREGUNTA].familia == "acuerdo"
    r = leer(PREGUNTA, "4/Fácil", perfil)
    assert (r.clase, r.puntuacion) == (ec.CRUZADA, None)
    assert r.aviso[0] == "RESPUESTA_EN_COLUMNA_EQUIVOCADA"
    assert r.aviso[2] == "facil"                                           # una etiqueta del diccionario sí es publicable
    assert leer(PREGUNTA, "Neutral", perfil).puntuacion == 3.0              # «Neutral» vale para cualquier familia


def test_texto_largo_en_una_columna_puntuada_es_respuesta_cruzada_sin_publicar_el_texto():
    perfil = perfil_de(["5/Totalmente de acuerdo", "4/De acuerdo", "3/Neutral", "4/De acuerdo", "5/Totalmente de acuerdo"])
    texto = "Necesito mas ejemplos practicos de casos reales del sector"
    r = leer(PREGUNTA, texto, perfil)
    assert (r.clase, r.puntuacion) == (ec.CRUZADA, None)
    assert "ejemplos" not in r.aviso[2] and "caracteres" in r.aviso[2]


def test_etiqueta_de_1_5_en_una_pregunta_de_1_10_es_respuesta_cruzada():
    cab = "¿QUE TAN SATISFECHO/A ESTA CON SU EXPERIENCIA GENERAL EN ESTE MODULO?"
    perfil = perfil_de(["9", "8", "10", "7", "9", "8", "5/Totalmente de acuerdo"], cab=cab)
    assert perfil.columnas[cab].escala == 10
    assert leer(cab, "5/Totalmente de acuerdo", perfil).clase == ec.CRUZADA


def test_columna_de_comentarios_conserva_el_texto_y_la_de_puntuacion_no():
    cab = "¿QUE ASPECTO PODRIA MEJORARSE EN ESTE MODULO?"
    perfil = perfil_de(["Mas practica", "Todo bien", "Mas casos", "0/Sin Información", "Nada que agregar a este modulo"], cab=cab)
    assert perfil.columnas[cab].clase == ec.COMENTARIO
    assert leer(cab, "Mas practica", perfil).comentario == "Mas practica"
    assert leer(cab, "0/Sin Información", perfil) is None                    # sin comentario: no es una respuesta ni un aviso


def test_el_catalogo_es_editable_una_etiqueta_nueva_se_anade_sin_codigo(monkeypatch):
    from pipeline import lector_hojas
    cfg = lector_hojas.cargar_config()
    voc = cfg["tipos_fuente"]["EVALUACION_DOCENTE"]["vocabularios"]["etiquetas"]
    assert "estupendo" not in str(voc)
    monkeypatch.setitem(voc["satisfaccion"], "5", voc["satisfaccion"]["5"] + ["estupendo"])
    ec.recargar_catalogo()
    try:
        assert ec.leer_valor("Estupendo").tipo == ec.ETIQUETA
    finally:
        monkeypatch.undo()
        ec.recargar_catalogo()
    assert ec.leer_valor("Estupendo").tipo == ec.TEXTO
