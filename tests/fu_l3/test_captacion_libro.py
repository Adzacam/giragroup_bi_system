"""
FU-L3 (DA6): captación de punta a punta (ingesta -> consolidación -> DW SQLite) con libros sintéticos de datos ficticios.

- los campos leads / inscritos de captación salen por sinónimos de CUALQUIER hoja programa x mes: hojas mensuales
  visibles, hojas ocultas rescatadas y la tabla por programa (IBP) dentro de un libro de actas;
- solo cuentan filas con ambos datos y 0 <= inscritos <= leads; las reservas se guardan y no entran en el KPI;
- un mismo POS y mes en varias hojas cuenta una vez, con prioridad a la hoja de detalle visible;
- las ocultas repetidas y los borradores no cuentan;
- recargar no duplica y el orden de carga de los libros no cambia el resultado;
- el libro con otros nombres, columnas en otro orden y otros sinónimos da el mismo resultado.
"""

import pytest
from sqlalchemy import text

from tests.fixtures.fuentes_sinteticas import captacion as cap
from tests.fu_l3.conftest import cargar_libro


def captacion_por_programa_y_mes(db):
    filas = db.execute(text(
        "SELECT m.pos_code, t.periodo_mes, f.leads_captacion, f.inscritos_captacion FROM fact_marketing f "
        "JOIN dim_modulo m ON m.id_modulo = f.id_modulo JOIN dim_tiempo t ON t.id_tiempo = f.id_tiempo "
        "WHERE f.leads_captacion IS NOT NULL")).fetchall()
    return {(p, mes): (int(l), int(i)) for p, mes, l, i in filas}


def captacion_por_mes(db):
    """Lo que ve el KPI-06 (la regla de la migración 014 aplicada a fact_marketing)."""
    filas = db.execute(text(
        "SELECT t.periodo_mes, SUM(f.leads_captacion), SUM(f.inscritos_captacion) FROM fact_marketing f "
        "JOIN dim_tiempo t ON t.id_tiempo = f.id_tiempo WHERE f.leads_captacion > 0 AND f.inscritos_captacion >= 0 "
        "AND f.inscritos_captacion <= f.leads_captacion GROUP BY t.periodo_mes")).fetchall()
    return {mes: (int(l), int(i)) for mes, l, i in filas}


def reservas_guardadas(db):
    filas = db.execute(text("SELECT pos_code_fuente, hoja, reservas_fuente FROM fact_planificacion_programa "
                            "WHERE reservas_fuente IS NOT NULL")).fetchall()
    return {(p, h): float(r) for p, h, r in filas}


@pytest.fixture
def libro_plan(dw_a, entorno):
    ruta = cap.construir_plan(cap.ORIGINAL, entorno, con_ibp=True)
    cargar_libro(dw_a, ruta, tipo_fuente="PLANIFICACION")
    return dw_a


def test_cada_programa_y_mes_cuenta_una_vez_con_prioridad_a_la_hoja_de_detalle(libro_plan):
    assert captacion_por_programa_y_mes(libro_plan) == cap.ESPERADO


def test_kpi06_por_mes_sin_filas_incompletas_ni_inscritos_mayores_que_leads(libro_plan):
    por_mes = captacion_por_mes(libro_plan)
    assert por_mes == cap.ESPERADO_MES
    # el 9302 de marzo no tiene inscritos en el detalle visible: la tabla por programa aporta su par válido (70, 7)
    assert por_mes["2027-03"] == (100 + 50 + 40 + 70, 10 + 5 + 0 + 7)
    # 9303 (inscritos > leads) y 9500 (sin inscritos) no cuentan
    assert ("POS-9303", "2027-03") not in captacion_por_programa_y_mes(libro_plan)
    assert ("POS-9500", "2027-06") not in captacion_por_programa_y_mes(libro_plan)


def test_cero_inscritos_es_una_conversion_real_de_cero(libro_plan):
    assert captacion_por_programa_y_mes(libro_plan)[("POS-9304", "2027-03")] == (40, 0)


