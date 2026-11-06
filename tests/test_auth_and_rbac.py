"""
tests/test_auth_and_rbac.py
----------------------------
Pruebas de verificación automatizada para:
- Autenticación segura de 2 factores (2FA / OTP)
- Control de intentos fallidos y bloqueo temporal de cuenta (Brute-force protection)
- Principio de Mínimo Privilegio (PoLP) y Control de Acceso Basado en Roles (RBAC)
- Regla Anti-Orfandad del Administrador (no auto-eliminación y no dejar al sistema sin admins)
- Centro de Notificaciones Institucionales
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from core.database import Base, get_db
from models.user import User
from models.notification import Notification
from core.security import get_password_hash, create_access_token

# ── Base de datos de pruebas en memoria (SQLite) ────────────────────────────
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Inicializa la base de datos de prueba antes de cada test con usuarios de prueba."""
    app.dependency_overrides[get_db] = override_get_db
    User.__table__.create(bind=test_engine, checkfirst=True)
    Notification.__table__.create(bind=test_engine, checkfirst=True)
    try:
        from models.log_pipeline import LogPipelineIngesta
        LogPipelineIngesta.__table__.create(bind=test_engine, checkfirst=True)
    except Exception:
        pass
    db = TestingSessionLocal()

    # Admin 1 (Principal)
    admin1 = User(
        id=1,
        username="admin1",
        email="admin1@giragroup.bo",
        hashed_password=get_password_hash("AdminPass123!"),
        role="ADMIN",
        is_active=True,
        failed_login_attempts=0,
    )
    # Admin 2 (Secundario para probar eliminación)
    admin2 = User(
        id=2,
        username="admin2",
        email="admin2@giragroup.bo",
        hashed_password=get_password_hash("AdminPass123!"),
        role="ADMIN",
        is_active=True,
        failed_login_attempts=0,
    )
    # Auditor de Calidad
    auditor = User(
        id=3,
        username="auditor",
        email="auditor@giragroup.bo",
        hashed_password=get_password_hash("AuditorPass123!"),
        role="AUDITOR_CALIDAD",
        is_active=True,
        failed_login_attempts=0,
    )
    # Notificación de prueba
    notif = Notification(
        id=1,
        user_id=1,
        role_target="ADMIN",
        title="Alerta de Calidad",
        message="Inconsistencia detectada en lote POS-2026",
        category="CALIDAD_DATAOPS",
        severity="WARNING",
        is_read=False,
    )

    db.add_all([admin1, admin2, auditor, notif])
    db.commit()
    db.close()

    yield

    Notification.__table__.drop(bind=test_engine, checkfirst=True)
    User.__table__.drop(bind=test_engine, checkfirst=True)
    app.dependency_overrides.pop(get_db, None)


# ── 1. PRUEBAS DE FLUJO 2FA Y BLOQUEO POR INTENTOS FALLIDOS ─────────────────

