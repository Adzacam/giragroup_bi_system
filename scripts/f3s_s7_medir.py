"""S-7 (F3S): corridas del ciclo mensual 2026-03 sobre la tmpfs de S-7 (nunca la DW viva ni el snapshot).
Mismo procedimiento que scripts/f3_b7_medir.py (f3_base y B-7), con el nombre del contenedor tmpfs parametrizado.

  python scripts/f3s_s7_medir.py corrida <base> <vacia|llena> <etiqueta>
      clona dw_vacio -> <base>, aplica 016, vacía cache_indice_beto (llena: carga output/f3s/s7/cache_f3s_base.sql),
      reposo de 30 s, corre medir_flujo_dataops.py + huella_dw_v2.py en giragroup_api con PYTHONHASHSEED=0 y 4 flags BETO en 0,
      muestrea psutil + docker stats cada 5 s y deja todo en output/f3s/s7/<etiqueta>.*
  python scripts/f3s_s7_medir.py exportar_cache <base>      vuelca cache_indice_beto de <base> (para las corridas con caché llena)
  python scripts/f3s_s7_medir.py borrar <base>
Variables: TMPFS_NAME (beto_pg_s7), MANTENER=1 deja la base creada (para extraer y medir sobre ella).
"""
import json
import os
import statistics as st
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "f3s" / "s7"
OUT.mkdir(parents=True, exist_ok=True)
TMPFS = os.environ.get("TMPFS_NAME", "beto_pg_s7")
DIR_SCRIPTS = "/tmp/flujo_s7"
SLICES = "/tmp/slices_s7"
CONTENEDORES = ("giragroup_api", "giragroup_pipeline", TMPFS)
INTERVALO = 5
REPOSO_S = 30
ENV = dict(os.environ, MSYS_NO_PATHCONV="1")


