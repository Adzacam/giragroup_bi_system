"""X-5: Pruebas de robustez de tareas (vigilante respeta latido y resumen BETO reconstruido tras reinicio)."""
import os
import sys
from types import SimpleNamespace

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from core.database import Base  # noqa: E402
import models  # noqa: F401, E402
from models.dim_origen import DimOrigenDocumental  # noqa: E402
from models.lote import Lote  # noqa: E402
from models.staging_registro import StagingRegistroCrudo  # noqa: E402
from routers.dataops import get_lote_resumen  # noqa: E402
from services import cache_consultas, cache_lectura, tareas_dataops  # noqa: E402


class _Row:
    def __init__(self, mapping):
        self._mapping = mapping


def test_vigilante_respeta_latido_reciente(monkeypatch):
    llamadas_fallar = []
    monkeypatch.setattr(tareas_dataops, "fallar", lambda tid, err: llamadas_fallar.append((tid, err)))

    vivo = _Row({
        "id": 101,
        "tipo": "CONSOLIDACION",
        "id_lote": 4,
        "estado": "EN_CURSO",
        "total": 100,
        "procesados": 50,
        "resultado": {},
        "error": None,
        "iniciado_por": "admin",
        "transcurrido": 240.0,
        "sin_latido": 15.0,  # latido reciente (< 180 s) aunque lleve 240 s corriendo
    })
    res = tareas_dataops._serializar(vivo)
    assert res["estado"] == "EN_CURSO"
    assert llamadas_fallar == []


def test_vigilante_marca_error_cuando_expira_latido(monkeypatch):
    llamadas_fallar = []
    monkeypatch.setattr(tareas_dataops, "fallar", lambda tid, err: llamadas_fallar.append((tid, err)))

    muerto = _Row({
        "id": 102,
        "tipo": "CONSOLIDACION",
        "id_lote": 4,
        "estado": "EN_CURSO",
        "total": 100,
        "procesados": 50,
        "resultado": {},
        "error": None,
        "iniciado_por": "admin",
        "transcurrido": 250.0,
        "sin_latido": tareas_dataops.SIN_LATIDO_SEG + 5,
    })
    res = tareas_dataops._serializar(muerto)
    assert res["estado"] == "ERROR"
    assert len(llamadas_fallar) == 1 and llamadas_fallar[0][0] == 102


def test_vigilante_tolera_sin_latido_none(monkeypatch):
    llamadas_fallar = []
    monkeypatch.setattr(tareas_dataops, "fallar", lambda tid, err: llamadas_fallar.append((tid, err)))

    sin_dato = _Row({
        "id": 103,
        "tipo": "CONSOLIDACION",
        "id_lote": 4,
        "estado": "EN_CURSO",
        "total": 100,
        "procesados": 0,
        "resultado": {},
        "error": None,
        "iniciado_por": "admin",
        "transcurrido": 5.0,
        "sin_latido": None,
    })
    res = tareas_dataops._serializar(sin_dato)
    assert res["estado"] == "EN_CURSO"
    assert llamadas_fallar == []


def test_resumen_beto_se_reconstruye_desde_bd_tras_reinicio(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _attach(dbapi_conn, _rec):
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS public")

    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    try:
        lote = Lote(id_lote=77, institucion="GiraGroup", periodo="2026-1", estado="PROCESADO", total_archivos=1)
        doc = DimOrigenDocumental(
            id_documento=77, id_lote=77, nombre_archivo="acta.xlsx", tipo_fuente="ACTA", tipo_escala="CENTESIMAL_100"
        )
        stg = StagingRegistroCrudo(
            id_documento=77,
            texto_plano="ESTUDIANTE: Ana Prueba | CI: 1234567 LP | NOTA: 90",
            es_ruido=False,
            score_confianza=0.95,
            estado_resolucion="APROBADO_AUTOMATICO",
            payload_json={
                "tipo_fuente": "ACTA",
                "tipo_escala": "CENTESIMAL_100",
                "tuplas": [{
                    "id": "stg-77-1",
                    "line_number": 1,
                    "raw_text": "ESTUDIANTE: Ana Prueba | CI: 1234567 LP | NOTA: 90",
                    "estado": "AUTOMATICO",
                    "categoria_particion": "AUTOMATICO",
                    "indice_registro": 95,
                    "estudiante": "Ana Prueba",
                    "ci": "1234567 LP",
                    "modulo": "Modulo 1",
                    "nota_original": "90",
                    "nota_normalizada": 90.0,
                    "total_entidades": 4,
                    "motivo": "APROBADO_AUTOMATICO",
                }],
            },
        )
        db.add_all([lote, doc, stg])
        db.commit()

        # Simular reinicio de la API: caches en memoria y disco vacias
        cache_consultas.invalidar()
        monkeypatch.setattr(cache_lectura, "leer", lambda _k: None)
        monkeypatch.setattr(cache_lectura, "guardar", lambda _k, _v: True)
        monkeypatch.setattr(tareas_dataops, "ultima", lambda _lote, _tipo: {"estado": "COMPLETADA"})

        res = get_lote_resumen("77", doc_id=None, db=db)
        assert res["status"] == "success"
        assert res["empty"] is False
        assert res["totalTuplas"] == 1
        assert res["autoCount"] == 1
    finally:
        db.close()