def test_login_step_one_success():
    """El paso 1 del login con credenciales correctas retorna temp_token y requiere MFA."""
    res = client.post("/api/v1/auth/login", json={
        "email": "admin1@giragroup.bo",
        "password": "AdminPass123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "temp_token" in data
    assert data["mfa_required"] is True


def test_login_failed_attempts_and_lockout():
    """5 intentos fallidos consecutivos bloquean la cuenta por 15 minutos."""
    for i in range(4):
        res = client.post("/api/v1/auth/login", json={
            "email": "admin1@giragroup.bo",
            "password": "WrongPassword!"
        })
        assert res.status_code == 401

    # 5to intento erróneo activa el bloqueo
    res5 = client.post("/api/v1/auth/login", json={
        "email": "admin1@giragroup.bo",
        "password": "WrongPassword!"
    })
    assert res5.status_code == 401

    # El siguiente intento (incluso con clave correcta) debe ser rechazado por cuenta bloqueada (403)
    res_blocked = client.post("/api/v1/auth/login", json={
        "email": "admin1@giragroup.bo",
        "password": "AdminPass123!"
    })
    assert res_blocked.status_code == 403
    assert "bloqueada" in res_blocked.json()["detail"].lower()


def test_verify_otp_flow():
    """El paso 2 valida el OTP generado y emite tokens JWT access y refresh."""
    login_res = client.post("/api/v1/auth/login", json={
        "email": "auditor@giragroup.bo",
        "password": "AuditorPass123!"
    })
    temp_token = login_res.json()["temp_token"]

    # Obtenemos el OTP almacenado para el test
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "auditor@giragroup.bo").first()
    # Generamos un código conocido para verificar
    user.otp_code_hash = get_password_hash("123456")
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    db.commit()
    db.close()

    # Código incorrecto -> 401
    bad_otp = client.post("/api/v1/auth/verify-otp", json={
        "temp_token": temp_token,
        "code": "999999"
    })
    assert bad_otp.status_code == 401

    # Código correcto -> 200 con tokens
    good_otp = client.post("/api/v1/auth/verify-otp", json={
        "temp_token": temp_token,
        "code": "123456"
    })
    assert good_otp.status_code == 200
    token_data = good_otp.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["user"]["role"] == "AUDITOR_CALIDAD"


# ── 2. PRUEBAS DE CONTROL DE ACCESO (RBAC & MINIMO PRIVILEGIO) ──────────────

def test_rbac_user_management_protected():
    """Solo los usuarios con rol ADMIN pueden consultar y gestionar la lista de usuarios."""
    # Sin token -> 401
    res_no_auth = client.get("/api/v1/users")
    assert res_no_auth.status_code == 401

    # Con rol AUDITOR_CALIDAD -> 403 Forbidden
    auditor_token = create_access_token({"sub": "3", "role": "AUDITOR_CALIDAD"})
    res_forbidden = client.get("/api/v1/users", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res_forbidden.status_code == 403

    # Con rol ADMIN -> 200 OK
    admin_token = create_access_token({"sub": "1", "role": "ADMIN"})
    res_ok = client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_ok.status_code == 200
    users_list = res_ok.json()
    assert len(users_list) >= 3


# ── 3. PRUEBAS DE LA REGLA ANTI-ORFANDAD ─────────────────────────────────────

def test_anti_orphan_cannot_delete_self():
    """Un administrador no puede eliminarse a sí mismo."""
    admin1_token = create_access_token({"sub": "1", "role": "ADMIN"})
    res = client.delete("/api/v1/users/1", headers={"Authorization": f"Bearer {admin1_token}"})
    assert res.status_code == 400
    assert "auto-eliminarse" in res.json()["detail"].lower()


def test_anti_orphan_cannot_leave_system_without_admins():
    """No se puede eliminar a un administrador si solo queda 1 administrador activo en el sistema."""
    admin1_token = create_access_token({"sub": "1", "role": "ADMIN"})

    # Hacemos a admin2 inactivo para que active_admins sea 1 (solo admin1)
    db = TestingSessionLocal()
    admin2_obj = db.query(User).filter(User.id == 2).first()
    admin2_obj.is_active = False
    db.commit()

    active_count = db.query(User).filter(User.role == "ADMIN", User.is_active == True).count()
    assert active_count == 1
    db.close()

    # Admin 1 intenta eliminar a Admin 2 (rol ADMIN) cuando solo hay 1 admin activo en el sistema
    res_last = client.delete("/api/v1/users/2", headers={"Authorization": f"Bearer {admin1_token}"})
    assert res_last.status_code == 400
    assert "sin administradores" in res_last.json()["detail"].lower()


# ── 4. PRUEBAS DE NOTIFICACIONES ─────────────────────────────────────────────

def test_notifications_endpoints():
    """El usuario puede consultar notificaciones y marcarlas como leídas."""
    admin1_token = create_access_token({"sub": "1", "role": "ADMIN"})

    # Listar notificaciones
    res = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {admin1_token}"})
    assert res.status_code == 200
    notifs_payload = res.json()
    assert notifs_payload["status"] == "success"
    notifs = notifs_payload["data"]
    assert len(notifs) >= 1
    assert notifs[0]["is_read"] is False

    # Marcar individual como leída
    res_read = client.patch("/api/v1/notifications/1/read", headers={"Authorization": f"Bearer {admin1_token}"})
    assert res_read.status_code == 200
    assert res_read.json()["is_read"] is True

    # Marcar todas como leídas
    res_all = client.post("/api/v1/notifications/mark-all-read", headers={"Authorization": f"Bearer {admin1_token}"})
    assert res_all.status_code == 200


# ── 5. PRUEBAS DE RECUPERACIÓN DE CONTRASEÑA Y PLANTILLAS DE EMAIL ───────────

def test_forgot_password_registered_user():
    """Solicitar recuperación para un usuario registrado genera código y responde 200."""
    res = client.post("/api/v1/auth/forgot-password", json={
        "email": "admin1@giragroup.bo"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "instrucciones" in data["message"].lower()

    # Verificar que el usuario tiene otp temporal en DB
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "admin1@giragroup.bo").first()
    assert user.otp_code_hash is not None
    assert user.otp_expires_at is not None
    db.close()


def test_forgot_password_unregistered_user():
    """Anti-enumeración: usuario no registrado responde 200 con el mismo mensaje neutro."""
    res = client.post("/api/v1/auth/forgot-password", json={
        "email": "inexistente@giragroup.bo"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"


def test_email_service_rendering():
    """El servicio de email renderiza correctamente las plantillas HTML con branding GiraGroup."""
    from services.email_service import email_service
    html_otp = email_service.render_otp_email(
        to_email="test@giragroup.bo",
        username="Tester",
        otp_code="654321",
        expires_in_minutes=5
    )
    assert ("654 321" in html_otp or "654321" in html_otp)
    assert "GiraGroup" in html_otp
    assert "0C1E33" in html_otp

    html_reset = email_service.render_password_reset_email(
        to_email="test@giragroup.bo",
        username="Tester",
        reset_code="789012",
        expires_in_minutes=15
    )
    assert ("789 012" in html_reset or "789012" in html_reset)
    assert "GiraGroup" in html_reset


def test_email_service_send_otp_and_reset_unconfigured(monkeypatch):
    """Cuando no hay SMTP_HOST configurado, el servicio opera en fallback de consola sin errores."""
    from services.email_service import email_service
    monkeypatch.delenv("SMTP_HOST", raising=False)
    
    res = email_service.send_otp_email(
        to_email="operador@giragroup.bo",
        username="Operador",
        otp_code="123456",
        expires_in_minutes=5
    )
    assert res["status"] == "delivered"
    assert res["otp"] == "123456"
    assert res["smtp"]["sent"] is False
    assert res["smtp"]["reason"] == "not_configured"

    res_reset = email_service.send_password_reset_email(
        to_email="operador@giragroup.bo",
        username="Operador",
        reset_code="654321",
        expires_in_minutes=15
    )
    assert res_reset["status"] == "delivered"
    assert res_reset["reset_code"] == "654321"
    assert res_reset["smtp"]["sent"] is False


def test_email_service_send_smtp_success(monkeypatch):
    """Envío real simulado vía smtplib con STARTTLS exitoso."""
    monkeypatch.setenv("EMAIL_BACKEND", "smtp")  # otro módulo fija EMAIL_BACKEND=console al importarse; aquí smtplib va con mock
    from unittest.mock import MagicMock
    import smtplib
    from services.email_service import email_service

    monkeypatch.setenv("SMTP_HOST", "smtp.testserver.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "sender@test.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret123")
    monkeypatch.setenv("SMTP_USE_TLS", "True")

    mock_smtp_inst = MagicMock()
    mock_smtp_class = MagicMock(return_value=mock_smtp_inst)
    monkeypatch.setattr(smtplib, "SMTP", mock_smtp_class)

    res = email_service.send_otp_email(
        to_email="cliente@giragroup.bo",
        username="Cliente",
        otp_code="987654",
        expires_in_minutes=5
    )

    assert res["status"] == "delivered"
    assert res["smtp"]["sent"] is True
    assert res["smtp"]["host"] == "smtp.testserver.com"
    mock_smtp_class.assert_called_once_with("smtp.testserver.com", 587, timeout=5.0)
    mock_smtp_inst.starttls.assert_called_once()
    mock_smtp_inst.login.assert_called_once_with("sender@test.com", "secret123")
    mock_smtp_inst.send_message.assert_called_once()
    mock_smtp_inst.quit.assert_called_once()


def test_email_service_smtp_resilience_to_failures(monkeypatch):
    """Si el servidor SMTP rechaza credenciales o hace timeout, no se produce excepción hacia el caller."""
    monkeypatch.setenv("EMAIL_BACKEND", "smtp")  # otro módulo fija EMAIL_BACKEND=console al importarse; aquí smtplib va con mock
    import smtplib
    from unittest.mock import MagicMock
    from services.email_service import email_service

    monkeypatch.setenv("SMTP_HOST", "smtp.error.com")
    monkeypatch.setenv("SMTP_USER", "fail@error.com")
    monkeypatch.setenv("SMTP_PASSWORD", "wrongpass")

    # Simular error de autenticación SMTP
    mock_smtp_inst = MagicMock()
    mock_smtp_inst.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication credentials invalid")
    mock_smtp_class = MagicMock(return_value=mock_smtp_inst)
    monkeypatch.setattr(smtplib, "SMTP", mock_smtp_class)

    res = email_service.send_otp_email(
        to_email="test@giragroup.bo",
        username="TestUser",
        otp_code="111222",
        expires_in_minutes=5
    )

    assert res["status"] == "delivered"
    assert res["smtp"]["sent"] is False
    assert res["smtp"]["error_type"] == "AuthenticationError"


def test_auth_service_email_service_consistency(monkeypatch):
    """Verifica que services/auth-service/services/email_service.py funcione de forma idéntica."""
    import importlib.util
    from pathlib import Path

    auth_email_path = Path("services/auth-service/services/email_service.py").resolve()
    assert auth_email_path.exists()

    spec = importlib.util.spec_from_file_location("auth_service_email", auth_email_path)
    auth_email_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auth_email_module)

    svc = auth_email_module.EmailService()
    monkeypatch.delenv("SMTP_HOST", raising=False)
    
    html = svc.render_otp_email("audit@giragroup.bo", "Auditor", "888999", 5)
    assert ("888 999" in html or "888999" in html)
    assert "GiraGroup" in html

    res = svc.send_otp_email("audit@giragroup.bo", "Auditor", "888999", 5)
    assert res["status"] == "delivered"
    assert res["otp"] == "888999"
    assert res["smtp"]["sent"] is False


def test_email_service_send_smtp_ssl_port_465(monkeypatch):
    """Verifica envío directo mediante SMTP_SSL (puerto 465)."""
    monkeypatch.setenv("EMAIL_BACKEND", "smtp")  # otro módulo fija EMAIL_BACKEND=console al importarse; aquí smtplib va con mock
    from unittest.mock import MagicMock
    import smtplib
    from services.email_service import email_service

    monkeypatch.setenv("SMTP_HOST", "mail.giragroup.bo")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USER", "admin@giragroup.bo")
    monkeypatch.setenv("SMTP_PASSWORD", '"securepass"')
    monkeypatch.setenv("SMTP_FROM_NAME", '"GiraGroup Notificaciones"')

    mock_ssl_inst = MagicMock()
    mock_ssl_class = MagicMock(return_value=mock_ssl_inst)
    monkeypatch.setattr(smtplib, "SMTP_SSL", mock_ssl_class)

    res = email_service.send_otp_email(
        to_email="direct@giragroup.bo",
        username="DirectUser",
        otp_code="333444",
        expires_in_minutes=5
    )

    assert res["status"] == "delivered"
    assert res["smtp"]["sent"] is True
    mock_ssl_class.assert_called_once_with("mail.giragroup.bo", 465, timeout=5.0)
    mock_ssl_inst.login.assert_called_once_with("admin@giragroup.bo", "securepass")
    mock_ssl_inst.send_message.assert_called_once()
    mock_ssl_inst.quit.assert_called_once()

    # Verificar que el mensaje incluye headers RFC 5322 Date y Message-ID
    sent_msg = mock_ssl_inst.send_message.call_args[0][0]
    assert "Date" in sent_msg
    assert "Message-ID" in sent_msg
    assert "GiraGroup Notificaciones" in sent_msg["From"]


def test_login_step_one_channel_dynamic(monkeypatch):
    """
    Verifica que el endpoint login retorna channel='email' cuando SMTP despacha exitosamente,
    y channel='console' cuando SMTP falla o no está configurado (fallback seguro).
    """
    monkeypatch.setenv("EMAIL_BACKEND", "smtp")  # otro módulo fija EMAIL_BACKEND=console al importarse; aquí smtplib va con mock
    import smtplib
    from unittest.mock import MagicMock

    # Caso 1: Sin SMTP configurado -> channel="console"
    monkeypatch.delenv("SMTP_HOST", raising=False)
    res_console = client.post("/api/v1/auth/login", json={
        "email": "admin1@giragroup.bo",
        "password": "AdminPass123!"
    })
    assert res_console.status_code == 200
    assert res_console.json()["channel"] == "console"

    # Caso 2: Con SMTP configurado y fallido (bad auth) -> fallback a channel="console"
    monkeypatch.setenv("SMTP_HOST", "smtp.broken.com")
    monkeypatch.setenv("SMTP_USER", "fail@broken.com")
    monkeypatch.setenv("SMTP_PASSWORD", "wrongpass")
    mock_smtp_inst = MagicMock()
    mock_smtp_inst.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Invalid credentials")
    monkeypatch.setattr(smtplib, "SMTP", MagicMock(return_value=mock_smtp_inst))

    res_fail = client.post("/api/v1/auth/login", json={
        "email": "admin1@giragroup.bo",
        "password": "AdminPass123!"
    })
    assert res_fail.status_code == 200
    assert res_fail.json()["channel"] == "console"

    # Caso 3: Con SMTP configurado y exitoso -> channel="email"
    monkeypatch.setenv("SMTP_HOST", "smtp.ok.com")
    monkeypatch.setenv("SMTP_USER", "ok@ok.com")
    monkeypatch.setenv("SMTP_PASSWORD", "okpass")
    mock_smtp_ok = MagicMock()
    monkeypatch.setattr(smtplib, "SMTP", MagicMock(return_value=mock_smtp_ok))

    res_email = client.post("/api/v1/auth/login", json={
        "email": "admin1@giragroup.bo",
        "password": "AdminPass123!"
    })
    assert res_email.status_code == 200
    assert res_email.json()["channel"] == "email"


def test_user_cache_detached_instance_and_change_password():
    """
    Verifica que:
    1. _USER_CACHE no lanza DetachedInstanceError en peticiones subsiguientes después de que
       una petición previa ejecuta db.commit() (ej. POST /api/v1/users).
    2. POST /api/v1/auth/change-password persiste el nuevo hash en la base de datos incluso
       cuando current_user proviene de _USER_CACHE (instancia expurgada de la sesión previa).
    """
    from core.security import invalidate_user_cache, verify_password

    invalidate_user_cache()
    admin_token = create_access_token({"sub": "1", "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Petición de escritura que hace db.commit() mientras admin1 se almacena en _USER_CACHE
    res_create = client.post(
        "/api/v1/users",
        json={
            "username": "cache_test_user",
            "email": "cache_test@giragroup.bo",
            "password": "CacheUserPass123!",
            "role": "AUDITOR_CALIDAD",
        },
        headers=headers,
    )
    assert res_create.status_code == 200

    # 2. Petición subsiguiente dentro del TTL (60s) que consume _USER_CACHE tras el commit
    res_list = client.get("/api/v1/users", headers=headers)
    assert res_list.status_code == 200

    # 3. Cambio de contraseña con usuario proveniente de _USER_CACHE
    res_chg = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "AdminPass123!",
            "new_password": "NewAdminPass456!",
            "confirm_password": "NewAdminPass456!",
        },
        headers=headers,
    )
    assert res_chg.status_code == 200

    db = TestingSessionLocal()
    admin_db = db.query(User).filter(User.id == 1).first()
    assert verify_password("NewAdminPass456!", admin_db.hashed_password) is True
    db.close()
