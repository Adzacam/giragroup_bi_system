"""
tests/load/locust_readiness.py
------------------------------
Escenarios de carga de la auditoría de producción (2026-11-01):

  a) CMIUser     50 usuarios concurrentes sobre /api/v1/kpis/cmi-completo (umbral p95 < 3 s).
  b) IngestaUser lotes multiarchivo a /api/v1/dataops/upload-batch, archivos abiertos en streaming
                 (requests envía el descriptor sin cargarlo entero en memoria).
  c) BetoUser    inferencia directa contra el servidor BETO (:8006) con umbral < 20 ms/oración
                 y confianza media >= 0,92.

Token: el login exige OTP, así que se emite un JWT de prueba desde el contenedor:
  docker exec giragroup_api python -c "from core.security import create_access_token;print(create_access_token({'sub':'1'}))"

Ejecución (gateway en :80):
  LOCUST_TOKEN=<jwt> locust -f tests/load/locust_readiness.py --host http://localhost \
      --users 50 --spawn-rate 10 --run-time 2m --headless CMIUser
  LOCUST_TOKEN=<jwt> locust -f tests/load/locust_readiness.py --host http://localhost \
      --users 3 --spawn-rate 1 --run-time 3m --headless IngestaUser
  BETO_HOST=http://<ip-del-contenedor-pipeline>:8006 locust -f tests/load/locust_readiness.py \
      --users 20 --spawn-rate 5 --run-time 1m --headless BetoUser

IngestaUser crea lotes reales en el DW: correrlo solo contra un entorno desechable y luego
ejecutar scripts/reset_dw.py.
"""

import os
import statistics
from pathlib import Path

from locust import HttpUser, task, between, events

TOKEN = os.getenv("LOCUST_TOKEN", "")
BETO_HOST = os.getenv("BETO_HOST", "http://localhost:8006")
DIR_ARCHIVOS = Path(os.getenv("LOCUST_UPLOAD_DIR", Path(__file__).resolve().parents[2] / "uploads" / "test"))

UMBRAL_P95_MS = 3000
UMBRAL_BETO_MS = 20
UMBRAL_BETO_CONFIANZA = 0.92

_latencias_beto: list = []
_confianzas_beto: list = []


class _ConToken(HttpUser):
    abstract = True

    def on_start(self):
        if not TOKEN:
            raise RuntimeError("Defina LOCUST_TOKEN (ver docstring)")
        self.client.headers["Authorization"] = f"Bearer {TOKEN}"


class CMIUser(_ConToken):
    wait_time = between(0.5, 1.5)

    @task(4)
    def cmi_completo(self):
        self.client.get("/api/v1/kpis/cmi-completo", name="CMI completo")

    @task(1)
    def cmi_filtrado(self):
        self.client.get("/api/v1/kpis/cmi-completo", params={"gestion": 2025}, name="CMI completo (gestión)")


class IngestaUser(_ConToken):
    wait_time = between(5, 10)

    @task
    def lote_multiarchivo(self):
        rutas = sorted(DIR_ARCHIVOS.glob("*.xlsx"))[:3]
        if not rutas:
            return
        descriptores = [open(r, "rb") for r in rutas]
        try:
            archivos = [
                ("files", (r.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
                for r, f in zip(rutas, descriptores)
            ]
            with self.client.post("/api/v1/dataops/upload-batch", files=archivos,
                                  data={"institucion": "GiraGroup Posgrado"},
                                  name="Ingesta lote x3", timeout=600, catch_response=True) as r:
                if r.status_code == 409:  # hash SHA-256 duplicado: rechazo esperado al repetir el lote
                    r.success()
        finally:
            for f in descriptores:
                f.close()


class BetoUser(HttpUser):
    host = BETO_HOST
    wait_time = between(0.05, 0.2)
    TEXTOS = [
        "JUAN PEREZ MAMANI CI 4567890 DIPLOMADO EN GESTION DE PROYECTOS NOTA 78",
        "MARIA LOPEZ 1234567 MAESTRIA EN SALUD PUBLICA MODULO 3 APROBADO 85",
        "CURSO EXCEL AVANZADO PAGO 350 BS CUOTA 2 PENDIENTE",
    ]

    @task
    def inferir(self):
        for texto in self.TEXTOS:
            with self.client.post("/infer", json={"text": texto}, name="BETO /infer", catch_response=True) as r:
                if r.status_code != 200:
                    r.failure(f"HTTP {r.status_code}")
                    continue
                cuerpo = r.json()
                _latencias_beto.append(cuerpo.get("latency_ms", 0.0))
                _confianzas_beto.extend(e["score"] for e in cuerpo.get("entities", []))


@events.quitting.add_listener
def _evaluar_umbrales(environment, **_):
    fallos = []
    for nombre, stats in environment.stats.entries.items():
        if nombre[0].startswith("CMI") and stats.num_requests:
            p95 = stats.get_response_time_percentile(0.95)
            if p95 >= UMBRAL_P95_MS:
                fallos.append(f"{nombre[0]}: p95 {p95:.0f} ms >= {UMBRAL_P95_MS}")
    if _latencias_beto:
        p50 = statistics.median(_latencias_beto)
        if p50 >= UMBRAL_BETO_MS:
            fallos.append(f"BETO: p50 {p50:.1f} ms/oración >= {UMBRAL_BETO_MS}")
    if _confianzas_beto and statistics.mean(_confianzas_beto) < UMBRAL_BETO_CONFIANZA:
        fallos.append(f"BETO: confianza media {statistics.mean(_confianzas_beto):.3f} < {UMBRAL_BETO_CONFIANZA}")
    if environment.stats.total.fail_ratio > 0.01:
        fallos.append(f"Tasa de error {environment.stats.total.fail_ratio:.1%} > 1 %")
    for f in fallos:
        print(f"[UMBRAL] {f}")
    if fallos:
        environment.process_exit_code = 1
