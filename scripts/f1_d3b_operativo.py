#!/usr/bin/env python
"""D-C: Efecto operativo en pipeline completo (beto-v1 vs beto-v2, 3 vacias + 3 llenas intercaladas en tmpfs)."""
import csv
import hashlib
import json
import os
import re
import shutil
import statistics as st
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

import agregar_flujo_repetido as afr  # noqa: E402
import f1_validar as fv  # noqa: E402
import medir_f0 as f0  # noqa: E402

MED = ROOT / "docs/mediciones"
ARBOL = "/tmp/f1_d3b"
SH_EXE = shutil.which("sh") or r"C:\Program Files\Git\bin\sh.exe"

CONTENEDORES = {
    "v1": {
        "nombre": "beto_pipeline_d3b_v1",
        "modelo_dir": str((ROOT / "output/f1/beto_local_respaldo").resolve()),
        "modelo_version": "beto-v1",
        "sha256_esperado": "5966dde3fa4adccacb8ed74c62c991a6bf140c2b4d67598a05a1c35e67ec9543",
    },
    "v2": {
        "nombre": "beto_pipeline_d3b_v2",
        "modelo_dir": str((ROOT / "pipeline/semantic/beto_local").resolve()),
        "modelo_version": "beto-v2",
        "sha256_esperado": "9ff7fb9d914aca9eaa0618d9603d869a30808d9218369aef7b12dd92362b5f92",
    },
}

FLAGS_BASE = [
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
]


def sh(*args: str, check: bool = True) -> str:
    res = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Comando fallo ({' '.join(args)}): {res.stderr or res.stdout}")
    return res.stdout


def sha256_archivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def sql_tmpfs(db: str, query: str) -> str:
    if not re.fullmatch(r"run_d3b_[a-z0-9_]+", db):
        raise ValueError(f"Base no autorizada: {db}")
    return sh(
        "docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", db, "-Atc", query
    ).strip()


def drop_db_tmpfs(db: str) -> None:
    if not re.fullmatch(r"run_d3b_[a-z0-9_]+", db):
        raise ValueError(f"Base no autorizada: {db}")
    sh(
        "docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", "postgres",
        "-c", f"DROP DATABASE IF EXISTS {db} WITH (FORCE);",
    )


def verificar_puertos() -> dict:
    tmpfs = sh("docker", "port", "beto_pg_tmpfs").strip()
    viva = sh("docker", "port", "giragroup_db").strip()
    p_tmpfs = re.findall(r":(\d+)$", tmpfs, re.M)
    p_viva = re.findall(r":(\d+)$", viva, re.M)
    if not p_tmpfs or set(p_tmpfs) & set(p_viva):
        raise RuntimeError(f"TMPFS_PORT no verificado: tmpfs={tmpfs!r} viva={viva!r}")
    return {"tmpfs_port": int(p_tmpfs[0]), "dw_viva_port": int(p_viva[0]) if p_viva else None}


def carga_sistema() -> dict:
    info = {"cpu_count": os.cpu_count()}
    try:
        info["loadavg"] = [round(x, 3) for x in os.getloadavg()]
    except (AttributeError, OSError):
        info["loadavg"] = None
    try:
        out = sh(
            "powershell", "-NoProfile", "-Command",
            "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average",
            check=False,
        ).strip()
        info["windows_cpu_load_pct"] = float(out) if out else None
    except Exception:
        info["windows_cpu_load_pct"] = None
    return info


def iniciar_contenedores() -> dict:
    info = {}
    for v, cfg in CONTENEDORES.items():
        nombre = cfg["nombre"]
        sh("docker", "rm", "-f", nombre, check=False)
        sh(
            "docker", "run", "-d",
            "--name", nombre,
            "--network", "giragroup_bi_system_default",
            "-e", "BETO_INT8=0",
            "-e", "OMP_NUM_THREADS=1",
            "-e", "MKL_NUM_THREADS=1",
            "-v", f"{cfg['modelo_dir']}:/app/pipeline/semantic/beto_local:ro",
            "giragroup_bi_system-pipeline",
            "sh", "-c", "uvicorn pipeline.semantic.inference_server:app --host 0.0.0.0 --port 8006 --workers 2",
        )
        # Esperar /health desde giragroup_api
        t0 = time.perf_counter()
        health = None
        while time.perf_counter() - t0 < 120:
            res = subprocess.run(
                [
                    "docker", "exec", "giragroup_api", "python", "-c",
                    f"import urllib.request; print(urllib.request.urlopen('http://{nombre}:8006/health', timeout=5).read().decode())",
                ],
                cwd=ROOT, text=True, capture_output=True,
            )
            if res.returncode == 0:
                health = json.loads(res.stdout.strip())
                break
            time.sleep(2)
        if health is None:
            raise RuntimeError(f"Timeout esperando /health de {nombre}")
        actual_sha = sh(
            "docker", "exec", nombre, "sha256sum", "/app/pipeline/semantic/beto_local/model.safetensors"
        ).split()[0]
        if actual_sha != cfg["sha256_esperado"]:
            raise RuntimeError(f"Hash inesperado en {nombre}: {actual_sha} != {cfg['sha256_esperado']}")
        info[v] = {
            "contenedor": nombre,
            "model_safetensors_sha256": actual_sha,
            "health": health,
        }
    return info


