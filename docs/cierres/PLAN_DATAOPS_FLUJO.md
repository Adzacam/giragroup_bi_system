# PLAN DATAOPS_FLUJO (DF) — Saneo del back y de la vista del flujo ① Carga → ② BETO → ③ Revisión — 2026-11-22

**Objetivo (1 línea):** que cada paso de DataOps muestre de forma clara y amigable lo que el sistema hizo, con cifras coherentes entre el back y la vista, y que la revisión humana ofrezca acciones propias de cada tipo de caso, no un mismo «Aprobar / Descartar» para todo.

**Entrada:**
- `CIERRE_ADW.md` (`9eee5bf`), `CIERRE_FU.md` (`f7a9ae2`) y `docs/fuentes/HALLAZGOS_FUENTES_Y_PENDIENTES.md`.
- Rama `beto-integracion`.

**Método:**
- Recorrido real con Playwright (sesión admin, 1440 px) por `/v2/dataops/ingesta`, `/lote/46/beto` y `/lote/46/revision`. Capturas en `.playwright-mcp/p1_*.png`, `p2_*.png` y `p3_*.png`.
- DW viva solo con `SELECT`.
- Lectura de `routers/dataops/*`, `services/revision_*.py`, `HumanReviewFlowView.jsx` y `BetoReadingFlowView.jsx`.

**Reglas que se mantienen:**
- **Invariantes:** cascada CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO; BETO solo para residuales y nunca sobrescribe A/B ni crea perfiles; umbrales 0,92 / 90 / 85 / 80 / bandas 0,85–0,60; estados A/B/C; **DW de 51 tablas + 10 vistas `bi`** (no crear una 52.ª tabla en `giragroup_db`, p. ej. `cache_beto_entidades`, sin decisión escrita de Lean).
- **Principio [[fuentes-agnosticas]]:** nada atado a nombres de archivo u hoja.
- **Agentes:** se lanzan con `model: "sonnet"` (o `"haiku"` para tareas rápidas), nunca con Opus, aunque el rol sea `dev-alta` (excepción consciente de costo sobre la tabla de `AGENTS.md`, aprobada por Lean).
- **Git selectivo:** el árbol de trabajo tiene rutas modificadas/untracked ajenas al plan (`CIERRE_FU.md`); en cada loop usar **`git add` selectivo por archivo tocado** (nunca `git add -A`).

---

## PARTE 1 — Lo que se ve hoy (evidencia)

### ① Carga (`/dataops/ingesta`)
| # | Hallazgo | Evidencia | Grav. |
|---|---|---|---|
| C1 | «Historial de lotes **(0)**» con la sección cerrada; al abrirla dice (13) | `p1_ingesta.png` vs `p1_historial.png`; causa raíz en front: `AnimatedNumberV2.jsx` (`triggerOnView = true` en `BatchHistory.jsx:151`) | 🟠 |
| C2 | La columna **Registros = 0** en los 13 lotes | `p1_historial.png`; causa raíz en front: `AnimatedNumberV2` dentro de `<details>` (`BatchHistory.jsx:228`); verificar además `n_filas` en lotes históricos de BD | 🔴 |
| C3 | «Programas activos» dice 1.227 en Carga, **76** al entrar a BETO y **0** al entrar a Revisión, mientras cargan | `p2_beto.png`, `p3_revision.png`; causa raíz: count-up de 900 ms en `BatchFlowHeader.jsx:47` | 🟠 |
| C4 | Período autodetectado absurdo: «2020–2029 (Auto)», «2020–2026 (Auto)» | tabla `lote` (lotes 40 y 42) | 🟠 |
| C5 | El tipo de fuente que eligió el clasificador, sus señales y su confianza no se ven por archivo; el historial solo muestra «Origen» | `p1_historial.png` | 🟡 |
| C6 | Los nombres de lote son genéricos («libro_4.xlsx»): no se sabe qué fuente es sin abrir la bitácora | `p1_historial.png` | 🟡 |

### ② Lectura de BETO (`/lote/:id/beto`)
| # | Hallazgo | Evidencia | Grav. |
|---|---|---|---|
| B1 | Un lote de **Evaluación docente** muestra «Escala: No aplica (Finanzas/Admisión)» y sus filas dicen «**Académica**», «Sin módulo o concepto identificado» y «Cédula: Sin dato» | `p2_beto_b.png` | 🔴 |
| B2 | Cascada: Cédula exacta **0** · BETO **0** de 61.821 entidades. En la pestaña de BETO, BETO aparece sin aportar nada y no se explica qué leyó, solo qué aceptó | `p2_beto_b.png`; 4 flags `BETO_*` en `False` (`pipeline/config.py:51-56`), `evaluacion.py:277-280` descarta `r_beto.beto_ents` y fija hex en líneas 431–435; `lectura.py:128` aún cita paso ③ | 🔴 (para la defensa) |
| B3 | Las entidades NER (IOB2) solo se ven dentro de «Ver explicación», fila por fila; el texto no se resalta por tipo de entidad | `p2_beto_b.png` | 🟠 |
| B4 | «En revisión **28**» en la tarjeta frente a «Revisión **(376)**» en el paso ③, en la misma pantalla | `p2_beto_b.png` | 🟠 |
| B5 | Paginación de **5 filas** sobre 18.990 = 3.798 páginas | `p2_beto_b.png` | 🟠 |
| B6 | Pantalla «Comprobando el estado del lote…» de 5 a 10 s, sin skeleton | `p2_beto.png` | 🟡 |

