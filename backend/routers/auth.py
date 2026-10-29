from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
import os
import sys
import logging
from jose import jwt, JWTError

from core.database import get_db
from models.user import User
from schemas.auth_schemas import (
    LoginRequest, LoginStepOneResponse, OTPVerifyRequest, TokenResponse,
    UserPublic, ChangePasswordRequest, ForgotPasswordRequest, ForgotPasswordResponse
)
from core.security import (
    verify_password, generate_otp, get_password_hash, create_access_token,
    get_current_user, invalidate_user_cache, SECRET_KEY, ALGORITHM
)
from services.email_service import email_service

logger = logging.getLogger("uvicorn.auth")
router = APIRouter(prefix="/api/v1/auth", tags=["Autenticacion"])

def _is_future(dt: Optional[datetime]) -> bool:
    if not dt:
        return False
    now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now(timezone.utc).replace(tzinfo=None)
    return dt > now

def _is_expired(dt: Optional[datetime]) -> bool:
    if not dt:
        return True
    now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now(timezone.utc).replace(tzinfo=None)
    return dt < now

@router.post("/login", response_model=LoginStepOneResponse)
def login_step_one(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
        
    if user.locked_until and _is_future(user.locked_until):
        raise HTTPException(status_code=403, detail="Cuenta bloqueada temporalmente")
        
    if not verify_password(req.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            invalidate_user_cache(user.id)
        db.commit()
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
        
    user.failed_login_attempts = 0
    user.locked_until = None

    # Verificar si el dispositivo ya fue validado para este usuario previamente
    trusted_device = False
    if req.device_token:
        try:
            d_payload = jwt.decode(req.device_token, SECRET_KEY, algorithms=[ALGORITHM])
            if d_payload.get("type") == "device_trust" and int(d_payload.get("sub")) == user.id:
                trusted_device = True
        except JWTError:
            trusted_device = False

    if trusted_device:
        db.commit()
        try:
            from models.log_pipeline import LogPipelineIngesta
            db.add(LogPipelineIngesta(
                etapa="AUTH_DISPOSITIVO",
                nivel="SUCCESS",
                modulo="Seguridad & 2FA",
                mensaje=f"Inicio de sesión directo mediante dispositivo de confianza para '{user.email}' (Rol: {user.role})"
            ))
            db.commit()
        except Exception:
            pass
        access_token = create_access_token({"sub": str(user.id), "role": user.role})
        new_device_token = jwt.encode(
            {"sub": str(user.id), "type": "device_trust", "exp": datetime.now(timezone.utc) + timedelta(days=30)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        return LoginStepOneResponse(
            mfa_required=False,
            access_token=access_token,
            token_type="bearer",
            device_token=new_device_token,
            user=UserPublic(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role,
                is_active=user.is_active
            )
        )

    otp = generate_otp()
    user.otp_code_hash = get_password_hash(otp)
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    db.commit()
    
    if os.getenv("ENV", "development").lower() == "development":
        msg_otp = f"DEV OTP para {user.email}: {otp}"
        sys.stderr.write(f"\n========================================\n{msg_otp}\n========================================\n")
        sys.stderr.flush()
        logger.info(msg_otp)

    # Despachar correo electrónico corporativo OTP
    try:
        email_service.send_otp_email(
            to_email=user.email,
            username=user.username,
            otp_code=otp,
            expires_in_minutes=5
        )
    except Exception as e:
        logger.warning(f"No se pudo despachar el correo OTP: {e}")
    
    temp_token = jwt.encode(
        {"sub": str(user.id), "type": "temp", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    
    return LoginStepOneResponse(
        temp_token=temp_token,
        mfa_required=True,
        channel="console"
    )

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(req: OTPVerifyRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(req.temp_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "temp":
            raise HTTPException(status_code=401, detail="Token invalido")
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    if not user.otp_code_hash or not user.otp_expires_at or _is_expired(user.otp_expires_at):
        raise HTTPException(status_code=400, detail="OTP expirado o no generado")
        
    if not verify_password(req.code, user.otp_code_hash):
        raise HTTPException(status_code=401, detail="Codigo OTP invalido")
        
    user.otp_code_hash = None
    user.otp_expires_at = None
    db.commit()

    try:
        from models.log_pipeline import LogPipelineIngesta
        db.add(LogPipelineIngesta(
            etapa="AUTH_2FA",
            nivel="SUCCESS",
            modulo="Seguridad & 2FA",
            mensaje=f"Autenticación exitosa con 2FA OTP para usuario '{user.email}' (Rol: {user.role})"
        ))
        db.commit()
    except Exception:
        db.rollback()
    
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    
    device_token = None
    if req.remember_device:
        device_token = jwt.encode(
            {"sub": str(user.id), "type": "device_trust", "exp": datetime.now(timezone.utc) + timedelta(days=30)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        device_token=device_token,
        user=UserPublic(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active
        )
    )

@router.post("/resend-otp")
def resend_otp(req: dict = Body(...), db: Session = Depends(get_db)):
    temp_token = req.get("temp_token")
    if not temp_token:
        raise HTTPException(status_code=400, detail="Se requiere temp_token")
        
    try:
        payload = jwt.decode(temp_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    # Cooldown de 60 segundos antes de reenviar
    if user.otp_expires_at:
        now = datetime.now(timezone.utc) if user.otp_expires_at.tzinfo else datetime.now(timezone.utc).replace(tzinfo=None)
        if user.otp_expires_at > now + timedelta(minutes=4):
            raise HTTPException(status_code=429, detail="Debe esperar antes de solicitar otro OTP")
        
    otp = generate_otp()
    user.otp_code_hash = get_password_hash(otp)
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    db.commit()
    
    logger.warning(f"🔑 DEV OTP RESEND para {user.email}: {otp}")
    print(f"DEV OTP RESEND para {user.email}: {otp}", flush=True)

    try:
        email_service.send_otp_email(
            to_email=user.email,
            username=user.username,
            otp_code=otp,
            expires_in_minutes=5
        )
    except Exception as e:
        logger.warning(f"No se pudo despachar el reenvío de correo OTP: {e}")

    return {"message": "OTP reenviado"}

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if user and user.is_active:
        reset_code = generate_otp()
        user.otp_code_hash = get_password_hash(reset_code)
        user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.commit()

        try:
            email_service.send_password_reset_email(
                to_email=user.email,
                username=user.username,
                reset_code=reset_code,
                expires_in_minutes=15
            )
        except Exception as e:
            logger.warning(f"No se pudo despachar el correo de restablecimiento: {e}")

    return ForgotPasswordResponse(
        message="Si la cuenta institucional está registrada, se ha enviado un correo con las instrucciones de restablecimiento.",
        status="success"
    )

@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual ingresada es incorrecta."
        )

    if len(req.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe tener al menos 6 caracteres."
        )

    if req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La confirmación no coincide con la nueva contraseña."
        )

    current_user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    invalidate_user_cache(current_user.id)

    return {
        "status": "success",
        "message": "Contraseña actualizada exitosamente."
    }

@router.post("/logout")
def logout():
    return {"message": "Cierre de sesión exitoso. Limpie su token en el cliente."}
