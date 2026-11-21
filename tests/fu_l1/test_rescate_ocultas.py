"""
FU-L1b (decisión de Lean): hojas ocultas de planificación que se usan.

Una oculta de un período sin hoja visible se usa; una oculta de un período ya cubierto por una visible se
ignora como duplicada; un borrador oculto se ignora; un informe de metas oculto se usa. El clasificador y el
extractor de planificación toman la misma decisión. Libros sintéticos con otros nombres de hoja y de archivo.
"""

from collections import Counter

import pytest

from models.log_inconsistencia import LogInconsistencia
from models.log_pipeline import LogPipelineIngesta
from models.staging_registro import StagingRegistroCrudo
from pipeline.ingesta import leer_archivo_con_metadatos
from services.planificacion_extractor import extraer_libro_planificacion
from tests.fixtures.fuentes_sinteticas import constructor as ctor
from tests.fu_l1.test_ingesta_hojas import ingesta  # noqa: F401  (fixture)


@pytest.fixture(params=[ctor.PLAN_ORIGINAL, ctor.PLAN_VARIANTE], ids=["original", "variante"])
def plan(request, tmp_path):
    return request.param, ctor.construir_plan(request.param, tmp_path)


def test_decision_por_hoja_oculta(plan):
    receta, ruta = plan
    libro = leer_archivo_con_metadatos(str(ruta))
    c = {n: (h.clasificacion.decision, h.clasificacion.regla, h.clasificacion.motivo) for n, h in libro.items()}
    assert c[receta.visible][:2] == ("usar", "tabla_de_datos")
    assert c[receta.oculta_libre] == ("usar", "oculta_rescatada", "oculta rescatada: período sin hoja visible")
    assert c[receta.oculta_cubierta][:2] == ("ignorar", "oculta_duplicada")
    assert c[receta.oculta_borrador][:2] == ("ignorar", "oculta")
    assert c[receta.oculta_informe][:2] == ("usar", "oculta_rescatada")
    assert libro[receta.oculta_libre].meta.periodo_dominante == "2027-01"
    assert libro[receta.oculta_informe].meta.gestiones_metas == [2027]


def test_original_y_variante_identicos(tmp_path):
    a = leer_archivo_con_metadatos(str(ctor.construir_plan(ctor.PLAN_ORIGINAL, tmp_path)))
    b = leer_archivo_con_metadatos(str(ctor.construir_plan(ctor.PLAN_VARIANTE, tmp_path)))
    firma = lambda libro: Counter((h.meta.estado, h.clasificacion.decision, h.clasificacion.regla, h.meta.filas_datos)
                                  for h in libro.values())
    assert firma(a) == firma(b)


def test_extractor_y_clasificador_coinciden(plan):
    receta, ruta = plan
    libro = leer_archivo_con_metadatos(str(ruta))
    datos = extraer_libro_planificacion(str(ruta), hojas_excluidas={n for n, h in libro.items() if not h.usada})
    por_hoja = Counter(f["hoja"] for f in datos["filas"])
    assert dict(por_hoja) == {receta.visible: 5, receta.oculta_libre: 4}
    assert {m["celda_origen"].split("!")[0] for m in datos["metas"]} == {receta.oculta_informe}
    usadas_extractor = set(por_hoja) | {receta.oculta_informe}
    assert usadas_extractor == {n for n, h in libro.items() if h.usada}


def test_oculta_visible_si_cubre_el_periodo_con_otra_forma_no_rescata(tmp_path):
    """La deduplicación compara períodos, no nombres: renombrar la visible no cambia la decisión."""
    receta = ctor.RecetaPlan(**{**ctor.PLAN_ORIGINAL.__dict__, "archivo": "otro.xlsx", "visible": "Hoja de trabajo"})
    libro = leer_archivo_con_metadatos(str(ctor.construir_plan(receta, tmp_path)))
    assert libro[receta.oculta_cubierta].clasificacion.regla == "oculta_duplicada"


def test_ingesta_una_sola_decision_y_sin_aviso_de_contradiccion(ingesta, tmp_path):  # noqa: F811
    db, _, procesar = ingesta
    receta = ctor.PLAN_VARIANTE
    _, doc = procesar(ctor.construir_plan(receta, tmp_path), tipo_fuente="PLANIFICACION")
    stg = {s.hoja: (s.categoria, s.n_filas) for s in db.query(StagingRegistroCrudo).filter_by(id_documento=doc.id_documento)}
    assert stg == {receta.visible: ("planificacion", 5), receta.oculta_libre: ("planificacion", 4),
                   receta.oculta_informe: ("planificacion_meta", 18)}
    ign = {i.campo_afectado: (i.regla_origen if hasattr(i, "regla_origen") else None, i.descripcion)
           for i in db.query(LogInconsistencia).filter_by(id_documento=doc.id_documento, tipo_regla="HOJA_IGNORADA")}
    assert set(ign) == {receta.oculta_cubierta, receta.oculta_borrador}
    assert "período ya cubierto" in ign[receta.oculta_cubierta][1]
    avisos = [l.mensaje for l in db.query(LogPipelineIngesta).filter_by(id_documento=doc.id_documento, nivel="WARN")]
    assert not any("extractor de planificación" in a for a in avisos)
