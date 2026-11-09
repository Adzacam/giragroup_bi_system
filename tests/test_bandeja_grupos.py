"""Bandeja agrupada: agrupación de casos y acciones de grupo (APROBAR, MAPEAR_ESTADO, CORREGIR_FECHA) de approve-group."""
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def _estados_desde_config(monkeypatch):
    monkeypatch.setenv("TESTING", "true")  # reglas de estado desde pipeline.config, sin consultar el catálogo real
    from services.catalogo_estados import invalidar_cache
    invalidar_cache()
    yield
    invalidar_cache()


@pytest.fixture
def dw():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from core.database import Base
    import models  # noqa: F401
    from models.dim_origen import DimOrigenDocumental
    from models.fact_financiero import FactSituacionFinanciera
    from models.fact_rendimiento import FactRendimientoAcademico as A
    from models.staging_entidad import StagingEntidadNoResuelta as S

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _public(dbapi_connection, _):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS public")

    Base.metadata.create_all(bind=engine)
    s = sessionmaker(bind=engine)()
    s.add_all([DimOrigenDocumental(id_documento=1, nombre_archivo="acta.xlsx", tipo_fuente="ACTA"),
               DimOrigenDocumental(id_documento=2, nombre_archivo="cobranza.xlsx", tipo_fuente="COBRANZA")])
    # staging: dos CI con el mismo valor normalizado (un grupo), una homonimia y una línea de baja confianza
    s.add_all([
        S(id_staging=1, id_documento=1, tipo_entidad="ESTUDIANTE", motivo="CI_NOMBRE_DISCORDANTE", texto_original="CI: 123 | Nombre: A (Discordante con: B)", resuelto=False),
        S(id_staging=2, id_documento=1, tipo_entidad="ESTUDIANTE", motivo="CI_NOMBRE_DISCORDANTE", texto_original="CI: 123 | Nombre: C (Discordante con: D)", resuelto=False),
        S(id_staging=3, id_documento=2, tipo_entidad="ESTUDIANTE", motivo="HOMONIMIA", texto_original="Ing. Ana Rojas", resuelto=False),
        S(id_staging=4, id_documento=2, tipo_entidad="ESTUDIANTE", motivo="BAJA_CONFIANZA_IA", texto_original="A: 5 | FECHA: 2026-01-02", resuelto=False),
        S(id_staging=5, id_documento=1, tipo_entidad="ESTUDIANTE", motivo="HOMONIMIA", texto_original="Resuelto Ya", resuelto=True),
    ])
    ok = dict(id_documento=1, id_estudiante=10, id_modulo=7, nota_final=80, id_tiempo=1, requiere_revision=True)
    s.add_all([
        # estados válidos y completos: APROBAR
        A(id_hecho_aca=1, estado_academico="Aprobado", estado_tutoria="Aprobado", estado_arca="Titulado", **ok),
        A(id_hecho_aca=2, estado_academico="Aprobado", estado_tutoria="Aprobado", estado_arca="Titulado", **ok),
        # combinación no admitida: MAPEAR_ESTADO
        A(id_hecho_aca=3, estado_academico="Aprobado", estado_tutoria="Tutoria", estado_arca="Titulado", **ok),
        # estado fuera de catálogo: MAPEAR_ESTADO
        A(id_hecho_aca=4, estado_academico="Retirado", estado_tutoria="Aprobado", estado_arca="Titulado", **ok),
        # solo falta la fecha: CORREGIR_FECHA
        A(id_hecho_aca=5, estado_academico="Aprobado", estado_tutoria="Aprobado", estado_arca="Titulado",
          **{**ok, "id_tiempo": None}),
        # falta estudiante: MANUAL
        A(id_hecho_aca=6, estado_academico="Aprobado", estado_tutoria="Aprobado", estado_arca="Titulado",
          **{**ok, "id_estudiante": None}),
        # ya revisado: no aparece
        A(id_hecho_aca=7, estado_academico="Aprobado", estado_tutoria="Aprobado", estado_arca="Titulado",
          **{**ok, "requiere_revision": False}),
        FactSituacionFinanciera(id_hecho_fin=1, id_documento=2, id_estudiante=10, id_tiempo=1, monto_deuda=100, requiere_revision=True),
        FactSituacionFinanciera(id_hecho_fin=2, id_documento=2, id_estudiante=10, id_tiempo=None, monto_deuda=100, requiere_revision=True),
    ])
    s.commit()
    yield s
    s.close()


