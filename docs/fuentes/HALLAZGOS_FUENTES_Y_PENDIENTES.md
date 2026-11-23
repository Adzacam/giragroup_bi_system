# Hallazgos de los 10 libros fuente y pendientes para el chat principal — 2026-11-22

**Qué es esto:** lo que se encontró en `uploads/data` (qué hay en cada libro, hoja y tabla, y qué datos son incongruentes), más la lista de lo que hay que revisar en el pipeline, en BETO y en la web cuando termine el chat de `PLAN_AUDITORIA_DW.md`. Es solo lectura: no cambia el sistema.

**De dónde salen las cifras (todas sin datos personales):**
- `docs/mediciones/fu_l0_hojas.csv` y `fu_l0_perfil.json`: perfil de las 62 hojas (script `scripts/auditoria_fuentes/perfil_fuentes.py`).
- `docs/fuentes/CONTRATO_FUENTES.md`: tipos de fuente, campos y decisión por hoja.
- `docs/cierres/PLAN_FUENTES_UPLOADS.md` (Parte 1): hallazgos por archivo.
- `docs/mediciones/fu_eval_matriz_decisiones.md` y `fu_cierre_dw_viva.csv`: qué se inserta, qué no y qué va a revisión.
- Cuando el plan y el perfil difieren en columnas o filas, se usa el perfil (mide filas físicas; el plan contaba solo datos).

**Etiquetas:** [ERROR] distorsiona un KPI o la web · [SUCIO] dato que el pipeline debe tolerar · [NOTA] observación.

---

## 1. Resumen

