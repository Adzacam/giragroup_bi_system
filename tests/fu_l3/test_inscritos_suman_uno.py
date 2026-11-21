"""
FU-L3 (A): una inscripción suma 1 en fact_marketing.inscritos y recargar el libro no duplica.

La tabla de inscripciones trae UNA fila por inscripción. La DW viva tenía el doble por año (7.102 frente a 3.551 en 2023).
"""

import pytest
from sqlalchemy import text

from tests.fixtures.fuentes_sinteticas import captacion as cap
from tests.fu_l3.conftest import cargar_libro


def inscritos_por_anio(db):
    filas = db.execute(text("SELECT t.gestion, SUM(f.inscritos) FROM fact_marketing f JOIN dim_tiempo t ON t.id_tiempo = f.id_tiempo "
                            "GROUP BY t.gestion")).fetchall()
    return {int(g): int(s) for g, s in filas}


def inscritos_por_programa_y_mes(db):
    filas = db.execute(text("SELECT m.pos_code, t.periodo_mes, SUM(f.inscritos) FROM fact_marketing f "
                            "JOIN dim_modulo m ON m.id_modulo = f.id_modulo JOIN dim_tiempo t ON t.id_tiempo = f.id_tiempo "
                            "GROUP BY m.pos_code, t.periodo_mes")).fetchall()
    return {(p, mes): int(s) for p, mes, s in filas}


@pytest.mark.parametrize("tipo", ["MARKETING", "ADMISION"])
def test_una_inscripcion_suma_uno(dw_a, entorno, tipo):
    cargar_libro(dw_a, cap.construir_inscripciones(entorno), tipo_fuente=tipo, tipo_escala=None)
    assert inscritos_por_anio(dw_a) == cap.INSCRITOS_POR_ANIO
    assert dw_a.execute(text("SELECT SUM(inscritos) FROM fact_marketing")).scalar() == len(cap.INSCRIPCIONES)


def test_las_inscripciones_van_al_programa_y_mes_de_la_fila(dw_a, entorno):
    cargar_libro(dw_a, cap.construir_inscripciones(entorno), tipo_fuente="MARKETING", tipo_escala=None)
    esperado = {}
    for _, _, _, pos, fecha in cap.INSCRIPCIONES:
        k = (pos, fecha[:7])
        esperado[k] = esperado.get(k, 0) + 1
    assert inscritos_por_programa_y_mes(dw_a) == esperado


def test_recargar_el_mismo_libro_no_duplica(dw_a, entorno):
    ruta = cap.construir_inscripciones(entorno)
    cargar_libro(dw_a, ruta, tipo_fuente="MARKETING", tipo_escala=None)
    antes = (inscritos_por_anio(dw_a), inscritos_por_programa_y_mes(dw_a))
    cargar_libro(dw_a, ruta, tipo_fuente="MARKETING", tipo_escala=None)
    assert (inscritos_por_anio(dw_a), inscritos_por_programa_y_mes(dw_a)) == antes


def test_el_libro_con_otro_nombre_y_columnas_en_otro_orden_da_lo_mismo(dw_a, dw_b, entorno):
    cargar_libro(dw_a, cap.construir_inscripciones(entorno), tipo_fuente="MARKETING", tipo_escala=None)
    cargar_libro(dw_b, cap.construir_inscripciones(entorno, "altas_2027.xlsx", variante=True), tipo_fuente="MARKETING", tipo_escala=None)
    assert inscritos_por_anio(dw_a) == inscritos_por_anio(dw_b) == cap.INSCRITOS_POR_ANIO
    assert inscritos_por_programa_y_mes(dw_a) == inscritos_por_programa_y_mes(dw_b)


def _borrar(db, id_documento):
    from services.ingestion_service import IngestionService
    assert IngestionService.eliminar_fuente(db, id_documento)


def test_borrar_el_documento_y_volver_a_subir_el_libro_no_duplica(dw_a, entorno):
    """Causa raíz del x2 de la DW viva: el borrado dejaba las inscripciones y la re-subida las sumaba otra vez."""
    ruta = cap.construir_inscripciones(entorno)
    _, doc = cargar_libro(dw_a, ruta, tipo_fuente="MARKETING", tipo_escala=None)
    assert inscritos_por_anio(dw_a) == cap.INSCRITOS_POR_ANIO
    _borrar(dw_a, doc)
    assert dw_a.execute(text("SELECT COUNT(*) FROM fact_marketing")).scalar() == 0     # el borrado retira sus inscripciones
    cargar_libro(dw_a, ruta, tipo_fuente="MARKETING", tipo_escala=None)
    assert inscritos_por_anio(dw_a) == cap.INSCRITOS_POR_ANIO                           # y la re-subida vuelve a 1 por inscripción


def test_borrar_un_documento_no_toca_las_inscripciones_de_otro(dw_a, entorno):
    _, doc_a = cargar_libro(dw_a, cap.construir_inscripciones(entorno, "tabla_a.xlsx"), tipo_fuente="MARKETING", tipo_escala=None)
    _, doc_b = cargar_libro(dw_a, cap.construir_inscripciones(entorno, "tabla_b.xlsx", variante=True), tipo_fuente="MARKETING", tipo_escala=None)
    assert inscritos_por_anio(dw_a) == {2027: 2 * len(cap.INSCRIPCIONES)}   # dos documentos distintos: cada uno aporta sus filas
    _borrar(dw_a, doc_a)
    assert inscritos_por_anio(dw_a) == cap.INSCRITOS_POR_ANIO


def test_una_inscripcion_sin_fecha_valida_va_a_revision_y_no_queda_sin_mes(dw_a, entorno):
    import openpyxl
    from models.staging_entidad import StagingEntidadNoResuelta
    ruta = cap.construir_inscripciones(entorno)
    wb = openpyxl.load_workbook(ruta)
    ws = wb.active
    cab = [c.value for c in ws[1]]
    fila = {"MARCA TEMPORAL": "sin fecha", "NUMEROPROYECTO": "POS-9302", "NOMBRE DEL PROGRAMA": "DIPLOMADO FICTICIO 9302",
            "CI": "9300099", "NOMBRES": "NORA", "PATERNO": "SINFECHA", "ESTADO DEL INSCRITO": "ACTIVO"}
    ws.append([fila[c] for c in cab])
    wb.save(ruta)
    cargar_libro(dw_a, ruta, tipo_fuente="MARKETING", tipo_escala=None)
    assert inscritos_por_anio(dw_a) == cap.INSCRITOS_POR_ANIO                       # la fila sin fecha no suma a ningún año
    assert dw_a.execute(text("SELECT COUNT(*) FROM fact_marketing WHERE id_tiempo IS NULL")).scalar() == 0
    assert dw_a.query(StagingEntidadNoResuelta).filter_by(motivo="FECHA_INSCRIPCION_INVALIDA").count() == 1
