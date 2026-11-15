"""F0: entrada inmutable y puertas de medición; no modifica lógica productiva.

La huella de lote usa JSON UTF-8, ensure_ascii=False, sort_keys=True y
separadores (',', ':') de [{ruta, bytes, sha256}], ordenado por ruta.
Los XLSX y logs íntegros permanecen en output/backups (ignorado por git).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "output/backups/f0_lote"
MANIFEST = ROOT / "docs/mediciones/f0_lote_manifest.json"
FLAGS = ("BETO_CASCADA_FINAL", "BETO_ACUERDO_QC", "BETO_SUGERENCIA_HITL", "BETO_VENTANA")
CONFIGS = dict(zip(("a0", "a1", "a2", "a3", "a12", "a123", "a2w"),
                   ((0,0,0,0), (1,0,0,0), (0,1,0,0), (0,0,1,0), (1,1,0,0), (1,1,1,0), (0,1,0,1))))
CACHES = ("cache_indice_beto", "cache_beto_entidades")
REFERENCE_TREE = "/tmp/f0_ref_73ec78f"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now():
    return datetime.now(ZoneInfo("America/La_Paz")).isoformat()


def canonical(entries):
    return json.dumps(sorted(entries, key=lambda x: x["ruta"]), ensure_ascii=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def inventory(base):
    return [{"ruta": p.relative_to(base).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p)}
            for folder in ("originales", "slices") for p in sorted((base / folder).glob("*.xlsx"))]


def verify(manifest=MANIFEST, base=None):
    m = json.loads(Path(manifest).read_text(encoding="utf-8"))
    actual = inventory(Path(base or m["copia_privada"]))
    if canonical(actual) != canonical(m["archivos"]) or hashlib.sha256(canonical(actual)).hexdigest() != m["sha256"]:
        raise ValueError("Lote faltante, extra o alterado: medición prohibida")
    return {"fecha": now(), "sha256": m["sha256"], "archivos": len(actual), "valido": True}


def freeze(args):
    files = sorted((ROOT / "uploads/data").glob("*.xlsx"), key=lambda p: ("ANTIGUO" in p.name, p.name))
    if len(files) != args.esperados:
        raise ValueError(f"Se requieren {args.esperados} originales; encontrados {len(files)}")
    if Path(args.salida).exists() or (PRIVATE / "slices").exists() and any((PRIVATE / "slices").iterdir()):
        raise ValueError("Congelamiento ya iniciado: verificar/recuperar bytes; nunca regenerar")
    (PRIVATE / "originales").mkdir(parents=True, exist_ok=True)
    (PRIVATE / "slices").mkdir(exist_ok=True)
    for p in files:
        target = PRIVATE / "originales" / p.name
        if target.exists():
            if digest(target) != digest(p):
                raise ValueError("Original recuperado distinto; requiere decisión de composición")
        else:
            shutil.copyfile(p, target)
    # Importar no llama main(); fijar globals evita depender de argv/entorno heredado.
    spec = importlib.util.spec_from_file_location("f0_ciclo", ROOT / "scripts/medir_ciclo_mensual.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = PRIVATE / "generador"
    (module.ROOT / "uploads/data").mkdir(parents=True, exist_ok=True)
    for p in (PRIVATE / "originales").glob("*.xlsx"):
        shutil.copyfile(p, module.ROOT / "uploads/data" / p.name)
    module.MES, module.SALIDA = args.mes, PRIVATE / "slices"
    module.FILAS_SIN_FECHA, module.REUSAR_SLICES = None, False
    info = module.construir_slices()
    if len(info) != args.esperados or any("slice" not in x for x in info):
        raise ValueError("No se generaron todos los slices; conservar copia para diagnóstico")
    import pandas as pd
    for item in info:
        item.pop("slice", None)
        sheets = pd.read_excel(PRIVATE / "originales" / item["archivo"], sheet_name=None)
        item["original_hojas"] = [{"hoja": h, "filas": len(df)} for h, df in sheets.items()]
    entries = inventory(PRIVATE)
    fingerprint = hashlib.sha256(canonical(entries)).hexdigest()
    m = {"fecha": now(), "mes_objetivo": args.mes, "filas_sin_fecha": 0,
         "copia_privada": str(PRIVATE), "generador_sha256": digest(ROOT / "scripts/medir_ciclo_mensual.py"),
         "serializacion": "JSON UTF-8 ensure_ascii=False sort_keys=True separators=(',',':'); lista por ruta",
         "algoritmo": "construir_slices: mes objetivo; fallback modal últimos 12 meses; sin fecha hoja completa",
         "orden": [p.name for p in files], "seleccion": info, "archivos": entries, "sha256": fingerprint,
         "despliegue": "pendiente; requiere Docker y verificación snapshot/copia"}
    write(args.salida, m)
    Path(args.salida).with_name("f0_lote_sha256.txt").write_text(fingerprint + "\n", encoding="utf-8")
    verify(args.salida)


def run(*args, input=None, combined=False):
    if args[0] == "sh" and os.name == "nt" and shutil.which("sh") is None:
        args = ("C:/Program Files/Git/bin/bash.exe", *args[1:])
    result = subprocess.run(args, input=input, capture_output=True, text=True, encoding="utf-8", errors="replace")
    # Retener también fallos/stderr íntegros fuera de git; nunca volcar dumps de caché.
    if "pg_dump" not in args and input is None:
        PRIVATE.mkdir(parents=True, exist_ok=True)
        with (PRIVATE / "comandos.stdout-stderr.txt").open("a", encoding="utf-8") as log:
            offset = log.tell()
            log.write(f"\n[{now()}] {args[0]} exit={result.returncode}\nSTDOUT\n{result.stdout}\nSTDERR\n{result.stderr}\n")
            length = log.tell() - offset
        def summary(value):
            return {"bytes_utf8": len(value.encode("utf-8")), "lineas": len(value.splitlines()),
                    "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(), "texto": "[REDACTADO]"}
        public = {"fecha": now(), "programa": args[0], "exit": result.returncode,
                  "redaccion": "resumen del flujo completo; íntegro privado recuperable",
                  "integral_privado": {"ruta": "comandos.stdout-stderr.txt", "offset_bytes": offset, "longitud_bytes": length},
                  "stdout": summary(result.stdout), "stderr": summary(result.stderr)}
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        if "/tmp/flujo/scripts/medir_flujo_dataops.py" in args:
            # Conservar todas las líneas del flujo, cada una redactada, sin hashes
            # individuales de millones de filas SQL en el repositorio.
            destination = MANIFEST.parent / (Path(args[-1]).name + ".stdout-stderr-redactados.txt")
            lines = ["STDOUT"] + ["[REDACTADO]" for _ in result.stdout.splitlines()] + ["STDERR"] + ["[REDACTADO]" for _ in result.stderr.splitlines()]
            destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with (MANIFEST.parent / "f0_comandos_redactados.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps(public, ensure_ascii=False) + "\n")
    if result.returncode:
        # Salidas pueden contener personas/credenciales: no imprimir al usuario.
        raise RuntimeError(f"Falló comando {args[0]} (código {result.returncode}); sin salida sensible")
    return result.stdout + result.stderr if combined else result.stdout


def compact_log():
    """Ejecutar sin escritores activos, después de warmups, antes de la serie."""
    source = MANIFEST.parent / "f0_comandos_redactados.jsonl"
    backup = PRIVATE / "logs" / ("comandos_redactados_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".jsonl")
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(source, backup)
    records = 0
    with backup.open(encoding="utf-8") as reader, source.open("w", encoding="utf-8") as writer:
        for line in reader:
            record = json.loads(line)
            for stream in ("stdout", "stderr"):
                value = record.get(stream)
                if isinstance(value, list):
                    record[stream] = {"lineas": len(value), "bytes_sin_saltos": sum(v["bytes"] for v in value),
                        "sha256_lista_lineas_redactadas": hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                        "texto": "[REDACTADO]", "nota": "Formato anterior; digest del stream íntegro no registrado, original privado preservado"}
            writer.write(json.dumps(record, ensure_ascii=False) + "\n")
            records += 1
    write(MANIFEST.parent / "f0_log_compactacion.json", {"fecha": now(), "registros": records,
        "original_privado": str(backup.relative_to(PRIVATE)), "original_sha256": digest(backup), "original_bytes": backup.stat().st_size,
        "compacto_sha256": digest(source), "compacto_bytes": source.stat().st_size,
        "integrales_privados": {"ruta": "comandos.stdout-stderr.txt", "sha256_al_compactar": digest(PRIVATE / "comandos.stdout-stderr.txt")},
        "protocolo": "No se descartan originales: archivo de log anterior íntegro privado; reemplazo público por resúmenes de stdout/stderr"})


def sql(db, query):
    if not re.fullmatch(r"(?:run_f0_|f0_cache_)[a-z0-9_]+", db):
        raise ValueError("Nombre de base no autorizado")
    return run("docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", db,
               "-v", "ON_ERROR_STOP=1", "-At", "-c", query).strip()


def snapshot_fingerprint(source, output):
    """Solo SELECT en transacciones READ ONLY; publicar únicamente conteos/digests."""
    if source == "snapshot":
        container, database = "giragroup_db", "snapshot_dw_20261110_1201"
        user = run("docker", "exec", container, "printenv", "POSTGRES_USER").strip()
    else:
        container, database, user = "beto_pg_tmpfs", "giragroup_db", "giragroup_user"
    def query(statement):
        return run("docker", "exec", container, "psql", "-U", user, "-d", database, "-qAt",
                   "-v", "ON_ERROR_STOP=1", "-c", "BEGIN TRANSACTION READ ONLY; " + statement + "; COMMIT").strip()
    relations = query("SELECT n.nspname || '.' || c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('public','bi') AND c.relkind IN ('r','p','v','m') ORDER BY 1").splitlines()
    tables = {}
    for relation in relations:
        schema, table = relation.split(".", 1)
        quoted = '"' + schema.replace('"', '""') + '"."' + table.replace('"', '""') + '"'
        answer = query(f"SELECT count(*), md5(coalesce(string_agg(row_to_json(t)::text, E'\\n' ORDER BY row_to_json(t)::text), '')) FROM {quoted} t")
        count, fingerprint = answer.split("|")
        tables[relation] = {"filas": int(count), "md5_filas": fingerprint}
    value = {"fecha": now(), "origen": source, "base": database, "relaciones": tables,
             "algoritmo": "COUNT y MD5 string_agg(row_to_json::text ordenado), READ ONLY; SHA256 JSON canónico de mapa de relaciones",
             "huella": hashlib.sha256(json.dumps(tables, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
    write(output, value)
    return value


def catalog_fingerprint(source="copia"):
    container, database, user = "beto_pg_tmpfs", "catalogo_copia", "giragroup_user"
    if source == "origen":
        container = "giragroup_catalog_db"
        database = run("docker", "exec", container, "printenv", "POSTGRES_DB").strip()
        user = run("docker", "exec", container, "printenv", "POSTGRES_USER").strip()
    # Una llamada, SELECT dinámicos en READ ONLY, salida exclusivamente conteos/MD5.
    query = """BEGIN TRANSACTION READ ONLY;
