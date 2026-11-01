"""
tests/test_agnostic_classifier_and_dw_reset.py
===============================================
Suite de Verificación Integral:
1. Clasificador semántico agnóstico de contenido (cero datos quemados de nombres/hojas).
2. Extracción de tuplas relacionales (BETO NER & Relational Extraction).
3. Reset seguro y respetuoso de invariantes dimensionales del Data Warehouse.
4. Compatibilidad de nuevas fuentes documentales en dim_origen_documental.
"""

import os
import sys
import pytest
import pandas as pd

# Asegurar path de imports
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pipeline.ingesta import (
    clasificar_contenido_agnostico,
    clasificar_categoria,
    clasificar_bloque,
)
from backend.services.ingestion_service import (
    normalizar_codigo_tipo_fuente,
    detectar_tipo_fuente_por_cabeceras,
)
from scripts.finetune_beto_ner import (
    RelationalExtractor,
    extraer_tuplas_relacionales,
    LABEL_LIST,
)
from scripts.reset_dw import (
    TABLAS_TRUNCAR,
    TABLAS_PRESERVAR,
    reset_data_warehouse,
)


class TestAgnosticClassifier:
    """Verifica la detección agnóstica sin depender de nombres de archivo u hojas fijas."""

    def test_clasificacion_academica_agnostica(self):
        """Archivo y hoja con nombres arbitrarios pero contenido académico."""
        df_academico = pd.DataFrame({
            "CI": ["10234567", "10234568", "10234569"],
            "Estudiante": ["Juan Perez", "Maria Lopez", "Carlos Gomez"],
            "Modulo": ["Módulo 1 Arquitectura", "Módulo 1 Arquitectura", "Módulo 1 Arquitectura"],
            "Calificacion Final": [85, 92, 45],
            "Asistencia": ["90%", "95%", "60%"]
        })

        res = clasificar_contenido_agnostico(df_academico)
        assert res["categoria"] == "academico"
        assert res["fact_table"] == "fact_rendimiento_academico"
        assert res["confidence"] >= 0.70

        # Probar a través de clasificar_categoria con nombres completamente arbitrarios
        cat = clasificar_categoria(df_academico, nombre_archivo="unseen_xyz_999.xlsx", nombre_hoja="Hoja_Aleatoria")
        assert cat == "academico"

    def test_clasificacion_financiera_agnostica(self):
        """Archivo con saldo, mora y cuota sin nombre reconocible."""
        df_financiero = pd.DataFrame({
            "Cedula": ["7829102", "8912301", "6712399"],
            "Titular": ["Laura Ramos", "Pedro Suarez", "Carmen Rios"],
            "Monto Deuda": [1200.50, 450.00, 0.00],
            "Cuotas Impagas": [2, 1, 0],
            "Fecha Vencimiento": ["2025-04-10", "2025-04-10", "2025-03-10"]
        })

        res = clasificar_contenido_agnostico(df_financiero)
        assert res["categoria"] == "financiero"
        assert res["fact_table"] == "fact_situacion_financiera"
        assert res["confidence"] >= 0.70

        cat = clasificar_categoria(df_financiero, nombre_archivo="archivo_desconocido.csv", nombre_hoja="Datos_001")
        assert cat == "financiero"

    def test_clasificacion_evaluacion_docente_agnostica(self):
        """Encuesta docente con escala de rating 1-5."""
        df_evaluacion = pd.DataFrame({
            "Docente": ["Ing. Alejandro Siles", "Ing. Alejandro Siles", "Dra. Sofia Alarcon"],
            "Modulo": ["Inteligencia de Negocios", "Inteligencia de Negocios", "Data Warehouse"],
            "Pregunta 1 Dominio del tema": [5, 4, 5],
            "Pregunta 2 Didactica y pedagogia": [4, 5, 4],
            "Pregunta 3 Cumplimiento cronograma": [5, 5, 5],
            "Satisfaccion General": [5, 4, 5],
            "Comentario": ["Excelente docente", "Muy buen contenido", "Clases dinamicas"]
        })

        res = clasificar_contenido_agnostico(df_evaluacion)
        assert res["categoria"] == "evaluacion_docente"
        assert res["fact_table"] == "fact_evaluacion_docente"
        assert res["confidence"] >= 0.70

        cat = clasificar_categoria(df_evaluacion, nombre_archivo="encuesta_random_2026.xlsx", nombre_hoja="Sheet1")
        assert cat == "evaluacion_docente"

    def test_clasificacion_rentabilidad_agnostica(self):
        """Costos, egresos y techos presupuestarios sin alumnos individuales."""
        df_rentabilidad = pd.DataFrame({
            "Categoria Financiera": ["Docencia", "Licencias Cloud", "Marketing y Pauta", "Operaciones"],
            "Presupuesto Asignado (Techo)": [15000.0, 8000.0, 12000.0, 5000.0],
            "Monto Ejecutado (Egresos)": [14200.0, 7850.0, 11900.0, 4800.0],
            "Desviacion": [-800.0, -150.0, -100.0, -200.0],
            "EBITDA Proyectado": [25000.0, 25000.0, 25000.0, 25000.0]
        })

        res = clasificar_contenido_agnostico(df_rentabilidad)
        assert res["categoria"] == "rentabilidad"
        assert res["fact_table"] == "fact_rentabilidad"
        assert res["confidence"] >= 0.70

        cat = clasificar_categoria(df_rentabilidad, nombre_archivo="reporte_financiero_interno.xlsx", nombre_hoja="Finanzas")
        assert cat == "rentabilidad"

    def test_clasificacion_marketing_agnostica(self):
        """Leads, campañas y admisiones de marketing."""
        df_mkt = pd.DataFrame({
            "Campana": ["Meta Ads Posgrado 2026", "Google Search Data Science", "Webinar Analytics"],
            "Medio de Contacto": ["Facebook", "Google", "LinkedIn"],
            "Leads Obtenidos": [250, 180, 95],
            "Preinscritos": [45, 38, 22],
            "Matriculas Confirmadas": [18, 14, 9],
            "Costo Programa": [1800.0, 1800.0, 1800.0]
        })

        res = clasificar_contenido_agnostico(df_mkt)
        assert res["categoria"] == "marketing"
        assert res["fact_table"] == "fact_marketing"
        assert res["confidence"] >= 0.70

        cat = clasificar_categoria(df_mkt, nombre_archivo="leads_conversion_q1.xlsx", nombre_hoja="Resultados")
        assert cat == "marketing"

    def test_egresos_servicio_no_confundidos_con_estudiante(self):
        """'servicio' contiene 'ci' pero debe clasificarse como egresos/rentabilidad, jamás como cobranza/estudiante."""
        df_servicios = pd.DataFrame({
            "Concepto del Servicio": ["Mantenimiento Servidores Cloud", "Soporte Licencias"],
            "Partida": ["Infraestructura TI", "Software"],
            "Cuota": [1, 2],
            "Monto": [4500.0, 3200.0]
        })
        res = clasificar_contenido_agnostico(df_servicios)
        assert res["categoria"] == "rentabilidad"
        assert res["fact_table"] == "fact_rentabilidad"

    def test_empleados_no_confundidos_con_marketing_lead(self):
        """'empleados' contiene la subcadena 'lead' pero no debe clasificarse como marketing."""
        df_empleados = pd.DataFrame({
            "Empleados": ["Juan Carlos Mamani", "Patricia Alarcon"],
            "Sueldo": [6000.0, 7500.0],
            "Fecha": ["2025-01-15", "2025-01-15"]
        })
        res = clasificar_contenido_agnostico(df_empleados)
        assert res["categoria"] != "marketing"

    def test_acta_con_docente_y_semestre_conserva_academico(self):
        """Un acta con nombre de docente y semestres 1-5 no debe confundirse con evaluación docente."""
        df_acta = pd.DataFrame({
            "CI": ["10234567", "10234568", "10234569"],
            "Estudiante": ["Juan Perez", "Maria Lopez", "Carlos Gomez"],
            "Docente": ["Ing. Alejandro Perez", "Ing. Alejandro Perez", "Ing. Alejandro Perez"],
            "Modulo": ["Sistemas Distribuidos", "Sistemas Distribuidos", "Sistemas Distribuidos"],
            "Nota Final": [85.0, 92.0, 70.0],
            "Semestre": [1, 2, 3]
        })
        res = clasificar_contenido_agnostico(df_acta)
        assert res["categoria"] == "academico"
        assert res["fact_table"] == "fact_rendimiento_academico"

    def test_acta_con_matricula_conserva_academico(self):
        """Módulo + Nota Final con columna Matrícula debe ser académico, no comercial/marketing."""
        df_notas = pd.DataFrame({
            "Modulo": ["Algoritmos Avanzados"],
            "Nota Final": [88.5],
            "Matricula": ["2025-1"]
        })
        res = clasificar_contenido_agnostico(df_notas)
        assert res["categoria"] == "academico"
        assert res["fact_table"] == "fact_rendimiento_academico"


