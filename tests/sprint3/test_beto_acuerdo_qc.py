"""Opción 2 (BETO_ACUERDO_QC): acuerdo regla–BETO como control de calidad. No toca las excepciones que ya filtran las reglas."""
import pytest

from pipeline import config as cfg
from services import beto_integracion as bi
from tests.sprint3.beto_utiles import EXCLUIR, ServicioFalso, catalogo, cliente, ent, extraer_con

RESUELTA = "ESTUDIANTE: Maria Lopez Quispe | MODULO: Gestion de Datos | NOTA: 85"


@pytest.fixture(autouse=True)
def solo_acuerdo(monkeypatch):
    for f in ("BETO_CASCADA_FINAL", "BETO_ACUERDO_QC", "BETO_SUGERENCIA_HITL", "BETO_VENTANA"):
        monkeypatch.setenv(f, "0")
    monkeypatch.setenv("BETO_ACUERDO_QC", "1")


def refinar(lineas, servicio, archivo="acta.xlsx", tipo_fuente="ACTA"):
    est, doc, mod = catalogo()
    cont = bi.Contadores()
    res = bi.refinar_lineas(lineas, extraer_con(est, doc, mod, tipo_fuente), tipo_fuente=tipo_fuente, cliente=cliente(servicio, cont),
                            contadores=cont, archivo=archivo, excluir_celda=EXCLUIR)
    return res, cont


def test_acuerdo_no_cambia_nada():
    servicio = ServicioFalso({bi.texto_para_beto(RESUELTA): [ent("ESTUDIANTE", "Maria Lopez Quispe", RESUELTA)]})
    (r,), cont = refinar([RESUELTA], servicio)
    est, doc, mod = catalogo()
    assert r.acuerdo == bi.ACUERDO and not r.degradada_por_acuerdo
    assert (r.ents[0]["acuerdo_beto"] if r.ents[0].get("acuerdo_beto") else None) == bi.ACUERDO
    assert (r.score, r.req_rev) == extraer_con(est, doc, mod)(RESUELTA)[1:]
    assert (cont.comparadas_acuerdo, cont.acuerdos, cont.desacuerdos, cont.tasa_acuerdo()) == (1, 1, 0, 1.0)


def test_desacuerdo_baja_un_escalon_y_deriva_a_revision():
    (r,), cont = refinar([RESUELTA], ServicioFalso({}))   # BETO ve «O» en todo el texto
    est, doc, mod = catalogo()
    score_reglas = extraer_con(est, doc, mod)(RESUELTA)[1]
    assert score_reglas >= 0.85, "la fila de prueba debe ser de pase directo para que el escalón se note"
    assert r.acuerdo == bi.DESACUERDO and r.degradada_por_acuerdo and r.req_rev is True
    assert r.score == round(cfg.UMBRAL_INDICE_REGISTRO_DEC - cfg.BETO_ESCALON_DESACUERDO_MARGEN, 4) == 0.84
    assert (cont.desacuerdos, cont.tasa_acuerdo()) == (1, 0.0)
    assert cont.desacuerdos_por_archivo_y_tipo == {"acta.xlsx | ACTA": 1}


def test_el_escalon_es_una_constante_nombrada_y_no_baja_mas_alla_de_la_banda_de_revision():
    assert bi.bajar_un_escalon(0.97) == 0.84 and bi.bajar_un_escalon(0.85) == 0.84
    assert bi.bajar_un_escalon(0.70) == 0.70 and bi.bajar_un_escalon(0.50) == 0.50 and bi.bajar_un_escalon(None) is None
    assert cfg.MOTIVO_DESACUERDO_REGLA_BETO == "DESACUERDO_REGLA_BETO"


def test_comparar_con_beto_cubre_los_cuatro_casos():
    texto = "ESTUDIANTE: Maria Lopez Quispe | MODULO: Gestion de Datos"
    persona = bi.EntidadBeto("ESTUDIANTE", "Maria Lopez Quispe", 12, 30, 0.95)
    modulo = bi.EntidadBeto("MODULO", "Maria Lopez Quispe", 12, 30, 0.90)
    assert bi.comparar_con_beto("Maria Lopez Quispe", texto, [persona]) == bi.ACUERDO
    assert bi.comparar_con_beto("Maria Lopez Quispe", texto, []) == bi.DESACUERDO
    assert bi.comparar_con_beto("Maria Lopez Quispe", texto, [modulo]) == bi.TIPO_DISTINTO
    assert bi.comparar_con_beto("Otra Persona Mas", texto, [persona]) == bi.NO_EVALUABLE
    parcial = bi.EntidadBeto("DOCENTE", "Maria", 12, 17, 0.9)   # cubre 5 de 18 caracteres: no alcanza el solape mínimo
    assert bi.comparar_con_beto("Maria Lopez Quispe", texto, [parcial]) == bi.DESACUERDO


