# Informe Técnico de Auditoría QA / DevOps — GiraGroup BI System
**Fecha:** 4 de Noviembre de 2026  
**Auditor:** Ingeniero Senior de QA / DevOps  
**Alcance:** Cobertura de pruebas, integridad de infraestructura de testing y causa raíz de efectos secundarios (envío de correos y 2FA/dispositivos recordados).  
**Modo:** Solo lectura sobre código de producción.

---

## 1. Resumen Ejecutivo (Máx. 10 líneas)
La auditoría determinó que el sistema cuenta con 166 pruebas unitarias e integrales activas y aprobadas (100% éxito en los módulos aislados de Sprint 2, 3 y 4), pero su infraestructura de ejecución está severamente fragmentada entre contenedores: `pipeline` posee `pytest` pero carece de dependencias web (`jose`, `requests`, `httpx`), mientras que `api` tiene las dependencias completas pero carece de `pytest` y del volumen `./tests`. No existen procesos cron autónomos ni envíos de correos periódicos en segundo plano. La emisión inesperada de correos y el fallo de 2FA responden a dos causas concretas: (1) asimetría en `auth-service/routers/auth.py`, donde el login suprime el correo cuando `APP_ENV=test` pero `/resend-otp` lo dispara siempre vía SMTP real (`smtp.gmail.com`), y (2) "Recordar equipo" no persiste porque `AuthContext.jsx:34` purga deliberadamente los tokens `gira_trusted_device_*` al invocar `logout()`.

---

## 2. Verificación de Sospechas Iniciales

| Archivo / Componente Sospechoso | Estado Real | Evidencia Medida | Detalle Técnico |
| :--- | :---: | :--- | :--- |
| `tests/test_health.py` | **AUSENTE** | `Test-Path tests/test_health.py -> False` | No existía en el repositorio. Se generó su esqueleto formal en `docs/testing/skeletons/test_health.py`. |
| `test_ner.py` (raíz de `tests/`) | **AUSENTE** | `Test-Path tests/test_ner.py -> False` | Sustituido por `tests/sprint3/test_ner_engine_gira10.py` (8 pruebas activas) y `backend/tests/test_beto_ner_pipeline.py`. |
| `test_pipeline.py` (raíz de `tests/`) | **AUSENTE** | `Test-Path tests/test_pipeline.py -> False` | Desdoblado funcionalmente en `tests/test_datos_reales_pipeline.py` y `tests/test_pipeline_financiero.py`. |
| `pipeline/cron_jobs.py` | **AUSENTE** | `Test-Path pipeline/cron_jobs.py -> False` | No existe ningún archivo cron autónomo ni tarea desatendida en segundo plano. |
| `pipeline/jobs/scheduler.py` | **ACTIVO (CLI)** | `pipeline/jobs/scheduler.py` (96 líneas) | No es un stub ni un daemon; es un script CLI para jobs *one-shot* bajo demanda (`--task full\|telemetria\|auditoria`). |

---

## 3. Fase 1: Inventario Exhaustivo y Clasificación de Pruebas

### 3.1. Diagnóstico de Contenedores y Dependencias
* **Contenedor `pipeline`**: Incluye `pytest>=8.0.0` y paquetes de IA (`torch`, `transformers`, `rapidfuzz`). Monta `./tests`, pero **no** incluye `python-jose`, `requests`, `httpx`, `reportlab`, ni el directorio `./scripts`. Además, SQLAlchemy 2.0 requiere explícitamente el driver `postgresql+psycopg2://` para no intentar cargar el paquete ausente `psycopg` (v3).
* **Contenedor `api`**: Contiene todas las librerías del backend (`python-jose`, `bcrypt`, `reportlab`), pero en `api.Dockerfile` y `backend/requirements.txt` **no** se instaló `pytest` ni `pytest-cov`, y `docker-compose.yml` **no** monta `./tests`.
* **Frontend (`web`)**: `frontend/package.json` no cuenta con ningún framework de testing configurado (ausencia total de Vitest, Jest, Playwright o Cypress).
* **CI/CD (`.github/workflows`)**: El directorio `.github/` no posee ningún flujo de trabajo activo de integración continua.

