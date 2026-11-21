# Contrato de fuentes (FU-L0)

**Alcance:** describe tipos de fuente y campos canónicos, no archivos. Los 10 libros de `uploads/data` son ejemplos de cada tipo.
**Fuentes de verdad:** `config/mapeo_fuentes.yaml` (catálogo editable de sinónimos y reglas), `docs/mediciones/fu_l0_perfil.json` (perfil sin PII, 62 hojas) y `docs/mediciones/fu_l0_hojas.csv` (una fila por hoja).
**Regla:** un archivo nuevo con otras cabeceras se incorpora añadiendo un sinónimo en el YAML, no código. Las cabeceras se publican; los valores de columnas personales no.

## 0. Conteo de hojas

El perfil mide **62 hojas** en 10 libros. PLAN_FUENTES_UPLOADS.md dice 61; la diferencia no se forzó. Por estado: 39 visibles, 23 ocultas, 0 veryHidden. Decisión (FU-L1b): 36 usar (29 visibles y 7 ocultas rescatadas), 26 ignorar.

## 1. Reglas generales

- **Hojas ocultas** (`hidden`, `veryHidden`): se ignoran, salvo que el contrato diga otra cosa.
- **Excepción de ocultas (FU-L1b, decisión de Lean, 2026-11-20):** una hoja oculta se usa cuando por contenido es de tipo PLANIFICACION (hoja mensual de detalle con un período año-mes dominante, o informe de metas con rótulos de gestión y columnas de meta), no cae en ninguna regla de forma ni de nombre (borrador, copia, centralizado, tabla dinámica, dashboard, filas repetidas) y ninguna hoja visible usada del mismo libro cubre su período o su entidad (prioridad a la hoja visible de detalle, DA6). Si el período ya está cubierto, se ignora como duplicada. Regla en `config/mapeo_fuentes.yaml` → `reglas_hoja.rescate_ocultas`; la aplican el clasificador y el extractor de planificación con una sola decisión. Hoy rescata 7 hojas: las 6 mensuales de jul. a dic. 2025 (140 filas de `fact_planificacion_programa`) y el informe de gestión (58 metas de `dim_meta`); las cifras congeladas no cambian.
- **Nombre y forma** (`reglas_hoja` del YAML): borrador, copia, `Hoja N`, tabla dinámica, dashboard y centralizado se detectan por nombre como señal y por forma (0 filas, resumen de fórmulas, filas repetidas). El resultado sale en la vista previa (FU-L8).
- **Cabecera** por contenido, no por índice fijo: la fila con más textos distintos no numéricos, ponderada por su proporción. Casi todas las hojas tienen la cabecera en la fila 1. Son excepciones: «Hoja 12» (fila 13), «DIP. EXP DOC. X MODULO» y «DIP. EXP UNIFRANZ» (fila 2), «FINAL EXPERTOCURSO» (fila 2) y «GESTIONES» (fila 5).
- **Normalización de cabeceras:** minúsculas, sin acentos, espacios colapsados. El símbolo «°» se pierde: «N° INSCRITOS» queda «n inscritos».
- **Filas que no son datos:** vacías, subtotales («total…») y repetidas no cuentan como datos.
- **Mora:** `cuotas_en_mora` es el conteo de cuotas impagas. Otras columnas con «mora» (`rango mora`, `dias de mora`) no se mapean a ese campo.
- **Etiquetas Likert:** se llevan a número con diccionario `cat_*` (FU-L5). Un 0 o «Sin Información» es NULL (DA1).

## 2. Contrato por tipo de fuente


### COBRANZA

