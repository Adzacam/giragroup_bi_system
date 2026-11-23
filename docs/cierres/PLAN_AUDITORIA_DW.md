# PLAN AUDITORÍA DW ↔ WEB (ADW) — 2026-11-20

Objetivo (1 línea): encontrar qué cifras del CMI y de los módulos web son incoherentes o están vacías, rastrear la causa en la DW, el pipeline, BETO o la revisión humana, y planificar la corrección por loops.

Entrada:
- `REESTRUCTURACION_VISTA_V2.md` y `CIERRE_RV2.md` (L0–L7 hechos, **sin commit**).
- Rama `beto-integracion` `38e317f`.
- DW viva `giragroup_db`, solo consultas `SELECT`.

Método:
- Consultas `SELECT` directas a la DW: los 23 KPI en todas las gestiones, la definición viva de `bi.vw_cmi_valores` y el perfil de los hechos.
- Lectura de los routers y servicios que alimentan cada pantalla y logs de la API.
- No hubo inspección en el navegador: el login pide 2FA y no se permitió generar un token de servicio. Las capturas por módulo pasan al Loop 0.

> **Advertencia de cifras.** Toda corrección de los loops 2–6 **cambia valores de KPI que hoy están congelados** en `docs/fuente_verdad_tesis.md`. Por eso cada una está en DECISIONES PENDIENTES y la fase cierra con un recongelado (L9) y un aviso al chat 3.

---

## PARTE 1 — Resultados de la auditoría

Gravedad: 🔴 cifra falsa o pantalla rota · 🟠 cifra engañosa o no comparable · 🟡 vacío o deuda.

### 1.1 Cuadro de Mando Integral: los 23 KPI

| # | KPI | Qué muestra | Qué hay en la DW (evidencia) | Causa | Grav. |
|---|---|---|---|---|---|
| A1 | KPI-20 Satisfacción institucional · KPI-19 Satisfacción docente | 12,58 % (2025), 22 % (2024); docente 58–67 % | `Experiencia Docente 2.0.xlsx` (doc 42): **84.544 de 92.016** respuestas institucionales = **0** y 87.927 docentes = 0, en una escala 1–5. El 0 no existe en esa escala | Las respuestas vacías o en texto se cargan como 0 en vez de NULL. El doc 42 está tipificado **ACTA / CENTESIMAL_100** aunque es una encuesta (ver C2) | 🔴 |
| A2 | KPI-16 Tasa de deserción | **0,00 % en verde** (2024 y 2025) | `asistencia_pct` NULL en los 25.191 hechos académicos; `incumplimiento_actividades_pct` = 0 en los 25.191 | La vista hace `COALESCE(...,0)` y `COALESCE(asistencia,100)`: la falta de dato se ve como «sin deserción». Lo mismo pasa con `regla_d_desercion` en riesgo | 🔴 |
| A3 | KPI-05 Estudiantes en mora · KPI-15 Cartera vencida | Mora 94 % (2024), 53 %, 75 %; vencida 85–99 % | 4.931 filas `estado_cartera='Mora'` con `cuotas_impagas = 0`. En 2024, 2.838 alumnos «en mora» y solo **1** fila con ≥ 2 cuotas impagas | La etiqueta de estado de la fuente no concuerda con las cuotas. Además, el módulo Financiero (`KPIService`) define mora como `cuotas_impagas > 0`: **dos cifras distintas** para el mismo concepto | 🔴 |
| A4 | KPI-02 Cumplimiento último mes | 6,25 % (2024), 157 % (2025), 15,28 % (2026) | 2024: la meta anual completa (10.719.694 Bs) está cargada **solo en diciembre**. 2026: la ejecución termina en **mayo**, con 252.233 Bs (mes parcial), y la meta llega a diciembre | Meta 2024 sin desglose mensual y mes en curso tratado como mes cerrado | 🔴 |
| A5 | KPI-06 Conversión de admisiones | Siempre «sin dato» | `fact_marketing`: 13.860 filas con `leads` = 0 en todas y `leads_captacion` / `inscritos_captacion` = NULL en todas | La fuente `TBL_INSCRITOS.xlsx` no trae interesados (leads). El KPI no se puede calcular con las fuentes actuales | 🟡 |
| A6 | KPI-07, 08, 09, 10, 11, 17, 21 en 2026 | Sin dato en 2026 | `fact_rendimiento_academico` solo tiene 2024 y 2025. La base ARCA cargada llega hasta 2025 | Falta la fuente académica 2026 | 🟡 |
| A7 | KPI-01 Ticket promedio | 2.882 / 1.927 / 3.654 / 2.955 Bs | El denominador es la matrícula académica y, si no hay, los pagantes. 2023 usa 2 pagantes; 2026 usa pagantes | Denominador distinto según el año: la serie no es comparable | 🟠 |
| A8 | KPI-18 Pendientes de revisión humana | 1.413 en 2026; vacío en 2024–2025 | Se agrupan por `created_at` de staging, no por la gestión del dato | Muchos pendientes son de datos 2024–2025, pero cuentan en 2026 | 🟠 |
| A9 | Índice de perspectivas | Aprendizaje «1 de 5 evaluados», Clientes «1 de 5» | 9 de los 23 KPI no tienen meta o umbral (01, 04, 09, 13, 14, 17, 21, 22, y 06 sin dato) | Configuración incompleta: el índice se calcula con pocos KPI | 🟠 |
| A10 | KPI-13 Avance meta anual | Igual a KPI-03 en 2024 y 2025 | Ambos KPI dan lo mismo en los años cerrados | Redundancia | 🟡 |
| A11 | Gestión 2023 en el selector | Casi todo vacío | `fact_situacion_financiera` 2023 = 2 filas; sin meta 2023; marketing 2022 = 51 filas | Años con datos residuales que ensucian el selector | 🟡 |
| A12 | KPI-22 Inscritos por convenio | 93 en 2023 (sin matrícula 2023) | `fact_techo_convenio` sí tiene 2023 | Coherente con su fuente, pero aislado. Verificar el origen | 🟡 |

