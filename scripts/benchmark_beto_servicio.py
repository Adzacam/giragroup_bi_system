"""Benchmark del servicio BETO (POST /infer-batch) con distintas configuraciones de hilos y procesos.

Arranca procesos extra del servidor dentro de giragroup_pipeline (puertos 8011+), ejecuta el cliente desde giragroup_api
sobre las líneas distintas del lote, muestrea CPU/RAM del equipo y del contenedor, y al final mata los procesos extra.
El servidor de compose (8006, TORCH_NUM_THREADS=4) se usa como primer worker de las configuraciones de 4 hilos.

Uso (host, máquina sin carga; /tmp/lineas_distintas.json ya en giragroup_api): python scripts/benchmark_beto_servicio.py <carpeta_salida> [config1,config2]
"""
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from medir_flujo_repetido import muestreador, sh  # noqa: E402

CONFIGS = [  # (nombre, hilos por proceso, nº de procesos)
    ("a_4hilos_1proceso", 4, 1),
    ("a_lineas_completas_4hilos_1proceso", 4, 1),
    ("b_4hilos_2procesos", 4, 2),
    ("c_4hilos_3procesos", 4, 3),
    ("d_8hilos_1proceso", 8, 1),
]
LINEAS = "/tmp/textos_indice_distintos.json"  # texto de 8 celdas por línea distinta, el mismo que evalúa /indice
LINEAS_COMPLETAS = "/tmp/lineas_distintas.json"


def exec_pipeline(cmd, detach=False):
    return sh(["docker", "exec"] + (["-d"] if detach else []) + ["giragroup_pipeline", "sh", "-c", cmd])


def arrancar(puerto, hilos):
    exec_pipeline(f"cd /app && TORCH_NUM_THREADS={hilos} nohup python -m pipeline.semantic.inference_server --host 0.0.0.0 --port {puerto} "
                  f"> /tmp/beto_{puerto}.log 2>&1 &", detach=True)


def esperar_salud(puerto, timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = sh(["docker", "exec", "giragroup_api", "python", "-c",
                f"import urllib.request,json;print(json.load(urllib.request.urlopen('http://pipeline:{puerto}/health',timeout=5))['engine'])"])
        if r.returncode == 0 and "BETO_PYTORCH_REAL" in r.stdout:
            return True
        time.sleep(3)
    return False


def matar_extras():
    exec_pipeline("for p in /proc/[0-9]*; do if tr '\\0' ' ' < $p/cmdline 2>/dev/null | grep -q -- '--port 801'; then kill -9 ${p#/proc/}; fi; done; true")


def recursos(m, nombre):
    def est(k):
        v = [x[k] for x in m if k in x]
        return {"media": round(sum(v) / len(v), 1), "max": max(v)} if v else None
    return {k: est(k) for k in ("host_cpu_pct", "host_ram_usada_gib", f"{nombre}_cpu_pct", f"{nombre}_ram_mib")} | {"muestras": len(m)}


def main(salida, solo=None):
    import medir_flujo_repetido as mfr
    mfr.CONTENEDORES = ("giragroup_pipeline", "giragroup_api")
    out = Path(salida)
    out.mkdir(parents=True, exist_ok=True)
    sh(["docker", "cp", str(ROOT / "scripts/benchmark_beto_cliente.py"), "giragroup_api:/app/scripts/"])
    previo = out / "resumen.json"
    resultados = json.loads(previo.read_text(encoding="utf-8")) if solo and previo.exists() else []
    for nombre, hilos, procesos in CONFIGS:
        if solo and nombre not in solo:
            continue
        matar_extras()
        if hilos == 4:
            puertos = [8006] + [8011 + i for i in range(procesos - 1)]
            extras = puertos[1:]
        else:
            puertos = [8011 + i for i in range(procesos)]
            extras = puertos
        for p, _ in zip(extras, range(len(extras))):
            arrancar(p, hilos)
        ok = all(esperar_salud(p) for p in puertos)
        if not ok:
            resultados.append({"config": nombre, "error": "algún servidor no levantó"})
            continue
        # calentamiento: un lote pequeño por puerto
        sh(["docker", "exec", "giragroup_api", "python", "-c",
            "import json,urllib.request,sys\n" + "\n".join(
                f"urllib.request.urlopen(urllib.request.Request('http://pipeline:{p}/infer-batch',data=json.dumps({{'textos':['Juan Perez | POS-5887']*8}}).encode(),headers={{'Content-Type':'application/json'}}),timeout=120).read()" for p in puertos)])
        time.sleep(10)
        muestras, parar = [], threading.Event()
        th = threading.Thread(target=muestreador, args=(parar, muestras))
        th.start()
        entrada = LINEAS_COMPLETAS if "completas" in nombre else LINEAS
        r = sh(["docker", "exec", "giragroup_api", "python", "/app/scripts/benchmark_beto_cliente.py", entrada, f"/tmp/bench_{nombre}.json"] + [str(p) for p in puertos])
        parar.set()
        th.join()
        sh(["docker", "cp", f"giragroup_api:/tmp/bench_{nombre}.json", str(out / f"cliente_{nombre}.json")])
        (out / f"recursos_{nombre}.json").write_text(json.dumps(muestras), encoding="utf-8")
        try:
            cliente = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            cliente = {"error": r.stdout[-300:] + r.stderr[-300:]}
        resultados.append({"config": nombre, "hilos": hilos, "procesos": procesos, "puertos": puertos, "entrada": entrada, "cliente": cliente,
                           "recursos": recursos(muestras, "giragroup_pipeline")})
        print(nombre, cliente.get("lineas_por_s"), flush=True)
        (out / "resumen.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
    matar_extras()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2].split(",") if len(sys.argv) > 2 else None)
