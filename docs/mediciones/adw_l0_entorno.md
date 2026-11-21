# ADW L0 — entorno de la evidencia (2026-11-20)

## Copia tmpfs usada
- Contenedor `adw_pg_tmpfs` (postgres:16-alpine, `--tmpfs /var/lib/postgresql/data` 4 GB, `127.0.0.1:55433`), base `giragroup_db`.
- **Origen: `pg_dump` de solo lectura de la DW viva `giragroup_db`** (no del snapshot). Motivo: `snapshot_dw_20261110_1201` es anterior a las recargas del 18–20-nov y no contiene los datos auditados (evaluación 14.234 filas en el snapshot frente a 715.217 en la DW viva; académico 22.618 frente a 25.191). `scripts/aislada_tmpfs.sh up` restauraría el snapshot y no reproduciría la auditoría.
- Verificación de la copia: académico 25.191 · evaluación 715.217 · `carga_fila_origen` 1.636.142 · staging 10.830, iguales a la DW viva.
- La DW viva y el snapshot no se modificaron (solo `pg_dump`).
- El contenedor es efímero (tmpfs): se pierde al detenerlo. Se reproduce con las órdenes de `scripts/auditoria_dw/ejecutar_l0.sh` tras recrearlo.

## Scripts y salidas (L0-1)
`scripts/auditoria_dw/adw_*.sql` → `sh scripts/auditoria_dw/ejecutar_l0.sh` → 1 CSV por bloque:

| Bloque | CSV | Filas | Hallazgos que respalda |
|---|---|---|---|
| KPI (23 × gestiones) | `adw_l0_kpi.csv` | 92 | A1–A4, A9–A12 |
| Evaluación docente | `adw_l0_evaluacion.csv` | 41 | A1, C2 |
| Cartera | `adw_l0_cartera.csv` | 10 | A3 |
| Rentabilidad | `adw_l0_rentabilidad.csv` | 48 | A4, C5 |
| Marketing | `adw_l0_marketing.csv` | 5 | A5 |
| Académico | `adw_l0_academico.csv` | 2 | A2, A6, D1 |
| Staging | `adw_l0_staging.csv` | 23 | pregunta 3 |
| Tareas DataOps | `adw_l0_tareas.csv` | 16 | C1, D3 |
| `carga_fila_origen` | `adw_l0_carga_fila_origen.csv` | 10 | C3 |

## Cotejo con la auditoría (lo que confirman los CSV)
- **A1/C2:** doc 42 sigue como `ACTA` / `CENTESIMAL_100`; puntuaciones = 0: 2024 docente 4.947 + 192, institucional 2.862; 2025 docente 77.673 + 1.483, institucional 75.032. Respuestas válidas institucionales 2024 = 1.050 (doc 42) + 41 (doc 40) = 1.091, como en DA1.
- **A2:** `con_asistencia` = 0 y `incumplimiento_cero` = todas las filas (14.285 + 10.744 = 25.029; ver nota).
- **A3:** 2024 `Mora`: 2.959 filas, 2.902 con 0 cuotas, 1 con ≥ 2.
- **A5:** `leads` = 0, `reservas` = 0 en todas las gestiones; `*_captacion` vacías. (La auditoría preguntaba por qué `reservas` está lleno: **no lo está**; L6-0 debe partir de este dato.)
- **C1:** tareas 45, 47 y 49 en ERROR con 0 procesados; 182 s, 878 s y 180 s (la 47 duró 878 s, no 180 s).
- **C3:** razones claves/hechos: 2,00 · 2,12 · 2,19 · 2,88 · 3,52.

## Diferencias frente al texto de la auditoría (a corregir en el plan)
1. **Académico:** la auditoría habla de 25.191 hechos, pero por gestión suman 14.285 + 10.744 = **25.029**; 162 filas tienen `id_tiempo` NULL (verificado con `LEFT JOIN`) y ninguna vista por gestión las cuenta. Es un hallazgo nuevo (**A13**) para L3/L5.
2. **Tarea 47:** duró 878 s, no 180 s: «exactamente 180 s» solo vale para las tareas 45 y 49.
3. **Marketing `reservas`:** es 0 en todas las filas, no «lleno» (ver DA6).

