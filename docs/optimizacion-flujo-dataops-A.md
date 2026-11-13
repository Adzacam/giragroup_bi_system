# Optimización del flujo DataOps, fase A: más velocidad con el mismo resultado

Fase A de la secuencia A → B → C. Solo cambios que no alteran la salida; comprobado con huellas md5 de 14 tablas del DW,
la bandeja y los KPI del CMI sobre la misma entrada (los 10 archivos del ciclo mensual) en copias aisladas del snapshot del
10 de noviembre con el DW reiniciado. Punto de partida: `docs/perfil-flujo-dataops.md`. Evidencia: `docs/evidencias/`.

## Cambios

| # | Cambio | Dónde | Motivo (del perfil) |
|---|---|---|---|
| 1 | Catálogo de personas preparado una vez por lista (`_PersonaPreparada`: nombre sin títulos, tokens, apellidos, contextos, CI normalizados) | `pipeline/normalization/person_resolver.py` | 201 M llamadas a `quitar_titulos` (91 % de la lectura): se normalizaban las 14.078 personas en cada una de las 8.178 resoluciones |
| 2 | Caché por consolidación de `DimOrigenDocumental` por documento, docente por nombre e institución por nombre | `backend/services/dw_loader.py` | 85.630 + 17.941 + 1.098 consultas repetidas |
| 3 | Evaluación docente en bloque (`diferir_eval` + `finalizar_cargas`, `execute_values` por páginas de 2.000) también en la consolidación de DataOps; el `ON CONFLICT` protege solo las 4 columnas que decide la bandeja, igual que la carga fila a fila | `backend/routers/dataops/consolidacion.py`, `dw_loader.py` | 81.481 `SELECT` + 81.481 `INSERT` + `flush` por respuesta |
| 4 | Orden fijo de las filas de staging al consolidar (`ORDER BY id`) | `consolidacion.py` | el resultado dependía del orden físico de la tabla (campos "el primero gana", numeración de ocurrencias) |
| 5 | Peticiones al índice BETO en paralelo (2 a la vez, `BETO_PETICIONES_SIMULTANEAS`) | `backend/services/confianza_service.py` | las 5.643 líneas sin caché iban de a una petición: ≈270 s |
| 6 | Servicio BETO con 2 procesos (`uvicorn --workers 2`, `BETO_WORKERS`), modelo cargado al arrancar cada proceso | `docker-compose.yml`, `pipeline/semantic/inference_server.py` | benchmark: 1 proceso 20,8 líneas/s, 2 procesos 31,8 (fase B) |
| 7 | Deshacer no bloqueante en la revisión: cada operación tiene su cuenta de 10 s y su botón; programar una no espera a la anterior | `frontend/.../hooks/colaRevision.mjs`, `useRevisionAcciones.js`, `HumanReviewFlowView.jsx` | la espera de 10 s por acción era el 70 % del tiempo humano estimado |
| — | Avance de `dataops_tarea` | — | ya estaba limitado a una escritura por segundo (`INTERVALO_SEG = 1.0`); sin cambio |
| — | Reutilizar la extracción del paso ③ en la consolidación | — | no se hizo: la lectura pasa `apariciones_lote = n` y la consolidación `1`, así que reutilizarla cambiaría la confianza de las entidades guardadas en `payload_json`; tras el cambio 1 la extracción ya no pesa |

Pruebas nuevas: `tests/sprint3/test_person_resolver_preparado.py` (equivalencia con el algoritmo original sobre 77 consultas y 300 personas; invalidación al cambiar la lista),
`tests/sprint5/revision_cola.test.mjs` (cola de operaciones). Suite: 634 passed, 11 skipped, 7 xfailed.

## Regresión de resultados (código anterior vs nuevo)

Mismos 10 slices en bytes (`CICLO_REUSAR_SLICES=1`; regenerarlos con openpyxl cambia el hash del archivo y con él `clave_origen`),
mismo orden de staging en ambos, ambos árboles de código dentro del contenedor (`/tmp/old` = HEAD `8c3cf1c`, `/tmp/new` = este cambio),
cada uno sobre su copia del snapshot con el DW vaciado. `scripts/huella_dw.py` + `scripts/comparar_huellas.py`
(`docs/evidencias/regresion_A/huella_old.json`, `huella_new.json`):

**IDÉNTICAS** las 14 tablas (conteo y md5 de filas ordenadas sin claves sustitutas ni marcas de tiempo): 85.630 hechos
(81.481 evaluación docente, 1.393 académicos, 1.030 financieros, 1.320 costos, 362 marketing, 95 rentabilidad, 1 techo),
6.656 en `stg_entidad_no_resuelta`, 14.939 estudiantes, 3.822 módulos, 685 docentes, 2.230 tiempos, 16.302 `carga_fila_origen`, 11 inconsistencias;
bandeja 194 casos / 12 grupos (7 manuales, 71 casos); KPI-10 y KPI-11 sin dato en la gestión (igual en ambos), KPI-18 = 71.

Nota sobre el procedimiento: una primera comparación "anterior vs nuevo" resultó inválida porque `services/ingestion_service.py` inserta `/app` al
frente de `sys.path` y la copia antigua terminó importando el código nuevo; se corrigió en las copias y se repitió. También se descartó una
diferencia aparente en `clave_origen` que venía de regenerar los slices (hash del archivo distinto), no del código.

