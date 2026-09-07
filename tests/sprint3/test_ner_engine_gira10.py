"""
tests/test_ner_engine_gira10.py
--------------------------------
Suite de pruebas unitarias y de integración para GIRA-10:
Extractor NER con BETO (pipeline/semantic/ner_engine.py).

Verifica:
1. Inferencia académica y financiera.
2. Invariante estricto de offsets de caracteres (start_char:end_char == valor).
3. Desambiguación semántica entre DOCENTE y ESTUDIANTE.
4. Procesamiento por lotes (batch processing).
5. Robustez frente a entradas atípicas (vacías, sin entidades, caracteres especiales).
6. Enriquecimiento mediante CatalogoGazetteer.
"""

import pytest
from pipeline.semantic.ner_engine import BetoNEREngine
from pipeline.semantic.ner_schema import TipoEntidad, ResultadoInferenciaNER
from pipeline.config import UMBRAL_CONFIANZA_ALTO


@pytest.fixture(scope="module")
def ner_engine():
    """Instancia compartida del motor NER para evitar recargar el modelo en cada test."""
    return BetoNEREngine()


def test_inferencia_academica_acta_notas(ner_engine):
    """Verifica la extracción completa en una oración de acta de notas."""
    oracion = (
        "En el programa Diplomado en Marketing Digital (código POS-5252), "
        "el docente Carlos Rojas evaluó al estudiante Juan Pérez "
        "en el módulo Métricas Digitales con la nota 88."
    )
    res = ner_engine.extraer_entidades(oracion)

    assert isinstance(res, ResultadoInferenciaNER)
    assert res.tiempo_inferencia_ms > 0
    assert len(res.entidades) >= 5

    # Validar tipos esperados
    programas = res.obtener_por_tipo(TipoEntidad.PROGRAMA)
    pos_list = res.obtener_por_tipo(TipoEntidad.POS)
    docentes = res.obtener_por_tipo(TipoEntidad.DOCENTE)
    estudiantes = res.obtener_por_tipo(TipoEntidad.ESTUDIANTE)
    notas = res.obtener_por_tipo(TipoEntidad.NOTA)

    assert len(programas) >= 1
    assert "Marketing Digital" in programas[0].valor
    assert len(pos_list) == 1 and pos_list[0].valor == "POS-5252"
    assert len(docentes) == 1 and docentes[0].valor == "Carlos Rojas"
    assert len(estudiantes) == 1 and estudiantes[0].valor == "Juan Pérez"
    assert len(notas) == 1 and notas[0].valor == "88"


def test_invariante_offsets_estricto(ner_engine):
    """Comprueba que toda entidad extraída coincida exactamente con su slice en el texto."""
    textos = [
        "En el programa POS-5308, el docente Alejandro Ruiz evaluó al estudiante Mario Conde con la nota 95.",
        "Se registró cobranza de 850 Bs en fecha 2024-10-15 para POS-5376 con factura F-1029.",
        "El estudiante Andrea Flores tiene carnet CI 7839201 en el programa Diplomado en Derecho Notarial."
    ]
    for txt in textos:
        res = ner_engine.extraer_entidades(txt)
        for ent in res.entidades:
            slice_real = txt[ent.start_char : ent.end_char]
            assert slice_real == ent.valor, (
                f"Discrepancia en offset para '{ent.tipo}': slice='{slice_real}' vs entidad='{ent.valor}'"
            )


def test_desambiguacion_semantica_roles(ner_engine):
    """Verifica que el modelo distinga con precisión al docente del estudiante."""
    oracion = "El docente Fernando Mendoza evaluó al estudiante Gabriel Salazar en el módulo Finanzas con la nota 74."
    res = ner_engine.extraer_entidades(oracion)

    docentes = [e.valor for e in res.obtener_por_tipo(TipoEntidad.DOCENTE)]
    estudiantes = [e.valor for e in res.obtener_por_tipo(TipoEntidad.ESTUDIANTE)]

    assert "Fernando Mendoza" in docentes
    assert "Gabriel Salazar" in estudiantes
    assert "Fernando Mendoza" not in estudiantes
    assert "Gabriel Salazar" not in docentes


