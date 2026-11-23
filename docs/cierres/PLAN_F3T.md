# PLAN F3T — 2026-11-16
Objetivo de la fase: que ninguna fila ya resuelta por una regla estructural (convenios, costos, rentabilidad) llegue a la revisión humana como «ESTUDIANTE», cualquiera sea la categoría del libro, y cerrar los pendientes de CIERRE_F3S antes de anunciar «F3 congelado».
Entrada: CIERRE previo leído = `CIERRE_F3S.md`; rama base = `beto-integracion` `d7ae167`.

## Hallazgo (DataOps real, lote #3 «BD Techos.xlsx», documento 20, DW viva)
- **Lo que pasa:** el lote tiene 207 filas: 176 convenios cargados y **30 casos pendientes** de tipo `ESTUDIANTE`, con motivo `BAJA_CONFIANZA_IA` e índice 0,577.
  - Cada caso es una fila completa de convenio: `N° | Gestión Techo | Coord.: Sharon | … | Insitución: CODESING | POS: 5165 | …`.
  - No hay ninguna persona que resolver: la CI es `TEMP` y el único nombre es el del coordinador.
  - Si se aprueba, falla con `revision.py:381-384` («trae la línea completa…»). Ese endpoint solo sabe resolver estudiantes.
- **Causa** (verificada en el código):
  - La regla de convenio (`registros_techo_convenio`) sí resuelve la fila, porque trae POS e institución (la errata «Insitución» se tolera).
  - Pero la exención de D-A8a, `fila_resuelta_por_regla` (`extraccion_por_encabezado.py:767-771`), solo se aplica cuando la categoría es `rentabilidad`.
  - Este libro se clasificó como **MARKETING**, así que su categoría es `marketing` (`consolidacion.py:200-208`).
  - Resultado: la fila pasa igual por el índice de persona y, por debajo de 0,60, cae a revisión.
  - La rama de convenios dentro de marketing existe en `pipeline.py:241`, pero la exención no la contempla.
- **Por qué la medición no lo vio:** el recorte 2026-03 de BD Techos tiene **1 fila** (`fact_techo_convenio` = 1). El ciclo mensual casi no ejercita convenios.
- **Para qué sirve la revisión humana:** existe para los casos en que el sistema duda **de una persona** (CI, nombre u homónimo) con índice < 0,85. La sugerencia que muestra la bandeja es la propuesta de BETO y de las reglas, y el auditor la confirma o la corrige. Estos 30 casos no deberían existir: ya están resueltos por regla y no hay ninguna persona que confirmar. Es un defecto (**D-T1**), no una revisión legítima.

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| T-1 | **D-T1**: que la exención dependa del **resultado de la regla** y no del nombre de la categoría. Una fila que `registros_rentabilidad`, `registros_costo_programa` o `registros_techo_convenio` convierte en hecho, en cualquier categoría donde el pipeline aplica esa regla (rentabilidad, marketing, admisión), no pasa por el índice de persona. La cascada no cambia: BETO sigue al final y solo para residuales | dev-media | — | T-2, T-5 | 1) prueba nueva con las 3 filas reales del documento 20 (11, 13 y 14) en un libro clasificado MARKETING: 0 casos `ESTUDIANTE`, 3 convenios; 2) en tmpfs, `BD Techos.xlsx` completo: `fact_techo_convenio` = todas las filas con POS + institución (número exacto en el JSON), 0 staging `ESTUDIANTE` y 0 sin explicar; 3) las pruebas de D-A8a y de orden de cascada siguen en verde | `f3t_d_t1.json` |
| T-2 | ¿Por qué `BD Techos.xlsx` completo se clasifica como **MARKETING** y no como TECHOS? Dar los puntajes por tipo de `detectar_tipo_fuente_por_cabeceras` para el libro completo y para el recorte. **Solo diagnóstico**: cambiar el clasificador afecta a los 10 archivos | dev-baja | — | T-1 | 1) puntajes por tipo y los tokens que los producen; 2) qué cambiaría en los otros 9 archivos si TECHOS ganara (lista, sin aplicar el cambio) | `f3t_clasificacion_techos.json` |
| T-3 | **¿Cambia la medición congelada?** Con T-1 aplicado, correr f3_base sobre el recorte. Si la huella es igual a `c8e10263…0153`, no se vuelve a medir nada. Si cambia, se repiten S-7 y S-8 completos | dev-alta | T-1 commit | — | 1) huella después de T-1 = N; 2) veredicto `sin_cambio` o `remedir`; 3) si es `remedir`, S-7/S-8 con los mismos criterios de PLAN_F3S | `f3t_huella_post_d_t1.json` |
| T-4 | **KPI-15**: la SFV de F3R decía 73,44 % y F3S dice 69,93 %, con el mismo cuadre 500 / 7 / 218. Escribir la fórmula exacta (`kpi_service.py`), el numerador y el denominador de cada valor, y cuál va en la SFV. El diagnóstico de `f2r_g5_kpi15.json` (725 «Vigente», TIPO DE CARTERA) queda como decisión de Lean | dev-baja | — | T-1, T-2 | 1) fórmula con archivo:línea; 2) 73,44 y 69,93 reproducidos con SQL, o señalado cuál está mal; 3) la SFV queda con un solo valor y su fuente | `f3t_kpi15_formula.json` |
| T-5 | **Lote #3 en la DW viva** (solo con el sí de Lean, DECISIÓN 1): después del rebuild con T-1, volver a procesar el documento 20 para que los 30 casos se conviertan en convenios. La idempotencia por `carga_fila_origen` evita duplicar los 176 ya cargados. **Antes, `pg_dump` de la DW viva** | dev-baja | T-1 + rebuild, DECISIÓN 1 | — | 1) dump previo con su sha256; 2) documento 20: 0 casos pendientes `ESTUDIANTE`, `fact_techo_convenio` del documento = 176 + 30 (o el número exacto con su motivo); 3) 0 convenios duplicados | `f3t_lote3_viva.json` |