class TestIngestionServiceSourceDetection:
    """Verifica normalizar_codigo_tipo_fuente y detectar_tipo_fuente_por_cabeceras."""

    def test_normalizar_codigos_nuevos(self):
        assert normalizar_codigo_tipo_fuente("EVALUACION_DOCENTE") == "EVALUACION_DOCENTE"
        assert normalizar_codigo_tipo_fuente("Evaluacion Docente y NPS") == "EVALUACION_DOCENTE"
        assert normalizar_codigo_tipo_fuente("EGRESOS") == "EGRESOS"
        assert normalizar_codigo_tipo_fuente("Planilla de Egresos y Gastos") == "EGRESOS"
        assert normalizar_codigo_tipo_fuente("TECHOS") == "TECHOS"
        assert normalizar_codigo_tipo_fuente("Techos Presupuestarios") == "TECHOS"
        assert normalizar_codigo_tipo_fuente("RENTABILIDAD") == "RENTABILIDAD"
        assert normalizar_codigo_tipo_fuente("MARKETING") == "MARKETING"
        assert normalizar_codigo_tipo_fuente("Campaña Marketing Leads") == "MARKETING"
        assert normalizar_codigo_tipo_fuente("PLANIFICACION") == "PLANIFICACION"

    def test_detectar_tipo_fuente_en_hojas_arbitrarias(self):
        df_eval = pd.DataFrame({
            "Docente": ["Prof. Juan Carlos"],
            "Evaluacion Docente": ["Excelente"],
            "Criterio Desempeno": [5],
            "Satisfaccion": [5]
        })
        detectado = detectar_tipo_fuente_por_cabeceras({"SheetX": df_eval}, filename="unseen_file.xlsx")
        assert detectado == "EVALUACION_DOCENTE"

        df_rent = pd.DataFrame({
            "Categoria": ["Sistemas"],
            "Egresos": [5000.0],
            "Techo Presupuestario": [6000.0],
            "Ejecutado vs Meta": ["95%"]
        })
        detectado_rent = detectar_tipo_fuente_por_cabeceras({"Hoja1": df_rent}, filename="random_file.xlsx")
        assert detectado_rent in ("RENTABILIDAD", "EGRESOS", "TECHOS")

    def test_detectar_tipo_fuente_servicios_no_es_cobranza(self):
        df_serv = pd.DataFrame({
            "Concepto del Servicio": ["Mantenimiento Servidores"],
            "Partida": ["Infraestructura TI"],
            "Cuota": [1],
            "Monto": [5000.0]
        })
        detectado = detectar_tipo_fuente_por_cabeceras({"Hoja1": df_serv}, filename="servicios.xlsx")
        assert detectado in ("EGRESOS", "RENTABILIDAD")
        assert detectado != "COBRANZA"

    def test_detectar_tipo_fuente_acta_con_docente_y_semestre(self):
        df_acta = pd.DataFrame({
            "CI": ["10234567", "10234568", "10234569", "10234570", "10234571"],
            "Estudiante": ["Juan", "Pedro", "Maria", "Ana", "Luis"],
            "Docente": ["Ing. Perez", "Ing. Perez", "Ing. Perez", "Ing. Perez", "Ing. Perez"],
            "Modulo": ["Sistemas", "Sistemas", "Sistemas", "Sistemas", "Sistemas"],
            "Nota Final": [85, 90, 78, 92, 60],
            "Semestre": [1, 2, 3, 4, 5]
        })
        detectado = detectar_tipo_fuente_por_cabeceras({"Hoja1": df_acta}, filename="acta_notas.xlsx")
        assert detectado == "ACTA"
        assert detectado != "EVALUACION_DOCENTE"

    def test_detectar_tipo_fuente_acta_con_matricula(self):
        df_acta = pd.DataFrame({
            "Modulo": ["Algoritmos"],
            "Nota Final": [85],
            "Matricula": ["2025-1"]
        })
        detectado = detectar_tipo_fuente_por_cabeceras({"Hoja1": df_acta}, filename="datos.xlsx")
        assert detectado == "ACTA"
        assert detectado != "ADMISION"
        assert detectado != "MARKETING"


