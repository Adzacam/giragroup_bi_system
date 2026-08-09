"""
test_validator.py — Tests unitarios para la validación estructural (GIRA-50, GIRA-43)
"""

import pytest
from pipeline.normalization.validator import validar_rango_temporal, detectar_nulos_criticos
from pipeline.normalization.error_logger import ErrorLogger


class TestValidarRangoTemporal:
    """Tests para el rango cronológico estricto 2024-2026."""

    def test_gestion_2024_valida(self):
        assert validar_rango_temporal(2024) is True

    def test_gestion_2025_valida(self):
        assert validar_rango_temporal(2025) is True

    def test_gestion_2026_valida(self):
        assert validar_rango_temporal(2026) is True

    def test_gestion_2023_invalida(self):
        assert validar_rango_temporal(2023) is False

    def test_gestion_2027_invalida(self):
        assert validar_rango_temporal(2027) is False

    def test_gestion_string_valida(self):
        """String numérico se castea correctamente."""
        assert validar_rango_temporal("2025") is True

    def test_gestion_string_invalida(self):
        assert validar_rango_temporal("2023") is False

    def test_gestion_none(self):
        assert validar_rango_temporal(None) is False

    def test_gestion_texto_no_numerico(self):
        assert validar_rango_temporal("abc") is False

    def test_gestion_cero(self):
        assert validar_rango_temporal(0) is False


class TestDetectarNulosCriticos:
    """Tests para la detección de ausencia de llaves naturales."""

    def test_registro_completo(self):
        """Registro con todas las llaves presentes → sin nulos."""
        registro = {"ci": "12345", "codigo_estudiante": "EST001", "nombre_completo": "Juan Perez"}
        assert detectar_nulos_criticos(registro) == []

    def test_ci_nulo(self):
        """CI es None → se reporta como nulo."""
        registro = {"ci": None, "nombre_completo": "Juan Perez"}
        nulos = detectar_nulos_criticos(registro)
        assert "ci" in nulos

    def test_ci_vacio(self):
        """CI es string vacío → se reporta como nulo."""
        registro = {"ci": "   ", "nombre_completo": "Juan Perez"}
        nulos = detectar_nulos_criticos(registro)
        assert "ci" in nulos

    def test_multiples_nulos(self):
        """Múltiples campos nulos se reportan todos."""
        registro = {"ci": None, "codigo_estudiante": "", "nombre_completo": "   ", "codigo": None}
        nulos = detectar_nulos_criticos(registro)
        assert len(nulos) == 4

    def test_campo_no_presente_no_se_reporta(self):
        """Campos que no existen en el registro no se reportan."""
        registro = {"otra_columna": "valor"}
        assert detectar_nulos_criticos(registro) == []

    def test_campo_con_valor_numerico(self):
        """Valores numéricos no se consideran vacíos."""
        registro = {"ci": 12345, "codigo": 0}
        assert detectar_nulos_criticos(registro) == []


class TestErrorLogger:
    """Tests para el acumulador de errores in-memory."""

    def test_registrar_y_exportar(self):
        logger = ErrorLogger("test_archivo.csv")
        logger.registrar_error(0, "Campo CI nulo")
        logger.registrar_error(5, "Gestión fuera de rango: 2023")

        reporte = logger.exportar_reporte()
        assert len(reporte) == 2
        assert reporte[0]["fila_id"] == 0
        assert reporte[0]["mensaje"] == "Campo CI nulo"
        assert reporte[0]["archivo"] == "test_archivo.csv"
        assert reporte[1]["fila_id"] == 5

    def test_total_errores(self):
        logger = ErrorLogger("archivo.xlsx")
        assert logger.total_errores == 0
        logger.registrar_error(0, "Error 1")
        logger.registrar_error(1, "Error 2")
        assert logger.total_errores == 2

    def test_limpiar(self):
        logger = ErrorLogger("archivo.xlsx")
        logger.registrar_error(0, "Error")
        logger.limpiar()
        assert logger.total_errores == 0
        assert logger.exportar_reporte() == []

    def test_nombre_archivo(self):
        logger = ErrorLogger("datos_cobranzas.csv")
        assert logger.nombre_archivo == "datos_cobranzas.csv"

    def test_logger_vacio(self):
        logger = ErrorLogger()
        assert logger.exportar_reporte() == []
        assert logger.total_errores == 0