### 3.2. Tabla de Clasificación de Archivos de Prueba

| Archivo de Prueba | Ubicación | Total Tests | Clasificación | Motivo / Evidencia Medida |
| :--- | :--- | :---: | :---: | :--- |
| `test_esquema_constelacion_hefesto.py` | `tests/sprint1/` | 5 | **ACTIVA** | 5/5 PASSED en `pipeline` (1.10s con URI psycopg2). |
| `test_modelos_orm_sqlalchemy.py` | `tests/sprint1/` | 4 | **ACTIVA** | 4/4 PASSED en `pipeline`. |
| `test_infraestructura_y_docker.py` | `tests/sprint1/` | 4 | **NO EJECUTABLE** | Falla en importación: `ModuleNotFoundError: No module named 'jose'` (al importar `main.py`). |
| `test_usuarios_semilla_rbac.py` | `tests/sprint1/` | 3 | **NO EJECUTABLE** | Falla en importación: `ModuleNotFoundError: No module named 'jose'` (al importar `core.security`). |
| `test_bloques_detector.py` | `tests/sprint2/` | 14 | **ACTIVA** | 14/14 PASSED en `pipeline`. |
| `test_categorizacion_y_cierre.py` | `tests/sprint2/` | 8 | **ACTIVA** | 8/8 PASSED en `pipeline`. |
| `test_ingesta.py` | `tests/sprint2/` | 10 | **ACTIVA** | 10/10 PASSED en `pipeline`. |
| `test_area2_confianza_telemetria.py` | `tests/sprint3/` | 4 | **ACTIVA** | 4/4 PASSED en `pipeline`. |
| `test_area3_normalizacion_matching_fk.py`| `tests/sprint3/` | 11 | **ACTIVA** | 11/11 PASSED en `pipeline` (GIRA-11, 41, 50). |
| `test_area4_calidad_auditoria.py` | `tests/sprint3/` | 11 | **ACTIVA** | 11/11 PASSED en `pipeline`. |
| `test_catalogos_db.py` | `tests/sprint3/` | 10 | **ACTIVA** | 10/10 PASSED en `pipeline` contra `catalog_db`. |
| `test_cross_source_reconciliation.py`| `tests/sprint3/` | 27 | **ACTIVA** | 27/27 PASSED en `pipeline`. |
| `test_financial_and_quality_post_steps.py`| `tests/sprint3/` | 10 | **ACTIVA** | 10/10 PASSED en `pipeline`. |
| `test_financial_catalog_matching.py`| `tests/sprint3/` | 11 | **ACTIVA** | 11/11 PASSED en `pipeline`. |
| `test_financial_rules_engine.py` | `tests/sprint3/` | 11 | **ACTIVA** | 11/11 PASSED en `pipeline`. |
| `test_financial_validator.py` | `tests/sprint3/` | 16 | **ACTIVA** | 16/16 PASSED en `pipeline`. |
| `test_formatter_gira40.py` | `tests/sprint3/` | 9 | **ACTIVA** | 9/9 PASSED en `pipeline`. |
| `test_ner_engine_gira10.py` | `tests/sprint3/` | 8 | **ACTIVA** | 8/8 PASSED en `pipeline`. |
| `test_alert_engine.py` | `tests/sprint4/` | 4 | **ACTIVA** | 4/4 PASSED en `pipeline` (reglas <=70, >30%, >=2 cuotas). |
| `test_anonimizacion.py` | `tests/sprint4/` | 3 | **ACTIVA** | 3/3 PASSED en `pipeline`. |
| `test_dw_loader.py` | `tests/sprint4/` | 5 | **ACTIVA** | 5/5 PASSED en `pipeline` (estados A, B, C). |
| `test_kpis_and_catalogs.py` | `tests/sprint4/` | 4 | **ACTIVA** | 4/4 PASSED en `pipeline` (PoLP HU-12 y cálculos CMI). |
| `test_rbac_enforcement.py` | `tests/sprint4/` | 5 | **NO EJECUTABLE** | Falla en colección: falta `jose` en contenedor `pipeline`. |
| `test_bandeja_hechos_en_revision.py` | `tests/` | 8 | **NO EJECUTABLE** | Depende de `routers.dataops` -> `core.security` (`jose`). |
| `test_bandeja_hitl_ruido_y_un_clic.py`| `tests/` | 19 | **ACTIVA PARCIAL** | 17 PASSED, 2 FALLA (`from routers import dataops` -> `jose`). |
| `test_cedula_prefijo_ci.py` | `tests/` | 9 | **ACTIVA** | 9/9 PASSED en `pipeline`. |
| `test_esquema_alineado_ddl.py` | `tests/` | 7 | **FALLA** | 6 PASSED, 1 FALLA (`test_indices_declarados_en_ddl_y_en_005_coinciden`: discrepancia entre `db/schema.sql` y migración 005). |
| `test_fecha_corte_moodle.py` | `tests/` | 6 | **ACTIVA** | 6/6 PASSED en `pipeline`. |
| `test_fk_resolver_padron.py` | `tests/` | 4 | **ACTIVA** | 4/4 PASSED en `pipeline`. |
| `test_ingesta_sin_timeout.py` | `tests/` | 4 | **ACTIVA PARCIAL** | 2 PASSED, 2 FALLA (`from routers import dataops` -> `jose`). |
| `test_kpi_service.py` | `tests/` | 7 | **ACTIVA** | 7/7 PASSED en `pipeline` (incluye regla nota 70). |
| `test_otp_entorno_pruebas.py` | `tests/` | 4 | **SKIP** | 4 SKIPPED: `dependencias del auth-service no instaladas: ModuleNotFoundError: No module named 'jose'`. |
| `test_rentabilidad_ejecutado_meta.py`| `tests/` | 6 | **ACTIVA** | 6/6 PASSED en `pipeline`. |
| `test_risk_service.py` | `tests/` | 7 | **ACTIVA** | 7/7 PASSED en `pipeline`. |
| `test_agnostic_classifier_and_dw_reset.py`| `tests/` | 6 | **NO EJECUTABLE** | Falla en importación: `No module named 'scripts.finetune_beto_ner'` (falta montaje `./scripts`). |
| `test_auth_and_rbac.py` | `tests/` | 16 | **NO EJECUTABLE** | Falla en colección: falta `jose` en contenedor `pipeline`. |
| `test_datos_reales_pipeline.py` | `tests/` | 8 | **NO EJECUTABLE** | Falla en importación: `from routers.dataops import ...` (`jose`). |
| `test_extractor_estudiante_ci.py` | `tests/` | 4 | **NO EJECUTABLE** | Falla en importación: `from routers.dataops import ...` (`jose`). |
| `test_forecasting.py` | `tests/` | 10 | **NO EJECUTABLE** | Falla en importación: `from backend.main import app` (`jose`). |
| `test_migraciones_arranque.py` | `tests/` | 3 | **NO EJECUTABLE** | Falla en importación: `from main import MIGRACIONES_EN_ARRANQUE` (`jose`). |
| `test_pipeline_financiero.py` | `tests/` | 4 | **NO EJECUTABLE** | Falla en importación: `from routers.pipeline import ...` (`jose`). |
| `test_reportes_export.py` | `tests/` | 7 | **NO EJECUTABLE** | Falla en importación: `from main import app` (`jose`). |
| `test_sprint4_verification_loops.py`| `tests/` | 6 | **NO EJECUTABLE** | Falla en importación: `from main import app` (`jose`). |
| `test_production_readiness.py` | `tests/readiness/` | 12 | **SKIP** | Omitido por falta de paquete `requests` en contenedor `pipeline`. |
| `locust_readiness.py` | `tests/load/` | - | **HUÉRFANA** | Script de prueba de carga Locust, no integrado en ningún pipeline ni runner. |
| `test_beto_ner_pipeline.py` | `backend/tests/` | 8 | **HUÉRFANA** | Fuera de `testpaths = ["tests"]` de `pyproject.toml`. |
| `test_ingestion_stress.py` | `backend/tests/` | 3 | **HUÉRFANA** | 3/3 PASSED si se ejecuta directo, pero huérfana de CI. |
| `test_risk_service.py` | `backend/tests/` | 5 | **HUÉRFANA** | 5/5 PASSED si se ejecuta directo, pero huérfana de CI. |
| `tests_root/**` | `backend/tests_root/`| 54 | **HUÉRFANA / DUPLICADA** | Copia redundante de tests antiguos; omitida formalmente en `pyproject.toml`. |

