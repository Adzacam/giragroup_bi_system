| Endpoint | ¿Lo usa el front? | ¿Coincide el contrato? | Pantalla afectada |
|---|---|---|---|
| GET /api/v1/alertas | sí | sí | Dashboards / CMI |
| GET /api/v1/audit/logs | sí | sí | Auditoría |
| POST /api/v1/auth/change-password | sí | sí (microservicio tras el gateway) | Login |
| POST /api/v1/auth/forgot-password | sí | sí (microservicio tras el gateway) | Login |
| POST /api/v1/auth/login | sí | sí | Login |
| POST /api/v1/auth/resend-otp | sí | sí (microservicio tras el gateway) | Login |
| POST /api/v1/auth/verify-otp | sí | sí (microservicio tras el gateway) | Login |
| GET /api/v1/catalogs/financial/concepts | sí | sí | Catálogos maestros / Cobranzas |
| GET /api/v1/catalogs/financial/cross-source-audit | sí | sí | Catálogos maestros / Cobranzas |
| GET /api/v1/catalogs/financial/cross-source-check/{} | sí | sí | Catálogos maestros / Cobranzas |
| POST /api/v1/catalogs/financial/detect-anomalies | sí | sí | Catálogos maestros / Cobranzas |
| POST /api/v1/catalogs/financial/evaluate-risk | sí | sí | Catálogos maestros / Cobranzas |
| POST /api/v1/catalogs/financial/match | sí | sí | Catálogos maestros / Cobranzas |
| POST /api/v1/catalogs/financial/resolve-student | sí | sí | Catálogos maestros / Cobranzas |
| POST /api/v1/catalogs/financial/validate-goal | sí | sí | Catálogos maestros / Cobranzas |
| POST /api/v1/catalogs/financial/validate-transaction | sí | sí | Catálogos maestros / Cobranzas |
| GET /api/v1/catalogs/institutional-summary | sí | sí | Catálogos maestros / Cobranzas |
| GET /api/v1/cmi/config | sí | sí | CMI web |
| PUT /api/v1/cmi/config/kpis/{} | sí | sí | CMI web |
| PUT /api/v1/cmi/config/perspectivas/{} | sí | sí | CMI web |
| GET /api/v1/cmi/scorecard | sí | sí | CMI web |
| GET /api/v1/dataops/PlainText/{} | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/catalogs | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/confirm-dw-insert | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/entities/unresolved | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/entities/{}/link | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/infer-beto | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/logs/{} | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/lote/{}/beto-reading | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/lote/{}/context | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/lote/{}/raw-vs-text | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/lote/{}/resumen | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/lote/{}/tarea | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/normalization-matrix/{} | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/plain-text-records | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/process-batch | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/process/{} | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/purge-staging-cache | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/rapidfuzz-compare | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/registro/{}/revelar-ci | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/review-tray | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/review-tray/approve-group | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/review-tray/aprobar-un-clic | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/review-tray/batch-resolve | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/review-tray/grupos | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/review-tray/{}/resolve | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/sources | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| DELETE /api/v1/dataops/sources/clear-completed | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/sources/delete-batch | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/sources/{} | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| DELETE /api/v1/dataops/sources/{} | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/tareas | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/tareas/{} | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/dataops/telemetry/summary | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/upload | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| POST /api/v1/dataops/upload-batch | sí | sí | DataOps (ingesta, lectura BETO, bandeja HITL) |
| GET /api/v1/docentes | sí | sí | Catálogos maestros / Cobranzas |
| POST /api/v1/docentes | sí | sí | Catálogos maestros / Cobranzas |
| DELETE /api/v1/docentes/{} | sí | sí | Catálogos maestros / Cobranzas |
| GET /api/v1/estudiantes | sí | sí | Catálogos maestros / Cobranzas |
| POST /api/v1/estudiantes | sí | sí | Catálogos maestros / Cobranzas |
| DELETE /api/v1/estudiantes/{} | sí | sí | Catálogos maestros / Cobranzas |
| GET /api/v1/forecast/alumnos | sí | sí | Proyecciones; Rendimiento y alertas |
| GET /api/v1/forecast/analitica-macro | sí | sí | Proyecciones |
| GET /api/v1/forecast/metas | sí | sí | Proyecciones |
| GET /api/v1/instituciones | sí | sí | Catálogos maestros / Cobranzas |
| GET /api/v1/kpis | sí | sí | Dashboards / CMI |
| GET /api/v1/kpis/academico | sí | sí | Dashboards / CMI |
| GET /api/v1/kpis/cmi-completo | sí | sí | Dashboards / CMI |
| GET /api/v1/kpis/financiero | sí | sí | Dashboards / CMI |
| GET /api/v1/kpis/pipeline | sí | sí | Dashboards / CMI |
| GET /api/v1/modulos | sí | sí | Catálogos maestros / Cobranzas |
| POST /api/v1/modulos | sí | sí | Catálogos maestros / Cobranzas |
| DELETE /api/v1/modulos/{} | sí | sí | Catálogos maestros / Cobranzas |
| GET /api/v1/notifications | sí | sí (microservicio tras el gateway) | Notificaciones |
| POST /api/v1/notifications/mark-all-read | sí | sí (microservicio tras el gateway) | Notificaciones |
| PATCH /api/v1/notifications/{}/read | sí | sí (microservicio tras el gateway) | Notificaciones |
| POST /api/v1/pipeline/process | sí | sí | Auditoría |
| GET /api/v1/powerbi/informe/versiones | sí | sí | CMI · Power BI |
| PUT /api/v1/powerbi/informe/versiones/{}/vigente | sí | sí | CMI · Power BI |
| GET /api/v1/reportes/export | sí | sí | Centro de reportes |
| GET /api/v1/reportes/historial | sí | sí | Centro de reportes |
| GET /api/v1/riesgos/alertas-tempranas | sí | sí | Rendimiento y alertas |
| GET /api/v1/riesgos/cruzado | sí | sí | Rendimiento y alertas |
| GET /api/v1/riesgos/ficha-estudiante/{} | sí | sí | Rendimiento y alertas |
| GET /api/v1/users | sí | sí (microservicio tras el gateway) | Gestión de usuarios |
| POST /api/v1/users | sí | sí (microservicio tras el gateway) | Gestión de usuarios |
| PUT /api/v1/users/{} | sí | sí (microservicio tras el gateway) | Gestión de usuarios |
| DELETE /api/v1/users/{} | sí | sí (microservicio tras el gateway) | Gestión de usuarios |
| POST /pipeline/process | sí | sí | Auditoría |
| DELETE /api/v1/catalogs/estados/combinaciones/{} | no | — | — |
| DELETE /api/v1/dataops/purge-staging-cache | no | — | — |
| GET / | no | — | — |
| GET /api/v1/catalogs/estados/combinaciones | no | — | — |
| GET /api/v1/estudiantes/{} | no | — | — |
| GET /api/v1/forecast/viabilidad-programas | no | — | — |
| GET /api/v1/kpis/costos-programa | no | — | — |
| GET /api/v1/kpis/techos-convenio | no | — | — |
| GET /api/v1/powerbi/informe | no | — | — |
| GET /api/v1/powerbi/informe/descargar | no | — | — |
| GET /health | no | — | — |
| PATCH /api/v1/dataops/review-tray/{}/resolve | no | — | — |
| POST /api/v1/catalogs/estados/combinaciones | no | — | — |
| POST /api/v1/dataops/review-tray/{}/lock | no | — | — |
| POST /api/v1/dataops/review-tray/{}/unlock | no | — | — |
| POST /api/v1/powerbi/informe | no | — | — |
