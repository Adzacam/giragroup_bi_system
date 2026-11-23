# ACTUALIZACIÓN DEL DOCX TRAS RV2, FU, ADW Y DF — 2026-11-23

- **Documento revisado (solo lectura):** `PROYECTO GRADO DAZA CAMPERO ADRIANO LEANDRO (4).docx` (23-nov). El texto se extrajo a una copia en el scratchpad; el docx no se tocó (`CLAUDE.md`, regla 2).
- **Fuente única de cifras:** `docs/fuente_verdad_tesis.md` (CONGELADO 21-nov, recongelado tras FU-L9 + ADW-L9). Cada cifra nueva sale de ahí.
- **Fuera de alcance, por indicación de Lean:** las cifras de pruebas `pytest` (943 / 924 / 72,69 %) **no se actualizan**.
- **Relación con la guía anterior:** `ACTUALIZACION_DOCX_F5C.md` ya está aplicada en esta versión (97,76 %, 3.382, 943, 1.663, etc.). Esta guía cubre **solo lo posterior**.
- **Dónde está cada cosa:** la columna «Lugar» da el capítulo o la sección y el texto que hay que buscar.

---

## 1. Power BI (retirado en RV2-L1)

El documento casi no depende de Power BI: **los requisitos RF-10, HU-10 y HU-11 ya hablan solo de la aplicación web**. Quedan 5 puntos:

| # | Lugar | Qué dice hoy | Qué hacer |
|---|---|---|---|
| 1.1 | Cap. I · Delimitación temática, párrafo «La explotación de los indicadores…» | «se gestiona a través de **dos canales**: una interfaz web interactiva que centraliza el panel directivo con vistas.» (frase rota: falta el segundo canal) | «La explotación de los indicadores se realiza mediante una interfaz web interactiva que centraliza el panel directivo con vistas por perspectiva.» |
| 1.2 | Cap. I · Alcances, párrafo del CMI | «…permitiendo su consulta **tanto** desde la plataforma web institucional.» | Quitar «tanto»: «…permitiendo su consulta desde la plataforma web institucional.» |
| 1.3 | Cap. I · Límites, párrafo «El sistema no contará con aplicaciones móviles…» | «ni publicará reportes en el servicio en la nube de Power BI Service (evitando costos de licenciamiento Pro)» | Sigue siendo cierto. Opcional, más completo: «ni integrará herramientas externas de inteligencia de negocios (Power BI u otras) ni publicará reportes en servicios en la nube; la consulta se realiza en la plataforma web (Chart.js)». |
| 1.4 | Cap. III · Sprint 5 · Tabla 3.25, fila **GCB-38**, columna «Entregable verificable» | `powerbi/dashboards` (carpeta que ya no existe) | `frontend/src/modules/admin/cmi/` (`CmiPage.jsx`, `scorecard/`, `prediccion/`, `config/`) |
| 1.5 | Cap. IV · Tabla de trazabilidad HU → módulo, fila **HU-11** | `backend/routers/powerbi.py` (borrado) | `backend/routers/cmi.py` (el servicio de KPI sigue en `kpi_service.py`) |
| 1.6 | Anexo F · **Tabla F.43** «Diccionario de datos de `powerbi_informe_version`» | Describe un informe `.pbix` y su despliegue | **No borrar la tabla:** `public.powerbi_informe_version` sigue en la DW vacía y sin uso (decisión D1-b, para mantener las 51 tablas). Agregar bajo el título una nota: «Tabla heredada sin uso: el acceso al informe `.pbix` se retiró de la interfaz y de la API; el CMI se consulta solo en la web.» |
| 1.7 | Anexo A · citas de entrevistas («Generación de dashboard en Power BI…», «herramientas como Power BI, Looker Studio o Tableau») | Citas textuales | **No cambiar:** son evidencia histórica de las entrevistas. |

**Verificar a ojo (no pude leer las imágenes del docx):** Figuras 3.2 y 3.3 (arquitectura y despliegue), 3.30 (mockup del CMI), 3.36 y 3.37 (dashboards). Si alguna dibuja Power BI o el informe `.pbix`, hay que regenerarla (chat 4). Los scripts que las generan ya no mencionan Power BI.

---

## 2. Contradicciones con lo corregido (sin pruebas `pytest`)