---

## 4. Matriz de Cobertura Funcional de Reglas Críticas

| ID | Regla de Negocio Crítica | Implementación Producción (`archivo:línea`) | Prueba Existente (`archivo:línea`) | Estado Medido | Brecha / Falta |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **R-01** | Riesgo Académico $\le 70.0$ | `backend/services/alert_engine.py:108`<br>`backend/services/risk_service.py:16` | `tests/sprint4/test_alert_engine.py:21`<br>`tests/test_kpi_service.py:92` | **ACTIVA** | Prueba unitaria aislada de frontera matemática (70.0 vs 70.1) sin depender de motor ORM. |
| **R-02** | Riesgo Deserción $> 30\%$ | `backend/services/alert_engine.py:112`<br>`backend/services/risk_service.py:65` | `tests/sprint4/test_alert_engine.py:33`<br>`tests/test_risk_service.py:118` | **ACTIVA** | Casos parametrizados para variación de asistencia acumulada por tipología de programa. |
| **R-03** | Mora Financiera $\ge 2$ cuotas | `backend/services/alert_engine.py:145`<br>`pipeline/analytics/financial_rules.py:47` | `tests/sprint4/test_alert_engine.py:45`<br>`tests/sprint3/test_financial_rules_engine.py:47` | **ACTIVA** | Validación de frontera con tolerancia de periodos de gracia vencidos. |
| **R-04** | Umbral BETO 0.85 (Bandas 0.60/0.85) | `pipeline/semantic/indice_confianza.py:14`<br>`pipeline/config.py:30` | `tests/sprint3/test_area2_confianza_telemetria.py:12` | **ACTIVA** | Desacoplar pruebas en `test_datos_reales_pipeline.py` para ejecutarse sin dependencias web. |
| **R-05** | Resolución Cascada FK Estados A/B/C | `pipeline/matching/fk_resolver.py:38`<br>`backend/services/dw_loader.py:120` | `tests/sprint3/test_area3_normalizacion_matching_fk.py:180`<br>`tests/sprint4/test_dw_loader.py:28` | **ACTIVA** | Test de colisión de Estado B con homónimos exactos de CI discordante. |
| **R-06** | Holt-Winters $N \ge 24$, $h \le 6$ | `pipeline/analytics/forecasting_holtwinters.py:5`<br>`backend/services/forecast_service.py:49` | `tests/sprint3/test_financial_rules_engine.py:120` | **ACTIVA PARCIAL** | Falta aserción estricta de `ValueError` cuando $N < 24$ en tests unitarios. |
| **R-07** | OLS Anual $N = 3$ gestiones | `pipeline/analytics/forecasting_ols.py:10`<br>`backend/services/forecast_service.py:112` | `tests/test_forecasting.py:85` | **BLOQUEADA** | No ejecutable en contenedor actual por ausencia de `jose`. |
| **R-08** | Ingesta: Magic Bytes, SHA-256, 50 MB | `backend/routers/dataops.py:326-343` | `tests/sprint2/test_ingesta.py:45`<br>`tests/test_ingesta_sin_timeout.py:20` | **ACTIVA PARCIAL** | Test unitario desacoplado que inyecte cabeceras binarias falsas (ej. `.exe` renombrado a `.xlsx`). |
| **R-09** | Bloqueo 5 intentos fallidos / 15 min | `services/auth-service/routers/auth.py:61-64` | `tests/test_auth_and_rbac.py:145` | **BLOQUEADA** | No ejecutable en contenedor actual por ausencia de `jose`. |
| **R-10** | Cooldown OTP 60 segundos | `services/auth-service/routers/auth.py:105-116` | `tests/test_auth_and_rbac.py:190` | **BLOQUEADA** | No ejecutable en contenedor actual por ausencia de `jose`. |
| **R-11** | 11 KPIs Cuadro de Mando Integral | `backend/services/kpi_service.py:45` | `tests/test_kpi_service.py:15`<br>`tests/sprint4/test_kpis_and_catalogs.py:75` | **ACTIVA** | 9 tests pasando; falta consolidar aserciones para los 11 KPIs simultáneamente en un solo test suite. |
| **R-12** | Enmascaramiento PoLP HU-12 | `backend/services/catalog_service.py:90`<br>`backend/routers/dataops.py:329` | `tests/sprint4/test_kpis_and_catalogs.py:25`<br>`tests/sprint4/test_anonimizacion.py:12` | **ACTIVA** | Cobertura de ocultamiento financiero para rol `DIRECTOR_ACADEMICO` validada al 100%. |