def _por_accion(res):
    out = {}
    for g in res["grupos"]:
        out.setdefault(g.get("accion_grupo", "STAGING"), []).append(g)
    return out


def test_agrupacion_cuenta_casos_y_grupos(dw):
    from services.bandeja_grupos import grupos_pendientes
    r = grupos_pendientes(dw)
    # 4 de staging (el resuelto no cuenta) + 6 hechos académicos + 2 financieros
    assert r["total_casos"] == 12
    ci = next(g for g in r["grupos"] if g["motivo"] == "CI_NOMBRE_DISCORDANTE")
    assert ci["n"] == 2 and ci["ids"] == [1, 2]
    acc = _por_accion(r)
    assert {k: sum(g["n"] for g in v) for k, v in acc.items()} == {"STAGING": 4, "APROBAR": 3, "MAPEAR_ESTADO": 2, "CORREGIR_FECHA": 2, "MANUAL": 1}
    assert [g["n"] for g in r["grupos"]] == sorted((g["n"] for g in r["grupos"]), reverse=True)


def test_agrupacion_se_limita_a_los_documentos_del_ciclo(dw):
    from services.bandeja_grupos import grupos_pendientes
    r = grupos_pendientes(dw, doc_ids=[2])
    assert r["total_casos"] == 4  # homonimia + baja confianza + 2 hechos financieros
    assert all("doc2" in g["valor"] or g["motivo"] in ("HOMONIMIA", "BAJA_CONFIANZA_IA") for g in r["grupos"])
    assert grupos_pendientes(dw, doc_ids=[99])["total_casos"] == 0


def test_motivo_de_estado(dw):
    from services.bandeja_grupos import motivo_estado
    assert motivo_estado("Aprobado", "Aprobado", "Titulado") == "OK"
    assert motivo_estado("Aprobado", "Tutoria", "Titulado") == "COMBINACION_INVALIDA"
    assert motivo_estado("Retirado", "Aprobado", "Titulado") == "ESTADO_FUERA_DE_CATALOGO"


def test_ids_del_grupo_devuelve_todos_los_casos(dw):
    from services.bandeja_grupos import clave_grupo, grupos_pendientes, ids_del_grupo
    assert ids_del_grupo(dw, clave_grupo("CI_NOMBRE_DISCORDANTE", "CI: 123 | Nombre: X (Discordante con: Y)")) == [1, 2]
    aprobar = _por_accion(grupos_pendientes(dw))["APROBAR"]
    aca = next(g for g in aprobar if "academico" in g["valor"])
    assert ids_del_grupo(dw, aca["clave"]) == ["HECHO-ACA-1", "HECHO-ACA-2"]
    fin = next(g for g in aprobar if "financiero" in g["valor"])
    assert ids_del_grupo(dw, fin["clave"]) == ["HECHO-FIN-1"]
    assert ids_del_grupo(dw, "HECHO_EN_REVISION::academico|doc9|falta:ninguno|x|y|z|estado:OK") == []
    assert ids_del_grupo(dw, aca["clave"], doc_ids=[2]) == []


def _usuario():
    return SimpleNamespace(id=1, username="auditor")


