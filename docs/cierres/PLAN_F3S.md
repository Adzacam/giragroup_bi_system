# PLAN F3S — 2026-11-16
Objetivo de la fase: corregir D-A9, D-A4 y D-A8a, reclasificar D-A8b como dato correcto de la fuente, actualizar la colección de Newman, medir pytest sobre el commit limpio y volver a medir todo lo congelado para anunciar «F3 congelado» sin limitaciones graves.
Entrada: CIERRE previo leído = `CIERRE_F3R.md` y `CIERRE_F3R_A.md`; rama base = `beto-integracion` `e3f4590`.

## Decisiones de Lean (16-nov)
1. **Defectos: corregir y volver a medir.** Se corrigen D-A9, D-A4 y D-A8a. **D-A8b no es defecto (Lean, 16-nov): 10.719.694 es la meta real de diciembre de 2024 de TECHOS/CERRADOS** y se carga tal cual. D-A4b, D-A5 y D-A2 se quedan como limitaciones declaradas en la Sección H de la SFV, sin cambios.
2. **Newman: actualizar la colección** `docs/api/postman_collection.json` para que use las rutas vigentes y volver a correrla.
3. **pytest: se mide sobre el commit limpio**, en un worktree sin los cambios locales de Lean (`backend/routers/powerbi.py`, `frontend/`).

