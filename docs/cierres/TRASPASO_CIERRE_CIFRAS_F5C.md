# TRASPASO al chat 1 — Cerrar las cifras pendientes con UNA sola fuente oficial

Origen: chat 2, tras entregar `ACTUALIZACION_DOCX_F5C.md` y `TABLAS_ACTUALIZADAS_F5C.docx`.
Objetivo del usuario: que toda cifra de la tesis salga del sistema, que exista **una sola versión oficial** (la SFV `docs/fuente_verdad_tesis.md`, etiqueta CONGELADO) y que el documento se ajuste a ella una sola vez.

Este archivo **no cambia ninguna cifra, umbral ni invariante**. Solo clasifica lo pendiente y propone el orden. Las decisiones de la columna «Lean» no las toma ningún chat.

## 1. Regla de "una sola versión"

1. Toda cifra del docx cita un ID de la SFV (A-01, E-03, J2-14...). Sin ID, no entra.
2. Cifra que ya no tiene respaldo **se elimina o se mide**; no se deja la vieja «como histórica» al lado de la nueva.
3. Las cifras retiradas se anotan en la SFV (como J1-15: 75,66 % RETIRADA) para que no reaparezcan.
4. Archivos de `docs/evidencias/` que respaldan una cifra (p. ej. `f1_beto_int8_*.json`) se **mueven o copian a `docs/mediciones/` y se registran en la SFV**, o la cifra se elimina.
5. Tras aplicar todo, una verificación de solo lectura compara los números del docx con la SFV (propuesta en la tarea Z-5). El docx no se modifica desde este repositorio.

## 2. Clasificación de los pendientes

### A. Se puede sacar del sistema (medición o cálculo; chat 2 con un PLAN)

| ID | Qué hacer | Cómo | Agente |
|---|---|---|---|
| D-13 | Tiempo por petición (Tabla 3.31, ¶3917) | Volver a correr Newman con reporte JSON sobre la copia tmpfs; guardar en `docs/mediciones/` | dev-media |
| D-10 | Pruebas por suite (Tablas 3.25 r7, 3.29; ¶2925, ¶2927, ¶3231, ¶3553) | `pytest --collect-only` / junit por carpeta; las filas deben sumar 924 | dev-media |
| D-11 | Cobertura por archivo (Tabla 3.30) | `pytest --cov=backend --cov=pipeline --cov-report=json` en el worktree limpio de `84cd352`; el detalle debe sumar 72,69 % | dev-media |
| D-17 | Filas por tabla del Apéndice F (Tabla F.1) | `scripts/diccionario_datos_csv.py` sobre la copia tmpfs del snapshot; contar objetos reales (59 vs 61) | dev-media |
| D-05 | Pronóstico ingenuo estacional (Tablas 3.24 r3, 3.36 r5, 4.1 r3, 4.7 r3) | Medir sobre N = 43 en tmpfs con el mismo hold-out de 6 meses; si no se puede, eliminar la comparación | dev-media |
| D-06 | OLS mensual N = 40 (Tablas 3.24 r5, 4.7 r4) | Medir sobre la copia tmpfs y congelar en la SFV. Hoy la SFV E-08 da Holt-Winters para otra serie; el invariante de CLAUDE.md no tiene medición | dev-media |
| D-09 | Carga del libro ARCA (27.692 hechos en 734 s, ¶4005) | Medir con el lote F5C o eliminar | dev-media |
| 3.34 r1–r3 | Medias por etapa y total de máquina | Calcular media y DE de `f5c_b7_corridas.json → corridas.*.etapas_s` (n = 3). No requiere medir de nuevo | dev-media |
| D-04 | 93,80 % / 6,20 % con o sin cédula; filas brutas/descartadas por libro (Tablas 3.17, 4.2) | Agregar el cálculo a `scripts/inventario_corpus.py` y congelar; o eliminar | dev-media |
| D-14 / D-15 | −3,06 pts por INT8; 97,27 % de nombres no vistos | Registrar `f1_beto_int8_*.json` en `docs/mediciones/` y en la SFV; D-15 medir sobre gold o eliminar | dev-media |

### B. Reemplazo por cifra que la SFV ya tiene (sin medir; solo texto)