### 2.1 Tabla 4.6 y texto de resultados del Objetivo 3 — la más importante
La Tabla 4.6 todavía trae los valores **del snapshot del 10-nov**; la SFV recongelada (Tabla F.1, base `giragroup_db` recarga FU-L9) trae los nuevos. Ninguna cifra del recongelado está en el docx.

| KPI | Docx 2025 / 2024 | SFV F.1 2025 / 2024 | Motivo del cambio |
|---|---|---|---|
| KPI-01 Ticket promedio | 3.773,91 / 2.311,15 | **2.571,95 / 2.279,51** | Denominador único: estudiantes pagantes |
| KPI-02 Cumplimiento último mes | 157,48 % / 6,25 % | 157,48 % / **N/D** | 2024 no tiene meta mensual (DA4) |
| KPI-04 Riesgo financiero | 623 / 314 | **808 / 362** | Regla única de mora: ≥ 2 cuotas (DA3) |
| KPI-05 Estudiantes en mora | 18,36 % / 14,08 % | **18,46 % / 10,60 %** | Ídem |
| KPI-06 Conversión de admisiones | N/D / N/D | **3,85 % / N/D** (2026: 2,94 %) | Se calcula con leads de planificación (DA6) |
| KPI-07 Promedio de calificaciones | 79,02 / 78,94 | **81,81 / 82,32** | Excluye inasistencias, eximidos y sin nota (DA-FU2) |
| KPI-08 Tasa de aprobación | 85,61 % / 85,50 % | **85,62 % / 84,98 %** | Las inasistencias cuentan como no aprobadas |
| KPI-09 Riesgo académico | 588 / 674 | **445 / 667** | Idem |
| KPI-15 Cartera vencida | 20,56 % / 43,58 % | **78,06 % / 69,61 %** | Deuda de estudiantes con ≥ 2 cuotas sobre deuda total |
| KPI-16 Tasa de deserción | 0,00 % / 0,00 % | **6,47 % / 5,38 %** | Se calcula desde el estado «Deserción» o «Abandono» (DA2-bis) |
| KPI-17 Prioridad crítica | 124 / 90 | **116 / 66** | Consecuencia de los anteriores |
| KPI-19 Satisfacción docentes | 81,23 % / N/D | **82,00 % / 81,10 %** | Los ceros de «Sin Información» pasan a NULL (DA1) |
| KPI-20 Satisfacción institucional | 84,39 % / N/D | **77,75 % / 79,72 %** | Idem |
| KPI-21 Matrícula efectiva | 3.455 / 3.147 | **3.571 / 3.773** | Recarga |
| KPI-03, 12, 13, 14, 22, 23 | — | Sin cambios | — |

**Ajustes de texto que acompañan a la tabla:**
- Título de la tabla: «…de los **22** indicadores…» → 23 (tiene 23 filas con KPI-23).
- Columna «Base de cálculo» de KPI-02: «(en 2024 solo hay meta de diciembre)» → «N/D: la fuente solo trae meta anual en 2024».
- Texto previo a la tabla: «salvo KPI-06, declarado N/D por ser tautológico» → ya no aplica; «**KPI-16 vale 0,00 %** porque las actas no traen el porcentaje de actividades incumplidas» → ya no aplica.
- **2026:** KPI-07, 08, 09, 10, 11, 16, 17, 21 y 22 quedan N/D (no hay actas 2026); se puede agregar una columna 2026 o una nota.

