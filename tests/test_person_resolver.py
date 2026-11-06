"""Cascada de personas sin cat_docente: CI exacta -> RapidFuzz en la dimensión (apellido + contexto) -> HITL."""
from pipeline.normalization.person_resolver import resolver_persona, quitar_titulos

DOC = [
    {"id": 268, "nombre": "Manuel Rojas", "ci": None, "contextos": ["Gestion de Proyectos"]},
    {"id": 460, "nombre": "Manuel Marcelo Rojas Barea", "ci": None, "contextos": ["Big Data"]},
    {"id": 151, "nombre": "Juan Humerto Rojas Noya", "ci": None, "contextos": ["Big Data"]},
]
EST = [{"id": 1, "nombre": "Ana Maria Perez Lima", "ci": "4859201", "contextos": ["Diplomado X"]}]


def test_quita_titulos():
    assert quitar_titulos("Ph.D. Lic. Ing. Dr. MSc. Mgr. Carlos Rojas") == "carlos rojas"


def test_docente_sin_homonimo_va_a_hitl():
    assert resolver_persona("Ing. Carlos Rojas", None, DOC) is None


def test_ci_exacta_prevalece():
    r = resolver_persona("Otro Nombre", "4.859.201", EST)
    assert r["id"] == 1 and r["fuente"] == "CI_EXACTA"


def test_fuzzy_con_apellido_y_titulo():
    r = resolver_persona("Dr. Juan Rojas Noya", None, DOC)
    assert r["id"] == 151 and r["fuente"] == "FUZZY"


def test_filtro_de_contexto_excluye_otro_modulo():
    assert resolver_persona("Juan Humerto Rojas", None, DOC, contexto=["Gestion de Proyectos"]) is None
    assert resolver_persona("Juan Humerto Rojas", None, DOC, contexto=["Big Data"])["id"] == 151


def test_un_solo_token_no_resuelve():
    assert resolver_persona("Rojas", None, DOC) is None