## L0-2 y L0-3 (hechos el 2026-11-20, con la sesión que inició Lean)
- **Capturas:** 18 JPG en `adw_l0_capturas/` (CMI en 2 modos; Académico: alertas, docente, catálogo, proyección; Financiero: recaudación, cartera, metas, proyección; DataOps: carga, lectura, revisión, lote 35, lote 1, datos maestros; Auditoría; Reportes). **Limitación:** la ventana se emuló a 1440 px, pero el panel devuelve las imágenes reducidas (700–800 px de ancho); no son capturas a 1440 px reales. Para las figuras del documento habría que repetirlas con otra herramienta.
- **Cifras visibles:** `adw_l0_cifras_web.csv` (129 filas: 92 KPI del CMI + índices + cifras de los demás módulos). Los KPI se transcribieron de `adw_l0_web_kpi_transcrito.txt`; los contadores animados se leyeron tras desplazar la página (a la primera lectura salían en 0).
- **Cruce:** `adw_l0_cruce_kpi_web_dw.csv` (92 celdas CMI frente a `bi.vw_cmi_scorecard`: **92 iguales**, tolerancia 2 % por el redondeo de pantalla), `adw_l0_cruce_dw_valores.csv` (consultas `adw_cruce_web.sql`) y `adw_l0_cruce_web_dw.csv` (28 cifras de los demás módulos: **15 difieren**, 8 coinciden (6 de ellas con matiz, p. ej. «igual solo con PROGRAMAS»), 2 confirmadas, 3 no cruzables).
- Scripts: `scripts/auditoria_dw/cruce_kpi_web_dw.py` y `generar_l0_web.py`.

## Hallazgos nuevos que no estaban en la auditoría (a decidir en qué loop entran)
| # | Hallazgo | Evidencia | Grav. | Loop sugerido |
|---|---|---|---|---|
| A14 | 43 `dim_docente` tienen nombres de más de 60 caracteres: comentarios de encuestas entraron como docentes (DOC-111 en pantalla) | `adw_l0_cruce_dw_valores.csv` | 🔴 | L2 |
| A15 | Catálogo: 634 módulos `MOD-GEN*` y 3 con nombre «0», «1» o fecha; la tarjeta dice «100 % con código POS canónico» | idem | 🟠 | L6 |
| A16 | «Matrícula activa auditada» 10.327 = estudiantes distintos de todas las gestiones, no matrícula activa (KPI-21 = 3.773 y 3.571) | idem | 🟠 | L5 |
| A17 | «Cartera vencida exigible» Bs 4.832.610,08 = **deuda total** de todas las gestiones y estados | `adw_l0_cartera.csv` | 🔴 | L4 |
| A18 | «Recaudación consolidada DW» = Bs 0 en Cartera, con `monto_pagado` = 26.172.122,73 | idem | 🔴 | L4/L5 |
| A19 | Docente: 100 de 689 docentes, 67.109 evaluaciones (DW: 449.586 válidas), satisfacción 3,28 (DW: 4,088) | idem | 🟠 | L2/L5 |
| A21 | Las pantallas financieras usan solo la categoría PROGRAMAS (meta 16.894.995; recaudado 5.309.447,68); el CMI suma TECHOS_CERRADOS (17.973.400; 5.695.043,78). De ahí 31,4 % frente a 31,7 % | `adw_l0_rentabilidad.csv` | 🔴 | L5 |
| A22 | Serie predictiva: N = 33 en pantalla, 43 meses con inscritos en la DW y N = 40 en el invariante | idem | 🟠 | L5/L9 |
| A23 | Auditoría muestra «205 lotes»; la DW tiene 3 lotes y 10 documentos | idem | 🟠 | L6 |
| A24 | «Seguridad & 2FA = 0 logs» con 2FA usado hoy | pantalla | 🟡 | fuera de alcance |
| B3+ | La misma pantalla del CMI llama a `/api/v1/cmi/scorecard` y a `/api/v1/kpis/cmi-completo` (dos motores); Alertas: crítica 107 frente a 78 del CMI, financiero 1.440 frente a 249 de la vista | red del navegador, `adw_l0_cruce_web_dw.csv` | 🔴 | L5 |
| B1* | La pantalla actual del CMI **no llama** a `/perspectivas/*/detalle`: el 500 de CLIENTES es latente (el front en ejecución no usa ese endpoint) | red del navegador | — | L1 |
| L7* | `bitacora_dataops` (citada en L7) no existe como tabla; hay `log_pipeline_ingesta` (12.403 filas, 10 documentos) | `information_schema` | 🟡 | L7 |
| D2* | Las revelaciones de PII (NOMBRE/CI/CORREO) se guardan en `log_auditoria_nlp` como «Resolución HITL»: 4 filas | pantalla de Auditoría | 🟠 | L8 |
