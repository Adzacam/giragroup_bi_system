# CIERRE F3U-B — 2026-11-17

Rama/base: `beto-integracion`, `1db9e5614d0297bd1002aea6f0d944290e807f06`. Esta fase es documental y de medición; no se modificó código de `backend/`, `pipeline/`, `frontend/`, `db/`, `scripts/` ni `docs/fuente_verdad_tesis.md`. Se preservaron los cambios locales que ya existían.

## Estado de tareas

| Tarea | Estado | Evidencia y resultado |
|---|---|---|
| B-0 Preparación | **Completada con desviaciones registradas** | [Preparación](../mediciones/f3ub_preparacion.json): contenedor propio `beto_pg_f3ub`, tmpfs 6 GB, `dw_vacio` en cero y migraciones 014 y 016 aplicadas a la plantilla temporal. Hash de lote correcto (`aafde8ad…db60`), 10 archivos y versión `1.xlsx` excluida. El primer clon sin 014 falló antes de cargar hechos; se guardó en [intento inválido](../mediciones/f3ub_intento_invalido.json), se corrigió la plantilla y se inició una única corrida limpia. La lectura de la DW viva mostró deriva concurrente durante la ejecución. |
| B-1 Carga completa | **Completada, con control de DW viva no satisfecho** | [Avance por documento](../mediciones/f3ub_avance.jsonl): 10/10 con lectura y consolidación `COMPLETADA`. [Conteos, hashes y dump](../mediciones/f3ub_completo.json); copia custom en `output/f3ub/f3u_completo.dump`. Lote, modelo y snapshot coinciden con las huellas congeladas. No se escribió en la DW viva desde esta corrida. El conteo de control vivo varió de 15/26 al inicio a 1/1 durante y después; por tanto no se declara cumplido el criterio de “sin cambios”. |
| B-2 Cuadre cobertura | **Parcial** | [JSON por archivo/hoja](../mediciones/f3ub_cobertura_por_hoja.json), [CSV](../mediciones/f3ub_cobertura_por_hoja.csv), [reproducibilidad](../mediciones/f3ub_reproducibilidad.json), [fechas por hecho](../mediciones/f3ub_fechas_por_hecho.json) y [defectos](../mediciones/f3ub_defectos.md). Dos corridas dieron el mismo MD5. Las 116.557 líneas leídas quedaron clasificadas: 90.508 con registros, 4.638 en bandeja, 21.411 con motivo de ruido y 0 sin explicar. Sin embargo, el script no verifica `origen = ...` por fila, no desglosa hechos/staging/log por hoja y no da fechas por hoja. Siete diferencias entre filas de origen y líneas leídas/subtotales, además de diferencias entre esperados y persistidos por documento, quedan `requiere_revision` o enlazadas a un defecto conocido; B-2 no se marca completa. |
| B-3 Diseño opción B | **Completada** | [Diseño de PLANIFICACION](../mediciones/f3ub_planificacion_diseno.md): hecho, vista, KPI-23, metas, fórmula y límites de implementación documentados, sin calcular el KPI ni modificar el código. |
| B-4 Adenda del inventario | **Completada** | [Adenda de origen](../mediciones/f3ub_planificacion_adenda.json): celdas manuales, conciliación de 24 meses, estados, pauta y pivots. Las dos series de metas no cuadran en todos los meses; P/EJECUTADO se conserva como pauta, sin KPI ni suma de ingresos. |
| B-5 Resumen | **Completada como síntesis; depende de las revisiones B-2** | [Resumen para Lean](../mediciones/f3ub_resumen.md) y [clasificación](../mediciones/f3ub_defectos.md). Los defectos conocidos se enlazan sin duplicar IDs D-U. Las siete causas no demostradas permanecen pendientes. |

## Conteo final de la copia completa

10 documentos, 30 tareas DataOps; 25.108 hechos de rendimiento académico, 10.719 financieros, 715.217 de evaluación docente, 10.432 de marketing, 95 de rentabilidad, 1.371 costos de programa y 206 techos/convenios. Forecast y cobranzas proyectadas permanecen en cero. La copia contiene 68 filas de staging, 14.359 no resueltas, 22.746 inconsistencias, 90 líneas de log de ingesta y 30.366 filas de `carga_fila_origen`. El dump queda fuera de Git y su SHA-256 está en `f3ub_completo.json`.

## Incidencia externa de la DW viva

B-0 observó 15 lotes y 26 documentos en `giragroup_db`; más tarde se observó lote/documento único, y al cierre el documento id 28 tenía nombre y hash del libro antiguo de evaluación. La corrida F3U-B se dirigió al contenedor y base separados. No se puede atribuir la deriva a esta tarea; el estado final no satisface el control de no cambio. No se hizo ninguna reparación o escritura en la DW viva.

## Decisiones que quedan para Lean

1. Resolver si las siete diferencias de origen/lectura se investigan o se documentan como limitación antes de F3V.
2. Confirmar `EJECUTADO VS META` como autoridad financiera para KPI-02/03/13/14 y conservar Informe Gestión como planificación.
3. Definir meta de KPI-23: 12 aperturas al mes o tasa de programas iniciados frente al plan.
4. Resolver pendientes F3U que el plan recuerda: encabezado/huella de SFV, B-7 con `n=3` y selección de corridas limpias.

F3U-B **no se declara congelado**. No se ejecutaron pytest ni rebuild, conforme al plan de fase sin cambios de código.

