"""
FU-L2: cobranza de punta a punta (ingesta -> consolidación -> DW SQLite) con libros sintéticos de datos ficticios.

Una regla por prueba:
- TIPO DE CARTERA -> estado_cartera_fuente (vocabulario normalizado; valor desconocido a revisión, no se descarta);
- TOTAL CUOTAS EN MORA -> cuotas_impagas (negativo -> 0 y «1s» -> 1, con aviso agregado);
- DIAS DE MORA -> dias_mora, nunca a cuotas; la cabecera «MORA» suelta no pisa a la específica;
- DA3: mora = cuotas >= 2; el estado de la fuente es solo descriptivo;
- pagos por mes: cada columna de pago va al mes del pago; «(PRELIMINAR)» excluida; deuda negativa -> 0;
- idempotencia: recargar no duplica;
- el libro con otros nombres, columnas en otro orden, sinónimos, filas basura y la «MORA» suelta da lo mismo.
"""

import json

import pytest
from sqlalchemy import text

from models.log_inconsistencia import LogInconsistencia
from models.staging_registro import StagingRegistroCrudo
from tests.fixtures.fuentes_sinteticas import constructor as ctor
from tests.fu_l2.conftest import avisos, cargar_libro, estados_fuente, hechos, mora_por_anio, pagos_por_anio


@pytest.fixture
def original(dw_a, entorno):
    ruta = ctor.construir_cobranza_l2(ctor.ORIGINAL_L2, entorno)
    cargar_libro(dw_a, ruta)
    return dw_a


def test_pagos_van_al_anio_del_mes_de_pago_y_se_excluye_preliminar(original):
    assert pagos_por_anio(original) == {a: float(m) for a, m in ctor.PAGOS_ESPERADOS_L2.items()}


def test_mora_es_cuotas_ge_2_por_anio_de_inicio_y_no_depende_del_estado_de_la_fuente(original):
    assert mora_por_anio(original) == ctor.MORA_ESPERADA_L2
    filas = original.execute(text(
        "SELECT estado_cartera, estado_cartera_fuente, cuotas_impagas FROM fact_situacion_financiera "
        "WHERE concepto = 'SITUACION_CARTERA'")).fetchall()
    assert filas
    for estado, fuente, cuotas in filas:
        assert estado == ("Mora" if cuotas >= 2 else "Vigente")
    # «CARTERA CERRADA» con 3 cuotas es mora (contradicción interna documentada, no se arregla); «EN MORA» sí; «INCOBRABLE» con 5 también
    por_fuente = {(f, e) for e, f, _ in filas}
    assert ("CERRADA", "Mora") in por_fuente and ("CERRADA", "Vigente") in por_fuente
    assert ("PREVISIONABLE", "Vigente") in por_fuente   # 1 cuota: no es mora aunque la fuente diga PREVISIONABLE


def test_estado_de_cartera_de_la_fuente_se_normaliza_y_lo_desconocido_va_a_revision(original):
    assert estados_fuente(original) == ctor.ESTADOS_FUENTE_ESPERADOS_L2
    # el hecho con valor fuera de catálogo no se descarta: queda cargado, sin estado de fuente
    fila = [h for h in hechos(original) if h[0] == ctor.CIS_L2[8] and h[2] == "SITUACION_CARTERA"]
    assert fila and fila[0][7] is None and fila[0][5] == 2 and fila[0][10] is True
    pendientes = [l for l in original.query(LogInconsistencia).filter_by(tipo_regla="VALOR_FUERA_DE_CATALOGO").all()]
    assert len(pendientes) == 1 and pendientes[0].estado_resolucion == "PENDIENTE"
    assert "CARTERA RARA" in pendientes[0].valor_recibido


def test_cuotas_negativas_y_texto_y_sobrepago_con_aviso_agregado(original):
    por_ci = {h[0]: h for h in hechos(original) if h[2] == "SITUACION_CARTERA"}
    assert por_ci[ctor.CIS_L2[5]][5] == 0           # -4 -> 0
    assert por_ci[ctor.CIS_L2[6]][5] == 1           # «1s» -> 1
    assert por_ci[ctor.CIS_L2[7]][3] == 0.0         # deuda -300 -> 0 (sobrepago)
    a = avisos(original)
    assert a[("CUOTAS_NEGATIVAS", "cuotas_en_mora", "REGISTRADO")] == 1
    assert a[("CUOTAS_CON_TEXTO", "cuotas_en_mora", "REGISTRADO")] == 1
    assert a[("SOBREPAGO", "monto_deuda", "REGISTRADO")] == 1


