"""Pruebas unitarias F3-2 (KPI-15): mapeo de estado_cartera desde campos de BD Cobranzas."""

from routers.dataops.consolidacion import derivar_estado_cartera


def test_f3_2_cartera_incobrable_es_previsionable():
    assert derivar_estado_cartera({"TIPO DE CARTERA": "CARTERA INCOBRABLE", "DIAS DE MORA": "400"}) == "Previsionable"


def test_f3_2_mora_por_dias():
    assert derivar_estado_cartera({"TIPO DE CARTERA": "CARTERA CERRADA", "DIAS DE MORA": "14", "RANGO MORA": "0"}) == "Mora"


def test_f3_2_mora_por_rango():
    assert derivar_estado_cartera({"TIPO DE CARTERA": "CARTERA CERRADA", "DIAS DE MORA": "", "RANGO MORA": "d) Mayor 361"}) == "Mora"


def test_f3_2_vigente_por_defecto_y_nulos():
    assert derivar_estado_cartera({"TIPO DE CARTERA": "CARTERA VIGENTE", "DIAS DE MORA": "", "RANGO MORA": "0"}) == "Vigente"
    assert derivar_estado_cartera({}, 0) == "Vigente"
    assert derivar_estado_cartera(None, 2) == "Mora"