class TestBetoNERAndRelationalExtraction:
    """Verifica las tuplas relacionales extraídas por BETO NER."""

    def test_extraer_tuplas_academicas(self):
        texto = "El estudiante Javier Mendoza cursó el Módulo 2 Modelado con la nota 90."
        entidades = [
            {"tipo": "ESTUDIANTE", "valor": "Javier Mendoza", "score": 0.95, "start": 14, "end": 28},
            {"tipo": "MODULO", "valor": "Módulo 2 Modelado", "score": 0.90, "start": 38, "end": 55},
            {"tipo": "NOTA", "valor": "90", "score": 0.98, "start": 68, "end": 70}
        ]
        tuplas = extraer_tuplas_relacionales(entidades, texto)
        assert len(tuplas["academicas"]) == 1
        t_aca = tuplas["academicas"][0]
        assert t_aca["estudiante"] == "Javier Mendoza"
        assert t_aca["modulo"] == "Módulo 2 Modelado"
        assert t_aca["nota"] == 90.0
        assert t_aca["confianza"] > 0.85

    def test_extraer_tuplas_financieras(self):
        texto = "La alumna Patricia Daza tiene un saldo de 2400 Bs en fecha 2025-05-15."
        entidades = [
            {"tipo": "ESTUDIANTE", "valor": "Patricia Daza", "score": 0.94, "start": 10, "end": 23},
            {"tipo": "MONTO", "valor": "2400 Bs", "score": 0.91, "start": 42, "end": 49},
            {"tipo": "FECHA", "valor": "2025-05-15", "score": 0.96, "start": 59, "end": 69}
        ]
        tuplas = extraer_tuplas_relacionales(entidades, texto)
        assert len(tuplas["financieras"]) == 1
        t_fin = tuplas["financieras"][0]
        assert t_fin["estudiante"] == "Patricia Daza"
        assert t_fin["monto"] == 2400.0
        assert t_fin["fecha"] == "2025-05-15"

    def test_extraer_tuplas_docentes(self):
        texto = "El docente Ing. Marcelo Claure impartió el Módulo 3 Arquitectura ETL."
        entidades = [
            {"tipo": "DOCENTE", "valor": "Ing. Marcelo Claure", "score": 0.95, "start": 11, "end": 30},
            {"tipo": "MODULO", "valor": "Módulo 3 Arquitectura ETL", "score": 0.92, "start": 43, "end": 68}
        ]
        tuplas = extraer_tuplas_relacionales(entidades, texto)
        assert len(tuplas["docentes"]) == 1
        t_doc = tuplas["docentes"][0]
        assert t_doc["docente"] == "Ing. Marcelo Claure"
        assert t_doc["modulo"] == "Módulo 3 Arquitectura ETL"

    def test_labels_bio_completos(self):
        assert "B-PER_ESTUDIANTE" in LABEL_LIST or "B-ESTUDIANTE" in LABEL_LIST
        assert "B-PER_DOCENTE" in LABEL_LIST or "B-DOCENTE" in LABEL_LIST
        assert "B-PROGRAMA" in LABEL_LIST
        assert "B-MODULO" in LABEL_LIST

    def test_tuplas_financieras_sin_producto_cartesiano(self):
        """Múltiples estudiantes y montos deben asociarse por proximidad, no por producto cartesiano."""
        texto = "Juan Perez debe 1.200,50 Bs y Maria Lopez debe 3.400,00 Bs."
        entidades = [
            {"tipo": "ESTUDIANTE", "valor": "Juan Perez", "score": 0.95, "start": 0, "end": 10},
            {"tipo": "MONTO", "valor": "1.200,50 Bs", "score": 0.90, "start": 16, "end": 27},
            {"tipo": "ESTUDIANTE", "valor": "Maria Lopez", "score": 0.95, "start": 30, "end": 41},
            {"tipo": "MONTO", "valor": "3.400,00 Bs", "score": 0.90, "start": 47, "end": 58},
        ]
        tuplas = extraer_tuplas_relacionales(entidades, texto)
        assert len(tuplas["financieras"]) == 2
        # Juan Perez -> 1200.5
        assert tuplas["financieras"][0]["estudiante"] == "Juan Perez"
        assert tuplas["financieras"][0]["monto"] == 1200.5
        # Maria Lopez -> 3400.0
        assert tuplas["financieras"][1]["estudiante"] == "Maria Lopez"
        assert tuplas["financieras"][1]["monto"] == 3400.0

    def test_parseo_nota_decimal_espanol(self):
        """Notas con coma decimal (ej. 85,5) deben parsearse exactamente."""
        texto = "El alumno Carlos Torrico obtuvo una calificacion de 85,5 puntos."
        entidades = [
            {"tipo": "ESTUDIANTE", "valor": "Carlos Torrico", "score": 0.95, "start": 10, "end": 24},
            {"tipo": "NOTA", "valor": "85,5", "score": 0.92, "start": 52, "end": 56}
        ]
        tuplas = extraer_tuplas_relacionales(entidades, texto)
        assert len(tuplas["academicas"]) == 1
        assert tuplas["academicas"][0]["nota"] == 85.5