def test_tipo_distinto_y_no_evaluable_no_se_penalizan():
    modulo = bi.EntidadBeto("MODULO", "Maria Lopez Quispe", RESUELTA.index("Maria"), RESUELTA.index("Maria") + 18, 0.9)
    (r,), cont = refinar([RESUELTA], ServicioFalso({bi.texto_para_beto(RESUELTA): [modulo]}))
    est, doc, mod = catalogo()
    assert r.acuerdo == bi.TIPO_DISTINTO and not r.degradada_por_acuerdo
    assert (r.score, r.req_rev) == extraer_con(est, doc, mod)(RESUELTA)[1:]
    assert cont.tipo_distinto == 1 and cont.desacuerdos == 0


def test_la_tasa_y_los_desacuerdos_se_agrupan_por_archivo_y_tipo():
    servicio = ServicioFalso({})
    est, doc, mod = catalogo()
    cont = bi.Contadores()
    cl = cliente(servicio, cont)
    bi.refinar_lineas([RESUELTA], extraer_con(est, doc, mod, "ACTA"), tipo_fuente="ACTA", cliente=cl, contadores=cont, archivo="a.xlsx", excluir_celda=EXCLUIR)
    bi.refinar_lineas([RESUELTA], extraer_con(est, doc, mod, "COBRANZA"), tipo_fuente="COBRANZA", cliente=cl, contadores=cont, archivo="c.xlsx", excluir_celda=EXCLUIR)
    assert cont.desacuerdos_por_archivo_y_tipo == {"a.xlsx | ACTA": 1, "c.xlsx | COBRANZA": 1}
    total = bi.Contadores()
    total.sumar(cont)
    total.sumar(cont)
    assert total.desacuerdos == 4 and total.desacuerdos_por_archivo_y_tipo["a.xlsx | ACTA"] == 2


def test_una_persona_que_las_reglas_no_resolvieron_no_se_compara():
    linea = "REGISTRO: 15 | DETALLE: maria lopez quispe 2024 | MODULO: Gestion de Datos"
    servicio = ServicioFalso({})
    (r,), cont = refinar([linea], servicio)
    assert r.acuerdo is None and servicio.llamadas == [] and cont.comparadas_acuerdo == 0


def test_las_excepciones_que_filtran_las_reglas_no_se_tocan():
    """Correo, etiqueta Likert, comentario o un solo token los descarta person_resolver/el extractor antes de BETO: la opción 2 no los reabre."""
    from pipeline.normalization.person_resolver import es_correo, es_etiqueta_likert, parece_nombre_propio
    assert es_correo("alguien@correo.com") and es_etiqueta_likert("5/Totalmente de acuerdo") and not parece_nombre_propio("todo bien")
    linea = "ESTUDIANTE: alguien@correo.com | MODULO: Gestion de Datos | NOTA: 85"
    servicio = ServicioFalso({})
    est, doc, mod = catalogo()
    antes = extraer_con(est, doc, mod)(linea)
    (r,), cont = refinar([linea], servicio)
    assert (r.ents, r.score, r.req_rev) == antes and cont.comparadas_acuerdo == 0 and r.acuerdo is None


def test_servicio_caido_no_cambia_ni_cuenta_desacuerdos():
    (r,), cont = refinar([RESUELTA], ServicioFalso(falla=True))
    est, doc, mod = catalogo()
    assert (r.score, r.req_rev) == extraer_con(est, doc, mod)(RESUELTA)[1:] and r.acuerdo is None and cont.desacuerdos == 0


def test_un_nombre_armado_con_varias_columnas_se_busca_palabra_por_palabra():
    """Cobranzas y actas ARCA parten el nombre (NOMBRES + PATERNO + MATERNO): el token de las reglas no aparece seguido en el texto."""
    texto = "APELLIDO PATERNO: CAYO | APELLIDO MATERNO: LIMA | NOMBRES: EDGAR | MONTO: 120"
    token = "EDGAR CAYO LIMA"
    assert token not in texto
    a, b, c = texto.index("CAYO"), texto.index("LIMA"), texto.index("EDGAR")
    todo = [bi.EntidadBeto("ESTUDIANTE", "CAYO", a, a + 4, 0.9), bi.EntidadBeto("ESTUDIANTE", "LIMA", b, b + 4, 0.9), bi.EntidadBeto("ESTUDIANTE", "EDGAR", c, c + 5, 0.9)]
    assert bi.comparar_con_beto(token, texto, todo) == bi.ACUERDO
    assert bi.comparar_con_beto(token, texto, []) == bi.DESACUERDO
    assert bi.comparar_con_beto(token, texto, todo[:1]) == bi.DESACUERDO          # solo cubre 4 de 14 caracteres
    assert bi.comparar_con_beto("EDGAR CAYO ROJAS", texto, todo) == bi.NO_EVALUABLE   # una palabra no está en el texto
    assert bi.comparar_con_beto("EDGAR", "EDGARDO: x", todo) == bi.NO_EVALUABLE        # no confunde EDGAR con EDGARDO