def detener_contenedores() -> None:
    for cfg in CONTENEDORES.values():
        sh("docker", "rm", "-f", cfg["nombre"], check=False)


def preparar_arbol() -> dict:
    manifest = json.loads((MED / "f0_lote_manifest.json").read_text(encoding="utf-8"))
    sh("docker", "exec", "giragroup_api", "rm", "-rf", ARBOL, "/tmp/slices_flujo", "/tmp/flujo/uploads/data")
    sh(
        "docker", "exec", "giragroup_api", "mkdir", "-p",
        f"{ARBOL}/backend", f"{ARBOL}/pipeline", f"{ARBOL}/db/seeds", f"{ARBOL}/uploads/data",
        "/tmp/flujo/uploads/data", "/tmp/slices_flujo", "/tmp/flujo/scripts",
    )
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
    return manifest


def obtener_grupos_bandeja(db: str, modelo_version: str) -> list:
    script = (
        "import json, sys; sys.path[:0]=['/tmp/f1_d3b','/tmp/f1_d3b/backend','/tmp/flujo/scripts']; "
        "import simular_revision as rev; cli=rev.cliente(); "
        "_, grupos = rev._todos_los_grupos(cli, {}); "
        "print(json.dumps(grupos, ensure_ascii=False))"
    )
    out = sh(
        "docker", "exec", "-w", ARBOL, "giragroup_api", "env",
        f"DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/{db}",
        f"BETO_MODELO_VERSION={modelo_version}",
        f"PYTHONPATH={ARBOL}:{ARBOL}/backend:/tmp/flujo/scripts",
        "python", "-c", script,
    )
    return json.loads(out.strip())


def comparar_huellas(h1: dict, h2: dict) -> dict:
    tablas_dist = [
        t for t in sorted(set(h1["tablas"]) | set(h2["tablas"]))
        if h1["tablas"].get(t) != h2["tablas"].get(t)
    ]
    return {
        "tablas_distintas": tablas_dist,
        "bandeja_igual": h1.get("bandeja") == h2.get("bandeja"),
        "kpis_iguales": h1.get("kpis") == h2.get("kpis"),
        "identica": (not tablas_dist and h1.get("bandeja") == h2.get("bandeja") and h1.get("kpis") == h2.get("kpis")),
    }