def test_aprobar_grupo_de_hechos_completos(dw):
    from models.fact_rendimiento import FactRendimientoAcademico as A
    from routers.dataops import AprobarGrupoRequest, _aprobar_grupo
    from services.bandeja_grupos import grupos_pendientes
    g = next(g for g in _por_accion(grupos_pendientes(dw))["APROBAR"] if "academico" in g["valor"])
    r = _aprobar_grupo(AprobarGrupoRequest(clave=g["clave"]), dw, _usuario())
    assert r["status"] == "success" and r["resolved_count"] == 2
    assert dw.query(A).filter(A.id_hecho_aca.in_([1, 2])).filter(A.requiere_revision == True).count() == 0  # noqa: E712
    # un segundo intento ya no encuentra casos pendientes
    assert _aprobar_grupo(AprobarGrupoRequest(clave=g["clave"]), dw, _usuario())["resolved_count"] == 0


def test_aprobar_grupo_con_campos_faltantes_se_rechaza(dw):
    from routers.dataops import AprobarGrupoRequest, _aprobar_grupo
    from services.bandeja_grupos import grupos_pendientes
    g = _por_accion(grupos_pendientes(dw))["MANUAL"][0]
    r = _aprobar_grupo(AprobarGrupoRequest(clave=g["clave"]), dw, _usuario())
    assert r["status"] == "error" and r["resolved_count"] == 0


def test_corregir_fecha_asigna_mes_y_gestion_a_todo_el_grupo(dw):
    from models.fact_rendimiento import FactRendimientoAcademico as A
    from models.fact_financiero import FactSituacionFinanciera as F
    from routers.dataops import AprobarGrupoRequest, _aprobar_grupo
    from services.bandeja_grupos import grupos_pendientes
    acc = _por_accion(grupos_pendientes(dw))["CORREGIR_FECHA"]
    # sin mes y gestión no se puede aprobar
    g_aca = next(g for g in acc if "academico" in g["valor"])
    assert _aprobar_grupo(AprobarGrupoRequest(clave=g_aca["clave"]), dw, _usuario())["status"] == "error"
    r = _aprobar_grupo(AprobarGrupoRequest(clave=g_aca["clave"], mes=3, gestion=2026), dw, _usuario())
    assert r["status"] == "success" and r["resolved_count"] == 1
    hecho = dw.query(A).filter(A.id_hecho_aca == 5).one()
    assert hecho.requiere_revision is False and hecho.id_tiempo is not None
    g_fin = next(g for g in acc if "financiero" in g["valor"])
    r = _aprobar_grupo(AprobarGrupoRequest(clave=g_fin["clave"], mes=3, gestion=2026), dw, _usuario())
    assert r["resolved_count"] == 1
    assert dw.query(F).filter(F.id_hecho_fin == 2).one().id_tiempo is not None


