"""Cliente del benchmark de POST /infer-batch: reparte lotes de 256 líneas entre varios servidores (uno por hilo) y mide líneas/s.

Uso (en giragroup_api): python scripts/benchmark_beto_cliente.py <lineas.json> <salida.json> puerto1 [puerto2 ...]
"""
import json
import queue
import sys
import threading
import time
import urllib.request

LOTE = 256


def main(ruta_lineas, salida, puertos):
    lineas = json.load(open(ruta_lineas, encoding="utf-8"))
    cola = queue.Queue()
    for i in range(0, len(lineas), LOTE):
        cola.put(lineas[i:i + LOTE])
    res = {"lineas": len(lineas), "lotes": cola.qsize(), "puertos": puertos, "errores": 0, "entidades": 0, "sin_entidades": 0,
           "latencias_ms_por_oracion_servidor": [], "por_puerto": {p: 0 for p in puertos}}
    lock = threading.Lock()

    def trabajador(puerto):
        url = f"http://pipeline:{puerto}/infer-batch"
        while True:
            try:
                lote = cola.get_nowait()
            except queue.Empty:
                return
            req = urllib.request.Request(url, data=json.dumps({"textos": lote}).encode("utf-8"),
                                         headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=600) as r:
                    j = json.loads(r.read().decode("utf-8"))
                with lock:
                    res["por_puerto"][puerto] += len(lote)
                    if j.get("status") != "success":
                        res["errores"] += len(lote)
                    for x in j.get("resultados", []):
                        n = len(x.get("entities") or [])
                        res["entidades"] += n
                        res["sin_entidades"] += n == 0
                    res["latencias_ms_por_oracion_servidor"].append(j.get("latency_ms_por_oracion"))
            except Exception as e:
                with lock:
                    res["errores"] += len(lote)
                    res.setdefault("mensajes", []).append(str(e)[:200])

    t0 = time.perf_counter()
    hilos = [threading.Thread(target=trabajador, args=(p,)) for p in puertos]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    res["segundos"] = round(time.perf_counter() - t0, 2)
    res["lineas_por_s"] = round(len(lineas) / res["segundos"], 2)
    lat = [x for x in res.pop("latencias_ms_por_oracion_servidor") if x is not None]
    res["ms_por_oracion_servidor_media"] = round(sum(lat) / len(lat), 2) if lat else None
    json.dump(res, open(salida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], [int(p) for p in sys.argv[3:]])
