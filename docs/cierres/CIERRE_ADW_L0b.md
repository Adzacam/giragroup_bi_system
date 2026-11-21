# CIERRE ADW-L0b — 2026-11-20
Rama / commit: beto-integracion · commit `adw(L0b): análisis de fuentes (L4-0, L6-0, L8-0)`; sin tocar el árbol de RV2 sin commit
Hecho (máx. 10 líneas):
- **L4-0** (`adw_l4_0_fuentes_metas.md`): la meta mensual de 2024 **no existe**; hay una sola cifra anual, 10.719.694 Bs, en `EJECUTADO VS META.xlsx`, hoja EJECUTADO, celda E25 (TECHOS/CERRADOS, diciembre). No hay meta 2023 en ningún archivo. 48 de 48 meses de `adw_l0_rentabilidad.csv` coinciden con el detalle EVM. Los 10 `CONFLICTO_FUENTES` (8 de meta de 2025, 7 con +100.000 Bs, y 2 de ejecución de marzo 2025) no se pueden resolver con los archivos. KPI-02 2024: 6,25 % actual · sin dato si se excluye · 75,04 % si se prorratea (suposición).
- **L6-0** (`adw_l6_0_fuente_captacion.md`): `fact_marketing` no sirve para KPI-06 (`leads` = 0 y `reservas` = 0 en todas las gestiones; `TBL_INSCRITOS` no tiene columna de leads). Sí hay interesados e inscritos en la misma fila en las hojas mensuales del doc 1 (`fact_planificacion_programa`): 2025 jul–dic = 1.351 / 35.085 = 3,85 %; 2026 ene–jun = 1.314 / 44.003 = 2,99 %; 2023 y 2024 no calculables.
- **L8-0** (`adw_l8_0_filas_sin_estudiante.md`): de 474 filas financieras sin estudiante, 472 son líneas de catálogo de programas (no pagos) y 2 traen un pago (1.523 Bs) con CI que sí existe en `dim_estudiante`. De 834 académicas: 750 catálogo, 68 docentes, 7 estados individuales sin identidad, 9 sin patrón. Rescatables por nombre: 0.
- Verificado por el chat de desarrollo: hash y celda E25 de la fuente de metas; cifras de leads/inscritos en la DW; deuda total.
- Corregida una fuga de datos personales en `adw_l6_0_inventario_excel.csv` (hojas sin cabecera dejaban correos y cédulas como «nombre de columna»): 27 celdas enmascaradas en el CSV y en el script que lo genera.
No hecho y por qué:
- No se decidió ninguna DA. **El plan cambió durante L0b:** `PLAN_FUENTES_UPLOADS.md` (FU) resuelve DA4 (KPI-02 excluye 2024 y 2023) y DA6 (KPI-06 desde Planificación/IBP) y declara que FU reemplaza a ADW-L0b, L2, L3, L4 y L7-C4. Estos informes quedan como evidencia de respaldo. DA7 sigue pendiente.
- Meta 2025: no se pudo decir cuál archivo es correcto (el detalle EVM difiere de ambos resúmenes) ni si 10.719.694 es total de empresa o solo TECHOS.
Invariantes cambiados: no
Pruebas: no se corrieron de nuevo (solo se añadieron scripts de análisis y documentos; el último resultado de L0 sigue vigente: 6 failed / 920 passed / 12 skipped / 7 xfailed, fallos ajenos). Cobertura no capturada.
Servicios reconstruidos + estado de docker compose ps: ninguno. `adw_pg_tmpfs` sigue activo fuera del compose.
Cambios de esquema o API: ninguno
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Meta anual 2024 (única) | 10.719.694 Bs | adw_l4_0_fuentes_metas.md
- KPI-02 2024 prorrateado | 75,04 % (suposición) | adw_l4_0_fuentes_metas.md
- Conversión inscritos/leads 2025 jul–dic | 3,85 % (1.351 / 35.085) | adw_l6_0_kpi06.csv
- Conversión inscritos/leads 2026 ene–jun | 2,99 % (1.314 / 44.003) | adw_l6_0_kpi06.csv
- Filas financieras sin estudiante que son pagos | 2 de 474 (1.523 Bs) | adw_l8_0_filas_sin_estudiante.md
- Filas académicas sin estudiante que son docentes | 68 de 834 | adw_l8_0_filas_sin_estudiante.md
- Filas de `fact_situacion_financiera` sin `id_tiempo` | 43 (4.600 Bs de deuda) | consulta sobre adw_pg_tmpfs (explica 4.832.610,08 frente a 4.828.010,08 de adw_l0_cartera.csv)
Impacto en el documento (sección o tabla): ninguno por L0b. Las cifras de conversión dependen de agrupar por hoja mensual (L6-0) o por fecha de inicio del programa (35.460 leads en 2025 y 47.402 en 2026 con esa otra agrupación); definir el criterio en FU-L3 antes de congelar.
Riesgos abiertos:
- `fact_marketing.inscritos` parece duplicado (≈ 2×; hipótesis del agente, no verificada); FU-L3 lo cubre.
- 43 filas financieras sin `id_tiempo` (y 162 académicas): hay que decidir qué hacer con ellas.
- Los agentes `dev-baja` pueden filtrar datos personales en CSV auxiliares; en este cierre se revisó a mano. Mantener la revisión.
- RV2 sigue sin commit.
Pendiente para el chat 4: nada.
