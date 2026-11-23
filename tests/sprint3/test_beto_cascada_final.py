"""Opción 1 (BETO_CASCADA_FINAL): BETO como última etapa de la cascada, solo para las líneas que las reglas no resolvieron."""
import pytest

from services import beto_integracion as bi
from tests.sprint3.beto_utiles import EXCLUIR, ServicioFalso, catalogo, cliente, ent, extraer_con

RESIDUAL = "REGISTRO: 15 | DETALLE: maria lopez quispe 2024 | MODULO: Gestion de Datos | NOTA: 85"
RESUELTA = "ESTUDIANTE: Maria Lopez Quispe | MODULO: Gestion de Datos | NOTA: 85"


@pytest.fixture(autouse=True)
def solo_cascada(monkeypatch):
    for f in ("BETO_CASCADA_FINAL", "BETO_ACUERDO_QC", "BETO_SUGERENCIA_HITL", "BETO_VENTANA"):
        monkeypatch.setenv(f, "0")
    monkeypatch.setenv("BETO_CASCADA_FINAL", "1")


def _texto(linea):
    return bi.texto_para_beto(linea)


def refinar(lineas, servicio, tipo_fuente="ACTA", omitir=None):
    est, doc, mod = catalogo()
    cont = bi.Contadores()
    res = bi.refinar_lineas(lineas, extraer_con(est, doc, mod, tipo_fuente), tipo_fuente=tipo_fuente, cliente=cliente(servicio, cont),
                            contadores=cont, archivo="acta.xlsx", omitir=omitir, excluir_celda=EXCLUIR)
    return res, cont


def test_flags_a3_por_defecto_y_apagado_explicito(monkeypatch):
    for f in ("BETO_CASCADA_FINAL", "BETO_ACUERDO_QC", "BETO_SUGERENCIA_HITL", "BETO_VENTANA"):
        monkeypatch.delenv(f, raising=False)
    assert bi.activo("BETO_CASCADA_FINAL") is True
    assert bi.activo("BETO_ACUERDO_QC") is True
    assert bi.activo("BETO_SUGERENCIA_HITL") is True
    assert bi.activo("BETO_VENTANA") is False
    assert bi.necesita_refinar() is True
    for f in ("BETO_CASCADA_FINAL", "BETO_ACUERDO_QC", "BETO_SUGERENCIA_HITL", "BETO_VENTANA"):
        monkeypatch.setenv(f, "0")
        assert bi.activo(f) is False
    assert bi.necesita_refinar() is False
    monkeypatch.setenv("BETO_CASCADA_FINAL", "si")
    assert bi.activo("BETO_CASCADA_FINAL") and bi.necesita_refinar()


def test_las_reglas_no_resuelven_la_linea_residual():
    est, doc, mod = catalogo()
    ents, score, _ = extraer_con(est, doc, mod)(RESIDUAL)
    assert bi.persona_sin_resolver(ents, "ESTUDIANTE")


def test_beto_resuelve_un_residual_contra_el_catalogo_y_queda_rotulado_beto():
    servicio = ServicioFalso({_texto(RESIDUAL): [ent("ESTUDIANTE", "maria lopez quispe", RESIDUAL, 0.97)]})
    (r,), cont = refinar([RESIDUAL], servicio)
    est = bi.entidad(r.ents, "ESTUDIANTE")
    assert r.promovida_por_beto and est["matchedCanonical"] == "Maria Lopez Quispe" and est["fuente_resolucion"] == "BETO"
    assert est["lecturaModelo"] == 0.97 and est["es_nuevo_perfil"] is False        # la confianza es la del modelo, no una lectura base fija
    assert "propuesto por BETO" in est["algorithm"]
    assert (cont.lineas_totales, cont.residuales_enviadas, cont.resueltas_por_beto, cont.a_hitl) == (1, 1, 1, 0)


def test_beto_nunca_sobrescribe_una_resolucion_de_reglas():
    servicio = ServicioFalso({_texto(RESUELTA): [ent("ESTUDIANTE", "Maria Lopez Quispe", RESUELTA, 0.99)]})
    (r,), cont = refinar([RESUELTA], servicio)
    est = bi.entidad(r.ents, "ESTUDIANTE")
    assert est["matchedCanonical"] == "Maria Lopez Quispe" and est["fuente_resolucion"] != "BETO" and not r.promovida_por_beto
    assert servicio.llamadas == [] and cont.residuales_enviadas == 0           # una línea ya resuelta no se manda a BETO
    # y con inyección directa del nombre de BETO la extracción conserva la resolución de reglas
    est_, doc, mod = catalogo()
    ents, *_ = extraer_con(est_, doc, mod)(RESUELTA, est_beto={"nombre": "Juan Carlos Mamani Flores", "prob": 0.99})
    assert bi.entidad(ents, "ESTUDIANTE")["matchedCanonical"] == "Maria Lopez Quispe"


