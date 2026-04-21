import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

# Obtener la URL de conexión. Si usas psycopg2 en el requirements, 
# la URL debe ser: postgresql://admin:admin123@localhost:5432/giragroup_bi
# Si el contenedor está corriendo, usará 'db' como host. Para local, usamos localhost.
# La función asume que tienes DATABASE_URL configurada.
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://admin:admin123@localhost:5432/giragroup_bi"
)

# En el mundo de Docker, la API buscará el host "db" en lugar de "localhost".
# Este pequeño truco cambia localhost a db si detecta que estamos dentro de Docker.
if os.getenv("DOCKER_ENV"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("localhost", "db")

# Crear el motor de conexión
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Crear la fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para crear los modelos ORM
Base = declarative_base()

# Dependencia para obtener la sesión de BD en cada endpoint
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()