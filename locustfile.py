"""
locustfile.py
Pruebas de carga concurrentes para el sistema GiraGroup BI segun la Tabla 3.35.
Evalua 6 endpoints criticos con concurrencia escalable de 5 a 50 usuarios durante 60 segundos.
"""

import os

from gevent.lock import Semaphore
from locust import HttpUser, task, between, events

# Usuario semilla de QA (backend/seed_users.py, solo APP_ENV=test). La contraseña es QA_ADMIN_PASSWORD de .env.
QA_EMAIL = os.getenv("LOCUST_QA_EMAIL", "qa.admin@giragroup.bo")
QA_PASSWORD = os.getenv("QA_ADMIN_PASSWORD", "")


class GiraGroupLoadUser(HttpUser):
    wait_time = between(0.1, 0.5)
    token = None

    # El primer usuario virtual resuelve el 2FA real (OTP de pruebas que el login devuelve con APP_ENV=test)
    # y recuerda el dispositivo; los demás entran con ese device_token, sin pisarse el OTP de la misma cuenta.
    _device_token = None
    _lock_2fa = Semaphore()

    def _login(self, device_token=None):
        body = {"email": QA_EMAIL, "password": QA_PASSWORD}
        if device_token:
            body["device_token"] = device_token
        return self.client.post("/api/v1/auth/login", json=body, name="/api/v1/auth/login")

    def on_start(self):
        """Autenticacion inicial del usuario virtual para llamadas protegidas."""
        cls = GiraGroupLoadUser
        if cls._device_token is None:
            with cls._lock_2fa:
                if cls._device_token is None:
                    paso1 = self._login().json()
                    if paso1.get("mfa_required") and paso1.get("otp_test"):
                        paso2 = self.client.post(
                            "/api/v1/auth/verify-otp",
                            json={"temp_token": paso1["temp_token"], "code": paso1["otp_test"], "remember_device": True},
                            name="/api/v1/auth/verify-otp",
                        ).json()
                        cls._device_token = paso2.get("device_token")
                        self.token = paso2.get("access_token")
                        return
        res = self._login(cls._device_token)
        self.token = res.json().get("access_token") if res.status_code == 200 else None

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
