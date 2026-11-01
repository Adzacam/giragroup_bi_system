"""
tests/sprint3/test_cross_source_reconciliation.py
-------------------------------------------------
Suite de pruebas unitarias para el Loop 3:
1. Cascada jerárquica de resolución de identidad:
   CI -> ID/Código Estudiante -> Correo -> Nombre + Programa (Fuzzy RapidFuzz)
2. Normalización de CI con sufijos departamentales ('4892019 LP' -> '4892019').
3. Detección de Discrepancias Cross-Source (Fragmentación Informacional):
   - Estudiante en Moodle pero ausente en Cobranzas.
   - Estudiante en Cobranzas pero ausente en Moodle.
   - Estudiante presente en ambas fuentes (Reconciliado).
4. Auditoría de fragmentación de lote.
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from core.database import Base
from models.dim_estudiante import DimEstudiante
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from services.cross_source_reconciler import IdentityResolutionCascade, CrossSourceReconciler


@pytest.fixture(scope="module")
def sqlite_dw_db():
    """Base de datos en memoria para probar la resolución y cruces del Data Warehouse."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def do_connect(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("ATTACH DATABASE ':memory:' AS public")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    # 1. Estudiantes de prueba
    est1 = DimEstudiante(id_estudiante=1, codigo_estudiante="12345678", nombre_completo="Carlos Mamani Choque")
    est2 = DimEstudiante(id_estudiante=2, codigo_estudiante="EST-00452", nombre_completo="Ana Maria Flores")
    est3 = DimEstudiante(id_estudiante=3, codigo_estudiante="carlos.lopez", nombre_completo="Carlos Lopez Quispe")
    est4 = DimEstudiante(id_estudiante=4, codigo_estudiante="98765432", nombre_completo="Lucia Fernandez Rios")
    est5 = DimEstudiante(id_estudiante=5, codigo_estudiante="45678901", nombre_completo="Jorge Mendoza Ali")

    session.add_all([est1, est2, est3, est4, est5])
    session.flush()

    # 2. Hechos académicos (Moodle / Actas)
    # est1 tiene notas en Moodle
    # est4 tiene notas en Moodle (pero NO tendrá pagos en cobranzas)
    aca1 = FactRendimientoAcademico(id_estudiante=1, nota_final=85.0, estado_academico="Aprobado")
    aca4 = FactRendimientoAcademico(id_estudiante=4, nota_final=92.0, estado_academico="Aprobado")
    session.add_all([aca1, aca4])

    # 3. Hechos financieros (Cobranzas)
    # est1 tiene pago/deuda en Cobranzas (Reconciliado con aca1)
    # est5 tiene deuda en Cobranzas (pero NO tendrá notas en Moodle)
    fin1 = FactSituacionFinanciera(id_estudiante=1, monto_deuda=1500.0, cuotas_impagas=0, estado_cartera="Vigente")
    fin5 = FactSituacionFinanciera(id_estudiante=5, monto_deuda=3000.0, cuotas_impagas=2, estado_cartera="Mora")
    session.add_all([fin1, fin5])

    session.commit()
    yield session
    session.close()