### 1.2 Web y API

| # | Hallazgo | Evidencia | Grav. |
|---|---|---|---|
| B1 | **`GET /api/v1/cmi/perspectivas/CLIENTES/detalle` responde 500.** Pertenece a la RV2 L4, sin commit | El SQL usa `public.fact_inscripcion`, `dim_programa`, `fact_captacion_marketing`, `dim_fuente_captacion` y `t.anio`; **ninguno existe** (la columna es `gestion`). 5 errores 500 en el log de la API | 🔴 |
| B2 | Errores silenciados | `_detalle_perspectiva` envuelve los KPP y las gráficas personalizadas en `except Exception: db.rollback()` sin registrar nada; la conversión por fuente hace lo mismo | 🟠 |
| B3 | **Dos motores de KPI** | El CMI usa `bi.vw_cmi_valores` (por gestión). Académico, Financiero, Metas y Cartera usan `KPIService`, con agregados en Python sobre todas las gestiones y definiciones distintas (mora, aprobación, conversión). La misma pantalla puede contradecir al CMI | 🔴 |
| B4 | Calidad NLP engañosa | `kpis/pipeline`: `tasa_calidad = 100 − requiere_revision / hechos` = 43 / 10.733 → **≈ 99,6 %**, mientras hay 1.413 entidades pendientes en staging que no entran en la cuenta | 🟠 |
| B5 | Caché de BETO inexistente | `beto_integracion.py` usa `public.cache_beto_entidades` («migración 015»). **La 015 no existe** (la lista salta de 014 a 016) y la tabla tampoco. Falla sin avisar («sigue sin caché») | 🟠 |
| B6 | Llamada residual a Power BI | 1 `GET /api/v1/powerbi/informe` en el log (pestaña con build anterior); ahora da 404 | 🟡 |

### 1.3 Pregunta 1: ¿qué falla en el pipeline?

| # | Hallazgo | Evidencia | Grav. |
|---|---|---|---|
| C1 | **La lectura BETO del lote 1 (Planificación) se interrumpe 3 veces** | Tareas 45, 47 y 49 terminan en ERROR con 0 procesados, **exactamente 180 s** después de empezar (`SIN_LATIDO_SEG`). La primera corrida (tarea 2) leyó 1.721 en menos de 1 s. Al reingestar el mismo archivo, el paso BETO no avanza ni llama a `terminar()`. Los logs se perdieron con el reinicio de la API a las 20:38 | 🔴 |
| C2 | **Clasificación errónea de fuente** | `Experiencia Docente 2.0.xlsx` quedó como `tipo_fuente = ACTA`, `tipo_escala = CENTESIMAL_100`, pero carga 1.006.336 claves en `fact_evaluacion_docente`. El tipo y la escala equivocados explican los ceros de A1 | 🔴 |
| C3 | Registro de idempotencia inflado | `carga_fila_origen` tiene entre 2 y 3 veces más claves que hechos: académico 50.390 frente a 25.191; financiero 30.948 frente a 10.733; evaluación 1.513.038 frente a 715.217; marketing 30.392 frente a 13.860. Quedan claves de reprocesos o de filas no cargadas, lo que roza la DECISIÓN 3 de F3V (idempotencia) | 🟠 |
| C4 | ¿Hojas enteras descartadas? | `LINEA_SIN_ENTIDAD` descartó 10.351 líneas de la hoja «DIP. EXP DOC. X MODULO» (doc 41), 805 de «DIPLOMADOS DOC 2» y 748 de «IBP» (doc 43). Puede que se estén perdiendo hojas con datos | 🟠 |
| C5 | Conflictos sin resolver | 10 `CONFLICTO_FUENTES` (MEDIA, PENDIENTE) en `fact_rentabilidad`, entre `BD Egresos` y `EJECUTADO VS META` | 🟡 |
| C6 | Cobertura de datos | Académico: 2024–2025. Financiero: hasta 2026, con ejecución solo hasta mayo de 2026. Sin leads de marketing. 2.327 estudiantes (13,8 %) sin CI | 🟡 |

### 1.4 Pregunta 2: ¿qué falla con BETO?

| # | Hallazgo | Evidencia | Grav. |
|---|---|---|---|
| D1 | Confianza por debajo del umbral | La confianza media de los hechos académicos es **0,840** (KPI-10 en ámbar, frente a 0,85) y solo el 51–54 % supera 0,85 (KPI-11 en rojo). Casi la mitad de lo académico quedaría para revisión | 🟠 |
| D2 | **Falsa señal de «corrección humana»** | `log_auditoria_nlp`: 12.332 filas del 19-nov, todas con `correccion_humana`, que en realidad son **aprobaciones en bloque «sin cambios»** (11.952 académicos + 374 financieros). Inflan cualquier métrica de retroalimentación y no aportan señal de entrenamiento | 🔴 |
| D3 | Tareas BETO interrumpidas | Ver C1 | 🔴 |
| D4 | Caché sin efecto | Ver B5: cada texto se vuelve a inferir | 🟠 |