def test_inferencia_financiera_cobranza(ner_engine):
    """Verifica extracción de montos, fechas, POS, facturas y CI."""
    oracion = (
        "Se registró cobranza de 1500.50 Bs en fecha 2024-11-21 "
        "para el programa POS-5308 bajo la factura F-94821 para el estudiante Marcelo Quispe con CI 6849201."
    )
    res = ner_engine.extraer_entidades(oracion)

    montos = res.obtener_por_tipo(TipoEntidad.MONTO)
    fechas = res.obtener_por_tipo(TipoEntidad.FECHA)
    facturas = res.obtener_por_tipo(TipoEntidad.FACTURA)
    cis = res.obtener_por_tipo(TipoEntidad.CI)
    pos_list = res.obtener_por_tipo(TipoEntidad.POS)

    assert len(montos) >= 1 and montos[0].valor == "1500.50"
    assert len(fechas) >= 1 and fechas[0].valor == "2024-11-21"
    assert len(facturas) >= 1 and facturas[0].valor == "F-94821"
    assert len(cis) >= 1 and cis[0].valor == "6849201"
    assert len(pos_list) >= 1 and pos_list[0].valor == "POS-5308"


def test_extraccion_lote_batch_processing(ner_engine):
    """Verifica que extraer_lote produzca resultados idénticos a extraer individualmente."""
    lote = [
        "En el programa POS-5252 el docente Carlos Rojas evaluó con nota 80.",
        "Cobranza de 300 Bs en fecha 2024-05-10 bajo factura F-001.",
        "El estudiante Sergio Ramos aprobó con la nota 90 en POS-5310."
    ]
    res_lote = ner_engine.extraer_lote(lote, batch_size=2)
    assert len(res_lote) == 3

    for i, oracion in enumerate(lote):
        res_ind = ner_engine.extraer_entidades(oracion)
        assert len(res_lote[i].entidades) == len(res_ind.entidades)
        for e_lote, e_ind in zip(res_lote[i].entidades, res_ind.entidades):
            assert e_lote.tipo == e_ind.tipo
            assert e_lote.valor == e_ind.valor
            assert e_lote.start_char == e_ind.start_char


def test_casos_limite_robustez(ner_engine):
    """Verifica que entradas vacías o anómalas no lancen excepciones."""
    # Texto vacío
    vacio = ner_engine.extraer_entidades("")
    assert len(vacio.entidades) == 0
    assert vacio.tiempo_inferencia_ms == 0.0

    # Texto con solo espacios
    espacios = ner_engine.extraer_entidades("     \n\t   ")
    assert len(espacios.entidades) == 0

    # Texto irrelevante sin entidades de negocio
    irrelevante = ner_engine.extraer_entidades("La reunión fue postergada para el próximo martes por motivos climáticos.")
    # Puede o no detectar fechas o palabras genéricas, pero no debe fallar
    assert isinstance(irrelevante, ResultadoInferenciaNER)

    # Lista vacía de lote
    assert ner_engine.extraer_lote([]) == []


def test_enriquecimiento_catalogo_gazetteer(ner_engine):
    """Comprueba que un código POS conocido sea enriquecido con metadata del catálogo."""
    oracion = "Se registró la inscripción en el programa POS-5308 para el estudiante Rodrigo Paz."
    res = ner_engine.extraer_entidades(oracion)

    pos_ents = res.obtener_por_tipo(TipoEntidad.POS)
    assert len(pos_ents) == 1
    # POS-5308 está en la semilla con 'DIPLOMADO EN DERECHO NOTARIAL EN BOLIVIA'
    pos_ent = pos_ents[0]
    assert pos_ent.score >= 0.98
    assert "programa_asociado" in pos_ent.metadata
    assert "DERECHO NOTARIAL" in pos_ent.metadata["programa_asociado"].upper()


def test_filtro_entidades_confiables(ner_engine):
    """Comprueba el funcionamiento del filtro de confianza probabilística."""
    oracion = "El docente Carlos Rojas evaluó al estudiante Juan Pérez con la nota 85 en POS-5252."
    res = ner_engine.extraer_entidades(oracion)

    confiables = res.entidades_confiables(umbral=UMBRAL_CONFIANZA_ALTO)
    assert len(confiables) > 0
    for ent in confiables:
        assert ent.es_confiable(umbral=UMBRAL_CONFIANZA_ALTO)
        assert ent.score >= UMBRAL_CONFIANZA_ALTO
