"""
services/analytics-service/main.py
----------------------------------
Microservicio de Analytics, Forecasting Holt-Winters y Power BI Embed (Puerto 8003).
Responsable de:
- Modelos estadísticos y series temporales (ExponentialSmoothing / statsmodels)
- Cálculo determinístico de KPIs y métricas CMI
- Generación de tokens y configuración para dashboards de Power BI
"""

import logging
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import get_db
from routers import forecast, kpis
from powerbi.embed_service import PowerBIEmbedService

logger = logging.getLogger("analytics_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="GIRAGROUP BI — Analytics & Forecasting Service",
    description="Microservicio de Forecasting Holt-Winters, Métricas CMI y Power BI Integration",
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

app.include_router(forecast.router)
app.include_router(kpis.router)

@app.get("/api/v1/powerbi/embed-token", tags=["Power BI"])
def get_powerbi_embed_token(report_id: str = Query(None, description="Identificador del reporte Power BI")):
    """Retorna configuración segura y Embed Token para renderizar Power BI en el cliente."""
    return PowerBIEmbedService.get_embed_config(report_id)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "analytics-service",
            "port": 8003,
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Falla de base de datos en analytics-service: {e}")
        raise HTTPException(status_code=503, detail="DB degradada.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
