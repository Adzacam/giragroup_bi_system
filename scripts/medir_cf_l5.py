"""CF-L5, comparación de DataOps sobre PostgreSQL tmpfs y red Docker propia.

  python scripts/medir_cf_l5.py smoke     # comprobación técnica sin lote
  python scripts/medir_cf_l5.py preparar  # tras completar CF-L1
  python scripts/medir_cf_l5.py vigente --confirmar-ventana-exclusiva
  python scripts/medir_cf_l5.py candidato --confirmar-ventana-exclusiva --modelo <ruta> \
      --modelo-version beto-v3 --revision <commit-CF-L4> --calidad <dictamen-CF-L3>
  python scripts/medir_cf_l5.py agregar --calidad <dictamen-CF-L3>
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import tarfile
import time
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import agregar_flujo_repetido as klm
from f0_mantener_activo import ExecutionState
import medir_f0 as f0


ROOT = f0.ROOT
PRIVATE = ROOT / "output/backups/cf_l5"
MED = ROOT / "docs/mediciones"
DB_CONTAINER = "beto_pg_tmpfs"
DB_USER = "giragroup_user"
NETWORK = "cf_l5_interna"
PIPELINE = "cf_l5_pipeline"
RUNNER = "cf_l5_runner"
TEMPLATE_DW, TEMPLATE_CAT = "cf_l5_base_dw", "cf_l5_base_catalog"
BASE_REVISION = "30b05df7c3d5c8680886a8a0d14a03994012c1a4"
SOURCES = ("backend", "pipeline", "db", "config")
SUPPORT = ("medir_flujo_dataops.py", "medir_ciclo_mensual.py", "simular_revision.py", "huella_dw.py")
CACHES = ("cache_indice_beto", "cache_beto_entidades")
FLAGS = {
    "BETO_CASCADA_FINAL": "1", "BETO_ACUERDO_QC": "1", "BETO_SUGERENCIA_HITL": "1",
    "BETO_VENTANA": "0", "BETO_VENTANA_STRIDE": "32", "BETO_ACUERDO_OMITIR_CI_EXACTA": "1",
    "BETO_CACHE_PERSISTENTE": "1", "BETO_INT8": "1", "HF_HUB_OFFLINE": "1",
}
RESET_DW = (
    "cache_indice_beto", "stg_entidad_no_resuelta", "staging_registros_crudos", "log_pipeline_ingesta",
    "log_inconsistencias", "log_auditoria_nlp", "dim_origen_documental", "carga_fila_origen", "lote",
    "dataops_tarea",
)
HOST_GUARD = """
import json, socket, sys
from sqlalchemy import text
from core.database import SessionLocal, CatalogSessionLocal
for live in ('db', 'catalog_db', 'giragroup_db', 'giragroup_catalog_db', 'giragroup_pipeline'):
    try:
        socket.getaddrinfo(live, None)
    except socket.gaierror:
        continue
    raise RuntimeError('Nombre de Compose resoluble desde la red de medición: ' + live)
observados = []
for fabrica in (SessionLocal, CatalogSessionLocal):
    with fabrica() as sesion:
        observados.append(sesion.execute(text('select current_database()')).scalar_one())
if observados != sys.argv[1:]:
    raise RuntimeError('Los destinos efectivos no coinciden con los clones previstos')
print(json.dumps(observados))
"""
WARMUP = """
import json, urllib.request
base = 'http://pipeline:8006'
with urllib.request.urlopen(base + '/health', timeout=180) as r:
    assert json.load(r)['engine'] == 'BETO_PYTORCH_REAL'
data = json.dumps({'textos': ['Programa de prueba institucional.'] * 16,
                   'ventana': False, 'stride': 32, 'max_length': 128}).encode()