### ③ Revisión (`/lote/:id/revision`)
| # | Hallazgo | Evidencia | Grav. |
|---|---|---|---|
| R1 | **Abrir la pantalla dispara un proceso de escritura.** `useEffect` llama a `prepararRevision` si no hay tarea previa. En esta inspección se lanzó la tarea 76 (PREPARACION_REVISION, 18.990 filas), sin que nadie pulsara nada. Fue idempotente (1.516 pendientes antes y después) | `HumanReviewFlowView.jsx:200-211`; `dataops_tarea.id = 76` | 🔴 |
| R2 | El resultado de esa tarea dice «**48.566** casos derivados a Revisión Humana», pero la bandeja tiene **376** | `dataops_tarea.resultado` (id 76); `consolidacion.py:575-680` incrementa `sent_hitl` por sub-ítem expandido antes de deduplicar en `StagingEntidadNoResuelta` | 🔴 |
| R3 | **Un solo CRUD para todo:** cada caso ofrece solo «Programar aprobación» y «Descartar caso», tenga el motivo que tenga | `p3_caso_abierto.png`; `HumanReviewFlowView.jsx:160-162` | 🔴 |
| R4 | El formulario no trae precargado lo que el sistema ya detectó: la fuente muestra «Programa: POS-5310 \| Módulo: 1», pero Programa, Módulo y Docente aparecen vacíos | `p3_caso_abierto.png` | 🔴 |
| R5 | Motivo contradictorio: «Índice BETO **(0,00)** en [0,60; 0,85)». Un 0 no está en esa banda: es una fila **sin lectura**, no una lectura de baja confianza | `p3_caso_abierto.png`; `revision_formularios.py:355-358` | 🔴 |
| R6 | Un caso de encuesta aparece con el área «Académica» | `p3_caso_abierto.png` | 🟠 |
| R7 | Los **candidatos** (similitud y probabilidad de BETO) se muestran en una tabla, pero **no se pueden elegir**: hay que escribir el nombre a mano | `HumanReviewFlowView.jsx:150-154` | 🔴 |
| R8 | Grupos sin valor: 350 grupos para 376 casos (casi todos de 1). Hay dos grupos con la misma etiqueta «Lectura con baja confianza» (24 y 4) | `p3_revision_b.png` | 🟠 |
| R9 | **52 avisos PENDIENTES de `log_inconsistencias`** que la web no muestra: RESPUESTA_EN_COLUMNA_EQUIVOCADA 32, VALOR_FUERA_DE_CATALOGO 13, PUNTUACION_FUERA_DE_ESCALA 5, LINEA_SIN_IDENTIDAD 2 | `SELECT` sobre `log_inconsistencias`; ningún endpoint de `revision.py` los lee | 🔴 |
| R10 | Motivos nuevos de FU (NOTA_FUERA_DE_RANGO, VALOR_FUERA_DE_CATALOGO…) **no están** en `MATRIZ_FORMULARIOS` y caen al formulario genérico de «académico / baja confianza» | `revision_formularios.py:235-243` | 🔴 |
| R11 | Los casos resueltos no se pueden reabrir ni corregir; un error del revisor no tiene vuelta atrás antes de consolidar | `HumanReviewFlowView.jsx:155` (`readOnly` en RESUELTOS) | 🟠 |
| R12 | `resolve_review_item` mide **~400 líneas** (`revision.py:276-684`), con validación, reglas por categoría y escritura mezcladas | `revision.py` | 🟠 (código) |

### Bandeja viva (todos los lotes)
CI_NOMBRE_DISCORDANTE 747 · HOMONIMIA 363 · BAJA_CONFIANZA_IA 323 · BAJA_CONFIANZA 74 · CI_DUDOSA 8 · FILA_SIN_IDENTIDAD 1 = **1.516**, más los **52** avisos de `log_inconsistencias` que hoy no se ven.

---

## PARTE 2 — Revisión con acciones según el contexto

**Patrón:** el back devuelve por caso un descriptor `acciones[]` (en lugar de un único formulario). Cada acción declara `{codigo, etiqueta, widget, campos, precarga, efecto, confirmacion}`. El front tiene **un renderizador genérico** con widgets reutilizables y no hardcodea nada por motivo. Así, agregar un motivo nuevo es configuración en el back, no código en el front.

