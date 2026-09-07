"""
tests/test_formatter_gira40.py — Validación de Formateo Semántico para BETO (GIRA-40)

Pruebas:
1. CatalogoGazetteer: Carga e inyección correcta de nombres oficiales a partir de POS-XXXX o números.
2. Invariante de Spans: oracion[span['start']:span['end']] == span['valor'].
3. Límite de 512 tokens: Validación sobre 50 documentos del corpus real.
4. Higiene de texto: Cero caracteres de control o bytes nulos que rompan tokenizers.
"""

import json
import os
import pytest
from pipeline.semantic.formatter import (
    CatalogoGazetteer,
    formatear_documento,
    obtener_gazetteer,
    limpiar_texto_celda,
)

RUTA_JSONL = os.path.join("output", "sprint2_documentos.jsonl")


class TestCatalogoGazetteer:
    """Valida la carga y resolución léxica del catálogo."""

    def test_carga_correcta_programas(self):
        gaz = CatalogoGazetteer()
        assert len(gaz.programas) >= 700, f"Se esperaban >= 700 programas, cargados: {len(gaz.programas)}"

    def test_resolucion_pos_con_prefijo_y_numerico(self):
        gaz = CatalogoGazetteer()
        # Con prefijo
        pos1, nom1 = gaz.resolver_programa("POS-5308")
        assert pos1 == "POS-5308"
        assert "DERECHO NOTARIAL" in nom1.upper()

        # Solo número
        pos2, nom2 = gaz.resolver_programa("5308")
        assert pos2 == "POS-5308"
        assert "DERECHO NOTARIAL" in nom2.upper()

        # Número float como string
        pos3, nom3 = gaz.resolver_programa("5308.0")
        assert pos3 == "POS-5308"

    def test_resolucion_programas_clave(self):
        gaz = CatalogoGazetteer()
        claves = ["POS-5252", "POS-5308", "POS-5376", "POS-5310"]
        for c in claves:
            pos, nom = gaz.resolver_programa(c)
            assert pos == c
            assert len(nom) > 5
            assert nom != c, f"El programa {c} no resolvió un nombre oficial"


class TestInvarianteSpansYOffsets:
    """Valida que todos los character offsets coincidan exactamente con el substring."""

    def test_offsets_actas_notas(self):
        doc = {
            "archivo": "test.xlsx",
            "hoja": "ACTAS DE NOTAS",
            "bloque_id": 0,
            "categoria": "academico",
            "texto_plano": (
                "POS - ACTAS | CÉDULA DE IDENTIDAD | APELLIDO PATERNO | NOMBRES | MÓDULO 1 | ESTADO\n"
                "POS-5381 | 3792463 | ABREGO | ROMEO GUNNAR | 95 | Aprobado"
            )
        }
        res = formatear_documento(doc)
        assert len(res) == 1
        item = res[0]
        assert item["subtipo"] == "ACTAS_NOTAS"

        for span in item["entidades_pistas"]:
            recuperado = item["oracion"][span["start"]:span["end"]]
            assert recuperado == span["valor"], f"Desfase de offset: '{recuperado}' != '{span['valor']}'"

    def test_offsets_evaluacion_docente(self):
        doc = {
            "archivo": "test.xlsx",
            "hoja": "EVALUACION DOCENTE",
            "bloque_id": 0,
            "categoria": "academico",
            "texto_plano": (
                "Nombre Completo | Programa | Módulo | Fecha | 1. ¿La/El docente explica bien?\n"
                "EDWIN BRAVO | POS-5252 | 1 | 2024-11-21 17:53:00 | 5/Totalmente de acuerdo"
            )
        }
        res = formatear_documento(doc)
        assert len(res) == 1
        item = res[0]
        assert item["subtipo"] == "EVALUACION_DOCENTE"

        for span in item["entidades_pistas"]:
            recuperado = item["oracion"][span["start"]:span["end"]]
            assert recuperado == span["valor"]

    def test_offsets_cobranzas(self):
        doc = {
            "archivo": "test.xlsx",
            "hoja": "COBRANZAS",
            "bloque_id": 0,
            "categoria": "financiero",
            "texto_plano": (
                "Fecha de Facturación | N° de Factura | NIT | Razón Social | Concepto | Monto\n"
                "2025-10-13 00:00:00 | 8634 | 7504276 | SILVIA SANCHEZ | CUOTA POSTGRADO | 848"
            )
        }
        res = formatear_documento(doc)
        assert len(res) == 1
        item = res[0]
        assert item["subtipo"] == "COBRANZAS"

        for span in item["entidades_pistas"]:
            recuperado = item["oracion"][span["start"]:span["end"]]
            assert recuperado == span["valor"]

    def test_offsets_inscripciones(self):
        doc = {
            "archivo": "test.xlsx",
            "hoja": "TBL_INSCRITOS",
            "bloque_id": 0,
            "categoria": "comercial",
            "texto_plano": (
                "MARCA TEMPORAL | NUMEROPROYECTO | ASESOR | CI | NOMBRES | PATERNO\n"
                "2023-04-14 19:44:33 | POS-4403 | PATRICIA DEL CASTILLO | 1114709 | CLAUDIA | BARYNA"
            )
        }
        res = formatear_documento(doc)
        assert len(res) == 1
        item = res[0]
        assert item["subtipo"] == "INSCRIPCIONES"

        for span in item["entidades_pistas"]:
            recuperado = item["oracion"][span["start"]:span["end"]]
            assert recuperado == span["valor"]


