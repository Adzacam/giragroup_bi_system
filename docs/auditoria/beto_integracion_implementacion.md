# Integración de BETO en el paso ③: implementación (opciones 1–3 y ventana)

Rama `beto-integracion`, creada desde `limpieza-repo` (73ec78f). Esta fase **implementa** las tres opciones y la ventana deslizante, cada una tras un flag
apagado por defecto, con pruebas. **No** se ejecutó la medición final ni se tocaron cifras, figuras ni el documento de la tesis.

## 1. Aislamiento

| Qué | Cómo |
|---|---|
| Snapshot `snapshot_dw_20261110_1201` | solo lectura (`pg_dump`). Huella de las 48 tablas (209.376 filas, md5 global `93234ced…`) idéntica antes y después del trabajo: `docs/mediciones/huella_snapshot_origen.json` |
| DW viva | no se usó. Las pruebas y los flujos corrieron contra una PostgreSQL 16 en tmpfs (`beto_pg_tmpfs`, `127.0.0.1:55432`) y una copia del catálogo; la API viva y `giragroup_db` no recibieron conexiones de este trabajo |
| Fidelidad de la copia | copia recién restaurada = origen, tabla por tabla (`huella_snapshot_copia_tmpfs.json`, sin diferencias) |
| Servicio BETO (:8006) | el de siempre (sin estado); se reinició para cargar el código nuevo. Es el único recurso compartido |

Comandos: `sh scripts/aislada_tmpfs.sh up` · `vacio` · `clon <db>` · `down` (ver §7).

## 2. Flags (`pipeline/config.py:BETO_FLAGS_POR_DEFECTO`, todos `False`)

Cada flag se activa con la variable de entorno del mismo nombre (`1`, `true`, `si`, `on`); `services/beto_integracion.py:activo()` la lee en cada llamada.

| Flag | Opción | Efecto |
|---|---|---|
| `BETO_CASCADA_FINAL` | 1 | BETO como última etapa, solo para residuales |
| `BETO_ACUERDO_QC` | 2 | acuerdo regla–BETO como control de calidad |
| `BETO_SUGERENCIA_HITL` | 3 | candidatos ordenados por score combinado en la bandeja |
| `BETO_VENTANA` | — | ventana deslizante (128 tokens, solape `BETO_VENTANA_STRIDE`, 32 por defecto) |

Constantes nombradas (no mágicas), también en `pipeline/config.py`: `BETO_ESCALON_DESACUERDO_MARGEN` (0,01 → el índice baja a 0,84), `BETO_SOLAPE_MINIMO_ACUERDO` (0,5),
`BETO_PESO_SIMILITUD` / `BETO_PESO_PROBABILIDAD` (0,5 / 0,5), `BETO_SUGERENCIAS_MAXIMAS` (5), `BETO_SUGERENCIA_CORTE_SIMILITUD` (70, solo para listar, no decide),
`BETO_TIPOS_FUENTE_CON_PERSONA` (ACTA, MOODLE, COBRANZA, ADMISION), `MOTIVO_DESACUERDO_REGLA_BETO`.
**Sin cambios:** 0,92 personas · 90 % homónimos · 85 % CI variante y docentes · 80 % módulos · bandas 0,85 / 0,60 · cascada CI_EXACTA → ENCABEZADO → FUZZY → REGEX (hay una prueba que fija los dos primeros).

## 3. Qué cambió por opción