| # | Libro | Tipo | Hojas (total / usadas) | Alimenta |
|---|---|---|---|---|
| 1 | BD Cobranzas | COBRANZA | 5 / 1 | KPI-01, 04, 05, 15 |
| 2 | BD Egresos | EGRESOS | 3 / 2 | costos y egresos; metas (subordinadas) |
| 3 | BD Techos | TECHOS | 1 / 1 | KPI-22 |
| 4 | Base centralizada Académica ARCA | ACTA + PLANIFICACION | 7 / 3 | KPI-07, 08, 09, 16, 17, 21; leads de IBP |
| 5 | EJECUTADO VS META | RENTABILIDAD | 2 / 1 | KPI-02, 03, 12, 13, 14 |
| 6 | TBL_INSCRITOS | MARKETING | 2 / 1 | inscritos (Clientes, KPI-21 de web) |
| 7 | PLANIFICACION Y EJECUCION ACADÉMICA | PLANIFICACION | 32 / 20 | KPI-06 (leads e inscritos), metas (`dim_meta`) |
| 8 | Evaluación Docente y Unifranz | EVALUACION_DOCENTE | 3 / 3 | KPI-19, 20 |
| 9 | Experiencia Docente 2.0 | EVALUACION_DOCENTE | 4 / 2 | KPI-19, 20 |
| 10 | [BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE | EVALUACION_DOCENTE | 3 / 2 | KPI-19, 20 |

Total: **62 hojas** (39 visibles, 23 ocultas); el sistema usa **36** (29 visibles y 7 ocultas rescatadas) y descarta **26**. Filas de datos leídas en hojas usadas: **78.005**; filas fantasma cortadas: **3.084**; subtotales cortados: **8**.

---

## 2. Qué hay en cada libro

### 2.1 BD Cobranzas (5 MB · COBRANZA)
| Hoja | Estado | Tamaño | Qué es |
|---|---|---|---|
| COBRANZAS 2024 2025 | visible | 10.022 × 83 (10.017 filas de datos), cabecera fila 1 | Una fila por estudiante y programa: programa, asesor, CI, contacto, facturas, días de mora, tipo de inscripción, **TIPO DE CARTERA**, costo, descuento, deuda total, cuotas, **36 columnas `MONTO <MES> <AÑO>`** (ene-2024 a dic-2026), total pagado, estados académico y ARCA, **TOTAL CUOTAS EN MORA**, RANGO MORA y 7 columnas «(PRELIMINAR)». 197.065 fórmulas (82.603 sin valor guardado). |
| Copia de COBRANZAS 2024 2025 | oculta | 6.212 × 51 (5.478 datos) | Copia antigua de la hoja principal. |
| Hoja 4 | visible | 1.055 × 27 (516 datos) | Forma de tabla dinámica; 48 filas repetidas. |
| Hoja 8 / Hoja 12 | visible | 8 × 10 / 26 × 12 | Tablas auxiliares (7 y 10 filas; la cabecera de Hoja 12 está en la fila 13). |

Vocabulario de cartera: CARTERA CERRADA 9.268 · VIGENTE 441 · INCOBRABLE 165 · PREVISIONABLE 69 · EN MORA 36.
Los datos llegan hasta **mayo de 2026**: las columnas de jun–dic 2026 están 100 % vacías.

Incongruencias:
- [ERROR] La DW leía «Mora» en 7.193 filas (la fuente solo dice EN MORA en 36): el cargador buscaba el texto «MORA» y asignaba la cabecera `mora` a cuotas; hay 3 columnas con «MORA» (DIAS DE MORA, RANGO MORA, TOTAL CUOTAS EN MORA). Causa de KPI-05 ≈ 94 % y KPI-15 ≈ 99 %.
- [ERROR] Cuotas en mora de 2024 perdidas (fuente: ≥ 2 cuotas en 369 / 809 / 643 filas por año de inicio; la DW tenía 1 / 580 / 869).
- [ERROR] Pagos asignados al año de inicio y no al mes del pago (fuente: 8.071.737 / 12.422.501 / 4.841.944 Bs en 2024 / 25 / 26; la DW: 7,27 M / 13,05 M / 5,84 M).
- [SUCIO] 1.518 filas «CARTERA CERRADA» tienen 2 o 3 cuotas en mora (contradicción interna).
- [SUCIO] Cuotas en mora negativas en 428 filas (−5…) y con texto («1s»); deuda total negativa en 629 (sobrepago); días de pago pendiente hasta 665.105 y texto «En curso»; «2 días» como total de cuotas (4); número de factura con texto y fechas; fecha fin con año 0205 (30 filas); celular con 3.667 textos.

### 2.2 BD Egresos (175 KB · EGRESOS)
| Hoja | Tamaño | Qué es |
|---|---|---|
| egresos | 1.468 × 15 (1.373 datos; 8.237 fórmulas) | Una fila por POS: egreso anterior, egreso real, ingreso y rentabilidad, en Bs y USD (tipo de cambio 6,86). |
| Gestiones | 25 × 8 (24) | Resumen mensual: ejecutado 2023–2025 y meta 2025 por tipo (programas / techos). |
| acumulados | 13 × 6 (12) | Lo mismo que Gestiones, pero como texto «Bs…». Se ignora. |

Incongruencias:
- [ERROR] Metas 2025 distintas a las de EJECUTADO VS META (por ejemplo abril 1.098.653 frente a 1.198.653; julio 1.158.082 frente a 1.258.082): 7 de las 10 diferencias son exactas de 100.000 (probable error de tipeo en una de las dos). Origen de los 10 `CONFLICTO_FUENTES`.
- [SUCIO] Un ingreso con fecha en el año 2580; 64 rentabilidades negativas; el tipo de programa mezcla estados («CERRADO», «CERRADO JEA») con tipos.
- [NOTA] La ejecución 2026 llega a mayo (252.233 Bs, parcial).

### 2.3 BD Techos (153 KB · TECHOS)
Una hoja, 1.991 × 29, **207 filas de datos** (1.783 vacías de cola, 327 fórmulas, 12 celdas combinadas). Una fila por convenio de programa con institución (24 instituciones): POS, programa, coordinación, asistente, asesor comercial, N° de inscritos, estado de pago, tipo de certificado y entrega de certificados. Techos de convenio 2022–2025.
- [SUCIO] POS «4924B» (formato no estándar); fecha de inicio en el año 2034; una institución escrita de dos formas; `id_institucion` vacío en 40,6 % de las filas.
- [NOTA] Coherente con la DW (los 93 de 2023 salen de 11 filas).

### 2.4 Base centralizada Académica ARCA (1,2 MB · ACTA + planificación)
| Hoja | Tamaño | Qué es |
|---|---|---|
| ACTAS DE NOTAS | 10.496 × 29 (8.660 datos; 1.835 vacías; 8.663 fórmulas) | Una fila por estudiante y programa: POS, CI, mes y año de inicio (**solo 2024 y 2025**), nombres, notas `MÓDULO 1…12` en formato ancho, ESTADO ACADÉMICO, ESTADO TUTORÍA, ESTADO ARCA, fecha de emisión, POS-CI. |
| MODULOS | 2.031 × 29 (2.030) | Catálogo de módulos con docente, horas, pago y contacto (alimenta `bridge_modulo_docente`). |
| IBP | 942 × 26 (748; 193 vacías) | Planificación por POS: escuela, inversión, punto de equilibrio, modalidad, estado, metas, **LEADS e inscritos** (2026). |
| CRITERIOS / PROGRMAS DE BAJA | 16 × 8 / 2 × 26 | Notas de criterio en texto (15 filas) y una fila. Se ignoran. |
| Tabla dinámica 1 / Hoja 8 | vacías | Se ignoran. |

Vocabularios: estado académico Aprobado 5.388 · En curso 1.471 · Reprobado 858 (+6 en minúscula) · Deserción 488 (+1) · Participó 448; estado de tutoría añade Abandono 251 (+18) e Insuficiencia académica.

Incongruencias:
- [ERROR] La deserción existe en la fuente (estado «Deserción» y «Abandono»), pero la DW daba 0 %.
- [ERROR] Notas con texto y valores fuera de rango en las columnas de módulo: «SIN NOTAS EN EL ACTA…», «No asistió a clases», «EXIMIDA», «Aprobó», apellidos y un **13.622.300** (parece una CI). Hay 2.968 notas en 0 (deserción o inasistencia) que bajaban el promedio de KPI-07.
- [ERROR] La hoja IBP se descartaba como `LINEA_SIN_ENTIDAD` aunque es fuente de leads 2026.
- [SUCIO] Estados escritos de varias formas («Reprobado/reprobado», «Deserción/deserción»); CI con complemento o ciudad (`-1C`, ` CBBA`, ` CH`): el sistema las pegaba y resolvía a otro estudiante; nombres con dígitos o espacios dobles.
- [SUCIO] MODULOS: fecha de inicio entre 2005 y 3035; horas = «SIN INFORMACION»; tipo de programa con mayúsculas mezcladas. IBP: inversión como texto «Bs 5.000,00» (62), gastos «N/A», celdas de META sueltas en la tabla.

### 2.5 EJECUTADO VS META (31 KB · RENTABILIDAD)
| Hoja | Tamaño | Qué es |
|---|---|---|
| EJECUTADO | 993 × 22 (24 datos; 968 vacías) | Ejecutado y meta por categoría y mes (2023–2026) y EBITDA. **La meta 2024 por categoría es una sola celda anual (10.719.694)**; metas 2025 y 2026 mensuales (la de 2026: 1.627.619,5 × 12). Dos columnas sin nombre con residuos de redondeo (−9,3e-10). |
| GESTIONES | 13 × 6 (8), cabecera fila 5 | Totales mensuales como texto «Bs…» mezclado con números. Se ignora. |

- [ERROR] Esto responde DA4: **2024 no tiene meta mensual** (la DW la colocaba en diciembre y daba KPI-02 = 6,25 %). **No existe meta 2023.**
- [NOTA] No hay ejecución de jun–dic 2026 aunque sus metas están cargadas.

### 2.6 TBL_INSCRITOS (3,4 MB · MARKETING)
| Hoja | Tamaño | Qué es |
|---|---|---|
| TBL_INSCRITOS | 15.197 × 37 (15.196; 68.328 fórmulas) | **Una fila por inscripción** (nov-2022 a may-2026): proyecto, programa, asesor, CI, datos personales, institución, nivel académico, NIT, tipo de inscripción, estado (ACTIVO 15.171), género, edad y rango de edad. |
| BAJAS POR DUPLICADOS | oculta, 1 × 26 | Solo cabecera. |

Inscripciones por año: 53 (2022) · 3.551 · 4.563 · 4.737 · 2.292 (2026).
- [ERROR] La DW tenía exactamente el doble (7.102 / 9.124 / 9.472 / 4.576): borrar un documento no borraba sus inscripciones y al volver a subir se sumaban.
- [ERROR] No trae leads: KPI-06 no puede salir de este libro.
- [SUCIO] Género en 4 formas (MUJER / Femenino / HOMBRE / Masculino); edad de 0 a 127 (31 en cero); «No hay datos» en rango de edad (1.505); celular con textos (5.980) y negativos; NIT con texto; tipo de inscripción con dos vocabularios; 4 columnas `… L` 100 % vacías; 5 filas vacías con confianza 0,0000.

### 2.7 PLANIFICACION Y EJECUCION ACADÉMICA (2,8 MB · PLANIFICACION · 32 hojas)
| Grupo de hojas | Estado | Qué son |
|---|---|---|
| Programas Notificados | visible | 1.755 × 71 (1.045 datos): catálogo de programas notificados. |
| Enero-2026 … Diciembre-2026 (12) | visibles | Una hoja por mes con POS, programa, **LEADS, N° INSCRITOS, RESERVAS**, costos, punto de equilibrio y pauta. Tienen entre 22 y 67 filas, salvo **Junio-2026 (1.024) y Diciembre-2026 (1.019)**, con ~970 y ~995 filas vacías o repetidas. |
| Julio-2025 … Diciembre-2025 (6) | ocultas, rescatadas | Mensuales de 2025 (23–30 filas); se usan porque ninguna hoja visible cubre ese período (decisión de Lean). |
| Informe Gestión | oculta, rescatada | Informe de metas 2025 y 2026 (58 metas de `dim_meta`). |
| Centralizado_Mensual | oculta | 2.479 datos, 1.997 duplicadas; se ignora. |
| «Julio-2025 borrador», «Septiembre-2025boor» | ocultas | Borradores; se ignoran. |
| Dashboard Programas, Dashboard Académico | ocultas | Se ignoran. |
| Julio … Diciembre (6, sin año) | ocultas | Mensuales antiguas; se ignoran. |
| Detalle Presupuestado-Proyectad | oculta | 301 × 30; se ignora. |

Leads e inscritos medidos en la fuente: Jul-2025 5.104 / 356 · Ago-2025 4.549 / 202 · Ene-2026 9.958 / 278 · Mar-2026 7.011 / 250 · Jun-2026 3.398 / 17 · Jul–Dic-2026 vacíos. (En la DW, tras la regla 0 ≤ inscritos ≤ leads: Jul-2025 288 inscritos, Mar-2026 7.073 leads, Jun-2026 690 leads.)
- [ERROR] Las hojas mensuales sí traen leads e inscritos por programa (responde DA6), pero el lector solo tomaba la planificación.
- [SUCIO] 9–34 subtotales por hoja; costo del programa como texto «Bs 4.300,00» o «-»; nombre de una asistente escrito de dos formas; «2 días» como duración; 6 columnas de pauta 100 % vacías; una cabecera de Enero-2026 contiene un correo personal.
- [SUCIO] Las hojas ocultas repiten datos de las visibles: el pipeline debe ignorarlas salvo la regla de rescate.

### 2.8 Evaluación Docente y Unifranz (837 KB · EVALUACION_DOCENTE)
| Hoja | Tamaño | Qué es |
|---|---|---|
| DIP. EXP DOC. X MODULO | 7.137 × 30 (4.095 filas; 3.040 vacías; 845 casi vacías; cabecera fila 2) | Evaluación por módulo, nov-2025 a may-2026; escalas 1–5 y 1–10. 52.975 respuestas válidas. |
| DIP. EXP UNIFRANZ | 987 × 29 (516; cabecera fila 2) | Experiencia institucional; mezcla 1–10 con 1–5; etiquetas en columna equivocada («4/Fácil» en «valor del programa»). |
| FINAL EXPERTOCURSO | 1.001 × 29 (275; cabecera fila 2) | Etiquetas **sin número** («Satisfecho», «Probable», «Neutral») y números 8 y 9 en una pregunta de 1–5. |

- [ERROR] La hoja por módulo (la más reciente) se descartaba entera como `LINEA_SIN_ENTIDAD` (10.351 líneas): por eso KPI-19 y KPI-20 de 2026 salían de una muestra parcial.

### 2.9 Experiencia Docente 2.0 (3,4 MB · EVALUACION_DOCENTE)
| Hoja | Estado | Tamaño | Qué es |
|---|---|---|---|
| DIPLOMADOS DOCENTE | visible | 14.847 × 43 (14.397; 227.596 fórmulas) | Cada pregunta trae **dos columnas** (texto y número), escala 0–5, con «0/Sin Información» explícito (por ejemplo 12.604 en la pregunta 8 y 13.726 en la 14). |
| CURSOS DOCENTE | visible | 829 × 38 (828; 13.248 fórmulas) | Igual; nombre, correo y fecha 100 % vacíos; «0/Sin información» en 733 de 828. |
| CURSOS DOC 1 / DIPLOMADOS DOC 2 | ocultas | 995 × 16 / 1.477 × 19 | Versiones previas; se ignoran. |

- [ERROR] El 0 es «Sin Información» de forma literal; al leer texto y número la DW duplicaba cada respuesta (claves de idempotencia ≈ 2× los hechos) y cargaba los ceros.
- [ERROR] El libro se subía como ACTA / CENTESIMAL_100 (la cabecera trae «promedio»).
- [NOTA] 94.578 celdas «0/Sin Información» en este libro (la columna de texto de cada par incluida); las preguntas puntuadas con ese valor son 77.893.

### 2.10 [BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE (2,7 MB · EVALUACION_DOCENTE)
| Hoja | Tamaño | Qué es |
|---|---|---|
| TBL EVALUACION DOCENTE | 16.962 × 32 (16.451; 794 duplicadas; 7.265 celdas combinadas; 14 cabeceras vacías) | Respuestas 1–5 como texto «n/Etiqueta». |
| TBL EXPERIENCIA UNIFRANZ | 13.793 × 26 (2.539; 11.253 vacías; 1.002 combinadas) | Escalas 1–5 y 1–10 mezcladas. |
| Análisis de Evaluación | 132 × 25 (129 subtotales; 254 fórmulas), cabecera fila 3 | Resumen de fórmulas sobre las respuestas. Se ignora. |

- [SUCIO] Respuestas escritas en la columna «Módulo» («4/De acuerdo»…).
- [ERROR] Respuestas cruzadas: una pregunta de satisfacción contiene «5/Totalmente de acuerdo» y el texto de otra pregunta como valor (10.751 celdas en los libros 8 y 10).

Respuestas válidas de encuestas (después de aplicar las reglas): 160.359 (libro 10) + 64.923 (libro 8) + 132.500 (libro 9) = **357.782**. Tras cargarlas quedan 409.859 hechos, con 12.937 sin fecha.

---

## 3. Incongruencias que se repiten entre libros

| Patrón | Dónde aparece | Qué provoca |
|---|---|---|
| Hojas ocultas, copias, borradores y dashboards con datos repetidos | Cobranzas, Experiencia 2.0, Planificación (19 ocultas), TBL_INSCRITOS | Cargar duplicados (6.862 líneas que dejaron de cargarse). |
| Filas fantasma y subtotales | Planificación (3.084), Evaluación Docente y Unifranz (1.076), ARCA | Registros vacíos con confianza 0, falsos pendientes. |
| Fórmulas sin valor guardado | Cobranzas (82.603), Planificación, Experiencia 2.0 | Celdas que se leen vacías (83.908 en hojas usadas). |
| Celdas combinadas y cabecera fuera de la fila 1 | ANTIGUO (7.265), Unifranz (cabecera fila 2), Hoja 12 (fila 13), GESTIONES (fila 5) | Cabecera mal detectada. |
| Números guardados como texto («Bs 4.300,00», «-», «N/A», «SIN INFORMACION», «2 días») | Cobranzas, Egresos, Ejecutado, Planificación, ARCA | Montos que no se leen como número. |
| Valores centinela que son «sin dato» (0, «0/Sin Información», «-», «N/A») | Encuestas, Cobranzas, Planificación | Promedios y tasas distorsionados. |
| Escalas mezcladas (1–5 con 1–10, 0–5) y etiquetas con o sin número | Los 3 libros de encuestas | Puntuaciones fuera de escala y respuestas en columna equivocada. |
| Vocabularios en varias formas (mayúsculas, acentos, sinónimos) | Género, estados académicos, tipo de programa, tipo de inscripción, instituciones | Categorías partidas. |
| Fechas y valores fuera de rango (años 0205, 2034, 2580, 3035, edad 127, días 665.105) | Cobranzas, Techos, Egresos, MODULOS, TBL_INSCRITOS | Períodos y KPI por año erróneos. |
| CI con complemento, ciudad o texto pegado; nombres con dígitos | ARCA, Cobranzas, TBL_INSCRITOS | Identidad resuelta a otra persona o bloqueada. |
| Dos fuentes con cifras distintas para lo mismo | Metas 2025 (Egresos frente a EJECUTADO VS META) | Conflicto de fuentes. |
| Dos columnas por pregunta (texto y número) | Experiencia 2.0, Unifranz | Respuestas duplicadas. |
| Datos que llegan hasta mayo de 2026 con meses posteriores vacíos | Cobranzas, Ejecutado, Planificación | Mes parcial que distorsiona KPI-02, 03 y 12. |

---

## 4. Qué falló en el pipeline y en BETO, y en qué estado queda

| Falla | Evidencia | Estado |
|---|---|---|
| Hojas válidas descartadas por no detectar entidad (`LINEA_SIN_ENTIDAD`) | 3.689 → 71 líneas; evaluación por módulo (10.351) e IBP (748) | Corregido (FU-L1) |
| Hojas ocultas y borradores cargadas como datos | 6.862 líneas duplicadas | Corregido: regla `rescate_ocultas` y `HOJA_IGNORADA` (FU-L1) |
| Libro de encuestas tipificado como acta; doble columna; 0 cargado | 357.782 válidas = DW; 0 puntuaciones fuera de escala | Corregido (FU-L5) |
| Lector de reportes Moodle partía la hoja por módulo con cabeceras basura | 25.553 líneas de cabecera mala | Corregido (FU-L5) |
| Inscritos ×2 | 3.551 / 4.563 / 4.737 / 2.292 = fuente | Corregido (FU-L3, migración 023) |
| Cartera por texto «MORA», cuotas desde «días de mora», pagos al año de inicio | pagos = fuente; mora 362 / 808 / 641 | Corregido (FU-L2, regla DA3) |
| CI con complemento resolvía a otro estudiante | `4892019-1C` se leía como `48920191C` | Corregido (FU-L4, `separar_ci`) |
| Estados sin normalizar, notas texto o fuera de rango, 0 por inasistencia | resultado por módulo y avisos agregados | Corregido (FU-L4) |
| La lectura BETO borraba el payload de staging (período, hoja, 58 metas) | hallado al recargar | Corregido (FU-L3) |
| Fechas con milisegundos rechazadas; inscripciones con CI incompleta contaban 0; inscripción asignada a un módulo leído de otra columna | hallados al recargar | Corregido (FU-L3) |
| `db.rollback()` borraba datos no confirmados en SQLite | 2 pruebas de KPI-06 fallaban | Corregido (SAVEPOINT, FU-L3) |
| Meta anual puesta en diciembre; conflicto de 100.000; mes parcial | KPI-02 2024 = 6,25 % | Corregido (FU-L6) |
| Listas fijas de cabeceras en el código | `extraccion_por_encabezado.py`, `routers/pipeline.py`, `routers/dataops/extraccion.py` | Migradas al catálogo en FU-L9 (declarado por esa sesión; no lo revisé línea a línea) |
| `fk_resolver.py` busca el padrón en una ruta fija de libro | deuda en lista blanca | **Pendiente** |
| Cascada de identidad bloquea filas de actas | 1.516 casos pendientes hoy: CI_NOMBRE_DISCORDANTE 747 · HOMONIMIA 363 · BAJA_CONFIANZA_IA 323 · BAJA_CONFIANZA 74 · CI_DUDOSA 8 · FILA_SIN_IDENTIDAD 1 | **Pendiente**: filas de actas 25.208 frente a 27.731 en copia limpia (KPI-16 2024 = 5,38 % frente a 10,17 % de la fuente) |
| Detección Egresos frente a Rentabilidad en `ingestion_service` | un libro de Egresos subido con otro tipo deja el conflicto de metas pendiente | **Pendiente** |
| Datos sucios en dimensiones (profesiones y números sueltos como programa o módulo) | aparecen en los filtros de Alertas Tempranas | **Pendiente** (columnas mal leídas en la carga) |
| Lote congelado 1387 incluye 110 filas de la hoja oculta `CURSOS DOC 1` | su script la lee por nombre | **Pendiente** (incoherente con lo que carga el sistema) |
| Pruebas de BETO | 4 fallan por falta de `seqeval` (y 2 por `statsmodels`) en el entorno del host | **Pendiente** de entorno, no de código |
| Lectura BETO lenta la primera vez | ~15 min sobre 15.196 líneas (el caché `beto-v2` la acelera) | [NOTA] |

---

## 5. Para retomar en el chat principal (cuando termine el chat de `PLAN_AUDITORIA_DW.md`)

Objetivo: ver qué está mal en el pipeline y en BETO, sanearlo, y que **no dependa de estos 10 archivos**.

### 5.1 El sistema debe analizar cualquier texto heterogéneo admitido
- Hoy `pipeline/ingesta.py` admite `.xlsx`, `.xls` y `.csv`, con un registro de lectores extensible (`LECTORES`). Hay que definir qué más es «texto heterogéneo admitido» antes de probarlo.
- Criterio de prueba: libros que el sistema nunca vio (otros nombres, cabeceras con sinónimos, columnas en otro orden, hojas ocultas, escalas mezcladas, texto libre, filas basura). Existen fixtures sintéticas en `tests/fixtures/fuentes_sinteticas/`; hay que ampliarlas con casos de texto libre largo (narrativo) y no solo tablas.
- Comprobar qué pasa cuando una hoja no es una tabla: qué reconoce el PLN, qué extrae el NER y qué deja para BETO. Hoy BETO es el último escalón de la cascada (CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO), solo para residuales, y nunca sobrescribe estados A/B.

### 5.2 Mostrar visualmente el flujo (PLN, NER, BETO)
Ya existe (declarado por la sesión de FU-L8; solo verifiqué la pantalla de Alertas Tempranas):
- Vista previa por hoja (usada, ignorada u oculta y por qué) con tabla editable columna → campo canónico (`POST /api/v1/dataops/preview-workbook`).
- Resumen de cascada por etapa (`resumen_cascada`) y pantalla de lectura BETO con «Qué significa».
Falta o está sin verificar:
- Recorrido interactivo de los 3 pasos de DataOps (claro, oscuro y móvil) con clic real.
- Mostrar, por entidad, qué etapa la resolvió y con qué evidencia o puntaje, y qué etiquetas (IOB2) puso BETO frente a lo que aceptó la cascada.
- Mostrar lo que el sistema reconoció del texto libre, no solo de columnas.

### 5.3 Revisión humana con contexto
Ya existe: motivos nuevos, bandeja agrupada por patrón y por hoja, bloque «Por qué está aquí» (regla, umbral, valor enmascarado), descarte de filas vacías, `HOJA_IGNORADA` fuera de la bandeja.
Revisar:
- Los **1.516 casos pendientes** (sobre todo 747 CI_NOMBRE_DISCORDANTE y 363 HOMONIMIA): si son de verdad accionables o producto de nombres antiguos del snapshot.
- Que cada caso muestre hoja, fila, columna, qué falla y qué corregir, sin datos personales.
- Que la aprobación en bloque no cuente como corrección (ADW-L8).
- Que los avisos agregados de FU-L2 a FU-L6 (cuotas negativas, notas fuera de rango, valores fuera de catálogo, conflictos de metas) lleguen a la web con su motivo legible.

### 5.4 Decisiones de Lean todavía abiertas
- KPI-16 de 2024: 10,17 % en la fuente frente a 5,38 % en la DW viva (aceptar o depurar las filas bloqueadas).
- Si KPI-03 y KPI-12 excluyen el mes parcial (extensión que no pidió Lean).

---

## 6. Datos personales
Los libros 1, 4, 6, 8, 9 y 10 traen nombres, CI, correos, celulares, direcciones o NIT en columnas que ningún informe publica (el perfil solo publica cabeceras y conteos). Una hoja oculta de una sola fila (`BAJAS POR DUPLICADOS`) traía un nombre, domicilio y fecha de nacimiento; el perfil ya no publica su contenido.
