"""
backend/main.py
---------------
Entrypoint principal de FastAPI para GiraGroup BI System (Sprint 4).
Incluye configuración de middleware de cabeceras de seguridad OWASP (A05)
y manejo centralizado de excepciones sanitizadas.
"""

import logging
from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import get_db
from routers import riesgos, forecast, auth, users, notifications

logger = logging.getLogger("api_main")

app = FastAPI(
    title="GiraGroup BI System API",
    description="API REST de Inteligencia de Negocios y Forecasting Predictivo (Sprint 4)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── Middleware de Seguridad OWASP (Cabeceras de Protección HTTP) ─────────────
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response: Response = await call_next(request)
    # OWASP A05: Cabeceras defensivas para prevenir Clickjacking, MIME-sniffing y XSS
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
    return response


# ── Middleware CORS Controlado ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Frontend React Vite
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ── Registro de Routers Modulares ─────────────────────────────────────────────
app.include_router(riesgos.router)
app.include_router(forecast.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(notifications.router)


@app.get(
    "/health",
    summary="Verificación de estado y salud del sistema",
    tags=["Monitoreo"]
)
def health_check(db: Session = Depends(get_db)):
    """Health check que verifica la conectividad al Data Warehouse sin fugar credenciales ni trazas."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "giragroup-bi-api",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Falla de conectividad en health check: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio temporalmente no disponible: conexión a base de datos degradada."
        )