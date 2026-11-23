# PLAN F5V — 2026-11-19
Objetivo de la fase (1 línea): cerrar los huecos visibles del flujo DataOps (V1 y V2), pasar las funciones del ex-paso ② al paso de lectura y completar el modal de métricas BETO con precisión, recall y curva de épocas animada, sin cambiar invariantes ni cifras.
Entrada: CIERRE previo leído = `CIERRE_FRONT_V2.md` (y `CIERRE_F3X.md`); rama base = `beto-integracion` `4d79857`. F5R en curso (no se toca la DW viva ni sus lotes).

## 1. Evaluación (lo que ya existe)
V2 **no tiene vistas propias de DataOps**: las rutas `/v2/dataops/*` (`frontend/src/App.jsx:573-615`) montan los mismos componentes V1 de `frontend/src/modules/dataops/*` dentro de `MainLayoutV2`. Todo cambio en V1 aparece en V2. El stepper tiene **3 pasos**: ① Carga · ② Lectura de BETO · ③ Revisión (N) (`components/BatchFlowStepper.jsx:13-39`). La antigua ruta `/dataops/texto` redirige a `…/beto?tab=texto` (`App.jsx:23-27`).

Leyenda: ✅ visible en vivo (V1 = V2) · 🟡 parcial · ❌ falta. Rutas relativas a `frontend/src/modules/dataops/` (front) o a la raíz (back).

