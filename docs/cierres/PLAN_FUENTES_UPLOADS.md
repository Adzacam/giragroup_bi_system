# PLAN FUENTES (FU) — Evaluación de `uploads/data` y corrección del flujo — 2026-11-20

**Objetivo:** saber qué contiene cada uno de los 10 libros fuente, compararlo con lo que hoy muestran la DW y la web (`PLAN_AUDITORIA_DW.md`) y planificar las correcciones hasta que el pipeline, BETO y la revisión humana (back y front) muestren lo correcto.

**Entrada:**
- `PLAN_AUDITORIA_DW.md`, con DA1–DA3 resueltas y DA4, DA6 y DA7 diferidas.
- Rama `beto-integracion` `38e317f`.

**Método:**
- Perfil de solo lectura con `openpyxl` + `pandas` de las 61 hojas: estado visible u oculto, celdas combinadas, fórmulas, fila de cabecera, nulos, tipos mezclados, rangos, variantes de texto, subtotales y duplicados.
- Cruce de agregados de la fuente con la DW viva.
- **Límite de este análisis:** el perfil leyó los archivos directamente, sin pasar por el lector, la clasificación ni el mapeo del sistema. Las causas de la sección 1 (cartera, inscritos duplicados, encuestas) se dedujeron del código y de la DW, no se reprodujeron. **FU-L0b** lo comprueba antes de corregir.
- **Sin PII:** nombres, CI, correos y celulares solo se describen con conteos.
- El script quedó en el scratchpad de la sesión. En **FU-L0** se pasa a `scripts/auditoria_fuentes/perfil_fuentes.py` y su salida a `docs/mediciones/fu_l0_perfil.json`.

---

## PARTE 1 — Qué tiene cada archivo

Leyenda: 🔴 error que hoy distorsiona la DW o la web · 🟠 dato sucio que el pipeline debe tolerar · 🟡 observación.

### 1. `BD Cobranzas.xlsx`: COBRANZA (doc 36)

| Hoja | Estado | Filas × cols | Qué es |
|---|---|---|---|
| COBRANZAS 2024 2025 | visible | 10.017 × 78 | **Una fila por estudiante y programa:** programa, asesor, CI, contacto, facturas, días de mora, tipo de inscripción, **TIPO DE CARTERA**, costo, descuento, deuda total, cuotas, **36 columnas mensuales `MONTO <MES> <AÑO>`** (ene-2024 a dic-2026), total pagado, estado académico y ARCA, **TOTAL CUOTAS EN MORA**, RANGO MORA y 7 columnas «(PRELIMINAR)». 197.065 fórmulas |
| Copia de COBRANZAS 2024 2025 | **oculta** | 5.478 × 51 | Copia antigua de la hoja principal |
| Hoja 4 / Hoja 8 / Hoja 12 | visible | 516 / 7 / 18 | Tablas auxiliares y dinámicas: 48 filas duplicadas y 11 cabeceras sin nombre |

**Problemas:**
- 🔴 **Cartera mal mapeada.** La fuente dice CERRADA 9.268 (92,5 %), VIGENTE 441, INCOBRABLE 165, PREVISIONABLE 69, EN MORA **36**. La DW guarda «Mora» en **7.193** filas. El cargador hace `"MORA" in estado → "Mora"` y, si no hay estado, `cuotas>0 → Mora` (`dw_loader.py:1543`). Además `ingestion_service` asigna la cabecera `mora` a `cuotas_impagas`, y en esta hoja hay tres columnas con «MORA» (DIAS DE MORA, RANGO MORA y TOTAL CUOTAS EN MORA). **Esta es la causa raíz de KPI-05 ≈ 94 % y KPI-15 ≈ 99 %.**
- 🔴 **Cuotas en mora perdidas en 2024.** La fuente tiene `TOTAL CUOTAS EN MORA ≥ 2` en 369 / 809 / 643 filas para 2024 / 2025 / 2026 (por año de inicio). La DW tiene **1 / 580 / 869**. *Corrige el hallazgo A3-bis del plan anterior: 2024 sí trae el dato y el que lo pierde es el ETL.*
- 🔴 **Pagos asignados al año equivocado.** Pagos mensuales de la fuente: 8.071.737 / 12.422.501 / 4.841.944 Bs (2024 / 25 / 26). `monto_pagado` en la DW: ≈ 7,27 M / 13,05 M / 5,84 M. La DW suma 26,17 M, frente a 25,34 M de `TOTAL PAGADO` (**+0,83 M, ~3 %**, que pueden ser duplicados de la hoja oculta). El año del hecho sale de la fecha de inicio, no del mes del pago.
- 🟠 Contradicción interna: 1.518 filas «CARTERA CERRADA» tienen `TOTAL CUOTAS EN MORA` de 2 o 3. Es una fórmula o un histórico desactualizado; la regla DA3 (≥ 2 cuotas) las contaría.
- 🟠 Datos sucios: `TOTAL CUOTAS EN MORA` negativa en 428 filas (−5…) y con texto `1s`; `DEUDA TOTAL` negativa en 629 (sobrepago); `DIAS DE PAGO PENDIENTE` hasta 665.105 y texto «En curso»; `TOTAL DE CUOTAS` = «2 días» (4); `NUMERO FACTURA` con «fd» y fechas; `FECHA FIN DIPLOMADO` con año **0205** (30 fuera de rango); CELULAR con 3.667 textos.
- 🟡 Las columnas de jun–dic 2026 están 100 % vacías: los datos llegan a **mayo de 2026**, lo que explica el mes parcial del KPI-02.

### 2. `Base centralizada Académica ARCA (1).xlsx`: ACTA (doc 43)

| Hoja | Estado | Filas × cols | Qué es |
|---|---|---|---|
| ACTAS DE NOTAS | visible | 8.660 × 26 | **Una fila por estudiante y programa:** POS, CI, mes y año de inicio (**solo 2024 y 2025**), nombres, notas `MÓDULO 1…12` en formato ancho, ESTADO ACADÉMICO, ESTADO TUTORÍA, ESTADO ARCA, fecha de emisión y POS-CI. 8.663 fórmulas |
| MODULOS | visible | 2.030 × 17 | Catálogo de módulos con docente, horas, pago, contacto y residencia |
| IBP | visible | 748 × 23 | Planificación por POS: escuela, inversión, punto de equilibrio, modalidad, estado, metas, **LEADS y N° DE INSCRITOS** (solo 2026) |
| CRITERIOS / PROGRMAS DE BAJA | visible | 15 / 1 | Notas de criterio |
| Tabla dinámica 1 / Hoja 8 | visible | **vacías** | — |

