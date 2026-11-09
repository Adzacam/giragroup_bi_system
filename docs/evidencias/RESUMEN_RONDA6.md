# Ronda 6 — ciclo mensual completo (10 archivos, hojas sin fecha completas) en menos de 5 min de máquina

## Tabla única de cifras (todo de ejecución)
| Cifra | Línea base | Final | Evidencia |
|---|---|---|---|
| Tiempo de máquina del ciclo completo | 427,4 s | 59,1 s ± 0,7 (3 corridas: 58,4 / 59,7 / 59,3) | ciclo_completo_linea_base.json, ciclo_completo_final_{1,2,3}.json |
| Lectura / reglas / BETO / carga (s) | 5,2 / 31,3 / 218,4 / 172,4 | 5,1 / 5,0 / 5,2 / 43,6 ± 0,7 | idem |
| Evaluación Docente y Unifranz (4.886 filas, 71.458 hechos) | 297,5 s | 27,1 s ± 0,2 (carga 23,9) | idem |
| BD Cobranzas | 25,2 s | 5,7 s ± 0,1 | idem |
| [BBDD] ANTIGUO RESPUESTAS | 51,9 s | 1,7 s | idem |
| Líneas enviadas a BETO | 12.993 (todas) | 2.838 candidatas (8.656 resueltas por reglas, 1.470 sin hecho posible) | lineas_beto_vs_reglas.json |
| Casos HITL nuevos por ciclo | 1.842 (neto en la bandeja) | 252 casos en 38 grupos (neto en la bandeja +32) | grupos_hitl_final_{1,2,3}.json |
| Aprobar grupo (máquina) | — | 36 de 38 grupos, 205 casos, 0,9–1,2 s en total (mediana 0,015 s por grupo); listar grupos 0,022 s | idem |
| Lote 1.387 (2 corridas idénticas) directo / HITL / staging | 97,62 % / 2,38 % / 0 % | 97,62 % / 2,38 % / 0 % | corrida_final_1/2.json |
| KPI-10 todas / solo BETO · KPI-11 | 0,9618 / 0,9209 · 97,62 % | idénticos | idem |
| Extracción directo A / B | 99,50 % / 99,64 % (+2) | idéntico | idem |
| F1 relajado BETO (modo C) gold_510 / layouts_5, fp32 → int8 | 0,9912 / 0,6923 | 0,9606 / 0,6774 (int8) | f1_beto_{fp32,int8}_*.json |
| pytest | 448 passed | 451 passed, 0 failed, 11 skipped, 7 xfailed | cobertura_ronda6.json |
| Cobertura global | 60,6 % | 60,0 % (7.883 de 13.137 líneas) | cobertura_ronda6.json |

Presupuesto: máquina ≤ 300 s → 59,1 s; grupos HITL ≤ 60 → 38. Tiempo humano no medido: con 59 s de máquina quedan 14 min de los 15 para revisar 38 grupos (≈ 22 s por grupo) o, con 252 casos individuales, ≈ 3 s por caso.

