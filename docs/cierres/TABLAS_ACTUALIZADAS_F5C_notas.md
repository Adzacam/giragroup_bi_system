# Notas de TABLAS_ACTUALIZADAS_F5C.docx

- Fuente de reemplazos: `docs/cierres/ACTUALIZACION_DOCX_F5C.md` (secciones 1 y 2). Docx original leido en solo lectura: `PROYECTO GRADO DAZA CAMPERO ADRIANO LEANDRO (3).docx` (no se modifico).
- Cada tabla va bajo su pie «Tabla X.Y ...» (el pie original del docx esta encima de la tabla). Arial 9 en todo; encabezados en negrita; bordes simples; A4 horizontal; sin color. No se agrego la linea «Fuente:» (no se pidio).
- Estandar numerico boliviano tal cual viene en la lista. Los porcentajes «(calc.)» se conservan marcados, tal cual estan en la lista.

## (a) Por tabla: filas x columnas finales y celdas cambiadas

| Tabla | Filas x columnas (con encabezado) | Celdas cambiadas | Filas eliminadas / nuevas | Pie cambiado |
|---|---|---|---|---|
| 3.24 | 6 x 6 | 11 | elim.: r4 ; 1 nueva(s) | si |
| 3.27 | 24 x 7 | 0 | 1 nueva(s) | no |
| 3.28 | 7 x 7 | 1 | - | no |
| 3.29 | 8 x 7 | 4 | - | no |
| 3.30 | 25 x 6 | 50 | - | no |
| 3.31 | 12 x 7 | 2 | - | no |
| 3.32 | 10 x 8 | 57 | - | no |
| 3.34 | 7 x 5 | 3 | - | no |
| 3.36 | 7 x 5 | 7 | - | no |
| 3.37 | 19 x 6 | 6 | - | no |
| 3.38 | 13 x 6 | 2 | - | no |
| 4.1 | 9 x 6 | 11 | - | no |
| 4.2 | 12 x 7 | 1 | - | no |
| 4.3 | 7 x 6 | 14 | elim.: r7, r8, r9, r10 | si |
| 4.3b (nueva) | 3 x 5 | tabla nueva (10 celdas de datos) | - | pie nuevo |
| 4.5 | 9 x 6 | 15 | - | no |
| 4.6 | 20 x 7 | 34 | elim.: r10, r11, r18 | si |
| 4.6b (nueva) | 5 x 7 | tabla nueva (28 celdas de datos) | - | pie nuevo |
| 4.6c (nueva) | 2 x 7 | tabla nueva (7 celdas de datos) | - | pie nuevo |
| 4.7 | 6 x 6 | 12 | - | no |
| 4.8 | 6 x 5 | 5 | - | no |
| F.1 | 60 x 6 | 3 | - | si |

Total de celdas existentes cambiadas: 238 (mas filas nuevas y tablas nuevas).

Detalle de eliminaciones/movimientos: 3.24 r4 (OLS matricula N = 33) eliminada; 4.3 r7 a r10 (bloque Bandeja/Staging) movidas a la nueva Tabla 4.3b; 4.6 r10 (KPI-10), r11 (KPI-11) y r18 (KPI-18) movidas a la nueva Tabla 4.6b (con KPI-15 para el valor de f3_base 73,44 %); nuevas filas: 3.24 (OLS anual) y 3.27 (KPI-23).

- Verificacion Tabla 4.5 (registros): suma de 7 archivos = 1.387 vs total 1.387 OK
- Verificacion Tabla 4.5 (directos): suma de 7 archivos = 1.356 vs total 1.356 OK
- Verificacion Tabla 4.5 (HITL): suma de 7 archivos = 31 vs total 31 OK
- Verificacion Tabla 3.32 (peticiones): suma de 8 endpoints = 1.121 vs total 1.121
- Verificacion Tabla 4.3: entidades [283, 154, 87, 25, 5] suman 554 (total declarado 554); registros por regla [110, 154, 87, 25, 5] suman 381 (total declarado 268).

