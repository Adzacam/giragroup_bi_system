"""Cascada de BETO residual CF-L4 con catálogo institucional sintético."""

from types import SimpleNamespace

import pytest

from routers.dataops import extraccion
from services import beto_integracion as bi
from services import modulo_validador


def modulo(id_, fk, pos, nombre, programa='Curso de Finanzas'):
    return SimpleNamespace(id_modulo=id_, id_cat_modulo=fk, pos_code=pos, nombre_modulo=nombre, programa=programa)


@pytest.fixture
def catalogo(monkeypatch):
    monkeypatch.setenv('BETO_CASCADA_FINAL', '0')
    monkeypatch.setenv('BETO_ACUERDO_QC', '0')
    monkeypatch.setenv('BETO_RESCATE_ACADEMICO', '1')
    monkeypatch.setattr(modulo_validador, '_cargar_reglas_catalogo', lambda **_: {'CENTINELA': {'ESTUDIANTE'}})
    return [modulo(1, None, 'POS-5000', 'Curso de Finanzas'), modulo(2, 8, 'POS-5000-M01', 'Control Financiero')]


def refinar(linea, fuente, propuestas, catalogo, estudiantes=()):
    solicitudes = []

    def post(textos):
        solicitudes.extend(textos)
        return [[bi.EntidadBeto(tipo, valor, texto.index(valor), texto.index(valor) + len(valor), prob)
                 for tipo, valor, prob in propuestas] for texto in textos]

    cont = bi.Contadores()
    cliente = bi.ClienteBeto(cache=bi.CacheMemoria(), post=post, contadores=cont)

    def extraer(linea, **kwargs):
        return extraccion.extract_entities_from_line(linea, list(estudiantes), [], catalogo, tipo_fuente=fuente, **kwargs)

    resultado, = bi.refinar_lineas([linea], extraer, tipo_fuente=fuente, cliente=cliente,
                                  contadores=cont, excluir_celda=extraccion.EXCLUIR_CELDA_BETO)
    return resultado, cont, solicitudes


def test_rescata_modulo_con_fk_existente_fuera_de_fuentes_persona(catalogo):
    linea = 'POS: POS-5000 | CONTENIDO: Control Financiero'
    resultado, cont, solicitudes = refinar(linea, 'EVALUACION_DOCENTE', [('MODULO', 'Control Financiero', .98)], catalogo)

    resuelto = bi.entidad(resultado.ents, 'MÓDULO')
    assert resuelto['fuente_resolucion'] == 'BETO'
    assert (resuelto['canonicalId'], resuelto['idModulo']) == ('POS-5000-M01', 2)
    assert resuelto['es_nuevo_perfil'] is False
    assert resultado.req_rev is False
    assert solicitudes and cont.residuales_academicas_enviadas == cont.lineas_academicas_rescatadas == 1
    assert cont.residuales_enviadas == 0


def test_rescata_programa_solo_cuando_oferta_es_unica(catalogo):
    linea = 'DETALLE CURRICULAR: Curso de Finanzas | GESTION: 2026'
    propuestas = [('PROGRAMA', 'Curso de Finanzas', .98)]
    ok, _, _ = refinar(linea, 'TECHOS', propuestas, catalogo)
    assert bi.entidad(ok.ents, 'PROGRAMA')['posCodigo'] == 'POS-5000'

    catalogo = [*catalogo, modulo(3, None, 'POS-5001', 'Curso de Finanzas')]
    ambiguo, cont, _ = refinar(linea, 'TECHOS', propuestas, catalogo)
    assert ambiguo.req_rev is True
    assert bi.ambiguedad_academica(ambiguo.ents) == 'AMBIGUO'
    assert cont.lineas_academicas_ambiguas == 1
    assert cont.lineas_academicas_rescatadas == 0


