"""
shared/auth_middleware.py
-------------------------
Módulo compartido de autenticación y validación de tokens JWT
para la arquitectura mixta de GIRAGROUP BI System.
Permite validar identidad y roles en cualquier microservicio sin acoplamiento a base de datos.
"""

from datetime import datetime, timezone
import os
from typing import Optional, List, Dict, Any
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_change_me_in_prod")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

class AuthenticatedUser(BaseModel):
    id: Optional[int] = None
    sub: str
    username: Optional[str] = None
    email: Optional[str] = None
    role: str = "USUARIO"
    roles: List[str] = []

def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user_claims(token: str = Depends(oauth2_scheme)) -> AuthenticatedUser:
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no contiene sujeto válido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    role = payload.get("role", "USUARIO")
    user_id = int(sub) if str(sub).isdigit() else payload.get("id")
    
    return AuthenticatedUser(
        id=user_id,
        sub=str(sub),
        username=payload.get("username", str(sub)),
        email=payload.get("email"),
        role=role,
        roles=[role] if role else []
    )

def require_roles_claims(allowed_roles: List[str]):
    def role_checker(current_user: AuthenticatedUser = Depends(get_current_user_claims)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Requiere uno de: {allowed_roles}"
            )
        return current_user
    return role_checker
