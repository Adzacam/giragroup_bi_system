"""Pruebas unitarias F7: tasa_acuerdo, rescate académico acotado, POST /embed, mapeo semántico y compuerta de dominio CMI."""
import io
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[2]
for p in (str(RAIZ), str(RAIZ / "backend"), str(RAIZ / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from pipeline.ingesta import MOTIVO_FUERA_DE_ALCANCE_CMI, evaluar_compuerta_dominio_cmi
from services import beto_integracion as bi
from services.mapeo_semantico_encabezados import (
    ORIGEN_BETO_ESQUEMA,
    MapeadorSemanticoEncabezados,
    perfil_columna_compatible,
)
from routers.dataops.extraccion import resolver_encabezados_beto_esquema


# ── F7-1a: Agregación correcta de tasa_acuerdo ────────────────────────────────

def test_f7_1a_agregacion_tasa_acuerdo_en_rango_0_1():
    from f6_regresion_tmpfs import agregar_beto_totales

    libros = [
        {"comparadas_acuerdo": 100, "acuerdos": 99, "desacuerdos": 1, "tasa_acuerdo": 0.99, "tiempo_beto_s": 10.2},
        {"comparadas_acuerdo": 110, "acuerdos": 108, "desacuerdos": 2, "tasa_acuerdo": 0.9818, "tiempo_beto_s": 5.3},
    ]
    tot = agregar_beto_totales(libros)
    assert tot["acuerdos"] == 207
    assert tot["comparadas_acuerdo"] == 210
    assert tot["tasa_acuerdo"] == 0.9857
    assert 0.0 <= tot["tasa_acuerdo"] <= 1.0


# ── F7-1b: Rescate académico acotado a hojas sin columna estructurada ─────────

def test_f7_1b_hoja_con_columnas_estructuradas_no_dispara_rescate(monkeypatch):
    monkeypatch.setenv("BETO_RESCATE_ACADEMICO", "1")
    monkeypatch.setenv("BETO_CASCADA_FINAL", "0")
    monkeypatch.setenv("BETO_ACUERDO_QC", "0")

    filas_estructuradas = [
        {"POS - ACTAS": "POS-5000", "MODULO 1": "85", "NOMBRE COMPLETO": "Ana Perez"},
    ]
    tiene_prog, tiene_mod = bi.hoja_tiene_columnas_academicas(filas_estructuradas)
    assert tiene_prog is True
    assert tiene_mod is True

    llamadas = []
    cont = bi.Contadores()
    cli = bi.ClienteBeto(cache=bi.CacheMemoria(), post=lambda lote: (llamadas.append(lote) or [[] for _ in lote]), contadores=cont)
    bi.refinar_lineas(
        ["POS - ACTAS: POS-5000 | MODULO 1: 85 | NOMBRE COMPLETO: Ana Perez"],
        lambda _l, **_kw: ([], 0.95, False),
        tipo_fuente="ACTA",
        cliente=cli,
        contadores=cont,
        permitir_rescate_programa=not tiene_prog,
        permitir_rescate_modulo=not tiene_mod,
    )
    assert llamadas == []
    assert cont.residuales_academicas_enviadas == 0

    # Hoja SIN columnas estructuradas de programa/módulo -> sí permite rescate
    filas_libres = [{"OBSERVACION": "Diplomado en Finanzas - Modulo 2", "NOMBRE COMPLETO": "Ana Perez"}]
    tp2, tm2 = bi.hoja_tiene_columnas_academicas(filas_libres)
    assert tp2 is False and tm2 is False


# ── F7-2b: Mapeo semántico con triple compuerta (coseno + margen + perfil) ────

def _fake_embed_semantico(textos):
    """Genera vectores ortogonales de prueba (8 dim) para validar la triple compuerta determinísticamente."""
    # Ejes: 0=nota, 1=monto, 2=ci, 3=docente, 4=estudiante, 5=programa, 6=modulo, 7=fecha
    mapa_kw = [
        (["calif", "nota", "promedio", "puntaje"], [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        (["importe", "monto", "saldo", "deuda", "pago", "cuota", "valor monetario", "fact"], [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        (["carnet", "cedula", "identidad", "ident", "ci"], [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        (["docente", "profesor", "facilitador", "titular", "instructor"], [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]),
        (["estudiante", "alumno", "nombres y apellidos", "participante", "postulante"], [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]),
        (["programa", "diplomado", "maestria", "pos"], [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0]),
        (["modulo", "asignatura", "materia", "curso"], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]),
        (["fecha"], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ]
    out = []
    for t in textos:
        tl = t.lower()
        if "ambiguo" in tl:
            # Similitud casi empatada entre nota (0.71) y monto (0.70) -> margen < 0.05 => debe rechazarse
            out.append([0.71, 0.70, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            continue
        vec = [0.0] * 8
        for kws, base in mapa_kw:
            if any(k in tl for k in kws):
                vec = [a + b for a, b in zip(vec, base)]
                break
        nrm = math.sqrt(sum(x * x for x in vec))
        out.append([x / nrm for x in vec] if nrm > 0 else [0.1] * 8)
    return out


def test_f7_2b_triple_compuerta_resuelve_ineditos_y_rechaza_incompatibles():
    mapper = MapeadorSemanticoEncabezados(embed_fn=_fake_embed_semantico, umbral_coseno=0.78, margen_minimo=0.05)

    encabezados = {
        "Calif. Pond.": ["85", "92.5", "70", "64", "88"],
        "Importe Neto Fact.": ["Bs. 1500", "2400.50", "1800", "3200"],
        "Carnet Ident.": ["6543269", "7788991-LP", "5432109"],
        "Docente Titular": ["Carlos Mendoza Ruiz", "Ana Maria Torrez", "Luis Rojas"],
        # Incompatible por perfil de columna: encabezado dice "Calif." pero valores son texto libre
        "Calif. Comentario": ["Muy bueno el curso", "Excelente explicacion", "Todo claro"],
        # Ambiguo: margen top1 - top2 < 0.05
        "Campo Ambiguo": ["80", "90", "85"],
        # Match RapidFuzz >= 85.0: jamás debe sobrescribirse
        "ESTUDIANTE": ["Juan Perez Lopez", "Maria Gomez"],
    }
    res = resolver_encabezados_beto_esquema(encabezados, mapeador=mapper)

    assert res["Calif. Pond."]["rol"] == "nota_final"
    assert res["Calif. Pond."]["origen"] == ORIGEN_BETO_ESQUEMA
    assert res["Importe Neto Fact."]["rol"] == "monto"
    assert res["Carnet Ident."]["rol"] == "ci_estudiante"
    assert res["Docente Titular"]["rol"] == "docente"
    # Rechazados por compuerta 2 (margen) y compuerta 3 (perfil de columna)
    assert "Calif. Comentario" not in res
    assert "Campo Ambiguo" not in res
    # Jamás sobrescribe RapidFuzz >= 85.0
    assert "ESTUDIANTE" not in res


def test_f7_2b_perfil_columna_sin_muestra_rechaza():
    assert perfil_columna_compatible("nota_final", []) is False
    assert perfil_columna_compatible("monto", ["", None, "nan"]) is False


# ── F7-3: Compuerta de dominio CMI en ingesta ─────────────────────────────────

def test_f7_3_compuerta_aisla_planillas_fuera_de_dominio_y_acepta_dominio():
    df_inventario = pd.DataFrame([
        ["CODIGO_ACTIVO", "DESCRIPCION_EQUIPO", "NUMERO_SERIE", "UBICACION_OFICINA", "ESTADO_FISICO"],
        ["ACT-001", "Laptop Dell Latitude", "SN998877", "Piso 3", "Operativo"],
        ["ACT-002", "Monitor LG 27", "SN445566", "Piso 2", "En mantenimiento"],
    ])
    res_inv = evaluar_compuerta_dominio_cmi(df_inventario)
    assert res_inv["en_alcance"] is False
    assert res_inv["motivo"] == MOTIVO_FUERA_DE_ALCANCE_CMI

    df_rrhh = pd.DataFrame([
        ["LEGAJO", "CARGO_INTERNO", "DIAS_VACACION", "AREA_OPERATIVA", "TURNO"],
        ["EMP-10", "Recepcionista", "15", "Administracion", "Mañana"],
        ["EMP-11", "Mensajero", "10", "Logistica", "Tarde"],
    ])
    res_rrhh = evaluar_compuerta_dominio_cmi(df_rrhh)
    assert res_rrhh["en_alcance"] is False
    assert res_rrhh["motivo"] == MOTIVO_FUERA_DE_ALCANCE_CMI

    df_acta = pd.DataFrame([
        ["CI", "NOMBRE COMPLETO", "POS - ACTAS", "MODULO 1", "NOTA FINAL"],
        ["6543269", "Ana Perez", "POS-5000", "85", "85"],
        ["7788991", "Luis Rojas", "POS-5000", "90", "90"],
    ])
    res_acta = evaluar_compuerta_dominio_cmi(df_acta)
    assert res_acta["en_alcance"] is True
    assert res_acta["motivo"] is None
