"""
tests/test_elegir_tipo_fuente.py
--------------------------------
La SPA sólo reconoce ACTA, COBRANZA, ADMISION y MOODLE y su elección pisaba la detección por cabeceras:
Egresos y Techos entraban como COBRANZA y la evaluación docente como ACTA. Un genérico de la SPA cede
ante un tipo especializado detectado; un tipo especializado elegido a mano siempre manda.
"""

from services.ingestion_service import elegir_tipo_fuente


def test_generico_de_la_spa_cede_ante_tipo_especializado():
    assert elegir_tipo_fuente("COBRANZA", "RENTABILIDAD") == "RENTABILIDAD"
    assert elegir_tipo_fuente("ACTA", "EVALUACION_DOCENTE") == "EVALUACION_DOCENTE"


def test_eleccion_explicita_se_respeta_en_lo_demas():
    assert elegir_tipo_fuente("COBRANZA", "ACTA") == "COBRANZA"
    assert elegir_tipo_fuente("TECHOS", "MARKETING") == "TECHOS"
    assert elegir_tipo_fuente(None, "ADMISION") == "ADMISION"
    assert elegir_tipo_fuente("ACTA", None) == "ACTA"
