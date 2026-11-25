"""Pruebas unitarias F9-1a: regla estricta en fila_resuelta_por_regla para marketing/admision y financiero."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
for p in (str(RAIZ), str(RAIZ / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from services.extraccion_por_encabezado import fila_resuelta_por_regla


def test_marketing_admision_completa_resuelta_por_regla():
    campos = {
        "CI": "6543269",
        "NOMBRE COMPLETO": "Lucia Salas Nina",
        "NUMEROPROYECTO": "POS-5510",
    }
    assert fila_resuelta_por_regla(campos, "marketing") is True
    assert fila_resuelta_por_regla(campos, "admision") is True


def test_marketing_admision_residuales_pasan_a_beto():
    sin_ci = {"NOMBRE COMPLETO": "Lucia Salas Nina", "NUMEROPROYECTO": "POS-5510"}
    ci_dudosa = {"CI": "123?", "NOMBRE COMPLETO": "Lucia Salas Nina", "NUMEROPROYECTO": "POS-5510"}
    ci_temp = {"CI": "TEMP-123456", "NOMBRE COMPLETO": "Lucia Salas Nina", "NUMEROPROYECTO": "POS-5510"}
    sin_programa = {"CI": "6543269", "NOMBRE COMPLETO": "Lucia Salas Nina"}
    sin_nombre = {"CI": "6543269", "NUMEROPROYECTO": "POS-5510"}

    for caso in (sin_ci, ci_dudosa, ci_temp, sin_programa, sin_nombre):
        assert fila_resuelta_por_regla(caso, "marketing") is False
        assert fila_resuelta_por_regla(caso, "admision") is False


def test_financiero_completo_resuelto_por_regla():
    campos = {
        "CI": "7771148-1C",
        "NOMBRE COMPLETO": "Carlos Perez Gomez",
        "MONTO DEUDA": "1500.50",
        "CUOTAS IMPAGAS": "2",
    }
    assert fila_resuelta_por_regla(campos, "financiero") is True


def test_financiero_residuales_pasan_a_beto():
    sin_ci = {"NOMBRE COMPLETO": "Carlos Perez Gomez", "MONTO DEUDA": "1500"}
    ci_dudosa = {"CI": "123?", "NOMBRE COMPLETO": "Carlos Perez Gomez", "MONTO DEUDA": "1500"}
    sin_fin = {"CI": "7771148", "NOMBRE COMPLETO": "Carlos Perez Gomez", "OBSERVACION": "En seguimiento"}
    fin_texto = {"CI": "7771148", "NOMBRE COMPLETO": "Carlos Perez Gomez", "MONTO DEUDA": "por definir"}

    for caso in (sin_ci, ci_dudosa, sin_fin, fin_texto):
        assert fila_resuelta_por_regla(caso, "financiero") is False
