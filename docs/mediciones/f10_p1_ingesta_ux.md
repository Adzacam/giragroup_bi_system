# F10-2a: Sincronización de Paso 1 (Ingesta)

- `IngestView.jsx`: guardia `transferredNotified` para emitir `Archivos transferidos al servidor` una sola vez; cierre inmediato de `isProcessing` y `uploadStageText` al completar la respuesta; botón explícito `Ir a Lectura de BETO` sin iniciar BETO automáticamente.
- `ProgresoTarea.jsx`: cálculo unificado de porcentaje (`procesados / total * 100`) sin `AnimatedNumberV2` duplicado, y suavizado EMA (`0.75 * previo + 0.25 * actual`) para `restante_seg`.
