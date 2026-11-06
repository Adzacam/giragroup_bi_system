"""
tests/test_ingesta_sin_timeout.py
---------------------------------
Subir los 10 libros de uploads/data terminaba en 504: upload-batch evaluaba todas las líneas (92 837) antes de
responder, a ~105 ms por línea (difflib en Python puro contra todo el catálogo), y el gateway corta a los 300 s.
1. fuzzy_score conserva sus resultados (ahora con rapidfuzz en C y normalización cacheada).
2. upload-batch responde tras la ingesta y deja la evaluación en segundo plano.
3. /resumen y /beto-reading reutilizan la evaluación mientras el lote no cambia.
"""

from difflib import SequenceMatcher

import pytest
from fastapi import BackgroundTasks

from services.dataops_evaluation_service import fuzzy_score, strip_accents


@pytest.mark.parametrize("a, b, esperado", [
    ("Juan Pérez", "JUAN PEREZ", (100.0, "Levenshtein Exact Match")),
    ("NATALY CAERO FORONDA", "Nataly Caero Foronda", (100.0, "Levenshtein Exact Match")),
    ("Maria Lopez", "Maria Lopez Vargas", None),   # subconjunto / rapidfuzz alto
    ("", "Juan", (0.0, "Empty")),
])
def test_fuzzy_score_casos_conocidos(a, b, esperado):
    score, algoritmo = fuzzy_score(a, b)
    if esperado:
        assert (score, algoritmo) == esperado
    else:
        assert score >= 80.0


def test_fuzzy_score_sin_palabras_en_comun_aproxima_a_difflib():
    a, b = "Diplomado en Gestion Publica", "Curso Taller Excel"
    score, algoritmo = fuzzy_score(a, b)
    t1 = " ".join(sorted(set(strip_accents(a).lower().split())))
    t2 = " ".join(sorted(set(strip_accents(b).lower().split())))
    difflib_pct = SequenceMatcher(None, t1, t2).ratio() * 100
    assert algoritmo == "SequenceMatcher Ratio"
    assert score < 80.0 and abs(score - difflib_pct) <= 10.0  # misma razón 2·M/T; nunca cruza el umbral de 80


def test_strip_accents_cacheado_y_sin_cambios():
    assert strip_accents("Ana Lucía Ríos") == "Ana Lucia Rios"
    assert strip_accents(None) == "" and strip_accents("") == ""