**Problemas:**
- 🔴 **La deserción sí existe en la fuente.** `ESTADO ACADEMICO = Deserción` aparece 313 veces (2024) y 176 (2025), más «Abandono» en ESTADO TUTORÍA (269). Da ≈ **6,5 % (2024)** y **4,5 % (2025)**. *Esto reabre DA2: el KPI-16 no necesita asistencia.*
- 🔴 **Notas con texto y valores fuera de rango.** En las columnas de módulo hay textos: «SIN NOTAS EN EL ACTA…», «No asistió a clases», «EXIMIDA», «Aprobó», apellidos («LOZADA», «FERNANDEZ», «MARIA YNES») y un **13.622.300** en MÓDULO 4 (probablemente una CI). Además hay 2.968 notas en 0 (deserción o inasistencia) que bajan el promedio del KPI-07; hay que decidir si un 0 por inasistencia cuenta como nota.
- 🟠 Estados escritos de varias formas: «Reprobado/reprobado», «Deserción/deserción», «No titulado/no titulado», «Abandono/abandono».
- 🟠 CI con complemento o ciudad en texto (34 casos: `-1C`, ` CBBA`, ` CH`), con un mínimo de 6.835 que es dudoso; nombres con dígitos u espacios dobles (125).
- 🟠 MODULOS: `FECHA INICIO` desde **2005** y hasta **3035**; `HRS MODULO` = «SIN INFORMACION»; TIPO DE PROGRAMA en mayúsculas y minúsculas mezcladas.
- 🟠 IBP: `INVERSION DEL PROGRAMA` como texto «Bs 5.000,00» (62); `GASTOS` = «N/A»; TIPO DE PROGRAMA «Diplomado/DIPLOMADO»; las celdas META 2025 y 2027 están sueltas en la tabla.
- 🔴 **Hojas descartadas sin revisión:** «IBP» (748 filas) quedó como `LINEA_SIN_ENTIDAD` y no se cargó, aunque es la única fuente de leads 2026 junto con Planificación.

### 3–5. Encuestas: `[BBDD] ANTIGUO…` (doc 40), `Evaluación Docente y Unifranz` (doc 41), `Experiencia Docente 2.0` (doc 42)

| Archivo :: hoja | Estado | Filas | Escala | Observación |
|---|---|---|---|---|
| ANTIGUO :: TBL EVALUACION DOCENTE | visible | 16.451 × 20 | texto «n/Etiqueta» 1–5 | 7.265 celdas combinadas, 748 duplicadas; respuestas escritas en la columna «Módulo» («4/De acuerdo»…) |
| ANTIGUO :: TBL EXPERIENCIA UNIFRANZ | visible | 2.539 × 17 | 1–5 + 1–10 | **Respuestas cruzadas:** una pregunta de satisfacción contiene «5/Totalmente de acuerdo» y el texto de otra pregunta como valor |
| Unifranz :: **DIP. EXP DOC. X MODULO** | visible | **4.095** (3.250 respuestas) | 1–5 y 1–10 | 🔴 **Descartada entera** como `LINEA_SIN_ENTIDAD` (10.351 líneas): es la evaluación por módulo 2025-11 → 2026-05 |
| Unifranz :: DIP. EXP UNIFRANZ | visible | 516 (285 respuestas) | mezcla | Etiquetas de otra escala en la columna equivocada («4/Fácil» en «valor del programa»); mezcla 1–10 con 1–5 |
| Unifranz :: FINAL EXPERTOCURSO | visible | 275 | mezcla | Etiquetas **sin número** («Satisfecho», «Probable», «Neutral») y números 8/9 en una pregunta de 1–5 |
| Exp 2.0 :: DIPLOMADOS DOCENTE | visible | 14.397 × 43 | 0–5 | Cada pregunta trae dos columnas (texto + número). **«0/Sin Información» explícito:** 12.604 en la P8, 13.726 en la P14, 12.807 en la P15 y P16. 227.596 fórmulas |
| Exp 2.0 :: CURSOS DOCENTE | visible | 828 × 38 | 0–5 | **Sin nombre, correo ni fecha** (100 % vacío); «0/Sin información» en 733 de 828 |
| Exp 2.0 :: CURSOS DOC 1 / DIPLOMADOS DOC 2 | **ocultas** | 994 / 1.476 | — | Versiones previas, descartadas (bien) |

**Conclusiones:**
- 🔴 **El 0 es «Sin Información» de forma literal**, lo que confirma DA1 (0 → NULL). Al leer las dos columnas texto + número, la DW **duplica** cada respuesta (claves de `carga_fila_origen` ≈ 2× los hechos) y además carga los 0.
- 🔴 El doc 42 está tipificado como **ACTA / CENTESIMAL_100**. Debería ser EVALUACION_DOCENTE con escala 1–5 (y 1–10 en las preguntas NPS).
- 🔴 La hoja principal del doc 41 (la más reciente, de 2025-11 a 2026-05) **no está en la DW**, así que KPI-19 y KPI-20 de 2026 salen de una muestra parcial.
- 🟠 Hacen falta un **diccionario de etiquetas** (De acuerdo, Satisfecho, Útiles, Fácil, Probable, Adecuada…) y una regla para las etiquetas sin número.

### 6. `TBL_INSCRITOS.xlsx`: MARKETING (doc 44)

| Hoja | Estado | Filas × cols | Qué es |
|---|---|---|---|
| TBL_INSCRITOS | visible | 15.196 × 37 | **Una fila por inscripción** (nov-2022 → may-2026): proyecto, programa, asesor, CI, datos personales, institución, nivel académico, NIT, tipo de inscripción, estado (ACTIVO 15.171), género, edad y rango de edad |
| BAJAS POR DUPLICADOS | oculta | 0 filas | Solo cabecera |

