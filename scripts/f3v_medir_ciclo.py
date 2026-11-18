"""V-7(a,b,c): Medición definitiva de f3_base (2 corridas, misma huella),
B-7 (3 corridas caché vacía + 3 corridas caché llena) y KLM (W=p95 medido, W=0, W=10).
"""
import hashlib
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
sys.path.insert(0, str(ROOT))
import scripts.agregar_flujo_repetido as afr  # noqa: E402

OUT = ROOT / "output" / "f3v"
OUT.mkdir(parents=True, exist_ok=True)
MED = ROOT / "docs" / "mediciones"
TMPFS = "beto_pg_tmpfs"
DIR_SCRIPTS = "/tmp/flujo_v7"
SLICES = "/tmp/slices_f3v"
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
        m = {
            "t": round(time.time(), 1),
            "host_cpu_pct": psutil.cpu_percent(interval=None),
            "host_ram_mb": round(psutil.virtual_memory().used / 1048576, 1),
        }
        r = sh(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}", *CONTENEDORES], timeout=15)
        for linea in r.stdout.splitlines():
            p = linea.split("|")
            if len(p) == 3:
                m[p[0]] = {"cpu": p[1].strip(), "mem": p[2].split("/")[0].strip()}
        muestras.append(m)
        parar.wait(INTERVALO)


def huella_sha(h: dict) -> str:
    payload = {k: h[k] for k in ("tablas", "bandeja", "kpis", "kpis_todos") if k in h}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def correr_una(base: str, modo: str, etiqueta: str) -> dict:
    psql("postgres", f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{base}' AND pid <> pg_backend_pid()")
    psql("postgres", f"DROP DATABASE IF EXISTS {base}")
    psql("postgres", f"CREATE DATABASE {base} TEMPLATE dw_vacio")
    psql(base, "TRUNCATE TABLE public.cache_indice_beto")
    if modo == "llena":
        sh(["docker", "cp", str(OUT / "cache_f3v_base.sql"), f"{TMPFS}:/tmp/cache_f3v_base.sql"])
        psql(base, archivo="/tmp/cache_f3v_base.sql")
    cache_n = int(sh(["docker", "exec", TMPFS, "psql", "-U", "giragroup_user", "-d", base, "-Atc",
                      "SELECT count(*) FROM public.cache_indice_beto"]).stdout.strip() or 0)
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
        f"CICLO_SLICES={SLICES}", f"PYTHONPATH=/app:/app/pipeline:{DIR_SCRIPTS}",
        "sh", "-c",
        f"cd /app && python {DIR_SCRIPTS}/medir_flujo_dataops.py /tmp/v7_{etiqueta}.json && "
        f"python {DIR_SCRIPTS}/huella_dw_v2.py /tmp/v7_{etiqueta}.huella_v2.json",
    ])
    dur = round(time.time() - t0, 2)
    parar.set()
    th.join(timeout=10)
    (OUT / f"{etiqueta}.log").write_text((r.stdout or "") + "\n--- stderr ---\n" + (r.stderr or ""), encoding="utf-8")
    sh(["docker", "cp", f"giragroup_api:/tmp/v7_{etiqueta}.json", str(OUT / f"{etiqueta}.json")])
    sh(["docker", "cp", f"giragroup_api:/tmp/v7_{etiqueta}.huella_v2.json", str(OUT / f"{etiqueta}.huella_v2.json")])
    (OUT / f"{etiqueta}.muestras.json").write_text(json.dumps(muestras, indent=1), encoding="utf-8")

    med = json.loads((OUT / f"{etiqueta}.json").read_text(encoding="utf-8"))
    hue = json.loads((OUT / f"{etiqueta}.huella_v2.json").read_text(encoding="utf-8"))
    sha_h = huella_sha(hue)
    t_maq = med.get("total", {}).get("tiempo_maquina_s", dur)
    print(f"[{etiqueta}] rc={r.returncode} cache={cache_n} maq={t_maq}s pared={dur}s huella={sha_h[:12]}", flush=True)
    return {
        "etiqueta": etiqueta,
        "modo": modo,
        "cache_filas_inicio": cache_n,
        "returncode": r.returncode,
        "duracion_pared_s": dur,
        "tiempo_maquina_s": t_maq,
        "etapas_s": med.get("etapas_s", {}),
        "dw_despues": med.get("dw_despues", {}),
        "huella_v2_sha256": sha_h,
    }


def ms(xs):
    return {"media": round(st.mean(xs), 2), "desv": round(st.stdev(xs), 2) if len(xs) > 1 else 0.0, "n": len(xs)}


