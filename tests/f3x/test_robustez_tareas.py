"""X-5: Pruebas de robustez de tareas (vigilante con latido, reconstrucción de resumen tras reinicio y liberación de memoria)."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from core.database import Base, get_db  # noqa: E402
from core.security import get_current_user  # noqa: E402
import models  # noqa: F401, E402
from models.dim_origen import DimOrigenDocumental  # noqa: E402
from models.lote import Lote  # noqa: E402
from models.staging_registro import StagingRegistroCrudo  # noqa: E402
from routers.dataops import router as dataops_router  # noqa: E402
from services import cache_consultas, cache_lectura, tareas_dataops  # noqa: E402
from services.dw_loader import DWLoaderService  # noqa: E402


def _fake_row(mapping: dict):
    return SimpleNamespace(_mapping=dict(mapping))


def test_vigilante_respeta_latido_reciente():
    row_viva = _fake_row({
        "id": 10,
        "tipo": "CONSOLIDACION",
        "id_lote": 4,
        "estado": "EN_CURSO",
        "total": 1000,
        "procesados": 500,
        "resultado": None,
        "error": None,
        "iniciado_por": "admin",
        "transcurrido": 600.0,  # > 180s desde inicio, pero con latido reciente
        "sin_latido": 5.0,
    })
    with patch.object(tareas_dataops, "fallar") as mock_fallar:
        res = tareas_dataops._serializar(row_viva)
    assert res["estado"] == "EN_CURSO"
    mock_fallar.assert_not_called()


def test_vigilante_marca_error_sin_latido_y_tolera_none():
    row_muerta = _fake_row({
        "id": 11,
        "tipo": "CONSOLIDACION",
        "id_lote": 4,
        "estado": "EN_CURSO",
        "total": 1000,
        "procesados": 500,
        "resultado": None,
        "error": None,
        "iniciado_por": "admin",
        "transcurrido": 600.0,
        "sin_latido": 185.0,
    })
    with patch.object(tareas_dataops, "fallar") as mock_fallar:
        res = tareas_dataops._serializar(row_muerta)
    assert res["estado"] == "ERROR"
    mock_fallar.assert_called_once()

    row_none = _fake_row({
        "id": 12,
        "tipo": "CONSOLIDACION",
        "id_lote": 4,
        "estado": "EN_CURSO",
        "total": 100,
        "procesados": 10,
        "resultado": None,
        "error": None,
        "iniciado_por": "admin",
        "transcurrido": 20.0,
        "sin_latido": None,
    })
    with patch.object(tareas_dataops, "fallar") as mock_fallar2:
        res2 = tareas_dataops._serializar(row_none)
    assert res2["estado"] == "EN_CURSO"
    mock_fallar2.assert_not_called()


def test_resumen_se_reconstruye_desde_bd_tras_reinicio():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": {"public": None}},
    )

    @event.listens_for(engine, "connect")
    def _attach_public(dbapi_conn, _conn_record):
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS public")

    for tbl in Base.metadata.tables.values():
        tbl.schema = None
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    lote = Lote(id_lote=7, institucion="GiraGroup Posgrado", periodo="2026-1", estado="PROCESADO", total_archivos=1)
    doc = DimOrigenDocumental(
        id_documento=70, id_lote=7, nombre_archivo="acta.xlsx", tipo_fuente="ACTA",
        tipo_escala="CENTESIMAL_100", hash_sha256="a" * 64, institucion="GiraGroup Posgrado", periodo="2026-1",
    )
    stg = StagingRegistroCrudo(
        id=700, id_documento=70, texto_plano="ESTUDIANTE: Ana | NOTA: 90",
        score_confianza=0.95, requiere_revision=False, es_ruido=False, n_filas=1,
        estado_resolucion="APROBADO_AUTOMATICO",
        payload_json={
            "tipo_fuente": "ACTA",
            "tipo_escala": "CENTESIMAL_100",
            "tuplas": [
                {
                    "id": "stg-700-1",
                    "line_number": 1,
                    "raw_line": "ESTUDIANTE: Ana | NOTA: 90",
                    "ci_enmascarado": None,
                    "estudiante": "Ana",
                    "modulo": "Finanzas",
                    "nota_original": "90",
                    "nota_normalizada": "90.00/100",
                    "indice_registro": 95,
                    "motivo": "APROBADO_AUTOMATICO",
                    "motivo_llano": "Aprobado",
                    "estado_resolucion": "APROBADO_AUTOMATICO",
                },
                {
                    "id": "stg-700-2",
                    "line_number": 2,
                    "raw_line": "ESTUDIANTE: Luis | NOTA: 80",
                    "ci_enmascarado": None,
                    "estudiante": "Luis",
                    "modulo": "Finanzas",
                    "nota_original": "80",
                    "nota_normalizada": "80.00/100",
                    "indice_registro": 72,
                    "motivo": "BAJA_CONFIANZA",
                    "motivo_llano": "Revisar",
                    "estado_resolucion": "PENDIENTE",
                },
            ],
        },
    )
    db.add_all([lote, doc, stg])
    db.commit()

    cache_consultas.invalidar()
    app = FastAPI()
    app.include_router(dataops_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, username="admin", role="ADMIN")
    client = TestClient(app)

    with patch.object(cache_lectura, "leer", return_value=None), \
         patch.object(cache_lectura, "guardar", return_value=True), \
         patch.object(tareas_dataops, "ultima", return_value={"estado": "COMPLETADA"}):
        r = client.get("/api/v1/dataops/lote/7/resumen")

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["empty"] is False
    assert body["totalTuplas"] == 2
    assert body["autoCount"] == 1
    assert body["auditCount"] == 1
    assert round(body["autoPct"] + body["auditPct"] + body["inconsistenciasPct"], 1) == 100.0
    db.close()


def test_dw_loader_liberar_memoria():
    loader = DWLoaderService(db=None)
    loader._cfo_existentes = {"a", "b"}
    loader._eval_pendientes = {"k": {"x": 1}}
    loader._cache_estudiante = {("1", "a"): (1, "A")}
    loader._est_nombres = [(1, "Ana")]
    loader.liberar_memoria()
    assert loader._cfo_existentes is None
    assert loader._est_nombres is None
    assert loader._eval_pendientes == {}
    assert loader._cache_estudiante == {}
