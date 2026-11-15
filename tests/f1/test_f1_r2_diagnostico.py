"""Pruebas mínimas de R-2 (scripts/f1_r2_diagnostico.py): bandas, emparejamiento por clave natural y regla técnica."""
from scripts.f1_r2_diagnostico import banda, emparejar, sql, veredicto_tecnico

import pytest


def _aca(**kw):
    base = {"tipo": "aca", "rid": "x", "archivo": "a.xlsx", "est_clave": "CI:1", "modulo_clave": "POS-1|M", "id_tiempo": 20250101,
            "nota": 90.0, "asistencia": None, "estado_academico": "Aprobado", "estado_tutoria": "Aprobado", "estado_arca": "Titulado",
            "est_ci_exacta": True, "estado_motivo": "OK"}
    base.update(kw)
    return base


def test_bandas_usan_los_umbrales_vigentes():
    assert banda(None) == "STAGING"
    assert banda(0.5999) == "STAGING"
    assert banda(0.60) == "REVISION"
    assert banda(0.8499) == "REVISION"
    assert banda(0.85) == "CONSOLIDADO"


def test_emparejar_es_multiconjunto():
    a = [_aca(rid="1"), _aca(rid="2"), _aca(rid="3", nota=50.0)]
    b = [_aca(rid="4"), _aca(rid="5", nota=70.0)]
    pares, solo_a, solo_b = emparejar(a, b)
    assert len(pares) == 1
    assert sorted(x["rid"] for x in solo_a) == ["2", "3"]
    assert [x["rid"] for x in solo_b] == ["5"]
    assert len(a) - len(solo_a) + len(solo_b) == len(b) - len(pares) + len(pares)  # suma cuadra


def test_veredicto_reglas_corroboran_y_fallan():
    assert veredicto_tecnico(_aca(), None)[0] == "revision_innecesaria_reglas_corroboran"
    v, _ = veredicto_tecnico(_aca(est_ci_exacta=False, id_tiempo=None), None)
    assert v == "revision_justificada_regla_falla:ci_exacta,fecha"
    stg = {"tipo": "stg", "tipo_fuente": "RENTABILIDAD", "encabezado_programa": True, "pos_en_catalogo": False}
    assert veredicto_tecnico(stg, None)[0] == "revision_justificada_regla_falla:pos_catalogo"
    stg_h = {"tipo": "stg", "tipo_fuente": "ACTA", "entidades": []}
    assert veredicto_tecnico(stg_h, _aca())[1] == "hecho_homologo_otra_corrida"


def test_sql_solo_bases_de_r2():
    with pytest.raises(ValueError):
        sql("giragroup_db", "SELECT 1")
    with pytest.raises(ValueError):
        sql("snapshot_dw_20261110_1201", "SELECT 1")
