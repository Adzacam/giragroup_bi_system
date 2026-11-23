"""Pruebas de CAT-L5 y CAT-L7: catálogo paginado a 20, filtros, limpieza sin uso y convenios."""

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ / "backend") not in sys.path:
    sys.path.insert(0, str(RAIZ / "backend"))

from core.database import Base, CatalogBase
from models.catalogos import CatInstitucion, CatInstitucionConvenio
from models.dim_modulo import DimModulo
from models.fact_techo_convenio import FactTechoConvenio
from services.catalogo_dataops import consultar, preview_modulos_sin_uso, limpiar_modulos_sin_uso
from services.instituciones_convenio import canonizar_o_registrar_institucion, invalidar_cache_convenios


@pytest.fixture
def dbs():
    eng_dw = create_engine("sqlite:///:memory:").execution_options(schema_translate_map={"public": None})
    Base.metadata.create_all(eng_dw)
    DwSession = sessionmaker(bind=eng_dw)
    dw = DwSession()

    eng_cat = create_engine("sqlite:///:memory:").execution_options(schema_translate_map={"public": None})
    CatalogBase.metadata.create_all(eng_cat)
    CatSession = sessionmaker(bind=eng_cat)
    cat = CatSession()

    dw.add(CatInstitucion(id_institucion=361, nombre_institucion="GiraGroup Posgrado", sigla="GG"))
    m_en_uso = DimModulo(id_modulo=1, pos_code="POS-5001", nombre_modulo="Módulo Con Uso", programa="Diplomado BI", id_institucion=361)
    m_sin_prog = DimModulo(id_modulo=2, pos_code="POS-5002", nombre_modulo="Módulo Sin Programa", programa=None, id_institucion=361)
    m_gen = DimModulo(id_modulo=3, pos_code="ADM-GEN", nombre_modulo="Administración General", programa=None, id_institucion=361)
    dw.add_all([m_en_uso, m_sin_prog, m_gen])
    dw.flush()

    cat.add_all([
        CatInstitucionConvenio(id_convenio=1, nombre_institucion="ECOGUZ", variantes_origen="ECOGUZ"),
        CatInstitucionConvenio(id_convenio=2, nombre_institucion="IBNORCA", variantes_origen="IBNORCA"),
    ])
    cat.commit()

    dw.add(FactTechoConvenio(
        clave_convenio="k1",
        id_modulo=1,
        id_convenio_catalogo=1,
        institucion="ECOGUZ",
        n_inscritos=25,
        gestion=2025,
    ))
    dw.commit()
    invalidar_cache_convenios()
    try:
        yield dw, cat
    finally:
        dw.close()
        cat.close()


def test_canonizar_o_registrar_institucion_convenio(dbs):
    _, cat = dbs
    # Exacta / variante societaria
    canon, id_c, score, est = canonizar_o_registrar_institucion("ECOGUZ S.R.L.", db_catalog=cat)
    assert canon == "ECOGUZ"
    assert id_c == 1
    assert est == "EXACTA"

    # Fuzzy >= 90 %
    canon2, id_c2, score2, est2 = canonizar_o_registrar_institucion("IBNORCA BOL", db_catalog=cat)
    assert est2 in ("FUZZY_OK", "DUDOSA", "NUEVA_REGISTRADA")

    # Nueva institución válida -> se registra en cat_institucion_convenio
    canon3, id_c3, score3, est3 = canonizar_o_registrar_institucion("CAINCO SANTA CRUZ", db_catalog=cat)
    assert est3 == "NUEVA_REGISTRADA"
    assert id_c3 is not None
    assert cat.query(CatInstitucionConvenio).filter_by(id_convenio=id_c3).first() is not None


def test_consultar_modulos_paginacion_20_y_filtros(dbs):
    dw, _ = dbs
    res = consultar(dw, "modulos", page=1)
    assert res["pagination"]["page_size"] == 20
    assert res["pagination"]["total_items"] == 3
    por_id = {r["id"]: r for r in res["data"]}
    assert por_id[1]["en_uso"] == 1
    assert por_id[2]["en_uso"] == 0

    res_gen = consultar(dw, "modulos", solo_genericos=True)
    assert [r["id"] for r in res_gen["data"]] == [3]

    res_sin_prog = consultar(dw, "modulos", sin_programa=True)
    assert {r["id"] for r in res_sin_prog["data"]} == {2, 3}

    res_uso = consultar(dw, "modulos", uso="en_uso")
    assert [r["id"] for r in res_uso["data"]] == [1]

    res_sin_uso = consultar(dw, "modulos", uso="sin_uso")
    assert {r["id"] for r in res_sin_uso["data"]} == {2, 3}


def test_consultar_instituciones_propia_y_convenio(dbs):
    dw, cat = dbs
    res = consultar(dw, "instituciones", db_catalog=cat)
    assert res["pagination"]["page_size"] == 20
    assert res["grupos"] == {"propia": 1, "convenio": 2}
    conv_ecoguz = next(r for r in res["data"] if r["grupo"] == "convenio" and r["nombre"] == "ECOGUZ")
    assert conv_ecoguz["n_programas"] == 1
    assert conv_ecoguz["n_inscritos"] == 25
    assert conv_ecoguz["anios"] == [2025]

    res_propia = consultar(dw, "instituciones", grupo="propia", db_catalog=cat)
    assert len(res_propia["data"]) == 1
    assert res_propia["data"][0]["nombre"] == "GiraGroup Posgrado"


def test_limpiar_modulos_sin_uso_conserva_los_en_uso(dbs):
    dw, _ = dbs
    prev = preview_modulos_sin_uso(dw)
    assert prev["total_sin_uso"] == 2
    eliminados = limpiar_modulos_sin_uso(dw)
    assert eliminados == 2
    restantes = dw.query(DimModulo).all()
    assert [m.id_modulo for m in restantes] == [1]
