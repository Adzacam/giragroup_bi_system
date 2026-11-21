# Propuesta ADW: base de `bi.vw_riesgo_estudiante` (NO aplicada)
**Problema.** La vista parte solo de estudiantes con registro académico en la gestión. 2026 (sin datos académicos) queda vacía y la regla financiera (DA3) ve 248 estudiantes en 2025 frente a ~1.4xx de la pantalla de Alertas.
**Propuesta** (`adw_riesgo_base_union.sql`): base = unión de estudiantes con registro académico o financiero por gestión; `regla_a_academico` y `regla_d_desercion` quedan NULL sin registro académico (no 0). Probada en tmpfs (copia de la DW viva, sin la 022):

| Gestión | Alumnos antes → después | Regla financiera antes → después | Críticos antes → después |
|---|---|---|---|
| 2023 | — → 2 | — → 0 | — → 0 |
| 2024 | 3.773 → 4.556 | 1 → 1 | 0 → 0 |
| 2025 | 3.571 → 4.787 | 248 → 577 | 78 → 77 |
| 2026 | — → 1.977 | — → 858 | — → 0 |

**Por qué no se aplicó.** `bi.vw_cmi_valores` calcula KPI-09 y KPI-17 con `COUNT(*) FILTER … FROM bi.vw_riesgo_estudiante GROUP BY gestion`. Con la base nueva, 2026 aparecería con **0** (falso cero) en vez de «sin dato». Hace falta, en la misma migración, que `riesgo_g` devuelva NULL cuando no hay registros académicos (`CASE WHEN COUNT(prom_notas)=0 THEN NULL …`). `vw_cmi_valores` la redefine FU-L2 (migración 022, en curso en otro chat), así que el cambio debe integrarse allí o después de FU-L9.
**Siguiente paso.** Que FU-L9 incorpore ambas piezas (vista + guarda de `riesgo_g`) y que `routers/riesgos.py` lea la vista.
