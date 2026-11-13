"""
docs/testing/skeletons/test_ner_thresholds.py
--------------------------------------------
Esqueleto de pruebas unitarias y de rendimiento para las compuertas de confianza del motor BETO NER.
Reglas:
- Banda ALTA: Score >= 0.85 -> Inserción directa en hechos del Data Warehouse.
- Banda MEDIA: Score en [0.60, 0.85) -> Derivado a Bandeja de Revisión Humana (HITL).
- Banda BAJA: Score < 0.60 -> Derivado a Staging no resuelto / Inconsistencia.
Marcador: unit, slow
"""

import pytest

BANDAS = {
    "ALTA": 0.85,
    "MEDIA": 0.60
}

def clasificar_banda_confianza(score: float) -> str:
    if score >= BANDAS["ALTA"]:
        return "CONSOLIDADO"
    elif score >= BANDAS["MEDIA"]:
        return "REVISION_HITL"
    else:
        return "STAGING_NO_RESUELTO"

@pytest.mark.unit
class TestNERConfidenceBands:

    def test_banda_alta_score_0_85_o_superior(self):
        """Un score de 0.85 exacto o superior se consolida directamente."""
        assert clasificar_banda_confianza(0.85) == "CONSOLIDADO"
        assert clasificar_banda_confianza(0.92) == "CONSOLIDADO"
        assert clasificar_banda_confianza(0.99) == "CONSOLIDADO"

    def test_banda_media_entre_0_60_y_0_849(self):
        """Scores entre 0.60 y 0.849 entran a bandeja de supervisión humana."""
        assert clasificar_banda_confianza(0.60) == "REVISION_HITL"
        assert clasificar_banda_confianza(0.75) == "REVISION_HITL"
        assert clasificar_banda_confianza(0.8499) == "REVISION_HITL"

    def test_banda_baja_inferior_a_0_60(self):
        """Scores bajo 0.60 son descartados a staging de entidades dudosas."""
        assert clasificar_banda_confianza(0.599) == "STAGING_NO_RESUELTO"
        assert clasificar_banda_confianza(0.30) == "STAGING_NO_RESUELTO"
        assert clasificar_banda_confianza(0.0) == "STAGING_NO_RESUELTO"

@pytest.mark.slow
def test_simulacion_carga_inferencia_batch():
    """Prueba lenta de extracción sobre 50 sentencias sintéticas."""
    sentencias = [f"Estudiante CI-{i:07d} asistió a Módulo de Arquitectura" for i in range(50)]
    assert len(sentencias) == 50