## Tiempos

Corrida única de la regresión (cada árbol en el overlay del contenedor, servicio BETO con 1 proceso):

| Etapa | Anterior | Nuevo |
|---|---:|---:|
| Carga | 16,8 s | 12,3 s |
| Lectura (paso ③) | 1.424,5 s | 168,6 s |
| Consolidación | 1.227,0 s | 448,3 s |
| Revisión, máquina | 1,5 s | 1,6 s |
| **Máquina** | **2.669,8 s (44,5 min)** | **630,8 s (10,5 min)** |

3 corridas con el código final por la ruta de despliegue (`/app`, bind mount) y el servicio con 2 procesos, máquina sin carga (`docs/evidencias/flujo_repetido_A2/`):

| Etapa | Antes (3 corridas) | Después (3 corridas) | DE después |
|---|---:|---:|---:|
| Carga | 8,5 s | 12,8 s | 0,2 |
| Lectura (paso ③), 15.926 líneas | 888,5 s (17,9 líneas/s) | 163,7 s (98,7 líneas/s) | 23,2 |
| Consolidación | 834,0 s | 417,9 s | 63,1 |
| Revisión, máquina | 1,0 s | 1,3 s | 0,3 |
| **Máquina** | **1.732 s (28,9 min), DE 112** | **596 s (9,9 min)** | **86,7** |

Las tres corridas dieron el mismo DW entre sí y la misma huella que la regresión (IDÉNTICAS, 14 tablas, bandeja y KPI).

Recursos (media de las 3 corridas; máximo entre paréntesis): CPU del equipo 43 % (78 %), RAM del equipo 24,4 GiB (26,0),
`giragroup_api` CPU 51 % (101 %), RAM 1,58 GiB (1,74); `giragroup_db` CPU 3,7 % (94 %). La CPU del equipo sube frente a las corridas
anteriores (11–31 %) porque ahora dos procesos BETO infieren a la vez.

### Parte humana (KLM, mismos parámetros que `docs/medicion-flujo-dataops-repetida.md`)

Bandeja: 194 casos en 12 grupos (5 en bloque, 1 corrección de fecha, 7 manuales con 71 casos). K 0,28; P 1,10; H 0,40; M 1,35; clic 0,20; W 10 s.

| | Deshacer bloqueante (antes) | Deshacer no bloqueante (ahora) |
|---|---:|---:|
| Parte humana | 1.071 s (17,9 min) | 311 s (5,2 min) |
| **Total estimado (máquina + humano)** | **46,7 min** antes / 27,8 min con la máquina nueva | **15,1 min** |

Con el Deshacer no bloqueante el revisor no espera los 10 s entre acciones (siguen corriendo en paralelo, cada una cancelable), así que el
modelo sin espera es el que corresponde. 15,1 min queda 0,1 min por encima de la meta RNF-03 (15 min) con la caché de índices heredada del snapshot (63,6 % de aciertos).

Referencia anterior (3 corridas, código anterior, `docs/medicion-flujo-dataops-repetida.md`): máquina 1.732 s (DE 112): lectura 888 s, consolidación 834 s.

Advertencia sobre la variabilidad: la misma lectura del código anterior midió 888 s (3 corridas desde `/app`) y 1.424 s (desde el overlay), y la
nueva 169 s (overlay) frente a 291–325 s (`/app`). Parte es el sistema de archivos del bind mount de Windows y parte es variación del equipo;
por eso las cifras de referencia son las 3 corridas por la misma ruta, con su DE.

## Benchmark del servicio BETO (fase B, `POST /infer-batch`, 15.488 textos de 8 celdas sin caché)

| Configuración | líneas/s | CPU pipeline | RAM pipeline | Nota |
|---|---:|---:|---:|---|
| a) 4 hilos × 1 proceso | 20,8 | 389 % | 0,61 GiB | 47,8 ms por oración en el servidor |
| a') ídem con la línea completa (1.373 caracteres de media) | 5,7 | 388 % | 0,76 GiB | 175,5 ms por oración: el texto de 8 celdas es 3,7× más rápido |
| **b) 4 hilos × 2 procesos** | **31,8** | 767 % | 1,25 GiB | elegida |
| c) 4 hilos × 3 procesos | 28,5 | 1.125 % | 1,85 GiB | corrió con la suite de pruebas en paralelo (CPU del equipo 57 %); no mejora a b |
| d) 8 hilos × 1 proceso | 17,7 | 385 % | 1,87 GiB | solo usó 4 núcleos; peor que a |

Ninguna configuración alcanza las 40 líneas/s del criterio de la fase C; la mejor es b con 31,8 (0 errores; 1.427 textos sin entidades en todas).
Con b, las 15.488 líneas distintas de un lote sin caché tardarían ≈ 487 s (8,1 min) en BETO.

## Pendiente

- Fase C (BETO real en el paso ③) descartada por ahora (decisión del autor): cambia resultados, obliga a un snapshot nuevo y el servicio no llega a 40 líneas/s.
- La pantalla de revisión con el Deshacer no bloqueante no se verificó en el navegador (sí sus pruebas de Node).
