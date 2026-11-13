#!/usr/bin/env bash
# ==============================================================================
# docs/testing/test.sh
# ---------------------
# Script bash equivalente al Makefile para ejecución en entornos Linux/CI/WSL.
# ==============================================================================
set -euo pipefail

TARGET="${1:-help}"

EXEC_PIPELINE="docker compose exec -e APP_ENV=test -e EMAIL_BACKEND=console -e DATABASE_URL=postgresql+psycopg2://giragroup_user:giragroup_secret_2026@giragroup_db:5432/giragroup_db -e CATALOG_DATABASE_URL=postgresql+psycopg2://giragroup_user:giragroup_secret_2026@catalog_db:5432/giragroup_catalog_db pipeline"

case "$TARGET" in
  unit)
    echo "==> Ejecutando pruebas unitarias..."
    $EXEC_PIPELINE pytest tests/sprint2/ tests/sprint3/test_area2_confianza_telemetria.py tests/sprint3/test_area3_normalizacion_matching_fk.py tests/sprint3/test_formatter_gira40.py tests/sprint4/test_anonimizacion.py tests/test_cedula_prefijo_ci.py tests/test_fecha_corte_moodle.py -v -m "not slow" --tb=short
    ;;
  integration)
    echo "==> Ejecutando pruebas de integración..."
    $EXEC_PIPELINE pytest tests/sprint1/test_esquema_constelacion_hefesto.py tests/sprint1/test_modelos_orm_sqlalchemy.py tests/sprint3/test_catalogos_db.py tests/sprint3/test_cross_source_reconciliation.py tests/sprint3/test_financial_catalog_matching.py tests/sprint4/test_alert_engine.py tests/sprint4/test_dw_loader.py tests/sprint4/test_kpis_and_catalogs.py tests/test_kpi_service.py tests/test_risk_service.py tests/test_rentabilidad_ejecutado_meta.py -v --tb=short
    ;;
  pipeline)
    echo "==> Ejecutando pruebas BETO Pipeline..."
    $EXEC_PIPELINE pytest tests/sprint3/test_ner_engine_gira10.py tests/sprint3/test_financial_rules_engine.py tests/sprint3/test_financial_validator.py tests/sprint3/test_financial_and_quality_post_steps.py tests/test_bandeja_hitl_ruido_y_un_clic.py -v --tb=short
    ;;
  all)
    echo "==> Ejecutando toda la suite..."
    $EXEC_PIPELINE pytest tests/sprint2/ tests/sprint3/ tests/sprint4/ -v --tb=short
    ;;
  *)
    echo "Uso: ./test.sh [unit|integration|pipeline|all]"
    exit 1
    ;;
esac
