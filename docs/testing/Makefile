# ==============================================================================
# docs/testing/Makefile
# ---------------------
# Automatización estandarizada de pruebas dockerizadas para GiraGroup BI System.
# Diseñado para ejecutar comandos reproducibles dentro de los contenedores Docker
# garantizando aislamiento de SMTP y base de datos de pruebas.
# ==============================================================================

SHELL := /bin/bash
COMPOSE := docker compose
COMPOSE_FALLBACK := docker-compose
EXEC_PIPELINE := docker compose exec -e APP_ENV=test -e EMAIL_BACKEND=console -e DATABASE_URL="postgresql+psycopg2://giragroup_user:giragroup_secret_2026@giragroup_db:5432/giragroup_db" -e CATALOG_DATABASE_URL="postgresql+psycopg2://giragroup_user:giragroup_secret_2026@catalog_db:5432/giragroup_catalog_db" pipeline
EXEC_API := docker compose exec -e APP_ENV=test -e EMAIL_BACKEND=console -e PYTHONPATH=/app api

.PHONY: help test-unit test-integration test-pipeline test-api test-e2e test-all coverage clean

help:
	@echo "=================================================================="
	@echo "  GIRAGROUP BI SYSTEM - AUTOMATIZACIÓN DE PRUEBAS (QA/DevOps)"
	@echo "=================================================================="
	@echo "  make test-unit         : Ejecuta pruebas unitarias (sin BD ni red)"
	@echo "  make test-integration  : Pruebas de integración con PostgreSQL"
	@echo "  make test-pipeline     : Pruebas del motor BETO y PLN (incluye marcas slow)"
	@echo "  make test-api          : Pruebas de API y endpoints REST (httpx/FastAPI)"
	@echo "  make test-e2e          : Pruebas end-to-end y readiness de producción"
	@echo "  make test-all          : Ejecuta la suite completa de pruebas"
	@echo "  make coverage          : Genera reporte de cobertura con pytest-cov"
	@echo "=================================================================="

test-unit:
	@echo "==> [1/6] Ejecutando pruebas unitarias puras (sin BD/red)..."
	$(EXEC_PIPELINE) pytest tests/sprint2/ tests/sprint3/test_area2_confianza_telemetria.py tests/sprint3/test_area3_normalizacion_matching_fk.py tests/sprint3/test_formatter_gira40.py tests/sprint4/test_anonimizacion.py tests/test_cedula_prefijo_ci.py tests/test_fecha_corte_moodle.py -v -m "not slow" --tb=short

test-integration:
	@echo "==> [2/6] Ejecutando pruebas de integración con PostgreSQL (Constelación + Catálogos)..."
	$(EXEC_PIPELINE) pytest tests/sprint1/test_esquema_constelacion_hefesto.py tests/sprint1/test_modelos_orm_sqlalchemy.py tests/sprint3/test_catalogos_db.py tests/sprint3/test_cross_source_reconciliation.py tests/sprint3/test_financial_catalog_matching.py tests/sprint4/test_alert_engine.py tests/sprint4/test_dw_loader.py tests/sprint4/test_kpis_and_catalogs.py tests/test_kpi_service.py tests/test_risk_service.py tests/test_rentabilidad_ejecutado_meta.py -v --tb=short

test-pipeline:
	@echo "==> [3/6] Ejecutando pruebas del pipeline BETO NER y Analytics (incluyendo marcas slow)..."
	$(EXEC_PIPELINE) pytest tests/sprint3/test_ner_engine_gira10.py tests/sprint3/test_financial_rules_engine.py tests/sprint3/test_financial_validator.py tests/sprint3/test_financial_and_quality_post_steps.py tests/test_bandeja_hitl_ruido_y_un_clic.py -v --tb=short

test-api:
	@echo "==> [4/6] Ejecutando pruebas de API y endpoints REST en contenedor 'api'..."
	$(EXEC_API) pytest tests/test_otp_entorno_pruebas.py tests/test_email_redesign_and_forgot_password.py -v --tb=short

test-e2e:
	@echo "==> [5/6] Ejecutando pruebas de Readiness y verificación de producción..."
	$(EXEC_PIPELINE) pytest tests/readiness/test_production_readiness.py -v --tb=short -m "not readiness_live"

test-all: test-unit test-integration test-pipeline
	@echo "==> [6/6] Suite completa ejecutada exitosamente."

coverage:
	@echo "==> Generando informe de cobertura de código..."
	$(EXEC_PIPELINE) pytest tests/sprint2/ tests/sprint3/ tests/sprint4/ --cov=pipeline --cov-report=term-missing
