"""F5C C-3: cada entidad lleva `confianza` y `origen_confianza` medidas según su origen; cero constantes en extraccion.py;
el agregador (mínimo), los umbrales (0,85 / 0,60) y la cascada no cambian."""
import os
import re
import sys
from types import SimpleNamespace

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from routers.dataops import extraccion as ex  # noqa: E402
from routers.dataops.extraccion import extract_entities_from_line, explicar_confianza  # noqa: E402

ORIGENES = {"BETO", "REGLA_ENCABEZADO", "REGEX", "FUZZY", "CI_EXACTA"}
SRC = os.path.join(ROOT, "backend", "routers", "dataops", "extraccion.py")


def _cat():
    est = [SimpleNamespace(id_estudiante=1, nombre_completo="Maria Lopez Quispe", ci_numero="4567890", ci=None,
                           codigo_estudiante="4567890", programa_origen=None)]
    doc = [SimpleNamespace(id_docente=1, nombre_completo="Ing. Pedro Rojas Vargas", _contextos=[])]
    mod = [SimpleNamespace(id_modulo=100, nombre_modulo="Gestion de Datos", pos_code="POS-1001", programa="DIPLOMADO EN DATOS")]
    return est, doc, mod


def _ent(ents, label):
    return next((e for e in ents if e["label"] == label), None)


def test_ci_exacta_es_uno():
    est, doc, mod = _cat()
    ents, _, _ = extract_entities_from_line("ESTUDIANTE: Maria Lopez | CI: 4567890 | MODULO: Gestion de Datos", est, doc, mod)
    e = _ent(ents, "ESTUDIANTE")
    assert e["origen_confianza"] == "CI_EXACTA" and e["confianza"] == 1.0
    assert _ent(ents, "DOCUMENTO / CI")["origen_confianza"] == "CI_EXACTA"


def test_fuzzy_es_el_puntaje_sobre_100():
    est, doc, mod = _cat()
    ents, _, _ = extract_entities_from_line("ESTUDIANTE: Maria Lopez Quispe | MODULO: Gestion de Datos", est, doc, mod)
    e = _ent(ents, "ESTUDIANTE")
    assert e["origen_confianza"] == "FUZZY"
    assert e["confianza"] == pytest.approx(e["fuzzScore"] / 100, abs=1e-3)


def test_encabezado_es_similitud_por_validez():
    ents, _, _ = extract_entities_from_line("DOCENTES: Pedro Rojas Vargas | MODULO: Algo Nuevo", [], [], [], tipo_fuente="ACTA")
    d = _ent(ents, "DOCENTE")
    sim = ex.similitud_encabezado("DOCENTES", ex._ENC_DOCENTE) / 100
    assert d["origen_confianza"] == "REGLA_ENCABEZADO" and d["confianza"] == pytest.approx(round(sim * 1.0, 4))
    assert 0.85 <= d["confianza"] < 1.0
    assert explicar_confianza(d).startswith("Regla por encabezado: similitud 0,93")


def test_encabezado_con_catalogo_usa_el_puntaje_del_catalogo():
    est, doc, mod = _cat()
    ents, _, _ = extract_entities_from_line("MODULO: Gestion de Datos | NOTA: 90", est, doc, mod)
    m = _ent(ents, "MÓDULO")
    assert m["origen_confianza"] == "REGLA_ENCABEZADO"
    assert m["confianza"] == pytest.approx(m["detalleConfianza"]["similitudEncabezado"] * m["fuzzScore"] / 100, abs=1e-3)


def test_regex_vale_uno_solo_si_valida():
    ents, _, _ = extract_entities_from_line("El estudiante con documento 4567890 aprobo", [], [], [])
    ci = _ent(ents, "DOCUMENTO / CI")
    assert ci["origen_confianza"] == "REGEX" and ci["confianza"] == 1.0
    ents, _, rev = extract_entities_from_line("ESTUDIANTE: Ana Rojas Paz | CI: 45678?", [], [], [])
    ci = _ent(ents, "DOCUMENTO / CI")
    assert ci["confianza"] < 1.0 and rev is True   # la validez se mide (5/6 dígitos) y la revisión sigue forzada


