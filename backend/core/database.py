import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# ── 1. Base de Datos Data Warehouse (Esquema Constelación) ─────────────
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://giragroup_user:giragroup_secret_2026@localhost:5432/giragroup_db"
)

if os.getenv("DOCKER_ENV"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("localhost", "giragroup_db")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
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

if os.getenv("DOCKER_ENV"):
    CATALOG_DATABASE_URL = CATALOG_DATABASE_URL.replace("localhost:5433", "catalog_db:5432").replace("localhost:5432", "catalog_db:5432")

catalog_engine = create_engine(CATALOG_DATABASE_URL)
CatalogSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=catalog_engine)
CatalogBase = declarative_base()

def get_catalog_db():
    db = CatalogSessionLocal()
    try:
        yield db
    finally:
        db.close()