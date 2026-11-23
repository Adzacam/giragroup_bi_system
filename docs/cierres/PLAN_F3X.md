# PLAN F3X — 2026-11-18
Objetivo de la fase: cerrar lo que F3W dejó abierto (borrado que duplica datos, suite de pruebas que no se corrió completa, diferencias y riesgos sin explicar) para que F3V empiece sobre una base sana.
Entrada: CIERRE previo leído = `CIERRE_F3W.md`; rama base = `beto-integracion` `c45cdb5`, con los cambios locales de Lean (frontend V2 + frontend de F3W, `backend/routers/powerbi.py`) sin commitear.

## Revisión de CIERRE_F3W (chat 1)
Bien: W-0 a W-14 tienen evidencia en `f3w_*`. La DW viva quedó con los 10 libros cargados por la web con el código final (4 de 4 tareas `COMPLETADA`, 0 errores 5xx, respaldo previo). El bloqueo por memoria se corrigió con la misma huella de hechos. vitest 84/84 y el build pasan.

Lo que no se puede dejar así:
1. **Pruebas.**
   - La «suite completa» de `f3w_verificacion.md` tiene **94 pruebas (82 passed, 12 failed)**, cuando la suite completa tiene unas 845 (F3T: 829 passed). No se corrió entera.
   - De los 12 fallos, **6 no son de entorno**: `test_lote_estado_flujo.py` falla por `contar_hechos_en_revision` desde que `routers.dataops` se dividió en módulos. Es una regresión.
2. **Borrado.** `DELETE /sources/{id}` y `delete-batch` dejan los hechos y `carga_fila_origen` huérfanos (FK `SET NULL`). Borrar y recargar desde la web duplica datos (riesgo 1 del cierre).
3. **Evidencia contradictoria.** `f3w_verificacion.md` (línea 46) dice que W-14 terminó en ERROR con 0 hechos, y `f3w_recarga_dw_viva.json` dice que se completó. Es la corrida anterior al arreglo, pero el archivo no lo aclara.
4. **Sin explicar:**
   - `fact_marketing` da 10.464 en el clon, 10.486 en la carga anterior y 10.490 en la viva.
   - Hallazgo latente de W-6: con el guardado diferido, el completado del docente no alcanza a las respuestas de la misma consolidación. Si eso deja respuestas sin docente, es un defecto de datos.
5. **Riesgos operativos:**
   - Cada worker retiene unos 2 GB después de consolidar.
   - El vigilante de 180 s marca ERROR tareas que siguen vivas.
   - El resumen de la lectura de BETO vive en la memoria de la API: si la API se reinicia, «Consolidar» queda inactivo.

## Decisiones de Lean (18-nov)
1. **Borrado:** el endpoint borra, en una transacción, los hechos, el staging, los logs y `carga_fila_origen` del documento.
2. **Frontend V2 + F3W:** lo commitea Lean aparte. F3X **no** commitea `frontend/`; solo comprueba que vitest y el build sigan pasando.
3. **1.383 casos de identidad pendientes en la DW viva:** los aprueba o descarta Lean desde la web. No es una tarea del plan.

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| X-1 | **Borrado completo (DECISIÓN 1).** `DELETE /sources/{id}` y `delete-batch` borran en una sola transacción los hechos de las 9 tablas (`id_documento`), `bridge_modulo_docente` si corresponde, staging, `log_inconsistencias`, `log_pipeline_ingesta` y `carga_fila_origen` del documento. **No** borra dimensiones ni catálogo. Mismos roles que hoy y registro en auditoría | dev-media | — | X-2, X-3 | 1) pytest: cargar → borrar → 0 filas del documento en cada tabla; dimensiones sin cambio; 2) pytest: cargar → borrar → recargar → conteos iguales a la primera carga (±0); 3) en el clon `beto_pg_f3w`, lo mismo con [BBDD] ANTIGUO; 4) si algo falla a mitad de camino, rollback: 0 filas borradas | `f3x_borrado.json` |
| X-2 | **Suite completa de verdad.** (a) Corregir la regresión de `test_lote_estado_flujo.py` (`contar_hechos_en_revision` después de la división de `routers.dataops`): arreglar el import o la ruta en el código, **no** en la prueba, salvo que la prueba apunte a un módulo que ya no existe. (b) `test_beto_ner_pipeline.py`: las 6 pruebas que necesitan PostgreSQL usan `DATABASE_URL` hacia tmpfs, o se marcan `requires_db` con motivo, sin borrar aserciones. (c) Correr la suite completa en un worktree limpio de `c45cdb5` más los arreglos (sin los cambios locales de Lean), contra la tmpfs con el snapshot y las 10 entradas | dev-media | X-1 (commit) | X-3, X-4 | 1) número de pruebas colectadas ≥ 845 (comparar con F3T: 829 passed); 2) **0 failed**; 3) skips listados con su motivo; 4) cobertura total y por archivo; 5) hash del commit medido | `f3x_pruebas.json`, `f3x_cobertura_archivos.csv` |
| X-3 | **Marketing 10.464 / 10.486 / 10.490.** Comparar, por documento, módulo y mes, el clon (W-13), la carga anterior en la viva (si está en `giragroup_db_pre_w14c.dump`) y la carga actual. Dar la fila de origen de cada diferencia | dev-media | — | X-1, X-2 | 1) las 26 filas de diferencia explicadas una por una (o por grupo con su regla), con archivo:línea; 2) veredicto `regla_correcta` o `defecto` | `f3x_marketing_delta.json` |
| X-4 | **Docente en las respuestas (hallazgo de W-6).** En el clon, comparar `fact_evaluacion_docente` de [BBDD] ANTIGUO y de Evaluación Docente y Unifranz con el código de `18c8bc3` (antes del guardado diferido) y con el actual: cuántas respuestas tienen el docente en NULL o distinto. Si hay diferencia, corregir para que el completado del docente se aplique antes de escribir el bloque | dev-media | — | X-1, X-3 | 1) respuestas con docente NULL antes = N1 y después = N2; 2) si N2 > N1, se corrige y N2 = N1 con prueba nueva; 3) la huella del resto de columnas no cambia | `f3x_docente_respuestas.json` |
| X-5 | **Robustez de las tareas.** (a) El vigilante respeta el latido: una tarea con latido reciente no pasa a ERROR, con prueba. (b) El resumen de la lectura de BETO se reconstruye desde la base cuando no está en memoria, de modo que «Consolidar» se habilita después de reiniciar la API. (c) Memoria: medir el RSS de cada worker antes y después de consolidar [BBDD] ANTIGUO y aplicar la medida más simple que la libere (liberar las estructuras al terminar, `gc.collect()`, o reciclar el worker con `--max-requests` en `docker-compose`). No cambia qué se carga | dev-media | X-4 (mismo loader) | — | 1) prueba del vigilante; 2) prueba de reinicio: después de reiniciar, `GET` del resumen ≠ vacío y «Consolidar» queda habilitado; 3) RSS después de consolidar ≤ RSS en reposo + 300 MB, o el worker se recicla, con números; 4) misma huella de hechos | `f3x_robustez_tareas.json` |
| X-6 | **Evidencia y residuos.** (a) `f3w_verificacion.md` aclara que la sección de la línea 46 es la corrida anterior al arreglo y apunta a `f3w_recarga_dw_viva.json`. (b) DW viva: listar los lotes vacíos #1–#3 y el tamaño de `cache_indice_beto`. Con X-1 desplegado, borrar los lotes vacíos solo con el sí de Lean (DECISIÓN 1 de abajo) | dev-baja | X-1 + rebuild | — | 1) evidencia sin contradicción; 2) lotes vacíos: conteo antes y después (o «pendiente de Lean») | `f3x_residuos.json` |

