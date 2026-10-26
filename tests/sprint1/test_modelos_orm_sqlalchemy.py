"""
backend/tests_root/sprint1/test_modelos_orm_sqlalchemy.py
---------------------------------------------------------
Tabla 3.14: Pruebas de verificación del Sprint 1 (Modelado ORM SQLAlchemy y Esquemas Pydantic)
Metodología Hefesto Fase 4: Integración, Poblamiento y Modelado ORM.
Figura 3.6: Diagrama de Clases del sistema.
"""

import pytest
from sqlalchemy.orm import declarative_base

from models.dim_estudiante import DimEstudiante
from models.dim_docente import DimDocente
from models.dim_modulo import DimModulo
from models.dim_tiempo import DimTiempo
from models.dim_origen import DimOrigenDocumental
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from models.user import User


class TestModelosORMSQLAlchemy:
    """Verificación de mapeo de clases ORM SQLAlchemy."""

    def test_nombres_de_tablas_orm_coinciden_con_hefesto(self):
        """Verifica que cada clase ORM apunte a su respectiva tabla física."""
        assert DimEstudiante.__tablename__ == "dim_estudiante"
        assert DimDocente.__tablename__ == "dim_docente"
        assert DimModulo.__tablename__ == "dim_modulo"
        assert DimTiempo.__tablename__ == "dim_tiempo"
        assert DimOrigenDocumental.__tablename__ == "dim_origen_documental"
        assert FactRendimientoAcademico.__tablename__ == "fact_rendimiento_academico"
        assert FactSituacionFinanciera.__tablename__ == "fact_situacion_financiera"
        assert User.__tablename__ == "users"

    def test_instanciacion_modelo_hecho_academico(self):
        """Valida inicialización y tipos del hecho académico."""
        hecho = FactRendimientoAcademico(
            id_estudiante=1,
            id_modulo=2,
            id_docente=3,
            id_tiempo=20260215,
            id_documento=10,
            nota_final=88.5,
            asistencia_pct=88.0,
            incumplimiento_actividades_pct=12.0,
            nivel_confianza_ia=0.985,
            requiere_revision=False
        )
        assert hecho.id_estudiante == 1
        assert hecho.id_modulo == 2
        assert hecho.id_docente == 3
        assert hecho.id_tiempo == 20260215
        assert hecho.id_documento == 10
        assert hecho.nota_final == 88.5
        assert hecho.asistencia_pct == 88.0
        assert hecho.porcentaje_asistencia == 88.0
        assert hecho.incumplimiento_actividades_pct == 12.0
        assert hecho.requiere_revision is False
        assert hecho.nivel_confianza_ia > 0.85

    def test_instanciacion_modelo_hecho_financiero(self):
        """Valida inicialización y tipos del hecho financiero."""
        hecho_fin = FactSituacionFinanciera(
            id_estudiante=1,
            id_tiempo=20260215,
            id_documento=11,
            monto_pagado=1500.0,
            cuotas_impagas=0,
            monto_deuda=0.0,
            estado_cartera="Vigente"
        )
        assert hecho_fin.id_estudiante == 1
        assert hecho_fin.id_tiempo == 20260215
        assert hecho_fin.id_documento == 11
        assert hecho_fin.monto_pagado == 1500.0
        assert hecho_fin.cuotas_impagas == 0
        assert hecho_fin.monto_deuda == 0.0
        assert hecho_fin.estado_cartera == "Vigente"

    def test_modelo_usuario_campos_de_seguridad(self):
        """Valida que User posea soporte para 2FA, intentos fallidos y control de acceso."""
        user = User(
            username="test_admin",
            email="test@giragroup.bo",
            hashed_password="hashed_secret_example",
            role="ADMIN",
            is_active=True,
            is_mfa_enabled=True,
            failed_login_attempts=0
        )
        assert user.role == "ADMIN"
        assert user.is_active is True
        assert user.is_mfa_enabled is True
        assert user.failed_login_attempts == 0
