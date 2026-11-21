"""FU-L4: reglas del acta por separado (sin base de datos): celda de nota, resultado, 0, estados y CI con complemento."""

import pytest

from services import acta_canonica as ac


@pytest.mark.parametrize("valor,clase,numero,resultado", [
    ("85", "NUMERO", 85.0, None), ("85.5", "NUMERO", 85.5, None), ("0", "NUMERO", 0.0, None), ("100", "NUMERO", 100.0, None),
    ("101", "FUERA_DE_RANGO", None, None), ("13.622.300", "FUERA_DE_RANGO", None, None), ("-3", "FUERA_DE_RANGO", None, None),
    ("Aprobó", "TEXTO", None, "APROBADO"), ("APROBO", "TEXTO", None, "APROBADO"),
    ("No asistió a clases", "TEXTO", None, "INASISTENCIA"), ("Nunca ingresó a clases", "TEXTO", None, "INASISTENCIA"),
    ("Faltas y no envió trabajo", "TEXTO", None, "INASISTENCIA"),
    ("EXIMIDA", "TEXTO", None, "EXIMIDO"), ("eximido", "TEXTO", None, "EXIMIDO"),
    ("SIN NOTAS EN EL ACTA DE NOTAS", "TEXTO", None, "SIN_NOTA"), ("Aparece en ARCA pero no en el acta", "TEXTO", None, "SIN_NOTA"),
    ("Pérez", "FUERA_DE_CATALOGO", None, None), ("experto 123", "FUERA_DE_CATALOGO", None, None),
    ("-", "VACIA", None, None), ("", "VACIA", None, None), (None, "VACIA", None, None), ("nan", "VACIA", None, None),
])
def test_celda_de_nota(valor, clase, numero, resultado):
    c = ac.leer_celda(valor)
    assert (c.clase, c.numero, c.resultado) == (clase, numero, resultado)


@pytest.mark.parametrize("nota,desercion,esperado", [
    (85.0, False, (85.0, "APROBADO")), (70.0, False, (70.0, "APROBADO")), (69.99, False, (69.99, "REPROBADO")),
    (0.0, False, (0.0, "REPROBADO")),          # 0 real: se queda con nota_final = 0
    (0.0, True, (None, "INASISTENCIA")),       # 0 de un desertor: inasistencia, sin nota
    (40.0, True, (40.0, "REPROBADO")),         # solo el 0 cambia con la deserción
])
def test_resultado_de_un_numero(nota, desercion, esperado):
    assert ac.resolver_numero(nota, desercion) == esperado


@pytest.mark.parametrize("valor,esperado", [
    ("Deserción", "DESERCION"), ("deserción", "DESERCION"), ("DESERCION", "DESERCION"), (" desercion ", "DESERCION"),
    ("Abandono", "ABANDONO"), ("abandono", "ABANDONO"),
    ("Aprobado", None), ("Reprobado", None), ("En curso", None), ("Insuficiencia académica", None), (None, None), ("", None),
])
def test_estado_de_desercion_ignora_mayusculas_y_acentos(valor, esperado):
    assert ac.codigo_estado(valor) == esperado


def test_desercion_en_estado_academico_o_en_tutoria():
    assert ac.es_desercion("Aprobado", "Abandono")
    assert ac.es_desercion("Deserción", None)
    assert not ac.es_desercion("Reprobado", "Insuficiencia académica")


@pytest.mark.parametrize("valor,esperado", [
    ("4892019", ("4892019", None)), ("4892019.0", ("4892019", None)), (4892019.0, ("4892019", None)),
    ("4892019-1C", ("4892019", "1C")), ("4892019 CBBA", ("4892019", "CBBA")), ("4892019 Ch.", ("4892019", "CH")),
    ("4892019sc", ("4892019", "SC")), ("4.892.019", ("4892019", None)), ("CI-4892019", ("4892019", None)),
    ("E-1234567", (None, None)), ("------", (None, None)), (None, (None, None)),
])
def test_ci_se_separa_en_numero_y_complemento(valor, esperado):
    assert ac.separar_ci(valor) == esperado


def test_columnas_de_modulo_por_sinonimos_y_numero_de_la_cabecera():
    campos = {"MODULO 1": "80", "MOD. 2": "70", "NOTA MODULO 10": "Aprobó", "MODULOS": "x", "NOMBRES": "ANA", "MODULO 3": ""}
    assert ac.columnas_modulo(campos) == {1: "80", 2: "70", 10: "Aprobó"}


def test_campos_por_sinonimos():
    campos = {"CI": "9100001", "CONDICION ACADEMICA": "Aprobado", "ESTADO DE TUTORIA": "Abandono", "ESTADO ARCA": "Titulado"}
    assert ac.valor_de_campo(campos, "ci") == "9100001"
    assert ac.valor_de_campo(campos, "estado_academico") == "Aprobado"
    assert ac.valor_de_campo(campos, "estado_tutoria") == "Abandono"
    assert ac.valor_de_campo(campos, "estado_arca") == "Titulado"
    assert ac.valor_de_campo({"X": "1"}, "estado_academico") is None


def test_el_estado_de_tutoria_no_se_confunde_con_el_academico():
    from services.extraccion_por_encabezado import estados_de_fila
    e = estados_de_fila({"ESTADO ACADEMICO": "reprobado", "ESTADO TUTORIA": "ABANDONO", "ESTADO ARCA": "no titulado"})
    assert (e["estado_academico"], e["estado_tutoria"], e["estado_arca"]) == ("Reprobado", "Abandono", "No Titulado")
    assert not e["estado_revision"]
    raro = estados_de_fila({"ESTADO ACADEMICO": "Egresado"})
    assert raro["estado_academico"] == "Egresado" and raro["estado_revision"]
    assert raro["avisos_estado"][0][:2] == ("VALOR_FUERA_DE_CATALOGO", "estado_academico")