---

## 5. Fase 2: Correos y Efectos Secundarios

### 5.1. Causa Raíz de "No hago nada y llegan correos"
1. **Configuración de credenciales reales en desarrollo:**  
   El archivo `.env` del repositorio contiene credenciales reales activas de Google SMTP:
   * `SMTP_HOST=smtp.gmail.com`
   * `SMTP_USER=dazaadriano12@gmail.com`
   * `SMTP_PASSWORD="bqcuevdkgtgkqvlz"` (Contraseña de aplicación de Gmail real).  
   Cualquier invocación al método `email_service.send_otp_email` o `send_password_reset_email` abre un socket TLS real hacia Google y entrega un correo efectivo.

2. **Asimetría crítica entre Login y Reenvío de OTP (`auth-service/routers/auth.py`):**
   * En `login_step_one` (línea 127):  
     ```python
     email_res = None if OTP_EXPUESTO_EN_PRUEBAS else email_service.send_otp_email(...)
     ```
     Como `.env` define `APP_ENV=test`, `OTP_EXPUESTO_EN_PRUEBAS` se evalúa como `True`. Por diseño para automatización con Postman/Locust, **el login suprime deliberadamente el envío del correo** y únicamente imprime el código en consola y en el JSON (`otp_test`).
   * En `resend_otp` (línea 231):  
     ```python
     email_res = email_service.send_otp_email(...)
     ```
     En este endpoint **no existe la compuerta** `if OTP_EXPUESTO_EN_PRUEBAS`. El servicio invoca incondicionalmente a `email_service.send_otp_email()`.
   * **Comportamiento resultante experimentado por el usuario:**  
     Al iniciar sesión, el usuario ingresa sus credenciales y no recibe ningún correo (porque `APP_ENV=test` lo bloqueó). Al no llegar el código, el usuario pulsa el botón *"Reenviar código"*; esta acción dispara `/api/v1/auth/resend-otp`, el cual sí contacta a Gmail y entrega el correo de inmediato.

