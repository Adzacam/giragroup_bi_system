# W-10 — Flujo DataOps de 3 pasos (solo frontend)

**Fecha:** 2026-11-17  
**Tarea:** `W-10` (D-W3, DECISIÓN 2)  
**Alcance:** Solo `frontend/src/` (`git diff --stat backend/` sin cambios de esta tarea).

## Cambios realizados
1. **Stepper de 3 pasos (V1 y V2):**
   - `frontend/src/modules/dataops/components/BatchFlowStepper.jsx`: reducido de 4 a 3 pasos (`Carga` → `Lectura de BETO` → `Revisión`), con grilla `repeat(3, minmax(150px, 1fr))` y conector centrado.
   - `frontend/src/modules/dataops/components/BatchFlowHeader.jsx`: títulos actualizados para pasos `1`, `2` y `3`.
   - `frontend/src/components/layout/Sidebar.jsx`: menú DataOps actualizado a 3 pasos (`① Carga de Archivos`, `② Lectura de BETO`, `③ Revisión`).
   - `frontend/src/modules/dataops/components/BatchHistory.jsx`: botones de estado actualizados al flujo de 3 pasos.
2. **Pestaña «Texto preparado» dentro de Lectura de BETO:**
   - `frontend/src/modules/dataops/components/TextoPreparadoTab.jsx`: tabla fila ↔ texto para BETO, datos protegidos y «Detalles de preparación».
   - `frontend/src/modules/dataops/BetoReadingFlowView.jsx`: `currentStep={2}`, pestañas `Resultados` y `Texto preparado` sincronizadas con `?tab=texto`, indicador de avance `Leyendo… N %` durante `processing`, y botón de retorno a `/ingesta`.
   - `frontend/src/modules/dataops/HumanReviewFlowView.jsx`: `currentStep={3}` y retorno a `/lote/:id/beto` con `toDataopsPath`.
3. **Resumen de preparación en Paso 1:**
   - `frontend/src/modules/dataops/IngestView.jsx`: muestra los 3 conteos (`Registros preparados`, `Campos por fila, máximo`, `Filas con observaciones`) en el resumen del lote activo/inspeccionado.
4. **Redirección de rutas heredadas:**
   - `frontend/src/App.jsx`: `/dataops/texto`, `/dataops/lote/:id/texto`, `/v2/dataops/texto` y `/v2/dataops/lote/:id/texto` redirigen a `.../beto?tab=texto` mediante `TextoRedirect`.

## Verificación
- `npx vitest run src/modules/dataops/__tests__/w10Flujo3Pasos.test.jsx`: **3/3 passed**
  - Stepper de 3 pasos (`Carga`, `Lectura de BETO`, `Revisión`, sin `Texto plano`).
  - Redirección de las 4 rutas viejas (`/dataops/texto`, `/dataops/lote/:id/texto`, `/v2/dataops/texto`, `/v2/dataops/lote/:id/texto`) a `beto?tab=texto`.
  - `BetoReadingFlowView` renderiza pestañas `Resultados` y `Texto preparado`, muestra `Leyendo… 45 %` y nunca invoca `startBatchReading` al entrar.
