from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os

from core.database import get_db
from models.user import User

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_change_me_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

import bcrypt
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8")[:72], salt).decode("utf-8")

def generate_otp():
    return "".join(str(secrets.randbelow(10)) for _ in range(6))

def generate_temp_password(prefix: str = "Gira#", length: int = 6) -> str:
    """Genera una contraseña temporal segura, legible y robusta (p. ej. Gira#8Kp2M9)."""
    digits = "23456789"
    uppers = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    lowers = "abcdefghijkmnopqrstuvwxyz"
    all_chars = digits + uppers + lowers
    chars = [secrets.choice(digits), secrets.choice(uppers), secrets.choice(lowers)]
    for _ in range(max(0, length - 3)):
        chars.append(secrets.choice(all_chars))
    secrets.SystemRandom().shuffle(chars)
    return f"{prefix}{''.join(chars)}"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

import time

# Caché en memoria con TTL de 60 segundos para evitar query síncrono a users por cada request
_USER_CACHE: dict[int, tuple[float, User]] = {}

def invalidate_user_cache(user_id: Optional[int] = None):
    """Invalida el usuario en caché tras cambio de contraseña, desactivación o bloqueo."""
    global _USER_CACHE
    if user_id is None:
        _USER_CACHE.clear()
    else:
        _USER_CACHE.pop(user_id, None)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type", "access")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = None
    now = time.time()
    if str(user_id).isdigit():
        uid_int = int(user_id)
        cached = _USER_CACHE.get(uid_int)
        if cached and (now - cached[0] < 60.0):
            user = cached[1]
        else:
            user = db.query(User).filter(User.id == uid_int).first()
            if user:
                _ = (
                    user.id,
                    user.username,
                    user.email,
                    user.role,
                    user.is_active,
                    user.hashed_password,
                    getattr(user, "phone", None),
                    getattr(user, "is_mfa_enabled", True),
                )
                try:
                    db.expunge(user)
                except Exception:
                    pass
                _USER_CACHE[uid_int] = (now, user)

    if not user:
        user = db.query(User).filter((User.username == str(user_id)) | (User.email == str(user_id))).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

def require_roles(allowed_roles: list[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos suficientes."
            )
        return current_user
    return role_checker
