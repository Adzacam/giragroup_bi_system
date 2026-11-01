"""
test_categorizacion_y_cierre.py — Tests para Loop 3 (Extracción, categorización, persistencia y reporte)

Valida la extracción de texto plano, la asignación de categorías, la persistencia en JSONL
y el cumplimiento estricto del invariante de conservación sobre el corpus real en uploads/data.
Queda prohibido usar uploads/test o datos sintéticos preexistentes.
"""

import json
import os
import tempfile

import pandas as pd
import pytest

from pipeline.ingesta import (
    clasificar_bloque,
    extraer_documentos_isla,
    procesar_corpus,
    generar_reporte_auditoria,
)


CORPUS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "uploads", "data"
)


class TestClasificarBloque:

    def test_clasificacion_academica(self):
        """Archivos u hojas con términos académicos se clasifican como 'academico'."""
        cat1 = clasificar_bloque("Base centralizada Académica ARCA (1).xlsx", "ACTAS DE NOTAS")
        assert cat1 == "academico"

        cat2 = clasificar_bloque("Evaluación Docente y Unifranz.xlsx", "DIP. EXP DOC. X MODULO")
        assert cat2 == "academico"

    def test_clasificacion_financiera(self):
        """Archivos u hojas con términos financieros se clasifican como 'financiero'."""
        cat1 = clasificar_bloque("BD Cobranzas.xlsx", "COBRANZAS 2024 2025")
        assert cat1 == "financiero"

        cat2 = clasificar_bloque("BD Egresos.xlsx", "egresos")
        assert cat2 == "financiero"

        cat3 = clasificar_bloque("BD Techos.xlsx", "BD Techos")
        assert cat3 == "financiero"

    def test_clasificacion_comercial(self):
        """Archivos u hojas con términos comerciales se clasifican como 'comercial'."""
        cat1 = clasificar_bloque("TBL_INSCRITOS.xlsx", "TBL_INSCRITOS")
        assert cat1 == "comercial"

        cat2 = clasificar_bloque("EJECUTADO VS META.xlsx", "EJECUTADO")
        # Ambos 'ejecutado' y 'meta' están presentes; meta suma comercial
        assert cat2 in ("comercial", "financiero")

    def test_bloque_ruido_es_descartable(self):
        """Un bloque marcado como ruido (es_ruido=True) se clasifica como 'descartable'."""
        cat = clasificar_bloque("Cualquiera.xlsx", "Hoja1", es_ruido=True)
        assert cat == "descartable"


class TestExtraerDocumentos:

    def test_extraccion_isla_valida(self):
        """Extrae texto plano concatenado y metadatos correctos por fila."""
        df_isla = pd.DataFrame([
            ["POS-001", "Ana Perez", "95"],
            ["POS-002", "Juan Lopez", "80"],
        ])
        isla = {
            "indice": 0,
            "fila_inicio": 5,
            "fila_fin": 6,
            "n_filas": 2,
            "es_ruido": False,
            "df": df_isla,
        }

        docs, n_proc, n_vac = extraer_documentos_isla("archivo.xlsx", "Hoja1", isla, "academico")

        assert len(docs) == 2
        assert n_proc == 2
        assert n_vac == 0
        assert docs[0]["id"] == "archivo.xlsx::Hoja1::isla_0::fila_5"
        assert docs[0]["texto"] == "POS-001 | Ana Perez | 95"
        assert docs[0]["categoria"] == "academico"
        assert docs[1]["id"] == "archivo.xlsx::Hoja1::isla_0::fila_6"

    def test_extraccion_isla_con_fila_vacia(self):
        """Filas vacías dentro de la isla no se convierten en documento y se contabilizan."""
        df_isla = pd.DataFrame([
            ["POS-001", "Ana"],
            ["", "   "],       # fila vacía
            ["POS-002", "Juan"],
        ])
        isla = {
            "indice": 1,
            "fila_inicio": 10,
            "fila_fin": 12,
            "n_filas": 3,
            "es_ruido": False,
            "df": df_isla,
        }

        docs, n_proc, n_vac = extraer_documentos_isla("archivo.xlsx", "Hoja1", isla, "academico")

        assert len(docs) == 2
        assert n_proc == 2
        assert n_vac == 1

    def test_extraccion_isla_ruido(self):
        """Islas de ruido no generan documentos."""
        isla = {
            "indice": 0,
            "fila_inicio": 0,
            "fila_fin": 0,
            "n_filas": 1,
            "es_ruido": True,
            "df": pd.DataFrame([["Encabezado suelto"]]),
        }
        docs, n_proc, n_vac = extraer_documentos_isla("archivo.xlsx", "Hoja1", isla, "descartable")
        assert docs == []
        assert n_proc == 0
        assert n_vac == 0


class TestCierreCorpusEInvariante:

    @pytest.mark.skipif(
        not os.path.isdir(CORPUS_DIR),
        reason="Corpus real no disponible en uploads/data",
    )
    def test_ejecucion_end_to_end_corpus_real(self, tmp_path):
        """
        Ejecuta Loop 3 sobre todos los archivos reales de uploads/data:
        - Persiste JSONL en archivo temporal.
        - Verifica el cumplimiento estricto del invariante de conservación:
          total_filas_raw = filas_procesadas + filas_descartadas_ruido + filas_vacias
        - Comprueba que todos los archivos tengan invariante_ok == True.
        """
        ruta_salida = os.path.join(str(tmp_path), "corpus_documentos.jsonl")
        docs, auditoria = procesar_corpus(CORPUS_DIR, ruta_salida_jsonl=ruta_salida)

        # 1. Validación global
        assert auditoria["archivos_leidos"] == 10
        assert auditoria["hojas_totales"] == 62
        assert auditoria["invariante_cumplido"] is True
        assert len(docs) == auditoria["filas_procesadas"]
        assert auditoria["filas_procesadas"] > 90000

        # 2. Invariante algebraico
        total_esperado = (
            auditoria["filas_procesadas"]
            + auditoria["filas_descartadas_ruido"]
            + auditoria["filas_vacias"]
        )
        assert total_esperado == auditoria["total_filas_raw"]

        # 3. Todos los archivos individuales deben cumplir el invariante
        for arch in auditoria["desglose_por_archivo"]:
            assert arch["invariante_ok"] is True, f"Invariante falló en {arch['archivo']}"

        # 4. Verificar archivo JSONL persistido
        assert os.path.exists(ruta_salida)
        line_count = 0
        with open(ruta_salida, "r", encoding="utf-8") as f:
            for line in f:
                line_count += 1
                doc_obj = json.loads(line)
                assert "id" in doc_obj
                assert "categoria" in doc_obj
                assert "texto" in doc_obj
        assert line_count == len(docs)

        # 5. Verificar reporte markdown generado
        reporte_md = generar_reporte_auditoria(auditoria)
        assert "# Reporte Final de Auditoría" in reporte_md
        assert "✅ SÍ (100% verificado)" in reporte_md