## Por qué no se anuncia todavía «F3 congelado»
Esto es lo que quedó en CIERRE_F3R: un archivo entero de evaluación docente se descarta (D-A4: 1.137 filas del recorte y 16.629 del libro), BETO intercepta 4 filas de metas (D-A8a: 91 de 95 registros), la SFV llama «distorsionado» a un dato que es correcto (D-A8b), Newman tiene 17 de 23 aserciones fallidas y pytest dio 1 fallo por cambios sin commit. Además, `dw_vacio` no estaba vacía (D-A9). Nada de eso puede quedar en la versión congelada de la tesis.

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| S-1 | **D-A9**: agregar `public.carga_fila_origen` al `TRUNCATE` de `scripts/aislada_tmpfs.sh:16` y revisar que no falte otra tabla con datos (staging, log, cache, carga) | dev-baja | — | S-2, S-3, S-5, S-6 | 1) después de `up`, `dw_vacio` tiene **0 filas** en todas las tablas `fact_*`, `stg_*`, `log_*`, `carga_fila_origen`, `staging_registros_crudos` y `dim_origen_documental` (catálogo y `bi.ref_*` se conservan); 2) lista de tablas con su conteo | `f3s_dw_vacio.json` |
| S-2 | **D-A4**: que la consolidación respete `staging_registros_crudos.categoria` cuando la hoja quedó como `evaluacion_docente` (Likert) aunque el documento esté como `ACTA` (`consolidacion.py:193-200`). Prueba nueva con un libro de dos hojas, una de actas y una Likert | dev-media | — | S-1, S-3 | 1) prueba nueva en verde; 2) sobre el recorte, `Experiencia Docente 2.0.xlsx` aporta **> 0** hechos a `fact_evaluacion_docente` y cada fila no cargada tiene motivo registrado (sin explicar = 0); 3) los hechos de los otros 9 archivos no cambian (conteo por tabla y por documento igual que en f3_base, salvo evaluación) | `f3s_d_a4.json` |
| S-3 | **D-A8a**: primero diagnosticar por qué 4 filas que la regla de rentabilidad ya resuelve (categoría + mes) llegan a BETO y salen como `ESTUDIANTE`. Después corregir **sin cambiar el orden de la cascada**: BETO sigue al final, solo para residuales, y no debe recibir una fila que una regla ya resolvió | dev-media | — | S-1, S-2 | 1) causa con archivo:línea; 2) prueba nueva con las 4 filas (`PROGRAMAS JUNIO`, `TECHOS/CERRADOS FEB/ABR/OCT`) en verde; 3) `fact_rentabilidad` del recorte = **95** y 0 filas de `EJECUTADO VS META` en staging como `ESTUDIANTE`; 4) la prueba de orden de cascada existente sigue en verde | `f3s_d_a8a.json` |
| S-4 | **D-A8b, sin cambios de código**: comprobar en la copia del snapshot (solo lectura) que la meta de TECHOS/CERRADOS de diciembre de 2024 es 10.719.694 y que es la única meta registrada de 2024, y dejar KPI-02 2024 = 6,25 % y KPI-03 2024 = 102,26 % recalculados con su consulta. En la SFV, D-A8b sale de la tabla de defectos y la nota de la línea de KPI-02 2024 dice solo el hecho: «en 2024 la fuente registra meta solo para diciembre (TECHOS/CERRADOS, 10.719.694 Bs)», sin «distorsionado» | dev-baja | — | S-1..S-3, S-5 | 1) meta de diciembre de 2024 = 10.719.694 y 0 metas en los demás meses de 2024, con la consulta guardada; 2) KPI-02/03 2024 iguales a los de la SFV (Δ = 0); 3) snapshot sha `14D45F5A…E2EB` igual antes y después | `f3s_d_a8b.json`, `f3s_d_a8b.sql` |
| S-5 | **Newman**: actualizar `docs/api/postman_collection.json` a las rutas y contratos vigentes y volver a correrla | dev-baja | — | S-1..S-4 | 1) cada petición apunta a una ruta de `f3r_inventario_api.json` (136 rutas); 2) **no se borran ni se debilitan aserciones**: el código de estado y el esquema siguen comprobándose, y el diff de la colección queda guardado; 3) 0 aserciones fallidas, o cada fallo restante es un defecto real con su ruta | `f3s_newman.json`, `f3s_newman_diff.txt` |
| S-6 | **pytest sobre el commit limpio**: `git worktree add` del commit de código de S-1..S-3, sin los cambios locales de Lean; suite completa con cobertura JSON | dev-baja | commit de código de S-1..S-3 | — | 1) **0 failed**; 2) collected, passed, skipped y xfailed con sus números; 3) cobertura total y por archivo; 4) hash del commit medido escrito en el JSON | `f3s_pruebas.json`, `f3s_cobertura_archivos.csv` |
| S-7 | **Volver a medir todo lo congelado** con el código corregido y `dw_vacio` vacía, como **una sola tarea**: f3_base sobre el recorte 2026-03 (huella v2 nueva, PYTHONHASHSEED=0, dos corridas con huella idéntica), extracción R3-1 (staging, bandeja, B-9, fuente_resolucion, KPI-10/11/18, cuadre KPI-15), B-7 (3 corridas con caché vacía + 3 con caché llena), KLM con W = p95 medido (sensibilidad W = 0/10), lote 1.387 (2 corridas) y Locust | dev-alta | S-1..S-3, S-6 | — | 1) dos corridas de f3_base con la misma huella; 2) RNF-03: la mediana con caché vacía y con KLM queda en < 15 min, o se declara en < 20 con su cifra; 3) cobertura por archivo con el script de A-1: D-A4 y D-A8a cerrados y 0 sin explicar; 4) cada cifra que cambie frente a F3R queda listada (anterior → nueva) en el JSON de comparación, **solo para el CIERRE, no para la SFV** | `f3s_base.json` + huella, `f3s_b7_corridas.json`, `f3s_klm.json`, `f3s_lote_1387.json`, `f3s_lote_1387_r2.json`, `f3s_locust.json`, `f3s_cobertura_por_archivo.json`, `f3s_cambios_vs_f3r.json` |
| S-8 | **Actualizar la SFV** con las cifras de S-4..S-7: Sección H (D-A9, D-A4 y D-A8a pasan a corregidos; D-A8b sale de la tabla (dato correcto de la fuente, con la nota de S-4); D-A4b, D-A5 y D-A2 siguen como limitaciones), Newman, pytest y la nueva huella en el encabezado. Actualizar `f3_sfv_trazabilidad.json` | dev-media | S-7 | — | 1) `verificar_sfv.py` **0 / 0 / 0**; 2) 0 menciones de «v1/v2», «F3R», «antes/después», «corregido en», «versión anterior»; 3) toda cifra que cambió apunta a un archivo `f3s_*` | `f3s_sfv_verificacion.txt` |

## Comandos exactos por tarea
- Base: `TMPFS_PORT=55632 scripts/aislada_tmpfs.sh up` (después de S-1) / `down` al terminar. Antes y después: lote `aafde8ad…db60`, modelo `9ff7fb9d…5f92`, snapshot `14D45F5A…E2EB`, flags BETO en False.
- Recorte: `CICLO_REUSAR_SLICES=1` con `output/backups/f0_lote/slices/`, igual que en f3_base. La SFV dice explícitamente que es el ciclo mensual 2026-03.
- S-6: `git worktree add ../gira_f3s_limpio <hash>`, luego `cd ../gira_f3s_limpio`, `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest --cov=backend --cov=pipeline --cov-report=json:...`, y al final `git worktree remove`.
- S-7 usa el mismo protocolo que B-7 (`f2r_g6_protocolo_b7.md`) y los mismos topes del lote 1.387. Nada se mide sobre la DW viva.

