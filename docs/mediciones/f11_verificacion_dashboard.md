# Verificación de Dashboard, CMI, Proyecciones y Reportes (F11-2)

- **Fecha:** 2026-11-25
- **Entorno:** `http://localhost:5173` (`giragroup_web` + `giragroup_gateway` + `giragroup_api`), `Lote #1` limpio en `giragroup_db`
- **Viewport:** `1280x800` (modo claro y modo oscuro)

## 1. Verificación API (FastAPI + Proxy `:5173`)
- `GET /api/v1/cmi/scorecard`: `200 OK` (4 perspectivas, 23 KPIs)
- `GET /api/v1/cmi/resumen`: `200 OK` (`gestiones`, `global_por_gestion`, `perspectivas_por_gestion`)
- `GET /api/v1/forecast/alumnos`: `200 OK` (Holt-Winters `m=12` + OLS)
- `GET /api/v1/forecast/analitica-macro`: `200 OK`
- `GET /api/v1/reportes/export` (probado para los 5 roles en `kpis`, `alertas`, `cierre`): `200 OK`; a través de `:5173` en `.xlsx` (`55 669` bytes) y `.pdf` (`40 861` bytes).

## 2. Verificación Visual en Navegador (`/browser`)
| Ruta | Modo Claro | Modo Oscuro | Hallazgos / Datos visibles | Errores consola / HTTP >=400 |
|---|---|---|---|---|
| `/v2/dashboard` → `/dashboard` | PASS | PASS | Redirección automática a `/dashboard`; sin botón `V1` en el navbar | 0 / 0 |
| `/dashboard` | PASS | PASS | CMI `49.4 / 100`, 23 indicadores en 4 perspectivas, 7 alertas prioritarias | 0 / 0 |
| `/reportes` | PASS | PASS | Descarga `XLSX` (`200 OK`, `1255` filas, `700 ms`) y `PDF` (`200 OK`, `1255` filas, `970 ms`) con toast de confirmación y bitácora | 0 / 0 |
| `/academico/rendimiento` | PASS | PASS | Reglas IF/THEN, matrícula activa auditada `9 995` alumnos | 0 / 0 |
| `/financiero/recaudacion` | PASS | PASS | Recaudación neta `Bs. 5.695.043,78`, deuda total `Bs. 1,041,769.19`, 24 filas mensuales | 0 / 0 |
| `/academico/proyeccion` | PASS | PASS | Holt-Winters (`m=12`) + OLS (`3.5762 alumnos/mes`, MAPE `13.82%`, RMSE `48.8`), banda IC 95 % y 25 programas | 0 / 0 |
| `/dataops/ingesta` | PASS | PASS | Programas activos `1 227`, historial de lotes (`1`), flujo de 3 pasos | 0 / 0 |