| Motivo (N hoy) | Qué ve el revisor | Acciones (CRUD según el caso) | Widget |
|---|---|---|---|
| **CI_NOMBRE_DISCORDANTE** (747) | Nombre de la fuente frente al nombre del padrón para la misma CI, enmascarados, con revelación auditada y similitud | **Misma persona: registrar variante** (no cambia el padrón) · **Misma persona: actualizar el nombre del padrón** · **Otra persona: corregir la CI** · Descartar la fila con motivo | `IdentityCompare` |
| **HOMONIMIA** (363) | Candidatos con similitud, probabilidad de BETO, programa y CI enmascarada | **Vincular al candidato seleccionado** (clic, sin escribir) · **Es otra persona: crear perfil en estado C** (acción humana; BETO nunca crea) · Descartar | `CandidateSelector` |
| **BAJA_CONFIANZA_IA** (323) | Texto con las entidades BETO resaltadas (IOB2) y su confianza | **Confirmar las entidades** · **Corregir una entidad** (tipo y tramo) · Descartar | `EntityTagEditor` |
| **SIN_LECTURA** (hoy BAJA_CONFIANZA con 0; 74) | «La fila no tiene datos legibles» y su texto | **Completar los datos faltantes** (campos precargados) · **Descartar por vacía** (si el payload está vacío, el sistema la descarta solo) | `ValueCorrector` |
| **CI_DUDOSA** (8) | CI original, número y complemento separados | **Corregir la CI** (valida formato) · **Sin CI: perfil TEMP (estado B)** · Descartar | `CiEditor` |
| **FILA / LINEA_SIN_IDENTIDAD** (3) | Fila de origen | **Vincular a una persona** (buscador en el padrón) · Descartar | `PersonSearch` |
| **VALOR_FUERA_DE_CATALOGO** (13) | Valor recibido y valores canónicos del catálogo | **Asignar un valor canónico** + ☐ **«Recordar como sinónimo»** (escribe en el catálogo `cat_*` o `cat_mapeo_columna`: el sistema aprende sin código) · Marcar sin dato | `CatalogPicker` |
| **RESPUESTA_EN_COLUMNA_EQUIVOCADA** (32) | Pregunta de la columna, etiqueta recibida y escala | **Mover a la pregunta correcta** · **Marcar sin respuesta** · Aplicar a todo el grupo | `ColumnReassign` |
| **PUNTUACION_FUERA_DE_ESCALA / NOTA_FUERA_DE_RANGO** (5 + n) | Valor, escala y fila | **Corregir el valor** · **Anular** (NULL) · **Es inasistencia** (solo notas) | `ValueCorrector` |
| **POS_NO_EN_DIM_MODULO** | Código POS y programa leído | **Vincular a un módulo existente** (buscador) · **Crear módulo** (decisión DD2) · Descartar | `ModuleSearch` |
| **CONFLICTO_FUENTES** (10, resueltos por regla) | Las dos fuentes, el valor elegido y la diferencia | Solo lectura · **Cambiar la fuente prioritaria** (ADMIN; modifica la regla, no el dato) | `SourceConflict` |

**Comunes a todos los casos:**
- **Leer:** qué falla, en qué hoja, fila y columna, y qué corregir.
- **Actualizar:** reabrir un caso resuelto mientras el lote no esté consolidado.
- **Borrar:** descartar con motivo (lista de motivos frecuentes y texto libre).
- **Auditoría:** cada acción guarda usuario, fecha, valor anterior y nuevo.
- **En bloque:** las acciones de grupo usan el mismo descriptor (por ejemplo «Registrar variante» para 120 casos con el mismo patrón).

---

## PARTE 3 — Lo que el sistema hace en cada paso, a la vista sin nombrar las tareas

En cada paso, una franja «**Qué hizo el sistema en este paso**» con tarjetas de capacidad (icono, cifra, frase corta y enlace a la evidencia). **No** muestra números de tarea ni la palabra «tarea». La relación tarea ↔ tarjeta queda solo en un documento interno, `docs/fuentes/MAPA_CAPACIDADES_DATAOPS.md`, para la defensa.

| Paso | Tarjeta (lo que ve el usuario) | Tarea del cronograma (solo en el documento interno) | Dónde va |
|---|---|---|---|
| ① | **Archivos leídos y limpiados** (hojas usadas / ignoradas y por qué, cabeceras normalizadas) | 7 | Vista previa por archivo, antes de «Procesar» |
| ① | **Formularios en línea (CSV)** y **Exportes de aula virtual** reconocidos | 8, 9 | Insignia por archivo en la cola |
| ① | **Tipo de fuente detectado** (tipo, señales y confianza; se puede corregir) | 10 | Fila del archivo en la cola e historial |
| ① | **Bitácora del procesamiento** (etapas, tiempos, huella SHA-256) | 13 | Botón «Bitácora», ahora con línea de tiempo |
| ① | **Procesar ahora** (disparo bajo demanda con progreso) | 23 | Botón principal, con estado |
| ② | **Texto preparado** (registro → texto plano bajo un contrato único) | 11 | Pestaña «Texto preparado» con un ejemplo antes/después |
| ② | **Entidades reconocidas** (personas, docentes, módulos resaltados en el texto) | 15 | Nueva vista de texto con resaltado IOB2 |
| ② | **Certeza por registro** (distribución de confianza y bandas) | 18 | Histograma de confianza sobre la tabla |
| ② | **Calidad del modelo** (matriz de confusión y F1) | 22 | Tarjeta que abre `BetoMetricasModal` |
| ② | **Datos personales protegidos** (cédulas y nombres enmascarados; revelación auditada) | 28 | Insignia fija y contador de revelaciones |
| ③ | **Variaciones de escritura resueltas** (similitud) | 16 | Columna de similitud en candidatos |
| ③ | **Coincidencias entre registros sin identificador común** | 17 | `CandidateSelector` con score combinado |
| ③ | **Marcados para revisión** (por qué y bandas) | 19 | Encabezado de la bandeja |
| ③ | **Inconsistencias registradas** (los 52 avisos de hoy y su estado) | 20 | Nueva pestaña «Avisos» en la bandeja |
| ③ | **Guardado en el almacén de datos** (hechos académicos y financieros cargados) | 21 | Resultado de «Consolidar», con cifras |
| ③ | **Claves validadas por similitud** (POS y módulos vinculados) | 27 | Casos POS_NO_EN_DIM_MODULO con `ModuleSearch` |