## Riesgos y control
- **RNF-03**: f3_base ya tarda 856 s (14,27 min). Con D-A4 corregido entran unas 1.137 filas más de evaluación, así que **puede pasar de 15 min**. No se optimiza dentro de esta fase: se mide y se declara. Si pasa de 20 min, se detiene y se avisa a Lean.
- **Cascada**: S-3 no puede cambiar el orden CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO. Si la corrección lo exige, se detiene: es una DECISIÓN de invariante.
- **Cambios locales de Lean**: no se agregan `backend/routers/powerbi.py`, `frontend/`, `PLAN_FRONT_V2.md` ni `CIERRE_FRONT_V2.md`. Siempre `git add` con rutas explícitas; nunca `-A` ni `.`.
- **Newman**: se prohíbe que la colección pase solo porque se quitaron aserciones. El diff (S-5, criterio 2) es la evidencia.
- **Cifras que cambian**: la SFV queda escrita con el valor vigente, sin narrar el cambio. El historial queda en `f3s_cambios_vs_f3r.json` y en el CIERRE.

## DECISIONES PENDIENTES PARA LEAN
0. ~~Celda 10.719.694~~ **Respondida (16-nov): es la meta de diciembre de 2024 de TECHOS/CERRADOS (opción b). Se carga tal cual; no se cambia código.** La evidencia de abajo queda como contexto.
1. **Celda 10.719.694 (META POR CATEGORIA 2024, TECHOS/CERRADOS diciembre).** ¿Qué es en el negocio?
   - Evidencia (lectura del Excel, 16-nov): es el valor de la celda **E25** de la hoja EJECUTADO, escrito a mano, sin fórmula. Es la única celda con valor en la columna E (E2:E25).
   - El ejecutado total de 2024 (PROGRAMAS 9.989.730,09 + TECHOS 972.000,32 = 10.961.730,41) dividido entre 10.719.694 da **102,26 %**, exactamente el KPI-03 de 2024 de la SFV.
   - El ejecutado total de diciembre de 2024 (670.367,88) dividido entre 10.719.694 da **6,25 %**, exactamente el KPI-02 de 2024.
   - Conclusión: el valor funciona como **meta anual 2024 de toda la institución**, no como la meta de diciembre de TECHOS. KPI-03 de 2024 sale coherente; KPI-02 de 2024 no.
   - La celda K25 («EJEC. 2025» = 13.482.928,4, también escrita a mano) es el mismo caso para 2025, pero la regla ya la ignora.
   - a) **(Recomendada)** Es la meta anual 2024. Regla: si una columna `META POR CATEGORIA AAAA` tiene un solo valor en todo el año, ese valor se toma como **meta anual del año** (para KPI-03) y no como meta mensual de esa categoría y mes. La celda se registra en `log_inconsistencias` como `META_ANUAL_EN_CELDA_MENSUAL`. Resultado: KPI-03 2024 = 102,26 % y KPI-02 2024 = N/D (no hay meta mensual en 2024).
   - b) Es la meta real de diciembre y se carga tal cual.
   - c) La meta 2024 de TECHOS no existe: toda la columna de 2024 se ignora para esa categoría.
2. B-10 (residual) y el merge de `beto-integracion` a `main` siguen pendientes, fuera de esta fase.

## Al cerrar
pytest en el worktree limpio (S-6) · rebuild de backend y del worker con los cambios de S-2 y S-3 · commits separados: `fix(f3s): D-A4, D-A8a y dw_vacio` (código y pruebas) y `docs(f3s): nueva medición congelada y SFV` (mediciones, SFV, colección de Postman, CIERRE) · `docs/cierres/CIERRE_F3S.md` con la tabla de cambios frente a F3R y la verificación 0/0/0. **No se anuncia «F3 congelado»**: eso lo hace el chat 1 después de revisar el CIERRE.

## PROMPT PARA CHAT 2
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F3S.md (base `beto-integracion` e3f4590).
Lean decidió corregir D-A9, D-A4 y D-A8a y volver a medir (D-A8b no es defecto: 10.719.694 es la meta real de diciembre de 2024; S-4 solo lo comprueba y ajusta la nota de la SFV); actualizar la colección de Newman sin debilitar aserciones; y medir pytest sobre el commit limpio en un worktree.
Orden: S-1, S-2, S-3, S-4 y S-5 en paralelo → commit de código → S-6 → S-7 (dev-alta, una sola tarea) → S-8.
No cambies el orden de la cascada. No agregues backend/routers/powerbi.py ni frontend/ a ningún commit. `git add` siempre con rutas explícitas.
Si RNF-03 pasa de 20 min o la huella de f3_base no se repite en las dos corridas, detente y avisa.
La SFV final no menciona versiones ni cambios; el historial va en f3s_cambios_vs_f3r.json y en CIERRE_F3S.md.
