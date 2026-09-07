"""
tests/test_area3_normalizacion_matching_fk.py
----------------------------------------------
Suite integral de pruebas unitarias para el Área 3:
- GIRA-11: Normalización con RapidFuzz (pipeline/normalization/fuzzy_normalizer.py)
- GIRA-41: Matching semántico contra catálogos maestros (pipeline/normalization/semantic_matcher.py)
- GIRA-50: Validación y resolución de llaves foráneas CI / Nombre (pipeline/normalization/fk_resolver.py)
"""

import pytest
from pathlib import Path

from pipeline.normalization.fuzzy_normalizer import (
    FuzzyNormalizer,
    canonizar_orden_apellidos_nombre,
    remover_diacriticos
)
from pipeline.normalization.semantic_matcher import SemanticMatcher
from pipeline.normalization.fk_resolver import FKResolver


# ==============================================================================
# 1. PRUEBAS GIRA-11: Normalización con RapidFuzz
# ==============================================================================

def test_gira11_canonizacion_apellidos_nombre():
    """Verifica la inversión de formato 'APELLIDOS, NOMBRES' a 'NOMBRES APELLIDOS'."""
    assert canonizar_orden_apellidos_nombre("QUISPE MAMANI, JUAN CARLOS") == "JUAN CARLOS QUISPE MAMANI"
    assert canonizar_orden_apellidos_nombre("ALVAREZ PEREZ, MARIA") == "MARIA ALVAREZ PEREZ"
    # Sin coma no altera
    assert canonizar_orden_apellidos_nombre("CARLOS ROJAS") == "CARLOS ROJAS"


def test_gira11_remocion_titulos_y_diacriticos():
    """Verifica que títulos profesionales y diacríticos sean limpiados consistentemente."""
    casos = [
        ("Lic. Carlos Rojas", "CARLOS ROJAS"),
        ("Dr. Juan Pérez", "JUAN PEREZ"),
        ("Msc. Ing. Andrea Gómez", "ANDREA GOMEZ"),
        ("Prof. Dr. Fernando Mendoza", "FERNANDO MENDOZA"),
        ("MAMANI FLORES, LIC. EDGAR", "EDGAR MAMANI FLORES"),
    ]
    for entrada, esperada in casos:
        obtenido = FuzzyNormalizer.limpiar_nombre(entrada)
        assert obtenido == esperada, f"Fallo en '{entrada}': obtenido '{obtenido}' != esperado '{esperada}'"


def test_gira11_similitud_rapidfuzz():
    """Verifica el cálculo de similitud con funciones de RapidFuzz."""
    # Mismo nombre en diferente orden (token sort debe dar 1.0)
    sim = FuzzyNormalizer.calcular_similitud("JUAN CARLOS PEREZ", "PEREZ JUAN CARLOS")
    assert sim >= 0.99

    # Typo menor ("Gonzales" vs "Gonzalez")
    sim_typo = FuzzyNormalizer.calcular_similitud("MARIA GONZALES", "MARIA GONZALEZ")
    assert sim_typo >= 0.85

    # Nombres completamente distintos
    sim_dist = FuzzyNormalizer.calcular_similitud("JUAN PEREZ", "RODRIGO ROJAS")
    assert sim_dist < 0.50


def test_gira11_buscar_mejor_coincidencia():
    """Verifica la búsqueda de mejor coincidencia en lote de opciones."""
    nomina = [
        "CARLOS ALBERTO ROJAS",
        "MARIA ELENA FLORES",
        "JUAN CARLOS QUISPE",
        "FERNANDO MENDOZA RIOS"
    ]
    res = FuzzyNormalizer.buscar_mejor_coincidencia(
        "Lic. Juan Carlos Quispe Mamani",
        nomina,
        umbral_minimo=0.70
    )
    assert res is not None
    assert res[0] == "JUAN CARLOS QUISPE"
    assert res[1] >= 0.70


# ==============================================================================
# 2. PRUEBAS GIRA-41: Matching Semántico contra Catálogos Maestros
# ==============================================================================

