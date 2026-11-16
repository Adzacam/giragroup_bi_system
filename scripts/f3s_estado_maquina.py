"""S-7 (F3S): estado de la máquina antes de una corrida (solo lectura).
Mide carga de CPU en reposo durante N s (psutil), CPU por proceso agrupado por nombre, procesos pesados fuera de Docker,
contenedores en marcha y plan de energía. No cambia ningún ajuste del sistema.
Uso: python scripts/f3s_estado_maquina.py <salida.json> [segundos=40]
Sale con código 3 si hay un proceso pesado ajeno no aceptado (lista PESADOS) o la CPU ajena en reposo es alta.
"""
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import psutil

PESADOS = re.compile(r"valorant|riot|vgc|steam|epicgames|epic games|pytest|locust|vite|jupyter", re.I)
NAVEGADORES = re.compile(r"^(brave|chrome|msedge|firefox|opera)(\.exe)?$", re.I)
ACEPTADOS = re.compile(r"^discord", re.I)
UMBRAL_REPOSO_PCT = 10.0      # CPU total del host en reposo por encima de esto: no se empieza
UMBRAL_PROCESO_PCT = 3.0      # % del host (24 núcleos = 100 %) para considerar un proceso "pesado"


def main(salida, segundos=40):
    ncpu = psutil.cpu_count()
    procs = {}
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            p.cpu_percent(None)
            procs[p.pid] = p
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    psutil.cpu_percent(None)
    muestras = []
    t0 = time.time()
    while time.time() - t0 < segundos:
        time.sleep(5)
        muestras.append(psutil.cpu_percent(None))
    por_nombre = defaultdict(lambda: {"n": 0, "cpu_pct_host": 0.0, "ram_mb": 0.0})
    for pid, p in procs.items():
        try:
            c = p.cpu_percent(None) / ncpu
            n = p.name()
            por_nombre[n]["n"] += 1
            por_nombre[n]["cpu_pct_host"] += c
            por_nombre[n]["ram_mb"] += p.memory_info().rss / 1048576
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    top = sorted(({"proceso": k, **{kk: round(vv, 2) for kk, vv in v.items()}} for k, v in por_nombre.items()
                  if k.lower() not in ("system idle process", "idle")), key=lambda x: -x["cpu_pct_host"])[:20]
    pesados, alertas = [], []
    for k, v in por_nombre.items():
        if k.lower() in ("system idle process", "idle"):
            continue
        if PESADOS.search(k):
            pesados.append({"proceso": k, "n": v["n"], "cpu_pct_host": round(v["cpu_pct_host"], 2)})
        elif NAVEGADORES.match(k) and (v["cpu_pct_host"] >= UMBRAL_PROCESO_PCT):
            pesados.append({"proceso": k, "n": v["n"], "cpu_pct_host": round(v["cpu_pct_host"], 2), "motivo": "navegador con CPU >= 3 %"})
        elif not ACEPTADOS.match(k) and v["cpu_pct_host"] >= UMBRAL_PROCESO_PCT and k.lower() not in ("vmmemwsl", "vmmem", "com.docker.backend"):
            alertas.append({"proceso": k, "cpu_pct_host": round(v["cpu_pct_host"], 2)})
    docker = subprocess.run(["docker", "ps", "--format", "{{.Names}}|{{.Status}}"], capture_output=True, text=True).stdout.split("\n")
    stats = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}"],
                           capture_output=True, text=True).stdout.splitlines()
    plan = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, encoding="cp850", errors="replace").stdout.strip()
    bat = psutil.sensors_battery()
    reposo = round(sum(muestras) / len(muestras), 1) if muestras else None
    out = {"fecha_epoch": round(t0, 1), "fecha": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t0)),
           "reposo_s": segundos, "cpu_host_reposo_media_pct": reposo, "cpu_host_reposo_max_pct": max(muestras) if muestras else None,
           "muestras_pct": muestras, "nucleos_logicos": ncpu, "top_procesos_cpu": top,
           "pesados_ajenos": pesados, "otros_procesos_con_cpu_ge_3pct": alertas,
           "discord_presente": any(ACEPTADOS.match(k) for k in por_nombre),
           "contenedores": [d for d in docker if d], "docker_stats": stats,
           "plan_energia": plan, "plan_energia_cambiado": False,
           "en_corriente_ac": (bat.power_plugged if bat else None),
           "apto": not pesados and not alertas and (reposo is not None and reposo < UMBRAL_REPOSO_PCT),
           "criterio_apto": f"sin pesados ajenos (juegos, lanzadores, pytest/locust/vite, navegador >= {UMBRAL_PROCESO_PCT} %), "
                            f"ningún otro proceso >= {UMBRAL_PROCESO_PCT} % salvo Discord, CPU host en reposo < {UMBRAL_REPOSO_PCT} %"}
    Path(salida).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("fecha", "cpu_host_reposo_media_pct", "cpu_host_reposo_max_pct", "pesados_ajenos",
                                          "otros_procesos_con_cpu_ge_3pct", "plan_energia", "en_corriente_ac", "apto")}, ensure_ascii=False))
    print("top:", [(x["proceso"], x["cpu_pct_host"]) for x in top[:8]])
    sys.exit(0 if out["apto"] else 3)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 40)
