"""
tests/test_fk_resolver_padron.py
--------------------------------
TBL_INSCRITOS no tiene columna de nombre completo: el padrón de FKResolver debe armar el nombre con
NOMBRES + PATERNO + MATERNO. Antes tomaba 'NOMBRE DEL PROGRAMA' y todo rescate por nombre caía en estado C.
"""

import pandas as pd
import pytest

from pipeline.normalization.fk_resolver import FKResolver


@pytest.fixture
def padron_tipo_inscritos(tmp_path):
    ruta = tmp_path / "TBL_INSCRITOS.xlsx"
    pd.DataFrame({
        "NUMEROPROYECTO": ["POS-4800", "POS-5361"],
        "NOMBRE DEL PROGRAMA": ["CURSO EN ATENCIÓN AL CLIENTE", "DIPLOMADO EN FINANZAS CORPORATIVAS"],
        "CI": ["9453509", "6080650"],
        "NOMBRES": ["Nataly", "Vivian Scarlet"],
        "PATERNO": ["Caero", "Bustillo"],
        "MATERNO": ["Foronda", "Barrientos"],
    }).to_excel(ruta, index=False)
    return ruta


def test_padron_usa_nombre_del_inscrito_y_no_el_programa(padron_tipo_inscritos):
    fk = FKResolver(padron_tipo_inscritos)
    originales = set(fk.nombres_originales.values())
    assert originales == {"Nataly Caero Foronda", "Vivian Scarlet Bustillo Barrientos"}
    assert not any("DIPLOMADO" in n.upper() or "CURSO" in n.upper() for n in originales)


def test_sin_ci_se_rescata_por_nombre_en_estado_b(padron_tipo_inscritos):
    res = FKResolver(padron_tipo_inscritos).resolver_estudiante(nombre="NATALY CAERO FORONDA", ci_candidato=None)
    assert res["fk_estado"] == "B"
    assert res["ci"] == "9453509"


def test_padron_con_nombre_completo_sigue_funcionando(tmp_path):
    ruta = tmp_path / "padron.xlsx"
    pd.DataFrame({"CI": ["4859201"], "NOMBRE COMPLETO": ["Ana Lucía Torrez Rojas"]}).to_excel(ruta, index=False)
    res = FKResolver(ruta).resolver_estudiante(nombre="Ana Lucia Torrez Rojas", ci_candidato=None)
    assert res["fk_estado"] == "B" and res["ci"] == "4859201"