SELECT coalesce(jsonb_object_agg(n.nspname || '.' || c.relname,
 query_to_xml(format($q$SELECT count(*) AS filas,
 md5(coalesce(string_agg(row_to_json(t)::text, E'\\n' ORDER BY row_to_json(t)::text), '')) AS md5
 FROM %I.%I t$q$, n.nspname, c.relname), false, true, '')::text), '{}'::jsonb)
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname IN ('public','bi') AND c.relkind IN ('r','p'); COMMIT;"""
    tables = json.loads(run("docker", "exec", container, "psql", "-U", user, "-d", database,
                            "-qAt", "-v", "ON_ERROR_STOP=1", "-c", query))
    return {"fecha": now(), "fuente": source, "tablas": len(tables),
            "sha256": hashlib.sha256(json.dumps(tables, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "metodo": "READ ONLY: conteo y MD5 de JSON filas ordenadas por tabla; SHA256 mapa XML canónico"}


def cache_state(db):
    result = {}
    for table in CACHES:
        exists = sql(db, f"SELECT to_regclass('public.{table}') IS NOT NULL") == "t"
        # Solo hashes/claves: nunca entidades/nombres.
        key = "modelo" if table == "cache_indice_beto" else "configuracion"
        result[table] = {"filas": int(sql(db, f"SELECT count(*) FROM public.{table}")) if exists else 0,
                         "sha256_claves": hashlib.sha256(sql(db, f"SELECT hash_texto, {key} FROM public.{table} ORDER BY hash_texto, {key}").encode()).hexdigest() if exists else None,
                         "sha256_contenido": hashlib.sha256(sql(db, f"SELECT to_jsonb(t) - 'creado_en' FROM public.{table} t ORDER BY hash_texto, {key}").encode()).hexdigest() if exists else None}
    return result


def seed_cache(db, seed=None, empty=False):
    if empty and seed:
        raise ValueError("CACHE_VACIA y CACHE_SEED_DB son mutuamente excluyentes")
    if seed and not re.fullmatch(r"f0_cache_(?:a0|a1|a2|a3|a12|a123|a2w)", seed):
        raise ValueError("Semilla fuera de bases F0 tmpfs")
    if empty:
        for table in CACHES:
            if sql(db, f"SELECT to_regclass('public.{table}') IS NOT NULL") == "t":
                sql(db, f"TRUNCATE public.{table}")
    if seed:
        # Transporte privado en memoria, sin dump a un archivo versionable.
        for table in CACHES:
            if sql(seed, f"SELECT to_regclass('public.{table}') IS NOT NULL") == "t":
                dump = run("docker", "exec", "beto_pg_tmpfs", "pg_dump", "-U", "giragroup_user", "-d", seed,
                           "--no-owner", "--no-privileges", "--clean", "--if-exists", "-t", f"public.{table}")
                run("docker", "exec", "-i", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", db,
                    "-v", "ON_ERROR_STOP=1", input=dump)
        if cache_state(db) != cache_state(seed):
            raise ValueError("Restauración de cachés no idéntica")
    state = cache_state(db)
    if empty and any(x["filas"] for x in state.values()):
        raise ValueError("Caché no vacía")
    return state


def explicit_flags(values):
    env = dict(v.split("=", 1) for v in values)
    if any(env.get(k) not in ("0", "1") for k in FLAGS):
        raise ValueError("Fijar explícitamente los cuatro flags BETO")
    if env.get("CATALOG_DATABASE_URL") != "postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/catalogo_copia":
        raise ValueError("Catálogo debe ser catalogo_copia aislado")
    return env


def valid_result(result):
    load = result.get("carga", {})
    if load.get("http") != 200 or load.get("archivos_exitosos") != 10 or load.get("archivos_fallidos") != 0:
        raise ValueError("Carga parcial o HTTP fallido")
    if not isinstance(load.get("registros_detectados"), int) or load["registros_detectados"] <= 0:
        raise ValueError("Conteo de entrada ausente o no positivo")
    if result.get("consolidacion_http") != 200 or not result.get("revision", {}).get("omitida"):
        raise ValueError("Consolidación fallida o revisión no omitida")
    if not result.get("dw_despues") or not result.get("etapas_s") or not result.get("total", {}).get("tiempo_maquina_s"):
        raise ValueError("Salida parcial sin tiempos/conteos")


def gates():
    """Ninguna inferencia hasta demostrar las huellas iniciales y el entorno."""
    directory = MANIFEST.parent
    before = json.loads((directory / "f0_snapshot_antes.json").read_text(encoding="utf-8"))
    copy = json.loads((directory / "f0_snapshot_copia.json").read_text(encoding="utf-8"))
    if before.get("huella") is None or before["huella"] != copy.get("huella"):
        raise ValueError("Snapshot/copia inicial no idénticos")
    env = json.loads((directory / "f0_entorno.json").read_text(encoding="utf-8"))
    if not all(env.get(k) for k in ("arbol_sha256", "modelo_sha256", "exclusividad_8006", "calentamiento_modelo")):
        raise ValueError("Entorno/calentamiento/exclusividad no verificados")
    return env


def verify_container(m, tree="/tmp/medida"):
    code = "import hashlib,json,pathlib; root=pathlib.Path('/tmp/flujo/uploads/data'); slices=pathlib.Path('/tmp/slices_flujo'); print(json.dumps([{'ruta':prefix+'/'+p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for prefix,folder in [('originales',root),('slices',slices)] for p in sorted(folder.glob('*.xlsx'))]))"
    actual = json.loads(run("docker", "exec", "giragroup_api", "python", "-c", code))
    if canonical(actual) != canonical(m["archivos"]):
        raise ValueError("Entrada contenedor faltante, extra o alterada")
    code_copy = "import hashlib,json,pathlib,sys; root=pathlib.Path(sys.argv[1])/'uploads/data'; print(json.dumps([{'ruta':'originales/'+p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(root.glob('*.xlsx'))]))"
    copied = json.loads(run("docker", "exec", "giragroup_api", "python", "-c", code_copy, tree))
    if canonical(copied) != canonical([x for x in m["archivos"] if x["ruta"].startswith("originales/")]):
        raise ValueError("Entrada del árbol aislado distinta del lote congelado")


def runtime_hash(container, path):
    code = "import pathlib,hashlib,json,sys; root=pathlib.Path(sys.argv[1]); entries=[{'ruta':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and 'uploads' not in p.relative_to(root).parts and (root.name not in ('medida','f0_ref_73ec78f') or p.relative_to(root).parts[0] in ('backend','pipeline','db'))]; print(hashlib.sha256(json.dumps(entries,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest())"
    return run("docker", "exec", container, "python", "-c", code, path).strip()


def verify_runtime(environment, path="/tmp/medida"):
    tree = runtime_hash("giragroup_api", path)
    model_path = environment.get("modelo_directorio", "")
    if not model_path.startswith("/"):
        raise ValueError("Ubicación del modelo no registrada")
    model = runtime_hash("giragroup_pipeline", model_path)
    expected_tree = environment["referencia_73ec78f"]["arbol_sha256"] if path == REFERENCE_TREE else environment["arbol_sha256"]
    if tree != expected_tree or model != environment["modelo_sha256"]:
        raise ValueError("Árbol/modelo cambió frente al entorno congelado")
    state = json.loads(run("docker", "inspect", "--format", '{"id":"{{.Id}}","imagen":"{{.Image}}","inicio":"{{.State.StartedAt}}"}', "giragroup_pipeline"))
    if state != environment.get("contenedores", {}).get("giragroup_pipeline"):
        raise ValueError("Servicio BETO recreado/reiniciado frente al entorno congelado")


def export_review(db, run_id, cache_dir):
    """Evidencia posterior al cronómetro; PII exclusivamente en carpeta privada."""
    target = PRIVATE / "corridas" / run_id
    target.mkdir(parents=True, exist_ok=False)
    exports, stats = [], {}
    tables = ("staging_registros_crudos", "stg_entidad_no_resuelta", "dataops_tarea", "log_inconsistencias",
              "log_pipeline_ingesta", "dim_origen_documental", "dim_estudiante", "dim_docente", "dim_tiempo",
              "cache_indice_beto", "cache_beto_entidades")
    facts = sql(db, "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'fact_%' ORDER BY table_name").splitlines()
    for table in list(tables) + facts:
        if sql(db, f"SELECT to_regclass('public.{table}') IS NOT NULL") != "t":
            continue
        raw = sql(db, f"SELECT row_to_json(t) FROM public.{table} t")
        file = target / (table + ".jsonl")
        file.write_text(raw + "\n", encoding="utf-8")
        exports.append({"archivo": str(file.relative_to(PRIVATE)), "sha256": digest(file), "bytes": file.stat().st_size})
        cols = set(sql(db, f"SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='{table}'").splitlines())
        expressions = ["count(*) AS total"]
        if "requiere_revision" in cols:
            expressions.append("count(*) FILTER (WHERE requiere_revision IS TRUE) AS requiere_revision")
        if "es_ruido" in cols:
            expressions.append("count(*) FILTER (WHERE es_ruido IS TRUE) AS ruido")
        score = next((k for k in ("score_confianza", "nivel_confianza_ia", "nivel_confianza") if k in cols), None)
        if score:
            expressions.extend([f"count(*) FILTER (WHERE {score} >= .85) AS banda_alta",
                f"count(*) FILTER (WHERE {score} >= .60 AND {score} < .85) AS banda_media",
                f"count(*) FILTER (WHERE {score} < .60) AS banda_baja",
                f"count(*) FILTER (WHERE {score} IS NULL) AS confianza_null"])
        summary = json.loads(sql(db, "SELECT row_to_json(x) FROM (SELECT " + ",".join(expressions) + f" FROM public.{table}) x"))
        summary.update({"unidad": "filas de " + table, "denominador_bandas": summary["total"], "columna_confianza": score,
                        "motivo_bandas_null": None if score else "Tabla sin columna de confianza; no se imputa"})
        stats[table] = summary
    run("docker", "cp", f"giragroup_api:{cache_dir}", str(target / "lectura"))
    for file in sorted((target / "lectura").rglob("*")):
        if file.is_file():
            exports.append({"archivo": str(file.relative_to(PRIVATE)), "sha256": digest(file), "bytes": file.stat().st_size})
    gestion = sql(db, "SELECT MAX(gestion) FROM bi.vw_cmi_gestiones")
    return {"exports_privados": exports, "estadisticas": stats,
            "gestion_scorecard_por_defecto": int(gestion) if gestion else None,
            "protocolo": "Export posterior a cronómetro; originales de lectura y rankings inmutables privados para A3/A4"}


def fixed_warmup():
    """Mismo calentamiento sintético por llamada, sin base de datos y fuera del reloj."""
    code = "import urllib.request,json; body=json.dumps({'textos':['Programa de prueba institucional.']*16,'ventana':False,'stride':32,'max_length':128}).encode(); results=[];\nfor n in range(4):\n r=urllib.request.urlopen(urllib.request.Request('http://pipeline:8006/infer-batch',data=body,headers={'Content-Type':'application/json'}),timeout=180); data=json.load(r); assert r.status==200 and data.get('status')=='success' and data.get('n_textos')==16 and len(data.get('resultados',[]))==16; results.append({'peticion':n+1,'http':r.status})\nprint(json.dumps(results))"
    return {"tipo": "sintetico_excluido", "textos_por_peticion": 16, "max_length": 128,
            "ventana": False, "stride": 32,
            "peticiones": json.loads(run("docker", "exec", "giragroup_api", "python", "-c", code))}


def windows_sleep_events(start, end):
    """Solo horarios/IDs de eventos; no usuarios, equipo ni fuentes de despertar."""
    if os.name != "nt":
        return {"aplica": False, "suspension_detectada": False}
    begin, finish = datetime.fromisoformat(start), datetime.fromisoformat(end)
    command = r"""$ErrorActionPreference='Stop'
