"""Pruebas unitarias F6-1: Extractor de Contexto de Hoja (Nivel 1)."""
import sys
import time
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
for p in (str(RAIZ), str(RAIZ / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from pipeline.ingesta import extraer_encabezado_hoja
from services.beto_integracion import (
    CacheMemoria,
    ClienteBeto,
    EntidadBeto,
    aplicar_herencia_hoja,
    extraer_contexto_hoja,
)


def test_extraer_encabezado_hoja_pre_tabla_y_limite_tokens():
    df = pd.DataFrame([
        ["DIPLOMADO EN FINANZAS CORPORATIVAS", "DIPLOMADO EN FINANZAS CORPORATIVAS", None],
        ["MÓDULO 2: VALORACIÓN DE EMPRESAS", None, None],
        ["Docente: Dr. Carlos Mendoza", "Gestión 2025", None],
        ["CI", "NOMBRE COMPLETO", "NOTA FINAL"],
        ["1234567", "Ana Pérez", "85"],
    ])
    texto = extraer_encabezado_hoja(df, "Acta_Finanzas.xlsx", "Enero-2026", fila_cabecera=3)
    assert "Acta_Finanzas" in texto
    assert "Enero-2026" in texto
    assert "DIPLOMADO EN FINANZAS CORPORATIVAS" in texto
    assert "Dr. Carlos Mendoza" in texto
    # No debe incluir la fila de cabecera ni filas de datos
    assert "Ana Pérez" not in texto
    assert len(texto.split()) <= 90


def test_extraer_contexto_hoja_una_sola_inferencia_y_sin_texto_crudo():
    llamadas = []

    def fake_post(lote):
        llamadas.append(list(lote))
        t = lote[0]
        ents = []
        for etiqueta, sub in (
            ("PROGRAMA", "Diplomado en Finanzas Corporativas"),
            ("MODULO", "Valoración de Empresas"),
            ("DOCENTE", "Carlos Mendoza"),
        ):
            idx = t.find(sub)
            if idx >= 0:
                ents.append(EntidadBeto(etiqueta, sub, idx, idx + len(sub), 0.92))
        return [ents]

    cliente = ClienteBeto(cache=CacheMemoria(), post=fake_post)
    txt_pre = (
        "ARCHIVO: Actas | HOJA: Enero-2026 | "
        "Diplomado en Finanzas Corporativas | Valoración de Empresas | Carlos Mendoza"
    )
    t0 = time.perf_counter()
    ctx = extraer_contexto_hoja("Actas.xlsx", "Enero-2026", texto_pre_tabla=txt_pre, cliente=cliente)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert len(llamadas) == 1
    assert elapsed_ms < 100.0
    assert ctx["programa"] == "Diplomado en Finanzas Corporativas"
    assert ctx["modulo"] == "Valoración de Empresas"
    assert ctx["docente"] == "Carlos Mendoza"
    assert ctx["gestion"] == 2026
    assert ctx["mes"] == 1
    assert ctx["fecha"] == "2026-01-01"
    # Jamás persistir texto crudo repetido
    assert "contexto_hoja_texto" not in ctx


def test_extraer_contexto_hoja_pestana_cobranzas_rango_anios():
    ctx = extraer_contexto_hoja("BD Cobranzas.xlsx", "COBRANZAS 2024 2025", cliente=None)
    assert ctx["gestion"] == 2025
    assert "contexto_hoja_texto" not in ctx


def test_herencia_no_pisa_columnas_explicitas():
    ctx_hoja = {
        "programa": "Diplomado en Finanzas",
        "modulo": "Módulo 1",
        "docente": "Carlos Mendoza",
        "gestion": 2026,
        "mes": 1,
        "fecha": "2026-01-01",
    }
    fila = {
        "programa": "Maestría en Derecho",
        "modulo": None,
        "docente": "",
        "fecha": "2025-11-15",
        "gestion": None,
    }
    res, heredado = aplicar_herencia_hoja(fila, ctx_hoja)
    assert heredado is True
    assert res["programa"] == "Maestría en Derecho"  # explícito intacto
    assert res["fecha"] == "2025-11-15"              # explícito intacto
    assert res["modulo"] == "Módulo 1"               # heredado
    assert res["docente"] == "Carlos Mendoza"        # heredado
    assert res["gestion"] == 2026                    # heredado

    fila_completa = {
        "programa": "P",
        "modulo": "M",
        "docente": "D",
        "gestion": 2024,
        "mes": 5,
        "fecha": "2024-05-01",
    }
    res2, heredado2 = aplicar_herencia_hoja(fila_completa, ctx_hoja)
    assert heredado2 is False
    assert res2 == fila_completa
