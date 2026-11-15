#!/usr/bin/env python
"""F1-V: 6 corridas de validación final (3 caché vacía + 3 caché llena con el modelo final) sobre /tmp/f1_validacion."""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import medir_f0 as f0

ARBOL = "/tmp/f1_validacion"
MEDICIONES = ROOT / "docs/mediciones"
SEED_SQL = ROOT / "output/f1/f1v_cache_seed.sql"

FLAGS_FINALES = [
    "BETO_CASCADA_FINAL=0",
    "BETO_ACUERDO_QC=0",
    "BETO_SUGERENCIA_HITL=0",
    "BETO_VENTANA=0",
    "BETO_VENTANA_STRIDE=32",
    "BETO_UMBRAL_REGLA=0.85",
    "BETO_UMBRAL_BETO=0.85",
    "BETO_PESO_SIM=0.55",
    "BETO_PESO_BETO=0.45",
    "BETO_INT8=0",
    "BETO_MODELO_VERSION=beto-v2",
]


def sh(*args: str, check: bool = True) -> str:
    res = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Comando falló ({' '.join(args)}): {res.stderr or res.stdout}")
    return res.stdout


def sql_tmpfs(db: str, query: str) -> str:
    if not re.fullmatch(r"run_f1v_[a-z0-9_]+", db):
        raise ValueError(f"Base no autorizada: {db}")
    return sh("docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", db, "-Atc", query).strip()


def cache_state_tmpfs(db: str) -> dict:
    result = {}
    for table in ("cache_indice_beto", "cache_beto_entidades"):
        exists = sql_tmpfs(db, f"SELECT to_regclass('public.{table}') IS NOT NULL") == "t"
        key = "modelo" if table == "cache_indice_beto" else "configuracion"
        result[table] = {
            "filas": int(sql_tmpfs(db, f"SELECT count(*) FROM public.{table}")) if exists else 0,
            "sha256_claves": hashlib.sha256(sql_tmpfs(db, f"SELECT hash_texto, {key} FROM public.{table} ORDER BY hash_texto, {key}").encode()).hexdigest() if exists else None,
            "sha256_contenido": hashlib.sha256(sql_tmpfs(db, f"SELECT to_jsonb(t) - 'creado_en' FROM public.{table} t ORDER BY hash_texto, {key}").encode()).hexdigest() if exists else None,
        }
    return result


def preparar_arbol() -> str:
    manifest = json.loads((MEDICIONES / "f0_lote_manifest.json").read_text(encoding="utf-8"))
    sh("docker", "exec", "giragroup_api", "rm", "-rf", ARBOL, "/tmp/slices_flujo", "/tmp/flujo/uploads/data")
    sh("docker", "exec", "giragroup_api", "mkdir", "-p",
       f"{ARBOL}/backend", f"{ARBOL}/pipeline", f"{ARBOL}/db/seeds", f"{ARBOL}/uploads/data",
       "/tmp/flujo/uploads/data", "/tmp/slices_flujo", "/tmp/flujo/scripts")
    sh("docker", "cp", str(ROOT / "backend") + "/.", f"giragroup_api:{ARBOL}/backend/")
    sh("docker", "cp", str(ROOT / "pipeline") + "/.", f"giragroup_api:{ARBOL}/pipeline/")
    sh("docker", "cp", str(ROOT / "db/seeds/seed_catalogos.sql"), f"giragroup_api:{ARBOL}/db/seeds/seed_catalogos.sql")
    for folder, dests in (("originales", (f"{ARBOL}/uploads/data", "/tmp/flujo/uploads/data")), ("slices", ("/tmp/slices_flujo",))):
        for p in (f0.PRIVATE / folder).glob("*.xlsx"):
            for dest in dests:
                sh("docker", "cp", str(p), f"giragroup_api:{dest}/{p.name}")
    f0.verify_container(manifest, ARBOL)
    for name in ("medir_flujo_dataops.py", "huella_dw.py", "simular_revision.py", "medir_ciclo_mensual.py"):
        sh("docker", "cp", str(ROOT / "scripts" / name), f"giragroup_api:/tmp/flujo/scripts/{name}")
    # Verificar que el modelo promocionado dentro del árbol coincide con f1_modelo_manifest.json
    mod_manifest = json.loads((MEDICIONES / "f1_modelo_manifest.json").read_text(encoding="utf-8"))
    raw = sh("docker", "exec", "giragroup_api", "python", "-c",
             f"import hashlib, json; from pathlib import Path; r=Path('{ARBOL}/pipeline/semantic/beto_local'); "
             "print(json.dumps({f.relative_to(r).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() "
             "for f in sorted(r.rglob('*')) if f.is_file()}))")
    actual = json.loads(raw)
    esperado = {x["archivo"]: x["sha256"] for x in mod_manifest["archivos"]}
    if actual != esperado:
        raise RuntimeError("El modelo en /tmp/f1_validacion no coincide con f1_modelo_manifest.json")
    return hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest()