| Tarea | Front (V1 = V2) | Backend / pipeline | Estado |
|---|---|---|---|
| T7 Lector Excel/Sheets + cabeceras | Carga: drag&drop `.xlsx/.csv` `IngestView.jsx:393-425`; cola paginada :359/:755 | `pipeline/ingesta.py:45` `_leer_xlsx`; `backend/services/extraccion_por_encabezado.py:48` `normalizar_encabezado` | ✅ |
| T8 Google Forms CSV (admisión) | Chip "Google Forms (Admisiones / Pagos)" en Carga | `pipeline/ingesta.py:79` `_leer_csv`; `asymmetric_flattener.py:128` `GFORMS_ADM_PAGOS`; `ingestion_service.py:189` | ✅ (sin lector dedicado; se detecta por cabeceras) |
| T9 Moodle CSV/XLSX | Chip "Moodle Export"; selector escala solo ACTA/MOODLE `IngestView.jsx:665-682` | `backend/services/readers/moodle_adapter.py:47,66` | ✅ |
| T10 Dispatcher tipo documental | Selector tipo `IngestView.jsx:647-661` (`dataopsConfig.js:33`) | `ingestion_service.py:233` `detectar_tipo_fuente_por_cabeceras`, :202 | ✅ |
| T11 Texto plano `col: val \| col: val` | Pestaña "Texto preparado" `components/TextoPreparadoTab.jsx:60-192` ("Del archivo al texto", Ver campos (N), Ver texto completo, Detalles de preparación) | `ingestion_service.py:460`; `oracion_beto` en `texto_preparado_service.py:58`; `GET /lote/{id}/raw-vs-text` `lectura.py:252` | 🟡 faltan los 3 KPI en la pestaña (hoy solo en `IngestView.jsx:759-773`); vista vieja `PlainTextTransformationView.jsx` huérfana |
| T13 Logs / bitácora | Drawer `components/PipelineTelemetryDrawer.jsx` (SHA-256 :61, cascada canónica :64, Eventos/Columnas :69, `.md` :36-47) | `ingestion_service.py:557` `_registrar_log`, :508 SHA-256; `GET /logs/{doc_id}[/export]` `ingesta.py:693-708` | ✅ (drawer sin animación de entrada) |
| T15 NER fila a fila | Entidades en "Ver explicación…" `BetoReadingFlowView.jsx:81` | `pipeline/semantic/ner_engine.py:92,173,256`; origen por entidad `fuente_resolucion` en `backend/routers/dataops/extraccion.py:294-606` | 🟡 se ven las entidades (estudiante, documento, docente, módulo, programa) pero no la etiqueta del modelo ni si las leyó BETO o una regla; en `TBL_INSCRITOS` hay mapeos dudosos (ver V-7, V-8) |
| T18 `indice_registro` / `motivo_llano` | Índice % :74; `motivo_llano` :79 | `backend/routers/dataops/evaluacion.py:291,502` | ✅ |
| T19 Requiere revisión / bandeja | Paso ③: pestañas Por grupos / Pendientes / Resueltos `HumanReviewFlowView.jsx:246`; `GruposBandeja.jsx` | `extraccion.py:819`; `revision.py:46,63,107` | 🟡 en vivo los 5 primeros grupos muestran el mismo motivo "Hecho cargado que necesita revisión" (no se distinguen) |
| T20 Inconsistencias / CSV | `por_que_detuvo` :129; "Exportar incidencias" :252 | `revision_consulta.py:135`; `GET /review-tray/export` `revision.py:76` | ✅ |
| T21 Consolidar + integridad | "Consolidar lote" :238; "Comprobar conteos del lote" `IntegridadLote.jsx` | `consolidacion.py:49,125`; `GET /lote/{id}/integridad` `lectura.py:63` | ✅ |
| T22 Métricas BETO / matriz | Botón "Métricas del modelo" `BetoReadingFlowView.jsx:150` → `components/BetoMetricasModal.jsx` (ficha, F1 estricto/relajado, desglose por clase, matriz 5×5, tabla de épocas); datos `src/constants/betoMetricas.json`; prueba `__tests__/w9MetricasModelo.test.jsx` | Sin endpoint (cálculo en `scripts/matriz_confusion_ner.py`, `ablacion_beto.py`) | 🟡 en vivo V1 y V2 (V2 con `modalPop`): **no muestra P 97,29 % ni R 98,63 %** (solo TP/FP/FN), épocas solo en tabla (sin curva), cifras sin conteo animado, rótulo "Métricas del modelo" |
| Archivo de entrenamiento + épocas | Tabla "Entrenamiento por época" `BetoMetricasModal.jsx:307-361` | `docs/mediciones/f1_training_info.json` `epoch_history` | 🟡 falta curva animada |
| T23 `POST /pipeline/process` | Carga usa `/process-batch` ("Procesar seleccionados (N)" `IngestView.jsx:457`) | `backend/routers/pipeline.py:264` `POST /api/v1/pipeline/process`; `ingesta.py:599,688` | ✅ (backend); rótulo distinto al pedido |
| T27 Respaldo difuso / `sugerencias_beto` | Tabla Candidato/Similitud/Prob. BETO/Score `HumanReviewFlowView.jsx:142-146` | `dw_loader.py:291` (cutoff 90), `beto_integracion.py:478-524` | ✅ |
| T28 Enmascarado + revelar con auditoría | Cédula `••••709` + "Revelar con auditoría" (lectura :57, revisión :132), "Ver texto original protegido" :140; texto preparado enmascarado | `dataops_evaluation_service.py:221` `enmascarar_ci`; `GET /registro/{id}/revelar-ci` `lectura.py:521` (escribe `LogAuditoriaNlp`) | ✅ |
| T33 Conteos de calidad | Cabecera del lote (Registros, En revisión), historial (3 lotes), 4 KPI de lectura, contadores de revisión | `GET /lote/{id}/resumen` `lectura.py:77`; `/telemetry/summary` `maestros.py:483` | 🟡 KPI "En revisión" = 0 en lectura mientras el stepper dice "Revisión (1411)" sin explicar la diferencia |