### 2.2 Párrafos que repiten esas cifras o conclusiones
| Lugar | Qué cambia |
|---|---|
| **Resumen y Abstract** | «De los 23 indicadores, los 19 de negocio tienen valor en 2025… salvo KPI-06 (N/D)» → con la SFV, **los 19 tienen valor en 2025**. |
| **Cap. IV · Resultados Obj. 3** (segundo párrafo) | «588 en riesgo académico, **623** en riesgo financiero y **124** en prioridad crítica» ya no coincide con la Tabla 4.6 nueva (445 / 808 / 116). «La regla de deserción no generó alertas porque…» → ya no es cierto: las alertas de deserción también se disparan por el estado «Deserción» o «Abandono» (commit `3083636`). |
| **Cap. V · Conclusiones**, 1.º y 4.º párrafos | «18 de los 19 de negocio tienen valor… (KPI-06 N/D)» y «KPI-06 se declara N/D por ser **Repetitivo**» (palabra suelta) → «los 19 de negocio tienen valor en 2025». Revisar «588 / 623 / 124». |
| **Cap. IV · Limitaciones metodológicas**, párrafo «Indicadores sin dato fuente» | «KPI-06 se declara N/D porque leads e inscritos coinciden… KPI-16 vale 0,00 %…» → reescribir: KPI-06 solo existe desde que las hojas de planificación traen leads (julio de 2025); KPI-16 se calcula desde el estado académico, sin porcentaje de asistencia. |
| **Cap. III · Sprint 3, Fase 6** y **Sprint 4** | «riesgo de deserción (incumplimiento de actividades > 30 %)» aparece también en el párrafo de `risk_service.py`, en la regla **R-DES** (Tabla de reglas) y en el texto «El fragmento de `risk_service.py` evalúa tres reglas…». Agregar: «o estado académico o de tutoría “Deserción” o “Abandono” en el acta». |
| **Cap. I · Alcances**, párrafo del motor de alertas | «Riesgo de Deserción (incumplimiento de actividades > 30 %)» → misma adición. También en **RF-08** (Requerimientos funcionales) y en **HU-07**. |
| **RNF-02** (Requerimientos no funcionales) | «la cédula se enmascara… su revelación queda restringida a ADMIN y AUDITOR_CALIDAD» → desde DD3 también se **enmascara el nombre** en Cartera, Alertas y ficha del estudiante, y la revelación auditada la pueden pedir ADMIN, ANALISTA_FINANCIERO y DIRECTOR_ACADEMICO (`riesgos.py`). |

### 2.3 Tabla 3.27 (catálogo de KPI): fórmulas y orígenes que cambiaron
| KPI | Docx | Debe decir |
|---|---|---|
| KPI-01 | Recaudación total / **Matrícula efectiva** | Recaudación total / estudiantes pagantes |
| KPI-02 | Monto ejecutado / monto meta del mes | Igual, **solo en gestiones con meta mensual**; usa el último mes cerrado |
| KPI-03, KPI-12 | — | Se calculan hasta el **último mes cerrado** de la fuente (DD5); agregar en la columna de fórmula |
| KPI-04 | ≥ 2 cuotas impagas **o cartera previsionable** | Estudiantes con **≥ 2 cuotas impagas** |
| KPI-05 | Estudiantes en mora **o previsionables** / total cartera activa | Estudiantes con ≥ 2 cuotas impagas / estudiantes con cartera |
| KPI-06 | «(Registrado como N/D*)» | Inscritos / leads de captación (hojas con leads, desde julio de 2025) |
| KPI-07, KPI-08 | Media de notas / notas ≥ 70 sobre total con nota | Excluye inasistencias, eximidos y sin nota del promedio; la aprobación cuenta las inasistencias como no aprobadas |
| KPI-15 | Deuda en mora **o previsionable** / deuda total | Deuda de estudiantes con ≥ 2 cuotas / deuda total |
| KPI-16 | Estudiantes con **incumplimiento o inasistencia > 30 %** / total | Estudiantes con estado académico o de tutoría «Deserción» o «Abandono» / matrícula (N/D si la gestión no trae ese dato) |
| KPI-19, KPI-20 | «Tabla de encuestas (**verificar nombre en el DW**)» (nota que quedó sin resolver) | `fact_evaluacion_docente`; puntuaciones válidas dentro de la escala (los ceros son «sin respuesta») |
| KPI-22 | `fact_marketing` | `fact_techo_convenio` (suma de `n_inscritos`) |

