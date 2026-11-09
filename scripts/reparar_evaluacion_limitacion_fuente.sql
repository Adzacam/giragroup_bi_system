-- Evaluación docente sin docente/fecha es un límite de la fuente, no un caso de revisión (ronda 6, tarea 3c).
-- Cambia el contenido del DW: 11.210 respuestas pasan de requiere_revision = TRUE (48 casos en la bandeja) a FALSE con motivo informativo.
UPDATE public.fact_evaluacion_docente
   SET requiere_revision = FALSE,
       motivo_revision = 'LIMITACION_FUENTE'
 WHERE requiere_revision AND motivo_revision IS DISTINCT FROM 'RESUELTO_HUMANO';
UPDATE public.fact_evaluacion_docente SET motivo_revision = 'TIEMPO_IMPUTADO' WHERE motivo_revision = 'FECHA_ESTIMADA_DEL_PROGRAMA';