**Problemas:**
- 🔴 **Inscritos duplicados ×2 en la DW.** Inscripciones de la fuente por año: 3.551 / 4.563 / 4.737 / 2.292 (2023–2026). `fact_marketing.inscritos` en la DW: **7.102 / 9.124 / 9.472 / 4.576**, exactamente el doble (y `carga_fila_origen` = 30.392 ≈ 2 × 15.196). Esto infla el KPI-21 y la matrícula de Clientes en la web.
- 🔴 **No tiene leads.** Es una tabla de inscritos, no de interesados: KPI-06 no puede salir de aquí (ver §8).
- 🟠 GÉNERO en cuatro formas (MUJER / Femenino / HOMBRE / Masculino); `EDAD L` de 0 a **127** (31 en cero); `RANGO EDAD` «No hay datos» en 1.505; CELULAR con 3 negativos y 5.980 textos; NIT con texto («-», nombres de empresa); TIPO DE INSCRIPCIÓN con dos vocabularios («INSCRIPCION NUEVO» / «Inscripción a nuevo programa»); 4 columnas `… L` 100 % vacías.

### 7. `BD Egresos.xlsx`: EGRESOS (doc 39) · 8. `EJECUTADO VS META.xlsx`: RENTABILIDAD (doc 38)

| Archivo :: hoja | Filas | Qué es |
|---|---|---|
| Egresos :: egresos | 1.373 × 15 | Egreso anterior, egreso real, ingreso y rentabilidad por POS (en Bs y USD, tipo de cambio 6,86) |
| Egresos :: Gestiones | 24 × 8 | Ejecutado 2023 / 2024 / 2025 y meta 2025 por mes y tipo (programas / techos) |
| Egresos :: acumulados | 12 × 6 | Lo mismo, **como texto** «Bs1.171.260» |
| EjVsMeta :: EJECUTADO | 24 × 21 | Ejecutado 2023–2026 por mes y categoría; **META POR CATEGORÍA 2024 = una sola celda (10.719.694)**; meta 2025 y 2026 **mensuales**; EBITDA; META 2026 = 1.627.619,5 × 12 meses; 2 columnas sin nombre con residuos de redondeo (−9,3e-10) |
| EjVsMeta :: GESTIONES | 12 × 6 | Totales mensuales como texto «Bs…» mezclado con números |

**Conclusiones:**
- 🔴 **DA4 queda respondida por la fuente: 2024 no tiene meta mensual.** Solo existe el total anual 10.719.694 en una celda. La DW lo cargó en diciembre. **No existe meta 2023.**
- 🔴 **Metas 2025 distintas entre archivos** (por ejemplo, abril: 1.098.653 en la DW frente a 1.198.653 en Egresos::acumulados; julio: 1.158.082 frente a 1.258.082). Una diferencia exacta de 100.000 apunta a un error de tipeo en uno de los dos, y es el origen de los 10 `CONFLICTO_FUENTES`.
- 🟠 Egresos: `INGRESO` con una fecha (año 2580); 64 rentabilidades negativas; TIPO DE PROGRAMA mezcla estados («CERRADO», «CERRADO JEA») con tipos.
- 🟡 La ejecución 2026 llega a mayo (252.233 Bs, parcial). Las metas jun–dic 2026 están cargadas, pero no la ejecución.

### 9. `BD Techos.xlsx`: TECHOS (doc 37)
- 207 × 18 (una hoja), con techos de convenio 2022–2025, coordinación, institución (24), POS, programa, estado de pago, N° de inscritos y certificados.
- 🟠 POS «4924B»; `Fecha Inicio` en **2034**; nombre de institución en dos formas («ECOGUZ»); 40,6 % sin `id_institucion`.
- 🟡 Alimenta el KPI-22. Coherente con la DW (93 en 2023 sale de las 11 filas de 2023).

### 10. `PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR'S).xlsx`: PLANIFICACION (doc 1)
- **32 hojas** (13 ocultas): una hoja por mes, de Julio-2025 a Diciembre-2026 (con borradores «Julio-2025 borrador» y «Septiembre-2025boor»), Centralizado_Mensual (oculta), Programas Notificados (1.045 × 30), Informe Gestión, 2 Dashboards y 6 hojas mensuales antiguas.
- 🔴 **Sí tiene LEADS e inscritos por programa** en las hojas mensuales (columnas `LEADS`, `N° INSCRITOS`, `RESERVAS`):

  | Hoja | Leads | Inscritos |
  |---|---|---|
  | Jul-2025 | 5.104 | 356 |
  | Ago-2025 | 4.549 | 202 |
  | Ene-2026 | 9.958 | 278 |
  | Mar-2026 | 7.011 | 250 |
  | Jun-2026 | 3.398 | 17 |
  | Jul–Dic-2026 | vacías | vacías |

  **Esto responde DA6:** el KPI-06 se puede calcular desde jul-2025 (≈ 3–7 %). Hoy el lector solo toma la planificación (KPI-23).
- 🟠 `Junio-2026` y `Diciembre-2026` tienen unas 1.000 filas, de las que 970 y 995 son vacías o duplicadas (formato arrastrado). Hay 9–34 subtotales por hoja, `COSTO PROGRAMA` como texto «Bs 4.300,00» o «-», el nombre de una asistente en dos formas, `Duración` = «2 días» y 6 columnas de pauta 100 % vacías.
- 🟠 **Se repite en hojas ocultas:** el pipeline debe ignorar las hojas ocultas y los borradores (`*borrador`, `*boor`, `Centralizado_*`) para no duplicar.

---

## PARTE 2 — Lo que la web muestra y lo que debería mostrar

| Tema | Web/DW hoy | Lo que dice la fuente | Corrige |
|---|---|---|---|
| KPI-05 / 15 Mora | 94 % / 85–99 % | Cartera en mora o previsionable < 2 %; ≥ 2 cuotas: 369 / 809 / 643 filas | FU-L2 |
| KPI-21 / Clientes Inscritos | 2× real | 3.551 / 4.563 / 4.737 / 2.292 | FU-L3 |
| KPI-06 Conversión | sin dato | leads + inscritos jul-2025 → jun-2026 (Planificación) e IBP 2026 | FU-L3 (DA6) |
| KPI-16 Deserción | 0 % (y DA2 lo pasaba a «sin dato») | ESTADO ACADÉMICO «Deserción»: 6,5 % / 4,5 % | FU-L4 (**reabre DA2**) |
| KPI-07 Promedio | 78,8 / 79,0 | Incluye 2.968 ceros por inasistencia y notas-texto | FU-L4 (DA-FU2) |
| KPI-19 / 20 Satisfacción | 58–67 % / 12–22 % | «0/Sin Información» explícito; hoja principal del doc 41 sin cargar | FU-L5 |
| KPI-02 Meta 2024 | 6,25 % | No hay meta mensual 2024 | FU-L6 (DA4) |
| Metas 2025 | — | Diferencias exactas de 100.000 entre archivos | FU-L6 |
| Pagos por año | 7,27 / 13,05 / 5,84 M | 8,07 / 12,42 / 4,84 M (por mes de pago) | FU-L2 |

