"""Tests F12: bandas de discordancia, etiquetas sin hash, prioridad, patron y guardrail HTTP 422."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from models.dim_origen import DimOrigenDocumental
from models.lote import Lote
from models.staging_entidad import StagingEntidadNoResuelta
from routers.dataops._comun import BatchResolveRequest
from routers.dataops.revision import batch_resolve_review_items, _validar_guardrail_discordancia
from services.bandeja_grupos import banda_discordancia, clave_grupo, grupos_pendientes
from services.revision_consulta import consultar, grupos_publicos


@pytest.fixture()
def db_mem():
    engine = create_engine("sqlite:///:memory:", execution_options={"schema_translate_map": {"public": None, "bi": None}})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


def _seed(db):
    lote = Lote(id_lote=1, institucion="GiraGroup", periodo="2026", estado="PENDIENTE_REVISION")
    db.add(lote)
    db.flush()
    doc = DimOrigenDocumental(id_documento=10, id_lote=1, nombre_archivo="ARCA.xlsx", tipo_fuente="ACTA")
    db.add(doc)
    db.flush()
    filas = [
        StagingEntidadNoResuelta(
            id_staging=1, id_documento=10, tipo_entidad="ESTUDIANTE",
            texto_original="CI: 1001 | Nombre: Ana Perez", score_fuzzy=20.0,
            nivel_confianza=0.50, motivo="CI_NOMBRE_DISCORDANTE", resuelto=False,
            payload_json={"prioridad": "ALTA"},
        ),
        StagingEntidadNoResuelta(
            id_staging=2, id_documento=10, tipo_entidad="ESTUDIANTE",
            texto_original="CI: 1002 | Nombre: Luis Gomez", score_fuzzy=45.0,
            nivel_confianza=0.70, motivo="CI_NOMBRE_DISCORDANTE", resuelto=False,
            payload_json={"prioridad": "MEDIA"},
        ),
        StagingEntidadNoResuelta(
            id_staging=3, id_documento=10, tipo_entidad="ESTUDIANTE",
            texto_original="CI: 1003 | Nombre: Maria Quispe", score_fuzzy=75.0,
            nivel_confianza=0.80, motivo="CI_NOMBRE_DISCORDANTE", resuelto=False,
            payload_json={"prioridad": "BAJA"},
        ),
        StagingEntidadNoResuelta(
            id_staging=4, id_documento=10, tipo_entidad="ESTUDIANTE",
            texto_original="Nombre: Carlos Rojas", score_fuzzy=60.0,
            nivel_confianza=0.55, motivo="BAJA_CONFIANZA_IA", resuelto=False,
            payload_json={"prioridad": "ALTA"},
        ),
    ]
    db.add_all(filas)
    db.commit()
    return doc


def test_bandas_discordancia_colapsan_por_banda_y_etiqueta_sin_hash(db_mem):
    doc = _seed(db_mem)
    assert banda_discordancia(20.0)[0] == "muy_distinto"
    assert banda_discordancia(45.0)[0] == "parcial"
    assert banda_discordancia(75.0)[0] == "casi_igual"
    assert clave_grupo("CI_NOMBRE_DISCORDANTE", "CI: 1001", score_fuzzy=20.0, id_documento=10) == "CI_NOMBRE_DISCORDANTE::doc10::muy_distinto"

    res = grupos_pendientes(db_mem, [doc.id_documento])
    assert res["total_casos"] == 4
    assert res["total_grupos"] == 4
    assert len(res["patrones"]) == 3
    assert {r["motivo"] for r in res["reglas_resumen"]} == {"CI_NOMBRE_DISCORDANTE", "BAJA_CONFIANZA_IA"}

    pub = grupos_publicos(db_mem, [doc])
    for g in pub["grupos"]:
        assert "#" not in g["etiqueta_legible"]
        assert "#" not in g["titulo"]


def test_consultar_filtra_patron_y_ordena_por_prioridad(db_mem):
    doc = _seed(db_mem)
    todos = consultar(db_mem, [doc], page=1, page_size=20)
    assert [it["prioridad"] for it in todos["items"]] == ["ALTA", "ALTA", "MEDIA", "BAJA"]

    solo_parcial = consultar(db_mem, [doc], page=1, page_size=20, patron="parcial")
    assert solo_parcial["total"] == 1
    assert solo_parcial["items"][0]["id"] == 2

    solo_alta = consultar(db_mem, [doc], page=1, page_size=20, prioridad="ALTA")
    assert solo_alta["total"] == 2
    assert all(it["prioridad"] == "ALTA" for it in solo_alta["items"])


def test_guardrail_422_para_discordante_menor_30_y_descarte_con_justificacion(db_mem, monkeypatch):
    from services.dw_loader import DWLoaderService
    monkeypatch.setattr(DWLoaderService, "cargar_registro", lambda self, reg: {"status": "loaded", "id_estudiante": 1})
    _seed(db_mem)
    with pytest.raises(HTTPException) as exc:
        _validar_guardrail_discordancia(db_mem, ["1"])
    assert exc.value.status_code == 422

    admin = SimpleNamespace(id=1, username="admin_general", role="ADMIN")
    with pytest.raises(HTTPException) as exc2:
        batch_resolve_review_items(
            BatchResolveRequest(item_ids=["1", "2"], accion="APROBAR", justificacion="prueba"),
            db=db_mem, current_user=admin,
        )
    assert exc2.value.status_code == 422

    # Caso 2 (CI_NOMBRE_DISCORDANTE score=45) sí permite aprobar en lote sin error de item_ids/justificacion
    res_ok = batch_resolve_review_items(
        BatchResolveRequest(item_ids=["2"], accion="APROBAR", justificacion="Confirmado F12"),
        db=db_mem, current_user=admin,
    )
    assert res_ok["status"] == "success"
    assert res_ok["accion"] == "APROBAR"
    assert res_ok["resolved_count"] == 1

    # Caso 4 (BAJA_CONFIANZA_IA) sí permite descartar en lote con justificación
    res = batch_resolve_review_items(
        BatchResolveRequest(item_ids=["4"], accion="DESCARTAR", justificacion="Fila duplicada F12"),
        db=db_mem, current_user=admin,
    )
    assert res["status"] == "success"
    assert res["accion"] == "DESCARTAR"
    assert res["resolved_count"] == 1