def test_oculta_rescatada_cuenta_y_oculta_repetida_y_borrador_no(libro_plan):
    por_pm = captacion_por_programa_y_mes(libro_plan)
    assert por_pm[("POS-9100", "2027-01")] == (60, 6)                      # oculta sin hoja visible: se rescata
    assert all(l not in (7777, 8888) for l, _ in por_pm.values())          # la oculta repetida no suma
    assert ("POS-9200", "2027-02") not in por_pm                            # el borrador no suma


def test_las_reservas_se_guardan_como_dato_del_embudo_y_no_entran_al_kpi(libro_plan):
    reservas = reservas_guardadas(libro_plan)
    assert reservas[("POS-9300", cap.ORIGINAL.visible)] == 4
    assert reservas[("POS-9301", cap.ORIGINAL.visible)] == 2
    # ninguna cifra del KPI incluye reservas: leads 100 + 50 + 40 + 70 en marzo
    assert captacion_por_mes(libro_plan)["2027-03"][0] == 260
    # y fact_marketing no guarda reservas de la planificación (no se mezclan con las del embudo individual)
    assert libro_plan.execute(text("SELECT COALESCE(SUM(reservas), 0) FROM fact_marketing")).scalar() == 0


def test_la_tabla_por_programa_obtiene_pos_y_periodo_por_sinonimos(libro_plan):
    filas = libro_plan.execute(text(
        "SELECT pos_code_fuente, id_tiempo_plan FROM fact_planificacion_programa WHERE hoja = :h"),
        {"h": cap.ORIGINAL.por_programa}).fetchall()
    assert len(filas) == len(cap.IBP)
    assert all(p and t for p, t in filas)       # antes entraban sin período ni POS


def test_recargar_el_mismo_libro_no_duplica(dw_a, entorno):
    ruta = cap.construir_plan(cap.ORIGINAL, entorno)
    cargar_libro(dw_a, ruta, tipo_fuente="PLANIFICACION")

    def huella():
        return (captacion_por_programa_y_mes(dw_a), dw_a.execute(text("SELECT COUNT(*) FROM fact_marketing")).scalar(),
                dw_a.execute(text("SELECT COUNT(*) FROM fact_planificacion_programa")).scalar())

    antes = huella()
    cargar_libro(dw_a, ruta, tipo_fuente="PLANIFICACION")
    assert huella() == antes


def test_la_variante_con_otros_nombres_columnas_y_sinonimos_da_lo_mismo(dw_a, dw_b, entorno):
    ruta_a = cap.construir_plan(cap.ORIGINAL, entorno)
    ruta_b = cap.construir_plan(cap.VARIANTE, entorno)
    assert ruta_a.name != ruta_b.name
    cargar_libro(dw_a, ruta_a, tipo_fuente="PLANIFICACION")
    cargar_libro(dw_b, ruta_b, tipo_fuente="PLANIFICACION")
    assert captacion_por_programa_y_mes(dw_a) == captacion_por_programa_y_mes(dw_b) == cap.ESPERADO
    assert captacion_por_mes(dw_a) == captacion_por_mes(dw_b)


# ── La tabla por programa dentro de un libro de actas (como en la fuente real) ────────────────

def _cargar_en_orden(db, entorno, receta, primero):
    plan = cap.construir_plan(receta, entorno, con_ibp=False)
    acta = cap.construir_acta_con_ibp(receta, entorno)
    orden = [(plan, "PLANIFICACION"), (acta, "ACTA")]
    for ruta, tipo in (orden if primero == "plan" else orden[::-1]):
        cargar_libro(db, ruta, tipo_fuente=tipo)


@pytest.mark.parametrize("primero", ["plan", "acta"])
def test_tabla_por_programa_de_un_libro_de_actas_se_deduplica_sin_importar_el_orden(dw_a, entorno, primero):
    _cargar_en_orden(dw_a, entorno, cap.ORIGINAL, primero)
    assert captacion_por_programa_y_mes(dw_a) == cap.ESPERADO
    assert captacion_por_mes(dw_a) == cap.ESPERADO_MES


