"""
backend/tests_root/sprint1/test_esquema_constelacion_hefesto.py
--------------------------------------------------------------
Tabla 3.14: Pruebas de verificación del Sprint 1 (Esquema Constelación en PostgreSQL)
Metodología Hefesto Fase 3: Modelo Lógico Dimensional.
Verifica:
1. Definición formal en db/schema.sql de las tablas de hechos y dimensiones.
2. Integridad de los diccionarios de datos (Tablas 3.10, 3.11, 3.12, 3.13).
3. Relaciones de llaves foráneas del modelo estrella/constelación.
"""

from pathlib import Path
import re
import pytest


def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "db" / "schema.sql").exists():
            return parent
    return current.parent.parent.parent


class TestEsquemaConstelacionHefesto:
    """Verificación DDL del Almacén Dimensional según Metodología Hefesto."""

    @pytest.fixture(scope="class")
    @staticmethod
    def schema_sql_content():
        root_dir = get_repo_root()
        schema_path = root_dir / "db" / "schema.sql"
        assert schema_path.exists(), f"db/schema.sql debe existir en la raíz del proyecto (buscado en {schema_path})"
        with open(schema_path, "r", encoding="utf-8") as f:
            return f.read().lower()

    def test_tabla_hechos_fact_rendimiento_academico(self, schema_sql_content):
        """Verifica la definición de fact_rendimiento_academico (Tabla 3.10)."""
        match = re.search(
            r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?fact_rendimiento_academico\s*\((.*?)\);",
            schema_sql_content,
            re.DOTALL
        )
        assert match, "Tabla fact_rendimiento_academico debe estar definida en db/schema.sql"
        table_body = match.group(1)

        # Métricas aditivas y semiaditivas
        assert "nota_final" in table_body
        assert "asistencia_pct" in table_body
        assert "incumplimiento_actividades_pct" in table_body
        assert "nivel_confianza_ia" in table_body
        assert "requiere_revision" in table_body

    def test_tabla_hechos_fact_situacion_financiera(self, schema_sql_content):
        """Verifica la definición de fact_situacion_financiera (Tabla 3.11)."""
        match = re.search(
            r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?fact_situacion_financiera\s*\((.*?)\);",
            schema_sql_content,
            re.DOTALL
        )
        assert match, "Tabla fact_situacion_financiera debe estar definida en db/schema.sql"
        table_body = match.group(1)

        assert "monto_pagado" in table_body
        assert "cuotas_impagas" in table_body
        assert "monto_deuda" in table_body
        assert "estado_cartera" in table_body

    def test_tablas_dimensiones_principales(self, schema_sql_content):
        """Verifica las 5 dimensiones del modelo constelación (Tabla 3.12)."""
        dimensiones_requeridas = [
            "dim_estudiante",
            "dim_docente",
            "dim_modulo",
            "dim_tiempo",
            "dim_origen_documental"
        ]
        for dim in dimensiones_requeridas:
            pattern = rf"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?{dim}\b"
            assert re.search(pattern, schema_sql_content), f"La dimensión {dim} debe estar definida en db/schema.sql"

    def test_tabla_transaccional_users(self, schema_sql_content):
        """Verifica la tabla de control de acceso RBAC users (Tabla 3.13)."""
        match = re.search(
            r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?users\s*\((.*?)\);",
            schema_sql_content,
            re.DOTALL
        )
        assert match, "Tabla users debe estar definida en db/schema.sql"
        table_body = match.group(1)

        assert "email" in table_body
        assert "hashed_password" in table_body
        assert "role" in table_body
        assert "is_active" in table_body

    def test_integridad_referencial_llaves_foraneas(self, schema_sql_content):
        """Verifica que los hechos referencien a las dimensiones mediante foreign keys."""
        match_aca = re.search(
            r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?fact_rendimiento_academico\s*\((.*?)\);",
            schema_sql_content,
            re.DOTALL
        )
        assert match_aca, "Tabla fact_rendimiento_academico no encontrada"
        aca_body = match_aca.group(1)

        assert re.search(r"references\s+(?:public\.)?dim_estudiante", aca_body)
        assert re.search(r"references\s+(?:public\.)?dim_modulo", aca_body)
        assert re.search(r"references\s+(?:public\.)?dim_tiempo", aca_body)
        assert re.search(r"references\s+(?:public\.)?dim_origen_documental", aca_body)
        assert re.search(r"references\s+(?:public\.)?dim_docente", aca_body)

        match_fin = re.search(
            r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?fact_situacion_financiera\s*\((.*?)\);",
            schema_sql_content,
            re.DOTALL
        )
        assert match_fin, "Tabla fact_situacion_financiera no encontrada"
        fin_body = match_fin.group(1)

        assert re.search(r"references\s+(?:public\.)?dim_estudiante", fin_body)
        assert re.search(r"references\s+(?:public\.)?dim_tiempo", fin_body)
        assert re.search(r"references\s+(?:public\.)?dim_categoria_financiera", fin_body)