Hallazgos adicionales en vivo:
- H1. Revisión, caso "Cédula dudosa" de `TBL_INSCRITOS.xlsx`: el formulario pide **Institución / Clave de convenio / Monto de convenio** (campos de convenio, no de identidad). `backend/services/revision_formularios.py`.
- H2. `GET /telemetry/summary` declara `"PyTorch 2.2"` fijo (`maestros.py:499`); `f1_training_info.json` `versions` registra otra versión.
- H3. Texto preparado, fila 1: `NOMBRE DEL PROGRAMA: ESO INTERNACIONAL DE LIDERAZGO…` — posible corte del nombre del programa (verificar contra el `.xlsx`).
- H4. Las cifras animadas parten en 0 hasta entrar en pantalla (comportamiento esperado de `AnimatedNumberV2`); no es defecto.
- Cifras del modal = SFV (`docs/fuente_verdad_tesis.md:133-152`, origen `f3r_ablacion.json` / `f3r_matriz_confusion.json`). **No hay cifra nueva ni pendiente.** `f1_evaluacion_despues/metricas.json` trae 0,9805 (otra corrida); no se usa.

## 2. Tareas (lo que falta)

| ID | Loop | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida / Evidencia |
|---|---|---|---|---|---|---|---|
| V-1 | Loop 1 Métricas BETO | En `BetoMetricasModal.jsx`: (a) rótulo del botón y título "Métricas del Modelo BETO"; (b) tarjeta F1 estricto con **Precisión 97,29 %** y **Recall 98,63 %** leídos de `gold_510_modo_c.estricto.precision/recall`, y relajado con P 98,84 % / R 100 %; (c) cifras con `AnimatedNumberV2`; (d) **curva de épocas** (dev F1 y train/dev loss, 3 épocas, época 2 marcada "Mejor") con `react-chartjs-2` + `withChartAnimationsV2` / `ChartRevealV2`; (e) celda PER_ESTUDIANTE→PROGRAMA resaltada con `--dataops-warning-*`; (f) texto llano: "qué significa" por bloque, sin nombrar tareas. Sin backend; datos siguen en `src/constants/betoMetricas.json` | dev-media | — | V-2, V-4 | 1) en V1 y V2 el modal muestra 97,96 / 97,29 / 98,63 / 99,42 / 0,9979 idénticos a `betoMetricas.json`; 2) la curva tiene 3 puntos = `epoch_history`; 3) `w9MetricasModelo.test.jsx` ampliado (P, R, 3 puntos) pasa; 4) con `prefers-reduced-motion` muestra valores finales | `docs/mediciones/f5v_verificacion_front.json` → `metricas_beto` |
| V-2 | Loop 2 Ex-paso ② | En `TextoPreparadoTab.jsx`: agregar las 3 tarjetas "Registros preparados", "Campos por fila, máximo", "Filas con observaciones" (reutilizar el cálculo de `IngestView.jsx:759-773`, extraer a un hook común) con `AnimatedNumberV2`; aviso por fila con observaciones; botones "Volver a carga de archivos" / "Ver resultados de la lectura". Borrar `PlainTextTransformationView.jsx` huérfano y su entrada en `v2/navigation/routeDataPrefetcherV2.js:36-37` | dev-media | — | V-1, V-4 | 1) pestaña Texto preparado del lote #35 muestra los 3 KPI con los mismos valores que Carga; 2) `grep PlainTextTransformationView` = 0; 3) vitest + build en verde | `f5v_verificacion_front.json` → `texto_preparado` |
| V-3 | Loop 3 Claridad para el usuario | (a) Lectura: nota bajo "En revisión" que explique la diferencia con los casos del paso ③ (identidad/catálogo vs banda 60–85 %); (b) Carga: "Procesar seleccionados (N)" → "Procesar archivos (N)" y columna "Detalle" → "Vista previa"; (c) `PipelineTelemetryDrawer.jsx` con entrada deslizante usando `v2-transitions.css` (respeta reduced-motion); (d) D3: historial con 3 pasos ① Carga ② Lectura de BETO ③ Revisión (`BatchHistory.jsx:29` quita la entrada `texto` muerta) y glosario/ayudas sin mención a un 4.º paso; el título "Lectura de BETO" **se mantiene** (D1) | dev-baja | V-2, V-7 | — | 1) los 3 rótulos visibles en V1 y V2; 2) drawer anima en V2 y abre sin animación con reduced-motion | `f5v_verificacion_front.json` → `rotulos` |
| V-4 | Loop 4 Bandeja (back) | Diagnosticar y corregir: (a) H1 `campos_correccion` para casos de cédula de `TBL_INSCRITOS` (debe pedir identidad, no convenio) en `revision_formularios.py`; (b) motivos de grupo indistinguibles en `/review-tray/grupos` (añadir archivo/tabla/tipo al rótulo del motivo, sin cambiar agrupación ni conteos); (c) H2 `maestros.py:499` leer la versión de torch de `f1_training_info.json`. Pruebas nuevas en `tests/f5v/` | dev-media | — | V-1, V-2 | 1) caso "Cédula dudosa" pide campos de identidad; 2) los 5 primeros grupos del lote #35 tienen rótulos distintos y la suma de casos no cambia (±0); 3) `tests/f5v` en verde; 4) cascada, umbrales y bandas sin cambio (diff limpio en `_comun.py`) | `docs/mediciones/f5v_bandeja.json` |
| V-5 | Loop 4 Bandeja | H3: comparar 20 filas de `TBL_INSCRITOS.xlsx` (columna NOMBRE DEL PROGRAMA) con `staging_registros_crudos.texto_plano` en la **copia tmpfs**; reportar si hay corte y en qué función | dev-baja | — | V-1, V-2, V-4 | 1) veredicto `corte` / `dato_original` con 20 filas comparadas | `docs/mediciones/f5v_nombre_programa.json` |
| V-7 | Loop 6 NER visible | Hacer explícito qué extrajo BETO en "Ver explicación y datos identificados" (`BetoReadingFlowView.jsx:78-84`): (a) añadir `fuente_resolucion` a la lista blanca de `backend/services/dataops_privacy.py:167` (no es dato personal; los tokens siguen enmascarados); (b) por entidad, chip con la etiqueta del modelo (`PER_ESTUDIANTE`, `PER_DOCENTE`, `MODULO`, `PROGRAMA`; CI como dato por regla) y chip de origen en lenguaje llano: "Leído por BETO", "Cédula exacta", "Encabezado del archivo", "Coincidencia aproximada", "Patrón"; (c) mostrar `lecturaModelo` (lectura del modelo) y `betoConfidence` (índice final) como dos barras `AnimatedProgressBarV2`; (d) leyenda corta de colores y orden de la cascada (CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO) sin nombrar tareas | dev-media | V-1 (mismo archivo) | V-8 | 1) en V1 y V2 cada entidad del lote #35 muestra etiqueta + origen; 2) ningún nombre, CI ni correo sale sin enmascarar (prueba de privacidad existente + una nueva); 3) vitest + `tests/f5v` en verde | `f5v_verificacion_front.json` → `ner_visible` |
| V-8 | Loop 6 NER visible (lógica) | Diagnóstico sobre la **copia tmpfs**, sin tocar BETO, umbrales ni cascada: en `TBL_INSCRITOS.xlsx` la lectura asigna "programa" = `CARRERA` (formación previa del inscrito), "docente" = `ASESOR` (asesor comercial) y "módulo" = `NIVEL ACADEMICO` con catálogo por aproximación, y no toma `NOMBRE DEL PROGRAMA`. (a) Contar en el lote #35 entidades por `fuente_resolucion` y por archivo; (b) listar las cabeceras que alimentan cada etiqueta en `backend/routers/dataops/extraccion.py:169-560`; (c) proponer corrección de mapeo por encabezado (p. ej. excluir `CARRERA`, `ASESOR`, `NIVEL ACADEMICO`; aceptar `NOMBRE DEL PROGRAMA`). **No se aplica**: si cambia conteos de hechos, pasa a decisión de Lean | dev-media | — | V-7 | 1) tabla etiqueta × origen × archivo para los 9 archivos; 2) 50 filas de `TBL_INSCRITOS` revisadas con veredicto correcto/incorrecto por etiqueta; 3) propuesta con impacto estimado en conteos | `docs/mediciones/f5v_ner_origen.json` |
| V-9 | Loop 7 Historial (D2) | `pg_dump` de la DW viva → `backups/f5v_pre_borrado.dump`; confirmar `docs_vivos=0` del lote #2 (el #1 ya tiene PLANIFICACION y no se borra; #3 ya no existe); borrar el lote #2 con `eliminar_lote_fuentes` / `DELETE /lote/{id}/fallido` según su estado; dejar auditoría | dev-baja | coordinar con F5R (sin carga en curso) | — | 1) dump presente y restaurable (`pg_restore --list` > 0 líneas); 2) historial muestra 2 lotes (#35, #1); 3) conteos de hechos ±0 | `docs/mediciones/f5v_borrado_lote2.json` |
| V-6 | Loop 5 Verificación visual | Recorrer en el navegador V1 y `/v2/dataops/*` con lote #35: Carga, Lectura (Resultados, Texto preparado, modal, entidades con origen), Revisión (Grupos, Pendientes, un caso abierto). Registrar cada elemento de la matriz como visible/no visible y si anima | dev-baja | V-1…V-5, V-7, V-9 | — | 1) 100 % de las filas ✅ de la matriz siguen visibles; 2) las 🟡 pasan a ✅; 3) 0 errores en consola | `docs/mediciones/f5v_verificacion_front.json` |