Get-WinEvent -ListLog System -ErrorAction Stop | Out-Null
$begin=[datetimeoffset]'__BEGIN__'; $finish=[datetimeoffset]'__END__'
$kernel=@(Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-Power'; Id=42; StartTime=$begin.LocalDateTime; EndTime=$finish.LocalDateTime} -ErrorAction SilentlyContinue | ForEach-Object { [pscustomobject]@{id=$_.Id;utc=$_.TimeCreated.ToUniversalTime().ToString('o')} })
$resume=@(Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Power-Troubleshooter'; Id=1; StartTime=$begin.LocalDateTime; EndTime=$finish.LocalDateTime} -ErrorAction SilentlyContinue | ForEach-Object { $x=[xml]$_.ToXml(); $d=@{}; foreach($v in $x.Event.EventData.Data){if($v.Name -in @('SleepTime','WakeTime','TargetState','EffectiveState')){$d[$v.Name]=$v.InnerText}}; [pscustomobject]@{id=$_.Id;utc=$_.TimeCreated.ToUniversalTime().ToString('o');datos=$d} })
[pscustomobject]@{aplica=$true;kernel_power_42=$kernel;power_troubleshooter_1=$resume} | ConvertTo-Json -Depth 6
exit 0
""".replace("__BEGIN__", begin.isoformat()).replace("__END__", finish.isoformat())
    events = json.loads(run("powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command))
    overlap = False
    for event in events["power_troubleshooter_1"]:
        values = event["datos"]
        if values.get("SleepTime") and values.get("WakeTime"):
            sleep = datetime.fromisoformat(values["SleepTime"].replace("Z", "+00:00"))
            wake = datetime.fromisoformat(values["WakeTime"].replace("Z", "+00:00"))
            overlap |= sleep < finish and wake > begin and wake > sleep
    events["suspension_detectada"] = bool(events["kernel_power_42"]) or overlap
    return events


def execute(args):
    if args.arbol not in ("/tmp/medida", REFERENCE_TREE):
        raise ValueError("F0 requiere uno de los dos árboles aislados autorizados")
    env = explicit_flags(args.variables)
    config = next((c for c, f in CONFIGS.items() if tuple(str(v) for v in f) == tuple(env[k] for k in FLAGS)), None)
    if config is None or env.get("BETO_VENTANA_STRIDE") != "32":
        raise ValueError("Configuración/stride no F0")
    if args.arbol == REFERENCE_TREE and (config != "a0" or not args.salida.startswith("f0_referencia_a0_") or not args.db.startswith("run_f0_referencia_a0_")):
        raise ValueError("Árbol de referencia reservado a a0 fuera de la matriz")
    if not re.fullmatch(r"(?:run_f0_|f0_cache_)[a-z0-9_]+", args.db) or not re.fullmatch(r"[a-zA-Z0-9_.-]+\.json", args.salida):
        raise ValueError("Nombre de base/salida inválido")
    seed, empty = os.environ.get("CACHE_SEED_DB"), os.environ.get("CACHE_VACIA") == "1"
    if bool(seed) == bool(empty):
        raise ValueError("F0 exige exactamente caché vacía o semilla")
    if seed and seed != "f0_cache_" + config:
        raise ValueError("Semilla de otra configuración")
    directory = MANIFEST.parent
    path = directory / args.salida
    meta_path = path.with_suffix(".meta.json")
    if path.exists() or meta_path.exists():
        raise ValueError("No sobrescribir evidencia; usar identificador nuevo")
    environment = gates()
    import f0_mantener_activo as energy
    energy_before = energy.check()
    verify_runtime(environment, args.arbol)
    verify()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    verify_container(manifest, args.arbol)
    tree_hash = environment["referencia_73ec78f"]["arbol_sha256"] if args.arbol == REFERENCE_TREE else environment["arbol_sha256"]
    meta = {"fecha": now(), "configuracion": config, "estado": "vacia" if empty else "llena",
            "valida": False, "flags": {k: env[k] for k in FLAGS}, "lote_sha256": manifest["sha256"],
            "arbol_sha256": tree_hash, "modelo_sha256": environment["modelo_sha256"], "arbol": args.arbol,
            "orden": manifest["orden"], "base": args.db, "catalogo": "catalogo_copia", "verificacion_antes": verify()}
    cache_dir, landing_dir = f"/tmp/f0/{args.db}/lectura", f"/tmp/f0/{args.db}/landing"
    meta.update({"lectura_cache_dir": cache_dir, "landing_dir": landing_dir})
    meta["energia_antes"] = energy_before
    meta["protocolo_vigilancia"] = "v2: inhibición temporal, eventos Windows y pared/monotonic host; temporizadores de producto sin cambios"
    meta["soporte_control_sha256"] = {"medir_f0.py": digest(Path(__file__)),
        "f0_mantener_activo.py": digest(ROOT / "scripts/f0_mantener_activo.py")}
    try:
        meta["catalogo_antes"] = catalog_fingerprint()
        if environment.get("catalogo_sha256") and meta["catalogo_antes"]["sha256"] != environment["catalogo_sha256"]:
            raise ValueError("Catálogo de copia cambió frente al entorno congelado")
        meta["recursos_antes"] = run("docker", "stats", "--no-stream", "--format", "{{json .}}").splitlines()
        meta["calentamiento_servicio"] = fixed_warmup()
        run("sh", "scripts/aislada_tmpfs.sh", "clon", args.db)
        meta["cache_antes"] = seed_cache(args.db, seed, empty)
        run("docker", "exec", "giragroup_api", "mkdir", "-p", "/tmp/flujo/scripts")
        run("docker", "exec", "giragroup_api", "mkdir", "-p", cache_dir, landing_dir)
        for name in ("medir_flujo_dataops.py", "huella_dw.py", "simular_revision.py", "medir_ciclo_mensual.py"):
            run("docker", "cp", str(ROOT / "scripts" / name), "giragroup_api:/tmp/flujo/scripts/" + name)
        # Cada proceso nuevo fija flags; ningún flag se hereda del contenedor.
        variables = args.variables + [f"DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/{args.db}",
            "FLUJO_SIN_REVISION=1", "CICLO_REUSAR_SLICES=1", "CICLO_FILAS_SIN_FECHA=0", "CICLO_SLICES=/tmp/slices_flujo",
            f"LECTURA_CACHE_DIR={cache_dir}", f"LANDING_DIR={landing_dir}",
            f"PYTHONPATH={args.arbol}:{args.arbol}/backend:/tmp/flujo/scripts"]
        started, monotonic_started = now(), time.perf_counter()
        log = run("docker", "exec", "-w", args.arbol, "giragroup_api", "env", *variables,
                  "python", "/tmp/flujo/scripts/medir_flujo_dataops.py", "/tmp/" + args.salida)
        finished, monotonic_finished = now(), time.perf_counter()
        wall_seconds = (datetime.fromisoformat(finished) - datetime.fromisoformat(started)).total_seconds()
        host_seconds = monotonic_finished - monotonic_started
        meta["tiempo_invocacion_host"] = {"inicio": started, "fin": finished,
            "pared_s": wall_seconds, "monotonic_s": host_seconds, "diferencia_relojes_s": wall_seconds - host_seconds,
            "incluye": "Importaciones, lectura/consolidación, huella y generación de evidencia; distinto del tiempo de máquina sin revisión"}
        (PRIVATE / (args.salida + ".stdout.txt")).write_text(log, encoding="utf-8")
        run("docker", "cp", "giragroup_api:/tmp/" + args.salida, str(PRIVATE / args.salida))
        data = json.loads((PRIVATE / args.salida).read_text(encoding="utf-8"))
        valid_result(data)
        meta["tiempo_invocacion_host"]["fuera_cronometro_dentro_invocacion_s"] = host_seconds - data["total"]["tiempo_maquina_s"]
        if environment.get("registros_esperados") is not None and data["carga"]["registros_detectados"] != environment["registros_esperados"]:
            raise ValueError("Conteo de entrada distinto del calentamiento congelado")
        state = sql(args.db, "SELECT estado FROM dataops_tarea WHERE tipo='LECTURA_BETO' ORDER BY id DESC LIMIT 1")
        if state != "COMPLETADA":
            raise ValueError("Lectura no completada/timeout")
        run("docker", "cp", "giragroup_api:/tmp/" + args.salida + ".huella.json", str(PRIVATE / (args.salida + ".huella.json")))
        footprint = json.loads((PRIVATE / (args.salida + ".huella.json")).read_text(encoding="utf-8"))
        # Claves de agrupación pueden contener nombres: publicar solamente digest.
        if "firma" in footprint.get("bandeja", {}):
            signature = footprint["bandeja"].pop("firma")
            footprint["bandeja"]["firma_sha256"] = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
        data["carga"].pop("errores", None)
        meta["cache_despues"] = cache_state(args.db)
        review = export_review(args.db, path.stem, cache_dir)
        write(path.with_suffix(".revision.json"), review)
        meta["revision_evidencia"] = path.with_suffix(".revision.json").name
        verify_container(manifest, args.arbol)
        verify_runtime(environment, args.arbol)
        meta["verificacion_despues"] = verify()
        meta["eventos_energia"] = windows_sleep_events(started, now())
        meta["energia_despues"] = energy.check()
        if meta["eventos_energia"]["suspension_detectada"]:
            raise ValueError("Suspensión Windows detectada: conservar inválida y repetir con nuevo sufijo")
        if abs(wall_seconds - host_seconds) > 5:
            raise ValueError("Salto del reloj de pared >5s frente a monotonic host: corrida perturbada")
        meta["catalogo_despues"] = catalog_fingerprint()
        if meta["catalogo_antes"]["sha256"] != meta["catalogo_despues"]["sha256"]:
            raise ValueError("Catálogo de copia mutado durante corrida")
        meta["recursos_despues"] = run("docker", "stats", "--no-stream", "--format", "{{json .}}").splitlines()
        traffic = run("docker", "logs", "--since", meta["fecha"], "giragroup_pipeline", combined=True)
        counts = {}
        for method, route in re.findall(r'"(GET|POST) (/[^ ?"]+)', traffic):
            counts[method + " " + route] = counts.get(method + " " + route, 0) + 1
        meta["trafico_servicio"] = {"desde": meta["fecha"], "peticiones_por_ruta": counts,
            "atribucion": "Ventana exclusiva declarada; no hay atribución individual de clientes a partir del log HTTP"}
        meta["valida"] = True
        write(path, data)
        write(str(path) + ".huella.json", footprint)
    except Exception as e:
        meta["motivo_invalida"] = type(e).__name__ + ": " + str(e)[:180]
        raise
    finally:
        write(meta_path, meta)


def deploy():
    verify()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    run("docker", "exec", "giragroup_api", "mkdir", "-p", "/tmp/flujo/scripts", "/tmp/flujo/uploads/data", "/tmp/slices_flujo")
    # CatalogRepository lee este seed desde ROOT/db/seeds incluso en la copia.
    run("docker", "exec", "giragroup_api", "mkdir", "-p", "/tmp/medida/db/seeds")
    run("docker", "cp", str(ROOT / "db/seeds/seed_catalogos.sql"), "giragroup_api:/tmp/medida/db/seeds/seed_catalogos.sql")
    for folder, dest in (("originales", "/tmp/flujo/uploads/data"), ("slices", "/tmp/slices_flujo")):
        for p in (PRIVATE / folder).glob("*.xlsx"):
            run("docker", "cp", str(p), f"giragroup_api:{dest}/{p.name}")
    # Reemplazar solo el enlace de la copia aislada, nunca /app/uploads.
    run("docker", "exec", "giragroup_api", "python", "-c",
        "from pathlib import Path; import shutil; p=Path('/tmp/medida/uploads'); p.unlink() if p.is_symlink() else None; shutil.copytree('/tmp/flujo/uploads',p,dirs_exist_ok=True)")
    verify_container(manifest)
    return manifest


def prepare(args):
    gates()
    manifest = deploy()
    seeds = []
    for config in args.configuraciones.split(","):
        if config not in CONFIGS:
            raise ValueError("Configuración desconocida")
        warm = argparse.Namespace(arbol="/tmp/medida", db="run_f0_warmup_" + config,
            salida="f0_warmup_" + config + ".json", variables=[f"{k}={v}" for k, v in zip(FLAGS, CONFIGS[config])] +
            ["BETO_VENTANA_STRIDE=32", "CATALOG_DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/catalogo_copia"])
        previous = (os.environ.get("CACHE_VACIA"), os.environ.pop("CACHE_SEED_DB", None))
        os.environ["CACHE_VACIA"] = "1"
        try:
            execute(warm)
        finally:
            for key, value in zip(("CACHE_VACIA", "CACHE_SEED_DB"), previous):
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        seed = "f0_cache_" + config
        # Seed DB contiene solo las dos cachés, sin tablas de negocio.
        run("docker", "exec", "beto_pg_tmpfs", "createdb", "-U", "giragroup_user", "-T", "template0", seed)
        for table in CACHES:
            if sql(warm.db, f"SELECT to_regclass('public.{table}') IS NOT NULL") == "t":
                dump = run("docker", "exec", "beto_pg_tmpfs", "pg_dump", "-U", "giragroup_user", "-d", warm.db,
                           "--no-owner", "--no-privileges", "-t", f"public.{table}")
                run("docker", "exec", "-i", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", seed,
                    "-v", "ON_ERROR_STOP=1", input=dump)
        if cache_state(seed) != cache_state(warm.db):
            raise ValueError("Semilla incompleta")
        seeds.append({"configuracion": config, "base": seed, "cache": cache_state(seed), "calentamiento_excluido": warm.salida})
        write(args.salida, {"fecha": now(), "lote_sha256": manifest["sha256"], "semillas": seeds})
        run("docker", "exec", "beto_pg_tmpfs", "dropdb", "-U", "giragroup_user", warm.db)


def _series(args):
    """Una única serie secuencial; guarda inválidas y nunca sobrescribe corridas."""
    environment = gates()
    environment["politica_clones"] = "Eliminar solo clon F0 sellado tras exportar respaldo privado; conservar a123_llena_r1 para revisión; nunca historia/tests/semillas"
    write(MANIFEST.parent / "f0_entorno.json", environment)
    for config in CONFIGS:
        for state in ("vacia", "llena"):
            for n in (1, 2, 3):
                basename = f"f0_{config}_{state}_r{n}"
                previous_path = MANIFEST.parent / (basename + ".meta.json")
                completed = [p for p in MANIFEST.parent.glob(basename + "*.meta.json")
                             if json.loads(p.read_text(encoding="utf-8")).get("valida")]
                if len(completed) > 1:
                    raise ValueError("Más de una réplica válida para la misma repetición; reconciliar antes de continuar")
                if completed:
                    continue
                if previous_path.exists():
                    previous = json.loads(previous_path.read_text(encoding="utf-8"))
                    suffix = 1
                    while (MANIFEST.parent / f"{basename}_reintento{suffix}.meta.json").exists():
                        suffix += 1
                    basename += f"_reintento{suffix}"
                os.environ.pop("CACHE_SEED_DB", None)
                os.environ.pop("CACHE_VACIA", None)
                if state == "vacia":
                    os.environ["CACHE_VACIA"] = "1"
                else:
                    os.environ["CACHE_SEED_DB"] = "f0_cache_" + config
                item = argparse.Namespace(arbol="/tmp/medida", db="run_" + basename,
                    salida=basename + ".json", variables=[f"{k}={v}" for k, v in zip(FLAGS, CONFIGS[config])] +
                    ["BETO_VENTANA_STRIDE=32", "CATALOG_DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/catalogo_copia"])
                print(json.dumps({"corrida": basename, "estado": "iniciando", "fecha": now()}), flush=True)
                execute(item)
                if not args.conservar_bases and not basename.startswith("f0_a123_llena_r1"):
                    # Respaldo recuperable privado antes de liberar tmpfs; nada personal en git.
                    dump = run("docker", "exec", "beto_pg_tmpfs", "pg_dump", "-U", "giragroup_user", "-d", item.db,
                               "--no-owner", "--no-privileges")
                    backup = PRIVATE / "corridas" / basename / "base.sql"
                    backup.write_text(dump, encoding="utf-8")
                    run("docker", "exec", "beto_pg_tmpfs", "dropdb", "-U", "giragroup_user", item.db)
                    meta_path = MANIFEST.parent / (basename + ".meta.json")
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    meta["clon_eliminado_tras_exportacion"] = True
                    meta["respaldo_privado"] = {"ruta": str(backup.relative_to(PRIVATE)), "sha256": digest(backup)}
                    write(meta_path, meta)
                print(json.dumps({"corrida": basename, "estado": "valida", "fecha": now()}), flush=True)


def series(args):
    import f0_mantener_activo as energy
    energy.bind_driver()
    try:
        return _series(args)
    finally:
        # También limpia al detenerse por una puerta o una excepción; el auxiliar
        # vigila el PID por si el proceso termina sin ejecutar finally.
        energy.request_stop()


def aggregate(args):
    directory = Path(args.directorio)
    rows, identity, invalid_runs = [], None, []
    for config in CONFIGS:
        for state in ("vacia", "llena"):
            samples, measurements = [], []
            candidates = sorted(directory.glob(f"{args.prefijo}_{config}_{state}_r*.meta.json"))
            valid_paths = []
            for candidate in candidates:
                candidate_meta = json.loads(candidate.read_text(encoding="utf-8"))
                if candidate_meta.get("valida"):
                    valid_paths.append(candidate.with_name(candidate.name.replace(".meta.json", ".json")))
                else:
                    invalid_runs.append({"id": candidate.name.replace(".meta.json", ""),
                        "metadatos": candidate.name, "configuracion": config, "estado": state,
                        "motivo": candidate_meta.get("motivo_invalida") or "No consta motivo de invalidez en metadatos"})
            if len(valid_paths) != 3:
                raise ValueError("Se requieren exactamente tres corridas válidas por celda")
            for path in valid_paths:
                data = json.loads(path.read_text(encoding="utf-8"))
                valid_result(data)
                meta = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
                footprint = json.loads(Path(str(path) + ".huella.json").read_text(encoding="utf-8"))
                if not meta.get("valida") or meta.get("configuracion") != config or meta.get("estado") != state:
                    raise ValueError("Metadatos de corrida inválidos")
                current = (meta["lote_sha256"], meta["arbol_sha256"], meta["modelo_sha256"], data["carga"]["registros_detectados"])
                identity = current if identity is None else identity
                if identity != current or not footprint.get("tablas") or "kpis" not in footprint:
                    raise ValueError("Identidad de lote/código/modelo distinta o huella incompleta")
                if tuple(meta["flags"][k] for k in FLAGS) != tuple(str(x) for x in CONFIGS[config]):
                    raise ValueError("Flags no corresponden a configuración")
                samples.append(data["total"]["tiempo_maquina_s"])
                measurements.append({"resultado": data, "huella": footprint})
            def numbers(obj, prefix=""):
                out = {}
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key not in ("id_lote", "revision_eventos"):
                            out.update(numbers(value, prefix + "." + key if prefix else key))
                elif obj is None or isinstance(obj, (int, float)) and not isinstance(obj, bool):
                    out[prefix] = obj
                return out
            flattened = [numbers(m) for m in measurements]
            # Estos tres KPI son obligatorios aunque todas las respuestas sean NULL,
            # estén ausentes o tengan un tipo no numérico inesperado.
            for flat, measurement in zip(flattened, measurements):
                for code in ("KPI-10", "KPI-11", "KPI-18"):
                    flat["huella.kpis." + code] = measurement["huella"].get("kpis", {}).get(code)
            metrics = {}
            for key in sorted(set().union(*(set(m) for m in flattened))):
                values = [m[key] for m in flattened if isinstance(m.get(key), (int, float)) and not isinstance(m.get(key), bool)]
                missing_reasons = []
                for flat, path, measurement in zip(flattened, valid_paths, measurements):
                    missing_kpi = key.startswith("huella.kpis.") and key.removeprefix("huella.kpis.") not in measurement["huella"].get("kpis", {})
                    if key not in flat or missing_kpi:
                        reason = "Métrica ausente en la respuesta de origen"
                    elif flat[key] is None:
                        reason = "NULL de origen: no hay valor observado; no se imputa cero"
                    elif not isinstance(flat[key], (int, float)) or isinstance(flat[key], bool):
                        reason = "Valor de origen no numérico; no se convierte ni imputa"
                    else:
                        continue
                    missing_reasons.append({"corrida": path.stem, "motivo": reason})
                metrics[key] = {"n": len(values), "media": statistics.mean(values) if values else None,
                                "de_muestral": statistics.stdev(values) if len(values) == 3 else None,
                                "ausencias": 3 - len(values), "motivos_ausencia": missing_reasons}
            rows.append({"configuracion": config, "estado": state, "n": 3,
                         "tiempo_maquina_s_media": statistics.mean(samples),
                         "tiempo_maquina_s_de_muestral": statistics.stdev(samples), "metricas": metrics,
                         "corridas": [{"id": p.stem, "resultado": p.name,
                            "metadatos": p.with_suffix(".meta.json").name,
                            "huella": p.name + ".huella.json"} for p in valid_paths]})
    write(args.salida, {"celdas": rows, "corridas_validas": 42, "identidad": identity,
                       "corridas_invalidas": invalid_runs,
                       "rnf03": "Solo máquina sin revisión; no certifica ciclo completo"})
    with Path(args.csv).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["configuracion", "estado", "metrica", "n", "media", "de_muestral", "ausencias", "motivos_ausencia"])
        w.writeheader()
        for row in rows:
            for key, value in row["metricas"].items():
                csv_value = dict(value, motivos_ausencia=json.dumps(value["motivos_ausencia"], ensure_ascii=False))
                w.writerow({"configuracion": row["configuracion"], "estado": row["estado"], "metrica": key, **csv_value})
    window = []
    for config in ("a2", "a2w"):
        for state in ("vacia", "llena"):
            for path in sorted(directory.glob(f"{args.prefijo}_{config}_{state}_r*.meta.json")):
                meta = json.loads(path.read_text(encoding="utf-8"))
                if not meta.get("valida"):
                    continue
                data = json.loads(path.with_name(path.name.replace(".meta.json", ".json")).read_text(encoding="utf-8"))
                for stage in ("lectura", "consolidacion"):
                    counts = data.get(stage + "_beto_contadores") or {}
                    total, missing = counts.get("comparadas_acuerdo"), counts.get("no_evaluables")
                    agree, disagree = counts.get("acuerdos"), counts.get("desacuerdos")
                    other = counts.get("tipo_distinto")
                    evaluable = agree + disagree if isinstance(agree, (float, int)) and isinstance(disagree, (float, int)) else None
                    reconciled = total == agree + disagree + other if all(isinstance(x, (float, int)) for x in (total, agree, disagree, other, missing)) else False
                    rate = missing / total if reconciled and total > 0 else None
                    window.append({"corrida": path.name.replace(".meta.json", ""), "configuracion": config, "estado": state,
                        "etapa": stage, "comparadas_acuerdo": total, "no_evaluables": missing,
                        "denominador_conciliado": reconciled, "fraccion_no_evaluable": rate,
                        "definicion_razon_puerta": "no_evaluables / comparadas_acuerdo según plan; razón entre contadores disjuntos, puede exceder 1",
                        "proporcion_no_evaluable_total_veredictos": missing / (total + missing) if reconciled and total + missing > 0 else None,
                        "definicion_codigo": "comparadas_acuerdo excluye no_evaluables; incluye acuerdos+desacuerdos+tipo_distinto",
                        "contradiccion_plan": "Plan describe inclusión de no_evaluables; código usa continue previo al contador. No se modifica lógica.",
                        "total_veredictos": total + missing if isinstance(total, (int, float)) and isinstance(missing, (int, float)) else None,
                        "cumple_menos_20_pct": rate < .20 if rate is not None else None,
                        "tasa_acuerdo_evaluable": agree / evaluable if evaluable else None,
                        "cobertura_evaluable": evaluable / (total + missing) if evaluable is not None and isinstance(total, (int, float)) and isinstance(missing, (int, float)) and total + missing > 0 else None,
                        "poblacion_cobertura": "comparadas_acuerdo + no_evaluables; todos los veredictos por persona de esta etapa",
                        "fraccion_acuerdo_desacuerdo_entre_comparadas": evaluable / total if evaluable is not None and total else None,
                        "ausencias": "Contadores ausentes/no conciliados: no evaluable" if rate is None else None})
    write(directory / "f0_ventana.json", {"etapas_separadas": True, "corridas": window})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("congelar")
    p.add_argument("--mes", default="2026-03")
    p.add_argument("--esperados", type=int, default=10)
    p.add_argument("--salida", default=str(MANIFEST))
    p = sub.add_parser("verificar")
    p.add_argument("--manifest", default=str(MANIFEST))
    p.add_argument("--base")
    p = sub.add_parser("agregar")
    p.add_argument("--directorio", required=True)
    p.add_argument("--prefijo", default="f0")
    p.add_argument("--salida", required=True)
    p.add_argument("--csv", required=True)
    p = sub.add_parser("restaurar-cache")
    p.add_argument("--db", required=True)
    p.add_argument("--seed")
    p.add_argument("--vacia", action="store_true")
    p = sub.add_parser("preparar-cache")
    p.add_argument("--configuraciones", default=",".join(CONFIGS))
    p.add_argument("--salida", required=True)
    p = sub.add_parser("huella-snapshot")
    p.add_argument("--origen", choices=("snapshot", "copia"), required=True)
    p.add_argument("--salida", required=True)
    p = sub.add_parser("series")
    p.add_argument("--conservar-bases", action="store_true")
    sub.add_parser("compactar-log")
    p = sub.add_parser("ejecutar")
    p.add_argument("arbol")
    p.add_argument("db")
    p.add_argument("salida")
    p.add_argument("variables", nargs="*")
    args = parser.parse_args()
    if args.cmd == "congelar":
        freeze(args)
    elif args.cmd == "verificar":
        print(json.dumps(verify(args.manifest, args.base)))
    elif args.cmd == "agregar":
        aggregate(args)
    elif args.cmd == "restaurar-cache":
        print(json.dumps(seed_cache(args.db, args.seed, args.vacia)))
    elif args.cmd == "ejecutar":
        execute(args)
    elif args.cmd == "huella-snapshot":
        snapshot_fingerprint(args.origen, args.salida)
    elif args.cmd == "series":
        series(args)
    elif args.cmd == "compactar-log":
        compact_log()
    else:
        prepare(args)


if __name__ == "__main__":
    main()