---

## PARTE 3 — Plan de corrección por loops

| Loop | Sección | Capa | Agente | Depende de | Paralelo con | Cambia cifras |
|---|---|---|---|---|---|---|
| FU-L0 | Perfil reproducible + contrato por fuente | scripts + docs | `dev-baja` | — | — | No |
| FU-L0b | **Tres vías** sobre una copia de los 10 archivos: (a) lo que tiene el archivo (perfil), (b) lo que devuelve el lector y el mapeo actuales del sistema, (c) lo que queda en la DW tmpfs. Confirma o descarta cada causa de la sección 1 | back (pipeline, solo lectura) | `dev-media` | FU-L0 | — | No (diagnóstico). Salida: `fu_l0b_tres_vias.csv` por hoja y campo |
| FU-L1 | Lector: hojas ocultas o borrador, cabecera, subtotales y filas fantasma | back (pipeline) | `dev-alta` | FU-L0 y FU-L0b | — | Sí (menos duplicados) |
| FU-L2 | Cobranza: cartera, cuotas en mora y pagos por mes | back (dw_loader, mapeo) | `dev-alta` | FU-L1 + DA3 | FU-L4, FU-L5 | **Sí** (KPI-01, 04, 05, 15) |
| FU-L3 | Inscritos ×2 + KPI-06 desde Planificación e IBP | back | `dev-media` | FU-L1 (DA6 resuelta) | FU-L2 | **Sí** (KPI-06, 21) |
| FU-L4 | ARCA: notas-texto, ceros, estados normalizados y deserción | back | `dev-media` | FU-L1 (DA2-bis y DA-FU2 resueltas) | FU-L2 | **Sí** (KPI-07, 08, 16) |
| FU-L5 | Encuestas: tipo, escala, diccionario de etiquetas, doble columna y hoja doc 41 | back + BETO | `dev-alta` | FU-L1 + DA1 | FU-L2 | **Sí** (KPI-19, 20) |
| FU-L6 | Metas: 2024 sin mensual, conflicto de 100.000 y mes parcial | back + vistas | `dev-media` | FU-L0 (DA4 y DA-FU3 resueltas) | FU-L2–L5 | **Sí** (KPI-02, 03, 12, 13, 14) |
| FU-L7 | Revisión humana: motivos nuevos y bandeja que explica por qué | back + front | `dev-media` | FU-L2–L5 | — | KPI-18 |
| FU-L8 | Front DataOps: vista previa por hoja (incluida / ignorada y por qué) y BETO | front | `dev-media` + `/frontend-design` | FU-L1, FU-L7 | — | No |
| FU-L9 | Recarga completa del lote en tmpfs + remedición + recongelado | todo | `dev-alta` | FU-L1–L8 | — | Recongela |

### FU-L0 — Perfil reproducible y contrato de fuentes (`dev-baja`)
- Pasar el script de perfil a `scripts/auditoria_fuentes/perfil_fuentes.py` (sin PII) y guardar la salida en `docs/mediciones/fu_l0_perfil.json`.
- **Según el principio rector:** el contrato describe **tipos de fuente y campos canónicos**, no archivos. Los 10 libros solo sirven de ejemplo. El resultado ejecutable es el catálogo de sinónimos (`cat_mapeo_columna` o `config/mapeo_fuentes.yaml`) y los vocabularios `cat_*`.
- Escribir `docs/fuentes/CONTRATO_FUENTES.md` con, para cada **tipo de fuente** (ejemplificado con su archivo actual):
  - tipo de fuente, hoja oficial y hojas a ignorar;
  - fila de cabecera y columnas que se usan, con su campo canónico;
  - granularidad (fila = estudiante×programa, respuesta, mes…), escala y vocabulario permitido;
  - qué columnas pueden venir vacías sin que sea error (punto 4 de tu lista).
- Criterio: las 61 hojas tienen una decisión («usar» o «ignorar» + motivo).

### FU-L1 — Lector robusto (`dev-alta`)
- Ignorar las hojas `hidden` y los nombres `*borrador*`, `*boor*`, `Copia de *`, `Hoja \d+`, `Tabla dinámica*`, `Dashboard*` y `Centralizado_*`, salvo que el contrato diga otra cosa. Registrar cada una como `HOJA_IGNORADA` con su motivo, en vez de `LINEA_SIN_ENTIDAD` × N líneas.
- **Sacar del descarte** las hojas válidas «DIP. EXP DOC. X MODULO» e «IBP».
- Cortar las filas fantasma (Jun- y Dic-2026: más de 970 filas vacías) y los subtotales.
- Leer el valor guardado de las celdas con fórmula; avisar si una celda con fórmula no tiene valor.
- Criterio: tests con un libro sintético (oculta, borrador, subtotal, filas fantasma). Ninguna hoja descartada en silencio.

### FU-L2 — Cobranza (`dev-alta`)
- **Mapeo explícito por contrato** (nada de «contiene MORA»):
  - `TIPO DE CARTERA` → `estado_cartera_fuente` (CERRADA, VIGENTE, EN MORA, PREVISIONABLE, INCOBRABLE);
  - `TOTAL CUOTAS EN MORA` → `cuotas_impagas` (negativo → 0 + aviso; texto «1s» → 1 + aviso);
  - `DIAS DE MORA` → días (nunca a `cuotas_impagas`).
