# Antes de decidir la fase C: caché vacía, una sola pasada de BETO y origen del KPI-10

Complementa `docs/mediciones/optimizacion-flujo-dataops-A.md`. Misma entrada (10 archivos del ciclo mensual), copias aisladas del snapshot del 10 de noviembre con el DW reiniciado.

## 1. Fase A con la caché de índices vacía (escenario de un mes nuevo)

`cache_indice_beto` truncada en cada copia (`FLUJO_CACHE_VACIA=1`), 3 corridas (`docs/evidencias/flujo_A_cache_vacia/`), servicio BETO con 2 procesos.

| Etapa | Media | DE | Mín–Máx |
|---|---:|---:|---:|
| Carga | 8,4 s | 0,7 | 7,7–9,0 |
| Lectura del paso ③ (reglas y catálogo, sin modelo) | 125,9 s | 26,7 | 100,4–153,7 |
| Consolidación (incluye el índice BETO de las 15.488 líneas distintas) | 797,3 s | 77,4 | 718,1–872,8 |
| Revisión, máquina | 0,8 s | 0,1 | |
| **Máquina** | **932 s (15,5 min)** | **104** | 827–1.036 |
| Parte humana (KLM, Deshacer no bloqueante) | 311 s (5,2 min) | | |
| **Total estimado** | **20,7 min** | | |

Con la caché llena (corridas A2): máquina 596 s (DE 87), total 15,1 min. El índice BETO de un mes nuevo añade ≈ 380 s a la consolidación (797 − 418).
El DW resultante tiene los mismos hechos que con la caché llena (el índice de cada texto no depende de la caché); en estas corridas solo cambian `clave_origen`
y `carga_fila_origen`, porque esa ejecución regeneró los archivos del ciclo (otro hash de archivo); corregido en `medir_flujo_repetido.py` (árbol propio en
`/tmp/flujo`, `medir_ciclo_mensual` actualizado).

## 2. ¿El mismo modelo y los mismos logits sirven para las entidades?

- **Mismo modelo.** `/indice` (`indice_confianza._cargar_modelo`) toma `engine._nlp_pipeline.model` del mismo singleton `get_engine_and_tokenizer()`
  que usa `/infer-batch`; si no hubiera motor, carga el mismo checkpoint (`pipeline/semantic/beto_local`, `BertForTokenClassification`).
- **Logits NER por token.** Sí: la cabeza tiene las 9 etiquetas IOB2 del ajuste (`O`, `B/I-PER_ESTUDIANTE`, `B/I-PER_DOCENTE`, `B/I-MODULO`, `B/I-PROGRAMA`);
  `calcular_indices` hace softmax sobre esos logits y promedia la probabilidad de los tokens etiquetados distinto de `O`.
- **Costo de decodificar de esos mismos logits** (`scripts/benchmark_una_pasada.py`, 1.024 textos de 8 celdas, 4 hilos, 1 proceso; `docs/evidencias/una_pasada/`):

| Variante | Tiempo | líneas/s | Índice igual al actual | Entidades iguales al pipeline NER |
|---|---:|---:|---:|---:|
| Índice actual (`calcular_indices`) | 58,5 s | 17,5 | — | — |
| Entidades actuales (pipeline NER, segundo forward) | 63,0 s | 16,2 | — | — |
| **Una pasada, recorte a 128 tokens** | 61,2 s | 16,7 | **1.024 de 1.024** (dif. máx. 0) | 750 de 1.024 |
| **Una pasada, sin recorte (512)** | 63,8 s | 16,1 | 752 de 1.024 | **1.024 de 1.024** |

  Decodificar las entidades de los logits ya calculados cuesta **+4,5 %** (2,6 s por 1.024 textos), frente a +108 % de un segundo forward.
  Las 274 diferencias de la variante de 128 son exactamente textos de más de 128 tokens (275 de 1.024, el 27 %): el índice actual los recorta y el
  pipeline NER no. No se puede tener a la vez el índice idéntico y las entidades idénticas en esos textos; con 512 tokens el índice medio pasa de
  0,9639 a 0,9631 en la muestra.

## 3. Estimación de la fase C sin forward duplicado

Supuesto: un solo `/infer-batch` por línea distinta en el paso ③ (entidades + probabilidades + índice) que se guarda en caché; la consolidación solo lee la caché.
Costo del forward único = costo medido del índice en la consolidación (≈ 380 s con caché vacía) × 1,045 (decodificar, punto 2).

| Escenario | Fase A medida | Fase C estimada | Diferencia |
|---|---:|---:|---|
| Caché vacía: máquina | 932 s | ≈ 8 + 126 + 397 + 418 + 1 = **950 s** | +18 s (+2 %) |
| Caché vacía: total con KLM | 20,7 min | ≈ 21,0 min | |
| Caché llena: máquina | 596 s | ≈ 8 + 126 + 0 + 418 + 1 ≈ **553–596 s** | igual o algo menor |
| Caché llena: total con KLM | 15,1 min | ≈ 14,4–15,1 min | |