> *Alcance del cronograma:* `MAPA_CAPACIDADES_DATAOPS.md` incluye también la **Tarea 33** (calidad del pipeline en DataOps). Las **Tareas 6** (indicador `GET /api/v1/health` en `AuditoriaSistema.jsx`) y **37** (pestaña Pretest–Postest en `CuadroMandoIntegral.jsx`) pertenecen a módulos fuera del flujo DataOps y quedan registradas en **DD7** para confirmar si se incorporan o quedan fuera de este plan.

---

## PARTE 3-bis — Trazabilidad con los planes previos (ADW: DW y web · FU: archivos fuente)

Este plan **no rehace** lo que ADW y FU ya corrigieron y cerraron (mora, inscritos ×2, encuestas con 0, hojas ocultas, deserción, metas, motor único de KPI, error 500 de CLIENTES). Toma **lo que esos cierres dejaron abierto**, más lo encontrado en el navegador (Parte 1).

| Pendiente de origen | Dónde lo cubre este plan |
|---|---|
| HALLAZGOS §4: `fk_resolver.py` con ruta fija y cabeceras CI literales (`fk_resolver.py:31, 56-57`) | DF-L7 (a, h) |
| HALLAZGOS §4: Egresos frente a Rentabilidad | DF-L7 (b) |
| HALLAZGOS §4: dimensiones con profesiones o números sueltos | DF-L7 (c), ampliado con los módulos `MOD-GEN*` |
| HALLAZGOS §4: cascada con 1.516 casos (747 + 363) | DF-L2, DF-L3 y DD4 |
| HALLAZGOS §4: lote 1.387 con hoja oculta | DF-L10 (DD6) |
| HALLAZGOS §4: pruebas BETO sin `torch`, `transformers`, `seqeval` y `statsmodels` (`requirements-dev.txt` inexistente) | DF-L7 (f) |
| HALLAZGOS §4: listas fijas de cabeceras «migradas al catálogo» (`extraccion.py:878, 947` y `fk_resolver.py:56-57`) | **DF-L7 (h)** — nuevo |
| HALLAZGOS §5.1: analizar cualquier texto heterogéneo, incluido texto libre | **DF-L11** — nuevo |
| HALLAZGOS §5.2: por entidad, qué etapa la resolvió y lo que BETO etiquetó frente a lo aceptado (sin crear 52.ª tabla en `giragroup_db`) | DF-L4 (b, c), DF-L11 (c) y **DD7** |
| HALLAZGOS §5.3: revisión con contexto y avisos FU en la web | DF-L2 (Parte 2) y R9 |
| HALLAZGOS §5.3 / ADW-L8: la aprobación en bloque no cuenta como corrección | **DF-L2 (g)** — nuevo |
| CIERRE_ADW p.1: etiquetas de Auditoría comprobadas en pantalla | **DF-L9 (f)** — nuevo |
| CIERRE_ADW p.2: nombres en Cartera y Alertas | DF-L7 (g) (DD3) |
| CIERRE_ADW p.3: 74 BAJA_CONFIANZA | DF-L7 (d) |
| CIERRE_ADW p.4: N de la serie predictiva (33 / 43 / 40) | **DF-L7 (i)** — nuevo |
| CIERRE_ADW p.5: 162 hechos sin `id_tiempo` | DF-L7 (e) |
| CIERRE_ADW p.6: premisas falsas en la auditoría (B5, C1, «reservas lleno») | **Hecho ahora en `PLAN_AUDITORIA_DW.md`** (marcadas como retiradas) |
| CIERRE_ADW p.7: 6 fallos de pytest del entorno | DF-L7 (f) |
| CIERRE_ADW p.8 (`KPI-22 2023`): discrepancia DW viva (sin valor) vs `adw_l9_remedicion_final.csv` (`93`) | **DF-L7 (j)** — nuevo |
| CIERRE_ADW p.9: capturas «después» a 1440 px de CMI, Académico, Financiero y Reportes | **DF-L9 (c)** o traspaso explícito a Chat 4 (**DD7**) |
| CIERRE_FU p.1: árbol Git con rutas modificadas/untracked ajenas al plan | Regla obligatoria de `git add` selectivo por loop (nunca `git add -A`) |
| CIERRE_FU p.2: 2 errores de consola en Alertas Tempranas (*«An unknown error occurred when fetching the script»*) | **DF-L7 (g)** y **DF-L9 (b)** |
| HALLAZGOS §5.4: KPI-16 2024 y mes parcial | DD4 y DD5 |

## PARTE 4 — Loops

