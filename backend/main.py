"""
backend/main.py
---------------
Entrypoint principal de FastAPI para GiraGroup BI System (Sprint 4).
Incluye configuración de middleware de cabeceras de seguridad OWASP (A05)
y manejo centralizado de excepciones sanitizadas.
"""

import os
import time
import logging
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Request, Response, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import get_db
from core.security import require_roles, create_access_token, verify_password
from models.user import User
from schemas.pipeline_schemas import PipelineExecutionResponse
from routers.pipeline import process_pipeline
from routers import (
    riesgos,
    forecast,
    auth,
    users,
    notifications,
    dataops,
    audit,
    catalogs,
    kpis,
    pipeline,
    reportes,
    cmi,
    powerbi
)
from seed_users import seed_default_users

logger = logging.getLogger("api_main")

# Migraciones que el arranque aplica si faltan, en este orden
MIGRACIONES_EN_ARRANQUE = (
    "003_dataops_lote_and_facts_alignment.sql",
    "004_extend_tipo_fuente_sources.sql",
    "005_alinear_esquema_con_ddl.sql",
    "006_capa_semantica_cmi.sql",
    "007_powerbi_informe_version.sql",
    "008_dataops_tarea.sql",
    "009_cache_indice_beto.sql",
    "010_dataops_tarea_ingesta.sql",
)
MIGRACION_LOTE = "003_dataops_lote_and_facts_alignment.sql"
MIGRACION_TIPO_FUENTE = "004_extend_tipo_fuente_sources.sql"
# pg_advisory_lock: los workers de uvicorn arrancan a la vez; solo uno migra y los demás esperan
LLAVE_LOCK_ARRANQUE = 7_310_004


def migraciones_a_aplicar(aplicadas: set) -> list:
    """
    003 recrea chk_dim_origen_tipo_fuente con 4 tipos. Si 004 ya está aplicada, reaplicar 003 fallaría
    (hay documentos RENTABILIDAD) o estrecharía la restricción: con 004 aplicada no se reaplica 003.
    005 (alineación con db/schema.sql) se aplica una vez, también al restaurar un respaldo anterior.
    """
    pendientes = [m for m in MIGRACIONES_EN_ARRANQUE if m not in aplicadas]
    if MIGRACION_TIPO_FUENTE in aplicadas:
        pendientes = [m for m in pendientes if m != MIGRACION_LOTE]
    return pendientes


def _migraciones_aplicadas(conn) -> set:
    """Versiones en schema_migrations, más 004 si la restricción vigente ya admite RENTABILIDAD (comprobación previa)."""
    aplicadas = set()
    if conn.execute(text("SELECT to_regclass('public.schema_migrations')")).scalar():
        aplicadas |= {v for (v,) in conn.execute(text("SELECT version FROM public.schema_migrations"))}
    definicion = conn.execute(text(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'chk_dim_origen_tipo_fuente'"
    )).scalar()
    if definicion and "RENTABILIDAD" in definicion:
        aplicadas.add(MIGRACION_TIPO_FUENTE)
    return aplicadas