def ejecutar_corrida(v: str, modo: str, r: int, puertos: dict, cont_info: dict, cache_dumps: dict, grupos_v: dict) -> dict:
    cfg = CONTENEDORES[v]
    modelo = cfg["modelo_version"]
    db = f"run_d3b_{v}_{modo}_r{r}"
    lectura, landing = f"/tmp/f1_d3b/{db}/lectura", f"/tmp/f1_d3b/{db}/landing"

    verif_antes = f0.verify()
    sh("docker", "exec", "giragroup_api", "rm", "-rf", f"/tmp/f1_d3b/{db}")
    sh("docker", "exec", "giragroup_api", "mkdir", "-p", lectura, landing)
    sh(SH_EXE, "scripts/aislada_tmpfs.sh", "clon", db)
    sql_tmpfs(db, "TRUNCATE public.cache_indice_beto;")

    if modo == "llena":
        dump_path = cache_dumps[v]
        sh("docker", "cp", dump_path, f"beto_pg_tmpfs:/tmp/d3b_cache_{v}.sql")
        sh(
            "docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", db,
            "-q", "-v", "ON_ERROR_STOP=1", "-f", f"/tmp/d3b_cache_{v}.sql",
        )

    cache_antes = int(sql_tmpfs(db, "SELECT count(*) FROM public.cache_indice_beto;"))
    modelos_antes = sql_tmpfs(db, "SELECT modelo || ':' || count(*) FROM public.cache_indice_beto GROUP BY modelo ORDER BY modelo;")
    if modo == "vacia" and cache_antes != 0:
        raise RuntimeError(f"Cache no vacia en {db}: {cache_antes}")
    if modo == "llena":
        otro = "beto-v2" if v == "v1" else "beto-v1"
        n_otro = int(sql_tmpfs(db, f"SELECT count(*) FROM public.cache_indice_beto WHERE modelo = '{otro}';"))
        if cache_antes == 0 or n_otro > 0:
            raise RuntimeError(f"Cache contaminada antes de {db}: total={cache_antes}, {otro}={n_otro}")

    base_url = f"http://{cfg['nombre']}:8006"
    env = FLAGS_BASE + [
        f"BETO_MODELO_VERSION={modelo}",
        f"DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/{db}",
        "FLUJO_SIN_REVISION=1",
        "CICLO_REUSAR_SLICES=1",
        "CICLO_FILAS_SIN_FECHA=0",
        "CICLO_SLICES=/tmp/slices_flujo",
        f"LECTURA_CACHE_DIR={lectura}",
        f"LANDING_DIR={landing}",
        f"PYTHONPATH={ARBOL}:{ARBOL}/backend:/tmp/flujo/scripts",
        f"BETO_INDICE_URL={base_url}/indice",
        f"BETO_INFERENCE_URL={base_url}/infer",
        f"BETO_INFER_BATCH_URL={base_url}/infer-batch",
    ]

    stem = f"f1_d3b_corrida_{v}_{modo}_r{r}.json"
    sys_antes = carga_sistema()
    inicio = datetime.now(timezone.utc).astimezone().isoformat()
    t0 = time.perf_counter()
    sh("docker", "exec", "-w", ARBOL, "giragroup_api", "env", *env, "python", "/tmp/flujo/scripts/medir_flujo_dataops.py", "/tmp/" + stem)
    pared_s = round(time.perf_counter() - t0, 3)
    sys_despues = carga_sistema()

    sh("docker", "cp", f"giragroup_api:/tmp/{stem}", str(MED / stem))
    sh("docker", "cp", f"giragroup_api:/tmp/{stem}.huella.json", str(MED / f"{stem}.huella.json"))
    sh("docker", "exec", "giragroup_api", "rm", "-rf", f"/tmp/f1_d3b/{db}", f"/tmp/{stem}", f"/tmp/{stem}.huella.json")

    data = json.loads((MED / stem).read_text(encoding="utf-8"))
    data.get("carga", {}).pop("errores", None)
    (MED / stem).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    cache_despues = int(sql_tmpfs(db, "SELECT count(*) FROM public.cache_indice_beto;"))
    modelos_despues = sql_tmpfs(db, "SELECT modelo || ':' || count(*) FROM public.cache_indice_beto GROUP BY modelo ORDER BY modelo;")
    otro = "beto-v2" if v == "v1" else "beto-v1"
    n_otro_despues = int(sql_tmpfs(db, f"SELECT count(*) FROM public.cache_indice_beto WHERE modelo = '{otro}';"))
    if n_otro_despues > 0:
        raise RuntimeError(f"Cache contaminada despues de {db}: {otro}={n_otro_despues}")

    if modo == "vacia" and v not in cache_dumps:
        dump_local = str(ROOT / f"output/f1/d3b_cache_{v}.sql")
        sh("docker", "exec", "beto_pg_tmpfs", "pg_dump", "-U", "giragroup_user", "-d", db, "--table=public.cache_indice_beto", "--data-only", "-f", f"/tmp/d3b_cache_{v}.sql")
        sh("docker", "cp", f"beto_pg_tmpfs:/tmp/d3b_cache_{v}.sql", dump_local)
        cache_dumps[v] = dump_local

    if v not in grupos_v:
        grupos_v[v] = obtener_grupos_bandeja(db, modelo)

    drop_db_tmpfs(db)
    verif_despues = f0.verify()

    meta = {
        "fecha_inicio": inicio,
        "fecha_fin": datetime.now(timezone.utc).astimezone().isoformat(),
        "version": v,
        "modelo_version": modelo,
        "modo_cache": modo,
        "repeticion": r,
        "base_tmpfs": db,
        "contenedor_indice": cont_info[v],
        "puertos": puertos,
        "lote_sha256_antes": verif_antes["sha256"],
        "lote_sha256_despues": verif_despues["sha256"],
        "cache_indice_beto_antes": cache_antes,
        "cache_indice_beto_despues": cache_despues,
        "modelos_en_cache_antes": modelos_antes.splitlines(),
        "modelos_en_cache_despues": modelos_despues.splitlines(),
        "pared_s": pared_s,
        "maquina_s": data["total"]["tiempo_maquina_s"],
        "sistema_antes": sys_antes,
        "sistema_despues": sys_despues,
    }
    (MED / f"{stem}.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] {stem}: maquina={meta['maquina_s']}s pared={pared_s}s cache={cache_antes}->{cache_despues}")
    return {"stem": stem, "data": data, "meta": meta}


