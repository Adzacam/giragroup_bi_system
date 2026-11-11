"""
Pruebas automatizadas para AsymmetricFlattener, Catálogo Maestro Institucional (Zero PII)
y el endpoint GET /api/v1/catalogs/institutional-summary.
"""

import io
import pytest
from openpyxl import Workbook

from pipeline.normalization.asymmetric_flattener import AsymmetricFlattener
from pipeline.normalization.catalog_repository import (
    PROGRAMAS_ACTIVOS_INSTITUCIONALES,
    obtener_resumen_institucional,
)


def test_catalogo_maestro_institucional_zero_pii():
    """Valida que el catálogo maestro contenga 18 programas y 0 PII de estudiantes."""
    resumen = obtener_resumen_institucional()
    assert resumen["total_programas_activos"] == 18
    assert resumen["sin_pii"] is True
    assert len(resumen["programas"]) == 18

    # Verificar que ningún programa contenga campos de estudiantes ni PII
    for p in resumen["programas"]:
        assert "estudiante" not in p
        assert "ci" not in p
        assert "nombre_estudiante" not in p
        assert "pos_code" in p
        assert "nombre" in p
        assert "arancel_base_bs" in p
        assert p["arancel_base_bs"] > 0
        assert p["modulos_count"] >= 2


def test_asymmetric_flattener_unmerging_and_dates():
    """Valida la descombinación de celdas A1:F2 y la inferencia automática de fechas 2024-2026."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Acta Notas"

    # Fila combinada A1:F2
    ws.merge_cells("A1:F2")
    ws["A1"] = "MAESTRÍA EN BUSINESS INTELLIGENCE Y BIG DATA"

    # Metadatos en fila 3
    ws["A3"] = "Docente:"
    ws["B3"] = "Dr. Ramiro Morales"
    ws["C3"] = "Gestión:"
    ws["D3"] = "2024 - 2026"

    # Cabecera desplazada en fila 5
    ws["A5"] = "CI"
    ws["B5"] = "Estudiante"
    ws["C5"] = "Modulo"
    ws["D5"] = "Nota"
    ws["E5"] = "Asistencia"
    ws["F5"] = "Fecha"

    # Datos en fila 6 y 7
    ws["A6"] = "1234567"
    ws["B6"] = "Carlos Perez"
    ws["C6"] = "Mineria de Datos"
    ws["D6"] = 85
    ws["E6"] = 90
    ws["F6"] = "15/03/2025"

    ws["A7"] = "7654321"
    ws["B7"] = "Ana Gomez"
    ws["C7"] = "Mineria de Datos"
    ws["D7"] = 92
    ws["E7"] = 95
    ws["F7"] = "10/04/2025"

    # Subtotal en fila 8
    ws["A8"] = "Promedio General"
    ws["D8"] = 88.5

    stream = io.BytesIO()
    wb.save(stream)
    excel_bytes = stream.getvalue()

    resultado = AsymmetricFlattener.procesar_archivo_asimetrico(excel_bytes, "acta_notas_unifranz.xlsx")

    assert resultado["origen_detectado"] == "GSHEETS_ACTA_NOTAS"
    assert "2024" in resultado["rango_fechas"] or "2025" in resultado["rango_fechas"] or "2026" in resultado["rango_fechas"]

    diag = resultado["diagnostico_estructural"]
    assert len(diag["celdas_combinadas"]) >= 1
    assert any("A1" in c["rango"] for c in diag["celdas_combinadas"])
    assert diag["fila_cabecera_desplazada"] == 5
    assert diag["filas_subtotales_descartadas"] >= 1

    # Chips de catálogo maestro
    chips = resultado["chips_catalogo"]
    assert "programa_cat" in chips
    assert "modulo_cat" in chips
    assert "precio_base_cat" in chips
    assert "Business Intelligence" in chips["programa_cat"] or "POS-5308" in chips["programa_cat"]


def test_asymmetric_flattener_multisheet_cover_page():
    """
    Valida el caso límite donde la Hoja 1 es una carátula/gráfico (<= 1 fila)
    y la Hoja 2 contiene la tabla asimétrica real con celdas combinadas.
    """
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Caratula"
    ws1["A1"] = "Informe General de Evaluaciones"

    ws2 = wb.create_sheet(title="DetalleNotas")
    ws2.merge_cells("A1:E2")
    ws2["A1"] = "DIPLOMADO EN GESTIÓN DE PROYECTOS DE TECNOLOGÍA"

    ws2["A4"] = "CI"
    ws2["B4"] = "Estudiante"
    ws2["C4"] = "Modulo"
    ws2["D4"] = "Nota"
    ws2["E4"] = "Fecha"

    ws2["A5"] = "5544332"
    ws2["B5"] = "Maria Lopez"
    ws2["C5"] = "Metodologias Agiles"
    ws2["D5"] = 90
    ws2["E5"] = "20/05/2026"

    stream = io.BytesIO()
    wb.save(stream)
    excel_bytes = stream.getvalue()

    resultado = AsymmetricFlattener.procesar_archivo_asimetrico(excel_bytes, "diplomado_notas.xlsx")

    assert resultado["diagnostico_estructural"]["fila_cabecera"] == 4
    assert len(resultado["diagnostico_estructural"]["celdas_combinadas"]) >= 1
    assert "2026" in resultado["rango_fechas"]


def test_asymmetric_flattener_multilevel_headers_and_subtotals():
    """Valida aplanamiento de cabeceras multinivel de hasta 3 filas y descarte de subtotales."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Acta Multinivel"

    # Fila 2: Categoría superior
    ws["C2"] = "EVALUACION TEORICA"
    ws["D2"] = "EVALUACION PRACTICA"

    # Fila 3: Subcategoría
    ws["C3"] = "Examen Parcial"
    ws["D3"] = "Proyecto Final"

    # Fila 4: Cabecera base
    ws["A4"] = "CI"
    ws["B4"] = "Alumno"
    ws["C4"] = "Nota 1"
    ws["D4"] = "Nota 2"

    ws["A5"] = "9988776"
    ws["B5"] = "Pedro Suarez"
    ws["C5"] = 80
    ws["D5"] = 85

    ws["A6"] = "Promedio General del Curso"
    ws["C6"] = 82.5

    stream = io.BytesIO()
    wb.save(stream)
    excel_bytes = stream.getvalue()

    resultado = AsymmetricFlattener.procesar_archivo_asimetrico(excel_bytes, "acta_multinivel.xlsx")

    diag = resultado["diagnostico_estructural"]
    assert diag["fila_cabecera"] == 4
    assert diag["encabezados_multinivel_aplanados"] >= 1
    assert diag["filas_subtotales_descartadas"] >= 1
    assert any("multinivel" in adv.lower() for adv in diag["advertencias_estructurales"])
    assert any("subtotales" in adv.lower() for adv in diag["advertencias_estructurales"])


def test_asymmetric_flattener_csv_with_semicolon_and_preamble():
    """Valida lectura de CSV con punto y coma (;), preámbulo desplazado y fechas."""
    csv_content = (
        "Reporte institucional no estructurado\n"
        "Periodo Academico: 2024 - 2026\n"
        "\n"
        "CI;Estudiante;Modulo;Monto;Fecha\n"
        "12345;Juan Perez;Analitica;1500;12/03/2025\n"
        "67890;Laura Torres;Analitica;1500;14/03/2025\n"
    ).encode("utf-8")

    resultado = AsymmetricFlattener.procesar_archivo_asimetrico(csv_content, "pagos_banco.csv")

    assert resultado["origen_detectado"] == "GFORMS_ADM_PAGOS"
    diag = resultado["diagnostico_estructural"]
    assert diag["fila_cabecera"] == 4
    assert "2024" in resultado["rango_fechas"] or "2025" in resultado["rango_fechas"]