@pytest.fixture(scope="module")
def matcher():
    return SemanticMatcher()


def test_gira41_matching_programa_exacto_pos(matcher):
    """Verifica resolución O(1) de programas por código POS."""
    res = matcher.enlazar_programa("POS-5308")
    assert res is not None
    assert res["pos"] == "POS-5308"
    assert res["tipo_match"] == "EXACTO_POS"
    assert res["score"] == 1.0
    assert "DERECHO NOTARIAL" in res["nombre_canonico"].upper()


def test_gira41_matching_programa_fuzzy(matcher):
    """Verifica resolución difusa de programas por nombre aproximado."""
    res = matcher.enlazar_programa("Diplomado en Derecho Notarial")
    assert res is not None
    assert "DERECHO" in res["nombre_canonico"].upper()
    assert res["pos"].startswith("POS-")
    assert res["score"] >= 0.80
    assert res["tipo_match"] in ("FUZZY_NOMBRE_PROGRAMA", "EXACTO_POS")




def test_gira41_matching_docente_catalogo(matcher):
    """Verifica grounding de docentes extraídos contra la nómina oficial."""
    res = matcher.enlazar_docente("Ing. Carlos Rojas")
    assert res is not None
    assert res["score"] >= 0.85
    assert "ROJAS" in res["nombre_canonico"].upper()


def test_gira41_programa_inexistente_retorna_none(matcher):
    """Un texto arbitrario que no se parece a ningún programa no debe matchear falsamente."""
    res = matcher.enlazar_programa("Curso de Cocina Molecular Japonesa Avanzada", umbral_minimo=0.85)
    assert res is None


# ==============================================================================
# 3. PRUEBAS GIRA-50: Validación y Resolución de Llave Foránea (CI / Nombre)
# ==============================================================================

@pytest.fixture(scope="module")
def fk_resolver():
    return FKResolver()


def test_gira50_estado_a_ci_valido(fk_resolver):
    """Estado A: Cuando el CI es válido y presente, se normaliza y valida directamente."""
    res = fk_resolver.resolver_estudiante(
        nombre="Mario Conde",
        ci_candidato="4.859.201"
    )
    assert res["estado_resolucion"] == "ESTADO_A_CI_VALIDO"
    assert res["ci"] == "4859201"
    assert res["es_sintetico"] is False
    assert res["requiere_auditoria"] is False
    assert res["score"] == 1.0


def test_gira50_estado_b_rescate_ci_por_nombre(fk_resolver):
    """Estado B: Cuando el CI falta, se busca en TBL_INSCRITOS por Nombre Completo."""
    if not fk_resolver.padron_nombres:
        pytest.skip("Padron TBL_INSCRITOS no disponible en entorno de prueba.")

    # Tomar un nombre real del padrón
    primer_nombre_limpio = next(iter(fk_resolver.padron_nombres.keys()))
    ci_esperado = fk_resolver.padron_nombres[primer_nombre_limpio]
    nombre_original = fk_resolver.nombres_originales[primer_nombre_limpio]

    # Resolver sin proporcionar CI
    res = fk_resolver.resolver_estudiante(
        nombre=nombre_original,
        ci_candidato=None
    )
    assert "ESTADO_B" in res["estado_resolucion"]
    assert res["ci"] == ci_esperado
    assert res["es_sintetico"] is False
    assert res["requiere_auditoria"] is False
    assert res["score"] >= 0.85


def test_gira50_estado_c_no_resuelto_genera_sintetico(fk_resolver):
    """Estado C: Persona no encontrada en el padrón genera CI sintético determinista y flag de auditoría."""
    nombre_fantasma = "Zacarías Desconocido Inventado 999"
    res = fk_resolver.resolver_estudiante(
        nombre=nombre_fantasma,
        ci_candidato=None
    )
    assert res["estado_resolucion"] == "ESTADO_C_NO_RESUELTO_SINTETICO"
    assert res["ci"].startswith("TEMP-CI-")
    assert res["es_sintetico"] is True
    assert res["requiere_auditoria"] is True
    assert res["score"] < 0.60
