-- ADW L8 (D2): las filas históricas «Aprobación en bloque sin cambios» pasan a llevar el marcador APROBACION_BLOQUE.
-- Solo cambia el texto de correccion_humana; no se borra ni se mueve ninguna fila.
-- Aplicado en la copia tmpfs. En la DW viva lo decide Lean (ver CIERRE_ADW_L8.md).
UPDATE public.log_auditoria_nlp SET correccion_humana = 'APROBACION_BLOQUE'
WHERE correccion_humana = 'Aprobación en bloque sin cambios';