### 1.5 Pregunta 3: ¿qué entra a revisión humana y tiene sentido?

**Pendientes (1.413), con lo que tiene sentido y lo que no:**

| Motivo | N | Fuzzy medio | Conf. media | ¿Tiene sentido? |
|---|---|---|---|---|
| CI_NOMBRE_DISCORDANTE | 756 (748 de ARCA, doc 43) | 28 | 0,84 | **Sí:** la CI coincide y el nombre no (fuzzy 28 < 85). Son conflictos reales de identidad, pero el 99 % viene de una sola fuente: conviene agruparlos por patrón |
| BAJA_CONFIANZA_IA | 573 | 47–56 | 0,47–0,56 | **Sí:** son residuales de la cascada, bajo la banda de 0,60 |
| HOMONIMIA | 70 | 100 | 0,80–0,85 | **Sí:** mismo nombre con distinta CI = estado C (invariante) |
| CI_DUDOSA | 9 | 59–91 | — | **Sí** |
| BAJA_CONFIANZA (doc 44) | 5 | **0** | **0** | **No:** son filas vacías de `TBL_INSCRITOS` que deberían descartarse automáticamente |

**Lo que no entra y por qué:**

| Motivo | N | Destino | ¿Tiene sentido? |
|---|---|---|---|
| CI_NOMBRE_VARIANTE | 13.028 | Registrado automáticamente | Sí: fuzzy ≥ 85 (umbral de variante) |
| FILA_EVALUACION_SIN_RESPUESTAS | 8.066 | Descartada | Sí, **pero** en el doc 42 las filas sin respuesta entran como 0 en vez de descartarse (A1) |
| FILA_ACADEMICA_SIN_ESTUDIANTE | 834 | Descartada | Dudoso: notas sin alumno se pierden sin revisión |
| FILA_FINANCIERA_SIN_ESTUDIANTE | 474 | Descartada | **Discutible:** son pagos y deudas que desaparecen de la cartera sin que nadie los vea |
| LINEA_SIN_ENTIDAD / SUBTOTAL | ~14.000 | Descartada / registrada | Sí para subtotales; dudoso para hojas completas (C4) |
| **Aprobación en bloque HITL** | **12.326 hechos** | Aprobados «sin cambios» por admin_general | **No como está:** la revisión se salta por volumen y se registra como corrección (D2) |

**Pregunta 4:** no existe; Lean confirmó el 2026-11-20 que el alcance son solo las preguntas 1–3.

---

> **Premisas retiradas (2026-11-22, según `CIERRE_ADW.md` / `CIERRE_ADW_L7.md`):**
> - **B5** (caché BETO inexistente por la falta de la migración 015) era una premisa falsa.
> - **C1** (lectura BETO del lote 1 interrumpida 3 veces) era contaminación de pytest, ya corregida con la guardia en `tests/adw/test_l7_pipeline.py`.
> - **«`reservas` lleno»** en `fact_marketing` era incorrecto.
>
> No se usan como evidencia en planes posteriores (`PLAN_DATAOPS_FLUJO.md`).

## PARTE 2 — Plan por loops

| Loop | Sección | Agente | Depende de | Paralelo con | Cambia cifras congeladas |
|---|---|---|---|---|---|
| L0 | Evidencia reproducible + capturas por módulo | `dev-baja` | — | — | No |
| L0b | **Análisis de fuentes** (L4-0 metas, L6-0 captación, L8-0 filas sin estudiante): solo lectura, un informe por tarea para decidir DA4, DA6 y DA7 | `dev-baja` | — | L0, L1, L7 | No |
| L1 | Arreglar el 500 de CLIENTES y los errores silenciados (B1, B2) | `dev-media` | L0 | L7 | No |
| L2 | Evaluación docente: clasificación, escala y ceros (A1, C2) | `dev-alta` | L0 (DA1 resuelta) | L3, L7 | **Sí** (KPI-19, 20) |
| L3 | Semántica de nulos: deserción y asistencia (A2) | `dev-media` | L0 (DA2 resuelta) | L2 | **Sí** (KPI-16, riesgo) |
| L4 | Finanzas: estado de cartera, meta 2024 y mes parcial (A3, A4, A7) | `dev-alta` | L0 + L4-0 (DA3 resuelta; meta 2024 espera DA4) | L2 | **Sí** (KPI-01, 02, 05, 15) |
| L5 | Un solo motor de KPI: `KPIService` → vistas `bi` (B3, B4) | `dev-media` | L3, L4 | — | Sí (pantallas de módulos) |
| L6 | Configuración del CMI: metas y umbrales faltantes, KPI-06/13, gestiones residuales (A5, A8–A11) | `dev-media` | L5 + L6-0 + **DA5** (KPI-06 espera DA6) | — | **Sí** (índices) |
| L7 | Pipeline y BETO: tarea interrumpida, caché 015, idempotencia, hojas descartadas (C1, C3, C4, B5) | `dev-alta` | L0 | L1, L2 | No (salvo que C4 recupere datos) |
| L8 | Revisión humana: aprobación en bloque, filas vacías, financieras sin alumno (D2, revisión) | `dev-media` | L7 + L8-0 (filas sin estudiante esperan DA7) | — | Sí (KPI-18) |
| L9 | Remedición, recongelado de la SFV y aviso al chat 3 | `dev-alta` | L1–L8 | — | Recongela |