class TestIdentityResolutionCascade:
    def test_normalizar_ci_con_sufijos(self):
        assert IdentityResolutionCascade.normalizar_ci("4892019 LP") == "4892019"
        assert IdentityResolutionCascade.normalizar_ci("  12345678-SC  ") == "12345678"
        assert IdentityResolutionCascade.normalizar_ci("98765432 CBBA") == "98765432"
        assert IdentityResolutionCascade.normalizar_ci(None) is None

    def test_nivel_1_resolucion_ci_directo(self, sqlite_dw_db):
        res = IdentityResolutionCascade.resolver_estudiante_cascada(sqlite_dw_db, ci="12345678")
        assert res["resuelto"] is True
        assert res["id_estudiante"] == 1
        assert res["nivel_resolucion"] == "CI"
        assert res["confianza"] == 100.0
        assert res["fk_estado"] == "A"
        assert res["requiere_revision"] is False

    def test_nivel_1_resolucion_ci_con_sufijo_departamental(self, sqlite_dw_db):
        res = IdentityResolutionCascade.resolver_estudiante_cascada(sqlite_dw_db, ci="12345678 LP")
        assert res["resuelto"] is True
        assert res["id_estudiante"] == 1
        assert res["nivel_resolucion"] == "CI"

    def test_nivel_2_resolucion_codigo_estudiante(self, sqlite_dw_db):
        res = IdentityResolutionCascade.resolver_estudiante_cascada(sqlite_dw_db, id_estudiante_codigo="EST-00452")
        assert res["resuelto"] is True
        assert res["id_estudiante"] == 2
        assert res["nivel_resolucion"] == "ID_ESTUDIANTE"
        assert res["confianza"] == 98.0
        assert res["fk_estado"] == "A"

    def test_nivel_3_resolucion_correo(self, sqlite_dw_db):
        res = IdentityResolutionCascade.resolver_estudiante_cascada(sqlite_dw_db, correo="carlos.lopez@giragroup.bo")
        assert res["resuelto"] is True
        assert res["id_estudiante"] == 3
        assert res["nivel_resolucion"] == "CORREO"
        assert res["confianza"] == 95.0

    def test_nivel_4_resolucion_fuzzy_nombre(self, sqlite_dw_db):
        # Nombre con leve variación o inversión
        res = IdentityResolutionCascade.resolver_estudiante_cascada(
            sqlite_dw_db,
            nombre="Carlos Mamani",
            programa="Diplomado en Gestión"
        )
        assert res["resuelto"] is True
        assert res["id_estudiante"] == 1
        assert res["nivel_resolucion"] == "NOMBRE_PROGRAMA"
        assert res["confianza"] >= 85.0
        assert res["fk_estado"] == "B"

    def test_nivel_5_no_resuelto_deriva_a_revision(self, sqlite_dw_db):
        res = IdentityResolutionCascade.resolver_estudiante_cascada(
            sqlite_dw_db,
            ci="99999999",
            nombre="Estudiante Fantasma Totalmente Desconocido"
        )
        assert res["resuelto"] is False
        assert res["id_estudiante"] is None
        assert res["nivel_resolucion"] == "NO_RESUELTO"
        assert res["fk_estado"] == "C"
        assert res["requiere_revision"] is True


class TestCrossSourceReconciler:
    def test_estudiante_reconciliado_en_ambas_fuentes(self, sqlite_dw_db):
        # est1 tiene registros tanto académicos como financieros
        res = CrossSourceReconciler.verificar_presencia_cruzada(sqlite_dw_db, id_estudiante=1)
        assert res["reconciliado"] is True
        assert res["estado"] == "RECONCILIADO"
        assert res["tiene_academico"] is True
        assert res["tiene_financiero"] is True
        assert res["alerta"] is None
        assert res["fragmentacion_detectada"] is False

    def test_estudiante_en_moodle_ausente_en_cobranzas(self, sqlite_dw_db):
        # est4 tiene notas en Moodle pero NINGÚN registro en cobranzas
        res = CrossSourceReconciler.verificar_presencia_cruzada(sqlite_dw_db, id_estudiante=4)
        assert res["reconciliado"] is False
        assert res["estado"] == "DISCREPANCIA_SIN_COBRANZA"
        assert res["tiene_academico"] is True
        assert res["tiene_financiero"] is False
        assert res["fragmentacion_detectada"] is True
        assert "NO figura en las planillas de cobranza" in res["alerta"]

    def test_estudiante_en_cobranzas_ausente_en_moodle(self, sqlite_dw_db):
        # est5 tiene cuotas en Cobranzas pero NO tiene actividad en aula virtual
        res = CrossSourceReconciler.verificar_presencia_cruzada(sqlite_dw_db, id_estudiante=5)
        assert res["reconciliado"] is False
        assert res["estado"] == "DISCREPANCIA_SIN_AULA_VIRTUAL"
        assert res["tiene_academico"] is False
        assert res["tiene_financiero"] is True
        assert res["fragmentacion_detectada"] is True
        assert "NO registra actividad académica en el aula virtual" in res["alerta"]

    def test_auditoria_consolidada_de_lote(self, sqlite_dw_db):
        auditoria = CrossSourceReconciler.auditar_discrepancias_lote(sqlite_dw_db, limite=10)
        assert auditoria["total_estudiantes_auditados"] == 5
        assert auditoria["estudiantes_reconciliados"] >= 1
        assert auditoria["discrepancias_sin_cobranza"] >= 1
        assert auditoria["discrepancias_sin_aula_virtual"] >= 1
        assert auditoria["total_discrepancias_fragmentacion"] >= 2
        assert len(auditoria["casos_discrepancia"]) >= 2