Comandos exactos por tarea:
- V-1, V-2, V-3: `cd frontend; npx vitest run` · `cd frontend; npm run build`
- V-4: `python -m pytest tests/f5v -q` · `python -m pytest tests --cov=backend --cov=pipeline`
- V-5, V-8: consulta de solo lectura sobre `beto_pg_tmpfs` (nunca la DW viva ni el snapshot)
- V-7: `cd frontend; npx vitest run` · `python -m pytest tests/f5v -q`
- V-9: `docker exec giragroup_db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > backups/f5v_pre_borrado.dump` · `pg_restore --list backups/f5v_pre_borrado.dump | wc -l`
- Cierre: `$env:POSTGRES_PASSWORD="<.env>"; docker compose up -d --build --no-deps web` y, si V-4 tocó backend, `docker compose up -d --build api`; `docker compose ps`; probar `GET /api/v1/dataops/review-tray/grupos?id_lote=35`

Riesgos y control:
- F5R usa la DW viva al mismo tiempo: V-4 no aprueba, descarta ni consolida casos; solo lectura sobre el lote #35.
- `betoMetricas.json` es una copia: `w9MetricasModelo.test.jsx` la ancla a `docs/mediciones/`; si difiere, falla la prueba (no se edita a mano, se regenera con `scripts/generar_beto_metricas_front.py`).
- Endpoint de métricas: **no se crea**. Las cifras están congeladas, no cambian por lote y la prueba ya las ata a `docs/mediciones/`; un endpoint añadiría superficie sin dato nuevo.
- V-4(b) no puede cambiar la agrupación ni los conteos (criterio ±0).