### L0 — Evidencia reproducible (`dev-baja`)
| ID | Tarea | Criterio | Salida |
|---|---|---|---|
| L0-1 | Pasar las consultas de esta auditoría a `scripts/auditoria_dw/adw_*.sql` y ejecutarlas sobre la **copia tmpfs** | 1 CSV por bloque (KPI, evaluación, cartera, rentabilidad, marketing, académico, staging, tareas, carga_fila_origen) | `docs/mediciones/adw_l0_*.csv` |
| L0-2 | Capturar cada módulo (CMI con sus 3 modos; Académico: rendimiento, docente, catálogo, proyección; Financiero: recaudación, cartera, metas, proyección; DataOps; Auditoría; Reportes) a 1440 px. Lean ingresa el 2FA | 1 captura por pantalla + lista de las cifras visibles | `docs/mediciones/adw_l0_capturas/`, `adw_l0_cifras_web.csv` |
| L0-3 | Cruzar cada cifra visible con su SQL equivalente | Tabla web ↔ DW con diferencia | `adw_l0_cruce_web_dw.csv` |

### L1 — 500 en el desglose de CLIENTES y errores silenciados (`dev-media`)
- Reescribir `inscritos_programa` con tablas reales: `fact_marketing.inscritos` + `dim_modulo` / `cat_programa` y `dim_tiempo.gestion`. Quitar `conversion_fuente` hasta que exista la fuente (A5).
- Cambiar los `except Exception` por `logger.exception` + una lista `avisos` en la respuesta.
- Test de API: las 4 perspectivas responden 200; un test recorre las tablas citadas en el SQL de `routers/` y falla si alguna no existe.
- Criterio: 0 respuestas 500 en `/cmi/perspectivas/*/detalle`.

### L2 — Evaluación docente (`dev-alta`) · DA1
- Corregir el clasificador para que `Experiencia Docente 2.0.xlsx` quede como `EVALUACION_DOCENTE` con su escala real.
- Lo que no sea un número dentro de la escala va a NULL, nunca a 0. Las filas sin `escala_max` se resuelven o se descartan con su motivo.
- Recargar solo los docs 40–42 en la copia tmpfs (idempotente, `carga_fila_origen`).
- Criterio: 0 puntuaciones fuera de [1, escala_max]; KPI-19 y KPI-20 recalculados y comparados contra L0. Salida: `adw_l2_eval_antes_despues.csv`.

### L3 — Semántica de nulos (`dev-media`) · DA2
- `bi.vw_cmi_valores` y `bi.vw_riesgo_estudiante`: con asistencia e incumplimiento ausentes, la deserción es NULL («sin dato», con motivo en `FALTANTES`), no 0.
- Migración nueva `0NN_kpi16_nulos.sql`.
- Criterio: KPI-16 = sin dato en 2024–2025 con su motivo. Test con datos sintéticos (con y sin asistencia).

### L4 — Finanzas (`dev-alta`) · DA3, DA4
- **Mora:** definir una sola regla de mora (por `estado_cartera` normalizado o por `cuotas_impagas`, según DA3) y aplicarla en la vista y en el servicio.
- **Meta 2024:** repartir la meta anual cargada en diciembre (según DA4) o excluir 2024 del KPI-02.
- **Mes parcial:** KPI-02 usa el último mes **cerrado** y KPI-12 compara periodos iguales.
- **KPI-01:** un solo denominador para todos los años.
- Criterio: tests por regla y tabla antes/después. Salida: `adw_l4_fin_antes_despues.csv`.

### L5 — Un solo motor de KPI (`dev-media`)
- `KPIService.obtener_kpis_*` y `obtener_perspectivas_cmi_completo` pasan a leer `bi.vw_cmi_scorecard` / `vw_cmi_valores` por gestión.
- `kpis/pipeline` incorpora los pendientes de staging en su tasa de calidad.
- Criterio: para cada KPI presente en un módulo, el valor en pantalla es igual al del CMI en la misma gestión (test de contrato).

### L6 — Configuración del CMI (`dev-media`) · DA5, DA6
- Proponer metas y umbrales para los 9 KPI sin umbral; el texto es de Lean (DA5).
- KPI-18 por gestión del dato.
- KPI-13 o KPI-03: diferenciar o retirar uno (DA6).
- Ocultar las gestiones con menos de N KPI con dato.

### L7 — Pipeline y BETO (`dev-alta`)
- **C1:** reproducir la reingesta del lote 1 en tmpfs, registrar con `bitacora_dataops` el motivo de `total = 0` y asegurar que el paso BETO llame a `terminar()` cuando no hay trabajo («0 textos nuevos»).
- **B5:** crear la migración `015_cache_beto_entidades.sql` faltante o apuntar a `cache_indice_beto`; medir el acierto de caché.
- **C3:** explicar la diferencia entre `carga_fila_origen` y los hechos y purgar las claves huérfanas (en tmpfs y con conteo antes/después).
- **C4:** revisar las hojas descartadas («DIP. EXP DOC. X MODULO», «DIPLOMADOS DOC 2», «IBP») y decir si contienen datos.
- **C5:** resolver o explicar los 10 `CONFLICTO_FUENTES`.
- Criterio: la reingesta del lote 1 da COMPLETADA. Salida: `adw_l7_*.json`.

### L8 — Revisión humana (`dev-media`) · DA7
- La aprobación en bloque se registra como `APROBACION_BLOQUE`, **no** como `correccion_humana` en `log_auditoria_nlp`.
- Las filas con confianza 0 y payload vacío se descartan automáticamente con su motivo.
- Las `FILA_FINANCIERA_SIN_ESTUDIANTE` pasan a la bandeja (DA7).
- Los 748 `CI_NOMBRE_DISCORDANTE` de ARCA se agrupan por patrón en la bandeja.
- Criterio: tests y conteos de la bandeja antes/después.

