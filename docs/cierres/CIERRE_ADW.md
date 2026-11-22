# CIERRE ADW — Plan Auditoría DW ↔ Web — 2026-11-22
**Estado: CERRADO.** Cierre consolidado del plan `PLAN_AUDITORIA_DW.md`. Congelado junto con FU en `CIERRE_FINAL_FU_ADW_L9.md` (SFV recongelada el 21-nov-2026).

## Loops
| Loop | Estado | Dónde |
|---|---|---|
| L0 evidencia y capturas | Hecho (capturas reducidas, no 1440 px reales) | `CIERRE_ADW_L0.md` |
| L0b análisis de fuentes | Hecho; DA4, DA6 y DA7 resueltas | `CIERRE_ADW_L0b.md` |
| L1 500 de CLIENTES y errores silenciados | Hecho | `CIERRE_ADW_L1.md` |
| L2 evaluación docente | Absorbido por FU-L5 | `CIERRE_FU_L5.md` |
| L3 nulos / deserción | Absorbido por FU-L4 (DA2-bis) | `CIERRE_FU_L4.md` |
| L4 finanzas (mora DA3, metas, KPI-01) | Absorbido por FU-L2, FU-L6 y migración 028 | `CIERRE_FU_L2.md`, `CIERRE_FU_L6.md` |
| L5 motor único de KPI | Hecho; DA8 (todas las categorías) aplicada | `CIERRE_ADW_L5.md`, `CIERRE_ADW_DA8.md` |
| L6 configuración del CMI | Parte de FU-L3/L6; DA5 mantiene 9 KPI sin umbral hasta que Lean defina metas | `CIERRE_FINAL_FU_ADW_L9.md` |
| L7 pipeline y BETO | Hecho (C1 era contaminación de pytest; B5 premisa falsa; C3 explicado); C4/C5 por FU | `CIERRE_ADW_L7.md` |
| L8 revisión humana | Hecho; reclasificación de 12.326 filas aplicada también en la DW viva | `CIERRE_ADW_L8.md` |
| L9 remedición y recongelado | Hecho por el chat FU (recarga, SFV, aviso al chat 3) | `CIERRE_FINAL_FU_ADW_L9.md` |

## Verificación final (2026-11-22, DW viva, solo SELECT)
- Invariantes: 49 tablas `public` + 2 `bi` = 51 · 10 vistas `bi` · 23 KPI en `bi.ref_kpi`.
- Marcador `APROBACION_BLOQUE` en la DW viva: 12.326 filas (hecho por ADW-L8/L9).
- Propuesta de base de `bi.vw_riesgo_estudiante` (`52ecec0`): **absorbida** en la migración 028 (unión académico + financiero y guarda NULL en `riesgo_g`).
- Scorecard vivo frente a `adw_l9_remedicion_final.csv`: 2 celdas difieren de 92: redondeo (KPI-03 2026: 109,07 frente a 109,0750) y **KPI-22 2023** (vivo sin valor; congelado 93). Revisar en el siguiente corte.
- `dataops_tarea`: 30 filas, sin tareas basura nuevas (el arreglo de pytest sigue vigente).

## Pendiente (no bloquea el cierre)
1. Verificar las pantallas en el navegador y repetir las capturas a 1440 px reales (necesita sesión con 2FA de Lean).
2. KPI-22 de 2023: confirmar por qué el scorecard vivo no lo muestra.
3. Las 74 filas `BAJA_CONFIANZA` pendientes (eran 5 con índice 0 en el doc 44; ahora 74): revisar su origen.
4. N de la serie predictiva (33 en pantalla, 43 meses con inscritos, 40 en el invariante).
5. 162 hechos académicos sin `id_tiempo` (A13) y catálogo con módulos `MOD-GEN*`.
6. Avisar al chat 1 de las premisas falsas de la auditoría (B5, C1, «reservas lleno») para que las retire del plan.
7. 6 fallos de pytest de entorno del host Windows (sin `statsmodels`/`torch`/`seqeval`), ajenos al plan.

## Lecciones
- Las pruebas que llaman a rutas con seguimiento de tareas deben aislar `tareas_dataops` (guardia en `tests/adw/test_l7_pipeline.py`).
- Revisar siempre a mano los CSV generados por agentes de bajo costo: uno filtró correos y cédulas.