def sh(cmd, timeout=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace", env=ENV)


def psql(base, sql=None, archivo=None):
    cmd = ["docker", "exec", TMPFS, "psql", "-U", "giragroup_user", "-d", base, "-v", "ON_ERROR_STOP=1", "-q"]
    cmd += ["-c", sql] if sql else ["-f", archivo]
    r = sh(cmd)
    if r.returncode:
        raise RuntimeError(r.stderr[-600:])
    return r.stdout


def muestreador(parar, muestras):
    psutil.cpu_percent(interval=None)
    while not parar.is_set():
        m = {"t": round(time.time(), 1), "host_cpu_pct": psutil.cpu_percent(interval=None),
             "host_ram_mb": round(psutil.virtual_memory().used / 1048576, 1)}
        r = sh(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}", *CONTENEDORES], timeout=15)
        for linea in r.stdout.splitlines():
            p = linea.split("|")
            if len(p) == 3:
                m[p[0]] = {"cpu": p[1].strip(), "mem": p[2].split("/")[0].strip()}
        muestras.append(m)
        parar.wait(INTERVALO)


def corrida(base, modo, etiqueta):
    sh(["docker", "cp", str(ROOT / "backend/scripts/migrations/016_b9_descartes_y_homonimos.sql"), f"{TMPFS}:/tmp/016.sql"])
    psql("postgres", f"drop database if exists {base}")
    psql("postgres", f"create database {base} template dw_vacio")
    psql(base, archivo="/tmp/016.sql")
    psql(base, "TRUNCATE TABLE public.cache_indice_beto; DROP TABLE IF EXISTS public.cache_beto_entidades")
    if modo == "llena":
        sh(["docker", "cp", str(OUT / "cache_f3s_base.sql"), f"{TMPFS}:/tmp/cache_f3s_base.sql"])
        psql(base, archivo="/tmp/cache_f3s_base.sql")
    cache_n = int(sh(["docker", "exec", TMPFS, "psql", "-U", "giragroup_user", "-d", base, "-Atc",
                      "SELECT count(*) FROM public.cache_indice_beto"]).stdout.strip() or 0)
    stats_antes = sh(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}"]).stdout.splitlines()
    time.sleep(REPOSO_S)
    muestras, parar = [], threading.Event()
    th = threading.Thread(target=muestreador, args=(parar, muestras))
    th.start()
    t0 = time.time()
    r = sh([
        "docker", "exec", "giragroup_api", "env",
        "PYTHONHASHSEED=0", "BETO_CASCADA_FINAL=0", "BETO_ACUERDO_QC=0", "BETO_SUGERENCIA_HITL=0", "BETO_VENTANA=0",
        f"DATABASE_URL=postgresql://giragroup_user:tmpfs_local@{TMPFS}:5432/{base}",
        f"CATALOG_DATABASE_URL=postgresql://giragroup_user:tmpfs_local@{TMPFS}:5432/catalogo_copia",
        "FLUJO_SIN_REVISION=1", "CICLO_REUSAR_SLICES=1", "CICLO_FILAS_SIN_FECHA=0",
        f"CICLO_SLICES={SLICES}", f"PYTHONPATH=/app:/app/pipeline:{DIR_SCRIPTS}/scripts",
        "sh", "-c",
        f"cd /app && python {DIR_SCRIPTS}/scripts/medir_flujo_dataops.py /tmp/s7_{etiqueta}.json && "
        f"python {DIR_SCRIPTS}/scripts/huella_dw_v2.py /tmp/s7_{etiqueta}.huella_v2.json",
    ])
    dur = round(time.time() - t0, 2)
    parar.set()
    th.join()
    (OUT / f"{etiqueta}.log").write_text((r.stdout or "") + "\n--- stderr ---\n" + (r.stderr or "")[-20000:], encoding="utf-8")
    for suf, dest in ((".json", ".json"), (".json.huella.json", ".huella_v1.json"), (".huella_v2.json", ".huella_v2.json")):
        sh(["docker", "cp", f"giragroup_api:/tmp/s7_{etiqueta}{suf}", str(OUT / f"{etiqueta}{dest}")])
    (OUT / f"{etiqueta}.recursos.json").write_text(json.dumps(muestras, ensure_ascii=False), encoding="utf-8")
    cpus = [m["host_cpu_pct"] for m in muestras]
    meta = {"base": base, "modo": modo, "etiqueta": etiqueta, "returncode": r.returncode, "duracion_pared_s": dur,
            "cache_indice_beto_al_iniciar": cache_n, "docker_stats_antes": stats_antes,
            "host_cpu_avg_pct": round(st.mean(cpus), 1) if cpus else None, "host_cpu_max_pct": max(cpus) if cpus else None,
            "n_muestras": len(muestras), "inicio_epoch": round(t0, 1)}
    (OUT / f"{etiqueta}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if os.environ.get("MANTENER") != "1":
        psql("postgres", f"drop database if exists {base}")
    print(json.dumps(meta, ensure_ascii=False)[:600], flush=True)
    if r.returncode != 0:
        raise SystemExit(f"Falló {base}: {(r.stderr or '')[-600:]}")


def exportar_cache(base):
    r = sh(["docker", "exec", TMPFS, "sh", "-c",
            f"pg_dump -U giragroup_user -d {base} -t public.cache_indice_beto --data-only > /tmp/cache_f3s_base.sql"])
    if r.returncode:
        raise SystemExit(r.stderr)
    sh(["docker", "cp", f"{TMPFS}:/tmp/cache_f3s_base.sql", str(OUT / "cache_f3s_base.sql")])
    print("cache exportada", (OUT / "cache_f3s_base.sql").stat().st_size)


if __name__ == "__main__":
    accion = sys.argv[1]
    if accion == "corrida":
        corrida(sys.argv[2], sys.argv[3], sys.argv[4])
    elif accion == "exportar_cache":
        exportar_cache(sys.argv[2])
    elif accion == "borrar":
        psql("postgres", f"drop database if exists {sys.argv[2]}")