| ID | Reemplazo |
|---|---|
| D-07 | Quitar 756 de 1.044. Usar B-09 de `f3_base` (2 CI_NOMBRE_DISCORDANTE + 2 CI_DUDOSA de 32 pendientes) o retirar el argumento. 1.044 de las alertas DATAOPS_CALIDAD es otra cosa |
| D-08 | Usar A-15/A-17 (BETO resolvió 3.382 de 11.560 entidades en el lote) y A-20 (14.408 líneas BETO en f3_base) |
| D-12 | 11 pruebas / 95,3 % → `bandeja_grupos.py` 92,99 % (`f3v_cobertura_archivos.csv`) |
| D-16 | «1.606 casos» → 700 casos en 10 grupos (f3_base) |
| D-18 | Texto: quitar «y de matrícula (N = 33)» si se retira el Gráfico 3.5 |
| Tabla 3.34 r4 | KLM 474,0 s, 700 casos en 10 grupos, 67 manuales |

### C. Decisión de Lean (ningún chat decide)

| ID | Decisión | Recomendación del chat 2 |
|---|---|---|
| D-01 RNF-03 | El docx dice que cumple (9,2 min); la SFV dice que no (20,52 min con caché llena + KLM; 31,75 min con caché vacía + KLM) | Declararlo con la cifra real. Optimizar y volver a medir es una fase aparte, con lote congelado nuevo. Cambiar el criterio de medición solo con decisión escrita de Lean |
| D-02 Likert | Instrumento válido (Tabla 4.4 del docx vs `f5_likert_pretest.json`, n por ítem de 4 a 9) | Elegir **un** instrumento, congelarlo como DATO_DE_LEAN en la SFV y rehacer 4.4, 4.9 y Gráfico 4.6 desde él |
| D-03 Línea base 600 min / 8–12 h-persona / 6 archivos | Mantener como DATO_DE_LEAN | Mantener, rotulado como dato de Lean, sin presentarlo como medición |
| Invariante OLS mensual N = 40 | Medir (D-06) o cambiar el invariante | Medir primero |

## 3. Orden propuesto

1. **Chat 1:** escribe `PLAN_F5S` (cierre de cifras) con las tareas de la sección A. **Todas las tareas con el agente `dev-media` (Claude Sonnet 5.5, esfuerzo medio)**, por decisión del usuario; no se reparte entre `dev-baja` y `dev-media`. Si el chat 1 ve una tarea que exige `dev-alta` (p. ej. un cambio de cascada o esquema), lo dice antes de asignarla.
2. **Lean:** responde D-01, D-02, D-03 y la regla de la sección 1 (en paralelo, no bloquea el paso 3).
3. **Chat 2:** ejecuta `PLAN_F5S`; cada medición queda en `docs/mediciones/` y se agrega a la SFV con CONGELADO una sola vez (SFV refrozada, SFV-verificación 0/0/0).
4. **Chat 4:** regenera Gráficos 3.2, 4.1, 4.3, 4.5 (con las dos condiciones frente a los umbrales de 15 y 20 min) y la figura 3.17; antes, corregir `scripts/generar_figuras_f4.py`.
5. **Chat 3:** emite la lista final «Lugar / Buscar / Reemplazar por» **desde la SFV nueva** y reemplaza las versiones anteriores (`ACTUALIZACION_DOCX_F5C.md` y `TABLAS_ACTUALIZADAS_F5C.docx` quedan marcados como superados).
6. **Chat 2 (tarea Z-5):** `scripts/verificar_docx_vs_sfv.py`, solo lectura del docx: lista cada número del docx sin ID de la SFV. Resultado en `docs/mediciones/`.

## 4. Pendientes técnicos conocidos de este chat

- Cambios previos sin commit en `backend/routers/powerbi.py`; el fallo de `test_powerbi_retencion` viene de ahí y no se corrigió.
- Archivos sin commit de este chat: `ACTUALIZACION_DOCX_F5C.md`, `TABLAS_ACTUALIZADAS_F5C.docx`, `TABLAS_ACTUALIZADAS_F5C_notas.md`, `TRASPASO_RNF03_F5C.md`, este traspaso y los cambios de `PLAN_F5V.md`.
- Inconsistencias que el cierre debe resolver: Tabla 4.2 (66.485 / 92.946 vs 90.538), Tabla 4.3 (381 vs 268), Tabla F.1 (61 vs 59), Tabla 3.30 (72,42 vs 72,69 %), KPI-15 2024 y KPI-18 2024/2025 sin cifra.
- Relacionado: `TRASPASO_RNF03_F5C.md` (la decisión D-01 ya está planteada ahí).
