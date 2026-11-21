"""Tests FU-L8 (FU-M3a): POST /preview-workbook (0 PII, hojas usadas/ignoradas/ocultas, mapeo editable) y resumen_cascada."""
import io
import json
import sys
from pathlib import Path

import openpyxl
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from main import app  # noqa: E402
from core.security import get_current_user  # noqa: E402
from models.user import User  # noqa: E402
from routers.dataops.lectura import _calcular_resumen_cascada  # noqa: E402


def _cliente():
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1, username="auditor", email="auditor@ejemplo.test", role="AUDITOR_CALIDAD", is_active=True
    )
    return TestClient(app)


def _xlsx_sintetico() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DATOS_ACTA"
    ws.append(["CI", "Estudiante", "Nota Final", "Estado Académico"])
    ws.append(["88990011", "Juan Carlos Perez", 85, "Aprobado"])
    ws.append(["77665544", "Maria Fernanda Lopez", 91, "Aprobado"])

    ws_hid = wb.create_sheet("Copia oculta")
    ws_hid.sheet_state = "hidden"
    ws_hid.append(["CI", "Estudiante"])
    ws_hid.append(["11223344", "Oculto Prueba"])

    ws_aux = wb.create_sheet("Hoja 4")
    ws_aux.append(["Col1"])
    ws_aux.append(["Resumen"])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_preview_workbook_sin_pii_y_con_mapeo_editable():
    cli = _cliente()
    contenido = _xlsx_sintetico()
    res = cli.post(
        "/api/v1/dataops/preview-workbook",
        files=[("file", ("libro_sintetico.xlsx", contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert data["resumen_hojas"]["total"] == 3
    assert data["resumen_hojas"]["usadas"] == 1
    assert data["resumen_hojas"]["ocultas"] == 1

    por_hoja = {h["hoja"]: h for h in data["hojas"]}
    assert por_hoja["DATOS_ACTA"]["decision"] == "usada"
    assert por_hoja["DATOS_ACTA"]["estado_visibilidad"] == "visible"
    assert por_hoja["DATOS_ACTA"]["filas_estimadas"] == 2
    assert por_hoja["Copia oculta"]["decision"] == "ignorada"
    assert por_hoja["Copia oculta"]["estado_visibilidad"] == "oculta"
    assert por_hoja["Hoja 4"]["decision"] == "ignorada"

    mapeo = {m["columna_origen"]: m["campo_canonico"] for m in data["mapeo_columnas"]}
    assert mapeo["CI"] == "ci"
    assert mapeo["Estudiante"] == "nombre_completo"
    assert mapeo["Nota Final"] == "nota_final"
    assert mapeo["Estado Académico"] == "estado_academico"
    assert "ci" in data["campos_canonicos_disponibles"]

    texto_plano = json.dumps(data, ensure_ascii=False)
    for pii in ("88990011", "Juan Carlos Perez", "77665544", "Maria Fernanda Lopez", "11223344", "Oculto Prueba"):
        assert pii not in texto_plano


def test_resumen_cascada_etapas_ordenadas():
    detalles = [
        {
            "lectura": {
                "entidades": [
                    {"origen_confianza": "CI_EXACTA"},
                    {"origen_confianza": "REGLA_ENCABEZADO"},
                    {"origen_confianza": "FUZZY"},
                ]
            }
        },
        {
            "lectura": {
                "entidades": [
                    {"fuente_resolucion": "REGEX"},
                    {"fuente_resolucion": "BETO"},
                    {"fuente_resolucion": "BETO"},
                ]
            }
        },
    ]
    cascada = _calcular_resumen_cascada(detalles)
    assert cascada["CI_EXACTA"] == 1
    assert cascada["ENCABEZADO"] == 1
    assert cascada["FUZZY"] == 1
    assert cascada["REGEX"] == 1
    assert cascada["BETO"] == 2
    assert cascada["total_entidades"] == 6
    assert [e["etapa"] for e in cascada["etapas"]] == ["CI_EXACTA", "ENCABEZADO", "FUZZY", "REGEX", "BETO"]
    assert sum(e["cantidad"] for e in cascada["etapas"]) == 6
