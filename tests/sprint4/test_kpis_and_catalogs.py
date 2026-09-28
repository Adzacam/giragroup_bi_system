"""
tests/sprint4/test_kpis_and_catalogs.py
---------------------------------------
Pruebas para los servicios de Catálogos (con filtrado PoLP) y cálculo de KPIs:
1. Filtrado de datos financieros sensibles según rol del solicitante en detalle de estudiante.
2. Verificación de cálculo de KPIs agregados (promedios, porcentajes de aprobación, montos en mora).
"""

import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from services.catalog_service import CatalogService
from services.kpi_service import KPIService
from models.dim_estudiante import DimEstudiante
from models.dim_docente import DimDocente
from models.dim_modulo import DimModulo
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera


class TestCatalogServicePoLP:
    def test_detalle_estudiante_oculta_finanzas_para_director_academico(self):
        db = MagicMock(spec=Session)
        est_mock = DimEstudiante(id_estudiante=5, nombre_completo="Laura Ortiz", codigo_estudiante="887766")
        db.query().filter().first.return_value = est_mock
        db.query().outerjoin().filter().all.return_value = []

        service = CatalogService(db)
        # Director Académico no debe tener acceso a situación financiera
        res = service.detalle_estudiante(id_estudiante=5, rol_usuario="DIRECTOR_ACADEMICO")

        assert res is not None
        assert res["nombre_completo"] == "Laura Ortiz"
        assert res["situacion_financiera"] is None  # PoLP: Ocultado estrictamente

    def test_detalle_estudiante_muestra_finanzas_para_analista_financiero(self):
        db = MagicMock(spec=Session)
        est_mock = DimEstudiante(id_estudiante=5, nombre_completo="Laura Ortiz", codigo_estudiante="887766")
        hecho_fin_mock = FactSituacionFinanciera(
            id_estudiante=5,
            monto_deuda=2500.0,
            cuotas_impagas=1,
            estado_cartera="Vigente",
            tipo_alerta="NORMAL"
        )

        q_est = MagicMock()
        q_est.filter.return_value.first.return_value = est_mock
        q_fin = MagicMock()
        q_fin.filter.return_value.order_by.return_value.first.return_value = hecho_fin_mock
        q_empty = MagicMock()
        q_empty.outerjoin.return_value.filter.return_value.all.return_value = []

        def mock_query(*args, **kwargs):
            if args and args[0] == DimEstudiante:
                return q_est
            elif args and args[0] == FactSituacionFinanciera:
                return q_fin
            return q_empty

        db.query.side_effect = mock_query

        service = CatalogService(db)
        res = service.detalle_estudiante(id_estudiante=5, rol_usuario="ANALISTA_FINANCIERO")

        assert res is not None
        assert res["situacion_financiera"] is not None
        assert res["situacion_financiera"]["monto_deuda"] == 2500.0
        assert res["situacion_financiera"]["cuotas_impagas"] == 1


class TestKPIServiceCalculations:
    def test_kpis_academicos_calculo_tasas(self):
        db = MagicMock(spec=Session)
        q_mock = MagicMock()
        q_mock.filter.return_value = q_mock
        q_mock.scalar.side_effect = [
            100,    # total evaluaciones
            75.5,   # promedio notas
            80,     # aprobados
            20,     # en riesgo <= 70
            5       # en riesgo deserción
        ]
        db.query.return_value = q_mock

        service = KPIService(db)
        kpis = service.obtener_kpis_academicos()

        assert kpis["total_evaluaciones_registradas"] == 100
        assert kpis["tasa_aprobacion_pct"] == 80.0
        assert kpis["tasa_reprobacion_pct"] == 20.0
        assert kpis["promedio_general_notas"] == 75.5
        assert kpis["estudiantes_en_riesgo_academico"] == 20

    def test_kpis_financieros_calculo_totales(self):
        db = MagicMock(spec=Session)
        q_mock = MagicMock()
        q_mock.filter.return_value = q_mock
        q_mock.scalar.side_effect = [
            50,        # total hechos fin
            150000.0,  # total deuda
            15,        # con mora
            35,        # sum cuotas
            3,         # previsionable
            7,         # mora
            40         # vigente
        ]
        db.query.return_value = q_mock

        service = KPIService(db)
        kpis = service.obtener_kpis_financieros()

        assert kpis["monto_total_deuda_bs"] == 150000.0
        assert kpis["estudiantes_con_cuotas_impagas"] == 15
        assert kpis["estudiantes_cartera_previsionable"] == 3