def test_beto_es_la_probabilidad_del_modelo():
    est, doc, mod = _cat()
    ents, _, _ = extract_entities_from_line("COMENTARIO: algo | ESTUDIANTE: M. L. Q.", est, doc, mod,
                                            est_beto={"nombre": "Maria Lopez Quispe", "prob": 0.73})
    e = _ent(ents, "ESTUDIANTE")
    assert e["origen_confianza"] == "BETO" and e["confianza"] == 0.73 and e["lecturaModelo"] == 0.73
    assert explicar_confianza(e) == "BETO p = 0,73"


def test_perfil_nuevo_no_lleva_beto_si_beto_no_corrio():
    ents, _, _ = extract_entities_from_line(
        "ESTUDIANTE: Ana Rojas Paz | DOCENTE: Ing. Luis Vaca Soto | MODULO: Tema Nuevo X | NOMBRE DEL PROGRAMA: DIPLOMADO Z",
        [], [], [], tipo_fuente="ACTA")
    nuevos = [e for e in ents if e.get("es_nuevo_perfil")]
    assert len(nuevos) == 3
    for e in ents:
        assert e["origen_confianza"] in ORIGENES and e["origen_confianza"] != "BETO"
        assert e["fuente_resolucion"] != "BETO"
        assert "betoConfidence" not in e and "lecturaModelo" not in e


def test_indice_es_el_minimo_y_umbral_sin_cambio():
    from routers.dataops._comun import UMBRAL_INDICE_REGISTRO_DEC
    assert UMBRAL_INDICE_REGISTRO_DEC == 0.85
    est, doc, mod = _cat()
    ents, score, rev = extract_entities_from_line("DOCENTES: Pedro Rojas Vargas | MODULO: Tema Nuevo X", est, [], mod, tipo_fuente="ACTA")
    nucleo = [e["confianza"] for e in ents if e["label"] in ("ESTUDIANTE", "MÓDULO", "DOCENTE", "PROGRAMA", "CONCEPTO_FINANCIERO")]
    assert score == round(min(nucleo), 2)
    assert rev == (score < 0.85)


def test_cero_constantes_de_confianza_en_extraccion():
    src = open(SRC, encoding="utf-8").read()
    patrones = [
        r"[\"'](?:confianza|lecturaModelo|betoConfidence)[\"']\s*:\s*-?\d",   # una confianza escrita como número
        r"prob_override\.get\(",                                            # lecturas base por defecto (0,85 / 0,88 / 0,91)
        r"scores_entidades\.append\(\s*\d",                                  # 0,94 programa / 0,92 concepto en el índice
        r"score_confianza\s*=\s*\d",                                         # 0,88 por defecto
        r"best_doc_score\s*=\s*\d",                                          # 94 / 88 de la coincidencia por contexto
        r"score\s*=\s*max\(score,\s*\d",                                     # alias fijos de módulo (87,5 / 89 / 91,5 / 93 / 95)
    ]
    hallados = {p: re.findall(p, src) for p in patrones}
    assert all(not v for v in hallados.values()), hallados


def test_privacidad_publica_confianza_y_origen_con_tokens_enmascarados():
    from services.dataops_privacy import registro_beto_publico
    ents, _, _ = extract_entities_from_line("ESTUDIANTE: Ana Rojas Paz | CI: 4567890 | MODULO: Gestion de Datos", [], [], [])
    pub = registro_beto_publico({"raw_text": "ESTUDIANTE: Ana Rojas Paz | CI: 4567890", "tipo_fuente": "ACTA",
                                 "lectura": {"entidades": ents}})
    e_pub = {e["label"]: e for e in pub["lectura"]["entidades"]}
    est = e_pub["ESTUDIANTE"]
    assert est["token"] == "••••" and est["origen_confianza"] == "REGLA_ENCABEZADO" and est["confianza"] == 1.0
    assert "4567890" not in str(pub)