def main():
    # 1. f3_base: 2 corridas
    b1 = correr_una("f3v_base_r1", "vacia", "base_r1")
    sh(["docker", "exec", TMPFS, "pg_dump", "-U", "giragroup_user", "-d", "f3v_base_r1", "-t", "public.cache_indice_beto",
        "--data-only", "--inserts", "-f", "/tmp/cache_f3v_base.sql"])
    sh(["docker", "cp", f"{TMPFS}:/tmp/cache_f3v_base.sql", str(OUT / "cache_f3v_base.sql")])
    b2 = correr_una("f3v_base_r2", "vacia", "base_r2")
    assert b1["huella_v2_sha256"] == b2["huella_v2_sha256"], "Huellas de base_r1 y base_r2 difieren!"

    base_out = {
        "tarea": "V-7(a)",
        "fecha": "2026-11-18",
        "recorte": "2026-03",
        "corridas": [b1, b2],
        "huella_identica": b1["huella_v2_sha256"] == b2["huella_v2_sha256"],
        "huella_v2_sha256": b1["huella_v2_sha256"],
        "resumen_tiempo_maquina_s": ms([b1["tiempo_maquina_s"], b2["tiempo_maquina_s"]]),
    }
    (MED / "f3v_base.json").write_text(json.dumps(base_out, indent=2, ensure_ascii=False), encoding="utf-8")

    # 2. B-7: 3 vacia + 3 llena
    vacias = [correr_una(f"f3v_b7_vacia_r{i}", "vacia", f"b7_vacia_r{i}") for i in (1, 2, 3)]
    llenas = [correr_una(f"f3v_b7_llena_r{i}", "llena", f"b7_llena_r{i}") for i in (1, 2, 3)]

    # 3. KLM con W=p95 medido de f3v_locust.json
    loc = json.loads((MED / "f3v_locust.json").read_text(encoding="utf-8"))
    pe = loc.get("por_endpoint", {})
    p95_g = pe.get("GET /api/v1/dataops/review-tray/grupos", {}).get("p95_ms", 0)
    p95_a = pe.get("POST /api/v1/dataops/review-tray/approve-group", {}).get("p95_ms", 0)
    w_med = round(max(p95_g, p95_a) / 1000.0, 4)

    h_ref = json.loads((OUT / "base_r1.huella_v2.json").read_text(encoding="utf-8"))
    ev = [{"accion": a, "casos": n} for _, a, n in h_ref["bandeja"]["firma"]]

    def _klm(w):
        afr.W_DESHACER = w
        t, dsg = afr.klm(ev, con_espera=True)
        return {"W_s": w, "klm_s": t, "desglose_s": dsg}

    klm_out = {
        "tarea": "V-7(c)",
        "W_medido_p95_s": w_med,
        "W_medido": _klm(w_med),
        "W_0": _klm(0.0),
        "W_10": _klm(10.0),
    }
    (MED / "f3v_klm.json").write_text(json.dumps(klm_out, indent=2, ensure_ascii=False), encoding="utf-8")

    st_v = ms([x["tiempo_maquina_s"] for x in vacias])
    st_l = ms([x["tiempo_maquina_s"] for x in llenas])
    klm_s = klm_out["W_medido"]["klm_s"]
    tot_v_s = round(st_v["media"] + klm_s, 2)
    tot_l_s = round(st_l["media"] + klm_s, 2)
    b7_out = {
        "tarea": "V-7(b)",
        "fecha": "2026-11-18",
        "corridas": {"vacia": vacias, "llena": llenas},
        "huella_unica_en_todas": len({x["huella_v2_sha256"] for x in vacias + llenas}) == 1,
        "resumen": {
            "vacia_maquina_s": st_v,
            "llena_maquina_s": st_l,
            "klm_W_medido_s": klm_s,
            "vacia_mas_klm_s": tot_v_s,
            "vacia_mas_klm_min": round(tot_v_s / 60, 2),
            "llena_mas_klm_s": tot_l_s,
            "llena_mas_klm_min": round(tot_l_s / 60, 2),
            "cumple_rnf03_15min": tot_v_s < 900,
            "cumple_aceptable_20min": tot_v_s < 1200,
        },
    }
    (MED / "f3v_b7_corridas.json").write_text(json.dumps(b7_out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("OK f3v_medir_ciclo:", json.dumps(b7_out["resumen"], ensure_ascii=False))


if __name__ == "__main__":
    main()