- **Granularidad:** Una fila por estudiante y programa, con una columna de pago por mes (`MONTO <MES> <AÑO>`).
- **Hojas oficiales (usar):** COBRANZAS 2024 2025 (BD Cobranzas.xlsx)
- **Hojas a ignorar de este tipo:** -
- **Cabecera y escala o vocabulario:** Cabecera en fila 1. Vocabulario de `estado_cartera_fuente` (conteos del perfil): CARTERA CERRADA 9.268; VIGENTE 441; PREVISIONABLE 69; INCOBRABLE 165; EN MORA 36.
- **Columnas usadas → campo canónico:**
- `estado_cartera_fuente` ← `tipo de cartera` (prioridad 1), `estado de cartera`, `estado cartera` (prioridad 2). Vocabulario normalizado: CERRADA, VIGENTE, EN MORA, PREVISIONABLE, INCOBRABLE. Descriptivo: no decide la mora. Un valor fuera del vocabulario no se descarta: el hecho se carga sin estado de fuente y el aviso `VALOR_FUERA_DE_CATALOGO` queda pendiente.
- `cuotas_en_mora` ← `total cuotas en mora` (1), `cuotas en mora`, `cuotas impagas`, `nro cuotas en mora` (2), `cuotas vencidas` (3). La cabecera suelta `mora` es **ambigua** (prioridad 9): solo vale si la hoja no trae ninguna cabecera específica de cuotas.
- `dias_mora` ← `dias de mora` (1), `dias en mora`, `dias de atraso` (2). Va a `fact_situacion_financiera.dias_mora`; nunca a cuotas.
- `monto_pago_mes` ← patrón `^monto (enero|…|diciembre) \d{4}$` (1) y `^(pago|abono|pagado) <mes> \d{4}$` (2); se excluyen las columnas «(PRELIMINAR)». Cada columna va al mes de su pago.
- `monto_deuda` ← `deuda total` (1), `saldo deudor`, `saldo pendiente` (2).
- `monto_pagado_total` ← `total pagado hasta la fecha` (1), `total pagado` (2), `monto pagado` (3). Solo se usa si la fila no trae columnas de pago mensual.
- `fecha_inicio` ← `fecha inicio diplomado` (1), `fecha de inicio`, `fecha inicio`, `fecha inicio programa` (2). El hecho de situación cae en esa fecha.
- `estado_academico` ← `estado academico`
- `programa` ← `nombre del programa`
- `pos` ← `pos`
- `ci` ← `ci`
- **Columnas no mapeadas (descriptivas):** `rango mora` (tramo de días), `dias de pago pendiente`, `estado arca`, `estado reprobado`, `pos-ci`, `validador pos`
- **Reglas de calidad (FU-L2, avisos agregados por documento y motivo, sin datos personales):** `cuotas_en_mora` negativo (p. ej. -5) → 0 (`CUOTAS_NEGATIVAS`); texto con número inicial («1s») → ese número (`CUOTAS_CON_TEXTO`); texto sin número → 0 (`CUOTAS_NO_NUMERICAS`). `monto_deuda` negativo (sobrepago) → 0 (`SOBREPAGO`). `dias_mora` negativo → 0. Las columnas «(PRELIMINAR)» no se cargan como pago mensual.
- **Mora (DA3, decisión de Lean):** un hecho está en mora si `cuotas_en_mora` ≥ 2 (umbral en `tipos_fuente.COBRANZA.regla_mora`). Una sola regla en `bi.vw_cmi_valores` (KPI-04, 05, 15), `bi.vw_cartera_estado`, `bi.vw_riesgo_estudiante`, KPIService y risk_service (`backend/services/regla_mora.py`). `estado_cartera` = Mora/Vigente por esa regla; el estado de la fuente se guarda aparte. KPI-05 = estudiantes en mora / estudiantes con cartera; KPI-15 = deuda de esos estudiantes / deuda total.
- **Contradicción interna documentada (no se corrige):** 1.518 filas «CARTERA CERRADA» traen 2 o más cuotas en mora; por DA3 cuentan como mora y su `estado_cartera_fuente` sigue siendo CERRADA.
- **Hechos que produce una fila:** una `SITUACION_CARTERA` (deuda, cuotas, días, estado de la fuente) en la fecha de inicio y un `PAGO_MES` por mes con pago (cuotas, deuda y estados en NULL). Idempotencia por `carga_fila_origen` (clave de la fila; la de cada pago lleva el mes).
- **Pueden venir vacías sin que sea error:** Las columnas de pago de meses sin ejecutar (p. ej. jun-dic 2026) pueden venir vacías; no es error. Observación y criterio libre pueden faltar. Del YAML: `observacion`, `criterio libre`, `comentario daf`.

### ACTA