### Opción 1 — BETO como última etapa (residuales)
- **Dónde:** `services/beto_integracion.py:refinar_lineas` (paso ③ en `routers/dataops/evaluacion.py`, consolidación en `consolidacion.py`); `extract_entities_from_line` acepta `est_beto` / `doc_beto` opcionales.
- **Residual:** línea de un tipo de documento con persona, que no es ruido (`fila_sin_entidad`), cuyo estudiante falta o es «perfil nuevo» (o cuyo docente tiene candidato sin resolver). El criterio de «confianza < banda baja» se aplica a esas personas: lo que las reglas resolvieron contra el catálogo (A/B) no se envía.
- **BETO:** `/infer-batch` (256 textos por petición, 2 a la vez), entidades de BETO antes de reglas y catálogo (campo nuevo `entidades_beto`), con caché. Se toma la entidad de mayor probabilidad del tipo pedido, fuera de columnas ajenas (asesor, sede…).
- **Resolución:** el nombre propuesto se resuelve con la misma cascada y umbrales (`_mejor_estudiante` / `_mejor_docente`, ≥ 80). Si se resuelve: entidad con `fuente_resolucion = "BETO"`, `lecturaModelo` = probabilidad de BETO (no una lectura base fija) y los bonos vigentes. Si no: la línea queda como estaba (HITL). **BETO nunca sobrescribe una resolución A/B ni crea perfiles** (una prueba lo fija).
- **Trazabilidad:** columna ya existente (`fuente_resolucion` dentro de las entidades de la lectura); sin cambio de esquema.
- **Contadores** (`Contadores.como_dict()`): `lineas_totales`, `residuales_enviadas`, `resueltas_por_beto`, `a_hitl`, `tiempo_beto_s`, `peticiones`, `textos_inferidos`, `textos_en_cache`. Salen en el resultado de la lectura (`beto`, también guardado en `dataops_tarea.resultado`) y en la respuesta de la consolidación (`beto`).

### Opción 2 — Acuerdo regla–BETO
- Para cada estudiante o docente que resolvieron las reglas se busca su nombre en el texto que vio BETO (frase completa o, si las reglas lo armaron con varias columnas, palabra por palabra) y se mide qué fracción cubren entidades persona de BETO (≥ 0,5 = acuerdo).
- **Acuerdo** → sin cambio. **Desacuerdo** (regla = persona, BETO = O) → la confianza baja un escalón (de pase directo a 0,84, banda de revisión; lo que ya está bajo 0,85 no se toca), `requiere_revision = True` y motivo `DESACUERDO_REGLA_BETO` (paso ③: `motivo`; consolidación: fila en `log_inconsistencias`). **Tipo distinto** (BETO la ve como módulo/programa) y **no evaluable** (el nombre queda fuera del texto que vio BETO) no se penalizan.
- **Métricas:** `comparadas_acuerdo`, `acuerdos`, `desacuerdos`, `tipo_distinto`, `no_evaluables`, `tasa_acuerdo`, `desacuerdos_por_archivo_y_tipo` (clave «archivo | tipo de documento»).
- **No toca** las excepciones que filtran las reglas (correo, Likert, comentario, un solo token): se descartan antes y una prueba lo fija.

### Opción 3 — Sugerencia en la bandeja HITL
- `score_combinado = 0,5 · similitud(nombre de la regla, candidato) + 0,5 · probabilidad_beto · similitud(tramo de BETO, candidato)`. Sin lectura de BETO queda solo la similitud.
- Homónimos: el cargador (`DWLoaderService.sugeridor`) guarda los candidatos ordenados en `payload_json.sugerencias` del caso. Grupos manuales (baja confianza): lo mismo desde la consolidación. Solo ordena: no se aprueba nada y `un_clic` no cambia.
- **API (aditiva):** campo opcional `sugerencias_beto` en cada caso de `GET /review-tray`, con `id`, `nombre`, `ci_enmascarado`, `similitud`, `probabilidad_beto`, `similitud_beto`, `tramo_beto`, `score_combinado`. Sin el campo, la respuesta es idéntica a la anterior (prueba). Vista: tabla de candidatos en `HumanReviewFlowView.jsx`.

### Ventana deslizante (`BETO_VENTANA`)
- `/infer-batch` acepta `ventana`, `stride` y `max_length` (128). El texto se parte en tramos de 126 tokens con solape `stride`; cada tramo se lee con el pipeline NER y las entidades se fusionan por máxima probabilidad (`pipeline/semantic/ventana.py`; las cortadas por el borde ceden ante la completa de la ventana vecina). Sin los campos nuevos el servicio se comporta como antes. **No se pasa a 512 tokens.**
- Con el flag se manda la línea completa (no las 8 celdas) y la clave de caché cambia (`…|ner|ventana128+<stride>`).
- Humo contra el servicio real: texto corto idéntico con y sin ventana; texto largo responde con ambas.

