"""Opción 3 (BETO_SUGERENCIA_HITL): candidatos ordenados por score combinado en la bandeja. Solo ordena; el humano decide."""
from types import SimpleNamespace

import pytest

from models.dim_estudiante import DimEstudiante
from models.staging_entidad import StagingEntidadNoResuelta
from pipeline import config as cfg
from services import beto_integracion as bi
from services.dw_loader import DWLoaderService
from services.revision_consulta import caso_guardado

CANDIDATOS = [{"id": 1, "nombre": "Juan Mamani Quispe"}, {"id": 2, "nombre": "Juan Carlos Mamani Flores"}, {"id": 3, "nombre": "Pedro Gomez"}]


def test_el_score_combinado_muestra_ambos_componentes_y_ordena_de_mayor_a_menor():
    tramo = bi.EntidadBeto("ESTUDIANTE", "Juan Carlos Mamani Flores", 0, 25, 0.99)
    sug = bi.sugerencias_ordenadas("Juan Mamani", CANDIDATOS, [tramo])
    assert [s["score_combinado"] for s in sug] == sorted((s["score_combinado"] for s in sug), reverse=True)
    for s in sug:
        esperado = cfg.BETO_PESO_SIMILITUD * s["similitud"] + cfg.BETO_PESO_PROBABILIDAD * s["probabilidad_beto"] * s["similitud_beto"]
        assert s["score_combinado"] == pytest.approx(esperado, abs=1e-3)
        assert {"similitud", "probabilidad_beto", "similitud_beto", "score_combinado"} <= set(s)
    assert cfg.BETO_PESO_SIMILITUD + cfg.BETO_PESO_PROBABILIDAD == pytest.approx(1.0)


def test_la_lectura_de_beto_puede_cambiar_el_orden_que_daria_la_similitud_sola():
    solo_similitud = bi.sugerencias_ordenadas("Juan Mamani", CANDIDATOS, None)
    tramo = bi.EntidadBeto("ESTUDIANTE", "Juan Carlos Mamani Flores", 0, 25, 0.99)
    con_beto = bi.sugerencias_ordenadas("Juan Mamani", CANDIDATOS, [tramo])
    assert solo_similitud[0]["nombre"] == "Juan Mamani Quispe" and con_beto[0]["nombre"] == "Juan Carlos Mamani Flores"
    assert all(s["probabilidad_beto"] is None and s["score_combinado"] == s["similitud"] for s in solo_similitud)


def test_sin_lectura_de_beto_ordena_por_similitud_y_el_desempate_es_estable():
    iguales = [{"id": 9, "nombre": "Ana Rojas"}, {"id": 8, "nombre": "Ana Rojas"}]
    assert bi.sugerencias_ordenadas("Ana Rojas", iguales, None) == bi.sugerencias_ordenadas("Ana Rojas", list(reversed(iguales)), None)


def test_se_limita_la_cantidad_de_candidatos():
    muchos = [{"id": i, "nombre": f"Ana Maria Rojas {i}"} for i in range(20)]
    assert len(bi.sugerencias_ordenadas("Ana Maria Rojas", muchos, None)) == cfg.BETO_SUGERENCIAS_MAXIMAS


def test_candidatos_por_similitud_enmascara_la_cedula():
    personas = [SimpleNamespace(id_estudiante=1, nombre_completo="Maria Lopez Quispe", ci_numero="4567890", ci=None, programa_origen=None),
                SimpleNamespace(id_estudiante=2, nombre_completo="Zzz Qqq", ci_numero=None, ci=None, programa_origen=None)]
    out = bi.candidatos_por_similitud("Maria Lopez Quispe", personas)
    assert [c["id"] for c in out] == [1] and "4567890" not in str(out) and out[0]["ci_enmascarado"]


def _caso(payload):
    ent = SimpleNamespace(id_staging=7, id_documento=1, tipo_entidad="ESTUDIANTE", motivo="HOMONIMIA", mejor_candidato="Juan Mamani Quispe",
                          estado_resolucion="PENDIENTE", nivel_confianza=0.7, lock_usuario_id=None, lock_expira=None, resuelto_en=None,
                          ci_temporal=None, score_fuzzy=91.0, texto_original="Juan Mamani", payload_json=payload)
    return caso_guardado(ent, SimpleNamespace(tipo_fuente="ACTA", nombre_archivo="a.xlsx"))


