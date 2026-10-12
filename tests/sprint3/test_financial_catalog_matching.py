"""
tests/sprint3/test_financial_catalog_matching.py
------------------------------------------------
Suite de pruebas unitarias para el Loop 1 del pipeline financiero:
1. Validación DDL de 'cat_concepto_financiero' y 'cat_historico_equivalencia'.
2. Homologación exacta contra conceptos canónicos (CUOTA, MATRICULA, CONTADO).
3. Homologación mediante equivalencias históricas ('Mensualidad' -> CUOTA, 'Inscripción' -> MATRICULA).
4. Homologación difusa de alta confianza (>= 90%).
5. Política estricta anti-contaminación (términos no homologados van a revisión humana y no se crean en DW).
6. Listado y filtrado de conceptos por tipo de movimiento.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.catalogos import CatalogBase, CatConceptoFinanciero, CatHistoricoEquivalencia
from services.financial_catalog_service import FinancialCatalogService


RUTA_SCHEMA = os.path.join("db", "schema_catalogos.sql")


@pytest.fixture(scope="module")
def sqlite_catalog_db():
    """Crea una base de datos SQLite en memoria para pruebas rápidas y aisladas."""
    engine = create_engine("sqlite:///:memory:")
    CatalogBase.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    # Sembrar conceptos canónicos
    c_cuota = CatConceptoFinanciero(
        codigo_canonico="FIN-CUOTA-01",
        nombre_canonico="CUOTA",
        tipo_movimiento="INGRESO",
        categoria_contable="COBRANZA",
        descripcion="Cuota periódica mensual"
    )
    c_mat = CatConceptoFinanciero(
        codigo_canonico="FIN-MAT-01",
        nombre_canonico="MATRICULA",
        tipo_movimiento="INGRESO",
        categoria_contable="COBRANZA",
        descripcion="Derecho de matrícula o inscripción inicial"
    )
    c_contado = CatConceptoFinanciero(
        codigo_canonico="FIN-CONTADO-01",
        nombre_canonico="CONTADO",
        tipo_movimiento="INGRESO",
        categoria_contable="COBRANZA",
        descripcion="Pago total al contado"
    )
    c_mora = CatConceptoFinanciero(
        codigo_canonico="FIN-MORA-01",
        nombre_canonico="MORA",
        tipo_movimiento="AJUSTE",
        categoria_contable="COBRANZA",
        descripcion="Recargo por mora"
    )
    c_doc = CatConceptoFinanciero(
        codigo_canonico="FIN-HON-DOC-01",
        nombre_canonico="HONORARIO_DOCENTE",
        tipo_movimiento="EGRESO",
        categoria_contable="DOCENTE",
        descripcion="Remuneración a docentes"
    )
    c_techo = CatConceptoFinanciero(
        codigo_canonico="FIN-TECHO-01",
        nombre_canonico="TECHO_CONVENIO",
        tipo_movimiento="INGRESO",
        categoria_contable="CONVENIO",
        descripcion="Facturación por convenios cerrados"
    )

    session.add_all([c_cuota, c_mat, c_contado, c_mora, c_doc, c_techo])
    session.flush()

    # Sembrar equivalencias históricas
    eqs = [
        CatHistoricoEquivalencia(
            id_concepto=c_cuota.id_concepto,
            termino_origen="Mensualidad",
            periodo_historico="2024-2025",
            confianza_mapeo=0.9800,
            fuente_referencia="BD Cobranzas.xlsx"
        ),
        CatHistoricoEquivalencia(
            id_concepto=c_cuota.id_concepto,
            termino_origen="Colegiatura",
            periodo_historico="HISTORICO",
            confianza_mapeo=0.9500,
            fuente_referencia="BD Cobranzas.xlsx"
        ),
        CatHistoricoEquivalencia(
            id_concepto=c_mat.id_concepto,
            termino_origen="Inscripción",
            periodo_historico="2024-2025",
            confianza_mapeo=0.9800,
            fuente_referencia="BD Cobranzas.xlsx"
        ),
        CatHistoricoEquivalencia(
            id_concepto=c_doc.id_concepto,
            termino_origen="Honorarios Docente",
            periodo_historico="2024-2025",
            confianza_mapeo=0.9900,
            fuente_referencia="BD Egresos.xlsx"
        ),
        CatHistoricoEquivalencia(
            id_concepto=c_techo.id_concepto,
            termino_origen="Techo Cerrado",
            periodo_historico="2024-2025",
            confianza_mapeo=0.9900,
            fuente_referencia="BD Techos.xlsx"
        )
    ]
    session.add_all(eqs)
    session.commit()

    yield session
    session.close()


class TestSchemaCatalogosFinancialDDL:
    """Valida la presencia del DDL de conceptos y equivalencias en schema_catalogos.sql."""

    def test_ddl_cat_concepto_financiero_definido(self):
        with open(RUTA_SCHEMA, "r", encoding="utf-8") as f:
            contenido = f.read()

        assert "CREATE TABLE IF NOT EXISTS public.cat_concepto_financiero" in contenido
        assert "codigo_canonico" in contenido
        assert "nombre_canonico" in contenido
        assert "tipo_movimiento" in contenido
        assert "categoria_contable" in contenido

    def test_ddl_cat_historico_equivalencia_definido(self):
        with open(RUTA_SCHEMA, "r", encoding="utf-8") as f:
            contenido = f.read()

        assert "CREATE TABLE IF NOT EXISTS public.cat_historico_equivalencia" in contenido
        assert "id_concepto" in contenido
        assert "termino_origen" in contenido
        assert "confianza_mapeo" in contenido
        assert "fuente_referencia" in contenido


class TestFinancialCatalogHomologation:
    """Valida la lógica de homologación, soporte histórico y política anti-contaminación."""

    def test_exact_canonical_match(self, sqlite_catalog_db):
        res = FinancialCatalogService.homologar_concepto("CUOTA", db_catalog=sqlite_catalog_db)
        assert res["homologado"] is True
        assert res["codigo_canonico"] == "FIN-CUOTA-01"
        assert res["nombre_canonico"] == "CUOTA"
        assert res["confianza"] == 100.0
        assert res["requiere_revision"] is False

    def test_exact_code_match(self, sqlite_catalog_db):
        res = FinancialCatalogService.homologar_concepto("FIN-MAT-01", db_catalog=sqlite_catalog_db)
        assert res["homologado"] is True
        assert res["codigo_canonico"] == "FIN-MAT-01"
        assert res["nombre_canonico"] == "MATRICULA"
        assert res["confianza"] == 100.0

    def test_historic_equivalence_mensualidad_to_cuota(self, sqlite_catalog_db):
        res = FinancialCatalogService.homologar_concepto("Mensualidad", db_catalog=sqlite_catalog_db)
        assert res["homologado"] is True
        assert res["codigo_canonico"] == "FIN-CUOTA-01"
        assert res["nombre_canonico"] == "CUOTA"
        assert res["es_equivalencia_historica"] is True
        assert res["confianza"] >= 95.0
        assert res["requiere_revision"] is False

    def test_historic_equivalence_inscripcion_to_matricula(self, sqlite_catalog_db):
        res = FinancialCatalogService.homologar_concepto("Inscripción", db_catalog=sqlite_catalog_db)
        assert res["homologado"] is True
        assert res["codigo_canonico"] == "FIN-MAT-01"
        assert res["nombre_canonico"] == "MATRICULA"
        assert res["es_equivalencia_historica"] is True
        assert res["requiere_revision"] is False

    def test_historic_equivalence_honorarios_docente(self, sqlite_catalog_db):
        res = FinancialCatalogService.homologar_concepto("Honorarios Docente", db_catalog=sqlite_catalog_db)
        assert res["homologado"] is True
        assert res["codigo_canonico"] == "FIN-HON-DOC-01"
        assert res["tipo_movimiento"] == "EGRESO"
        assert res["requiere_revision"] is False

    def test_fuzzy_high_confidence(self, sqlite_catalog_db):
        # Ligera variación o minúsculas con tildes
        res = FinancialCatalogService.homologar_concepto("mensualidad", db_catalog=sqlite_catalog_db)
        assert res["homologado"] is True
        assert res["codigo_canonico"] == "FIN-CUOTA-01"
        assert res["confianza"] >= 90.0

    def test_anti_pollution_unknown_concept_requires_review(self, sqlite_catalog_db):
        """Si un concepto no existe y no supera el 90%, NO se inventa en el catálogo ni en DW."""
        res = FinancialCatalogService.homologar_concepto(
            "Cobro extraordinario convenio X",
            db_catalog=sqlite_catalog_db,
            umbral_confianza=90.0
        )
        assert res["homologado"] is False
        assert res["codigo_canonico"] is None
        assert res["nombre_canonico"] is None
        assert res["requiere_revision"] is True
        assert "inferior al umbral de seguridad" in res["motivo"]

        # Verificar que NO se haya insertado un nuevo registro en la base de datos
        total_conceptos = sqlite_catalog_db.query(CatConceptoFinanciero).count()
        assert total_conceptos == 6

    def test_anti_pollution_aporte_extra(self, sqlite_catalog_db):
        res = FinancialCatalogService.homologar_concepto(
            "Aporte extraordinario no catalogado",
            db_catalog=sqlite_catalog_db,
            umbral_confianza=90.0
        )
        assert res["homologado"] is False
        assert res["requiere_revision"] is True

    def test_listar_conceptos_con_filtro(self, sqlite_catalog_db):
        ingresos = FinancialCatalogService.listar_conceptos(sqlite_catalog_db, tipo_movimiento="INGRESO")
        assert len(ingresos) >= 3
        for c in ingresos:
            assert c["tipo_movimiento"] == "INGRESO"

        todos = FinancialCatalogService.listar_conceptos(sqlite_catalog_db)
        assert len(todos) == 6