- **Granularidad:** Una fila por estudiante y programa. Notas por módulo en formato ancho (`MODULO 1…12`).
- **Hojas oficiales (usar):** ACTAS DE NOTAS (Base centralizada Académica ARCA (1).xlsx)
- **Hojas a ignorar de este tipo:** -
- **Cabecera y escala o vocabulario:** Cabecera en fila 1. Vocabulario de estado académico (conteos del perfil): Aprobado 5.388; En curso 1.471; Reprobado 858 (+6 en minúscula); Deserción 488 (+1); Participó 448. El estado de tutoría añade Abandono (251 + 18 en minúscula) e Insuficiencia académica.
- **Columnas usadas → campo canónico:**
- `ci` ← `cedula de identidad`
- `pos` ← `pos - actas`
- `estado_academico` ← `estado academico`, `estado tutoria`
- `nota_modulo` ← patrón `^modulo \d{1,2}$`
- **Columnas no mapeadas:** `nombres`, `apellido paterno`, `apellido materno`, `pos-ci`, `comentarios`, `fecha emision arca`
- **Reglas de calidad:** Notas con texto («Aprobó», «EXIMIDA», «No asistió», apellidos) → resultado canónico o revisión (DA-FU2). Un 0 cuenta como INASISTENCIA solo con estado Deserción o Abandono. Una nota fuera de 0-100 → NOTA_FUERA_DE_RANGO.
- **Pueden venir vacías sin que sea error:** Estado de tutoría, comentarios y fecha de emisión pueden faltar. Una nota de módulo no cursado puede venir vacía. Del YAML: `comentarios`, `estado tutoria`.

### EVALUACION_DOCENTE

