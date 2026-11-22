"""Tests unitarios y de contrato para FU-L9 + ADW-L9 (M5, migraciones 022..028, riesgos, encuestas)."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]


def test_mapeo_yaml_y_json_sincronizados_con_extraccion():
    datos_yaml = yaml.safe_load((RAIZ / "config" / "mapeo_fuentes.yaml").read_text(encoding="utf-8"))
    datos_json = json.loads((RAIZ / "pipeline" / "mapeo_fuentes.json").read_text(encoding="utf-8"))
    assert datos_yaml == datos_json
    ext = datos_yaml.get("extraccion") or {}
    for clave in (
        "claves_ci", "claves_nombre_completo", "claves_nota",
        "claves_fecha_financiera", "claves_fecha_academica",
        "claves_mes", "claves_anio", "clave_descarga_moodle",
        "financieros", "no_estudiante", "palabras_no_estudiante",
        "atributos_estudiante", "roles",
    ):
        assert ext.get(clave), f"Falta extraccion.{clave} en config/mapeo_fuentes.yaml"


def test_m5_modulos_leen_desde_catalogo():
    from services import extraccion_por_encabezado as epe
    from routers import pipeline as rp
    from routers.dataops import extraccion as de

    assert "NOTA FINAL" in epe._CLAVES_NOTA
    assert "GESTION" in epe._CLAVES_ANIO
    assert "monto_deuda" in rp._ENCABEZADOS_FINANCIEROS
    assert "DEUDA TOTAL" in rp._ENCABEZADOS_FINANCIEROS["monto_deuda"]
    assert "ASESOR" in de._ENCABEZADOS_NO_ESTUDIANTE
    assert "NIT" in de._PALABRAS_NO_ESTUDIANTE
    assert "POS" in de._ENC_CODIGO_PROGRAMA
    assert "DEUDA TOTAL" in de._ENC_MONTO


def test_migraciones_022_a_028_registradas():
    from core.migraciones import MIGRACIONES_EN_ARRANQUE

    esperadas = [
        "022_fu_l2_cobranza_mora_da3.sql",
        "023_fu_l3_fact_marketing_documento.sql",
        "024_fu_l4_actas_resultado_desercion.sql",
        "025_fu_l5_encuestas_escala_da1.sql",
        "026_fu_l6_metas_granularidad.sql",
        "027_adw_l6_cmi_config.sql",
        "028_fu_l9_decisiones_lean.sql",
    ]
    for m in esperadas:
        assert m in MIGRACIONES_EN_ARRANQUE
        assert (RAIZ / "backend" / "scripts" / "migrations" / m).exists()


def test_migracion_028_contiene_decisiones_lean():
    sql = (RAIZ / "backend" / "scripts" / "migrations" / "028_fu_l9_decisiones_lean.sql").read_text(encoding="utf-8")
    assert "CREATE OR REPLACE VIEW bi.vw_riesgo_estudiante AS" in sql
    assert "UNION" in sql
    assert "f.recaudacion / NULLIF(f.pagantes, 0) AS valor" in sql
    assert "CASE WHEN COUNT(prom_notas) = 0 THEN NULL" in sql


def test_riesgos_router_tiene_resumen_vista():
    from routers import riesgos

    rutas = {r.path for r in riesgos.router.routes}
    assert "/api/v1/riesgos/resumen-vista" in rutas


def test_encuestas_sin_fecha_no_imputan_tiempo_del_programa():
    codigo = (RAIZ / "backend" / "services" / "dw_loader.py").read_text(encoding="utf-8")
    # En la sección de fact_evaluacion_docente no debe llamarse _tiempo_del_programa
    bloque = codigo[codigo.index("3c. Ruteo EVALUACION_DOCENTE"):codigo.index("3c. Ruteo EVALUACION_DOCENTE") + 4500]
    assert "_tiempo_del_programa" not in bloque
    assert "id_tiempo = None" in bloque
