"""
FU-L6 (DA4): el cálculo local de KPIService (sin vistas bi, o con filtro de programa) coincide con la regla de la vista:
KPI-02 solo con meta MENSUAL y sobre el último mes CERRADO (el de corte de la fuente es parcial, salvo diciembre).
Y el motivo «sin dato» del KPI-02 explica si la fuente solo trae meta anual o ninguna.
"""

import pytest

from services import metas_cobertura, metas_canonica
from services.kpi_service import KPIService
from tests.fixtures.fuentes_sinteticas import metas
from tests.fu_l6.conftest import cargar_libro, dw_a, entorno  # noqa: F401


def _suma(anio, mes, fn):
    return sum(fn(c, anio, mes) for c in metas.CATEGORIAS)


@pytest.fixture
def dw_metas(entorno, dw_a):
    cargar_libro(dw_a, metas.construir_rentabilidad(entorno, metas.ORIGINAL), tipo_fuente="RENTABILIDAD")
    return dw_a


def _kpi02(db, gestion):
    res = KPIService(db).obtener_perspectivas_cmi_completo(gestion=gestion)
    assert res["fuente"] == "calculo_local (sin vistas bi)"
    return res["perspectivas"]["financiera"]["cumplimiento_metas_mensual_pct"]


def test_kpi02_local_sin_meta_mensual_queda_sin_dato(dw_metas):
    assert _kpi02(dw_metas, 2030) is None       # sin meta alguna
    assert _kpi02(dw_metas, 2031) is None       # solo una celda de meta anual: no es la meta de diciembre


def test_kpi02_local_con_meta_mensual_usa_el_ultimo_mes_cerrado(dw_metas):
    esperado_2032 = 100.0 * _suma(2032, 12, metas.ejecutado) / _suma(2032, 12, metas.meta_mensual)
    assert _kpi02(dw_metas, 2032) == pytest.approx(esperado_2032, abs=0.01)
    # 2033: el corte de la fuente es mayo (parcial); el último mes cerrado es abril
    esperado_2033 = 100.0 * _suma(2033, 4, metas.ejecutado) / _suma(2033, 4, metas.meta_mensual)
    assert _kpi02(dw_metas, 2033) == pytest.approx(esperado_2033, abs=0.01)


def test_motivo_sin_dato_del_kpi02(dw_metas):
    assert metas_cobertura.motivo_sin_dato_kpi02(dw_metas, 2031) == "La fuente solo trae meta anual."
    assert metas_cobertura.motivo_sin_dato_kpi02(dw_metas, 2030) == "No hay meta cargada para esta gestión."
    assert metas_cobertura.motivo_sin_dato_kpi02(dw_metas, 2099) == "No hay meta cargada para esta gestión."   # sin filas de la gestión
    assert metas_cobertura.motivo_sin_dato_kpi02(dw_metas, 2032) == metas_canonica.motivo_sin_dato("kpi_02_sin_mes_cerrado")


def test_los_textos_sin_dato_salen_del_catalogo(dw_metas, monkeypatch):
    base = metas_canonica._config()
    cambiada = {**base, "metas": {**base["metas"], "motivos_sin_dato": {**base["metas"]["motivos_sin_dato"], "kpi_02_solo_anual": "Solo meta anual."}}}
    monkeypatch.setattr(metas_canonica, "_config", lambda: cambiada)
    assert metas_cobertura.motivo_sin_dato_kpi02(dw_metas, 2031) == "Solo meta anual."
