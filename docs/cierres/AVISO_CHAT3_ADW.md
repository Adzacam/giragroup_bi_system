# AVISO AL CHAT 3 — ADW + FU CONGELADO (2026-11-21)

**Estado: ADW + FU CONGELADO.** Se ejecutó el cierre final `FU-L9` + `ADW-L9` + `ADW-B5` sobre `giragroup_db` (migraciones `022..028`, recarga controlada completa de los 10 libros fuente de `uploads/data/`, remedición y recongelado de `docs/fuente_verdad_tesis.md`).

## Cifras finales congeladas (remedición `docs/mediciones/adw_l9_remedicion_final.csv`)
| Código | Indicador | 2024 | 2025 | 2026 | Cambio clave |
|---|---|---|---|---|---|
| KPI-01 | Ticket promedio por estudiante (Bs) | 2.279,51 | 2.571,95 | 2.325,62 | Denominador único `pagantes` (A7) |
| KPI-02 | Cumplimiento último mes (%) | N/D | 157,48 % | 100,99 % | 2024 sin meta mensual (DA4) |
| KPI-03 | Cumplimiento meta a la fecha (%) | 102,26 % | 110,54 % | 109,08 % | Meses cerrados + todas las categorías |
| KPI-04 | Estudiantes con riesgo financiero | 362 | 808 | 641 | Mora DA3 (`cuotas_impagas >= 2`) |
| KPI-05 | Estudiantes en mora (%) | 10,60 % | 18,46 % | 37,75 % | Mora DA3 + pagos por mes (FU-L2) |
| KPI-06 | Conversión de admisiones (%) | N/D | 3,85 % | 2,94 % | Leads + inscritos de Planificación e IBP (DA6) |
| KPI-07 | Promedio de calificaciones (pts) | 82,32 | 81,81 | N/D | Limpieza de notas-texto y ceros (FU-L4) |
| KPI-08 | Tasa de aprobación (%) | 84,98 % | 85,62 % | N/D | Resultados normalizados (FU-L4) |
| KPI-09 | Estudiantes en riesgo académico | 667 | 445 | N/D | Guarda NULL sin registros académicos (`52ecec0`) |
| KPI-10 | Confianza media extracción (%) | 84,09 % | 83,92 % | N/D | — |
| KPI-11 | Automatización directa (%) | 54,34 % | 51,51 % | N/D | — |
| KPI-12 | Variación interanual ingresos (%) | 17,60 % | 28,10 % | 20,61 % | Periodos iguales cerrados |
| KPI-13 | Avance sobre la meta anual (%) | 102,26 % | 110,54 % | 31,69 % | Sin cambios (DA5) |
| KPI-14 | Brecha a la meta anual (Bs) | 0,00 | 0,00 | 12.278.356,22 | — |
| KPI-15 | Cartera vencida (%) | 69,61 % | 78,06 % | 23,07 % | Mora DA3 (`cuotas_impagas >= 2`) |
| KPI-16 | Tasa de deserción (%) | 5,38 % | 6,47 % | N/D | Deserción + Abandono (DA2-bis) |
| KPI-17 | Estudiantes en prioridad crítica | 66 | 116 | N/D | Guarda NULL sin registros académicos (`52ecec0`) |
| KPI-18 | Pendientes de revisión humana | 204 | 948 | 364 | Agrupados por gestión del dato (ADW-L6) |
| KPI-19 | Satisfacción docente (%) | 81,10 % | 82,00 % | 84,01 % | DA1 (0 → NULL), hoja por módulo, `id_tiempo = NULL` sin fecha |
| KPI-20 | Satisfacción institucional (%) | 79,72 % | 77,75 % | 80,20 % | DA1 (0 → NULL), NPS solo informativo |
| KPI-21 | Matrícula efectiva (cant.) | 3.773 | 3.571 | N/D | Sin duplicados (FU-L3) |
| KPI-22 | Inscritos por convenio (cant.) | 1.631 | 2.609 | N/D | 2023 = 93 |
| KPI-23 | Cumplimiento inicios planificados | 100,00 % | 99,77 % | 46,62 % | Incluye IBP 2026 |

## Pronóstico financiero (DA8 — `docs/mediciones/adw_da8_forecast_despues.json`)
- Pendiente OLS anual: `+2.360.251,66 Bs/año` · CAGR histórico: `22,85 %`
- Meta anual 2026: `17.973.400 Bs` · Recaudado acumulado 2026: `5.695.043,78 Bs` · Avance: `31,7 %`
- RMSE Caso 3 (Holt-Winters metas): `297.317,61`
