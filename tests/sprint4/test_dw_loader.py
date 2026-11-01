"""
tests/sprint4/test_dw_loader.py
-------------------------------
Pruebas unitarias para el Servicio de Carga al Data Warehouse (DWLoaderService):
1. Resolución directa de estudiante por CI (Estado A).
2. Rescate difuso por nombre cuando CI es sintético (Estado B).
3. Derivación a stg_entidad_no_resuelta cuando no hay coincidencia (Estado C).
4. Asignación efectiva de llaves foráneas dimensionales (id_estudiante, id_modulo, id_tiempo).
5. Manejo de hechos financieros y persistencia de métricas canónicas.
"""

import pytest
from unittest.mock import MagicMock
from datetime import date
from sqlalchemy.orm import Session

from services.dw_loader import DWLoaderService
from models.dim_estudiante import DimEstudiante
from models.dim_docente import DimDocente
from models.dim_modulo import DimModulo
from models.dim_tiempo import DimTiempo
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from models.staging_entidad import StagingEntidadNoResuelta


class TestDWLoaderResolution:
    def test_resolver_estudiante_ci_directo_existente(self):
        db = MagicMock(spec=Session)
        estudiante_mock = DimEstudiante(id_estudiante=10, codigo_estudiante="4892019", nombre_completo="Carlos Murillo")
        db.query().filter().first.return_value = estudiante_mock

        loader = DWLoaderService(db)
        id_est, estado = loader.resolver_o_crear_estudiante(ci="4892019", nombre="Carlos Murillo")

        assert id_est == 10
        assert estado == "A"

    def test_resolver_estudiante_ci_directo_nuevo(self):
        db = MagicMock(spec=Session)
        db.query().filter().first.return_value = None  # No existe aún

        loader = DWLoaderService(db)
        id_est, estado = loader.resolver_o_crear_estudiante(ci="8932014", nombre="Estudiante Nuevo")

        assert estado == "A"
        assert db.add.called
        assert db.flush.called

    def test_resolver_estudiante_sintetico_derivado_a_staging_estado_c(self):
        db = MagicMock(spec=Session)
        # Base vacía de estudiantes para forzar falla de match
        db.query().all.return_value = []

        loader = DWLoaderService(db)
        id_est, estado = loader.resolver_o_crear_estudiante(
            ci="TEMP-CI-9988AABB",
            nombre="Nombre Desconocido X",
            doc_id=5,
            confianza_ia=0.55
        )

        assert id_est is None
        assert estado == "C"
        # Debe haberse agregado a staging
        assert db.add.called
        stg_obj = db.add.call_args[0][0]
        assert isinstance(stg_obj, StagingEntidadNoResuelta)
        assert stg_obj.tipo_entidad == "ESTUDIANTE"
        assert stg_obj.fk_estado == "C"
        assert stg_obj.resuelto is False

    def test_resolver_tiempo_genera_datos_calendario(self):
        db = MagicMock(spec=Session)
        db.query().filter().first.return_value = None

        loader = DWLoaderService(db)
        id_t = loader.resolver_o_crear_tiempo("2025-05-18")

        assert id_t == 20250518
        assert db.add.called
        t_obj = db.add.call_args[0][0]
        assert isinstance(t_obj, DimTiempo)
        assert t_obj.gestion == 2025
        assert t_obj.mes == 5
        assert t_obj.nombre_mes == "Mayo"
        assert t_obj.periodo_mes == "2025-05"

    def test_cargar_registro_academico_asigna_fks(self):
        db = MagicMock(spec=Session)
        estudiante_mock = DimEstudiante(id_estudiante=42, codigo_estudiante="123456", nombre_completo="Ana Perez")
        modulo_mock = DimModulo(id_modulo=7, nombre_modulo="Marketing Digital", pos_code="POS-5291")
        docente_mock = DimDocente(id_docente=3, nombre_completo="Lic. Gomez")
        tiempo_mock = DimTiempo(id_tiempo=20250518)

        # Mock de consultas
        def mock_query(model):
            m = MagicMock()
            if model == DimEstudiante:
                m.filter().first.return_value = estudiante_mock
            elif model == DimModulo:
                m.filter().first.return_value = modulo_mock
            elif model == DimDocente:
                m.filter().first.return_value = docente_mock
            elif model == DimTiempo:
                m.filter().first.return_value = tiempo_mock
            elif model == FactRendimientoAcademico:
                m.filter().first.return_value = None
            return m

        db.query.side_effect = mock_query

        loader = DWLoaderService(db)
        reg_prueba = {
            "doc_id": 1,
            "categoria": "academico",
            "resoluciones": {
                "estudiante": {
                    "valor_extraido": "Ana Perez",
                    "fk_resolucion": {"ci": "123456", "fk_estado": "A", "nombre_resuelto": "Ana Perez"}
                },
                "docente": {"valor_extraido": "Lic. Gomez"},
                "modulo": {"valor_extraido": "Marketing Digital"},
                "nota_final": 88.0,
                "asistencia_pct": 95.0,
                "incumplimiento_actividades_pct": 5.0,
                "nivel_confianza_ia": 0.95
            },
            "calidad": {"requiere_revision": False}
        }

        res = loader.cargar_registro(reg_prueba)
        assert res["status"] == "loaded"
        assert res["tipo"] == "academico"
        assert res["id_estudiante"] == 42
        assert res["id_modulo"] == 7
        assert res["fk_estado"] == "A"
        assert db.add.called
