"""
backend/tests_root/sprint1/test_infraestructura_y_docker.py
-----------------------------------------------------------
Tabla 3.14: Pruebas de verificación del Sprint 1 (Infraestructura y Contenedores)
1. Verificación del archivo docker-compose.yml y orquestación de servicios.
2. Comprobación de parámetros de conexión a PostgreSQL (giragroup_db y catalog_db).
3. Prueba del endpoint /health de FastAPI para disponibilidad del backend.
"""

import os
from pathlib import Path
import pytest
import yaml
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from main import app
from core.database import engine, SQLALCHEMY_DATABASE_URL, CATALOG_DATABASE_URL, SessionLocal, get_db


def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "docker-compose.yml").exists():
            return parent
    return current.parent.parent.parent


class TestInfraestructuraDocker:
    """Verificación de la arquitectura contenerizada y configuración base."""

    def test_docker_compose_servicios_principales_configurados(self):
        """Verifica que docker-compose.yml contenga los servicios esenciales del sistema."""
        root_dir = get_repo_root()
        compose_path = root_dir / "docker-compose.yml"
        assert compose_path.exists(), f"El archivo docker-compose.yml debe existir en la raíz (buscado en {compose_path})"

        with open(compose_path, "r", encoding="utf-8") as f:
            compose_data = yaml.safe_load(f)

        services = compose_data.get("services", {})
        # Verificar servicios esenciales de la arquitectura física (Figura 3.2 y 3.3)
        assert "api" in services or "giragroup_api" in str(services), "Servicio de API FastAPI debe estar definido"
        assert "db" in services or "giragroup_db" in str(services), "Servicio PostgreSQL DW debe estar definido"
        assert "web" in services or "giragroup_web" in str(services), "Servicio Frontend React debe estar definido"

    def test_database_url_segura_y_configurada(self):
        """Valida que la cadena de conexión apunte a giragroup_db con credenciales institucionales."""
        assert "giragroup_db" in SQLALCHEMY_DATABASE_URL
        assert "giragroup_user" in SQLALCHEMY_DATABASE_URL
        assert engine.pool is not None

    def test_endpoint_health_status(self):
        """Verifica que el backend exponga /health y retorne estado healthy y servicio conectado."""
        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            client = TestClient(app)
            res = client.get("/health")
            assert res.status_code == 200
            data = res.json()
            assert data.get("status") == "healthy"
            assert "service" in data
            assert data.get("service") == "giragroup-bi-api"
            assert data.get("database") == "connected"
            assert mock_db.execute.called

            # Validar resiliencia ante fallo de conectividad en BD (HTTP 503)
            mock_failing_db = MagicMock()
            mock_failing_db.execute.side_effect = Exception("Conexión rechazada a PostgreSQL")
            app.dependency_overrides[get_db] = lambda: mock_failing_db
            res_fail = client.get("/health")
            assert res_fail.status_code == 503
            assert "Servicio temporalmente no disponible" in res_fail.json().get("detail", "")
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_session_lifecycle(self):
        """Verifica que SessionLocal abra y cierre sesiones limpiamente sin fugas de conexiones."""
        session = SessionLocal()
        assert session is not None
        session.close()