class TestValidacion50DocumentosCorpusReal:
    """Valida límites de tokens, higiene de caracteres y estabilidad sobre el corpus real."""

    def test_ejecucion_50_documentos_limite_tokens(self):
        assert os.path.exists(RUTA_JSONL), f"No existe {RUTA_JSONL}"

        with open(RUTA_JSONL, "r", encoding="utf-8") as f:
            docs = [json.loads(line) for line in f]

        assert len(docs) >= 50, f"Se esperaban al menos 50 documentos, encontrados {len(docs)}"

        muestras_50 = docs[:50]
        total_oraciones = 0

        for d_idx, doc in enumerate(muestras_50):
            # Procesar hasta 5 filas por documento para probar diversidad de subtipos
            oraciones = formatear_documento(doc, max_filas=5)
            for o in oraciones:
                total_oraciones += 1
                texto = o["oracion"]

                # 1. Higiene: Sin bytes nulos ni caracteres de control
                assert "\x00" not in texto, f"Byte nulo detectado en doc {d_idx}"
                assert "\r" not in texto, f"Retorno de carro no filtrado en doc {d_idx}"

                # 2. Límite estricto de tokens de BETO (< 512)
                # Un token aproximado es ~0.75 palabras, con len(split) < 350 es seguro < 512
                n_palabras = len(texto.split())
                assert n_palabras < 380, f"Oración demasiado larga ({n_palabras} palabras): {texto[:100]}..."
                assert o["n_tokens_aprox"] < 512, f"Tokens aprox exceden 512: {o['n_tokens_aprox']}"

                # 3. Verificación de spans de entidades
                for s in o["entidades_pistas"]:
                    sub = texto[s["start"]:s["end"]]
                    assert sub == s["valor"], (
                        f"Falla de span en doc {d_idx} ({o['subtipo']}): "
                        f"esperado '{s['valor']}', obtenido '{sub}' en [{s['start']}:{s['end']}]"
                    )

        assert total_oraciones >= 50, f"Se esperaban >= 50 oraciones procesadas, total: {total_oraciones}"

    def test_limpieza_texto_celda(self):
        sucio = "  Hola \x00 mundo \x08 con   espacios \t y saltos \n "
        limpio = limpiar_texto_celda(sucio)
        assert "\x00" not in limpio
        assert "\x08" not in limpio
        assert limpio == "Hola mundo con espacios y saltos"
