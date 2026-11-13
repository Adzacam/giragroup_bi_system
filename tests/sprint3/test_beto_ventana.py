"""BETO_VENTANA: ventana deslizante (max_length 128, solape configurable, fusión por máxima probabilidad). No cambia a 512 tokens."""
import io
import json

import pytest

from pipeline import config as cfg
from pipeline.semantic.ventana import fusionar_entidades, tramos_de_tokens
from services import beto_integracion as bi


def test_un_texto_que_cabe_en_una_ventana_da_un_solo_tramo():
    assert tramos_de_tokens(0, 126, 32) == [(0, 0)] and tramos_de_tokens(126, 126, 32) == [(0, 126)]


def test_los_tramos_cubren_todo_el_texto_y_se_solapan_el_stride():
    tramos = tramos_de_tokens(300, 126, 32)
    assert tramos[0][0] == 0 and tramos[-1][1] == 300
    assert all(b0 - a0 == 126 - 32 for (a0, _), (b0, _) in zip(tramos[:-1], tramos[1:]))
    assert all(a1 - b0 == 32 for (_, a1), (b0, _) in zip(tramos[:-2], tramos[1:-1]))
    assert all(i1 - i0 <= 126 for i0, i1 in tramos)
    assert tramos_de_tokens(300, 126, 0)[1][0] == 126        # sin solape
    assert tramos_de_tokens(300, 10, 50)[-1][1] == 300       # stride mayor que la ventana: avanza de a 1 y termina igual
    with pytest.raises(ValueError):
        tramos_de_tokens(10, 0, 0)


def test_configuracion_no_cambia_a_512():
    assert cfg.BETO_MAX_LENGTH_TOKENS == 128 and cfg.BETO_VENTANA_STRIDE == 32 and cfg.BETO_FLAGS_POR_DEFECTO["BETO_VENTANA"] is False
    from pipeline.semantic.indice_confianza import MAX_LENGTH_TOKENS
    assert MAX_LENGTH_TOKENS == cfg.BETO_MAX_LENGTH_TOKENS


def p(grupo, ini, fin, score, borde=False):
    return {"entity_group": grupo, "start": ini, "end": fin, "score": score, "borde": borde}


def test_fusion_por_maxima_probabilidad_entre_ventanas_que_se_solapan():
    fusion = fusionar_entidades([p("PER_ESTUDIANTE", 10, 30, 0.91), p("PER_ESTUDIANTE", 10, 30, 0.97), p("PER_ESTUDIANTE", 12, 28, 0.95)])
    assert [(x["start"], x["end"], x["score"]) for x in fusion] == [(10, 30, 0.97)]


def test_una_entidad_cortada_por_el_borde_cede_ante_la_completa_de_la_ventana_vecina():
    fusion = fusionar_entidades([p("PER_ESTUDIANTE", 100, 112, 0.99, borde=True), p("PER_ESTUDIANTE", 100, 125, 0.93)])
    assert [(x["start"], x["end"]) for x in fusion] == [(100, 125)]
    sola = fusionar_entidades([p("PER_ESTUDIANTE", 100, 112, 0.99, borde=True)])
    assert len(sola) == 1                                     # si nadie la cubre, se conserva


def test_grupos_distintos_se_conservan_y_la_salida_es_estable():
    ps = [p("MODULO", 5, 20, 0.8), p("PER_ESTUDIANTE", 10, 30, 0.9), p("PER_ESTUDIANTE", 40, 50, 0.7)]
    assert fusionar_entidades(ps) == fusionar_entidades(list(reversed(ps)))
    assert len(fusionar_entidades(ps)) == 3


class _Tokenizador:
    def __call__(self, texto, add_special_tokens=False, return_offsets_mapping=True):
        offs, i = [], 0
        for palabra in texto.split(" "):
            offs.append((i, i + len(palabra)))
            i += len(palabra) + 1
        return {"offset_mapping": offs}


class _Pipeline:
    """Pipeline NER simulado: ve solo las primeras 126 palabras de cada texto (como el recorte de 128 tokens) y marca el nombre buscado."""
    tokenizer = _Tokenizador()

    def __init__(self, nombre):
        self.nombre, self.vistos = nombre, []

    def __call__(self, textos, batch_size=16):
        salida = []
        for t in textos:
            self.vistos.append(len(t.split(" ")))
            visible = " ".join(t.split(" ")[:126])
            i = visible.find(self.nombre)
            salida.append([{"entity_group": "PER_ESTUDIANTE", "start": i, "end": i + len(self.nombre), "score": 0.95}] if i >= 0 else [])
        return salida


def _motor(nombre):
    from pipeline.semantic.ner_engine import BetoNEREngine
    motor = BetoNEREngine(auto_load=False)
    motor._nlp_pipeline = _Pipeline(nombre)
    return motor