def test_nombre_de_beto_fuera_del_catalogo_deja_la_linea_como_estaba():
    servicio = ServicioFalso({_texto(RESIDUAL): [ent("ESTUDIANTE", "maria lopez quispe", RESIDUAL, 0.97)]})
    est, doc, mod = catalogo()
    mod.append(mod[0])
    sin_maria = est[1:]
    cont = bi.Contadores()
    (r,) = bi.refinar_lineas([RESIDUAL], extraer_con(sin_maria, doc, mod), tipo_fuente="ACTA", cliente=cliente(servicio, cont), contadores=cont,
                             excluir_celda=EXCLUIR)
    antes = extraer_con(sin_maria, doc, mod)(RESIDUAL)
    assert (r.ents, r.score, r.req_rev) == antes and not r.promovida_por_beto
    assert (cont.resueltas_por_beto, cont.a_hitl) == (0, 1)


def test_si_beto_no_ve_persona_la_linea_queda_en_hitl():
    (r,), cont = refinar([RESIDUAL], ServicioFalso({}))
    assert not r.promovida_por_beto and (cont.residuales_enviadas, cont.a_hitl) == (1, 1)


def test_servicio_caido_no_cambia_nada():
    (r,), cont = refinar([RESIDUAL], ServicioFalso(falla=True))
    est, doc, mod = catalogo()
    assert (r.ents, r.score, r.req_rev) == extraer_con(est, doc, mod)(RESIDUAL)
    assert cont.resueltas_por_beto == 0 and cont.a_hitl == 1


def test_un_tramo_en_columna_de_asesor_no_se_propone_como_estudiante():
    linea = "REGISTRO: 15 | ASESOR: maria lopez quispe 2024 | MODULO: Gestion de Datos"
    servicio = ServicioFalso({_texto(linea): [ent("ESTUDIANTE", "maria lopez quispe", linea, 0.99)]})
    (r,), cont = refinar([linea], servicio)
    assert not r.promovida_por_beto and cont.resueltas_por_beto == 0


def test_solo_los_tipos_de_documento_con_persona_pasan_a_beto():
    servicio = ServicioFalso({_texto(RESIDUAL): [ent("ESTUDIANTE", "maria lopez quispe", RESIDUAL, 0.97)]})
    (r,), cont = refinar([RESIDUAL], servicio, tipo_fuente="RENTABILIDAD")
    assert servicio.llamadas == [] and not r.promovida_por_beto and cont.residuales_enviadas == 0


def test_filas_omitidas_como_ruido_no_se_evaluan_ni_se_cuentan():
    servicio = ServicioFalso({_texto(RESIDUAL): [ent("ESTUDIANTE", "maria lopez quispe", RESIDUAL, 0.97)]})
    res, cont = refinar([RESIDUAL, RESUELTA], servicio, omitir=lambda l: l == RESIDUAL)
    assert res[0] is None and res[1] is not None and cont.lineas_totales == 1 and servicio.llamadas == []


def test_cache_evita_repetir_la_inferencia_y_se_cuentan_aciertos():
    servicio = ServicioFalso({_texto(RESIDUAL): [ent("ESTUDIANTE", "maria lopez quispe", RESIDUAL, 0.97)]})
    est, doc, mod = catalogo()
    cont = bi.Contadores()
    cl = cliente(servicio, cont)
    for _ in range(2):
        bi.refinar_lineas([RESIDUAL], extraer_con(est, doc, mod), tipo_fuente="ACTA", cliente=cl, contadores=cont, excluir_celda=EXCLUIR)
    assert len(servicio.llamadas) == 1 and cont.textos_inferidos == 1 and cont.textos_en_cache == 1 and cont.peticiones == 1


def test_docente_no_resuelto_se_promueve_solo_si_el_catalogo_lo_encuentra():
    linea = "ESTUDIANTE: Maria Lopez Quispe | DOCENTE: tutor 7 | OBS: pedro rojas vargas | MODULO: Gestion de Datos | NOTA: 85"
    servicio = ServicioFalso({_texto(linea): [ent("DOCENTE", "pedro rojas vargas", linea, 0.95)]})
    est, doc, mod = catalogo()
    ents, *_ = extraer_con(est, doc, mod)(linea)
    assert bi.persona_sin_resolver(ents, "DOCENTE")
    (r,), cont = refinar([linea], servicio)
    d = bi.entidad(r.ents, "DOCENTE")
    assert r.promovida_por_beto and d["matchedCanonical"] == "Ing. Pedro Rojas Vargas" and d["fuente_resolucion"] == "BETO"


def test_los_umbrales_vigentes_no_cambian():
    from pipeline import config as cfg
    assert (cfg.UMBRAL_INDICE_REGISTRO_DEC, cfg.UMBRAL_CONFIANZA_MEDIO) == (0.85, 0.60)
    from pipeline.normalization.person_resolver import UMBRAL_PERSONA
    assert UMBRAL_PERSONA == 0.92
