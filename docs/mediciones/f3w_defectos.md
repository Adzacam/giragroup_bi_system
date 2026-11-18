# Defectos Detectados en W-1 / W-1b (`f3w_defectos.md`)

| ID | Descripción | Archivo y línea | Veredicto | Se corrige en |
|---|---|---|---|---|
| **D-W1** | SPA solo reconoce 4 tipos de fuente (`ACTA`, `MOODLE`, `COBRANZA`, `ADMISION`) | `frontend/src/constants/dataopsConfig.js:33-38` | `defecto` | **F3W (W-2)** |
| **D-W2** | `resolve_review_item` no rutea `evaluacion_docente`, `rentabilidad` ni `marketing` (HTTP 503) | `backend/routers/dataops/revision.py:385-387` | `defecto` | **F3W (W-3)** |
| **D-W4** | Casos HITL solo se crean al consolidar, paso 4 aparece en 0 antes | `backend/routers/dataops/consolidacion.py:197-240` | `defecto` | **F3W (W-5)** |
| **D-W5** | Consolidación recalcula `indices_cascada` y hace flush fila a fila | `backend/routers/dataops/consolidacion.py:209`, `dw_loader.py` | `defecto` | **F3W (W-6)** |
| **D-W6** | Formulario de revisión fijo (`Nota sobre 100, Mes, Gestión`) | `frontend/src/modules/dataops/HumanReviewFlowView.jsx` | `defecto` | **F3W (W-4)** |
| **D-W7** | Respuestas Likert 1–10 escaladas ×10 como notas en `formatter.py` | `pipeline/semantic/formatter.py:238-252` | `defecto` | **F3W / F3V** |
| **D-W8** | Toasts apilados sin progreso % agrupado | `frontend/src/services/sileoToast.js`, `notificationService.js` | `defecto` | **F3W (W-7)** |
| **D-W9** | Navegación fija `/dataops/*` rompe `/v2/dataops/*` | `frontend/src/modules/dataops/*.jsx` | `defecto` | **F3W (W-9)** |
| **D-W10** | `carga_fila_origen` solo escribe `fact_marketing` con `id_documento=1` | `backend/services/dw_loader.py` | `defecto` | **F3W (W-13)** |
| **D-W11** | Expansión de filas con saltos de línea internos en celdas (`Evaluación Docente y Unifranz`, `[BBDD] ANTIGUO`) y multi-hoja | `pipeline/ingesta.py` / reglas B-9 | `regla_correcta` + `defecto` menor en celdas multilínea | **F3V** (reglas de expansión complejas) |
