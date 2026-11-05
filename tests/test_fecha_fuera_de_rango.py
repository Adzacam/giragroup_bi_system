"""
tests/test_fecha_fuera_de_rango.py
----------------------------------
En 'BD Cobranzas.xlsx' (hoja 'Copia de COBRANZAS 2024 2025') tres filas traen el número de factura en la
columna FECHA ULTIMA FACTURA, con formato fecha: Excel lo muestra como 1902-08-04 o 1928-11-22 y el CMI
creaba las gestiones 1902 y 1928. Una fecha fuera de 2000..2100 se descarta y se usa la siguiente columna.
"""

from datetime import date, datetime

from services.extraccion_por_encabezado import fecha_de_fila, parsear_fecha


def test_descarta_fechas_fuera_del_rango_de_negocio():
    assert parsear_fecha(datetime(1928, 11, 22)) is None
    assert parsear_fecha(datetime(1902, 8, 4)) is None
    assert parsear_fecha(datetime(205, 5, 31)) is None   # año mal tecleado
    assert parsear_fecha("22/11/1928") is None
    assert parsear_fecha(datetime(2024, 2, 29)) == date(2024, 2, 29)


def test_cobranza_con_factura_en_columna_fecha_usa_la_primera_factura():
    campos = {"FECHA ULTIMA FACTURA": datetime(1928, 11, 22), "FECHA DE LA PRIMERA FACTURA": datetime(2024, 2, 1)}
    assert fecha_de_fila(campos, "financiero") == date(2024, 2, 1)