### L9 — Remedición y recongelado (`dev-alta`)
- Recalcular los 23 KPI, comparar con L0, actualizar `fuente_verdad_tesis.md` como **CONGELADO** con la nueva huella y avisar «ADW congelado» al chat 3.
- `pytest` + cobertura, vitest, rebuild de `api` y `web`, capturas «después» por módulo.
- Escribir `CIERRE_ADW.md`.

---

## Riesgos y control
- **Recargas:** L2, L4 y L7 solo trabajan en la copia tmpfs; el snapshot `snapshot_dw_20261110_1201` es de solo lectura. Antes de cada recarga se hace `pg_dump` en `backups/`.
- **RV2 sin commit:** el bug B1 vive en el código de RV2 sin commit. Commitear RV2 antes de L1, o hacer L1 sobre esa rama.
- **Invariantes:** no cambian la cascada, los umbrales (0,92 / 90 / 85 / 80 / 0,85–0,60) ni el conteo de 51 / 10 / 23. Los cambios de vistas son `CREATE OR REPLACE`.
- **Logs:** subir la retención de logs de la API (los de C1 se perdieron con un rebuild).

## DECISIONES PENDIENTES PARA LEAN
- **DA1 — RESUELTA (Lean, 2026-11-20): fuera de escala o texto = NULL (sin respuesta).**
  - **Regla:** cuenta solo `puntuacion ∈ [1, escala_max]`. El resto se guarda como NULL en el parser (L2) y además se filtra en `bi.vw_cmi_valores`, para que no dependa de la recarga.
  - **Filas sin `escala_max`:** se infiere la escala desde la cabecera de la hoja. Si no se puede, quedan sin respuesta con su motivo en `log_inconsistencias`.
  - **NPS:** se conserva aparte, en su escala de 0–10, donde el 0 sí es válido.
  - **Estimado con la DW actual** (L2 lo confirma tras corregir la clasificación del doc 42):

    | Gestión | KPI-19 docente hoy → nuevo | KPI-20 institucional hoy → nuevo | Respuestas institucionales válidas |
    |---|---|---|---|
    | 2024 | 58,61 → **79,99** | 22,00 → **79,71** | 1.091 |
    | 2025 | 66,77 → **81,90** | 12,58 → **78,37** | 14.342 |
    | 2026 | 82,35 → 82,35 | 70,99 → **79,30** | 6.715 |

  - **Consecuencia:** con la meta de 85 y el umbral ámbar de 75, KPI-19 y KPI-20 pasan de **rojo a ámbar** en 2024–2025. 2024 institucional se apoya en solo 1.091 respuestas válidas, así que L2 muestra la *n* junto al valor en el drill-down.
- **DA2 — REEMPLAZADA por DA2-bis (`PLAN_FUENTES_UPLOADS.md`):** el KPI-16 se calcula desde el campo canónico `estado_academico` (Deserción / Abandono) de cualquier fuente; solo queda «sin dato» si ninguna fuente lo trae. Texto original:
- ~~DA2 — RESUELTA (Lean, 2026-11-20): KPI-16 = «sin dato» mientras no haya asistencia.~~
  - En `bi.vw_cmi_valores`, KPI-16 se calcula solo para las gestiones con `asistencia_pct` o `incumplimiento_actividades_pct` **realmente informados**. Se quitan los `COALESCE(…,0)` y `COALESCE(asistencia,100)`; si no hay dato, el valor es NULL.
  - En `FALTANTES` del router: *«No hay asistencia ni incumplimiento de actividades registrados en esta gestión.»*
  - `bi.vw_riesgo_estudiante.regla_d_desercion` sigue la misma regla (NULL, no 0), así que `k_reglas` y `nivel_prioridad` solo suman reglas con dato. L3 mide el efecto en KPI-17 (críticos) y en KPI-09.
  - Las 25.191 filas académicas tienen asistencia NULL e incumplimiento 0, y ese 0 también se considera «no informado» si la fuente no trae la columna. L3 verifica en el lector de ARCA si la columna existe y si viene vacía.
  - **Estimado:** KPI-16 pasa de 0,00 % en verde a **sin dato** en 2024–2025. El índice de Estudiantes y mercado pierde un KPI en verde.
- **DA3 — RESUELTA (Lean, 2026-11-20): mora = `cuotas_impagas ≥ 2`.** Una sola regla para `bi.vw_cmi_valores`, `bi.vw_cartera_estado`, `bi.vw_riesgo_estudiante` y `KPIService`. `estado_cartera` de la fuente queda solo como dato descriptivo.
  - **KPI-05:** estudiantes con ≥ 2 cuotas impagas sobre estudiantes con cartera.
  - **KPI-15:** deuda de esos estudiantes sobre la deuda total.
  - **KPI-04:** deja de usar `Previsionable` y pasa a ser el conteo absoluto de la misma regla, o se redefine para no duplicar el KPI-05 (propuesta en L4; la decide Lean).
  - **Estimado con la DW actual** (L4 lo confirma en tmpfs):

    | Gestión | KPI-05 hoy → nuevo | KPI-15 hoy → nuevo |
    |---|---|---|
    | 2024 | 94,28 % → **0,03 %** | 85,56 % → **0,00 %** |
    | 2025 | 53,11 % → **13,12 %** | 87,38 % → **12,00 %** |
    | 2026 | 75,33 % → **43,40 %** | 99,22 % → **27,82 %** |

  - **CORRECCIÓN (PLAN_FUENTES_UPLOADS.md §1):** la fuente **sí** trae cuotas en mora en 2024 (369 filas con ≥ 2). Quien pierde el dato es el ETL, así que las cifras estimadas de arriba no valen hasta FU-L2. Texto original:
  - ~~Nuevo hallazgo A3-bis:~~ en 2024 solo 1 de 3.188 estudiantes tiene ≥ 2 cuotas impagas. La fuente 2024 probablemente no trae el detalle de cuotas (`cuotas_impagas` = 0 por defecto), así que la cifra de 2024 sería otro «0 por falta de dato», igual que el KPI-16. L4 verifica en `BD Cobranzas.xlsx` si 2024 tiene columnas de cuotas. Si no las tiene, KPI-05 y KPI-15 de 2024 pasan a «sin dato» con motivo. 2023, con 2 filas, también queda sin dato.