@pytest.fixture
def dw():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from core.database import Base
    import models  # noqa: F401

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _public(dbapi_connection, _):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS public")

    Base.metadata.create_all(bind=engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def test_upload_batch_no_evalua_antes_de_responder(dw, monkeypatch):
    from io import BytesIO
    from starlette.datastructures import Headers, UploadFile
    from routers import dataops

    def _no_sincrono(*_a, **_k):
        raise AssertionError("upload-batch no debe evaluar el lote antes de responder")

    monkeypatch.setattr(dataops, "_evaluar_documentos_lote", _no_sincrono)
    contenido = "Nombre Completo,Cédula de Identidad,Ciudad\nAdriano Daza Camargo,CI-4892019,Cochabamba\n".encode("utf-8")
    archivo = UploadFile(file=BytesIO(contenido), filename="inscripciones.csv", headers=Headers({"content-type": "text/csv"}))
    tareas = BackgroundTasks()

    res = dataops.upload_batch(files=[archivo], source_types=["ADMISION"], tipos_fuente=["ADMISION"], tipos_escala=None,
                               archivos_meta=None, institucion="GiraGroup Posgrado", periodo=None, tipo_escala_global=None,
                               background_tasks=tareas, db=dw)

    assert res.archivos_exitosos == 1
    assert [t.func for t in tareas.tasks] == [dataops._evaluar_lote_en_segundo_plano]


def test_lectura_del_lote_reutiliza_la_evaluacion_hasta_que_cambia(dw, monkeypatch, tmp_path):
    from models.dim_origen import DimOrigenDocumental
    from models.staging_entidad import StagingEntidadNoResuelta
    from routers import dataops
    from services import cache_consultas, cache_lectura

    cache_consultas.invalidar()
    monkeypatch.setattr(cache_lectura, "DIR", tmp_path)  # caché de disco aislada del entorno
    llamadas = []
    monkeypatch.setattr(dataops, "_evaluar_documentos_lote",
                        lambda db, docs, persistir_staging=True, **kw: llamadas.append(1) or {"totalTuplas": 0, "detalles": []})
    dw.add(DimOrigenDocumental(id_documento=1, nombre_archivo="ARCA.xlsx", tipo_fuente="ACTA"))
    dw.commit()
    docs = dw.query(DimOrigenDocumental).all()

    dataops._evaluacion_lectura(dw, docs)
    dataops._evaluacion_lectura(dw, docs)
    assert len(llamadas) == 1  # el segundo GET no recalcula

    from models.staging_registro import StagingRegistroCrudo
    dw.add(StagingRegistroCrudo(id_documento=1, texto_plano="x"))
    dw.commit()
    dataops._evaluacion_lectura(dw, docs)
    assert len(llamadas) == 2  # cambió el staging del lote: se recalcula
    cache_consultas.invalidar()


def test_lectura_calculada_por_otro_worker_se_lee_del_disco(dw, monkeypatch, tmp_path):
    """La caché en memoria es por proceso: lo que otro worker dejó en disco no se vuelve a calcular."""
    from models.dim_origen import DimOrigenDocumental
    from routers import dataops
    from services import cache_consultas, cache_lectura

    cache_consultas.invalidar()
    monkeypatch.setattr(cache_lectura, "DIR", tmp_path)
    dw.add(DimOrigenDocumental(id_documento=7, nombre_archivo="ARCA.xlsx", tipo_fuente="ACTA"))
    dw.commit()
    docs = dw.query(DimOrigenDocumental).all()
    clave = ("evaluacion_lectura", (7,), dataops._huella_evaluacion(dw, [7]))
    cache_lectura.guardar(clave, {"totalTuplas": 42, "detalles": []})

    def _no_recalcular(*a, **kw):
        raise AssertionError("no debía recalcular")
    monkeypatch.setattr(dataops, "_evaluar_documentos_lote", _no_recalcular)
    assert dataops._evaluacion_lectura(dw, docs)["totalTuplas"] == 42
    cache_consultas.invalidar()


def test_resolucion_de_la_bandeja_se_superpone_sin_releer(dw, monkeypatch, tmp_path):
    """Revisar un caso no vuelve a leer el lote con BETO: la resolución se aplica sobre la lectura cacheada."""
    from models.dim_origen import DimOrigenDocumental
    from models.staging_entidad import StagingEntidadNoResuelta
    from routers import dataops
    from services import cache_consultas, cache_lectura

    cache_consultas.invalidar()
    monkeypatch.setattr(cache_lectura, "DIR", tmp_path)
    llamadas = []
    base = {"totalTuplas": 2, "autoCount": 1, "auditCount": 1, "inconsistenciasCount": 0, "detalles": [
        {"stg_id": 5, "raw_text": "fila A", "categoria_particion": "AUTOMATICO", "estado": "AUTOMATICO"},
        {"stg_id": 5, "raw_text": "fila B", "categoria_particion": "REVISION", "estado": "REVISION"},
    ]}
    monkeypatch.setattr(dataops, "_evaluar_documentos_lote", lambda *a, **kw: llamadas.append(1) or base)
    dw.add(DimOrigenDocumental(id_documento=9, nombre_archivo="ARCA.xlsx", tipo_fuente="ACTA"))
    dw.commit()
    docs = dw.query(DimOrigenDocumental).all()
    assert dataops._evaluacion_lectura(dw, docs)["auditCount"] == 1

    dw.add(StagingEntidadNoResuelta(id_documento=9, tipo_entidad="ESTUDIANTE", texto_original="fila B",
                                    registro_origen_id=5, resuelto=True, estado_resolucion="RESUELTO_HUMANO"))
    dw.commit()
    res = dataops._evaluacion_lectura(dw, docs)
    assert len(llamadas) == 1  # no se releyó
    assert (res["autoCount"], res["auditCount"]) == (2, 0)
    assert base["detalles"][1]["categoria_particion"] == "REVISION"  # la base cacheada no se modifica
    cache_consultas.invalidar()


def test_la_lectura_de_beto_no_deja_la_transaccion_abierta(dw, monkeypatch):
    """Tras cargar los datos, el cálculo corre sin transacción abierta (antes bloqueaba TRUNCATE por minutos)."""
    from models.dim_origen import DimOrigenDocumental
    from models.staging_registro import StagingRegistroCrudo
    from routers import dataops

    dw.add(DimOrigenDocumental(id_documento=11, nombre_archivo="ARCA.xlsx", tipo_fuente="ACTA"))
    dw.add(StagingRegistroCrudo(id_documento=11, texto_plano="NOMBRES: Ana | MÓDULO 1: 80"))
    dw.commit()
    docs = dw.query(DimOrigenDocumental).all()
    en_transaccion = []
    original = dataops.extract_entities_from_line

    def _espiar(*a, **kw):
        en_transaccion.append(dw.in_transaction())
        return original(*a, **kw)
    monkeypatch.setattr(dataops, "extract_entities_from_line", _espiar)
    dataops._evaluar_documentos_lote(dw, docs, persistir_staging=False)
    assert en_transaccion and not any(en_transaccion)
