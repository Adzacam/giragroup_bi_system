"""Recupera cachés F0 exactas de stdout privado, sin inferencia ni regeneración.

Las huellas originales excluyen creado_en. Se conserva el texto JSON SQL exacto
para comprobar contenido y claves antes de cualquier restauración en tmpfs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil

import medir_f0 as f0


KEYS = {
    "cache_indice_beto": ("hash_texto", "modelo", "indice"),
    "cache_beto_entidades": ("hash_texto", "configuracion", "entidades"),
}


def content_state(content, table):
    rows = [json.loads(line) for line in content.splitlines() if line.strip()]
    if any(set(row) != set(KEYS[table]) for row in rows):
        raise ValueError("Columnas de caché recuperada no coinciden")
    second = KEYS[table][1]
    # PostgreSQL psql -At separa columnas por | y cache_state aplica strip().
    keys = "\n".join(row["hash_texto"] + "|" + row[second] for row in rows)
    return {"filas": len(rows), "sha256_claves": hashlib.sha256(keys.encode()).hexdigest(),
            "sha256_contenido": hashlib.sha256(content.strip().encode()).hexdigest()}


def extract(log, seeds, directory):
    """Lee por bloques; no carga el log completo de cientos de MB en memoria."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    expected = {}
    for seed in seeds["semillas"]:
        for table, state in seed["cache"].items():
            expected.setdefault(state["sha256_contenido"], []).append((seed["configuracion"], table, state))
    found, collecting, lines, candidate = {}, False, [], None

    def finish():
        if candidate is None:
            return
        content = "".join(lines).strip()
        fingerprint = hashlib.sha256(content.encode()).hexdigest()
        if fingerprint not in expected or fingerprint in found:
            return
        matching = [entry for entry in expected[fingerprint] if entry[1] == candidate]
        if not matching:
            return
        state = content_state(content, candidate)
        if any(state != entry[2] for entry in matching):
            raise ValueError("Contenido coincidente pero claves/conteos distintos")
        target = directory / (fingerprint + ".jsonl")
        target.write_text(content + "\n", encoding="utf-8")
        found[fingerprint] = {"tabla": candidate, "archivo": target.name, "estado": state,
                              "sha256_archivo": f0.digest(target)}

    with Path(log).open(encoding="utf-8") as reader:
        for line in reader:
            marker = line.rstrip("\r\n")
            if marker == "STDOUT":
                collecting, lines, candidate = True, [], None
            elif marker == "STDERR" and collecting:
                finish()
                collecting, lines, candidate = False, [], None
            elif collecting:
                if not lines and not line.strip():
                    continue
                if not lines and candidate is None:
                    try:
                        row = json.loads(line)
                    except (ValueError, TypeError):
                        collecting = False
                        continue
                    candidate = next((table for table, keys in KEYS.items()
                                      if isinstance(row, dict) and set(row) == set(keys)), None)
                    if candidate is None:
                        collecting = False
                        continue
                lines.append(line)
    if collecting:
        finish()
    empty = hashlib.sha256(b"").hexdigest()
    if empty in expected:
        # Es el estado vacío explícitamente verificado en el manifiesto previo.
        found[empty] = {"archivo": None, "estado": {"filas": 0, "sha256_claves": empty, "sha256_contenido": empty},
                        "nota": "Tabla vacía según manifiesto previo; no se inventan filas"}
    missing = sorted(set(expected) - set(found))
    if missing:
        raise ValueError(f"Faltan {len(missing)} bloques exactos; recuperación incompleta, inferencia prohibida")
    return found


