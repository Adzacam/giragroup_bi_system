import os
import socket
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

def _can_resolve(host: str) -> bool:
    try:
        socket.gethostbyname(host)
        return True
    except (socket.gaierror, Exception):
        return False

# ── 1. Base de Datos Data Warehouse (Esquema Constelación) ─────────────
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://giragroup_user:giragroup_secret_2026@localhost:5432/giragroup_db"
)

# Ajuste dinámico de host: si estamos dentro de Docker o si giragroup_db es resoluble
if os.getenv("DOCKER_ENV") and _can_resolve("giragroup_db"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("localhost", "giragroup_db")
elif "giragroup_db" in SQLALCHEMY_DATABASE_URL and not _can_resolve("giragroup_db"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("giragroup_db", "localhost")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"connect_timeout": 1},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── 2. Base de Datos de Catálogos Institucionales (3NF) ─────────────────
CATALOG_DATABASE_URL = os.getenv(
    "CATALOG_DATABASE_URL",
    "postgresql://giragroup_user:giragroup_secret_2026@localhost:5433/giragroup_catalog_db"
)

if os.getenv("DOCKER_ENV") and _can_resolve("catalog_db"):
    CATALOG_DATABASE_URL = CATALOG_DATABASE_URL.replace("localhost:5433", "catalog_db:5432").replace("localhost:5432", "catalog_db:5432")
elif "catalog_db" in CATALOG_DATABASE_URL and not _can_resolve("catalog_db"):
    CATALOG_DATABASE_URL = CATALOG_DATABASE_URL.replace("catalog_db:5432", "localhost:5433").replace("catalog_db", "localhost")

catalog_engine = create_engine(
    CATALOG_DATABASE_URL,
    connect_args={"connect_timeout": 1},
    pool_pre_ping=True
)
CatalogSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=catalog_engine)
CatalogBase = declarative_base()

def get_catalog_db():
    db = CatalogSessionLocal()
    try:
        yield db
    finally:
        db.close()