@pytest.fixture
def catalogo(monkeypatch):
    """Catálogo en SQLite con los estados de la hoja CRITERIOS (el real vive en giragroup_catalog_db)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    import core.database as cdb
    from models.catalogos import CatEstadoAcademico, CatEstadoArca, CatEstadoReprobado
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    cdb.CatalogBase.metadata.create_all(bind=engine, tables=[t for n, t in cdb.CatalogBase.metadata.tables.items()
                                                              if n in ("cat_estado_academico", "cat_estado_reprobado", "cat_estado_arca", "cat_combinacion_estado")])
    Sesion = sessionmaker(bind=engine)
    s = Sesion()
    s.add_all([CatEstadoAcademico(nombre_estado="Aprobado"), CatEstadoReprobado(nombre_detalle="Aprobado"),
               CatEstadoReprobado(nombre_detalle="Tutoria"), CatEstadoArca(nombre_arca="Titulado")])
    s.commit()
    s.close()
    monkeypatch.setattr(cdb, "CatalogSessionLocal", Sesion)
    return Sesion


def test_mapear_estado_agrega_la_combinacion_y_aprueba_el_grupo(dw, catalogo):
    from models.catalogos import CatCombinacionEstado
    from models.fact_rendimiento import FactRendimientoAcademico as A
    from routers.dataops import AprobarGrupoRequest, _aprobar_grupo
    from services.bandeja_grupos import grupos_pendientes
    g = next(g for g in _por_accion(grupos_pendientes(dw))["MAPEAR_ESTADO"] if "Tutoria" in g["valor"])
    r = _aprobar_grupo(AprobarGrupoRequest(clave=g["clave"], accion="MAPEAR_ESTADO"), dw, _usuario())
    assert r["resolved_count"] == 1 and r["motivo"] == "COMBINACION_INVALIDA" and "cat_combinacion_estado" in r["accion"]
    cs = catalogo()
    assert cs.query(CatCombinacionEstado).count() == 1
    cs.close()
    assert dw.query(A).filter(A.id_hecho_aca == 3).one().requiere_revision is False


def test_mapear_estado_reescribe_o_agrega_el_estado_fuera_de_catalogo(dw, catalogo):
    from models.catalogos import CatEstadoAcademico
    from models.fact_rendimiento import FactRendimientoAcademico as A
    from services.bandeja_grupos import grupos_pendientes, mapear_estado_grupo
    g = next(g for g in _por_accion(grupos_pendientes(dw))["MAPEAR_ESTADO"] if "Retirado" in g["valor"])
    r = mapear_estado_grupo(dw, g["clave"], None, canonico="Deserción")
    assert r["mapeados"] == 1 and "'Retirado' -> 'Deserción'" in r["accion"]
    hecho = dw.query(A).filter(A.id_hecho_aca == 4).one()
    assert hecho.estado_academico == "Deserción" and hecho.requiere_revision is False
    # sin canónico, el valor nuevo se agrega al catálogo de estados
    dw.query(A).filter(A.id_hecho_aca == 4).update({"estado_academico": "Retirado", "requiere_revision": True})
    dw.commit()
    g = next(g for g in _por_accion(grupos_pendientes(dw))["MAPEAR_ESTADO"] if "Retirado" in g["valor"])
    r = mapear_estado_grupo(dw, g["clave"], None)
    assert "agregado a catálogo" in r["accion"]
    cs = catalogo()
    assert cs.query(CatEstadoAcademico).filter_by(nombre_estado="Retirado").count() == 1
    cs.close()


def test_mapear_estado_de_un_grupo_ok_no_hace_nada(dw, catalogo):
    from services.bandeja_grupos import grupos_pendientes, mapear_estado_grupo
    g = next(g for g in _por_accion(grupos_pendientes(dw))["APROBAR"] if "academico" in g["valor"])
    assert mapear_estado_grupo(dw, g["clave"], None) == {"mapeados": 0, "motivo": "OK"}


def test_aprobar_grupo_de_staging_delega_en_la_resolucion_en_lote(dw, monkeypatch):
    import routers.dataops as d
    visto = {}

    def falso(payload, db, current_user):
        visto["ids"] = payload.item_ids
        visto["estudiante"] = payload.estudiante_resuelto
        return {"status": "success", "resolved_count": len(payload.item_ids)}

    monkeypatch.setattr(d, "batch_resolve_review_items", falso)
    from services.bandeja_grupos import clave_grupo
    clave = clave_grupo("CI_NOMBRE_DISCORDANTE", "CI: 123 | Nombre: A (Discordante con: B)")
    r = d._aprobar_grupo(d.AprobarGrupoRequest(clave=clave, estudiante_resuelto="Ana Rojas"), dw, _usuario())
    assert visto == {"ids": ["1", "2"], "estudiante": "Ana Rojas"} and r["resolved_count"] == 2 and r["casos_del_grupo"] == 2
    assert d._aprobar_grupo(d.AprobarGrupoRequest(clave=clave, doc_id=2), dw, _usuario())["resolved_count"] == 0  # alcance por documento
