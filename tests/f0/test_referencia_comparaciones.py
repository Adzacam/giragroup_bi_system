"""La referencia usa ruta fija y la comparación conserva firmas redactadas."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import medir_f0 as f0
import comparar_huellas
import comparar_f0


@pytest.mark.parametrize("tree", ["/app", "/tmp/otro", "/tmp/f0_ref_73ec78f/../app"])
def test_measurement_rejects_unapproved_tree_before_any_command(tree):
    with pytest.raises(ValueError, match="árboles aislados"):
        f0.execute(SimpleNamespace(arbol=tree))


@pytest.mark.parametrize("flags,output", [((0, 1, 0, 0), "f0_referencia_a0_vacia_r1.json"),
                                          ((0, 0, 0, 0), "f0_a0_vacia_r1.json")])
def test_reference_cannot_enter_ablation_or_enable_options(flags, output):
    variables = [f"{key}={value}" for key, value in zip(f0.FLAGS, flags)] + ["BETO_VENTANA_STRIDE=32",
        "CATALOG_DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/catalogo_copia"]
    with pytest.raises(ValueError, match="reservado a a0"):
        f0.execute(SimpleNamespace(arbol=f0.REFERENCE_TREE, variables=variables, salida=output,
                                  db="run_f0_referencia_a0_vacia_r1"))


def test_public_redacted_signature_difference_is_not_silently_ignored(tmp_path, capsys):
    value = {"tablas": {"hechos": {"filas": 1, "md5": "same"}},
             "bandeja": {"casos": 1, "grupos": 1, "manuales": 1, "casos_manuales": 1, "firma_sha256": "old"},
             "kpis": {"KPI-10": None}}
    left, right = tmp_path / "left.json", tmp_path / "right.json"
    f0.write(left, value)
    f0.write(right, value)
    assert comparar_huellas.main(left, right) == 0
    value["bandeja"]["firma_sha256"] = "changed"
    f0.write(right, value)
    assert comparar_huellas.main(left, right) == 1
    assert "firma_sha256 distinta" in capsys.readouterr().out


def test_matrix_comparisons_separate_28_replicas_30_flags_and_21_cache_pairs(tmp_path):
    cells = []
    for config in f0.CONFIGS:
        for state in ("vacia", "llena"):
            runs = []
            for n in (1, 2, 3):
                identifier = f"f0_{config}_{state}_r{n}"
                metadata, footprint = identifier + ".meta.json", identifier + ".json.huella.json"
                f0.write(tmp_path / metadata, {"valida": True})
                f0.write(tmp_path / footprint, {"tablas": {"hechos": {"filas": 1, "md5": config}},
                    "bandeja": {"casos": 1, "grupos": 1, "firma_sha256": "same"}, "kpis": {"KPI-10": None}})
                runs.append({"id": identifier, "metadatos": metadata, "huella": footprint})
            cells.append({"configuracion": config, "estado": state, "corridas": runs})
    f0.write(tmp_path / "f0_ablacion.json", {"corridas_validas": 42, "celdas": cells})
    report = comparar_f0.compare(tmp_path)
    assert report["replicas_identicas"] is True
    assert len(report["comparaciones"]) == 79
    replicas = [r for r in report["comparaciones"] if r["tipo"] == "replicas"]
    contrasts = [r for r in report["comparaciones"] if r["tipo"] == "contraste_flags"]
    assert len(replicas) == 28 and all(r["identicas"] for r in replicas)
    assert len(contrasts) == 30 and not any(r["identicas"] for r in contrasts)
    caches = [r for r in report["comparaciones"] if r["tipo"] == "estado_cache"]
    assert len(caches) == 21 and all(r["identicas"] for r in caches)
    assert report["referencia"]["estado"] == "pendiente"
    # Una variación entre réplicas se distingue de los cambios legítimos por flags.
    fp = tmp_path / "f0_a0_vacia_r2.json.huella.json"
    data = json.loads(fp.read_text(encoding="utf-8"))
    data["bandeja"]["firma_sha256"] = "perturbed"
    f0.write(fp, data)
    perturbed = comparar_f0.compare(tmp_path)
    assert perturbed["replicas_identicas"] is False
    changed_cache = next(r for r in perturbed["comparaciones"] if r["tipo"] == "estado_cache" and r["origen"] == "f0_a0_vacia_r2")
    assert changed_cache["requiere_explicacion"] is True
    assert changed_cache["clasificacion"]["campos_bandeja_distintos"] == ["firma_sha256"]
