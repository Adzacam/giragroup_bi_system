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


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Inicializa la base de datos de prueba antes de cada test con usuarios de prueba."""
    User.__table__.create(bind=test_engine, checkfirst=True)
    Notification.__table__.create(bind=test_engine, checkfirst=True)
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
