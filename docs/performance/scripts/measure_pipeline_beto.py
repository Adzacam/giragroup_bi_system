#!/usr/bin/env python3
"""
Script de medición reproducible del Pipeline Semántico BETO (:8006)
Sistema BI GiraGroup - Auditoría de Rendimiento

Evalúa:
  1) Cold-start vs Warm latency de `/infer`, `/infer-batch` y `/indice` via HTTP (:8006).
  2) Barrido de tamaño de lote (`batch_size` = 1, 8, 16, 32, 64, 128) para encontrar
     el punto óptimo de throughput (textos/segundo).
Utiliza `httpx` si está disponible o `urllib.request` de la librería estándar como fallback.

Uso:
  python docs/performance/scripts/measure_pipeline_beto.py --url http://localhost:8006
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, List, Tuple

try:
    import httpx  # type: ignore
except ImportError:
    httpx = None

SAMPLE_TEXTS: List[str] = [
    "ESTUDIANTE: JUAN CARLOS PEREZ GOMEZ | CI: 7845123 LP | DIPLOMADO EN GERENCIA DE PROYECTOS | MODULO I: FORMULACION | NOTA FINAL: 84 | ASISTENCIA: 92% | MONTO PAGADO: Bs. 1500 | SALDO: Bs. 300",
    "ALUMNA MARIA FERNANDA ROJAS VARGAS DOCENTE ING. ROBERTO CARLOS MENDOZA PROGRAMA EXPERTO EN BIM MODULO III PRESUPUESTOS PROMEDIO 65 REPROBADO CUOTAS VENCIDAS 2",
    "PAGO REGISTRADO COMPROBANTE NRO 004512 ESTUDIANTE LUIS ALBERTO TORREZ MONTO Bs. 850.00 FECHA 2025-03-14 CONCEPTO CUOTA 2 DIPLOMADO FINANZAS CORPORATIVAS",
    "ACTA DE CALIFICACIONES GESTION 2025-I DOCENTE DRA. CLAUDIA PATRICIA SALAZAR ASIGNATURA ESTADISTICA APLICADA ESTUDIANTE ANA GABRIELA MAMANI FLORES NOTA 91 APROBADO",
]


def generate_batch(size: int) -> List[str]:
    return [SAMPLE_TEXTS[i % len(SAMPLE_TEXTS)] for i in range(size)]


def _http_get(url: str, timeout: float = 5.0) -> Tuple[int, str]:
    if httpx is not None:
        r = httpx.get(url, timeout=timeout)
        return r.status_code, r.text
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.getcode() or 200, resp.read().decode("utf-8", errors="replace")


def _http_post_json(url: str, payload: Dict[str, object], timeout: float = 180.0) -> int:
    if httpx is not None:
        r = httpx.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.status_code
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        resp.read()
        return resp.getcode() or 200


def benchmark_http_pipeline(base_url: str, batch_sizes: List[int], iterations: int) -> int:
    url = base_url.rstrip("/")
    try:
        code, body = _http_get(f"{url}/health", timeout=5.0)
        print(f"[OK] Pipeline BETO activo en {url} (/health -> HTTP {code}: {body.strip()})")
    except Exception as exc:
        print(
            f"[AVISO] No se pudo conectar al contenedor pipeline en {url} ({exc}).\n"
            "Para ejecutar esta medición inicie el servicio: `docker compose up -d pipeline`",
            file=sys.stderr,
        )
        return 2

    # 1. Medir /infer individual (warm-up + iteraciones)
    print("\n=== 1. Latencia Unitaria POST /infer ===")
    t0 = time.perf_counter()
    _http_post_json(f"{url}/infer", {"texto": SAMPLE_TEXTS[0], "umbral_confianza": 0.85})
    cold_ms = (time.perf_counter() - t0) * 1000.0

    unit_latencies: List[float] = []
    for _ in range(iterations):
        t_start = time.perf_counter()
        _http_post_json(f"{url}/infer", {"texto": SAMPLE_TEXTS[0], "umbral_confianza": 0.85})
        unit_latencies.append((time.perf_counter() - t_start) * 1000.0)

    p95_idx = min(len(unit_latencies) - 1, int(len(unit_latencies) * 0.95))
    print(
        f"Primera llamada (Cold/Warm check): {cold_ms:.1f} ms | "
        f"Media ({iterations} reqs): {statistics.mean(unit_latencies):.1f} ms | "
        f"p95: {sorted(unit_latencies)[p95_idx]:.1f} ms"
    )

    # 2. Barrido de tamaño de lote en /infer-batch y /indice
    print("\n=== 2. Barrido de Tamaño de Lote (/infer-batch vs /indice) ===")
    header = f"{'Endpoint':<15} | {'Batch Size':>10} | {'Latencia(ms)':>14} | {'ms / texto':>12} | {'Textos / seg':>14}"
    print(header)
    print("-" * len(header))

    for endpoint in ("/infer-batch", "/indice"):
        for bsize in batch_sizes:
            textos = generate_batch(bsize)
            payload: Dict[str, object] = {"textos": textos}
            if endpoint == "/infer-batch":
                payload["umbral_confianza"] = 0.85

            runs_ms: List[float] = []
            for _ in range(max(1, iterations // 2)):
                t_b = time.perf_counter()
                _http_post_json(f"{url}{endpoint}", payload)
                runs_ms.append((time.perf_counter() - t_b) * 1000.0)

            avg_ms = statistics.mean(runs_ms)
            ms_per_text = avg_ms / bsize
            tps = (bsize / avg_ms) * 1000.0 if avg_ms > 0 else 0.0
            print(
                f"{endpoint:<15} | {bsize:>10d} | {avg_ms:>14.1f} | {ms_per_text:>12.2f} | {tps:>14.1f}"
            )

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark reproducible del servicio BETO (:8006)")
    parser.add_argument("--url", default=os.getenv("BETO_SERVICE_URL", "http://localhost:8006"))
    parser.add_argument(
        "--batch-sizes",
        default="1,8,16,32,64,128",
        help="Tamaños de lote separados por coma",
    )
    parser.add_argument("--iterations", type=int, default=6)
    args = parser.parse_args()

    sizes = [int(x.strip()) for x in args.batch_sizes.split(",") if x.strip()]
    rc = benchmark_http_pipeline(base_url=args.url, batch_sizes=sizes, iterations=args.iterations)
    sys.exit(rc)


if __name__ == "__main__":
    main()