| Loop | Sección | Capa | Agente (modelo) | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|---|
| DF-L0 | Línea base + mapa interno de capacidades | doc + e2e | `dev-baja` (haiku) | — | — | (a) capturas de los 3 pasos a 1440, 768 y 375 px, claro y oscuro, con un lote de encuestas y uno financiero; (b) `MAPA_CAPACIDADES_DATAOPS.md` con las 17 tareas de DataOps + Tarea 33 → componente y endpoint; (c) vitest y pytest anotados | `df_l0_capturas/`, `df_l0_pruebas.txt` |
| DF-L1 | Back: **ver no escribe** + cifras coherentes | back + front mínimo | `dev-media` (sonnet) | L0 (DD1 resuelta) | L4 | (a) abrir ①, ② o ③ no crea filas en `dataops_tarea` (test); (b) `consolidacion.py:654, 678-680` reporta el conteo real deduplicado del lote en `StagingEntidadNoResuelta` (376) y no `sent_hitl` por sub-ítem (48.566); (c) desactivar `triggerOnView`/count-up de `AnimatedNumberV2` en celdas de tabla y `<details>` (`BatchHistory.jsx:151, 228`) + verificar `n_filas` en BD: historial = 13 cerrado y Registros = filas reales; (d) desactivar count-up en `BatchFlowHeader.jsx:47`: «Programas activos» idéntico en los 3 pasos; (e) período autodetectado acotado a las fechas con evidencia («2020–2029» → rango real o «sin fechas») | `df_l1_coherencia.csv` |
| DF-L2 | Back: **acciones según el contexto** | back | `dev-media` (sonnet) | L1 (DD2 resuelta) | — | (a) `acciones[]` por motivo (Parte 2) con precarga desde el payload; (b) SIN_LECTURA separado de BAJA_CONFIANZA_IA (0 ≠ banda); (c) los 52 avisos expuestos en `/review-tray/avisos` y accionables; (d) `reabrir` y auditoría (valor anterior y nuevo); (e) «Recordar como sinónimo» escribe en el catálogo y una segunda carga lo resuelve sola (test con fixture sintética); (f) invariantes: BETO no crea perfiles ni sobrescribe A/B (test); (g) la aprobación en bloque queda como `APROBACION_BLOQUE` y no como `correccion_humana`, también con las acciones nuevas de grupo (test); (h) `CandidateSelector` (`HOMONIMIA`) poblado con candidatos vía RapidFuzz on-demand en `revision_consulta.py` (`probabilidad_beto = null`) cuando `BETO_SUGERENCIA_HITL=False` | `df_l2_matriz_acciones.md`, `df_l2_pruebas.txt` |
| DF-L3 | Front: **bandeja de revisión** | front | `dev-media` (sonnet) + `/frontend-design` | L2 | L5 | (a) maestro–detalle (lista a la izquierda, caso a la derecha) en lugar de `<details>`; (b) renderizador genérico de `acciones[]` con los widgets de la Parte 2 (ninguno conoce el motivo); (c) candidatos elegibles con clic; (d) grupos por patrón real (sin dos grupos con la misma etiqueta; la homonimia agrupa por par); (e) atajos A/D/↑/↓; (f) 20 casos por página o lista virtual; (g) área correcta por categoría | `df_l3_capturas/` |
| DF-L4 | ② BETO **que se entienda** | back + front | `dev-media` (sonnet) + `/frontend-design` | L0 (DD7 resuelta) | L1 | (a) escala y área según el tipo de fuente (encuesta → Likert 1–5 / 1–10, área «Evaluación docente»); (b) contrato en `evaluacion.py`/`lectura.py` que persiste y conserva `beto_ents` en el `payload_json` de `staging_registro_crudo` separado de `ents_pub` (sin crear `cache_beto_entidades` ni tabla #52 en `giragroup_db`), elimina hex fijos de `evaluacion.py:431-435`, corrige el texto obsoleto de `lectura.py:128` (paso ②) y renderiza texto con resaltado IOB2 y confianza; (c) embudo de la cascada que separa «leído por BETO» de «aceptado por BETO» (aclarando cuándo `CI_EXACTA = 0` es esperable, p. ej. encuestas sin CI), con la frase de por qué BETO va al final; (d) «En revisión» con la misma cifra en ② y ③, o con dos etiquetas distintas («banda 60–85 % de lectura» frente a «casos de revisión»); (e) 20 filas por página y skeleton | `df_l4_capturas/` |
| DF-L5 | ① Carga **que muestre la detección** | back + front | `dev-media` (sonnet) | L1 | L3 | (a) por archivo: tipo detectado, 3 señales principales, confianza y opción de corregir antes de procesar; (b) vista previa de hojas (usada / ignorada / oculta y motivo) visible en la cola; (c) bitácora como línea de tiempo con SHA-256; (d) nombre visible del lote = tipo + período, no «libro_4» | `df_l5_capturas/` |
| DF-L6 | **Capacidades visibles** en los 3 pasos | front | `dev-media` (sonnet) + `/design:design-system` | L3, L4, L5 | — | (a) franja «Qué hizo el sistema» con las 17 tarjetas de la Parte 3 en su sitio, sin números de tarea (un test busca `/tarea\s*\d/i` en el DOM → 0); (b) solo tokens existentes, animaciones de 200–900 ms con `prefers-reduced-motion`; (c) contraste AA en claro y oscuro; (d) responsivo a 375 px | `df_l6_capturas/`, `df_l6_a11y.txt` |
| DF-L7 | Pendientes de los hallazgos | back | `dev-media` (sonnet) | L1 | L3–L6 | (a) `fk_resolver.py` sin ruta fija (`:31`) ni lista literal de cabeceras CI (`:56-57`) (padrón y cabeceras por catálogo/config); (b) detección Egresos frente a Rentabilidad con fixture sintética; (c) dimensiones sin profesiones ni números sueltos como programa o módulo (regla + limpieza en tmpfs); (d) origen de los 74 BAJA_CONFIANZA explicado; (e) 162 hechos sin `id_tiempo` explicados o corregidos; (f) crear/definir `requirements-dev.txt` con `torch`, `transformers`, `seqeval` y `statsmodels` (o ejecución equivalente en contenedor) → las 6 pruebas de entorno pasan; (g) DD3: nombres enmascarados en Cartera, Alertas y ficha, con revelación auditada (0 nombres en claro en las respuestas) + corregir los 2 errores de consola en `/academico/rendimiento`; (h) verificar que no quedan listas fijas de cabeceras en `extraccion_por_encabezado.py`, `routers/pipeline.py`, `routers/dataops/extraccion.py` (`:878, 947`) ni `fk_resolver.py` (`:56-57`) (test que falla si una lista literal de sinónimos vive en el código y no en el catálogo); (i) N de la serie predictiva: explicar 33 / 43 / 40 y dejar una sola definición, con la cifra en `docs/mediciones/` (si cambia el invariante N = 40 → detenerse y preguntar a Lean); (j) verificar y documentar la discrepancia de `KPI-22 2023` (DW viva sin valor frente a `93` en `adw_l9_remedicion_final.csv`) | `df_l7_*.csv` |
| DF-L8 | Código limpio del flujo | back + front | `dev-media` (sonnet) + `/clean-scalable-code` | L2, L3 | — | (a) `resolve_review_item` partido en servicio por acción (router < 60 líneas por endpoint); (b) ningún componente de `modules/dataops` pasa de 300 líneas (`IngestView.jsx` 1.038, `BetoMetricasModal.jsx` 467 y `BetoReadingFlowView.jsx` 340); (c) `FIELD_LIMITS` e `initialFieldValue` del front se eliminan (llegan en el descriptor); (d) 0 imports sin uso | `df_l8_lineas.txt` |
| DF-L9 | Verificación E2E + cierre | e2e | `dev-baja` (haiku) | L1–L8 | — | (a) script Playwright en `e2e/` que recorre ① → ② → ③ con un lote sintético y resuelve un caso de cada motivo con su acción propia; (b) 0 errores de consola en DataOps ①②③ y en `/academico/rendimiento`; (c) capturas «después» a 1440, 768 y 375 px, claro y oscuro de DataOps ①②③ y Auditoría (las de CMI/Académico/Financiero/Reportes a 1440 px se derivan a Chat 4 `/gira-figuras` tras el rebuild); (d) rebuild de `web` y `api`; (e) `CIERRE_DF.md`; (f) en `/v2/admin/auditoria` se ven las etiquetas «Aprobación en bloque» y «Revelación autorizada» de eventos reales (filtro por tipo de evento si la ventana de 200 no los alcanza) + indicador de salud `GET /api/v1/health` (Tarea 6) | `df_l9_e2e.txt`, `df_l9_capturas/` |

| DF-L10 | Lote congelado v2 sin hoja oculta (DD6) | scripts + mediciones | `dev-alta` (rol) con `model: "sonnet"` | L7 | L3–L6 | (a) `df_lote_1387_v2.json`: 1.387 registros, mismas cuotas, 0 filas de hojas ocultas, sin nombres de archivo u hoja en el script (test con grep); (b) 2 corridas con diferencia 0; (c) antes/después de A-01 a A-13, F1 y matriz; (d) F1 ≥ 0,85 o se detiene; (e) SFV recongelada y avisos a los chats 3 y 4 | `df_lote_1387_v2*.json`, `df_l10_antes_despues.csv` |

| DF-L11 | **PLN sobre cualquier texto heterogéneo** (HALLAZGOS §5.1) | pipeline + front | `dev-alta` (rol) con `model: "sonnet"` | L1, L4 | L3, L5, L7 | (a) definir por escrito qué es «texto heterogéneo admitido» (`.xlsx`, `.xls`, `.csv` y hojas que no son tabla: celdas de texto narrativo, comentarios, bloques sin cabecera) en `docs/fuentes/CONTRATO_FUENTES.md`; (b) fixtures sintéticas nuevas en `tests/fixtures/fuentes_sinteticas/`: texto libre largo, hoja sin cabecera, comentarios mezclados con datos, columnas en otro orden; (c) para esas hojas, el sistema muestra en ② qué reconoció el PLN (normalización), qué extrajo el NER y qué quedó para BETO, sin cargar como hecho lo que no tiene estructura (va a revisión con su motivo); (d) la cascada y los umbrales no cambian (invariante); (e) test: una fixture nunca vista produce la vista de ② sin errores y 0 hechos inventados | `df_l11_texto_heterogeneo.md`, `df_l11_capturas/` |

Orden: **L0 → (L1 ‖ L4) → L2 → (L3 ‖ L5 ‖ L7 ‖ L11) → (L6 ‖ L10) → L8 → L9.**

## Comandos
```powershell
cd frontend; npx vitest run; npm run build
```
```powershell
.venv\Scripts\python -m pytest tests -q --cov=backend --cov-report=term
```
```powershell
docker compose up -d --build --no-deps web api
```
```powershell
node e2e/dataops_flujo.mjs
```

## Riesgos y control
- **Escrituras desde la vista:** DF-L1 va primero porque una simple visita lanza procesos. Hasta corregirlo, las verificaciones en el navegador se hacen sobre lotes de prueba.
- **Cifras congeladas:** DF-L2 y DF-L7 pueden mover KPI-16 (si se resuelven los 747 CI_NOMBRE_DISCORDANTE) y KPI-18. Cualquier cambio de cifra pasa por la DW tmpfs y se recongela con aviso al chat 3.
- **Invariantes:** «Crear perfil» es solo una acción humana (estado C o TEMP B), nunca de BETO. La cascada y los umbrales no cambian.
- **Privacidad:** los widgets muestran datos enmascarados; la revelación queda auditada; los ejemplos de los informes van sin PII.

## DECISIONES PENDIENTES PARA LEAN
- **DD1 — RESUELTA (Lean, 2026-11-22): la preparación se encadena al terminar la lectura BETO.**
  - Cuando `LECTURA_BETO` termina en COMPLETADA, el back crea en el mismo flujo la tarea `PREPARACION_REVISION` del lote, que es idempotente (`already_prepared` no rehace nada).
  - Se **elimina** el `useEffect` de `HumanReviewFlowView.jsx:200-211`: ③ solo lee y muestra el progreso si la preparación sigue en curso («Preparando casos… se habilita al terminar»).
  - Si la preparación falla, ③ muestra el error y un botón «Reintentar preparación» (la única escritura que se dispara desde la vista, y solo con un clic).
  - Los lotes antiguos que nunca se prepararon se preparan con el mismo botón; no se lanza nada solo al abrir la pantalla.
  - **Criterios DF-L1:**
    - test: GET de ①, ② y ③ → 0 filas nuevas en `dataops_tarea`;
    - test: al completar `LECTURA_BETO` existe exactamente 1 `PREPARACION_REVISION` para el lote;
    - una segunda lectura no duplica casos (los pendientes quedan iguales).
- **DD2 — RESUELTA (Lean, 2026-11-22): ADMIN y AUDITOR_CALIDAD** pueden usar «Crear perfil (estado C)», «Crear módulo» y «Recordar como sinónimo».
  - Es el mismo `require_roles(["ADMIN", "AUDITOR_CALIDAD"])` que ya usa la bandeja. Ningún otro rol ve esas acciones: el descriptor `acciones[]` se filtra por rol en el back, no solo en el front.
  - Cada creación queda en la auditoría (usuario, fecha, origen = caso N) y se puede **deshacer** mientras el lote no esté consolidado: el perfil o módulo creado se elimina si nada más lo referencia, y el sinónimo se retira del catálogo.
  - «Cambiar la fuente prioritaria» (CONFLICTO_FUENTES) sigue siendo **solo ADMIN**, porque cambia una regla global.
  - **Tests de DF-L2:**
    - el auditor crea un perfil C y un sinónimo → 200;
    - DIRECTOR_ACADEMICO → 403;
    - al deshacer, no queda la fila;
    - una segunda carga con el sinónimo lo resuelve sola.
- **DD3 — RESUELTA (Lean, 2026-11-22): enmascarar también el nombre en Cartera y Alertas, con revelación auditada.**
  - **Back:**
    - `risk_service.py`, `routers/riesgos.py` (alertas tempranas, cruzado y ficha) y el servicio de cartera devuelven `nombre_enmascarado` (por ejemplo «J•••• P••••») y `id_estudiante`, **nunca** el nombre en claro, para todos los roles;
    - endpoint nuevo `GET /api/v1/riesgos/estudiante/{id}/revelar?campo=nombre|ci` que deja registro en la auditoría (usuario, rol, motivo, fecha) igual que `revelar-ci` de DataOps;
    - roles permitidos: ADMIN, ANALISTA_FINANCIERO (Cartera) y DIRECTOR_ACADEMICO (Alertas académicas).
  - **Front:** `CarteraMora.jsx`, `RendimientoAlertas.jsx` y la ficha del estudiante usan el mismo componente de revelación que DataOps (`useRevealCampo`), con «Revelar» y «Ocultar»; la revelación caduca al salir de la pantalla.
  - **Exportes:** CSV y PDF de Cartera y Alertas exportan el nombre enmascarado, salvo exportación explícita «con datos personales» (solo ADMIN, auditada).
  - **Búsqueda:** buscar por nombre sigue funcionando en el back (compara en claro y devuelve enmascarado).
  - **Tests:**
    - ninguna respuesta de `/riesgos/*` ni de cartera contiene el nombre en claro (test que compara con `dim_estudiante`);
    - revelar sin rol → 403;
    - revelar con rol → 200 y una fila nueva en la auditoría.
  - **Dónde:** se agrega como **DF-L7 (g)**. Toca módulos fuera de DataOps, pero es la misma regla de privacidad.
- **DD4 — RESUELTA (Lean, 2026-11-22): se acepta el KPI-16 2024 que resulte después de resolver los casos de identidad con las acciones nuevas.**
  - No hay depuración previa ni ajuste manual de la cifra: el valor sale solo de la DW después de la revisión humana.
  - **En DF-L9:**
    - medir KPI-16 2024 antes y después de resolver la bandeja (`df_l9_kpi16.csv`), con cuántos CI_NOMBRE_DISCORDANTE y HOMONIMIA se resolvieron, con qué acción, y cuántas filas de actas se desbloquearon (25.208 → n, frente a 27.731 de la copia limpia);
    - informar la brecha restante frente al 10,17 % de la fuente y su causa (casos aún pendientes o descartados).
  - Si la cifra cambia, se recongela en `fuente_verdad_tesis.md` con aviso al chat 3.
  - La resolución de los 747 + 363 casos es **trabajo humano** (Lean o el auditor) con las acciones de DF-L3. No la hace un agente, aunque las acciones de grupo («Registrar variante» para un patrón) la aceleran.
- **DD5 — RESUELTA (Lean, 2026-11-22): se mantiene la exclusión del mes parcial en KPI-03 y KPI-12.**
  - Queda aprobada como regla: KPI-02, KPI-03 y KPI-12 usan hasta el último mes **cerrado** de la fuente (hoy abril de 2026, porque mayo llega a medias).
  - No hay cambio de código.
  - **Solo transparencia en la web:** el drill-down de los tres KPI muestra «Calculado hasta <mes> (último mes cerrado de la fuente)». Se agrega a DF-L6 junto con las tarjetas de capacidad, porque usa los mismos tokens y componentes.
  - La memoria del proyecto deja de listarla como decisión abierta.
- **DD6 — RESUELTA (Lean, 2026-11-22): regenerar el lote congelado sin la hoja oculta.** Se hace en el loop nuevo **DF-L10**:
  - **Mismo tamaño y estratos:** se conservan **1.387 registros** y las mismas cuotas por categoría (450 académico, 350 + 53 + 24 financiero, 250 inscritos, 260 evaluación docente). Las 110 filas de evaluación se toman de las hojas **visibles** de encuestas que el sistema sí usa, con semilla fija y orden determinista.
  - **Sin nombres de archivo ni de hoja** ([[fuentes-agnosticas]]): `scripts/reejecutar_lote_1387_uploads_data.py` deja de tener la lista `MUESTRAS` atada a archivos y hojas. Elige las hojas con la **misma clasificación del sistema** (`preview-workbook` / `HOJA_IGNORADA`): tipo de fuente, hoja usada y no oculta salvo la regla de rescate. Así el lote nunca vuelve a divergir de lo que carga el sistema.
  - **Versionado:** el lote actual queda como histórico (`f5c_lote_1387_r1.json` sin tocar) y el nuevo es `df_lote_1387_v2.json` + `.huella.json` (sha256 de los textos y lista de filas de origen). Sigue habiendo **un único lote congelado** vigente (invariante).
  - **Remedición:** 2 corridas idénticas con el BETO vigente (`df_lote_1387_v2_r1.json` y `_r2.json`, con diferencia 0) y la tabla antes/después de A-01 a A-13 y de las cifras derivadas: distribución por bandas, personas A/B/C, cascada por etapa, F1 y matriz de confusión (RNF-04 ≥ 0,85).
  - **Recongelado y avisos:** `fuente_verdad_tesis.md` (Tabla A.1 y las que citen `f5c_lote_1387_r1.json`) como **CONGELADO**, con aviso al chat 3 (texto del documento) y al chat 4 (Gráficos 3.2 y 4.2 y los que usen el lote).
  - **Si F1 queda por debajo de 0,85** (RNF-04) **o** una cifra cambia más de 5 puntos porcentuales: se detiene **antes** de recongelar y vuelve a Lean.
- **DD7 — RESUELTA (Lean, 2026-11-22): spans BETO en `payload_json` (51 tablas intactas) y alcance acotado.**
  1. **Spans IOB2 de BETO sin romper el invariante de 51 tablas DW:** Se adopta la **opción (a)**: `evaluacion.py`/`lectura.py` persisten `beto_ents` dentro del `payload_json` existente de `staging_registro_crudo` (separado de `ents_pub`) y desactivan la creación de `public.cache_beto_entidades` en `giragroup_db` (usando caché en memoria/disco del servicio `pipeline` si hace falta), manteniendo exactamente **51 tablas**, la cascada en residuales y `RNF-03 < 15 min`. `CandidateSelector` (`HOMONIMIA`) usa RapidFuzz on-demand (`DF-L2 h`) cuando `BETO_SUGERENCIA_HITL=False`.
  2. **Alcance fuera de DataOps:**
     - **Tarea 6** (`GET /api/v1/health` en `AuditoriaSistema.jsx`): **incluida** en `DF-L9 (f)`.
     - **Tarea 37** (pestaña Pretest–Postest en `CuadroMandoIntegral.jsx`): **fuera de este plan** (pertenece al CMI).
     - **Capturas «después» a 1440 px** de CMI, Académico, Financiero y Reportes (`CIERRE_ADW.md:34, 37`): **derivadas explícitamente al Chat 4 (`/gira-figuras`)** tras el rebuild de `DF-L9`.

Al cerrar cada loop: vitest + pytest con cobertura · rebuild de lo tocado · commit `df(L<n>): …` · `CIERRE_DF_L<n>.md`.

## PROMPT PARA CHAT 2 (uno por loop)
```
/gira-desarrollar
Ejecuta SOLO el loop DF-L<n> de docs/cierres/PLAN_DATAOPS_FLUJO.md (Parte 4).
- Agentes con model "sonnet" (o "haiku" en tareas rápidas), nunca Opus.
- Si el loop depende de una DECISIÓN (DD*) sin respuesta escrita de Lean, detente.
- Respeta las fuentes agnósticas: nada de nombres de archivo u hoja en el código.
- Respeta el invariante de 51 tablas DW: no crear nuevas tablas en giragroup_db sin decisión escrita.
- Las tarjetas de capacidad no muestran números de tarea.
- Usa git add selectivo por archivo tocado en el loop (nunca git add -A; hay rutas ajenas en el árbol).
- Verifica en el navegador (Playwright) con lotes de prueba; no abras ③ en lotes reales hasta cerrar DF-L1.
- Cierra con docs/cierres/CIERRE_DF_L<n>.md y commit df(L<n>).
```
