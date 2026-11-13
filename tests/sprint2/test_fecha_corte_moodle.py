"""
tests/test_fecha_corte_moodle.py
--------------------------------
Moodle no exporta la fecha del curso: los 35 hechos del reporte quedaban sin fecha en la bandeja.
La fecha de corte es MOODLE_FECHA_CORTE si está configurada; si no, la fecha de descarga de la fila.
"""

from datetime import date

from services.extraccion_por_encabezado import campos_por_encabezado, fecha_de_fila

LINEA_MOODLE = (
    "First name: Carlos | Surname: Mendoza Ruiz | ID number: CI-1029384 | "
    "Course: POS-5376 - Maestría en Ciberseguridad | Grade/100.00: 88.50 | Status: Completed | "
    "Last downloaded from this course: 2026-09-15 14:30:00"
)


def _fecha(linea, categoria="academico"):
    return fecha_de_fila(campos_por_encabezado(linea.split(" | ")), categoria)


def test_moodle_usa_la_fecha_de_descarga_por_defecto(monkeypatch):
    monkeypatch.delenv("MOODLE_FECHA_CORTE", raising=False)
    assert _fecha(LINEA_MOODLE) == date(2026, 9, 15)


def test_moodle_fecha_de_corte_configurable(monkeypatch):
    monkeypatch.setenv("MOODLE_FECHA_CORTE", "2026-06-30")
    assert _fecha(LINEA_MOODLE) == date(2026, 6, 30)
    # Sin columna de descarga, la configuración igual aplica a las filas de Moodle
    assert _fecha(LINEA_MOODLE.rsplit(" | ", 1)[0]) == date(2026, 6, 30)


def test_fecha_de_corte_no_se_aplica_fuera_de_moodle(monkeypatch):
    monkeypatch.setenv("MOODLE_FECHA_CORTE", "2026-06-30")
    assert _fecha("NOMBRES: Ana Lucía | APELLIDO PATERNO: Torrez | MÓDULO 1: 78") is None
    assert _fecha("CI: 2560728 | NOMBRES: PEDRO PABLO | DEUDA TOTAL: 750", "financiero") is None