- **DA4 — RESUELTA en `PLAN_FUENTES_UPLOADS.md`:** KPI-02 excluye toda gestión sin meta mensual real (2024 y 2023 → «sin dato»). Texto previo:
- ~~DA4 — DIFERIDA (Lean, 2026-11-20): se decide después del análisis de los archivos fuente.~~
  - Nueva tarea **L4-0** (`dev-baja`, solo lectura, antes de L4):
    - abrir `EJECUTADO VS META.xlsx` (doc 38) y `BD Egresos.xlsx` (doc 39);
    - documentar en `docs/mediciones/adw_l4_0_fuentes_metas.md` si 2024 trae metas mensuales, en qué hoja y columnas, o solo un total anual;
    - incluir las metas de 2023 (hoy vacías), si existen;
    - incluir los 10 `CONFLICTO_FUENTES` entre ambos archivos.
  - Con ese informe, Lean elige entre cargar la meta mensual real (si existe), excluir 2024 del KPI-02 o prorratearla.
  - L4 ejecuta mora (DA3) y mes parcial sin esperar DA4. Solo la parte de la meta 2024 queda bloqueada.
- **DA5:** metas y umbrales para KPI-01, 04, 09, 13, 14, 17, 21 y 22.
- **DA6 — RESUELTA en `PLAN_FUENTES_UPLOADS.md`:** KPI-06 = inscritos / leads de captación desde hojas programa×mes, con mapeo genérico; sin leads → «sin dato». Texto previo:
- ~~DA6 — DIFERIDA (Lean, 2026-11-20): se decide después del análisis.~~ Nueva tarea **L6-0** (`dev-baja`, solo lectura):
  - Revisar todas las hojas y columnas de `TBL_INSCRITOS.xlsx` (doc 44) y de los demás archivos del lote: ¿hay interesados, leads, prospectos, reservas o postulantes?
  - Explicar por qué `fact_marketing.leads` = 0 y `reservas` está lleno, y qué contiene `reservas` (¿sirve como embudo?).
  - Revisar el historial de la migración `014_conversion_captacion_comprobable.sql`: por qué se creó `*_captacion` y de qué fuente esperaba datos.
  - Salida: `docs/mediciones/adw_l6_0_fuente_captacion.md`, con tres opciones (fuente existente, redefinición con `reservas` o «no medible») y la cifra que daría cada una.
  - L6 avanza con el resto. KPI-06 sigue en «sin dato» con su motivo hasta que Lean decida.
- **DA7 — RESUELTA (Lean, 2026-11-20), con base en `docs/mediciones/adw_l8_0_filas_sin_estudiante.md`:**
  - **Catálogo de programas** (472 financieras + 750 académicas): descarte automático con motivo `CATALOGO_PROGRAMA_NO_PAGO` / `CATALOGO_PROGRAMA_NO_ALUMNO`. No van a la bandeja ni crean perfiles.
  - **Docentes** (68 académicas): descarte automático con motivo `DOCENTE_NO_ESTUDIANTE`.
  - **Residuales a la bandeja** (18): 2 pagos con CI existente (1.523 Bs), 7 estados académicos individuales sin identidad y 9 sin patrón. L8 investiga por qué CI_EXACTA no enlazó los 2 pagos.
  - **Perfil TEMP (estado B):** no se crea para ninguna clase.
  - Efecto: la bandeja deja de recibir 1.290 filas de ruido y recibe 18 con sentido. Las `FILA_FINANCIERA_SIN_ESTUDIANTE` ya no se tratan como «pagos que desaparecen» (aplica a 2 filas).
- **DA8 — RESUELTA (Lean, 2026-11-20): meta y recaudación cuentan TODAS las categorías (PROGRAMAS + TECHOS_CERRADOS).** Igual que `bi.vw_metas_mensual` y el CMI. El pronóstico financiero (`forecast_service.py`, `time_series_extractor.py`) ya no filtra por PROGRAMAS: avance de meta 31,4 % → **31,7 %** (= KPI-13), meta 2026 16.894.995 → 17.973.400, recaudado 5.309.447,68 → 5.695.043,78, pendiente OLS 2.436.142 → 2.360.252 Bs/año, CAGR 26,76 % → 22,85 %, RMSE del Caso 3 252.859 → 297.318 (`docs/mediciones/adw_da8_forecast_antes.json` / `_despues.json`). **Cambia cifras del pronóstico financiero: recongelar en L9.**
- ~~DA7 — DIFERIDA (Lean, 2026-11-20): se decide después del análisis.~~ Tarea **L8-0** (`dev-baja`, solo lectura, antes de L8):
  - Sacar de `stg_entidad_no_resuelta` las 474 `FILA_FINANCIERA_SIN_ESTUDIANTE` y las 834 `FILA_ACADEMICA_SIN_ESTUDIANTE` (payload, `clave_origen`, documento y hoja).
  - Clasificarlas: sin CI ni nombre / con nombre sin CI / con CI fuera de `dim_estudiante` / filas de totales o encabezados.
  - Sumar el monto (Bs) de las financieras que se perderían.
  - Salida, **sin PII** (CI y nombres enmascarados con el mismo criterio de `dataops_privacy.py`): `docs/mediciones/adw_l8_0_filas_sin_estudiante.md`.
  - Con eso, Lean decide para cada clase si va a la bandeja, se descarta o se crea un perfil TEMP (estado B, según el invariante). L8 ejecuta lo demás (aprobación en bloque, filas vacías y agrupación de CI_NOMBRE_DISCORDANTE) sin esperar DA7.

