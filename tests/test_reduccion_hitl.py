"""Reducción de casos HITL: variante de nombre con CI exacta, líneas sin hecho posible y agrupación de la bandeja."""
from routers.pipeline import _motivo_no_aplicable
from services.bandeja_grupos import clave_grupo, valor_normalizado
from services.dw_loader import _es_variante_de_nombre


def test_variante_de_nombre_con_apellido_comun_y_placeholder():
    assert _es_variante_de_nombre("MARIA JOSE LOPEZ", "Maria Jose Lopez Gonzales")
    assert _es_variante_de_nombre("Estudiante CI 9984721", "LETICIA FRIDA QUENTA MARCANI")
    assert not _es_variante_de_nombre("JUAN PEREZ SOTO", "CARLOS ROJAS VARGAS")


def test_lineas_sin_hecho_posible():
    assert _motivo_no_aplicable(["N°: 1498"]) == "SOLO_NUMERACION"
    assert _motivo_no_aplicable(["Ninguno", "Ninguno"]) == "TEXTO_LIBRE_SIN_ENCABEZADO"
    assert _motivo_no_aplicable(["N°: 3", "NOMBRES: Ana"]) is None


def test_grupos_por_motivo_y_valor_normalizado():
    assert clave_grupo("CI_NOMBRE_DISCORDANTE", "CI: 123 | Nombre: A (Discordante con: B)") == clave_grupo("CI_NOMBRE_DISCORDANTE", "CI: 123 | Nombre: C (Discordante con: D)")
    assert valor_normalizado("BAJA_CONFIANZA_IA", "A: 5 | FECHA INICIO: 2026-01-02 | ESTADO: x") == valor_normalizado("BAJA_CONFIANZA_IA", "A: 9 | FECHA INICIO: 2026-03-04 | ESTADO: y")
    assert clave_grupo("HOMONIMIA", "Ing. Ana Rojas") == clave_grupo("HOMONIMIA", "ANA ROJAS")
