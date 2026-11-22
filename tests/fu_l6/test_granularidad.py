"""
FU-L6 (DA4): la granularidad de la meta (MENSUAL / ANUAL) sale de la FORMA de la fuente, no del año.

- una sola celda de meta en la hoja (por categoría y año) es una meta ANUAL y NO se coloca como meta de ningún mes;
- dos o más meses con meta son una meta MENSUAL (la hoja completa decide, no un bloque ni una fila);
- una hoja que solo cubre un mes no permite deducir una meta anual: se lee como mensual;
- una gestión sin meta no tiene granularidad (queda sin meta, sin bandera);
- el libro original y su variante (otro nombre de archivo y de hoja, columnas en otro orden) dan el mismo resultado.
"""

import pytest

from services import metas_canonica
from services.extraccion_por_encabezado import campos_por_encabezado, registros_rentabilidad
from tests.fixtures.fuentes_sinteticas import metas
from tests.fu_l6.conftest import cargar_libro, dw_a, dw_b, entorno, filas_rentabilidad  # noqa: F401


def _linea(cat, mes, **cols):
    celdas = [f"CATEGORIA: {cat}", f"MES NUMERICO: {mes}"] + [f"{k.replace('_', ' ')}: {v}" for k, v in cols.items()]
    return campos_por_encabezado(celdas)


def _perfil(*filas):
    return metas_canonica.perfilar(filas)


# ── Perfil de la hoja ─────────────────────────────────────────────────

def test_una_sola_celda_de_meta_es_anual_y_dos_o_mas_son_mensuales():
    filas = [_linea("TECHOS/CERRADOS", m, **{"EJECUTADO_2040": 100 + m, "META_POR_CATEGORIA_2040": 5000 if m == 12 else ""}) for m in range(1, 13)]
    filas = [{k: v for k, v in f.items() if v != ""} for f in filas]
    filas += [_linea("PROGRAMAS", m, **{"EJECUTADO_2040": 100, "META_POR_CATEGORIA_2040": 90}) for m in range(1, 13)]
    perfil = _perfil(*filas)
    assert perfil.granularidad("TECHOS_CERRADOS", 2040) == "ANUAL"
    assert perfil.granularidad("PROGRAMAS", 2040) == "MENSUAL"
    assert perfil.granularidad("PROGRAMAS", 2041) is None      # sin meta de ese año: sin granularidad


def test_el_perfil_no_depende_del_ano_ni_del_mes_donde_cae_la_celda():
    for anio, mes in ((2024, 12), (2031, 3), (2050, 7)):
        filas = [_linea("PROGRAMAS", m, **{f"EJECUTADO_{anio}": 10, f"META_POR_CATEGORIA_{anio}": 99 if m == mes else ""}) for m in range(1, 13)]
        perfil = _perfil(*[{k: v for k, v in f.items() if v != ""} for f in filas])
        assert perfil.granularidad("PROGRAMAS", anio) == "ANUAL", (anio, mes)


def test_hoja_de_un_solo_mes_se_lee_como_mensual():
    perfil = _perfil(_linea("PROGRAMAS", 3, **{"EJECUTADO_2040": 10, "META_POR_CATEGORIA_2040": 12}),
                     _linea("TECHOS/CERRADOS", 3, **{"EJECUTADO_2040": 1, "META_POR_CATEGORIA_2040": 2}))
    assert perfil.granularidad("PROGRAMAS", 2040) == "MENSUAL"
    assert perfil.granularidad("TECHOS_CERRADOS", 2040) == "MENSUAL"


def test_los_registros_llevan_la_granularidad_solo_con_perfil_y_solo_si_hay_meta():
    fila = _linea("TECHOS/CERRADOS", 12, **{"EJECUTADO_2040": 10, "META_POR_CATEGORIA_2040": 5000})
    sin_perfil = registros_rentabilidad(fila)
    assert [r["granularidad_meta"] for r in sin_perfil] == [None]
    filas = [_linea("TECHOS/CERRADOS", m, **{"EJECUTADO_2040": 10}) for m in range(1, 12)] + [fila]
    perfil = _perfil(*filas)
    reg = registros_rentabilidad(fila, perfil)
    assert [r["granularidad_meta"] for r in reg] == ["ANUAL"]
    solo_ejecutado = registros_rentabilidad(_linea("TECHOS/CERRADOS", 5, **{"EJECUTADO_2040": 10}), perfil)
    assert [r["granularidad_meta"] for r in solo_ejecutado] == [None]


def test_sinonimos_de_columna_salen_del_catalogo():
    """Las columnas «año» no están en el código: el catálogo (sección `metas.columnas`) las define."""
    assert metas_canonica.anio_de_columna("EJECUTADO 2032", "ejecutado") == 2032
    assert metas_canonica.anio_de_columna("META POR CATEGORIA 2031", "meta_especifica") == 2031
    assert metas_canonica.anio_de_columna("META 2032", "meta_generica") == 2032
    assert metas_canonica.anio_de_columna("EJEC. 2025", "ejecutado") is None         # total de todas las categorías: no es ejecutado por categoría
    assert metas_canonica.anio_de_columna("META 2025 2DO SEMESTRE", "meta_generica") is None
    assert "TIPO DE INGRESO" in metas_canonica.claves_categoria()


# ── Libro completo (ingesta + consolidación + DW) ─────────────────────

def _cargar(db, tmp_path, receta):
    ruta = metas.construir_rentabilidad(tmp_path, receta)
    return cargar_libro(db, ruta, tipo_fuente="RENTABILIDAD")


def test_libro_marca_granularidad_por_la_forma_y_no_coloca_la_meta_anual_en_diciembre(entorno, dw_a):
    _cargar(dw_a, entorno, metas.ORIGINAL)
    filas = filas_rentabilidad(dw_a)
    esperado = metas.esperado_rentabilidad()
    assert filas == esperado
    # la meta anual de 2031 es una sola celda y lleva la bandera ANUAL; ningún otro mes de 2031 trae meta
    anual = {k: v for k, v in filas.items() if k[1] == 2031 and v[1] is not None}
    assert list(anual) == [("TECHOS_CERRADOS", 2031, 12)] and anual[("TECHOS_CERRADOS", 2031, 12)][2] == "ANUAL"
    assert filas[("PROGRAMAS", 2031, 12)][1] is None                     # la meta anual no se copia a la otra categoría
    # 2030 no trae meta: ni meta ni bandera
    assert all(v[1] is None and v[2] is None for k, v in filas.items() if k[1] == 2030)
    # 2032 y 2033: meta mensual en cada mes
    assert all(v[2] == "MENSUAL" for k, v in filas.items() if k[1] in (2032, 2033) and v[1] is not None)
    assert sum(1 for k, v in filas.items() if k[1] == 2032 and v[1] is not None) == 24


def test_variante_con_otros_nombres_y_columnas_da_el_mismo_resultado(entorno, dw_a, dw_b):
    _cargar(dw_a, entorno, metas.ORIGINAL)
    _cargar(dw_b, entorno, metas.VARIANTE)
    assert filas_rentabilidad(dw_a) == filas_rentabilidad(dw_b)


def test_recargar_el_libro_no_duplica_ni_cambia_la_bandera(entorno, dw_a):
    _cargar(dw_a, entorno, metas.ORIGINAL)
    antes = filas_rentabilidad(dw_a)
    _cargar(dw_a, entorno, metas.ORIGINAL)
    assert filas_rentabilidad(dw_a) == antes
