"""
FU-L3 (DA6): lectura de la captación por campos canónicos del catálogo (sin nombres de columna en el código).

- sinónimos: LEADS, interesados, prospectos / N° INSCRITOS, inscritos, total inscritos, reservas;
- período: fecha, año + mes (número o nombre) o el de la hoja mensual; nunca la fecha de inicio del programa;
- validez: ambos datos, enteros, 0 <= inscritos <= leads;
- una sola hoja gana por programa y mes, sin depender del orden de carga.
"""

import itertools

import pytest

from services import captacion_canonica as capt
from services.extraccion_por_encabezado import metricas_captacion, registro_planificacion


def test_sinonimos_de_leads_inscritos_y_reservas():
    assert capt.campo_de_cabecera("LEADS")[0] == "leads_captacion"
    assert capt.campo_de_cabecera("Interesados")[0] == "leads_captacion"
    assert capt.campo_de_cabecera("PROSPECTOS")[0] == "leads_captacion"
    for cab in ("N° INSCRITOS", "N° DE INSCRITOS", "inscritos", "TOTAL INSCRITOS"):
        assert capt.campo_de_cabecera(cab)[0] == "inscritos_captacion", cab
    assert capt.campo_de_cabecera("RESERVAS")[0] == "reservas"
    assert capt.campo_de_cabecera("ESTADO DEL INSCRITO") is None   # no es una columna de captación
    assert capt.campo_de_cabecera("CI") is None


def test_sinonimos_de_pos_programa_y_periodo():
    assert capt.campo_de_cabecera("POS - IBP")[0] == "pos"
    assert capt.campo_de_cabecera("NOMBRE DEL PROGRAMA")[0] == "programa"
    assert capt.campo_de_cabecera("ANO IBP")[0] == "anio_periodo"
    assert capt.campo_de_cabecera("MES IBP")[0] == "mes_periodo"
    assert capt.campo_de_cabecera("NOMBRE MES")[0] == "mes_periodo"
    assert capt.campo_de_cabecera("FECHA")[0] == "fecha_periodo"
    assert capt.campo_de_cabecera("FECHA INICIO") is None          # la fecha de inicio NO es el período de captación


def test_fila_con_ambos_datos_y_periodo_de_la_fila():
    f = capt.leer_fila({"POS": "5381.0", "ANO": "2025", "MES": "7", "LEADS": "100", "N° INSCRITOS": "10", "RESERVAS": "4"})
    assert (f.pos, f.leads, f.inscritos, f.reservas) == ("POS-5381", 100, 10, 4)
    assert f.periodo.isoformat() == "2025-07-01" and not f.periodo_de_hoja
    assert f.valida and f.conversion_posible


def test_mes_en_texto_y_ano_ibp_y_fecha():
    f = capt.leer_fila({"POS - IBP": "5381", "ANO IBP": "2026", "MES IBP": "Marzo", "INTERESADOS": "50", "INSCRITOS": "5"})
    assert f.periodo.isoformat() == "2026-03-01" and f.pos == "POS-5381"
    g = capt.leer_fila({"POS": "POS-1234", "FECHA": "2025-10-17", "LEADS": "8", "INSCRITOS": "2"})
    assert g.periodo.isoformat() == "2025-10-01"


def test_sin_periodo_en_la_fila_se_usa_el_de_la_hoja_y_nunca_la_fecha_de_inicio():
    f = capt.leer_fila({"POS": "4321", "FECHA INICIO": "2030-01-15", "LEADS": "20", "N INSCRITOS": "2"}, anio_hoja=2025, mes_hoja=10)
    assert f.periodo.isoformat() == "2025-10-01" and f.periodo_de_hoja
    sin = capt.leer_fila({"POS": "4321", "FECHA INICIO": "2030-01-15", "LEADS": "20", "N INSCRITOS": "2"})
    assert sin.periodo is None and not sin.conversion_posible


