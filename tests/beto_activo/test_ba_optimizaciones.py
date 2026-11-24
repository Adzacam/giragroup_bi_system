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
            "configuracion_beto": cliente.configuracion,
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
    monkeypatch.setenv("BETO_RESCATE_ACADEMICO", "0")
    monkeypatch.delenv("BETO_ACUERDO_OMITIR_CI_EXACTA", raising=False)
    monkeypatch.setenv("BETO_ACUERDO_SOLO_FUZZY", "0")

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


def test_acuerdo_qc_primera_insercion_sin_padron(monkeypatch):
    monkeypatch.setenv("BETO_CASCADA_FINAL", "0")
    monkeypatch.setenv("BETO_ACUERDO_QC", "1")
    monkeypatch.setenv("BETO_RESCATE_ACADEMICO", "0")
    monkeypatch.setenv("BETO_ACUERDO_SOLO_FUZZY", "0")

    def post_falso(lote):
        return [[bi.EntidadBeto("ESTUDIANTE", "Ana Maria Perez", 17, 32, 0.96)] for _ in lote]

    def extraer_sin_padron(linea, **_kw):
        return (
            [{
                "label": "ESTUDIANTE",
                "token": "Ana Maria Perez",
                "matchedCanonical": None,
                "fuente_resolucion": "ENCABEZADO",
                "es_nuevo_perfil": True,
            }],
            0.92,
            False,
        )

    cont_sin = bi.Contadores()
    res_sin = bi.refinar_lineas(
        ["Nombre Completo: Ana Maria Perez"],
        extraer_sin_padron,
        tipo_fuente="ACTA",
        cliente=bi.ClienteBeto(cache=bi.CacheMemoria(), post=post_falso, contadores=cont_sin),
        contadores=cont_sin,
        sin_padron=True,
    )
    assert cont_sin.comparadas_acuerdo == 1
    assert cont_sin.acuerdos == 1
    assert res_sin[0].ents[0]["acuerdo_beto"] == "ACUERDO"


def test_preview_no_asigna_preguntas_de_encuesta_a_campos_canonicos():
    from routers.dataops.ingesta import _inferir_campo_canonico

    assert _inferir_campo_canonico("Nombre Completo") == "nombre_completo"
    assert _inferir_campo_canonico("Programa") == "programa"
    assert _inferir_campo_canonico("Módulo") == "modulo"
    assert _inferir_campo_canonico("1. ¿La/El docente explica los conceptos de manera clara y comprensible?") == ""
    assert _inferir_campo_canonico("2. ¿La/El docente mostró dominio sobre los temas del curso?") == ""
    assert _inferir_campo_canonico("3. ¿La/El docente fomenta la participación de las/los estudiantes en las clases?") == ""
    assert _inferir_campo_canonico("5. ¿La/El docente cumple con el contenido y los horarios establecidos para el módulo?") == ""


def test_evaluacion_docente_anonima_no_cae_a_sin_lectura():
    from routers.dataops.extraccion import extract_entities_from_line

    linea = (
        "Nombre Completo: ENTRADA ANONIMA - PERSONA 1 | Programa: POS-5310 | Módulo: 1 | "
        "1. ¿La/El docente explica los conceptos de manera clara y comprensible?: 4/De acuerdo"
    )
    ents, score, req_rev = extract_entities_from_line(
        linea,
        estudiantes=[],
        docentes=[],
        modulos=[],
        tipo_fuente="EVALUACION_DOCENTE",
    )
    est = next(e for e in ents if e["label"] == "ESTUDIANTE")
    assert est["es_anonima"] is True
    assert est["canonicalId"] == "EVALUACION_ANONIMA"
    assert est["es_nuevo_perfil"] is False
    assert score >= 0.85
    assert req_rev is False


def test_evaluacion_docente_likert_estructurada_no_cae_a_baja_confianza_ia():
    from services import encuesta_canonica
    from services.extraccion_por_encabezado import campos_por_encabezado, fila_resuelta_por_regla

    fila = (
        "Nombre Completo: Juan Perez | Programa: POS-5252 | Módulo: 1 | "
        "1. ¿La/El docente explica los conceptos de manera clara y comprensible?: 5/Totalmente de acuerdo"
    )
    campos = campos_por_encabezado([c.strip() for c in fila.split("|")])
    perfil = encuesta_canonica.perfilar([campos])
    assert fila_resuelta_por_regla(campos, "evaluacion_docente", perfil_encuesta=perfil) is True


from tests.sprint5.test_beto_integracion_flujo import _servicio, entorno  # noqa: F401


def test_ci_exacta_no_es_sobrescrita_por_indice_beto_bajo(entorno, monkeypatch, tmp_path):
    import io
    import pandas as pd
    from models.dim_estudiante import DimEstudiante
    from models.dim_modulo import DimModulo
    from models.fact_rendimiento import FactRendimientoAcademico
    from models.lote import Lote
    from models.staging_entidad import StagingEntidadNoResuelta
    from routers.dataops import consolidacion
    from services import ingestion_service

    monkeypatch.setenv("BETO_CASCADA_FINAL", "0")
    monkeypatch.setenv("BETO_ACUERDO_QC", "0")
    monkeypatch.setenv("BETO_SUGERENCIA_HITL", "0")
    _servicio(monkeypatch, [])
    lote = Lote(institucion="Prueba", periodo="2024")
    entorno.add(lote)
    entorno.flush()
    entorno.add(DimEstudiante(nombre_completo="JHOSELIN DANITZA ROMERO", ci="8645347", ci_numero="8645347", fk_estado="A"))
    entorno.add(DimModulo(nombre_modulo="POS-5381 · Módulo 1", pos_code="POS-5381-M01", programa="DIPLOMADO"))
    entorno.commit()
    buf = io.BytesIO()
    pd.DataFrame([{
        "POS - ACTAS": 5381,
        "CÉDULA DE IDENTIDAD": "8645347",
        "MES INICO": 12,
        "AÑO INCIO": 2024,
        "NOMBRE COMPLETO": "JHOSELIN DANITZA ROMERO",
        "MÓDULO 1": 91,
    }]).to_excel(buf, index=False)
    p = tmp_path / "arca.xlsx"
    p.write_bytes(buf.getvalue())
    ingestion_service.IngestionService.procesar_archivo(
        entorno, str(p), p.name, id_lote=lote.id_lote, tipo_fuente="ACTA", institucion="Prueba", tipo_escala="CENTESIMAL_100"
    )
    monkeypatch.setattr(consolidacion, "obtener_indices", lambda textos, **kw: [0.49] * len(textos))
    res = consolidacion._consolidar(consolidacion.ConfirmDwInsertRequest(id_lote=lote.id_lote), entorno, None)
    assert res["desglose"]["inserted_academico"] >= 1
    assert entorno.query(FactRendimientoAcademico).count() >= 1
    assert entorno.query(StagingEntidadNoResuelta).filter_by(motivo="BAJA_CONFIANZA_IA").count() == 0