for _ in range(4):
    req = urllib.request.Request(base + '/infer-batch', data, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        res = json.load(r)
        assert r.status == 200 and res['status'] == 'success' and len(res['resultados']) == 16
"""


def call(*args, env=None, check=True):
    return subprocess.run(args, env=env, check=check, capture_output=True, text=True, encoding="utf-8", errors="replace")


def docker(*args, **kwargs):
    return call("docker", *args, **kwargs).stdout.strip()


def sql(db, query):
    return docker("exec", DB_CONTAINER, "psql", "-U", DB_USER, "-d", db,
                  "-v", "ON_ERROR_STOP=1", "-qAt", "-c", query)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def database_exists(nombre):
    return sql("postgres", f"SELECT 1 FROM pg_database WHERE datname='{nombre}'") == "1"


def clone(nombre, template):
    if not re.fullmatch(r"cf_l5_[a-z0-9_]+", nombre) or not re.fullmatch(r"[a-z0-9_]+", template):
        raise ValueError("Nombre de base fuera de CF-L5")
    sql("postgres", f"CREATE DATABASE {nombre} TEMPLATE {template}")


def drop(nombre):
    if not re.fullmatch(r"cf_l5_(?:smoke|ej|seed)_[a-z0-9_]+", nombre):
        raise ValueError("Solo se eliminan los clones temporales de la corrida")
    sql("postgres", f"DROP DATABASE {nombre}")


@contextmanager
def trial_databases(prefix):
    names = []
    suffix = uuid4().hex[:8]
    try:
        for name, template in (("dw", TEMPLATE_DW), ("cat", TEMPLATE_CAT)):
            db = f"cf_l5_ej_{prefix}_{name}_{suffix}"
            clone(db, template)
            names.append(db)
        yield names
    finally:
        for db in names:
            drop(db)


def table_exists(db, table):
    return sql(db, f"SELECT to_regclass('public.{table}') IS NOT NULL") == "t"


def clear_caches(dw, cat):
    for db in (dw, cat):
        for tabla in CACHES:
            if table_exists(db, tabla):
                sql(db, f"TRUNCATE TABLE public.{tabla}")


def caches_empty(cache):
    return all(not v or v.startswith("0:") for v in cache.values())


def table_fingerprint(db, table, exclude_time=False):
    row = "to_jsonb(t) - 'creado_en'" if exclude_time else "to_jsonb(t)"
    return sql(db, f"SELECT concat(count(*), ':', md5(coalesce(string_agg(md5(({row})::text), ''"
                   f" ORDER BY md5(({row})::text)), ''))) FROM public.{table} t")


def cache_state(db):
    return {t: table_fingerprint(db, t, exclude_time=True) if table_exists(db, t) else None for t in CACHES}


def hydrate_cache(db, seed):
    for tabla in CACHES:
        if not table_exists(seed, tabla):
            continue
        params = ("docker", "exec", DB_CONTAINER, "pg_dump", "-U", DB_USER, "-d", seed, "--no-owner",
                  "--no-privileges", "--clean", "--if-exists", "-t", f"public.{tabla}")
        with subprocess.Popen(params, stdout=subprocess.PIPE) as export:
            subprocess.run(("docker", "exec", "-i", DB_CONTAINER, "psql", "-U", DB_USER, "-d", db,
                            "-q", "-v", "ON_ERROR_STOP=1"), stdin=export.stdout, check=True)
            if export.wait():
                raise RuntimeError("Falló la exportación de caché tmpfs")
    if cache_state(db) != cache_state(seed):
        raise RuntimeError("La restauración de caché difiere de la precarga")


def catalog_fingerprint(db):
    tablas = sql(db, "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                     "AND tablename NOT LIKE 'cache_%' ORDER BY tablename").splitlines()
    content = {t: table_fingerprint(db, t) for t in tablas if re.fullmatch(r"[a-z0-9_]+", t)}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def controls(dw, catalog):
    catalog_sha = catalog_fingerprint(catalog)
    return {
        "catalogo_sha256": catalog_sha,
        "cat_modulo_local": table_fingerprint(dw, "cat_modulo"),
        "pk_modulo": set(sql(dw, "SELECT id_modulo FROM public.dim_modulo").splitlines()),
        "fk_huerfanas": int(sql(dw, "SELECT count(*) FROM dim_modulo d WHERE d.id_cat_modulo IS NOT NULL "
                                   "AND NOT EXISTS (SELECT 1 FROM cat_modulo c WHERE c.id_modulo = d.id_cat_modulo)")),
        "pos_invalidos": int(sql(dw, "SELECT count(*) FROM dim_modulo WHERE upper(trim(pos_code)) IN ('POS--','UNDEFINED')")),
        "mod_gen": int(sql(dw, "SELECT count(*) FROM dim_modulo WHERE pos_code LIKE 'MOD-GEN%'")),
        "programas_con_pos": int(sql(dw, "SELECT count(*) FROM dim_modulo WHERE programa ~* '\\mPOS[[:space:]:-]*[0-9]+\\M'")),
        "tablas_dw": int(sql(dw, "SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('public','bi') AND table_type='BASE TABLE'")),
        "vistas_bi": int(sql(dw, "SELECT count(*) FROM information_schema.views WHERE table_schema='bi'")),
    }


def validate_tmpfs():
    info = read_inspect(DB_CONTAINER)
    if "/var/lib/postgresql/data" not in info["HostConfig"]["Tmpfs"] or not info["State"]["Running"]:
        raise RuntimeError("PostgreSQL de medición ausente o fuera de tmpfs")
    return info


def read_inspect(name):
    return json.loads(docker("inspect", name))[0]


def isolated_network(db_info):
    exists = call("docker", "network", "inspect", NETWORK, check=False)
    if exists.returncode:
        docker("network", "create", "--driver", "bridge", "--internal", NETWORK)
    if NETWORK not in db_info["NetworkSettings"]["Networks"]:
        docker("network", "connect", NETWORK, DB_CONTAINER)
    net = json.loads(docker("network", "inspect", NETWORK))[0]
    if not net["Internal"] or {x["Name"] for x in net["Containers"].values()} != {DB_CONTAINER}:
        raise RuntimeError("La red CF-L5 debe ser interna y estar libre de otros servicios")


def prepare_templates(dw_source, cat_source):
    if (dw_source, cat_source) != ("cf_l1_dw", "cf_l1_catalog"):
        raise ValueError("Las plantillas definitivas se clonan de las bases saneadas CF-L1")
    if database_exists(TEMPLATE_DW) or database_exists(TEMPLATE_CAT):
        raise RuntimeError("Ya hay plantillas CF-L5. La comparación exige una única pareja de origen.")
    clone(TEMPLATE_DW, dw_source)
    clone(TEMPLATE_CAT, cat_source)
    hechos = sql(TEMPLATE_DW, "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'fact_%'").splitlines()
    vaciar = [t for t in (*hechos, *RESET_DW) if re.fullmatch(r"[a-z0-9_]+", t) and table_exists(TEMPLATE_DW, t)]
    sql(TEMPLATE_DW, "TRUNCATE " + ", ".join(f"public.{t}" for t in vaciar) + " RESTART IDENTITY CASCADE")
    clear_caches(TEMPLATE_DW, TEMPLATE_CAT)
    conteo = {t: int(sql(TEMPLATE_DW, f"SELECT count(*) FROM public.{t}")) for t in vaciar}
    if any(conteo.values()):
        raise RuntimeError("La plantilla conserva datos de etapas/facts tras la restauración")
    state = controls(TEMPLATE_DW, TEMPLATE_CAT)
    state["pk_modulo"] = len(state["pk_modulo"])
    f0.write(PRIVATE / "plantillas.json", {"origen": [dw_source, cat_source], "destino": [TEMPLATE_DW, TEMPLATE_CAT],
                                           "conteo_fact_y_etapa": conteo, "controles": state})
    print(json.dumps(state, ensure_ascii=False), flush=True)


def stage_tree(dest, revision, worktree):
    dest.mkdir()
    archive = dest.parent / "arbol.tar"
    call("git", "archive", "--format=tar", "-o", str(archive), revision, *SOURCES)
    with tarfile.open(archive) as tar:
        tar.extractall(dest, filter="data")
    archive.unlink()
    if worktree:
        # Los archivos rastreados toman su versión actual. Los únicos nuevos se pasan explícitamente.
        paths = call("git", "diff", "--name-only", revision, "--", *SOURCES).stdout.splitlines() + worktree
        for relative in sorted(set(paths)):
            source = (ROOT / relative).resolve()
            if not source.is_relative_to(ROOT) or Path(relative).parts[0] not in SOURCES:
                raise ValueError(f"Ruta fuera del árbol CF-L5: {relative}")
            target = dest / relative
            if source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            else:
                target.unlink(missing_ok=True)
    for relative in ("output", "docs/evidencias", "uploads/data", "scripts", "pipeline/semantic/beto_local"):
        (dest / relative).mkdir(parents=True, exist_ok=True)
    for script in SUPPORT:
        shutil.copyfile(ROOT / "scripts" / script, dest / "scripts" / script)
    return tree_fingerprint(dest)


def tree_fingerprint(tree):
    archivos = (p for p in tree.rglob("*") if p.is_file())
    return hashlib.sha256(f0.canonical([{"ruta": p.relative_to(tree).as_posix(), "sha256": f0.digest(p)}
                                        for p in archivos])).hexdigest()


def bind(path, target):
    return ("--mount", f"type=bind,source={path.resolve()},target={target},readonly")


@contextmanager
def environment(args, tree, dw, cat):
    api_img = read_inspect("giragroup_api")["Image"]
    pipeline_img = read_inspect("giragroup_pipeline")["Image"]
    verify = f0.verify(base=f0.PRIVATE)
    env = os.environ.copy()
    password = docker("exec", DB_CONTAINER, "printenv", "POSTGRES_PASSWORD")
    prefix = f"postgresql://{DB_USER}:{quote(password, safe='')}@{DB_CONTAINER}:5432/"
    env.update(FLAGS, DATABASE_URL=prefix + dw, CATALOG_DATABASE_URL=prefix + cat,
               BETO_MODELO_VERSION=args.modelo_version, BETO_WORKERS=str(args.workers),
               TORCH_NUM_THREADS=str(args.torch_threads), PYTHONPATH="/cf:/cf/backend:/cf/scripts",
               PYTHONHASHSEED="0", CICLO_REUSAR_SLICES="1", CICLO_FILAS_SIN_FECHA="0",
               CICLO_SLICES="/cf_slices", FLUJO_SIN_REVISION="1", FLUJO_ESPERAR_PREPARACION="1", LECTURA_CACHE_DIR="/tmp/cache_lectura",
               LANDING_DIR="/tmp/landing_cf_l5")
    all_names = set(FLAGS) | {"DATABASE_URL", "CATALOG_DATABASE_URL", "BETO_MODELO_VERSION", "BETO_WORKERS",
                             "TORCH_NUM_THREADS", "PYTHONPATH", "PYTHONHASHSEED", "CICLO_REUSAR_SLICES",
                             "CICLO_FILAS_SIN_FECHA", "CICLO_SLICES", "FLUJO_SIN_REVISION", "FLUJO_ESPERAR_PREPARACION",
                             "LECTURA_CACHE_DIR", "LANDING_DIR"}
    common = ("-d", "--rm", "--network", NETWORK, "--workdir", "/cf", *bind(tree, "/cf"),
              *bind(args.modelo, "/cf/pipeline/semantic/beto_local"),
              *(part for k in sorted(all_names) for part in ("-e", k)))
    model_command = ("uvicorn", "pipeline.semantic.inference_server:app", "--host", "0.0.0.0",
                     "--port", "8006", "--workers", str(args.workers))
    created = []
    try:
        docker("run", "--name", PIPELINE, "--network-alias", "pipeline", *common, pipeline_img, *model_command, env=env)
        created.append(PIPELINE)
        docker("run", "--name", RUNNER, *common, *bind(f0.PRIVATE / "originales", "/cf/uploads/data"),
               *bind(f0.PRIVATE / "slices", "/cf_slices"), api_img, "sleep", "infinity", env=env)
        created.append(RUNNER)
        effective = json.loads(docker("exec", RUNNER, "python", "-c", HOST_GUARD, dw, cat))
        if any(set(read_inspect(name)["NetworkSettings"]["Networks"]) != {NETWORK} for name in created):
            raise RuntimeError("Un ejecutor quedó conectado a una red ajena")
        end = time.monotonic() + 120
        while call("docker", "exec", RUNNER, "python", "-c",
                   "import socket; socket.create_connection(('pipeline',8006),1)", check=False).returncode != 0:
            if time.monotonic() >= end:
                raise RuntimeError("El servicio BETO aislado no abrió su puerto")
            time.sleep(2)
        calentamiento = call("docker", "exec", RUNNER, "python", "-c", WARMUP, check=False)
        if calentamiento.returncode:
            raise RuntimeError(calentamiento.stderr.strip())
        logs = call("docker", "logs", PIPELINE)
        if "Modelo NER cuantizado a int8" not in logs.stderr + logs.stdout:
            raise RuntimeError("El servicio BETO no confirmó la cuantización INT8")
        yield {"destinos": effective, "red": NETWORK, "api_imagen": api_img, "pipeline_imagen": pipeline_img,
               "flags": FLAGS, "workers": args.workers, "torch_threads": args.torch_threads,
               "modelo_version": args.modelo_version, "modelo_sha256": f0.digest(args.modelo / "model.safetensors"),
               "precalentamiento": {"peticiones": 4, "textos_sinteticos_por_peticion": 16, "max_length": 128},
               "lote_sha256": verify["sha256"],
               "secuencia": ["LECTURA_BETO", "PREPARACION_REVISION", "CONSOLIDACION"],
               "consolidacion_api": "POST confirm-dw-insert en_segundo_plano=true; espera por GET tarea"}
    finally:
        for name in reversed(created):
            docker("rm", "-f", name, check=False)


def klm_times(footprint):
    espera = read(MED / "f5c_klm.json")["W_medido_p95_s"]
    grupos = [{"accion": accion, "casos": n} for _, accion, n in footprint["bandeja"].pop("firma")]
    report = {}
    backup = klm.W_DESHACER
    try:
        for w in (espera, 0, 10):
            klm.W_DESHACER = w
            seconds, breakdown = klm.klm(grupos, True)
            report[str(w)] = {"W_s": w, "tiempo_humano_estimado_s": seconds, "desglose_s": breakdown}
    finally:
        klm.W_DESHACER = backup
    return report, espera


def measure(args, tree, dw, cat, target):
    antes = controls(dw, cat)
    caches_antes = {"dw": cache_state(dw), "catalogo": cache_state(cat)}
    with environment(args, tree, dw, cat) as runtime:
        time.sleep(30)
        recursos = docker("stats", "--no-stream", "--format", "{{json .}}", RUNNER, PIPELINE, DB_CONTAINER)
        inicio = f0.now()
        start = time.perf_counter()
        salida = call("docker", "exec", RUNNER, "python", "/cf/scripts/medir_flujo_dataops.py", "/tmp/medicion.json", check=False)
        elapsed = round(time.perf_counter() - start, 2)
        (target / "ejecucion_privada.log").write_text(salida.stdout + salida.stderr, encoding="utf-8")
        if salida.returncode:
            raise RuntimeError("Falló el flujo DataOps. El detalle queda en la carpeta privada de la corrida.")
        result = json.loads(docker("exec", RUNNER, "cat", "/tmp/medicion.json"))
        footprint = json.loads(docker("exec", RUNNER, "cat", "/tmp/medicion.json.huella.json"))
        f0.valid_result(result)
        if sql(dw, "SELECT estado FROM dataops_tarea WHERE tipo='LECTURA_BETO' ORDER BY id DESC LIMIT 1") != "COMPLETADA":
            raise RuntimeError("La lectura BETO no terminó correctamente")
        if f0.windows_sleep_events(inicio, f0.now())["suspension_detectada"]:
            raise RuntimeError("Corrida afectada por suspensión del equipo")
    despues = controls(dw, cat)
    pid_anteriores, pid_posteriores = antes.pop("pk_modulo"), despues.pop("pk_modulo")
    delta = {k: despues[k] - antes[k] for k in ("fk_huerfanas", "pos_invalidos", "mod_gen", "programas_con_pos")}
    delta.update({"pk_modulo_eliminadas": len(pid_anteriores - pid_posteriores),
                  "pk_modulo_nuevas": len(pid_posteriores - pid_anteriores),
                  "cat_modulo_local_mutado": antes["cat_modulo_local"] != despues["cat_modulo_local"],
                  "catalogo_mutado": antes["catalogo_sha256"] != despues["catalogo_sha256"]})
    tiempos_klm, espera = klm_times(footprint)
    etapas = result["etapas_s"]
    maquina = result["total"]["tiempo_maquina_s"]
    total = round(maquina + tiempos_klm[str(espera)]["tiempo_humano_estimado_s"], 2)
    return {"runtime": runtime, "etapas_s": etapas, "maquina_s": maquina,
            "recursos_antes": [json.loads(line) for line in recursos.splitlines()],
            "total_con_klm_s": total, "klm": tiempos_klm, "W_principal_s": espera, "duracion_invocacion_s": elapsed,
            "bandeja": footprint["bandeja"], "huella_tablas": {k: {"filas": v.get("filas"), "md5": v.get("md5")}
                                                               for k, v in footprint["tablas"].items()},
            "controles_antes": antes, "controles_despues": despues, "variaciones": delta,
            "caches_iniciales": caches_antes, "caches_finales": {"dw": cache_state(dw), "catalogo": cache_state(cat)},
            "conteo_entrada": result["carga"]["registros_detectados"]}


def warm_cache(args, tree, work):
    arm = args.accion
    if not (database_exists(TEMPLATE_DW) and database_exists(TEMPLATE_CAT)):
        raise RuntimeError("Faltan las plantillas comunes CF-L5. Ejecute preparar tras CF-L1.")
    seed_dw, seed_cat = f"cf_l5_seed_{arm}_dw", f"cf_l5_seed_{arm}_cat"
    target = work / "precalentar_cache"
    target.mkdir(exist_ok=True)
    seed_path = target / "resumen.json"
    if seed_path.is_file() and all(database_exists(n) for n in (seed_dw, seed_cat)):
        seed = read(seed_path)
        if seed["caches_finales"] != {"dw": cache_state(seed_dw), "catalogo": cache_state(seed_cat)}:
            raise RuntimeError("Las bases de precarga cambiaron desde su medición privada")
    else:
        for db, template in ((seed_dw, TEMPLATE_DW), (seed_cat, TEMPLATE_CAT)):
            if database_exists(db):
                drop(db)
            clone(db, template)
        print(f"{arm}: iniciando precarga para caché llena, fuera de la serie", flush=True)
        seed = measure(args, tree, seed_dw, seed_cat, target)
        f0.write(seed_path, seed)
        print(f"{arm}: precarga completada ({seed['maquina_s']} s)", flush=True)
    if caches_empty(seed["caches_finales"]["catalogo"]):
        raise RuntimeError("La precarga no materializó la caché persistente de entidades")
    return seed_dw, seed_cat


def series(args, tree, work):
    arm = args.accion
    seed_dw, seed_cat = warm_cache(args, tree, work)
    results = {}
    for modo in ("fria", "llena"):
        results[modo] = []
        for i in range(1, 4):
            target = work / f"{modo}_{i}"
            target.mkdir(exist_ok=True)
            result_path = target / "resumen.json"
            if result_path.is_file():
                obs = read(result_path)
            else:
                with trial_databases(f"{arm}_{modo}_{i}") as (dw, cat):
                    if modo == "llena":
                        hydrate_cache(dw, seed_dw)
                        hydrate_cache(cat, seed_cat)
                    elif not all(caches_empty(cache_state(db)) for db in (dw, cat)):
                        raise RuntimeError("Una clonación de caché fría contiene entradas")
                    print(f"{arm}/{modo}/{i}: iniciando", flush=True)
                    obs = measure(args, tree, dw, cat, target)
                    obs.update({"condicion": modo, "corrida": i})
                    f0.write(result_path, obs)
            results[modo].append(obs)
            print(f"{arm}/{modo}/{i} completada ({obs['maquina_s']} s)", flush=True)
    drop(seed_dw)
    drop(seed_cat)
    return results


def stat(values):
    return {"media": round(statistics.mean(values), 2), "desviacion_muestral": round(statistics.stdev(values), 2)}


def read_quality(path):
    data = read(path)
    if not data["aprobado_calidad_cf_l3"]:
        raise ValueError("El dictamen no aprobó el candidato INT8 de CF-L3")
    return {
        "evidencia": Path(path).name,
        "sha256_evidencia": f0.digest(path),
        "vigente": data["vigente"]["resultados"]["int8"],
        "candidato": data["candidato"]["resultados"]["int8"],
        "sha256_modelos": {a: data[a]["sha256"]["model.safetensors"] for a in ("vigente", "candidato")},
    }


def aggregate(calidad):
    arms = {arm: read(PRIVATE / arm / "serie.json") for arm in ("vigente", "candidato")}
    results = {a: r["corridas"] for a, r in arms.items()}
    rows = [{"configuracion": a, **{k: r[k] for k in ("condicion", "corrida", "maquina_s", "total_con_klm_s")},
             **r["etapas_s"]} for a, modes in results.items() for runs in modes.values() for r in runs]
    runs = [r for modes in results.values() for observations in modes.values() for r in observations]
    invariantes = ("lote_sha256", "api_imagen", "pipeline_imagen", "workers", "torch_threads")
    estados = {(tuple(r["runtime"][k] for k in invariantes), r["controles_antes"]["catalogo_sha256"],
                r["controles_antes"]["cat_modulo_local"], r["conteo_entrada"]) for r in runs}
    if len(runs) != 12 or len(estados) != 1:
        raise RuntimeError("Las doce corridas deben compartir lote, catálogo, módulos, entradas e imágenes/configuración Docker")
    for arm, modes in results.items():
        if any(r["runtime"]["modelo_sha256"] != calidad["sha256_modelos"][arm] for observations in modes.values() for r in observations):
            raise RuntimeError("El modelo medido no coincide con el dictamen RNF-04")
    summary = {}
    for arm, modes in results.items():
        summary[arm] = {}
        for mode, observations in modes.items():
            methods = set.intersection(*(set(r["etapas_s"]) for r in observations))
            times = {k: stat([r["etapas_s"][k] for r in observations]) for k in sorted(methods) if k.endswith("_s")}
            total = stat([r["total_con_klm_s"] for r in observations])
            summary[arm][mode] = {"n": len(observations), "por_etapa_s": times, "total_con_klm_s": total,
                                  "maquina_s": stat([r["maquina_s"] for r in observations]),
                                  "cumple_15_min": total["media"] < 900, "cumple_20_min": total["media"] < 1200}
    evidence = {"tarea": "CF-L5", "protocolo_klm": "f5c_klm.json, W p95 congelado y sensibilidad 0/10 s",
                "rnf04": calidad,
                "fuentes": {"lote": "f0_lote_manifest.json", "medicion": "scripts/medir_flujo_dataops.py"},
                "resumen": summary, "series": arms}
    f0.write(MED / "cf_l5_rnf03_rnf04.json", evidence)
    campos = list(dict.fromkeys(key for row in rows for key in row))
    with (MED / "cf_l5_rnf03_rnf04.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=campos)
        writer.writeheader()
        writer.writerows(rows)


def parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=("smoke", "preparar", "vigente", "candidato", "agregar"))
    ap.add_argument("--modelo", type=Path, default=ROOT / "pipeline/semantic/beto_local")
    ap.add_argument("--modelo-version", default="beto-v2")
    ap.add_argument("--calidad", type=Path, help="Evidencia del modelo aprobado en CF-L3")
    ap.add_argument("--revision", default=BASE_REVISION)
    ap.add_argument("--cambios-locales", nargs="+", default=[], help="Rutas nuevas CF incluidas junto a los cambios rastreados")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--torch-threads", type=int, default=4)
    ap.add_argument("--confirmar-ventana-exclusiva", action="store_true")
    return ap


def stage_run(args):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    work = PRIVATE / (f"smoke_{timestamp}" if args.accion == "smoke" else args.accion)
    work.mkdir(exist_ok=True)
    tree = work / "arbol"
    manifest_path = work / "plan.json"
    config = {
        "accion": args.accion, "revision": args.revision, "cambios_locales": args.cambios_locales,
        "modelo_sha256": f0.digest(args.modelo / "model.safetensors"), "modelo_version": args.modelo_version,
        "workers": args.workers, "torch_threads": args.torch_threads, "flags": FLAGS,
        "api_imagen": read_inspect("giragroup_api")["Image"],
        "pipeline_imagen": read_inspect("giragroup_pipeline")["Image"],
        "script_sha256": f0.digest(Path(__file__)),
    }
    if manifest_path.is_file():
        sha = tree_fingerprint(tree)
        if read(manifest_path) != {**config, "arbol_sha256": sha}:
            raise RuntimeError("La reanudación exige el mismo código, modelo e imágenes")
    else:
        sha = stage_tree(tree, args.revision, args.cambios_locales)
        f0.write(manifest_path, {**config, "arbol_sha256": sha})
    return work, tree, sha


def main():
    ap = parser()
    args = ap.parse_args()
    PRIVATE.mkdir(parents=True, exist_ok=True)
    if args.accion in ("candidato", "agregar"):
        if args.calidad is None:
            ap.error("CF-L5 necesita --calidad con el dictamen aprobado de CF-L3")
        calidad = read_quality(args.calidad)
        if args.accion == "agregar":
            aggregate(calidad)
            return
    db_info = validate_tmpfs()
    f0.verify(base=f0.PRIVATE)
    if args.accion == "preparar":
        prepare_templates("cf_l1_dw", "cf_l1_catalog")
        return
    if args.accion != "smoke" and not args.confirmar_ventana_exclusiva:
        ap.error("La medición definitiva requiere una ventana sin entrenamiento ni cargas concurrentes")
    if args.accion == "candidato" and args.modelo_version == "beto-v2":
        ap.error("El candidato requiere una versión nueva de caché")
    args.modelo = args.modelo.resolve()
    if not (args.modelo / "model.safetensors").is_file():
        ap.error("El modelo local debe incluir model.safetensors")
    if args.accion == "candidato" and calidad["sha256_modelos"]["candidato"] != f0.digest(args.modelo / "model.safetensors"):
        ap.error("El checkpoint no coincide con el candidato aprobado en el dictamen")
    isolated_network(db_info)
    work, tree, sha = stage_run(args)
    if (work / "serie.json").exists():
        print("La serie ya se completó; resultados en " + str(work / "serie.json"))
        return
    if args.accion == "smoke":
        dw, cat = "cf_l5_smoke_dw", "cf_l5_smoke_catalog"
        for nombre, origen in ((dw, "dw_vacio"), (cat, "catalogo_copia")):
            clone(nombre, origen)
        try:
            with environment(args, tree, dw, cat) as runtime:
                runtime["arbol_sha256"] = sha
                f0.write(work / "preflight.json", runtime)
                print(json.dumps(runtime, ensure_ascii=False), flush=True)
        finally:
            for db in (dw, cat):
                drop(db)
        return
    with (ExecutionState() if os.name == "nt" else nullcontext()):
        corridas = series(args, tree, work)
    f0.verify(base=f0.PRIVATE)
    f0.write(work / "serie.json", {"arbol_sha256": sha, "revision": args.revision, "corridas": corridas})


if __name__ == "__main__":
    main()
