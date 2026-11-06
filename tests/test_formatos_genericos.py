"""
tests/test_formatos_genericos.py
--------------------------------
El cargador debe reconocer cualquier archivo con la estructura de los reales, no sólo sus nombres exactos:
- Encuestas cuyas preguntas llevan ':' ('1: Docente explica claramente (1-5)'): se partían al leer
  'ENCABEZADO: valor' y toda la fila se descartaba como FILA_EVALUACION_SIN_RESPUESTAS.
- Ingresos agregados con categorías propias ('Inscripciones', 'Diplomados'): sólo se aceptaban PROGRAMAS y
  TECHOS_CERRADOS y el resto se descartaba como FILA_AGREGADA_SIN_CATEGORIA_MES.
"""

from datetime import date

from services.extraccion_por_encabezado import (
    campos_por_encabezado, categoria_rentabilidad, motivo_fila_sin_entidad, registros_evaluacion,
    registros_rentabilidad,
)


def _campos(linea: str):
    return campos_por_encabezado([c.strip() for c in linea.split(" | ")])


def test_encuesta_con_dos_puntos_en_la_pregunta_produce_respuestas():
    # Así queda la línea tras ingestion_service (': ' del encabezado -> ' - ')
    campos = _campos("NOMBRE COMPLETO: Lucía Quispe | FECHA: 04/11/2022 | PROGRAMA: Especialidad en Auditoría | "
                     "MODULO: 2 | 1 - Docente explica claramente (1-5): 5 | 2 - Docente domina temas del curso (1-5): 3")
    respuestas = registros_evaluacion(campos)
    assert len(respuestas) == 2
    assert {r["puntuacion"] for r in respuestas} == {5.0, 3.0}
    assert motivo_fila_sin_entidad(campos, "evaluacion_docente") is None


def test_categoria_de_ingreso_propia_se_conserva():
    assert categoria_rentabilidad("Inscripciones") == "INSCRIPCIONES"
    assert categoria_rentabilidad("Cursos cortos") == "CURSOS_CORTOS"
    assert categoria_rentabilidad("POR PROGRAMAS") == "PROGRAMAS"
    assert categoria_rentabilidad("TOTAL GENERAL") is None
    assert categoria_rentabilidad("79337") is None


def test_fila_mensual_con_categoria_propia_genera_un_registro_por_anio():
    campos = _campos("CATEGORIA: Diplomados | MES: Enero | MES NUMERICO: 1 | EJECUTADO 2023: 32592 | "
                     "META POR CATEGORIA 2024: 34343 | EJECUTADO 2024: 31552")
    regs = registros_rentabilidad(campos)
    assert {r["fecha"] for r in regs} == {date(2023, 1, 1), date(2024, 1, 1)}
    assert all(r["categoria_financiera"] == "DIPLOMADOS" for r in regs)
    assert motivo_fila_sin_entidad(campos, "rentabilidad") is None


def test_hoja_de_totales_sin_categoria_sigue_siendo_derivada():
    campos = _campos("MES: Enero | EJECUTADO 2023: 356842 | EJECUTADO 2024: 410987 | META 2025: 451025")
    assert registros_rentabilidad(campos) == []