## Comandos exactos por tarea
- Clon: `beto_pg_f3w` (127.0.0.1:55634), restaurado desde `output/f3ub/f3u_completo.dump`. **Nada contra la DW viva** salvo X-6(b), y eso solo con el sí de Lean y con `pg_dump` previo.
- X-2: `git worktree add ../gira_f3x_limpio <hash>`; `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest --cov=backend --cov=pipeline --cov-report=json:...` con `DATABASE_URL` hacia la tmpfs; al final, `git worktree remove`.
- Frontend sin commit: al cerrar, `cd frontend && npx vitest run && npm run build` solo para comprobar que nada se rompió.
- Rebuild de `api` después de X-1, X-4 y X-5 → reiniciar `giragroup_gateway` → `/health` 200.

## Riesgos y control
- **Invariantes:** la cascada, los umbrales y los estados no se tocan. X-1 cambia el borrado, no la carga. X-4 y X-5 tienen que dejar la misma huella de hechos, salvo la corrección del docente si X-4 la confirma; esa diferencia se reporta aparte.
- **Commits:** `git add` con rutas explícitas; **nunca** `frontend/`, `backend/routers/powerbi.py` ni `uploads/otras_versiones/`.
- **La DW viva tiene datos de Lean** (1.383 casos en revisión): X-6(b) no toca lotes con documentos.

## DECISIONES PENDIENTES PARA LEAN
1. ¿Se borran los lotes vacíos #1–#3 de la DW viva con el borrado nuevo (X-6b)? Recomendado: sí, con `pg_dump` previo.
2. **Después de F3X viene F3V:** implementar PLANIFICACION con el diseño B (51 tablas, 10 hechos, 23 KPI: cambia invariantes ya aprobados en F3U-B). Luego, la medición final con el código definitivo: f3_base con 2 corridas, B-7 con 3 corridas por condición en «Alto rendimiento», lote 1.387, KLM y SFV (encabezado, huella, «corridas limpias»). Recién ahí se anuncia «F3 congelado».

## Al cerrar
pytest completo (X-2) + cobertura · vitest y build solo como comprobación · rebuild de `api` y reinicio del gateway · commit `fix(f3x): borrado completo, suite completa y robustez de tareas` (solo backend, pruebas, scripts y docs) · `CIERRE_F3X.md`. **No se anuncia «F3 congelado».**

## PROMPT PARA CHAT 2
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F3X.md (base `beto-integracion` c45cdb5; los cambios locales de Lean en frontend/ y powerbi.py no se tocan ni se commitean).
Decisiones: el borrado de un documento elimina en una transacción sus hechos, staging, logs y carga_fila_origen (X-1). El frontend lo commitea Lean aparte. Los 1.383 casos de identidad los resuelve Lean en la web.
Orden: X-1, X-3 y X-4 en paralelo → commit de X-1 → X-2 (suite completa en un worktree limpio, ≥ 845 pruebas, 0 failed) → X-5 → X-6.
Todo contra el clon beto_pg_f3w. En la DW viva, solo X-6(b), y solo con mi sí y `pg_dump` previo.
No des por cumplido ningún criterio sin su archivo en docs/mediciones/. Escribe CIERRE_F3X.md. No anuncies «F3 congelado».
