"""Censura de datos personales: el CI completo no viaja en las respuestas de DataOps al navegador."""
from routers.dataops import extract_entities_from_line
from services.dataops_evaluation_service import (
    cis_en_entidades,
    entidad_sin_ci,
    texto_sin_ci,
)

CI = "7391044"


def test_texto_sin_ci_reemplaza_por_version_enmascarada():
    assert texto_sin_ci(f"Vargas Luis {CI} LP 82", {CI}) == "Vargas Luis ••••044 LP 82"


def test_texto_sin_ci_no_toca_textos_sin_ci_ni_valores_no_texto():
    assert texto_sin_ci("Sin documento", {CI}) == "Sin documento"
    assert texto_sin_ci(82.5, {CI}) == 82.5


def test_detecta_el_numero_suelto_aunque_el_ci_traiga_extension():
    cis = cis_en_entidades([{"label": "DOCUMENTO / CI", "token": "7391044 LP"}])
    assert {"7391044 LP", "7391044"} <= cis


def test_entidad_enmascara_campos_ci_y_textos_que_lo_contienen():
    ent = {"label": "ESTUDIANTE", "token": "Vargas Luis", "ci": CI, "matchedCanonical": f"Vargas Luis ({CI})"}
    pub = entidad_sin_ci(ent, {CI})
    assert pub["ci"] == "••••044" and CI not in pub["matchedCanonical"] and pub["token"] == "Vargas Luis"


def test_pipeline_real_de_extraccion_no_deja_el_ci_en_lo_publicado():
    linea = f"Estudiante: Vargas Alarcón Luis, CI {CI} LP, módulo Minería de Datos, nota 82"
    ents, *_ = extract_entities_from_line(linea, [], [], [], tipo_escala="CENTESIMAL_100", tipo_fuente="ACTA", apariciones_lote=1)
    cis = cis_en_entidades(ents)
    publicas = [entidad_sin_ci(e, cis) for e in ents]
    assert CI in str(ents), "la extracción debe encontrar el CI para que la prueba tenga sentido"
    assert CI not in str(publicas) and CI not in texto_sin_ci(linea, cis)
