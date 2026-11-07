"""Cascada de personas sin cat_docente: CI exacta -> RapidFuzz en la dimensión (apellido + contexto) -> HITL."""
from pipeline.normalization.person_resolver import resolver_persona, resolver_persona_detalle, quitar_titulos

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


def test_bloqueo_escalonado_programa_sin_candidato_escala_a_dimension():
    # El programa del registro no contiene candidatos: se escala a la dimensión completa (umbral 0,92 + apellido)
    r = resolver_persona_detalle("Juan Humerto Rojas", None, DOC, contexto=["Gestion de Proyectos"])
    assert r["resultado"]["id"] == 151 and r["nivel"] == "DIMENSION"
    r = resolver_persona_detalle("Juan Humerto Rojas", None, DOC, contexto=["Big Data"])
    assert r["resultado"]["id"] == 151 and r["nivel"] == "PROGRAMA"


def test_nivel_modulo_precede_a_programa():
    docs = [{"id": 1, "nombre": "Ana Lopez Rojas", "ci": None, "modulos": ["Modulo A"], "contextos": ["P1"]}]
    assert resolver_persona_detalle("Ana Lopez Rojas", None, docs, contexto=["P1"], ctx_modulo=["Modulo A"])["nivel"] == "MODULO"


def test_dos_empatados_van_a_hitl_por_empate():
    docs = [{"id": 1, "nombre": "Ana Lopez Rojas", "ci": None}, {"id": 2, "nombre": "Ana Lopez Rojas", "ci": None}]
    r = resolver_persona_detalle("Ana Lopez Rojas", None, docs)
    assert r["resultado"] is None and r["motivo"] == "empate"


def test_cero_candidatos_motivo():
    assert resolver_persona_detalle("Zoe Quispe Mamani", None, DOC)["motivo"] == "sin_candidatos"


def test_un_solo_token_no_resuelve():
    assert resolver_persona("Rojas", None, DOC) is None


def test_un_correo_no_es_un_nombre():
    from pipeline.normalization.person_resolver import es_correo
    assert es_correo("alanhuarca1@gmail.com") and not es_correo("Alan Huarca")
    assert resolver_persona_detalle("alanhuarca1@gmail.com", None, DOC)["motivo"] == "correo"
