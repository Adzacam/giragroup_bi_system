# CIERRE F3W — 2026-11-18

Rama / commit: `beto-integracion`. Base `18c8bc3`. Commit de la fase con backend, pruebas, scripts y documentos (rutas explícitas; hash en el commit siguiente). **El frontend de F3W no está en ese commit**: casi todos los archivos de `frontend/src/modules/dataops/` importan componentes de `frontend/src/v2/` (`AnimatedNumberV2`, `toDataopsPath`…), y Lean decidió que el frontend V2 se commitea aparte; los cambios de F3W en el frontend (DataOps, notificaciones, `App.jsx`, `Navbar.jsx`, `Sidebar.jsx`, `tokens.css` y `v2/`) siguen en el árbol de trabajo y entran con el commit de la V2. `backend/routers/powerbi.py` y los demás cambios locales de Lean quedan fuera.

**No se anuncia «F3 congelado».**

## Hecho
- **W-0 a W-13** con sus salidas en `docs/mediciones/f3w_*` (línea base, purga del lote #18, recorrido por archivo, diferencias de F3U-B, tipo documental, aprobación por categoría, formularios, dos fases, rapidez, notificaciones, carga e historial, métricas del modelo, flujo de 3 pasos, revelar por fila, `carga_fila_origen`).
- **Cinco defectos del frontend:** `toDataopsPath` importado (ya estaba), menú V2 con 3 pasos (ya estaba), subtítulo «tres pasos» (ya estaba; se corrigió un comentario «4 Pasos»), barra V1 a 375 px (corregida y medida: `scrollWidth` 375, sin desborde) y «Revelar correo» solo con dato de correo (ya estaba). Prueba nueva `w13Correcciones.test.jsx`.
- **W-11:** `npx vitest run` 14 archivos / 84 pruebas en verde; `npm run build` sin errores; `web` y `api` reconstruidos (`/health` 200). Evidencia: `f3w_verificacion.md`.
- **Bloqueo de la consolidación corregido:** la API se quedaba sin memoria al guardar hasta el final 715.217 respuestas y 1.632.508 trazas; ahora se escriben por bloques de 50.000 con latido de la tarea (`dw_loader.py`, `tareas_dataops.py`, `consolidacion.py`). Misma huella de hechos; 17 pruebas en verde. Evidencia: `f3w_bloqueo_consolidacion.json`.
- **W-14 completada con el código corregido:** respaldo `pg_dump` (`output/f3w/giragroup_db_pre_w14c.dump`, sha `f04081c8…e7d3`), limpieza de la carga anterior y carga de los 10 libros por la web (lote #4): INGESTA, LECTURA_BETO, PREPARACION_REVISION y CONSOLIDACION `COMPLETADA`, 0 errores 5xx, sin OOM. Evidencia: `f3w_recarga_dw_viva.json`.

## Duplicación e idempotencia (verificado)
- El borrado de documentos por la API (`DELETE /sources/{id}` y `delete-batch`) **no elimina los hechos ni `carga_fila_origen`** (FK `SET NULL`; `carga_fila_origen` sin FK). Por eso no se confió en la idempotencia: antes de recargar se hizo `pg_dump` y una limpieza SQL de la carga anterior en una transacción (hechos con `id_documento` 10 a 19, todo `fact_marketing` y la trazabilidad de esos documentos).
- Tras la recarga: 0 hechos huérfanos y `carga_fila_origen` con 1.632.508 filas y claves distintas; conteos iguales a la carga anterior en 8 de 9 tablas.
- En el clon, volver a consolidar el mismo lote agrega 0 hechos y 0 trazas. **No se re-consolidó en la DW viva.**

## No hecho y por qué
- **Casos de identidad:** quedan 1.383 pendientes en staging (incluidos los «Cédula dudosa»); no se aprobó ninguno, son decisiones de Lean.
- **Verificación visual completa** (V1 y V2, claro y oscuro, capturas por paso): no hecha; solo la barra V1 a 375 px y el recorrido de V2 en claro.
- **pytest completo con cobertura:** no se ejecutó en esta sesión (última cifra en `f3w_verificacion.md`: suite F3W 52 passed; 12 fallos preexistentes de entorno en la suite completa). Solo se corrieron las 17 pruebas del arreglo.
- **Diferencia de marketing sin explicar:** `fact_marketing` 10.490 (viva, esta carga), 10.486 (viva, carga anterior) y 10.464 (clon).

## Invariantes cambiados: no
Cascada, umbrales (0,92 / 90 / 85 / 80; bandas 0,85 / 0,60), estados A/B/C y esquema sin cambios. La escala de ARCA (0 a 100) la eligió el operador igual que en la carga de W-13.

## Pruebas
Frontend: 14 archivos / 84 pruebas / 0 fallos; build sin errores. Backend: 17 pruebas del arreglo en verde (`tests/f3w/test_bloqueo_consolidacion.py` más f3s, f3t, W-13 y W-5); suite F3W 52 passed según `f3w_verificacion.md`; suite completa y cobertura no repetidas.

## Servicios reconstruidos + estado de compose
`web` y `api` reconstruidos con el código final (`docker compose up -d --build`); gateway reiniciado tras reconstruir `api` (`/health` 200). 9 contenedores `giragroup_*` arriba. `beto_pg_f3w` (clon) detenido durante la carga web para liberar memoria (su contenido en tmpfs se reconstruye desde `output/f3ub/f3u_completo.dump`).

## Cambios de esquema o API
Sin cambios de esquema. Cambios de comportamiento: la consolidación escribe respuestas y trazas diferidas por bloques de 50.000 y emite latidos de tarea. (Los de W-3, W-4, W-12 y W-13 están en sus JSON.)

## Cifras nuevas (cifra | valor | archivo en docs/mediciones/)
| Cifra | Valor | Archivo |
|---|---|---|
| Barra V1 a 375 px | `scrollWidth` 375, sin desborde | `f3w_verificacion.md` |
| vitest | 14 archivos / 84 pruebas en verde | `f3w_verificacion.md` |
| Causa del bloqueo | memoria: pico de 2.376 MB por worker antes, 1.623 MB después | `f3w_bloqueo_consolidacion.json` |
| Hechos cargados en la DW viva | evaluación 715.217; académico 25.108; financiero 10.719; marketing 10.490; rentabilidad 95; costo 1.371; techo 206; bridge 1.690 | `f3w_recarga_dw_viva.json` |
| `carga_fila_origen` | 1.632.508 filas, claves distintas, 9 de 10 documentos | `f3w_recarga_dw_viva.json` |
| Tareas del lote #4 | 4 de 4 `COMPLETADA` (116.557 líneas) | `f3w_recarga_dw_viva.json` |
| Respaldo previo a la recarga | sha `f04081c8…e7d3`, 120.328.916 bytes | `f3w_recarga_dw_viva.json` |

Los tiempos de la carga no son la cifra de RNF-03 (la caché de BETO ya estaba poblada).

## Impacto en el documento (sección o tabla)
La DW viva contiene ahora la carga de los 10 libros, hecha con el código final. La SFV no debe afirmar que la trazabilidad por `carga_fila_origen` cubre PLANIFICACION (no inserta hechos). Las capturas o figuras del flujo DataOps con 4 pasos deben revisarse (ahora son 3).

## Riesgos abiertos
1. **El borrado de documentos deja hechos y trazas huérfanos** (FK `SET NULL`): cualquier purga por la web seguida de una recarga los duplicaría. Hay que decidir si el endpoint debe borrarlos.
2. **Consumo de memoria de la API:** cada worker retiene ~2 GB tras consolidar (pico 5,5 GiB entre 4 workers); una segunda consolidación seguida puede quedarse sin memoria.
3. **Marketing +4 / +26** sin explicar (ver arriba).
4. **Vigilante de 180 s** marca ERROR tareas que siguen vivas; el arreglo añade latidos, pero el vigilante no se revisó.
5. **El resumen de lectura de BETO vive en memoria de la API:** tras reiniciarla, «Consolidar lote» queda inactivo hasta pulsar «Actualizar» en el paso ②.
6. **Residuos:** lotes vacíos #1 a #3 y `cache_indice_beto` en la DW viva; la caché afecta los tiempos de cualquier medición (no usar estos tiempos como RNF-03).
7. **Hallazgo latente de W-6:** con el diferido, el completado de docente no alcanza a las respuestas de la misma consolidación; no se corrigió para no cambiar qué se carga.
8. **Frontend de F3W sin commit** (entra con el commit de la V2) y cambios locales de Lean sin commit en `backend/routers/powerbi.py` y `frontend/`.

## Pendiente para el chat 4
Capturas por paso del flujo de 3 pasos (V1/V2, claro y oscuro) y las tablas de la carga de los 10 libros a partir de `f3w_recarga_dw_viva.json`.

## Para decidir (Lean)
- Casos de identidad pendientes: aprobar o descartar.
- El commit de la V2 debe incluir los cambios de frontend de F3W (listados arriba); sin ellos el backend del commit de F3W queda sin su interfaz.
- ¿El borrado de documentos debe eliminar también sus hechos y trazas?