def test_dias_de_mora_van_a_dias_nunca_a_cuotas(original):
    por_ci = {h[0]: h for h in hechos(original) if h[2] == "SITUACION_CARTERA"}
    assert por_ci[ctor.CIS_L2[2]][8] == 45 and por_ci[ctor.CIS_L2[2]][5] == 2   # 45 días, 2 cuotas
    assert por_ci[ctor.CIS_L2[3]][8] == 120 and por_ci[ctor.CIS_L2[3]][5] == 1  # 120 días de mora y solo 1 cuota: no es mora (DA3)
    assert por_ci[ctor.CIS_L2[4]][8] == 400


def test_pago_mensual_es_un_hecho_sin_cuotas_ni_estado(original):
    pagos = [h for h in hechos(original) if h[2] == "PAGO_MES"]
    assert pagos
    for h in pagos:
        assert h[3] is None and h[5] is None and h[6] is None and h[9] is None


def test_hoja_oculta_basura_y_resumen_no_suman(original):
    # la oculta traía 55555 por mes y 99 cuotas: nada de eso llega a la DW
    assert all(h[4] < 55555 for h in hechos(original))
    assert max(h[5] for h in hechos(original) if h[5] is not None) <= 5
    descartes = original.query(LogInconsistencia).filter_by(tipo_regla="LINEA_SIN_ENTIDAD").all()
    assert not [d for d in descartes if d.campo_afectado == ctor.ORIGINAL_L2.hoja_datos]


def test_recargar_el_mismo_libro_no_duplica(dw_a, entorno):
    ruta = ctor.construir_cobranza_l2(ctor.ORIGINAL_L2, entorno)
    cargar_libro(dw_a, ruta)
    antes = (hechos(dw_a), pagos_por_anio(dw_a))
    cargar_libro(dw_a, ruta)
    assert (hechos(dw_a), pagos_por_anio(dw_a)) == antes


def test_variante_con_otros_nombres_columnas_sinonimos_y_mora_suelta_da_el_mismo_resultado(dw_a, dw_b, entorno):
    ruta_a = ctor.construir_cobranza_l2(ctor.ORIGINAL_L2, entorno)
    ruta_b = ctor.construir_cobranza_l2(ctor.VARIANTE_L2, entorno)
    assert ruta_a.name != ruta_b.name
    _, doc_a = cargar_libro(dw_a, ruta_a)
    _, doc_b = cargar_libro(dw_b, ruta_b)
    assert hechos(dw_a) == hechos(dw_b)
    assert pagos_por_anio(dw_a) == pagos_por_anio(dw_b) == {a: float(m) for a, m in ctor.PAGOS_ESPERADOS_L2.items()}
    assert mora_por_anio(dw_a) == mora_por_anio(dw_b) == ctor.MORA_ESPERADA_L2
    assert estados_fuente(dw_a) == estados_fuente(dw_b)
    assert avisos(dw_a) == avisos(dw_b)
    # la «MORA» suelta valía 99 en todas las filas: de usarse como cuotas habría 10 estudiantes en mora
    assert max(h[5] for h in hechos(dw_b) if h[5] is not None) <= 5


def test_la_matriz_de_cabeceras_separa_las_tres_columnas_mora(dw_a, entorno):
    ruta = ctor.construir_cobranza_l2(ctor.VARIANTE_L2, entorno)
    _, doc = cargar_libro(dw_a, ruta)
    from services.ingestion_service import canonizar_cabeceras
    canon = canonizar_cabeceras(["DIAS EN MORA", "RANGO MORA", "CUOTAS IMPAGAS", "MORA", "ESTADO DE CARTERA"])
    assert canon["DIAS EN MORA"][0] == "dias_mora"
    assert canon["RANGO MORA"][0] == "rango_mora"
    assert canon["CUOTAS IMPAGAS"][0] == "cuotas_impagas"
    assert canon["MORA"][0] != "cuotas_impagas"
    assert canon["ESTADO DE CARTERA"][0] == "estado_cartera_fuente"
    # y la fuente quedó como cobranza por sus cabeceras
    from models.dim_origen import DimOrigenDocumental
    assert dw_a.query(DimOrigenDocumental).filter_by(id_documento=doc).one().tipo_fuente == "COBRANZA"


def test_sin_datos_personales_en_avisos_ni_logs(original):
    textos = [f"{l.valor_recibido} {l.valor_esperado} {l.descripcion}" for l in original.query(LogInconsistencia).all()
              if l.tipo_regla in ("CUOTAS_NEGATIVAS", "CUOTAS_CON_TEXTO", "SOBREPAGO", "VALOR_FUERA_DE_CATALOGO")]
    for ci in ctor.CIS_L2:
        assert not any(ci in t for t in textos)
    for nombre, paterno in ctor.NOMBRES_L2:
        assert not any(paterno in t for t in textos)
