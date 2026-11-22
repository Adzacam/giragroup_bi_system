"""
Pruebas de verificación de PLAN_DATAOPS_FLUJO (DF-L1, DF-L2, DF-L4, DF-L7, DF-L11).
"""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from pipeline.normalization.asymmetric_flattener import AsymmetricFlattener
from pipeline.normalization.fk_resolver import FKResolver
from services.revision_acciones_descriptor import construir_acciones
from services.revision_formularios import construir_motivo_detalle
from services.risk_service import _enmascarar_nombre


def test_df_l1_periodo_acotado():
    rango_absurdo = AsymmetricFlattener.calcular_rango_fechas(["2020", "2029"])
    assert "2029" not in rango_absurdo
    assert AsymmetricFlattener.calcular_rango_fechas(["2099"]) == "Sin fechas"


def test_df_l2_acciones_por_motivo_y_roles_dd2():
    acc_admin = construir_acciones("HOMONIMIA", "academico", {}, rol_usuario="ADMIN")
    assert any(a["codigo"] == "CREAR_PERFIL_C" for a in acc_admin)
    acc_dir = construir_acciones("HOMONIMIA", "academico", {}, rol_usuario="DIRECTOR_ACADEMICO")
    assert not any(a["codigo"] == "CREAR_PERFIL_C" for a in acc_dir)

    acc_conf_admin = construir_acciones("CONFLICTO_FUENTES", "academico", {}, rol_usuario="ADMIN")
    assert any(a["codigo"] == "CAMBIAR_FUENTE_PRIORITARIA" for a in acc_conf_admin)
    acc_conf_aud = construir_acciones("CONFLICTO_FUENTES", "academico", {}, rol_usuario="AUDITOR_CALIDAD")
    assert not any(a["codigo"] == "CAMBIAR_FUENTE_PRIORITARIA" for a in acc_conf_aud)


def test_df_l2_sin_lectura_separado_de_baja_confianza():
    det = construir_motivo_detalle("academico", "BAJA_CONFIANZA_IA", {"confianza": 0.0})
    assert "no tiene datos legibles" in det.lower()
    assert "[0,60; 0,85)" not in det
    acc = construir_acciones("BAJA_CONFIANZA", "academico", {"ner_confidence": 0.0}, rol_usuario="ADMIN")
    assert acc[0]["codigo"] == "COMPLETAR_DATOS"


def test_df_l4_evaluacion_sin_hex_ni_paso3():
    ev_src = Path("backend/routers/dataops/evaluacion.py").read_text(encoding="utf-8")
    for hx in ("#3b82f6", "#10b981", "#f59e0b", "#8b5cf6"):
        assert hx not in ev_src
    lec_src = Path("backend/routers/dataops/lectura.py").read_text(encoding="utf-8")
    assert "Ábrela en el paso ②" in lec_src
    assert "Ábrela en el paso ③" not in lec_src


def test_df_l7_sin_listas_fijas_en_fk_resolver_y_extraccion():
    fk_src = Path("pipeline/normalization/fk_resolver.py").read_text(encoding="utf-8")
    assert "TBL_INSCRITOS.xlsx" not in fk_src
    assert '("CI", "CARNET", "CEDULA"' not in fk_src
    ext_src = Path("backend/routers/dataops/extraccion.py").read_text(encoding="utf-8")
    assert 'claves_nota = ["NOTA_FINAL"' not in ext_src
    assert 'claves_asist = ["ASISTENCIA"' not in ext_src


def test_df_l7_dd3_enmascaramiento_nombre():
    assert _enmascarar_nombre("Juan Perez") == "J•••• P••••"
    assert _enmascarar_nombre("") == "••••"


def test_df_l11_fixtures_heterogeneas():
    from routers.dataops.extraccion import extract_entities_from_line
    base = Path("tests/fixtures/fuentes_sinteticas")
    for nombre in ("texto_libre_largo.csv", "hoja_sin_cabecera.csv", "columnas_otro_orden.csv"):
        contenido = (base / nombre).read_text(encoding="utf-8")
        for linea in contenido.splitlines():
            if not linea.strip():
                continue
            ents, score, req_rev = extract_entities_from_line(linea, [], [], [])
            assert isinstance(ents, list)
            assert 0.0 <= float(score) <= 1.0