def test_el_libro_de_actas_con_otros_nombres_y_sinonimos_da_lo_mismo(dw_a, dw_b, entorno):
    _cargar_en_orden(dw_a, entorno, cap.ORIGINAL, "plan")
    _cargar_en_orden(dw_b, entorno, cap.VARIANTE, "acta")
    assert captacion_por_programa_y_mes(dw_a) == captacion_por_programa_y_mes(dw_b) == cap.ESPERADO


def test_el_acta_no_pierde_sus_hechos_por_traer_una_hoja_de_planificacion(dw_a, entorno):
    acta = cap.construir_acta_con_ibp(cap.ORIGINAL, entorno)
    cargar_libro(dw_a, acta, tipo_fuente="ACTA")
    assert dw_a.execute(text("SELECT COUNT(*) FROM fact_rendimiento_academico")).scalar() == 2


def test_un_sinonimo_nuevo_en_el_catalogo_basta_sin_tocar_codigo():
    """Añadir un sinónimo de leads en el catálogo hace leer la cabecera nueva sin cambiar código."""
    from pipeline import lector_hojas
    from services import captacion_canonica as capt

    sinonimos = lector_hojas.cargar_config()["tipos_fuente"]["PLANIFICACION"]["campos"]["leads_captacion"]["sinonimos"]
    nuevo = {"texto": "clientes potenciales", "prioridad": 1}
    assert capt.campo_de_cabecera("Clientes potenciales") is None
    sinonimos.append(nuevo)
    capt.recargar_catalogo()
    try:
        assert capt.campo_de_cabecera("Clientes potenciales")[0] == "leads_captacion"
        f = capt.leer_fila({"POS": "5000", "ANO": "2026", "MES": "2", "CLIENTES POTENCIALES": "30", "INSCRITOS": "3"})
        assert f.valida and f.leads == 30
    finally:
        sinonimos.remove(nuevo)
        capt.recargar_catalogo()


def test_subir_el_libro_corregido_reemplaza_la_cifra_y_no_la_suma(dw_a, entorno):
    """Un re-envío con una cifra corregida (otro documento, misma hoja) no duplica el programa y mes."""
    import openpyxl
    ruta = cap.construir_plan(cap.ORIGINAL, entorno, con_ibp=False)
    cargar_libro(dw_a, ruta, tipo_fuente="PLANIFICACION")
    assert captacion_por_programa_y_mes(dw_a)[("POS-9300", "2027-03")] == (100, 10)
    wb = openpyxl.load_workbook(ruta)
    ws = wb[cap.ORIGINAL.visible]
    cab = [c.value for c in ws[1]]
    ws.cell(row=2, column=cab.index("LEADS") + 1, value=120)       # 9300: 100 -> 120 leads
    corregido = entorno / "plan_captacion_corregido.xlsx"
    wb.save(corregido)
    cargar_libro(dw_a, corregido, tipo_fuente="PLANIFICACION")
    assert captacion_por_programa_y_mes(dw_a)[("POS-9300", "2027-03")] == (120, 10)
    assert captacion_por_mes(dw_a)["2027-03"] == (120 + 50 + 40, 10 + 5 + 0)


def test_borrar_el_documento_de_detalle_deja_la_cifra_de_la_tabla_por_programa(dw_a, entorno):
    """La captación se recalcula desde las filas vigentes: sin el detalle mensual, gana la tabla por programa."""
    from services.ingestion_service import IngestionService
    plan = cap.construir_plan(cap.ORIGINAL, entorno, con_ibp=False)
    acta = cap.construir_acta_con_ibp(cap.ORIGINAL, entorno)
    _, doc_plan = cargar_libro(dw_a, plan, tipo_fuente="PLANIFICACION")
    cargar_libro(dw_a, acta, tipo_fuente="ACTA")
    assert captacion_por_programa_y_mes(dw_a) == cap.ESPERADO
    assert IngestionService.eliminar_fuente(dw_a, doc_plan)
    # solo queda la tabla por programa: sus cifras (las filas con ambos datos) y nada del detalle borrado
    assert captacion_por_programa_y_mes(dw_a) == {
        ("POS-9300", "2027-03"): (900, 90), ("POS-9301", "2027-03"): (600, 60), ("POS-9302", "2027-03"): (70, 7),
        ("POS-9400", "2027-04"): (200, 20), ("POS-9401", "2027-04"): (100, 5), ("POS-9400", "2027-05"): (300, 12)}
    # volver a subir el detalle devuelve la cifra de la hoja de detalle (prioridad), sin duplicar
    cargar_libro(dw_a, plan, tipo_fuente="PLANIFICACION")
    assert captacion_por_programa_y_mes(dw_a) == cap.ESPERADO