### 2.4 Sprint 5: descripción de la plataforma web
| Lugar | Qué cambia |
|---|---|
| Texto inicial del Sprint 5 | Habla de **tres** pasos (①②③), pero **Tabla 3.26** lista cuatro («② Texto plano», «③ Lectura BETO», «④ Revisión HITL») y **GCB-35** dice «flujo guiado en cuatro pasos». Son tres: ① Carga, ② Lectura de BETO (el texto preparado es una pestaña dentro de ②), ③ Revisión. Quitar `PlainTextTransformationView.jsx` y la ruta `/dataops/lote/:id/texto`; ajustar numeración y rutas (`/v2/dataops/...`, V2 es ahora la vista principal). |
| Tabla 3.26, fila «Cuadro de mando» | `CuadroMandoIntegral.jsx` se partió en `CmiPage.jsx`, `CmiHeader.jsx`, `scorecard/`, `prediccion/` y `config/`; ruta `/v2/dashboard`. |
| Párrafo de la bandeja HITL | «ofrece **tres acciones**: aprobar todos, asignar un estado académico… o asignar mes y gestión» → cada caso ofrece acciones propias de su motivo (vincular a un candidato, corregir cédula, asignar valor del catálogo, anular, etc.), según el rol; se pueden **reabrir** casos resueltos antes de consolidar; la aprobación en bloque queda con su propia etiqueta; una pestaña de **Avisos** muestra las inconsistencias registradas. |
| Sección «Construcción de los Tableros del CMI» | No describe lo que hoy ve el usuario. Agregar un párrafo: mapa estratégico con las cuatro perspectivas en tarjetas horizontales, vista general (matriz de semáforo de los 23 KPI, alertas prioritarias, evolución del índice), desglose por perspectiva con buscador y gráficas, analítica predictiva con sub-pestañas, botón **Actualizar** con aviso de progreso, y **configuración** de metas, umbrales, indicadores y gráficas personalizados (solo ADMIN y los analistas financiero y de marketing, y estos solo en su perspectiva). Los indicadores personalizados viven en el esquema `app` y **no entran en el índice global**. |
| Nombre de la perspectiva «Clientes» | La interfaz la rotula «**Estudiantes y mercado**». Alinear el nombre (o poner el rótulo entre paréntesis la primera vez). |
| Figuras **3.30, 3.36 y 3.37** | Capturas y mockups del CMI anteriores a RV2: regenerar (chat 4). |
| **GCB-35, GCB-36** | Revisar la descripción con lo anterior. |

### 2.5 Contradicciones internas del documento
| # | Lugar | Contradicción |
|---|---|---|
| 2.5.1 | Cap. I · Límites (último párrafo de «no resolverá de manera autónoma…») frente a Cap. IV · Limitaciones («Bitácora de descartes») | Límites: «las entidades descartadas por reglas de calidad (etiquetas Likert, correos y comentarios) **no se registran en bitácora**». Limitaciones y SFV B-10: «**no quedan descartes sin bitácora**» (0 sin explicar). Alinear con la SFV: ahora el sistema también registra las líneas sin entidad, los subtotales y las hojas ignoradas con su motivo en `log_inconsistencias`. **Confirmar con el chat 1 cuáles descartes quedan fuera** y corregir el párrafo de Límites. |
| 2.5.2 | Resultados Obj. 3 y Conclusiones | «(Tabla 4.6) … **22** indicadores» frente a «**23** indicadores» en el resto. |
| 2.5.3 | Cap. IV · Tabla 4.8 y Conclusiones | «**9,2 minutos**» y «Cumple» frente a la SFV: 20,52 min (caché llena + KLM) y 31,75 min (caché vacía + KLM), **RNF-03 no se cumple**. Ya identificado en `ACTUALIZACION_DOCX_F5C.md` §6.A: es la **decisión D-01 de Lean** y sigue sin resolver. |

---

## 3. ¿Cambian los Alcances y los Límites? **Sí.**

### Alcances
| Párrafo | Cambio |
|---|---|
| CMI («El sistema estructurará un Cuadro de Mando Integral…») | Quitar «tanto» (punto 1.2). Agregar una frase: «…con vista general, desglose por perspectiva y configuración de metas, umbrales, indicadores y gráficas personalizados por los roles Administrador, Analista Financiero y Analista de Marketing, estos dos últimos solo en su perspectiva». |
| Motor de alertas | Riesgo de deserción: agregar el estado académico o de tutoría «Deserción» o «Abandono». |
| Módulo DataOps | «una bandeja de revisión humana con registro auditable de correcciones» → agregar «con acciones propias según el tipo de caso, reapertura de casos resueltos, y datos personales enmascarados con revelación auditada». |
| Pipeline ETL | Opcional, pero recomendable por la defensa: «reconoce el tipo de fuente por su contenido, ignora hojas ocultas, copias y borradores dejando el motivo registrado, y mapea las columnas con un catálogo editable, sin depender del nombre del archivo». |

