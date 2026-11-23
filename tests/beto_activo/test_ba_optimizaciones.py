"""Tests unitarios para las optimizaciones de rendimiento de BETO (RNF-03)."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from services import beto_integracion as bi
from pipeline import config as cfg


def test_precargar_desde_staging_evita_reinferencia():
    llamadas = []

    def post_falso(lote):
        llamadas.append(list(lote))
        return [[] for _ in lote]

    cliente = bi.ClienteBeto(cache=bi.CacheMemoria(), post=post_falso)
    linea_1 = "ESTUDIANTE: Maria Lopez Quispe | MODULO: Gestion | NOTA: 85"
    linea_2 = "ESTUDIANTE: Juan Perez | MODULO: Finanzas | NOTA: 78"
    stg = SimpleNamespace(
        payload_json={
            "tuplas": [
                {
                    "raw_line": linea_1,
                    "beto_ents": [{"tipo": "ESTUDIANTE", "texto": "Maria Lopez Quispe", "start": 12, "end": 30, "score": 0.96}],
                },
                {
                    "raw_line": linea_2,
                    "beto_ents": [],
                },
            ]
        }
    )

    n = bi.precargar_desde_staging(cliente, [stg])
    assert n == 2

    res = cliente.entidades([bi.texto_para_beto(linea_1), bi.texto_para_beto(linea_2)])
    assert llamadas == []
    assert len(res[bi.texto_para_beto(linea_1)]) == 1
    assert res[bi.texto_para_beto(linea_2)] == []
    assert cliente.contadores.textos_en_cache == 2
    assert cliente.contadores.textos_inferidos == 0


def test_cache_entidades_usa_catalog_db_y_bulk_insert():
    from sqlalchemy import event
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _attach_public(dbapi_conn, _conn_record):
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS public")

    Session = sessionmaker(bind=engine)
    bi.CacheEntidades._tabla_lista = False
    cache = bi.CacheEntidades(session_factory=Session)

    nuevos = {
        bi.hash_texto("texto a"): [bi.EntidadBeto("ESTUDIANTE", "Ana", 0, 3, 0.95)],
        bi.hash_texto("texto b"): [],
    }
    cache.guardar(nuevos, "cfg-test")
    leidos = cache.leer(list(nuevos.keys()), "cfg-test")
    assert len(leidos) == 2
    assert leidos[bi.hash_texto("texto a")][0].texto == "Ana"
    assert leidos[bi.hash_texto("texto b")] == []

    with engine.connect() as conn:
        cnt = conn.execute(text("SELECT count(*) FROM cache_beto_entidades")).scalar()
        assert cnt == 2


def test_cliente_beto_ordena_faltan_por_longitud(monkeypatch):
    monkeypatch.setattr(cfg, "BETO_LOTE_TEXTOS", 2)
    lotes_recibidos = []

    def post_falso(lote):
        lotes_recibidos.append(list(lote))
        return [[] for _ in lote]

    cliente = bi.ClienteBeto(cache=bi.CacheMemoria(), post=post_falso)
    textos = [
        "texto sumamente largo con muchas palabras para probar el ordenamiento",
        "corto",
        "mediano de prueba",
        "ok",
    ]
    res = cliente.entidades(textos)
    assert len(res) == 4
    assert lotes_recibidos == [
        ["ok", "corto"],
        ["mediano de prueba", "texto sumamente largo con muchas palabras para probar el ordenamiento"],
    ]


def test_acuerdo_qc_omite_ci_exacta_por_defecto_y_es_configurable(monkeypatch):
    monkeypatch.setenv("BETO_CASCADA_FINAL", "0")
    monkeypatch.setenv("BETO_ACUERDO_QC", "1")
    monkeypatch.delenv("BETO_ACUERDO_OMITIR_CI_EXACTA", raising=False)

    llamadas = []

    def post_falso(lote):
        llamadas.append(list(lote))
        return [[] for _ in lote]

    def extraer_ci(linea, **_kw):
        return (
            [{"label": "ESTUDIANTE", "token": "Maria Lopez", "matchedCanonical": "Maria Lopez", "fuente_resolucion": "CI_EXACTA"}],
            0.98,
            False,
        )

    cont_1 = bi.Contadores()
    bi.refinar_lineas(
        ["CI: 1234567 | ESTUDIANTE: Maria Lopez"],
        extraer_ci,
        tipo_fuente="ACTA",
        cliente=bi.ClienteBeto(cache=bi.CacheMemoria(), post=post_falso, contadores=cont_1),
        contadores=cont_1,
    )
    assert llamadas == []
    assert cont_1.comparadas_acuerdo == 0

    monkeypatch.setenv("BETO_ACUERDO_OMITIR_CI_EXACTA", "0")
    cont_2 = bi.Contadores()
    bi.refinar_lineas(
        ["CI: 1234567 | ESTUDIANTE: Maria Lopez"],
        extraer_ci,
        tipo_fuente="ACTA",
        cliente=bi.ClienteBeto(cache=bi.CacheMemoria(), post=post_falso, contadores=cont_2),
        contadores=cont_2,
    )
    assert len(llamadas) == 1
    assert cont_2.comparadas_acuerdo == 1


def test_ner_engine_extraer_lote_ordena_por_longitud_y_conserva_orden():
    from pipeline.semantic.ner_engine import BetoNEREngine

    eng = BetoNEREngine(auto_load=False)
    orden_visto = []

    def fake_pipeline(chunk, batch_size=None):
        orden_visto.append(list(chunk))
        return [[] for _ in chunk]

    eng._nlp_pipeline = fake_pipeline
    textos = [
        "ESTUDIANTE: Maria Lopez Quispe | MODULO: Gestion de Datos",
        "CI: 123",
        "ESTUDIANTE: Ana",
        "CI: 123",
    ]
    res = eng.extraer_lote(textos, batch_size=10)
    assert len(res) == 4
    assert orden_visto == [[
        "CI: 123",
        "ESTUDIANTE: Ana",
        "ESTUDIANTE: Maria Lopez Quispe | MODULO: Gestion de Datos",
    ]]
    assert [r.texto for r in res] == textos
