# ADR-RV2-01: Esquema `app` para KPI y Gráficas Personalizadas sin Alterar Invariantes

- **Estado:** Aceptado (Decisiones D3, D4, D6 de `REESTRUCTURACION_VISTA_V2.md`)
- **Fecha:** 2026-11-20

## Contexto
El Cuadro de Mando Integral debe permitir a `ADMIN`, `ANALISTA_FINANCIERO` (solo `FINANCIERA`) y `ANALISTA_MARKETING` (solo `CLIENTES`) crear indicadores personalizados (`KPP-nn`) y gráficas personalizadas sin alterar los invariantes de la tesis:
- **51 tablas** en `public` + `bi`
- **10 vistas** en `bi`
- **23 KPI oficiales** en `bi.ref_kpi` y el índice global ponderado

## Decisión
1. **Esquema `app` separado:** Se crea el esquema `app` (fuera de `public` y `bi`) mediante la migración idempotente `021_esquema_app_personalizacion.sql`:
   - `app.medida_catalogo`: lista blanca cerrada de medidas sobre vistas `bi` y hechos `fact_*` con dimensiones permitidas **sin PII** (`dim_estudiante` y columnas de nombre, CI, correo o teléfono quedan excluidas).
   - `app.kpi_personalizado`: indicadores `KPP-nn` vinculados a `app.medida_catalogo`, evaluados fuera de `bi.ref_kpi` y del índice global.
   - `app.grafico_personalizado`: definiciones de gráficas (medida, dimensión, agregación, tipo, perspectiva destino, auditoría).
2. **Motor de consulta seguro:** El backend construye SQL únicamente con identificadores de `app.medida_catalogo`, ejecutado bajo `SET LOCAL TRANSACTION READ ONLY`, `statement_timeout = '5000'` (timeout → HTTP 504), `LIMIT 500`, agregación obligatoria (`SUM`, `AVG`, `COUNT`, `COUNT_DISTINCT`, `MIN`, `MAX`), ocultamiento de grupos con `n < 5` (`"< 5"`), y caché de 60 s.
3. **RBAC por perspectiva:** `ADMIN` edita todo; `ANALISTA_FINANCIERO` solo `FINANCIERA`; `ANALISTA_MARKETING` solo `CLIENTES`; `DIRECTOR_ACADEMICO` y `AUDITOR_CALIDAD` solo lectura (HTTP 403 en mutaciones).

## Consecuencias
- Los scripts `diccionario_datos_csv.py` e `inventario_tablas*.py` siguen filtrando `public` + `bi`, manteniendo 51 / 10 / 23 intactos.
- Nunca se ejecuta SQL libre del usuario.