- **Mora = `cuotas_impagas ≥ 2`** (DA3), con la misma regla en la vista y en el servicio.
- **Pagos por mes:** cada columna `MONTO <MES> <AÑO>` va a su `id_tiempo`. Las «(PRELIMINAR)» se excluyen.
- `DEUDA TOTAL` negativa → sobrepago (0 de deuda + aviso).
- Criterios:
  - la suma de pagos por año en la DW es igual a la de la fuente (8.071.737 / 12.422.501 / 4.841.944);
  - la cantidad de estudiantes con ≥ 2 cuotas por año es igual a la fuente;
  - salida: `fu_l2_cobranza_fuente_vs_dw.csv`.

### FU-L3 — Inscritos y conversión (`dev-media`) · DA6
- Encontrar por qué cada inscripción suma 2 (doble paso por `FactMarketing` en `dw_loader.py:~1500` y doble clave en `carga_fila_origen`). Garantizar 1 inscripción = 1.
- **KPI-06** (según DA6): leads e inscritos por mes desde las hojas mensuales de Planificación (jul-2025 → jun-2026) e IBP 2026 hacia `fact_marketing.leads_captacion` / `inscritos_captacion`.
- Criterios: inscritos por año en la DW iguales a la fuente; KPI-06 recalculado por mes. Salida: `fu_l3_inscritos_conversion.csv`.

### FU-L4 — ARCA (`dev-media`) · DA2-bis, DA-FU2
- Las notas en texto (comentarios, «EXIMIDA», apellidos) se convierten en NULL con motivo; «Aprobó» se trata según DA-FU2; un valor mayor que 100 se descarta como `NOTA_FUERA_DE_RANGO` y va a revisión.
- Estados normalizados (minúsculas y acentos) a un catálogo: Aprobado, Reprobado, Deserción, Participó, En curso, Abandono, Insuficiencia académica.
- **KPI-16** = estudiantes con estado Deserción o Abandono sobre la matrícula, si se aprueba DA2-bis.
- CI con complemento o ciudad: se separan en `ci_numero` y `ci_complemento` (las columnas ya existen en `dim_estudiante`).
- Criterio: conteo de estados de la DW igual al de la fuente por año. Salida: `fu_l4_arca_fuente_vs_dw.csv`.

### FU-L5 — Encuestas (`dev-alta`)
- Clasificar el doc 42 como `EVALUACION_DOCENTE`.
- Leer **solo la columna numérica** cuando la pregunta trae dos (texto y número), para no duplicar.
- Diccionario de etiquetas → número para 1–5. Las etiquetas sin número se mapean por diccionario. Un 0, «Sin Información» o un valor fuera de escala se guardan como NULL (DA1).
- Las preguntas 1–10 se guardan con `escala_max = 10`. NPS queda aparte.
- Cargar «DIP. EXP DOC. X MODULO» (doc 41).
- Las respuestas cruzadas entre columnas (etiqueta de otra escala) se marcan con `RESPUESTA_EN_COLUMNA_EQUIVOCADA` y van a revisión **agrupadas**, no fila por fila.
- Criterio: 0 puntuaciones fuera de [1, escala]; respuestas cargadas = respuestas válidas de la fuente. Salida: `fu_l5_encuestas_fuente_vs_dw.csv`.

### FU-L6 — Metas (`dev-media`) · DA4, DA-FU3
- 2024 se trata según DA4: ahora se sabe que **no hay meta mensual**, así que la recomendación es excluir 2024 del KPI-02 y mantenerlo en KPI-03 y KPI-13 como meta anual.
- 2023 sin meta queda «sin dato».
- Conflicto 2025 (EjVsMeta frente a Egresos, diferencias de 100.000): Lean elige el archivo de verdad (DA-FU3) y los 10 `CONFLICTO_FUENTES` se cierran con esa regla.
- Mes parcial: KPI-02 toma el último mes cerrado, con fecha de corte de la fuente = mayo 2026.

### FU-L7 — Revisión humana con sentido (`dev-media`)
- **Motivos nuevos:** `HOJA_IGNORADA` (informativo, no va a la bandeja), `NOTA_FUERA_DE_RANGO`, `RESPUESTA_EN_COLUMNA_EQUIVOCADA`, `CUOTAS_NEGATIVAS`, `CONFLICTO_META`.
- La bandeja agrupa por patrón y por hoja de origen y muestra **por qué** cada caso está ahí: regla, umbral y valor de la fuente.
- Las filas vacías o de confianza 0 se descartan automáticamente.
- La aprobación en bloque no cuenta como corrección (ver ADW-L8).
- Criterio: cada pendiente tiene un motivo documentado; tests.

### FU-L8 — Front DataOps (`dev-media`) · `/frontend-design`
- Paso «Carga»: lista de hojas del libro con su estado (usada / ignorada / oculta) y motivo, filas leídas y descartadas.
- Paso «BETO»: cuántas filas resolvió cada etapa de la cascada (CI exacta → encabezado → fuzzy → regex → BETO).
- Paso «Revisión»: grupos por motivo con un ejemplo enmascarado.
- Colores y animaciones del sistema; responsivo.
- Criterio: tests de componentes y verificación en el navegador (con tu 2FA).

### FU-L9 — Recarga y recongelado (`dev-alta`)
- `pg_dump` en `backups/` y recarga de los 10 archivos en la copia tmpfs.
- Comparar cada `fu_l*_fuente_vs_dw.csv` (diferencia 0 o explicada), recalcular los 23 KPI, actualizar `fuente_verdad_tesis.md` como **CONGELADO** y avisar al chat 3.
- `CIERRE_FU.md`.

## Riesgos y control
- **Solo en tmpfs:** el snapshot es de solo lectura.
- **Invariantes:** la cascada, los umbrales y el conteo de 51 / 10 / 23 no cambian.
- **PII:** ningún informe muestra CI, nombres ni contactos; los ejemplos van enmascarados con `dataops_privacy.py`.
- **Planes que se cruzan:** FU reemplaza a ADW-L0b, L2, L3, L4 y L7-C4. ADW-L1 (error 500), L5 (motor único de KPI) y L8 (aprobación en bloque) siguen vigentes.