## (b) Buscar que no coincidieron y filas/celdas sin reemplazo definido

**Buscar sin coincidencia:** 0. Las 258 asignaciones de celda (238 con cambio de texto) se verificaron contra el texto original (igualdad con la celda o contenido en ella; en filas completas con «...» o columnas omitidas en Buscar se verificaron solo las columnas citadas). Casos de lectura especial, sin discrepancia de texto:
- 3.24 r1 y r2: el Buscar omite la columna 1 (Serie/Fuente); el Reemplazar define las 6 celdas. En r2 los seis valores del pronostico (396,44 · 423,55 · 479,38 · 440,72 · 416,17 · 402,81) van juntos en la ultima celda, con los intervalos al final (en 4.7 r2 la propia lista los pone entre parentesis dentro de una sola celda). La columna 1 de r2 queda «mismo ajuste de N = 43» y la de parametros «mismos parametros», tal cual la lista.
- 4.7 r1 y r2: Buscar con «...» (columna 1) o sin la columna 1; el Reemplazar da 5 celdas (columnas 0 a 4) y la columna 5 (Estatus Academico) queda sin cambios. En 4.7 r1 c1 la lista deja «fact_marketing.inscritos» (se pierde «(Matricula mensual)»).
- 4.1 r4 c5: el original es «Cumple (652 pruebas totales » (sin parentesis de cierre, defecto del docx); el reemplazo lo cierra.
- 4.6 r15 c5: de la lista se toma solo «43,58 %»; la aclaracion entre parentesis (73,44 % en f3_base «va en la Tabla 4.6b») se uso para la fila KPI-15 de la Tabla 4.6b y no se escribio en la celda.
- 4.6 r2 c5: se conserva «6,25 % (en 2024 solo hay meta de diciembre)» tal cual.

**Celdas/filas sin reemplazo definido (quedan con el valor viejo del docx; decision pendiente de Lean):**
- 3.24 r3 (Naive estacional, MAPE 10,32 %, «HW resulta 3,57 pp inferior») y r5 (OLS recaudacion mensual N = 40: R2 0,7128; RMSE 118.783,06): D-05 y D-06; sin medicion congelada. Contradicen al HW nuevo de r1.
- 3.27: solo se agrega KPI-23; las demas filas no tienen cambio definido.
- 3.29 r1 a r6 (pruebas por suite 387/125/32/51/16/21): D-10, quedan historicas; suman 632 y no 924 (el TOTAL ya es 924/12/943).
- 3.30 (filas no listadas): no se tocaron; mezcla de bases por D-11: el CSV de cobertura por archivo suma 72,42 % (11.366/15.694), no 72,69 %; las filas cambiadas vienen del CSV y el TOTAL de `f5c_pruebas.json`.
- 3.31 columna Tiempo (ms): D-13, sin respaldo en `f3v_newman.json`; queda como estaba.
- 3.34 r1 a r4 (tiempo de maquina 60,0 s, inferencia, carga DW, esfuerzo KLM 490,5 s con 188 casos/37 grupos): D-01, pendiente de Lean; el encabezado c2 ya dice «Valor observado (F5C)» pero esas 4 filas conservan los valores de Ronda 8.
- 3.37 r14 (RNF-03: «9,2 min postest»), 4.1 r5 (9,2 min, «Cumple como estimacion») y 4.8 r2 (9,2 min; -590,8 min): D-01/D-03 (RNF-03 no cumple segun la SFV: 20,52 / 31,75 min). Quedan sin cambio.
- 4.2: solo r11 c5 (90.538). Las filas por libro suman 66.485 procesables y el total sigue en 92.946 brutos y 93,80 % de CI (D-04, sin respaldo en SFV): la tabla queda internamente inconsistente hasta que Lean decida medir o eliminar.
- 4.3: sin reemplazo para el encabezado y las columnas de accion. Revisar: los registros por regla suman 381 y no 268 (la lista da 110, 154, 87, 25 y 5; salvo Likert, igualan al conteo de entidades; el total sigue en 268). Las proporciones suman 99,99 %.
- 4.6: columnas 2025 de KPI-02/03/04/05/07/08/09 y la columna de base de calculo (c6) de KPI-01, 02, 04, 07, 09 y 12 a 22 sin cambio (la lista no define reemplazo). KPI-06 queda N/D** en ambas gestiones. KPI-19 y KPI-20: N/D en 2024. Sin cifra congelada: KPI-15 de 2024 y KPI-18 de 2024/2025 (en 4.6b van como «—»; KPI-18 solo tiene el valor 32 de la gestion 2026 en f3_base).
- 4.6b y 4.6c: la lista no define los encabezados de columna ni la columna de base de calculo; los escribi con el mismo patron de la 4.6 (para 4.6b: unidad, perspectiva e indicador de la fila original). Los textos de la columna «Base de Calculo» de 4.6b/4.6c y los encabezados de 4.3b son redaccion minima mia a partir de la lista; revisar. 4.3b: columna Grupos de la fila Staging puesta en «—» (la lista no da grupos).
- 4.7 r3 (naive estacional 10,32 %) y r4 (OLS mensual): D-05, D-06; sin cambio. 4.7 r5 c0 y c1 («Regresion OLS Anual Recaudacion (DW)», «fact_rentabilidad.monto_ejecutado (Valores DW)») no tienen reemplazo, mientras la nueva fila de 3.24 usa META_ANUAL como fuente: posible inconsistencia entre ambas.
- 4.8: r2 (ver arriba) y r4 sin cambio (declarada igual en la lista).
- F.1: solo se cambiaron el pie, r1 c4-c5 (23 KPI) y r23 c5 (dim_tiempo). La tabla conserva 59 filas, pero el pie ahora dice 51 tablas base y 10 vistas (61 objetos): faltan `fact_planificacion_programa` y `bi.vw_planificacion_ejecucion_mensual`, y la columna «Filas en Snapshot» (p. ej. dim_estudiante 14.078, fact_*, stg 1.044 activas, dim_meta 0, schema_migrations 1) no se regenero (D-17). Pendiente de Lean: `python scripts/diccionario_datos_csv.py` sobre la copia tmpfs.
- Sin reemplazo de la lista y fuera del alcance pedido: Tablas 3.1, 3.9, 3.17, 3.18, 3.20, 3.22, 4.4, 4.9, Cuadros y T82 (existen reemplazos en la lista, pero no estaban en el listado del usuario).

## (c) Verificacion de fuente Arial 9

Script en el scratchpad (`verify_fonts.py`, fuera del repo). Resultado de la ultima corrida sobre el .docx:

```
runs totales: 1770 | con texto: 1770 | no conformes (no Arial 9): 0 []
w:color/w:shd/w:highlight en documento: 0
estilos usados: {'TableGrid'}
docDefaults rFonts: {'ascii': 'Arial', 'hAnsi': 'Arial', 'cs': 'Arial', 'eastAsia': 'Arial'} sz: 18
Normal sz: 18 rFonts: {'ascii': 'Arial', 'hAnsi': 'Arial', 'cs': 'Arial', 'eastAsia': 'Arial'}
parrafos sin runs sin marca Arial 9: 0
tablas: 22
```

Criterio: cada `w:r` tiene `w:rFonts` ascii/hAnsi/cs/eastAsia = Arial y `w:sz`/`w:szCs` = 18 (9 pt); ademas el estilo Normal y `docDefaults` estan en Arial 9; sin `w:color`, `w:shd` ni `w:highlight`; los parrafos sin runs (celdas vacias) llevan marca de parrafo Arial 9.
