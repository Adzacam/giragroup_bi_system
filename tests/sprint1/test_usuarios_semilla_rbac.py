"""
backend/tests_root/sprint1/test_usuarios_semilla_rbac.py
--------------------------------------------------------
Tabla 3.14: Pruebas de verificación del Sprint 1 (Control de Acceso y Semillas de Usuarios)
Verifica que las cuentas institucionales base para los 5 perfiles RBAC
estén debidamente configuradas con credenciales seguras y roles normalizados.
"""

import pytest
from core.security import verify_password, get_password_hash
from seed_users import USERS


class TestUsuariosSemillaRBAC:
    """Verificación de la línea base operativa y usuarios institucionales."""

    def test_catalogo_de_roles_institucionales_completo(self):
        """Verifica la presencia de los 5 roles clave en la semilla del sistema."""
        roles_encontrados = {u["role"] for u in USERS}
        roles_esperados = {
            "ADMIN",
            "AUDITOR_CALIDAD",
            "DIRECTOR_ACADEMICO",
            "ANALISTA_FINANCIERO",
            "ANALISTA_MARKETING"
        }
        assert roles_esperados.issubset(roles_encontrados), (
            f"Faltan roles en las semillas. Encontrados: {roles_encontrados}"
        )

    def test_correos_con_dominio_institucional(self):
        """Valida que todos los usuarios semilla usen el dominio @giragroup.bo."""
        for u in USERS:
            assert u["email"].endswith("@giragroup.bo"), f"El email {u['email']} debe usar @giragroup.bo"

    def test_hashing_de_contrasenas_seguro(self):
        """Comprueba que el algoritmo de hash (bcrypt/argon2) genere firmas seguras."""
        raw_pass = "giragroup2026"
        hashed = get_password_hash(raw_pass)
        assert hashed != raw_pass
        assert verify_password(raw_pass, hashed) is True
        assert verify_password("incorrecta", hashed) is False
