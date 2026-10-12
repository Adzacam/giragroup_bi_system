"""
services/auth-service/main.py
-----------------------------
Punto de entrada FastAPI para el Microservicio Auth & IAM (Puerto 8001).
Responsable de:
- Autenticación mediante credenciales y 2FA TOTP / OTP
- Emisión, verificación y refresco de tokens JWT
- Gestión de usuarios y control de acceso basado en roles (RBAC)
"""

import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import get_db, Base, engine
from models.user import User
from routers import auth, users

logger = logging.getLogger("auth_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="GIRAGROUP BI — Auth & IAM Service",
    description="Microservicio autónomo de Identidad, Autenticación 2FA y Control de Acceso RBAC",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de routers
app.include_router(auth.router)
app.include_router(users.router)

@app.get("/health", summary="Health Check Auth Service")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "auth-service",
            "port": 8001,
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Falla de base de datos en auth-service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio no disponible: DB degradada."
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