def explicar_182_680() -> dict:
    rows = list(csv.DictReader((MED / "f1_r2_bandeja_diff.csv").open(encoding="utf-8")))
    altas = [r for r in rows if r["sentido"] == "alta"]
    bajas = [r for r in rows if r["sentido"] == "baja"]
    assert len(altas) == 569 and len(bajas) == 71, f"Conteos inesperados: +{len(altas)} / -{len(bajas)}"
    assert 182 + len(altas) - len(bajas) == 680

    por_motivo_alta = dict(Counter(r["motivo"] for r in altas).most_common())
    por_motivo_baja = dict(Counter(r["motivo"] for r in bajas).most_common())
    por_archivo_alta = [{"archivo": a, "altas": n} for a, n in Counter(r["archivo"] for r in altas).most_common(5)]
    por_archivo_baja = [{"archivo": a, "bajas": n} for a, n in Counter(r["archivo"] for r in bajas).most_common(5)]

    grupos_alta = Counter((r["grupo"], r["accion_grupo"]) for r in altas)
    grupos_nuevos = [
        {"grupo": g, "accion_grupo": acc, "casos_alta": n}
        for (g, acc), n in grupos_alta.most_common()
    ]
    return {
        "fuente": "docs/mediciones/f1_r2_bandeja_diff.csv",
        "bandeja_v1": {"casos": 182, "grupos": 12},
        "bandeja_v2": {"casos": 680, "grupos": 19},
        "cuadre": {"altas": len(altas), "bajas": len(bajas), "neto": len(altas) - len(bajas), "formula": "182 + 569 - 71 = 680"},
        "altas_por_motivo": por_motivo_alta,
        "bajas_por_motivo": por_motivo_baja,
        "top5_archivos_altas": por_archivo_alta,
        "top5_archivos_bajas": por_archivo_baja,
        "grupos_en_altas": grupos_nuevos,
    }


def calcular_klm_version(grupos: list) -> dict:
    eventos = [{"accion": g.get("accion_grupo") or "MANUAL", "casos": int(g["n"])} for g in grupos]
    total_con_w, desglose_con_w = afr.klm(eventos, True)
    total_sin_w, desglose_sin_w = afr.klm(eventos, False)
    return {
        "etiqueta": "klm_estimado_d3b",
        "grupos_total": len(grupos),
        "casos_total": sum(e["casos"] for e in eventos),
        "regla_mapeo": "Cada grupo de /api/v1/dataops/review-tray/grupos se mapea directamente por g['accion_grupo'] (APROBAR / MANUAL / CORREGIR_FECHA / MAPEAR_ESTADO) con casos = g['n'].",
        "eventos": [
            {"grupo": g["clave"][:24], "titulo": g.get("titulo"), "accion": g.get("accion_grupo") or "MANUAL", "casos": int(g["n"])}
            for g in grupos
        ],
        "con_espera_W_10s": {"total_s": total_con_w, "desglose_s": desglose_con_w},
        "sin_espera_W_0s": {"total_s": total_sin_w, "desglose_s": desglose_sin_w},
    }


def resumen_estadistico(vals: list) -> dict:
    return {
        "n": len(vals),
        "valores": [round(x, 3) for x in vals],
        "media_s": round(st.mean(vals), 3),
        "de_s": round(st.stdev(vals), 3) if len(vals) > 1 else 0.0,
    }


