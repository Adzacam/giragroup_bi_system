"""
tests/test_risk_service.py
--------------------------
Pruebas unitarias exhaustivas para services/risk_service.py:
- Formateo de períodos y códigos cortos de programas
- Riesgo cruzado (académico + financiero)
- Reglas determinísticas estrictas IF/THEN (Académica, Deserción, Financiera, Crítica >= 2)
- Casos de frontera (70.0 vs 70.1, 30.0% vs 30.1%, 1 vs 2 cuotas en mora)
- Filtros (periodo, programa, modulo, docente, regla, búsqueda)
- Ficha cruzada del estudiante con trazabilidad documental (SHA-256)
"""

import sys
from pathlib import Path
from datetime import datetime
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.database import Base
from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_docente import DimDocente
from models.dim_tiempo import DimTiempo
from models.dim_origen import DimOrigenDocumental
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera

from services.risk_service import (
    _formatear_periodo,
    _codigo_corto_programa,
    get_riesgo_cruzado,
    evaluar_alertas_tempranas_deterministicas,
    obtener_ficha_cruzada_estudiante,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def do_connect(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("ATTACH DATABASE ':memory:' AS public")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_formatear_periodo():
    # Caso 1: con doc_periodo
    assert _formatear_periodo(None, doc_periodo="2025-I") == "2025-I"
    assert _formatear_periodo(None, doc_periodo=" 2026-II ") == "2026-II"

    # Caso 2: sin tiempo ni doc_periodo
    assert _formatear_periodo(None, None) == "Multi-Semestre"

    # Caso 3: con tiempo y semestre explícito
    t1 = DimTiempo(id_tiempo=1, gestion=2026, semestre=2)
    assert _formatear_periodo(t1) == "2026-II"

    # Caso 4: con tiempo y mes <= 6
    t2 = DimTiempo(id_tiempo=2, gestion=2025, mes=4)
    assert _formatear_periodo(t2) == "2025-I"

    # Caso 5: con tiempo y mes > 6
    t3 = DimTiempo(id_tiempo=3, gestion=2025, mes=9)
    assert _formatear_periodo(t3) == "2025-II"


def test_codigo_corto_programa():
    # Con pos_code explícito
    assert _codigo_corto_programa("Cualquier Programa", pos_code="POS-99") == "POS-99"
    # Con pos_code MOD-GEN (debe descartarse)
    assert _codigo_corto_programa("Maestría en Data Science", pos_code="MOD-GEN", idx=1) == "MSC-101"
    # Diplomado
    assert _codigo_corto_programa("Diplomado en Finanzas", idx=2) == "DIP-202"
    # Especialidad / Experto
    assert _codigo_corto_programa("Experto en Ciberseguridad", idx=3) == "EXP-303"
    # Dos palabras
    assert _codigo_corto_programa("Auditoría Forense", idx=1) == "AUD-FOR"
    # Una palabra
    assert _codigo_corto_programa("Marketing", idx=4) == "MARK-04"
    # Vacío
    assert _codigo_corto_programa("", idx=5) == "PRG-05"


def test_get_riesgo_cruzado(db_session):
    e1 = DimEstudiante(id_estudiante=1, nombre_completo="Juan Perez", codigo_estudiante="EST-001", ci="1234567")
    e2 = DimEstudiante(id_estudiante=2, nombre_completo="Maria Gomez", codigo_estudiante="EST-002", ci="7654321")
    db_session.add_all([e1, e2])

    # e1 cumple ambas condiciones (nota <= 70 y cuotas >= 2)
    fa1 = FactRendimientoAcademico(id_hecho_aca=1, id_estudiante=1, nota_final=65.0)
    ff1 = FactSituacionFinanciera(id_hecho_fin=1, id_estudiante=1, cuotas_impagas=3, monto_deuda=1500.0, estado_cartera="En Mora")

    # e2 nota alta (85.0), no debe entrar en riesgo cruzado
    fa2 = FactRendimientoAcademico(id_hecho_aca=2, id_estudiante=2, nota_final=85.0)
    ff2 = FactSituacionFinanciera(id_hecho_fin=2, id_estudiante=2, cuotas_impagas=2, monto_deuda=1000.0, estado_cartera="En Mora")

    db_session.add_all([fa1, ff1, fa2, ff2])
    db_session.commit()

    alertas = get_riesgo_cruzado(db_session, limite_nota=70.0, min_cuotas_mora=2)
    assert len(alertas) == 1
    assert alertas[0]["estudiante"] == "Juan Perez"
    assert alertas[0]["codigo"] == "EST-001"
    assert alertas[0]["rendimiento"]["nota_actual"] == 65.0
    assert alertas[0]["finanzas"]["cuotas_mora"] == 3


def test_evaluar_alertas_deterministicas_y_fronteras(db_session):
    # Setup de dimensiones
    t1 = DimTiempo(id_tiempo=1, gestion=2026, semestre=1, periodo_mes="2026-01")
    doc1 = DimDocente(id_docente=1, nombre_completo="Dr. Carlos Mendoza")
    mod1 = DimModulo(id_modulo=1, nombre_modulo="Machine Learning I", programa="Maestría en Data Science", pos_code="MDS-01")
    orig1 = DimOrigenDocumental(id_documento=1, nombre_archivo="notas.xlsx", hash_sha256="abc123hash", periodo="2026-I")

    # Estudiante A: Riesgo Académico puro (nota = 70.0 frontera exacta)
    ea = DimEstudiante(id_estudiante=10, nombre_completo="Alumno Academico", ci="111", codigo_estudiante="A001")
    fa_a = FactRendimientoAcademico(
        id_hecho_aca=10, id_estudiante=10, id_modulo=1, id_docente=1, id_tiempo=1, id_documento=1,
        nota_final=70.0, incumplimiento_actividades_pct=10.0, asistencia_pct=95.0
    )
    ff_a = FactSituacionFinanciera(
        id_hecho_fin=10, id_estudiante=10, id_modulo=1, id_tiempo=1, id_documento=1,
        cuotas_impagas=1, monto_deuda=200.0, estado_cartera="Vigente"
    )

    # Estudiante B: Fuera de riesgo académico por frontera (nota = 70.1)
    eb = DimEstudiante(id_estudiante=11, nombre_completo="Alumno Fuera Frontera", ci="222", codigo_estudiante="A002")
    fa_b = FactRendimientoAcademico(
        id_hecho_aca=11, id_estudiante=11, id_modulo=1, id_docente=1, id_tiempo=1, id_documento=1,
        nota_final=70.1, incumplimiento_actividades_pct=30.0, asistencia_pct=70.0
    )
    ff_b = FactSituacionFinanciera(
        id_hecho_fin=11, id_estudiante=11, id_modulo=1, id_tiempo=1, id_documento=1,
        cuotas_impagas=1, monto_deuda=100.0, estado_cartera="Vigente"
    )

    # Estudiante D: Riesgo Deserción (incumplimiento = 30.1 frontera)
    ed = DimEstudiante(id_estudiante=12, nombre_completo="Alumno Desercion", ci="333", codigo_estudiante="A003")
    fa_d = FactRendimientoAcademico(
        id_hecho_aca=12, id_estudiante=12, id_modulo=1, id_docente=1, id_tiempo=1, id_documento=1,
        nota_final=80.0, incumplimiento_actividades_pct=30.1, asistencia_pct=85.0
    )
    ff_d = FactSituacionFinanciera(
        id_hecho_fin=12, id_estudiante=12, id_modulo=1, id_tiempo=1, id_documento=1,
        cuotas_impagas=0, monto_deuda=0.0
    )

    # Estudiante F: Riesgo Financiero (cuotas_mora = 2 frontera)
    ef = DimEstudiante(id_estudiante=13, nombre_completo="Alumno Financiero", ci="444", codigo_estudiante="A004")
    fa_f = FactRendimientoAcademico(
        id_hecho_aca=13, id_estudiante=13, id_modulo=1, id_docente=1, id_tiempo=1, id_documento=1,
        nota_final=88.0, incumplimiento_actividades_pct=5.0
    )
    ff_f = FactSituacionFinanciera(
        id_hecho_fin=13, id_estudiante=13, id_modulo=1, id_tiempo=1, id_documento=1,
        cuotas_impagas=2, monto_deuda=1200.0, estado_cartera="En Mora"
    )

    # Estudiante ADF: Triple Alerta Crítica (A+D+F)
    eadf = DimEstudiante(id_estudiante=14, nombre_completo="Alumno Critico ADF", ci="555", codigo_estudiante="A005")
    fa_adf = FactRendimientoAcademico(
        id_hecho_aca=14, id_estudiante=14, id_modulo=1, id_docente=1, id_tiempo=1, id_documento=1,
        nota_final=50.0, incumplimiento_actividades_pct=45.0, tipo_alerta="DESERCION"
    )
    ff_adf = FactSituacionFinanciera(
        id_hecho_fin=14, id_estudiante=14, id_modulo=1, id_tiempo=1, id_documento=1,
        cuotas_impagas=4, monto_deuda=3500.0, estado_cartera="En Mora"
    )

    # Estudiante AD: Académico + Deserción (A+D)
    ead = DimEstudiante(id_estudiante=15, nombre_completo="Alumno Critico AD", ci="666", codigo_estudiante="A006")
    fa_ad = FactRendimientoAcademico(
        id_hecho_aca=15, id_estudiante=15, id_modulo=1, id_docente=1, id_tiempo=1, id_documento=1,
        nota_final=55.0, incumplimiento_actividades_pct=40.0
    )

    # Estudiante DF: Deserción + Financiero (D+F)
    edf = DimEstudiante(id_estudiante=16, nombre_completo="Alumno Critico DF", ci="777", codigo_estudiante="A007")
    fa_df = FactRendimientoAcademico(
        id_hecho_aca=16, id_estudiante=16, id_modulo=1, id_docente=1, id_tiempo=1, id_documento=1,
        nota_final=85.0, asistencia_pct=50.0 # asistencia 50% -> inasistencia 50% > 30%
    )
    ff_df = FactSituacionFinanciera(
        id_hecho_fin=16, id_estudiante=16, id_modulo=1, id_tiempo=1, id_documento=1,
        cuotas_impagas=3, monto_deuda=1800.0
    )

    # Estudiante AF: Académico + Financiero (A+F)
    eaf = DimEstudiante(id_estudiante=17, nombre_completo="Alumno Critico AF", ci="888", codigo_estudiante="A008")
    fa_af = FactRendimientoAcademico(
        id_hecho_aca=17, id_estudiante=17, id_modulo=1, id_docente=1, id_tiempo=1, id_documento=1,
        nota_final=60.0
    )
    ff_af = FactSituacionFinanciera(
        id_hecho_fin=17, id_estudiante=17, id_modulo=1, id_tiempo=1, id_documento=1,
        cuotas_impagas=2, monto_deuda=900.0
    )

    db_session.add_all([t1, doc1, mod1, orig1])
    db_session.add_all([ea, eb, ed, ef, eadf, ead, edf, eaf])
    db_session.add_all([fa_a, ff_a, fa_b, ff_b, fa_d, ff_d, fa_f, ff_f, fa_adf, ff_adf, fa_ad, fa_df, ff_df, fa_af, ff_af])
    db_session.commit()

    # Evaluación general sin filtros
    res = evaluar_alertas_tempranas_deterministicas(db_session)
    assert res["status"] == "success"
    assert res["motor_reglas"] == "DETERMINISTICO_IF_THEN_ESTRICTO"
    tarjetas = res["tarjetas"]

    # Verificar conteos de tarjetas
    # Alumnos con riesgo académico: ea (70.0), eadf (50.0), ead (55.0), eaf (60.0) -> total 4
    # eb (70.1) NO entra en académico
    assert tarjetas["riesgo_academico"]["total_alumnos"] == 4

    # Alumnos con riesgo deserción: ed (30.1%), eadf (45%), ead (40%), edf (50% por inasistencia) -> total 4
    # eb (30.0%) NO entra en deserción (> 30.0)
    assert tarjetas["riesgo_desercion"]["total_alumnos"] == 4

    # Alumnos con riesgo financiero: ef (2), eadf (4), edf (3), eaf (2) -> total 4
    # ea (1), eb (1) NO entran en financiero (>= 2)
    assert tarjetas["riesgo_financiero"]["total_alumnos"] == 4

    # Crítica (>= 2 reglas): eadf (3 reglas), ead (2 reglas), edf (2 reglas), eaf (2 reglas) -> total 4
    assert tarjetas["alerta_critica"]["total_alumnos"] == 4

    # Verificar filtros por regla
    res_aca = evaluar_alertas_tempranas_deterministicas(db_session, regla_filtro="ACADEMICO")
    assert all(e["regla_academico"] for e in res_aca["estudiantes"])

    res_des = evaluar_alertas_tempranas_deterministicas(db_session, regla_filtro="DESERCION")
    assert all(e["regla_desercion"] for e in res_des["estudiantes"])

    res_fin = evaluar_alertas_tempranas_deterministicas(db_session, regla_filtro="FINANCIERO")
    assert all(e["regla_financiero"] for e in res_fin["estudiantes"])

    res_crit = evaluar_alertas_tempranas_deterministicas(db_session, regla_filtro="CRITICA")
    assert all(e["cantidad_reglas"] >= 2 for e in res_crit["estudiantes"])

    res_ad = evaluar_alertas_tempranas_deterministicas(db_session, regla_filtro="A+D")
    assert all(e["regla_academico"] and e["regla_desercion"] for e in res_ad["estudiantes"])

    res_df = evaluar_alertas_tempranas_deterministicas(db_session, regla_filtro="D+F")
    assert all(e["regla_desercion"] and e["regla_financiero"] for e in res_df["estudiantes"])

    res_af = evaluar_alertas_tempranas_deterministicas(db_session, regla_filtro="A+F")
    assert all(e["regla_academico"] and e["regla_financiero"] for e in res_af["estudiantes"])

    res_adf = evaluar_alertas_tempranas_deterministicas(db_session, regla_filtro="A+D+F")
    assert len(res_adf["estudiantes"]) == 1
    assert res_adf["estudiantes"][0]["id_estudiante"] == 14

    # Filtros por atributos de búsqueda y programa
    res_busq = evaluar_alertas_tempranas_deterministicas(db_session, busqueda="Critico")
    assert len(res_busq["estudiantes"]) > 0

    res_prog = evaluar_alertas_tempranas_deterministicas(db_session, programa="Maestría en Data Science")
    assert len(res_prog["estudiantes"]) > 0

    res_mod = evaluar_alertas_tempranas_deterministicas(db_session, modulo="Machine Learning I")
    assert len(res_mod["estudiantes"]) > 0

    res_doc = evaluar_alertas_tempranas_deterministicas(db_session, docente="Dr. Carlos Mendoza")
    assert len(res_doc["estudiantes"]) > 0

    res_per = evaluar_alertas_tempranas_deterministicas(db_session, periodo="2026-I")
    assert len(res_per["estudiantes"]) > 0


def test_obtener_ficha_cruzada_estudiante(db_session):
    # Caso 1: Estudiante no encontrado
    assert obtener_ficha_cruzada_estudiante(db_session, 999) is None

    # Caso 2: Estudiante con historial y hash documental
    t = DimTiempo(id_tiempo=1, gestion=2026, semestre=1)
    doc = DimDocente(id_docente=1, nombre_completo="Ing. Juan Docente")
    mod = DimModulo(id_modulo=1, nombre_modulo="Módulo Base", programa="Diplomado en Gestión")
    orig = DimOrigenDocumental(id_documento=1, nombre_archivo="acta_2026.xlsx", hash_sha256="hash_valido_sha256")
    est = DimEstudiante(id_estudiante=20, nombre_completo="Sofia Lopez", ci="998877", codigo_estudiante="SL-01")

    fa = FactRendimientoAcademico(
        id_hecho_aca=100, id_estudiante=20, id_modulo=1, id_docente=1, id_tiempo=1, id_documento=1,
        nota_final=68.0, incumplimiento_actividades_pct=35.0, asistencia_pct=80.0
    )
    ff = FactSituacionFinanciera(
        id_hecho_fin=100, id_estudiante=20, id_modulo=1, id_tiempo=1, id_documento=1,
        monto_pagado=500.0, monto_deuda=1500.0, cuotas_impagas=2, concepto="Colegiatura Módulo 1"
    )

    db_session.add_all([t, doc, mod, orig, est, fa, ff])
    db_session.commit()

    ficha = obtener_ficha_cruzada_estudiante(db_session, 20)
    assert ficha is not None
    assert ficha["status"] == "success"
    assert ficha["nombre_completo"] == "Sofia Lopez"
    assert ficha["ci"] == "998877"
    assert ficha["resumen_reglas"]["promedio_notas"] == 68.0
    assert ficha["resumen_reglas"]["incumplimiento_max_pct"] == 35.0
    assert ficha["resumen_reglas"]["cuotas_mora_total"] == 2
    assert ficha["resumen_reglas"]["alerta_critica"] is True
    assert "A" in ficha["resumen_reglas"]["tag"]
    assert "D" in ficha["resumen_reglas"]["tag"]
    assert "F" in ficha["resumen_reglas"]["tag"]

    # Validar trazabilidad SHA-256 en ambos hechos
    assert ficha["historial_academico"][0]["hash_sha256"] == "hash_valido_sha256"
    assert ficha["historial_academico"][0]["origen_archivo"] == "acta_2026.xlsx"
    assert ficha["historial_financiero"][0]["hash_sha256"] == "hash_valido_sha256"
    assert ficha["historial_financiero"][0]["origen_archivo"] == "acta_2026.xlsx"