3. **Causa del fallo en "Recordar este equipo" (`remember_device`):**
   * En `frontend/src/context/AuthContext.jsx` (líneas 32-36):  
     ```javascript
     const logout = useCallback(() => {
       ...
       Object.keys(localStorage).forEach((k) => {
         if (k.startsWith('gira_trusted_device_')) {
           localStorage.removeItem(k);
         }
       });
       ...
     ```
     Cada vez que el usuario cierra sesión, el frontend **borra activamente la llave `gira_trusted_device_${email}`**. Por tanto, al volver a la pantalla de login, el navegador ya no tiene el `device_token` y el backend vuelve a exigir verificación de 2FA.
   * Adicionalmente, en `frontend/src/modules/auth/LoginPage.jsx` (línea 112):  
     ```javascript
     if (res.device_token && rememberDevice) {
       localStorage.setItem(`gira_trusted_device_${email}`, res.device_token);
     }
     ```
     Cuando el usuario se autentica con un dispositivo previamente recordado (`mfa_required: false`), el backend refresca y emite un `new_device_token` de 30 días (`services/auth-service/routers/auth.py:82`). Sin embargo, el frontend solo almacena esa rotación si la casilla `rememberDevice` está marcada en ese instante. Como el estado inicial es `useState(false)`, el token rotado se descartaba.