## 4. Cambios de esquema y de API

| Cambio | Detalle |
|---|---|
| Tabla nueva `cache_beto_entidades` (migración `015_cache_beto_entidades.sql`) | **Justificación:** `cache_indice_beto` guarda un solo número por texto; las opciones necesitan la lista de entidades. Está **fuera** de `MIGRACIONES_EN_ARRANQUE` (una prueba existente fija esa lista) y el módulo la crea al primer uso con un flag encendido. Con todo apagado no existe ni se usa |
| `POST /infer-batch` | campos de entrada opcionales `ventana`, `stride`, `max_length`; campo de salida nuevo `entidades_beto` |
| `GET /review-tray` | campo opcional `sugerencias_beto` |
| Lectura (paso ③) y consolidación | clave opcional `beto` (contadores) solo con flags encendidos |
| `ResultadoInferenciaNER` | campo `entidades_beto` (no va en `to_dict`) |
| Motivo nuevo | `DESACUERDO_REGLA_BETO` (`log_inconsistencias.tipo_regla`; etiqueta en `MOTIVOS` de la bandeja) |

## 5. Pruebas

| | Resultado |
|---|---|
| Colectadas | **699** (652 de la rama base + 47 nuevas) |
| Resultado | **681 passed, 0 failed**, 11 skipped, 7 xfailed (los mismos skips y xfails de antes; sin skip nuevo ni aserciones existentes modificadas) |
| Cobertura (`--cov=backend --cov=pipeline`) | **70,15 %** (10.210 / 14.555); antes 68,45 % |
| Node | 5 de la rama base, sin cambios; la vista compila (`vite build`) |

Pruebas nuevas: `tests/sprint3/test_beto_cascada_final.py` (13), `test_beto_acuerdo_qc.py` (11), `test_beto_ventana.py` (11), `tests/sprint5/test_beto_sugerencia_hitl.py` (9),
`test_beto_integracion_flujo.py` (4, con servicio BETO simulado de extremo a extremo en lectura y consolidación); soporte en `tests/sprint3/beto_utiles.py`.
Se ejecutó la suite de sprint 2/3/5 tras cada commit y la completa al final; ninguna falló, no hizo falta revertir.

Commits (uno por opción): `c1fa29e` flags, cliente y caché · `8723f14` opción 1 · `ead64a0` opción 2 · `391a0db` opción 3 · `632a94d` ajuste del acuerdo con nombres de varias columnas · `8bac1d2` ventana · y uno de contadores.

## 6. Verificación con los flags apagados: huella idéntica

Mismo lote (10 archivos del ciclo, bytes fijos), clones de la misma plantilla, `scripts/huella_dw.py` + `scripts/comparar_huellas.py`:

- **Referencia:** código de `limpieza-repo` (73ec78f) sin cambios → `docs/mediciones/flujo_base.json.huella.json`.
- **Rama final, todo apagado** → `docs/mediciones/flujo_off_final.json.huella.json`.
- Salida: `IDÉNTICAS: 14 tablas, bandeja 182 casos / 12 grupos, KPI {'KPI-10': None, 'KPI-11': None, 'KPI-18': 59.0}` (`docs/mediciones/comparacion_huella_flags_apagados.txt`).
  Son 14 tablas por conteo y md5 de filas ordenadas (hechos, dimensiones, staging, claves de origen, inconsistencias), la bandeja y los KPI del CMI.