La fase C **no acelera** el ciclo: hoy ya se hace un solo forward por línea distinta (en la consolidación); C lo adelanta al paso ③ y le suma la
decodificación. Su valor es de contenido (que el paso ③ muestre entidades de BETO), no de tiempo. Con caché vacía ninguna de las dos fases llega a
15 min en CPU: con la parte humana de 311 s, la máquina tendría que bajar a 589 s, lo que deja ≈ 36 s para BETO sobre 15.488 textos (≈ 430 líneas/s;
el mejor CPU medido es 31,8). Con GPU (`docker-compose.gpu.yml`, el código cita ~4×) el índice bajaría a ≈ 95 s y el total a ≈ 16 min; no medido.
Además, la fase C cambia la confianza y con ella la bandeja: la parte humana de C no es necesariamente 311 s.

## 4. Qué promedia el KPI-10

- Vista `bi.vw_cmi_valores` (migración 014, CTE `aca_g`): `KPI-10 = AVG(nivel_confianza_ia) × 100` y `KPI-11 = % con nivel_confianza_ia ≥ 0,85`,
  sobre `fact_rendimiento_academico` de la gestión (solo hechos académicos; los NULL no cuentan).
- `nivel_confianza_ia` se escribe en `DWLoaderService.cargar_registro` (`backend/services/dw_loader.py`) con `resoluciones["nivel_confianza_ia"]`:
  - `/pipeline/process` (`backend/routers/pipeline.py`, `r_l["nivel_confianza_ia"] = indice`): el **índice BETO** de la línea (`confianza_service.obtener_indices`),
    o el de la caché si las reglas resolvieron la fila (`indices_en_cache`); `None` si no hay índice.
  - DataOps (`backend/routers/dataops/consolidacion.py`, `if indice is not None: score = indice`): el **índice BETO**; solo si el servicio no
    responde usa la confianza del extractor (lectura base fija 0,91/0,88/0,98/0,54 + bonos, `calcular_indice_entidad_con_bonos`).
- El índice BETO (`pipeline/semantic/indice_confianza.calcular_indices`) es la media de la probabilidad softmax de los tokens que BETO etiqueta distinto
  de `O` en las primeras 8 celdas de la línea (recorte a 128 tokens); si no detecta ninguna entidad, **0,55** (texto < 20 caracteres) o **0,72** (constantes, no del modelo).
- En el snapshot: KPI-10 = 93,43 (2024) y 92,69 (2025); KPI-11 = 91,91 y 90,10. De los 10.437 hechos académicos de 2025, 10.386 tienen confianza;
  ninguno vale exactamente 0,72 ni 0,55 (valores con 4 decimales del modelo), así que el KPI-10 del snapshot es, en la práctica, la confianza media de BETO
  sobre las líneas con entidades. La migración 013 lo rotula «Confianza media de extracción (reglas y BETO)»: el número sale de BETO; las reglas deciden
  qué líneas se cargan, no la confianza.
- Lo que el índice **no** es: no es entropía (es la probabilidad media de la clase elegida) y no mide la resolución contra el catálogo.

## 5. Deshacer no bloqueante, verificado en el navegador sobre una copia

Copia `clon_ui` (snapshot del 10-nov, DW reiniciado, los 10 archivos consolidados, bandeja sin revisar: 194 casos en 12 grupos). La API se reinició
temporalmente apuntando solo a esa copia (override de compose que cambia el nombre de la base dentro del contenedor) y la pantalla se sirvió con el
servidor de desarrollo (`web-dev`, código actual; la imagen `giragroup_web` es del 11-nov y no tiene el cambio). Lote 1, paso ④, vista por grupos.

| Prueba | Resultado |
|---|---|
| Dos «Aprobar grupo» seguidos (101 y 7 casos) | Dos avisos activos a la vez, cada uno con su cuenta y su Deshacer; ambos enviados (2 × `POST /review-tray/approve-group` 200); hechos en revisión 114 → 6 |
| Otro par (6 casos y, tras pasar de página, 1 caso) | Captura con los dos avisos activos (5 s y 10 s): `docs/evidencias/deshacer_no_bloqueante/dos_avisos_activos.jpg`; hechos en revisión 6 → 0 |
| Dos descartes seguidos (casos 36 y 37) y Deshacer del 36 | Solo queda el aviso del 37; se envía solo el 37 (`POST /review-tray/37/resolve` 200, `DESCARTADO`); el 36 sigue `PENDIENTE` |

Detalles vistos: el texto dice «grupo de 1 casos» (plural fijo); la paginación de grupos y los filtros siguen activos mientras hay avisos pendientes.
Al terminar, la API volvió a la base viva y la copia se borró.