## PRINCIPIO RECTOR — «Los archivos no se queman en el sistema» (Lean, 2026-11-20)
El sistema **no puede depender de un archivo, nombre, hoja ni orden de columnas concretos**. Los 10 libros de `uploads/data` son **casos de prueba**, no la especificación. Reglas obligatorias para todos los loops FU:
1. **Sin nombres de archivo ni de hoja en el código.** Prohibido `if "ARCA" in nombre`, `sheet_name="COBRANZAS 2024 2025"` o índices de columna fijos. Un test recorre `backend/` y `pipeline/` y falla si aparece un nombre de libro o de hoja de `uploads/data`.
2. **Detección por contenido.** El tipo de fuente sale del *score* de cabeceras y valores (`ingestion_service`), y cada hoja se clasifica sola: cabecera detectada, granularidad y si es una tabla de datos o un resumen.
3. **Mapeo por sinónimos configurables, no por código.** Columna de la fuente → campo canónico (`estado_academico`, `cuotas_en_mora`, `dias_mora`, `estado_cartera_fuente`, `leads`, `inscritos`, `puntuacion`…) desde un **catálogo editable**: `cat_mapeo_columna` en `catalog_db` (ya existe y está vacío) o `config/mapeo_fuentes.yaml` versionado, con sinónimos, normalización de acentos y mayúsculas y prioridad. Si se agrega un archivo nuevo con otras cabeceras, se añade un sinónimo, no código.
4. **Vocabularios normalizados por catálogo:** estados académicos (Deserción / Abandono → `DESERCION`), cartera, etiquetas Likert y géneros, en tablas `cat_*` de `catalog_db`. Un valor desconocido no se descarta: va a revisión como `VALOR_FUERA_DE_CATALOGO`.
5. **Los KPI leen campos canónicos, no fuentes.**
   - El **KPI-16** usa `estado_academico = DESERCION` venga del archivo que venga (ARCA hoy, Moodle u otro acta mañana).
   - Si ninguna fuente de la gestión trae ese campo, el KPI-16 queda **«sin dato»** con motivo; nunca 0. Lo mismo vale para mora, leads, satisfacción y metas.
6. **Reglas de hoja genéricas:** las hojas ocultas, las que parecen borrador o copia y las tablas dinámicas o resúmenes se detectan por *estado y forma* (oculta, pocas filas, fórmulas de agregado, cabecera repetida), no por su nombre exacto. El nombre es solo una señal más, y el resultado sale en la vista previa (FU-L8) para que el usuario lo confirme.
7. **Pruebas con archivos sintéticos** (`tests/fixtures/fuentes_sinteticas/`): las mismas fuentes con **otros nombres de archivo y de hoja, columnas en otro orden, sinónimos de cabecera, filas de basura y hojas ocultas**. El resultado en la DW debe ser idéntico al del archivo original. Este es el criterio de aceptación de FU-L1 a FU-L5.

Impacto en los loops:
- FU-L0 produce el **catálogo de mapeo** (sinónimos), no un contrato atado a nombres de archivo.
- FU-L1 a FU-L5 implementan reglas sobre campos canónicos.
- FU-L8 muestra en el front el mapeo detectado (columna → campo) y deja corregirlo antes de cargar.

## DECISIONES PENDIENTES PARA LEAN
- **DA2-bis — RESUELTA (Lean, 2026-11-20): sí, el KPI-16 se calcula desde el estado académico,** con el principio rector:
  - campo canónico `estado_academico` ∈ {`DESERCION`, `ABANDONO`} sobre la matrícula de la gestión, desde cualquier fuente que lo traiga;
  - sin fuente con ese campo → «sin dato»;
  - estimado con las fuentes actuales: ≈ 6,5 % (2024) y 4,5 % (2025), que FU-L4 confirma;
  - reemplaza a DA2 de `PLAN_AUDITORIA_DW.md` y a ADW-L3.
- **DA4 — RESUELTA (Lean, 2026-11-20): excluir del KPI-02 toda gestión sin meta mensual real.**
  - **Regla genérica** (principio rector), no «si año = 2024»: el cargador marca la granularidad de la meta (`MENSUAL` / `ANUAL`) según la forma de la fuente. Una sola celda anual cuenta como `ANUAL` y no se coloca en diciembre.
  - KPI-02 solo se calcula con meta `MENSUAL`; si no la hay, queda «sin dato» con el motivo «La fuente solo trae meta anual».
  - KPI-03, 13 y 14 usan la meta anual.
  - Resultado esperado: KPI-02 2024 pasa de 6,25 % a **sin dato**, y 2023 queda sin dato (no hay meta). FU-L6 lo implementa.
  - Reemplaza a DA4 de `PLAN_AUDITORIA_DW.md`.
- **DA6 — RESUELTA (Lean, 2026-11-20): KPI-06 se calcula con leads e inscritos de captación.**
  - **Regla genérica:** los campos canónicos `leads_captacion` e `inscritos_captacion` se mapean por sinónimos (LEADS, interesados, prospectos / N° INSCRITOS, inscritos) desde **cualquier** hoja de datos cuya granularidad sea programa×mes. Hoy salen de las hojas mensuales de planificación y de la hoja de planificación por POS (IBP).
  - **Fórmula:** Σ inscritos_captacion / Σ leads_captacion por gestión, solo con filas que tengan ambos datos y `0 ≤ inscritos ≤ leads` (la regla de la migración 014 se mantiene).
  - **Gestiones sin leads** (2023, 2024 y el primer semestre de 2025) → «sin dato». El motivo dice desde qué mes hay datos, y el drill-down muestra la cobertura mensual (meses con dato / meses de la gestión).
  - **Deduplicación:** si el mismo POS y mes aparece en varias hojas (mensual, centralizada, IBP), se cuenta una vez, con prioridad a la hoja de detalle visible. Las hojas ocultas o borradores no cuentan (FU-L1).
  - Las `RESERVAS` se guardan como dato del embudo, pero no entran en el KPI.
  - Reemplaza a DA6 de `PLAN_AUDITORIA_DW.md` y a ADW-L6-0.