Al cerrar cada loop: pytest del loop (`tests/adw/`) · vitest (si toca front CMI) · commit acotado `adw(L<n>): …` · `CIERRE_ADW_L<n>.md`.

---

## PARTE 3 — Estado real y plan de cierre **PARTE B** (actualización 2026-11-21)

> **Frontera estricta (sin choque con `PLAN_FUENTES_UPLOADS.md` — PARTE A):**
> - **Alcance exclusivo de PARTE B:** auditoría de la Data Warehouse (`bi.vw_cmi_*`, `bi.ref_kpi`, serie predictiva), configuración del CMI, coherencia entre las perspectivas/áreas del frontend (CMI, Académico, Financiero, Auditoría, Reportes) y precheck/capturas finales.
> - **Regla de evaluación sin tocar el core:** no modificar `pipeline/` core, `tests/sprint*` ni el flujo DataOps (`routers/dataops/*`, `frontend/src/modules/dataops/*`, reservados a PARTE A).
> - **Archivos exclusivos de PARTE B:** `scripts/auditoria_dw/`, `backend/scripts/migrations/027_adw_l6_cmi_config.sql`, `backend/routers/cmi.py`, `frontend/src/modules/admin/cmi/*` (y `tests/adw/`).

### Avance verificado (rama `beto-integracion` · `03c1a6f`)
- **Cerrados:** `ADW-L0`, `ADW-L0b`, `ADW-L1`, `ADW-L5`, `ADW-L7`, `ADW-L8`, `ADW-DA8`, y `ADW-L9` parcial (`CIERRE_ADW_*.md`).
- **Reemplazados por PARTE A (`PLAN_FUENTES_UPLOADS.md`):** `ADW-L2` (por FU-L5), `ADW-L3` (por FU-L4), `ADW-L4` (por FU-L2/L6, **salvo A7/KPI-01 pendiente de decisión**), `ADW-L7-C4` (por FU-L1/L3).
- **Pendientes:** `ADW-L6` (Configuración CMI + migración `027`, parte no bloqueada por DA5), ajuste de perspectivas/áreas en front CMI, auditoría de serie predictiva/precheck DW y cierre final `ADW-L9` (`dev-alta`).

### Tareas pendientes PARTE B — `dev-baja` (auditoría SQL de solo lectura, diagnóstico, precheck y capturas)

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en `docs/mediciones/` |
|---|---|---|---|---|---|---|
| **ADW-B1** | **Auditoría SQL de la serie predictiva (`N = 33` vs `43` vs `40`):** consultar tmpfs + `time_series_extractor.py` + respuesta de `/api/v1/forecast/*` para explicar la discrepancia de `AVISO_CHAT3_ADW.md:23` (solo lectura). | `dev-baja` | — | ADW-B2, ADW-M1 | CSV con lista de meses por fuente (DW, extractor, API, SFV) y causa exacta de la diferencia. | `adw_l9_auditoria_n_predictiva.csv` |
| **ADW-B2** | **Diagnóstico de entorno y HTTP 502 en API:** (1) verificar en solo lectura las 6 fallas de entorno (`seqeval` / `statsmodels`) entre local y `giragroup_api` sin modificar `tests/sprint*` ni `requirements.txt`; (2) diagnosticar el **HTTP 502 Bad Gateway** observado en `http://localhost/api/v1/*` (`docker compose ps` + logs de `giragroup_api` / `giragroup_gateway`). | `dev-baja` | — | ADW-B1, ADW-M1 | JSON con estado de paquetes/servicios y causa raíz del 502. | `adw_diagnostico_entorno_api.json` |
| **ADW-B3** | **Precheck DW pre-recongelado (solo tmpfs + backup):** (1) `pg_dump` preventivo de `giragroup_db` en `backups/`; (2) probar doble aplicación idempotente de `022 → 023 → 024 → 025 → 026 → 027` en tmpfs limpia; (3) verificar SQL exacto **51 tablas + 10 vistas `bi` + 23 KPI en `bi.ref_kpi`**; (4) inventariar los **5** contenedores huérfanos (`fu_l6_pg_tmpfs`, `fu_l5_pg_tmpfs`, `adw_pg_tmpfs`, `beto_pg_tmpfs`, `beto_pg_f3w`). | `dev-baja` | ADW-M1 | ADW-B4 | Backup creado en `backups/`; doble aplicación `022..027` con exit code 0; SQL confirma `51 / 10 / 23`; inventario completo en JSON. | `adw_precheck_dw.json` |
| **ADW-B4** | **Unit tests front CMI + guardia «cero hex sueltos»:** tests Vitest para `DesglosePerspectiva.jsx` y `TarjetaKpi.jsx` (validando `captacion_mensual`, `captacion_cobertura`, `n_respuestas` y coherencia por perspectiva), más chequeo de cero `#RRGGBB` sueltos en `frontend/src/modules/admin/cmi/`. | `dev-baja` | ADW-M2 | ADW-B3 | `npx vitest run` 100 % verde; 0 hex sueltos en CMI. | `adw_cmi_vitest_resumen.txt` |
| **ADW-B5** | **Rebuild + capturas «después» por área (tras `FU-L9`/`ADW-L9`):** reconstruir `api`, `pipeline` y `web`, validar 9/9 servicios `Up` y `/health` 200 (0 errores 502/500), y capturar a 1440 px cada módulo/área (CMI 3 modos, Académico, Financiero, Auditoría, Reportes) + cruce web↔DW. | `dev-baja` | ADW-L9 (`dev-alta`) + ADW-M2 | — | 9/9 servicios `Up`; 0 errores 500/502; 1 PNG por pantalla + tabla de cruce. | `docs/mediciones/adw_l9_capturas/`, `adw_l9_cruce_web_dw.csv` |

