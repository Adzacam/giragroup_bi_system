#!/usr/bin/env python3
"""
Script de medición reproducible de latencia Backend (FastAPI + Gateway)
Sistema BI GiraGroup - Auditoría de Rendimiento

Calcula p50, p95, p99, media, máximo, RPS y tamaño de payload bajo concurrencia N
para los endpoints críticos del CMI, Riesgos, Forecast, DataOps, Reportes y Auditoría.
Utiliza `httpx.AsyncClient` si está instalado o `urllib.request` + `ThreadPoolExecutor`
de la librería estándar como fallback automático.

Uso:
  python docs/performance/scripts/measure_backend.py \
      --base-url http://localhost:8000 \
      --concurrency 10 \
      --requests 50 \
      --output docs/performance/scripts/backend_benchmark_results.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    import httpx  # type: ignore
except ImportError:
    httpx = None


@dataclass
class EndpointSpec:
    name: str
    method: str
    path: str
    timeout: float = 60.0


ENDPOINTS: List[EndpointSpec] = [
    EndpointSpec("Health Check", "GET", "/health"),
    EndpointSpec("CMI Completo (11 KPIs + Charts)", "GET", "/api/v1/kpis/cmi-completo"),
    EndpointSpec("CMI Perspectivas", "GET", "/api/v1/kpis/perspectivas"),
    EndpointSpec("Alertas Tempranas (Reglas A/D/F)", "GET", "/api/v1/riesgos/alertas-tempranas"),
    EndpointSpec("Riesgo Cruzado", "GET", "/api/v1/riesgos/cruzado"),
    EndpointSpec("Ficha Estudiante #1", "GET", "/api/v1/riesgos/ficha-estudiante/1"),
    EndpointSpec("Forecast Alumnos (HW)", "GET", "/api/v1/forecast/alumnos?horizonte=6"),
    EndpointSpec("Forecast Metas Mensual (HW)", "GET", "/api/v1/forecast/metas?horizonte=6&granularidad=MENSUAL"),
    EndpointSpec("Forecast Analítica Macro (5 HW + 2 OLS)", "GET", "/api/v1/forecast/analitica-macro?horizonte=6"),
    EndpointSpec("DataOps Sources Status", "GET", "/api/v1/dataops/sources"),
    EndpointSpec("DataOps Quarantine / Review Tray", "GET", "/api/v1/dataops/review-tray"),
    EndpointSpec("Reportes Export KPIs (XLSX)", "GET", "/api/v1/reportes/export?tipo=kpis&formato=xlsx"),
    EndpointSpec("Audit Logs (limit=200)", "GET", "/api/v1/audit/logs?limit=200"),
]


def percentile(sorted_values: List[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)


def summarize_metrics(
    spec: EndpointSpec,
    total_requests: int,
    concurrency: int,
    latencies_ms: List[float],
    payload_sizes: List[int],
    status_counts: Dict[int, int],
    errors: int,
    wall_elapsed: float,
) -> Dict[str, object]:
    sorted_lat = sorted(latencies_ms)
    return {
        "name": spec.name,
        "method": spec.method,
        "path": spec.path,
        "requests": total_requests,
        "concurrency": concurrency,
        "errors": errors,
        "statuses": str(status_counts),
        "p50_ms": round(percentile(sorted_lat, 50), 2),
        "p95_ms": round(percentile(sorted_lat, 95), 2),
        "p99_ms": round(percentile(sorted_lat, 99), 2),
        "mean_ms": round(statistics.mean(sorted_lat), 2) if sorted_lat else 0.0,
        "min_ms": round(sorted_lat[0], 2) if sorted_lat else 0.0,
        "max_ms": round(sorted_lat[-1], 2) if sorted_lat else 0.0,
        "avg_bytes": int(statistics.mean(payload_sizes)) if payload_sizes else 0,
        "rps": round(total_requests / max(wall_elapsed, 1e-6), 2),
    }


def _stdlib_single_request(
    base_url: str, spec: EndpointSpec, headers: Dict[str, str]
) -> Tuple[float, int, Optional[int], bool]:
    url = f"{base_url.rstrip('/')}{spec.path}"
    req = urllib.request.Request(url, headers=headers, method=spec.method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=spec.timeout) as resp:
            body = resp.read()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            code = resp.getcode() or 200
            return elapsed_ms, len(body), code, code >= 500
    except urllib.error.HTTPError as http_err:
        body = http_err.read() if http_err.fp else b""
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return elapsed_ms, len(body), http_err.code, http_err.code >= 500
    except Exception:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return elapsed_ms, 0, None, True


def benchmark_endpoint_stdlib(
    base_url: str,
    spec: EndpointSpec,
    total_requests: int,
    concurrency: int,
    headers: Dict[str, str],
) -> Dict[str, object]:
    latencies_ms: List[float] = []
    payload_sizes: List[int] = []
    status_counts: Dict[int, int] = {}
    errors = 0

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(_stdlib_single_request, base_url, spec, headers)
            for _ in range(total_requests)
        ]
        for fut in futures:
            elapsed_ms, size_b, code, is_err = fut.result()
            latencies_ms.append(elapsed_ms)
            if code is not None:
                payload_sizes.append(size_b)
                status_counts[code] = status_counts.get(code, 0) + 1
            if is_err:
                errors += 1
    wall_elapsed = time.perf_counter() - wall_start

    return summarize_metrics(
        spec, total_requests, concurrency, latencies_ms, payload_sizes, status_counts, errors, wall_elapsed
    )


async def benchmark_endpoint_httpx(
    client: "httpx.AsyncClient",
    spec: EndpointSpec,
    total_requests: int,
    concurrency: int,
    headers: Dict[str, str],
) -> Dict[str, object]:
    sem = asyncio.Semaphore(concurrency)
    latencies_ms: List[float] = []
    payload_sizes: List[int] = []
    status_counts: Dict[int, int] = {}
    errors = 0

    async def worker() -> None:
        nonlocal errors
        async with sem:
            t0 = time.perf_counter()
            try:
                resp = await client.request(
                    spec.method,
                    spec.path,
                    headers=headers,
                    timeout=spec.timeout,
                )
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                latencies_ms.append(elapsed_ms)
                payload_sizes.append(len(resp.content))
                status_counts[resp.status_code] = status_counts.get(resp.status_code, 0) + 1
                if resp.status_code >= 500:
                    errors += 1
            except Exception:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                latencies_ms.append(elapsed_ms)
                errors += 1

    wall_start = time.perf_counter()
    await asyncio.gather(*(worker() for _ in range(total_requests)))
    wall_elapsed = time.perf_counter() - wall_start

    return summarize_metrics(
        spec, total_requests, concurrency, latencies_ms, payload_sizes, status_counts, errors, wall_elapsed
    )


async def run_suite(
    base_url: str,
    concurrency: int,
    requests_per_endpoint: int,
    token: Optional[str],
    output_csv: Optional[str],
) -> int:
    headers: Dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Verificar conectividad inicial
    probe_spec = EndpointSpec("Health Check", "GET", "/health", timeout=5.0)
    _, _, code, is_err = _stdlib_single_request(base_url, probe_spec, headers)
    if code is None:
        print(
            f"[AVISO] No se pudo conectar a {base_url}. "
            "Asegúrese de que los contenedores Docker estén activos (`docker compose up -d`).",
            file=sys.stderr,
        )
        return 2

    driver_name = "httpx.AsyncClient" if httpx is not None else "urllib.request + ThreadPoolExecutor"
    print(f"[OK] Conectado a {base_url} (/health -> HTTP {code}) | Motor HTTP: {driver_name}")

    results: List[Dict[str, object]] = []
    print(
        f"\nEjecutando benchmark ({requests_per_endpoint} reqs/endpoint, concurrencia={concurrency})...\n"
    )
    header_fmt = (
        f"{'Endpoint':<40} | {'p50(ms)':>8} | {'p95(ms)':>8} | "
        f"{'p99(ms)':>8} | {'Max(ms)':>8} | {'Bytes':>8} | {'RPS':>6}"
    )
    print(header_fmt)
    print("-" * len(header_fmt))

    if httpx is not None:
        limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
        async with httpx.AsyncClient(base_url=base_url.rstrip("/"), limits=limits) as client:
            for spec in ENDPOINTS:
                res = await benchmark_endpoint_httpx(
                    client=client,
                    spec=spec,
                    total_requests=requests_per_endpoint,
                    concurrency=concurrency,
                    headers=headers,
                )
                results.append(res)
                print(
                    f"{str(res['name'])[:40]:<40} | "
                    f"{res['p50_ms']:>8.1f} | "
                    f"{res['p95_ms']:>8.1f} | "
                    f"{res['p99_ms']:>8.1f} | "
                    f"{res['max_ms']:>8.1f} | "
                    f"{res['avg_bytes']:>8d} | "
                    f"{res['rps']:>6.1f}"
                )
    else:
        for spec in ENDPOINTS:
            res = benchmark_endpoint_stdlib(
                base_url=base_url,
                spec=spec,
                total_requests=requests_per_endpoint,
                concurrency=concurrency,
                headers=headers,
            )
            results.append(res)
            print(
                f"{str(res['name'])[:40]:<40} | "
                f"{res['p50_ms']:>8.1f} | "
                f"{res['p95_ms']:>8.1f} | "
                f"{res['p99_ms']:>8.1f} | "
                f"{res['max_ms']:>8.1f} | "
                f"{res['avg_bytes']:>8d} | "
                f"{res['rps']:>6.1f}"
            )

    if output_csv and results:
        os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
        print(f"\n[OK] Resultados exportados a: {output_csv}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de latencia p50/p95/p99 para FastAPI GiraGroup")
    parser.add_argument("--base-url", default=os.getenv("BENCH_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--requests", type=int, default=30)
    parser.add_argument("--token", default=os.getenv("BENCH_BEARER_TOKEN"))
    parser.add_argument("--output", default=None, help="Ruta opcional para guardar CSV de resultados")
    args = parser.parse_args()

    rc = asyncio.run(
        run_suite(
            base_url=args.base_url,
            concurrency=args.concurrency,
            requests_per_endpoint=args.requests,
            token=args.token,
            output_csv=args.output,
        )
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