- **DA-FU2 — RESUELTA (Lean, 2026-11-20): opción recomendada.** Regla genérica sobre campos canónicos (sin depender de ARCA):
  - El cargador guarda `nota_final` numérica y un **resultado** canónico por módulo (`APROBADO`, `REPROBADO`, `INASISTENCIA`, `EXIMIDO`, `SIN_NOTA`), según el número o el vocabulario `cat_*`: «Aprobó» → `APROBADO`; «No asistió», «Nunca ingresó», «Faltas y no envió» → `INASISTENCIA`; «EXIMIDA» → `EXIMIDO`; «SIN NOTAS EN EL ACTA…» → `SIN_NOTA`.
  - Un **0** cuenta como `INASISTENCIA` cuando el estado del estudiante es Deserción o Abandono o el texto lo indica. Si no, es un 0 real y se queda con `nota_final = 0`.
  - **KPI-07 (promedio):** solo notas numéricas de 1 a 100, sin `INASISTENCIA`, `EXIMIDO` ni `SIN_NOTA`. Un 0 real sí entra.
  - **KPI-08 (aprobación):** `APROBADO` (nota ≥ 70 o texto «Aprobó») / (`APROBADO` + `REPROBADO` + `INASISTENCIA`). `EXIMIDO` y `SIN_NOTA` quedan fuera del denominador.
  - Las notas mayores de 100 o con texto que no está en el catálogo (apellidos, CI) van a revisión como `NOTA_FUERA_DE_RANGO` o `VALOR_FUERA_DE_CATALOGO` (FU-L7).
  - FU-L4 entrega la tabla antes/después de KPI-07 y 08 por gestión.
- **DA-FU3 — RESUELTA (Lean, 2026-11-20): para metas e ingresos ejecutados manda la fuente de tipo RENTABILIDAD (hoy `EJECUTADO VS META`).**
  - **Regla genérica** de prioridad por **tipo de fuente y campo**, no por nombre de archivo, configurable en el catálogo de mapeo:
    - `monto_meta` y `monto_ejecutado`: RENTABILIDAD > EGRESOS;
    - egresos y costos por programa: EGRESOS > RENTABILIDAD.
  - Si dos fuentes del mismo lote dan otro valor para el mismo campo y mes, se carga el de la fuente prioritaria y se registra `CONFLICTO_FUENTES` como **resuelto automáticamente por regla**, con los dos valores y la diferencia. Va a la bandeja solo como informativo, no como pendiente.
  - Los 10 `CONFLICTO_FUENTES` pendientes se cierran con esta regla en FU-L6. El informe `fu_l6_conflictos_metas.csv` lista mes, valor elegido, valor descartado y diferencia (las de 100.000 quedan señaladas para avisar al área financiera).
- **DA7 — RESUELTA (Lean, 2026-11-21 · `2298a8b`):** catálogo de programas se descarta con `CATALOGO_PROGRAMA_NO_PAGO` / `CATALOGO_PROGRAMA_NO_ALUMNO`; docentes sin CI se descartan con `DOCENTE_NO_ESTUDIANTE`; los 18 residuales reales van a bandeja sin crear perfil `TEMP` (estado `B`).

Al cerrar cada loop: pytest del loop (`tests/fu_l<n>`) · vitest (si toca front DataOps) · commit acotado `fu(L<n>): …` · `CIERRE_FU_L<n>.md`.

---

## PARTE 4 — Estado real y plan de cierre **PARTE A** (actualización 2026-11-21)

> **Frontera estricta (sin choque con `PLAN_AUDITORIA_DW.md` — PARTE B):**
> - **Alcance exclusivo de PARTE A:** evaluación de archivos en `uploads/data`, clasificación de qué SÍ/NO se inserta, qué SÍ/NO va a revisión humana, backend de revisión/ingesta/lectura DataOps y pantallas del flujo DataOps (3 pasos).
> - **Regla de evaluación sin tocar el core:** no modificar el código core de `pipeline/` ni los `tests/sprint*` durante esta fase; primero evaluar con las evidencias de `uploads/data` y tmpfs qué falla en pipeline/BETO, qué entra o no entra y qué va o no va a revisión humana.
> - **Archivos exclusivos de PARTE A:** `scripts/auditoria_fuentes/`, `backend/services/{bandeja_grupos,revision_consulta}.py`, `backend/routers/dataops/{ingesta,lectura,revision}.py`, `frontend/src/modules/dataops/*` (y `tests/fu_l6..l8`). No toca `routers/cmi.py`, `frontend/src/modules/admin/cmi/*` ni vistas `bi.vw_cmi_*` (que pertenecen a PARTE B).

### Avance verificado (rama `beto-integracion` · `03c1a6f`)
- **Cerrados:** `FU-L0`, `FU-L1`, `FU-L2`, `FU-L3`, `FU-L4`, `FU-L5` (`CIERRE_FU_L0.md`..`CIERRE_FU_L5.md`).
- **En curso sin cerrar:** `FU-L6` (código y `tests/fu_l6/` en el árbol de trabajo; `fu_l6_pg_tmpfs` en `127.0.0.1:55441`; faltan los 3 CSV en `docs/mediciones/fu_l6_*`, commit y `CIERRE_FU_L6.md`).
- **Pendientes:** `FU-L7` (revisión humana con sentido), `FU-L8` (contratos + front DataOps) y `FU-L9` (recarga final + recongelado — `dev-alta`).

### Tareas pendientes PARTE A — `dev-baja` (evaluación en tmpfs, matriz de decisiones y unit tests DataOps)

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en `docs/mediciones/` |
|---|---|---|---|---|---|---|
| **FU-B1** | **Evidencia de `FU-L6` en tmpfs:** ejecutar `fu_l6_recarga_metas.py`, `fu_l6_comparar_fuente_vs_dw.py` contra `fu_l6_pg_tmpfs` (`55441`) y `pytest tests/fu_l6 -v` (sin tocar `tests/sprint*`); verificar 0 PII y redactar borrador `CIERRE_FU_L6.md`. | `dev-baja` | — | FU-B2 | 3 CSV en `docs/mediciones/fu_l6_*.csv`; salida literal de `pytest tests/fu_l6`; borrador `CIERRE_FU_L6.md`. | `fu_l6_metas_fuente_vs_dw.csv`, `fu_l6_conflictos_metas.csv`, `fu_l6_kpi_antes_despues.csv` |
| **FU-B2** | **Matriz de evaluación de `uploads/data` (solo lectura):** consolidar los resultados de `fu_l0..fu_l6` y tmpfs en una tabla única por tipo de fuente y hoja (61 hojas) detallando: **(1) qué falla en pipeline y BETO**, **(2) qué SÍ debe insertarse**, **(3) qué NO debe insertarse** (ocultas, borradores, subtotales, filas fantasma, ceros «Sin Información», doble columna) y **(4) qué SÍ vs qué NO debe ir a revisión humana**. | `dev-baja` | FU-B1 (para metas) | FU-M2 | 100 % de las 61 hojas y tipos de anomalía clasificados con conteos reales de `docs/mediciones/` y 0 PII. | `fu_eval_matriz_decisiones.md`, `fu_eval_matriz_decisiones.csv` |
| **FU-B3** | **Unit tests front DataOps + guardia «cero hex sueltos»:** tests Vitest para `motivosBandeja.js` (todos los motivos nuevos + enmascarado sin PII), `GruposBandeja.jsx` y `BetoReadingFlowView.jsx`, más chequeo automatizado de cero `#RRGGBB` hardcodeados en `frontend/src/modules/dataops/`. | `dev-baja` | FU-M3b | — | `npx vitest run` 100 % verde; 0 fugas PII; 0 hex sueltos en DataOps. | `fu_l8_vitest_dataops.txt` |