- **Granularidad:** Una fila por respuesta. Una columna por pregunta.
- **Hojas oficiales (usar):** TBL EVALUACION DOCENTE ([BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx); TBL EXPERIENCIA UNIFRANZ ([BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx); DIP. EXP DOC. X MODULO (Evaluación Docente y Unifranz.xlsx); DIP. EXP UNIFRANZ (Evaluación Docente y Unifranz.xlsx); FINAL EXPERTOCURSO (Evaluación Docente y Unifranz.xlsx); DIPLOMADOS DOCENTE (Experiencia Docente 2.0.xlsx); CURSOS DOCENTE (Experiencia Docente 2.0.xlsx)
- **Hojas a ignorar de este tipo:** -
- **Cabecera y escala o vocabulario:** Cabecera en fila 1 (encuestas ANTIGUO y Experiencia 2.0), fila 2 (DIP. EXP. DOC. X MODULO, DIP. EXP. UNIFRANZ, FINAL EXPERTOCURSO). Escala 1-5; las preguntas «escala del 1 al 10» tienen `escala_max` = 10. Experiencia 2.0 es 0-5 con dos columnas por pregunta (texto y número).
- **Columnas usadas → campo canónico:**
- `puntuacion` ← patrón `^(a )?\d+\. `
- `escala_max` ← regla de escala (ver YAML)
- `programa` ← `programa`, `programa pos`, `programa - pos`
- **Columnas no mapeadas:** `nombre completo del usuario`, `direccion de correo`, `grupos`, `fecha`, `modulo`, `numero del modulo`, `respuesta numero`
- **Reglas de calidad:** 0 o «Sin Información» → NULL (DA1). Etiquetas sin número («Satisfecho», «Probable», «Neutral») → diccionario de FU-L5. Respuesta en la columna de otra pregunta → RESPUESTA_EN_COLUMNA_EQUIVOCADA, agrupada. Con par texto/número se lee solo la columna numérica.
- **Pueden venir vacías sin que sea error:** Comentarios, sugerencias y datos de contacto pueden faltar. La numérica de un par puede venir vacía si la pregunta no aplica. Del YAML: `comentarios`.

### MARKETING

- **Granularidad:** Una fila por inscripción individual (nov-2022 a may-2026).
- **Hojas oficiales (usar):** TBL_INSCRITOS (TBL_INSCRITOS.xlsx)
- **Hojas a ignorar de este tipo:** -
- **Cabecera y escala o vocabulario:** Cabecera en fila 1. El género viene en cuatro formas (MUJER, Femenino, HOMBRE, Masculino) → catálogo `genero`.
- **Columnas usadas → campo canónico:**
- `programa` ← `nombre del programa`
- `ci` ← `ci`
- `genero` ← `genero`, `genero l`
- **Columnas no mapeadas:** `nombres`, `paterno`, `materno`, `celular`, `correo electronico`, `direccion`, `nit`, `razon social`, `asesor`, `pos-ci incritos`
- **Reglas de calidad:** Esta fuente **no** tiene leads, así que no alimenta KPI-06 (DA6). Cada fila es una inscripción: no se cuenta dos veces (origen del ×2 en la DW, FU-L3).
- **Pueden venir vacías sin que sea error:** NIT, razón social, celular y correo pueden venir vacíos. Las columnas derivadas `… L` pueden estar 100 % vacías. Del YAML: `rango edad`, `nivel academico l`, `universidad`.

### EGRESOS

- **Granularidad:** Egresos por programa (una fila por POS) y resumen mensual de ejecución por tipo de ingreso.
- **Hojas oficiales (usar):** egresos (BD Egresos.xlsx); Gestiones (BD Egresos.xlsx)
- **Hojas a ignorar de este tipo:** -
- **Cabecera y escala o vocabulario:** Cabecera en fila 1 en ambas hojas. Montos en Bs y USD (tipo de cambio 6,86). El resumen trae números; la hoja «acumulados» los trae como texto «Bs…» y no se usa.
- **Columnas usadas → campo canónico:**
- `monto_egreso` ← `egreso real`
- `monto_ejecutado` ← patrón `^ejecutado \d{4}$`
- `monto_meta` ← patrón `^meta \d{4}$`
- `programa` ← `nombre del programa`
- `pos` ← `nro pos`
- **Columnas no mapeadas:** `ingreso`, `rentabilidad`, `comentarios`, `tipo de cambio`, `egreso anterior`
- **Reglas de calidad:** Ejecutado 2023-2025 y meta 2025 en el resumen. Meta 2024 sin detalle mensual (DA4). Prioridad de `monto_meta` y `monto_ejecutado`: RENTABILIDAD > EGRESOS (DA-FU3).
- **Pueden venir vacías sin que sea error:** Columnas en dólares y tipo de cambio pueden venir vacías en filas sin conversión. Del YAML: -.

### RENTABILIDAD

- **Granularidad:** Ejecutado frente a meta por categoría y mes, con EBITDA.
- **Hojas oficiales (usar):** EJECUTADO (EJECUTADO VS META.xlsx)
- **Hojas a ignorar de este tipo:** -
- **Cabecera y escala o vocabulario:** Cabecera en fila 1. La meta 2024 por categoría es una sola celda anual (10.719.694), no mensual. Meta 2025 y 2026 son mensuales.
- **Columnas usadas → campo canónico:**
- `monto_meta` ← patrón `^meta( por categoria)? \d{4}`
- `monto_ejecutado` ← patrón `^ejecutado \d{4}$`, patrón `^ejec\. \d{4}$`
- **Columnas no mapeadas:** `ebitda meta 2024`, `ebitda ejecutado 2024`, `ebitda meta 2025`, `ebitda ejecutado 2025`, `proyeccion maestrias`, `categoria`, `mes`, `mes numerico`
- **Reglas de calidad:** Metas 2025 distintas entre archivos con diferencias exactas de 100.000: gana esta fuente y el conflicto se registra como CONFLICTO_FUENTES resuelto por regla (FU-L6).
- **Pueden venir vacías sin que sea error:** Columnas EBITDA de años sin dato y las dos columnas sin nombre (residuos de redondeo) pueden venir vacías. Del YAML: `ebitda meta 2024`, `ebitda ejecutado 2024`.

### TECHOS

- **Granularidad:** Una fila por convenio (programa × institución).
- **Hojas oficiales (usar):** BD Techos (BD Techos.xlsx)
- **Hojas a ignorar de este tipo:** -
- **Cabecera y escala o vocabulario:** Cabecera en fila 1. Una institución escrita de dos formas («ECOGUZ»): se normaliza por catálogo.
- **Columnas usadas → campo canónico:**
- `pos` ← `pos`
- `programa` ← `programa`
- **Columnas no mapeadas:** `coord.`, `asistente`, `asesor comercial`, `institucion`, `insitucin`, `n inscr.`, `estado de pago`, `tipo de certificado`, `estado entrega de certificados`, `id_institucion`
- **Reglas de calidad:** POS con formato no estándar («4924B») y fechas de inicio fuera de rango → fila a revisión, no descarte silencioso.
- **Pueden venir vacías sin que sea error:** `id_institucion` viene vacío en 40,6 % de las filas; no es error. Del YAML: `id_institucion`, `fecha conclusion`.

### PLANIFICACION

- **Granularidad:** Una fila por programa y mes (hojas mensuales 2026 e IBP) y una fila por programa notificado.
- **Hojas oficiales (usar):** IBP (Base centralizada Académica ARCA (1).xlsx); Programas Notificados (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); Enero-2026 (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); Febrero-2026 (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); Marzo-2026 (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); Abril-2026 (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); Mayo-2026 (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); Junio-2026 (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); Julio-2026 (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); Agosto-2026 (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); Septiembre-2026 (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); Octubre-2026 (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); Noviembre-2026 (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); Diciembre-2026 (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx); ocultas rescatadas (FU-L1b): Julio-2025, Agosto-2025, Septiembre-2025, Octubre-2025, Noviembre-2025, Diciembre-2025 e Informe Gestión (PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx)
- **Hojas a ignorar de este tipo:** -
- **Cabecera y escala o vocabulario:** Cabecera en fila 1. Las hojas mensuales 2025 están ocultas y se usan por la excepción de ocultas (período sin hoja visible); los borradores, el centralizado, los dashboards y las mensuales antiguas sin año siguen ignorados. Junio-2026 y Diciembre-2026 traen 970 y 995 filas repetidas o vacías.
- **Columnas usadas → campo canónico:**
- `pos` ← `pos`, `pos - ibp`
- `programa` ← `programa`, `nombre del programa`
- `leads_captacion` ← `leads`
- `inscritos_captacion` ← `n inscritos`, `n de inscritos`
- `reservas` ← `reservas`
- **Columnas no mapeadas:** `costo programa`, `punto de equilibrio`, `estado`, `comentarios`, `comentario daf`, `p/ejecutado`, `p/asignado`, `tc (cliente externo)`
- **Reglas de calidad:** Leads e inscritos de captación (DA6): sumar por mes solo filas con ambos datos y 0 ≤ inscritos ≤ leads. Las reservas se guardan y no entran en el KPI. POS × mes en varias hojas: se cuenta una vez, con prioridad a la hoja visible de detalle.
- **Pueden venir vacías sin que sea error:** Leads e inscritos vacíos en jul-dic 2026 (no hay ejecución cargada); no es error. Columnas de pauta y de digital pueden venir vacías. Del YAML: `comentarios`, `comentario daf`, `comentario digital / video solicitado`, `comentario admisiones`.

### Hojas sin tipo en este contrato

- `MODULOS` (catálogo de módulos con docente): **usada** (corrección de FU-L1). Produce las asignaciones módulo-docente que llenan `bridge_modulo_docente`, la única tabla puente de la DW. Sus columnas de contacto del docente no se publican en informes.

## 3. Prioridad de fuentes por campo (DA-FU3)

| Campo | Prioridad |
|---|---|
| `monto_meta`, `monto_ejecutado` | RENTABILIDAD > EGRESOS |
| `monto_egreso`, costos | EGRESOS > RENTABILIDAD |

Un conflicto entre dos fuentes del mismo lote y mes se resuelve con esta regla y se registra como `CONFLICTO_FUENTES` informativo (FU-L6).

## 4. Hojas (62): decisión y motivo

Criterio: las 62 hojas tienen decisión (usar o ignorar) con motivo. «DIP. EXP DOC. X MODULO» e «IBP» se marcan usar, como pide el plan.

| archivo | hoja | estado | decisión | motivo | tipo |
|---|---|---|---|---|---|
| [BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx | TBL EVALUACION DOCENTE | visible | usar | Hoja visible de respuestas 1-5 con texto 'n/Etiqueta'; cabecera en fila 1 | EVALUACION_DOCENTE |
| [BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx | TBL EXPERIENCIA UNIFRANZ | visible | usar | Hoja visible con respuestas cruzadas entre preguntas (RESPUESTA_EN_COLUMNA_EQUIVOCADA); se usa con reglas de FU-L5 | EVALUACION_DOCENTE |
| [BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx | Análisis de Evaluación | visible | ignorar | Resumen con 254 fórmulas de agregado sobre la tabla de respuestas (129 filas); no es fuente de respuestas | - |
| Base centralizada Académica ARCA (1).xlsx | ACTAS DE NOTAS | visible | usar | Hoja visible; una fila por estudiante y programa; cabecera en fila 1; estado académico y notas por módulo | ACTA |
| Base centralizada Académica ARCA (1).xlsx | MODULOS | visible | usar | Alimenta `bridge_modulo_docente` (corregido en FU-L1; las columnas de contacto no se publican) | ACTA |
| Base centralizada Académica ARCA (1).xlsx | Tabla dinámica 1 | visible | ignorar | Tabla dinámica vacía (0 filas) | - |
| Base centralizada Académica ARCA (1).xlsx | PROGRMAS  DE BAJA | visible | ignorar | Una sola fila de datos; notas de criterio de baja sin granularidad de fuente | - |
| Base centralizada Académica ARCA (1).xlsx | IBP | visible | usar | Excepción del plan (DA6): única fuente de leads e inscritos 2026 junto con planificación; cabecera en fila 1 | PLANIFICACION |
| Base centralizada Académica ARCA (1).xlsx | Hoja 8 | visible | ignorar | Hoja vacía (0 filas) | - |
| Base centralizada Académica ARCA (1).xlsx | CRITERIOS | visible | ignorar | Notas de criterio en texto (15 filas); no es tabla de datos | - |
| BD Cobranzas.xlsx | COBRANZAS 2024 2025 | visible | usar | Hoja principal visible; una fila por estudiante y programa; fórmulas de cartera; cabecera en fila 1 | COBRANZA |
| BD Cobranzas.xlsx | Hoja 8 | visible | ignorar | Tabla auxiliar de 7 filas; sin campos canónicos | - |
| BD Cobranzas.xlsx | Hoja 12 | visible | ignorar | Tabla auxiliar de 10 filas con cabecera en fila 13; sin campos canónicos | - |
| BD Cobranzas.xlsx | Hoja 4 | visible | ignorar | Tabla auxiliar visible con 48 filas repetidas y forma de tabla dinámica; no aporta campos canónicos | - |
| BD Cobranzas.xlsx | Copia de COBRANZAS 2024 2025 | hidden | ignorar | Oculta y copia antigua de la hoja principal (estado hidden, nombre 'Copia de') | - |
| BD Egresos.xlsx | egresos | visible | usar | Hoja visible; egreso real y rentabilidad por programa (una fila por POS) | EGRESOS |
| BD Egresos.xlsx | Gestiones | visible | usar | Resumen numérico mensual por tipo de ingreso; fuente secundaria de meta 2025 (gana RENTABILIDAD por DA-FU3) | EGRESOS |
| BD Egresos.xlsx | acumulados | visible | ignorar | Mismo dato que Gestiones pero como texto 'Bs…'; es el origen de la diferencia de 100.000 en la meta 2025 (CONFLICTO_FUENTES) | - |
| BD Techos.xlsx | BD Techos | visible | usar | Hoja visible; una fila por convenio; alimenta KPI-22 | TECHOS |
| EJECUTADO VS META.xlsx | EJECUTADO | visible | usar | Hoja visible; ejecutado y meta por categoría y mes; prioridad sobre EGRESOS en metas (DA-FU3) | RENTABILIDAD |
| EJECUTADO VS META.xlsx | GESTIONES | visible | ignorar | Totales mensuales en texto con prefijo 'Bs' mezclado con números; duplica EJECUTADO; no se lee como numérico | - |
| Evaluación Docente y Unifranz.xlsx | DIP. EXP DOC. X MODULO | visible | usar | Excepción del plan: evaluación por módulo 2025-11 a 2026-05 (DA, FU-L5); cabecera en fila 2 | EVALUACION_DOCENTE |
| Evaluación Docente y Unifranz.xlsx | DIP. EXP UNIFRANZ | visible | usar | Hoja visible con mezcla de escalas (1-5 y 1-10) y etiquetas en columna equivocada; se usa con reglas de FU-L5 | EVALUACION_DOCENTE |
| Evaluación Docente y Unifranz.xlsx | FINAL EXPERTOCURSO | visible | usar | Hoja visible con etiquetas sin número ('Satisfecho', 'Probable'); se usa con diccionario de FU-L5 | EVALUACION_DOCENTE |
| Experiencia Docente 2.0.xlsx | CURSOS DOC 1 | hidden | ignorar | Oculta; versión previa del curso | - |
| Experiencia Docente 2.0.xlsx | DIPLOMADOS DOCENTE | visible | usar | Hoja visible 0-5 con dos columnas por pregunta (texto y número); se lee solo la numérica | EVALUACION_DOCENTE |
| Experiencia Docente 2.0.xlsx | CURSOS DOCENTE | visible | usar | Hoja visible 0-5; identificación (nombre, correo, fecha) 100 % vacía; solo agregados | EVALUACION_DOCENTE |
| Experiencia Docente 2.0.xlsx | DIPLOMADOS DOC 2 | hidden | ignorar | Oculta; versión previa del diplomado | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Centralizado_Mensual | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Julio-2025 | hidden | usar | Oculta rescatada: período sin hoja visible (2025-07); hoja mensual de detalle con LEADS e inscritos (FU-L1b, decisión de Lean) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Agosto-2025 | hidden | usar | Oculta rescatada: período sin hoja visible (2025-08); hoja mensual de detalle con LEADS e inscritos (FU-L1b, decisión de Lean) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Septiembre-2025 | hidden | usar | Oculta rescatada: período sin hoja visible (2025-09); hoja mensual de detalle con LEADS e inscritos (FU-L1b, decisión de Lean) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Octubre-2025 | hidden | usar | Oculta rescatada: período sin hoja visible (2025-10); hoja mensual de detalle con LEADS e inscritos (FU-L1b, decisión de Lean) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Noviembre-2025 | hidden | usar | Oculta rescatada: período sin hoja visible (2025-11); hoja mensual de detalle con LEADS e inscritos (FU-L1b, decisión de Lean) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Julio-2025 borrador | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Diciembre-2025 | hidden | usar | Oculta rescatada: período sin hoja visible (2025-12); hoja mensual de detalle con LEADS e inscritos (FU-L1b, decisión de Lean) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Informe Gestión | hidden | usar | Oculta rescatada: informe de metas (gestiones 2025 y 2026) sin hoja visible equivalente; fuente de las 58 metas de `dim_meta` (FU-L1b, decisión de Lean) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Programas Notificados | visible | usar | Hoja visible del catálogo de programas notificados; POS y programa | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Enero-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; ignorar filas repetidas y vacías (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Febrero-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; ignorar filas repetidas y vacías (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Marzo-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; ignorar filas repetidas y vacías (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Abril-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; ignorar filas repetidas y vacías (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Mayo-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; ignorar filas repetidas y vacías (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Junio-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; ignorar filas repetidas y vacías (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Julio-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; ignorar filas repetidas y vacías (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Agosto-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; ignorar filas repetidas y vacías (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Septiembre-2025boor | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Septiembre-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; ignorar filas repetidas y vacías (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Octubre-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; ignorar filas repetidas y vacías (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Noviembre-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; ignorar filas repetidas y vacías (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Diciembre-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; ignorar filas repetidas y vacías (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Dashboard Programas | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Dashboard Académico | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Julio | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Agosto | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Septiembre | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Octubre | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Noviembre | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Diciembre | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Detalle Presupuestado-Proyectad | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| TBL_INSCRITOS.xlsx | TBL_INSCRITOS | visible | usar | Hoja visible; una fila por inscripción individual (nov-2022 a may-2026); no es lista de leads | MARKETING |
| TBL_INSCRITOS.xlsx | BAJAS POR DUPLICADOS | hidden | ignorar | Oculta; sin filas de datos | - |

## 5. Pendientes que el contrato deja abiertos

- FU-L5: confirmar la regla del par texto/número en `DIPLOMADOS DOCENTE` y `CURSOS DOCENTE`.
- FU-L4: confirmar el diccionario de estados académicos (acentos y minúsculas).
- FU-L6: confirmar la lista de conflictos de meta 2025 con su diferencia.
- `MODULOS`: resuelto en FU-L1, queda como «usar».

