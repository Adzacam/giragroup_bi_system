"""
backend/tests_root/sprint4/test_alertas_tempranas_vista3.py
-----------------------------------------------------------
Pruebas unitarias e integración para la Vista 3:
Monitoreo de Reglas de Umbral y Alertas Tempranas (IF/THEN determinístico).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_docente import DimDocente
from models.dim_tiempo import DimTiempo
from models.dim_origen import DimOrigenDocumental
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from services.risk_service import (
    evaluar_alertas_tempranas_deterministicas,
    obtener_ficha_cruzada_estudiante,
)


def _crear_mock_db_constelacion():
    est1 = DimEstudiante(
        id_estudiante=101,
        nombre_completo="Vargas Alarcón Luis",
        ci="7391044 LP",
        ci_numero="7391044",
        codigo_estudiante="7391044",
        programa_origen="Maestría en BI",
        ciudad="La Paz",
        deprecado=False,
    )
    est2 = DimEstudiante(
        id_estudiante=102,
        nombre_completo="Mamani Flores Juan",
        ci="6849201 LP",
        ci_numero="6849201",
        codigo_estudiante="6849201",
        programa_origen="Maestría en BI",
        ciudad="La Paz",
        deprecado=False,
    )
    est3 = DimEstudiante(
        id_estudiante=103,
        nombre_completo="Soto Quiroga Ana",
        ci="5920183 SC",
        ci_numero="5920183",
        codigo_estudiante="5920183",
        programa_origen="Diplomado Finanzas",
        ciudad="Santa Cruz",
        deprecado=False,
    )
    est4 = DimEstudiante(
        id_estudiante=104,
        nombre_completo="Ríos Mendoza Pedro",
        ci="4829102 CB",
        ci_numero="4829102",
        codigo_estudiante="4829102",
        programa_origen="Maestría en BI",
        ciudad="Cochabamba",
        deprecado=False,
    )

    mod1 = DimModulo(
        id_modulo=1,
        nombre_modulo="MOD-02: Minería de Datos",
        programa="Maestría en BI",
        pos_code="POS-04",
    )
    mod2 = DimModulo(
        id_modulo=2,
        nombre_modulo="MOD-01: Gestión Tesorería",
        programa="Diplomado Finanzas",
        pos_code="DIP-12",
    )

    doc1 = DimDocente(id_docente=10, nombre_completo="Dr. Carlos Gómez")
    tiempo1 = DimTiempo(id_tiempo=202602, gestion=2026, semestre=2, mes=8, periodo_mes="2026-08")
    orig1 = DimOrigenDocumental(
        id_documento=50,
        nombre_archivo="acta_notas_bi.xlsx",
        periodo="2026-II",
        hash_sha256="a1b2c3d4e5f60123456789abcdef",
    )

    # Hechos académicos:
    # est1: nota 64 (<=70 -> A), incumplimiento 38.5% (>30% -> D)
    # est2: nota 68 (<=70 -> A), incumplimiento 35.0% (>30% -> D)
    # est3: nota 82 (OK), incumplimiento 10.0% (OK)
    # est4: nota 91 (OK), incumplimiento 5.0% (OK)
    aca_rows = [
        FactRendimientoAcademico(
            id_hecho_aca=1,
            id_estudiante=101,
            id_modulo=1,
            id_docente=10,
            id_tiempo=202602,
            id_documento=50,
            nota_final=64.0,
            asistencia_pct=61.5,
            incumplimiento_actividades_pct=38.5,
            estado_academico="Reprobado",
        ),
        FactRendimientoAcademico(
            id_hecho_aca=2,
            id_estudiante=102,
            id_modulo=1,
            id_docente=10,
            id_tiempo=202602,
            id_documento=50,
            nota_final=68.0,
            asistencia_pct=65.0,
            incumplimiento_actividades_pct=35.0,
            estado_academico="Reprobado",
        ),
        FactRendimientoAcademico(
            id_hecho_aca=3,
            id_estudiante=103,
            id_modulo=2,
            id_docente=10,
            id_tiempo=202602,
            id_documento=50,
            nota_final=82.0,
            asistencia_pct=90.0,
            incumplimiento_actividades_pct=10.0,
            estado_academico="Aprobado",
        ),
        FactRendimientoAcademico(
            id_hecho_aca=4,
            id_estudiante=104,
            id_modulo=1,
            id_docente=10,
            id_tiempo=202602,
            id_documento=50,
            nota_final=91.0,
            asistencia_pct=95.0,
            incumplimiento_actividades_pct=5.0,
            estado_academico="Aprobado",
        ),
    ]

    # Hechos financieros:
    # est1: 3 cuotas impagas (>=2 -> F) -> est1 tiene A+D+F (Triple Alerta)
    # est2: 0 cuotas impagas -> est2 tiene A+D
    # est3: 2 cuotas impagas (>=2 -> F) -> est3 tiene F
    fin_rows = [
        FactSituacionFinanciera(
            id_hecho_fin=10,
            id_estudiante=101,
            id_modulo=1,
            id_tiempo=202602,
            id_documento=50,
            concepto="Cuotas 2, 3 y 4",
            monto_pagado=1500.0,
            monto_deuda=4500.0,
            cuotas_impagas=3,
            estado_cartera="En Mora",
        ),
        FactSituacionFinanciera(
            id_hecho_fin=11,
            id_estudiante=103,
            id_modulo=2,
            id_tiempo=202602,
            id_documento=50,
            concepto="Cuotas 1 y 2",
            monto_pagado=800.0,
            monto_deuda=2400.0,
            cuotas_impagas=2,
            estado_cartera="En Mora",
        ),
    ]

    db = MagicMock()

    def query_side_effect(model):
        q = MagicMock()
        if model is DimEstudiante:
            q.filter.return_value.all.return_value = [est1, est2, est3, est4]
            q.filter.return_value.first.return_value = est1
        elif model is DimModulo:
            q.all.return_value = [mod1, mod2]
        elif model is DimDocente:
            q.all.return_value = [doc1]
        elif model is DimTiempo:
            q.all.return_value = [tiempo1]
        elif model is DimOrigenDocumental:
            q.all.return_value = [orig1]
        elif model is FactRendimientoAcademico:
            q.all.return_value = aca_rows
            q.filter.return_value.order_by.return_value.all.return_value = [aca_rows[0]]
        elif model is FactSituacionFinanciera:
            q.all.return_value = fin_rows
            q.filter.return_value.order_by.return_value.all.return_value = [fin_rows[0]]
        return q

    db.query.side_effect = query_side_effect
    return db


def test_evaluacion_deterministica_reglas_if_then():
    db = _crear_mock_db_constelacion()
    res = evaluar_alertas_tempranas_deterministicas(db=db)

    assert res["status"] == "success"
    assert res["motor_reglas"] == "DETERMINISTICO_IF_THEN_ESTRICTO"
    assert res["total_matricula_activa"] == 4

    tarjetas = res["tarjetas"]
    # est1 y est2 tienen promedio <= 70 -> 2 alumnos (50%)
    assert tarjetas["riesgo_academico"]["total_alumnos"] == 2
    assert tarjetas["riesgo_academico"]["porcentaje_matricula"] == 50.0
    # est1 y est2 tienen incumplimiento > 30% -> 2 alumnos
    assert tarjetas["riesgo_desercion"]["total_alumnos"] == 2
    # est1 y est3 tienen mora >= 2 cuotas -> 2 alumnos, deuda = 4500 + 2400 = 6900 Bs
    assert tarjetas["riesgo_financiero"]["total_alumnos"] == 2
    assert tarjetas["riesgo_financiero"]["monto_mora_bs"] == 6900.0
    # est1 (A+D+F) y est2 (A+D) tienen >= 2 reglas -> 2 alumnos en Alerta Crítica
    assert tarjetas["alerta_critica"]["total_alumnos"] == 2

    # Verificar tags nominales y ordenamiento por severidad
    estudiantes = res["estudiantes"]
    assert len(estudiantes) == 3  # est1, est2, est3 (est4 no dispara ninguna regla)
    assert estudiantes[0]["id_estudiante"] == 101
    assert estudiantes[0]["tag"] == "A+D+F"
    assert estudiantes[1]["id_estudiante"] == 102
    assert estudiantes[1]["tag"] == "A+D"
    assert estudiantes[2]["id_estudiante"] == 103
    assert estudiantes[2]["tag"] == "F"


def test_filtro_por_interseccion_y_programa():
    db = _crear_mock_db_constelacion()
    res_triple = evaluar_alertas_tempranas_deterministicas(db=db, regla_filtro="A+D+F")
    assert res_triple["total_estudiantes_filtrados"] == 1
    assert res_triple["estudiantes"][0]["nombre_completo"] == "Vargas Alarcón Luis"

    res_fin = evaluar_alertas_tempranas_deterministicas(db=db, regla_filtro="FINANCIERO")
    assert res_fin["total_estudiantes_filtrados"] == 2


def test_ficha_cruzada_estudiante():
    db = _crear_mock_db_constelacion()
    ficha = obtener_ficha_cruzada_estudiante(db=db, id_estudiante=101)
    assert ficha is not None
    assert ficha["id_estudiante"] == 101
    assert ficha["resumen_reglas"]["tag"] == "A+D+F"
    assert ficha["resumen_reglas"]["alerta_critica"] is True
    assert len(ficha["historial_academico"]) == 1
    assert ficha["historial_academico"][0]["hash_sha256"] == "a1b2c3d4e5f60123456789abcdef"
    assert len(ficha["historial_financiero"]) == 1
    assert ficha["historial_financiero"][0]["cuotas_impagas"] == 3
