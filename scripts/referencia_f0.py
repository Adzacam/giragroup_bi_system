"""Referencia a0 del commit fijo 73ec78f, fuera de las 42 mediciones F0."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import medir_f0 as f0


def archive():
    """Código histórico solo en carpeta privada; puede contener secretos antiguos."""
    commit = f0.run("git", "rev-parse", "73ec78f^{commit}").strip()
    target = f0.PRIVATE / "referencia_73ec78f.tar"
    report_path = f0.MANIFEST.parent / "f0_referencia_preparacion.json"
    if target.exists() and report_path.exists():
        previous = json.loads(report_path.read_text(encoding="utf-8"))
        if previous.get("git_commit") != commit or previous.get("archivo_sha256") != f0.digest(target):
            raise ValueError("Archivo histórico privado alterado; no extraer ni sobrescribir")
        return target, previous
    if target.exists():
        raise ValueError("Archivo histórico existente sin procedencia; verificar antes de usar")
    if not target.exists():
        f0.run("git", "archive", "--format=tar", "-o", str(target), commit,
               "backend", "pipeline", "db/seeds/seed_catalogos.sql")
    result = {"fecha": f0.now(), "git_commit": commit, "archivo_privado": target.name,
              "archivo_sha256": f0.digest(target), "datos_incluidos": False,
              "nota": "Archivo histórico privado no versionable; no se publica código antiguo ni credenciales"}
    f0.write(report_path, result)
    return target, result


def prepare_tree():
    target, report = archive()
    f0.verify()
    env_path = f0.MANIFEST.parent / "f0_entorno.json"
    env = json.loads(env_path.read_text(encoding="utf-8"))
    root = f0.REFERENCE_TREE
    exists = f0.run("docker", "exec", "giragroup_api", "python", "-c",
                    "from pathlib import Path; import sys; print(int(Path(sys.argv[1]).exists()))", root).strip() == "1"
    if exists:
        if not env.get("referencia_73ec78f") or f0.runtime_hash("giragroup_api", root) != env["referencia_73ec78f"]["arbol_sha256"]:
            raise ValueError("Árbol de referencia existente sin huella válida; no sobrescribir")
        return env["referencia_73ec78f"]
    f0.run("docker", "exec", "giragroup_api", "mkdir", "-p", root)
    f0.run("docker", "cp", str(target), "giragroup_api:/tmp/f0_ref_73ec78f.tar")
    f0.run("docker", "exec", "giragroup_api", "tar", "-xf", "/tmp/f0_ref_73ec78f.tar", "-C", root)
    code = """from pathlib import Path
import hashlib,shutil
root=Path('/tmp/f0_ref_73ec78f')
p=root/'backend/services/ingestion_service.py'
original=p.read_text()
old='\"/app\", \"/app/pipeline\"'
assert old in original, 'Rutas originales no reconocidas'
p.write_text(original.replace(old,'\"/tmp/f0_ref_73ec78f\", \"/tmp/f0_ref_73ec78f/pipeline\"'))
model=root/'pipeline/semantic/beto_local'
assert not model.exists(), 'El archivo Git no debe incluir pesos'
model.symlink_to('/tmp/medida/pipeline/semantic/beto_local',target_is_directory=True)
shutil.copytree('/tmp/flujo/uploads',root/'uploads')
print(hashlib.sha256((root/'db/seeds/seed_catalogos.sql').read_bytes()).hexdigest())
"""
    seed_sha = f0.run("docker", "exec", "giragroup_api", "python", "-c", code).strip()
    if seed_sha != env["seed_catalogos"]["sha256"]:
        raise ValueError("Seed institucional histórico distinto del congelado; referencia pendiente")
    manifest = json.loads(f0.MANIFEST.read_text(encoding="utf-8"))
    f0.verify_container(manifest, root)
    report.update({"arbol": root, "arbol_sha256": f0.runtime_hash("giragroup_api", root),
                   "lote_sha256": manifest["sha256"], "modelo_sha256": env["modelo_sha256"], "seed_sha256": seed_sha,
                   "ajuste_exclusivo_copia": 'ingestion_service.py: "/app", "/app/pipeline" → ruta fija referencia; pesos enlazados a copia medida',
                   "estado": "arbol_referencia_preparado"})
    env["referencia_73ec78f"] = report
    f0.write(env_path, env)
    f0.write(f0.MANIFEST.parent / "f0_referencia_preparacion.json", report)
    return report


def execute():
    import os
    prepare_tree()
    basename = "f0_referencia_a0_vacia_r1"
    path = f0.MANIFEST.parent / (basename + ".meta.json")
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")).get("valida"):
            return
        retry = 1
        while (f0.MANIFEST.parent / f"{basename}_reintento{retry}.meta.json").exists():
            retry += 1
        basename += f"_reintento{retry}"
    previous = (os.environ.get("CACHE_VACIA"), os.environ.pop("CACHE_SEED_DB", None))
    os.environ["CACHE_VACIA"] = "1"
    try:
        f0.execute(SimpleNamespace(arbol=f0.REFERENCE_TREE, db="run_" + basename, salida=basename + ".json",
            variables=[key + "=0" for key in f0.FLAGS] + ["BETO_VENTANA_STRIDE=32",
                "CATALOG_DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/catalogo_copia"]))
    finally:
        for key, value in zip(("CACHE_VACIA", "CACHE_SEED_DB"), previous):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arbol", action="store_true", help="Preparar árbol Docker sin inferir")
    parser.add_argument("--ejecutar", action="store_true", help="Medir referencia a0 fuera de la matriz")
    args = parser.parse_args()
    execute() if args.ejecutar else prepare_tree() if args.arbol else archive()
