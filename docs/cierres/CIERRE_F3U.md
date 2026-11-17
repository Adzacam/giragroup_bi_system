# CIERRE F3U — 2026-11-17

## Resultado

F3U queda **cerrado parcialmente como fase documental**. Se completaron el inventario U-3 de las 32 hojas del libro PLANIFICACION y el diseño U-4 de su aporte al DW/CMI, sin cambios de código ni de esquema. No se declara completada la cobertura de los diez libros: los artefactos finales de U-1, U-2 y U-5 no se generaron ni se conservaron antes de que desapareciera el contenedor temporal `f3u_completo`.

La evidencia disponible durante la ejecución registró que la entrada usada tenía SHA-256 `aafde8adc246af13c4eeb9ffbf766eda4348cfb6e855860d0bf00bcd24cbdb60`, que las 10 solicitudes de carga recibieron respuesta HTTP 200, y que la lectura BETO llegó a 116.557 líneas. Esos datos de avance no prueban la consolidación: no se obtuvo el JSON final con estados e IDs de los diez documentos ni un conteo final de hechos, staging, logs y `carga_fila_origen`. Por eso no se presentan como cumplimiento de U-1/U-2. El primer intento no válido se descartó; `dw_vacio` no incluía la migración 016 que la carga necesitaba. Para el segundo intento, se aplicó dicha migración solo al clon desechable antes de empezar con tablas vacías.

## Evidencia generada

| Tarea | Resultado | Evidencia |
|---|---|---|
| U-1 — carga completa en tmpfs | Parcial/no verificable al final. Se preparó el clon aislado y arrancó la carga completa. No hay conteos finales ni huellas posteriores persistidos. | Avance anotado en esta sesión; sin `f3u_completo.json`. |
| U-2 — cobertura por archivo y hoja | No completada. No se produjo una medición para `f3u_completo`, no hay cuadre de hojas ni clasificación de `sin_explicar`. | Existe la medición previa F3S [f3s_cobertura_por_archivo.json](../mediciones/f3s_cobertura_por_archivo.json), que corresponde a `f3s_base_r1`; no sustituye U-2. El script correcto es `scripts/f3s_cobertura_por_archivo.py`. |
| U-3 — inventario de PLANIFICACION | Completada: 32/32 hojas descritas; 19 `dato_fuente`, 11 `derivada`, 2 `borrador_duplicado`, ninguna vacía. Se estiman 1.663 filas fuente útiles, excluyendo filas plantilla con solo `FALSE`/`TRUE`/`0`. | [f3u_planificacion_inventario.json](../mediciones/f3u_planificacion_inventario.json) |
| U-4 — diseño de PLANIFICACION | Completada como propuesta, pendiente de decisión de Lean. Incluye destinos A/B, mapeos, estimación, KPI y cambios de invariantes. | [f3u_planificacion_diseno.md](../mediciones/f3u_planificacion_diseno.md) |
| U-5 — resumen de cobertura y decisiones | No completada por depender del U-2. | No se generó `f3u_resumen.md`. |

El inventario U-3 tiene hash de libro `c65129c62c9cfaa13ac483d2f5d7afed5c65d4a503547adb08829a075cf8dba0`. Entre sus hallazgos: 1.340 filas con POS válido, 323 filas fuente sin POS, 1.334 con clave POS+mes y 8 repeticiones de POS+mes. Por ello, POS+mes es una clave de relación y no de fila. Los borradores contienen 46 filas útiles que no se sumaron al estimado fuente. La propuesta B preserva el grano por fila de origen con una nueva `fact_planificacion_programa`, una vista mensual y KPI-23; su recomendación es de diseño y requiere aprobación, no es una decisión implementada.

## Límites y decisiones pendientes

- No se puede afirmar el criterio de 10/10 documentos consolidados, 100 % de hojas cuadradas, repetibilidad del cuadre ni invariancia de huellas antes/después.
- El plan detecta la necesidad de revisar el comportamiento de la carga completa sobre `dw_vacio`; el desvío de migración 016 se documentó arriba. La consolidación final y cualquier efecto sobre las tablas no se pudieron medir.
- No se modificaron `backend/`, `pipeline/`, `frontend/`, `db/` ni `docs/fuente_verdad_tesis.md`. Los cambios locales preexistentes se preservaron.
- No se corrieron pruebas ni rebuild; esta fase no incluye cambios de código.
- No se creó un commit porque faltan las salidas de U-1/U-2/U-5 que el plan incluye en el conjunto de cierre, y el árbol tiene cambios ajenos preexistentes.

Lean debe decidir la opción A o B de PLANIFICACION y, para cada defecto de cobertura D-U#, si se corrige en F3V o se declara como limitación. Antes de esas decisiones, hay que repetir/recuperar U-1 y completar U-2 en un clon aislado, guardar sus artefactos y producir el resumen U-5. No anunciar «F3 congelado».

## Adenda posterior — F3U-B (2026-11-17)

El cierre anterior describe el estado de F3U al concluir esa ejecución. La fase de continuación se documenta en [CIERRE_F3U_B.md](CIERRE_F3U_B.md): completó la carga aislada de los 10 libros y produjo dump/evidencias, y realizó dos corridas reproducibles de cobertura. El cuadre B-2 sigue parcial por diferencias origen/lectura y esperado/persistido que requieren revisión y por límites del script de cobertura. La observación de la DW viva también detectó deriva concurrente. Esta adenda preserva el historial y no declara la fase congelada.