def correr_una(estado: str, idx: int, modelo_digest: str) -> dict:
    db = f"run_f1v_{estado}_r{idx}"
    salida = f"f1_validacion_{estado}_r{idx}.json"
    out_path = MEDICIONES / salida
    huella_path = MEDICIONES / f"{salida}.huella.json"
    meta_path = MEDICIONES / f"{salida}.meta.json"
    for p in (out_path, huella_path, meta_path):
        if p.exists():
            p.unlink()

    verif_antes = f0.verify()
    assert verif_antes["valido"] is True

    cache_dir = f"/tmp/f1v/{db}/lectura"
    landing_dir = f"/tmp/f1v/{db}/landing"
    sh("docker", "exec", "giragroup_api", "rm", "-rf", f"/tmp/f1v/{db}")
    sh("docker", "exec", "giragroup_api", "mkdir", "-p", cache_dir, landing_dir)
    bash_exe = shutil.which("sh") or r"C:\Program Files\Git\bin\bash.exe"
    sh(bash_exe, "scripts/aislada_tmpfs.sh", "clon", db)

    sql_tmpfs(db, "TRUNCATE public.cache_indice_beto;")
    if sql_tmpfs(db, "SELECT to_regclass('public.cache_beto_entidades') IS NOT NULL") == "t":
        sql_tmpfs(db, "TRUNCATE public.cache_beto_entidades;")

    if estado == "llena":
        if not SEED_SQL.exists():
            raise RuntimeError("Falta semilla de caché llenada con el modelo final")
        sh("docker", "cp", str(SEED_SQL), "beto_pg_tmpfs:/tmp/f1v_cache_seed.sql")
        sh("docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", db, "-v", "ON_ERROR_STOP=1", "-f", "/tmp/f1v_cache_seed.sql")

    cache_antes = cache_state_tmpfs(db)
    if estado == "vacia":
        assert cache_antes["cache_indice_beto"]["filas"] == 0
    else:
        assert cache_antes["cache_indice_beto"]["filas"] > 0

    variables = FLAGS_FINALES + [
        f"DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/{db}",
        "FLUJO_SIN_REVISION=1",
        "CICLO_REUSAR_SLICES=1",
        "CICLO_FILAS_SIN_FECHA=0",
        "CICLO_SLICES=/tmp/slices_flujo",
        f"LECTURA_CACHE_DIR={cache_dir}",
        f"LANDING_DIR={landing_dir}",
        f"PYTHONPATH={ARBOL}:{ARBOL}/backend:/tmp/flujo/scripts",
    ]

    started = datetime.now(timezone.utc).astimezone().isoformat()
    t0 = time.perf_counter()
    sh("docker", "exec", "-w", ARBOL, "giragroup_api", "env", *variables,
       "python", "/tmp/flujo/scripts/medir_flujo_dataops.py", "/tmp/" + salida)
    pared_s = time.perf_counter() - t0
    finished = datetime.now(timezone.utc).astimezone().isoformat()

    sh("docker", "cp", f"giragroup_api:/tmp/{salida}", str(out_path))
    sh("docker", "cp", f"giragroup_api:/tmp/{salida}.huella.json", str(huella_path))

    data = json.loads(out_path.read_text(encoding="utf-8"))
    data.get("carga", {}).pop("errores", None)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    huella = json.loads(huella_path.read_text(encoding="utf-8"))
    if "firma" in huella.get("bandeja", {}):
        sig = huella["bandeja"].pop("firma")
        huella["bandeja"]["firma_sha256"] = hashlib.sha256(json.dumps(sig, sort_keys=True).encode()).hexdigest()
        huella_path.write_text(json.dumps(huella, indent=2, ensure_ascii=False), encoding="utf-8")

    cache_despues = cache_state_tmpfs(db)
    verif_despues = f0.verify()
    assert verif_despues["sha256"] == verif_antes["sha256"]

    if estado == "vacia" and idx == 1:
        SEED_SQL.parent.mkdir(parents=True, exist_ok=True)
        dump = sh("docker", "exec", "beto_pg_tmpfs", "pg_dump", "-U", "giragroup_user", "-d", db,
                  "--data-only", "--table=public.cache_indice_beto")
        SEED_SQL.write_text(dump, encoding="utf-8")

    sh("docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", "postgres", "-c", f"DROP DATABASE IF EXISTS {db};")

    meta = {
        "fecha_inicio": started,
        "fecha_fin": finished,
        "estado": estado,
        "corrida": idx,
        "arbol": ARBOL,
        "modelo_digest": modelo_digest,
        "lote_sha256": verif_despues["sha256"],
        "pared_s": round(pared_s, 3),
        "tiempo_maquina_s": data["total"]["tiempo_maquina_s"],
        "cache_antes": cache_antes,
        "cache_despues": cache_despues,
        "valida": True,
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"data": data, "huella": huella, "meta": meta}


