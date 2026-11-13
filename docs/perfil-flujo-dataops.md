# Perfil del flujo DataOps (10 archivos, copia aislada `clon_perf`)

cProfile sobre la lectura del paso ③ (`_evaluar_lote_en_segundo_plano`, ejecutada en el hilo principal) y la consolidación del paso ④
(`POST /confirm-dw-insert`), con un contador de sentencias SQL (`before_cursor_execute`). Los tiempos bajo el perfilador **no son
medición** (sobrecarga ~2–3× en código Python puro); valen para el ranking y las cuentas. Script: `scripts/perfilar_flujo_dataops.py`;
evidencia: `docs/evidencias/perfil_dataops/` (`perfil.json`, `perfil_lectura.prof`, `perfil_consolidacion.prof`).

## Qué hace cada paso hoy

- **Paso ③ «Lectura de BETO»**: no ejecuta el modelo. `extract_entities_from_line` (`backend/routers/dataops/extraccion.py:153`) aplica reglas,
  regex y encabezados, y resuelve personas y módulos contra el catálogo con RapidFuzz (`pipeline/normalization/person_resolver.py`).
  La confianza es una lectura base fija (0,91 / 0,88 / 0,98 / 0,54) más bonos (`calcular_indice_entidad_con_bonos`). El contenedor de la API no tiene torch.
- **Paso ④ Consolidación**: por bloque de staging pide el índice a `pipeline:8006/indice` (`confianza_service.obtener_indices`, 256 líneas por petición,
  caché `cache_indice_beto`), vuelve a ejecutar `extract_entities_from_line` por línea y carga fila a fila con `DWLoaderService.cargar_registro`.

## Lectura (15.926 líneas; 3.074 s bajo el perfilador)

| Función | Llamadas | Acumulado | % |
|---|---:|---:|---:|
| `extract_entities_from_line` | 15.926 | 3.049,6 s | 99 % |
| `_resolver_persona_cascada` → `resolver_persona_detalle` | 8.178 | 2.801,5 s | **91 %** |
| `quitar_titulos` | 201.300.851 | 2.484,7 s | 81 % |
| `_sin_acentos` (dentro de `quitar_titulos`) | 201.300.851 | 1.484,8 s | 48 % |
| `_coincide_contexto` | 50.430.586 | 1.470,3 s | 48 % |
| `_candidatos` | 9.320 | 1.280,5 s | 42 % |
| `re.sub` | 413.830.628 | 537,1 s | 17 % |
| `_mejor_modulo` | — | 105 s (perfil propio) | 3 % |

Causa: por cada nombre a resolver (8.178 llamadas no memoizadas), `resolver_persona_detalle` recorre las 14.078 personas del catálogo y para cada
una recalcula `quitar_titulos` + `_tokens` (normalización NFD + 4 regex) tanto en el filtro de contexto como en `_candidatos`. Son 201 millones de
normalizaciones de los mismos 14 mil nombres. Precomputar por persona (nombre sin títulos, tokens, contextos normalizados) una sola vez por catálogo
da el mismo resultado y elimina más del 90 % del tiempo de la lectura. SQL en la lectura: 2.182 sentencias, 2.161 de ellas `UPDATE dataops_tarea`
(avance de la barra, una por línea).

## Consolidación (1.143 s bajo el perfilador; 295.368 sentencias SQL = 18,5 por línea)

| Componente | Perfil propio | Nota |
|---|---:|---|
| `socket.recv_into` (respuestas de `pipeline:8006/indice`) | 273,1 s en 43 lecturas | 5.643 textos sin caché → ≈20,7 líneas/s del servicio BETO; no lo infla el perfilador |
| `person_resolver` (`quitar_titulos`, `_candidatos`, `_tokens`, `re.sub`) | ≈480 s | la misma causa que en la lectura, repetida al consolidar |
| `_mejor_modulo` + `fuzzy_score` | 105 + 65 s | 6,7 M comparaciones RapidFuzz contra 3.585 módulos |
| `psycopg2 cursor.execute` | 63 s | 295.467 ejecuciones |

Sentencias por tabla (las más frecuentes):

| Sentencia | Cantidad | Origen |
|---|---:|---|
| `SELECT` del ORM (lista de columnas larga; `DimOrigenDocumental` por registro y `FactEvaluacionDocente` por `clave_respuesta`) | 176.940 | `cargar_registro` líneas 1005 y 1276: **2 consultas por cada uno de los 85.630 registros** |
| `INSERT fact_evaluacion_docente` | 81.481 | un INSERT + `flush` por respuesta; existe `diferir_eval`/`finalizar_cargas` (execute_values) pero la consolidación no lo usa |
| `SELECT dim_docente` | 17.941 | `resolver_o_crear_docente` sin caché por nombre |
| `SELECT stg_entidad_no_resuelta` | 7.037 | comprobación de ruido/caso ya registrado por línea descartada |
| `SELECT dim_modulo` | 1.999 | módulos por nombre (memoizado) |
| `SELECT cat_institucion` | 1.098 | `_resolver_id_institucion` sin caché |
| `INSERT carga_fila_origen` / `SELECT carga_fila_origen` | 1.106 / 553 | 3 sentencias por fila de marketing/admisión |

Caché de índices: 90.212 → 95.855 filas (+5.643, las nuevas del lote). Tasa de acierto con la caché heredada del snapshot: 9.845 de 15.488 textos distintos (63,6 %).

## Resultado del lote (idéntico al de las 3 corridas)

85.630 hechos (81.481 evaluación docente, 1.393 académicos, 1.030 financieros, 1.320 costos, 362 marketing, 95 rentabilidad, 1 techo), 6.656 entidades en staging, 10 documentos.
