"""Sprint 3: corpus, trazabilidad y evaluación BETO sin ejecutar entrenamiento/modelo."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from scripts.preparar_corpus_robusto import (particionar_por_persona, clave_persona,
    calcular_solapamiento, leer_jsonl, ARCHIVOS_CORPUS, BASE_DIR)
from scripts.matriz_confusion_ner import matriz_confusion, generar
from scripts.beto_metricas import metricas_relajadas

pytestmark = pytest.mark.sprint3


def test_particion_personas_normalizadas_y_roles():
    personas = ["Lic. José Pérez", "Jose Perez", "Ana Luna", "Dr. Ana Luna", "Pedro Sur", "Luis Paz"]
    train, dev = particionar_por_persona(personas, .5)
    assert not {clave_persona(x) for x in train} & {clave_persona(x) for x in dev}
    assert (train, dev) == particionar_por_persona(reversed(personas), .5)
    assert len(train) + len(dev) == 4


@pytest.mark.parametrize("fraccion", [0, 1, -0.1, 1.1])
def test_fraccion_invalida(fraccion):
    with pytest.raises(ValueError):
        particionar_por_persona(["Ana"], fraccion)


def test_corpus_dos_procesos_reales(tmp_path):
    metas = []
    for n in (1, 2):
        salida = tmp_path / str(n)
        env = dict(os.environ, PYTHONHASHSEED="0", PYTHONUTF8="1")
        subprocess.run([sys.executable, str(BASE_DIR / "scripts/preparar_corpus_robusto.py"),
                        "--salida", str(salida)], env=env, check=True, capture_output=True, text=True)
        metas.append(json.loads((salida / "corpus_meta.json").read_text(encoding="utf-8")))
    assert metas[0]["sha256"] == metas[1]["sha256"]
    assert metas[0]["tamanos"] == {"train": 1400, "dev": 350, "test": 180}
    assert set(metas[0]["solapamiento"]["personas_solapadas"].values()) == {0}
    for nombre in ARCHIVOS_CORPUS:
        assert (tmp_path / "1" / nombre).read_bytes() == (tmp_path / "2" / nombre).read_bytes()


def test_training_info_sha_formato_sin_entrenar(tmp_path):
    from scripts.entrenar_beto_robusto import construir_training_info
    for nombre in (*ARCHIVOS_CORPUS, "model.safetensors"):
        (tmp_path / nombre).write_bytes(nombre.encode())
    info = construir_training_info(salida=tmp_path, datos_dir=tmp_path, historial=[],
        best_epoch=2, best_dev_f1=.8, duracion=1, device="cpu", tamanos={"train": 3,"dev": 1,"test": 1},
        comando={"argv": ["python", "entrenar_beto_robusto.py"], "PYTHONHASHSEED": "0"})
    assert info["seed"] == 42
    assert set(info["versions"]) >= {"torch", "transformers", "seqeval"}
    assert "sin early stopping" in info["selection"]
    assert len(info["sha256"]) == 4
    for nombre, valor in info["sha256"].items():
        assert valor == hashlib.sha256((tmp_path / nombre).read_bytes()).hexdigest()
    assert json.loads(json.dumps(info))["command"]["PYTHONHASHSEED"] == "0"


def test_salida_modelo_protegida_y_no_vacia(tmp_path):
    from scripts.entrenar_beto_robusto import validar_salida
    with pytest.raises(ValueError):
        validar_salida(BASE_DIR / "pipeline/semantic/beto_local/nuevo")
    (tmp_path / "existente").write_text("no tocar")
    with pytest.raises(ValueError):
        validar_salida(tmp_path)


def test_matriz_desde_ejemplo_real_del_test(tmp_path):
    registro = leer_jsonl(BASE_DIR / "data/test_gold_real.jsonl")[0]
    true = registro["tags"]
    pred = list(true)
    entidad = next(i for i,t in enumerate(true) if t != "O")
    exterior = true.index("O")
    pred[entidad] = "O"  # FN
    pred[exterior] = "B-PROGRAMA"  # FP
    entrada = tmp_path / "predicciones.json"
    entrada.write_text(json.dumps({"dataset": "EJEMPLO; no inferencia", "y_true": [true], "y_pred": [pred]}))
    res = generar(entrada, tmp_path / "matriz.json")
    assert res["n_tokens"] == len(true)
    assert res["por_clase"]["O"]["fp"] == 1
    assert res["por_clase"]["O"]["fn"] == 1
    assert sum(map(sum, res["matriz"])) == len(true)
    assert json.loads((tmp_path / "matriz.json").read_text())["matriz"] == res["matriz"]


@pytest.mark.parametrize("true,pred", [([["O"]], []), ([["O"]], [["O", "O"]])])
def test_matriz_rechaza_desalineacion(true,pred):
    with pytest.raises(ValueError):
        matriz_confusion(true,pred)


def test_relajado_matching_uno_a_uno():
    res = metricas_relajadas([["B-MODULO", "O", "B-MODULO"]], [["B-MODULO", "I-MODULO", "I-MODULO"]])
    assert res["tp"] == 1
    assert res["precision"] == 1
    assert res["recall"] == .5


def test_inferencia_alineacion_y_truncado_sin_modelo():
    from scripts.evaluar_beto_checkpoint import predecir
    class Enc(dict):
        def word_ids(self): return [None, 0, 0, 1, None]
    class Tokenizer:
        def __call__(self, *a, **kw): return Enc()
    class Pred:
        def argmax(self, *a): return self
        def __getitem__(self, i): return self
        def tolist(self): return [0, 1, 2, 0, 0]
    class Model:
        class config:
            id2label = {0:"O", 1:"B-MODULO", 2:"I-MODULO"}
        def __call__(self, **kw):
            class Out: logits = Pred()
            return Out()
    assert predecir(["Modulo", "uno"], Tokenizer(), Model()) == ["B-MODULO", "O"]
    with pytest.raises(ValueError, match="truncada"):
        predecir(["a", "b", "c"], Tokenizer(), Model())


def test_manifiesto_coincide_con_vigentes():
    datos = json.loads((BASE_DIR / "docs/evidencias/beto_manifiesto.json").read_text(encoding="utf-8"))
    for nombre, info in datos["datos"].items():
        assert hashlib.sha256((BASE_DIR / "data" / nombre).read_bytes()).hexdigest() == info["sha256"]
    modelo = BASE_DIR / "pipeline/semantic/beto_local/model.safetensors"
    esperado = datos["modelo_vigente"]["archivos"]["model.safetensors"]["sha256"]
    assert len(esperado) == 64
    if modelo.exists():
        with modelo.open("rb") as f:
            assert hashlib.file_digest(f, "sha256").hexdigest() == esperado
    for nombre, info in datos["fuentes_y_evaluacion"].items():
        assert hashlib.sha256((BASE_DIR / nombre).read_bytes()).hexdigest() == info["sha256"]


def test_orquestacion_sin_entrenar(tmp_path):
    import shutil
    bash = shutil.which("bash")
    gitbash = Path("C:/Program Files/Git/bin/bash.exe")
    if gitbash.exists(): bash = str(gitbash)
    if not bash: pytest.skip("requiere Bash")
    spy = tmp_path / "python_spy.sh"
    log = tmp_path / "invocaciones.txt"
    spy.write_text('#!/bin/sh\nprintf \'%s|%s|%s\\n\' "$PYTHONHASHSEED" "$BETO_INT8" "$*" >> "$BETO_TEST_LOG"\n', encoding="utf-8")
    spy.chmod(0o755)
    env = dict(os.environ, PYTHON=spy.as_posix(), BETO_SALIDA=(tmp_path / "salida").as_posix(), BETO_TEST_LOG=log.as_posix())
    subprocess.run([bash, str(BASE_DIR / "scripts/beto_reproducir.sh")], env=env, check=True, capture_output=True)
    llamadas = log.read_text().splitlines()
    assert len(llamadas) == 3
    assert all(linea.startswith("0|0|") for linea in llamadas)
    assert "preparar_corpus_robusto.py" in llamadas[0]
    assert "entrenar_beto_robusto.py" in llamadas[1]
    assert "evaluar_beto_checkpoint.py" in llamadas[2]
    assert "--modelo" in llamadas[2] and "--gold" in llamadas[2]