def comparar_huellas(ref_path: Path, actual: dict) -> dict:
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    diffs = {}
    ref_tab = ref.get("tablas", {})
    act_tab = actual.get("tablas", {})
    for t in sorted(set(ref_tab) | set(act_tab)):
        if ref_tab.get(t) != act_tab.get(t):
            diffs[t] = {"f1_off": ref_tab.get(t), "f1_validacion": act_tab.get(t)}
    return {
        "identica_a_f1_off": (len(diffs) == 0 and ref.get("bandeja") == actual.get("bandeja") and ref.get("kpi") == actual.get("kpi")),
        "tablas_diferentes": diffs,
        "bandeja_f1_off": ref.get("bandeja"),
        "bandeja_f1_validacion": actual.get("bandeja"),
        "kpi_f1_off": ref.get("kpi"),
        "kpi_f1_validacion": actual.get("kpi"),
    }


def main() -> None:
    modelo_digest = preparar_arbol()
    resultados = {"vacia": [], "llena": []}
    for estado in ("vacia", "llena"):
        for idx in (1, 2, 3):
            print(f"[F1-V] Ejecutando {estado} r{idx}...")
            resultados[estado].append(correr_una(estado, idx, modelo_digest))

    resumen = {
        "lote_sha256": resultados["vacia"][0]["meta"]["lote_sha256"],
        "modelo_version": "beto-v2",
        "flags": {k.split("=")[0]: k.split("=")[1] for k in FLAGS_FINALES},
        "series": {},
        "comparacion_huella_vs_f1_off": comparar_huellas(MEDICIONES / "f1_off.json.huella.json", resultados["vacia"][0]["huella"]),
    }
    for estado in ("vacia", "llena"):
        tm = [r["meta"]["tiempo_maquina_s"] for r in resultados[estado]]
        ps = [r["meta"]["pared_s"] for r in resultados[estado]]
        resumen["series"][estado] = {
            "n": len(tm),
            "tiempo_maquina_s": {"valores": tm, "media": round(statistics.mean(tm), 3), "de": round(statistics.stdev(tm), 3)},
            "pared_s": {"valores": ps, "media": round(statistics.mean(ps), 3), "de": round(statistics.stdev(ps), 3)},
            "cache_filas_antes": [r["meta"]["cache_antes"]["cache_indice_beto"]["filas"] for r in resultados[estado]],
            "cache_filas_despues": [r["meta"]["cache_despues"]["cache_indice_beto"]["filas"] for r in resultados[estado]],
        }

    (MEDICIONES / "f1_validacion_resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
