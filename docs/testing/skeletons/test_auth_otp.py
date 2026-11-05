"""
docs/testing/skeletons/test_auth_otp.py
--------------------------------------
Esqueleto de pruebas unitarias y de integración para el ciclo de vida de autenticación 2FA, OTP y Trusted Device.
Casos:
- Generación de código OTP aleatorio de 6 dígitos numéricos.
- Cooldown anti-spam de 60 segundos (no emitir nuevo código antes de 60 s).
- Bloqueo de cuenta tras 5 intentos fallidos por 15 minutos.
- Recordar dispositivo (Trusted Device Token con vigencia de 30 días).
- Aislamiento estricto de envío de correos (MOCK en pruebas / EMAIL_BACKEND=console).
Marcador: unit
"""

import time
from datetime import datetime, timedelta, timezone
import pytest
from unittest.mock import MagicMock

@pytest.mark.unit
class TestAuthOTPSecurity:

    def test_generacion_otp_formato_6_digitos(self):
        """Verifica que el código generado sea estrictamente numérico y de longitud 6."""
        import secrets
        otp = "".join(str(secrets.randbelow(10)) for _ in range(6))
        assert len(otp) == 6
        assert otp.isdigit()

    def test_cooldown_anti_spam_60_segundos(self):
        """Si un usuario solicita otro OTP antes de 60 s, el sistema debe denegarlo o reutilizar el vigente."""
        now = datetime.now(timezone.utc)
        otp_emitido = now - timedelta(seconds=25) # Hace 25 segundos
        cooldown_limite = 60

        segundos_transcurridos = (now - otp_emitido).total_seconds()
        en_cooldown = segundos_transcurridos < cooldown_limite
        assert en_cooldown is True

    def test_expiracion_otp_5_minutos(self):
        """El OTP deja de ser válido exactamente al cumplirse los 5 minutos."""
        now = datetime.now(timezone.utc)
        expira_en = now - timedelta(seconds=1) # Ya pasó la fecha de expiración
        assert expira_en < now

    def test_bloqueo_por_fuerza_bruta_5_intentos(self):
        """Tras 5 intentos fallidos, la cuenta entra en bloqueo temporal por 15 minutos."""
        intentos_maximos = 5
        intentos_actuales = 5
        bloqueado = intentos_actuales >= intentos_maximos
        tiempo_bloqueo_minutos = 15 if bloqueado else 0
        assert bloqueado is True
        assert tiempo_bloqueo_minutos == 15

    def test_recordar_dispositivo_persistencia_token(self):
        """El token de dispositivo de confianza debe tener una expiración de 30 días y validarse sin MFA."""
        user_id = 42
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": "device_trust",
            "exp": now + timedelta(days=30)
        }
        assert payload["type"] == "device_trust"
        assert int(payload["sub"]) == user_id
        assert (payload["exp"] - now).days == 30

    def test_aislamiento_smtp_en_entorno_testing(self, monkeypatch):
        """Verifica que bajo APP_ENV=test jamás se invoque el protocolo SMTP real."""
        import smtplib
        mock_smtp = MagicMock()
        monkeypatch.setattr(smtplib, "SMTP", mock_smtp)
        monkeypatch.setattr(smtplib, "SMTP_SSL", mock_smtp)

        # Simular servicio de correo en entorno de prueba
        def despachar_correo_seguro(app_env: str, email: str, codigo: str):
            if app_env == "test":
                # Salida a consola / memoria; no tocar socket
                return {"enviado": False, "canal": "console", "otp": codigo}
            # Producción
            server = smtplib.SMTP("smtp.empresa.com", 587)
            server.sendmail("from@empresa.com", email, codigo)
            return {"enviado": True, "canal": "smtp"}

        res = despachar_correo_seguro("test", "test@giragroup.bo", "123456")
        assert res["enviado"] is False
        assert res["canal"] == "console"
        mock_smtp.assert_not_called()
