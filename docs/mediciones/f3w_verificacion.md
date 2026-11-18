# W-11 — Cierre técnico (pruebas, build y rebuild)

**Fecha:** 2026-11-17  
**Estado:** Listo para verificación visual en navegador (V1 y V2, claro/oscuro) y posterior ejecución de `W-14` en la DW viva.

## Resultados de pruebas y compilación
1. **Frontend (`cd frontend; npx vitest run`):**
   - **13/13 archivos, 78/78 pruebas aprobadas** (incluidas `w2TipoDocumental`, `w4FormulariosPorMotivo`, `w7NotificacionesBotones`, `w8CargaHistorial`, `w9MetricasModelo`, `w10Flujo3Pasos`, `w12RevelarPorFila`, y corrección de las 2 fallas en `v2Ronda5.test.jsx`).
2. **Build de producción (`cd frontend; npm run build`):**
   - **OK** (`vite build`, 2035 módulos transformados, 0 errores).
3. **Backend (`pytest`):**
   - Suite F3W (`test_w3_aprobacion_categorias.py`, `test_w4_formularios.py`, `test_w12_revelar_por_fila.py`, `test_w13_carga_fila_origen.py` con `--cov=services --cov=routers/dataops`): **52 passed, 0 failed**.
   - Nota sobre la suite completa (`pytest -q --no-cov`): **82 passed, 12 failed preexistentes** en `test_beto_ner_pipeline.py` (6 fallas por conexión local a PostgreSQL `:5432` sin `DATABASE_URL` y aserción de `markdown_report`) y `test_lote_estado_flujo.py` (6 fallas por `contar_hechos_en_revision` tras la división modular de `routers.dataops`).
4. **Rebuild de contenedores (`docker compose build api web` + `docker compose up -d api web`):**
   - `giragroup_api` y `giragroup_web` reconstruidos y levantados con el código actualizado.
   - `backend/main.py` actualizado para asegurar el constraint `dataops_tarea_tipo_check` con `PREPARACION_REVISION` al arrancar la API sobre `giragroup_db`.

## Pendiente (fuera de esta ejecución)
- Verificación visual en navegador (V1 y V2, claro y oscuro) de los 3 pasos con `[BBDD] ANTIGUO` y/o lote de prueba.
- `W-14`: recarga de los 10 libros por la web en la DW viva.

---

## Actualización 2026-11-17 (cierre del frontend y W-14)

### Defectos del frontend
| # | Defecto | Resultado |
|---|---|---|
| 1 | Falta `toDataopsPath` en `HumanReviewFlowView.jsx` | Ya importado (`HumanReviewFlowView.jsx:21`); grep: ningún uso sin import |
| 2 | Menú lateral V2 con 3 pasos | `SidebarV2.jsx` ya tiene 3 (Ingesta, Lectura de BETO, Revisión Humana) |
| 3 | Subtítulo «tres pasos» | Ya decía «tres pasos» (`BatchFlowHeader.jsx:92`); se corrigió el comentario «4 Pasos» de `App.jsx:417` |
| 4 | Barra superior V1 desborda a 375 px | Corregido (`Navbar.jsx`: etiqueta con clase; `tokens.css`: a ≤ 480 px se oculta la etiqueta, `min-width:0` y `max-width:100vw`). **Medido en el navegador a 375 px: `scrollWidth` = 375, sin desborde horizontal** (`floating-navbar` 375 px) |
| 5 | «Revelar correo» solo con dato de correo | Ya condicionado con `hasCorreo` (`HumanReviewFlowView.jsx`, `BetoReadingFlowView.jsx`, `TextoPreparadoTab.jsx`); prueba `w12RevelarPorFila.test.jsx` |

Prueba nueva: `frontend/src/modules/dataops/__tests__/w13Correcciones.test.jsx` (4 pruebas).

### Pruebas y despliegue
- `npx vitest run`: **14 archivos, 84 pruebas, todas en verde**. `npm run build`: **0 errores**.
- `docker compose up -d --build web`: `giragroup_web` reconstruido; `http://localhost/` responde 200 y el navegador carga la versión nueva.
- La suite de pytest completa con cobertura **no se volvió a ejecutar en esta actualización** (ver el estado de la actualización anterior de este archivo).

### Verificación visual (V1/V2, claro/oscuro)
Hecha solo parcialmente: a 375 px se midió la barra V1; el flujo de 3 pasos se recorrió en V2 (claro) con el lote real de la DW viva (carga, lectura de BETO y revisión). **No se hicieron capturas del modo oscuro ni de V1 por paso.**

### Hallazgos de la carga real (W-14)
Ver `f3w_recarga_dw_viva.json`. Resumen: la ingesta (10/10) y la lectura de BETO (116.557 tuplas) funcionaron; la preparación de revisión y la consolidación se detienen en la línea 104.250 y la consolidación termina en ERROR. 0 hechos cargados. Sirve como prueba de punta a punta fallida del flujo de 3 pasos.
- La interfaz muestra «Consolidar lote» inactivo si se reinicia la API después de leer (el resumen de lectura vive en memoria); se recupera con «Actualizar» en el paso ②.
- Un lote interrumpido deja una conexión a la BD «idle in transaction» que bloquea el borrado de sus documentos (`DELETE /sources/{id}`).
- «Historial de lotes» muestra (0) en la pantalla de carga aunque existan lotes en la BD (el contador y la tabla difieren según el estado).

---

## Actualización 2026-11-18 (bloqueo corregido y W-14 repetida)

- **Causa del bloqueo:** falta de memoria de la API, no un deadlock (`f3w_bloqueo_consolidacion.json`). Las 715.217 respuestas de evaluación y sus 1.632.508 trazas se guardaban en memoria hasta el final de la consolidación (`dw_loader.py`, `_eval_pendientes` y `_cfo_pendientes`); un worker llegaba a 2,4 GB en el clon y a 4,1 GB en la viva.
- **Corrección:** escritura por bloques de 50.000 y latido de la tarea. Misma huella de hechos en el clon; 17 pruebas en verde (`tests/f3w/test_bloqueo_consolidacion.py` y las de f3s, f3t, W-13 y W-5). `giragroup_api` reconstruido con el cambio y gateway reiniciado (`/health` 200).
- **Segunda carga por la web (lote #4):** INGESTA, LECTURA_BETO, PREPARACION_REVISION y CONSOLIDACION `COMPLETADA` (116.557 de 116.557), sin errores 5xx, sin OOM, sin reinicios y con un pico de memoria de la API de 5,5 GiB. Conteos finales en `f3w_recarga_dw_viva.json`.
- **Limpieza previa y duplicación:** el borrado de documentos por la API **no** borra hechos ni `carga_fila_origen` (FK `SET NULL` y sin FK). Antes de recargar se hizo `pg_dump` (`output/f3w/giragroup_db_pre_w14c.dump`, sha `f04081c8…e7d3`) y una limpieza SQL de la carga anterior en una transacción. Tras la recarga: 0 hechos huérfanos y `carga_fila_origen` con 1.632.508 filas y claves distintas. No se re-consolidó en la viva (en el clon la reconsolidación agrega 0 hechos).
- **Diferencia sin explicar:** `fact_marketing` 10.490 (viva, esta carga) frente a 10.486 (viva, carga anterior) y 10.464 (clon).
- **Sigue pendiente:** verificación visual completa V1/V2 en modo oscuro, pytest completo con cobertura en esta sesión y la aprobación de los casos de identidad.
