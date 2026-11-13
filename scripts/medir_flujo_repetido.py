"""Repite N veces la medición del flujo DataOps (10 archivos) sobre copias aisladas del snapshot con el DW reiniciado,
registrando CPU y RAM del equipo (psutil) y de los contenedores (docker stats) cada INTERVALO s.

Uso (host, sin otras cargas): python scripts/medir_flujo_repetido.py <carpeta_salida> [N=3] [desde=1]
Cada corrida: crea clon_rep_<i> desde el snapshot, vacía el DW, aplica la migración 014, ejecuta medir_flujo_dataops.py en giragroup_api y borra el clon.
"""
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = "snapshot_dw_20261110_1201"
INTERVALO = 5
CONTENEDORES = ("giragroup_api", "giragroup_db")  # contenedores muestreados con docker stats
TRUNC = ("public.fact_rendimiento_academico, public.fact_situacion_financiera, public.fact_evaluacion_docente, public.fact_marketing, "
         "public.fact_rentabilidad, public.fact_forecast, public.fact_cobranzas_proyectadas, public.stg_entidad_no_resuelta, "
         "public.staging_registros_crudos, public.log_pipeline_ingesta, public.log_inconsistencias, public.log_auditoria_nlp, "
         "public.dim_origen_documental, public.lote, public.dataops_tarea")


def sh(cmd, timeout=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")


def psql(usuario, base, sql=None, archivo=None):
    cmd = ["docker", "exec", "giragroup_db", "psql", "-U", usuario, "-d", base, "-v", "ON_ERROR_STOP=1", "-q"]
    cmd += ["-c", sql] if sql else ["-f", archivo]
    r = sh(cmd)
    if r.returncode:
        raise RuntimeError(r.stderr[-400:])


def muestreador(parar, muestras):
    psutil.cpu_percent(None)
    while not parar.is_set():
        t0 = time.time()
        cpu = psutil.cpu_percent(None)
        mem = psutil.virtual_memory()
        d = sh(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}"], 30).stdout.splitlines()
        cont = {}
        for ln in d:
            n, c, m = (ln.split("|") + ["", ""])[:3]
            if n in CONTENEDORES:
                usado = m.split("/")[0].strip()
                mb = float(usado[:-3]) * (1024 if usado.endswith("GiB") else 1) if usado[-3:] in ("MiB", "GiB") else 0
                cont[n] = {"cpu_pct": float(c.strip("%") or 0), "ram_mib": round(mb, 1)}
        muestras.append({"t": round(time.time(), 1), "host_cpu_pct": cpu, "host_ram_usada_gib": round(mem.used / 2**30, 2),
                         "host_ram_pct": mem.percent, **{f"{k}_{m}": v[m] for k, v in cont.items() for m in v}})
        parar.wait(max(0.1, INTERVALO - (time.time() - t0)))


def resumen_recursos(m):
    def est(k):
        v = [x[k] for x in m if k in x]
        return {"media": round(sum(v) / len(v), 1), "max": max(v)} if v else None
    return {k: est(k) for k in ("host_cpu_pct", "host_ram_usada_gib", "giragroup_api_cpu_pct", "giragroup_api_ram_mib",
                                "giragroup_db_cpu_pct", "giragroup_db_ram_mib")} | {"muestras": len(m)}


def main(salida, n, desde=1):
    out = Path(salida)
    out.mkdir(parents=True, exist_ok=True)
    usuario = sh(["docker", "exec", "giragroup_db", "printenv", "POSTGRES_USER"]).stdout.strip()
    previo = out / "corridas.json"
    corridas = json.loads(previo.read_text(encoding="utf-8")) if desde > 1 and previo.exists() else []
    for i in range(desde, n + 1):
        base = f"clon_rep_{i}"
        psql(usuario, "postgres", f"drop database if exists {base}")
        psql(usuario, "postgres", f"create database {base} template {SNAPSHOT}")
        psql(usuario, base, f"TRUNCATE TABLE {TRUNC} RESTART IDENTITY CASCADE")
        sh(["docker", "cp", str(ROOT / "backend/scripts/migrations/014_conversion_captacion_comprobable.sql"), "giragroup_db:/tmp/014.sql"])
        psql(usuario, base, archivo="/tmp/014.sql")
        for nombre in ("medir_flujo_dataops.py", "huella_dw.py", "simular_revision.py"):
            sh(["docker", "cp", str(ROOT / "scripts" / nombre), "giragroup_api:/app/scripts/"])
        time.sleep(30)  # reposo para que el muestreo parta con la máquina estable
        muestras, parar = [], threading.Event()
        th = threading.Thread(target=muestreador, args=(parar, muestras))
        th.start()
        t0 = time.time()
        cmd = (f'cd /app && export DATABASE_URL=$(echo $DATABASE_URL | sed "s#/giragroup_db\\$#/{base}#") && '
               f'CICLO_REUSAR_SLICES=1 CICLO_FILAS_SIN_FECHA=0 CICLO_SLICES=/tmp/slices_flujo PYTHONPATH=/app:/app/scripts python scripts/medir_flujo_dataops.py /tmp/flujo_{i}.json')
        r = sh(["docker", "exec", "giragroup_api", "sh", "-c", cmd])
        dur = time.time() - t0
        parar.set()
        th.join()
        sh(["docker", "cp", f"giragroup_api:/tmp/flujo_{i}.json", str(out / f"flujo_corrida_{i}.json")])
        sh(["docker", "cp", f"giragroup_api:/tmp/flujo_{i}.json.huella.json", str(out / f"huella_corrida_{i}.json")])
        (out / f"recursos_corrida_{i}.json").write_text(json.dumps(muestras), encoding="utf-8")
        psql(usuario, "postgres", f"drop database if exists {base}")
        corridas.append({"corrida": i, "duracion_total_s": round(dur, 1), "salida": r.stdout[-300:], "recursos": resumen_recursos(muestras)})
        print(f"corrida {i} lista en {dur:.0f} s", flush=True)
        (out / "corridas.json").write_text(json.dumps(corridas, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
