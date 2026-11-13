"""
docs/testing/skeletons/test_kpis.py
----------------------------------
Esqueleto de pruebas unitarias para los 11 Indicadores Clave de Desempeño (KPIs) del CMI institucional.
Perspectivas del Cuadro de Mando Integral:
1. Aprendizaje y Crecimiento (Calidad Docente, Cobertura)
2. Procesos Internos (Eficacia Académica, Tasa Aprobación, Tasa Deserción)
3. Clientes / Estudiantes (Conversión de Admisión, Satisfacción, Retención)
4. Financiera (Ticket Promedio, Margen Contributivo, Cumplimiento Presupuestario)
Marcador: unit
"""

import pytest

@pytest.mark.unit
class TestCMI11KPIs:

    def test_kpi_1_tasa_aprobacion(self):
        """KPI 1: Aprobados / Total Evaluados (Nota >= 70)."""
        evaluados = [{"nota": 80}, {"nota": 70}, {"nota": 65}, {"nota": 90}]
        aprobados = [e for e in evaluados if e["nota"] >= 70]
        tasa = len(aprobados) / len(evaluados)
        assert tasa == 0.75

    def test_kpi_2_tasa_reprobacion(self):
        """KPI 2: Reprobados / Total Evaluados (Nota < 70)."""
        evaluados = [{"nota": 80}, {"nota": 70}, {"nota": 65}, {"nota": 50}]
        reprobados = [e for e in evaluados if e["nota"] < 70]
        tasa = len(reprobados) / len(evaluados)
        assert tasa == 0.50

    def test_kpi_3_tasa_desercion_academica(self):
        """KPI 3: Retirados / Inscritos Totales."""
        inscritos_totales = 100
        retirados = 12
        tasa = retirados / inscritos_totales
        assert tasa == 0.12

    def test_kpi_4_ticket_promedio(self):
        """KPI 4: Ingresos Cobrados / Cantidad de Transacciones."""
        ingresos = 150000.0
        transacciones = 150
        ticket = ingresos / transacciones
        assert ticket == 1000.0

    def test_kpi_5_ticket_promedio_division_cero(self):
        """KPI 4 defensa: Transacciones = 0 no genera ZeroDivisionError."""
        ingresos = 0.0
        transacciones = 0
        ticket = ingresos / transacciones if transacciones > 0 else 0.0
        assert ticket == 0.0

    def test_kpi_6_tasa_conversion_admision(self):
        """KPI 6: Matriculados / Leads Totales Contactados."""
        leads = 500
        matriculados = 75
        conversion = matriculados / leads
        assert conversion == 0.15

    def test_kpi_7_morosidad_cartera(self):
        """KPI 7: Monto en Mora / Cartera Total por Cobrar."""
        cartera_total = 200000.0
        monto_mora = 30000.0
        tasa_mora = monto_mora / cartera_total
        assert tasa_mora == 0.15

    def test_kpi_8_cumplimiento_presupuestario_rentabilidad(self):
        """KPI 8: Ejecutado / Meta Presupuestada."""
        meta = 500000.0
        ejecutado = 460000.0
        cumplimiento = (ejecutado / meta) * 100.0
        assert cumplimiento == 92.0

    def test_kpi_9_calidad_docente_promedio(self):
        """KPI 9: Sumatoria Evaluaciones Docentes / Total Evaluaciones (Escala 1 a 100)."""
        scores = [88.5, 92.0, 78.0, 95.5]
        promedio = sum(scores) / len(scores)
        assert round(promedio, 2) == 88.5

    def test_kpi_10_tasa_retencion_estudiantil(self):
        """KPI 10: Continuidad de estudiantes entre módulos consecutivos."""
        modulo_1 = 50
        modulo_2 = 45
        tasa_retencion = modulo_2 / modulo_1
        assert tasa_retencion == 0.90

    def test_kpi_11_eficiencia_operativa_dataops(self):
        """KPI 11: Registros Validados Directos / Registros Totales Procesados."""
        total_crudos = 1000
        inconsistencias_hitl = 50
        eficiencia = (total_crudos - inconsistencias_hitl) / total_crudos
        assert eficiencia == 0.95
