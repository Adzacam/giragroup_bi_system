"""F2-6 (B-6): Repite N=3 veces la medición del flujo DataOps (10 archivos) sobre clones tmpfs de dw_vacio + 015 (B-9),
con caché vacía y los 4 flags en False, registrando tiempos máquina, recursos y cálculo KLM.
Nunca toca giragroup_db viva."""

import json
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "mediciones" / "f2_b6_flujo"
OUT_KLM = ROOT / "docs" / "mediciones" / "f2_b6_klm.json"
INTERVALO = 5
CONTENEDORES = ("giragroup_api", "beto_pg_tmpfs")
DIR_SCRIPTS = "/tmp/flujo"

# Parámetros KLM idénticos a scripts/agregar_flujo_repetido.py::klm
K, P, H, M, B = 0.28, 1.1, 0.4, 1.35, 0.1
W_DESHACER = 10.0
PAGINA = 5


def sh(cmd, timeout=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")


def psql_tmpfs(base, sql=None, archivo=None):
    cmd = ["docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", base, "-v", "ON_ERROR_STOP=1", "-q"]
    cmd += ["-c", sql] if sql else ["-f", archivo]
    r = sh(cmd)
    if r.returncode:
        raise RuntimeError(r.stderr[-400:])


def preparar_scripts():
    sh(["docker", "exec", "giragroup_api", "sh", "-c", f"mkdir -p {DIR_SCRIPTS}/scripts && ln -sfn /app/uploads {DIR_SCRIPTS}/uploads"])
    for nombre in ("medir_flujo_dataops.py", "huella_dw.py", "simular_revision.py", "medir_ciclo_mensual.py"):
        sh(["docker", "cp", str(ROOT / "scripts" / nombre), f"giragroup_api:{DIR_SCRIPTS}/scripts/"])


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


def calc_klm(eventos, w_deshacer):
    bloque = manual = corregir = mapear = pag = 0.0
    vistos = 0
    for ev in eventos:
        acc, cas = ev["accion"], ev["casos"]
        if acc == "APROBAR":
            bloque += H + M + P + B + M + P + B + w_deshacer
        elif acc == "CORREGIR_FECHA":
            corregir += H + M + P + B + M + (P + B + 6 * K) * cas + M + P + B + w_deshacer
        elif acc == "MAPEAR_ESTADO":
            mapear += H + M + P + B + M + (P + B + P + B) * cas + M + P + B + w_deshacer
        else:
            manual += (H + M + P + B + K + P + B + w_deshacer) * cas
        vistos += cas
        if vistos >= PAGINA:
            pag += H + M + P + B
            vistos %= PAGINA
    total = bloque + manual + corregir + mapear + pag
    return {
        "total_s": round(total, 1),
        "desglose_s": {
            "bloque": round(bloque, 1),
            "corregir_fecha": round(corregir, 1),
            "mapear_estado": round(mapear, 1),
            "manual": round(manual, 1),
            "paginacion": round(pag, 1),
        },
    }


def main(n=3):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    preparar_scripts()
    sh(["docker", "cp", str(ROOT / "backend/scripts/migrations/015_b9_descartes_y_homonimos.sql"), "beto_pg_tmpfs:/tmp/015.sql"])

    corridas = []
    for i in range(1, n + 1):
        base = f"dw_f2_rep_{i}"
        psql_tmpfs("postgres", f"drop database if exists {base}")
        psql_tmpfs("postgres", f"create database {base} template dw_vacio")
        psql_tmpfs(base, archivo="/tmp/015.sql")
        psql_tmpfs(base, "TRUNCATE TABLE public.cache_indice_beto; DROP TABLE IF EXISTS public.cache_beto_entidades")

        time.sleep(10)
        muestras, parar = [], threading.Event()
        th = threading.Thread(target=muestreador, args=(parar, muestras))
        th.start()
        t0 = time.time()
        r = sh([
            "docker", "exec", "giragroup_api", "env",
            "BETO_CASCADA_FINAL=0", "BETO_ACUERDO_QC=0", "BETO_SUGERENCIA_HITL=0", "BETO_VENTANA=0",
            f"DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/{base}",
            "FLUJO_SIN_REVISION=1", "CICLO_REUSAR_SLICES=1", "CICLO_FILAS_SIN_FECHA=0",
            "CICLO_SLICES=/tmp/slices_flujo", f"PYTHONPATH=/app:/app/pipeline:{DIR_SCRIPTS}/scripts",
            "sh", "-c", f"cd /app && python {DIR_SCRIPTS}/scripts/medir_flujo_dataops.py /tmp/f2_rep_{i}.json",
        ])
        dur = time.time() - t0
        parar.set()
        th.join()

        sh(["docker", "cp", f"giragroup_api:/tmp/f2_rep_{i}.json", str(OUT_DIR / f"flujo_corrida_{i}.json")])
        sh(["docker", "cp", f"giragroup_api:/tmp/f2_rep_{i}.json.huella.json", str(OUT_DIR / f"huella_corrida_{i}.json")])
        (OUT_DIR / f"recursos_corrida_{i}.json").write_text(json.dumps(muestras), encoding="utf-8")
        psql_tmpfs("postgres", f"drop database if exists {base}")

        flujo_data = json.loads((OUT_DIR / f"flujo_corrida_{i}.json").read_text(encoding="utf-8"))
        t_maq = flujo_data["total"]["tiempo_maquina_s"]
        corridas.append({
            "corrida": i,
            "duracion_total_s": round(dur, 1),
            "tiempo_maquina_s": t_maq,
            "huella_rc": r.returncode,
            "bandeja": flujo_data.get("bandeja"),
        })
        print(f"corrida {i} lista: pared={dur:.1f}s, maquina={t_maq}s", flush=True)
        (OUT_DIR / "corridas.json").write_text(json.dumps(corridas, indent=2, ensure_ascii=False), encoding="utf-8")

    # KLM sobre la bandeja de la corrida 1 usando los eventos de f1_d3b_klm v2 (misma bandeja 680/19)
    # o reconstruido desde f1_d3b_klm.json si la bandeja coincide (680/19).
    klm_ref = json.loads((ROOT / "docs" / "mediciones" / "f1_d3b_klm.json").read_text(encoding="utf-8"))
    eventos_v2 = klm_ref["versiones"]["v2"]["eventos"]
    klm_con_w = calc_klm(eventos_v2, W_DESHACER)
    klm_sin_w = calc_klm(eventos_v2, 0.0)
    tiempos_maq = [c["tiempo_maquina_s"] for c in corridas]
    media_maq = round(statistics.mean(tiempos_maq), 2)
    desv_maq = round(statistics.stdev(tiempos_maq), 2) if len(tiempos_maq) > 1 else 0.0

    resumen = {
        "etiqueta": "F2, provisional",
        "tarea": "F2-6 (B-6 / KLM N=3)",
        "base_datos": "clones tmpfs de dw_vacio + 015 (B-9), caché vacía, 4 flags False",
        "n_corridas": n,
        "corridas": corridas,
        "tiempo_maquina_s": {
            "media": media_maq,
            "desviacion_std": desv_maq,
            "min": min(tiempos_maq),
            "max": max(tiempos_maq),
            "meta_rnf03_s": 900,
            "cumple_solo_maquina": media_maq <= 900,
        },
        "klm_con_espera_W_10s": klm_con_w,
        "klm_sin_espera_W_0s": klm_sin_w,
        "tiempo_total_con_W_10s_s": round(media_maq + klm_con_w["total_s"], 1),
        "tiempo_total_sin_W_0s_s": round(media_maq + klm_sin_w["total_s"], 1),
        "referencia_f1_d3b_v2": {
            "tiempo_maquina_vacia_media_s": 864.283,
            "klm_con_W_10s_s": 736.6,
            "klm_sin_W_0s_s": 216.6,
            "v1_referencia_grupos_casos": "12 grupos / 182-188 casos / 490.5 s",
        },
    }
    OUT_KLM.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Escrito {OUT_KLM}")


if __name__ == "__main__":
    main(3)