### Tareas pendientes PARTE A — `dev-media` (revisión humana y vistas DataOps)

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en `docs/mediciones/` |
|---|---|---|---|---|---|---|
| **FU-M1** | **Ajustes de cierre de `FU-L6` (solo si `FU-B1` detecta fallas):** corregir únicamente lo que falle en `tests/fu_l6` o diferencias ≠ 0 en metas tmpfs, sin tocar `pipeline/` core ni `tests/sprint*`. | `dev-media` | FU-B1 | FU-M2 | `pytest tests/fu_l6` 100 % verde; diferencia 0 fuente vs tmpfs; 0 `CONFLICTO_FUENTES` pendientes. | `fu_l6_metas_fuente_vs_dw.csv` |
| **FU-M2** | **`FU-L7` — Revisión humana con sentido (backend):** (1) añadir catálogo de motivos nuevos (`HOJA_IGNORADA` solo informativo fuera de bandeja, `NOTA_FUERA_DE_RANGO`, `RESPUESTA_EN_COLUMNA_EQUIVOCADA`, `CUOTAS_NEGATIVAS`, `CONFLICTO_META`, `VALOR_FUERA_DE_CATALOGO`, `PUNTUACION_FUERA_DE_ESCALA`, `ESCALA_NO_INFERIBLE`) en `bandeja_grupos.py`, `revision_consulta.py` y `routers/dataops/revision.py`; (2) **corregir bug**: propagar `patrones` y `patron` en `revision_consulta.py:280-299` (`grupos_publicos`); (3) devolver explicación estructurada (`regla`, `umbral`, `valor_enmascarado` vía `dataops_privacy.py`); (4) descartar las 5 filas vacías con confianza `0,0000` (doc 44) y agrupar los 1.255 `VALOR_FUERA_DE_CATALOGO`. | `dev-media` | — | FU-B1, FU-B2 | `GET /review-tray/grupos` expone `patrones`, `patron` y explicación sin PII; `HOJA_IGNORADA` = 0 en bandeja pendiente; `pytest tests/fu_l7` 100 % verde. | `fu_l7_bandeja_antes_despues.json` |
| **FU-M3a** | **`FU-L8` — Contratos backend DataOps:** (1) endpoint de vista previa en `routers/dataops/ingesta.py` (`POST /preview-workbook` o equivalente) con hojas (usada/ignorada/oculta + motivo + filas estimadas) y mapeo editable `columna → campo canónico`; (2) agregar `resumen_cascada` (`CI_EXACTA`, `ENCABEZADO`, `FUZZY`, `REGEX`, `BETO`) en `routers/dataops/lectura.py` (`/resumen` y `/beto-reading`). | `dev-media` | FU-M2 | — | `pytest tests/fu_l8` 100 % verde; 0 PII; sin romper contratos existentes. | `fu_l8_contratos_dataops.json` |
| **FU-M3b** | **`FU-L8` — Front DataOps (React/V2):** siguiendo el diseño visual corroborado en `http://localhost/` (`tokens.css` / `v2-layout.css`, cero hex sueltos, stepper de 3 pasos, tarjetas `rounded-2xl`, claro/oscuro, responsivo): (1) `IngestView.jsx` vista previa por hoja + tabla editable `columna → campo canónico`; (2) `BetoReadingFlowView.jsx` resumen de cascada con `ORIGEN_INFO` + `AnimatedProgressBarV2` + bloque `"Qué significa:"`; (3) `HumanReviewFlowView.jsx` + `GruposBandeja.jsx` + `motivosBandeja.js` mostrando `patrones`, motivos nuevos y bloque `"Por qué está aquí"`. | `dev-media` | FU-M2, FU-M3a | — | `npx vitest run` y `npm run build` en verde; 0 hex sueltos en diff de DataOps. | `fu_l8_componentes_dataops.json` |

### Cierre final PARTE A — `dev-alta` (diferido hasta aprobar `FU-B2` y cerrar PARTE B)
- **`FU-L9`:** aplicar limpieza de deuda del principio rector + recarga controlada del lote en tmpfs/DW viva + recongelado coordinado con `ADW-L9`.

## PROMPT PARA CHAT 2 — PARTE A (`dev-media` o `dev-baja`)
```text
/gira-desarrollar
Ejecuta SOLO la tarea <FU-B1 | FU-B2 | FU-B3 | FU-M1 | FU-M2 | FU-M3a | FU-M3b> de docs/cierres/PLAN_FUENTES_UPLOADS.md (PARTE 4 — PARTE A).
- NO toques el código core de pipeline/ ni los tests/sprint*, ni los archivos de CMI/vistas bi (reservados a PLAN_AUDITORIA_DW.md — PARTE B).
- Hay cambios sin commitear de otras sesiones: haz git add SOLO de tus archivos (nunca git add -A).
- Recargas y pruebas solo en tmpfs (nunca sobre snapshot_dw_20261110_1201 ni la DW viva).
- Sin PII en informes ni respuestas; en front DataOps usa solo tokens de tokens.css / v2-tokens.css (cero hex sueltos).
- Cierra con pruebas del ticket, evidencia en docs/mediciones/, commit acotado y CIERRE_FU_L<n>.md.
```