## Qué se cambió y qué aportó (medido)
1. **Reglas antes de BETO** (`routers/pipeline.py`): la línea se resuelve por la cascada de reglas; solo las no resueltas van al modelo; las demás usan el índice de la caché si existe (nunca se calcula). BETO: 218,4 → 5,2 s. Una resuelta por reglas con índice < 0,60 en caché se carga y queda en `log_inconsistencias` (BAJA_CONFIANZA_CARGADA, 53). Ya existían deduplicación, caché `cache_indice_beto`, lotes de 32 y max_length 128; se añadió `torch.inference_mode`. Los hilos siguen en 4 (`TORCH_NUM_THREADS`): con 24 hilos medimos 1.162 ms por forward frente a 53 ms con 4 (comentario en `ner_engine.py`).
2. **Cuantización int8**: `BETO_INT8=1` (opcional, apagada). No se adopta: gold_510 modo C cae 3,06 puntos de F1 relajado (0,9912 → 0,9606) y layouts_5 modo C 1,49; el criterio era ≤ 1 punto. En la cascada de producción (modo B) el F1 no cae (gold_510 1,0 / 1,0; layouts_5 0,7164 → 0,7368).
3. **Carga**: el perfil mostró que el costo no era el INSERT sino (a) `resolver_o_crear_modulo` trayendo los 3.580 DimModulo como objetos ORM por cada módulo por nombre (21 de los 25 s de Cobranzas), (b) el padrón de TBL_INSCRITOS leído del xlsx en cada petición (~3 s por archivo), (c) 14–15 registros por fila de encuesta repitiendo la resolución del mismo estudiante/módulo/docente. Se añadieron cachés por instancia (módulo por nombre, estudiante por entrada, programa), el padrón en caché por archivo y la evaluación docente se inserta en bloque con `execute_values` (páginas de 2.000, `ON CONFLICT (clave_respuesta) DO UPDATE`, sin pisar `RESUELTO_HUMANO`). No se hizo COPY ni `ON CONFLICT` sobre `carga_fila_origen` para las demás tablas: el costo restante de carga (43,6 s, 24 de ellos en evaluación docente) ya cabe en el presupuesto.
4. **HITL**: (a) CI exacta con nombre distinto: si el nombre guardado es un marcador ('Estudiante CI …') o `token_set_ratio ≥ 85` con un token en común, se resuelve y queda CI_NOMBRE_VARIANTE en el log (258): de 257 casos, 0 quedan; (b) las líneas que las reglas resuelven ya no pasan por staging; (c) evaluación docente sin docente/fecha: `requiere_revision = FALSE` con motivo LIMITACION_FUENTE (y TIEMPO_IMPUTADO si el id_tiempo se imputó con el último período con actas del programa: 491 respuestas); (d) líneas sin hecho posible (solo 'N°: 1498' o texto libre sin encabezados, 1.470) no van a BETO ni a la bandeja: un registro agregado por hoja en el log (LINEAS_NO_APLICABLES); (e) `GET /dataops/review-tray/grupos` y `POST /dataops/review-tray/approve-group` agrupan por (motivo, valor normalizado) staging y hechos en revisión. Los 2 grupos que `approve-group` no resuelve (47 casos) son hechos de ARCA sin nota o con estado fuera de catálogo: hay que corregirlos caso por caso.

## Regresión (T4)
- Huella del DW, línea base contra final (`regresion_huella_dw.json`, filas en claves naturales, sin ids seriales, marcas de tiempo ni `nivel_confianza_ia`): iguales fact_marketing, fact_rentabilidad, fact_forecast, fact_techo_convenio, dim_docente, dim_categoria_financiera, bridge_modulo_docente. Diferencias, todas de la tarea 3: fact_costo_programa +51 filas y fact_rendimiento_academico +26 (líneas que antes iban a staging por BAJA_CONFIANZA_IA y ahora se cargan por haberlas resuelto las reglas), 125 hechos académicos y 71 de costo salen de `requiere_revision`, dim_modulo +4 (módulos de esas líneas), fact_evaluacion_docente: solo cambian `requiere_revision`/`motivo_revision` (3 filas más), dim_estudiante: 106 estudiantes menos (comentarios libres como 'Liderazgo' o 'Más comunicación' que la línea base creaba como estudiantes Estado C) y 21 nombres de marcador completados por CI_NOMBRE_VARIANTE.
- Lote 1.387 dos veces: idénticas. gold_510 y layouts_5 con la configuración final (fp32, inference_mode): igual que la ronda anterior (columnas fp32 de f1_beto_*).
- Cambios de contenido en el DW real: 11.210 respuestas de evaluación docente pasan a `requiere_revision = FALSE` con LIMITACION_FUENTE (`scripts/reparar_evaluacion_limitacion_fuente.sql`); los 48 casos de evaluación docente salen de la bandeja.
- `nivel_confianza_ia` queda nulo en las líneas resueltas por reglas que no estaban en la caché de BETO (ver el costo en `huella_dw`).

## Cierre (T6)
- id_tiempo de evaluación docente: se imputa solo desde actas del programa y queda marcado TIEMPO_IMPUTADO (491 respuestas en el ciclo); 1.970 respuestas siguen sin fecha (LIMITACION_FUENTE).
- Diccionario de datos: `diccionario_datos.csv`, 50 tablas (48 de public + `bi.ref_kpi` y `bi.ref_perspectiva`), 414 columnas; 269 descripciones se derivan del nombre de la columna (marcadas "derivada del nombre"), el resto son específicas.
- Inventario de las 48 tablas: `inventario_tablas_48.csv` (ronda anterior).

## Límites
- La línea base se midió en esta máquina con el clon de `giragroup_db` de hoy; "ciclo completo" = 10 archivos con las filas del mes en hojas con fecha y hojas sin fecha completas (el recorte de 300 filas se quitó), no el histórico de cada archivo.
- Los casos HITL por ciclo no incluyen el stock previo de la bandeja (23.121 en staging, 3.678 hechos).
- BETO: no se registraron las líneas realmente inferidas (excluye caché); 2.838 es el máximo.
