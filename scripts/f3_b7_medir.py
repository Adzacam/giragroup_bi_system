"""F3-5 (B-7): Medición final del ciclo mensual (RNF-03) bajo protocolo f2r_g6_protocolo_b7.md.
Ejecuta 3 corridas con caché vacía + 3 corridas con caché llena sobre clones tmpfs (dw_vacio + 016),
registrando psutil + docker stats cada 5 s, 30 s de reposo entre corridas, huella_dw_v2 y KLM canónico.
"""

import hashlib
import json
import statistics as st
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from agregar_flujo_repetido import klm  # noqa: E402

MED = ROOT / "docs" / "mediciones"
DIR_SCRIPTS = "/tmp/flujo"
CONTENEDORES = ("giragroup_api", "giragroup_pipeline", "beto_pg_tmpfs")
INTERVALO = 5
REPOSO_S = 30
BETO_MODEL_SHA_PREF = "9ff7fb9d"
LOTE_SHA_PREF = "aafde8ad"


def sh(cmd, timeout=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")


def psql_tmpfs(base, sql=None, archivo=None):
    cmd = ["docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", base, "-v", "ON_ERROR_STOP=1", "-q"]
    cmd += ["-c", sql] if sql else ["-f", archivo]
    r = sh(cmd)
    if r.returncode:
        raise RuntimeError(r.stderr[-400:])


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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


def ms(vals):
    return {
        "valores": [round(v, 2) for v in vals],
        "media": round(st.mean(vals), 2),
        "de": round(st.stdev(vals), 2) if len(vals) > 1 else 0.0,
        "min": round(min(vals), 2),
        "max": round(max(vals), 2),
    }


def main():
    sh(["docker", "cp", str(ROOT / "scripts" / "huella_dw_v2.py"), f"giragroup_api:{DIR_SCRIPTS}/scripts/huella_dw_v2.py"])
    sh(["docker", "cp", str(ROOT / "backend/scripts/migrations/016_b9_descartes_y_homonimos.sql"), "beto_pg_tmpfs:/tmp/016.sql"])

    huella_ref = json.loads((MED / "f3_base.json.huella.json").read_text(encoding="utf-8"))
    modelo_sha_antes = sha256_file(ROOT / "pipeline/semantic/beto_local/model.safetensors")
    manifest = json.loads((MED / "f0_lote_manifest.json").read_text(encoding="utf-8"))
    stats_antes = sh(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}"]).stdout.splitlines()

    # Asegurar f3_base si hace falta para exportar cache_indice_beto
    existe_f3_base = sh(["docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", "postgres", "-Atc", "SELECT 1 FROM pg_database WHERE datname='f3_base'"]).stdout.strip()
    if existe_f3_base != "1":
        psql_tmpfs("postgres", "create database f3_base template dw_vacio")
        psql_tmpfs("f3_base", archivo="/tmp/016.sql")
        psql_tmpfs("f3_base", "TRUNCATE TABLE public.cache_indice_beto; DROP TABLE IF EXISTS public.cache_beto_entidades")
        r_base = sh([
            "docker", "exec", "giragroup_api", "env",
            "PYTHONHASHSEED=0", "BETO_CASCADA_FINAL=0", "BETO_ACUERDO_QC=0", "BETO_SUGERENCIA_HITL=0", "BETO_VENTANA=0",
            "DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/f3_base",
            "FLUJO_SIN_REVISION=1", "CICLO_REUSAR_SLICES=1", "CICLO_FILAS_SIN_FECHA=0",
            "CICLO_SLICES=/tmp/slices_flujo", f"PYTHONPATH=/app:/app/pipeline:{DIR_SCRIPTS}/scripts",
            "sh", "-c", f"cd /app && python {DIR_SCRIPTS}/scripts/medir_flujo_dataops.py /tmp/f3_base.json",
        ])
        if r_base.returncode != 0:
            raise RuntimeError(f"Falló f3_base: {r_base.stderr[-400:]}")
    sh(["docker", "exec", "beto_pg_tmpfs", "sh", "-c", "pg_dump -U giragroup_user -d f3_base -t public.cache_indice_beto --data-only > /tmp/cache_f3.sql"])

    resultados = {"vacia": [], "llena": []}
    for modo in ("vacia", "llena"):
        for idx in range(1, 4):
            p_json = MED / f"f3_b7_corrida_{modo}_r{idx}.json"
            p_huella = MED / f"f3_b7_corrida_{modo}_r{idx}.huella.json"
            p_rec = MED / f"f3_b7_corrida_{modo}_r{idx}.recursos.json"
            if p_json.exists() and p_huella.exists() and p_rec.exists():
                d = json.loads(p_json.read_text(encoding="utf-8"))
                h = json.loads(p_huella.read_text(encoding="utf-8"))
                muestras = json.loads(p_rec.read_text(encoding="utf-8"))
                diffs = [k for k in huella_ref["tablas"] if huella_ref["tablas"][k] != h["tablas"].get(k)]
                cpus = [m["host_cpu_pct"] for m in muestras if "host_cpu_pct" in m]
                resultados[modo].append({
                    "corrida": idx,
                    "duracion_pared_s": d["total"]["tiempo_maquina_s"],
                    "tiempo_maquina_s": d["total"]["tiempo_maquina_s"],
                    "etapas_s": d["etapas_s"],
                    "diffs_huella_vs_f3_base": diffs,
                    "bandeja": {k: v for k, v in h["bandeja"].items() if k != "firma"},
                    "kpis": h["kpis"],
                    "host_cpu_avg_pct": round(st.mean(cpus), 1) if cpus else None,
                    "host_cpu_max_pct": max(cpus) if cpus else None,
                })
                print(f"[{modo} r{idx}] reutilizado: maquina={d['total']['tiempo_maquina_s']}s diffs={diffs}", flush=True)
                continue
            base = f"f3_b7_{modo}_{idx}"
            psql_tmpfs("postgres", f"drop database if exists {base}")
            psql_tmpfs("postgres", f"create database {base} template dw_vacio")
            psql_tmpfs(base, archivo="/tmp/016.sql")
            psql_tmpfs(base, "TRUNCATE TABLE public.cache_indice_beto; DROP TABLE IF EXISTS public.cache_beto_entidades")
            if modo == "llena":
                psql_tmpfs(base, archivo="/tmp/cache_f3.sql")

            time.sleep(REPOSO_S)
            muestras, parar = [], threading.Event()
            th = threading.Thread(target=muestreador, args=(parar, muestras))
            th.start()
            t0 = time.time()
            r = sh([
                "docker", "exec", "giragroup_api", "env",
                "PYTHONHASHSEED=0",
                "BETO_CASCADA_FINAL=0", "BETO_ACUERDO_QC=0", "BETO_SUGERENCIA_HITL=0", "BETO_VENTANA=0",
                f"DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/{base}",
                "FLUJO_SIN_REVISION=1", "CICLO_REUSAR_SLICES=1", "CICLO_FILAS_SIN_FECHA=0",
                "CICLO_SLICES=/tmp/slices_flujo", f"PYTHONPATH=/app:/app/pipeline:{DIR_SCRIPTS}/scripts",
                "sh", "-c",
                f"cd /app && python {DIR_SCRIPTS}/scripts/medir_flujo_dataops.py /tmp/b7_{modo}_{idx}.json && "
                f"python {DIR_SCRIPTS}/scripts/huella_dw_v2.py /tmp/b7_{modo}_{idx}.huella.json",
            ])
            dur_pared = round(time.time() - t0, 2)
            parar.set()
            th.join()

            sh(["docker", "cp", f"giragroup_api:/tmp/b7_{modo}_{idx}.json", str(p_json)])
            sh(["docker", "cp", f"giragroup_api:/tmp/b7_{modo}_{idx}.huella.json", str(p_huella)])
            p_rec.write_text(json.dumps(muestras, ensure_ascii=False), encoding="utf-8")
            psql_tmpfs("postgres", f"drop database if exists {base}")

            if r.returncode != 0:
                raise RuntimeError(f"Falló {base}: {r.stderr[-400:]}")
            d = json.loads(p_json.read_text(encoding="utf-8"))
            h = json.loads(p_huella.read_text(encoding="utf-8"))
            diffs = [k for k in huella_ref["tablas"] if huella_ref["tablas"][k] != h["tablas"].get(k)]
            cpus = [m["host_cpu_pct"] for m in muestras if "host_cpu_pct" in m]
            resultados[modo].append({
                "corrida": idx,
                "duracion_pared_s": dur_pared,
                "tiempo_maquina_s": d["total"]["tiempo_maquina_s"],
                "etapas_s": d["etapas_s"],
                "diffs_huella_vs_f3_base": diffs,
                "bandeja": {k: v for k, v in h["bandeja"].items() if k != "firma"},
                "kpis": h["kpis"],
                "host_cpu_avg_pct": round(st.mean(cpus), 1) if cpus else None,
                "host_cpu_max_pct": max(cpus) if cpus else None,
            })
            print(f"[{modo} r{idx}] maquina={d['total']['tiempo_maquina_s']}s diffs={diffs}", flush=True)

    modelo_sha_despues = sha256_file(ROOT / "pipeline/semantic/beto_local/model.safetensors")
    stats_despues = sh(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}"]).stdout.splitlines()

    resumen_modos = {}
    for modo, runs in resultados.items():
        resumen_modos[modo] = {
            "n": len(runs),
            "tiempo_maquina_s": ms([x["tiempo_maquina_s"] for x in runs]),
            "carga_s": ms([x["etapas_s"]["carga_s"] for x in runs]),
            "lectura_beto_s": ms([x["etapas_s"]["lectura_beto_s"] for x in runs]),
            "consolidacion_s": ms([x["etapas_s"]["consolidacion_s"] for x in runs]),
            "todas_huellas_identicas_f3_base": all(len(x["diffs_huella_vs_f3_base"]) == 0 for x in runs),
        }

    (MED / "f3_b7_corridas.json").write_text(json.dumps({
        "etiqueta": "F3, final",
        "tarea": "F3-5 (B-7)",
        "protocolo": "docs/mediciones/f2r_g6_protocolo_b7.md",
        "lote_manifest": manifest.get("lote_sha256") or LOTE_SHA_PREF,
        "modelo_beto_v2_sha256": {"antes": modelo_sha_antes, "despues": modelo_sha_despues, "prefijo_ok": modelo_sha_antes.startswith(BETO_MODEL_SHA_PREF)},
        "docker_stats_antes": stats_antes,
        "docker_stats_despues": stats_despues,
        "corridas": resultados,
        "resumen": resumen_modos,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    # KLM sobre la bandeja de f3_base usando eventos_v2 de f1_d3b_klm.json (misma firma 680/19)
    klm_ref = json.loads((MED / "f1_d3b_klm.json").read_text(encoding="utf-8"))
    eventos = klm_ref["versiones"]["v2"]["eventos"]
    k_con, d_con = klm(eventos, True)
    k_sin, d_sin = klm(eventos, False)
    (MED / "f3_b7_klm.json").write_text(json.dumps({
        "etiqueta": "F3, final",
        "tarea": "F3-5 (B-7 KLM)",
        "fuente_formula": "scripts/agregar_flujo_repetido.py::klm",
        "bandeja": {"casos": 680, "grupos": 19, "manuales": 14, "casos_manuales": 47},
        "con_espera_W_10s": {"total_s": k_con, "desglose_s": d_con},
        "sin_espera_W_0s": {"total_s": k_sin, "desglose_s": d_sin},
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    maq_vacia_media = resumen_modos["vacia"]["tiempo_maquina_s"]["media"]
    tot_w10 = round(maq_vacia_media + k_con, 2)
    tot_w0 = round(maq_vacia_media + k_sin, 2)
    (MED / "f3_b7_rnf03.json").write_text(json.dumps({
        "etiqueta": "F3, final",
        "tarea": "F3-5 (RNF-03 dos números)",
        "solo_maquina": {
            "cache_vacia_media_s": maq_vacia_media,
            "cache_llena_media_s": resumen_modos["llena"]["tiempo_maquina_s"]["media"],
            "cumple_900s": maq_vacia_media <= 900,
            "cumple_1200s": maq_vacia_media <= 1200,
        },
        "maquina_mas_klm": {
            "con_espera_W_10s_s": tot_w10,
            "cumple_900s_W10": tot_w10 <= 900,
            "cumple_1200s_W10": tot_w10 <= 1200,
            "sin_espera_W_0s_s": tot_w0,
            "cumple_900s_W0": tot_w0 <= 900,
            "cumple_1200s_W0": tot_w0 <= 1200,
        },
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print("[OK] B-7 completo", flush=True)


if __name__ == "__main__":
    main()