app = FastAPI(
    title="GiraGroup BI System API",
    description="API REST de Inteligencia de Negocios y Forecasting Predictivo (Sprint 4)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
def on_startup():
    import sys
    if ("pytest" in sys.modules) or (os.getenv("TESTING") == "true") or (os.getenv("APP_ENV") == "test"):
        return

    from pathlib import Path
    from core.database import Base, engine
    import models  # noqa: F401  registro de tablas

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT pg_advisory_lock(:llave)"), {"llave": LLAVE_LOCK_ARRANQUE})
            conn.commit()
            try:
                try:
                    Base.metadata.create_all(bind=conn)
                    conn.execute(text("""
                        ALTER TABLE staging_registros_crudos ADD COLUMN IF NOT EXISTS requiere_revision BOOLEAN DEFAULT FALSE;
                        ALTER TABLE staging_registros_crudos ADD COLUMN IF NOT EXISTS score_confianza NUMERIC(5, 4) DEFAULT 1.0;
                        ALTER TABLE staging_registros_crudos ADD COLUMN IF NOT EXISTS resuelto BOOLEAN DEFAULT FALSE;
                        ALTER TABLE staging_registros_crudos ADD COLUMN IF NOT EXISTS resuelto_por INTEGER REFERENCES users(id) ON DELETE SET NULL;
                        ALTER TABLE staging_registros_crudos ADD COLUMN IF NOT EXISTS resuelto_en TIMESTAMP;
                        ALTER TABLE fact_rendimiento_academico ADD COLUMN IF NOT EXISTS estado_tutoria VARCHAR(50);
                        ALTER TABLE fact_rendimiento_academico ADD COLUMN IF NOT EXISTS estado_arca VARCHAR(50);
                        ALTER TABLE fact_evaluacion_docente ADD COLUMN IF NOT EXISTS tipo_pregunta VARCHAR(20);
                        ALTER TABLE fact_evaluacion_docente ADD COLUMN IF NOT EXISTS escala_max INTEGER;
                        ALTER TABLE fact_evaluacion_docente ADD COLUMN IF NOT EXISTS clave_respuesta VARCHAR(64);
                        CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_eval_clave ON fact_evaluacion_docente (clave_respuesta);
                    """))
                    conn.commit()

                    dir_migraciones = Path(__file__).resolve().parent / "scripts" / "migrations"
                    for nombre in migraciones_a_aplicar(_migraciones_aplicadas(conn)):
                        mig = dir_migraciones / nombre
                        if mig.exists():
                            conn.execute(text(mig.read_text(encoding="utf-8")))
                            conn.commit()
                            logger.info("Migración aplicada en el arranque: %s", nombre)
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error creating/migrating DB tables: {e}")

                try:
                    seed_default_users()
                except Exception as e:
                    logger.error(f"Error seeding default users: {e}")
            finally:
                conn.execute(text("SELECT pg_advisory_unlock(:llave)"), {"llave": LLAVE_LOCK_ARRANQUE})
                conn.commit()
    except Exception as e:  # BD no disponible: la API arranca igual y lo deja en el log
        logger.error(f"Error creating/migrating DB tables: {e}")

# ── Middleware de Seguridad OWASP y Cabeceras de Caché HTTP ───────────────────
_CACHEABLE_GET_PREFIXES = (
    "/api/v1/catalogs/institutional-summary",
    "/api/v1/catalogs/financial/concepts",
    "/api/v1/docentes",
    "/api/v1/modulos",
    "/api/v1/instituciones",
    "/api/v1/kpis",
)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    t0 = time.perf_counter()
    response: Response = await call_next(request)
    dur_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    response.headers["Server-Timing"] = f"app;dur={dur_ms}"
    if dur_ms > 300.0 and request.url.path.startswith("/api/"):
        logger.warning(f"[SLOW ENDPOINT] {request.method} {request.url.path} tardó {dur_ms} ms (presupuesto: 300 ms)")
    # Las cabeceras de seguridad OWASP (X-Frame-Options, CSP, etc.) las pone solo el gateway nginx:
    # repetirlas aquí las duplicaba en cada respuesta. Este middleware solo agrega las de caché.
    if request.method == "GET" and response.status_code == 200:
        if any(request.url.path.startswith(p) for p in _CACHEABLE_GET_PREFIXES):
            response.headers.setdefault("Cache-Control", "private, max-age=60, stale-while-revalidate=120")
            response.headers.setdefault("Vary", "Authorization, Accept-Encoding")
    return response


# ── Compresión HTTP GZip (respuestas >= 1000 bytes) ──────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Middleware CORS Controlado ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Frontend React Vite
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ── Registro de Routers del Monolito Core ─────────────────────────────────────
app.include_router(dataops.router)
app.include_router(kpis.router)
app.include_router(cmi.router)
app.include_router(powerbi.router)
app.include_router(forecast.router)
app.include_router(riesgos.router)
app.include_router(catalogs.router)
app.include_router(reportes.router)
app.include_router(pipeline.router)
app.include_router(audit.router)

# Alias raíz de compatibilidad: el gateway (location /pipeline), el respaldo de auditApi.js y la suite
# de RBAC lo usan. Se eliminó en 73cc813 y devolvía 404; reutiliza la misma función y su control de roles.
app.add_api_route(
    "/pipeline/process",
    process_pipeline,
    methods=["POST"],
    response_model=PipelineExecutionResponse,
    summary="Alias de compatibilidad: Ejecutar pipeline completo bajo demanda",
    tags=["Pipeline Integrado"],
)

# En despliegue distribuido (Docker), auth, users y notifications corren en sus microservicios (:8001, :8002, :8004).
# Se montan condicionalmente en modo monolítico local / testing para compatibilidad con la suite pytest y TestClient.
if os.getenv("STANDALONE_MONOLITH", "true").lower() == "true":
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(notifications.router)





# ── Endpoint OAuth2 Password Flow / Login Unificado ─────────────────────────
@app.post("/api/v1/auth/login", summary="Login OAuth2 / JSON", tags=["Autenticación"])
async def swagger_oauth2_login(
    request: Request,
    db: Session = Depends(get_db)
):
    """Permite autenticarse desde Swagger UI (OAuth2 Form) o clientes JSON (Locust/Frontend)."""
    username = None
    password = None
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.json()
        username = body.get("username") or body.get("email")
        password = body.get("password")
    else:
        form = await request.form()
        username = form.get("username") or form.get("email")
        password = form.get("password")

    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenciales incorrectas (usuario o contraseña inválidos)."
        )
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/", summary="Portal API Root", tags=["Monitoreo"])
def root():
    """Ruta raíz de la API para orientar accesos directos desde navegador."""
    return {
        "status": "online",
        "service": "GIRAGROUP BI System API",
        "message": "API REST operativa. Para acceder a la aplicación web interactiva, visite http://localhost:5173",
        "frontend_url": "http://localhost:5173",
        "docs_url": "http://localhost:8000/docs",
        "health_url": "http://localhost:8000/health"
    }


@app.api_route(
    "/api/v1/health",
    methods=["GET", "HEAD"],
    include_in_schema=False
)
@app.api_route(
    "/health",
    methods=["GET", "HEAD"],
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