---
name: gira-figuras
description: Chat de figuras y comandos de GiraGroup BI. Usar para generar gráficos, capturas, tablas exportadas o consultas de solo lectura a partir de docs/mediciones/, según un PLAN_FIG.
---

# Figuras y comandos (chat 4)

Generas salidas, no lógica. Fuente única: archivos de `docs/mediciones/` o consultas de solo lectura.

## Reglas
- No cambias código del sistema ni calculas cifras que no estén en una medición.
- Un gráfico usa exactamente los valores del JSON o CSV de origen; si falta un dato, lo reportas y no lo estimas.
- Las capturas son reales, de la aplicación en ejecución. Nunca generadas con texto fijo.
- Salida en `docs/figuras/<fase>/`, en PNG a 300 ppp.

## Entrega
`docs/cierres/FIGURAS_<fase>.md`:

| Archivo | Figura o tabla del docx | Pie propuesto | Insertar después de | Datos de origen |
|---|---|---|---|---|
