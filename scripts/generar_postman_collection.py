"""
scripts/generar_postman_collection.py
Genera la coleccion oficial de Postman v2.1.0 para pruebas de caja negra automatizadas
con Newman segun la Tabla 3.24 de la tesis de grado.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / "docs" / "postman_collection.json"

collection = {
    "info": {
        "_postman_id": "c8f9b4a1-8d23-4e8a-bf92-e30a597d8e20",
        "name": "GiraGroup BI - Pruebas de Caja Negra (Tabla 3.24)",
        "description": "Suite automatizada de verificacion funcional E2E y seguridad para API Gateway y Microservicios.",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "variable": [
        {"key": "baseUrl", "value": "http://localhost", "type": "string"},
        {"key": "temp_token", "value": "", "type": "string"},
        {"key": "access_token", "value": "", "type": "string"},
        # Usuario semilla de QA (backend/seed_users.py, solo APP_ENV=test). La contraseña se pasa al
        # ejecutar: newman run ... --env-var qa_password=<QA_ADMIN_PASSWORD de .env> (no se versiona).
        {"key": "qa_email", "value": "qa.admin@giragroup.bo", "type": "string"},
        {"key": "qa_password", "value": "", "type": "string"},
        {"key": "otp_code", "value": "", "type": "string"}
    ],
    "item": [
        {
            "name": "1. Health Check Gateway & API",
            "request": {
                "method": "GET",
                "header": [],
                "url": {
                    "raw": "{{baseUrl}}/health",
                    "host": ["{{baseUrl}}"],
                    "path": ["health"]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Status code es 200 OK', function () { pm.response.to.have.status(200); });",
                            "pm.test('Servicio reporta estado saludable', function () {",
                            "    var json = pm.response.json();",
                            "    pm.expect(json.status).to.eql('healthy');",
                            "    pm.expect(json.database).to.eql('connected');",
                            "});",
                            "pm.test('Cabeceras OWASP presentes', function () {",
                            "    pm.response.to.have.header('x-content-type-options');",
                            "    pm.response.to.have.header('x-frame-options');",
                            "});"
                        ]
                    }
                }
            ]
        },
        {
            "name": "2. Auth - Paso 1: Login Credenciales",
            "request": {
                "method": "POST",
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"email\": \"{{qa_email}}\",\n    \"password\": \"{{qa_password}}\"\n}"
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/auth/login",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "auth", "login"]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Status code es 200 OK', function () { pm.response.to.have.status(200); });",
                            "var json = pm.response.json();",
                            "if (json.mfa_required) {",
                            "    pm.test('Requiere 2FA OTP', function () { pm.expect(json.temp_token).to.be.a('string'); });",
                            "    pm.collectionVariables.set('temp_token', json.temp_token);",
                            "    pm.test('OTP de pruebas disponible (APP_ENV=test)', function () { pm.expect(json.otp_test).to.match(/^[0-9]{6}$/); });",
                            "    pm.collectionVariables.set('otp_code', json.otp_test);",
                            "} else {",
                            "    pm.test('Login directo con token de acceso', function () { pm.expect(json.access_token).to.be.a('string'); });",
                            "    pm.collectionVariables.set('access_token', json.access_token);",
                            "}"
                        ]
                    }
                }
            ]
        },
        {
            "name": "3. Auth - Paso 2: Verificacion 2FA OTP",
            "request": {
                "method": "POST",
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"temp_token\": \"{{temp_token}}\",\n    \"code\": \"{{otp_code}}\",\n    \"remember_device\": true\n}"
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/auth/verify-otp",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "auth", "verify-otp"]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Status code es 200 OK', function () { pm.response.to.have.status(200); });",
                            "var json = pm.response.json();",
                            "pm.test('Retorna access_token valido', function () { pm.expect(json.access_token).to.be.a('string'); });",
                            "pm.collectionVariables.set('access_token', json.access_token);"
                        ]
                    }
                }
            ]
        },
        {
            "name": "4. KPIs - Cuadro de Mando Integral Completo",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{access_token}}"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/kpis/cmi-completo",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "kpis", "cmi-completo"]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Status code es 200 OK', function () { pm.response.to.have.status(200); });",
                            "var json = pm.response.json();",
                            "pm.test('Estructura contiene 4 perspectivas CMI', function () {",
                            "    pm.expect(json.perspectivas).to.have.property('financiera');",
                            "    pm.expect(json.perspectivas).to.have.property('cliente_mercado');",
                            "    pm.expect(json.perspectivas).to.have.property('procesos_internos');",
                            "    pm.expect(json.perspectivas).to.have.property('aprendizaje_crecimiento');",
                            "});"
                        ]
                    }
                }
            ]
        },
        {
            "name": "5. Riesgos - Alertas Tempranas Deterministicas",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{access_token}}"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/riesgos/alertas-tempranas",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "riesgos", "alertas-tempranas"]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Status code es 200 OK', function () { pm.response.to.have.status(200); });",
                            "var json = pm.response.json();",
                            "pm.test('Respuesta contiene tarjetas de riesgo y reglas', function () {",
                            "    pm.expect(json.status).to.eql('success');",
                            "    pm.expect(json.tarjetas).to.have.property('riesgo_academico');",
                            "    pm.expect(json.tarjetas).to.have.property('riesgo_desercion');",
                            "    pm.expect(json.tarjetas).to.have.property('riesgo_financiero');",
                            "    pm.expect(json.tarjetas).to.have.property('alerta_critica');",
                            "});"
                        ]
                    }
                }
            ]
        },
        {
            "name": "6. Forecast - Proyeccion de Inscritos (Holt-Winters)",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{access_token}}"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/forecast/alumnos",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "forecast", "alumnos"]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Status code es 200 OK', function () { pm.response.to.have.status(200); });",
                            "var json = pm.response.json();",
                            "pm.test('Modelo Holt-Winters valido con horizonte de proyeccion', function () {",
                            "    pm.expect(json.data.metodo).to.include('HoltWinters');",
                            "    pm.expect(json.data.proyecciones).to.be.an('array');",
                            "    pm.expect(json.data).to.have.property('rmse');",
                            "});"
                        ]
                    }
                }
            ]
        },
        {
            "name": "7. Forecast - Proyeccion de Recaudacion (OLS Metas)",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{access_token}}"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/forecast/metas",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "forecast", "metas"]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Status code es 200 OK', function () { pm.response.to.have.status(200); });",
                            "var json = pm.response.json();",
                            "pm.test('Modelo de metas y recaudacion valido', function () {",
                            "    pm.expect(json.data.metodo).to.include('HoltWinters');",
                            "    pm.expect(json.data.proyecciones).to.be.an('array');",
                            "    pm.expect(json.data).to.have.property('rmse');",
                            "});"
                        ]
                    }
                }
            ]
        },
        {
            "name": "8. Reportes - Exportacion XLSX (HU-12)",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{access_token}}"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/reportes/export?tipo=kpis&formato=xlsx",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "reportes", "export"],
                    "query": [
                        {"key": "tipo", "value": "kpis"},
                        {"key": "formato", "value": "xlsx"}
                    ]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Status code es 200 OK', function () { pm.response.to.have.status(200); });",
                            "pm.test('Content-Type corresponde a Excel XLSX', function () {",
                            "    pm.expect(pm.response.headers.get('content-type')).to.include('openxmlformats');",
                            "});"
                        ]
                    }
                }
            ]
        },
        {
            "name": "9. Reportes - Exportacion PDF (HU-12)",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{access_token}}"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/reportes/export?tipo=alertas&formato=pdf",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "reportes", "export"],
                    "query": [
                        {"key": "tipo", "value": "alertas"},
                        {"key": "formato", "value": "pdf"}
                    ]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Status code es 200 OK', function () { pm.response.to.have.status(200); });",
                            "pm.test('Content-Type corresponde a application/pdf', function () {",
                            "    pm.expect(pm.response.headers.get('content-type')).to.include('pdf');",
                            "});"
                        ]
                    }
                }
            ]
        },
        {
            "name": "10. Seguridad - Caso 401 Unauthorized",
            "request": {
                "method": "GET",
                "header": [],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/kpis/cmi-completo",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "kpis", "cmi-completo"]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Status code es 401 Unauthorized sin token', function () { pm.response.to.have.status(401); });",
                            "pm.test('Encabezado WWW-Authenticate presente', function () {",
                            "    pm.response.to.have.header('www-authenticate');",
                            "});"
                        ]
                    }
                }
            ]
        },
        {
            "name": "11. Seguridad - Caso 422 Validacion de Esquema",
            "request": {
                "method": "POST",
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": {
                    "mode": "raw",
                    "raw": "{}"
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/auth/login",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "auth", "login"]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Status code es 422 Unprocessable Entity', function () { pm.response.to.have.status(422); });",
                            "var json = pm.response.json();",
                            "pm.test('Detalle de validacion Pydantic retornado', function () {",
                            "    pm.expect(json).to.have.property('detail');",
                            "    pm.expect(json.detail).to.be.an('array');",
                            "});"
                        ]
                    }
                }
            ]
        }
    ]
}

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)

print(f"Coleccion de Postman generada exitosamente en: {OUTPUT_FILE}")
