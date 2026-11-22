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
- **Etiquetas Likert:** se llevan a número con el diccionario `vocabularios.etiquetas` del YAML (FU-L5). Un 0 o «Sin Información» es NULL (DA1).

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
- `ci` ← `cedula de identidad` (1), `ci`, `carnet de identidad`, `documento de identidad` (2), `nro de ci` (3). FU-L4: un CI con complemento o ciudad en el texto (`4892019-1C`, `4892019 CBBA`, `4892019.0`) se separa en `ci_numero` y `ci_complemento` antes de la cascada de identidad; resuelve al mismo estudiante (estado A) que `4892019`.
- `pos` ← `pos - actas`
- `estado_academico` ← `estado academico` (1), `estado final`, `condicion academica`, `situacion academica` (2)
- `estado_tutoria` ← `estado tutoria` (1), `estado reprobado`, `estado de tutoria` (2). Puede traer Abandono o Deserción.
- `estado_arca` ← `estado arca` (1), `estado de titulacion` (2)
- `nota_modulo` ← patrón `^(nota )?(modulo|mod.?) ?\d{1,2}$`; el número de módulo sale de la cabecera.
- **Columnas no mapeadas:** `nombres`, `apellido paterno`, `apellido materno`, `pos-ci`, `comentarios`, `fecha emision arca`
- **Estados (FU-L4):** los tres estados se llevan a su nombre de catálogo (`cat_estado_*`) sin importar mayúsculas, acentos ni espacios (`reprobado` = `Reprobado`, `deserción` = `Deserción`, `abandono` = `Abandono`). Un estado fuera del catálogo no se descarta: se guarda como vino, la fila queda en revisión y se registra `VALOR_FUERA_DE_CATALOGO` (agregado). Vocabulario de deserción (`vocabularios.estado_desercion`): `DESERCION` y `ABANDONO`.
- **Resultado por módulo (DA-FU2, FU-L4):** cada celda de nota guarda `nota_final` (número de 0 a 100) y un `resultado` canónico: un número ≥ 70 es `APROBADO` y uno menor `REPROBADO`; el texto sale de `vocabularios.resultado_nota`: «Aprobó» → `APROBADO`; «No asistió», «Nunca ingresó», «Faltas y no envió»… → `INASISTENCIA`; «EXIMIDA» → `EXIMIDO`; «SIN NOTAS EN EL ACTA…» y «Aparece en ARCA pero no en el acta» → `SIN_NOTA` (en estos casos `nota_final` es NULL). Un **0** es `INASISTENCIA` (nota NULL) si el estado académico o de tutoría es Deserción o Abandono; si no, es un 0 real (nota 0, `REPROBADO`). Una celda vacía o «-» no genera hecho.
- **Reglas de calidad:** un número fuera de 0-100 (en el acta hay CI pegados) → nota NULL, fila a revisión y aviso `NOTA_FUERA_DE_RANGO`; un texto fuera del vocabulario (apellidos, comentarios) → nota NULL, fila a revisión y aviso `VALOR_FUERA_DE_CATALOGO`. Los avisos son agregados por documento y motivo y nunca publican el valor. El `CERO_COMO_INASISTENCIA` es informativo.
- **KPI que lee (campos canónicos, no la fuente):** KPI-07 = promedio de notas numéricas sin `INASISTENCIA`, `EXIMIDO` ni `SIN_NOTA` (un 0 real entra); KPI-08 = `APROBADO` / (`APROBADO` + `REPROBADO` + `INASISTENCIA`); KPI-16 (DA2-bis) = estudiantes con estado `DESERCION` o `ABANDONO` (académico o de tutoría) / matrícula de la gestión, desde cualquier fuente que traiga el estado; sin fuente con estado en la gestión, «sin dato» (nunca 0). `fact_rendimiento_academico.estado_de_fuente` distingue el estado de la fuente del que el cargador deduce de la nota.
- **Pueden venir vacías sin que sea error:** Estado de tutoría, comentarios y fecha de emisión pueden faltar. Una nota de módulo no cursado puede venir vacía. Del YAML: `comentarios`, `estado tutoria`.