def prepare(log=None):
    f0.verify()
    seed_path = f0.MANIFEST.parent / "f0_cache_semillas.json"
    seeds = json.loads(seed_path.read_text(encoding="utf-8"))
    manifest = json.loads(f0.MANIFEST.read_text(encoding="utf-8"))
    if seeds["lote_sha256"] != manifest["sha256"] or {s["configuracion"] for s in seeds["semillas"]} != set(f0.CONFIGS):
        raise ValueError("Semillas/lote originales no corresponden a F0")
    directory = f0.PRIVATE / "recuperacion_cache"
    frozen = directory / "fuente_original_stdout.txt"
    directory.mkdir(parents=True, exist_ok=True)
    if not frozen.exists():
        shutil.copyfile(Path(log or f0.PRIVATE / "comandos.stdout-stderr.txt"), frozen)
    source = frozen
    blocks = extract(source, seeds, directory)
    environment = json.loads((f0.MANIFEST.parent / "f0_entorno.json").read_text(encoding="utf-8"))
    for seed in seeds["semillas"]:
        meta = json.loads((f0.MANIFEST.parent / ("f0_warmup_" + seed["configuracion"] + ".meta.json")).read_text(encoding="utf-8"))
        if not meta.get("valida") or meta["modelo_sha256"] != environment["modelo_sha256"] or meta["lote_sha256"] != manifest["sha256"]:
            raise ValueError("Procedencia de calentamiento distinta del lote/modelo congelados")
    entries = []
    for seed in seeds["semillas"]:
        tables = {}
        for table, expected in seed["cache"].items():
            block = blocks[expected["sha256_contenido"]]
            if block["estado"] != expected:
                raise ValueError("Estado recuperado no idéntico al manifiesto original")
            tables[table] = {"estado": expected, "archivo_privado": str((directory / block["archivo"]).relative_to(f0.PRIVATE)) if block["archivo"] else None}
        entries.append({"configuracion": seed["configuracion"], "base": seed["base"], "tablas": tables})
    report = {"fecha": f0.now(), "estado": "recuperacion_offline_verificada", "semillas_regeneradas": False,
              "lote_sha256": manifest["sha256"], "semillas_originales_sha256": f0.digest(seed_path),
              "fuente_privada": str(source.relative_to(f0.PRIVATE)), "fuente_sha256": f0.digest(source), "fuente_bytes": source.stat().st_size,
              "modelo_sha256": environment["modelo_sha256"], "arbol_sha256": environment["arbol_sha256"],
              "script_sha256": f0.digest(Path(__file__)), "semillas": entries,
              "identidad": "Contenido, claves y conteos exactos de cada caché original; creado_en excluido por protocolo original",
              "restauracion_db": "pendiente; no se ejecuta inferencia ni se modifica servidor en esta preparación"}
    f0.write(f0.MANIFEST.parent / "f0_cache_recuperacion.json", report)
    return report


def restore():
    report_path = f0.MANIFEST.parent / "f0_cache_recuperacion.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    environment = json.loads((f0.MANIFEST.parent / "f0_entorno.json").read_text(encoding="utf-8"))
    if report.get("modelo_sha256", environment["modelo_sha256"]) != environment["modelo_sha256"] or f0.runtime_hash("giragroup_pipeline", environment["modelo_directorio"]) != environment["modelo_sha256"]:
        raise ValueError("Pesos/tokenizador distintos: no restaurar semillas")
    results = []
    for seed in report["semillas"]:
        db = seed["base"]
        if db != "f0_cache_" + seed["configuracion"] or seed["configuracion"] not in f0.CONFIGS:
            raise ValueError("Nombre de semilla no autorizado")
        exists = f0.run("docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", "postgres", "-At",
                        "-c", f"SELECT 1 FROM pg_database WHERE datname='{db}'").strip() == "1"
        expected = {table: item["estado"] for table, item in seed["tablas"].items()}
        if exists:
            if f0.cache_state(db) != expected:
                raise ValueError("Semilla existente distinta; no sobrescribir")
            results.append({"base": db, "estado": "existente_identica"})
            continue
        f0.run("docker", "exec", "beto_pg_tmpfs", "createdb", "-U", "giragroup_user", "-T", "template0", db)
        for table, item in seed["tablas"].items():
            schema = f0.run("docker", "exec", "beto_pg_tmpfs", "pg_dump", "-U", "giragroup_user", "-d", "dw_vacio",
                            "--schema-only", "--no-owner", "--no-privileges", "-t", "public." + table)
            f0.run("docker", "exec", "-i", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", db,
                   "-v", "ON_ERROR_STOP=1", input=schema)
            if item["archivo_privado"]:
                source = f0.PRIVATE / item["archivo_privado"]
                content = source.read_text(encoding="utf-8")
                if content_state(content, table) != item["estado"]:
                    raise ValueError("Archivo privado recuperado alterado")
                data = io.StringIO(newline="")
                writer = csv.writer(data, lineterminator="\n")
                for line in content.splitlines():
                    row = json.loads(line)
                    writer.writerow([row[key] for key in KEYS[table]])
                command = "COPY public." + table + "(" + ",".join(KEYS[table]) + ") FROM STDIN WITH (FORMAT csv)"
                f0.run("docker", "exec", "-i", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", db,
                       "-v", "ON_ERROR_STOP=1", "-c", command, input=data.getvalue())
        actual = f0.cache_state(db)
        if actual != expected:
            raise ValueError("Restauración no coincide con caché original")
        results.append({"base": db, "estado": "restaurada_identica", "cache": actual})
        report["restauracion_db"] = results
        f0.write(report_path, report)
    report["estado"] = "restauracion_db_verificada"
    report["restauracion_db"] = results
    f0.write(report_path, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restaurar", action="store_true")
    args = parser.parse_args()
    restore() if args.restaurar else prepare()