**Sobre «idéntico al snapshot del 10-nov»:** el snapshot es un DW ya consolidado con otra carga histórica (p. ej. 22.618 hechos académicos), no el resultado de este lote: no hay forma de reproducirlo desde los 10 archivos de hoy. Lo que sí se comprobó es (a) que el snapshot no cambió (huella global de 48 tablas igual antes y después), (b) que la copia aislada es idéntica a él, y (c) que el DW que produce el código con los flags apagados es idéntico al del código de la rama base sobre el mismo lote. Esa es la garantía operativa: con los flags apagados no cambia nada.
(El lote de hoy da 12.992 líneas y 182 casos; las 15.926 y 194 de las mediciones anteriores corresponden a otro estado de `uploads/data`. Las comparaciones de esta fase usan siempre los mismos bytes.)

## 7. Comandos exactos para la fase de medición (no ejecutados)

Preparación (una vez):
```bash
sh scripts/aislada_tmpfs.sh up            # PostgreSQL tmpfs + copia del snapshot y del catálogo
sh scripts/aislada_tmpfs.sh vacio         # plantilla dw_vacio (snapshot vaciado + migración 014)
sh scripts/copiar_arbol.sh medida         # árbol de código a /tmp/medida del contenedor
# slices fijos de los 10 archivos (una vez; luego CICLO_REUSAR_SLICES=1 los reutiliza): ver scripts/flujo_aislada.sh y medir_ciclo_mensual.py
docker compose restart pipeline           # carga el servicio con /infer-batch nuevo (BETO_WORKERS=2)
```
**A/B por flag** (cada línea = 1 corrida; repetir 3 veces con `run_<n>` distinto; `CACHE_VACIA=1` = mes nuevo, sin = caché llena):
```bash
sh scripts/flujo_aislada.sh /tmp/medida run_a0 a0.json                                              # todo apagado (referencia)
sh scripts/flujo_aislada.sh /tmp/medida run_a1 a1.json BETO_CASCADA_FINAL=1                         # opción 1
sh scripts/flujo_aislada.sh /tmp/medida run_a2 a2.json BETO_ACUERDO_QC=1                            # opción 2
sh scripts/flujo_aislada.sh /tmp/medida run_a3 a3.json BETO_SUGERENCIA_HITL=1                       # opción 3
sh scripts/flujo_aislada.sh /tmp/medida run_a12 a12.json BETO_CASCADA_FINAL=1 BETO_ACUERDO_QC=1      # combinadas
CACHE_VACIA=1 sh scripts/flujo_aislada.sh /tmp/medida run_v1 v1.json BETO_CASCADA_FINAL=1 BETO_ACUERDO_QC=1 BETO_SUGERENCIA_HITL=1   # caché vacía
CACHE_VACIA=1 sh scripts/flujo_aislada.sh /tmp/medida run_w1 w1.json BETO_ACUERDO_QC=1 BETO_VENTANA=1                               # ventana
```
Cada corrida deja `docs/mediciones/<salida>.json` (tiempos por etapa, líneas/s, `lectura_beto_contadores`, `consolidacion_beto_contadores`) y `<salida>.json.huella.json`.
- **Diferencia de DW por flag:** `python scripts/comparar_huellas.py docs/mediciones/a0.json.huella.json docs/mediciones/a1.json.huella.json` (con flags apagados debe dar IDÉNTICAS; con un flag encendido las diferencias son el efecto).
- **Ablación:** repetir el A/B por flag y por combinación (a0, a1, a2, a3, a12, a123) y tabular hechos, staging, bandeja (casos y grupos), KPI-10/11/18 y `desacuerdos`/`tasa_acuerdo`/`resueltas_por_beto`.
- **Tasa de acuerdo y desacuerdos por archivo/tipo:** `consolidacion_beto_contadores` (y `lectura_beto_contadores`) de las corridas con `BETO_ACUERDO_QC=1`; añadir `BETO_VENTANA=1` para reducir los «no evaluables».
- **Tiempo de flujo con caché vacía y llena:** `CACHE_VACIA=1` frente a sin ella, 3 corridas cada una (media y DE con `scripts/agregar_flujo_repetido.py`).
- **Humo previo (opcional):** `BETO_ACUERDO_QC=1 BETO_CASCADA_FINAL=1 python scripts/humo_beto_integracion.py 150` dentro de `giragroup_api` con `DATABASE_URL` de una base aislada con un lote cargado.
- **Suite:** `DATABASE_URL=postgresql://giragroup_user:tmpfs_local@127.0.0.1:55432/giragroup_db CATALOG_DATABASE_URL=postgresql://giragroup_user:tmpfs_local@127.0.0.1:55432/catalogo_copia python -m pytest tests --cov=backend --cov=pipeline`.
- **Al terminar:** `sh scripts/aislada_tmpfs.sh down`.

