"""
services/audit-service/main.py
------------------------------
Microservicio de Auditoría, Trazabilidad Inmutable y Compliance (Puerto 8004).
Responsable de:
- Almacenamiento centralizado de eventos de auditoría (ingesta, seguridad, accesos)
- Consulta y filtrado granular por severidad, fecha y módulo
- Exportación certificada de bitácoras para directores y auditores
"""

import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import get_db
from routers import audit

logger = logging.getLogger("audit_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="GIRAGROUP BI — Audit & Observability Service",
    description="Microservicio de Trazabilidad Inmutable, Cumplimiento y Registro de Auditoría",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit.router)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "audit-service",
            "port": 8004,
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Falla en audit-service health: {e}")
        raise HTTPException(status_code=503, detail="DB degradada.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
