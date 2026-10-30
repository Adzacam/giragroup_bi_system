"""
locustfile.py
Pruebas de carga concurrentes para el sistema GiraGroup BI segun la Tabla 3.35.
Evalua 6 endpoints criticos con concurrencia escalable de 5 a 50 usuarios durante 60 segundos.
"""

from locust import HttpUser, task, between, events


class GiraGroupLoadUser(HttpUser):
    wait_time = between(0.1, 0.5)
    token = None

    def on_start(self):
        """Autenticacion inicial del usuario virtual para llamadas protegidas."""
        try:
            res1 = self.client.post(
                "/api/v1/auth/login",
                json={"email": "loadtest@giragroup.bo", "password": "giragroup2026"},
                name="/api/v1/auth/login"
            )
            if res1.status_code == 200:
                data1 = res1.json()
                if "access_token" in data1:
                    self.token = data1.get("access_token")
                elif "temp_token" in data1:
                    res2 = self.client.post(
                        "/api/v1/auth/verify-otp",
                        json={"temp_token": data1.get("temp_token"), "code": "123456", "remember_device": True},
                        name="/api/v1/auth/verify-otp"
                    )
                    if res2.status_code == 200:
                        self.token = res2.json().get("access_token")
        except Exception:
            self.token = None

    def _auth_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(3)
    def test_health(self):
        """1. Health Check Gateway"""
        self.client.get("/health", name="[GET] /health")

    @task(2)
    def test_forecast_alumnos(self):
        """2. Forecast Alumnos (Holt-Winters)"""
        self.client.get("/api/v1/forecast/alumnos", headers=self._auth_headers(), name="[GET] /api/v1/forecast/alumnos")

    @task(2)
    def test_forecast_metas(self):
        """3. Forecast Metas (OLS / Holt-Winters)"""
        self.client.get("/api/v1/forecast/metas", headers=self._auth_headers(), name="[GET] /api/v1/forecast/metas")

    @task(2)
    def test_riesgos(self):
        """4. Alertas Tempranas Deterministicas"""
        self.client.get("/api/v1/riesgos/alertas-tempranas", headers=self._auth_headers(), name="[GET] /api/v1/riesgos/alertas-tempranas")

    @task(2)
    def test_kpis_cmi_completo(self):
        """5. KPIs CMI Completo"""
        self.client.get("/api/v1/kpis/cmi-completo", headers=self._auth_headers(), name="[GET] /api/v1/kpis/cmi-completo")

    @task(1)
    def test_audit_logs(self):
        """6. Logs de Auditoria y Trazabilidad"""
        self.client.get("/api/v1/audit/logs", headers=self._auth_headers(), name="[GET] /api/v1/audit/logs")