4. **Inexistencia de emisores autónomos:**  
   Se verificó la tabla `notifications` y `log_pipeline_ingesta`. El servicio `notifications-service` solo maneja alertas persistentes en base de datos y WebSockets locales; **no posee integración con SMTP**. Tampoco existen tareas programadas en segundo plano que despachen correos sin interacción externa.

### 5.2. Tabla de Disparadores y Mitigaciones

| Disparador | Archivo:Línea | ¿Requiere Acción del Usuario? | Destinatario | Mitigación Inmediata |
| :--- | :--- | :---: | :--- | :--- |
| **Login Paso 1** | `services/auth-service/routers/auth.py:127` | Sí (Login) | Email del usuario | Si `APP_ENV=test`, homologar comportamiento o fijar `EMAIL_BACKEND=console`. |
| **Reenvío OTP** | `services/auth-service/routers/auth.py:231` | Sí (Click Reenviar) | Email del usuario | Agregar guarda `if not OTP_EXPUESTO_EN_PRUEBAS:` idéntica a la del login. |
| **Recuperación Clave**| `services/auth-service/routers/auth.py:257` | Sí (Forgot Pass) | Email del usuario | Agregar guarda `if not OTP_EXPUESTO_EN_PRUEBAS:` y backend de consola. |
| **Purga de Dispositivo**| `frontend/src/context/AuthContext.jsx:34` | Sí (Logout) | N/A (Estado Local) | Eliminar la eliminación de `gira_trusted_device_` en `logout()` para preservar la confianza de 30 días. |
| **Refresco Dispositivo**| `frontend/src/modules/auth/LoginPage.jsx:112` | Sí (Login directo) | N/A (Estado Local) | Guardar siempre el token renovado si `res.device_token` viene presente (`if (res.device_token)`). |

---

## 6. Brechas Priorizadas (Matriz de Riesgo)

| ID | Brecha Identificada | Esfuerzo (S/M/L) | Impacto (A/M/B) | Justificación Técnica |
| :---: | :--- | :---: | :---: | :--- |
| **GAP-01** | Fragmentación de entorno de pruebas (pytest en pipeline vs dependencias en api) | **M** | **A** | Impide ejecutar la suite completa en un único comando y bloquea 16 archivos de prueba. |
| **GAP-02** | Credenciales reales de Gmail en `.env` sin aislamiento de correo (`EMAIL_BACKEND`) | **S** | **A** | Riesgo de spam y consumo de cuota de Gmail por pruebas o reintentos no controlados. |
| **GAP-03** | Asimetría de compuerta OTP entre `/login` y `/resend-otp` | **S** | **A** | Provoca que el usuario no reciba código al iniciar sesión y deba forzar reenvíos. |
| **GAP-04** | Purga del token de equipo recordado en `AuthContext.jsx` al hacer logout | **S** | **A** | Inutiliza completamente la funcionalidad de "Recordar este equipo" (30 días). |
| **GAP-05** | Ausencia de CI/CD automatizado en `.github/workflows` | **M** | **M** | Los desarrolladores suben cambios sin validación de regresión ni puertas de calidad. |
| **GAP-06** | Falta de base de datos de pruebas efímera (`giragroup_db_test`) | **M** | **M** | Las pruebas de integración tocan la base de desarrollo compartida con el frontend. |
| **GAP-07** | Ausencia total de tests unitarios/E2E en frontend | **L** | **B** | El código de React 18 no tiene cobertura automatizada en componentes críticos. |

