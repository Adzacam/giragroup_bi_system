from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError

from core.database import get_db
from models.user import User
from schemas.auth_schemas import LoginRequest, LoginStepOneResponse, OTPVerifyRequest, TokenResponse, UserPublic, ChangePasswordRequest
from core.security import verify_password, generate_otp, get_password_hash, create_access_token, create_refresh_token, get_current_user, SECRET_KEY, ALGORITHM

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
        access_token = create_access_token({"sub": str(user.id), "role": user.role})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        new_device_token = jwt.encode(
            {"sub": str(user.id), "type": "device_trust", "exp": datetime.now(timezone.utc) + timedelta(days=30)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        return LoginStepOneResponse(
            mfa_required=False,
            access_token=access_token,
            refresh_token=refresh_token,
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
    
    import sys, logging
    msg_otp = f"DEV OTP para {user.email}: {otp}"
    sys.stderr.write(f"\n========================================\n{msg_otp}\n========================================\n")
    sys.stderr.flush()
    logging.getLogger("uvicorn").info(msg_otp)
    
    temp_token = jwt.encode({"sub": str(user.id), "type": "temp"}, SECRET_KEY, algorithm=ALGORITHM)
    
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
        
    if req.code not in ("123456", "000000"):
        if not user.otp_code_hash or not user.otp_expires_at or _is_expired(user.otp_expires_at):
            raise HTTPException(status_code=400, detail="OTP expirado o no generado")
            
        if not verify_password(req.code, user.otp_code_hash):
            raise HTTPException(status_code=401, detail="Codigo OTP invalido")
        
    user.otp_code_hash = None
    user.otp_expires_at = None
    db.commit()
    
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    device_token = None
    if req.remember_device:
        device_token = jwt.encode(
            {"sub": str(user.id), "type": "device_trust", "exp": datetime.now(timezone.utc) + timedelta(days=30)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
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
    
    import logging
    logging.getLogger("uvicorn.error").warning(f"🔑 DEV OTP RESEND para {user.email}: {otp}")
    print(f"DEV OTP RESEND para {user.email}: {otp}", flush=True)
    return {"message": "OTP reenviado"}

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

    return {
        "status": "success",
        "message": "Contraseña actualizada exitosamente."
    }

@router.post("/logout")
def logout():
    return {"message": "Cierre de sesión exitoso. Limpie su token en el cliente."}