def test_el_motor_lee_la_parte_que_el_recorte_de_128_tokens_no_veia():
    nombre = "Maria Lopez Quispe"
    texto = " ".join(["relleno"] * 200 + [nombre])
    motor = _motor(nombre)
    assert motor._nlp_pipeline([texto])[0] == []              # sin ventana BETO no llega al nombre
    con = motor._predicciones_con_ventana([texto], 128, 32)[0]
    assert len(con) == 1 and texto[con[0]["start"]:con[0]["end"]] == nombre and con[0]["score"] == 0.95


def test_el_motor_encuentra_el_nombre_que_cae_en_la_union_de_dos_ventanas():
    nombre = "Maria Lopez Quispe"
    texto = " ".join(["relleno"] * 124 + [nombre] + ["relleno"] * 80)    # el nombre cruza el corte de la primera ventana
    con = _motor(nombre)._predicciones_con_ventana([texto], 128, 32)[0]
    assert [texto[x["start"]:x["end"]] for x in con] == [nombre]


def test_un_texto_corto_se_lee_entero_y_con_una_sola_llamada_por_texto():
    motor = _motor("Ana Rojas")
    texto = "Ana Rojas | MODULO: Gestion"
    out = motor._predicciones_con_ventana([texto, texto + "!"], 128, 32)
    assert len(motor._nlp_pipeline.vistos) == 2 and all(len(o) == 1 for o in out)


def test_infer_batch_expone_entidades_beto_y_acepta_la_ventana(monkeypatch):
    from fastapi.testclient import TestClient
    from pipeline.semantic import inference_server as srv
    from pipeline.semantic.ner_schema import EntidadExtraida, ResultadoInferenciaNER, TipoEntidad
    recibido = {}

    class Motor:
        _nlp_pipeline = object()

        def extraer_lote(self, textos, ventana=False, stride=32, max_length=128, **_):
            recibido.update(ventana=ventana, stride=stride, max_length=max_length)
            e = EntidadExtraida(tipo=TipoEntidad.ESTUDIANTE, valor="Ana Rojas", start_char=0, end_char=9, score=0.96, origen="BETO_NER")
            return [ResultadoInferenciaNER(texto=t, entidades=[e], entidades_beto=[e]) for t in textos]

    monkeypatch.setattr(srv, "get_engine_and_tokenizer", lambda: (Motor(), None))
    cli = TestClient(srv.app)
    r = cli.post("/infer-batch", json={"textos": ["Ana Rojas"], "ventana": True, "stride": 16, "max_length": 128}).json()
    assert recibido == {"ventana": True, "stride": 16, "max_length": 128}
    assert r["resultados"][0]["entidades_beto"] == [{"type": "ESTUDIANTE", "text": "Ana Rojas", "start": 0, "end": 9, "score": 0.96}]
    cli.post("/infer-batch", json={"textos": ["x"]})
    assert recibido == {"ventana": False, "stride": 32, "max_length": 128}      # sin los campos nuevos: comportamiento de siempre


class _Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_el_cliente_pide_la_ventana_solo_con_el_flag_y_cambia_la_clave_de_cache(monkeypatch):
    cuerpos = []
    cuerpo = {"status": "success", "resultados": [{"entidades_beto": [{"type": "ESTUDIANTE", "text": "Ana Rojas", "start": 0, "end": 9, "score": 0.9}]}]}

    def urlopen(req, timeout=0):
        cuerpos.append(json.loads(req.data.decode()))
        return _Respuesta(json.dumps(cuerpo).encode())

    monkeypatch.setattr(bi.urllib.request, "urlopen", urlopen)
    for f in ("BETO_VENTANA", "BETO_VENTANA_STRIDE"):
        monkeypatch.delenv(f, raising=False)
    sin = bi.configuracion_modelo()
    assert bi._post_infer_batch(["Ana Rojas"])[0][0].texto == "Ana Rojas" and cuerpos[-1] == {"textos": ["Ana Rojas"]}
    monkeypatch.setenv("BETO_VENTANA", "1")
    monkeypatch.setenv("BETO_VENTANA_STRIDE", "48")
    bi._post_infer_batch(["Ana Rojas"])
    assert cuerpos[-1] == {"textos": ["Ana Rojas"], "ventana": True, "stride": 48, "max_length": 128}
    assert bi.configuracion_modelo() != sin and "ventana128+48" in bi.configuracion_modelo()
    larga = " | ".join(f"c{i}: {i}" for i in range(12))
    assert bi.texto_para_beto(larga) == larga                   # con la ventana se manda la línea completa
    monkeypatch.delenv("BETO_VENTANA")
    assert bi.texto_para_beto(larga).count("|") == 7             # sin ella, las primeras 8 celdas como el índice
