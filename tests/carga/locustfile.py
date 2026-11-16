"""Escenario reescrito de pruebas de carga con Locust (R3-8 / Tabla 3.32).

Simula 50 usuarios concurrentes consultando los endpoints principales del BI
y la bandeja de revisión DataOps para medir RPS, p50/p95/p99 y el tiempo de
respuesta del sistema W para el modelo KLM (J0-4).
"""
import os
from locust import HttpUser, between, task


class GiraGroupBIUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self):
        self.headers = {}
        token = os.environ.get("LOCUST_TOKEN", "").strip()
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self.grupo_clave = os.environ.get("LOCUST_GRUPO_CLAVE", "STG_SYNTHETIC::R3_8_PROBE")

    @task(2)
    def health(self):
        self.client.get("/health", name="GET /health")

    @task(3)
    def kpis_cmi(self):
        self.client.get("/api/v1/kpis/cmi-completo", headers=self.headers, name="GET /api/v1/kpis/cmi-completo")

    @task(3)
    def cmi_scorecard(self):
        self.client.get("/api/v1/cmi/scorecard?gestion=2025", headers=self.headers, name="GET /api/v1/cmi/scorecard")

    @task(2)
    def riesgos_alertas(self):
        self.client.get("/api/v1/riesgos/alertas-tempranas", headers=self.headers, name="GET /api/v1/riesgos/alertas-tempranas")

    @task(2)
    def forecast_alumnos(self):
        self.client.get("/api/v1/forecast/alumnos", headers=self.headers, name="GET /api/v1/forecast/alumnos")

    @task(2)
    def forecast_metas(self):
        self.client.get("/api/v1/forecast/metas", headers=self.headers, name="GET /api/v1/forecast/metas")

    @task(3)
    def review_tray_grupos(self):
        self.client.get(
            "/api/v1/dataops/review-tray/grupos",
            headers=self.headers,
            name="GET /api/v1/dataops/review-tray/grupos",
        )

    @task(1)
    def review_tray_approve_group(self):
        self.client.post(
            "/api/v1/dataops/review-tray/approve-group",
            json={"clave": self.grupo_clave},
            headers=self.headers,
            name="POST /api/v1/dataops/review-tray/approve-group",
        )