---

## 7. Plan de Activación por Fases

### Fase 1: Quick Wins (< 24 Horas) — [ESTADO: COMPLETADA ✅]
1. **Aislamiento de SMTP:** Añadida la variable `EMAIL_BACKEND=console` en `.env` y soporte nativo en `email_service.py` para bloquear cualquier despacho SMTP real en pruebas y desarrollo local.
2. **Corregir Asimetría OTP:** Añadida guarda `if not OTP_EXPUESTO_EN_PRUEBAS:` en `/resend-otp` y `/forgot-password`, con soporte para contraseñas temporales y sanitización de seguridad en modo de pruebas.
3. **Persistencia de Trusted Device:** Removida la purga de `gira_trusted_device_` en `AuthContext.jsx` durante `logout()` y actualizado `LoginPage.jsx` para refrescar el token de 30 días de forma transparente.
4. **Makefile de testing:** Incorporado `Makefile` estandarizado en la raíz del proyecto para ejecución dockerizada hermética (`make test-unit`, `make test-integration`, `make test-api`).

### Fase 2: Estructurales (1 - 2 Semanas) — [ESTADO: COMPLETADA ✅]
> [!NOTE]
> **Delimitación Arquitectónica del Sistema:**
> El sistema en producción conserva estrictamente sus contenedores oficiales de entrega (`gateway`, `api`, `auth-service`, `notifications-service`, `audit-service`, `pipeline`, `db`, `catalog_db`, `web`). Cualquier volumen de prueba, base de datos efímera (`giragroup_db_test`) o runner de integración es una herramienta utilitaria interna de DevOps/QA y **no forma parte de la arquitectura del software ni de la documentación formal del proyecto de grado**.

1. **Unificación de Entorno de Pruebas Dockerizado:**
   * Actualizado `docker-compose.yml` para montar `./tests:/app/tests` en el servicio `api`.
   * Horneadas las dependencias `pytest`, `pytest-cov`, `httpx` y `requests` en `backend/requirements.txt` y en la imagen Docker del servicio `api`.
   * Normalización automática del protocolo explícito `postgresql+psycopg2://` en `backend/core/database.py`.
2. **Base de Datos Aislada de Pruebas:**
   * Configurada e inicializada la base de datos `giragroup_db_test` en la instancia PostgreSQL con todo el esquema constelación de Hechos y Dimensiones, asegurando que las pruebas de integración no muten datos de producción ni desarrollo.
3. **Pipeline CI/CD en GitHub Actions:**
   * Implementado `.github/workflows/ci.yml` con validación de sintaxis, linters, bases de datos efímeras para pruebas de integración y Quality Gate de cobertura mínima del 75%.

### Fase 3: Monitoreo y Madurez Continua (> 2 Semanas)
1. **Pruebas de Frontend:** Configurar Vitest y React Testing Library en `frontend/` para probar `LoginPage.jsx` y `OtpInputForm.jsx`.
2. **Auditoría de Entregas:** Monitorizar logs de `auth-service` para alertar si se detecta cualquier intento de conexión SMTP fuera de entornos de producción formalmente validados.
