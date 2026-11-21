# L8-0: filas sin estudiante (solo lectura)

Fecha: 2026-11-20. Fuente: `public.stg_entidad_no_resuelta` en la copia efímera `adw_pg_tmpfs` (no se tocó la DW viva ni el snapshot). Script: `scripts/auditoria_dw/adw_l8_0_filas_sin_estudiante.py` (solo imprime agregados). Sin CI, nombres, correos ni payloads en este informe: no se listó ningún identificador, por lo que no hizo falta enmascarar (criterio de `dataops_privacy.py`: CI como `••••123`).

## 1. Conteos de partida

| Motivo | Documento | Filas | Descarte / tipo_fuente |
|---|---|---|---|
| FILA_FINANCIERA_SIN_ESTUDIANTE | 36 (`BD Cobranzas.xlsx`) | 474 | RUIDO / COBRANZA |
| FILA_ACADEMICA_SIN_ESTUDIANTE | 43 (`Base centralizada Académica ARCA (1).xlsx`) | 834 | RUIDO / ACTA |

Todas las filas tienen `clave_origen`, `payload_json` y `texto_original`. `ci_temporal` está vacío en las 1.308. El payload trae `raw_line`, `tipo_fuente` y `descarte`; no trae hoja (**hoja: no determinado**).

## 2. Reglas de clasificación (una clase por fila, en este orden)

- **D (totales/encabezados):** la línea no tiene campos «etiqueta: valor», o contiene «total», «subtotal», «encabezado» o «cabecera», o tiene 1 solo campo.
- **C (CI fuera de `dim_estudiante`):** hay un CI de 5 a 10 dígitos (etiqueta tipo CI/cédula/documento/NIT/código estudiante, o valor suelto) y ningún CI coincide con `dim_estudiante` (no deprecados).
- **E (otra):** CI presente y que sí existe en `dim_estudiante`, o caso no previsto.
- **B (nombre sin CI):** etiqueta de nombre (nombre(s), estudiante, alumno, apellido, razón social, docente) con valor, sin CI.
- **A (sin CI ni nombre):** ninguna de las anteriores.

## 3. Resultados por clase

| Clase | Financieras (474) | Académicas (834) | Total |
|---|---|---|---|
| A sin CI ni nombre | 472 (99,6 %) | 766 (91,8 %) | 1.238 |
| B nombre sin CI | 0 | 68 (8,2 %) | 68 |
| C CI fuera de dim | 0 | 0 | 0 |
| D totales/encabezados | 0 | 0 | 0 |
| E otra (CI existente en dim) | 2 (0,4 %) | 0 | 2 |

Clase C: 0 filas, así que rescatables por nombre exacto = 0. Clase B: 68 filas, todas con etiqueta «DOCENTE»; ninguna coincide con un estudiante de `dim_estudiante` (coincidencia normalizada exacta).

Subtipos de A: 7 filas académicas con estado académico individual (sin identidad); 1.222 de catálogo de programas, cursos o módulos (financieras 472 y académicas 750 en su mayoría); 9 restantes sin etiqueta reconocible.

## 4. Financieras (doc 36)

- Etiquetas presentes: POS, fecha de inicio, nombre del programa, inscritos, diplomas emitidos, costo programa, tipo de programa. Solo 2 filas traen «Monto en Bs.», «Canal de Pago» y «N.° de Factura».
- Suma de «Monto en Bs.»: **1.523,00 Bs** (2 filas, ambas en clase E).
- Deuda y pagado por fila: **no determinado**. No hay etiqueta de deuda, saldo, pagado ni cuota en el payload.
- Cuotas impagas ≥ 2 (DA3): **no determinado**, sin etiqueta de cuotas.
- Porción de la deuda de cartera: deuda total `adw_l0_cartera.csv` = 4.828.010,08 Bs. Los 1.523,00 Bs representan **0,0315 %**. Este cociente es solo ilustrativo, porque el monto no es deuda pendiente.
- Lectura importante: 472 de 474 filas son catálogo de programas, no pagos ni deudas. La premisa «pagos que desaparecen» aplica solo a 2 filas.

## 5. Académicas (doc 43)

- Notas o calificaciones: **no determinado**. No hay campo de nota, calificación ni promedio (0 campos).
- Gestión (AÑO IBP): 2024 = 275, 2025 = 327, 2026 = 147 (749 filas con dato; 85 sin año).
- Programas distintos: 405 (nombres no mostrados).
- Estados de programa: cerrado 383, inicio confirmado 152, abierto 72, reprogramado 21, baja 10, otros 2.
- Estados académicos individuales (7 filas, sin identidad): aprobado, reprobado, deserción, en curso, participó, titulado, no titulado, abandono, congelamiento, tutoría, insuficiencia académica.
- Las 68 filas de clase B son de docentes: no son estudiantes y el invariante prohíbe docentes en el catálogo.

## 6. Propuesta de salida por clase (decide Lean)

| Clase | Filas | Propuesta | Justificación |
|---|---|---|---|
| Financiera A (catálogo) | 472 | Descarte automático con motivo `CATALOGO_PROGRAMA_NO_PAGO` | No son pagos ni deudas; revisar por muestreo antes del descarte. |
| Financiera E (CI existente) | 2 | **Bandeja de revisión humana** y revisar por qué la cascada (CI_EXACTA) no las enlazó | Son los únicos pagos (1.523,00 Bs) y su CI sí existe en `dim_estudiante`. Crear TEMP sería duplicar un estudiante. |
| Académica A con estado individual | 7 | Bandeja de revisión humana | Sin nombre ni CI no se puede crear perfil TEMP (requiere identidad). |
| Académica A catálogo | 750 | Descarte automático con motivo `CATALOGO_PROGRAMA_NO_ALUMNO` | Son programas, cursos o módulos. |
| Académica A restantes | 9 | Bandeja de revisión humana | Sin patrón claro; revisar. |
| Académica B (docentes) | 68 | Descarte automático con motivo `DOCENTE_NO_ESTUDIANTE` | Son docentes, fuera del catálogo; no admiten perfil TEMP de estudiante. Sus datos personales no se muestran. |
| C | 0 | Sin acción | No hay filas. |

Alternativa TEMP (estado B): **no recomendada** para ninguna clase, porque no hay identidad suficiente en A y B es docente. Solo la E podría ser un perfil TEMP si la CI existente se confirmara como de otra persona.

## 7. Limitaciones

- La clase E (CI existente) requiere revisar el enlace: no se comprobó si el CI coincide con el mismo estudiante del pago o si es un NIT institucional.
- No hay campos de deuda, pagado, cuotas ni notas en el payload. Para la cifra de cartera hay que usar la fuente de cobranzas, no este payload (**no determinado**).
- Se usó solo la copia tmpfs; no se verificó el staging de origen de cada hoja.

Comando de reproducción: `python scripts/auditoria_dw/adw_l8_0_filas_sin_estudiante.py`