### EVALUACION_DOCENTE

- **Granularidad:** Una fila por respuesta. Una columna por pregunta (docente o experiencia institucional).
- **Hojas oficiales (usar):** TBL EVALUACION DOCENTE ([BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx); TBL EXPERIENCIA UNIFRANZ ([BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx); DIP. EXP DOC. X MODULO (Evaluación Docente y Unifranz.xlsx); DIP. EXP UNIFRANZ (Evaluación Docente y Unifranz.xlsx); FINAL EXPERTOCURSO (Evaluación Docente y Unifranz.xlsx); DIPLOMADOS DOCENTE (Experiencia Docente 2.0.xlsx); CURSOS DOCENTE (Experiencia Docente 2.0.xlsx)
- **Hojas a ignorar de este tipo:** -
- **Cómo se reconoce (FU-L5, por contenido):** una hoja es una encuesta si al menos 3 de sus columnas traen respuestas tipo Likert del diccionario («5/Totalmente de acuerdo», «Satisfecho»…) en la mitad o más de sus celdas (`encuesta.clasificacion` del YAML). Un libro es EVALUACION_DOCENTE si esas hojas son la mitad o más de sus filas, aunque se suba como ACTA / CENTESIMAL_100 (el libro «Experiencia Docente 2.0» pasaba por acta porque su cabecera trae «promedio»). Una hoja de encuesta no se pasa por el adaptador de reportes de Moodle aunque comparta cabeceras («Dirección de correo»): ese adaptador tomaba la fila de grupos como cabecera.
- **Cabecera y escala o vocabulario:** Cabecera por contenido: fila 1 (encuestas ANTIGUO y Experiencia 2.0) o fila 2 con una fila de grupos arriba (DIP. EXP. DOC. X MODULO, DIP. EXP. UNIFRANZ, FINAL EXPERTOCURSO). Escala **por pregunta** (no por libro): 1-5 por defecto y 1-10 cuando la cabecera lo dice («escala del 1 al 10») o cuando los números sueltos de la columna son la mayoría de sus respuestas y pasan de 5; una etiqueta «n/Etiqueta» es siempre de 1-5; una columna con números por encima de 10 no tiene escala inferible (ESCALA_NO_INFERIBLE, sin respuesta). Experiencia 2.0 trae el 0 como «0/Sin Información» y dos columnas por pregunta (texto y número).
- **Columnas usadas → campo canónico:**
- `puntuacion` ← columna de pregunta puntuada, detectada por sus valores (el patrón `^(a )?\d+\. ` queda como sinónimo de cabecera numerada)
- `escala_max` ← `encuesta.escala` del YAML (cabecera, valores de la columna)
- `programa` ← `programa`, `programa pos`, `programa - pos`
- **Pares texto + número:** dos columnas de la misma pregunta («A 1. ¿…?» y «A 1. N°¿…?») son una sola respuesta; se lee la numérica y la otra no suma (`encuesta.pares`). Si falta la numérica, manda el diccionario. Las columnas calculadas («promedio docente») no son respuestas (`encuesta.columnas_derivadas`).
- **Diccionario de etiquetas** (`vocabularios.etiquetas` del YAML, editable): familias acuerdo, satisfacción, probabilidad, facilidad, calidad, utilidad y carga, cada una de 1 a 5; «Neutral» (3) vale en cualquier familia. Solo acuerdo, satisfacción y probabilidad pueden venir sin número («Satisfecho», «Muy probable»); «Excelente», «Bueno», «Útiles», «Adecuada»… solo valen escritas «n/Etiqueta» (sueltas son una palabra de un comentario).
- **Columnas no mapeadas:** `nombre completo del usuario`, `direccion de correo`, `grupos`, `fecha`, `modulo`, `numero del modulo`, `respuesta numero`
- **Tipo de pregunta (KPI-19 / KPI-20 / NPS):** por palabras del catálogo (`encuesta.tipo_pregunta`). NPS: las de recomendación («recomiende»); DOCENTE: las que nombran al docente; INSTITUCIONAL: plataforma, atención, soporte, administración, comunicación institucional, recursos tecnológicos. Una pregunta sin palabra clave toma el tipo de su hoja: institucional si ninguna pregunta de la hoja nombra al docente, docente si alguna lo hace.
- **Reglas de calidad (DA1):** cuenta solo `puntuacion` en [1, `escala_max`]; un 0, «Sin Información», un número fuera de escala, una etiqueta desconocida o una respuesta cruzada es NULL y no genera hecho (el NPS 0-10 es la excepción: allí el 0 vale y va aparte, fuera de KPI-19 y KPI-20). Cada caso queda en `log_inconsistencias` agregado por documento, hoja y pregunta, con el número de respuestas y un ejemplo que no publica texto libre: `SIN_INFORMACION` (informativo), `PUNTUACION_FUERA_DE_ESCALA`, `RESPUESTA_EN_COLUMNA_EQUIVOCADA` (etiqueta de otra familia, etiqueta de 1-5 en una pregunta de 1-10, texto de otra pregunta o una respuesta escrita en la columna del módulo), `VALOR_FUERA_DE_CATALOGO` y `ESCALA_NO_INFERIBLE`, estos cuatro a revisión. La vista `bi.vw_cmi_valores` (migración 025) aplica el mismo filtro.
- **Pueden venir vacías sin que sea error:** Comentarios, sugerencias y datos de contacto pueden faltar; el comentario con «0/Sin Información» es «sin comentario». La numérica de un par puede venir vacía si la pregunta es de comentario. Una hoja puede no traer nombre, correo ni fecha (solo agregados). Del YAML: `comentarios`.

### MARKETING

- **Granularidad:** Una fila por inscripción individual (nov-2022 a may-2026).
- **Hojas oficiales (usar):** TBL_INSCRITOS (TBL_INSCRITOS.xlsx)
- **Hojas a ignorar de este tipo:** -
- **Cabecera y escala o vocabulario:** Cabecera en fila 1. El género viene en cuatro formas (MUJER, Femenino, HOMBRE, Masculino) → catálogo `genero`.
- **Columnas usadas → campo canónico:**
- `programa` ← `nombre del programa`
- `pos` ← `numeroproyecto`, `numero proyecto`, `pos` (FU-L3: cada inscripción suma al programa de su fila)
- `fecha_inscripcion` ← `marca temporal`, `fecha de inscripcion` (FU-L3)
- `ci` ← `ci`
- `genero` ← `genero`, `genero l`
- **Columnas no mapeadas:** `nombres`, `paterno`, `materno`, `celular`, `correo electronico`, `direccion`, `nit`, `razon social`, `asesor`, `pos-ci incritos`
- **Reglas de calidad:** Esta fuente **no** tiene leads, así que no alimenta KPI-06 (DA6). Cada fila es una inscripción y suma 1 al programa (POS de su fila) y mes de su fecha de inscripción. FU-L3: el ×2 de la DW viva venía de que `fact_marketing` no guardaba el documento de origen: borrar el documento quitaba sus claves de idempotencia pero no sus inscripciones, y al volver a subir el libro se sumaban otra vez. Desde la migración 023 cada fila de inscripciones lleva su `id_documento` y el borrado la retira. Las dos claves por fila de `carga_fila_origen` (por archivo y por contenido) son por diseño: 30.392 = 2 × 15.196 no es duplicado.
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
- **Reglas de calidad:** Ejecutado 2023-2025 y meta 2025 en el resumen. Prioridad de `monto_meta` y `monto_ejecutado`: RENTABILIDAD > EGRESOS (DA-FU3, FU-L6): si esta fuente trae otra cifra para la misma categoría y mes, se carga la de RENTABILIDAD y el conflicto queda `CONFLICTO_FUENTES` resuelto por regla (informativo). Para `monto_egreso` y los costos por programa manda EGRESOS (la prioridad está en el catálogo, `prioridad_fuentes`).
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
- **Reglas de calidad:** Metas 2025 distintas entre archivos (7 de las 10 diferencias son exactas de 100.000): gana esta fuente y el conflicto se registra como `CONFLICTO_FUENTES` resuelto por regla (estado `RESUELTO_REGLA`, con los dos valores, la diferencia y la señal de múltiplo de 100.000 para avisar al área financiera; FU-L6, `fu_l6_conflictos_metas.csv`).
- **Granularidad de la meta (DA4, FU-L6):** el cargador marca cada meta `MENSUAL` o `ANUAL` por la FORMA de la hoja (no por el año): por categoría y año se cuentan los meses con meta; una sola celda es `ANUAL` y no se coloca como meta de ningún mes (`fact_rentabilidad.granularidad_meta`, migración 026); dos o más meses son `MENSUAL`; una hoja que solo cubre un mes se lee como mensual. Las columnas «año» (`monto_ejecutado`, `monto_meta` por año) y la columna de serie salen de `metas.columnas` y `metas.claves_categoria` del catálogo.
- **KPI que lee (FU-L6):** KPI-02 = último mes cerrado frente a la meta MENSUAL de ese mes (sin meta mensual: «sin dato», con el motivo «La fuente solo trae meta anual.» o «No hay meta cargada para esta gestión.»); KPI-03 = ejecutado de los meses cerrados frente a la meta de esos meses más la meta anual completa; KPI-13 y KPI-14 usan la meta anual (mensual + anual) y el ejecutado acumulado; KPI-12 compara los meses cerrados con los mismos de la gestión anterior. El mes de corte (último mes con ejecutado de toda la fuente) es parcial salvo diciembre y no cuenta en KPI-02, KPI-03 ni KPI-12.
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
- `leads_captacion` ← `leads`, `interesados`, `total interesados`, `prospectos` (FU-L3)
- `inscritos_captacion` ← `n inscritos`, `n de inscritos`, `inscritos`, `total inscritos` (FU-L3)
- `reservas` ← `reservas`, `total reservas`
- `anio_periodo` ← `ano`, `anio`, `gestion`, `ano ibp`, `anio ibp` · `mes_periodo` ← `mes`, `nombre mes`, `mes ibp` · `fecha_periodo` ← `fecha` (FU-L3: período de la fila; sin él se usa el de la hoja mensual, nunca la fecha de inicio del programa)
- **Columnas no mapeadas:** `costo programa`, `punto de equilibrio`, `estado`, `comentarios`, `comentario daf`, `p/ejecutado`, `p/asignado`, `tc (cliente externo)`
- **Reglas de calidad:** Leads e inscritos de captación (DA6, FU-L3): sumar por mes solo filas con ambos datos y 0 ≤ inscritos ≤ leads (una fila con leads y sin inscritos, o con más inscritos que leads, no cuenta). Las reservas se guardan en `fact_planificacion_programa.reservas_fuente` y no entran en el KPI. POS × mes en varias hojas: se cuenta una vez, con prioridad a la hoja de detalle mensual visible; la tabla por programa (IBP, con el mes en cada fila) solo aporta los POS y meses que el detalle no trae; las ocultas repetidas y los borradores no cuentan. Prioridades en `captacion.prioridad_origen` del YAML (1 detalle visible, 2 detalle oculto rescatado, 3 tabla por programa visible, 4 oculta). El resultado queda en `fact_marketing.leads_captacion` / `inscritos_captacion` (un recálculo, no una suma: recargar no duplica). Gestión sin leads → KPI-06 «sin dato» con motivo (desde qué mes hay datos) y cobertura mensual (meses con dato de 12) en el drill-down de Clientes. Otra hoja con leads e inscritos por programa y mes (de cualquier libro) se lee igual con solo añadir el sinónimo.
- **Pueden venir vacías sin que sea error:** Leads e inscritos vacíos en jul-dic 2026 (no hay ejecución cargada); no es error. Columnas de pauta y de digital pueden venir vacías. Del YAML: `comentarios`, `comentario daf`, `comentario digital / video solicitado`, `comentario admisiones`.

### Hojas sin tipo en este contrato

- `MODULOS` (catálogo de módulos con docente): **usada** (corrección de FU-L1). Produce las asignaciones módulo-docente que llenan `bridge_modulo_docente`, la única tabla puente de la DW. Sus columnas de contacto del docente no se publican en informes.

## 3. Prioridad de fuentes por campo (DA-FU3)

| Campo | Prioridad |
|---|---|
| `monto_meta`, `monto_ejecutado` | RENTABILIDAD > EGRESOS |
| `monto_egreso`, costos | EGRESOS > RENTABILIDAD |

Un conflicto entre dos fuentes de DISTINTO tipo para el mismo campo, categoría y mes se resuelve con esta regla (llegue primero o después) y se registra como `CONFLICTO_FUENTES` con estado `RESUELTO_REGLA` (informativo, no pendiente; FU-L6). Un hueco (vacío o 0) de la fuente prioritaria lo llena la otra sin conflicto. Dos fuentes del MISMO tipo con valores distintos no tienen regla: el conflicto queda `PENDIENTE`. La prioridad es del catálogo (`prioridad_fuentes`); cambiar el orden allí cambia quién gana sin tocar código.

## 4. Hojas (62): decisión y motivo

Criterio: las 62 hojas tienen decisión (usar o ignorar) con motivo. «DIP. EXP DOC. X MODULO» e «IBP» se marcan usar, como pide el plan.

| archivo | hoja | estado | decisión | motivo | tipo |
|---|---|---|---|---|---|
| [BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx | TBL EVALUACION DOCENTE | visible | usar | Hoja visible de respuestas 1-5 con texto 'n/Etiqueta'; cabecera en fila 1 | EVALUACION_DOCENTE |
| [BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx | TBL EXPERIENCIA UNIFRANZ | visible | usar | Hoja visible con respuestas cruzadas entre preguntas (RESPUESTA_EN_COLUMNA_EQUIVOCADA, agrupadas) y 1-5 con 1-10; se lee con las reglas de FU-L5 | EVALUACION_DOCENTE |
| [BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx | Análisis de Evaluación | visible | ignorar | Resumen con 254 fórmulas de agregado sobre la tabla de respuestas (129 filas); no es fuente de respuestas | - |
| Base centralizada Académica ARCA (1).xlsx | ACTAS DE NOTAS | visible | usar | Hoja visible; una fila por estudiante y programa; cabecera en fila 1; estado académico y notas por módulo | ACTA |
| Base centralizada Académica ARCA (1).xlsx | MODULOS | visible | usar | Alimenta `bridge_modulo_docente` (corregido en FU-L1; las columnas de contacto no se publican) | ACTA |
| Base centralizada Académica ARCA (1).xlsx | Tabla dinámica 1 | visible | ignorar | Tabla dinámica vacía (0 filas) | - |
| Base centralizada Académica ARCA (1).xlsx | PROGRMAS  DE BAJA | visible | ignorar | Una sola fila de datos; notas de criterio de baja sin granularidad de fuente | - |
| Base centralizada Académica ARCA (1).xlsx | IBP | visible | usar | Excepción del plan (DA6): tabla por programa con el mes en cada fila (POS - IBP, MES IBP, AÑO IBP); aporta leads e inscritos de captación solo donde la hoja mensual de detalle no trae el programa y mes (FU-L3); cabecera en fila 1 | PLANIFICACION |
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
| Evaluación Docente y Unifranz.xlsx | DIP. EXP DOC. X MODULO | visible | usar | Evaluación por módulo 2025-11 a 2026-05; por contenido es una encuesta (FU-L5) y deja de descartarse; cabecera en fila 2 | EVALUACION_DOCENTE |
| Evaluación Docente y Unifranz.xlsx | DIP. EXP UNIFRANZ | visible | usar | Hoja visible con mezcla de escalas (1-5 y 1-10) y etiquetas en columna equivocada; se usa con reglas de FU-L5 | EVALUACION_DOCENTE |
| Evaluación Docente y Unifranz.xlsx | FINAL EXPERTOCURSO | visible | usar | Hoja visible con etiquetas sin número ('Satisfecho', 'Probable'); se usa con diccionario de FU-L5 | EVALUACION_DOCENTE |
| Experiencia Docente 2.0.xlsx | CURSOS DOC 1 | hidden | ignorar | Oculta; versión previa del curso | - |
| Experiencia Docente 2.0.xlsx | DIPLOMADOS DOCENTE | visible | usar | Hoja visible con dos columnas por pregunta (texto y número) y «0/Sin Información» explícito; se lee solo la numérica y el 0 es NULL (DA1) | EVALUACION_DOCENTE |
| Experiencia Docente 2.0.xlsx | CURSOS DOCENTE | visible | usar | Hoja visible con dos columnas por pregunta; identificación (nombre, correo, fecha) 100 % vacía; el 0 es NULL (DA1) | EVALUACION_DOCENTE |
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
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Enero-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; leads e inscritos por programa y mes de captación, KPI-06 (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Febrero-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; leads e inscritos por programa y mes de captación, KPI-06 (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Marzo-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; leads e inscritos por programa y mes de captación, KPI-06 (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Abril-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; leads e inscritos por programa y mes de captación, KPI-06 (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Mayo-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; leads e inscritos por programa y mes de captación, KPI-06 (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Junio-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; leads e inscritos por programa y mes de captación, KPI-06 (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Julio-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; leads e inscritos por programa y mes de captación, KPI-06 (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Agosto-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; leads e inscritos por programa y mes de captación, KPI-06 (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Septiembre-2025boor | hidden | ignorar | Oculta (hidden); borrador, copia, resumen o duplicado de otra hoja; no se usa | - |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Septiembre-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; leads e inscritos por programa y mes de captación, KPI-06 (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Octubre-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; leads e inscritos por programa y mes de captación, KPI-06 (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Noviembre-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; leads e inscritos por programa y mes de captación, KPI-06 (FU-L3) | PLANIFICACION |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | Diciembre-2026 | visible | usar | Hoja mensual visible 2026 con LEADS, N° INSCRITOS y RESERVAS; leads e inscritos por programa y mes de captación, KPI-06 (FU-L3) | PLANIFICACION |
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
- FU-L6: resuelto. La lista de conflictos de meta con su diferencia está en `docs/mediciones/fu_l6_conflictos_metas.csv`.
- `MODULOS`: resuelto en FU-L1, queda como «usar».



---

## Texto heterogéneo admitido (DF-L11)

Se admite como entrada heterogénea cualquier archivo `.xlsx`, `.xls` o `.csv` que contenga:
1. **Tablas con encabezados desplazados o columnas en otro orden:** se normalizan vía `asymmetric_flattener.py` y `cat_mapeo_columna` (sin listas fijas de cabeceras).
2. **Comentarios mezclados con datos o texto narrativo largo:** cada bloque se serializa al contrato de texto plano (`col: val | ...` o texto libre) sin descartar silenciosamente.
3. **Bloques u hojas sin cabecera reconocible:** el motor PLN/NER (`extract_entities_from_line` + BETO IOB2) muestra en el paso ② qué normalizó y qué entidades reconoció; **nunca** carga como hecho en el DW lo que carece de estructura tabular o identidad verificada, derivándolo a revisión humana con su motivo explícito.
