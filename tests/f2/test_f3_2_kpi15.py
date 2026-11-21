"""Pruebas unitarias del estado de cartera derivado (F3-2, reemplazadas por DA3 en FU-L2).

DA3 (decisión de Lean, 2026-11-20): Mora = cuotas_impagas >= 2. El tipo de cartera, los días de mora y el rango de
mora de la fuente ya no deciden la mora (antes bastaba un día de mora o un rango «d) Mayor 361»: KPI-05 ~ 94 %)."""

from routers.dataops.consolidacion import derivar_estado_cartera


def test_f3_2_cartera_incobrable_ya_no_decide_la_mora():
    assert derivar_estado_cartera({"TIPO DE CARTERA": "CARTERA INCOBRABLE", "DIAS DE MORA": "400"}) == "Vigente"


def test_f3_2_dias_de_mora_no_deciden_la_mora():
    assert derivar_estado_cartera({"TIPO DE CARTERA": "CARTERA CERRADA", "DIAS DE MORA": "14", "RANGO MORA": "0"}) == "Vigente"


def test_f3_2_rango_de_mora_no_decide_la_mora():
    assert derivar_estado_cartera({"TIPO DE CARTERA": "CARTERA CERRADA", "DIAS DE MORA": "", "RANGO MORA": "d) Mayor 361"}) == "Vigente"


def test_f3_2_mora_es_dos_o_mas_cuotas():
    assert derivar_estado_cartera({"TIPO DE CARTERA": "CARTERA VIGENTE"}, 1) == "Vigente"
    assert derivar_estado_cartera({"TIPO DE CARTERA": "CARTERA VIGENTE", "DIAS DE MORA": "", "RANGO MORA": "0"}) == "Vigente"
    assert derivar_estado_cartera({}, 0) == "Vigente"
    assert derivar_estado_cartera(None, 2) == "Mora"