def test_borrar_la_unica_fuente_de_captacion_vacia_el_kpi(dw_a, entorno):
    from services.ingestion_service import IngestionService
    _, doc = cargar_libro(dw_a, cap.construir_plan(cap.ORIGINAL, entorno), tipo_fuente="PLANIFICACION")
    assert captacion_por_mes(dw_a)
    assert IngestionService.eliminar_fuente(dw_a, doc)
    assert captacion_por_mes(dw_a) == {}
    assert dw_a.execute(text("SELECT COUNT(*) FROM fact_marketing")).scalar() == 0


def _ingestar_y_leer(db, entorno, rutas):
    """Ingesta de libros en un lote y lectura BETO (la que reemplazaba el payload de staging)."""
    from routers import dataops
    from models.dim_origen import DimOrigenDocumental
    from models.lote import Lote
    from services import ingestion_service

    lote = Lote(institucion="Prueba", periodo="2027")
    db.add(lote)
    db.commit()
    ids = []
    for ruta, tipo, escala in rutas:
        res = ingestion_service.IngestionService.procesar_archivo(
            db, str(ruta), ruta.name, id_lote=lote.id_lote, institucion="Prueba", tipo_fuente=tipo, tipo_escala=escala)
        ids.append(res["id_documento"])
    docs = db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_documento.in_(ids)).all()
    dataops._evaluar_documentos_lote(db, docs, persistir_staging=True)      # la lectura BETO
    db.commit()
    return lote, ids


def test_la_lectura_beto_conserva_el_payload_de_la_ingesta_y_la_captacion_sale_igual(dw_a, entorno):
    """
    Hallazgo de la recarga real: la lectura BETO reemplazaba el payload de staging y se perdían el período de la hoja y la
    prioridad de la hoja de detalle: la tabla por programa ganaba al detalle mensual visible.
    """
    from routers import dataops
    from models.staging_registro import StagingRegistroCrudo

    db = dw_a
    lote, ids = _ingestar_y_leer(db, entorno, [(cap.construir_plan(cap.ORIGINAL, entorno, con_ibp=False), "PLANIFICACION", None),
                                               (cap.construir_acta_con_ibp(cap.ORIGINAL, entorno), "ACTA", "CENTESIMAL_100")])
    por_hoja = {(s.id_documento, s.hoja): s.payload_json for s in db.query(StagingRegistroCrudo).filter(StagingRegistroCrudo.id_documento.in_(ids))}
    assert all("tuplas" in p for p in por_hoja.values())
    assert por_hoja[(ids[0], cap.ORIGINAL.visible)]["prioridad_captacion"] == 1
    assert por_hoja[(ids[0], cap.ORIGINAL.visible)]["mes_hoja"] == 3
    assert por_hoja[(ids[0], cap.ORIGINAL.oculta_rescatada)]["prioridad_captacion"] == 2
    assert por_hoja[(ids[1], cap.ORIGINAL.por_programa)]["prioridad_captacion"] == 3
    dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), db, None)
    db.commit()
    assert captacion_por_programa_y_mes(db) == cap.ESPERADO      # gana el detalle visible, no la tabla por programa


def test_la_lectura_beto_conserva_las_metas_del_informe_de_gestion(dw_b, entorno):
    from routers import dataops
    from models.dim_meta import DimMeta
    from tests.fixtures.fuentes_sinteticas import constructor as ctor

    db = dw_b
    lote, ids = _ingestar_y_leer(db, entorno, [(ctor.construir_plan(ctor.PLAN_ORIGINAL, entorno), "PLANIFICACION", None)])
    dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), db, None)
    db.commit()
    assert db.query(DimMeta).count() == 18       # antes de FU-L3 la lectura las borraba del payload y dim_meta quedaba vacía