def test_la_api_agrega_el_campo_solo_cuando_hay_sugerencias_y_no_cambia_el_resto():
    sin = _caso(None)
    sug = [{"id": 2, "nombre": "Juan Carlos Mamani Flores", "similitud": 0.7, "probabilidad_beto": 0.99, "similitud_beto": 1.0, "score_combinado": 0.85}]
    sug_enmascarado = [{**s, "nombre": "••••"} for s in sug]
    con = _caso({"sugerencias": sug})
    assert "sugerencias_beto" not in sin and con["sugerencias_beto"] == sug_enmascarado
    assert con["candidatos"] == sug_enmascarado
    assert {k: v for k, v in con.items() if k not in ("sugerencias_beto", "candidatos", "acciones")} == {
        k: v for k, v in sin.items() if k not in ("candidatos", "acciones")
    }  # cambio aditivo: ninguna clave previa no ligada a candidatos varía
    assert con["un_clic"] == sin["un_clic"] and con["estado_resolucion"] == "PENDIENTE"   # no autoaprueba ni marca un clic


def test_homonimia_guarda_los_candidatos_ordenados_si_la_opcion_esta_encendida(dw_sqlite):
    db = dw_sqlite
    db.add_all([DimEstudiante(nombre_completo="Juan Perez Soto", codigo_estudiante="E1", deprecado=False),
                DimEstudiante(nombre_completo="Juan Perez Soto", codigo_estudiante="E2", deprecado=False)])
    db.commit()
    llamadas = []

    def sugeridor(nombre, candidatos, texto):
        llamadas.append((nombre, [c["nombre"] for c in candidatos], texto))
        return bi.sugerencias_ordenadas(nombre, candidatos, None)

    loader = DWLoaderService(db)
    loader.sugeridor, loader._texto_beto = sugeridor, "ESTUDIANTE: Juan Perez Soto"
    assert loader.resolver_o_crear_estudiante(ci=None, nombre="Juan Perez Soto", confianza_ia=0.9) == (None, "C")
    stg = db.query(StagingEntidadNoResuelta).one()
    assert stg.motivo == "HOMONIMIA" and stg.resuelto is False and stg.estado_resolucion in (None, "PENDIENTE")
    assert [s["nombre"] for s in stg.payload_json["sugerencias"]] == ["Juan Perez Soto", "Juan Perez Soto"]
    assert llamadas == [("Juan Perez Soto", ["Juan Perez Soto", "Juan Perez Soto"], "ESTUDIANTE: Juan Perez Soto")]


def test_homonimia_sin_la_opcion_no_agrega_payload(dw_sqlite):
    db = dw_sqlite
    db.add_all([DimEstudiante(nombre_completo="Juan Perez Soto", codigo_estudiante="E1", deprecado=False),
                DimEstudiante(nombre_completo="Juan Perez Soto", codigo_estudiante="E2", deprecado=False)])
    db.commit()
    DWLoaderService(db).resolver_o_crear_estudiante(ci=None, nombre="Juan Perez Soto", confianza_ia=0.9)
    assert db.query(StagingEntidadNoResuelta).one().payload_json is None


def test_un_fallo_del_sugeridor_no_impide_derivar_el_caso(dw_sqlite):
    db = dw_sqlite
    db.add_all([DimEstudiante(nombre_completo="Juan Perez Soto", codigo_estudiante="E1", deprecado=False),
                DimEstudiante(nombre_completo="Juan Perez Soto", codigo_estudiante="E2", deprecado=False)])
    db.commit()
    loader = DWLoaderService(db)
    loader.sugeridor = lambda *a: (_ for _ in ()).throw(RuntimeError("BETO caído"))
    assert loader.resolver_o_crear_estudiante(ci=None, nombre="Juan Perez Soto", confianza_ia=0.9) == (None, "C")
    assert db.query(StagingEntidadNoResuelta).one().payload_json is None
