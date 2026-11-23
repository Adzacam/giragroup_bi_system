"""Tests unitarios de BA-L3: defaults a3, ruteo <0.85 sin insertar y prioridad por banda 0.60."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from pipeline import config as cfg
from pipeline.semantic.indice_confianza import BANDA_CONSOLIDADO, BANDA_REVISION, BANDA_STAGING, clasificar_banda
from services import beto_integracion


def test_defaults_a3_activos(monkeypatch):
    for k in ("BETO_CASCADA_FINAL", "BETO_ACUERDO_QC", "BETO_SUGERENCIA_HITL", "BETO_VENTANA"):
        monkeypatch.delenv(k, raising=False)
    assert cfg.BETO_FLAGS_POR_DEFECTO["BETO_CASCADA_FINAL"] is True
    assert cfg.BETO_FLAGS_POR_DEFECTO["BETO_ACUERDO_QC"] is True
    assert cfg.BETO_FLAGS_POR_DEFECTO["BETO_SUGERENCIA_HITL"] is True
    assert cfg.BETO_FLAGS_POR_DEFECTO["BETO_VENTANA"] is False
    assert beto_integracion.activo("BETO_CASCADA_FINAL") is True
    assert beto_integracion.activo("BETO_ACUERDO_QC") is True
    assert beto_integracion.activo("BETO_SUGERENCIA_HITL") is True
    assert beto_integracion.activo("BETO_VENTANA") is False


def test_ruteo_nuevo_y_prioridad_por_banda_060():
    # >= 0.85 -> BANDA_CONSOLIDADO (pase directo si no hay desacuerdo ni relación inválida)
    assert clasificar_banda(0.85) == BANDA_CONSOLIDADO
    assert clasificar_banda(0.92) == BANDA_CONSOLIDADO

    # [0.60, 0.85) -> BANDA_REVISION -> va a bandeja sin insertar con prioridad MEDIA
    assert clasificar_banda(0.84) == BANDA_REVISION
    assert clasificar_banda(0.60) == BANDA_REVISION

    # < 0.60 -> BANDA_STAGING -> va a bandeja sin insertar con prioridad ALTA
    assert clasificar_banda(0.59) == BANDA_STAGING
    assert clasificar_banda(0.0) == BANDA_STAGING

    # Desacuerdo regla-BETO baja un escalón (0.95 -> 0.84, banda de revisión)
    bajado = beto_integracion.bajar_un_escalon(0.95)
    assert bajado == 0.84
    assert clasificar_banda(bajado) == BANDA_REVISION
