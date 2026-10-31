"""
tests/test_kpi_service.py
-------------------------
Pruebas unitarias para el KPI ticket_promedio_bs en KPIService:
1. Cálculo estático exacto de recaudación / matrícula.
2. Manejo estricto de división por cero (matrícula 0 o nula).
3. Cálculo por programa con datos agregados de hechos financieros y académicos.
4. Presencia del KPI ticket promedio en la perspectiva FINANCIERA del CMI.
"""

import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from services.kpi_service import KPIService


class TestKPITicketPromedio:
    def test_calcular_ticket_promedio_estatico_exactitud(self):
        """Valida que ticket_promedio_bs = recaudación / matrícula sea exacto."""
        # Caso exacto
        ticket = KPIService.calcular_ticket_promedio(recaudacion=150000.0, matricula=30)
        assert ticket == 5000.0

        # Caso con redondeo a 2 decimales
        ticket_decimal = KPIService.calcular_ticket_promedio(recaudacion=10000.0, matricula=3)
        assert ticket_decimal == 3333.33

        # Caso recaudación cero
        ticket_cero = KPIService.calcular_ticket_promedio(recaudacion=0.0, matricula=25)
        assert ticket_cero == 0.0

    def test_calcular_ticket_promedio_manejo_division_por_cero(self):
        """Valida que matrícula = 0 o valores nulos/negativos no lancen ZeroDivisionError y retornen 0.0."""
        # Matrícula cero con recaudación positiva
        res_cero = KPIService.calcular_ticket_promedio(recaudacion=75000.0, matricula=0)
        assert res_cero == 0.0

        # Matrícula None o negativa
        res_none = KPIService.calcular_ticket_promedio(recaudacion=50000.0, matricula=None)
        assert res_none == 0.0

        res_neg = KPIService.calcular_ticket_promedio(recaudacion=50000.0, matricula=-10)
        assert res_neg == 0.0

    def test_calcular_ticket_promedio_por_programa_con_db_mock(self):
        """
        Valida que calcular_ticket_promedio_por_programa cruce recaudación y matrícula
        por programa de forma exacta y controle división por cero por programa.
        """
        db = MagicMock(spec=Session)

        # Mock query de recaudación: (programa, total_recaudacion, alumnos_pagantes)
        filas_recaudacion = [
            ("Diplomado en BI y Big Data", 150000.0, 30),
            ("Maestría en Data Science", 240000.0, 20),
            ("Curso Corto Python", 15000.0, 0),  # Matrícula 0 -> debe dar 0.0
        ]

        # Mock query de matrícula académica: (programa, total_matricula)
        filas_matricula = [
            ("Diplomado en BI y Big Data", 30),
            ("Maestría en Data Science", 20),
            ("Curso Corto Python", 0),  # Matrícula académica 0
        ]

        q_rec = MagicMock()
        q_rec.outerjoin.return_value = q_rec
        q_rec.filter.return_value = q_rec
        q_rec.group_by.return_value.all.return_value = filas_recaudacion

        q_mat = MagicMock()
        q_mat.outerjoin.return_value = q_mat
        q_mat.filter.return_value = q_mat
        q_mat.group_by.return_value.all.return_value = filas_matricula

        # side_effect para alternar entre q_rec y q_mat
        db.query.side_effect = [q_rec, q_mat]

        service = KPIService(db)
        resultado = service.calcular_ticket_promedio_por_programa()

        assert len(resultado) == 3

        # Programa 1: Diplomado BI
        prog_bi = next(r for r in resultado if r["programa"] == "Diplomado en BI y Big Data")
        assert prog_bi["recaudacion_bs"] == 150000.0
        assert prog_bi["matricula"] == 30
        assert prog_bi["ticket_promedio_bs"] == 5000.0

        # Programa 2: Maestría Data Science
        prog_msc = next(r for r in resultado if r["programa"] == "Maestría en Data Science")
        assert prog_msc["recaudacion_bs"] == 240000.0
        assert prog_msc["matricula"] == 20
        assert prog_msc["ticket_promedio_bs"] == 12000.0

        # Programa 3: Curso Corto Python (División por cero controlada)
        prog_py = next(r for r in resultado if r["programa"] == "Curso Corto Python")
        assert prog_py["recaudacion_bs"] == 15000.0
        assert prog_py["matricula"] == 0
        assert prog_py["ticket_promedio_bs"] == 0.0

    def test_perspectiva_financiera_cmi_contiene_ticket_promedio(self):
        """Valida que el CMI consolidado exponga ticket_promedio_bs en la perspectiva financiera."""
        db = MagicMock(spec=Session)
        # Mockear las llamadas escalares y agregadas de cmi
        q_mock = MagicMock()
        q_mock.filter.return_value = q_mock
        q_mock.scalar.return_value = 10
        q_mock.outerjoin.return_value.group_by.return_value.all.return_value = []
        db.query.return_value = q_mock

        service = KPIService(db)
        cmi = service.obtener_perspectivas_cmi_completo()

        assert cmi["status"] == "success"
        persp_fin = cmi["perspectivas"]["financiera"]
        assert "ticket_promedio_bs" in persp_fin
        assert isinstance(persp_fin["ticket_promedio_bs"], (int, float))
        assert persp_fin["ticket_promedio_bs"] >= 0.0
        assert "ticket_promedio_programas" in persp_fin
        assert isinstance(persp_fin["ticket_promedio_programas"], list)


@pytest.fixture
def sqlite_dw():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from core.database import Base
    import models.dim_modulo, models.dim_tiempo, models.fact_marketing  # noqa: F401  registro de tablas

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def do_connect(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("ATTACH DATABASE ':memory:' AS public")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


class TestKPIConversionAdmisiones:
    def test_conversion_ignora_filas_sin_leads(self, sqlite_dw):
        """
        Las filas del seed histórico (leads = 0) no deben entrar al cálculo:
        antes 34 leads vs 15 224 inscritos daban una conversión de 44 776 %.
        """
        from models.dim_modulo import DimModulo
        from models.dim_tiempo import DimTiempo
        from models.fact_marketing import FactMarketing

        sqlite_dw.add_all([
            DimModulo(id_modulo=1, nombre_modulo="Diplomado BI", programa="Diplomados"),
            DimTiempo(id_tiempo=1, gestion=2026, periodo_mes="2026-05"),
        ])
        sqlite_dw.add_all([
            FactMarketing(id_modulo=1, id_tiempo=1, leads=40, reservas=0, inscritos=10),
            FactMarketing(id_modulo=1, id_tiempo=1, leads=0, reservas=0, inscritos=500),  # seed histórico
        ])
        sqlite_dw.commit()

        cmi = KPIService(sqlite_dw).obtener_perspectivas_cmi_completo()

        assert cmi["kpis"]["6_tasa_conversion_admisiones"] == 25.0
        assert cmi["perspectivas"]["cliente_mercado"]["total_postulantes_leads"] == 40
