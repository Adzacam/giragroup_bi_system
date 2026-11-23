# Cierre parcial A0 — Inventario y trazabilidad

Fecha de trabajo: 2026-11-20. Rama `beto-integracion`, base Git `38e317f`. La lectura incluyó el árbol de trabajo local, que ya contenía cambios de la reestructuración del CMI.

| Tarea | Estado | Evidencia |
|---|---|---|
| A0-1. Inventario | Inventario estático de los componentes y rutas V1 y V2. Falta confirmar qué elementos se muestran por gestión y rol. | [aud_a0_elementos.csv](../mediciones/aud_a0_elementos.csv) |
| A0-2. Trazabilidad | Mapeo estático a endpoint, payload y origen. Las trazas que requieren confirmación se señalan en el CSV. | [aud_a0_trazabilidad.csv](../mediciones/aud_a0_trazabilidad.csv) |
| A0-3. Contexto | Fórmulas de los KPI base y fuentes de los cuatro casos predictivos. Pendiente de revisión por Lean. | [contexto_datos_cmi.md](../contexto_datos_cmi.md) |
| A0-4. Capturas | Bloqueado en esta sesión. El navegador no pudo confirmar la URL de la ventana de GiraGroup. La CLI tampoco tuvo acceso al motor local de Docker. | Campos de observación vacíos en el CSV. |

Cada ID identifica una tarjeta, campo de tabla, serie, contador u otro elemento del código. Los elementos repetibles se registran una vez por campo o serie. El CSV separa el estado de observación de la trazabilidad estática. Un campo vacío en `valor_mostrado` significa falta de observación y no representa el valor del indicador. El contexto documenta definiciones y fórmulas. Las señales S1–S11 siguen como hipótesis del sondeo.

| Módulo | Elementos y trazas con ID coincidente |
|---|---:|
| CMI | 150 |
| Académica | 106 |
| Financiera | 61 |
| DataOps | 127 |
| Transversal | 95 |
| **Total** | **539** |

La verificación estructural del CSV confirmó IDs únicos, correspondencia 1 a 1 y ausencia de valores declarados como observados. Los estados de traza distinguen el mapeo estático, las transformaciones locales, los contratos con campos ausentes y las acciones documentadas sin ejecución.

## Navegación para completar la observación

Las rutas V1 y V2 comparten los componentes principales según `frontend/src/App.jsx`. V2 añade el prefijo `/v2`. La visita por rol debe usar los permisos reales de cada pantalla.

| Módulo | Rutas base | Roles para la comprobación |
|---|---|---|
| CMI | `/dashboard` y `/cmi`, modos Perspectivas y Analítica predictiva | ADMIN y los roles con visibilidad de perspectivas según `backend/routers/cmi.py` |
| Académica | `/academico/rendimiento`, `/academico/docente`, `/academico/catalogo`, `/academico/proyeccion` | ADMIN y DIRECTOR_ACADEMICO. Incluir ANALISTA_MARKETING para catálogo y proyección. |
| Financiera | `/financiero/recaudacion`, `/financiero/cartera`, `/financiero/metas`, `/financiero/proyeccion` | ADMIN y ANALISTA_FINANCIERO |
| DataOps | `/dataops/ingesta`, `/dataops/beto`, `/dataops/revision`, `/dataops/datos-maestros` y rutas por lote | ADMIN y AUDITOR_CALIDAD |
| Transversal | `/reportes`, `/admin/auditoria`, `/notificaciones` | ADMIN y los roles con acceso según `frontend/src/App.jsx` |

## Efectos al abrir pantallas

- Pronósticos de alumnos y analítica macro. `backend/services/forecast_service.py:157` y `:209` pueden persistir proyecciones en `public.fact_forecast` cuando no hay una entrada aplicable en caché. La macro usa esa ruta para los segmentos del caso 2. `frontend/src/v2/navigation/routeDataPrefetcherV2.js` precarga esos endpoints en `/cmi`, `/academico/proyeccion` y `/financiero/proyeccion`.
- Revisión humana. `frontend/src/modules/dataops/HumanReviewFlowView.jsx:193` solicita preparar la revisión al montar la vista para determinados lotes. El componente de tareas en segundo plano se monta para ADMIN y AUDITOR_CALIDAD desde `frontend/src/App.jsx:350`. Sus consultas periódicas pueden marcar como fallidas las tareas que dejaron de reportar progreso mediante `backend/services/tareas_dataops.py:162`.
- Reportes. La generación de un exporte por GET registra un evento de auditoría mediante `backend/routers/reportes.py:538`. Abrir el historial y generar un exporte tienen efectos distintos.

Estas rutas se deben observar sobre una copia de trabajo aislada de la DW viva. En el inventario visual todavía faltan los valores, roles y gestiones observados y las capturas por bloque. El cierre de A0 queda pendiente de esa evidencia. Los loops de reconciliación y perfilado no se iniciaron. El trabajo de esta sesión consistió en lectura de código y documentación, sin consultas al DW, cambios de aplicación ni commit.

## Diferencias de código para comprobar en los loops siguientes

| Elemento | Diferencia observable en código | Comprobación pendiente |
|---|---|---|
| Cartera y mora, recaudación | `CarteraMora.jsx:56` busca `total_recaudado_bs` o `recaudacion_total` en la respuesta financiera. El esquema `KpisFinancieros` carece de ambos campos. | A1 debe comprobar la rama efectiva y compararla con Recaudación. |
| Metas de gestión, matriz de viabilidad | `MetasGestion.jsx:340` y `:361` consumen `volumen_historico` y `decision_estrategica`. `forecast_service.py:431` y `:439` devuelven `total_historico` y `decision_sugerida`. | A1 debe verificar el valor mostrado y el campo JSON en el entorno auditado. |
| CMI, conversión y automatización | KPI-06 se calcula a partir de `leads_captacion`. KPI-11 cuenta filas por banda de confianza. | A2 debe contrastar la definición y la fuente. A5 debe comparar la banda con el ruteo real. |
| DataOps, intervalo de fechas y latencia | `IngestView.jsx:356` consume `rango_fechas`, que el contexto de lote no devuelve. El total de latencia se deriva de los eventos de la página visible de la bitácora. | A1 debe comprobar el intervalo mostrado y el alcance de la agregación. |
