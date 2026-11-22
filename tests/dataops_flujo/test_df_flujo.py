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


def test_df_l2_r4_precarga_desde_raw_y_sin_lectura_por_que():
    from types import SimpleNamespace
    from services.revision_consulta import caso_guardado

    ent = SimpleNamespace(
        id_staging=12081,
        id_documento=54,
        tipo_entidad="ESTUDIANTE",
        motivo="BAJA_CONFIANZA",
        nivel_confianza=0.0,
        score_fuzzy=0.0,
        mejor_candidato=None,
        ci_temporal=None,
        texto_original="Nombre Completo: Juan Perez | Programa: POS-5310 | Módulo: 1",
        estado_resolucion="PENDIENTE",
        lock_usuario_id=None,
        lock_expira=None,
        resuelto_en=None,
        payload_json={"motivo_llano": "Índice del registro (0) inferior al umbral de pase directo (85)."},
    )
    doc = SimpleNamespace(id_documento=54, tipo_fuente="EVALUACION_DOCENTE", nombre_archivo="libro_4.xlsx")
    caso = caso_guardado(ent, doc, db=None, rol_usuario="ADMIN")
    assert caso["motivo"] == "SIN_LECTURA"
    assert "índice del registro (0)" not in caso["por_que_detuvo"].lower()
    assert caso["programa"] == "POS-5310"
    assert caso["numero_modulo"] == 1
    assert caso["acciones"][0]["precarga"]["programa"] == "POS-5310"
    assert caso["acciones"][0]["precarga"]["numero_modulo"] == 1


def test_df_l2_dim_models_fields_en_ejecutor_y_rapidfuzz():
    from models.dim_estudiante import DimEstudiante
    from models.dim_modulo import DimModulo
    from pathlib import Path

    assert hasattr(DimEstudiante, "ci")
    assert hasattr(DimEstudiante, "programa_origen")
    assert not hasattr(DimEstudiante, "ci_nit")
    assert hasattr(DimModulo, "pos_code")
    assert not hasattr(DimModulo, "codigo_pos")

    ej_src = Path("backend/services/revision_acciones_ejecutor.py").read_text(encoding="utf-8")
    rc_src = Path("backend/services/revision_consulta.py").read_text(encoding="utf-8")
    assert "ci_nit" not in ej_src
    assert "ci_nit" not in rc_src
    assert "programa_academico" not in rc_src
    assert "DimModulo(pos_code=" in ej_src
    assert "begin_nested()" in ej_src


def test_df_l4_lectura_acepta_page_size_20():
    lec_src = Path("backend/routers/dataops/lectura.py").read_text(encoding="utf-8")
    assert "Query(5, ge=1, le=5)" not in lec_src
    assert "Query(20, ge=1, le=50)" in lec_src
