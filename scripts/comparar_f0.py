"""Contrastes y réplicas F0 sobre artefactos sellados; no conecta a bases."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re

import comparar_huellas
import medir_f0 as f0

CONTRASTS = (("a0", "a1"), ("a0", "a2"), ("a1", "a12"), ("a3", "a123"), ("a2", "a2w"))


def compare(directory):
    directory = Path(directory)
    aggregate = json.loads((directory / "f0_ablacion.json").read_text(encoding="utf-8"))
    if aggregate.get("corridas_validas") != 42:
        raise ValueError("Comparación requiere las 42 corridas agregadas válidas")
    runs = {}
    for cell in aggregate["celdas"]:
        cell_runs = {}
        for run in cell["corridas"]:
            repetition = re.search(r"_r([123])(?:_|$)", run["id"])
            if not repetition or int(repetition[1]) in cell_runs:
                raise ValueError("Repeticiones faltantes o duplicadas")
            meta = json.loads((directory / run["metadatos"]).read_text(encoding="utf-8"))
            if not meta.get("valida"):
                raise ValueError("No comparar una corrida inválida")
            cell_runs[int(repetition[1])] = run
        if set(cell_runs) != {1, 2, 3}:
            raise ValueError("Cada celda requiere r1, r2 y r3 válidas")
        runs[cell["configuracion"], cell["estado"]] = cell_runs
    if set(runs) != {(c, s) for c in f0.CONFIGS for s in ("vacia", "llena")}:
        raise ValueError("Matriz de celdas incompleta")
    results = []

    def one(left, right, name, category):
        output = io.StringIO()
        with redirect_stdout(output):
            code = comparar_huellas.main(directory / left["huella"], directory / right["huella"])
        path = directory / name
        path.write_text(output.getvalue(), encoding="utf-8")
        result = {"origen": left["id"], "destino": right["id"], "identicas": code == 0,
                  "tipo": category, "evidencia": path.name}
        a = json.loads((directory / left["huella"]).read_text(encoding="utf-8"))
        b = json.loads((directory / right["huella"]).read_text(encoding="utf-8"))
        result["clasificacion"] = {
            "tablas_con_cambio_conteo": [key for key in sorted(set(a["tablas"]) | set(b["tablas"]))
                if a["tablas"].get(key, {}).get("filas") != b["tablas"].get(key, {}).get("filas")],
            "tablas_con_cambio_contenido": [key for key in sorted(set(a["tablas"]) | set(b["tablas"]))
                if a["tablas"].get(key, {}).get("md5") != b["tablas"].get(key, {}).get("md5")],
            "campos_bandeja_distintos": [key for key in ("casos", "grupos", "manuales", "casos_manuales", "firma", "firma_sha256")
                if a["bandeja"].get(key) != b["bandeja"].get(key)],
            "kpis_distintos": [key for key in sorted(set(a.get("kpis", {})) | set(b.get("kpis", {})))
                if a.get("kpis", {}).get(key) != b.get("kpis", {}).get(key)],
        }
        result["requiere_explicacion"] = code != 0
        results.append(result)
        return result

    for (config, state), repetitions in runs.items():
        for n in (2, 3):
            one(repetitions[1], repetitions[n], f"f0_comparacion_replicas_{config}_{state}_r1_r{n}.txt", "replicas")
    for source, target in CONTRASTS:
        for state in ("vacia", "llena"):
            for n in (1, 2, 3):
                one(runs[source, state][n], runs[target, state][n],
                    f"f0_comparacion_{source}_{target}_{state}_r{n}.txt", "contraste_flags")
    for config in f0.CONFIGS:
        for n in (1, 2, 3):
            one(runs[config, "vacia"][n], runs[config, "llena"][n],
                f"f0_comparacion_cache_{config}_r{n}.txt", "estado_cache")
    references = []
    for path in directory.glob("f0_referencia_a0_vacia_r*.meta.json"):
        if json.loads(path.read_text(encoding="utf-8")).get("valida"):
            references.append(path)
    if len(references) > 1:
        raise ValueError("Más de una referencia válida; reconciliar IDs antes de comparar")
    reference = {"estado": "pendiente", "commit": "73ec78f"}
    if references:
        identifier = references[0].name.removesuffix(".meta.json")
        source = {"id": identifier, "huella": identifier + ".json.huella.json"}
        reference = {"estado": "comparada", "commit": "73ec78f", "comparaciones": [
            one(source, runs["a0", "vacia"][n], f"f0_comparacion_referencia_a0_vacia_r{n}.txt", "referencia")
            for n in (1, 2, 3)]}
    report = {"fecha": f0.now(), "comparaciones": results, "referencia": reference,
              "script_sha256": f0.digest(Path(__file__)),
              "replicas_identicas": all(r["identicas"] for r in results if r["tipo"] == "replicas"),
              "interpretacion": "Diferencias entre flags requieren explicación; no se clasifican automáticamente como fallo. Réplicas y referencia esperan identidad."}
    f0.write(directory / "f0_comparaciones.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directorio", default=str(f0.MANIFEST.parent))
    args = parser.parse_args()
    compare(args.directorio)
