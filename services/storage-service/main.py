"""
services/storage-service/main.py
--------------------------------
Microservicio de Almacenamiento e Ingesta de Archivos Heterogéneos (Puerto 8005).
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.storage_router import router as storage_router

logger = logging.getLogger("storage_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="GIRAGROUP BI — File Storage Service",
    description="Microservicio de Carga, Almacenamiento y Lectura Heterogénea de Documentos",
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

app.include_router(storage_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "storage-service",
        "port": 8005
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