@pytest.mark.parametrize("leads,inscritos,valida", [
    ("100", "10", True), ("100", "0", True), ("0", "0", True),
    ("10", "11", False),          # más inscritos que leads
    ("100", None, False),         # falta uno de los dos
    (None, "5", False),
    ("100", "-1", False),
    ("100", "2.5", False),
])
def test_regla_ambos_datos_y_0_le_inscritos_le_leads(leads, inscritos, valida):
    campos = {"POS": "5000", "ANO": "2026", "MES": "1"}
    if leads is not None:
        campos["LEADS"] = leads
    if inscritos is not None:
        campos["N INSCRITOS"] = inscritos
    f = capt.leer_fila(campos)
    assert f is not None and f.valida is valida


def test_fila_sin_ningun_dato_de_captacion_no_es_de_captacion():
    assert capt.leer_fila({"POS": "5000", "PROGRAMA": "X", "ESTADO": "Inicio Confirmado"}) is None


def test_metricas_captacion_conserva_el_contrato_anterior():
    assert metricas_captacion({"LEADS": "40", "INSCRITOS": "0"}) == {"leads": 40, "inscritos": 0}
    assert metricas_captacion({"CI": "123456", "NOMBRES": "Persona Prueba", "EDAD": "127"}) == {}
    assert metricas_captacion({"INTERESADOS": "-1", "INSCRITOS": "2.5"}) == {}
    assert metricas_captacion({"PROSPECTOS": "30", "N° INSCRITOS": "3", "RESERVAS": "1"}) == {"leads": 30, "inscritos": 3, "reservas": 1}


def test_registro_planificacion_toma_pos_periodo_y_captacion_por_sinonimos():
    r = registro_planificacion({"POS - IBP": "5381.0", "NOMBRE DEL PROGRAMA": "DIPLOMADO FICTICIO", "ANO IBP": "2026",
                                "MES IBP": "2", "N° DE INSCRITOS": "7", "LEADS": "90", "ESTADO PROGRAMA": "Confirmado"})
    assert r["pos_code_fuente"] == "POS-5381"
    assert r["fecha_plan"].isoformat() == "2026-02-01" and r["fecha_captacion"].isoformat() == "2026-02-01"
    assert (r["leads_fuente"], r["inscritos_fuente"]) == (90, 7)
    assert r["estado_fuente"] is None    # «ESTADO PROGRAMA» no alimenta el KPI-23 (no se mapea al estado del programa)


def test_registro_planificacion_de_hoja_mensual_sin_anio_en_la_fila():
    r = registro_planificacion({"POS": "5000", "MES": "10", "LEADS": "20", "N INSCRITOS": "2", "FECHA INICIO": "2026-01-10"},
                               hoja="Hoja", anio_hoja=2025, mes_hoja=10)
    assert r["fecha_captacion"].isoformat() == "2025-10-01"
    assert r["fecha_plan"].isoformat() == "2026-01-10"   # el período del hecho conserva su regla anterior


def _cand(hoja, prioridad, leads, ins):
    return {"hoja": hoja, "prioridad": prioridad, "leads": leads, "inscritos": ins}


def test_gana_la_hoja_de_detalle_y_se_suman_sus_filas():
    gan = capt.elegir_fuente([_cand("detalle", 1, 100, 10), _cand("detalle", 1, 50, 5), _cand("por programa", 3, 999, 99)])
    assert (gan["hoja"], gan["leads"], gan["inscritos"], gan["hojas_descartadas"]) == ("detalle", 150, 15, 1)


def test_el_orden_de_carga_no_cambia_la_hoja_ganadora():
    cands = [_cand("a", 3, 1, 1), _cand("b", 1, 2, 2), _cand("c", 2, 3, 3), _cand("d", 1, 4, 4)]
    resultados = {tuple(sorted((k, str(v)) for k, v in capt.elegir_fuente(list(p)).items())) for p in itertools.permutations(cands)}
    assert len(resultados) == 1
    assert capt.elegir_fuente(cands)["hoja"] == "b"          # misma prioridad: desempate por nombre de hoja


def test_prioridades_de_hoja_por_estado_y_forma():
    assert capt.prioridad_de_hoja("visible", "2026-03") == 1       # detalle mensual visible
    assert capt.prioridad_de_hoja("hidden", "2025-07") == 2        # detalle mensual oculta rescatada
    assert capt.prioridad_de_hoja("visible", None) == 3            # tabla por programa con el mes en cada fila
    assert capt.prioridad_de_hoja("hidden", None) == 4