- V-7 solo amplía la lista blanca con `fuente_resolucion` (texto de origen, sin datos personales).
- V-8 no cambia BETO (`dccuchile/bert-base-spanish-wwm-cased`, 128 tokens), umbrales ni orden de cascada; solo diagnostica el mapeo por encabezado.
- V-9 es destructivo: sin `pg_dump` verificado no se ejecuta.

Hallazgo NER (revisión en vivo, lote #35, 2026-11-19): la pestaña Resultados muestra por fila las entidades como "estudiante / documento / ci / docente / módulo / programa" con su valor enmascarado y su coincidencia de catálogo, pero **no** muestra la etiqueta del modelo ni si la leyó BETO o una regla. La API ya calcula `fuente_resolucion` (BETO, CI_EXACTA, ENCABEZADO, FUZZY, REGEX) en `extraccion.py:294-606`, pero `dataops_privacy.py:167` la descarta. En los registros revisados de `TBL_INSCRITOS.xlsx` la confianza de lectura vale 0,88/0,91, que son los valores por defecto de las reglas (`extraccion.py:103`), no una probabilidad de BETO. Las etiquetas IOB2 (`PER_ESTUDIANTE`…) hoy solo aparecen en el modal de métricas.

DECISIONES DE LEAN (2026-11-19):
- D1. Título del paso de lectura: **se deja "Lectura de BETO"**.
- D2. Lotes vacíos del historial: **sí se borran**, con `pg_dump` previo → V-9.
- D3. **3 pasos** (① Carga ② Lectura de BETO ③ Revisión) en el sistema → V-3(d). En el documento lo aplica el chat 3 (este repo no toca el docx).

- D4 (respondida vía PLAN_F5C, DECISIÓN 1): el mapeo erróneo por encabezado **se corrige ahora** y el índice se recalcula con confianzas medidas por origen; C-4 vuelve a medir todo lo afectado.

## 3. Integración con PLAN_F5C (ajuste 2026-11-19)
F5V y F5C tocan `backend/routers/dataops/extraccion.py` y el mismo flujo visible. Se ejecutan como **una sola fase** con este orden y estos reemplazos:
- **V-8 se absorbe en C-1** (diagnóstico columna → entidad en los 10 libros; mismo objetivo, más amplio). No se ejecuta por separado; su salida es `f5c_columnas_por_entidad.json`.
- **V-5 se ejecuta tras C-0** (necesita los `.xlsx` en `uploads/data/`) y alimenta C-1.
- **V-7 espera a C-3**: los chips de origen usan `origen_confianza` ∈ {`BETO`, `REGLA_ENCABEZADO`, `REGEX`, `FUZZY`, `CI_EXACTA`} (no `fuente_resolucion` ni `lecturaModelo`/`betoConfidence`). Mostrar «Regla por encabezado: similitud 0,96 · valor validado» o «BETO p = 0,73». La lista blanca de `dataops_privacy.py` se amplía con `confianza` y `origen_confianza`.
- **V-4(a,b)** no toca `extraccion.py` (solo `revision_formularios.py`, rótulos de grupos y `maestros.py`): corre en paralelo con C-0/C-1.
- **V-9 y C-5 comparten un único `pg_dump`** previo; V-9 borra el lote #2 y C-5 reprocesa TBL_INSCRITOS.
- **V-6** (verificación visual) va al final, después de C-5, y comprueba además que TBL_INSCRITOS muestra programa correcto y sin docente-asesor.
- **Orden:** C-0 → (V-1, V-2, V-4, V-5, C-1 en paralelo) → C-2 → C-3 (dev-alta; informe A/B; **detenerse y avisar** si KPI-11 < 0,85 o el HITL se multiplica) → V-7 → V-3 → C-4 (dev-alta) → V-9 + C-5 → V-6.
- Invariantes: cascada, umbrales 0,92/90/85/80, bandas 0,85/0,60 y agregador (mínimo) sin cambio. Ninguna regla depende del nombre del archivo. No commitear `backend/routers/powerbi.py`.

Al cerrar: pytest + cobertura · rebuild de `web` (y `api` si V-4) · commit `F5V: <resumen>` · `CIERRE_F5V.md`.

## PROMPT PARA CHAT 2
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F5V.md junto con docs/cierres/PLAN_F5C.md como una sola fase (ver sección 3, orden de ejecución). V-8 queda absorbida por C-1. D1–D4 decididas. Sin cifras nuevas: las del modal salen de betoMetricas.json anclado a docs/mediciones. No apruebes, descartes ni consolides casos. Escribe CIERRE_F5V.md.