### Tareas pendientes PARTE B — `dev-media` (vistas DW, configuración CMI y perspectivas del front por área)

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en `docs/mediciones/` |
|---|---|---|---|---|---|---|
| **ADW-M1** | **`ADW-L6` (parte NO bloqueada por DA5) + migración `027`:** (1) crear migración idempotente `027_adw_l6_cmi_config.sql` (sobre `026`, solo tmpfs) para asignar KPI-18 a la gestión del dato (sin usar `created_at`); (2) filtrar gestiones residuales con menos de `N` KPI con dato (ej. 2023) en `bi.vw_cmi_gestiones` o `routers/cmi.py`; (3) **solo si Lean responde DA5**: poblar metas/umbrales en `bi.ref_kpi` y definir KPI-13 vs KPI-03. | `dev-media` | `026` (PARTE A `FU-L6`) | ADW-B1, ADW-B2 | `pytest tests/adw/test_l6_cmi_config.py` 100 % verde en tmpfs; 51 tablas + 10 vistas `bi` + 23 KPI intactos; selector sin años residuales vacíos. | `adw_l6_cmi_config_antes_despues.csv` |
| **ADW-M2** | **Perspectivas del front ajustadas al área vista (CMI + módulos):** (1) exponer `n_respuestas` para KPI-19 y KPI-20 en `routers/cmi.py`; (2) en `DesglosePerspectiva.jsx:105-128`, sustituir la serie muerta `conversion_fuente` por `captacion_mensual` + `captacion_cobertura` y mostrar `n_respuestas` en `TarjetaKpi.jsx` / `CmiDetalleKpi.jsx`; (3) revisar que cada perspectiva del CMI (Financiera, Clientes/Estudiantes, Procesos Internos, Aprendizaje y Crecimiento) y los paneles de área (Académico, Financiero) muestren solo métricas y gráficas acordes al área vista, respetando `tokens.css` (cero hex sueltos, `serif-display`, `tabular-nums`, claro/oscuro). | `dev-media` | — | ADW-M1, ADW-B1 | `npx vitest run` y `npm run build` en verde; 0 errores 500 en `/cmi/perspectivas/*/detalle`; 0 hex sueltos en CMI. | `adw_perspectivas_front_revision.json` |

### Cierre final PARTE B — `dev-alta` (coordinado con `FU-L9`)
- **`ADW-L9`:** remedición final de los 23 KPI × 4 gestiones tras la recarga controlada, recongelado único en `docs/fuente_verdad_tesis.md` y aviso «ADW + FU congelado» al Chat 3.

### Decisiones pendientes de Lean que impactan PARTE B
- **DA5:** metas y umbrales para los 9 KPI sin umbral (`KPI-01, 04, 09, 13, 14, 17, 21, 22`) y definición de `KPI-13` vs `KPI-03`.
- **KPI-01 (A7):** denominador único para todos los años (`pagantes` o `matricula`).
- **Riesgo estudiantil (`52ecec0`):** confirmar si la base de `bi.vw_riesgo_estudiante` y `routers/riesgos.py` entran antes de `ADW-L9`.
- **Encuestas sin fecha / NPS (`CIERRE_FU_L5.md:40-42`)** y **serie predictiva `N = 33/43/40`** (tras `ADW-B1`).

## PROMPT PARA CHAT 2 — PARTE B (`dev-media` o `dev-baja`)
```text
/gira-desarrollar
Ejecuta SOLO la tarea <ADW-B1 | ADW-B2 | ADW-B3 | ADW-B4 | ADW-B5 | ADW-M1 | ADW-M2> de docs/cierres/PLAN_AUDITORIA_DW.md (PARTE 3 — PARTE B).
- NO toques pipeline/ core, tests/sprint* ni los archivos de DataOps (reservados a PLAN_FUENTES_UPLOADS.md — PARTE A).
- Hay cambios sin commitear de otras sesiones: haz git add SOLO de tus archivos (nunca git add -A).
- Migraciones (027) y pruebas solo en tmpfs; nunca sobre snapshot_dw_20261110_1201 ni la DW viva sin autorización.
- Si la tarea toca una DECISIÓN sin respuesta escrita de Lean (DA5, KPI-01, riesgo 52ecec0), implementa solo la parte no bloqueada y detente.
- Cierra con pruebas del ticket, evidencia en docs/mediciones/, commit acotado y CIERRE_ADW_L<n>.md.
```