class TestDataWarehouseResetSafety:
    """Verifica la seguridad y los invariantes del reset de Data Warehouse."""

    def test_requiere_confirmacion_explicita(self):
        with pytest.raises(ValueError, match="confirm=True"):
            reset_data_warehouse(confirm=False)

    def test_tablas_preservadas_estricto(self):
        assert "users" in TABLAS_PRESERVAR
        assert "dim_tiempo" in TABLAS_PRESERVAR
        assert "cat_institucion" in TABLAS_PRESERVAR

    def test_tablas_truncadas_incluyen_constelacion_completa(self):
        assert "fact_rendimiento_academico" in TABLAS_TRUNCAR
        assert "fact_situacion_financiera" in TABLAS_TRUNCAR
        assert "fact_evaluacion_docente" in TABLAS_TRUNCAR
        assert "fact_marketing" in TABLAS_TRUNCAR
        assert "fact_rentabilidad" in TABLAS_TRUNCAR
        assert "fact_forecast" in TABLAS_TRUNCAR
        assert "fact_cobranzas_proyectadas" in TABLAS_TRUNCAR
        assert "staging_registros_crudos" in TABLAS_TRUNCAR
        assert "stg_entidad_no_resuelta" in TABLAS_TRUNCAR
        assert "dim_origen_documental" in TABLAS_TRUNCAR
        assert "lote" in TABLAS_TRUNCAR