## Comandos exactos por tarea
- T-1 y T-3: tmpfs con `TMPFS_PORT=55632 scripts/aislada_tmpfs.sh up/down`. El libro completo se lee de `uploads/data/` y el recorte de `output/backups/f0_lote/slices/`. Antes y después se verifican los sha del lote, del modelo y del snapshot.
- Rebuild después de T-1: `docker compose build api pipeline && docker compose up -d api pipeline`, **y después reiniciar `giragroup_gateway`** (nginx guarda la IP vieja; ya pasó en F3S). Verificar `/health` = 200.
- T-5: `pg_dump` de `giragroup_db` a `output/f3t/` antes de reprocesar. Nada en la DW viva sin el sí de Lean.

## Riesgos y control
- **Cascada (invariante):** T-1 no cambia el orden. Solo deja de pedir índice de persona a filas que una regla ya convirtió en hecho. Si la corrección exigiera mover a BETO, se detiene.
- **Alcance:** T-1 no toca el clasificador; eso lo decide T-2. T-1 tampoco cambia `revision.py`: con la causa corregida, esos casos ya no se crean. Si quedan casos sin persona en otro archivo, se registran.
- **Cambios locales de Lean** (`powerbi.py`, `frontend/`, PLAN/CIERRE_FRONT_V2): nunca se agregan. `git add` siempre con rutas explícitas.

## DECISIONES PENDIENTES PARA LEAN
1. **T-5 (DW viva):** ¿se vuelve a procesar el documento 20 para cargar los 30 convenios (recomendado, con `pg_dump` previo)? ¿O se borra el lote #3 y se carga de nuevo?
2. **Clasificación de BD Techos** (después de T-2): ¿se corrige el clasificador (implica volver a medir todo) o se deja como MARKETING con la rama de convenios?
3. **Pendientes de CIERRE_F3S:**
   - a) Las pruebas dependen de los 10 archivos de `uploads/data` (sin versionar) y de una tmpfs con el snapshot. ¿Se marcan como dependientes de datos locales o se documenta el requisito?
   - b) B-7 quedó con 1 corrida limpia por condición, pero el protocolo pide 3. ¿Lo aceptas así o se miden 2 más con la máquina limpia?
   - c) Diagnóstico de KPI-15 (decisión 3 de F2R).
   - d) Migración 016 en la DW viva, B-10 y merge a `main`.

## Al cerrar
pytest sobre el commit limpio (worktree, base tmpfs con el snapshot y las 10 entradas) · rebuild de `api` y `pipeline` + reinicio del gateway · commit `fix(f3t): D-T1 convenios resueltos por regla no van a revisión` y `docs(f3t): …` · `CIERRE_F3T.md`. El chat 1 anuncia «F3 congelado» solo después de revisar este CIERRE.

## PROMPT PARA CHAT 2
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F3T.md (base `beto-integracion` d7ae167).
D-T1: en el lote #3 (BD Techos, documento 20 de la DW viva) hay 30 filas de convenio que la regla `registros_techo_convenio` ya resuelve, pero que caen a revisión como ESTUDIANTE. La exención de D-A8a (`fila_resuelta_por_regla`) solo mira la categoría `rentabilidad`, y este libro quedó como MARKETING.
Orden: T-1, T-2 y T-4 en paralelo → commit de T-1 → rebuild + reinicio del gateway → T-3. T-5 solo con mi sí (DECISIÓN 1) y con `pg_dump` previo.
No cambies el orden de la cascada ni el clasificador. No agregues powerbi.py ni frontend/ a ningún commit.