### Límites
| Tema | Cambio |
|---|---|
| Power BI | Opcional: reformular como en 1.3. |
| Descartes sin bitácora | Corregir (2.5.1). |
| **Límites nuevos que hoy son verdad y el documento no declara** | (a) **KPI-16** se calcula solo desde el estado «Deserción» o «Abandono» de las actas; no usa porcentaje de asistencia ni de actividades incumplidas. (b) **KPI-06** solo existe desde julio de 2025 (las hojas con leads); 2023 y 2024 son N/D. (c) **KPI-02** solo se calcula en gestiones con meta mensual; 2024 es N/D y 2023 no tiene meta. (d) **KPI-02, 03 y 12** se calculan hasta el último mes cerrado de la fuente. (e) **No hay actas 2026**: nueve indicadores quedan N/D en 2026. (f) **Mora** se define como 2 o más cuotas impagas; el estado de cartera de la fuente no es consistente con las cuotas y no se usa para el cálculo. (g) **Nueve indicadores no tienen meta ni umbral** y no puntúan en el índice del CMI. (h) Los indicadores y las gráficas **personalizados** no entran en el índice global ni se consideran parte del catálogo de 23. |

---

## 4. Lo que NO hay que actualizar todavía (está planificado, no ejecutado)
- **BETO activo en la cascada final** y el ruteo «**menos de 0,85 va a revisión sin insertarse**» (`PLAN_BETO_ACTIVO.md`). Cuando se ejecute cambia: los flags de la SFV (hoy `False`), A-12 a A-16, la semántica de la banda 0,60–0,85 (Justificación técnica, Sprint 3 Fase 6, GCB-24 y Justificación económica) y los 9,2 min. **Hoy el documento describe el sistema tal como está.**
- **Limpieza del catálogo de módulos e instituciones** (`PLAN_CATALOGO.md`): no cambia ninguna cifra del documento hasta que se ejecute y se recargue.
- **Recarga completa y prueba de aceptación** (`PLAN_ACEPTACION_FLUJO.md`): las cifras de staging («756 de los 1.044 pendientes», «32 pendientes», «5.090 filas de bitácora») y el lote 1.387 (DF-L10) se actualizan cuando se remida.

---

## 5. Inconsistencias dentro de la propia SFV (resolver con el chat 1 antes de pasarlas al documento)
| # | Dónde | Problema |
|---|---|---|
| 5.1 | Cabecera, regla 2 («tres bases») frente a Tabla F.1 | La regla dice que KPI-01 a 09 y 12 a 22 salen del **snapshot 10-nov**; la Tabla F.1 los toma de la **recarga FU-L9**. Y la Tabla F.2 sigue con KPI-10, KPI-11 y KPI-18 de `f3_base`, que F.1 también lista con otros valores (83,92 % / 51,51 % / 948). Hay que fijar una sola base por KPI. |
| 5.2 | Tabla H.2, fila «Lim. KPI-06 tautológico» y fila «Lim. Metas/Des.» | Siguen diciendo que KPI-06 es N/D y que la deserción es 0. Contradicen las notas de recongelado y F.1. |
| 5.3 | Tabla E.2 (E-09) frente a la nota DA8 | E-09 da OLS anual +2.436.141,68 Bs/año y CAGR 26,76 %; la nota de recongelado da +2.360.251,66 y 22,85 %. |
| 5.4 | Tabla F.3 (alertas) | Las 7.094 alertas y las cifras de mora salen del snapshot; no están remedidas con las reglas nuevas de deserción y mora, así que no coinciden con F.1. |
| 5.5 | Tabla C.3 frente al perfil de fuentes | La SFV dice 60 hojas; el perfil de `uploads/data` cuenta **62** (39 visibles y 23 ocultas; el sistema usa 36). |
| 5.6 | Tabla G.1 | `schema_migrations = 17`; hoy hay migraciones hasta la 028. |

## 6. Anexo F (diccionario de datos)
Las migraciones 020 a 028 cambiaron columnas (`granularidad_meta`, `resultado`, `estado_de_fuente`, vínculo de `fact_marketing` con su documento, escala de las respuestas, entre otras) y agregaron el esquema `app` (3 tablas, **fuera de las 51**). Regenerar las tablas F.x desde `docs/evidencias/diccionario_datos.csv` (`scripts/diccionario_datos_csv.py`) y agregar una nota: «El esquema `app` guarda la configuración personalizada y no forma parte del almacén dimensional».