def test_modulo_homonimo_en_una_oferta_activa_misma_bandeja(catalogo):
    catalogo = [*catalogo, modulo(3, 9, 'POS-5000-M02', 'Control Financiero')]
    linea = 'POS: POS-5000 | CONTENIDO: Control Financiero'
    resultado, cont, _ = refinar(linea, 'EVALUACION_DOCENTE', [('MODULO', 'Control Financiero', .98)], catalogo)

    assert resultado.req_rev is True
    assert bi.ambiguedad_academica(resultado.ents) == 'AMBIGUO'
    assert not bi.entidad(resultado.ents, 'MÓDULO').get('canonicalId')
    assert cont.lineas_academicas_ambiguas == 1


@pytest.mark.parametrize('valor', ['ESTUDIANTE', 'Asignatura fuera del catálogo', 'MOD-GEN'])
def test_rechaza_centinelas_y_modulos_sin_clave_local(catalogo, valor):
    linea = f'POS: POS-5000 | CONTENIDO: {valor}'
    resultado, cont, _ = refinar(linea, 'EVALUACION_DOCENTE', [('MODULO', valor, .98)], catalogo)
    assert bi.entidad(resultado.ents, 'MÓDULO') is None
    assert cont.lineas_academicas_rescatadas == 0


@pytest.mark.parametrize('ci_visible,fuentes', [(True, {'CI_EXACTA'}), (False, {'ENCABEZADO', 'FUZZY'})])
def test_conserva_persona_a_b_y_programa_previo_durante_rescate(catalogo, ci_visible, fuentes):
    persona = SimpleNamespace(id_estudiante=17, nombre_completo='Ana Lopez', ci_numero='1234567')
    linea = ('CI: 1234567 | ' if ci_visible else '') + 'ESTUDIANTE: Ana Lopez | POS: POS-5000 | CONTENIDO: Control Financiero'
    base, _, _ = extraccion.extract_entities_from_line(linea, [persona], [], catalogo, tipo_fuente='ACTA')
    resultado, _, _ = refinar(linea, 'ACTA', [('MODULO', 'Control Financiero', .98)], catalogo, [persona])
    assert bi.entidad(base, 'ESTUDIANTE')['fuente_resolucion'] in fuentes
    assert bi.entidad(resultado.ents, 'ESTUDIANTE') == bi.entidad(base, 'ESTUDIANTE')
    assert bi.entidad(resultado.ents, 'PROGRAMA') == bi.entidad(base, 'PROGRAMA')
    assert bi.entidad(resultado.ents, 'MÓDULO')['fuente_resolucion'] == 'BETO'


def test_finanzas_sin_contexto_no_se_envia(catalogo):
    linea = 'CONCEPTO: Arrendamiento | MONTO: 5200'
    _, cont, solicitudes = refinar(linea, 'EGRESOS', (), catalogo)
    assert solicitudes == []
    assert cont.residuales_academicas_enviadas == 0


def test_flag_apagado_no_ejecuta_rescate(catalogo, monkeypatch):
    monkeypatch.delenv('BETO_RESCATE_ACADEMICO')
    assert bi.activo('BETO_RESCATE_ACADEMICO') is False
    assert bi.necesita_refinar() is False
    linea = 'POS: POS-5000 | CONTENIDO: Control Financiero'
    resultado, cont, solicitudes = refinar(linea, 'EVALUACION_DOCENTE', [], catalogo)
    assert bi.entidad(resultado.ents, 'MÓDULO') is None
    assert solicitudes == []
    assert cont.lineas_academicas_rescatadas == 0


def test_el_rescate_no_carga_predicciones_guardadas_con_otro_modelo(catalogo):
    cliente = bi.ClienteBeto(cache=bi.CacheMemoria(), configuracion='candidato')
    anterior = SimpleNamespace(payload_json={'configuracion_beto': 'vigente', 'tuplas': [
        {'raw_line': 'POS: POS-5000', 'beto_ents': []}
    ]})
    assert bi.precargar_desde_staging(cliente, [anterior]) == 0