def main() -> None:
    puertos = verificar_puertos()
    verif_inicial = f0.verify()
    preparar_arbol()
    cont_info = iniciar_contenedores()

    corridas = []
    cache_dumps = {}
    grupos_v = {}
    try:
        for r in (1, 2, 3):
            for modo in ("vacia", "llena"):
                for v in ("v1", "v2"):
                    corridas.append(ejecutar_corrida(v, modo, r, puertos, cont_info, cache_dumps, grupos_v))
    finally:
        detener_contenedores()

    verif_final = f0.verify()
    if verif_inicial["sha256"] != verif_final["sha256"]:
        raise RuntimeError("El sha256 del lote cambio durante D-C!")

    # Consistencia interna y contra referencias
    ref_huellas = {
        "v1": json.loads((MED / "f1_off.json.huella.json").read_text(encoding="utf-8")),
        "v2": json.loads((MED / "f1_validacion_vacia_r1.json.huella.json").read_text(encoding="utf-8")),
    }
    consistencia = {}
    resumen_v = {}
    klm_out = {
        "tarea": "D-C",
        "etiqueta": "klm_estimado_d3b",
        "fuente_klm": "scripts/agregar_flujo_repetido.py::klm",
        "parametros": {"K": afr.K, "P": afr.P, "H": afr.H, "M": afr.M, "B": afr.B, "W_DESHACER": afr.W_DESHACER, "PAGINA": afr.PAGINA},
        "versiones": {},
    }

    for v in ("v1", "v2"):
        cv = [c for c in corridas if c["meta"]["version"] == v]
        huellas = [json.loads((MED / f"{c['stem']}.huella.json").read_text(encoding="utf-8")) for c in cv]
        internas = [comparar_huellas(huellas[0], h) for h in huellas[1:]]
        vs_ref = comparar_huellas(huellas[0], ref_huellas[v])
        consistencia[v] = {
            "6_corridas_identicas_entre_si": all(x["identica"] for x in internas),
            "contra_referencia": "f1_off.json.huella.json" if v == "v1" else "f1_validacion_vacia_r1.json.huella.json",
            "identica_a_referencia": vs_ref["identica"],
            "detalle_referencia": vs_ref,
        }

        vacias = [c for c in cv if c["meta"]["modo_cache"] == "vacia"]
        llenas = [c for c in cv if c["meta"]["modo_cache"] == "llena"]
        maq_vacia = resumen_estadistico([c["meta"]["maquina_s"] for c in vacias])
        par_vacia = resumen_estadistico([c["meta"]["pared_s"] for c in vacias])
        maq_llena = resumen_estadistico([c["meta"]["maquina_s"] for c in llenas])
        par_llena = resumen_estadistico([c["meta"]["pared_s"] for c in llenas])

        klm_v = calcular_klm_version(grupos_v[v])
        klm_v["tiempo_maquina_vacia_media_s"] = maq_vacia["media_s"]
        klm_v["tiempo_total_con_W_10s"] = round(maq_vacia["media_s"] + klm_v["con_espera_W_10s"]["total_s"], 1)
        klm_v["tiempo_total_sin_W_0s"] = round(maq_vacia["media_s"] + klm_v["sin_espera_W_0s"]["total_s"], 1)
        klm_out["versiones"][v] = klm_v

        h0 = huellas[0]
        d0 = cv[0]["data"]
        resumen_v[v] = {
            "modelo_version": CONTENEDORES[v]["modelo_version"],
            "huella_sha256": sha256_archivo(MED / f"{cv[0]['stem']}.huella.json"),
            "lineas_leidas_beto": d0["etapas_s"].get("lineas_leidas_beto"),
            "tablas_dw_staging": h0["tablas"],
            "bandeja": h0["bandeja"],
            "kpis": h0["kpis"],
            "tiempos": {
                "maquina_vacia": maq_vacia,
                "pared_vacia": par_vacia,
                "maquina_llena": maq_llena,
                "pared_llena": par_llena,
            },
            "klm_estimado_d3b": {
                "con_W_10s": klm_v["con_espera_W_10s"]["total_s"],
                "sin_W_0s": klm_v["sin_espera_W_0s"]["total_s"],
                "tiempo_total_con_W_10s": klm_v["tiempo_total_con_W_10s"],
                "tiempo_total_sin_W_0s": klm_v["tiempo_total_sin_W_0s"],
            },
        }

    (MED / "f1_d3b_klm.json").write_text(json.dumps(klm_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    operativo = {
        "tarea": "D-C",
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "lote_sha256_antes": verif_inicial["sha256"],
        "lote_sha256_despues": verif_final["sha256"],
        "flags": FLAGS_BASE,
        "consistencia": consistencia,
        "versiones": resumen_v,
        "explicacion_bandeja_182_a_680": explicar_182_680(),
    }
    (MED / "f1_d3b_operativo.json").write_text(json.dumps(operativo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("[OK] D-C completo -> f1_d3b_operativo.json y f1_d3b_klm.json")


if __name__ == "__main__":
    main()
