import os
from pathlib import Path

os.environ["TESTING"] = "true"
os.environ["APP_ENV"] = "test"
os.environ["EMAIL_BACKEND"] = "console"

import pytest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from routers.auth import forgot_password, login_step_one, verify_otp, change_password
from schemas.auth_schemas import (
    ForgotPasswordRequest, LoginRequest, OTPVerifyRequest, ChangePasswordRequest
)
from core.security import get_password_hash, generate_temp_password, verify_password, generate_otp
from models.user import User
from services.email_service import email_service, mask_email

TEST_DB_FILE = Path(__file__).resolve().parent / "test_auth_temp.db"
SQLALCHEMY_TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE.as_posix()}"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    User.__table__.create(bind=test_engine, checkfirst=True)
    db = TestingSessionLocal()
    db.query(User).filter(User.email == "test_flow@giragroup.bo").delete()
    db.query(User).filter(User.email == "dazaadrian012@gmail.com").delete()

    user = User(
        username="flow_user",
        email="test_flow@giragroup.bo",
        hashed_password=get_password_hash("OriginalSecret123!"),
        role="docente",
        is_active=True,
        failed_login_attempts=0
    )
    db.add(user)
    db.commit()
    db.close()
    yield
    try:
        db = TestingSessionLocal()
        db.query(User).filter(User.email == "test_flow@giragroup.bo").delete()
        db.query(User).filter(User.email == "dazaadrian012@gmail.com").delete()
        db.commit()
        db.close()
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_db():
    yield
    try:
        if TEST_DB_FILE.exists():
            TEST_DB_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def test_mask_email_function():
    # Validación de enmascaramiento según requerimiento de privacidad
    assert mask_email("dazaadrian012@gmail.com") == "daz********@gmail.com"
    assert mask_email("admin_general@giragroup.bo") == "adm********@giragroup.bo"
    assert mask_email("qa@test.bo") == "q****@test.bo"
    assert mask_email("a@b.com") == "a****@b.com"
    assert mask_email("") == ""


def test_generate_temp_password():
    pwd1 = generate_temp_password(length=6)
    pwd2 = generate_temp_password(length=6)
    assert len(pwd1) == len("Gira#") + 6
    assert pwd1 != pwd2
    assert any(c.isupper() for c in pwd1)
    assert any(c.islower() for c in pwd1)
    assert any(c.isdigit() for c in pwd1)


def test_otp_email_template_elements_and_subject():
    # 1. Asunto del correo solicitado: "[GiraGroup BI] Código de seguridad para iniciar sesión"
    with patch.object(email_service, "_send_smtp") as mock_send:
        mock_send.return_value = {"sent": True, "host": "smtp.gmail.com", "port": 587}
        res = email_service.send_otp_email(
            to_email="dazaadrian012@gmail.com",
            username="adrian",
            otp_code="748363",
            expires_in_minutes=5
        )
        assert res["status"] == "delivered"
        mock_send.assert_called_once()
        subject_used = mock_send.call_args[1]["subject"]
        assert subject_used == "[GiraGroup BI] Código de seguridad para iniciar sesión"
        assert "748363" not in subject_used

    # 2. Renderizado de HTML según imagen de referencia
    html = email_service.render_otp_email(
        to_email="dazaadrian012@gmail.com",
        username="adrian",
        otp_code="748363",
        expires_in_minutes=5
    )
    # Branding institucional y colores
    assert "GIRA" in html and "GROUP" in html
    assert "SISTEMA DE INTELIGENCIA DE NEGOCIOS Y PLN" in html
    assert "#0C1E33" in html or "#0c1e33" in html
    assert "#D99B26" in html or "#d99b26" in html

    # Correo enmascarado
    assert "daz********@gmail.com" in html
    assert "dazaadrian012@gmail.com" not in html

    # Código OTP destacado y acción
    assert "748 363" in html or "748363" in html
    assert "Selecciona y copia este código" in html

    # Alerta de expiración
    assert "Expira en 5 minutos" in html
    assert "No compartas este código" in html

    # Detalles de acceso limpios (SIN TLS ni SHA-256)
    assert "TLS 1.3" not in html
    assert "SHA-256" not in html
    assert "Dispositivo Confiable" not in html
    assert "INFORMACIÓN DEL ACCESO" in html
    assert "seguridad@giragroup.bo" in html

    # Nota de mensaje automático en pie
    assert "Este mensaje fue generado automáticamente. No respondas a este correo" in html


def test_password_reset_email_template_elements():
    html = email_service.render_password_reset_email(
        to_email="dazaadrian012@gmail.com",
        username="adrian",
        temp_password="Gira#8kP4m2",
        expires_in_minutes=15
    )
    assert "GIRA" in html and "GROUP" in html
    assert "daz********@gmail.com" in html
    assert "Gira#8kP4m2" in html
    assert "Copia esta contraseña e inicia sesión en la plataforma" in html
    assert "Actualiza tu contraseña" in html
    assert "TLS 1.3" not in html
    assert "SHA-256" not in html
    assert "Este mensaje fue generado automáticamente. No respondas a este correo" in html


def test_forgot_password_and_login_with_temp_password():
    """
    Flujo completo de recuperación de contraseña:
    1. Olvido de contraseña genera una contraseña temporal y la asocia a la cuenta.
    2. El usuario inicia sesión exitosamente usando la contraseña temporal.
    3. El usuario completa el 2FA con el OTP emitido.
    4. El usuario actualiza su contraseña a una nueva y definitiva.
    5. El usuario inicia sesión con la nueva contraseña definitiva.
    """
    db = TestingSessionLocal()
    try:
        # 1. Solicitar recuperación
        res_forgot = forgot_password(
            ForgotPasswordRequest(email="test_flow@giragroup.bo"),
            db=db
        )
        assert res_forgot.status == "success"
        temp_pwd = res_forgot.temp_password_test
        assert temp_pwd is not None, "Debe emitirse la contraseña temporal en modo de pruebas"

        # Verificar que el hash en DB coincide con la contraseña temporal
        u = db.query(User).filter(User.email == "test_flow@giragroup.bo").first()
        assert verify_password(temp_pwd, u.hashed_password)

        # 2. Iniciar sesión usando la contraseña temporal generada
        res_login = login_step_one(
            LoginRequest(email="test_flow@giragroup.bo", password=temp_pwd),
            db=db
        )
        assert res_login.mfa_required is True
        temp_token = res_login.temp_token
        assert temp_token is not None

        # 3. Completar 2FA con el OTP emitido
        otp = generate_otp()
        u.otp_code_hash = get_password_hash(otp)
        db.commit()

        res_verify = verify_otp(
            OTPVerifyRequest(temp_token=temp_token, code=otp),
            db=db
        )
        assert res_verify.access_token is not None
        current_user = u

        # 4. Cambiar contraseña en perfil
        new_permanent_password = "BrandNewSecurePass999!"
        res_change = change_password(
            ChangePasswordRequest(
                current_password=temp_pwd,
                new_password=new_permanent_password,
                confirm_password=new_permanent_password
            ),
            db=db,
            current_user=current_user
        )
        assert res_change["status"] == "success"

        # 5. Iniciar sesión exitosamente con la nueva contraseña permanente
        res_login_new = login_step_one(
            LoginRequest(email="test_flow@giragroup.bo", password=new_permanent_password),
            db=db
        )
        assert res_login_new.mfa_required is True
    finally:
        db.close()