## 8. Riesgos abiertos

1. **«No evaluable» alto sin ventana.** En el humo (150 líneas de cobranzas) 145 comparaciones fueron no evaluables: el nombre queda fuera de las primeras 8 celdas que ve BETO. La tasa de acuerdo solo será representativa con `BETO_VENTANA=1`, que manda la línea completa y cuesta más (≈ 3,7× por texto en el benchmark anterior).
2. **Costo de la opción 2.** Compara todas las personas resueltas por reglas: es un pase de BETO sobre casi todo el lote (con caché vacía ≈ 13 min con 2 procesos, 31,8 líneas/s). La opción 1 envía pocas líneas.
3. **Fragmentos de BETO.** Con nombres en mayúsculas el servicio devuelve a veces trozos («ED» + «GAR» para EDGAR). La comparación usa la unión de tramos persona (≥ 50 % de los caracteres del nombre) y por eso lo tolera, pero un nombre cortado entre etiquetas distintas puede dar falsos desacuerdos; conviene mirar los desacuerdos por archivo antes de fiarse de la tasa.
4. **Efecto en KPI-10.** Con la opción 2 los hechos en desacuerdo bajan su `nivel_confianza_ia` a 0,84 (por diseño): KPI-10 y KPI-11 cambian y la bandeja crece con casos de motivo `DESACUERDO_REGLA_BETO` (hechos cargados en revisión, no filas de staging). No hay vista propia del motivo en la bandeja de hechos: queda en `log_inconsistencias` y en el paso ③.
5. **Opción 1 con efecto acotado en el DW.** En la consolidación la identidad de los hechos académicos viene de los encabezados, no del extractor; el nombre que promueve BETO influye en filas financieras/de admisión, en el estado de la lectura y en la bandeja. No es un «rescate» de las ≈ 3.500 filas académicas sin estudiante: esas son ruido por encabezado y se descartan antes.
6. **Orden de las sugerencias (opción 3).** Los pesos 0,5 / 0,5 son una decisión de diseño sin validar contra decisiones humanas; hay que medir en la fase de medición cuántas veces el primer candidato coincide con el que el revisor elige.
7. **Caché de entidades.** Los nombres de personas se guardan en `cache_beto_entidades` (como en el DW); no hay purga automática.
8. **Servicio compartido.** Reiniciar `giragroup_pipeline` afecta a cualquier consumidor del puerto 8006 durante unos segundos; el flujo aislado y la API viva comparten ese servicio.
9. **Humo, no medición.** El humo de §5 y el de la ventana comprueban el cableado, no valen como resultados.

## 9. Archivos tocados (24 respecto de 73ec78f, además de evidencias en `docs/mediciones/`)

`pipeline/config.py` · `pipeline/semantic/{inference_server,ner_engine,ner_schema,ventana}.py` · `backend/services/{beto_integracion,dw_loader,revision_consulta}.py` ·
`backend/routers/dataops/{consolidacion,evaluacion,extraccion}.py` · `backend/scripts/migrations/015_cache_beto_entidades.sql` · `frontend/src/modules/dataops/HumanReviewFlowView.jsx` ·
`scripts/{aislada_tmpfs.sh,copiar_arbol.sh,flujo_aislada.sh,huella_base_completa.py,humo_beto_integracion.py,medir_flujo_dataops.py}` · pruebas listadas en §5.
