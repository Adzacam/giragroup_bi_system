"""Puertas F0 sin Docker ni personas reales."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location("medir_f0", Path(__file__).resolve().parents[2] / "scripts/medir_f0.py")
f0 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f0)


def test_input_missing_extra_and_hash_change(tmp_path):
    for folder in ("originales", "slices"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "a.xlsx").write_bytes(b"immutable fixture")
    entries = f0.inventory(tmp_path)
    manifest = tmp_path / "manifest.json"
    f0.write(manifest, {"copia_privada": str(tmp_path), "archivos": entries,
                        "sha256": f0.hashlib.sha256(f0.canonical(entries)).hexdigest()})
    assert f0.verify(manifest)["valido"]
    reordered = json.loads(manifest.read_text(encoding="utf-8"))
    reordered["archivos"].reverse()  # Windows/Linux pueden ordenar nombres distinto.
    f0.write(manifest, reordered)
    assert f0.verify(manifest)["valido"]
    target = tmp_path / "slices/a.xlsx"
    target.unlink()
    with pytest.raises(ValueError):
        f0.verify(manifest)
    target.write_bytes(b"altered fixture")
    with pytest.raises(ValueError):
        f0.verify(manifest)
    target.write_bytes(b"immutable fixture")
    (tmp_path / "slices/extra.xlsx").write_bytes(b"extra")
    with pytest.raises(ValueError):
        f0.verify(manifest)


def test_inherited_flags_cannot_substitute_explicit_flags(monkeypatch):
    for flag in f0.FLAGS:
        monkeypatch.setenv(flag, "1")
    with pytest.raises(ValueError, match="cuatro flags"):
        f0.explicit_flags([])
    with pytest.raises(ValueError, match="Catálogo"):
        f0.explicit_flags([f"{k}=0" for k in f0.FLAGS])


def test_cache_conflict_and_invalid_database_do_not_execute(monkeypatch):
    monkeypatch.setattr(f0, "run", lambda *a, **kw: pytest.fail("must not execute"))
    with pytest.raises(ValueError):
        f0.seed_cache("run_f0_test", "f0_cache_a0", empty=True)
    with pytest.raises(ValueError):
        f0.seed_cache("run_f0_test", "giragroup_db")
    with pytest.raises(ValueError):
        f0.sql("run_f0_x;DROP DATABASE y", "SELECT 1")


def test_empty_cache_is_verified_for_both_tables(monkeypatch):
    queries = []
    def fake(db, query):
        queries.append(query)
        if "to_regclass" in query:
            return "t"
        if "count(*)" in query:
            return "0"
        return ""
    monkeypatch.setattr(f0, "sql", fake)
    state = f0.seed_cache("run_f0_test", empty=True)
    assert len([q for q in queries if q.startswith("TRUNCATE")]) == 2
    assert all(v["filas"] == 0 for v in state.values())


def test_seed_restores_only_both_caches_and_checks_identity(monkeypatch):
    commands = []
    monkeypatch.setattr(f0, "sql", lambda db, q: "t")
    def command(*args, **kw):
        commands.append((args, kw))
        return "-- private dump"
    monkeypatch.setattr(f0, "run", command)
    monkeypatch.setattr(f0, "cache_state", lambda db: {t: {"filas": 2, "sha256_claves": "x"} for t in f0.CACHES})
    assert f0.seed_cache("run_f0_test", "f0_cache_a0")["cache_indice_beto"]["filas"] == 2
    assert len(commands) == 4
    assert all(any(t in str(args) for t in f0.CACHES) for args, kw in commands if "pg_dump" in args)
    monkeypatch.setattr(f0, "cache_state", lambda db: {"filas": 0 if db.startswith("run") else 1})
    with pytest.raises(ValueError, match="no idéntica"):
        f0.seed_cache("run_f0_test", "f0_cache_a0")


def result():
    return {"carga": {"http": 200, "archivos_exitosos": 10, "archivos_fallidos": 0, "registros_detectados": 100},
            "consolidacion_http": 200, "revision": {"omitida": True}, "dw_despues": {"hechos": 1},
            "lectura_beto_contadores": {"comparadas_acuerdo": 7, "acuerdos": 4, "desacuerdos": 2, "tipo_distinto": 1, "no_evaluables": 3},
            "etapas_s": {"carga": 1}, "total": {"tiempo_maquina_s": 2}}


def test_partial_output_rejected():
    f0.valid_result(result())
    for section in ("carga", "consolidacion_http", "etapas_s", "dw_despues", "total"):
        data = result()
        data.pop(section)
        with pytest.raises(ValueError):
            f0.valid_result(data)


def test_aggregation_requires_three_per_cell(tmp_path):
    data = result()
    for config in f0.CONFIGS:
        for state in ("vacia", "llena"):
            for n in (1, 2, 3):
                path = tmp_path / f"f0_{config}_{state}_r{n}.json"
                f0.write(path, data)
                f0.write(path.with_suffix(".meta.json"), {"valida": True, "configuracion": config, "estado": state,
                    "lote_sha256": "lote", "arbol_sha256": "code", "modelo_sha256": "model",
                    "flags": dict(zip(f0.FLAGS, map(str, f0.CONFIGS[config])))})
                f0.write(str(path) + ".huella.json", {"tablas": {"hechos": {"filas": 1}}, "kpis": {"KPI-10": None}})
    args = SimpleNamespace(directorio=str(tmp_path), prefijo="f0", salida=str(tmp_path / "summary.json"), csv=str(tmp_path / "summary.csv"))
    f0.aggregate(args)
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["corridas_validas"] == 42
    window = json.loads((tmp_path / "f0_ventana.json").read_text(encoding="utf-8"))
    reading = next(r for r in window["corridas"] if r["etapa"] == "lectura")
    assert reading["comparadas_acuerdo"] == 7
    assert reading["total_veredictos"] == 10
    assert reading["cobertura_evaluable"] == .6
    assert reading["tasa_acuerdo_evaluable"] == pytest.approx(4/6)
    assert reading["fraccion_no_evaluable"] == pytest.approx(3/7)
    assert reading["proporcion_no_evaluable_total_veredictos"] == .3
    assert reading["denominador_conciliado"] is True
    assert reading["cumple_menos_20_pct"] is False
    cell = summary["celdas"][0]
    for code in ("KPI-10", "KPI-11", "KPI-18"):
        metric = cell["metricas"]["huella.kpis." + code]
        assert metric["n"] == 0
        assert metric["media"] is None
        assert metric["de_muestral"] is None
        assert metric["ausencias"] == 3
        assert len(metric["motivos_ausencia"]) == 3
        expected = "NULL" if code == "KPI-10" else "ausente"
        assert all(expected in reason["motivo"] for reason in metric["motivos_ausencia"])
    assert len(cell["corridas"]) == 3
    assert cell["corridas"][0] == {"id": "f0_a0_vacia_r1", "resultado": "f0_a0_vacia_r1.json",
        "metadatos": "f0_a0_vacia_r1.meta.json", "huella": "f0_a0_vacia_r1.json.huella.json"}
    f0.write(tmp_path / "f0_a0_vacia_r0.meta.json", {"valida": False, "motivo_invalida": "interferencia"})
    f0.aggregate(args)  # Una réplica inválida conservada nunca participa en media/DE.
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["corridas_invalidas"] == [{"id": "f0_a0_vacia_r0", "metadatos": "f0_a0_vacia_r0.meta.json",
        "configuracion": "a0", "estado": "vacia", "motivo": "interferencia"}]
    # Valor no numérico explícito no desaparece ni entra en la media.
    f0.write(tmp_path / "f0_a0_vacia_r1.json.huella.json", {"tablas": {"hechos": {"filas": 1}},
        "kpis": {"KPI-10": "no disponible", "KPI-11": 90, "KPI-18": 25}})
    f0.aggregate(args)
    cell = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["celdas"][0]
    assert cell["metricas"]["huella.kpis.KPI-10"]["n"] == 0
    assert any("no numérico" in reason["motivo"] for reason in cell["metricas"]["huella.kpis.KPI-10"]["motivos_ausencia"]), cell["metricas"]["huella.kpis.KPI-10"]
    assert cell["metricas"]["huella.kpis.KPI-11"]["n"] == 1
    assert cell["metricas"]["huella.kpis.KPI-11"]["media"] == 90
    assert cell["metricas"]["huella.kpis.KPI-11"]["de_muestral"] is None
    original = tmp_path / "f0_a0_vacia_r3"
    for suffix in (".json", ".meta.json", ".json.huella.json"):
        Path(str(original) + suffix).rename(tmp_path / ("f0_a0_vacia_r3_reintento" + suffix))
    f0.aggregate(args)  # Reintento con identificador nuevo; no exige sobrescribir r3.
    (tmp_path / "f0_a0_vacia_r3_reintento.json").unlink()
    with pytest.raises(FileNotFoundError):
        f0.aggregate(args)


def test_snapshot_gate_rejects_nonidentical_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(f0, "MANIFEST", tmp_path / "manifest.json")
    f0.write(tmp_path / "f0_snapshot_antes.json", {"huella": "a"})
    f0.write(tmp_path / "f0_snapshot_copia.json", {"huella": "b"})
    with pytest.raises(ValueError, match="no idénticos"):
        f0.gates()


def test_series_resume_reuses_valid_retry_without_creating_fourth_sample(tmp_path, monkeypatch):
    monkeypatch.setattr(f0, "MANIFEST", tmp_path / "manifest.json")
    monkeypatch.setattr(f0, "gates", lambda: {})
    monkeypatch.setattr(f0, "execute", lambda args: pytest.fail("All repetitions already valid; must not rerun"))
    import f0_mantener_activo as energy
    monkeypatch.setattr(energy, "bind_driver", lambda: None)
    monkeypatch.setattr(energy, "request_stop", lambda: None)
    for config in f0.CONFIGS:
        for state in ("vacia", "llena"):
            for n in (1, 2, 3):
                path = tmp_path / f"f0_{config}_{state}_r{n}.meta.json"
                f0.write(path, {"valida": True})
    f0.write(tmp_path / "f0_a0_vacia_r1.meta.json", {"valida": False, "motivo_invalida": "interferencia"})
    f0.write(tmp_path / "f0_a0_vacia_r1_reintento1.meta.json", {"valida": True})
    f0.series(SimpleNamespace(conservar_bases=False))
    assert len(list(tmp_path.glob("*.meta.json"))) == 43


def test_runtime_rejects_pipeline_restart_even_when_code_and_model_match(monkeypatch):
    monkeypatch.setattr(f0, "runtime_hash", lambda container, path: "code" if container == "giragroup_api" else "model")
    monkeypatch.setattr(f0, "run", lambda *args, **kw: json.dumps({"id": "same-container", "imagen": "same-image", "inicio": "restarted"}))
    environment = {"arbol_sha256": "code", "modelo_sha256": "model", "modelo_directorio": "/model",
        "contenedores": {"giragroup_pipeline": {"id": "same-container", "imagen": "same-image", "inicio": "initial"}}}
    with pytest.raises(ValueError, match="reiniciado"):
        f0.verify_runtime(environment)


def test_log_compaction_preserves_original_bytes_and_private_integrals(tmp_path, monkeypatch):
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir()
    private.mkdir()
    monkeypatch.setattr(f0, "MANIFEST", public / "manifest.json")
    monkeypatch.setattr(f0, "PRIVATE", private)
    (private / "comandos.stdout-stderr.txt").write_text("private fixture bytes\n", encoding="utf-8")
    source = public / "f0_comandos_redactados.jsonl"
    lines = [{"linea": i, "bytes": 10, "sha256": "hash", "texto": "[REDACTADO]"} for i in range(1, 101)]
    original = (json.dumps({"stdout": lines, "stderr": []}) + "\n").encode()
    source.write_bytes(original)
    f0.compact_log()
    provenance = json.loads((public / "f0_log_compactacion.json").read_text(encoding="utf-8"))
    assert (private / provenance["original_privado"]).read_bytes() == original
    assert provenance["original_sha256"] == f0.hashlib.sha256(original).hexdigest()
    compact = json.loads(source.read_text(encoding="utf-8"))
    assert compact["stdout"]["lineas"] == 100
    assert compact["stdout"]["bytes_sin_saltos"] == 1000
    assert source.stat().st_size < len(original)
    assert (private / "comandos.stdout-stderr.txt").read_text(encoding="utf-8") == "private fixture bytes\n"
