"""Recuperación exacta de cachés desde stdout sintético, sin Docker ni personas."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("recuperacion_f0", SCRIPTS / "recuperar_f0_cache.py")
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def fixture_block():
    content = json.dumps({"hash_texto": "0" * 64, "modelo": "F0_SMOKE", "indice": .5})
    state = recovery.content_state(content, "cache_indice_beto")
    empty = recovery.content_state("", "cache_beto_entidades")
    seeds = {"semillas": [{"configuracion": config, "cache": {"cache_indice_beto": state, "cache_beto_entidades": empty}}
                           for config in ("a0", "a1")]}
    return content, seeds


def test_recovery_matches_original_content_keys_and_count(tmp_path):
    content, seeds = fixture_block()
    log = tmp_path / "stdout.txt"
    log.write_text("[2026-11-13] docker exit=0\nSTDOUT\nnot a cache\n\nSTDERR\n\n"
                   + "[2026-11-13] docker exit=0\nSTDOUT\n" + content + "\n\nSTDERR\n\n", encoding="utf-8")
    result = recovery.extract(log, seeds, tmp_path / "recovered")
    expected = seeds["semillas"][0]["cache"]["cache_indice_beto"]
    block = result[expected["sha256_contenido"]]
    assert block["estado"] == expected
    saved = tmp_path / "recovered" / block["archivo"]
    assert saved.read_text(encoding="utf-8").strip() == content
    assert result[recovery.hashlib.sha256(b"").hexdigest()]["estado"]["filas"] == 0


def test_changed_payload_is_not_accepted_as_original_cache(tmp_path):
    content, seeds = fixture_block()
    changed = content.replace('"indice": 0.5', '"indice": 0.6')
    log = tmp_path / "stdout.txt"
    log.write_text("STDOUT\n" + changed + "\n\nSTDERR\n", encoding="utf-8")
    with pytest.raises(ValueError, match="bloques exactos"):
        recovery.extract(log, seeds, tmp_path / "recovered")


def test_matching_content_cannot_hide_wrong_key_digest(tmp_path):
    content, seeds = fixture_block()
    seeds["semillas"][0]["cache"]["cache_indice_beto"]["sha256_claves"] = "wrong"
    log = tmp_path / "stdout.txt"
    log.write_text("STDOUT\n" + content + "\n\nSTDERR\n", encoding="utf-8")
    with pytest.raises(ValueError, match="claves/conteos"):
        recovery.extract(log, seeds, tmp_path / "recovered")


def test_recovered_rows_must_have_exact_cache_schema():
    with pytest.raises(ValueError, match="Columnas"):
        recovery.content_state(json.dumps({"hash_texto": "0" * 64, "modelo": "F0_SMOKE", "indice": .5,
                                           "unexpected": True}), "cache_indice_beto")
